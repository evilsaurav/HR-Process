"""
Service: keka_sync_service.py
Purpose: Backend service for Keka HRMS sync. Ingests exported Excel/CSV sheets
from Keka HRMS, normalizes mobile numbers, and updates candidate employee numbers
and relieving dates in the database without overwriting existing data with blanks.
Includes friendly Excel report generation for unmatched records.
"""

import os
import re
import pandas as pd
from typing import Dict, Any, List, Optional

from services.sheet_processor import read_sheet, normalize_mobile
from services.document_formatters import format_date_long
from services.excel_export_service import export_to_excel
from database import db_manager


# Keywords for fuzzy column detection in Keka exports
MOBILE_COLUMN_KEYWORDS = [
    "mobile", "mobile number", "mobile_number", "contact",
    "contact number", "contact_number", "phone", "phone number",
    "cell", "contact no", "mobile no"
]

EMP_NUM_COLUMN_KEYWORDS = [
    "employee number", "employee code", "emp no", "emp id",
    "employee id", "emp code", "employee_number", "emp_number",
    "employee_code", "emp_id", "staff id", "staff code"
]

RELIEVING_DATE_KEYWORDS = [
    "relieving date", "exit date", "last working day", "relieving_date",
    "lwd", "date of exit", "resignation date", "date of relieving",
    "separation date", "last day"
]

NAME_COLUMN_KEYWORDS = [
    "candidate name", "employee name", "name", "full name",
    "emp name", "candidate_name", "employee_name", "staff name"
]


def _detect_column(df_columns, keywords: List[str]) -> Optional[str]:
    """
    Finds a matching column name in df_columns based on flexible keyword matching.
    Strips non-alphanumeric characters and checks lowercased tokens.
    """
    col_cleaned_map = {
        re.sub(r"[^a-z0-9]", "", str(c).lower()): c
        for c in df_columns
    }
    for kw in keywords:
        clean_kw = re.sub(r"[^a-z0-9]", "", kw.lower())
        if clean_kw in col_cleaned_map:
            return col_cleaned_map[clean_kw]
    return None


def process_keka_sync_sheet(file_path: str) -> Dict[str, Any]:
    """
    Processes an exported Keka HRMS sheet (.xlsx, .xls, or .csv).
    Matches rows to existing candidates by normalized 10-digit mobile number.
    Updates candidate employee_number and relieving_date (if present in sheet).

    DATA PRESERVATION GUARANTEE:
    - Blank/empty values in the sheet will NEVER overwrite existing database values.
    - Unmatched rows are NOT inserted as new candidates (update operation only).

    Returns summary dict:
    {
        "success": bool,
        "total_rows": int,
        "matched_count": int,
        "updated_count": int,
        "unmatched_rows": [
            {
                "row_number": int,
                "mobile": str,
                "name": str,
                "reason": str
            }, ...
        ],
        "errors": [
            {
                "row_number": int,
                "error": str
            }, ...
        ]
    }
    """
    if not os.path.exists(file_path):
        print(f"File not found error (Keka Sync): {file_path}")
        return {
            "success": False,
            "error": "We couldn't read this file. Please make sure it's a valid Excel (.xlsx) or CSV file, close it if it's open in another program, and try again.",
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "unmatched_rows": [],
            "errors": []
        }

    try:
        df = read_sheet(file_path)
    except Exception as e:
        print("Sheet reading error (Keka Sync):", e)
        return {
            "success": False,
            "error": "We couldn't read this file. Please make sure it's a valid Excel (.xlsx) or CSV file, close it if it's open in another program, and try again.",
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "unmatched_rows": [],
            "errors": []
        }

    if df.empty:
        return {
            "success": True,
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "unmatched_rows": [],
            "errors": []
        }

    # Detect expected columns using fuzzy matching
    col_mobile = _detect_column(df.columns, MOBILE_COLUMN_KEYWORDS)
    col_emp_num = _detect_column(df.columns, EMP_NUM_COLUMN_KEYWORDS)
    col_relieving = _detect_column(df.columns, RELIEVING_DATE_KEYWORDS)
    col_name = _detect_column(df.columns, NAME_COLUMN_KEYWORDS)

    if not col_mobile:
        return {
            "success": False,
            "error": "Could not identify a Mobile Number column in the uploaded sheet. Please check your column headers.",
            "total_rows": len(df),
            "matched_count": 0,
            "updated_count": 0,
            "unmatched_rows": [],
            "errors": []
        }

    if not col_emp_num:
        return {
            "success": False,
            "error": "Could not identify an Employee Number / Code column in the uploaded sheet. Please check your column headers.",
            "total_rows": len(df),
            "matched_count": 0,
            "updated_count": 0,
            "unmatched_rows": [],
            "errors": []
        }

    matched_count = 0
    updated_count = 0
    unmatched_rows = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based row number accounting for header row
        raw_mobile = row.get(col_mobile)
        mobile = normalize_mobile(raw_mobile)

        if not mobile or len(mobile) < 10:
            errors.append({
                "row_number": row_num,
                "error": f"Invalid or missing mobile number '{raw_mobile}' in row {row_num}."
            })
            continue

        cand_name = ""
        if col_name and pd.notna(row.get(col_name)):
            cand_name = str(row.get(col_name)).strip()

        # Extract & sanitize employee number
        raw_emp = row.get(col_emp_num)
        emp_num = None
        if pd.notna(raw_emp):
            s_emp = str(raw_emp).strip()
            # Clean floating numbers imported from Excel (e.g. 1042.0 -> 1042)
            if s_emp.endswith(".0"):
                s_emp = s_emp[:-2]
            if s_emp and s_emp.lower() not in ["nan", "none", "null"]:
                emp_num = s_emp

        # Extract & sanitize relieving date (optional; blank if active employee)
        relieving_date = None
        if col_relieving and pd.notna(row.get(col_relieving)):
            s_rel = str(row.get(col_relieving)).strip()
            if s_rel and s_rel.lower() not in ["nan", "none", "null"]:
                formatted_rel = format_date_long(s_rel, fallback=s_rel)
                if formatted_rel:
                    relieving_date = formatted_rel

        # Match against candidates table in database
        existing_candidate = db_manager.get_candidate_by_mobile(mobile)
        if not existing_candidate:
            unmatched_rows.append({
                "row_number": row_num,
                "mobile": mobile,
                "name": cand_name or f"Row {row_num}",
                "reason": "No candidate found with this mobile number in the system."
            })
            continue

        matched_count += 1

        # Determine whether any field has changed
        field_changed = False
        if emp_num is not None and existing_candidate.get("employee_number") != emp_num:
            field_changed = True
        if relieving_date is not None and existing_candidate.get("relieving_date") != relieving_date:
            field_changed = True

        # Perform partial update (None values are ignored, preserving existing data)
        success = db_manager.update_employee_lifecycle_data(
            mobile=mobile,
            employee_number=emp_num,
            relieving_date=relieving_date
        )

        if success and field_changed:
            updated_count += 1

    return {
        "success": True,
        "total_rows": len(df),
        "matched_count": matched_count,
        "updated_count": updated_count,
        "unmatched_rows": unmatched_rows,
        "errors": errors
    }


def export_unmatched_report(unmatched_rows: List[Dict[str, Any]], output_path: str) -> str:
    """
    Exports unmatched Keka sync rows to a formatted Excel file for HR inspection.
    Uses user-friendly, non-technical column headers.
    """
    formatted_data = []
    for r in unmatched_rows:
        formatted_data.append({
            "Row Number": r.get("row_number", ""),
            "Mobile Number": r.get("mobile", ""),
            "Candidate Name (from sheet)": r.get("name", ""),
            "Reason": r.get("reason", "No candidate found with this mobile number in the system.")
        })

    return export_to_excel(
        data=formatted_data,
        output_path=output_path,
        sheet_name="Unmatched Keka Records"
    )


def update_employee_lifecycle_data(mobile: str, employee_number: Optional[str] = None,
                                   relieving_date: Optional[str] = None) -> bool:
    """
    Updates employee_number and/or relieving_date for a candidate.
    Empty/blank strings are treated as None to prevent overwriting existing data.
    """
    return db_manager.update_employee_lifecycle_data(
        mobile=mobile,
        employee_number=employee_number,
        relieving_date=relieving_date
    )


def get_candidates_pending_keka_sync() -> List[Dict[str, Any]]:
    """
    Returns list of candidates whose status is 'Joined' but employee_number
    has not yet been populated by Keka sync.
    """
    return db_manager.get_candidates_pending_keka_sync()


from services.keka_mapper import detect_keka_columns, extract_record_from_keka_row


def process_rich_keka_sheet(file_path: str, allow_new_inserts: bool = True) -> Dict[str, Any]:
    """
    Ingests comprehensive Keka Master Sheet (.xlsx, .xls, .csv) with 25+ fields.
    Matches existing candidates by normalized mobile or employee number.
    If matched: updates all non-empty fields in database (preserving existing fields).
    If unmatched and allow_new_inserts is True (Option C Hybrid): inserts new employee directly with status 'Joined'.
    If unmatched and allow_new_inserts is False: registers in unmatched list for inspection.
    """
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": "We couldn't read this file. Please make sure the file exists, close it if open in another program, and try again.",
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "inserted_count": 0,
            "unmatched_rows": [],
            "errors": [],
        }

    try:
        df = read_sheet(file_path)
    except Exception as e:
        print("Read rich sheet error:", e)
        return {
            "success": False,
            "error": "We couldn't process this file format. Please check the Excel/CSV sheet and try again.",
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "inserted_count": 0,
            "unmatched_rows": [],
            "errors": [],
        }

    if df.empty:
        return {
            "success": True,
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "inserted_count": 0,
            "unmatched_rows": [],
            "errors": [],
        }

    col_mapping = detect_keka_columns(list(df.columns))
    if not col_mapping:
        return {
            "success": False,
            "error": "Could not recognize any standard Keka columns in this sheet. Please verify the header row.",
            "total_rows": len(df),
            "matched_count": 0,
            "updated_count": 0,
            "inserted_count": 0,
            "unmatched_rows": [],
            "errors": [],
        }

    matched_count = 0
    updated_count = 0
    inserted_count = 0
    unmatched_rows = []
    errors = []
    source_name = os.path.basename(file_path)

    for idx, row in df.iterrows():
        row_num = idx + 2
        row_dict = row.to_dict()
        record = extract_record_from_keka_row(row_dict, col_mapping)

        # Normalize mobile
        raw_mob = record.get("mobile")
        norm_mob = normalize_mobile(raw_mob)
        if norm_mob:
            record["mobile"] = norm_mob

        emp_no = record.get("employee_number")

        # Match strategy: 1) by mobile, 2) by employee_number
        matched_cand = None
        if norm_mob:
            matched_cand = db_manager.get_candidate_by_mobile(norm_mob)

        if not matched_cand and emp_no:
            conn = db_manager.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM candidates WHERE employee_number = ?", (emp_no,))
            row_id = cur.fetchone()
            conn.close()
            if row_id:
                matched_cand = db_manager.get_candidate_by_id(row_id[0])

        if matched_cand:
            cand_id = matched_cand["id"]
            ok = db_manager.update_candidate_keka_master(cand_id, record)
            matched_count += 1
            if ok:
                updated_count += 1
        else:
            if allow_new_inserts:
                new_id = db_manager.insert_keka_employee(record, source_sheet_name=source_name)
                if new_id:
                    inserted_count += 1
                else:
                    errors.append({
                        "row_number": row_num,
                        "error": f"Could not insert employee record for row {row_num}."
                    })
            else:
                unmatched_rows.append({
                    "row_number": row_num,
                    "mobile": norm_mob or raw_mob or "N/A",
                    "name": record.get("display_name") or record.get("candidate_name") or "N/A",
                    "employee_number": emp_no or "N/A",
                    "reason": "No matching candidate found in the active database.",
                })

    return {
        "success": True,
        "total_rows": len(df),
        "matched_count": matched_count,
        "updated_count": updated_count,
        "inserted_count": inserted_count,
        "unmatched_rows": unmatched_rows,
        "detected_fields": list(col_mapping.keys()),
        "errors": errors,
    }
