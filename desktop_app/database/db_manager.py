import sqlite3
import datetime
import json
import re
from typing import Optional
from config import DB_PATH
from services.encryption import encrypt_text, decrypt_text

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT,
            mobile TEXT UNIQUE,
            email TEXT,
            applied_designation TEXT,
            negotiated_salary TEXT,
            recent_designation TEXT,
            highest_education TEXT,
            total_experience TEXT,
            core_technical_skills TEXT,
            key_responsibilities TEXT,
            contact_location TEXT,
            status TEXT DEFAULT 'Applied',
            source_sheet_name TEXT,
            upload_date TEXT,
            last_updated TEXT,
            father_name TEXT,
            full_address TEXT,
            gender TEXT,
            department TEXT,
            date_joined TEXT,
            employee_number TEXT,
            relieving_date TEXT,
            archived INTEGER DEFAULT 0,
            archived_at TEXT,
            welcome_email_sent INTEGER DEFAULT 0,
            welcome_email_sent_at TEXT,
            tag TEXT
        )
    """)

    # Safe idempotent migration: add new columns if missing in existing database
    cur.execute("PRAGMA table_info(candidates)")
    existing_cand_cols = {row[1] for row in cur.fetchall()}
    new_candidate_columns = [
        ("father_name", "TEXT"),
        ("full_address", "TEXT"),
        ("gender", "TEXT"),
        ("department", "TEXT"),
        ("date_joined", "TEXT"),
        ("employee_number", "TEXT"),
        ("relieving_date", "TEXT"),
        ("archived", "INTEGER DEFAULT 0"),
        ("archived_at", "TEXT"),
        ("tag", "TEXT"),
        # Rich Keka Master Fields
        ("first_name", "TEXT"),
        ("last_name", "TEXT"),
        ("display_name", "TEXT"),
        ("work_email", "TEXT"),
        ("personal_email", "TEXT"),
        ("date_of_birth", "TEXT"),
        ("marital_status", "TEXT"),
        ("marriage_date", "TEXT"),
        ("current_address", "TEXT"),
        ("permanent_address", "TEXT"),
        ("mother_name", "TEXT"),
        ("spouse_name", "TEXT"),
        ("job_title", "TEXT"),
        ("reporting_to", "TEXT"),
        ("reporting_manager_emp_no", "TEXT"),
        ("employment_status", "TEXT"),
        ("worker_type", "TEXT"),
        ("time_type", "TEXT"),
        ("leave_plan", "TEXT"),
        ("shift_policy", "TEXT"),
        ("weekly_off_policy", "TEXT"),
        ("notice_period", "TEXT"),
        ("pan_number", "TEXT"),
        ("aadhaar_number", "TEXT"),
        ("pf_number", "TEXT"),
        ("uan_number", "TEXT"),
        ("exit_date", "TEXT"),
        ("exit_status", "TEXT"),
        ("termination_type", "TEXT"),
        ("termination_reason", "TEXT"),
        ("cost_center", "TEXT"),
        ("middle_name", "TEXT"),
        ("blood_group", "TEXT"),
        ("physically_handicapped", "TEXT"),
        ("nationality", "TEXT"),
        ("work_phone", "TEXT"),
        ("home_phone", "TEXT"),
        ("children_names", "TEXT"),
        ("attendance_number", "TEXT"),
        ("location_country", "TEXT"),
        ("legal_entity", "TEXT"),
        ("business_unit", "TEXT"),
        ("sub_department", "TEXT"),
        ("secondary_job_title", "TEXT"),
        ("dotted_line_manager", "TEXT"),
        ("band", "TEXT"),
        ("pay_grade", "TEXT"),
        ("attendance_time_tracking_policy", "TEXT"),
        ("attendance_capture_scheme", "TEXT"),
        ("holiday_list_name", "TEXT"),
        ("expense_policy_name", "TEXT"),
        ("comments", "TEXT"),
        ("resignation_note", "TEXT"),
        ("extension_of_service_till", "TEXT"),
        ("extension_of_service_months", "TEXT"),
        ("project_test", "TEXT"),
        ("welcome_email_sent", "INTEGER DEFAULT 0"),
        ("welcome_email_sent_at", "TEXT"),
    ]
    for col_name, col_type in new_candidate_columns:
        if col_name not in existing_cand_cols:
            cur.execute(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type}")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_employee_number ON candidates(employee_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_mobile ON candidates(mobile)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key_id TEXT PRIMARY KEY,
            provider TEXT,
            encrypted_value TEXT,
            extra_json TEXT,
            is_verified INTEGER DEFAULT 0,
            last_checked TEXT
        )
    """)

    # Check if reference_number_config table exists and check its columns for migration
    cur.execute("PRAGMA table_info(reference_number_config)")
    columns = [row[1] for row in cur.fetchall()]
    if columns and "id" in columns:
        cur.execute("SELECT format_template, padding_width, range_start, range_end, current_number FROM reference_number_config WHERE id = 1")
        old_data = cur.fetchone()
        cur.execute("DROP TABLE reference_number_config")
        cur.execute("""
            CREATE TABLE reference_number_config (
                sequence_name TEXT PRIMARY KEY,
                format_template TEXT,
                padding_width INTEGER,
                range_start INTEGER,
                range_end INTEGER,
                current_number INTEGER
            )
        """)
        if old_data:
            cur.execute("""
                INSERT INTO reference_number_config (sequence_name, format_template, padding_width, range_start, range_end, current_number)
                VALUES ('hr_reference', ?, ?, ?, ?, ?)
            """, old_data)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reference_number_config (
                sequence_name TEXT PRIMARY KEY,
                format_template TEXT,
                padding_width INTEGER,
                range_start INTEGER,
                range_end INTEGER,
                current_number INTEGER
            )
        """)

    # Template storage table for document generation
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL,
            designation_label TEXT NOT NULL,
            template_file_path TEXT NOT NULL,
            created_date TEXT,
            UNIQUE(document_type, designation_label)
        )
    """)

    # Audit trail / history log for document generation events
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            document_type TEXT,
            reference_number TEXT,
            generated_date TEXT,
            extra_fields_json TEXT,
            file_path TEXT,
            generated_by TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    # Audit trail / history log for email dispatches
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT,
            document_type TEXT,
            subject TEXT,
            attachment_filename TEXT,
            attachment_path TEXT,
            sent_by TEXT DEFAULT 'HR Desktop',
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    # Idempotent column check for email_log
    cur.execute("PRAGMA table_info(email_log)")
    existing_email_cols = {row[1] for row in cur.fetchall()}
    email_cols_to_check = [
        ("candidate_id", "INTEGER"),
        ("recipient_email", "TEXT"),
        ("recipient_name", "TEXT"),
        ("document_type", "TEXT"),
        ("subject", "TEXT"),
        ("attachment_filename", "TEXT"),
        ("attachment_path", "TEXT"),
        ("sent_by", "TEXT"),
        ("timestamp", "TEXT"),
        ("status", "TEXT"),
        ("error_message", "TEXT"),
    ]
    for col_name, col_type in email_cols_to_check:
        if col_name not in existing_email_cols:
            cur.execute(f"ALTER TABLE email_log ADD COLUMN {col_name} {col_type}")

    # Scheduled emails queue
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            recipient_email TEXT NOT NULL,
            recipient_name TEXT,
            document_type TEXT,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            attachment_path TEXT,
            scheduled_time TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            created_at TEXT NOT NULL,
            dispatched_at TEXT,
            error_message TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    # Document Staging Queue for Human-in-the-Loop review and batch dispatch
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_staging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            status TEXT DEFAULT 'Staged',
            doc_file_path TEXT NOT NULL,
            pdf_file_path TEXT,
            preferred_format TEXT DEFAULT 'pdf',
            recipient_email TEXT NOT NULL,
            recipient_name TEXT NOT NULL,
            email_subject TEXT NOT NULL,
            email_body TEXT NOT NULL,
            reference_number TEXT,
            extra_fields_json TEXT,
            discrepancy_warnings_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            dispatched_at TEXT,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
        )
    """)

    # Idempotent column check for document_staging
    cur.execute("PRAGMA table_info(document_staging)")
    existing_staging_cols = {row[1] for row in cur.fetchall()}
    staging_cols_to_check = [
        ("candidate_id", "INTEGER"),
        ("document_type", "TEXT"),
        ("status", "TEXT DEFAULT 'Staged'"),
        ("doc_file_path", "TEXT"),
        ("pdf_file_path", "TEXT"),
        ("preferred_format", "TEXT DEFAULT 'pdf'"),
        ("recipient_email", "TEXT"),
        ("recipient_name", "TEXT"),
        ("email_subject", "TEXT"),
        ("email_body", "TEXT"),
        ("reference_number", "TEXT"),
        ("extra_fields_json", "TEXT"),
        ("discrepancy_warnings_json", "TEXT"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
        ("dispatched_at", "TEXT"),
    ]
    for col_name, col_type in staging_cols_to_check:
        if col_name not in existing_staging_cols:
            cur.execute(f"ALTER TABLE document_staging ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()


def upsert_candidate(data: dict, source_sheet_name: str):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur.execute("""
            INSERT INTO candidates
            (candidate_name, mobile, email, applied_designation, negotiated_salary,
             recent_designation, highest_education, total_experience, core_technical_skills,
             key_responsibilities, contact_location, status, source_sheet_name, upload_date, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(mobile) DO UPDATE SET
                candidate_name=excluded.candidate_name,
                email=excluded.email,
                applied_designation=excluded.applied_designation,
                negotiated_salary=excluded.negotiated_salary,
                recent_designation=excluded.recent_designation,
                highest_education=excluded.highest_education,
                total_experience=excluded.total_experience,
                core_technical_skills=excluded.core_technical_skills,
                key_responsibilities=excluded.key_responsibilities,
                contact_location=excluded.contact_location,
                source_sheet_name=excluded.source_sheet_name,
                last_updated=excluded.last_updated
        """, (
            data.get("candidate_name"), data.get("mobile"), data.get("email"),
            data.get("applied_designation"), data.get("negotiated_salary"),
            data.get("recent_designation"), data.get("highest_education"),
            data.get("total_experience"), data.get("core_technical_skills"),
            data.get("key_responsibilities"), data.get("contact_location"),
            "Applied", source_sheet_name, now, now
        ))
        conn.commit()
        return True
    except Exception as e:
        print("Upsert error:", e)
        return False
    finally:
        conn.close()

def get_all_candidates(search_term="", status_filter="All", include_archived=False):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []
    if not include_archived:
        query += " AND (archived = 0 OR archived IS NULL)"
    if search_term:
        query += " AND (candidate_name LIKE ? OR contact_location LIKE ? OR applied_designation LIKE ? OR mobile LIKE ?)"
        like = f"%{search_term}%"
        params += [like, like, like, like]
    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY id DESC"
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows

def update_candidate_status(candidate_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE candidates SET status=?, last_updated=? WHERE id=?",
                 (status, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), candidate_id))
    conn.commit()
    conn.close()


def insert_candidate(data: dict, source_sheet_name: str = "") -> int:
    """
    Inserts a candidate and returns the inserted row ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cand_mob = str(data.get("mobile") or "").strip() or None
    sheet_src = str(source_sheet_name or data.get("source_sheet_name") or "").strip()

    try:
        cur.execute("""
            INSERT INTO candidates
            (candidate_name, mobile, email, applied_designation, negotiated_salary,
             recent_designation, highest_education, total_experience, core_technical_skills,
             key_responsibilities, contact_location, department, date_joined, status, tag, source_sheet_name, upload_date, last_updated)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(mobile) DO UPDATE SET
                candidate_name=COALESCE(NULLIF(excluded.candidate_name, ''), candidates.candidate_name),
                email=COALESCE(NULLIF(excluded.email, ''), candidates.email),
                applied_designation=COALESCE(NULLIF(excluded.applied_designation, ''), candidates.applied_designation),
                negotiated_salary=COALESCE(NULLIF(excluded.negotiated_salary, ''), candidates.negotiated_salary),
                recent_designation=COALESCE(NULLIF(excluded.recent_designation, ''), candidates.recent_designation),
                highest_education=COALESCE(NULLIF(excluded.highest_education, ''), candidates.highest_education),
                total_experience=COALESCE(NULLIF(excluded.total_experience, ''), candidates.total_experience),
                core_technical_skills=COALESCE(NULLIF(excluded.core_technical_skills, ''), candidates.core_technical_skills),
                key_responsibilities=COALESCE(NULLIF(excluded.key_responsibilities, ''), candidates.key_responsibilities),
                contact_location=COALESCE(NULLIF(excluded.contact_location, ''), candidates.contact_location),
                department=COALESCE(NULLIF(excluded.department, ''), candidates.department),
                date_joined=COALESCE(NULLIF(excluded.date_joined, ''), candidates.date_joined),
                tag=COALESCE(NULLIF(excluded.tag, ''), candidates.tag),
                source_sheet_name=COALESCE(NULLIF(excluded.source_sheet_name, ''), candidates.source_sheet_name),
                last_updated=excluded.last_updated
        """, (
            str(data.get("candidate_name") or "").strip(),
            cand_mob,
            str(data.get("email") or "").strip(),
            str(data.get("applied_designation") or "").strip(),
            str(data.get("negotiated_salary") or "").strip(),
            str(data.get("recent_designation") or "").strip(),
            str(data.get("highest_education") or "").strip(),
            str(data.get("total_experience") or "").strip(),
            str(data.get("core_technical_skills") or "").strip(),
            str(data.get("key_responsibilities") or "").strip(),
            str(data.get("contact_location") or "").strip(),
            str(data.get("department") or "").strip(),
            str(data.get("date_joined") or "").strip(),
            str(data.get("status") or "Applied").strip(),
            str(data.get("tag") or "").strip(),
            sheet_src,
            now,
            now
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_candidate_tag(candidate_id: int, tag: str) -> bool:
    """Updates candidate status tag (Immediate Joiner, Docs Pending, On Hold, Top Priority)."""
    if not candidate_id:
        return False
    conn = get_connection()
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute("UPDATE candidates SET tag = ?, last_updated = ? WHERE id = ?", (str(tag or "").strip(), now, int(candidate_id)))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("update_candidate_tag error:", e)
        return False
    finally:
        conn.close()


def get_candidates_by_tag(tag: str) -> List[dict]:
    """Returns all candidates with a specific tag."""
    if not tag:
        return []
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM candidates WHERE tag = ? AND (archived = 0 OR archived IS NULL) ORDER BY id DESC", (str(tag).strip(),))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def get_upcoming_joinees(days: int = 7) -> List[dict]:
    """
    Returns active candidates whose expected date_joined falls between today and today + days.
    """
    all_cands = get_all_candidates() or []
    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=days)

    upcoming = []
    for c in all_cands:
        doj_str = str(c.get("date_joined") or "").strip()
        if not doj_str:
            continue
        parsed_dt = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed_dt = datetime.datetime.strptime(doj_str, fmt).date()
                break
            except ValueError:
                continue

        if parsed_dt and today <= parsed_dt <= max_date:
            item = dict(c)
            item["days_until_joining"] = (parsed_dt - today).days
            item["parsed_doj"] = parsed_dt.strftime("%Y-%m-%d")
            upcoming.append(item)

    upcoming.sort(key=lambda x: x["days_until_joining"])
    return upcoming


def get_distinct_source_sheets() -> List[str]:
    """
    Returns list of distinct source sheet and department names for quick batch filtering.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT source_sheet_name FROM candidates WHERE source_sheet_name IS NOT NULL AND source_sheet_name != ''")
        sources = {row[0].strip() for row in cur.fetchall() if row[0] and row[0].strip()}
        cur.execute("SELECT DISTINCT department FROM candidates WHERE department IS NOT NULL AND department != ''")
        depts = {row[0].strip() for row in cur.fetchall() if row[0] and row[0].strip()}
        all_sheets = sorted(list(sources.union(depts)))
        return all_sheets
    finally:
        conn.close()

def update_candidate_extra_details(candidate_id: int, father_name: str, full_address: str, gender: str, department: str, date_joined: str, employee_number: str):
    conn = get_connection()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE candidates
        SET father_name = ?,
            full_address = ?,
            gender = ?,
            department = ?,
            date_joined = ?,
            employee_number = ?,
            last_updated = ?
        WHERE id = ?
    """, (father_name, full_address, gender, department, date_joined, employee_number, now, candidate_id))
    conn.commit()
    conn.close()

def update_candidate(candidate_id: int, fields: dict) -> bool:
    """
    Updates any valid columns of a candidate by ID.
    Used for inline data corrections and general profile updates.
    """
    if candidate_id is None or not fields:
        return False
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(candidates)")
        valid_cols = {row[1] for row in cur.fetchall()}

        update_fields = {}
        for k, v in fields.items():
            if k in valid_cols:
                update_fields[k] = str(v).strip() if v is not None else ""

        if not update_fields:
            return False

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_fields["last_updated"] = now

        set_clauses = [f"{col} = ?" for col in update_fields.keys()]
        values = list(update_fields.values()) + [int(candidate_id)]

        cur.execute(f"UPDATE candidates SET {', '.join(set_clauses)} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("update_candidate error:", e)
        return False
    finally:
        conn.close()


def update_candidate_keka_master(candidate_id: int, fields: dict) -> bool:
    """
    Updates candidate with non-empty fields from Keka master data.
    Never overwrites existing database values with blanks or None.
    """
    if candidate_id is None or not fields:
        return False
    existing = get_candidate_by_id(candidate_id)
    if not existing:
        return False

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(candidates)")
        valid_cols = {row[1] for row in cur.fetchall()}

        update_fields = {}
        for k, v in fields.items():
            if k in valid_cols and v is not None and str(v).strip() != "" and str(v).strip().lower() not in ["none", "nan", "null"]:
                update_fields[k] = str(v).strip()

        if not update_fields:
            return True

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_fields["last_updated"] = now

        set_clauses = [f"{col} = ?" for col in update_fields.keys()]
        values = list(update_fields.values()) + [int(candidate_id)]

        conn.execute(f"UPDATE candidates SET {', '.join(set_clauses)} WHERE id = ?", values)
        conn.commit()
        return True
    except Exception as e:
        print("update_candidate_keka_master error:", e)
        return False
    finally:
        conn.close()

def insert_keka_employee(fields: dict, source_sheet_name: str = "") -> int | None:
    """
    Inserts a newly onboarded employee from Keka master sheet into the candidates table.
    Guarantees duplicate employee prevention:
    If employee_number or mobile already exists, does NOT insert a duplicate candidate row.
    Instead, updates the existing candidate via update_candidate_keka_master and returns existing ID.
    """
    if not fields:
        return None

    cand_name = str(fields.get("candidate_name", "") or fields.get("display_name", "") or "").strip()
    if cand_name.lower() in ["none", "nan", "null", ""]:
        cand_name = ""

    emp_no = str(fields.get("employee_number", "") or "").strip()
    if emp_no.endswith(".0"):
        emp_no = emp_no[:-2]

    raw_mob = str(fields.get("mobile", "") or "").strip()
    clean_mob = re.sub(r"\D", "", raw_mob)
    if len(clean_mob) >= 10:
        clean_mob = clean_mob[-10:]

    # Guard: Must have at least a valid name, employee number, or mobile number (skip trailing blank rows)
    if not cand_name and not emp_no and not clean_mob:
        return None

    # Guard: Skip automated report footer/watermark lines
    if "this report is generated by keka" in cand_name.lower():
        return None

    if emp_no and emp_no.lower() not in ["none", "nan", "null"]:
        existing = get_candidate_by_employee_number(emp_no)
        if existing:
            update_candidate_keka_master(existing["id"], fields)
            return existing["id"]

    if clean_mob and clean_mob.lower() not in ["none", "nan", "null"]:
        existing_mob = get_candidate_by_mobile(clean_mob)
        if existing_mob:
            update_candidate_keka_master(existing_mob["id"], fields)
            return existing_mob["id"]

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(candidates)")
        valid_cols = {row[1] for row in cur.fetchall()}

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {k: str(v).strip() for k, v in fields.items() if k in valid_cols and v is not None and str(v).strip() not in ["", "None", "nan", "null"]}
        if emp_no:
            data["employee_number"] = emp_no
        if clean_mob:
            data["mobile"] = clean_mob
        data["source_sheet_name"] = source_sheet_name
        data["upload_date"] = now
        data["last_updated"] = now
        if "status" not in data or not data["status"]:
            data["status"] = "Joined"

        cols = list(data.keys())
        placeholders = ["?"] * len(cols)
        vals = list(data.values())

        cur.execute(f"INSERT INTO candidates ({', '.join(cols)}) VALUES ({', '.join(placeholders)})", vals)
        new_id = cur.lastrowid
        conn.commit()
        return new_id
    except Exception as e:
        print("insert_keka_employee error:", e)
        return None
    finally:
        conn.close()

def get_candidate_related_counts(candidate_id: int) -> dict:
    """
    Returns counts of linked records in document_generation_log and email_log
    for a given candidate_id.
    """
    if candidate_id is None:
        return {"documents": 0, "emails": 0}
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = ?", (int(candidate_id),))
    doc_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM email_log WHERE candidate_id = ?", (int(candidate_id),))
    email_count = cur.fetchone()[0]
    conn.close()
    return {"documents": doc_count, "emails": email_count}

def permanently_delete_candidate(candidate_id: int) -> bool:
    """
    Permanently deletes a candidate and all their linked records
    (document_generation_log, email_log) in a single atomic transaction.
    Returns True if candidate was found and deleted, False otherwise.
    """
    if candidate_id is None:
        return False
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Delete dependent rows first to prevent FK constraint failures
        cur.execute("DELETE FROM document_generation_log WHERE candidate_id = ?", (int(candidate_id),))
        cur.execute("DELETE FROM email_log WHERE candidate_id = ?", (int(candidate_id),))
        cur.execute("DELETE FROM scheduled_emails WHERE candidate_id = ?", (int(candidate_id),))
        cur.execute("DELETE FROM candidates WHERE id = ?", (int(candidate_id),))
        count = cur.rowcount
        conn.commit()
        return count > 0
    except Exception as e:
        conn.rollback()
        print("Permanent delete candidate error:", e)
        return False
    finally:
        conn.close()

def delete_candidate(candidate_id: int) -> bool:
    """
    Backward-compatible alias for permanently_delete_candidate.
    Ensures that existing callers safely delete candidate records
    and their dependencies in an atomic transaction.
    """
    return permanently_delete_candidate(candidate_id)


# ================= EMAIL SCHEDULING QUEUE =================

def schedule_email(
    candidate_id: int,
    recipient_email: str,
    recipient_name: str,
    document_type: str,
    subject: str,
    body: str,
    attachment_path: str,
    scheduled_time: str
) -> int | None:
    """Inserts a scheduled email into scheduled_emails queue. Returns new row ID."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO scheduled_emails
            (candidate_id, recipient_email, recipient_name, document_type,
             subject, body, attachment_path, scheduled_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Scheduled', ?)
        """, (
            candidate_id, recipient_email, recipient_name, document_type,
            subject, body, attachment_path, scheduled_time, now
        ))
        row_id = cur.lastrowid
        conn.commit()
        return row_id
    except Exception as e:
        print("schedule_email error:", e)
        return None
    finally:
        conn.close()

def get_scheduled_emails(status: str = "Scheduled") -> list[dict]:
    """Returns scheduled emails filtered by status, or all if status is 'All'."""
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT id, candidate_id, recipient_email, recipient_name, document_type,
               subject, body, attachment_path, scheduled_time, status, created_at,
               dispatched_at, error_message
        FROM scheduled_emails
    """
    params = []
    if status and status != "All":
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY scheduled_time ASC, id ASC"

    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows

def update_scheduled_email_status(schedule_id: int, status: str, error_message: str = None) -> bool:
    """Updates status and dispatched_at for a scheduled email."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status in ["Sent", "Failed"] else None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE scheduled_emails
            SET status = ?, dispatched_at = ?, error_message = ?
            WHERE id = ?
        """, (status, now, error_message, int(schedule_id)))
        count = cur.rowcount
        conn.commit()
        return count > 0
    except Exception as e:
        print("update_scheduled_email_status error:", e)
        return False
    finally:
        conn.close()

def cancel_scheduled_email(schedule_id: int) -> bool:
    """Cancels a scheduled email if it has not yet been dispatched."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE scheduled_emails SET status = 'Cancelled' WHERE id = ? AND status = 'Scheduled'", (int(schedule_id),))
        count = cur.rowcount
        conn.commit()
        return count > 0
    except Exception as e:
        print("cancel_scheduled_email error:", e)
        return False
    finally:
        conn.close()

def archive_candidate(candidate_id: int) -> bool:
    """
    Soft-deletes a candidate by setting archived = 1 and archived_at = current timestamp.
    Preserves all existing data, status, and related rows in document_generation_log / email_log.
    Returns True if candidate was found and updated, False otherwise.
    """
    if candidate_id is None:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE candidates
            SET archived = 1,
                archived_at = ?
            WHERE id = ?
        """, (now, int(candidate_id)))
        count = cur.rowcount
        conn.commit()
        return count > 0
    except Exception as e:
        print("Archive candidate error:", e)
        return False
    finally:
        conn.close()

def restore_candidate(candidate_id: int) -> bool:
    """
    Restores an archived candidate by setting archived = 0 and archived_at = NULL.
    Leaves candidate status and all other fields completely intact.
    Returns True if candidate was found and restored, False otherwise.
    """
    if candidate_id is None:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE candidates
            SET archived = 0,
                archived_at = NULL,
                last_updated = ?
            WHERE id = ?
        """, (now, int(candidate_id)))
        count = cur.rowcount
        conn.commit()
        return count > 0
    except Exception as e:
        print("Restore candidate error:", e)
        return False
    finally:
        conn.close()

def get_archived_candidates(search_term=""):
    """
    Returns only archived candidates (archived = 1), with optional search term.
    """
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM candidates WHERE archived = 1"
    params = []
    if search_term:
        query += " AND (candidate_name LIKE ? OR contact_location LIKE ? OR applied_designation LIKE ? OR mobile LIKE ?)"
        like = f"%{search_term}%"
        params += [like, like, like, like]
    query += " ORDER BY archived_at DESC, id DESC"
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows

def get_candidate_by_id(candidate_id: int) -> dict | None:
    """Finds a candidate by primary key ID."""
    if candidate_id is None:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM candidates WHERE id = ?", (int(candidate_id),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    cols = [d[0] for d in cur.description]
    res = dict(zip(cols, row))
    conn.close()
    return res

def get_candidate_by_mobile(mobile: str) -> dict | None:
    """Finds a candidate by normalized mobile number."""
    if not mobile:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM candidates WHERE mobile = ?", (str(mobile).strip(),))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    cols = [d[0] for d in cur.description]
    res = dict(zip(cols, row))
    conn.close()
    return res

def get_candidate_by_employee_number(employee_number: str) -> Optional[dict]:
    """Finds a candidate by employee_number."""
    if not employee_number:
        return None
    clean_emp = str(employee_number).strip()
    if clean_emp.endswith(".0"):
        clean_emp = clean_emp[:-2]
    if not clean_emp or clean_emp.lower() in ["none", "nan", "null"]:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM candidates WHERE employee_number = ?", (clean_emp,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        conn.close()

def update_employee_lifecycle_data(mobile: str, employee_number: str = None, relieving_date: str = None) -> bool:
    """
    Updates employee_number and/or relieving_date for the candidate with the given mobile number.
    Supports partial updates: only non-None and non-empty values are updated.
    Empty/blank strings are treated as None to guarantee existing database values are never overwritten.
    Returns True if candidate was found and updated, False otherwise.
    """
    if not mobile:
        return False
    clean_mobile = str(mobile).strip()

    updates = []
    params = []

    # Only update if non-None, non-empty, and not literal 'nan'/'none'/'null'
    if employee_number is not None:
        s_emp = str(employee_number).strip()
        if s_emp and s_emp.lower() not in ["none", "nan", "null"]:
            updates.append("employee_number = ?")
            params.append(s_emp)

    if relieving_date is not None:
        s_rel = str(relieving_date).strip()
        if s_rel and s_rel.lower() not in ["none", "nan", "null"]:
            updates.append("relieving_date = ?")
            params.append(s_rel)

    if not updates:
        cand = get_candidate_by_mobile(clean_mobile)
        return cand is not None

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates.append("last_updated = ?")
    params.append(now)

    params.append(clean_mobile)

    conn = get_connection()
    cur = conn.cursor()
    query = f"UPDATE candidates SET {', '.join(updates)} WHERE mobile = ?"
    cur.execute(query, params)
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count > 0

def get_candidates_pending_keka_sync() -> list[dict]:
    """
    Returns candidates whose status is 'Joined' but employee_number is still empty or NULL.
    Used to track employees pending Keka HRMS sync.
    Excludes archived candidates, blank ghost rows, and automated report watermark lines.
    """
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT * FROM candidates
        WHERE status = 'Joined'
          AND (archived = 0 OR archived IS NULL)
          AND (employee_number IS NULL OR TRIM(employee_number) = '')
          AND (candidate_name IS NOT NULL AND TRIM(candidate_name) != '' AND LOWER(candidate_name) NOT IN ('none', 'nan', 'null'))
          AND (candidate_name NOT LIKE '%This report is generated by Keka%')
        ORDER BY id DESC
    """
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def save_api_key(key_id: str, provider: str, api_key: str):
    conn = get_connection()
    enc = encrypt_text(api_key)
    conn.execute("""
        INSERT INTO app_settings (key_id, provider, encrypted_value, is_verified, last_checked)
        VALUES (?,?,?,0,?)
        ON CONFLICT(key_id) DO UPDATE SET provider=excluded.provider,
            encrypted_value=excluded.encrypted_value, is_verified=0
    """, (key_id, provider, enc, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def mark_verified(key_id: str, verified: bool):
    conn = get_connection()
    conn.execute("UPDATE app_settings SET is_verified=?, last_checked=? WHERE key_id=?",
                 (1 if verified else 0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key_id))
    conn.commit()
    conn.close()

def get_all_api_keys():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key_id, provider, encrypted_value, is_verified FROM app_settings")
    rows = cur.fetchall()
    conn.close()
    result = []
    for key_id, provider, enc_val, verified in rows:
        result.append({
            "key_id": key_id,
            "provider": provider,
            "api_key": decrypt_text(enc_val),
            "verified": bool(verified)
        })
    return result

def delete_api_key(key_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM app_settings WHERE key_id=?", (key_id,))
    conn.commit()
    conn.close()


def save_reference_config(sequence_name: str, format_template: str, padding_width: int, range_start: int, range_end: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT range_start, current_number FROM reference_number_config WHERE sequence_name = ?", (sequence_name,))
    existing = cur.fetchone()

    if existing and existing[0] == range_start:
        current_num = existing[1]
    else:
        current_num = range_start

    conn.execute("""
        INSERT INTO reference_number_config (sequence_name, format_template, padding_width, range_start, range_end, current_number)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sequence_name) DO UPDATE SET
            format_template=excluded.format_template,
            padding_width=excluded.padding_width,
            range_start=excluded.range_start,
            range_end=excluded.range_end,
            current_number=excluded.current_number
    """, (sequence_name, format_template, padding_width, range_start, range_end, current_num))
    conn.commit()
    conn.close()

def get_reference_config(sequence_name: str = "hr_reference"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT format_template, padding_width, range_start, range_end, current_number FROM reference_number_config WHERE sequence_name = ?", (sequence_name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "sequence_name": sequence_name,
        "format_template": row[0],
        "padding_width": row[1],
        "range_start": row[2],
        "range_end": row[3],
        "current_number": row[4]
    }

def preview_next_reference(sequence_name: str = "hr_reference"):
    from services.reference_number_service import format_reference_number
    config = get_reference_config(sequence_name)
    if not config:
        return None
    if config["current_number"] > config["range_end"]:
        return {"exhausted": True, "remaining": 0, "total": config["range_end"] - config["range_start"] + 1}
    formatted = format_reference_number(config["format_template"], config["padding_width"], config["current_number"])
    remaining = config["range_end"] - config["current_number"] + 1
    total = config["range_end"] - config["range_start"] + 1
    return {"exhausted": False, "formatted": formatted, "remaining": remaining, "total": total}

def consume_next_reference(sequence_name: str = "hr_reference"):
    config = get_reference_config(sequence_name)
    if not config:
        return None, f"No reference number configuration found for '{sequence_name}'. Please set it up in Settings."
    if config["current_number"] > config["range_end"]:
        return None, f"Reference number range exhausted for '{sequence_name}'. Please add a new range in Settings."
    from services.reference_number_service import format_reference_number
    formatted = format_reference_number(config["format_template"], config["padding_width"], config["current_number"])
    conn = get_connection()
    conn.execute("UPDATE reference_number_config SET current_number = current_number + 1 WHERE sequence_name = ?", (sequence_name,))
    conn.commit()
    conn.close()
    return formatted, None


# ================= DOCUMENT TEMPLATES =================

def resolve_template_path(relative_path: str) -> str:
    """
    Resolves a template path stored in the database (which may be stored as a relative path
    like 'templates/offer/xxx.docx') into an absolute path anchored to TEMPLATES_DIR,
    regardless of the current working directory the app is launched from.
    """
    from config import TEMPLATES_DIR
    import os
    # Strip any leading 'templates/' or 'templates\' prefix from the stored relative path
    # since TEMPLATES_DIR already points to the templates folder itself
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("templates/"):
        normalized = normalized[len("templates/"):]
    return os.path.normpath(os.path.join(TEMPLATES_DIR, normalized))

def add_document_template(document_type: str, designation_label: str, template_file_path: str) -> bool:
    """Inserts a new mapping, returns False if duplicate or fails."""
    conn = get_connection()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute("""
            INSERT INTO document_templates (document_type, designation_label, template_file_path, created_date)
            VALUES (?, ?, ?, ?)
        """, (document_type, designation_label, template_file_path, now))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Template mapping already exists: ({document_type}, '{designation_label}')")
        return False
    except Exception as e:
        print(f"Error adding document template: {e}")
        return False
    finally:
        conn.close()

def get_templates_by_type(document_type: str) -> list[dict]:
    """Returns all templates for a given document type."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, designation_label, template_file_path
        FROM document_templates
        WHERE document_type = ?
        ORDER BY designation_label ASC
    """, (document_type,))
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "designation_label": r[1], "template_file_path": r[2]}
        for r in rows
    ]

def get_template_path(document_type: str, designation_label: str):
    """Returns the template file path for a specific type and designation, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT template_file_path
        FROM document_templates
        WHERE document_type = ? AND designation_label = ?
    """, (document_type, designation_label))
    row = cur.fetchone()
    conn.close()
    if row:
        return resolve_template_path(row[0])
    return None

def delete_document_template(template_id: int):
    """Deletes a template mapping from the database by id."""
    conn = get_connection()
    conn.execute("DELETE FROM document_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

def get_all_document_templates() -> list[dict]:
    """Returns all document templates across all types."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, document_type, designation_label, template_file_path, created_date
        FROM document_templates
        ORDER BY document_type ASC, designation_label ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "document_type": r[1],
            "designation_label": r[2],
            "template_file_path": r[3],
            "created_date": r[4]
        }
        for r in rows
    ]


# ================= DOCUMENT GENERATION AUDIT LOG =================

def log_document_generation(candidate_id: int, document_type: str, reference_number: str,
                            extra_fields_dict: dict, file_path: str, generated_by: str = None) -> int:
    """
    Logs a document generation event into document_generation_log.
    extra_fields_dict is serialized to JSON string.
    Returns the newly inserted log record ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra_json = json.dumps(extra_fields_dict or {})
    cur.execute("""
        INSERT INTO document_generation_log
        (candidate_id, document_type, reference_number, generated_date, extra_fields_json, file_path, generated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (candidate_id, document_type, reference_number, now, extra_json, file_path, generated_by))
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_generation_history(candidate_id: int) -> list[dict]:
    """
    Returns all generation records for a given candidate, ordered by generated_date DESC.
    extra_fields_json is deserialized back into a python dict.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, candidate_id, document_type, reference_number, generated_date, extra_fields_json, file_path, generated_by
        FROM document_generation_log
        WHERE candidate_id = ?
        ORDER BY generated_date DESC
    """, (candidate_id,))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        try:
            extra_fields = json.loads(r[5]) if r[5] else {}
        except Exception:
            extra_fields = {}
        result.append({
            "id": r[0],
            "candidate_id": r[1],
            "document_type": r[2],
            "reference_number": r[3],
            "generated_date": r[4],
            "extra_fields": extra_fields,
            "file_path": r[6],
            "generated_by": r[7]
        })
    return result

def get_all_generation_logs() -> list[dict]:
    """
    Returns all document generation records in the system, ordered by generated_date DESC.
    extra_fields_json is deserialized back into a python dict.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, candidate_id, document_type, reference_number, generated_date, extra_fields_json, file_path, generated_by
        FROM document_generation_log
        ORDER BY generated_date DESC
    """)
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        try:
            extra_fields = json.loads(r[5]) if r[5] else {}
        except Exception:
            extra_fields = {}
        result.append({
            "id": r[0],
            "candidate_id": r[1],
            "document_type": r[2],
            "reference_number": r[3],
            "generated_date": r[4],
            "extra_fields": extra_fields,
            "file_path": r[6],
            "generated_by": r[7]
        })
    return result


def log_email_dispatch(
    recipient_email: str,
    recipient_name: str = None,
    document_type: str = None,
    subject: str = None,
    attachment_filename: str = None,
    attachment_path: str = None,
    sent_by: str = "HR Desktop",
    status: str = "Success",
    error_message: str = None,
    candidate_id: int = None
) -> int:
    """Records an email dispatch event into email_log. Returns log row ID."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO email_log
        (candidate_id, recipient_email, recipient_name, document_type, subject,
         attachment_filename, attachment_path, sent_by, timestamp, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        recipient_email,
        recipient_name,
        document_type,
        subject,
        attachment_filename,
        attachment_path,
        sent_by,
        now,
        status,
        error_message
    ))
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_email_logs(candidate_id: int = None, limit: int = 200) -> list:
    """
    Returns list of email dispatch logs ordered newest first.
    Optionally filtered by candidate_id.
    """
    conn = get_connection()
    cur = conn.cursor()
    if candidate_id:
        cur.execute("""
            SELECT id, candidate_id, recipient_email, recipient_name, document_type,
                   subject, attachment_filename, attachment_path, sent_by, timestamp,
                   status, error_message
            FROM email_log
            WHERE candidate_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (candidate_id, limit))
    else:
        cur.execute("""
            SELECT id, candidate_id, recipient_email, recipient_name, document_type,
                   subject, attachment_filename, attachment_path, sent_by, timestamp,
                   status, error_message
            FROM email_log
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "candidate_id": r[1],
            "recipient_email": r[2],
            "recipient_name": r[3],
            "document_type": r[4],
            "subject": r[5],
            "attachment_filename": r[6],
            "attachment_path": r[7],
            "sent_by": r[8],
            "timestamp": r[9],
            "status": r[10],
            "error_message": r[11],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Document Staging & Welcome Email Pipeline Functions
# ---------------------------------------------------------------------------

def create_staging_record(
    candidate_id: int,
    document_type: str,
    status: str = "Staged",
    doc_file_path: str = "",
    pdf_file_path: str = None,
    preferred_format: str = "pdf",
    recipient_email: str = "",
    recipient_name: str = "",
    email_subject: str = "",
    email_body: str = "",
    reference_number: str = None,
    extra_fields: dict = None,
    discrepancy_warnings: list = None
) -> int:
    """
    Inserts a newly prepared draft document into document_staging queue.
    Returns the newly generated staging ID.
    """
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    extra_fields_json = (
        json.dumps(extra_fields, ensure_ascii=False)
        if isinstance(extra_fields, (dict, list))
        else (extra_fields or None)
    )
    discrepancy_warnings_json = (
        json.dumps(discrepancy_warnings, ensure_ascii=False)
        if isinstance(discrepancy_warnings, (dict, list))
        else (discrepancy_warnings or None)
    )

    cur.execute("""
        INSERT INTO document_staging (
            candidate_id, document_type, status, doc_file_path, pdf_file_path,
            preferred_format, recipient_email, recipient_name, email_subject, email_body,
            reference_number, extra_fields_json, discrepancy_warnings_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        document_type,
        status,
        doc_file_path,
        pdf_file_path,
        preferred_format,
        recipient_email,
        recipient_name,
        email_subject,
        email_body,
        reference_number,
        extra_fields_json,
        discrepancy_warnings_json,
        now,
        now
    ))
    staging_id = cur.lastrowid
    conn.commit()
    conn.close()
    return staging_id


def get_staging_records(status: str = "Staged") -> list:
    """
    Retrieves records from document_staging with candidate details joined.
    If status is None or 'All', returns all staging records regardless of status.
    Ordered newest first.
    """
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT 
            s.id, s.candidate_id, s.document_type, s.status, s.doc_file_path,
            s.pdf_file_path, s.preferred_format, s.recipient_email, s.recipient_name,
            s.email_subject, s.email_body, s.reference_number, s.extra_fields_json,
            s.discrepancy_warnings_json, s.created_at, s.updated_at, s.dispatched_at,
            c.candidate_name, c.employee_number, c.applied_designation, c.department,
            c.mobile, c.negotiated_salary
        FROM document_staging s
        LEFT JOIN candidates c ON s.candidate_id = c.id
    """
    params = []
    if status and status.lower() != "all":
        query += " WHERE s.status = ?"
        params.append(status)
    query += " ORDER BY s.id DESC"

    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = []
    for r in cur.fetchall():
        record = dict(zip(cols, r))
        if record.get("extra_fields_json"):
            try:
                record["extra_fields"] = json.loads(record["extra_fields_json"])
            except Exception:
                record["extra_fields"] = {}
        else:
            record["extra_fields"] = {}

        if record.get("discrepancy_warnings_json"):
            try:
                record["discrepancy_warnings"] = json.loads(record["discrepancy_warnings_json"])
            except Exception:
                record["discrepancy_warnings"] = []
        else:
            record["discrepancy_warnings"] = []

        rows.append(record)

    conn.close()
    return rows


def get_staging_record_by_id(staging_id: int):
    """
    Retrieves a single staging record by ID with joined candidate information.
    Returns None if not found.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            s.id, s.candidate_id, s.document_type, s.status, s.doc_file_path,
            s.pdf_file_path, s.preferred_format, s.recipient_email, s.recipient_name,
            s.email_subject, s.email_body, s.reference_number, s.extra_fields_json,
            s.discrepancy_warnings_json, s.created_at, s.updated_at, s.dispatched_at,
            c.candidate_name, c.employee_number, c.applied_designation, c.department,
            c.mobile, c.negotiated_salary
        FROM document_staging s
        LEFT JOIN candidates c ON s.candidate_id = c.id
        WHERE s.id = ?
    """, (staging_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    cols = [d[0] for d in cur.description]
    record = dict(zip(cols, row))
    if record.get("extra_fields_json"):
        try:
            record["extra_fields"] = json.loads(record["extra_fields_json"])
        except Exception:
            record["extra_fields"] = {}
    else:
        record["extra_fields"] = {}

    if record.get("discrepancy_warnings_json"):
        try:
            record["discrepancy_warnings"] = json.loads(record["discrepancy_warnings_json"])
        except Exception:
            record["discrepancy_warnings"] = []
    else:
        record["discrepancy_warnings"] = []

    conn.close()
    return record


def update_staging_record(staging_id: int, **kwargs) -> bool:
    """
    Updates fields on an existing staging record.
    Supports extra_fields (dict) and discrepancy_warnings (list).
    """
    if not kwargs:
        return False

    valid_cols = {
        "candidate_id", "document_type", "status", "doc_file_path", "pdf_file_path",
        "preferred_format", "recipient_email", "recipient_name", "email_subject",
        "email_body", "reference_number", "extra_fields_json", "discrepancy_warnings_json",
        "created_at", "updated_at", "dispatched_at"
    }

    updates = {}
    for k, v in kwargs.items():
        if k == "extra_fields":
            updates["extra_fields_json"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
        elif k == "discrepancy_warnings":
            updates["discrepancy_warnings_json"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
        elif k in valid_cols:
            updates[k] = v

    if not updates:
        return False

    if "updated_at" not in updates:
        updates["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    params = list(updates.values())
    params.append(staging_id)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE document_staging SET {set_clause} WHERE id = ?", params)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error updating staging record {staging_id}: {e}")
        return False
    finally:
        conn.close()


def delete_staging_record(staging_id: int) -> bool:
    """
    Deletes a staging record from document_staging by ID.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM document_staging WHERE id = ?", (staging_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error deleting staging record {staging_id}: {e}")
        return False
    finally:
        conn.close()


def update_candidate_welcome_email_status(candidate_id: int, sent: bool = True) -> bool:
    """
    Updates the candidate's welcome email sent status and timestamp.
    """
    conn = get_connection()
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sent_val = 1 if sent else 0
        sent_at = now if sent else None
        conn.execute("""
            UPDATE candidates
            SET welcome_email_sent = ?,
                welcome_email_sent_at = ?,
                last_updated = ?
            WHERE id = ?
        """, (sent_val, sent_at, now, candidate_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating candidate welcome email status: {e}")
        return False
    finally:
        conn.close()


def get_selected_candidates_pending_welcome() -> list:
    """
    Returns non-archived candidates who are in 'Selected' status and have not yet
    received a welcome email (welcome_email_sent is 0 or NULL).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM candidates
        WHERE status = 'Selected'
          AND (welcome_email_sent = 0 OR welcome_email_sent IS NULL)
          AND (archived = 0 OR archived IS NULL)
        ORDER BY id DESC
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def get_dashboard_staging_counts() -> dict:
    """
    Returns counts of documents in staging grouped by status, along with total staged.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM document_staging GROUP BY status")
    counts = {"staged": 0, "approved": 0, "dispatched": 0, "failed": 0, "total": 0}
    total = 0
    for status, count in cur.fetchall():
        key = (status or "").strip().lower()
        counts[key] = count
        total += count
    counts["total"] = total
    counts["Staged"] = counts.get("staged", 0)
    counts["Approved"] = counts.get("approved", 0)
    counts["Dispatched"] = counts.get("dispatched", 0)
    counts["Failed"] = counts.get("failed", 0)
    conn.close()
    return counts


