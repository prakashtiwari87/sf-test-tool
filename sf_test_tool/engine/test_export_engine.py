"""
test_export_engine.py — Test Export Engine
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Export to Excel (.xlsx)
  • Export to CSV (.csv)
  • Export to PDF (.pdf)
  • Formatted test results
  • Summary sheets
  • Detailed results
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import io

class TestExportEngine:
    """
    Exports test results to various formats.
    """
    
    def __init__(self):
        """Initialize export engine."""
        pass
    
    # ══════════════════════════════════════════════════════════
    # EXCEL EXPORT
    # ══════════════════════════════════════════════════════════
    
    def export_to_excel(
        self,
        test_scripts: List[Dict],
        test_results: Optional[List[Dict]] = None,
        execution_summary: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Export test scripts and results to Excel.
        
        Args:
            test_scripts: List of test script dictionaries
            test_results: Optional list of test results
            execution_summary: Optional execution summary
            output_path: Optional file path to save
        
        Returns:
            Excel file as bytes
        """
        # Create Excel writer
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Test Scripts
            scripts_df = self._scripts_to_dataframe(test_scripts, test_results)
            scripts_df.to_excel(writer, sheet_name='Test Scripts', index=False)
            
            # Sheet 2: Summary (if execution summary provided)
            if execution_summary:
                summary_df = self._summary_to_dataframe(execution_summary)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 3: Detailed Results (if results provided)
            if test_results:
                results_df = self._results_to_dataframe(test_results)
                results_df.to_excel(writer, sheet_name='Detailed Results', index=False)
            
            # Format worksheets
            self._format_excel_worksheets(writer)
        
        output.seek(0)
        excel_bytes = output.read()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(excel_bytes)
        
        return excel_bytes
    
    def _scripts_to_dataframe(
        self,
        test_scripts: List[Dict],
        test_results: Optional[List[Dict]] = None
    ) -> pd.DataFrame:
        """Convert test scripts to DataFrame."""
        
        # Create results lookup if provided
        results_lookup = {}
        if test_results:
            results_lookup = {
                r.get('script_id'): r for r in test_results
            }
        
        rows = []
        for script in test_scripts:
            script_id = script.get('script_id')
            result = results_lookup.get(script_id, {})
            
            row = {
                'Script ID': script_id,
                'Test Type': script.get('test_type'),
                'Persona': script.get('persona'),
                'User Utterance': script.get('utterance'),
                'Expected Intent': script.get('expected_intent'),
                'Expected Response': script.get('expected_response'),
                'Actual Response': result.get('actual_response', ''),
                'Detected Intent': result.get('detected_intent', ''),
                'Status': result.get('status', 'Not Executed').upper(),
                'Judge Verdict': result.get('judge_verdict', ''),
                'Confidence': result.get('judge_confidence', ''),
                'Judge Reasoning': result.get('judge_reasoning', '')
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _summary_to_dataframe(self, execution_summary: Dict) -> pd.DataFrame:
        """Convert execution summary to DataFrame."""
        
        summary_data = {
            'Metric': [
                'Total Scripts',
                'Executed',
                'Passed',
                'Failed',
                'Errors',
                'Pass Rate (%)',
                'Duration (seconds)'
            ],
            'Value': [
                execution_summary.get('total_scripts', 0),
                execution_summary.get('executed', 0),
                execution_summary.get('passed', 0),
                execution_summary.get('failed', 0),
                execution_summary.get('errors', 0),
                execution_summary.get('pass_rate', 0),
                execution_summary.get('duration_sec', 0)
            ]
        }
        
        return pd.DataFrame(summary_data)
    
    def _results_to_dataframe(self, test_results: List[Dict]) -> pd.DataFrame:
        """Convert test results to detailed DataFrame."""
        
        rows = []
        for result in test_results:
            row = {
                'Result ID': result.get('result_id'),
                'Execution ID': result.get('execution_id'),
                'Script ID': result.get('script_id'),
                'Test Type': result.get('test_type'),
                'Persona': result.get('persona'),
                'User Utterance': result.get('user_utterance'),
                'Agent Response': result.get('actual_response'),
                'Expected Response': result.get('expected_response'),
                'Expected Intent': result.get('expected_intent'),
                'Detected Intent': result.get('detected_intent'),
                'Status': result.get('status', '').upper(),
                'Judge Verdict': result.get('judge_verdict'),
                'Confidence': result.get('judge_confidence'),
                'Reasoning': result.get('judge_reasoning'),
                'Duration (sec)': result.get('duration_sec'),
                'Executed At': result.get('executed_at')
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _format_excel_worksheets(self, writer):
        """Format Excel worksheets."""
        
        workbook = writer.book
        
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Bold headers
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
    
    # ══════════════════════════════════════════════════════════
    # CSV EXPORT
    # ══════════════════════════════════════════════════════════
    
    def export_to_csv(
        self,
        test_scripts: List[Dict],
        test_results: Optional[List[Dict]] = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Export test scripts and results to CSV.
        
        Args:
            test_scripts: List of test scripts
            test_results: Optional test results
            output_path: Optional file path
        
        Returns:
            CSV file as bytes
        """
        # Create DataFrame
        df = self._scripts_to_dataframe(test_scripts, test_results)
        
        # Convert to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        csv_content = output.getvalue()
        csv_bytes = csv_content.encode('utf-8')
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(csv_bytes)
        
        return csv_bytes
    
    # ══════════════════════════════════════════════════════════
    # PDF EXPORT
    # ══════════════════════════════════════════════════════════
    
    def export_to_pdf(
        self,
        test_scripts: List[Dict],
        test_results: Optional[List[Dict]] = None,
        execution_summary: Optional[Dict] = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Export test results to PDF.
        
        Note: Requires reportlab or similar PDF library.
        This is a simplified version that creates HTML and converts to PDF.
        
        Args:
            test_scripts: Test scripts
            test_results: Test results
            execution_summary: Execution summary
            output_path: Output file path
        
        Returns:
            PDF file as bytes
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            # Create PDF
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a73e8'),
                spaceAfter=30
            )
            
            story.append(Paragraph("Agentforce Test Results", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Summary section
            if execution_summary:
                story.append(Paragraph("Execution Summary", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Scripts', str(execution_summary.get('total_scripts', 0))],
                    ['Passed', str(execution_summary.get('passed', 0))],
                    ['Failed', str(execution_summary.get('failed', 0))],
                    ['Pass Rate', f"{execution_summary.get('pass_rate', 0)}%"],
                    ['Duration', f"{execution_summary.get('duration_sec', 0):.1f}s"]
                ]
                
                summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(summary_table)
                story.append(PageBreak())
            
            # Test results section
            story.append(Paragraph("Test Results", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            # Create results lookup
            results_lookup = {}
            if test_results:
                results_lookup = {r.get('script_id'): r for r in test_results}
            
            # Add test results
            for script in test_scripts[:20]:  # Limit to first 20 for PDF
                result = results_lookup.get(script.get('script_id'), {})
                status = result.get('status', 'not executed').upper()
                
                # Status color
                status_color = colors.green if status == 'PASS' else colors.red if status == 'FAIL' else colors.orange
                
                test_data = [
                    ['Test Type:', script.get('test_type', '')],
                    ['Persona:', script.get('persona', '')],
                    ['Utterance:', script.get('utterance', '')],
                    ['Expected:', script.get('expected_response', '')[:100] + '...'],
                    ['Actual:', result.get('actual_response', '')[:100] + '...'],
                    ['Status:', status]
                ]
                
                test_table = Table(test_data, colWidths=[1.5*inch, 5*inch])
                test_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BACKGROUND', (0, -1), (-1, -1), status_color),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                
                story.append(test_table)
                story.append(Spacer(1, 0.2*inch))
            
            # Build PDF
            doc.build(story)
            output.seek(0)
            pdf_bytes = output.read()
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
            
            return pdf_bytes
        
        except ImportError:
            # reportlab not available - return simple text-based PDF alternative
            print("reportlab not installed. PDF export not available.")
            return b"PDF export requires reportlab library"


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def export_test_results(
    test_scripts: List[Dict],
    test_results: Optional[List[Dict]] = None,
    execution_summary: Optional[Dict] = None,
    format: str = "xlsx",
    output_path: Optional[str] = None
) -> bytes:
    """
    Quick export function.
    
    Usage:
        excel_bytes = export_test_results(
            test_scripts=scripts,
            test_results=results,
            execution_summary=summary,
            format="xlsx",
            output_path="./test_results.xlsx"
        )
    """
    engine = TestExportEngine()
    
    if format == "xlsx":
        return engine.export_to_excel(test_scripts, test_results, execution_summary, output_path)
    elif format == "csv":
        return engine.export_to_csv(test_scripts, test_results, output_path)
    elif format == "pdf":
        return engine.export_to_pdf(test_scripts, test_results, execution_summary, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")