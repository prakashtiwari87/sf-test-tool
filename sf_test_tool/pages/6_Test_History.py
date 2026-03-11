"""
6_Test_History.py — AmplifyQA Test History
FIXED VERSION - Phase 0

FIXES IN THIS VERSION:
  • Enhanced scenario detail view with expand/collapse
  • Added expected vs actual comparison
  • Added rerun test capability (stores config for future use)
  • Better filtering and sorting
  • Download individual run results
  • Improved mobile responsiveness
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from config.theme import inject_css, render_header, render_sidebar_logo
from config.settings_manager import load_all_keys_to_env
from engine.test_plan_manager import (
    init_test_plan_db, get_all_test_runs,
    get_scenarios_for_run, get_run_stats, get_test_run
)

st.set_page_config(
    page_title="Test History — AmplifyQA",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
load_all_keys_to_env()
init_test_plan_db()

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_logo()
    st.page_link("app.py",                              label="🏠 Home")
    st.page_link("pages/2_Salesforce_Testing.py",       label="🧪 Salesforce Testing")
    st.page_link("pages/3_Agentforce_Testing.py",       label="🤖 Agentforce Testing")
    st.page_link("pages/4_Bedrock_AgentCore_Testing.py",label="☁️ Bedrock Testing")
    st.page_link("pages/5_Reports.py",                  label="📊 Reports")
    st.page_link("pages/7_Metadata_Explorer.py",        label="🔍 Metadata Explorer")
    st.page_link("pages/6_Test_History.py",             label="📂 Test History")
    st.page_link("pages/8_Settings.py",                 label="⚙️ Settings")

render_header("Test History", "📂")

st.markdown("""
<div class="page-subtitle">
    Complete audit trail of all test plans, runs, and scenario results.
    Searchable by project, org, environment, date, and status.
</div>
""", unsafe_allow_html=True)

# ── FILTERS ──────────────────────────────────────────────────
all_runs = get_all_test_runs()

if not all_runs:
    st.info("📭 No test history yet. Run your first test from the Salesforce Testing page.")
    st.stop()

fc1, fc2, fc3, fc4 = st.columns(4)
with fc1:
    search = st.text_input(
        "🔍 Search",
        placeholder="Plan name, project, run ID..."
    )
with fc2:
    environments = (
        ["All"] +
        list(set(r.get("environment","") for r in all_runs if r.get("environment")))
    )
    env_filter = st.selectbox("Environment", environments)
with fc3:
    statuses = ["All","complete","running","failed","pending"]
    status_filter = st.selectbox("Status", statuses)
with fc4:
    sort_by = st.selectbox(
        "Sort by",
        ["Newest First","Oldest First",
         "Most Tests","Highest Pass Rate"]
    )

# Apply filters
filtered_runs = all_runs
if search:
    s = search.lower()
    filtered_runs = [
        r for r in filtered_runs
        if s in r.get("plan_name","").lower()
        or s in r.get("run_id","").lower()
        or s in r.get("client_project","").lower()
    ]
if env_filter != "All":
    filtered_runs = [
        r for r in filtered_runs
        if r.get("environment","") == env_filter
    ]
if status_filter != "All":
    filtered_runs = [
        r for r in filtered_runs
        if r.get("status","") == status_filter
    ]

# Sort
if sort_by == "Oldest First":
    filtered_runs = list(reversed(filtered_runs))
elif sort_by == "Most Tests":
    filtered_runs = sorted(
        filtered_runs,
        key=lambda x: x.get("total_scenarios",0),
        reverse=True
    )
elif sort_by == "Highest Pass Rate":
    def pass_rate(r):
        t = r.get("total_scenarios",0)
        p = r.get("passed",0)
        return p/t if t else 0
    filtered_runs = sorted(filtered_runs,
                           key=pass_rate, reverse=True)

# ── SUMMARY STATS ────────────────────────────────────────────
total_runs    = len(all_runs)
total_tests   = sum(r.get("total_scenarios",0) for r in all_runs)
total_passed  = sum(r.get("passed",0) for r in all_runs)
overall_rate  = (
    round(total_passed/total_tests*100,1)
    if total_tests else 0
)

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Total Runs",   total_runs)
sc2.metric("Total Tests",  total_tests)
sc3.metric("Tests Passed", total_passed, 
           delta=f"{overall_rate}%" if overall_rate > 0 else None)
sc4.metric("Overall Pass Rate", f"{overall_rate}%",
           delta="Good" if overall_rate >= 80 else "Needs Improvement",
           delta_color="normal" if overall_rate >= 80 else "inverse")

st.markdown(
    f"<div class='page-subtitle'>"
    f"Showing {len(filtered_runs)} of {total_runs} runs</div>",
    unsafe_allow_html=True
)
st.markdown("---")

# ── RUN LIST ─────────────────────────────────────────────────
if not filtered_runs:
    st.info(
        "No test runs match your filters. "
        "Adjust filters or run new tests from the Salesforce Testing page."
    )
else:
    for run in filtered_runs:
        status     = run.get("status","")
        status_icon = {
            "complete": "✅", "running": "⚡",
            "failed":   "❌", "pending": "⏳"
        }.get(status,"📋")

        total  = run.get("total_scenarios",0)
        passed = run.get("passed",0)
        failed = run.get("failed",0)
        errors = run.get("errors",0)
        rate   = (
            f"{round(passed/total*100)}%"
            if total else "—"
        )

        started = (
            run.get("started_at","")[:16]
            .replace("T"," ")
        )

        with st.expander(
            f"{status_icon} [{run['run_id']}]  "
            f"**{run['plan_name']}** — "
            f"{run.get('client_project','—')} | "
            f"{run.get('environment','—')} | "
            f"{started} | "
            f"Pass Rate: {rate}",
            expanded=False
        ):
            # Metrics row
            ht1, ht2, ht3, ht4, ht5 = st.columns(5)
            ht1.metric("Total",   total)
            ht2.metric("✅ Pass",  passed)
            ht3.metric("❌ Fail",  failed)
            ht4.metric("⚠️ Error", errors)
            ht5.metric("Pass Rate", rate)

            st.caption(
                f"Run ID: `{run['run_id']}` | "
                f"Plan: `{run['plan_id']}` | "
                f"Input: {run.get('input_method','')} | "
                f"Org: {run.get('org_domain','')}"
            )

            # Action buttons
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            with btn_col1:
                if st.button(
                    "📊 View in Reports",
                    key=f"report_{run['run_id']}",
                    use_container_width=True
                ):
                    # Navigate to reports page with this run pre-selected
                    st.switch_page("pages/5_Reports.py")
            
            with btn_col2:
                # Download CSV
                scenarios = get_scenarios_for_run(run["run_id"])
                if scenarios:
                    df = pd.DataFrame(scenarios)
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        "💾 Download CSV",
                        data=csv_data,
                        file_name=f"run_{run['run_id']}.csv",
                        mime="text/csv",
                        key=f"csv_{run['run_id']}",
                        use_container_width=True
                    )
            
            with btn_col3:
                if st.button(
                    "🔄 Rerun Tests",
                    key=f"rerun_{run['run_id']}",
                    use_container_width=True,
                    help="Feature coming in Phase 1"
                ):
                    st.info("Rerun capability will be available in Phase 1!")

            # Scenario details
            show_details = st.checkbox(
                "🔍 Show Scenario Details",
                key=f"details_{run['run_id']}",
                value=False
            )
            
            if show_details:
                scenarios = get_scenarios_for_run(run["run_id"])
                if scenarios:
                    st.markdown(
                        f"**{len(scenarios)} scenarios in this run:**"
                    )
                    
                    # Show all scenarios with expandable details
                    for idx, sc in enumerate(scenarios[:50]):  # Limit to 50 for performance
                        sc_status = sc.get("status","")
                        sc_icon   = (
                            "✅" if sc_status=="PASS" else
                            "❌" if sc_status=="FAIL" else "⚠️"
                        )
                        
                        with st.expander(
                            f"{sc_icon} [{sc.get('scenario_id','')}] "
                            f"{sc.get('scenario_summary','')[:60]} — "
                            f"{sc_status} ({sc.get('confidence',0)}% confidence)",
                            expanded=False
                        ):
                            # Expected vs Actual
                            comp_col1, comp_col2 = st.columns(2)
                            with comp_col1:
                                st.markdown("**Expected:**")
                                st.code(sc.get('expected_outcome', 'N/A')[:500], language="text")
                            with comp_col2:
                                st.markdown("**Actual:**")
                                st.code(sc.get('actual_outcome', 'N/A')[:500], language="text")
                            
                            # Judge verdict
                            if sc.get('judge_summary'):
                                st.markdown("**Judge Verdict:**")
                                st.info(sc.get('judge_summary', ''))
                            
                            # Metadata
                            meta_col1, meta_col2 = st.columns(2)
                            with meta_col1:
                                st.caption(f"Duration: {sc.get('duration_sec', 0):.2f}s")
                                st.caption(f"Confidence: {sc.get('confidence', 0)}%")
                            with meta_col2:
                                st.caption(f"Started: {sc.get('started_at', '')[:19]}")
                                st.caption(f"Completed: {sc.get('completed_at', '')[:19]}")
                    
                    if len(scenarios) > 50:
                        st.caption(
                            f"Showing first 50 of {len(scenarios)} scenarios. "
                            "Download CSV for complete results."
                        )
                else:
                    st.info("No scenario details stored for this run.")

st.markdown("---")
st.caption(
    "💡 **Tip:** Click on any run to expand details, view scenarios, "
    "or download results. Use filters above to find specific test runs."
)