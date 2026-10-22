"""
Service: dashboard_service.py
Purpose: Aggregates real-time metrics and operational action queues for HR:
- Status overview counts across candidate pipeline
- Experience & Salary certificates due for relieved employees
- Upcoming & overdue annual increment reminders
- Pending Keka HRMS sync tracking
"""

import datetime
from typing import Dict, List, Any, Optional

from config import STATUS_OPTIONS
from database import db_manager

try:
    from services import smart_rule_detector
except ImportError:
    try:
        from desktop_app.services import smart_rule_detector
    except ImportError:
        smart_rule_detector = None


def _parse_date_safe(date_str: Any) -> Optional[datetime.date]:
    """Safely parses various date formats into datetime.date."""
    if not date_str:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    if isinstance(date_str, datetime.datetime):
        return date_str.date()

    s = str(date_str).strip()
    if not s or s.lower() in ["none", "nan", "null", "nat"]:
        return None

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d %B %Y", "%d %b %Y",
        "%Y-%m-%d %H:%M:%S"
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    try:
        import pandas as pd
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if dt is not pd.NaT and not pd.isna(dt):
            return dt.to_pydatetime().date()
    except Exception:
        pass

    return None


def get_status_overview() -> Dict[str, int]:
    """
    Returns counts per status from config.STATUS_OPTIONS plus a 'total' key.
    """
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM candidates GROUP BY status")
    rows = cur.fetchall()
    conn.close()

    counts = {opt: 0 for opt in STATUS_OPTIONS}
    total = 0
    for status, count in rows:
        st_clean = str(status).strip() if status else "Applied"
        if st_clean in counts:
            counts[st_clean] = count
        else:
            counts[st_clean] = count
        total += count

    counts["total"] = total
    return counts


def get_experience_certificate_due_list() -> List[Dict[str, Any]]:
    """
    Returns candidates who have a relieving_date set (have left),
    flagging whether an experience/salary certificate was already issued.
    """
    conn = db_manager.get_connection()
    cur = conn.cursor()
    query = """
        SELECT id, candidate_name, mobile, applied_designation, relieving_date
        FROM candidates
        WHERE relieving_date IS NOT NULL
          AND TRIM(relieving_date) != ''
          AND LOWER(TRIM(relieving_date)) NOT IN ('none', 'nan', 'null')
        ORDER BY id DESC
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        cid = r[0]
        history = db_manager.get_generation_history(cid)
        already_issued = any(
            h.get("document_type") in ["experience", "experience_certificate", "salary", "salary_certificate"]
            for h in history
        )

        result.append({
            "candidate_id": cid,
            "candidate_name": r[1] or "Unknown",
            "mobile": r[2] or "-",
            "applied_designation": r[3] or "-",
            "relieving_date": r[4] or "-",
            "already_issued": already_issued
        })

    return result


def get_increment_due_list() -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculates upcoming (335 <= days < 365) and overdue (days >= 365) annual increments
    for currently active joined employees (status='Joined' and relieving_date is empty).
    Flags 'already_issued'=True if an increment document was generated within the last 370 days.
    """
    conn = db_manager.get_connection()
    cur = conn.cursor()
    query = """
        SELECT id, candidate_name, mobile, applied_designation, date_joined, relieving_date
        FROM candidates
        WHERE status = 'Joined'
          AND (relieving_date IS NULL OR TRIM(relieving_date) = '' OR LOWER(TRIM(relieving_date)) IN ('none', 'nan', 'null'))
          AND date_joined IS NOT NULL
          AND TRIM(date_joined) != ''
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    today = datetime.date.today()
    upcoming = []
    overdue = []

    for r in rows:
        cid, name, mobile, desig, date_joined_raw, _ = r
        dt_joined = _parse_date_safe(date_joined_raw)
        if not dt_joined:
            continue

        days_since = (today - dt_joined).days

        # Check if increment letter was issued in the last 370 days
        history = db_manager.get_generation_history(cid)
        already_issued = False
        for h in history:
            if h.get("document_type") in ["increment", "increment_letter"]:
                gen_date_raw = h.get("generated_date")
                gen_date = _parse_date_safe(gen_date_raw)
                if gen_date and (today - gen_date).days <= 370:
                    already_issued = True
                    break

        item = {
            "candidate_id": cid,
            "candidate_name": name or "Unknown",
            "mobile": mobile or "-",
            "applied_designation": desig or "-",
            "date_joined": date_joined_raw,
            "days_since_joining": days_since,
            "already_issued": already_issued
        }

        if 335 <= days_since < 365:
            upcoming.append(item)
        elif days_since >= 365:
            overdue.append(item)

    # Sort descending by days since joining (most urgent first)
    upcoming.sort(key=lambda x: x["days_since_joining"], reverse=True)
    overdue.sort(key=lambda x: x["days_since_joining"], reverse=True)

    return {
        "upcoming": upcoming,
        "overdue": overdue
    }


def get_keka_pending_summary() -> Dict[str, Any]:
    """
    Returns count and list of joined candidates awaiting Keka Employee Number sync.
    """
    pending = db_manager.get_candidates_pending_keka_sync()
    return {
        "count": len(pending),
        "candidates": pending
    }


def get_recent_email_dispatches(limit: int = 5) -> List[Dict[str, Any]]:
    """Returns recent email dispatch logs ordered newest first."""
    try:
        return db_manager.get_email_logs(limit=limit)
    except Exception:
        return []


def get_recent_document_generations(limit: int = 5) -> List[Dict[str, Any]]:
    """Returns recent document generation logs ordered newest first with candidate details."""
    try:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT d.id, d.candidate_id, c.candidate_name, d.document_type,
                   d.reference_number, d.generated_date, d.file_path, d.generated_by
            FROM document_generation_log d
            LEFT JOIN candidates c ON d.candidate_id = c.id
            ORDER BY d.id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "candidate_id": r[1],
                "candidate_name": r[2] or "Unknown",
                "document_type": r[3] or "-",
                "reference_number": r[4] or "-",
                "generated_date": r[5] or "-",
                "file_path": r[6] or "",
                "generated_by": r[7] or "HR Desktop",
            }
            for r in rows
        ]
    except Exception:
        return []


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Aggregates high-level executive dashboard metrics:
    - pending_welcome_emails: Candidates where status == 'Selected' and welcome email not sent
    - letters_to_generate: Actionable suggestions identified by smart rule detector
    - staged_letters_ready: Count of records in document_staging with status == 'Staged'
    - dispatched_today: Count of records in email_log with status in ('Sent', 'Success') and today's date
    - Pipeline status counts: total_candidates, selected_candidates, in_interview, in_pipeline, joined_candidates, etc.
    - Life-cycle due counts: exp_due_count, increment_due_count, keka_pending_count
    """
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()

    # 1. Pending Welcome Emails
    cur.execute("""
        SELECT COUNT(*) FROM candidates
        WHERE status = 'Selected'
          AND (welcome_email_sent = 0 OR welcome_email_sent IS NULL)
          AND (archived = 0 OR archived IS NULL)
    """)
    row_welcome = cur.fetchone()
    pending_welcome_emails = row_welcome[0] if row_welcome else 0

    # 2. Letters to Generate (Smart Rule Detector)
    letters_to_generate = 0
    try:
        detector = smart_rule_detector
        if not detector:
            try:
                from services import smart_rule_detector as s_det
                detector = s_det
            except ImportError:
                try:
                    from desktop_app.services import smart_rule_detector as s_det
                    detector = s_det
                except ImportError:
                    detector = None
        if detector and hasattr(detector, "scan_all_candidates_for_document_needs"):
            needs = detector.scan_all_candidates_for_document_needs()
            letters_to_generate = len(needs) if needs else 0
    except Exception as ex:
        print(f"Error scanning candidates for document needs: {ex}")
        letters_to_generate = 0

    # 3. Staged Letters Ready
    try:
        cur.execute("SELECT COUNT(*) FROM document_staging WHERE status = 'Staged'")
        row_staged = cur.fetchone()
        staged_letters_ready = row_staged[0] if row_staged else 0
    except Exception:
        staged_letters_ready = 0

    # 4. Dispatched Today
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    try:
        cur.execute("""
            SELECT COUNT(*) FROM email_log
            WHERE (status = 'Sent' OR status = 'Success' OR LOWER(status) IN ('sent', 'success'))
              AND (timestamp LIKE ? OR SUBSTR(timestamp, 1, 10) = ?)
        """, (f"{today_str}%", today_str))
        row_disp = cur.fetchone()
        dispatched_today = row_disp[0] if row_disp else 0
    except Exception:
        dispatched_today = 0

    # 5. Candidate Pipeline Breakdown
    cur.execute("""
        SELECT status, COUNT(*) FROM candidates
        WHERE (archived = 0 OR archived IS NULL)
        GROUP BY status
    """)
    status_rows = cur.fetchall()
    conn.close()

    status_counts = {opt: 0 for opt in STATUS_OPTIONS}
    status_counts["Selected"] = 0
    total_candidates = 0
    for st, count in status_rows:
        st_clean = str(st).strip() if st else "Applied"
        status_counts[st_clean] = count
        total_candidates += count

    selected_candidates = status_counts.get("Selected", 0)
    in_interview = status_counts.get("Interview", 0)
    applied_candidates = status_counts.get("Applied", 0)
    shortlisted_candidates = status_counts.get("Shortlisted", 0)
    offer_sent_candidates = status_counts.get("Offer Sent", 0)
    joined_candidates = status_counts.get("Joined", 0)
    rejected_candidates = status_counts.get("Rejected", 0)
    in_pipeline = in_interview + shortlisted_candidates + applied_candidates

    # 6. Life-cycle Due Counts
    exp_due = get_experience_certificate_due_list()
    exp_due_count = len(exp_due)

    inc_due = get_increment_due_list()
    inc_upcoming_count = len(inc_due.get("upcoming", []))
    inc_overdue_count = len(inc_due.get("overdue", []))
    increment_due_count = inc_upcoming_count + inc_overdue_count

    keka_summary = get_keka_pending_summary()
    keka_pending_count = keka_summary.get("count", 0)

    return {
        "pending_welcome_emails": pending_welcome_emails,
        "letters_to_generate": letters_to_generate,
        "staged_letters_ready": staged_letters_ready,
        "dispatched_today": dispatched_today,
        "total_candidates": total_candidates,
        "selected_candidates": selected_candidates,
        "in_interview": in_interview,
        "in_pipeline": in_pipeline,
        "joined_candidates": joined_candidates,
        "applied_candidates": applied_candidates,
        "shortlisted_candidates": shortlisted_candidates,
        "offer_sent_candidates": offer_sent_candidates,
        "rejected_candidates": rejected_candidates,
        "status_overview": status_counts,
        "exp_due_count": exp_due_count,
        "increment_due_count": increment_due_count,
        "keka_pending_count": keka_pending_count,
    }


def get_department_breakdown() -> Dict[str, Any]:
    """
    Returns candidate metrics grouped by department / source sheet (e.g. PPSA UP, Bihar, Maharashtra).
    """
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COALESCE(NULLIF(department, ''), NULLIF(source_sheet_name, ''), 'General / Unassigned') as dept_name,
            COUNT(*) as total_count,
            SUM(CASE WHEN status = 'Selected' THEN 1 ELSE 0 END) as sel_count,
            SUM(CASE WHEN status = 'Joined' THEN 1 ELSE 0 END) as join_count,
            SUM(CASE WHEN status = 'Interview' THEN 1 ELSE 0 END) as int_count
        FROM candidates
        WHERE (archived = 0 OR archived IS NULL)
        GROUP BY dept_name
        ORDER BY total_count DESC
    """)
    rows = cur.fetchall()
    conn.close()

    result = {}
    for r in rows:
        dname = str(r[0]).strip()
        tot = r[1] or 0
        sel = r[2] or 0
        joined = r[3] or 0
        interview = r[4] or 0
        result[dname] = {
            "total": tot,
            "selected": sel,
            "joined": joined,
            "interview": interview,
            "in_pipeline": tot - joined
        }
    return result


def get_pipeline_funnel_summary() -> Dict[str, int]:
    """
    Returns sequential funnel stage counts for quick executive overview.
    """
    overview = get_status_overview()
    return {
        "Applied": overview.get("Applied", 0),
        "Interview": overview.get("Interview", 0),
        "Selected": overview.get("Selected", 0),
        "Offer Sent": overview.get("Offer Sent", 0),
        "Joined": overview.get("Joined", 0),
        "Rejected": overview.get("Rejected", 0),
        "total": overview.get("total", 0),
    }
