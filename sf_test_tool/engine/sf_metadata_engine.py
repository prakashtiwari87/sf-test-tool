"""
sf_metadata_engine.py
Automatically discovers and caches ALL Salesforce org metadata.
Runs on org connect — no manual configuration needed.
Fast-fails gracefully if features not enabled in org.

ENHANCED VERSION with selective sync support.
"""

import sqlite3
import json
import os
import requests
from datetime import datetime
from typing import Optional, Callable, List
from config.settings_manager import DB_PATH


# ─────────────────────────────────────────────────────────────
# DATABASE SETUP FOR METADATA
# ─────────────────────────────────────────────────────────────

def init_metadata_db():
    """Create all metadata tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_objects (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain    TEXT NOT NULL,
            object_name   TEXT NOT NULL,
            object_label  TEXT,
            object_type   TEXT,
            is_custom     INTEGER DEFAULT 0,
            is_queryable  INTEGER DEFAULT 1,
            is_createable INTEGER DEFAULT 1,
            is_updateable INTEGER DEFAULT 1,
            is_deletable  INTEGER DEFAULT 1,
            record_count  INTEGER DEFAULT 0,
            synced_at     TEXT,
            UNIQUE(org_domain, object_name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_fields (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            object_name     TEXT NOT NULL,
            field_name      TEXT NOT NULL,
            field_label     TEXT,
            field_type      TEXT,
            is_required     INTEGER DEFAULT 0,
            is_custom       INTEGER DEFAULT 0,
            is_createable   INTEGER DEFAULT 1,
            is_updateable   INTEGER DEFAULT 1,
            is_nillable     INTEGER DEFAULT 1,
            max_length      INTEGER,
            picklist_values TEXT,
            reference_to    TEXT,
            default_value   TEXT,
            UNIQUE(org_domain, object_name, field_name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_packages (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain     TEXT NOT NULL,
            package_name   TEXT,
            namespace      TEXT,
            version        TEXT,
            package_type   TEXT,
            install_date   TEXT,
            synced_at      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_apps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain   TEXT NOT NULL,
            app_name     TEXT,
            app_label    TEXT,
            app_type     TEXT,
            is_default   INTEGER DEFAULT 0,
            synced_at    TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_agents (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain    TEXT NOT NULL,
            agent_name    TEXT,
            agent_label   TEXT,
            agent_type    TEXT,
            channel       TEXT,
            status        TEXT,
            description   TEXT,
            synced_at     TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_flows (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain   TEXT NOT NULL,
            flow_name    TEXT,
            flow_label   TEXT,
            flow_type    TEXT,
            status       TEXT,
            object_name  TEXT,
            synced_at    TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_validation_rules (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain   TEXT NOT NULL,
            object_name  TEXT,
            rule_name    TEXT,
            is_active    INTEGER,
            description  TEXT,
            error_msg    TEXT,
            synced_at    TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sf_sync_status (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain     TEXT NOT NULL UNIQUE,
            last_sync      TEXT,
            total_objects  INTEGER DEFAULT 0,
            total_fields   INTEGER DEFAULT 0,
            total_agents   INTEGER DEFAULT 0,
            total_packages INTEGER DEFAULT 0,
            total_apps     INTEGER DEFAULT 0,
            total_flows    INTEGER DEFAULT 0,
            sync_duration  TEXT,
            status         TEXT DEFAULT 'never'
        )
    """)

    # Migrate existing tables to add missing columns
    _migrate_sync_status_table(cur)

    conn.commit()
    conn.close()


def _migrate_sync_status_table(cur):
    """Add any missing columns to sf_sync_status table"""
    try:
        cur.execute("PRAGMA table_info(sf_sync_status)")
        existing = [row[1] for row in cur.fetchall()]
        migrations = [
            ("total_apps",
             "ALTER TABLE sf_sync_status ADD COLUMN total_apps  INTEGER DEFAULT 0"),
            ("total_flows",
             "ALTER TABLE sf_sync_status ADD COLUMN total_flows INTEGER DEFAULT 0"),
        ]
        for col, sql in migrations:
            if col not in existing:
                cur.execute(sql)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _get_headers(sf) -> dict:
    return {
        "Authorization": f"Bearer {sf.session_id}",
        "Content-Type":  "application/json"
    }


def _api_get(sf, endpoint: str, timeout: int = 10) -> tuple:
    """Make a Salesforce REST API GET call with timeout"""
    instance = sf.sf_instance
    if not instance.startswith("https://"):
        instance = f"https://{instance}"
    url = f"{instance}{endpoint}"
    try:
        resp = requests.get(
            url, headers=_get_headers(sf), timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def _safe_soql(sf, query: str) -> list:
    """
    Run a SOQL query safely.
    Returns empty list on any error — never raises.
    """
    try:
        from connectors.salesforce_connector import run_soql_query
        records, err = run_soql_query(sf, query)
        if err or not records:
            return []
        return records
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# DISCOVERY FUNCTIONS
# ─────────────────────────────────────────────────────────────

def discover_all_objects(sf, org_domain: str,
                         progress_callback=None,
                         selected_objects: Optional[List[str]] = None) -> tuple:
    """
    Discover ALL objects in the org — standard and custom.
    If selected_objects is provided, only sync those specific objects.
    Returns list of object metadata dicts.
    """
    data, err = _api_get(sf, "/services/data/v59.0/sobjects/")
    if err:
        return [], err

    sobjects   = data.get("sobjects", [])
    
    # Filter to selected objects if specified
    if selected_objects:
        sobjects = [o for o in sobjects if o.get("name") in selected_objects]
    
    discovered = []
    conn       = sqlite3.connect(DB_PATH)
    cur        = conn.cursor()

    for i, obj in enumerate(sobjects):
        name = obj.get("name", "")
        if not name:
            continue

        is_custom = name.endswith("__c") or name.endswith("__x")
        record = {
            "org_domain":    org_domain,
            "object_name":   name,
            "object_label":  obj.get("label", name),
            "object_type":   "Custom" if is_custom else "Standard",
            "is_custom":     1 if is_custom else 0,
            "is_queryable":  1 if obj.get("queryable")  else 0,
            "is_createable": 1 if obj.get("createable") else 0,
            "is_updateable": 1 if obj.get("updateable") else 0,
            "is_deletable":  1 if obj.get("deletable")  else 0,
            "synced_at":     datetime.now().isoformat()
        }

        cur.execute("""
            INSERT INTO sf_objects
            (org_domain, object_name, object_label, object_type,
             is_custom, is_queryable, is_createable, is_updateable,
             is_deletable, synced_at)
            VALUES (:org_domain,:object_name,:object_label,:object_type,
                    :is_custom,:is_queryable,:is_createable,
                    :is_updateable,:is_deletable,:synced_at)
            ON CONFLICT(org_domain, object_name) DO UPDATE SET
            object_label = excluded.object_label,
            synced_at    = excluded.synced_at
        """, record)
        discovered.append(record)

        if progress_callback and i % 20 == 0:
            progress_callback(f"Scanning objects: {i}/{len(sobjects)}", int((i/len(sobjects))*10))

    conn.commit()
    conn.close()
    return discovered, None


def discover_object_fields(sf, org_domain: str,
                           object_name: str) -> tuple:
    """
    Discover ALL fields for a specific Salesforce object.
    Includes type, picklist values, relationships and constraints.
    """
    data, err = _api_get(
        sf,
        f"/services/data/v59.0/sobjects/{object_name}/describe/",
        timeout=15
    )
    if err:
        return [], err

    fields     = data.get("fields", [])
    discovered = []
    conn       = sqlite3.connect(DB_PATH)
    cur        = conn.cursor()

    for field in fields:
        fname = field.get("name", "")
        if not fname:
            continue

        picklist = [
            pv.get("value", "")
            for pv in field.get("picklistValues", [])
            if pv.get("active")
        ]
        refs = [r for r in field.get("referenceTo", []) if r]

        record = {
            "org_domain":      org_domain,
            "object_name":     object_name,
            "field_name":      fname,
            "field_label":     field.get("label", fname),
            "field_type":      field.get("type", "string"),
            "is_required":     0 if field.get("nillable", True) else 1,
            "is_custom":       1 if fname.endswith("__c") else 0,
            "is_createable":   1 if field.get("createable") else 0,
            "is_updateable":   1 if field.get("updateable") else 0,
            "is_nillable":     1 if field.get("nillable")   else 0,
            "max_length":      field.get("length", 0),
            "picklist_values": json.dumps(picklist) if picklist else None,
            "reference_to":    json.dumps(refs)     if refs     else None,
            "default_value":   str(field.get("defaultValue","")) or None
        }

        cur.execute("""
            INSERT INTO sf_fields
            (org_domain, object_name, field_name, field_label,
             field_type, is_required, is_custom, is_createable,
             is_updateable, is_nillable, max_length,
             picklist_values, reference_to, default_value)
            VALUES (:org_domain,:object_name,:field_name,:field_label,
                    :field_type,:is_required,:is_custom,:is_createable,
                    :is_updateable,:is_nillable,:max_length,
                    :picklist_values,:reference_to,:default_value)
            ON CONFLICT(org_domain, object_name, field_name) DO UPDATE SET
            field_label     = excluded.field_label,
            field_type      = excluded.field_type,
            picklist_values = excluded.picklist_values
        """, record)
        discovered.append(record)

    conn.commit()
    conn.close()
    return discovered, None


def discover_agents(sf, org_domain: str, progress_callback=None) -> tuple:
    """
    Discover Agentforce / Einstein AI Agents.
    Fast-fails silently if org does not have Agentforce enabled.
    """
    if progress_callback:
        progress_callback("Checking for Agentforce / AI Agents...", 42)
    
    agents = []
    conn   = sqlite3.connect(DB_PATH)
    cur    = conn.cursor()

    agent_queries = [
        (
            "SELECT Id, DeveloperName, MasterLabel, Description, Status "
            "FROM BotDefinition LIMIT 100",
            "Agentforce", "Chat"
        ),
        (
            "SELECT Id, DeveloperName, MasterLabel, Description "
            "FROM GenAiApplication LIMIT 100",
            "GenAI Agent", "Multi-channel"
        ),
    ]

    for query, agent_type, channel in agent_queries:
        records = _safe_soql(sf, query)
        for r in records:
            agent = {
                "org_domain":  org_domain,
                "agent_name":  r.get("DeveloperName", ""),
                "agent_label": r.get("MasterLabel", ""),
                "agent_type":  agent_type,
                "channel":     channel,
                "status":      r.get("Status", "Active"),
                "description": r.get("Description", ""),
                "synced_at":   datetime.now().isoformat()
            }
            try:
                cur.execute("""
                    INSERT INTO sf_agents
                    (org_domain, agent_name, agent_label,
                     agent_type, channel, status, description, synced_at)
                    VALUES (:org_domain,:agent_name,:agent_label,
                            :agent_type,:channel,:status,
                            :description,:synced_at)
                """, agent)
                agents.append(agent)
            except Exception:
                pass

    conn.commit()
    conn.close()
    
    if progress_callback:
        progress_callback(f"✓ {len(agents)} agent(s) synced", 44)
    
    return agents, None


def discover_installed_packages(sf, org_domain: str, progress_callback=None) -> tuple:
    """
    Discover all installed managed packages.
    Fast-fails silently if none exist.
    """
    if progress_callback:
        progress_callback("Checking installed packages...", 76)
    
    packages = []
    conn     = sqlite3.connect(DB_PATH)
    cur      = conn.cursor()

    records = _safe_soql(
        sf,
        "SELECT Id, SubscriberPackage.Name, "
        "SubscriberPackage.NamespacePrefix, "
        "SubscriberPackageVersion.MajorVersion, "
        "SubscriberPackageVersion.MinorVersion "
        "FROM InstalledSubscriberPackage LIMIT 200"
    )

    for r in records:
        pkg = r.get("SubscriberPackage") or {}
        ver = r.get("SubscriberPackageVersion") or {}
        package = {
            "org_domain":   org_domain,
            "package_name": pkg.get("Name", ""),
            "namespace":    pkg.get("NamespacePrefix", ""),
            "version": (
                f"{ver.get('MajorVersion','')}"
                f".{ver.get('MinorVersion','')}"
                if ver else ""
            ),
            "package_type": "Managed",
            "synced_at":    datetime.now().isoformat()
        }
        try:
            cur.execute("""
                INSERT INTO sf_packages
                (org_domain, package_name, namespace,
                 version, package_type, synced_at)
                VALUES (:org_domain,:package_name,:namespace,
                        :version,:package_type,:synced_at)
            """, package)
            packages.append(package)
        except Exception:
            pass

    conn.commit()
    conn.close()
    
    if progress_callback:
        progress_callback(f"✓ {len(packages)} package(s) synced", 82)
    
    return packages, None


def discover_custom_apps(sf, org_domain: str, progress_callback=None) -> tuple:
    """
    Discover all Lightning apps.
    Fast-fails silently if AppDefinition not available.
    """
    if progress_callback:
        progress_callback("Checking custom apps...", 70)
    
    apps = []
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    records = _safe_soql(
        sf,
        "SELECT Id, DeveloperName, Label, IsDefault, Type "
        "FROM AppDefinition LIMIT 200"
    )

    for r in records:
        app = {
            "org_domain": org_domain,
            "app_name":   r.get("DeveloperName", ""),
            "app_label":  r.get("Label", ""),
            "app_type":   r.get("Type", "Standard"),
            "is_default": 1 if r.get("IsDefault") else 0,
            "synced_at":  datetime.now().isoformat()
        }
        try:
            cur.execute("""
                INSERT INTO sf_apps
                (org_domain, app_name, app_label,
                 app_type, is_default, synced_at)
                VALUES (:org_domain,:app_name,:app_label,
                        :app_type,:is_default,:synced_at)
            """, app)
            apps.append(app)
        except Exception:
            pass

    conn.commit()
    conn.close()
    
    if progress_callback:
        progress_callback(f"✓ {len(apps)} app(s) synced", 74)
    
    return apps, None


def discover_flows(sf, org_domain: str, progress_callback=None) -> tuple:
    """
    Discover all active Flows and Process Automations.
    Fast-fails silently if not accessible.
    """
    if progress_callback:
        progress_callback("Checking flows and automations...", 46)
    
    flows = []
    conn  = sqlite3.connect(DB_PATH)
    cur   = conn.cursor()

    records = _safe_soql(
        sf,
        "SELECT Id, ApiName, Label, ProcessType, Status "
        "FROM FlowDefinitionView "
        "WHERE Status != 'Obsolete' LIMIT 200"
    )

    for r in records:
        flow = {
            "org_domain":  org_domain,
            "flow_name":   r.get("ApiName", ""),
            "flow_label":  r.get("Label", ""),
            "flow_type":   r.get("ProcessType", ""),
            "status":      r.get("Status", ""),
            "object_name": "",
            "synced_at":   datetime.now().isoformat()
        }
        try:
            cur.execute("""
                INSERT INTO sf_flows
                (org_domain, flow_name, flow_label,
                 flow_type, status, object_name, synced_at)
                VALUES (:org_domain,:flow_name,:flow_label,
                        :flow_type,:status,:object_name,:synced_at)
            """, flow)
            flows.append(flow)
        except Exception:
            pass

    conn.commit()
    conn.close()
    
    if progress_callback:
        progress_callback(f"✓ {len(flows)} flow(s) synced", 52)
    
    return flows, None


# ─────────────────────────────────────────────────────────────
# FULL ORG SYNC
# ─────────────────────────────────────────────────────────────

def sync_full_org_metadata(sf, org_domain: str,
                            progress_callback=None,
                            objects_to_detail: int = 60) -> dict:
    """
    Full org metadata sync.
    Discovers objects, fields, agents, packages, apps and flows.
    Each step fast-fails gracefully — never hangs.
    """
    init_metadata_db()
    start = datetime.now()

    def log(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    summary = {
        "org_domain": org_domain,
        "objects":    0,
        "fields":     0,
        "agents":     0,
        "packages":   0,
        "apps":       0,
        "flows":      0,
        "errors":     [],
        "started_at": start.isoformat()
    }

    # 1 — Discover all objects
    log("Scanning all Salesforce objects...", 5)
    objects, err = discover_all_objects(sf, org_domain, log)
    if err:
        summary["errors"].append(f"Objects: {err}")
    else:
        summary["objects"] = len(objects)
        log(f"Found {len(objects)} objects", 10)

    # 2 — Pull field details for priority objects first
    priority_objects = [
        "Contact", "Account", "Lead", "Opportunity", "Case",
        "Task", "Event", "Campaign", "Contract", "Order",
        "Product2", "Asset", "Quote", "User"
    ]

    custom_objects = [
        o["object_name"] for o in objects
        if o.get("is_custom")
        and o.get("is_queryable")
        and not any(o["object_name"].endswith(s) for s in [
            "__History", "__Share", "__Feed",
            "__Tag", "__ChangeEvent"
        ])
    ]

    other_objects = [
        o["object_name"] for o in objects
        if o["object_name"] not in priority_objects
        and o["object_name"] not in custom_objects
        and o.get("is_queryable")
    ]

    detail_list = (
        priority_objects
        + custom_objects[:30]
        + other_objects
    )[:objects_to_detail]

    log(f"Pulling field details for {len(detail_list)} objects...", 15)
    total_fields = 0

    for i, obj_name in enumerate(detail_list):
        pct = 15 + int((i / len(detail_list)) * 25)  # 15-40%
        log(f"Fields ({i+1}/{len(detail_list)}): {obj_name}", pct)
        fields, err = discover_object_fields(sf, org_domain, obj_name)
        if not err:
            total_fields += len(fields)

    summary["fields"] = total_fields
    log(f"Discovered {total_fields} fields across {len(detail_list)} objects", 40)

    # 3 — Agents
    agents, _ = discover_agents(sf, org_domain, log)
    summary["agents"] = len(agents)

    # 4 — Flows
    flows, _ = discover_flows(sf, org_domain, log)
    summary["flows"] = len(flows)

    # 5 — Apps
    apps, _ = discover_custom_apps(sf, org_domain, log)
    summary["apps"] = len(apps)

    # 6 — Packages
    packages, _ = discover_installed_packages(sf, org_domain, log)
    summary["packages"] = len(packages)

    # Save sync status
    duration             = str(datetime.now() - start).split(".")[0]
    summary["sync_duration"] = duration
    summary["completed_at"]  = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO sf_sync_status
        (org_domain, last_sync, total_objects, total_fields,
         total_agents, total_packages, total_apps, total_flows,
         sync_duration, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete')
        ON CONFLICT(org_domain) DO UPDATE SET
        last_sync      = excluded.last_sync,
        total_objects  = excluded.total_objects,
        total_fields   = excluded.total_fields,
        total_agents   = excluded.total_agents,
        total_packages = excluded.total_packages,
        total_apps     = excluded.total_apps,
        total_flows    = excluded.total_flows,
        sync_duration  = excluded.sync_duration,
        status         = 'complete'
    """, (
        org_domain,
        datetime.now().isoformat(),
        summary["objects"],
        summary["fields"],
        summary["agents"],
        summary["packages"],
        summary["apps"],
        summary["flows"],
        duration
    ))
    conn.commit()
    conn.close()

    log(f"Sync complete in {duration}", 100)
    return summary


# ─────────────────────────────────────────────────────────────
# SELECTIVE SYNC FUNCTION (NEW)
# ─────────────────────────────────────────────────────────────

def selective_sync_metadata(sf, org_domain: str,
                            metadata_types: List[str],
                            progress_callback: Optional[Callable] = None,
                            selected_objects: Optional[List[str]] = None) -> dict:
    """
    Selectively sync specific metadata types.
    
    Args:
        sf: Salesforce connection
        org_domain: Organization domain
        metadata_types: List of types to sync. Options:
            - 'objects': Sync objects and fields
            - 'agents': Sync Agentforce agents
            - 'flows': Sync flows
            - 'apps': Sync Lightning apps
            - 'packages': Sync installed packages
        progress_callback: Callback function(msg: str, pct: float)
        selected_objects: Optional list of specific object names (only used if 'objects' in metadata_types)
    
    Returns:
        dict: Counts of synced metadata
    """
    init_metadata_db()
    start = datetime.now()

    def log(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    summary = {
        "total_objects": 0,
        "total_fields": 0,
        "total_agents": 0,
        "total_flows": 0,
        "total_apps": 0,
        "total_packages": 0,
    }

    log("Starting selective metadata sync...", 1)

    # Calculate progress increments
    num_types = len(metadata_types)
    pct_per_type = 90 / max(num_types, 1)
    current_pct = 5

    # Sync each selected type
    if 'objects' in metadata_types:
        log("Syncing objects and fields...", current_pct)
        objects, err = discover_all_objects(sf, org_domain, log, selected_objects)
        if not err:
            summary["total_objects"] = len(objects)
            
            # Sync fields for the objects
            log(f"Syncing fields for {len(objects)} objects...", current_pct + 5)
            total_fields = 0
            for i, obj in enumerate(objects):
                if obj.get("is_queryable"):
                    fields, _ = discover_object_fields(sf, org_domain, obj["object_name"])
                    if fields:
                        total_fields += len(fields)
            
            summary["total_fields"] = total_fields
            log(f"✓ {len(objects)} objects + {total_fields} fields synced", current_pct + pct_per_type)
        current_pct += pct_per_type

    if 'agents' in metadata_types:
        agents, _ = discover_agents(sf, org_domain, log)
        summary["total_agents"] = len(agents)
        current_pct += pct_per_type

    if 'flows' in metadata_types:
        flows, _ = discover_flows(sf, org_domain, log)
        summary["total_flows"] = len(flows)
        current_pct += pct_per_type

    if 'apps' in metadata_types:
        apps, _ = discover_custom_apps(sf, org_domain, log)
        summary["total_apps"] = len(apps)
        current_pct += pct_per_type

    if 'packages' in metadata_types:
        packages, _ = discover_installed_packages(sf, org_domain, log)
        summary["total_packages"] = len(packages)
        current_pct += pct_per_type

    # Save sync status
    duration = str(datetime.now() - start).split(".")[0]
    
    log("Saving sync status...", 95)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO sf_sync_status
        (org_domain, last_sync, total_objects, total_fields,
         total_agents, total_packages, total_apps, total_flows,
         sync_duration, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'complete')
        ON CONFLICT(org_domain) DO UPDATE SET
        last_sync      = excluded.last_sync,
        total_objects  = COALESCE(excluded.total_objects, sf_sync_status.total_objects),
        total_fields   = COALESCE(excluded.total_fields, sf_sync_status.total_fields),
        total_agents   = COALESCE(excluded.total_agents, sf_sync_status.total_agents),
        total_packages = COALESCE(excluded.total_packages, sf_sync_status.total_packages),
        total_apps     = COALESCE(excluded.total_apps, sf_sync_status.total_apps),
        total_flows    = COALESCE(excluded.total_flows, sf_sync_status.total_flows),
        sync_duration  = excluded.sync_duration,
        status         = 'complete'
    """, (
        org_domain,
        datetime.now().isoformat(),
        summary["total_objects"] or 0,
        summary["total_fields"] or 0,
        summary["total_agents"] or 0,
        summary["total_packages"] or 0,
        summary["total_apps"] or 0,
        summary["total_flows"] or 0,
        duration
    ))
    conn.commit()
    conn.close()

    parts = []
    if summary["total_objects"]: parts.append(f"{summary['total_objects']} objects")
    if summary["total_fields"]: parts.append(f"{summary['total_fields']} fields")
    if summary["total_agents"]: parts.append(f"{summary['total_agents']} agents")
    if summary["total_flows"]: parts.append(f"{summary['total_flows']} flows")
    if summary["total_apps"]: parts.append(f"{summary['total_apps']} apps")
    if summary["total_packages"]: parts.append(f"{summary['total_packages']} packages")
    
    summary_msg = f"✅ Selective sync complete — {', '.join(parts)}" if parts else "✅ Sync complete"
    log(summary_msg, 100)
    return summary


# ─────────────────────────────────────────────────────────────
# METADATA QUERY FUNCTIONS — Used by Test Runner
# ─────────────────────────────────────────────────────────────

# Fields that should NEVER be sent when creating a record
SYSTEM_EXCLUDED_FIELDS = {
    'Id', 'OwnerId', 'CreatedDate', 'CreatedById',
    'LastModifiedDate', 'LastModifiedById',
    'SystemModstamp', 'IsDeleted', 'LastActivityDate',
    'LastViewedDate', 'LastReferencedDate',
    'MasterRecordId', 'IsEmailBounced',
    'EmailBouncedDate', 'EmailBouncedReason',
    'Jigsaw', 'JigsawContactId', 'IndividualId',
    'CleanStatus', 'ConnectionReceivedId',
    'ConnectionSentId', 'PhotoUrl',
    'HasOptedOutOfEmail', 'HasOptedOutOfFax',
    'DoNotCall', 'EmailBouncedDate',
}


def get_object_fields(org_domain: str, object_name: str) -> list:
    """Get all cached fields for an object"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT field_name, field_label, field_type, is_required,
               is_createable, is_custom, picklist_values,
               reference_to, max_length
        FROM sf_fields
        WHERE org_domain = ? AND object_name = ?
        ORDER BY is_required DESC, is_custom ASC, field_name
    """, (org_domain, object_name))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "field_name", "field_label", "field_type", "is_required",
        "is_createable", "is_custom", "picklist_values",
        "reference_to", "max_length"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_createable_fields(org_domain: str, object_name: str) -> list:
    """
    Get only fields that can be set when creating a record.
    Excludes all system, audit and read-only fields.
    """
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    excluded = ",".join(f"'{f}'" for f in SYSTEM_EXCLUDED_FIELDS)

    cur.execute(f"""
        SELECT field_name, field_label, field_type, is_required,
               is_custom, picklist_values, reference_to, max_length
        FROM sf_fields
        WHERE org_domain  = ?
          AND object_name = ?
          AND is_createable = 1
          AND field_name NOT IN ({excluded})
        ORDER BY is_required DESC, is_custom ASC, field_name
    """, (org_domain, object_name))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "field_name", "field_label", "field_type", "is_required",
        "is_custom", "picklist_values", "reference_to", "max_length"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_required_fields(org_domain: str, object_name: str) -> list:
    """Get only required fields for an object"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    excluded = ",".join(f"'{f}'" for f in SYSTEM_EXCLUDED_FIELDS)
    cur.execute(f"""
        SELECT field_name, field_type, picklist_values
        FROM sf_fields
        WHERE org_domain  = ?
          AND object_name = ?
          AND is_required   = 1
          AND is_createable = 1
          AND field_name NOT IN ({excluded})
    """, (org_domain, object_name))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "field_name":      r[0],
            "field_type":      r[1],
            "picklist_values": r[2]
        }
        for r in rows
    ]


def get_all_objects(org_domain: str,
                    include_custom: bool = True) -> list:
    """Get all discovered objects for an org"""
    conn  = sqlite3.connect(DB_PATH)
    cur   = conn.cursor()
    query = """
        SELECT object_name, object_label, object_type,
               is_custom, is_createable, is_queryable, record_count
        FROM sf_objects
        WHERE org_domain = ? AND is_queryable = 1
    """
    params = [org_domain]
    if not include_custom:
        query += " AND is_custom = 0"
    query += " ORDER BY is_custom ASC, object_name"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    cols = [
        "object_name", "object_label", "object_type",
        "is_custom", "is_createable", "is_queryable", "record_count"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_all_agents(org_domain: str) -> list:
    """Get all discovered Agentforce agents"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT agent_name, agent_label, agent_type,
               channel, status, description
        FROM sf_agents WHERE org_domain = ?
    """, (org_domain,))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "agent_name", "agent_label", "agent_type",
        "channel", "status", "description"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_all_flows(org_domain: str) -> list:
    """Get all discovered flows"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT flow_name, flow_label, flow_type, status, object_name
        FROM sf_flows WHERE org_domain = ?
        ORDER BY flow_type, flow_name
    """, (org_domain,))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "flow_name", "flow_label", "flow_type",
        "status", "object_name"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_all_apps(org_domain: str) -> list:
    """Get all discovered apps"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT app_name, app_label, app_type, is_default
        FROM sf_apps WHERE org_domain = ?
        ORDER BY app_label
    """, (org_domain,))
    rows = cur.fetchall()
    conn.close()
    cols = ["app_name", "app_label", "app_type", "is_default"]
    return [dict(zip(cols, r)) for r in rows]


def get_all_packages(org_domain: str) -> list:
    """Get all discovered installed packages"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT package_name, namespace, version, package_type
        FROM sf_packages WHERE org_domain = ?
        ORDER BY package_name
    """, (org_domain,))
    rows = cur.fetchall()
    conn.close()
    cols = ["package_name", "namespace", "version", "package_type"]
    return [dict(zip(cols, r)) for r in rows]


def get_sync_status(org_domain: str) -> dict:
    """Get last sync status for an org"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT last_sync, total_objects, total_fields,
               total_agents, total_packages, total_apps,
               total_flows, sync_duration, status
        FROM sf_sync_status WHERE org_domain = ?
    """, (org_domain,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"status": "never"}
    cols = [
        "last_sync", "total_objects", "total_fields",
        "total_agents", "total_packages", "total_apps",
        "total_flows", "sync_duration", "status"
    ]
    return dict(zip(cols, row))


def get_picklist_values(org_domain: str,
                        object_name: str,
                        field_name: str) -> list:
    """Get picklist values for a specific field"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT picklist_values FROM sf_fields
        WHERE org_domain  = ?
          AND object_name = ?
          AND field_name  = ?
    """, (org_domain, object_name, field_name))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            pass
    return []


def search_objects(org_domain: str, search_term: str) -> list:
    """Search objects by name or label"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT object_name, object_label, object_type, is_custom
        FROM sf_objects
        WHERE org_domain = ?
          AND (object_name  LIKE ?
           OR  object_label LIKE ?)
          AND is_queryable = 1
        ORDER BY is_custom ASC, object_name
        LIMIT 20
    """, (org_domain, f"%{search_term}%", f"%{search_term}%"))
    rows = cur.fetchall()
    conn.close()
    cols = ["object_name", "object_label", "object_type", "is_custom"]
    return [dict(zip(cols, r)) for r in rows]


def search_fields(org_domain: str, object_name: str,
                  search_term: str) -> list:
    """Search fields within an object by name or label"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT field_name, field_label, field_type,
               is_required, is_custom
        FROM sf_fields
        WHERE org_domain  = ?
          AND object_name = ?
          AND (field_name  LIKE ?
           OR  field_label LIKE ?)
        ORDER BY is_required DESC, field_name
        LIMIT 30
    """, (org_domain, object_name,
          f"%{search_term}%", f"%{search_term}%"))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "field_name", "field_label", "field_type",
        "is_required", "is_custom"
    ]
    return [dict(zip(cols, r)) for r in rows]


# ─────────────────────────────────────────────────────────────
# ADDITIONAL HELPER FUNCTIONS FOR OTHER METADATA
# ─────────────────────────────────────────────────────────────

def get_org_flows(org_domain: str) -> list:
    """Alias for get_all_flows for compatibility"""
    return get_all_flows(org_domain)


def get_org_apps(org_domain: str) -> list:
    """Alias for get_all_apps for compatibility"""
    return get_all_apps(org_domain)


def get_org_packages(org_domain: str) -> list:
    """Alias for get_all_packages for compatibility"""
    return get_all_packages(org_domain)


def get_org_triggers(org_domain: str) -> list:
    """Get triggers (not implemented yet)"""
    return []


def get_org_components(org_domain: str) -> list:
    """Get Lightning components (not implemented yet)"""
    return []


def get_org_validation_rules(org_domain: str) -> list:
    """Get validation rules from database"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT object_name, rule_name, is_active, description, error_msg
        FROM sf_validation_rules WHERE org_domain = ?
        ORDER BY object_name, rule_name
    """, (org_domain,))
    rows = cur.fetchall()
    conn.close()
    cols = ["object_name", "name", "is_active", "description", "error_message"]
    return [dict(zip(cols, r)) for r in rows]


def search_all_metadata(org_domain: str, search_term: str) -> dict:
    """
    Search across all metadata types.
    
    Returns:
        Dictionary with search results for each metadata type
    """
    if not search_term:
        return {}
    
    search_pattern = f"%{search_term}%"
    results = {}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        
        # Search objects
        cur.execute("""
            SELECT object_name, object_label, is_custom
            FROM sf_objects 
            WHERE org_domain=? AND (object_name LIKE ? OR object_label LIKE ?)
            LIMIT 20
        """, (org_domain, search_pattern, search_pattern))
        results['objects'] = [
            {"object_name": r[0], "object_label": r[1], "is_custom": r[2]}
            for r in cur.fetchall()
        ]
        
        # Search fields
        cur.execute("""
            SELECT object_name, field_name, field_label, field_type
            FROM sf_fields 
            WHERE org_domain=? AND (field_name LIKE ? OR field_label LIKE ?)
            LIMIT 20
        """, (org_domain, search_pattern, search_pattern))
        results['fields'] = [
            {"object_name": r[0], "field_name": r[1], "field_label": r[2], "field_type": r[3]}
            for r in cur.fetchall()
        ]
        
        # Search agents
        cur.execute("""
            SELECT agent_name, agent_type, description
            FROM sf_agents 
            WHERE org_domain=? AND (agent_name LIKE ? OR description LIKE ?)
            LIMIT 10
        """, (org_domain, search_pattern, search_pattern))
        results['agents'] = [
            {"agent_name": r[0], "agent_type": r[1], "description": r[2]}
            for r in cur.fetchall()
        ]
        
        # Search flows
        cur.execute("""
            SELECT flow_label, flow_name, flow_type, status
            FROM sf_flows 
            WHERE org_domain=? AND (flow_label LIKE ? OR flow_name LIKE ?)
            LIMIT 10
        """, (org_domain, search_pattern, search_pattern))
        results['flows'] = [
            {"label": r[0], "flow_name": r[1], "process_type": r[2], "status": r[3]}
            for r in cur.fetchall()
        ]
        
        # Search apps
        cur.execute("""
            SELECT app_label, app_name, app_type
            FROM sf_apps 
            WHERE org_domain=? AND (app_label LIKE ? OR app_name LIKE ?)
            LIMIT 10
        """, (org_domain, search_pattern, search_pattern))
        results['apps'] = [
            {"label": r[0], "name": r[1], "app_type": r[2]}
            for r in cur.fetchall()
        ]
        
        # Search packages
        cur.execute("""
            SELECT package_name, namespace, version
            FROM sf_packages 
            WHERE org_domain=? AND (package_name LIKE ? OR namespace LIKE ?)
            LIMIT 10
        """, (org_domain, search_pattern, search_pattern))
        results['packages'] = [
            {"name": r[0], "namespace_prefix": r[1], "version_number": r[2]}
            for r in cur.fetchall()
        ]
        
        conn.close()
        return results
    except Exception:
        return {}