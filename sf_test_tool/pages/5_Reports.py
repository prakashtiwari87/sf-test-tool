import streamlit as st
import pandas as pd
from reports.report_generator import (
    calculate_summary,
    create_pass_fail_donut,
    create_results_by_type_bar,
    create_duration_chart,
    create_priority_breakdown,
    generate_html_report
)

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide", initial_sidebar_state = "collapsed")
st.title("📊 Test Reports & Analytics")
from config.page_init import page_init
sf, org = page_init()

if not st.session_state.get("test_results"):
    st.info("💡 No test results yet. Go to **▶️ Test Runner** to run your tests first.")
    st.stop()

results = st.session_state.test_results
summary = calculate_summary(results)
org_info = st.session_state.get("sf_org_info", {})

# ── SUMMARY METRICS ───────────────────────────────────────────
st.subheader("📈 Executive Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Tests",    summary["total"])
col2.metric("✅ Passed",       summary["passed"])
col3.metric("❌ Failed",       summary["failed"])
col4.metric("⚠️ Errors",       summary["errors"])
col5.metric("Pass Rate",      f"{summary['pass_rate']}%",
            delta="Good" if summary["pass_rate"] >= 80 else "Needs Attention")

st.markdown("---")

# ── CHARTS ────────────────────────────────────────────────────
st.subheader("📊 Visual Analytics")

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(create_pass_fail_donut(summary),     use_container_width=True)
with chart_col2:
    st.plotly_chart(create_results_by_type_bar(results), use_container_width=True)

chart_col3, chart_col4 = st.columns(2)
with chart_col3:
    st.plotly_chart(create_duration_chart(results),      use_container_width=True)
with chart_col4:
    st.plotly_chart(create_priority_breakdown(results),  use_container_width=True)

st.markdown("---")

# ── DETAILED RESULTS TABLE ─────────────────────────────────────
st.subheader("📋 Detailed Test Results")

df = pd.DataFrame(results)

status_filter = st.multiselect(
    "Filter by Status:", ["PASS", "FAIL", "ERROR"],
    default=["PASS", "FAIL", "ERROR"]
)
filtered_df = df[df["status"].isin(status_filter)]

st.dataframe(
    filtered_df[[
        "test_id", "test_name", "status", "test_type",
        "priority", "expected_output", "actual_output", "reason", "duration_sec"
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

col1, col2 = st.columns(2)

with col1:
    html_report = generate_html_report(results, summary, org_info)
    st.download_button(
        "📄 Download HTML Report",
        data=html_report,
        file_name="salesforce_test_report.html",
        mime="text/html",
        use_container_width=True
    )

with col2:
    csv_data = df.to_csv(index=False)
    st.download_button(
        "📊 Download CSV Results",
        data=csv_data,
        file_name="test_results.csv",
        mime="text/csv",
        use_container_width=True
    )