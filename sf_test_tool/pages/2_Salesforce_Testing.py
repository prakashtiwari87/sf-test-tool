"""
2_Salesforce_Testing.py
Enterprise-grade Test Execution Command Center.
Supports bulk structured execution via Excel or UI prompt builder.
Full audit trail, row-by-row execution, permanent result storage.
"""

import streamlit as st
import pandas as pd
import json
import time
import io
from datetime import datetime

# ── PAGE CONFIG — MUST BE FIRST ───────────────────────────────
st.set_page_config(
    page_title="Salesforce Testing — AmplifyQA",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state = "collapsed",
)

# ── IMPORTS ───────────────────────────────────────────────────
from config.theme import inject_css, render_header, render_sidebar_logo
from config.settings_manager import (
    get_active_salesforce_connection,
    get_selected_judge_models,
    load_all_keys_to_env
)
from connectors.salesforce_connector import connect_with_oauth, get_org_info
from engine.excel_loader import (
    load_test_cases_from_excel,
    load_test_cases_from_bulk_prompts,
    create_excel_template,
)
from engine.test_orchestrator import run_all_tests
from engine.test_plan_manager import (
    init_test_plan_db,
    create_test_plan,
    create_test_run,
    complete_test_run,
    save_scenario_result,
    get_all_test_runs
)
from reports.report_generator import (
    save_results_to_json,
    generate_html_report
)

# ── INIT ──────────────────────────────────────────────────────
inject_css()
load_all_keys_to_env()
init_test_plan_db()

# ── AUTO-CONNECT SALESFORCE ───────────────────────────────────
sf  = st.session_state.get("sf_connection")
org = st.session_state.get("sf_org_info", {})

if not sf:
    active = get_active_salesforce_connection()
    if active and active.get("client_id"):
        sf_try, err = connect_with_oauth(
            client_id=active["client_id"],
            client_secret=active["client_secret"],
            domain=active["domain"]
        )
        if sf_try:
            st.session_state.sf_connection = sf_try
            st.session_state.sf_org_info   = get_org_info(sf_try)
            sf  = sf_try
            org = st.session_state.sf_org_info

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_logo()
    st.page_link("app.py",                               label="🏠 Home")
    st.page_link("pages/2_Salesforce_Testing.py",        label="🧪 Salesforce Testing")
    st.page_link("pages/3_Agentforce_Testing.py",        label="🤖 Agentforce Testing")
    st.page_link("pages/4_Bedrock_AgentCore_Testing.py", label="☁️ Bedrock Testing")
    st.page_link("pages/5_Reports.py",                   label="📊 Reports")
    st.page_link("pages/7_Metadata_Explorer.py",         label="🔍 Metadata Explorer")
    st.page_link("pages/6_Test_History.py",              label="📂 Test History")
    st.page_link("pages/8_Settings.py",                  label="⚙️ Settings")

# ── HEADER — org is now guaranteed to be defined ──────────────
render_header(
    "Salesforce Testing", "🧪",
    org_name=org.get("org_name", ""),
    environment=org.get("org_type", "Salesforce")
)

# ── SESSION STATE DEFAULTS ────────────────────────────────────
defaults = {
    "runner_stage":      "metadata",
    "test_plan_meta":    {},
    "test_cases":        [],
    "run_results":       [],
    "current_run_id":    None,
    "current_plan_id":   None,
    "input_method":      None,
    "bulk_prompt_rows":  [
        {"prompt_id": "UI-0001", "intent": "",
         "expected_outcome": "", "priority": "Medium", "tags": ""}
    ],
    "execution_paused":  False,
    "execution_stopped": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── JUDGE MODELS ──────────────────────────────────────────────
judge_models = st.session_state.get(
    "judge_models", get_selected_judge_models()
)
llm_model = (
    judge_models[0] if judge_models
    else "groq/llama-3.3-70b-versatile"
)

# ── CONNECTION STATUS STRIP ───────────────────────────────────
conn_col1, conn_col2, conn_col3 = st.columns([2, 2, 3])
with conn_col1:
    if sf:
        st.success(f"🟢 {org.get('org_name', 'Connected')}")
    else:
        st.error("❌ Not connected — go to Settings")
with conn_col2:
    st.info(f"🧠 {len(judge_models)} judge model(s)")
with conn_col3:
    stage_labels = {
        "metadata": "📋 Step 1 of 4: Test Plan Setup",
        "input":    "📥 Step 2 of 4: Test Input",
        "running":  "⚡ Step 3 of 4: Executing",
        "results":  "✅ Step 4 of 4: Results"
    }
    st.info(stage_labels.get(st.session_state.runner_stage, ""))

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# STAGE 1 — TEST PLAN METADATA
# ══════════════════════════════════════════════════════════════
if st.session_state.runner_stage == "metadata":

    st.subheader("📋 Test Plan Setup")
    st.caption(
        "All metadata is persisted to the database and tied to "
        "every test scenario result for full audit traceability."
    )

    with st.form("test_plan_form"):
        col1, col2 = st.columns(2)

        with col1:
            plan_name = st.text_input(
                "Test Plan Name *",
                placeholder="e.g. Sprint 42 Regression Suite"
            )
            client_project = st.text_input(
                "Client / Project",
                placeholder="e.g. Acme Corp — Phase 2"
            )
            run_type = st.selectbox(
                "Run Type",
                ["Single Run", "Bulk Run", "Regression Run",
                 "Smoke Test", "Scheduled Run (future)"]
            )

        with col2:
            description = st.text_area(
                "Test Plan Description",
                placeholder="Describe the scope and objectives...",
                height=100
            )
            environment = st.selectbox(
                "Salesforce Environment",
                ["Sandbox", "Production", "Developer Edition",
                 "Scratch Org", "UAT", "Staging"]
            )
            org_display = (
                org.get("org_name", "")
                or org.get("domain", "Not connected")
            )
            st.text_input(
                "Salesforce Org",
                value=org_display,
                disabled=True
            )

        submitted = st.form_submit_button(
            "✅ Confirm and Continue to Test Input →",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not plan_name.strip():
                st.error("Test Plan Name is required.")
            elif not sf:
                st.error(
                    "Salesforce not connected. "
                    "Go to Settings to connect your org."
                )
            else:
                st.session_state.test_plan_meta = {
                    "plan_name":      plan_name.strip(),
                    "description":    description.strip(),
                    "client_project": client_project.strip(),
                    "environment":    environment,
                    "org_domain":     org.get("domain", ""),
                    "org_name":       org.get("org_name", ""),
                    "run_type":       run_type,
                    "created_at":     datetime.now().isoformat()
                }
                st.session_state.runner_stage = "input"
                st.rerun()

    # Recent runs
    st.markdown("---")
    st.subheader("📂 Recent Test Runs")
    recent_runs = get_all_test_runs()
    if recent_runs:
        for run in recent_runs[:10]:
            status_icon = {
                "complete": "✅", "running": "⚡",
                "failed":   "❌", "pending": "⏳"
            }.get(run["status"], "📋")
            passed = run.get("passed", 0)
            total  = run.get("total_scenarios", 0)
            rate   = f"{round(passed/total*100)}%" if total else "—"

            col1, col2, col3, col4, col5 = st.columns([3,2,1,1,1])
            with col1:
                st.write(f"{status_icon} **{run['plan_name']}**")
                st.caption(
                    f"{run.get('client_project','—')} | "
                    f"{run.get('environment','—')} | "
                    f"{run.get('started_at','')[:16].replace('T',' ')}"
                )
            with col2:
                st.write(f"🏢 {run.get('org_domain','—')[:35]}")
            with col3:
                st.metric("Total",  total)
            with col4:
                st.metric("Passed", passed)
            with col5:
                st.metric("Rate",   rate)
            st.markdown("---")
    else:
        st.info("No test runs yet. Create your first test plan above.")


# ══════════════════════════════════════════════════════════════
# STAGE 2 — INPUT METHOD + TEST CASES
# ══════════════════════════════════════════════════════════════
elif st.session_state.runner_stage == "input":

    meta = st.session_state.test_plan_meta
    st.subheader(f"📥 Test Input — {meta.get('plan_name')}")
    st.caption(
        f"📁 {meta.get('client_project','—')} | "
        f"🌐 {meta.get('environment')} | "
        f"🏢 {meta.get('org_name','—')} | "
        f"🔄 {meta.get('run_type')}"
    )

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Plan Setup"):
            st.session_state.runner_stage = "metadata"
            st.rerun()

    st.markdown("---")
    st.markdown("### How do you want to provide your tests?")

    input_tab1, input_tab2 = st.tabs([
        "📊 Upload Structured Excel",
        "✏️ Add Prompts via UI"
    ])

    # ── EXCEL UPLOAD ──────────────────────────────────────────
    with input_tab1:
        col_dl, col_info = st.columns([1, 3])
        with col_dl:
            st.download_button(
                label="⬇️ Download Excel Template",
                data=create_excel_template(),
                file_name="sf_test_scenarios_template.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )
        with col_info:
            st.info(
                "Template columns: **Test Scenario ID** | "
                "**Test Scenario Summary** | "
                "**Detailed Test Steps / Instructions** | "
                "**Expected Outcome / Result** | "
                "Priority | Tags"
            )

        uploaded = st.file_uploader(
            "Upload your completed Excel file",
            type=["xlsx", "xls"],
            key="excel_upload"
        )

        if uploaded:
            test_cases, warning = load_test_cases_from_excel(uploaded)
            if test_cases:
                st.session_state.test_cases   = test_cases
                st.session_state.input_method = "excel"

                st.success(f"✅ Loaded **{len(test_cases)}** test scenarios")
                if warning:
                    st.warning(f"⚠️ {warning}")

                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Total Scenarios", len(test_cases))
                sc2.metric("Est. Runtime",    f"~{len(test_cases)*30//60} min")
                sc3.metric("Judge Models",    len(judge_models))

                st.markdown("**Preview (first 10 rows):**")
                preview = pd.DataFrame([{
                    "ID":       tc["test_id"],
                    "Summary":  tc["test_name"][:60],
                    "Steps":    tc["input_data"][:80] + "...",
                    "Expected": tc["expected_output"][:60],
                    "Priority": tc["priority"]
                } for tc in test_cases[:10]])
                st.dataframe(preview, use_container_width=True)

                if len(test_cases) > 10:
                    st.caption(f"... and {len(test_cases)-10} more rows")

                with st.expander("🔧 Selective Execution Options"):
                    priorities   = list(set(tc["priority"] for tc in test_cases))
                    sel_priority = st.multiselect(
                        "Filter by Priority:",
                        options=priorities, default=priorities
                    )
                    sel_start = st.number_input(
                        "Start from row:", min_value=1,
                        max_value=len(test_cases), value=1
                    )
                    sel_end = st.number_input(
                        "End at row:", min_value=1,
                        max_value=len(test_cases), value=len(test_cases)
                    )
                    if st.button("Apply Filters"):
                        filtered = [
                            tc for tc in test_cases
                            if tc["priority"] in sel_priority
                            and sel_start <= tc["row_number"] <= sel_end
                        ]
                        st.session_state.test_cases = filtered
                        st.success(f"Filtered to {len(filtered)} scenarios")
                        st.rerun()

                st.markdown("---")
                if st.button(
                    f"⚡ Execute All {len(st.session_state.test_cases)} Scenarios →",
                    type="primary",
                    use_container_width=True
                ):
                    st.session_state.runner_stage    = "running"
                    st.session_state.execution_paused  = False
                    st.session_state.execution_stopped = False
                    st.rerun()
            else:
                st.error(f"❌ Could not load file: {warning}")

    # ── UI BULK PROMPT BUILDER ────────────────────────────────
    with input_tab2:
        st.markdown("### 📝 Bulk Prompt Builder")
        st.caption(
            "Add test prompts row by row. "
            "Each prompt is an independent execution unit."
        )

        tcol1, tcol2, tcol3, tcol4 = st.columns(4)
        with tcol1:
            if st.button("➕ Add Row", use_container_width=True):
                rows = st.session_state.bulk_prompt_rows
                rows.append({
                    "prompt_id":        f"UI-{len(rows)+1:04d}",
                    "intent":           "",
                    "expected_outcome": "",
                    "priority":         "Medium",
                    "tags":             ""
                })
                st.session_state.bulk_prompt_rows = rows
                st.rerun()
        with tcol2:
            if st.button("🗑 Clear All", use_container_width=True):
                st.session_state.bulk_prompt_rows = [{
                    "prompt_id": "UI-0001", "intent": "",
                    "expected_outcome": "", "priority": "Medium",
                    "tags": ""
                }]
                st.rerun()
        with tcol3:
            csv_import = st.file_uploader(
                "Import CSV", type=["csv"],
                key="csv_import", label_visibility="collapsed"
            )
            if csv_import:
                try:
                    df = pd.read_csv(csv_import, dtype=str).fillna("")
                    new_rows = []
                    for i, row in df.iterrows():
                        new_rows.append({
                            "prompt_id":        row.get("prompt_id", f"UI-{i+1:04d}"),
                            "intent":           row.get("intent", row.get("prompt", "")),
                            "expected_outcome": row.get("expected_outcome", row.get("expected", "")),
                            "priority":         row.get("priority", "Medium"),
                            "tags":             row.get("tags", "")
                        })
                    if new_rows:
                        st.session_state.bulk_prompt_rows = new_rows
                        st.success(f"Imported {len(new_rows)} rows")
                        st.rerun()
                except Exception as e:
                    st.error(f"CSV import failed: {e}")
        with tcol4:
            st.caption("📤 Import CSV")

        st.markdown("---")

        rows         = st.session_state.bulk_prompt_rows
        updated_rows = []

        for i, row in enumerate(rows):
            c1, c2, c3, c4, c5 = st.columns([1, 4, 3, 1, 1])
            with c1:
                pid = st.text_input(
                    "ID", value=row.get("prompt_id", f"UI-{i+1:04d}"),
                    key=f"pid_{i}", label_visibility="collapsed"
                )
            with c2:
                intent = st.text_area(
                    "Prompt", value=row.get("intent", ""),
                    key=f"intent_{i}", height=80,
                    placeholder="e.g. Create a Contact with First Name, Last Name, Email.",
                    label_visibility="collapsed"
                )
            with c3:
                expected = st.text_area(
                    "Expected", value=row.get("expected_outcome", ""),
                    key=f"exp_{i}", height=80,
                    placeholder="e.g. Contact created with valid ID",
                    label_visibility="collapsed"
                )
            with c4:
                priority = st.selectbox(
                    "Priority",
                    ["High", "Medium", "Low", "Critical"],
                    index=["High","Medium","Low","Critical"].index(
                        row.get("priority","Medium")
                    ),
                    key=f"prio_{i}",
                    label_visibility="collapsed"
                )
            with c5:
                if st.button("🗑", key=f"del_{i}", help="Remove row"):
                    new_rows = [r for j, r in enumerate(rows) if j != i]
                    st.session_state.bulk_prompt_rows = new_rows or [{
                        "prompt_id": "UI-0001", "intent": "",
                        "expected_outcome": "", "priority": "Medium",
                        "tags": ""
                    }]
                    st.rerun()

            updated_rows.append({
                "prompt_id":        pid,
                "intent":           intent,
                "expected_outcome": expected,
                "priority":         priority,
                "tags":             row.get("tags", "")
            })

        st.session_state.bulk_prompt_rows = updated_rows
        valid_rows = [r for r in updated_rows if r.get("intent","").strip()]

        st.markdown("---")
        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("Total Rows",    len(updated_rows))
        cs2.metric("Ready to Run",  len(valid_rows))
        cs3.metric("Est. Runtime",  f"~{max(1,len(valid_rows)*30)//60} min")

        if st.button(
            f"⚡ Execute {len(valid_rows)} Prompt(s) →",
            type="primary",
            use_container_width=True,
            disabled=(len(valid_rows) == 0)
        ):
            test_cases = load_test_cases_from_bulk_prompts(valid_rows)
            st.session_state.test_cases        = test_cases
            st.session_state.input_method      = "ui_bulk"
            st.session_state.runner_stage      = "running"
            st.session_state.execution_paused  = False
            st.session_state.execution_stopped = False
            st.rerun()


# ══════════════════════════════════════════════════════════════
# STAGE 3 — EXECUTION DASHBOARD
# ══════════════════════════════════════════════════════════════
elif st.session_state.runner_stage == "running":

    meta       = st.session_state.test_plan_meta
    test_cases = st.session_state.test_cases

    if not sf:
        st.error("Salesforce not connected.")
        if st.button("← Back"):
            st.session_state.runner_stage = "input"
            st.rerun()
        st.stop()

    # Create plan + run in DB on first entry
    if not st.session_state.current_plan_id:
        plan_id = create_test_plan(
            plan_name=meta.get("plan_name"),
            description=meta.get("description",""),
            client_project=meta.get("client_project",""),
            environment=meta.get("environment",""),
            org_domain=meta.get("org_domain",""),
            run_type=meta.get("run_type","Single Run"),
            total_scenarios=len(test_cases)
        )
        run_id = create_test_run(
            plan_id=plan_id,
            plan_name=meta.get("plan_name"),
            client_project=meta.get("client_project",""),
            environment=meta.get("environment",""),
            org_domain=meta.get("org_domain",""),
            run_type=meta.get("run_type","Single Run"),
            input_method=st.session_state.input_method or "prompt",
            total_scenarios=len(test_cases),
            models_used=judge_models
        )
        st.session_state.current_plan_id = plan_id
        st.session_state.current_run_id  = run_id

    plan_id = st.session_state.current_plan_id
    run_id  = st.session_state.current_run_id

    st.markdown(f"### ⚡ Executing: **{meta.get('plan_name')}**")
    st.caption(
        f"Run ID: `{run_id}` | "
        f"{meta.get('client_project','—')} | "
        f"{meta.get('environment')} | "
        f"{meta.get('org_name','—')}"
    )

    ctrl1, ctrl2, ctrl3, _ = st.columns([1, 1, 1, 4])
    with ctrl1:
        if st.button("⏸ Pause",  use_container_width=True):
            st.session_state.execution_paused  = True
    with ctrl2:
        if st.button("▶ Resume", use_container_width=True):
            st.session_state.execution_paused  = False
    with ctrl3:
        if st.button("⏹ Stop",   use_container_width=True, type="secondary"):
            st.session_state.execution_stopped = True

    st.markdown("---")

    total = len(test_cases)
    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    total_ph = mc1.empty()
    run_ph   = mc2.empty()
    pass_ph  = mc3.empty()
    fail_ph  = mc4.empty()
    err_ph   = mc5.empty()
    prog_ph  = mc6.empty()

    progress_bar = st.progress(0)
    status_ph    = st.empty()
    eta_ph       = st.empty()

    st.markdown("### 📋 Execution Log")
    log_container = st.container()

    results      = []
    passed_count = 0
    failed_count = 0
    error_count  = 0
    run_start    = time.time()

    with log_container:
        for idx, tc in enumerate(test_cases):

            if st.session_state.execution_stopped:
                st.warning(f"⏹ Stopped at scenario {idx+1}/{total}")
                break

            pause_wait = 0
            while st.session_state.execution_paused:
                time.sleep(1)
                pause_wait += 1
                if pause_wait > 300:
                    break

            pct      = int((idx / total) * 100)
            elapsed  = time.time() - run_start
            remain   = (elapsed/max(idx,1))*(total-idx) if idx > 0 else total*30
            eta_min  = int(remain // 60)
            eta_sec  = int(remain % 60)

            progress_bar.progress(pct)
            total_ph.metric("Total",    total)
            run_ph.metric(  "Running",  idx + 1)
            pass_ph.metric( "Passed",   passed_count)
            fail_ph.metric( "Failed",   failed_count)
            err_ph.metric(  "Errors",   error_count)
            prog_ph.metric( "Progress", f"{pct}%")
            eta_ph.caption( f"⏱ ETA: {eta_min}m {eta_sec}s remaining")
            status_ph.info(
                f"🔄 Executing {idx+1}/{total}: "
                f"**{tc.get('test_name','')[:70]}**"
            )

            tc_start   = time.time()
            tc_results = run_all_tests(
                test_cases=[tc], sf=sf,
                llm_model=llm_model, judge_models=judge_models
            )
            result = tc_results[0] if tc_results else {
                "test_id":           tc.get("test_id",""),
                "test_name":         tc.get("test_name",""),
                "test_type":         tc.get("test_type","prompt"),
                "status":            "ERROR",
                "confidence":        0,
                "consensus":         "Execution failed",
                "judge_summary":     "No result returned",
                "actual_output":     "",
                "expected_output":   tc.get("expected_output",""),
                "priority":          tc.get("priority","Medium"),
                "tags":              tc.get("tags",""),
                "input_data":        tc.get("input_data",""),
                "duration_sec":      round(time.time()-tc_start, 2),
                "timestamp":         datetime.now().isoformat(),
                "individual_results": [],
                "pass_count":        0,
                "fail_count":        0,
                "error_count":       0,
                "models_used":       len(judge_models),
                "error":             "No result returned",
                "reason":            ""
            }

            result["row_number"] = tc.get("row_number", idx+1)
            results.append(result)
            save_scenario_result(run_id, plan_id, idx+1, result)

            status = result.get("status","ERROR")
            if   status == "PASS":  passed_count += 1
            elif status == "FAIL":  failed_count += 1
            else:                   error_count  += 1

            icon = {"PASS":"✅","FAIL":"❌","ERROR":"⚠️"}.get(status,"❓")
            conf = result.get("confidence", 0)

            with st.expander(
                f"{icon} [{result.get('test_id','')}] "
                f"{result.get('test_name','')[:70]} "
                f"— {status} ({conf}% confidence)",
                expanded=(status in ["FAIL","ERROR"])
            ):
                dc1, dc2, dc3 = st.columns(3)
                dc1.metric("Status",     status)
                dc2.metric("Confidence", f"{conf}%")
                dc3.metric("Duration",   f"{result.get('duration_sec',0)}s")
                st.markdown("**Judge Consensus:**")
                st.write(result.get("consensus","—"))
                st.markdown("**Judge Summary:**")
                st.write(result.get("judge_summary","—"))
                if result.get("individual_results"):
                    st.markdown("**Individual Judge Results:**")
                    for jr in result["individual_results"]:
                        j_icon = "✅" if jr.get("verdict","")=="PASS" else "❌"
                        st.caption(
                            f"{j_icon} "
                            f"{str(jr.get('model','')).split('/')[-1]}: "
                            f"{jr.get('reason','')[:120]}"
                        )
                st.markdown("**Actual Output:**")
                st.code(str(result.get("actual_output",""))[:1000], language="json")
                if result.get("error"):
                    st.error(f"Error: {result.get('error')}")

    # Execution complete
    progress_bar.progress(100)
    status_ph.empty()
    eta_ph.empty()
    total_ph.metric("Total",    total)
    run_ph.metric(  "Done",     len(results))
    pass_ph.metric( "Passed",   passed_count)
    fail_ph.metric( "Failed",   failed_count)
    err_ph.metric(  "Errors",   error_count)
    prog_ph.metric( "Progress", "100%")

    complete_test_run(run_id, results)
    st.session_state.run_results = results
    pass_rate = round(passed_count/len(results)*100, 1) if results else 0

    if passed_count == len(results):
        st.success(f"🎉 All {len(results)} scenarios PASSED ({pass_rate}%)")
    elif passed_count > 0:
        st.warning(f"⚠️ {passed_count} passed, {failed_count} failed, {error_count} errors ({pass_rate}%)")
    else:
        st.error(f"❌ All {len(results)} scenarios failed or errored")

    if st.button("📊 View Full Results & Export →", type="primary", use_container_width=True):
        st.session_state.runner_stage = "results"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# STAGE 4 — RESULTS & EXPORT
# ══════════════════════════════════════════════════════════════
elif st.session_state.runner_stage == "results":

    meta    = st.session_state.test_plan_meta
    results = st.session_state.run_results
    run_id  = st.session_state.current_run_id

    st.subheader(f"📊 Results: {meta.get('plan_name','Test Run')}")
    st.caption(
        f"Run ID: `{run_id}` | "
        f"{meta.get('client_project','—')} | "
        f"{meta.get('environment')} | "
        f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    total     = len(results)
    passed    = sum(1 for r in results if r.get("status")=="PASS")
    failed    = sum(1 for r in results if r.get("status")=="FAIL")
    errors    = sum(1 for r in results if r.get("status")=="ERROR")
    avg_conf  = round(sum(r.get("confidence",0) for r in results)/total, 1) if total else 0
    pass_rate = round(passed/total*100, 1) if total else 0

    mc1,mc2,mc3,mc4,mc5,mc6 = st.columns(6)
    mc1.metric("Total",           total)
    mc2.metric("✅ Passed",        passed)
    mc3.metric("❌ Failed",        failed)
    mc4.metric("⚠️ Errors",        errors)
    mc5.metric("Pass Rate",        f"{pass_rate}%")
    mc6.metric("Avg Confidence",   f"{avg_conf}%")
    st.markdown("---")

    st.subheader("📤 Export Options")
    exp1, exp2, exp3 = st.columns(3)

    with exp1:
        json_data = json.dumps({
            "run_id": run_id, "plan_name": meta.get("plan_name"),
            "client_project": meta.get("client_project"),
            "environment": meta.get("environment"),
            "executed_at": datetime.now().isoformat(),
            "summary": {
                "total": total, "passed": passed,
                "failed": failed, "errors": errors,
                "pass_rate": pass_rate, "avg_confidence": avg_conf
            },
            "results": results
        }, indent=2, default=str)
        st.download_button(
            "⬇️ Download Full JSON", data=json_data,
            file_name=f"test_run_{run_id}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json", use_container_width=True
        )

    with exp2:
        excel_rows = []
        for r in results:
            judges    = r.get("individual_results",[])
            judge_str = " | ".join([
                f"{str(j.get('model','')).split('/')[-1]}: {j.get('verdict','')}"
                for j in judges[:5]
            ])
            excel_rows.append({
                "Scenario ID":      r.get("test_id",""),
                "Scenario Summary": r.get("test_name",""),
                "Test Steps":       r.get("input_data","")[:500],
                "Expected Outcome": r.get("expected_output","")[:300],
                "Actual Output":    r.get("actual_output","")[:500],
                "Status":           r.get("status",""),
                "Confidence %":     r.get("confidence",0),
                "Consensus":        r.get("consensus",""),
                "Judge Summary":    r.get("judge_summary",""),
                "Judge Details":    judge_str,
                "Duration (s)":     r.get("duration_sec",0),
                "Timestamp":        r.get("timestamp",""),
                "Error":            r.get("error","")
            })
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            pd.DataFrame(excel_rows).to_excel(
                writer, index=False, sheet_name="Test Results"
            )
            for col in writer.sheets["Test Results"].columns:
                writer.sheets["Test Results"].column_dimensions[
                    col[0].column_letter
                ].width = 25
        st.download_button(
            "⬇️ Download Excel Report",
            data=excel_buf.getvalue(),
            file_name=f"test_results_{run_id}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with exp3:
        try:
            html = generate_html_report(
                results=results,
                run_name=meta.get("plan_name",""),
                org_name=meta.get("org_name",""),
                environment=meta.get("environment",""),
                client_project=meta.get("client_project","")
            )
            st.download_button(
                "⬇️ Download HTML Report", data=html,
                file_name=f"test_report_{run_id}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html", use_container_width=True
            )
        except Exception:
            st.info("HTML report unavailable")

    st.markdown("---")
    st.subheader("🔍 Detailed Scenario Results")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        filter_status = st.multiselect(
            "Filter by Status:", ["PASS","FAIL","ERROR"],
            default=["PASS","FAIL","ERROR"]
        )
    with fc2:
        filter_search = st.text_input("Search:", placeholder="Name or ID...")
    with fc3:
        sort_by = st.selectbox("Sort by:", ["Row Number","Status","Confidence","Duration"])

    filtered = [
        r for r in results
        if r.get("status","") in filter_status
        and (
            not filter_search
            or filter_search.lower() in r.get("test_name","").lower()
            or filter_search.lower() in r.get("test_id","").lower()
        )
    ]
    sort_key = {
        "Row Number": lambda x: x.get("row_number",0),
        "Status":     lambda x: x.get("status",""),
        "Confidence": lambda x: -x.get("confidence",0),
        "Duration":   lambda x: -x.get("duration_sec",0)
    }.get(sort_by, lambda x: x.get("row_number",0))
    filtered = sorted(filtered, key=sort_key)

    page_size   = 25
    total_pages = max(1, (len(filtered)+page_size-1)//page_size)
    page_num    = st.number_input(
        f"Page (1–{total_pages}):", min_value=1,
        max_value=total_pages, value=1
    ) if total_pages > 1 else 1

    st.caption(f"Showing {len(filtered)} of {total} scenarios")

    for r in filtered[(page_num-1)*page_size : page_num*page_size]:
        status     = r.get("status","ERROR")
        icon       = {"PASS":"✅","FAIL":"❌","ERROR":"⚠️"}.get(status,"❓")
        conf       = r.get("confidence",0)

        with st.expander(
            f"{icon} [{r.get('test_id','')}] "
            f"{r.get('test_name','')[:70]} "
            f"— {status} | {conf}% | {r.get('duration_sec',0)}s",
            expanded=False
        ):
            tab_a, tab_b, tab_c, tab_d = st.tabs([
                "📋 Summary", "🧠 Judge Results",
                "📤 Actual Output", "🔎 Test Details"
            ])
            with tab_a:
                ac1,ac2,ac3,ac4 = st.columns(4)
                ac1.metric("Status",     status)
                ac2.metric("Confidence", f"{conf}%")
                ac3.metric("Pass Votes", r.get("pass_count",0))
                ac4.metric("Fail Votes", r.get("fail_count",0))
                st.markdown("**Consensus:**")
                st.write(r.get("consensus","—"))
                st.markdown("**Judge Summary:**")
                st.write(r.get("judge_summary","—"))
                if r.get("error"):
                    st.error(f"Error: {r.get('error')}")
            with tab_b:
                judges = r.get("individual_results",[])
                if judges:
                    for j in judges:
                        j_icon = "✅" if j.get("verdict")=="PASS" else "❌"
                        st.markdown(
                            f"{j_icon} **{str(j.get('model','')).split('/')[-1]}** "
                            f"— {j.get('verdict','')}"
                        )
                        st.caption(j.get("reason","")[:200])
                else:
                    st.info("No individual judge results")
            with tab_c:
                st.markdown("**Expected:**")
                st.info(r.get("expected_output","—")[:500])
                st.markdown("**Actual:**")
                try:
                    st.json(json.loads(r.get("actual_output","")))
                except Exception:
                    st.code(str(r.get("actual_output",""))[:2000])
            with tab_d:
                st.code(r.get("test_id",""))
                st.write(r.get("input_data","")[:500])
                st.caption(
                    f"Priority: {r.get('priority','—')} | "
                    f"Tags: {r.get('tags','—')} | "
                    f"Timestamp: {r.get('timestamp','—')}"
                )

    st.markdown("---")
    act1, act2, act3 = st.columns(3)
    with act1:
        if st.button("🔄 Re-run Failed Only", use_container_width=True):
            failed_cases = [
                next((tc for tc in st.session_state.test_cases
                      if tc["test_id"] == r["test_id"]), None)
                for r in results if r.get("status") in ["FAIL","ERROR"]
            ]
            failed_cases = [tc for tc in failed_cases if tc]
            if failed_cases:
                st.session_state.test_cases      = failed_cases
                st.session_state.current_plan_id = None
                st.session_state.current_run_id  = None
                st.session_state.runner_stage    = "running"
                st.rerun()
            else:
                st.success("No failures to re-run!")
    with act2:
        if st.button("📋 New Test Run (Same Plan)", use_container_width=True):
            st.session_state.current_plan_id = None
            st.session_state.current_run_id  = None
            st.session_state.run_results     = []
            st.session_state.runner_stage    = "input"
            st.rerun()
    with act3:
        if st.button("🆕 New Test Plan", type="primary", use_container_width=True):
            for k in ["test_plan_meta","test_cases","run_results",
                      "current_run_id","current_plan_id","input_method"]:
                st.session_state[k] = (
                    {} if k == "test_plan_meta" else
                    [] if k in ["test_cases","run_results"] else None
                )
            st.session_state.bulk_prompt_rows = [{
                "prompt_id": "UI-0001", "intent": "",
                "expected_outcome": "", "priority": "Medium", "tags": ""
            }]
            st.session_state.runner_stage = "metadata"
            st.rerun()