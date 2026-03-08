"""
test_plan_manager.py
Manages Test Plans, Test Runs, and Test Scenarios in the database.
Provides full audit trail, immutable run records, and result storage.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from config.settings_manager import DB_PATH


# ─────────────────────────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────────────────────────

def init_test_plan_db():
    """Create all test plan and execution tables"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Test Plans
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id         TEXT UNIQUE NOT NULL,
            plan_name       TEXT NOT NULL,
            description     TEXT,
            client_project  TEXT,
            environment     TEXT,
            org_domain      TEXT,
            run_type        TEXT DEFAULT 'Single Run',
            status          TEXT DEFAULT 'draft',
            created_at      TEXT,
            created_by      TEXT DEFAULT 'user',
            total_scenarios INTEGER DEFAULT 0
        )
    """)

    # Test Runs (one plan can have multiple runs)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT UNIQUE NOT NULL,
            plan_id         TEXT NOT NULL,
            plan_name       TEXT,
            client_project  TEXT,
            environment     TEXT,
            org_domain      TEXT,
            status          TEXT DEFAULT 'pending',
            total_scenarios INTEGER DEFAULT 0,
            passed          INTEGER DEFAULT 0,
            failed          INTEGER DEFAULT 0,
            errors          INTEGER DEFAULT 0,
            blocked         INTEGER DEFAULT 0,
            skipped         INTEGER DEFAULT 0,
            started_at      TEXT,
            completed_at    TEXT,
            duration_sec    REAL DEFAULT 0,
            run_type        TEXT DEFAULT 'Single Run',
            input_method    TEXT DEFAULT 'prompt',
            models_used     TEXT,
            FOREIGN KEY(plan_id) REFERENCES test_plans(plan_id)
        )
    """)

    # Individual Test Scenarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_scenarios (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id      TEXT NOT NULL,
            run_id           TEXT NOT NULL,
            plan_id          TEXT NOT NULL,
            row_number       INTEGER,
            scenario_summary TEXT,
            test_steps       TEXT,
            expected_outcome TEXT,
            actual_outcome   TEXT,
            status           TEXT DEFAULT 'pending',
            pass_fail        TEXT,
            confidence       REAL DEFAULT 0,
            judge_consensus  TEXT,
            judge_summary    TEXT,
            individual_judges TEXT,
            step_logs        TEXT,
            error_detail     TEXT,
            duration_sec     REAL DEFAULT 0,
            models_used      INTEGER DEFAULT 0,
            pass_count       INTEGER DEFAULT 0,
            fail_count       INTEGER DEFAULT 0,
            error_count      INTEGER DEFAULT 0,
            started_at       TEXT,
            completed_at     TEXT,
            FOREIGN KEY(run_id) REFERENCES test_runs(run_id)
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# TEST PLAN OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_test_plan(plan_name: str, description: str = "",
                     client_project: str = "", environment: str = "",
                     org_domain: str = "", run_type: str = "Single Run",
                     total_scenarios: int = 0) -> str:
    """Create a new test plan and return its plan_id"""
    init_test_plan_db()
    plan_id = f"PLAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    conn    = sqlite3.connect(DB_PATH)
    cur     = conn.cursor()
    cur.execute("""
        INSERT INTO test_plans
        (plan_id, plan_name, description, client_project,
         environment, org_domain, run_type, status,
         created_at, total_scenarios)
        VALUES (?,?,?,?,?,?,?,'active',?,?)
    """, (
        plan_id, plan_name, description, client_project,
        environment, org_domain, run_type,
        datetime.now().isoformat(), total_scenarios
    ))
    conn.commit()
    conn.close()
    return plan_id


def get_all_test_plans() -> list:
    """Get all test plans ordered by most recent"""
    init_test_plan_db()
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT plan_id, plan_name, description, client_project,
               environment, org_domain, run_type, status,
               created_at, total_scenarios
        FROM test_plans
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    cols = [
        "plan_id", "plan_name", "description", "client_project",
        "environment", "org_domain", "run_type", "status",
        "created_at", "total_scenarios"
    ]
    return [dict(zip(cols, r)) for r in rows]


# ─────────────────────────────────────────────────────────────
# TEST RUN OPERATIONS
# ─────────────────────────────────────────────────────────────

def create_test_run(plan_id: str, plan_name: str,
                    client_project: str = "", environment: str = "",
                    org_domain: str = "", run_type: str = "Single Run",
                    input_method: str = "prompt",
                    total_scenarios: int = 0,
                    models_used: list = None) -> str:
    """Create a new test run under a plan and return its run_id"""
    init_test_plan_db()
    run_id = f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"
    conn   = sqlite3.connect(DB_PATH)
    cur    = conn.cursor()
    cur.execute("""
        INSERT INTO test_runs
        (run_id, plan_id, plan_name, client_project, environment,
         org_domain, status, total_scenarios, started_at,
         run_type, input_method, models_used)
        VALUES (?,?,?,?,?,?,'running',?,?,?,?,?)
    """, (
        run_id, plan_id, plan_name, client_project, environment,
        org_domain, total_scenarios,
        datetime.now().isoformat(), run_type, input_method,
        json.dumps(models_used or [])
    ))
    conn.commit()
    conn.close()
    return run_id


def complete_test_run(run_id: str, results: list):
    """Mark a run as complete and store aggregated stats"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    passed  = sum(1 for r in results if r.get("status") == "PASS")
    failed  = sum(1 for r in results if r.get("status") == "FAIL")
    errors  = sum(1 for r in results if r.get("status") == "ERROR")
    blocked = sum(1 for r in results if r.get("status") == "BLOCKED")

    cur.execute("""
        UPDATE test_runs SET
        status       = 'complete',
        passed       = ?,
        failed       = ?,
        errors       = ?,
        blocked      = ?,
        completed_at = ?
        WHERE run_id = ?
    """, (passed, failed, errors, blocked,
          datetime.now().isoformat(), run_id))
    conn.commit()
    conn.close()


def get_test_run(run_id: str) -> dict:
    """Get a single test run by ID"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT run_id, plan_id, plan_name, client_project,
               environment, org_domain, status, total_scenarios,
               passed, failed, errors, blocked, skipped,
               started_at, completed_at, run_type, input_method
        FROM test_runs WHERE run_id = ?
    """, (run_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    cols = [
        "run_id", "plan_id", "plan_name", "client_project",
        "environment", "org_domain", "status", "total_scenarios",
        "passed", "failed", "errors", "blocked", "skipped",
        "started_at", "completed_at", "run_type", "input_method"
    ]
    return dict(zip(cols, row))


def get_all_test_runs(plan_id: str = None) -> list:
    """Get all test runs, optionally filtered by plan"""
    init_test_plan_db()
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    if plan_id:
        cur.execute("""
            SELECT run_id, plan_id, plan_name, client_project,
                   environment, org_domain, status, total_scenarios,
                   passed, failed, errors, started_at, completed_at,
                   run_type, input_method
            FROM test_runs WHERE plan_id = ?
            ORDER BY started_at DESC
        """, (plan_id,))
    else:
        cur.execute("""
            SELECT run_id, plan_id, plan_name, client_project,
                   environment, org_domain, status, total_scenarios,
                   passed, failed, errors, started_at, completed_at,
                   run_type, input_method
            FROM test_runs
            ORDER BY started_at DESC
            LIMIT 100
        """)
    rows = cur.fetchall()
    conn.close()
    cols = [
        "run_id", "plan_id", "plan_name", "client_project",
        "environment", "org_domain", "status", "total_scenarios",
        "passed", "failed", "errors", "started_at", "completed_at",
        "run_type", "input_method"
    ]
    return [dict(zip(cols, r)) for r in rows]


# ─────────────────────────────────────────────────────────────
# TEST SCENARIO OPERATIONS
# ─────────────────────────────────────────────────────────────

def save_scenario_result(run_id: str, plan_id: str,
                          row_number: int, result: dict):
    """Save a single scenario result to the database"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    scenario_id = (
        result.get("test_id")
        or f"SCN-{run_id}-{row_number:04d}"
    )
    cur.execute("""
        INSERT INTO test_scenarios
        (scenario_id, run_id, plan_id, row_number,
         scenario_summary, test_steps, expected_outcome,
         actual_outcome, status, pass_fail, confidence,
         judge_consensus, judge_summary, individual_judges,
         step_logs, error_detail, duration_sec, models_used,
         pass_count, fail_count, error_count,
         started_at, completed_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        scenario_id, run_id, plan_id, row_number,
        result.get("test_name",        ""),
        result.get("input_data",       ""),
        result.get("expected_output",  ""),
        result.get("actual_output",    "")[:3000],
        result.get("status",           "ERROR"),
        result.get("status",           "ERROR"),
        result.get("confidence",        0),
        result.get("consensus",        ""),
        result.get("judge_summary",    ""),
        json.dumps(result.get("individual_results", [])),
        result.get("step_logs",        ""),
        result.get("error",            ""),
        result.get("duration_sec",      0),
        result.get("models_used",       0),
        result.get("pass_count",        0),
        result.get("fail_count",        0),
        result.get("error_count",       0),
        result.get("timestamp",         datetime.now().isoformat()),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def get_scenarios_for_run(run_id: str) -> list:
    """Get all scenarios for a test run"""
    init_test_plan_db()
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT scenario_id, row_number, scenario_summary,
               test_steps, expected_outcome, actual_outcome,
               status, confidence, judge_consensus, judge_summary,
               individual_judges, error_detail, duration_sec,
               models_used, pass_count, fail_count, error_count,
               started_at, completed_at
        FROM test_scenarios
        WHERE run_id = ?
        ORDER BY row_number ASC
    """, (run_id,))
    rows = cur.fetchall()
    conn.close()
    cols = [
        "scenario_id", "row_number", "scenario_summary",
        "test_steps", "expected_outcome", "actual_outcome",
        "status", "confidence", "judge_consensus", "judge_summary",
        "individual_judges", "error_detail", "duration_sec",
        "models_used", "pass_count", "fail_count", "error_count",
        "started_at", "completed_at"
    ]
    return [dict(zip(cols, r)) for r in rows]


def get_run_stats(run_id: str) -> dict:
    """Get aggregated stats for a run from scenario table"""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='PASS'    THEN 1 ELSE 0 END) as passed,
            SUM(CASE WHEN status='FAIL'    THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='ERROR'   THEN 1 ELSE 0 END) as errors,
            SUM(CASE WHEN status='BLOCKED' THEN 1 ELSE 0 END) as blocked,
            AVG(confidence) as avg_confidence,
            SUM(duration_sec) as total_duration
        FROM test_scenarios WHERE run_id = ?
    """, (run_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "total":          row[0] or 0,
        "passed":         row[1] or 0,
        "failed":         row[2] or 0,
        "errors":         row[3] or 0,
        "blocked":        row[4] or 0,
        "avg_confidence": round(row[5] or 0, 1),
        "total_duration": round(row[6] or 0, 1),
        "pass_rate": (
            round((row[1] or 0) / row[0] * 100, 1)
            if row[0] else 0
        )
    }