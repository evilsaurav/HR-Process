"""
Service: hr_report_exporter.py
Purpose: Generates a polished 1-click Executive HR Daily Briefing report in Excel (.xlsx)
for Directors, Project Leads, and Auditors.
"""

import os
import datetime
from typing import Optional
import pandas as pd
from config import DESKTOP_APP_DIR
from services import dashboard_service
from services import ai_copilot_service
from database import db_manager


def export_daily_executive_summary(target_path: Optional[str] = None) -> str:
    """
    Exports a comprehensive 2-sheet executive summary workbook:
    - Sheet 1: 'Executive Overview' (KPIs, stage breakdown, compliance)
    - Sheet 2: 'Action Priorities' (pending welcome, overdue increments, data hygiene)
    Returns the file path of the created Excel report.
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_slug = now.strftime("%Y%m%d_%H%M%S")

    if not target_path:
        out_dir = os.path.join(DESKTOP_APP_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        target_path = os.path.join(out_dir, f"DFY_Daily_HR_Briefing_{date_slug}.xlsx")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    stats = dashboard_service.get_dashboard_stats()
    overview = dashboard_service.get_status_overview()
    keka_summary = dashboard_service.get_keka_pending_summary()
    inc_due = dashboard_service.get_increment_due_list()
    exp_due = dashboard_service.get_experience_certificate_due_list()
    briefing = ai_copilot_service.generate_daily_operational_briefing()

    # Sheet 1: KPIs
    kpi_data = [
        {"Category": "Report Header", "Metric": "Organization", "Value": "Doctors For You (DFY)"},
        {"Category": "Report Header", "Metric": "Generated Timestamp", "Value": now_str},
        {"Category": "Pipeline Overview", "Metric": "Total Candidates in Pipeline", "Value": overview.get("total", 0)},
        {"Category": "Pipeline Overview", "Metric": "Applied (Initial)", "Value": overview.get("Applied", 0)},
        {"Category": "Pipeline Overview", "Metric": "Interview Stage", "Value": overview.get("Interview", 0)},
        {"Category": "Pipeline Overview", "Metric": "Selected Candidates", "Value": overview.get("Selected", 0)},
        {"Category": "Pipeline Overview", "Metric": "Joined Staff", "Value": overview.get("Joined", 0)},
        {"Category": "Pipeline Overview", "Metric": "Offers Sent", "Value": overview.get("Offer Sent", 0)},
        {"Category": "Operations & Staging", "Metric": "Selected Awaiting Welcome Email", "Value": stats.get("pending_welcome_emails", 0)},
        {"Category": "Operations & Staging", "Metric": "Staged Letters Ready for Final Go", "Value": stats.get("staged_letters_ready", 0)},
        {"Category": "Operations & Staging", "Metric": "Dispatched Today", "Value": stats.get("dispatched_today", 0)},
        {"Category": "Compliance & Due", "Metric": "Annual Increments Overdue (>=365 days)", "Value": len(inc_due.get("overdue", []))},
        {"Category": "Compliance & Due", "Metric": "Annual Increments Upcoming (Next 30 days)", "Value": len(inc_due.get("upcoming", []))},
        {"Category": "Compliance & Due", "Metric": "Relieving / Experience Certificates Due", "Value": len([c for c in exp_due if not c.get("already_issued")])},
        {"Category": "Compliance & Due", "Metric": "Joined Staff Pending Keka Emp ID Sync", "Value": keka_summary.get("count", 0)},
    ]
    df_kpi = pd.DataFrame(kpi_data)

    # Sheet 2: Action Priorities
    action_rows = []
    for idx, b in enumerate(briefing.get("bullets", []), start=1):
        action_rows.append({
            "Priority #": idx,
            "Type": b.get("type", "General").replace("_", " ").title(),
            "Action Item": b.get("headline", ""),
            "Guidance": b.get("subtext", ""),
            "Action Target Page": str(b.get("action_target", "")).upper(),
            "Urgent": "Yes ⚠️" if b.get("is_urgent") else "No"
        })
    df_actions = pd.DataFrame(action_rows)

    with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
        df_kpi.to_excel(writer, sheet_name="Executive Overview", index=False)
        df_actions.to_excel(writer, sheet_name="Action Priorities", index=False)

    return target_path
