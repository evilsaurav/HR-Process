"""
Page: dashboard_page.py
Purpose: Executive HR Command Center & Operations Dashboard.
Redesigned with a compact 3-Tier Bento Layout:
- Tier 1: 4 prominent interactive Action Cards with 1-click deep navigation.
- Tier 2: Left 55% Bento = AI Operations Copilot (Daily Briefing, Top 5 Policy Chips, Ask-HR Search, 1-Click Hygiene Fixer).
          Right 45% Bento = HRMS Health, Pipeline Funnel, Keka Sync Status, Joinee Countdown, Executive Summary Export.
- Tier 3: Unified 3-Tab Operations Hub (Due Reminders | Operations Log | Sheet & Batch Breakdown).
~70% vertical space reduction compared to the legacy stacked tables layout.
"""

import os
import datetime
from typing import Optional, Callable, Dict, Any, List
import flet as ft

from config import PRIMARY_COLOR, STATUS_OPTIONS, DESKTOP_APP_DIR, ASSETS_DIR
from services import dashboard_service
from services import excel_export_service
from services import ai_copilot_service
from services import dfy_policy_service
from services import hr_report_exporter
from database import db_manager
from utils import ui_theme


def dashboard_view(page: ft.Page, on_navigate: Optional[Callable] = None):
    # Feedback helper
    def show_message(text: str, is_success: bool = True):
        try:
            page.open(ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED
            ))
            page.update()
        except Exception:
            pass

    # Navigation trigger helper supporting both callback and page session
    def trigger_navigate(target: str, **kwargs):
        nav_fn = on_navigate or getattr(page, "on_navigate", None)
        if not nav_fn and hasattr(page, "session"):
            try:
                nav_fn = page.session.get("navigate_to")
            except Exception:
                pass
        if callable(nav_fn):
            try:
                nav_fn(target, **kwargs)
            except TypeError:
                nav_fn(target)
        else:
            show_message(f"Navigating to {target.title()}...", True)

    # 1. Fetch Real-Time Operational Data
    stats = dashboard_service.get_dashboard_stats()
    overview = dashboard_service.get_status_overview()
    funnel = dashboard_service.get_pipeline_funnel_summary()
    dept_breakdown = dashboard_service.get_department_breakdown()
    exp_due_list = dashboard_service.get_experience_certificate_due_list()
    inc_due = dashboard_service.get_increment_due_list()
    keka_summary = dashboard_service.get_keka_pending_summary()
    recent_emails = dashboard_service.get_recent_email_dispatches(limit=5)
    recent_gens = dashboard_service.get_recent_document_generations(limit=5)
    briefing_data = ai_copilot_service.generate_daily_operational_briefing()
    upcoming_joinees = db_manager.get_upcoming_joinees(days=7)

    # =========================================================================
    # TIER 1: TOP 4 PROMINENT ACTION CARDS
    # =========================================================================

    welcome_count_text = ft.Text(str(stats.get("pending_welcome_emails", 0)), size=30, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)
    letters_count_text = ft.Text(str(stats.get("letters_to_generate", 0)), size=30, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)
    staging_count_text = ft.Text(str(stats.get("staged_letters_ready", 0)), size=30, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)
    pipeline_count_text = ft.Text(str(stats.get("in_pipeline", 0)), size=30, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)

    def build_action_card(title: str, subtitle: str, count_ctrl: ft.Text, icon, accent_color: str, bg_color: str, border_color: str, on_click):
        icon_box = ft.Container(
            content=ft.Icon(icon, color=accent_color, size=22),
            padding=8,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.18, accent_color),
        )

        action_pill = ft.Container(
            content=ft.Row([
                ft.Text("Action", size=10, weight=ft.FontWeight.BOLD, color=accent_color),
                ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=11, color=accent_color),
            ], spacing=2, tight=True),
            padding=ft.padding.symmetric(horizontal=6, vertical=3),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.12, accent_color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, accent_color)),
        )

        card_content = ft.Column([
            ft.Row([icon_box, ft.Container(expand=True), action_pill], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=2),
            count_ctrl,
            ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(subtitle, size=11, color=ui_theme.COLOR_TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ], spacing=3)

        card = ft.Container(
            content=card_content,
            padding=14,
            border_radius=12,
            bgcolor=bg_color,
            border=ft.Border.all(1.5, border_color),
            shadow=[ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK), offset=ft.Offset(0, 3))],
            expand=1,
            on_click=on_click,
            animate_scale=ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT),
        )

        def on_hover(e):
            card.scale = 1.02 if e.data == "true" else 1.0
            try:
                card.update()
            except Exception:
                pass

        card.on_hover = on_hover
        return card

    card_welcome = build_action_card(
        title="Pending Welcome Emails",
        subtitle="Selected awaiting welcome",
        count_ctrl=welcome_count_text,
        icon=ft.Icons.MARK_EMAIL_UNREAD_ROUNDED,
        accent_color="#F59E0B",
        bg_color="#1F1A12",
        border_color="#F59E0B",
        on_click=lambda e: trigger_navigate("joining", filter="selected"),
    )

    card_letters = build_action_card(
        title="Letters to Generate",
        subtitle="Staff needing letters detected",
        count_ctrl=letters_count_text,
        icon=ft.Icons.AUTO_AWESOME_ROUNDED,
        accent_color="#3B82F6",
        bg_color="#131B2E",
        border_color="#3B82F6",
        on_click=lambda e: trigger_navigate("documents", tab=0),
    )

    card_staging = build_action_card(
        title="Staged Ready for Final Go",
        subtitle="Draft letters ready to dispatch",
        count_ctrl=staging_count_text,
        icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
        accent_color="#10B981",
        bg_color="#10231D",
        border_color="#10B981",
        on_click=lambda e: trigger_navigate("documents", tab=1),
    )

    card_pipeline = build_action_card(
        title="In Pipeline",
        subtitle=f"{stats.get('in_interview', 0)} Interview • {stats.get('applied_candidates', 0)} Applied",
        count_ctrl=pipeline_count_text,
        icon=ft.Icons.PEOPLE_ALT_ROUNDED,
        accent_color="#8B5CF6",
        bg_color="#1E152E",
        border_color="#8B5CF6",
        on_click=lambda e: trigger_navigate("joining"),
    )

    action_cards_row = ft.Row([card_welcome, card_letters, card_staging, card_pipeline], spacing=12)

    # =========================================================================
    # 1-CLICK DATA HYGIENE FIXER MODAL
    # =========================================================================
    def open_quick_fix_dialog(candidate_id: int, missing_field: str, candidate_name: str):
        val_input = ft.TextField(
            label=f"Enter {missing_field.replace('_', ' ').title()}",
            autofocus=True,
            border_radius=8,
            border_color=ui_theme.COLOR_CARD_BORDER,
            focused_border_color=ui_theme.COLOR_PRIMARY_LIGHT,
        )

        def do_save_fix(e):
            val = val_input.value.strip()
            if not val:
                show_message("Please enter a valid value.", False)
                return
            db_manager.update_candidate(candidate_id, {missing_field: val})
            page.close(dlg)
            show_message(f"Updated {missing_field.title()} for '{candidate_name}' successfully!", True)
            refresh_dashboard()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.AUTO_FIX_HIGH_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=24),
                ft.Text(f"Quick Fix: {candidate_name}", weight=ft.FontWeight.BOLD, size=16),
            ], spacing=8),
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text(f"Complete the missing '{missing_field.replace('_', ' ')}' for this candidate to maintain 100% data hygiene.", size=13, color=ui_theme.COLOR_TEXT_SECONDARY),
                    ft.Container(height=4),
                    val_input,
                ], spacing=10, tight=True),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                ft.ElevatedButton("Save & Update", bgcolor=PRIMARY_COLOR, color=ft.Colors.WHITE, on_click=do_save_fix),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()

    # =========================================================================
    # POLICY QUICK RULE DIALOG
    # =========================================================================
    def show_policy_modal(rule_key: str):
        rule = dfy_policy_service.get_quick_rule(rule_key)
        if not rule:
            return

        points = [
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ui_theme.COLOR_SUCCESS, size=14),
                ft.Text(p, size=12, color=ui_theme.COLOR_TEXT_PRIMARY, expand=True),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
            for p in rule.get("key_points", [])
        ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=24),
                ft.Text(rule["headline"], weight=ft.FontWeight.BOLD, size=16),
            ], spacing=8),
            content=ft.Container(
                width=500,
                content=ft.Column([
                    ui_theme.status_badge(f"Official DFY HR Manual (Updated 2025) — {rule['article_title']}"),
                    ft.Container(height=4),
                    ft.Text(rule["plain_hinglish"], size=13, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
                    ft.Text("Key Official Provisions:", size=12, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_MUTED),
                    ft.Column(points, spacing=4),
                    ft.Container(height=4),
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.1, ui_theme.COLOR_PRIMARY),
                        padding=8,
                        border_radius=8,
                        content=ft.Text(f"💡 Action Tip: {rule['action_tip']}", size=11, color=ui_theme.COLOR_PRIMARY_LIGHT),
                    ),
                ], spacing=8, tight=True),
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: page.close(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()

    # =========================================================================
    # TIER 2: BENTO GRID (LEFT: AI COPILOT 55% | RIGHT: HRMS HEALTH 45%)
    # =========================================================================

    # --- LEFT BENTO: AI Operations & Policy Copilot ---
    briefing_bullets_column = ft.Column(spacing=6)

    def render_briefing_bullets(bullets_list):
        briefing_bullets_column.controls.clear()
        for b in bullets_list[:4]:
            is_fix = b.get("action_target") == "quick_fix"
            cid = b.get("candidate_id")
            mfield = b.get("missing_field")

            if is_fix and cid and mfield:
                action_btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.AUTO_FIX_HIGH_ROUNDED, size=11, color=ft.Colors.WHITE),
                        ft.Text("Fix", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ], spacing=2, tight=True),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=6,
                    bgcolor=ui_theme.COLOR_PRIMARY,
                    on_click=lambda e, cand_id=cid, fld=mfield: open_quick_fix_dialog(cand_id, fld, b.get("headline", "Candidate")),
                )
            elif b.get("action_target"):
                action_btn = ft.Container(
                    content=ft.Row([
                        ft.Text(b.get("action_text", "Go"), size=10, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_PRIMARY_LIGHT),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=12, color=ui_theme.COLOR_PRIMARY_LIGHT),
                    ], spacing=1, tight=True),
                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                    border_radius=6,
                    bgcolor=ft.Colors.with_opacity(0.12, ui_theme.COLOR_PRIMARY),
                    on_click=lambda e, target=b.get("action_target"), flt=b.get("action_filter"): trigger_navigate(target, filter=flt),
                )
            else:
                action_btn = ft.Container()

            item_row = ft.Container(
                bgcolor=ui_theme.COLOR_CARD_BG_HOVER,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border_radius=8,
                border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                content=ft.Row([
                    ft.Text(b.get("icon", "💡"), size=14),
                    ft.Column([
                        ft.Text(b.get("headline", ""), size=12, weight=ft.FontWeight.W_600, color=ui_theme.COLOR_TEXT_PRIMARY),
                        ft.Text(b.get("subtext", ""), size=10, color=ui_theme.COLOR_TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=1, expand=True),
                    action_btn,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )
            briefing_bullets_column.controls.append(item_row)

    render_briefing_bullets(briefing_data.get("bullets", []))

    # Top 5 Pinned Policy Quick Chips
    policy_chips = ft.Row([
        ft.Chip(label=ft.Text("🏥 Insurance (Art. 6)", size=10), on_click=lambda e: show_policy_modal("insurance")),
        ft.Chip(label=ft.Text("⏱️ Hours 9:30-5:30 (Art. 4)", size=10), on_click=lambda e: show_policy_modal("working_hours")),
        ft.Chip(label=ft.Text("📅 Leaves (Art. 4)", size=10), on_click=lambda e: show_policy_modal("leaves")),
        ft.Chip(label=ft.Text("⏳ Probation (Art. 2)", size=10), on_click=lambda e: show_policy_modal("probation")),
        ft.Chip(label=ft.Text("🚪 Notice Period (Art. 5)", size=10), on_click=lambda e: show_policy_modal("notice_period")),
    ], wrap=True, spacing=4)

    # Ask-HR Query Bar & Result Card
    ask_input = ft.TextField(
        hint_text="Ask candidate stats or DFY policy (e.g. 'Bihar candidates', 'Probation rule')...",
        dense=True,
        expand=True,
        border_radius=8,
        border_color=ui_theme.COLOR_CARD_BORDER,
        focused_border_color=ui_theme.COLOR_PRIMARY_LIGHT,
    )
    ask_result_container = ft.Container(visible=False)

    def do_ask_query(e):
        q = ask_input.value.strip()
        if not q:
            return
        res = ai_copilot_service.process_ask_hr_query(q)
        act_btn = None
        if res.get("action_button"):
            act_info = res["action_button"]
            act_btn = ft.ElevatedButton(
                act_info["text"],
                icon=ft.Icons.ARROW_FORWARD,
                color=ft.Colors.WHITE,
                bgcolor=PRIMARY_COLOR,
                height=30,
                on_click=lambda ev: trigger_navigate(act_info["target"], search_term=act_info.get("search_term"), filter=act_info.get("filter")),
            )

        ask_result_container.content = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.18, ui_theme.COLOR_PRIMARY),
            padding=10,
            border_radius=8,
            border=ft.Border.all(1, ui_theme.COLOR_PRIMARY_LIGHT),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color=ui_theme.COLOR_PRIMARY_LIGHT, size=16),
                    ft.Text(res.get("headline", "Answer"), size=12, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_PRIMARY_LIGHT),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.CLOSE, icon_size=14, on_click=lambda ev: setattr(ask_result_container, "visible", False) or page.update()),
                ], spacing=6),
                ft.Text(res.get("answer", ""), size=12, color=ui_theme.COLOR_TEXT_PRIMARY),
                act_btn if act_btn else ft.Container(),
            ], spacing=6),
        )
        ask_result_container.visible = True
        page.update()

    ask_input.on_submit = do_ask_query
    ask_btn = ft.IconButton(ft.Icons.SEARCH, bgcolor=PRIMARY_COLOR, icon_color=ft.Colors.WHITE, icon_size=16, on_click=do_ask_query)

    left_bento_content = ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=20),
            ft.Text("AI Operations & Policy Copilot", size=14, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ft.Container(expand=True),
            ui_theme.status_badge("100% Offline Capable 🛡️"),
        ], spacing=6),
        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
        briefing_bullets_column,
        ft.Container(height=2),
        ft.Text("Official DFY Rules Quick-Access:", size=10, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_MUTED),
        policy_chips,
        ft.Container(height=2),
        ft.Row([ask_input, ask_btn], spacing=6),
        ask_result_container,
    ], spacing=6)

    left_bento_card = ft.Container(
        content=left_bento_content,
        padding=14,
        border_radius=12,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        expand=55,
    )

    # --- RIGHT BENTO: HRMS Health, Joinee Countdown & 1-Click Executive Summary ---
    def do_download_daily_summary(e):
        try:
            out_file = hr_report_exporter.export_daily_executive_summary()
            show_message(f"Daily Briefing Report generated: {os.path.basename(out_file)}!", True)
            ui_theme.show_export_success_dialog(page, out_file, report_title="Executive Daily Briefing")
        except Exception as ex:
            show_message(f"Export error: {ex}", False)

    btn_download_summary = ft.ElevatedButton(
        "📄 Download Daily Briefing (Excel)",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        color=ft.Colors.WHITE,
        bgcolor=PRIMARY_COLOR,
        height=32,
        on_click=do_download_daily_summary,
    )

    # Pipeline Funnel Pills
    funnel_pills = ft.Row([
        ui_theme.status_badge(f"Applied: {funnel.get('Applied', 0)}"),
        ui_theme.status_badge(f"Interview: {funnel.get('Interview', 0)}"),
        ui_theme.status_badge(f"Selected: {funnel.get('Selected', 0)}"),
        ui_theme.status_badge(f"Joined: {funnel.get('Joined', 0)}"),
    ], wrap=True, spacing=6)

    # Keka Sync Status Pill
    keka_p_count = keka_summary.get("count", 0)
    if keka_p_count > 0:
        keka_pill = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING_ROUNDED, size=14, color=ui_theme.COLOR_WARNING),
                ft.Text(f"{keka_p_count} Joined staff missing Keka Emp ID", size=11, color=ui_theme.COLOR_WARNING, weight=ft.FontWeight.BOLD),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.15, ui_theme.COLOR_WARNING),
            border=ft.Border.all(1, ui_theme.COLOR_WARNING),
            on_click=lambda e: trigger_navigate("keka"),
        )
    else:
        keka_pill = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=14, color=ui_theme.COLOR_SUCCESS),
                ft.Text("All Joined Staff Synced with Keka", size=11, color=ui_theme.COLOR_SUCCESS, weight=ft.FontWeight.BOLD),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.15, ui_theme.COLOR_SUCCESS),
            border=ft.Border.all(1, ui_theme.COLOR_SUCCESS),
        )

    # Upcoming Joinees (next 7 days)
    if upcoming_joinees:
        joinee_items = [
            ft.Text(f"• {j.get('candidate_name')} ({j.get('applied_designation')}) — Joining in {j.get('days_until_joining')} day{'s' if j.get('days_until_joining') > 1 else ''}", size=11, color=ui_theme.COLOR_TEXT_PRIMARY)
            for j in upcoming_joinees[:3]
        ]
        joinee_box = ft.Column(joinee_items, spacing=2)
    else:
        joinee_box = ft.Text("No candidates scheduled to join in the next 7 days.", size=11, color=ui_theme.COLOR_TEXT_MUTED)

    right_bento_content = ft.Column([
        ft.Row([
            ft.Icon(ft.Icons.ANALYTICS_ROUNDED, color=ui_theme.COLOR_SUCCESS, size=20),
            ft.Text("HRMS Health & Joinee Countdown", size=14, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ft.Container(expand=True),
        ], spacing=6),
        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
        ft.Text("Pipeline Stage Distribution:", size=11, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_MUTED),
        funnel_pills,
        ft.Container(height=2),
        ft.Text("Keka Master Synchronization:", size=11, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_MUTED),
        keka_pill,
        ft.Container(height=2),
        ft.Text("⏳ Upcoming Joinees (Next 7 Days):", size=11, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_MUTED),
        joinee_box,
        ft.Container(height=4),
        btn_download_summary,
    ], spacing=6)

    right_bento_card = ft.Container(
        content=right_bento_content,
        padding=14,
        border_radius=12,
        bgcolor=ui_theme.COLOR_CARD_BG,
        border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
        expand=45,
    )

    bento_grid_row = ft.Row([left_bento_card, right_bento_card], spacing=12)

    # =========================================================================
    # TIER 3: UNIFIED 3-TAB OPERATIONS HUB (HIGH-DENSITY)
    # =========================================================================

    # --- TAB 1: 🔔 Due Reminders Content ---
    def export_exp_due_clicked(e):
        if not exp_due_list:
            show_message("No records to export.", False)
            return
        out_path = os.path.join(DESKTOP_APP_DIR, "output", "experience_certificates_due.xlsx")
        export_data = [
            {"Candidate Name": c["candidate_name"], "Mobile": c["mobile"], "Designation": c["applied_designation"], "Relieving Date": c["relieving_date"], "Certificate Issued": "Yes" if c["already_issued"] else "Pending"}
            for c in exp_due_list
        ]
        excel_export_service.export_to_excel(export_data, out_path, sheet_name="Certificates Due")
        show_message(f"Certificates due list exported to {os.path.basename(out_path)}!", True)
        ui_theme.show_export_success_dialog(page, out_path, record_count=len(export_data), report_title="Relieving Certificates Due")

    def export_inc_clicked(list_data, filename, sheet_name):
        if not list_data:
            show_message("No records to export.", False)
            return
        out_path = os.path.join(DESKTOP_APP_DIR, "output", filename)
        export_data = [
            {"Candidate Name": c["candidate_name"], "Mobile": c["mobile"], "Designation": c["applied_designation"], "Date Joined": c["date_joined"], "Days Active": c["days_since_joining"], "Increment Letter Issued": "Yes" if c["already_issued"] else "Action Needed"}
            for c in list_data
        ]
        excel_export_service.export_to_excel(export_data, out_path, sheet_name=sheet_name)
        show_message(f"Report exported to {os.path.basename(out_path)}!", True)
        ui_theme.show_export_success_dialog(page, out_path, record_count=len(export_data), report_title=f"Annual Increments ({sheet_name})")

    # Table: Relieving Certificates Due
    if not exp_due_list:
        exp_table = ft.Text("🎉 All relieved staff have received their certificates.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
    else:
        exp_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["candidate_name"], size=12, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(c.get("applied_designation", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(str(c.get("relieving_date", "-")), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ui_theme.status_badge("Issued ✅" if c.get("already_issued") else "Pending ⚠️")),
            ])
            for c in exp_due_list[:6]
        ]
        exp_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Employee", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Relieving Date", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=11)),
            ],
            rows=exp_rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=8,
            column_spacing=14,
        )

    # Table: Overdue Increments
    overdue_list = inc_due.get("overdue", [])
    if not overdue_list:
        inc_table = ft.Text("🎉 No overdue annual increments.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
    else:
        inc_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["candidate_name"], size=12, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(c.get("applied_designation", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(str(c.get("date_joined", "-")), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(f"{c.get('days_since_joining', 0)} days", size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ui_theme.status_badge("Issued ✅" if c.get("already_issued") else "Overdue ⚠️")),
            ])
            for c in overdue_list[:6]
        ]
        inc_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Employee", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Joined", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Tenure", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=11)),
            ],
            rows=inc_rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=8,
            column_spacing=14,
        )

    tab1_content = ft.Container(
        padding=12,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=18),
                ft.Text("Relieving & Experience Certificates Due", size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ft.Container(expand=True),
                ft.TextButton("Export Certificates Excel", icon=ft.Icons.DOWNLOAD, on_click=export_exp_due_clicked),
            ], spacing=6),
            ft.Row([exp_table], scroll=ft.ScrollMode.AUTO),
            ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
            ft.Row([
                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=ui_theme.COLOR_WARNING, size=18),
                ft.Text("Annual Increment Reminders (Tenure >= 365 Days)", size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ft.Container(expand=True),
                ft.TextButton("Export Increments Excel", icon=ft.Icons.DOWNLOAD, on_click=lambda e: export_inc_clicked(overdue_list, "overdue_increments.xlsx", "Overdue")),
            ], spacing=6),
            ft.Row([inc_table], scroll=ft.ScrollMode.AUTO),
        ], spacing=10),
    )

    # --- TAB 2: 📜 Operations Activity Log Content ---
    if not recent_emails:
        disp_table = ft.Text("No recent email dispatches recorded.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
    else:
        disp_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(em.get("timestamp", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(em.get("recipient_name") or "Candidate", size=11, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(str(em.get("document_type", "-")).replace("_", " ").title(), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ui_theme.status_badge("Sent ✅" if em.get("status") in ("Success", "Sent") else "Failed ❌")),
            ])
            for em in recent_emails[:6]
        ]
        disp_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Timestamp", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Recipient", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, size=11)),
            ],
            rows=disp_rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=8,
            column_spacing=14,
        )

    if not recent_gens:
        gen_table = ft.Text("No recent document generations recorded.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
    else:
        gen_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(dg.get("generated_date", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(dg.get("candidate_name", "Unknown"), size=11, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(str(dg.get("document_type", "-")).replace("_", " ").title(), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(dg.get("reference_number", "-"), size=11, color=ui_theme.COLOR_PRIMARY_LIGHT)),
            ])
            for dg in recent_gens[:6]
        ]
        gen_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Generated Date", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Candidate", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, size=11)),
                ft.DataColumn(ft.Text("Reference #", weight=ft.FontWeight.BOLD, size=11)),
            ],
            rows=gen_rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=8,
            column_spacing=14,
        )

    tab2_content = ft.Container(
        padding=12,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MARK_EMAIL_READ_ROUNDED, color=ui_theme.COLOR_SUCCESS, size=18),
                ft.Text("Recent Email Dispatches", size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ui_theme.status_badge(f"Dispatched Today: {stats.get('dispatched_today', 0)}"),
            ], spacing=6),
            ft.Row([disp_table], scroll=ft.ScrollMode.AUTO),
            ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
            ft.Row([
                ft.Icon(ft.Icons.DESCRIPTION_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=18),
                ft.Text("Recent Generated Documents & Reference Numbers", size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ], spacing=6),
            ft.Row([gen_table], scroll=ft.ScrollMode.AUTO),
        ], spacing=10),
    )

    # --- TAB 3: 📊 Sheet & Batch Breakdown Content ---
    breakdown_cards = []
    for dname, dinfo in list(dept_breakdown.items())[:8]:
        breakdown_cards.append(
            ft.Container(
                bgcolor=ui_theme.COLOR_CARD_BG_HOVER,
                padding=10,
                border_radius=8,
                border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                width=240,
                content=ft.Column([
                    ft.Text(dname, size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Divider(height=4, color=ui_theme.COLOR_CARD_BORDER),
                    ft.Text(f"• Total Candidates: {dinfo.get('total', 0)}", size=11, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ft.Text(f"• Selected: {dinfo.get('selected', 0)}", size=11, color=ui_theme.COLOR_WARNING),
                    ft.Text(f"• Joined Staff: {dinfo.get('joined', 0)}", size=11, color=ui_theme.COLOR_SUCCESS),
                    ft.Text(f"• In Interview: {dinfo.get('interview', 0)}", size=11, color=ui_theme.COLOR_SECONDARY_LIGHT),
                ], spacing=3),
            )
        )

    tab3_content = ft.Container(
        padding=12,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MAP_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=18),
                ft.Text("State & Spreadsheet Batch Breakdown (UP, Bihar, Maharashtra, etc.)", size=13, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ], spacing=6),
            ft.Row(breakdown_cards, wrap=True, spacing=10),
        ], spacing=10),
    )

    # High-Density Tab Switcher
    tab_due = ft.Tab(label="🔔 Due Reminders")
    tab_due.text = "🔔 Due Reminders"
    tab_log = ft.Tab(label="📜 Operations Log")
    tab_log.text = "📜 Operations Log"
    tab_breakdown = ft.Tab(label="📊 Sheet Breakdown")
    tab_breakdown.text = "📊 Sheet Breakdown"

    tab_content_container = ft.Container(content=tab1_content)

    def on_tab_click(e):
        idx = 0
        if hasattr(e, "data") and str(e.data).isdigit():
            idx = int(e.data)
        elif hasattr(e.control, "selected_index"):
            idx = int(e.control.selected_index)

        if idx == 0:
            tab_content_container.content = tab1_content
        elif idx == 1:
            tab_content_container.content = tab2_content
        elif idx == 2:
            tab_content_container.content = tab3_content
        try:
            page.update()
        except Exception:
            pass

    operations_tabs = ft.TabBar(
        tabs=[tab_due, tab_log, tab_breakdown],
        on_click=on_tab_click,
    )

    operations_hub_card = ui_theme.modern_card(ft.Column([
        operations_tabs,
        ft.Divider(height=1, color=ui_theme.COLOR_CARD_BORDER),
        tab_content_container,
    ], spacing=4))

    # =========================================================================
    # REFRESH DASHBOARD CONTROLLER
    # =========================================================================
    def refresh_dashboard(e=None):
        nonlocal stats, overview, funnel, dept_breakdown, exp_due_list, inc_due, keka_summary, briefing_data, upcoming_joinees
        stats = dashboard_service.get_dashboard_stats()
        overview = dashboard_service.get_status_overview()
        funnel = dashboard_service.get_pipeline_funnel_summary()
        dept_breakdown = dashboard_service.get_department_breakdown()
        exp_due_list = dashboard_service.get_experience_certificate_due_list()
        inc_due = dashboard_service.get_increment_due_list()
        keka_summary = dashboard_service.get_keka_pending_summary()
        briefing_data = ai_copilot_service.generate_daily_operational_briefing()
        upcoming_joinees = db_manager.get_upcoming_joinees(days=7)

        # Update action cards text
        welcome_count_text.value = str(stats.get("pending_welcome_emails", 0))
        letters_count_text.value = str(stats.get("letters_to_generate", 0))
        staging_count_text.value = str(stats.get("staged_letters_ready", 0))
        pipeline_count_text.value = str(stats.get("in_pipeline", 0))

        # Re-render briefing
        render_briefing_bullets(briefing_data.get("bullets", []))

        view_column.stats = stats
        show_message("Executive Dashboard refreshed with latest HR operations data! 🔄", True)
        page.update()

    # =========================================================================
    # HEADER SECTION WITH OFFICIAL DFY LOGO
    # =========================================================================
    logo_path = os.path.join(ASSETS_DIR, "dfy_logo112.png")
    if os.path.exists(logo_path):
        header_brand_icon = ft.Image(src=logo_path, width=42, height=42, fit=ft.BoxFit.CONTAIN)
    else:
        header_brand_icon = ft.Icon(ft.Icons.LOCAL_HOSPITAL_ROUNDED, color=PRIMARY_COLOR, size=34)

    btn_refresh = ui_theme.secondary_button("Refresh", icon=ft.Icons.REFRESH_ROUNDED, on_click=refresh_dashboard)

    header_row = ft.Row([
        ft.Row([
            header_brand_icon,
            ft.Column([
                ft.Row([
                    ft.Text("Executive HR Command Center", size=22, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ui_theme.status_badge("Doctors For You 🏥"),
                ], spacing=8),
                ft.Text("Compact Operations Hub, AI Policy Copilot & Automated Document Staging Pipeline.", size=12, color=ui_theme.COLOR_TEXT_SECONDARY),
            ], spacing=2, expand=True),
        ], spacing=12, expand=True),
        btn_refresh,
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # =========================================================================
    # ASSEMBLE FULL VIEW LAYOUT (3-TIER BENTO)
    # =========================================================================
    view_column = ft.Column([
        header_row,               # controls[0] (Branded Header)
        ft.Container(height=6),
        action_cards_row,         # controls[2] (Tier 1: 4 Prominent Action Cards)
        ft.Container(height=6),
        bento_grid_row,           # controls[4] (Tier 2: Left AI Copilot 55% | Right Health 45%)
        ft.Container(height=6),
        operations_hub_card,      # controls[6] (Tier 3: Unified 3-Tab Operations Hub)
        ft.Container(height=16),
    ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)

    # Expose attributes for easy test inspection and automation
    view_column.action_cards_row = action_cards_row
    view_column.bento_grid_row = bento_grid_row
    view_column.operations_tabs = operations_tabs
    view_column.operations_hub_card = operations_hub_card
    view_column.activity_card = operations_hub_card
    view_column.card_welcome = card_welcome
    view_column.card_letters = card_letters
    view_column.card_staging = card_staging
    view_column.card_pipeline = card_pipeline
    view_column.stats = stats
    view_column.refresh_dashboard = refresh_dashboard
    view_column.trigger_navigate = trigger_navigate

    return view_column
