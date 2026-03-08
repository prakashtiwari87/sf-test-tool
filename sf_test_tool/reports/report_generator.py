import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
from io import BytesIO


def calculate_summary(results: list) -> dict:
    """Calculate high-level test run statistics"""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    errors = sum(1 for r in results if r.get("status") == "ERROR")
    unknown = total - passed - failed - errors

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "unknown": unknown,
        "pass_rate": round((passed / total) * 100, 1) if total > 0 else 0,
        "avg_duration": round(
            sum(r.get("duration_sec", 0) for r in results) / total, 2
        ) if total > 0 else 0
    }


def create_pass_fail_donut(summary: dict):
    """Create a donut chart showing Pass/Fail/Error breakdown"""
    labels = ["PASS", "FAIL", "ERROR"]
    values = [summary["passed"], summary["failed"], summary["errors"]]
    colors = ["#2ECC71", "#E74C3C", "#F39C12"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(colors=colors),
        textinfo="label+percent+value",
        textfont=dict(size=14)
    )])

    fig.update_layout(
        title=dict(text="Test Results Overview", font=dict(size=18)),
        showlegend=True,
        height=400
    )
    return fig


def create_results_by_type_bar(results: list):
    """Create a bar chart showing Pass/Fail by test type"""
    df = pd.DataFrame(results)
    if df.empty:
        return go.Figure()

    summary = df.groupby(["test_type", "status"]).size().reset_index(name="count")

    fig = px.bar(
        summary,
        x="test_type",
        y="count",
        color="status",
        barmode="group",
        color_discrete_map={"PASS": "#2ECC71", "FAIL": "#E74C3C", "ERROR": "#F39C12"},
        title="Results by Test Type",
        labels={"test_type": "Test Type", "count": "Number of Tests", "status": "Status"}
    )
    fig.update_layout(height=400)
    return fig


def create_duration_chart(results: list):
    """Show test execution duration per test"""
    df = pd.DataFrame(results)
    if df.empty:
        return go.Figure()

    colors = [
        "#2ECC71" if s == "PASS" else "#E74C3C" if s == "FAIL" else "#F39C12"
        for s in df["status"]
    ]

    fig = go.Figure(data=[go.Bar(
        x=df["test_id"],
        y=df["duration_sec"],
        marker_color=colors,
        text=df["status"],
        textposition="auto"
    )])
    fig.update_layout(
        title="Test Execution Duration (seconds)",
        xaxis_title="Test ID",
        yaxis_title="Duration (sec)",
        height=350
    )
    return fig


def create_priority_breakdown(results: list):
    """Pie chart of test results by priority"""
    df = pd.DataFrame(results)
    if df.empty:
        return go.Figure()

    priority_pass = df[df["status"] == "PASS"].groupby("priority").size().reset_index(name="passed")
    priority_fail = df[df["status"] != "PASS"].groupby("priority").size().reset_index(name="failed")

    merged = pd.merge(priority_pass, priority_fail, on="priority", how="outer").fillna(0)

    fig = px.sunburst(
        df,
        path=["priority", "status"],
        title="Results by Priority Level",
        color="status",
        color_discrete_map={"PASS": "#2ECC71", "FAIL": "#E74C3C", "ERROR": "#F39C12"}
    )
    fig.update_layout(height=400)
    return fig


def generate_html_report(results: list, summary: dict, org_info: dict = None) -> str:
    """Generate a complete standalone HTML test report"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows_html = ""
    for r in results:
        status = r.get("status", "UNKNOWN")
        color = "#2ECC71" if status == "PASS" else "#E74C3C" if status == "FAIL" else "#F39C12"
        rows_html += f"""
        <tr>
            <td>{r.get('test_id','')}</td>
            <td>{r.get('test_name','')}</td>
            <td><span style="color:{color};font-weight:bold">{status}</span></td>
            <td>{r.get('test_type','')}</td>
            <td>{r.get('priority','')}</td>
            <td style="font-size:12px">{r.get('expected_output','')[:100]}</td>
            <td style="font-size:12px">{r.get('actual_output','')[:100]}</td>
            <td style="font-size:12px;color:#666">{r.get('reason','')}</td>
            <td>{r.get('duration_sec','')}s</td>
        </tr>"""

    org_name = org_info.get("org_name", "N/A") if org_info else "N/A"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Salesforce Test Automation Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background: #f4f6f9; }}
        .header {{ background: linear-gradient(135deg, #1565C0, #0288D1);
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 5px 0; opacity: 0.9; }}
        .summary-cards {{ display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; flex: 1;
                 min-width: 150px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .card .number {{ font-size: 36px; font-weight: bold; margin: 5px 0; }}
        .card .label {{ font-size: 13px; color: #666; }}
        .pass {{ color: #2ECC71; }}
        .fail {{ color: #E74C3C; }}
        .error {{ color: #F39C12; }}
        .total {{ color: #1565C0; }}
        table {{ width: 100%; border-collapse: collapse; background: white;
                 border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th {{ background: #1565C0; color: white; padding: 12px; text-align: left; font-size: 13px; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 13px; vertical-align: top; }}
        tr:hover {{ background: #f9f9f9; }}
        .section-title {{ font-size: 20px; font-weight: bold; color: #1565C0;
                           margin: 25px 0 10px 0; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Salesforce AI Test Automation Report</h1>
        <p>Generated: {now} | Org: {org_name}</p>
    </div>

    <div class="summary-cards">
        <div class="card">
            <div class="number total">{summary['total']}</div>
            <div class="label">Total Tests</div>
        </div>
        <div class="card">
            <div class="number pass">{summary['passed']}</div>
            <div class="label">Passed</div>
        </div>
        <div class="card">
            <div class="number fail">{summary['failed']}</div>
            <div class="label">Failed</div>
        </div>
        <div class="card">
            <div class="number error">{summary['errors']}</div>
            <div class="label">Errors</div>
        </div>
        <div class="card">
            <div class="number {'pass' if summary['pass_rate'] >= 80 else 'fail'}">{summary['pass_rate']}%</div>
            <div class="label">Pass Rate</div>
        </div>
        <div class="card">
            <div class="number total">{summary['avg_duration']}s</div>
            <div class="label">Avg Duration</div>
        </div>
    </div>

    <div class="section-title">📋 Detailed Test Results</div>
    <table>
        <thead>
            <tr>
                <th>Test ID</th><th>Test Name</th><th>Status</th><th>Type</th>
                <th>Priority</th><th>Expected</th><th>Actual</th>
                <th>LLM Reason</th><th>Duration</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>

    <div class="footer">
        Generated by Salesforce AI Test Automation Tool | Powered by LLM-as-Judge
    </div>
</body>
</html>"""

    return html


def save_results_to_json(results: list, filename: str = None) -> str:
    """Save test results as JSON for history tracking"""
    import os
    if not filename:
        results_dir = os.path.join(
            os.path.dirname(__file__), "..", "test_cases", "results"
        )
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = os.path.join(results_dir, f"test_run_{timestamp}.json")
    payload = {
        "run_timestamp": datetime.now().isoformat(),
        "summary":       calculate_summary(results),
        "results":       results
    }
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return filename

    return filename