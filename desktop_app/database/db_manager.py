import sqlite3
import datetime
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
            last_updated TEXT
        )
    """)

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_number_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            format_template TEXT,
            padding_width INTEGER,
            range_start INTEGER,
            range_end INTEGER,
            current_number INTEGER
        )
    """)

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

def get_all_candidates(search_term="", status_filter="All"):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM candidates WHERE 1=1"
    params = []
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

def delete_candidate(candidate_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
    conn.commit()
    conn.close()


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


def save_reference_config(format_template: str, padding_width: int, range_start: int, range_end: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT range_start, current_number FROM reference_number_config WHERE id = 1")
    existing = cur.fetchone()

    if existing and existing[0] == range_start:
        current_num = existing[1]
    else:
        current_num = range_start

    conn.execute("""
        INSERT INTO reference_number_config (id, format_template, padding_width, range_start, range_end, current_number)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            format_template=excluded.format_template,
            padding_width=excluded.padding_width,
            range_start=excluded.range_start,
            range_end=excluded.range_end,
            current_number=excluded.current_number
    """, (format_template, padding_width, range_start, range_end, current_num))
    conn.commit()
    conn.close()

def get_reference_config():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT format_template, padding_width, range_start, range_end, current_number FROM reference_number_config WHERE id=1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "format_template": row[0],
        "padding_width": row[1],
        "range_start": row[2],
        "range_end": row[3],
        "current_number": row[4]
    }

def preview_next_reference():
    from services.reference_number_service import format_reference_number
    config = get_reference_config()
    if not config:
        return None
    if config["current_number"] > config["range_end"]:
        return {"exhausted": True, "remaining": 0, "total": config["range_end"] - config["range_start"] + 1}
    formatted = format_reference_number(config["format_template"], config["padding_width"], config["current_number"])
    remaining = config["range_end"] - config["current_number"] + 1
    total = config["range_end"] - config["range_start"] + 1
    return {"exhausted": False, "formatted": formatted, "remaining": remaining, "total": total}

def consume_next_reference():
    config = get_reference_config()
    if not config:
        return None, "No reference number configuration found. Please set it up in Settings."
    if config["current_number"] > config["range_end"]:
        return None, "Reference number range exhausted. Please add a new range in Settings."
    from services.reference_number_service import format_reference_number
    formatted = format_reference_number(config["format_template"], config["padding_width"], config["current_number"])
    conn = get_connection()
    conn.execute("UPDATE reference_number_config SET current_number = current_number + 1 WHERE id=1")
    conn.commit()
    conn.close()
    return formatted, None
