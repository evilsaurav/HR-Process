"""
Page: dashboard_page.py
Purpose: Executive HR Command Center & Operations Dashboard:
- 4 prominent, live, clickable Action Cards (Pending Welcome, Letters to Generate, Staged Ready, In Pipeline)
- Real-time candidate pipeline status overview with animated stat cards
- Experience and Salary certificates due for relieved employees (with Excel export)
- Annual increment reminders (upcoming & overdue, with Excel export)
- Keka HRMS synchronization status card
- Live operations activity log & audit trail (recent dispatches, recent document generations)
- Instant dynamic refresh and deep navigation hooks.
"""

import os
import datetime
from typing import Optional, Callable
import flet as ft

from config import PRIMARY_COLOR, STATUS_OPTIONS, DESKTOP_APP_DIR
from services import dashboard_service
from services import excel_export_service
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

    # 1. Fetch Real-Time Data
    stats = dashboard_service.get_dashboard_stats()
    overview = dashboard_service.get_status_overview()
    exp_due_list = dashboard_service.get_experience_certificate_due_list()
    inc_due = dashboard_service.get_increment_due_list()
    keka_summary = dashboard_service.get_keka_pending_summary()
    recent_emails = dashboard_service.get_recent_email_dispatches(limit=5)
    recent_gens = dashboard_service.get_recent_document_generations(limit=5)

    # =========================================================================
    # 2. TOP ACTION CARDS (LIVE OPERATIONAL COMMAND CENTER)
    # =========================================================================

    welcome_count_text = ft.Text(
        str(stats.get("pending_welcome_emails", 0)),
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ui_theme.COLOR_TEXT_PRIMARY
    )
    letters_count_text = ft.Text(
        str(stats.get("letters_to_generate", 0)),
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ui_theme.COLOR_TEXT_PRIMARY
    )
    staging_count_text = ft.Text(
        str(stats.get("staged_letters_ready", 0)),
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ui_theme.COLOR_TEXT_PRIMARY
    )
    pipeline_count_text = ft.Text(
        str(stats.get("in_pipeline", 0)),
        size=32,
        weight=ft.FontWeight.BOLD,
        color=ui_theme.COLOR_TEXT_PRIMARY
    )

    def build_action_card(
        title: str,
        subtitle: str,
        count_text_ctrl: ft.Text,
        icon,
        accent_color: str,
        bg_color: str,
        border_color: str,
        on_click,
    ) -> ft.Container:
        icon_box = ft.Container(
            content=ft.Icon(icon, color=accent_color, size=24),
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.18, accent_color),
        )

        action_pill = ft.Container(
            content=ft.Row([
                ft.Text("Quick Action", size=10, weight=ft.FontWeight.BOLD, color=accent_color),
                ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=12, color=accent_color),
            ], spacing=3, tight=True),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.12, accent_color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, accent_color)),
        )

        card_content = ft.Column([
            ft.Row([
                icon_box,
                ft.Container(expand=True),
                action_pill,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=4),
            count_text_ctrl,
            ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
            ft.Text(subtitle, size=11, color=ui_theme.COLOR_TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
        ], spacing=4)

        card = ft.Container(
            content=card_content,
            padding=18,
            border_radius=14,
            bgcolor=bg_color,
            border=ft.Border.all(1.5, border_color),
            shadow=[
                ft.BoxShadow(
                    blur_radius=12,
                    spread_radius=0,
                    color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                    offset=ft.Offset(0, 4),
                )
            ],
            expand=1,
            on_click=on_click,
            animate_scale=ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT),
            animate=ft.Animation(duration=150, curve=ft.AnimationCurve.EASE_OUT),
        )

        def on_hover(e):
            if e.data == "true":
                card.scale = 1.025
                card.shadow = [
                    ft.BoxShadow(
                        blur_radius=18,
                        spread_radius=1,
                        color=ft.Colors.with_opacity(0.4, accent_color),
                        offset=ft.Offset(0, 6),
                    )
                ]
            else:
                card.scale = 1.0
                card.shadow = [
                    ft.BoxShadow(
                        blur_radius=12,
                        spread_radius=0,
                        color=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                        offset=ft.Offset(0, 4),
                    )
                ]
            try:
                card.update()
            except Exception:
                pass

        card.on_hover = on_hover
        return card

    card_welcome = build_action_card(
        title="🎉 Pending Welcome Emails",
        subtitle="Selected awaiting welcome email",
        count_text_ctrl=welcome_count_text,
        icon=ft.Icons.MARK_EMAIL_UNREAD_ROUNDED,
        accent_color="#F59E0B",
        bg_color="#1F1A12",
        border_color="#F59E0B",
        on_click=lambda e: trigger_navigate("joining", filter="selected"),
    )

    card_letters = build_action_card(
        title="🔍 Letters to Generate",
        subtitle="Staff needing documents detected",
        count_text_ctrl=letters_count_text,
        icon=ft.Icons.AUTO_AWESOME_ROUNDED,
        accent_color="#3B82F6",
        bg_color="#131B2E",
        border_color="#3B82F6",
        on_click=lambda e: trigger_navigate("documents", tab=0),
    )

    card_staging = build_action_card(
        title="🚀 Staged Ready for Final Go",
        subtitle="Drafted letters in staging queue",
        count_text_ctrl=staging_count_text,
        icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
        accent_color="#10B981",
        bg_color="#10231D",
        border_color="#10B981",
        on_click=lambda e: trigger_navigate("documents", tab=1),
    )

    card_pipeline = build_action_card(
        title="👥 In Pipeline / Interviews",
        subtitle=f"{stats.get('in_interview', 0)} Interviewing • {stats.get('applied_candidates', 0)} Applied",
        count_text_ctrl=pipeline_count_text,
        icon=ft.Icons.PEOPLE_ALT_ROUNDED,
        accent_color="#8B5CF6",
        bg_color="#1E152E",
        border_color="#8B5CF6",
        on_click=lambda e: trigger_navigate("joining"),
    )

    action_cards_row = ft.Row([
        card_welcome,
        card_letters,
        card_staging,
        card_pipeline,
    ], spacing=14)

    # =========================================================================
    # 3. PIPELINE STATUS OVERVIEW STAT CARDS ROW
    # =========================================================================

    stat_cards_row = ft.Row([
        ui_theme.animated_stat_card("Total", overview.get("total", 0), ft.Icons.PEOPLE_ROUNDED, ui_theme.COLOR_PRIMARY),
        ui_theme.animated_stat_card("Joined", overview.get("Joined", 0), ft.Icons.CHECK_CIRCLE_ROUNDED, ui_theme.COLOR_SUCCESS),
        ui_theme.animated_stat_card("Offer Sent", overview.get("Offer Sent", 0), ft.Icons.SEND_ROUNDED, ui_theme.COLOR_PRIMARY_LIGHT),
        ui_theme.animated_stat_card("Interview", overview.get("Interview", 0), ft.Icons.EVENT_ROUNDED, ui_theme.COLOR_WARNING),
        ui_theme.animated_stat_card("Shortlisted", overview.get("Shortlisted", 0), ft.Icons.THUMB_UP_ROUNDED, ui_theme.COLOR_INFO),
        ui_theme.animated_stat_card("Applied", overview.get("Applied", 0), ft.Icons.INBOX_ROUNDED, ui_theme.COLOR_SECONDARY_LIGHT),
        ui_theme.animated_stat_card("Rejected", overview.get("Rejected", 0), ft.Icons.CANCEL_ROUNDED, ui_theme.COLOR_ERROR),
    ], wrap=True, spacing=14)

    # =========================================================================
    # 4. EXPERIENCE / SALARY CERTIFICATE DUE SECTION
    # =========================================================================

    def export_exp_due_clicked(e):
        if not exp_due_list:
            show_message("No records to export.", False)
            return
        out_path = os.path.join(DESKTOP_APP_DIR, "output", "experience_certificates_due.xlsx")
        export_data = [
            {
                "Candidate Name": c["candidate_name"],
                "Mobile": c["mobile"],
                "Designation": c["applied_designation"],
                "Relieving Date": c["relieving_date"],
                "Certificate Issued": "Yes" if c["already_issued"] else "Pending",
            }
            for c in exp_due_list
        ]
        excel_export_service.export_to_excel(export_data, out_path, sheet_name="Certificates Due")
        show_message(f"Certificates due list exported to {os.path.basename(out_path)}!", True)

    if not exp_due_list:
        exp_table_content = ft.Text(
            "🎉 No certificates due. All relieved employees have received their certificates or there are no relieving records.",
            size=13, color=ui_theme.COLOR_TEXT_MUTED
        )
    else:
        exp_rows = []
        for c in exp_due_list:
            issued = c["already_issued"]
            status_chip = ui_theme.status_badge("Issued ✅" if issued else "Pending ⚠️")

            exp_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["candidate_name"], weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(c["mobile"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(c["applied_designation"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(c["relieving_date"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(status_chip),
            ]))

        exp_data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Relieving Date", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Certificate Status", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
            ],
            rows=exp_rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=24,
        )
        exp_table_content = ft.Row([exp_data_table], scroll=ft.ScrollMode.AUTO)

    exp_export_btn = ui_theme.secondary_button(
        "Export to Excel",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        on_click=export_exp_due_clicked,
    )

    exp_card = ui_theme.modern_card(ft.Column([
        ft.Row([
            ui_theme.section_title(ft.Icons.WORKSPACE_PREMIUM_ROUNDED, "Experience / Salary Certificates Due"),
            ft.Container(expand=True),
            exp_export_btn,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
        ft.Text(
            "Employees who have relieved or departed and are awaiting their official Experience/Salary Certificates.",
            size=12, color=ui_theme.COLOR_TEXT_MUTED
        ),
        exp_table_content,
    ], spacing=10))

    # =========================================================================
    # 5. ANNUAL INCREMENT REMINDERS SECTION
    # =========================================================================

    upcoming_list = inc_due.get("upcoming", [])
    overdue_list = inc_due.get("overdue", [])

    def export_inc_clicked(list_data, filename, sheet_name):
        if not list_data:
            show_message("No records to export.", False)
            return
        out_path = os.path.join(DESKTOP_APP_DIR, "output", filename)
        export_data = [
            {
                "Candidate Name": c["candidate_name"],
                "Mobile": c["mobile"],
                "Designation": c["applied_designation"],
                "Date Joined": c["date_joined"],
                "Days Active": c["days_since_joining"],
                "Increment Letter Issued": "Yes" if c["already_issued"] else "Action Needed",
            }
            for c in list_data
        ]
        excel_export_service.export_to_excel(export_data, out_path, sheet_name=sheet_name)
        show_message(f"Report exported to {os.path.basename(out_path)}!", True)

    def create_inc_table(items, is_overdue=False):
        rows = []
        for c in items:
            issued = c["already_issued"]
            if is_overdue:
                badge_text = "Issued ✅" if issued else "Overdue ⚠️"
            else:
                badge_text = "Issued ✅" if issued else "Due Soon 🔔"

            status_chip = ui_theme.status_badge(badge_text)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["candidate_name"], weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(c["mobile"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(c["applied_designation"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(c["date_joined"], color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(ft.Text(f"{c['days_since_joining']} days", color=ui_theme.COLOR_TEXT_SECONDARY)),
                ft.DataCell(status_chip),
            ]))

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Employee Name", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Date Joined", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Days Active", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=24,
        )

    inc_controls = []
    if not upcoming_list and not overdue_list:
        inc_controls.append(
            ft.Text(
                "🎉 No pending increments right now. All active joined employees are within their normal annual tenure.",
                size=13, color=ui_theme.COLOR_TEXT_MUTED
            )
        )
    else:
        if overdue_list:
            inc_controls.append(ft.Row([
                ft.Text(f"⚠️ Overdue Increments (Joined ≥ 365 days ago - {len(overdue_list)} employees)",
                        weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_ERROR),
                ft.Container(expand=True),
                ui_theme.secondary_button(
                    "Export Overdue to Excel",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=lambda e: export_inc_clicked(overdue_list, "overdue_increments.xlsx", "Overdue"),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            inc_controls.append(ft.Row([create_inc_table(overdue_list, is_overdue=True)], scroll=ft.ScrollMode.AUTO))
            inc_controls.append(ft.Container(height=10))

        if upcoming_list:
            inc_controls.append(ft.Row([
                ft.Text(f"🔔 Upcoming Increments (Due within next 30 days - {len(upcoming_list)} employees)",
                        weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_WARNING),
                ft.Container(expand=True),
                ui_theme.secondary_button(
                    "Export Upcoming to Excel",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=lambda e: export_inc_clicked(upcoming_list, "upcoming_increments.xlsx", "Upcoming"),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            inc_controls.append(ft.Row([create_inc_table(upcoming_list, is_overdue=False)], scroll=ft.ScrollMode.AUTO))

    inc_card = ui_theme.modern_card(ft.Column([
        ui_theme.section_title(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, "Annual Increment Reminders"),
        ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
        ft.Text(
            "Tracking active employees approaching or completing 1 year of service from their Date Joined.",
            size=12, color=ui_theme.COLOR_TEXT_MUTED
        ),
        ft.Column(inc_controls, spacing=10),
    ], spacing=10))

    # =========================================================================
    # 6. KEKA HRMS SYNC STATUS SECTION
    # =========================================================================

    pending_keka_count = keka_summary.get("count", 0)
    if pending_keka_count > 0:
        keka_tile = ft.Container(
            bgcolor=ui_theme.COLOR_WARNING_BG,
            padding=16,
            border_radius=10,
            border=ft.Border.all(1, ui_theme.COLOR_WARNING),
            content=ft.Row([
                ft.Icon(ft.Icons.SYNC_ROUNDED, color=ui_theme.COLOR_WARNING, size=28),
                ft.Column([
                    ft.Text(f"⚠️ {pending_keka_count} Joined Employee(s) Awaiting Keka Sync", weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ft.Text(
                        "These employees have joined but are missing Keka Employee Numbers. "
                        "Go to the Keka Sync page to upload your Keka export sheet and sync them.",
                        size=12, color=ui_theme.COLOR_TEXT_SECONDARY
                    ),
                ], spacing=2, expand=True),
            ], spacing=12),
        )
    else:
        keka_tile = ft.Container(
            bgcolor=ui_theme.COLOR_SUCCESS_BG,
            padding=16,
            border_radius=10,
            border=ft.Border.all(1, ui_theme.COLOR_SUCCESS),
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=ui_theme.COLOR_SUCCESS, size=28),
                ft.Column([
                    ft.Text("✅ All Joined Employees Synchronized with Keka", weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ft.Text("All currently joined candidates have their official Keka Employee Numbers assigned.", size=12, color=ui_theme.COLOR_TEXT_SECONDARY),
                ], spacing=2, expand=True),
            ], spacing=12),
        )

    keka_card = ui_theme.modern_card(ft.Column([
        ui_theme.section_title(ft.Icons.SYNC_ROUNDED, "Keka HRMS Sync Status"),
        ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
        keka_tile,
    ], spacing=10))

    # =========================================================================
    # 7. RECENT OPERATIONS ACTIVITY LOG & AUDIT TRAIL
    # =========================================================================

    activity_content = ft.Column(spacing=14)

    def render_activity_content(emails_data, gens_data, today_count):
        activity_content.controls.clear()

        # Recent email dispatches
        if not emails_data:
            disp_view = ft.Text("No recent email dispatches recorded.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
        else:
            disp_rows = []
            for em in emails_data:
                st = em.get("status", "Sent")
                badge = ui_theme.status_badge("Sent ✅" if st in ("Success", "Sent") else "Failed ❌")
                rec_name = em.get("recipient_name") or "Candidate"
                rec_email = em.get("recipient_email") or "-"
                disp_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(em.get("timestamp", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(f"{rec_name} ({rec_email})", size=12, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(str(em.get("document_type", "-")).replace("_", " ").title(), size=12, color=ui_theme.COLOR_TEXT_SECONDARY)),
                    ft.DataCell(badge),
                ]))

            disp_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Timestamp", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Recipient", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ],
                rows=disp_rows,
                heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                border_radius=8,
                column_spacing=18,
            )
            disp_view = ft.Row([disp_table], scroll=ft.ScrollMode.AUTO)

        # Recent document generations
        if not gens_data:
            gen_view = ft.Text("No recent document generations recorded.", size=12, color=ui_theme.COLOR_TEXT_MUTED)
        else:
            gen_rows = []
            for dg in gens_data:
                gen_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(dg.get("generated_date", "-"), size=11, color=ui_theme.COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(dg.get("candidate_name", "Unknown"), size=12, weight=ft.FontWeight.W_500, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(str(dg.get("document_type", "-")).replace("_", " ").title(), size=12, color=ui_theme.COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(dg.get("reference_number", "-"), size=11, color=ui_theme.COLOR_PRIMARY_LIGHT)),
                    ft.DataCell(ft.Text(dg.get("generated_by", "HR Desktop"), size=11, color=ui_theme.COLOR_TEXT_MUTED)),
                ]))

            gen_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Generated Date", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Employee / Candidate", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Reference No", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Author", weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY)),
                ],
                rows=gen_rows,
                heading_row_color=ui_theme.COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, ui_theme.COLOR_CARD_BORDER),
                border_radius=8,
                column_spacing=18,
            )
            gen_view = ft.Row([gen_table], scroll=ft.ScrollMode.AUTO)

        activity_content.controls.extend([
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MARK_EMAIL_READ_ROUNDED, color=ui_theme.COLOR_SUCCESS, size=18),
                    ft.Text("Recent Email Dispatches", weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_TEXT_PRIMARY),
                    ui_theme.status_badge(f"Dispatched Today: {today_count}"),
                ], spacing=8),
                disp_view,
            ], spacing=8),
            ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=18),
                    ft.Text("Recent Generated Documents", weight=ft.FontWeight.BOLD, size=14, color=ui_theme.COLOR_TEXT_PRIMARY),
                ], spacing=8),
                gen_view,
            ], spacing=8),
        ])

    render_activity_content(recent_emails, recent_gens, stats.get("dispatched_today", 0))

    activity_card = ui_theme.modern_card(ft.Column([
        ft.Row([
            ui_theme.section_title(ft.Icons.HISTORY_ROUNDED, "Operations Activity Log & Audit Trail"),
            ft.Container(expand=True),
            ui_theme.status_badge("Live Syncing ✅"),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=10, color=ui_theme.COLOR_CARD_BORDER),
        ft.Text(
            "Continuous audit trail tracking recent candidate email dispatches, offer releases, and document generations.",
            size=12, color=ui_theme.COLOR_TEXT_MUTED
        ),
        activity_content,
    ], spacing=10))

    # =========================================================================
    # DYNAMIC DASHBOARD REFRESH LOGIC
    # =========================================================================

    def refresh_dashboard(e=None):
        nonlocal stats, overview, exp_due_list, inc_due, keka_summary
        stats = dashboard_service.get_dashboard_stats()
        overview = dashboard_service.get_status_overview()
        exp_due_list = dashboard_service.get_experience_certificate_due_list()
        inc_due = dashboard_service.get_increment_due_list()
        keka_summary = dashboard_service.get_keka_pending_summary()
        rec_emails = dashboard_service.get_recent_email_dispatches(limit=5)
        rec_gens = dashboard_service.get_recent_document_generations(limit=5)

        # Update action card count texts
        welcome_count_text.value = str(stats.get("pending_welcome_emails", 0))
        letters_count_text.value = str(stats.get("letters_to_generate", 0))
        staging_count_text.value = str(stats.get("staged_letters_ready", 0))
        pipeline_count_text.value = str(stats.get("in_pipeline", 0))

        # Update stat cards
        for card_ctrl in stat_cards_row.controls:
            card_col = card_ctrl.content
            label_text = card_col.controls[2].value
            if label_text == "Total":
                card_col.controls[1].value = str(overview.get("total", 0))
            elif label_text in overview:
                card_col.controls[1].value = str(overview.get(label_text, 0))

        render_activity_content(rec_emails, rec_gens, stats.get("dispatched_today", 0))
        view_column.stats = stats
        show_message("Dashboard refreshed with latest HR operations data! 🔄", True)
        page.update()

    btn_refresh = ui_theme.secondary_button(
        "Refresh Dashboard",
        icon=ft.Icons.REFRESH_ROUNDED,
        on_click=refresh_dashboard,
    )

    # Header row with title and refresh button
    header_row = ft.Row([
        ft.Row([
            ft.Container(
                content=ft.Icon(ft.Icons.DASHBOARD_ROUNDED, color=ui_theme.COLOR_PRIMARY_LIGHT, size=28),
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.12, ui_theme.COLOR_PRIMARY),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, ui_theme.COLOR_PRIMARY_LIGHT)),
            ),
            ft.Column([
                ft.Text("Executive HR Command Center", size=26, weight=ft.FontWeight.BOLD, color=ui_theme.COLOR_TEXT_PRIMARY),
                ft.Text("Live operational action cards, automated staging pipeline, due certificate reminders, and HRMS sync.", size=13, color=ui_theme.COLOR_TEXT_SECONDARY),
            ], spacing=2, expand=True),
        ], spacing=14, expand=True),
        btn_refresh,
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Top Section combining Header and the 4 prominent Action Cards
    top_section = ft.Column([
        header_row,
        ft.Container(height=12),
        ui_theme.section_title(ft.Icons.FLASH_ON_ROUNDED, "⚡ Live Operational Action Center"),
        ft.Container(height=4),
        action_cards_row,
    ], spacing=0)

    # =========================================================================
    # 8. ASSEMBLE FULL VIEW LAYOUT
    # =========================================================================

    view_column = ft.Column([
        top_section,              # controls[0] (Header + 4 Live Action Cards)
        ft.Container(height=10),  # controls[1]
        stat_cards_row,           # controls[2] (7 Stat Cards: Total, Joined, etc.)
        ft.Container(height=10),  # controls[3]
        exp_card,                 # controls[4] (Experience Certificates Due)
        ft.Container(height=10),  # controls[5]
        inc_card,                 # controls[6] (Increment Reminders)
        ft.Container(height=10),  # controls[7]
        keka_card,                # controls[8] (Keka HRMS Sync Status)
        ft.Container(height=10),  # controls[9]
        activity_card,            # controls[10] (Recent Dispatches & Generations)
        ft.Container(height=20),  # controls[11]
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)

    # Expose attributes for easy test inspection and automation
    view_column.action_cards_row = action_cards_row
    view_column.stat_cards_row = stat_cards_row
    view_column.exp_card = exp_card
    view_column.inc_card = inc_card
    view_column.keka_card = keka_card
    view_column.activity_card = activity_card
    view_column.card_welcome = card_welcome
    view_column.card_letters = card_letters
    view_column.card_staging = card_staging
    view_column.card_pipeline = card_pipeline
    view_column.stats = stats
    view_column.refresh_dashboard = refresh_dashboard
    view_column.trigger_navigate = trigger_navigate

    return view_column
