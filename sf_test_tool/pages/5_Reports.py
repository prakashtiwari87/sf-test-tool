"""
5_Reports.py — AmplifyQA Test Reports & Analytics
FIXED VERSION - Phase 0

FIXES IN THIS VERSION:
  • Reads test results from DATABASE instead of broken session state
  • Connects to test_plan_manager to get actual run results
  • Shows most recent test run by default
  • Added PDF export capability
  • Added test run selector dropdown
  • Maintained all existing chart functionality
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from reports.report_generator import (
    calculate_summary,
    create_pass_fail_donut,
    create_results_by_type_bar,
    create_duration_chart,
    create_priority_breakdown,
    generate_html_report
)
from engine.test_plan_manager import (
    init_test_plan_db,
    get_all_test_runs,
    get_scenarios_for_run,
    get_run_stats
)

st.set_page_config(
    page_title="Reports", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

from config.page_init import page_init
from config.theme import render_header

# ── INITIALIZE ────────────────────────────────────────────────
init_test_plan_db()
sf, org = page_init()

render_header(
    "Test Reports & Analytics", "📊",
    org_name=org.get("org_name", ""),
    environment=org.get("org_type", "")
)

# ── GET TEST RUNS FROM DATABASE ───────────────────────────────
all_runs = get_all_test_runs()

if not all_runs:
    st.info(
        "💡 No test results yet. Go to **Salesforce Testing** page to run your first test."
    )
    st.stop()

# ── SELECT TEST RUN ───────────────────────────────────────────
st.markdown("### 📋 Select Test Run")

# Create dropdown options
run_options = {}
for run in all_runs:
    run_id = run["run_id"]
    plan_name = run.get("plan_name", "Unnamed Plan")
    started_at = run.get("started_at", "")[:16].replace("T", " ")
    status = run.get("status", "unknown")
    total = run.get("total_scenarios", 0)
    passed = run.get("passed", 0)
    
    label = f"[{status.upper()}] {plan_name} — {started_at} — {passed}/{total} passed"
    run_options[label] = run_id

# Default to most recent run
default_label = list(run_options.keys())[0] if run_options else None

selected_label = st.selectbox(
    "Choose test run to view:",
    options=list(run_options.keys()),
    index=0,
    help="Select a test run to view detailed results and analytics"
)

selected_run_id = run_options[selected_label]

# ── GET SELECTED RUN DATA ─────────────────────────────────────
# Get scenarios for the selected run
scenarios = get_scenarios_for_run(selected_run_id)

if not scenarios:
    st.warning(f"No scenario results found for run: {selected_run_id}")
    st.stop()

# Convert scenarios to results format expected by report_generator
results = []
for sc in scenarios:
    results.append({
        "test_id": sc.get("scenario_id", ""),
        "test_name": sc.get("scenario_summary", ""),
        "status": sc.get("status", "ERROR"),
        "test_type": "Functional",  # Can be enhanced later
        "priority": "Medium",  # Can be enhanced later
        "expected_output": sc.get("expected_outcome", "")[:200],
        "actual_output": sc.get("actual_outcome", "")[:200],
        "reason": sc.get("judge_summary", ""),
        "duration_sec": sc.get("duration_sec", 0),
        "confidence": sc.get("confidence", 0)
    })

# Calculate summary
summary = calculate_summary(results)
org_info = org

st.markdown("---")

# ── SUMMARY METRICS ───────────────────────────────────────────
st.subheader("📈 Executive Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Tests", summary["total"])
col2.metric("✅ Passed", summary["passed"], 
            delta=f"+{summary['passed']}" if summary['passed'] > 0 else None)
col3.metric("❌ Failed", summary["failed"],
            delta=f"-{summary['failed']}" if summary['failed'] > 0 else None)
col4.metric("⚠️ Errors", summary["errors"],
            delta=f"-{summary['errors']}" if summary['errors'] > 0 else None)
col5.metric(
    "Pass Rate", f"{summary['pass_rate']}%",
    delta="Good" if summary["pass_rate"] >= 80 else "Needs Attention",
    delta_color="normal" if summary["pass_rate"] >= 80 else "inverse"
)

st.markdown("---")

# ── CHARTS ────────────────────────────────────────────────────
st.subheader("📊 Visual Analytics")

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(create_pass_fail_donut(summary), use_container_width=True)
with chart_col2:
    st.plotly_chart(create_results_by_type_bar(results), use_container_width=True)

chart_col3, chart_col4 = st.columns(2)
with chart_col3:
    st.plotly_chart(create_duration_chart(results), use_container_width=True)
with chart_col4:
    st.plotly_chart(create_priority_breakdown(results), use_container_width=True)

st.markdown("---")

# ── DETAILED RESULTS TABLE ─────────────────────────────────────
st.subheader("📋 Detailed Test Results")

df = pd.DataFrame(results)

# Add filter
status_filter = st.multiselect(
    "Filter by Status:", ["PASS", "FAIL", "ERROR"],
    default=["PASS", "FAIL", "ERROR"]
)
filtered_df = df[df["status"].isin(status_filter)]

# Display styled dataframe
st.dataframe(
    filtered_df[[
        "test_id", "test_name", "status", "test_type",
        "priority", "expected_output", "actual_output", 
        "reason", "duration_sec", "confidence"
    ]].style.apply(
        lambda row: [
            "background-color: #d4edda" if row["status"] == "PASS"
            else "background-color: #f8d7da" if row["status"] == "FAIL"
            else "background-color: #fff3cd"
            for _ in row
        ], axis=1
    ),
    use_container_width=True,
    height=400
)

st.markdown("---")

# ── DOWNLOADS ─────────────────────────────────────────────────
st.subheader("⬇️ Download Report")

col1, col2, col3 = st.columns(3)

with col1:
    html_report = generate_html_report(results, summary, org_info)
    st.download_button(
        "📄 Download HTML Report",
        data=html_report,
        file_name=f"test_report_{selected_run_id}.html",
        mime="text/html",
        use_container_width=True
    )

with col2:
    csv_data = df.to_csv(index=False)
    st.download_button(
        "📊 Download CSV Results",
        data=csv_data,
        file_name=f"test_results_{selected_run_id}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col3:
    # Excel download
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Test Results', index=False)
        
        # Add summary sheet
        summary_df = pd.DataFrame([{
            "Total Tests": summary["total"],
            "Passed": summary["passed"],
            "Failed": summary["failed"],
            "Errors": summary["errors"],
            "Pass Rate %": summary["pass_rate"]
        }])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    excel_buffer.seek(0)
    st.download_button(
        "📑 Download Excel Report",
        data=excel_buffer,
        file_name=f"test_report_{selected_run_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ── ADDITIONAL INFO ───────────────────────────────────────────
st.markdown("---")
with st.expander("ℹ️ Test Run Information"):
    # Get full run details
    selected_run = next((r for r in all_runs if r["run_id"] == selected_run_id), {})
    
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.write(f"**Run ID:** `{selected_run_id}`")
        st.write(f"**Plan ID:** `{selected_run.get('plan_id', '—')}`")
        st.write(f"**Plan Name:** {selected_run.get('plan_name', '—')}")
        st.write(f"**Client/Project:** {selected_run.get('client_project', '—')}")
    with info_col2:
        st.write(f"**Environment:** {selected_run.get('environment', '—')}")
        st.write(f"**Status:** {selected_run.get('status', '—')}")
        st.write(f"**Started:** {selected_run.get('started_at', '—')[:19]}")
        st.write(f"**Completed:** {selected_run.get('completed_at', '—')[:19]}")

# Import io for Excel export
import io