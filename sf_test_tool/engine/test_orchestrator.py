"""
test_orchestrator.py
Runs test cases and judges results using multiple LLM models.
Uses live Salesforce metadata and strict prompt parsing.
No hallucinations — strictly follows user instructions.
"""

import json
import time
from datetime import datetime
from config.settings_manager import get_selected_judge_models
from connectors.llm_connector import (
    multi_model_judge, get_llm_response,
    parse_prompt_to_test_steps, DEFAULT_JUDGE_MODELS
)
from engine.prompt_parser import (
    parse_test_prompt, build_field_list,
    get_field_generation_prompt, FIELD_GROUPS
)

# Fields that must never be sent to Salesforce
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
    'HasOptedOutOfEmail', 'HasOptedOutOfFax', 'DoNotCall',
}

FAKE_ID_PATTERNS = [
    "000abc", "000xyz", "000def", "0000000",
    "test123", "999999", "111111"
]


def get_judge_models(session_judge_models=None) -> list:
    """Get judge models — session → database → defaults"""
    if session_judge_models and len(session_judge_models) > 0:
        return session_judge_models
    db_models = get_selected_judge_models()
    if db_models:
        return db_models
    return DEFAULT_JUDGE_MODELS


def _get_org_domain(sf) -> str:
    """Extract clean org domain from sf connection"""
    if not sf:
        return ""
    instance = sf.sf_instance or ""
    return (
        instance
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )


def _clean_data(data: dict,
                valid_fields: set,
                exclude_fields: set) -> dict:
    """
    Remove system fields, excluded fields, fake IDs
    and invalid values before sending to Salesforce.
    """
    cleaned = {}
    for k, v in data.items():
        if k in SYSTEM_EXCLUDED_FIELDS:             continue
        if k in exclude_fields:                      continue
        if k not in valid_fields:                    continue
        if v is None or v == "" or v == "null":      continue
        if isinstance(v, str) and any(
            p in v.lower() for p in FAKE_ID_PATTERNS
        ):
            continue
        cleaned[k] = v
    return cleaned


def _resolve_existing_account(sf) -> str:
    """Fetch the ID of the first available Account in the org"""
    try:
        from connectors.salesforce_connector import run_soql_query
        records, _ = run_soql_query(
            sf, "SELECT Id, Name FROM Account LIMIT 1"
        )
        if records:
            return records[0]["Id"]
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────
# CORE: CREATE RECORDS FROM PROMPT
# ─────────────────────────────────────────────────────────────

def create_records_from_prompt(sf, prompt: str,
                                llm_model: str,
                                org_domain: str) -> tuple:
    """
    Parse prompt → get metadata → generate data → create records.
    Strictly follows include/exclude instructions from the prompt.
    Creates multiple records if the prompt asks for more than one.
    """
    from engine.sf_metadata_engine import (
        get_createable_fields, discover_object_fields
    )
    from connectors.salesforce_connector import (
        create_record, run_soql_query
    )

    # Step 1 — Parse the prompt into structured instructions
    parsed = parse_test_prompt(prompt, llm_model)

    object_name  = parsed.get("object_name",  "Contact")
    record_count = max(1, int(parsed.get("record_count", 1)))
    field_values = parsed.get("field_values", {})
    exclude_set  = set(parsed.get("exclude_fields", []))

    # Step 2 — Get real createable fields from metadata cache
    createable = get_createable_fields(org_domain, object_name)
    if not createable:
        # Pull on the fly if not cached yet
        discover_object_fields(sf, org_domain, object_name)
        createable = get_createable_fields(org_domain, object_name)

    if not createable:
        return None, (
            f"No field metadata found for {object_name}. "
            f"Please run Metadata Sync in Settings first."
        )

    # Step 3 — Apply include/exclude rules from the parsed prompt
    allowed_fields    = build_field_list(parsed, createable)
    valid_field_names = {f["field_name"] for f in allowed_fields}

    if not allowed_fields:
        return None, (
            f"After applying your include/exclude rules, "
            f"no valid fields remain for {object_name}."
        )

    # Step 4 — Resolve "use_existing" references to real IDs
    resolved_values = {}
    for field_key, field_val in field_values.items():
        if str(field_val).lower() == "use_existing":
            if "account" in field_key.lower():
                account_id = _resolve_existing_account(sf)
                if account_id:
                    resolved_values["AccountId"] = account_id
        else:
            if field_key not in SYSTEM_EXCLUDED_FIELDS:
                resolved_values[field_key] = field_val

    # Step 5 — Create each record
    created_records = []
    errors          = []

    for i in range(record_count):
        # Generate field data using strict prompt
        gen_prompt = get_field_generation_prompt(
            parsed, allowed_fields, object_name, i + 1
        )
        gen_resp, gen_err = get_llm_response(
            gen_prompt, model=llm_model, max_tokens=600
        )
        if gen_err:
            errors.append(
                f"Record {i+1}: generation failed — {gen_err}"
            )
            continue

        try:
            clean = (
                gen_resp.strip()
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            raw_data = json.loads(clean)
        except Exception as e:
            errors.append(f"Record {i+1}: JSON parse error — {e}")
            continue

        # Clean: remove system fields, excluded fields, fake IDs
        data = _clean_data(raw_data, valid_field_names, exclude_set)

        # Apply resolved values (e.g. real AccountId)
        for k, v in resolved_values.items():
            if k in valid_field_names and k not in exclude_set:
                data[k] = v

        if not data:
            errors.append(
                f"Record {i+1}: no valid fields after cleaning"
            )
            continue

        # Create in Salesforce
        result, err = create_record(sf, object_name, data)
        if err:
            errors.append(f"Record {i+1} create error: {err}")
            continue

        record_id = result.get("id", "")

        # Fetch back the created record details
        if record_id:
            safe_fields = [
                f["field_name"] for f in allowed_fields
                if f["field_type"] not in ["reference"]
                and f["field_name"] not in SYSTEM_EXCLUDED_FIELDS
            ][:12]
            fetch_str = ", ".join(["Id"] + safe_fields)
            records, _ = run_soql_query(
                sf,
                f"SELECT {fetch_str} FROM {object_name} "
                f"WHERE Id = '{record_id}' LIMIT 1"
            )
            created_records.append({
                "record_index": i + 1,
                "record_id":    record_id,
                "record":       records[0] if records else data,
                "fields_used":  list(data.keys())
            })
        else:
            created_records.append({
                "record_index": i + 1,
                "record_id":    "",
                "record":       data,
                "fields_used":  list(data.keys())
            })

    # Build final summary
    if created_records:
        ids = [r["record_id"] for r in created_records
               if r["record_id"]]
        return {
            "operation":       "create",
            "object":          object_name,
            "records_created": len(created_records),
            "record_ids":      ids,
            "records":         created_records,
            "errors":          errors,
            "fields_excluded": [
                f for f in list(exclude_set)
                if f not in SYSTEM_EXCLUDED_FIELDS
            ],
            "summary": (
                f"{len(created_records)} {object_name} record(s) "
                f"created successfully. "
                f"Record IDs: {', '.join(ids)}"
                + (f" | Warnings: {errors}" if errors else "")
            )
        }, None

    return None, (
        f"Failed to create any {object_name} records. "
        f"Errors: {'; '.join(errors)}"
    )


# ─────────────────────────────────────────────────────────────
# QUERY FROM PROMPT
# ─────────────────────────────────────────────────────────────

def query_from_prompt(sf, parsed: dict,
                       llm_model: str,
                       org_domain: str) -> tuple:
    """Execute a SOQL query based on parsed prompt instructions"""
    from connectors.salesforce_connector import run_soql_query
    from engine.sf_metadata_engine import get_createable_fields

    object_name = parsed.get("object_name", "Contact")
    fields      = get_createable_fields(org_domain, object_name)
    field_list  = ", ".join(
        ["Id"] + [
            f["field_name"] for f in fields[:10]
            if f["field_name"] not in SYSTEM_EXCLUDED_FIELDS
        ]
    ) if fields else "Id, Name"

    records, err = run_soql_query(
        sf,
        f"SELECT {field_list} FROM {object_name} LIMIT 10"
    )
    return {
        "operation": "query",
        "object":    object_name,
        "records":   records,
        "count":     len(records),
        "summary":   f"Found {len(records)} {object_name} records"
    }, err


# ─────────────────────────────────────────────────────────────
# PROMPT TEST RUNNER
# ─────────────────────────────────────────────────────────────

def run_prompt_test(sf, test_case: dict,
                    llm_model: str) -> tuple:
    """
    Main handler for plain English test prompts.
    Parses → validates → executes → returns real Salesforce results.
    Never simulates UI — always calls real Salesforce APIs.
    """
    prompt     = (
        test_case.get("input_data")
        or test_case.get("test_name", "")
    )
    org_domain = _get_org_domain(sf)

    # Parse the prompt to understand what the user wants
    parsed    = parse_test_prompt(prompt, llm_model)
    operation = parsed.get("operation", "create").lower()

    if operation == "create":
        return create_records_from_prompt(
            sf, prompt, llm_model, org_domain
        )
    elif operation == "query":
        return query_from_prompt(
            sf, parsed, llm_model, org_domain
        )
    else:
        # Default to create for now
        return create_records_from_prompt(
            sf, prompt, llm_model, org_domain
        )


# ─────────────────────────────────────────────────────────────
# API TEST RUNNER
# ─────────────────────────────────────────────────────────────

def run_api_test(sf, test_case: dict,
                 llm_model: str) -> tuple:
    """Run a structured Salesforce API or SOQL test"""
    try:
        action     = test_case.get("test_type", "api").lower()
        input_d    = test_case.get("input_data", "")
        org_domain = _get_org_domain(sf)

        if "soql" in action or "query" in action:
            from connectors.salesforce_connector import run_soql_query
            query = (
                input_d
                if input_d.strip().upper().startswith("SELECT")
                else "SELECT Id, Name FROM Account LIMIT 5"
            )
            records, err = run_soql_query(sf, query)
            if err:
                return None, err
            return {"records": records, "count": len(records)}, None

        if "create" in action or "insert" in action:
            return create_records_from_prompt(
                sf,
                input_d or test_case.get("test_name", ""),
                llm_model,
                org_domain
            )

        from connectors.salesforce_connector import call_salesforce_api
        endpoint = (
            input_d if input_d.startswith("/")
            else "/services/data/v59.0/sobjects/"
        )
        return call_salesforce_api(sf, endpoint)

    except Exception as e:
        return None, f"API test error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# MAIN RUNNER — runs all test cases with multi-model judging
# ─────────────────────────────────────────────────────────────

def run_all_tests(test_cases: list, sf,
                  llm_model: str,
                  judge_models: list = None) -> list:
    """
    Run all test cases and judge each result with multiple LLM models.
    """
    models_to_use = get_judge_models(judge_models)
    results       = []

    for tc in test_cases:
        start   = time.time()
        test_id = tc.get("test_id",   f"TC{len(results)+1:03d}")
        name    = tc.get("test_name", "Unnamed Test")
        t_type  = tc.get("test_type", "api").lower()
        actual_result = None
        error         = None

        try:
            if (
                "prompt" in t_type
                or "nlp"   in t_type
                or "plain" in t_type
            ):
                actual_result, error = run_prompt_test(
                    sf, tc, llm_model
                )
            elif "web" in t_type or "ui" in t_type:
                actual_result = {
                    "note": "Web UI test — Playwright runner"
                }
            elif "agent" in t_type or "agentforce" in t_type:
                actual_result = {
                    "note": "Agentforce test — see Agentforce page"
                }
            else:
                actual_result, error = run_api_test(
                    sf, tc, llm_model
                )
        except Exception as e:
            error = str(e)

        elapsed  = round(time.time() - start, 2)
        expected = tc.get(
            "expected_output",
            "Records created successfully with valid Record IDs returned"
        )

        # Judge the result
        if error and not actual_result:
            judge_result = {
                "final_status":       "ERROR",
                "status":             "ERROR",
                "confidence":         0,
                "consensus":          "Error during execution",
                "summary":            str(error),
                "individual_results": [],
                "pass_count":         0,
                "fail_count":         0,
                "error_count":        len(models_to_use)
            }
        else:
            actual_str   = (
                str(actual_result) if actual_result
                else str(error)
            )
            judge_result = multi_model_judge(
                test_name=name,
                expected_result=expected,
                actual_result=actual_str,
                models=models_to_use
            )
            judge_result["status"] = judge_result.get(
                "final_status", "ERROR"
            )

        results.append({
            "test_id":            test_id,
            "test_name":          name,
            "test_type":          t_type,
            "priority":           tc.get("priority", "Medium"),
            "tags":               tc.get("tags", ""),
            "input_data":         str(tc.get("input_data",""))[:500],
            "expected_output":    expected,
            "actual_output":      str(actual_result)[:3000],
            "status":             judge_result.get("status",     "ERROR"),
            "confidence":         judge_result.get("confidence",  0),
            "consensus":          judge_result.get("consensus",   ""),
            "judge_summary":      judge_result.get("summary",     ""),
            "individual_results": judge_result.get(
                "individual_results", []
            ),
            "reason":             judge_result.get("summary",     ""),
            "pass_count":         judge_result.get("pass_count",  0),
            "fail_count":         judge_result.get("fail_count",  0),
            "error_count":        judge_result.get("error_count", 0),
            "models_used":        len(models_to_use),
            "duration_sec":       elapsed,
            "timestamp":          datetime.now().isoformat(),
            "error":              str(error) if error else ""
        })

    return results


# ─────────────────────────────────────────────────────────────
# SAVE TO DATABASE
# ─────────────────────────────────────────────────────────────

def save_results_to_db(results: list,
                       run_name: str = None) -> bool:
    """Save test run results to SQLite database"""
    try:
        import sqlite3
        from config.settings_manager import DB_PATH

        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name        TEXT,
                test_id         TEXT,
                test_name       TEXT,
                test_type       TEXT,
                status          TEXT,
                confidence      REAL,
                consensus       TEXT,
                judge_summary   TEXT,
                actual_output   TEXT,
                expected_output TEXT,
                duration_sec    REAL,
                models_used     INTEGER,
                pass_count      INTEGER,
                fail_count      INTEGER,
                error_count     INTEGER,
                timestamp       TEXT
            )
        """)
        run = run_name or (
            f"Run {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        for r in results:
            cur.execute("""
                INSERT INTO test_results
                (run_name, test_id, test_name, test_type, status,
                 confidence, consensus, judge_summary, actual_output,
                 expected_output, duration_sec, models_used,
                 pass_count, fail_count, error_count, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                run,
                r["test_id"],         r["test_name"],
                r["test_type"],       r["status"],
                r["confidence"],      r["consensus"],
                r["judge_summary"],   r["actual_output"],
                r["expected_output"], r["duration_sec"],
                r["models_used"],     r["pass_count"],
                r["fail_count"],      r["error_count"],
                r["timestamp"]
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Could not save results: {e}")
        return False