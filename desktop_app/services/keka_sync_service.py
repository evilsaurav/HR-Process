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


def detect_keka_conflicts_and_duplicates(file_path: str) -> Dict[str, Any]:
    """
    Pre-sync conflict detection and duplicate analysis for Keka Master Sheets.
    - Inspects sheet for internal duplicates (same employee_number appearing in multiple rows).
    - Matches incoming sheet records against database candidates (by employee_number, then mobile).
    - Compares key fields (candidate_name, applied_designation, department, negotiated_salary,
      contact_location, current_address, relieving_date, employment_status, mobile) and flags differences.
    - Evaluates whether the sheet represents a re-upload (>= 50% matched existing candidates).
    """
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": "We couldn't read this file. Please make sure the file exists, close it if open in another program, and try again.",
            "total_rows": 0,
            "internal_duplicates": [],
            "conflicting_employees": [],
            "identical_matches": [],
            "new_employees": [],
            "is_sheet_reupload": False,
            "detected_fields": [],
        }

    try:
        df = read_sheet(file_path)
    except Exception as e:
        print("detect_keka_conflicts_and_duplicates read sheet error:", e)
        return {
            "success": False,
            "error": "We couldn't process this file format. Please check the Excel/CSV sheet and try again.",
            "total_rows": 0,
            "internal_duplicates": [],
            "conflicting_employees": [],
            "identical_matches": [],
            "new_employees": [],
            "is_sheet_reupload": False,
            "detected_fields": [],
        }

    if df.empty:
        return {
            "success": True,
            "total_rows": 0,
            "internal_duplicates": [],
            "conflicting_employees": [],
            "identical_matches": [],
            "new_employees": [],
            "is_sheet_reupload": False,
            "detected_fields": [],
        }

    col_mapping = detect_keka_columns(list(df.columns))
    if not col_mapping:
        return {
            "success": False,
            "error": "Could not recognize any standard Keka columns in this sheet. Please verify the header row.",
            "total_rows": len(df),
            "internal_duplicates": [],
            "conflicting_employees": [],
            "identical_matches": [],
            "new_employees": [],
            "is_sheet_reupload": False,
            "detected_fields": [],
        }

    KEY_FIELDS = [
        "candidate_name", "applied_designation", "department",
        "negotiated_salary", "contact_location", "current_address",
        "relieving_date", "employment_status", "mobile"
    ]

    seen_emp_numbers = {}
    conflicting_employees = []
    identical_matches = []
    new_employees = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        row_dict = row.to_dict()
        record = extract_record_from_keka_row(row_dict, col_mapping)

        # Normalize mobile
        raw_mob = record.get("mobile")
        norm_mob = normalize_mobile(raw_mob)
        if norm_mob:
            record["mobile"] = norm_mob

        # Clean employee number
        raw_emp = record.get("employee_number")
        emp_no = None
        if raw_emp is not None:
            s_emp = str(raw_emp).strip()
            if s_emp.endswith(".0"):
                s_emp = s_emp[:-2]
            if s_emp and s_emp.lower() not in ["none", "nan", "null"]:
                emp_no = s_emp
                record["employee_number"] = emp_no
            else:
                record["employee_number"] = ""

        # Map relieving_date fallback from exit_date
        if record.get("exit_date") and not record.get("relieving_date"):
            record["relieving_date"] = record["exit_date"]

        # Track internal duplicates in sheet
        cand_name_display = record.get("candidate_name") or record.get("display_name") or ""
        if emp_no:
            seen_emp_numbers.setdefault(emp_no, []).append({
                "row_number": row_num,
                "name": cand_name_display
            })

        # Match strategy: 1) by employee_number, 2) by mobile
        matched_cand = None
        if emp_no:
            matched_cand = db_manager.get_candidate_by_employee_number(emp_no)
        if not matched_cand and norm_mob:
            matched_cand = db_manager.get_candidate_by_mobile(norm_mob)

        if matched_cand:
            cand_id = matched_cand["id"]
            cand_name = matched_cand.get("candidate_name") or matched_cand.get("display_name") or cand_name_display or "Unknown"

            changed_fields = {}
            for field in KEY_FIELDS:
                new_val = record.get(field)
                if new_val is None:
                    continue
                s_new = str(new_val).strip()
                if s_new.lower() in ["", "none", "nan", "null"]:
                    continue
                old_val = matched_cand.get(field)
                s_old = str(old_val).strip() if old_val is not None else ""
                if s_old.lower() in ["none", "nan", "null"]:
                    s_old = ""

                if s_new != s_old:
                    changed_fields[field] = {
                        "old": old_val if old_val is not None else "",
                        "new": new_val
                    }

            # Check if employee_number itself differs
            if emp_no:
                old_emp = matched_cand.get("employee_number")
                s_old_emp = str(old_emp).strip() if old_emp is not None else ""
                if s_old_emp and s_old_emp.lower() not in ["none", "nan", "null"] and s_old_emp != emp_no:
                    changed_fields["employee_number"] = {
                        "old": old_emp,
                        "new": emp_no
                    }

            if changed_fields:
                conflicting_employees.append({
                    "employee_number": emp_no or matched_cand.get("employee_number") or "",
                    "candidate_id": cand_id,
                    "candidate_name": cand_name,
                    "mobile": norm_mob or matched_cand.get("mobile") or "",
                    "existing": {f: v["old"] for f, v in changed_fields.items()},
                    "incoming": {f: v["new"] for f, v in changed_fields.items()},
                    "changed_fields": changed_fields,
                    "record": record,
                    "row_number": row_num
                })
            else:
                identical_matches.append({
                    "employee_number": emp_no or matched_cand.get("employee_number") or "",
                    "candidate_id": cand_id,
                    "candidate_name": cand_name,
                    "mobile": norm_mob or matched_cand.get("mobile") or "",
                    "record": record,
                    "row_number": row_num
                })
        else:
            new_employees.append({
                "employee_number": emp_no or "",
                "candidate_name": cand_name_display or "Unknown",
                "mobile": norm_mob or record.get("mobile") or "",
                "record": record,
                "row_number": row_num
            })

    # Internal sheet duplicates analysis
    internal_duplicates = []
    for eno, items in seen_emp_numbers.items():
        if len(items) > 1:
            internal_duplicates.append({
                "employee_number": eno,
                "rows": [it["row_number"] for it in items],
                "candidate_name": next((it["name"] for it in items if it["name"]), "Unknown"),
                "count": len(items)
            })

    total_rows = len(df)
    matched_total = len(conflicting_employees) + len(identical_matches)
    is_sheet_reupload = bool((total_rows > 0) and ((matched_total / total_rows) >= 0.5))

    return {
        "success": True,
        "total_rows": total_rows,
        "internal_duplicates": internal_duplicates,
        "conflicting_employees": conflicting_employees,
        "identical_matches": identical_matches,
        "new_employees": new_employees,
        "is_sheet_reupload": is_sheet_reupload,
        "detected_fields": list(col_mapping.keys())
    }


def sync_rich_keka_sheet_with_resolutions(
    file_path: str,
    resolutions: Optional[Dict[str, str]] = None,
    default_action: str = 'update',
    allow_new_inserts: bool = True
) -> Dict[str, Any]:
    """
    Ingests comprehensive Keka Master Sheet with explicit conflict resolution.
    - resolutions: dict mapping employee_number or mobile -> 'update' or 'keep'.
    - default_action: 'update' (overwrite DB with sheet values) or 'keep' (preserve current DB values).
    - allow_new_inserts: whether to import new non-pipeline staff into candidates table with status 'Joined'.
    """
    detection = detect_keka_conflicts_and_duplicates(file_path)
    if not detection.get("success"):
        return detection

    if detection["total_rows"] == 0:
        return {
            "success": True,
            "total_rows": 0,
            "matched_count": 0,
            "updated_count": 0,
            "kept_count": 0,
            "inserted_count": 0,
            "unmatched_rows": [],
            "errors": [],
            "detected_fields": detection.get("detected_fields", []),
            "internal_duplicates": [],
            "conflicting_employees": [],
            "identical_matches": [],
            "new_employees": [],
            "is_sheet_reupload": False,
        }

    resolutions_map = {str(k).strip(): str(v).lower().strip() for k, v in (resolutions or {}).items()}
    default_action = default_action.lower().strip()

    matched_count = 0
    updated_count = 0
    kept_count = 0
    inserted_count = 0
    unmatched_rows = []
    errors = []
    source_name = os.path.basename(file_path)

    # 1. Process Conflicting Employees
    for item in detection["conflicting_employees"]:
        emp_no = item.get("employee_number")
        mob = item.get("mobile")
        cand_id = item.get("candidate_id")
        record = item.get("record")
        row_num = item.get("row_number")

        action = default_action
        if emp_no and emp_no in resolutions_map:
            action = resolutions_map[emp_no]
        elif mob and mob in resolutions_map:
            action = resolutions_map[mob]

        matched_count += 1
        if action == "keep":
            kept_count += 1
        else:
            ok = db_manager.update_candidate_keka_master(cand_id, record)
            if ok:
                updated_count += 1
            else:
                errors.append({
                    "row_number": row_num,
                    "error": f"Failed to update candidate #{cand_id} ({item.get('candidate_name')})"
                })

    # 2. Process Identical Matches
    for item in detection["identical_matches"]:
        emp_no = item.get("employee_number")
        mob = item.get("mobile")
        cand_id = item.get("candidate_id")
        record = item.get("record")
        row_num = item.get("row_number")

        action = default_action
        if emp_no and emp_no in resolutions_map:
            action = resolutions_map[emp_no]
        elif mob and mob in resolutions_map:
            action = resolutions_map[mob]

        matched_count += 1
        if action == "keep":
            kept_count += 1
        else:
            ok = db_manager.update_candidate_keka_master(cand_id, record)
            if ok:
                updated_count += 1
            else:
                errors.append({
                    "row_number": row_num,
                    "error": f"Failed to update candidate #{cand_id} ({item.get('candidate_name')})"
                })

    # 3. Process New Employees
    for item in detection["new_employees"]:
        record = item.get("record")
        row_num = item.get("row_number")
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
                "mobile": item.get("mobile") or "N/A",
                "name": item.get("candidate_name") or "N/A",
                "employee_number": item.get("employee_number") or "N/A",
                "reason": "No matching candidate found in the active database.",
            })

    return {
        "success": True,
        "total_rows": detection["total_rows"],
        "matched_count": matched_count,
        "updated_count": updated_count,
        "kept_count": kept_count,
        "inserted_count": inserted_count,
        "unmatched_rows": unmatched_rows,
        "internal_duplicates": detection.get("internal_duplicates", []),
        "conflicting_employees": detection.get("conflicting_employees", []),
        "identical_matches": detection.get("identical_matches", []),
        "new_employees": detection.get("new_employees", []),
        "is_sheet_reupload": detection.get("is_sheet_reupload", False),
        "detected_fields": detection.get("detected_fields", []),
        "errors": errors,
    }


def process_rich_keka_sheet(file_path: str, allow_new_inserts: bool = True) -> Dict[str, Any]:
    """
    Ingests comprehensive Keka Master Sheet (.xlsx, .xls, .csv) with 25+ fields.
    Matches existing candidates by normalized mobile or employee number.
    If matched: updates all non-empty fields in database (preserving existing fields).
    If unmatched and allow_new_inserts is True (Option C Hybrid): inserts new employee directly with status 'Joined'.
    If unmatched and allow_new_inserts is False: registers in unmatched list for inspection.
    """
    return sync_rich_keka_sheet_with_resolutions(
        file_path=file_path,
        resolutions=None,
        default_action='update',
        allow_new_inserts=allow_new_inserts
    )
