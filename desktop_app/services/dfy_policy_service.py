"""
Service: dfy_policy_service.py
Purpose: Fast, 100% offline knowledge search & citation engine for the
official Doctors For You HR Manual (Updated 2025).
Provides instant policy lookups, Article citations, and plain-Hinglish
explanations for non-technical HR managers and field coordinators.
"""

import os
import json
import re
from typing import List, Dict, Optional, Any

KNOWLEDGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge",
    "dfy_hr_policy.json"
)

# In-memory cache
_POLICY_DATA: Optional[Dict[str, Any]] = None


def _load_policy_data() -> Dict[str, Any]:
    global _POLICY_DATA
    if _POLICY_DATA is not None:
        return _POLICY_DATA

    if not os.path.exists(KNOWLEDGE_PATH):
        return {"source": "HR Manual DFY 2025", "total_articles": 0, "articles": []}

    try:
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            _POLICY_DATA = json.load(f)
            return _POLICY_DATA
    except Exception as e:
        print("Error reading DFY policy knowledge JSON:", e)
        return {"source": "HR Manual DFY 2025", "total_articles": 0, "articles": []}


def get_all_policy_articles() -> List[Dict[str, Any]]:
    """Returns all 10 official DFY HR Manual Articles."""
    data = _load_policy_data()
    return data.get("articles", [])


def get_article_by_number(num: int) -> Optional[Dict[str, Any]]:
    """Fetches a specific Article by number (1 to 10)."""
    articles = get_all_policy_articles()
    for art in articles:
        if art.get("article_num") == num:
            return art
    return None


def search_dfy_policy(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the official DFY HR Manual using multi-tier weighted keyword matching.
    Works 100% offline without needing internet or an AI API key.
    Returns list of matched articles sorted by relevance score.
    """
    if not query or not query.strip():
        return []

    articles = get_all_policy_articles()
    tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) >= 2]
    if not tokens:
        return []

    scored_results = []
    for art in articles:
        score = 0.0
        num = art.get("article_num", 0)
        title_lower = str(art.get("title", "")).lower()
        summary_lower = str(art.get("summary", "")).lower()
        full_text_lower = str(art.get("full_text", "")).lower()
        keywords = [k.lower() for k in art.get("keywords", [])]

        # Specific high-relevance intent mappings
        if any(tok in ("probation", "confirmation") for tok in tokens) and num in (2, 3):
            score += 25.0
        if any(tok in ("leave", "leaves", "chutti", "casual", "sick", "maternity", "holiday") for tok in tokens) and num == 4:
            score += 25.0
        if any(tok in ("hour", "hours", "timing", "time", "samay", "9:30", "5:30") for tok in tokens) and num == 4:
            score += 25.0
        if any(tok in ("notice", "resignation", "terminate", "termination", "relieving", "settlement", "exit") for tok in tokens) and num == 5:
            score += 25.0
        if any(tok in ("insurance", "medical", "bima", "benefit", "benefits", "hospital") for tok in tokens) and num == 6:
            score += 25.0
        if any(tok in ("harassment", "posh", "safety", "complaint") for tok in tokens) and num == 7:
            score += 25.0
        if any(tok in ("training", "capacity", "learning") for tok in tokens) and num == 8:
            score += 25.0
        if any(tok in ("committee", "appeal", "appeals") for tok in tokens) and num == 9:
            score += 25.0
        if any(tok in ("confidential", "social", "media", "conduct", "rules") for tok in tokens) and num == 10:
            score += 25.0

        # General token matching
        for tok in tokens:
            # Keyword exact or substring match
            for kw in keywords:
                if tok in kw:
                    score += 6.0
                    break
            # Title match
            if tok in title_lower:
                score += 4.0
            # Summary match
            if tok in summary_lower:
                score += 2.0
            # Full text count
            if tok in full_text_lower:
                score += 1.0

        if score > 0:
            item = dict(art)
            item["relevance_score"] = round(score, 1)
            scored_results.append(item)

    scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored_results[:max_results]


def get_quick_rule(rule_key: str) -> Optional[Dict[str, Any]]:
    """
    Returns pre-curated quick-reference rule cards for the top 5 pinned operational topics.
    Designed for 1-click access by non-technical HR staff.
    """
    key = str(rule_key or "").strip().lower()

    quick_rules = {
        "probation": {
            "key": "probation",
            "headline": "Probation Period & Performance Review",
            "article_ref": 2,
            "article_title": "Article 2. Policies & General Conduct",
            "plain_hinglish": "Har naye employee ka initial probation period hota hai. Probation complete hone par manager ke sath structured review hota hai aur satisfactory performance par employee confirm hota hai.",
            "key_points": [
                "Full-time staff (minimum 48 hours/week) and part-time staff dono par applicable.",
                "Probation completion par written review report mandatory hai.",
                "Confirmation letter issue hone ke baad hi official regular status milta hai."
            ],
            "action_tip": "Document Generator me jaakar confirmation ya extension letter select karein."
        },
        "leaves": {
            "key": "leaves",
            "headline": "Holidays, Casual & Sick Leaves Policy",
            "article_ref": 4,
            "article_title": "Article 4. Holidays and Leaves",
            "plain_hinglish": "Staff ko yearly Casual Leave (CL) aur Medical/Sick Leave (SL) milti hain. Female employees ko Maternity Leave ki suvidha milti hai. Leave application pehle se approve karwana mandatory hai.",
            "key_points": [
                "Casual leave lene se pehle supervisor ki prior written approval zaroori hai.",
                "Emergency medical leave ke liye doctor certificate submit karna hota hai.",
                "Unapproved absenteeism salary deduction ka reason ban sakti hai."
            ],
            "action_tip": "Emergency leave records ko Keka leave calendar se sync rakhein."
        },
        "working_hours": {
            "key": "working_hours",
            "headline": "Official Office & Field Working Hours",
            "article_ref": 4,
            "article_title": "Article 4. Hours of Work",
            "plain_hinglish": "Doctors For You ke regular working hours Monday se Saturday subah 9:30 AM se shaam 5:30 PM (48 hours per week) hain.",
            "key_points": [
                "Regular duty timing: 9:30 AM – 5:30 PM.",
                "Field disaster response / medical camps me emergency operational schedule follow hota hai.",
                "Attendance biometrics ya official register me mark karna mandatory hai."
            ],
            "action_tip": "Offer aur Appointment letter me standard 9:30 AM - 5:30 PM clause automatic add hota hai."
        },
        "notice_period": {
            "key": "notice_period",
            "headline": "Resignation, Notice Period & Relieving Rules",
            "article_ref": 5,
            "article_title": "Article 5. Termination and Resignation",
            "plain_hinglish": "Resignation dene par employment contract ke anusaar notice period serve karna mandatory hai. No-dues aur handover complete hone ke baad hi official Relieving & Experience Certificate issue hota hai.",
            "key_points": [
                "Notice period serve na karne par notice-pay recovery ki ja sakti hai.",
                "Handover of DFY assets (laptop, ID card, files) mandatory hai.",
                "Final settlement finance team dwara 30-45 days me process hota hai."
            ],
            "action_tip": "Relieved employee ka certificate generate karne ke liye Document Generator me Relieving Certificate chunein."
        },
        "insurance": {
            "key": "insurance",
            "headline": "Group Medical & Life Insurance Benefits",
            "article_ref": 6,
            "article_title": "Article 6. Employee Benefits & Insurance",
            "plain_hinglish": "Doctors For You apne eligible staff ko Group Health Medical Insurance aur accidental life insurance cover provide karta hai.",
            "key_points": [
                "Eligible employees joining ke 30 days ke andar group policy me enroll ho jate hain.",
                "Medical emergencies me designated network hospitals me cashless treatment available hota hai.",
                "Official project duty travel expenses DFY reimbursement policy ke tahat claim kiye ja sakte hain."
            ],
            "action_tip": "New joinee ke welcome email me insurance enrollment guidelines shamil karein."
        }
    }

    return quick_rules.get(key)
