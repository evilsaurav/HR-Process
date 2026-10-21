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
