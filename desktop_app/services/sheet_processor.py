import difflib
import os
import re
import datetime
import pandas as pd
from config import REQUIRED_CANDIDATE_COLUMNS
from database import db_manager


RECOGNIZED_HEADER_KEYWORDS = {
    # Keka fields
    "employeenumber", "employeecode", "empid", "firstname", "middlename", "lastname",
    "displayname", "fullname", "workemail", "personalemail", "mobilephone", "mobile",
    "dateofbirth", "gender", "maritalstatus", "marriagedate", "bloodgroup",
    "fathername", "mothername", "spousename", "location", "department", "subdepartment",
    "jobtitle", "datejoined", "pannumber", "aadhaarnumber", "pfnumber", "uannumber",
    "employmentstatus", "exitdate", "exitstatus", "terminationtype", "terminationreason",
    "reportingto", "reportingmanageremployeenumber", "leaveplan", "costcenter",
    "workertype", "timetype", "noticeperiod", "legalentity", "businessunit",
    "currentaddress", "permanentaddress", "currentaddressline1", "permanentaddressline1",
    # Joining Process pipeline fields
    "candidatename", "applieddesignation", "negotiatedsalary", "recentdesignation",
    "highesteducationqualification", "highesteducation", "totalyearsofexperience",
    "totalexperience", "coretechnicalskills", "keyresponsibilities", "contactlocation",
    "email", "status"
}


def read_sheet(file_path: str) -> pd.DataFrame:
    """
    Intelligently reads an Excel (.xlsx, .xls) or CSV file into a pandas DataFrame:
    - Auto-detects header row offset (e.g. Row 2 in Keka reports with company/title banners).
    - Auto-selects best sheet if workbook contains multiple tabs.
    - Auto-detects CSV delimiters (comma, tab, semicolon) and handles encodings.
    """
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    def _tok(v):
        return re.sub(r"[^a-z0-9]", "", str(v or "").lower())

    if file_path.lower().endswith((".xlsx", ".xls")):
        with pd.ExcelFile(file_path) as xl:
            best_sheet = xl.sheet_names[0]
            best_row = 0
            max_score = 0

            for s in xl.sheet_names:
                try:
                    df_probe = xl.parse(s, header=None, nrows=15)
                    for r_idx, row in df_probe.iterrows():
                        score = sum(1 for val in row if _tok(val) in RECOGNIZED_HEADER_KEYWORDS)
                        if score > max_score:
                            max_score = score
                            best_row = r_idx
                            best_sheet = s
                except Exception:
                    continue

            header_arg = best_row if max_score >= 2 else 0
            return xl.parse(best_sheet, header=header_arg)
    else:
        # CSV / TSV reader
        for enc in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
            try:
                with open(file_path, "r", encoding=enc, errors="replace") as f:
                    lines = [f.readline() for _ in range(15)]
                lines = [l for l in lines if l.strip()]
                if not lines:
                    return pd.read_csv(file_path, encoding=enc)

                best_sep = ","
                best_row = 0
                max_score = 0
                for sep in [",", "\t", ";"]:
                    for r_idx, line in enumerate(lines):
                        tokens = [_tok(t.strip()) for t in line.split(sep)]
                        score = sum(1 for t in tokens if t in RECOGNIZED_HEADER_KEYWORDS)
                        if score > max_score:
                            max_score = score
                            best_row = r_idx
                            best_sep = sep

                header_arg = best_row if max_score >= 2 else 0
                return pd.read_csv(file_path, sep=best_sep, header=header_arg, encoding=enc)
            except Exception:
                continue
        return pd.read_csv(file_path)


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Returns a list of required column names missing from the DataFrame."""
    missing = [c for c in REQUIRED_CANDIDATE_COLUMNS if c not in df.columns]
    return missing


def normalize_mobile(value) -> str:
    """Extracts digits and normalizes to the last 10 digits."""
    digits = re.sub(r"\D", "", str(value))
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_name_for_comparison(name: str) -> str:
    """
    Normalizes candidate name for fuzzy similarity matching:
    - Strips honorific prefixes (Mr., Ms., Dr., etc.)
    - Removes punctuation and symbols
    - Converts to lowercase and collapses multiple spaces
    """
    if not name:
        return ""
    cleaned = re.sub(r"^(mr\.|mrs\.|ms\.|dr\.|shri|smt\.)\s+", "", str(name).strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", "", cleaned.lower())
    return " ".join(cleaned.split())


def compute_name_similarity(name1: str, name2: str) -> float:
    """
    Computes candidate name similarity ratio using difflib.SequenceMatcher.
    Returns a float from 0.0 (no similarity) to 1.0 (exact match).
    """
    n1 = normalize_name_for_comparison(name1)
    n2 = normalize_name_for_comparison(name2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    return round(difflib.SequenceMatcher(None, n1, n2).ratio(), 4)


def extract_candidate_rows_from_sheet(file_path: str) -> dict:
    """
    Safely reads and validates candidate rows from an Excel or CSV file
    WITHOUT writing anything to the database.

    Returns:
      {
          "success": bool,
          "error": str or None,
          "total_sheet_rows": int,
          "valid_rows": list[dict],
          "errors": list[str]
      }
    """
    if not file_path or not os.path.exists(file_path):
        return {
            "success": False,
            "error": "The selected file could not be found. Please check the file path and try again.",
            "total_sheet_rows": 0,
            "valid_rows": [],
            "errors": [],
        }

    try:
        df = read_sheet(file_path)
    except Exception as e:
        print("Error reading spreadsheet file:", e)
        return {
            "success": False,
            "error": "We couldn't read this file. Please make sure it's a valid Excel (.xlsx, .xls) or CSV file, close it if it's open in Microsoft Excel, and try again.",
            "total_sheet_rows": 0,
            "valid_rows": [],
            "errors": [],
        }

    if df.empty:
        return {
            "success": False,
            "error": "The uploaded file is empty. Please select a spreadsheet with candidate data.",
            "total_sheet_rows": 0,
            "valid_rows": [],
            "errors": [],
        }

    missing = validate_columns(df)
    if missing:
        return {
            "success": False,
            "error": f"The uploaded sheet is missing required columns: {', '.join(missing)}. Please check your column headers.",
            "total_sheet_rows": len(df),
            "valid_rows": [],
            "errors": [],
        }

    valid_rows = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        mobile = normalize_mobile(row.get("Mobile", ""))
        if not mobile or len(mobile) < 10:
            errors.append(f"Row {row_num}: Invalid or missing 10-digit mobile number")
            continue

        cand_data = {
            "row_index": row_num,
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
        valid_rows.append(cand_data)

    return {
        "success": True,
        "error": None,
        "total_sheet_rows": len(df),
        "valid_rows": valid_rows,
        "errors": errors,
    }


def detect_duplicates(
    uploaded_rows: list[dict],
    existing_candidates: list[dict] = None,
    fuzzy_threshold: float = 0.85,
) -> dict:
    """
    Compares uploaded candidate rows against existing candidates in the database.
    A row is flagged as a duplicate if:
      (a) Normalized 10-digit mobile matches an existing candidate's mobile, OR
      (b) Candidate name closely matches an existing candidate (similarity >= fuzzy_threshold)

    Returns structured results:
      {
          "total_rows": int,
          "duplicate_count": int,
          "new_count": int,
          "duplicate_percentage": float,
          "duplicates": list[dict],
          "new_rows": list[dict]
      }
    """
    if existing_candidates is None:
        existing_candidates = db_manager.get_all_candidates() or []

    # Build mobile lookup index for O(1) matching
    mobile_index = {}
    for cand in existing_candidates:
        mob = normalize_mobile(cand.get("mobile", ""))
        if mob and len(mob) >= 10:
            mobile_index[mob] = cand

    duplicates = []
    new_rows = []

    for row in uploaded_rows:
        cand_mobile = normalize_mobile(row.get("mobile", ""))
        cand_name = str(row.get("candidate_name", "")).strip()

        matched_existing = None
        match_type = None
        match_reason = None
        similarity_score = 0.0

        # Rule (a): Exact mobile number match
        if cand_mobile and cand_mobile in mobile_index:
            matched_existing = mobile_index[cand_mobile]
            match_type = "mobile"
            match_reason = f"Mobile number matches existing candidate ({cand_mobile})"
            similarity_score = 1.0

        # Rule (b): Fuzzy name match if mobile didn't match
        if not matched_existing and cand_name:
            best_cand = None
            best_sim = 0.0

            for cand in existing_candidates:
                exist_name = cand.get("candidate_name") or ""
                sim = compute_name_similarity(cand_name, exist_name)
                if sim > best_sim:
                    best_sim = sim
                    best_cand = cand

            if best_sim >= fuzzy_threshold and best_cand:
                matched_existing = best_cand
                match_type = "name"
                pct = int(round(best_sim * 100))
                match_reason = f"Candidate name closely matches '{best_cand.get('candidate_name')}' ({pct}% similarity)"
                similarity_score = best_sim

        if matched_existing:
            duplicates.append({
                "existing_record": matched_existing,
                "uploaded_row": row,
                "match_type": match_type,
                "match_reason": match_reason,
                "similarity": similarity_score,
                "action": "keep",  # Safe default: do NOT overwrite unless HR explicitly chooses
            })
        else:
            new_rows.append(row)

    total = len(uploaded_rows)
    dup_count = len(duplicates)
    new_count = len(new_rows)
    pct = round((dup_count / total * 100), 1) if total > 0 else 0.0

    return {
        "total_rows": total,
        "duplicate_count": dup_count,
        "new_count": new_count,
        "duplicate_percentage": pct,
        "duplicates": duplicates,
        "new_rows": new_rows,
    }


def safe_update_candidate(candidate_id: int, new_data: dict, source_sheet_name: str = "") -> bool:
    """
    Safely updates an existing candidate's record with new uploaded data.
    IMPORTANT: Blank, None, or 'nan' values in new_data will NEVER overwrite
    existing non-empty values in the database.
    Lifecycle fields (status, date_joined, employee_number, relieving_date, etc.)
    are left untouched.
    """
    existing = db_manager.get_candidate_by_id(candidate_id)
    if not existing:
        return False

    updateable_fields = [
        "candidate_name",
        "email",
        "applied_designation",
        "negotiated_salary",
        "recent_designation",
        "highest_education",
        "total_experience",
        "core_technical_skills",
        "key_responsibilities",
        "contact_location",
    ]

    updates = []
    params = []

    for field in updateable_fields:
        if field in new_data:
            val = new_data.get(field)
            if val is not None:
                s_val = str(val).strip()
                if s_val and s_val.lower() not in ["nan", "none", "null"]:
                    updates.append(f"{field} = ?")
                    params.append(s_val)

    if source_sheet_name:
        updates.append("source_sheet_name = ?")
        params.append(str(source_sheet_name).strip())

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates.append("last_updated = ?")
    params.append(now)

    if not updates:
        return True

    params.append(candidate_id)
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE candidates SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        return True
    except Exception as e:
        print("Safe update error:", e)
        return False
    finally:
        conn.close()


def insert_new_candidate(data: dict, source_sheet_name: str = "") -> bool:
    """
    Inserts a genuinely new candidate record into the candidates table.
    Default status is 'Applied'.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO candidates
            (candidate_name, mobile, email, applied_designation, negotiated_salary,
             recent_designation, highest_education, total_experience, core_technical_skills,
             key_responsibilities, contact_location, status, source_sheet_name, upload_date, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            str(data.get("candidate_name") or "").strip(),
            str(data.get("mobile") or "").strip(),
            str(data.get("email") or "").strip(),
            str(data.get("applied_designation") or "").strip(),
            str(data.get("negotiated_salary") or "").strip(),
            str(data.get("recent_designation") or "").strip(),
            str(data.get("highest_education") or "").strip(),
            str(data.get("total_experience") or "").strip(),
            str(data.get("core_technical_skills") or "").strip(),
            str(data.get("key_responsibilities") or "").strip(),
            str(data.get("contact_location") or "").strip(),
            "Applied",
            str(source_sheet_name or data.get("source_sheet_name") or "").strip(),
            now,
            now
        ))
        conn.commit()
        return True
    except Exception as e:
        print("Insert candidate error:", e)
        return False
    finally:
        conn.close()


def apply_joining_decisions(
    duplicates: list[dict],
    new_rows: list[dict],
    source_sheet_name: str = "",
) -> dict:
    """
    Applies confirmed decisions safely to the database:
      - 'keep': Candidate record is untouched (left as-is).
      - 'replace': Candidate record updated with non-empty uploaded fields.
      - new_rows: Inserted fresh into candidates table.

    Returns summary:
      {
          "success": bool,
          "added_count": int,
          "updated_count": int,
          "kept_count": int,
          "total_processed": int,
          "errors": list[str]
      }
    """
    added_count = 0
    updated_count = 0
    kept_count = 0
    errors = []

    # 1. Process duplicates based on user action
    for item in duplicates:
        action = item.get("action", "keep")
        cand_id = item.get("existing_record", {}).get("id")
        uploaded = item.get("uploaded_row", {})
        cand_name = uploaded.get("candidate_name") or item.get("existing_record", {}).get("candidate_name") or "Candidate"

        if action == "replace":
            if cand_id:
                ok = safe_update_candidate(cand_id, uploaded, source_sheet_name=source_sheet_name)
                if ok:
                    updated_count += 1
                else:
                    errors.append(f"Could not update record for '{cand_name}'.")
            else:
                errors.append(f"Missing ID for existing candidate '{cand_name}'.")
        else:
            # Action is 'keep' -> untouched!
            kept_count += 1

    # 2. Process genuinely new candidates
    for new_cand in new_rows:
        cand_name = new_cand.get("candidate_name") or "New Candidate"
        ok = insert_new_candidate(new_cand, source_sheet_name=source_sheet_name)
        if ok:
            added_count += 1
        else:
            errors.append(f"Could not add new candidate '{cand_name}'.")

    return {
        "success": len(errors) == 0,
        "added_count": added_count,
        "updated_count": updated_count,
        "kept_count": kept_count,
        "total_processed": added_count + updated_count + kept_count,
        "errors": errors,
    }


def process_sheet(file_path: str, source_sheet_name: str):
    """
    Legacy wrapper for backwards-compatibility with older tests.
    Extracts rows, detects duplicates, safely updates/adds.
    """
    extracted = extract_candidate_rows_from_sheet(file_path)
    if not extracted["success"]:
        return {"success": False, "error": extracted["error"]}

    valid_rows = extracted["valid_rows"]
    dup_res = detect_duplicates(valid_rows)

    # In legacy non-interactive mode, new rows are inserted and duplicates are kept
    res = apply_joining_decisions(
        duplicates=dup_res["duplicates"],
        new_rows=dup_res["new_rows"],
        source_sheet_name=source_sheet_name
    )

    return {
        "success": True,
        "total_rows": extracted["total_sheet_rows"],
        "processed": res["added_count"] + res["updated_count"],
        "duplicates_skipped": res["kept_count"],
        "errors": extracted["errors"] + res["errors"],
    }
