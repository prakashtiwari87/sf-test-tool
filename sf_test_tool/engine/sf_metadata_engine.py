"""
sf_metadata_engine.py — Enhanced Salesforce Metadata Sync Engine

FEATURES:
  • Selective metadata sync (choose which metadata types to download)
  • Fixed function naming (aliases for backward compatibility)
  • Complete search functionality across all metadata
  • Proper progress callback handling
  • Support for all metadata types: Objects, Fields, Agents, Flows, Triggers,
    Lightning Components, Lightning Apps, Installed Packages, Validation Rules

FIXES IN THIS VERSION:
  • Added get_all_objects, get_object_fields, get_all_agents aliases
  • Added search_objects function for metadata search
  • Added selective_sync_metadata for choosing metadata types
  • Fixed database column mappings
  • Fixed progress callback signatures
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Callable, Dict, List
from contextlib import contextmanager

# ─────────────────────────────────────────────────────────────
# DATABASE MANAGEMENT
# ─────────────────────────────────────────────────────────────

@contextmanager
def _get_db():
    """Context manager for database connections."""
    from config.settings_manager import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_metadata_db():
    """Initialize all metadata tables with proper schema."""
    with _get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sf_objects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain  TEXT NOT NULL,
            api_name    TEXT NOT NULL,
            label       TEXT,
            is_custom   INTEGER DEFAULT 0,
            is_queryable INTEGER DEFAULT 1,
            is_createable INTEGER DEFAULT 1,
            key_prefix  TEXT,
            synced_at   TEXT,
            UNIQUE(org_domain, api_name)
        );

        CREATE TABLE IF NOT EXISTS sf_fields (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain  TEXT NOT NULL,
            object_name TEXT NOT NULL,
            api_name    TEXT NOT NULL,
            label       TEXT,
            field_type  TEXT,
            is_custom   INTEGER DEFAULT 0,
            is_required INTEGER DEFAULT 0,
            max_length  INTEGER,
            picklist_values TEXT,
            UNIQUE(org_domain, object_name, api_name)
        );

        CREATE TABLE IF NOT EXISTS sf_agents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain   TEXT NOT NULL,
            agent_id     TEXT,
            agent_name   TEXT,
            agent_type   TEXT,
            description  TEXT,
            is_active    INTEGER DEFAULT 0,
            bot_user_id  TEXT,
            created_by   TEXT,
            last_modified TEXT,
            raw_json     TEXT,
            synced_at    TEXT,
            UNIQUE(org_domain, agent_id)
        );

        CREATE TABLE IF NOT EXISTS sf_flows (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain    TEXT NOT NULL,
            flow_id       TEXT,
            api_name      TEXT,
            label         TEXT,
            process_type  TEXT,
            status        TEXT,
            description   TEXT,
            is_active     INTEGER DEFAULT 0,
            last_modified TEXT,
            raw_json      TEXT,
            synced_at     TEXT,
            UNIQUE(org_domain, flow_id)
        );

        CREATE TABLE IF NOT EXISTS sf_apex_triggers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            trigger_id      TEXT,
            name            TEXT,
            table_enum_or_id TEXT,
            is_active       INTEGER DEFAULT 1,
            status          TEXT,
            body_preview    TEXT,
            last_modified   TEXT,
            raw_json        TEXT,
            synced_at       TEXT,
            UNIQUE(org_domain, trigger_id)
        );

        CREATE TABLE IF NOT EXISTS sf_lightning_components (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            component_id    TEXT,
            name            TEXT,
            api_version     REAL,
            description     TEXT,
            is_aura         INTEGER DEFAULT 0,
            master_label    TEXT,
            last_modified   TEXT,
            raw_json        TEXT,
            synced_at       TEXT,
            UNIQUE(org_domain, component_id)
        );

        CREATE TABLE IF NOT EXISTS sf_lightning_apps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            app_id          TEXT,
            name            TEXT,
            label           TEXT,
            description     TEXT,
            is_default      INTEGER DEFAULT 0,
            form_factors    TEXT,
            last_modified   TEXT,
            raw_json        TEXT,
            synced_at       TEXT,
            UNIQUE(org_domain, app_id)
        );

        CREATE TABLE IF NOT EXISTS sf_installed_packages (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain       TEXT NOT NULL,
            package_id       TEXT,
            name             TEXT,
            namespace_prefix TEXT,
            version_number   TEXT,
            version_name     TEXT,
            publisher        TEXT,
            install_date     TEXT,
            raw_json         TEXT,
            synced_at        TEXT,
            UNIQUE(org_domain, package_id)
        );

        CREATE TABLE IF NOT EXISTS sf_validation_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            rule_id         TEXT,
            name            TEXT,
            object_name     TEXT,
            is_active       INTEGER DEFAULT 1,
            description     TEXT,
            error_message   TEXT,
            raw_json        TEXT,
            synced_at       TEXT,
            UNIQUE(org_domain, rule_id)
        );

        CREATE TABLE IF NOT EXISTS sf_sync_status (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL UNIQUE,
            last_sync       TEXT,
            total_objects   INTEGER DEFAULT 0,
            total_fields    INTEGER DEFAULT 0,
            total_agents    INTEGER DEFAULT 0,
            total_flows     INTEGER DEFAULT 0,
            total_triggers  INTEGER DEFAULT 0,
            total_components INTEGER DEFAULT 0,
            total_apps      INTEGER DEFAULT 0,
            total_packages  INTEGER DEFAULT 0,
            total_vr        INTEGER DEFAULT 0,
            sync_duration   TEXT,
            sync_errors     TEXT,
            status          TEXT DEFAULT 'pending'
        );
        """)


# ─────────────────────────────────────────────────────────────
# SYNC STATUS
# ─────────────────────────────────────────────────────────────

def get_sync_status(org_domain: str) -> dict:
    """Get the current sync status for an org."""
    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM sf_sync_status WHERE org_domain=?", (org_domain,)
            ).fetchone()
            if row:
                status_dict = dict(row)
                # Add computed 'status' field if last_sync exists
                if status_dict.get('last_sync'):
                    status_dict['status'] = 'complete'
                return status_dict
            return {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def _upsert_many(conn: sqlite3.Connection, table: str,
                 conflict_cols: tuple, rows: list):
    """Generic upsert for a list of dicts into a table."""
    if not rows:
        return
    keys    = list(rows[0].keys())
    placeholders = ",".join("?" * len(keys))
    col_list     = ",".join(keys)
    upd_cols     = [k for k in keys if k not in conflict_cols]
    upd_clause   = ",".join(f"{k}=excluded.{k}" for k in upd_cols)
    conflict_str = ",".join(conflict_cols)
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_str}) DO UPDATE SET {upd_clause}"
    )
    conn.executemany(sql, [tuple(r[k] for k in keys) for r in rows])


# ─────────────────────────────────────────────────────────────
# INDIVIDUAL SYNC FUNCTIONS
# ─────────────────────────────────────────────────────────────

def sync_objects_and_fields(sf, org_domain: str,
                             progress_callback: Optional[Callable] = None,
                             selected_objects: Optional[List[str]] = None) -> int:
    """
    Sync Salesforce objects and their fields.
    
    Args:
        sf: Salesforce connection object
        org_domain: Organization domain
        progress_callback: Callback function(msg: str, pct: float)
        selected_objects: Optional list of object API names to sync. If None, syncs all.
    
    Returns:
        Number of objects synced
    """
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Fetching list of all Salesforce objects…", 5)
    try:
        describe = sf.describe()
        sobjects = describe.get("sobjects", [])
    except Exception as e:
        cb(f"ERROR fetching objects: {e}", 5)
        return 0

    # Filter to selected objects if specified
    if selected_objects:
        sobjects = [o for o in sobjects if o.get("name") in selected_objects]
        cb(f"Filtering to {len(sobjects)} selected objects…", 7)
    
    cb(f"Found {len(sobjects)} objects. Storing…", 8)
    obj_rows = []
    for o in sobjects:
        obj_rows.append({
            "org_domain":   org_domain,
            "api_name":     o.get("name", ""),
            "label":        o.get("label", ""),
            "is_custom":    1 if o.get("custom", False) else 0,
            "is_queryable": 1 if o.get("queryable", True) else 0,
            "is_createable": 1 if o.get("createable", True) else 0,
            "key_prefix":   o.get("keyPrefix", ""),
            "synced_at":    now,
        })

    with _get_db() as conn:
        _upsert_many(conn, "sf_objects", ("org_domain", "api_name"), obj_rows)

    # Sync fields for queryable objects
    queryable = [o for o in sobjects if o.get("queryable", True)]
    total     = len(queryable)
    all_fields = []

    cb(f"Describing fields for {total} queryable objects…", 10)
    for i, o in enumerate(queryable):
        pct = 10 + int((i / max(total, 1)) * 30)   # 10–40%
        if i % 25 == 0 or len(queryable) < 50:
            cb(f"Describing {o['name']} ({i+1}/{total})…", pct)
        try:
            desc = sf.__getattr__(o["name"]).describe()
            for f in desc.get("fields", []):
                field_data = {
                    "org_domain":  org_domain,
                    "object_name": o["name"],
                    "api_name":    f.get("name", ""),
                    "label":       f.get("label", ""),
                    "field_type":  f.get("type", ""),
                    "is_custom":   1 if f.get("custom", False) else 0,
                    "is_required": 1 if (not f.get("nillable", True)
                                         and not f.get("defaultedOnCreate", False)) else 0,
                    "max_length":  f.get("length", 0),
                }
                
                # Store picklist values
                if f.get("type") == "picklist" and f.get("picklistValues"):
                    values = [pv.get("value") for pv in f.get("picklistValues", [])]
                    field_data["picklist_values"] = json.dumps(values)
                
                all_fields.append(field_data)
        except Exception:
            pass

    with _get_db() as conn:
        # Insert in batches to avoid lock issues
        batch = 500
        for start in range(0, len(all_fields), batch):
            _upsert_many(conn, "sf_fields",
                         ("org_domain", "object_name", "api_name"),
                         all_fields[start:start+batch])

    return len(obj_rows)


def sync_agents(sf, org_domain: str,
                progress_callback: Optional[Callable] = None) -> int:
    """Sync Agentforce/Einstein Bot agents via Tooling API."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Agentforce Agents…", 42)
    rows = []
    try:
        # Try BotDefinition first (Agentforce native type)
        try:
            result = sf.toolingexecute(
                "GET",
                "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,Description,"
                "BotType,Status,LastModifiedDate+FROM+BotDefinition+LIMIT+200"
            )
            records = result.get("records", [])
        except Exception:
            records = []

        # Fall back to BotVersion if nothing returned
        if not records:
            try:
                result = sf.toolingexecute(
                    "GET",
                    "tooling/query/?q=SELECT+Id,MasterLabel,Description,BotType,"
                    "Status,LastModifiedDate+FROM+BotVersion+WHERE+IsLatestVersion=true+LIMIT+200"
                )
                records = result.get("records", [])
            except Exception:
                records = []

        for r in records:
            rows.append({
                "org_domain":    org_domain,
                "agent_id":      r.get("Id", ""),
                "agent_name":    r.get("MasterLabel") or r.get("DeveloperName", ""),
                "agent_type":    r.get("BotType", ""),
                "description":   r.get("Description", "") or "",
                "is_active":     1 if r.get("Status", "") in ("Active", "Published") else 0,
                "bot_user_id":   "",
                "created_by":    "",
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })

    except Exception as e:
        cb(f"Warning — could not sync agents: {e}", 42)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_agents", ("org_domain", "agent_id"), rows)

    cb(f"✓ {len(rows)} agent(s) synced", 44)
    return len(rows)


def sync_flows(sf, org_domain: str,
               progress_callback: Optional[Callable] = None) -> int:
    """Sync all Flow Definitions."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Flows…", 46)
    rows = []
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,ProcessType,"
            "ActiveVersionId,Description,LastModifiedDate+FROM+FlowDefinition+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":    org_domain,
                "flow_id":       r.get("Id", ""),
                "api_name":      r.get("DeveloperName", ""),
                "label":         r.get("MasterLabel", ""),
                "process_type":  r.get("ProcessType", ""),
                "status":        "Active" if r.get("ActiveVersionId") else "Draft",
                "description":   r.get("Description", "") or "",
                "is_active":     1 if r.get("ActiveVersionId") else 0,
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })
    except Exception as e:
        cb(f"Warning — could not sync flows: {e}", 46)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_flows", ("org_domain", "flow_id"), rows)

    cb(f"✓ {len(rows)} flow(s) synced", 52)
    return len(rows)


def sync_apex_triggers(sf, org_domain: str,
                        progress_callback: Optional[Callable] = None) -> int:
    """Sync Apex Triggers."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Apex Triggers…", 54)
    rows = []
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,Name,TableEnumOrId,Status,LastModifiedDate+FROM+ApexTrigger+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":      org_domain,
                "trigger_id":      r.get("Id", ""),
                "name":            r.get("Name", ""),
                "table_enum_or_id": r.get("TableEnumOrId", ""),
                "is_active":       1 if r.get("Status") == "Active" else 0,
                "status":          r.get("Status", ""),
                "body_preview":    "",
                "last_modified":   r.get("LastModifiedDate", ""),
                "raw_json":        json.dumps(r),
                "synced_at":       now,
            })
    except Exception as e:
        cb(f"Warning — could not sync triggers: {e}", 54)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_apex_triggers", ("org_domain", "trigger_id"), rows)

    cb(f"✓ {len(rows)} trigger(s) synced", 60)
    return len(rows)


def sync_lightning_components(sf, org_domain: str,
                               progress_callback: Optional[Callable] = None) -> int:
    """Sync Lightning Web Components and Aura Components."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Lightning Components…", 62)
    rows = []
    
    # Try LWC first
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,Description,"
            "ApiVersion,LastModifiedDate+FROM+LightningComponentBundle+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":    org_domain,
                "component_id":  r.get("Id", ""),
                "name":          r.get("DeveloperName", ""),
                "api_version":   r.get("ApiVersion", 0.0),
                "description":   r.get("Description", "") or "",
                "is_aura":       0,
                "master_label":  r.get("MasterLabel", ""),
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })
    except Exception as e:
        cb(f"Warning — could not sync LWC: {e}", 64)

    # Try Aura
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,Description,"
            "ApiVersion,LastModifiedDate+FROM+AuraDefinitionBundle+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":    org_domain,
                "component_id":  r.get("Id", ""),
                "name":          r.get("DeveloperName", ""),
                "api_version":   r.get("ApiVersion", 0.0),
                "description":   r.get("Description", "") or "",
                "is_aura":       1,
                "master_label":  r.get("MasterLabel", ""),
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })
    except Exception as e:
        cb(f"Warning — could not sync Aura: {e}", 66)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_lightning_components", ("org_domain", "component_id"), rows)

    cb(f"✓ {len(rows)} component(s) synced", 68)
    return len(rows)


def sync_lightning_apps(sf, org_domain: str,
                        progress_callback: Optional[Callable] = None) -> int:
    """Sync Lightning Apps."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Lightning Apps…", 70)
    rows = []
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,Description,"
            "FormFactors,LastModifiedDate+FROM+AppDefinition+LIMIT+200"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":    org_domain,
                "app_id":        r.get("Id", ""),
                "name":          r.get("DeveloperName", ""),
                "label":         r.get("MasterLabel", ""),
                "description":   r.get("Description", "") or "",
                "is_default":    0,
                "form_factors":  r.get("FormFactors", ""),
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })
    except Exception as e:
        cb(f"Warning — could not sync apps: {e}", 70)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_lightning_apps", ("org_domain", "app_id"), rows)

    cb(f"✓ {len(rows)} app(s) synced", 74)
    return len(rows)


def sync_installed_packages(sf, org_domain: str,
                             progress_callback: Optional[Callable] = None) -> int:
    """Sync installed managed packages."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Installed Packages…", 76)
    rows = []
    
    # Try InstalledSubscriberPackage first
    try:
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,SubscriberPackageId,SubscriberPackage.Name,"
            "SubscriberPackage.NamespacePrefix,SubscriberPackageVersion.Name,"
            "SubscriberPackageVersion.MajorVersion,SubscriberPackageVersion.MinorVersion,"
            "SubscriberPackageVersion.PatchVersion,SubscriberPackageVersion.BuildNumber+"
            "FROM+InstalledSubscriberPackage+LIMIT+200"
        )
        for r in result.get("records", []):
            pkg = r.get("SubscriberPackage", {}) or {}
            ver = r.get("SubscriberPackageVersion", {}) or {}
            version = f"{ver.get('MajorVersion',0)}.{ver.get('MinorVersion',0)}.{ver.get('PatchVersion',0)}"
            rows.append({
                "org_domain":       org_domain,
                "package_id":       r.get("SubscriberPackageId", ""),
                "name":             pkg.get("Name", ""),
                "namespace_prefix": pkg.get("NamespacePrefix", "") or "",
                "version_number":   version,
                "version_name":     ver.get("Name", ""),
                "publisher":        "",
                "install_date":     "",
                "raw_json":         json.dumps(r),
                "synced_at":        now,
            })
    except Exception as e1:
        cb(f"Trying alternate package query…", 78)
        # Fallback to PackageSubscriber
        try:
            result = sf.query_all(
                "SELECT Id,SubscriberPackageName,SubscriberPackageNamespace,"
                "SubscriberPackageVersionNumber,SubscriberPackageVersionName "
                "FROM PackageSubscriber LIMIT 200"
            )
            for r in result.get("records", []):
                rows.append({
                    "org_domain":       org_domain,
                    "package_id":       r.get("Id", ""),
                    "name":             r.get("SubscriberPackageName", ""),
                    "namespace_prefix": r.get("SubscriberPackageNamespace", "") or "",
                    "version_number":   r.get("SubscriberPackageVersionNumber", ""),
                    "version_name":     r.get("SubscriberPackageVersionName", "") or "",
                    "publisher":        "",
                    "install_date":     "",
                    "raw_json":         json.dumps(r),
                    "synced_at":        now,
                })
        except Exception as e2:
            cb(f"Warning — could not sync packages: {e2}", 78)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_installed_packages",
                         ("org_domain", "package_id"), rows)

    cb(f"✓ {len(rows)} package(s) synced", 82)
    return len(rows)


def sync_validation_rules(sf, org_domain: str,
                           progress_callback: Optional[Callable] = None) -> int:
    """Sync validation rules via Tooling API."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Validation Rules…", 84)
    rows = []
    try:
        result  = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,ValidationName,EntityDefinition.QualifiedApiName,"
            "Active,Description,ErrorMessage,LastModifiedDate+FROM+ValidationRule+LIMIT+1000"
        )
        for r in result.get("records", []):
            entity = r.get("EntityDefinition") or {}
            rows.append({
                "org_domain":   org_domain,
                "rule_id":      r.get("Id", ""),
                "name":         r.get("ValidationName", ""),
                "object_name":  entity.get("QualifiedApiName", ""),
                "is_active":    1 if r.get("Active", False) else 0,
                "description":  (r.get("Description") or ""),
                "error_message": (r.get("ErrorMessage") or ""),
                "raw_json":     json.dumps(r),
                "synced_at":    now,
            })
    except Exception as e:
        cb(f"Warning — could not sync validation rules: {e}", 84)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_validation_rules",
                         ("org_domain", "rule_id"), rows)

    cb(f"✓ {len(rows)} validation rule(s) synced", 90)
    return len(rows)


# ─────────────────────────────────────────────────────────────
# MAIN SYNC FUNCTIONS
# ─────────────────────────────────────────────────────────────

def sync_full_org_metadata(sf, org_domain: str,
                           progress_callback: Optional[Callable] = None,
                           **kwargs):
    """
    Run a complete metadata sync for the given Salesforce org.

    progress_callback signature: callback(msg: str, pct: float)
    Both arguments are always provided.

    Syncs (in order):
      1. Objects & Fields
      2. Agentforce Agents
      3. Flows
      4. Apex Triggers
      5. Lightning Components (LWC + Aura)
      6. Lightning Apps
      7. Installed Packages
      8. Validation Rules
      
    Returns:
        dict: Counts of all synced metadata types
    """
    start_time = datetime.utcnow()

    def log(msg: str, pct: float = 0.0):
        """Safe wrapper — always calls callback with both args."""
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except Exception:
                pass

    init_metadata_db()
    errors = []
    counts = {
        "total_objects":    0,
        "total_fields":     0,
        "total_agents":     0,
        "total_flows":      0,
        "total_triggers":   0,
        "total_components": 0,
        "total_apps":       0,
        "total_packages":   0,
        "total_vr":         0,
    }

    log("Starting full org metadata sync…", 1)

    # ── Step 1: Objects & Fields (10–40%) ─────────────────────
    try:
        log("Scanning all Salesforce objects…", 5)
        n_obj = sync_objects_and_fields(sf, org_domain, progress_callback)
        counts["total_objects"] = n_obj

        with _get_db() as conn:
            counts["total_fields"] = conn.execute(
                "SELECT COUNT(*) FROM sf_fields WHERE org_domain=?",
                (org_domain,)
            ).fetchone()[0]

        log(f"✓ {n_obj} objects + {counts['total_fields']} fields synced", 40)
    except Exception as e:
        errors.append(f"Objects/Fields: {e}")
        log(f"ERROR syncing objects: {e}", 40)

    # ── Step 2: Agents (42–44%) ────────────────────────────────
    try:
        counts["total_agents"] = sync_agents(sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"Agents: {e}")
        log(f"ERROR syncing agents: {e}", 44)

    # ── Step 3: Flows (46–52%) ─────────────────────────────────
    try:
        counts["total_flows"] = sync_flows(sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"Flows: {e}")
        log(f"ERROR syncing flows: {e}", 52)

    # ── Step 4: Triggers (54–60%) ──────────────────────────────
    try:
        counts["total_triggers"] = sync_apex_triggers(sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"Triggers: {e}")
        log(f"ERROR syncing triggers: {e}", 60)

    # ── Step 5: Lightning Components (62–68%) ─────────────────
    try:
        counts["total_components"] = sync_lightning_components(
            sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"LightningComponents: {e}")
        log(f"ERROR syncing components: {e}", 68)

    # ── Step 6: Lightning Apps (70–74%) ───────────────────────
    try:
        counts["total_apps"] = sync_lightning_apps(sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"LightningApps: {e}")
        log(f"ERROR syncing apps: {e}", 74)

    # ── Step 7: Installed Packages (76–82%) ───────────────────
    try:
        counts["total_packages"] = sync_installed_packages(
            sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"Packages: {e}")
        log(f"ERROR syncing packages: {e}", 82)

    # ── Step 8: Validation Rules (84–90%) ─────────────────────
    try:
        counts["total_vr"] = sync_validation_rules(sf, org_domain, progress_callback)
    except Exception as e:
        errors.append(f"ValidationRules: {e}")
        log(f"ERROR syncing validation rules: {e}", 90)

    # ── Save sync status (95%) ─────────────────────────────────
    end_time = datetime.utcnow()
    duration = str(end_time - start_time).split('.')[0]  # Remove microseconds
    
    log("Saving sync status…", 95)
    try:
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO sf_sync_status
                    (org_domain, last_sync, total_objects, total_fields,
                     total_agents, total_flows, total_triggers,
                     total_components, total_apps, total_packages,
                     total_vr, sync_duration, sync_errors, status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(org_domain) DO UPDATE SET
                    last_sync        = excluded.last_sync,
                    total_objects    = excluded.total_objects,
                    total_fields     = excluded.total_fields,
                    total_agents     = excluded.total_agents,
                    total_flows      = excluded.total_flows,
                    total_triggers   = excluded.total_triggers,
                    total_components = excluded.total_components,
                    total_apps       = excluded.total_apps,
                    total_packages   = excluded.total_packages,
                    total_vr         = excluded.total_vr,
                    sync_duration    = excluded.sync_duration,
                    sync_errors      = excluded.sync_errors,
                    status           = excluded.status
            """, (
                org_domain,
                datetime.utcnow().isoformat(),
                counts["total_objects"],
                counts["total_fields"],
                counts["total_agents"],
                counts["total_flows"],
                counts["total_triggers"],
                counts["total_components"],
                counts["total_apps"],
                counts["total_packages"],
                counts["total_vr"],
                duration,
                "; ".join(errors) if errors else "",
                "complete"
            ))
    except Exception as e:
        log(f"ERROR saving sync status: {e}", 95)

    summary = (
        f"✅ Sync complete — "
        f"{counts['total_objects']} objects, "
        f"{counts['total_fields']} fields, "
        f"{counts['total_agents']} agents, "
        f"{counts['total_flows']} flows, "
        f"{counts['total_triggers']} triggers, "
        f"{counts['total_components']} components, "
        f"{counts['total_apps']} apps, "
        f"{counts['total_packages']} packages, "
        f"{counts['total_vr']} validation rules"
    )
    log(summary, 100)
    return counts


def selective_sync_metadata(sf, org_domain: str,
                            metadata_types: List[str],
                            progress_callback: Optional[Callable] = None,
                            selected_objects: Optional[List[str]] = None):
    """
    Selectively sync specific metadata types.
    
    Args:
        sf: Salesforce connection
        org_domain: Organization domain
        metadata_types: List of metadata types to sync. Options:
            - 'objects': Sync objects and fields
            - 'agents': Sync Agentforce agents
            - 'flows': Sync flows
            - 'triggers': Sync Apex triggers
            - 'components': Sync Lightning components
            - 'apps': Sync Lightning apps
            - 'packages': Sync installed packages
            - 'validation_rules': Sync validation rules
        progress_callback: Callback function(msg: str, pct: float)
        selected_objects: Optional list of specific object API names (only used if 'objects' in metadata_types)
    
    Returns:
        dict: Counts of synced metadata
    """
    start_time = datetime.utcnow()
    
    def log(msg: str, pct: float = 0.0):
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except Exception:
                pass

    init_metadata_db()
    errors = []
    counts = {
        "total_objects": 0,
        "total_fields": 0,
        "total_agents": 0,
        "total_flows": 0,
        "total_triggers": 0,
        "total_components": 0,
        "total_apps": 0,
        "total_packages": 0,
        "total_vr": 0,
    }
    
    log("Starting selective metadata sync…", 1)
    
    # Calculate progress increments based on selected types
    num_types = len(metadata_types)
    pct_per_type = 90 / max(num_types, 1)
    current_pct = 5
    
    # Sync each selected type
    if 'objects' in metadata_types:
        try:
            log("Syncing objects and fields…", current_pct)
            n_obj = sync_objects_and_fields(sf, org_domain, progress_callback, selected_objects)
            counts["total_objects"] = n_obj
            
            with _get_db() as conn:
                counts["total_fields"] = conn.execute(
                    "SELECT COUNT(*) FROM sf_fields WHERE org_domain=?",
                    (org_domain,)
                ).fetchone()[0]
            
            log(f"✓ {n_obj} objects + {counts['total_fields']} fields synced", current_pct + pct_per_type)
        except Exception as e:
            errors.append(f"Objects: {e}")
        current_pct += pct_per_type
    
    if 'agents' in metadata_types:
        try:
            counts["total_agents"] = sync_agents(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Agents: {e}")
        current_pct += pct_per_type
    
    if 'flows' in metadata_types:
        try:
            counts["total_flows"] = sync_flows(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Flows: {e}")
        current_pct += pct_per_type
    
    if 'triggers' in metadata_types:
        try:
            counts["total_triggers"] = sync_apex_triggers(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Triggers: {e}")
        current_pct += pct_per_type
    
    if 'components' in metadata_types:
        try:
            counts["total_components"] = sync_lightning_components(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Components: {e}")
        current_pct += pct_per_type
    
    if 'apps' in metadata_types:
        try:
            counts["total_apps"] = sync_lightning_apps(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Apps: {e}")
        current_pct += pct_per_type
    
    if 'packages' in metadata_types:
        try:
            counts["total_packages"] = sync_installed_packages(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Packages: {e}")
        current_pct += pct_per_type
    
    if 'validation_rules' in metadata_types:
        try:
            counts["total_vr"] = sync_validation_rules(sf, org_domain, progress_callback)
        except Exception as e:
            errors.append(f"Validation Rules: {e}")
        current_pct += pct_per_type
    
    # Save sync status
    end_time = datetime.utcnow()
    duration = str(end_time - start_time).split('.')[0]
    
    log("Saving sync status…", 95)
    try:
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO sf_sync_status
                    (org_domain, last_sync, total_objects, total_fields,
                     total_agents, total_flows, total_triggers,
                     total_components, total_apps, total_packages,
                     total_vr, sync_duration, sync_errors, status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(org_domain) DO UPDATE SET
                    last_sync        = excluded.last_sync,
                    total_objects    = COALESCE(excluded.total_objects, sf_sync_status.total_objects),
                    total_fields     = COALESCE(excluded.total_fields, sf_sync_status.total_fields),
                    total_agents     = COALESCE(excluded.total_agents, sf_sync_status.total_agents),
                    total_flows      = COALESCE(excluded.total_flows, sf_sync_status.total_flows),
                    total_triggers   = COALESCE(excluded.total_triggers, sf_sync_status.total_triggers),
                    total_components = COALESCE(excluded.total_components, sf_sync_status.total_components),
                    total_apps       = COALESCE(excluded.total_apps, sf_sync_status.total_apps),
                    total_packages   = COALESCE(excluded.total_packages, sf_sync_status.total_packages),
                    total_vr         = COALESCE(excluded.total_vr, sf_sync_status.total_vr),
                    sync_duration    = excluded.sync_duration,
                    sync_errors      = excluded.sync_errors,
                    status           = excluded.status
            """, (
                org_domain,
                datetime.utcnow().isoformat(),
                counts["total_objects"] or None,
                counts["total_fields"] or None,
                counts["total_agents"] or None,
                counts["total_flows"] or None,
                counts["total_triggers"] or None,
                counts["total_components"] or None,
                counts["total_apps"] or None,
                counts["total_packages"] or None,
                counts["total_vr"] or None,
                duration,
                "; ".join(errors) if errors else "",
                "complete"
            ))
    except Exception as e:
        log(f"ERROR saving sync status: {e}", 95)
    
    summary_parts = []
    if counts["total_objects"]: summary_parts.append(f"{counts['total_objects']} objects")
    if counts["total_fields"]: summary_parts.append(f"{counts['total_fields']} fields")
    if counts["total_agents"]: summary_parts.append(f"{counts['total_agents']} agents")
    if counts["total_flows"]: summary_parts.append(f"{counts['total_flows']} flows")
    if counts["total_triggers"]: summary_parts.append(f"{counts['total_triggers']} triggers")
    if counts["total_components"]: summary_parts.append(f"{counts['total_components']} components")
    if counts["total_apps"]: summary_parts.append(f"{counts['total_apps']} apps")
    if counts["total_packages"]: summary_parts.append(f"{counts['total_packages']} packages")
    if counts["total_vr"]: summary_parts.append(f"{counts['total_vr']} validation rules")
    
    summary = f"✅ Selective sync complete — {', '.join(summary_parts)}"
    log(summary, 100)
    return counts


# ─────────────────────────────────────────────────────────────
# READ HELPERS (used by Metadata Explorer page)
# ─────────────────────────────────────────────────────────────

def get_org_objects(org_domain: str) -> list:
    """Get all objects for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT api_name as object_name, label as object_label, "
                "is_custom, is_queryable, is_createable "
                "FROM sf_objects WHERE org_domain=? ORDER BY api_name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_fields(org_domain: str, object_name: str = "") -> list:
    """Get fields for an object or all fields."""
    try:
        with _get_db() as conn:
            if object_name:
                rows = conn.execute(
                    "SELECT api_name as field_name, label as field_label, "
                    "field_type, is_custom, is_required, max_length, picklist_values "
                    "FROM sf_fields WHERE org_domain=? AND object_name=? "
                    "ORDER BY api_name",
                    (org_domain, object_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT api_name as field_name, label as field_label, "
                    "field_type, is_custom, is_required, max_length, picklist_values, object_name "
                    "FROM sf_fields WHERE org_domain=? ORDER BY object_name, api_name",
                    (org_domain,)
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_agents(org_domain: str) -> list:
    """Get all agents for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_agents WHERE org_domain=? ORDER BY agent_name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_flows(org_domain: str) -> list:
    """Get all flows for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_flows WHERE org_domain=? ORDER BY label",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_triggers(org_domain: str) -> list:
    """Get all triggers for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_apex_triggers WHERE org_domain=? ORDER BY name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_components(org_domain: str) -> list:
    """Get all Lightning components for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_lightning_components WHERE org_domain=? ORDER BY name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_apps(org_domain: str) -> list:
    """Get all Lightning apps for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_lightning_apps WHERE org_domain=? ORDER BY label",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_packages(org_domain: str) -> list:
    """Get all installed packages for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_installed_packages WHERE org_domain=? ORDER BY name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_validation_rules(org_domain: str) -> list:
    """Get all validation rules for an org."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_validation_rules WHERE org_domain=? ORDER BY object_name, name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────
# ALIASES FOR BACKWARD COMPATIBILITY
# ─────────────────────────────────────────────────────────────

def get_all_objects(org_domain: str) -> list:
    """Alias for get_org_objects for backward compatibility."""
    return get_org_objects(org_domain)


def get_object_fields(org_domain: str, object_name: str = "") -> list:
    """Alias for get_org_fields for backward compatibility."""
    return get_org_fields(org_domain, object_name)


def get_all_agents(org_domain: str) -> list:
    """Alias for get_org_agents for backward compatibility."""
    return get_org_agents(org_domain)


# ─────────────────────────────────────────────────────────────
# SEARCH FUNCTIONALITY
# ─────────────────────────────────────────────────────────────

def search_objects(org_domain: str, search_term: str) -> list:
    """
    Search for objects by name or label.
    
    Args:
        org_domain: Organization domain
        search_term: Search query
    
    Returns:
        List of matching objects with their metadata
    """
    if not search_term:
        return []
    
    search_pattern = f"%{search_term}%"
    
    try:
        with _get_db() as conn:
            rows = conn.execute("""
                SELECT 
                    api_name as object_name,
                    label as object_label,
                    is_custom,
                    CASE WHEN is_custom = 1 THEN 'Custom Object' ELSE 'Standard Object' END as object_type
                FROM sf_objects 
                WHERE org_domain=? 
                AND (
                    api_name LIKE ? COLLATE NOCASE
                    OR label LIKE ? COLLATE NOCASE
                )
                ORDER BY is_custom DESC, api_name
                LIMIT 50
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            
            return [dict(r) for r in rows]
    except Exception:
        return []


def search_all_metadata(org_domain: str, search_term: str) -> Dict[str, list]:
    """
    Search across all metadata types.
    
    Args:
        org_domain: Organization domain
        search_term: Search query
    
    Returns:
        Dictionary with search results for each metadata type
    """
    if not search_term:
        return {}
    
    search_pattern = f"%{search_term}%"
    results = {}
    
    try:
        with _get_db() as conn:
            # Search objects
            objects = conn.execute("""
                SELECT api_name, label, is_custom
                FROM sf_objects 
                WHERE org_domain=? AND (api_name LIKE ? COLLATE NOCASE OR label LIKE ? COLLATE NOCASE)
                LIMIT 20
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['objects'] = [dict(r) for r in objects]
            
            # Search fields
            fields = conn.execute("""
                SELECT object_name, api_name, label, field_type
                FROM sf_fields 
                WHERE org_domain=? AND (api_name LIKE ? COLLATE NOCASE OR label LIKE ? COLLATE NOCASE)
                LIMIT 20
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['fields'] = [dict(r) for r in fields]
            
            # Search agents
            agents = conn.execute("""
                SELECT agent_name, agent_type, description
                FROM sf_agents 
                WHERE org_domain=? AND (agent_name LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE)
                LIMIT 10
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['agents'] = [dict(r) for r in agents]
            
            # Search flows
            flows = conn.execute("""
                SELECT label, api_name, process_type, status
                FROM sf_flows 
                WHERE org_domain=? AND (label LIKE ? COLLATE NOCASE OR api_name LIKE ? COLLATE NOCASE)
                LIMIT 10
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['flows'] = [dict(r) for r in flows]
            
            # Search triggers
            triggers = conn.execute("""
                SELECT name, table_enum_or_id, status
                FROM sf_apex_triggers 
                WHERE org_domain=? AND name LIKE ? COLLATE NOCASE
                LIMIT 10
            """, (org_domain, search_pattern)).fetchall()
            results['triggers'] = [dict(r) for r in triggers]
            
            # Search components
            components = conn.execute("""
                SELECT name, master_label, description
                FROM sf_lightning_components 
                WHERE org_domain=? AND (name LIKE ? COLLATE NOCASE OR master_label LIKE ? COLLATE NOCASE)
                LIMIT 10
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['components'] = [dict(r) for r in components]
            
            # Search apps
            apps = conn.execute("""
                SELECT label, name, description
                FROM sf_lightning_apps 
                WHERE org_domain=? AND (label LIKE ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE)
                LIMIT 10
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['apps'] = [dict(r) for r in apps]
            
            # Search packages
            packages = conn.execute("""
                SELECT name, namespace_prefix, version_number
                FROM sf_installed_packages 
                WHERE org_domain=? AND (name LIKE ? COLLATE NOCASE OR namespace_prefix LIKE ? COLLATE NOCASE)
                LIMIT 10
            """, (org_domain, search_pattern, search_pattern)).fetchall()
            results['packages'] = [dict(r) for r in packages]
            
        return results
    except Exception:
        return {}