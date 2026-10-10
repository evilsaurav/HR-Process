import pandas as pd
import re
from config import REQUIRED_CANDIDATE_COLUMNS
from database.db_manager import upsert_candidate

def read_sheet(file_path: str) -> pd.DataFrame:
    if file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)

def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_CANDIDATE_COLUMNS if c not in df.columns]
    return missing

def normalize_mobile(value) -> str:
    digits = re.sub(r"\D", "", str(value))
    return digits[-10:] if len(digits) >= 10 else digits

def process_sheet(file_path: str, source_sheet_name: str):
    df = read_sheet(file_path)
    missing = validate_columns(df)
    if missing:
        return {"success": False, "error": f"Missing columns: {', '.join(missing)}"}

    added_or_updated = 0
    errors = []

    for idx, row in df.iterrows():
        mobile = normalize_mobile(row.get("Mobile", ""))
        if not mobile or len(mobile) < 10:
            errors.append(f"Row {idx+2}: Invalid/missing mobile number")
            continue

        data = {
            "candidate_name": str(row.get("Candidate Name", "")).strip(),
            "mobile": mobile,
            "email": str(row.get("Email", "")).strip(),
            "applied_designation": str(row.get("Applied Designation", "")).strip(),
            "negotiated_salary": str(row.get("Negotiated Salary", "")).strip(),
            "recent_designation": str(row.get("Recent Designation", "")).strip(),
            "highest_education": str(row.get("Highest Education Qualification", "")).strip(),
            "total_experience": str(row.get("Total Years of Experience (Inferred)", "")).strip(),
            "core_technical_skills": str(row.get("Core Technical Skills", "")).strip(),
            "key_responsibilities": str(row.get("Key Responsibilities", "")).strip(),
            "contact_location": str(row.get("Contact Location", "")).strip(),
        }

        ok = upsert_candidate(data, source_sheet_name)
        if ok:
            added_or_updated += 1
        else:
            errors.append(f"Row {idx+2}: Database error")

    return {
        "success": True,
        "total_rows": len(df),
        "processed": added_or_updated,
        "errors": errors
    }
