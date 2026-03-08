"""
sf_metadata_engine.py — AmplifyQA Salesforce Metadata Engine
Syncs and stores comprehensive org metadata including:
  • Standard & Custom Objects + Fields
  • Agentforce / Einstein Agents (BotDefinition via Tooling API)
  • Flows (FlowDefinition)
  • Apex Triggers
  • Lightning Components (LWC + Aura)
  • Lightning Apps
  • Installed Packages (PackageSubscriber)
  • Validation Rules

PROGRESS CALLBACK CONTRACT
  All progress_callback calls use the signature:
      progress_callback(msg: str, pct: float)
  where pct is 0–100. The callback must accept both arguments.
  In 8_Settings.py define it as: def _on_progress(msg, pct): ...
"""

import sqlite3
import os
import json
import traceback
from datetime import datetime
from typing import Callable, Optional

# ─────────────────────────────────────────────────────────────
# DB PATH
# ─────────────────────────────────────────────────────────────
_DB_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_DB_PATH = os.path.join(_DB_DIR, "settings.db")


def _get_db() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────
# SCHEMA INIT
# ─────────────────────────────────────────────────────────────

def init_metadata_db():
    """Create all metadata tables if they don't exist."""
    with _get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sf_objects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain  TEXT NOT NULL,
            api_name    TEXT NOT NULL,
            label       TEXT,
            is_custom   INTEGER DEFAULT 0,
            is_queryable INTEGER DEFAULT 1,
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
            sobject_type    TEXT,
            status          TEXT,
            namespace_prefix TEXT,
            api_version     TEXT,
            body_length     INTEGER,
            last_modified   TEXT,
            raw_json        TEXT,
            synced_at       TEXT,
            UNIQUE(org_domain, trigger_id)
        );

        CREATE TABLE IF NOT EXISTS sf_lightning_components (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain       TEXT NOT NULL,
            component_id     TEXT,
            name             TEXT,
            label            TEXT,
            component_type   TEXT,
            namespace_prefix TEXT,
            api_version      TEXT,
            last_modified    TEXT,
            raw_json         TEXT,
            synced_at        TEXT,
            UNIQUE(org_domain, component_id)
        );

        CREATE TABLE IF NOT EXISTS sf_lightning_apps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            org_domain      TEXT NOT NULL,
            app_id          TEXT,
            name            TEXT,
            label           TEXT,
            nav_type        TEXT,
            namespace_prefix TEXT,
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
            sync_errors     TEXT
        );
        """)


# ─────────────────────────────────────────────────────────────
# STATUS
# ─────────────────────────────────────────────────────────────

def get_sync_status(org_domain: str) -> dict:
    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM sf_sync_status WHERE org_domain=?", (org_domain,)
            ).fetchone()
            return dict(row) if row else {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────
# INDIVIDUAL SYNC HELPERS
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


# ── Objects & Fields ──────────────────────────────────────────

def sync_objects_and_fields(sf, org_domain: str,
                             progress_callback: Optional[Callable] = None) -> int:
    """Sync all SObjects and their fields. Returns total objects synced."""
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

    cb(f"Found {len(sobjects)} objects. Storing…", 8)
    obj_rows = []
    for o in sobjects:
        obj_rows.append({
            "org_domain":   org_domain,
            "api_name":     o.get("name", ""),
            "label":        o.get("label", ""),
            "is_custom":    1 if o.get("custom", False) else 0,
            "is_queryable": 1 if o.get("queryable", True) else 0,
            "key_prefix":   o.get("keyPrefix", ""),
            "synced_at":    now,
        })

    with _get_db() as conn:
        _upsert_many(conn, "sf_objects", ("org_domain", "api_name"), obj_rows)

    # Sync fields for a sensible subset (all queryable objects)
    queryable = [o for o in sobjects if o.get("queryable", True)]
    total     = len(queryable)
    all_fields = []

    cb(f"Describing fields for {total} queryable objects…", 10)
    for i, o in enumerate(queryable):
        pct = 10 + int((i / max(total, 1)) * 30)   # 10–40%
        if i % 25 == 0:
            cb(f"Describing {o['name']} ({i+1}/{total})…", pct)
        try:
            desc = sf.__getattr__(o["name"]).describe()
            for f in desc.get("fields", []):
                all_fields.append({
                    "org_domain":  org_domain,
                    "object_name": o["name"],
                    "api_name":    f.get("name", ""),
                    "label":       f.get("label", ""),
                    "field_type":  f.get("type", ""),
                    "is_custom":   1 if f.get("custom", False) else 0,
                    "is_required": 1 if (not f.get("nillable", True)
                                         and not f.get("defaultedOnCreate", False)) else 0,
                })
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


# ── Agentforce Agents ─────────────────────────────────────────

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
        # Try GenAiPlanner (Agentforce native type) first
        try:
            result = sf.toolingexecute(
                "GET",
                "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,Description,"
                "BotType,Status+FROM+BotDefinition+LIMIT+200"
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
                    "Status,LastModifiedDate+FROM+BotDefinition+LIMIT+200"
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


# ── Flows ─────────────────────────────────────────────────────

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
        # Use Tooling API for richer metadata
        query = (
            "tooling/query/?q=SELECT+Id,ApiName,MasterLabel,ProcessType,"
            "Status,Description,LastModifiedDate+FROM+FlowDefinition+LIMIT+500"
        )
        result  = sf.toolingexecute("GET", query)
        records = result.get("records", [])

        for r in records:
            rows.append({
                "org_domain":    org_domain,
                "flow_id":       r.get("Id", ""),
                "api_name":      r.get("ApiName", ""),
                "label":         r.get("MasterLabel", ""),
                "process_type":  r.get("ProcessType", ""),
                "status":        r.get("Status", ""),
                "description":   (r.get("Description") or ""),
                "is_active":     1 if r.get("Status") == "Active" else 0,
                "last_modified": r.get("LastModifiedDate", ""),
                "raw_json":      json.dumps(r),
                "synced_at":     now,
            })
    except Exception as e:
        cb(f"Warning — could not sync flows via Tooling API: {e}", 46)
        # Fall back to REST API query on FlowDefinition (may have less fields)
        try:
            soql   = "SELECT Id,ApiName,Label,ProcessType,ActiveVersionId FROM FlowDefinition LIMIT 500"
            result = sf.query_all(soql)
            for r in result.get("records", []):
                rows.append({
                    "org_domain":   org_domain,
                    "flow_id":      r.get("Id", ""),
                    "api_name":     r.get("ApiName", ""),
                    "label":        r.get("Label", ""),
                    "process_type": r.get("ProcessType", ""),
                    "status":       "Active" if r.get("ActiveVersionId") else "Draft",
                    "description":  "",
                    "is_active":    1 if r.get("ActiveVersionId") else 0,
                    "last_modified": "",
                    "raw_json":     json.dumps(r),
                    "synced_at":    now,
                })
        except Exception:
            pass

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_flows", ("org_domain", "flow_id"), rows)

    cb(f"✓ {len(rows)} flow(s) synced", 52)
    return len(rows)


# ── Apex Triggers ─────────────────────────────────────────────

def sync_apex_triggers(sf, org_domain: str,
                       progress_callback: Optional[Callable] = None) -> int:
    """Sync all Apex Triggers."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Apex Triggers…", 54)
    rows = []
    try:
        soql = (
            "SELECT Id,Name,TableEnumOrId,Status,NamespacePrefix,"
            "ApiVersion,LengthWithoutComments,LastModifiedDate "
            "FROM ApexTrigger LIMIT 500"
        )
        result = sf.query_all(soql)
        for r in result.get("records", []):
            rows.append({
                "org_domain":       org_domain,
                "trigger_id":       r.get("Id", ""),
                "name":             r.get("Name", ""),
                "sobject_type":     r.get("TableEnumOrId", ""),
                "status":           r.get("Status", ""),
                "namespace_prefix": r.get("NamespacePrefix", "") or "",
                "api_version":      str(r.get("ApiVersion", "")),
                "body_length":      r.get("LengthWithoutComments", 0),
                "last_modified":    r.get("LastModifiedDate", ""),
                "raw_json":         json.dumps(r),
                "synced_at":        now,
            })
    except Exception as e:
        cb(f"Warning — could not sync triggers: {e}", 54)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_apex_triggers", ("org_domain", "trigger_id"), rows)

    cb(f"✓ {len(rows)} trigger(s) synced", 60)
    return len(rows)


# ── Lightning Components ──────────────────────────────────────

def sync_lightning_components(sf, org_domain: str,
                               progress_callback: Optional[Callable] = None) -> int:
    """Sync Lightning Web Components (LWC) and Aura Components."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Lightning Components (LWC + Aura)…", 62)
    rows = []
    try:
        # LWC via Tooling API
        result  = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,"
            "NamespacePrefix,ApiVersion,LastModifiedDate+FROM+LightningComponentBundle+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":        org_domain,
                "component_id":      r.get("Id", ""),
                "name":              r.get("DeveloperName", ""),
                "label":             r.get("MasterLabel", ""),
                "component_type":    "LWC",
                "namespace_prefix":  r.get("NamespacePrefix", "") or "",
                "api_version":       str(r.get("ApiVersion", "")),
                "last_modified":     r.get("LastModifiedDate", ""),
                "raw_json":          json.dumps(r),
                "synced_at":         now,
            })
    except Exception as e:
        cb(f"Warning — LWC sync: {e}", 62)

    try:
        # Aura Components via Tooling API
        result  = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,"
            "NamespacePrefix,ApiVersion,LastModifiedDate+FROM+AuraDefinitionBundle+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":        org_domain,
                "component_id":      r.get("Id", ""),
                "name":              r.get("DeveloperName", ""),
                "label":             r.get("MasterLabel", ""),
                "component_type":    "Aura",
                "namespace_prefix":  r.get("NamespacePrefix", "") or "",
                "api_version":       str(r.get("ApiVersion", "")),
                "last_modified":     r.get("LastModifiedDate", ""),
                "raw_json":          json.dumps(r),
                "synced_at":         now,
            })
    except Exception as e:
        cb(f"Warning — Aura sync: {e}", 64)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_lightning_components",
                         ("org_domain", "component_id"), rows)

    cb(f"✓ {len(rows)} lightning component(s) synced", 68)
    return len(rows)


# ── Lightning Apps ────────────────────────────────────────────

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
        result  = sf.toolingexecute(
            "GET",
            "tooling/query/?q=SELECT+Id,DeveloperName,MasterLabel,"
            "NavType,NamespacePrefix,LastModifiedDate+FROM+AppDefinition+LIMIT+500"
        )
        for r in result.get("records", []):
            rows.append({
                "org_domain":       org_domain,
                "app_id":           r.get("Id", ""),
                "name":             r.get("DeveloperName", ""),
                "label":            r.get("MasterLabel", ""),
                "nav_type":         r.get("NavType", ""),
                "namespace_prefix": r.get("NamespacePrefix", "") or "",
                "last_modified":    r.get("LastModifiedDate", ""),
                "raw_json":         json.dumps(r),
                "synced_at":        now,
            })
    except Exception as e:
        cb(f"Warning — could not sync Lightning Apps: {e}", 70)

    if rows:
        with _get_db() as conn:
            _upsert_many(conn, "sf_lightning_apps", ("org_domain", "app_id"), rows)

    cb(f"✓ {len(rows)} Lightning app(s) synced", 74)
    return len(rows)


# ── Installed Packages ────────────────────────────────────────

def sync_installed_packages(sf, org_domain: str,
                             progress_callback: Optional[Callable] = None) -> int:
    """Sync installed managed/unmanaged packages."""
    now = datetime.utcnow().isoformat()

    def cb(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)

    cb("Syncing Installed Packages…", 76)
    rows = []
    try:
        soql = (
            "SELECT Id,SubscriberPackageId,SubscriberPackage.Name,"
            "SubscriberPackage.NamespacePrefix,"
            "SubscriberPackageVersion.VersionNumber,"
            "SubscriberPackageVersion.Name,"
            "SubscriberPackageVersion.ReleaseState "
            "FROM InstalledSubscriberPackage LIMIT 200"
        )
        result = sf.toolingexecute(
            "GET",
            "tooling/query/?q=" + soql.replace(" ", "+")
        )
        for r in result.get("records", []):
            pkg     = r.get("SubscriberPackage") or {}
            ver     = r.get("SubscriberPackageVersion") or {}
            rows.append({
                "org_domain":       org_domain,
                "package_id":       r.get("Id", ""),
                "name":             pkg.get("Name", ""),
                "namespace_prefix": pkg.get("NamespacePrefix", "") or "",
                "version_number":   ver.get("VersionNumber", ""),
                "version_name":     ver.get("Name", "") or "",
                "publisher":        "",
                "install_date":     "",
                "raw_json":         json.dumps(r),
                "synced_at":        now,
            })
    except Exception as e:
        cb(f"Warning — InstalledSubscriberPackage via Tooling failed: {e}. Trying PackageSubscriber…", 76)
        try:
            soql2 = (
                "SELECT Id,SubscriberPackageName,SubscriberPackageNamespace,"
                "SubscriberPackageVersionNumber,SubscriberPackageVersionName "
                "FROM PackageSubscriber LIMIT 200"
            )
            result = sf.query_all(soql2)
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

    cb(f"✓ {len(rows)} installed package(s) synced", 82)
    return len(rows)


# ── Validation Rules ──────────────────────────────────────────

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
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def sync_full_org_metadata(sf, org_domain: str,
                           progress_callback: Optional[Callable] = None):
    """
    Run a complete metadata sync for the given Salesforce org.

    progress_callback MUST have signature: callback(msg: str, pct: float)
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
    """

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
    log("Saving sync status…", 95)
    try:
        with _get_db() as conn:
            conn.execute("""
                INSERT INTO sf_sync_status
                    (org_domain, last_sync, total_objects, total_fields,
                     total_agents, total_flows, total_triggers,
                     total_components, total_apps, total_packages,
                     total_vr, sync_errors)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
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
                    sync_errors      = excluded.sync_errors
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
                "; ".join(errors) if errors else "",
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
        f"{counts['total_packages']} packages"
    )
    log(summary, 100)
    return counts


# ─────────────────────────────────────────────────────────────
# READ HELPERS (used by Metadata Explorer page)
# ─────────────────────────────────────────────────────────────

def get_org_objects(org_domain: str) -> list:
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_objects WHERE org_domain=? ORDER BY api_name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_fields(org_domain: str, object_name: str = "") -> list:
    try:
        with _get_db() as conn:
            if object_name:
                rows = conn.execute(
                    "SELECT * FROM sf_fields WHERE org_domain=? AND object_name=? "
                    "ORDER BY api_name",
                    (org_domain, object_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sf_fields WHERE org_domain=? ORDER BY object_name, api_name",
                    (org_domain,)
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def get_org_agents(org_domain: str) -> list:
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
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM sf_validation_rules WHERE org_domain=? ORDER BY object_name, name",
                (org_domain,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []