"""
Service: smart_rule_detector.py
Purpose: Evaluates employee and candidate records against Keka dates, statuses, and
prior document logs to automatically identify documents that need to be issued:
- Offer Letters (Active joinees without prior offer on file)
- Extension Letters (Contract end / tenure extension dates recorded)
- Experience / Relieving Certificates (Separation / Exit dates recorded)
- Termination Letters (Involuntary separation recorded)
- Increment Letters (Salary or pay grade revisions)
"""

import os
import sys
import re
import datetime
from typing import Dict, Any, List, Optional

try:
    from database import db_manager
except ImportError:
    try:
        from desktop_app.database import db_manager
    except ImportError:
        import db_manager

try:
    from services import ai_service
except ImportError:
    try:
        from desktop_app.services import ai_service
    except ImportError:
        import ai_service


def _parse_date_safe(date_str: Any) -> Optional[datetime.date]:
    """Safely parses various date formats into datetime.date."""
    if not date_str:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    if isinstance(date_str, datetime.datetime):
        return date_str.date()

    val = str(date_str).strip()
    if not val or val.lower() in ("none", "nan", "nat", "null", "undefined", "-"):
        return None

    # Strip time part if present
    val_clean = val.split(" ")[0].strip()

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%b %d, %Y",
        "%B %d, %Y"
    )
    for fmt in formats:
        try:
            return datetime.datetime.strptime(val_clean, fmt).date()
        except ValueError:
            continue
    return None


def _is_populated(val: Any) -> bool:
    """Returns True if the value is non-empty and not a placeholder/null representation."""
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "nat", "null", "undefined", "n/a", "-"):
        return False
    return True


def _has_prior_doc(doc_type_key: str, history: Optional[List[Any]]) -> bool:
    """
    Checks if a document matching doc_type_key has already been recorded in candidate's history.
    History items can be dicts (from document_generation_log or document_staging) or raw string types.
    """
    if not history:
        return False

    key = doc_type_key.lower().strip()

    for item in history:
        if isinstance(item, str):
            item_type = item.lower().strip()
        elif isinstance(item, dict):
            item_type = str(item.get("document_type") or item.get("doc_type") or "").lower().strip()
        else:
            item_type = str(item).lower().strip()

        if not item_type:
            continue

        if key in ("offer", "offer_letter"):
            if any(k in item_type for k in ("offer", "appointment")):
                return True
        elif key in ("experience", "experience_certificate"):
            if any(k in item_type for k in ("experience", "relieving", "salary_cert")):
                return True
        elif key in ("extension", "extension_letter"):
            if "extension" in item_type:
                return True
        elif key in ("increment", "increment_letter"):
            if "increment" in item_type:
                return True
        elif key in ("termination", "termination_letter"):
            if "termination" in item_type:
                return True
        elif key == item_type or key in item_type or item_type in key:
            return True

    return False


def classify_candidate_document_need(
    candidate: Dict[str, Any], history: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates rule hierarchy against a candidate record:
    1. Termination Letter: If termination_type or termination_reason is non-empty
    2. Experience / Relieving Certificate: If exit_date or exit_status is populated
    3. Extension Letter: If extension_of_service_till or extension_of_service_months is populated,
       OR candidate's calculated contract end date is within 30 days
    4. Increment Letter: If pay_grade has changed or salary increment detected
    5. Offer Letter: If candidate status == 'Joined' or employment_status == 'Active',
       and candidate has no prior offer letter in history
    6. Default / None: If none match -> 'none'

    Returns:
    {
        "candidate_id": int | None,
        "employee_number": str | None,
        "name": str,
        "suggested_doc_type": str,
        "trigger_reason": str,
        "priority": "High" | "Normal",
        "missing_fields": List[str]
    }
    """
    if not candidate:
        return {
            "candidate_id": None,
            "employee_number": None,
            "name": "Unknown",
            "suggested_doc_type": "none",
            "trigger_reason": "Profile up to date / No document triggered",
            "priority": "Normal",
            "missing_fields": []
        }

    cand_id = candidate.get("id")

    # If history is not provided, fetch prior generation and staging records for this candidate
    if history is None:
        if cand_id is not None:
            try:
                cand_logs = db_manager.get_generation_history(cand_id) or []
            except Exception:
                cand_logs = []
            try:
                staged = db_manager.get_staging_records(status="Staged") or []
                cand_staged = [s for s in staged if s.get("candidate_id") == cand_id]
            except Exception:
                cand_staged = []
            history = cand_logs + cand_staged
        else:
            history = []

    suggested_type = "none"
    reason = "Profile up to date / No document triggered"

    # Rule 1: Termination Letter
    term_type = str(candidate.get("termination_type") or "").strip()
    term_reason = str(candidate.get("termination_reason") or "").strip()

    is_termination = False
    # If explicitly resignation without involuntary cause, treat as voluntary separation (handled by Rule 2)
    if "resignation" in term_type.lower() and not any(
        k in term_reason.lower()
        for k in ("performance", "misconduct", "disciplinary", "involuntary", "absconding", "termination")
    ):
        is_termination = False
    elif _is_populated(term_type) or _is_populated(term_reason):
        is_termination = True

    if is_termination:
        suggested_type = "termination_letter"
        reason = "Involuntary separation / Termination recorded"

    # Rule 2: Experience / Relieving Certificate
    elif (
        _is_populated(candidate.get("exit_date"))
        or _is_populated(candidate.get("exit_status"))
        or _is_populated(candidate.get("relieving_date"))
        or "resignation" in term_type.lower()
    ):
        suggested_type = "experience_certificate"
        reason = "Employee separation / Exit date recorded"

    # Rule 3: Extension Letter
    elif (
        _is_populated(candidate.get("extension_of_service_till"))
        or _is_populated(candidate.get("extension_of_service_months"))
        or (
            _is_populated(candidate.get("contract_end_date") or candidate.get("contract_end"))
            and _parse_date_safe(candidate.get("contract_end_date") or candidate.get("contract_end")) is not None
            and 0
            <= (
                _parse_date_safe(candidate.get("contract_end_date") or candidate.get("contract_end"))
                - datetime.date.today()
            ).days
            <= 30
        )
    ):
        suggested_type = "extension_letter"
        reason = "Service extension date or tenure recorded"

    # Rule 4: Increment Letter
    elif bool(
        candidate.get("pay_grade_changed")
        or candidate.get("pay_grade_revised")
        or candidate.get("pay_grade_change")
        or candidate.get("salary_increment")
        or candidate.get("increment_detected")
        or candidate.get("revised_salary")
        or candidate.get("increment_amount")
        or candidate.get("has_increment")
    ):
        suggested_type = "increment_letter"
        reason = "Salary/Pay Grade revision detected"

    # Rule 5: Offer Letter
    elif (
        (
            str(candidate.get("status") or "").strip().lower() in ("joined", "active", "working")
            or str(candidate.get("employment_status") or "").strip().lower() in ("active", "working")
        )
        and not _has_prior_doc("offer_letter", history)
    ):
        suggested_type = "offer_letter"
        reason = "Active joinee without prior offer letter on file"

    # Rule 6: Default / None
    else:
        suggested_type = "none"
        reason = "Profile up to date / No document triggered"

    # Priority determination
    priority = "High" if suggested_type in ["termination_letter", "offer_letter"] else "Normal"

    # Data completeness audit
    audit_warnings = []
    if suggested_type != "none":
        try:
            audit_warnings = ai_service.audit_candidate_data_completeness(candidate, suggested_type)
        except Exception:
            audit_warnings = []

    cand_name = candidate.get("candidate_name") or candidate.get("display_name")
    if not cand_name:
        cand_name = candidate.get("name") or "Unknown"

    return {
        "candidate_id": cand_id,
        "employee_number": candidate.get("employee_number"),
        "name": cand_name,
        "suggested_doc_type": suggested_type,
        "trigger_reason": reason,
        "priority": priority,
        "missing_fields": audit_warnings
    }


def scan_all_candidates_for_document_needs() -> List[Dict[str, Any]]:
    """
    Scans all active candidates in the database against smart rules and prior document history.
    Returns a list of actionable recommendation dictionaries for candidates requiring attention.
    Entries where suggested_doc_type is 'none' or where the suggested document was already
    generated or currently staged are excluded.
    """
    try:
        from database import db_manager
    except ImportError:
        import db_manager

    # 1. Fetch active candidates (exclude archived)
    try:
        candidates = db_manager.get_all_candidates(include_archived=False)
    except Exception as e:
        print(f"Error fetching candidates for smart detector: {e}")
        return []

    # 2. Fetch prior generation logs and staged records
    try:
        all_logs = db_manager.get_all_generation_logs() or []
    except Exception:
        all_logs = []

    try:
        all_staged = db_manager.get_staging_records(status="Staged") or []
    except Exception:
        all_staged = []

    # Map history by candidate_id for O(1) lookups
    from collections import defaultdict
    history_map = defaultdict(list)
    for log in all_logs:
        cid = log.get("candidate_id")
        if cid is not None:
            history_map[cid].append(log)

    for staged in all_staged:
        cid = staged.get("candidate_id")
        if cid is not None:
            history_map[cid].append(staged)

    actionable_suggestions = []
    for cand in candidates:
        cid = cand.get("id")
        cand_history = history_map.get(cid, [])
        recommendation = classify_candidate_document_need(cand, history=cand_history)
        doc_type = recommendation.get("suggested_doc_type")

        # Exclude 'none'
        if not doc_type or doc_type == "none":
            continue

        # If the suggested document is already in history (generated or currently staged),
        # skip it so we don't produce duplicate suggestions
        if _has_prior_doc(doc_type, cand_history):
            continue

        actionable_suggestions.append(recommendation)

    return actionable_suggestions
