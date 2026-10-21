"""
Page: dashboard_page.py
Purpose: Executive HR Dashboard:
- Candidate pipeline status overview with animated stat cards
- Experience and Salary certificates due for relieved employees
- Annual increment reminders (upcoming & overdue)
- Keka HRMS synchronization status
Includes Excel exports for all reminder queues and modern depth styling.
"""

import os
import flet as ft

from config import PRIMARY_COLOR, STATUS_OPTIONS, DESKTOP_APP_DIR
from services import dashboard_service
from services import excel_export_service
from utils import ui_theme


def dashboard_view(page: ft.Page):
    # Feedback helper
    def show_message(text: str, is_success: bool = True):
        page.open(ft.SnackBar(
            ft.Text(text),
            bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED
        ))
        page.update()

    # 1. Fetch Real-Time Data
    overview = dashboard_service.get_status_overview()
    exp_due_list = dashboard_service.get_experience_certificate_due_list()
    inc_due = dashboard_service.get_increment_due_list()
    keka_summary = dashboard_service.get_keka_pending_summary()

    # 2. Build Pipeline Overview Cards
    stat_cards_row = ft.Row([
        ui_theme.animated_stat_card("Total", overview.get("total", 0), ft.Icons.PEOPLE_ROUNDED, ui_theme.COLOR_PRIMARY),
        ui_theme.animated_stat_card("Joined", overview.get("Joined", 0), ft.Icons.CHECK_CIRCLE_ROUNDED, ui_theme.COLOR_SUCCESS),
        ui_theme.animated_stat_card("Offer Sent", overview.get("Offer Sent", 0), ft.Icons.SEND_ROUNDED, ui_theme.COLOR_PRIMARY_LIGHT),
        ui_theme.animated_stat_card("Interview", overview.get("Interview", 0), ft.Icons.EVENT_ROUNDED, ui_theme.COLOR_WARNING),
        ui_theme.animated_stat_card("Shortlisted", overview.get("Shortlisted", 0), ft.Icons.THUMB_UP_ROUNDED, ui_theme.COLOR_INFO),
        ui_theme.animated_stat_card("Applied", overview.get("Applied", 0), ft.Icons.INBOX_ROUNDED, ui_theme.COLOR_SECONDARY_LIGHT),
        ui_theme.animated_stat_card("Rejected", overview.get("Rejected", 0), ft.Icons.CANCEL_ROUNDED, ui_theme.COLOR_ERROR),
    ], wrap=True, spacing=14)

    # 3. Build Experience/Salary Certificate Due Section
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

    # 4. Build Increment Reminders Section
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

    # 5. Build Keka Sync Status Summary Card
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

    # 6. Assemble Full Dashboard Layout
    return ft.Column([
        # Header (controls[0])
        ui_theme.page_header(
            ft.Icons.DASHBOARD_ROUNDED,
            "HR Dashboard",
            "Welcome back! Real-time overview of candidate pipeline, due certificates, increment schedules, and sync status."
        ),

        # Spacing (controls[1])
        ft.Container(height=10),

        # Stat cards row (controls[2])
        stat_cards_row,

        # Spacing (controls[3])
        ft.Container(height=10),

        # Experience certificate due (controls[4])
        exp_card,

        # Spacing (controls[5])
        ft.Container(height=10),

        # Increment reminders (controls[6])
        inc_card,

        # Spacing (controls[7])
        ft.Container(height=10),

        # Keka sync status (controls[8])
        keka_card,

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
