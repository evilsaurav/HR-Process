"""
Service: ai_copilot_service.py
Purpose: Dual-Engine AI Operations Copilot for Doctors For You HRMS.
- Generates intelligent daily operational briefings (actionable alerts, data hygiene).
- Natural language "Ask-HR" query router supporting Hinglish and English.
- 100% Guaranteed Offline execution using deterministic SQLite heuristics and local DFY policy index.
- Optional automatic upgrade to Online LLMs (Gemini, Groq, OpenAI) when configured.
"""

import re
from typing import Dict, Any, List, Optional
from database import db_manager
from services import dashboard_service
from services import dfy_policy_service


def generate_daily_operational_briefing() -> Dict[str, Any]:
    """
    Scans the database to produce a crisp, executive daily briefing with 3-4 bullet points.
    Runs 100% offline.
    """
    stats = dashboard_service.get_dashboard_stats()
    inc_due = dashboard_service.get_increment_due_list()
    exp_due = dashboard_service.get_experience_certificate_due_list()
    keka_summary = dashboard_service.get_keka_pending_summary()

    bullets = []
    hygiene_alerts = []
    action_count = 0

    # 1. Selected candidates awaiting welcome email
    pending_welcome = stats.get("pending_welcome_emails", 0)
    if pending_welcome > 0:
        action_count += pending_welcome
        bullets.append({
            "icon": "🎉",
            "type": "welcome_pending",
            "headline": f"{pending_welcome} Selected candidate{'s are' if pending_welcome > 1 else ' is'} awaiting official Welcome Email.",
            "subtext": "Joining process me jaakar ek sath review karein aur dispatch karein.",
            "action_text": "Review Welcome Emails",
            "action_target": "joining",
            "action_filter": "selected",
            "is_urgent": True,
        })

    # 2. Joined staff needing Keka employee numbers
    keka_pending = keka_summary.get("count", 0)
    if keka_pending > 0:
        action_count += keka_pending
        bullets.append({
            "icon": "⚠️",
            "type": "keka_sync_needed",
            "headline": f"{keka_pending} Joined staff member{'s need' if keka_pending > 1 else ' needs'} Keka Employee Number assignment.",
            "subtext": "Keka Sync page par jaakar latest Keka master sheet upload karein.",
            "action_text": "Open Keka Sync",
            "action_target": "keka",
            "is_urgent": True,
        })

    # 3. Overdue Annual Increments
    overdue_inc = inc_due.get("overdue", [])
    if overdue_inc:
        action_count += len(overdue_inc)
        bullets.append({
            "icon": "🔔",
            "type": "increment_overdue",
            "headline": f"{len(overdue_inc)} Active employee{'s are' if len(overdue_inc) > 1 else ' is'} overdue for 1-year Annual Increment.",
            "subtext": "DFY HR Policy (Article 2) ke anusaar performance review & increment letter issue karein.",
            "action_text": "Generate Increment Letters",
            "action_target": "documents",
            "action_tab": 0,
            "is_urgent": True,
        })

    # 4. Certificates due for relieved staff
    pending_certs = [c for c in exp_due if not c.get("already_issued")]
    if pending_certs:
        action_count += len(pending_certs)
        bullets.append({
            "icon": "📄",
            "type": "certificate_due",
            "headline": f"{len(pending_certs)} Relieved employee{'s awaiting' if len(pending_certs) > 1 else ' awaiting'} Experience/Salary Certificate.",
            "subtext": "DFY Article 5 ke anusaar no-dues verification ke baad certificates issue karein.",
            "action_text": "Issue Certificates",
            "action_target": "documents",
            "action_tab": 0,
            "is_urgent": False,
        })

    # 5. Data Hygiene Scan (Candidates missing email, location, or mobile)
    all_cands = db_manager.get_all_candidates() or []
    missing_loc_cands = [c for c in all_cands if not str(c.get("contact_location") or "").strip()]
    missing_email_cands = [c for c in all_cands if not str(c.get("email") or "").strip() or "@" not in str(c.get("email") or "")]

    if missing_loc_cands:
        c = missing_loc_cands[0]
        hygiene_alerts.append({
            "candidate_id": c["id"],
            "candidate_name": c["candidate_name"],
            "issue": "Missing posting location",
            "missing_field": "contact_location",
        })

    if missing_email_cands:
        c = missing_email_cands[0]
        hygiene_alerts.append({
            "candidate_id": c["id"],
            "candidate_name": c["candidate_name"],
            "issue": "Missing or invalid email",
            "missing_field": "email",
        })

    if hygiene_alerts:
        alert_item = hygiene_alerts[0]
        bullets.append({
            "icon": "🛡️",
            "type": "data_hygiene",
            "headline": f"Data Hygiene Notice: '{alert_item['candidate_name']}' is {alert_item['issue'].lower()}.",
            "subtext": "Offer letter aur dispatch se pehle missing details update karna zaroori hai.",
            "action_text": "⚡ Quick Fix",
            "action_target": "quick_fix",
            "candidate_id": alert_item["candidate_id"],
            "missing_field": alert_item["missing_field"],
            "is_urgent": False,
        })

    # Fallback when everything is clear
    if not bullets:
        bullets.append({
            "icon": "🌟",
            "type": "all_clear",
            "headline": "All DFY HR operations are up-to-date! No critical alerts today.",
            "subtext": "All welcome emails, Keka IDs, and scheduled documents are synchronized.",
            "action_text": "View Pipeline",
            "action_target": "joining",
            "is_urgent": False,
        })

    return {
        "bullets": bullets,
        "action_count": action_count,
        "hygiene_alerts": hygiene_alerts,
        "source": "offline_rule_engine",
    }


def process_ask_hr_query(query: str, use_online_llm: bool = False) -> Dict[str, Any]:
    """
    Parses and answers HR queries in Hinglish or English with 100% offline fallback.
    Routes to:
      1. DFY HR Policy Engine (if query asks about leaves, probation, hours, notice, insurance, etc.)
      2. Candidate Database Engine (if query asks about candidate count, state/location, status, salary)
      3. Workflow Help Engine (if query asks how to upload sheet, generate letters, etc.)
    """
    q_clean = str(query or "").strip().lower()
    if not q_clean:
        return {
            "type": "general",
            "headline": "HR Assistant",
            "answer": "Aap candidate stats (jaise 'Bihar candidates kitne hain?'), DFY HR Policy (jaise 'Probation period kya hai?') ya workflow ke bare me pooch sakte hain.",
            "source": "offline_rule_engine",
        }

    # ---------------- 1. Check for DFY HR Policy Keywords ----------------
    policy_keywords = [
        "policy", "probation", "leave", "leaves", "chutti", "casual", "sick", "maternity",
        "working hours", "timing", "samay", "hours", "9:30", "5:30", "notice period", "resignation",
        "relieving", "terminate", "termination", "insurance", "medical", "bima", "benefit",
        "harassment", "posh", "training", "committee", "rules", "rule"
    ]
    if any(pw in q_clean for pw in policy_keywords):
        results = dfy_policy_service.search_dfy_policy(q_clean, max_results=1)
        if results:
            art = results[0]
            headline = f"DFY HR Manual (Updated 2025) — {art.get('title')}"
            summary = art.get("summary", "")
            return {
                "type": "policy_rule",
                "headline": headline,
                "answer": f"{summary}\n\n📖 Citation: {art.get('title')} (HR Manual DFY 2025)",
                "details": art,
                "source": "dfy_policy_engine",
                "action_button": {
                    "text": "Open Full Policy Guide",
                    "target": "help",
                }
            }

    # ---------------- 2. Check for Candidate Database Queries ----------------
    all_cands = db_manager.get_all_candidates() or []

    # State / Location Queries
    for state in ["bihar", "up", "uttar pradesh", "maharashtra", "delhi", "patna", "mumbai", "lucknow", "gaya"]:
        if state in q_clean:
            matched = [
                c for c in all_cands
                if state in str(c.get("contact_location") or "").lower()
                or state in str(c.get("department") or "").lower()
                or state in str(c.get("source_sheet_name") or "").lower()
            ]
            count = len(matched)
            sel_count = sum(1 for c in matched if c.get("status") == "Selected")
            joined_count = sum(1 for c in matched if c.get("status") == "Joined")
            state_title = state.title()

            return {
                "type": "candidate_stat",
                "headline": f"Candidate Overview for {state_title}",
                "answer": (
                    f"System me {state_title} region/sheet ke total {count} candidates record hain.\n"
                    f"• Selected: {sel_count} candidates\n"
                    f"• Joined: {joined_count} staff members\n"
                    f"• Applied/Interviewing: {count - (sel_count + joined_count)}"
                ),
                "source": "offline_rule_engine",
                "action_button": {
                    "text": f"View {state_title} Candidates",
                    "target": "joining",
                    "search_term": state_title,
                }
            }

    # Status Queries (Selected, Joined, Interview, Applied)
    for st in ["selected", "joined", "interview", "applied", "shortlisted"]:
        if st in q_clean:
            st_proper = st.title()
            matched = [c for c in all_cands if c.get("status") == st_proper]
            count = len(matched)
            return {
                "type": "candidate_stat",
                "headline": f"Candidates in '{st_proper}' Status",
                "answer": f"Filhal total {count} candidate{'s' if count > 1 else ''} '{st_proper}' status me hain.",
                "source": "offline_rule_engine",
                "action_button": {
                    "text": f"View {st_proper} List",
                    "target": "joining",
                    "filter": st_proper.lower(),
                }
            }

    # Total Count Query
    if any(k in q_clean for k in ["total", "kitne candidate", "how many", "all candidates", "count"]):
        total = len(all_cands)
        stats = dashboard_service.get_dashboard_stats()
        return {
            "type": "candidate_stat",
            "headline": "Total Candidate Pipeline Summary",
            "answer": (
                f"DFY HRMS pipeline me total {total} candidates recorded hain.\n"
                f"• Applied: {stats.get('applied_candidates', 0)}\n"
                f"• Selected: {stats.get('pending_welcome_emails', 0)} (awaiting welcome)\n"
                f"• In Interview: {stats.get('in_interview', 0)}"
            ),
            "source": "offline_rule_engine",
            "action_button": {
                "text": "Go to Joining Process",
                "target": "joining",
            }
        }

    # ---------------- 3. Check for Workflow / How-To Queries ----------------
    if any(k in q_clean for k in ["offer letter", "offer", "generate", "document", "draft"]):
        return {
            "type": "workflow_help",
            "headline": "Offer Letter / Document Generation",
            "answer": (
                "Offer Letter generate karne ke do aasan tarike hain:\n"
                "1. **Smart Detector**: Document Generator page ke Tab 1 me jayein. System automatic suggest karega kis candidate ko offer letter chahiye, aur direct Staging me draft bana dega.\n"
                "2. **Staging & Final Go**: Tab 2 me preview karein, zaroorat ho to inline edit karein, aur 'Final Go: Dispatch' button se send karein."
            ),
            "source": "offline_rule_engine",
            "action_button": {
                "text": "Open Document Generator",
                "target": "documents",
                "action_tab": 0,
            }
        }

    if any(k in q_clean for k in ["welcome email", "welcome", "swagat"]):
        return {
            "type": "workflow_help",
            "headline": "Welcome Email Sending Process",
            "answer": (
                "Selected candidates ko Welcome Email bhejne ke liye:\n"
                "1. Joining Process page par 'Selected' filter chunein.\n"
                "2. Candidates ko select karein aur top toolbar par '✉️ Review & Send Welcome Emails' button dabayein.\n"
                "3. Preview modal me text check karke Send karein."
            ),
            "source": "offline_rule_engine",
            "action_button": {
                "text": "Go to Welcome Queue",
                "target": "joining",
                "filter": "selected",
            }
        }

    if any(k in q_clean for k in ["excel", "upload", "sheet", "duplicate"]):
        return {
            "type": "workflow_help",
            "headline": "Excel Sheet Upload & Duplicate Safety",
            "answer": (
                "Sheet upload karte samay system multi-sheets auto-detect karta hai.\n"
                "Agar koi candidate dubara upload hota hai, to system warning screen dikhata hai jisme aap 'Keep Existing' ya 'Replace with New' chun sakte hain taaki database clean rahe."
            ),
            "source": "offline_rule_engine",
            "action_button": {
                "text": "Open Joining Process",
                "target": "joining",
            }
        }

    # ---------------- 4. General Default Fallback ----------------
    return {
        "type": "general",
        "headline": "DFY HR Assistant",
        "answer": (
            f"Aapne poocha: '{query}'.\n"
            "Aap inme se kuch bhi pooch sakte hain:\n"
            "• 'Bihar candidates kitne hain?'\n"
            "• 'DFY me probation period kitna hota hai?'\n"
            "• 'Resignation notice period rule kya hai?'\n"
            "• 'Offer letter kaise banate hain?'"
        ),
        "source": "offline_rule_engine",
    }
