"""
Service: keka_mapper.py
Purpose: Intelligent column resolver and data normalizer for Keka HRMS reports.
Maps diverse column variants across Keka export templates to internal DB attributes.
"""

import re
from typing import Dict, Any, List, Optional


# Canonical attribute definitions with flexible keyword matchers
KEKA_FIELD_DEFINITIONS: Dict[str, List[str]] = {
    "employee_number": [
        "employee number", "employee code", "emp no", "emp id", "employee id",
        "emp code", "employee_number", "emp_number", "staff id", "staff code"
    ],
    "first_name": ["first name", "firstname", "first_name", "fname"],
    "middle_name": ["middle name", "middlename", "middle_name", "mname"],
    "last_name": ["last name", "lastname", "last_name", "lname", "surname"],
    "display_name": [
        "display name", "employee name", "candidate name",
        "name", "display_name", "emp name", "staff name"
    ],
    "full_name": ["full name", "fullname", "full_name"],
    "work_email": [
        "work email", "work email address", "official email", "company email",
        "work_email", "office email", "email work"
    ],
    "personal_email": [
        "personal email", "personal email address", "personal_email", "email personal",
        "secondary email", "private email"
    ],
    "mobile": [
        "mobile phone", "mobile", "mobile number", "mobile_number", "contact",
        "contact number", "contact_number", "phone", "phone number", "cell", "contact no", "mobile no"
    ],
    "work_phone": ["work phone", "work telephone", "office phone", "work_phone"],
    "home_phone": ["home phone", "landline", "telephone", "home_phone"],
    "date_of_birth": ["date of birth", "dob", "birth date", "date_of_birth", "birthdate"],
    "gender": ["gender", "sex"],
    "marital_status": ["marital status", "marital_status", "marriage status"],
    "marriage_date": ["marriage date", "wedding date", "anniversary date", "marriage_date"],
    "blood_group": ["blood group", "blood_group", "blood", "bg"],
    "physically_handicapped": [
        "physically handicapped", "disability", "differently abled", "handicapped", "physically_handicapped"
    ],
    "nationality": ["nationality", "citizenship"],

    # Address Breakdown & Composites
    "current_address": [
        "current address", "current residential address", "present address",
        "current_address", "residential address", "local address", "current full address"
    ],
    "current_address_line_1": ["current address line 1", "current address 1", "current address line1"],
    "current_address_line_2": ["current address line 2", "current address 2", "current address line2"],
    "current_address_city": ["current address city", "current city"],
    "current_address_state": ["current address state", "current state"],
    "current_address_zip": ["current address zip", "current address pin", "current pincode", "current zip"],
    "current_address_country": ["current address country", "current country"],

    "permanent_address": [
        "permanent address", "permanent_address", "home address", "native address", "permanent full address"
    ],
    "permanent_address_line_1": ["permanent address line 1", "permanent address 1", "permanent address line1"],
    "permanent_address_line_2": ["permanent address line 2", "permanent address 2", "permanent address line2"],
    "permanent_address_city": ["permanent address city", "permanent city"],
    "permanent_address_state": ["permanent address state", "permanent state"],
    "permanent_address_zip": ["permanent address zip", "permanent address pin", "permanent pincode", "permanent zip"],
    "permanent_address_country": ["permanent address country", "permanent country"],

    # Family
    "father_name": ["father name", "father's name", "father", "fathers name", "father_name"],
    "mother_name": ["mother name", "mother's name", "mother", "mothers name", "mother_name"],
    "spouse_name": ["spouse name", "spouse's name", "spouse", "husband name", "wife name", "spouse_name"],
    "children_names": ["children names", "children name", "children", "child names", "children_names"],

    # Job & Organizational Hierarchy
    "attendance_number": ["attendance number", "attendance id", "attendance code", "attendance_number"],
    "contact_location": [
        "location", "work location", "job location",
        "office location", "city", "posting location", "base location"
    ],
    "location_country": ["location country", "work location country"],
    "legal_entity": ["legal entity", "company", "entity", "legal_entity"],
    "business_unit": ["business unit", "bu", "division", "business_unit"],
    "department": ["department", "dept", "project", "division"],
    "sub_department": ["sub department", "sub dept", "subdivision", "sub_department"],
    "job_title": [
        "job title", "designation", "applied designation", "role", "position",
        "current designation", "job_title", "title"
    ],
    "secondary_job_title": ["secondary job title", "secondary designation", "secondary title", "secondary_job_title"],
    "reporting_to": [
        "reporting to", "reporting manager", "manager name", "manager", "reports to",
        "supervisor", "lead"
    ],
    "reporting_manager_emp_no": [
        "reporting manager employee number", "manager employee number", "manager emp id",
        "reporting manager emp no", "manager emp code", "supervisor id"
    ],
    "dotted_line_manager": ["dotted line manager", "secondary manager", "dotted manager", "dotted_line_manager"],
    "date_joined": [
        "date joined", "date of joining", "doj", "joining date", "hire date",
        "start date", "date_joined"
    ],
    "leave_plan": ["leave plan", "leave policy", "leave policy name", "leave_plan"],
    "band": ["band", "grade band", "employee band"],
    "pay_grade": ["pay grade", "pay scale", "salary band", "pay_grade"],
    "time_type": ["time type", "fulltime parttime", "time_type", "work time type"],
    "worker_type": ["worker type", "employee type", "employment type", "staff type", "worker_type"],
    "shift_policy": ["shift policy name", "shift policy", "shift timing", "work shift", "shift_policy"],
    "weekly_off_policy": [
        "weekly off policy name", "attendance time tracking & weekly off policy", "weekly off policy", "weekly off",
        "weekend policy", "weekly_off_policy"
    ],
    "attendance_time_tracking_policy": [
        "attendance time tracking policy", "attendance policy", "time tracking policy", "attendance_time_tracking_policy"
    ],
    "attendance_capture_scheme": [
        "attendance capture scheme", "capture scheme", "attendance scheme", "attendance_capture_scheme"
    ],
    "holiday_list_name": ["holiday list name", "holiday list", "holiday calendar", "holiday_list_name"],
    "expense_policy_name": ["expense policy name", "expense policy", "claims policy", "expense_policy_name"],
    "notice_period": ["notice period", "notice days", "notice period in days", "notice_period"],

    # Statutory & Identity
    "pan_number": ["pan number", "pan", "pan no", "pan card", "pan_number"],
    "aadhaar_number": ["aadhaar number", "aadhar number", "aadhaar", "aadhar", "aadhaar no", "aadhaar_number"],
    "pf_number": ["pf number", "pf no", "provident fund number", "pf code", "pf_number"],
    "uan_number": ["uan number", "uan", "universal account number", "uan_number"],
    "employment_status": [
        "employment status", "status", "working status", "employee status", "employment_status"
    ],

    # Exit & Separation
    "exit_date": [
        "exit date", "relieving date", "last working day", "lwd", "date of exit",
        "resignation date", "date of relieving", "separation date", "last day", "exit_date"
    ],
    "comments": ["comments", "remarks", "notes", "comment"],
    "exit_status": ["exit status", "separation status", "exit_status"],
    "termination_type": ["termination type", "separation type", "exit type", "termination_type"],
    "termination_reason": [
        "termination reason", "exit reason", "reason for leaving", "separation reason", "termination_reason"
    ],
    "resignation_note": ["resignation note", "resignation remarks", "resignation comments", "resignation_note"],
    "cost_center": ["cost center", "project test", "cost centre", "accounts cost center", "cost_center"],
    "extension_of_service_till": [
        "extension of service till in", "extension of service till", "extension till", "extension_of_service_till"
    ],
    "extension_of_service_months": [
        "extension of service months in", "extension of service months", "extension months", "extension_of_service_months"
    ],
    "project_test": ["project test", "project name", "project_test"],
}


def _clean_str(val: Any) -> str:
    """Removes non-alphanumeric chars and lowercases."""
    return re.sub(r"[^a-z0-9]", "", str(val or "").lower())


def detect_keka_columns(columns: List[str]) -> Dict[str, str]:
    """
    Given a list of raw column headers from a spreadsheet, maps each internal
    attribute to the best matching raw column header.
    Returns: {internal_attr: raw_column_header}
    """
    col_cleaned_map = {
        _clean_str(c): c for c in columns if c is not None and str(c).strip() != ""
    }

    mapping = {}
    for attr, keywords in KEKA_FIELD_DEFINITIONS.items():
        matched_header = None
        for kw in keywords:
            clean_kw = _clean_str(kw)
            if clean_kw in col_cleaned_map:
                matched_header = col_cleaned_map[clean_kw]
                break
        if matched_header:
            mapping[attr] = matched_header

    return mapping


def extract_record_from_keka_row(row: Dict[str, Any], col_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Extracts and standardizes a single employee record from a raw spreadsheet row dict.
    Supports multi-line address composition, float stripping, and date sanitation.
    """
    record = {}
    for attr, header in col_mapping.items():
        raw_val = row.get(header)
        if isinstance(raw_val, float) and raw_val.is_integer():
            val_str = str(int(raw_val))
        else:
            val_str = str(raw_val).strip()
            if val_str.endswith(".0"):
                val_str = val_str[:-2]

        if val_str != "" and val_str.lower() not in ["none", "nan", "nat", "null"]:
            record[attr] = val_str

    # Date formatting sanitation (strip ' 00:00:00' if present)
    for d_field in ["date_of_birth", "marriage_date", "date_joined", "exit_date", "extension_of_service_till"]:
        val = record.get(d_field)
        if val:
            clean_date = str(val).split(" ")[0].strip()
            if clean_date.lower() not in ["nan", "none", "nat", "null"]:
                record[d_field] = clean_date
            else:
                record[d_field] = ""

    # Construct current_address from address line components if not directly present
    if not record.get("current_address"):
        curr_line1 = record.get("current_address_line_1", "")
        curr_line2 = record.get("current_address_line_2", "")
        curr_city = record.get("current_address_city", "")
        curr_state = record.get("current_address_state", "")
        curr_zip = record.get("current_address_zip", "")
        curr_country = record.get("current_address_country", "")

        curr_parts = [p for p in [curr_line1, curr_line2, curr_city, curr_state] if p and p.lower() not in ["nan", "none"]]
        curr_str = ", ".join(curr_parts)
        if curr_zip and curr_zip.lower() not in ["nan", "none"]:
            curr_str += f" - {curr_zip}"
        if curr_country and curr_country.lower() not in ["nan", "none"]:
            curr_str += f", {curr_country}"
        if curr_str.strip():
            record["current_address"] = curr_str.strip()

    # Construct permanent_address from address line components if not directly present
    if not record.get("permanent_address"):
        perm_line1 = record.get("permanent_address_line_1", "")
        perm_line2 = record.get("permanent_address_line_2", "")
        perm_city = record.get("permanent_address_city", "")
        perm_state = record.get("permanent_address_state", "")
        perm_zip = record.get("permanent_address_zip", "")
        perm_country = record.get("permanent_address_country", "")

        perm_parts = [p for p in [perm_line1, perm_line2, perm_city, perm_state] if p and p.lower() not in ["nan", "none"]]
        perm_str = ", ".join(perm_parts)
        if perm_zip and perm_zip.lower() not in ["nan", "none"]:
            perm_str += f" - {perm_zip}"
        if perm_country and perm_country.lower() not in ["nan", "none"]:
            perm_str += f", {perm_country}"
        if perm_str.strip():
            record["permanent_address"] = perm_str.strip()

    # Synthetic display_name & candidate_name fallback
    cand_name = record.get("full_name") or record.get("display_name")
    if not cand_name:
        fname = record.get("first_name", "")
        mname = record.get("middle_name", "")
        lname = record.get("last_name", "")
        parts = [p for p in [fname, mname, lname] if p]
        if parts:
            cand_name = " ".join(parts).strip()

    if cand_name:
        if not record.get("display_name"):
            record["display_name"] = cand_name
        if not record.get("candidate_name"):
            record["candidate_name"] = cand_name

    # Email fallback: prefer work_email, then personal_email, populate generic 'email'
    if not record.get("email"):
        record["email"] = record.get("work_email") or record.get("personal_email") or ""

    # Address fallback: permanent_address, then current_address, populate generic 'full_address'
    if not record.get("full_address"):
        record["full_address"] = record.get("permanent_address") or record.get("current_address") or ""

    # Designation fallback: job_title populates 'applied_designation'
    if not record.get("applied_designation") and record.get("job_title"):
        record["applied_designation"] = record["job_title"]

    return record
