"""
test_reporting_engine.py — Test Reporting Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • Professional PDF reports
  • Excel workbooks with multiple sheets
  • Interactive HTML reports
  • Charts and visualizations
  • Summary and detailed sections
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

# Optional imports
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

class TestReportingEngine:
    """Generates professional test reports in multiple formats."""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(
        self,
        test_results: List[Dict],
        kpis: Dict,
        metadata: Optional[Dict] = None
    ) -> str:
        """Generate interactive HTML report."""
        
        # Build HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {metadata.get('run_id', 'Unknown') if metadata else 'Unknown'}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .summary {{ background: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .kpi-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Test Execution Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Run ID:</strong> {metadata.get('run_id', 'N/A') if metadata else 'N/A'}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Tests:</strong> {len(test_results)}</p>
    </div>
    
    <h2>Key Performance Indicators</h2>
    <div class="kpi-grid">
        <div class="kpi-card">
            <div>Pass Rate</div>
            <div class="kpi-value">{kpis.get('pass_rate', 0)}%</div>
        </div>
        <div class="kpi-card">
            <div>Avg Confidence</div>
            <div class="kpi-value">{kpis.get('average_confidence', 0)}</div>
        </div>
        <div class="kpi-card">
            <div>Avg Duration</div>
            <div class="kpi-value">{kpis.get('average_duration', 0)}s</div>
        </div>
        <div class="kpi-card">
            <div>Total Tests</div>
            <div class="kpi-value">{kpis.get('total_tests', 0)}</div>
        </div>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>#</th>
            <th>Test Name</th>
            <th>Status</th>
            <th>Confidence</th>
            <th>Duration</th>
        </tr>
"""
        
        for i, result in enumerate(test_results[:100]):  # Limit to 100 for HTML
            status_class = "pass" if result.get("status") == "PASS" else "fail"
            html_content += f"""
        <tr>
            <td>{i+1}</td>
            <td>{result.get('test_name', 'Test ' + str(i+1))}</td>
            <td class="{status_class}">{result.get('status', 'N/A')}</td>
            <td>{result.get('confidence', 0)}%</td>
            <td>{result.get('duration_sec', 0):.2f}s</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        # Save HTML
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        return filepath
    
    def generate_pdf_report(
        self,
        test_results: List[Dict],
        kpis: Dict,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Generate PDF report from HTML."""
        
        if not WEASYPRINT_AVAILABLE:
            return None
        
        # First generate HTML
        html_path = self.generate_html_report(test_results, kpis, metadata)
        
        # Convert to PDF
        pdf_filename = html_path.replace('.html', '.pdf')
        
        try:
            HTML(html_path).write_pdf(pdf_filename)
            return pdf_filename
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return None
    
    def generate_excel_report(
        self,
        test_results: List[Dict],
        kpis: Dict,
        metadata: Optional[Dict] = None
    ) -> str:
        """Generate Excel workbook with multiple sheets."""
        
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Sheet 1: Summary
            summary_data = {
                'Metric': ['Total Tests', 'Passed', 'Failed', 'Errors', 'Pass Rate', 'Avg Confidence'],
                'Value': [
                    kpis.get('total_tests', 0),
                    kpis.get('tests_passed', 0),
                    kpis.get('tests_failed', 0),
                    kpis.get('tests_error', 0),
                    f"{kpis.get('pass_rate', 0)}%",
                    kpis.get('average_confidence', 0)
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: All KPIs
            kpi_data = {
                'KPI': list(kpis.keys()),
                'Value': list(kpis.values())
            }
            pd.DataFrame(kpi_data).to_excel(writer, sheet_name='KPIs', index=False)
            
            # Sheet 3: Detailed Results
            df = pd.DataFrame(test_results)
            if not df.empty:
                # Select relevant columns
                cols = ['test_name', 'status', 'confidence', 'duration_sec', 'expected_output', 'actual_output']
                available_cols = [c for c in cols if c in df.columns]
                df[available_cols].to_excel(writer, sheet_name='Test Results', index=False)
        
        return filepath


# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def generate_report(
    test_results: List[Dict],
    kpis: Dict,
    format: str = "html",
    metadata: Optional[Dict] = None
) -> str:
    """
    Quick report generation.
    
    Usage:
        report_path = generate_report(
            test_results=results,
            kpis=kpis,
            format="pdf",
            metadata={"run_id": "RUN-001"}
        )
    """
    engine = TestReportingEngine()
    
    if format == "html":
        return engine.generate_html_report(test_results, kpis, metadata)
    elif format == "pdf":
        return engine.generate_pdf_report(test_results, kpis, metadata)
    elif format == "excel":
        return engine.generate_excel_report(test_results, kpis, metadata)
    else:
        raise ValueError(f"Unsupported format: {format}")