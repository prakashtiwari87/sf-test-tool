"""
excel_loader.py
Loads test cases from Excel files and plain text prompts.
Supports the enterprise Test Runner format:
| Test Scenario ID | Test Scenario Summary | Detailed Test Steps | Expected Outcome |
"""

import io
import json
import pandas as pd
from datetime import datetime


REQUIRED_COLUMNS = [
    "Test Scenario ID",
    "Test Scenario Summary",
    "Detailed Test Steps / Instructions",
    "Expected Outcome / Result"
]

COLUMN_ALIASES = {
    "Test Scenario ID":                   ["id", "scenario id", "test id",
                                           "scenario_id", "test_id", "#"],
    "Test Scenario Summary":              ["summary", "name", "test name",
                                           "scenario", "title", "test scenario"],
    "Detailed Test Steps / Instructions": ["steps", "instructions",
                                           "test steps", "detailed steps",
                                           "prompt", "input", "description",
                                           "test instructions"],
    "Expected Outcome / Result":          ["expected", "expected result",
                                           "expected outcome", "outcome",
                                           "result", "expected output"]
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map any column name variations to the standard names"""
    rename_map = {}
    df_cols_lower = {c.lower().strip(): c for c in df.columns}

    for standard_name, aliases in COLUMN_ALIASES.items():
        if standard_name in df.columns:
            continue
        for alias in aliases:
            if alias.lower() in df_cols_lower:
                rename_map[df_cols_lower[alias.lower()]] = standard_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def load_test_cases_from_excel(uploaded_file) -> tuple:
    """
    Load test cases from an uploaded Excel file.
    Returns (list of test case dicts, error string or None).

    Supports:
    - .xlsx and .xls files
    - 1000+ rows
    - Flexible column name matching
    - Row-by-row validation
    """
    try:
        content = uploaded_file.read()
        df      = pd.read_excel(io.BytesIO(content), dtype=str)
        df      = df.fillna("")
        df      = _normalize_columns(df)

        # Validate required columns exist
        missing = [
            c for c in REQUIRED_COLUMNS if c not in df.columns
        ]
        if missing:
            return [], (
                f"Missing required columns: {', '.join(missing)}. "
                f"Found: {', '.join(df.columns.tolist())}. "
                f"Required: {', '.join(REQUIRED_COLUMNS)}"
            )

        # Drop fully empty rows
        df = df.replace("", pd.NA).dropna(
            how="all",
            subset=REQUIRED_COLUMNS
        ).fillna("")

        if df.empty:
            return [], "No data rows found in the Excel file."

        test_cases = []
        errors     = []

        for idx, row in df.iterrows():
            row_num  = idx + 2  # Excel row number (1-indexed + header)
            scenario_id = str(row.get(
                "Test Scenario ID", ""
            )).strip()
            summary = str(row.get(
                "Test Scenario Summary", ""
            )).strip()
            steps   = str(row.get(
                "Detailed Test Steps / Instructions", ""
            )).strip()
            expected = str(row.get(
                "Expected Outcome / Result", ""
            )).strip()

            # Skip fully empty rows
            if not summary and not steps:
                continue

            # Warn about missing expected outcome
            if not expected:
                errors.append(
                    f"Row {row_num}: missing Expected Outcome"
                )
                expected = (
                    "Operation completed successfully in Salesforce"
                )

            # Auto-generate ID if missing
            if not scenario_id:
                scenario_id = f"SCN-{row_num:04d}"

            test_cases.append({
                "test_id":        scenario_id,
                "test_name":      summary or steps[:80],
                "test_type":      "prompt",
                "priority":       str(row.get("Priority", "Medium")).strip() or "Medium",
                "tags":           str(row.get("Tags", "")).strip(),
                "action":         "PROMPT",
                "input_data":     steps or summary,
                "expected_output": expected,
                "row_number":     row_num,
                "source":         "excel"
            })

        if not test_cases:
            return [], "No valid test cases found after parsing."

        warning = (
            f" Warnings: {'; '.join(errors[:5])}"
            if errors else ""
        )
        return test_cases, (warning.strip() or None)

    except Exception as e:
        return [], f"Failed to parse Excel file: {str(e)}"


def load_test_cases_from_prompt(prompt_text: str) -> list:
    """
    Create a single test case from a plain text prompt.
    Used when user types directly in the UI.
    """
    if not prompt_text or not prompt_text.strip():
        return []

    return [{
        "test_id":         f"PROMPT-{datetime.now().strftime('%H%M%S')}",
        "test_name":       (
            prompt_text[:80] + "..."
            if len(prompt_text) > 80
            else prompt_text
        ),
        "test_type":       "prompt",
        "priority":        "Medium",
        "tags":            "",
        "action":          "PROMPT",
        "input_data":      prompt_text.strip(),
        "expected_output": (
            "Operation completed successfully in Salesforce "
            "with valid data returned"
        ),
        "row_number":      1,
        "source":          "ui_prompt"
    }]


def load_test_cases_from_bulk_prompts(prompt_rows: list) -> list:
    """
    Create test cases from multiple UI prompt rows.
    Each row: {"prompt_id", "intent", "expected_outcome",
               "priority", "tags"}
    """
    test_cases = []
    for i, row in enumerate(prompt_rows):
        if not row.get("intent", "").strip():
            continue
        test_cases.append({
            "test_id":         row.get("prompt_id") or f"UI-{i+1:04d}",
            "test_name":       row.get("intent", "")[:80],
            "test_type":       "prompt",
            "priority":        row.get("priority", "Medium"),
            "tags":            row.get("tags", ""),
            "action":          "PROMPT",
            "input_data":      row.get("intent", ""),
            "expected_output": (
                row.get("expected_outcome", "")
                or "Operation completed successfully in Salesforce"
            ),
            "row_number":      i + 1,
            "source":          "ui_bulk"
        })
    return test_cases


def create_excel_template() -> bytes:
    """
    Generate a downloadable Excel template with the required columns
    and sample rows showing correct format.
    """
    sample_data = [
        {
            "Test Scenario ID": "SCN-0001",
            "Test Scenario Summary": (
                "Create a new Contact record with mandatory fields"
            ),
            "Detailed Test Steps / Instructions": (
                "Create a Contact record in Salesforce with First Name, "
                "Last Name, and Email fields populated. "
                "Do not fill any address fields. "
                "Return the Contact Record ID after creation."
            ),
            "Expected Outcome / Result": (
                "Contact record created successfully. "
                "A valid Salesforce Record ID (starting with 003) "
                "is returned."
            ),
            "Priority": "High",
            "Tags": "contact,create,smoke"
        },
        {
            "Test Scenario ID": "SCN-0002",
            "Test Scenario Summary": (
                "Query all Account records and return count"
            ),
            "Detailed Test Steps / Instructions": (
                "Query the Salesforce org for all Account records. "
                "Return the total count and the first 5 Account Names."
            ),
            "Expected Outcome / Result": (
                "SOQL query executes successfully. "
                "Returns a list of Account records with Name field populated."
            ),
            "Priority": "Medium",
            "Tags": "account,query,regression"
        },
        {
            "Test Scenario ID": "SCN-0003",
            "Test Scenario Summary": (
                "Create 2 Lead records with all phone fields"
            ),
            "Detailed Test Steps / Instructions": (
                "Create 2 Lead records in Salesforce. "
                "Include: First Name, Last Name, Company, Email, "
                "all phone fields (Phone, MobilePhone, Fax). "
                "Do not fill any address fields. "
                "Return both Lead Record IDs."
            ),
            "Expected Outcome / Result": (
                "2 Lead records created successfully. "
                "2 valid Salesforce Record IDs returned. "
                "All phone fields populated, no address fields filled."
            ),
            "Priority": "High",
            "Tags": "lead,create,bulk,phone"
        },
    ]

    df  = pd.DataFrame(sample_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Test Scenarios")

        # Format the worksheet
        ws = writer.sheets["Test Scenarios"]
        col_widths = {
            "A": 15, "B": 40, "C": 60, "D": 50,
            "E": 12, "F": 25
        }
        for col, width in col_widths.items():
            ws.column_dimensions[col].width = width

    return buf.getvalue()


def validate_excel_structure(df: pd.DataFrame) -> tuple:
    """
    Validate that a DataFrame has the required structure.
    Returns (is_valid: bool, issues: list)
    """
    df      = _normalize_columns(df)
    issues  = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        issues.append(f"Missing columns: {', '.join(missing)}")
        return False, issues

    empty_summary = df[
        df["Test Scenario Summary"].str.strip() == ""
    ]
    if len(empty_summary) > 0:
        issues.append(
            f"{len(empty_summary)} rows have empty Test Scenario Summary"
        )

    empty_steps = df[
        df["Detailed Test Steps / Instructions"].str.strip() == ""
    ]
    if len(empty_steps) > 0:
        issues.append(
            f"{len(empty_steps)} rows have empty Test Steps"
        )

    return len(issues) == 0, issues