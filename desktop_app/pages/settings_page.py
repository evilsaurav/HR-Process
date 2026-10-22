import os
import flet as ft
from config import DESKTOP_APP_DIR
from database import db_manager
from services.api_key_detector import detect_provider
from services import ai_service, email_service, excel_export_service
from utils.ui_theme import (
    modern_card,
    page_header,
    section_title,
    status_badge,
    primary_button,
    secondary_button,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_BG_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
)


def settings_view(page: ft.Page):
    api_key_input = ft.TextField(
        label="Paste any AI API Key here",
        password=True,
        can_reveal_password=True,
        expand=True,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )
    detected_text = ft.Text("", size=12, color=COLOR_TEXT_SECONDARY)
    keys_list_column = ft.Column(spacing=10)

    gmail_method = ft.RadioGroup(
        value="app_password",
        content=ft.Row([
            ft.Radio(value="app_password", label="App Password"),
            ft.Radio(value="oauth", label="OAuth2 (also enables Drive Backup)"),
        ])
    )
    gmail_email_field = ft.TextField(
        label="Gmail Address", width=350, border_radius=10,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    gmail_app_password_field = ft.TextField(
        label="Gmail App Password (16-digit)", password=True, can_reveal_password=True,
        width=350, border_radius=10, border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    gmail_credentials_path_field = ft.TextField(
        label="OAuth credentials.json path", width=350, border_radius=10,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    gmail_status = ft.Text("", size=13)

    # Prefill saved Gmail settings from database
    gmail_saved = {k["key_id"]: k["api_key"] for k in db_manager.get_all_api_keys() if k["provider"] == "Gmail"}
    if "gmail_method" in gmail_saved and gmail_saved["gmail_method"]:
        gmail_method.value = gmail_saved["gmail_method"]
    if "gmail_email" in gmail_saved and gmail_saved["gmail_email"]:
        gmail_email_field.value = gmail_saved["gmail_email"]
    if "gmail_app_password" in gmail_saved and gmail_saved["gmail_app_password"]:
        gmail_app_password_field.value = gmail_saved["gmail_app_password"]
    if "gmail_credentials_path" in gmail_saved and gmail_saved["gmail_credentials_path"]:
        gmail_credentials_path_field.value = gmail_saved["gmail_credentials_path"]

    # ---------------- Delete Confirmation Dialog for API Key ----------------
    def confirm_delete_key(key_id: str, provider: str):
        def do_delete(e):
            db_manager.delete_api_key(key_id)
            page.close(dlg)
            refresh_keys_list(update_page=False)
            page.open(
                ft.SnackBar(
                    ft.Text(f"API key for '{provider}' deleted successfully."),
                    bgcolor=ft.Colors.GREEN,
                )
            )
            page.update()

        def cancel_delete(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_400, size=24),
                ft.Text("Confirm Deletion", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ], spacing=8),
            content=ft.Text(f"Are you sure you want to delete the API key for '{provider}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_delete),
                ft.ElevatedButton("Delete", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700, on_click=do_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
        page.update()

    def refresh_keys_list(update_page: bool = True):
        keys_list_column.controls.clear()
        for item in db_manager.get_all_api_keys():
            if item["provider"] == "Gmail":
                continue

            status_icon = ft.Icon(
                ft.Icons.CHECK_CIRCLE if item["verified"] else ft.Icons.CANCEL,
                color=COLOR_SUCCESS if item["verified"] else COLOR_ERROR,
                size=20,
            )
            masked = item["api_key"][:6] + "••••••" + item["api_key"][-4:] if len(item["api_key"]) > 10 else "••••"

            def make_test(k_id=item["key_id"], provider=item["provider"], key_val=item["api_key"]):
                def _test(e):
                    success, msg = ai_service.test_connection(provider, key_val)
                    db_manager.mark_verified(k_id, success)
                    refresh_keys_list(update_page=False)
                    page.open(ft.SnackBar(ft.Text(msg), bgcolor=ft.Colors.GREEN if success else ft.Colors.RED))
                    page.update()
                return _test

            def make_delete(k_id=item["key_id"], prov=item["provider"]):
                return lambda e: confirm_delete_key(k_id, prov)

            keys_list_column.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=10,
                    bgcolor=COLOR_CARD_BG_HOVER,
                    border=ft.Border.all(1, COLOR_CARD_BORDER),
                    content=ft.Row([
                        status_icon,
                        ft.Column([
                            ft.Text(item["provider"], weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                            ft.Text(masked, size=12, color=COLOR_TEXT_MUTED),
                        ], expand=True, spacing=2),
                        ft.TextButton(
                            "Test Connection",
                            on_click=make_test(),
                            icon=ft.Icons.WIFI_TETHERING,
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Delete Key",
                            on_click=make_delete(),
                        ),
                    ])
                )
            )
        if update_page:
            page.update()

    def add_key(e):
        key_val = api_key_input.value.strip()
        if not key_val:
            return
        provider = detect_provider(key_val)
        key_id = f"{provider}_{len(db_manager.get_all_api_keys())+1}"
        db_manager.save_api_key(key_id, provider, key_val)
        api_key_input.value = ""
        detected_text.value = ""
        refresh_keys_list(update_page=False)
        page.update()

    def on_key_change(e):
        val = api_key_input.value.strip()
        if val:
            provider = detect_provider(val)
            detected_text.value = f"🔍 Detected Provider: {provider}"
            detected_text.color = COLOR_PRIMARY_LIGHT
        else:
            detected_text.value = ""
        page.update()

    api_key_input.on_change = on_key_change

    def test_gmail(e):
        if gmail_method.value == "app_password":
            success, msg = email_service.test_app_password(gmail_email_field.value, gmail_app_password_field.value)
        else:
            success, msg = email_service.test_oauth(gmail_credentials_path_field.value)

        gmail_status.value = ("🟢 " if success else "🔴 ") + msg
        gmail_status.color = COLOR_SUCCESS if success else COLOR_ERROR

        if success:
            db_manager.save_api_key("gmail_method", "Gmail", gmail_method.value)
            db_manager.mark_verified("gmail_method", True)
            if gmail_method.value == "app_password":
                db_manager.save_api_key("gmail_email", "Gmail", gmail_email_field.value)
                db_manager.mark_verified("gmail_email", True)
                db_manager.save_api_key("gmail_app_password", "Gmail", gmail_app_password_field.value)
                db_manager.mark_verified("gmail_app_password", True)
            else:
                db_manager.save_api_key("gmail_credentials_path", "Gmail", gmail_credentials_path_field.value)
                db_manager.mark_verified("gmail_credentials_path", True)
        page.update()

    # ---------------- Email Dispatch History Card ----------------
    email_history_container = ft.Container()

    def refresh_email_history(update_page: bool = True):
        logs = db_manager.get_email_logs(limit=100)
        if not logs:
            email_history_container.content = ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Column([
                    ft.Icon(ft.Icons.MARK_EMAIL_READ_OUTLINED, size=36, color=COLOR_TEXT_MUTED),
                    ft.Text("No emails have been dispatched yet.", size=13, color=COLOR_TEXT_SECONDARY),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            )
        else:
            def export_email_history(e):
                if not logs:
                    page.open(ft.SnackBar(ft.Text("No records to export."), bgcolor=ft.Colors.RED))
                    page.update()
                    return
                out_path = os.path.join(DESKTOP_APP_DIR, "output", "email_dispatch_log.xlsx")
                export_data = [
                    {
                        "Date & Time": r.get("timestamp", ""),
                        "Recipient Name": r.get("recipient_name", ""),
                        "Recipient Email": r.get("recipient_email", ""),
                        "Document Type": (r.get("document_type") or "").replace("_", " ").title(),
                        "Subject": r.get("subject", ""),
                        "Attachment": r.get("attachment_filename", ""),
                        "Status": r.get("status", ""),
                        "Sent By": r.get("sent_by", ""),
                        "Error Details": r.get("error_message") or "",
                    }
                    for r in logs
                ]
                excel_export_service.export_to_excel(export_data, out_path, sheet_name="Email Dispatch Log")
                page.open(ft.SnackBar(ft.Text(f"Email log exported to {os.path.basename(out_path)}!"), bgcolor=ft.Colors.GREEN))
                page.update()

            table_rows = []
            for r in logs[:20]:
                is_ok = r.get("status") == "Success"
                badge = status_badge("Success") if is_ok else status_badge("Failed")
                table_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r.get("timestamp", "-"), size=12, color=COLOR_TEXT_MUTED)),
                    ft.DataCell(ft.Text(r.get("recipient_email", "-"), weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text((r.get("document_type") or "-").replace("_", " ").title(), color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(r.get("attachment_filename") or "-", size=12, color=COLOR_TEXT_MUTED)),
                    ft.DataCell(badge),
                ]))

            dt = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date & Time", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Recipient Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Attachment", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ],
                rows=table_rows,
                heading_row_color=COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                border_radius=10,
                column_spacing=18,
            )

            email_history_container.content = ft.Column([
                ft.Row([
                    ft.Text(f"Total Logged Dispatches: {len(logs)}", size=12, color=COLOR_TEXT_SECONDARY),
                    ft.Container(expand=True),
                    secondary_button("Export to Excel", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=export_email_history),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([dt], scroll=ft.ScrollMode.AUTO),
            ], spacing=10)

        if update_page:
            page.update()

    refresh_keys_list(update_page=False)
    refresh_email_history(update_page=False)

    email_history_card = modern_card(ft.Column([
        section_title(ft.Icons.MARK_EMAIL_READ_ROUNDED, "Email Dispatch History & Audit Trail"),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        email_history_container,
    ], spacing=12))

    # ---------------- Reusable Reference Number Card Builder ----------------

    def build_reference_number_card(page, sequence_name: str, card_title: str, default_format: str, icon):
        format_field = ft.TextField(
            label="Reference No Format (use {YEAR} and {NUM})",
            value=default_format, width=350, border_radius=10,
            border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
        )
        padding_field = ft.TextField(
            label="Number Padding (e.g. 3 = 001)", value="3", width=200, border_radius=10,
            border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
        )
        start_field = ft.TextField(
            label="Range Start", width=150, border_radius=10,
            border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
        )
        end_field = ft.TextField(
            label="Range End", width=150, border_radius=10,
            border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
        )
        preview_text = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        remaining_text = ft.Text("", size=12, color=COLOR_TEXT_SECONDARY)

        def load_preview():
            preview = db_manager.preview_next_reference(sequence_name)
            if not preview:
                preview_text.value = "⚠️ No reference range configured yet."
                preview_text.color = COLOR_TEXT_MUTED
                remaining_text.value = ""
            elif preview["exhausted"]:
                preview_text.value = "🔴 Range Exhausted! Please add a new range above."
                preview_text.color = COLOR_ERROR
                remaining_text.value = f"0 of {preview['total']} remaining"
            else:
                preview_text.value = f"🟢 Next Reference No: {preview['formatted']}"
                preview_text.color = COLOR_SUCCESS
                remaining_text.value = f"{preview['remaining']} of {preview['total']} remaining"
            page.update()

        def save_config(e):
            try:
                padding = int(padding_field.value)
                start = int(start_field.value)
                end = int(end_field.value)
                if start > end:
                    raise ValueError("Range Start cannot be greater than Range End")
                db_manager.save_reference_config(sequence_name, format_field.value, padding, start, end)
                load_preview()
                page.open(ft.SnackBar(ft.Text(f"{card_title} saved successfully!"), bgcolor=ft.Colors.GREEN))
            except Exception as ex:
                print("Reference config save error:", ex)
                page.open(
                    ft.SnackBar(
                        ft.Text("Please enter valid whole numbers only for padding, start, and end values, then try again."),
                        bgcolor=ft.Colors.RED,
                    )
                )
            page.update()

        existing_config = db_manager.get_reference_config(sequence_name)
        if existing_config:
            format_field.value = existing_config["format_template"]
            padding_field.value = str(existing_config["padding_width"])
            start_field.value = str(existing_config["range_start"])
            end_field.value = str(existing_config["range_end"])
        load_preview()

        return modern_card(ft.Column([
            section_title(icon, card_title),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(f"Format mein {{YEAR}} aur {{NUM}} placeholders use karo. Jaise: {default_format}",
                    size=12, color=COLOR_TEXT_SECONDARY),
            format_field,
            ft.Row([padding_field, start_field, end_field], spacing=12),
            primary_button("Save Range", icon=ft.Icons.SAVE, on_click=save_config),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            preview_text,
            remaining_text,
        ], spacing=12))

    hr_ref_card = build_reference_number_card(
        page,
        sequence_name="hr_reference",
        card_title="HR Reference Number Configuration",
        default_format="DFY/HR/{YEAR}/{NUM}",
        icon=ft.Icons.TAG,
    )

    emp_ref_card = build_reference_number_card(
        page,
        sequence_name="employee_number",
        card_title="Employee Number Configuration",
        default_format="DFY/EMP/{NUM}",
        icon=ft.Icons.BADGE,
    )

    about_section = modern_card(
        gradient=True,
        content=ft.Column([
            section_title(ft.Icons.INFO_OUTLINE, "About Application"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([
                ft.Text("DFY HRMS Desktop", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                status_badge("v1.0.0 Stable"),
            ], spacing=10),
            ft.Text("Next-generation offline-first desktop suite for healthcare and corporate human resource pipelines.",
                    size=12, color=COLOR_TEXT_SECONDARY),
            ft.Container(height=8),
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=18),
                ft.Text("Designed by Insomniac", size=14, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY_LIGHT),
            ], spacing=8),
            ft.Container(height=6),
            ft.Text("Saurav Kumar", size=15, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ft.Text("Data Professional & Full-Stack Software Engineer", size=12,
                    color=COLOR_TEXT_SECONDARY, italic=True),
            ft.Container(height=4),
            ft.Text(
                "Bridging rigorous public health analytics with scalable software "
                "engineering. Architect of data systems across 22+ districts in Bihar, "
                "offline-first platforms, high-performance dashboards, and AI-integrated "
                "applications that turn complex, unstructured operations into structured efficiency.",
                size=12, color=COLOR_TEXT_SECONDARY,
            ),
            ft.Container(height=10),
            ft.Row([
                ft.Icon(ft.Icons.VISIBILITY_OUTLINED, color=COLOR_PRIMARY_LIGHT, size=18),
                ft.Text("Vision: Suraj Mani", size=14, weight=ft.FontWeight.W_600, color=COLOR_PRIMARY_LIGHT),
            ], spacing=8),
        ], spacing=6)
    )

    return ft.Column([
        # Header
        page_header(
            icon=ft.Icons.SETTINGS_ROUNDED,
            title="⚙️ Settings",
            subtitle="Configure AI providers, Gmail, Reference Numbers, and application backups",
        ),

        ft.Container(height=10),

        # AI Provider API Keys
        modern_card(ft.Column([
            section_title(ft.Icons.SMART_TOY_OUTLINED, "AI Provider API Keys"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text("Koi bhi AI provider ki API key paste karo — system khud pehchan lega.",
                    size=12, color=COLOR_TEXT_SECONDARY),
            ft.Row([
                api_key_input,
                primary_button("Add Key", icon=ft.Icons.ADD, on_click=add_key),
            ], spacing=12),
            detected_text,
            keys_list_column,
        ], spacing=12)),

        ft.Container(height=14),

        # Gmail Configuration
        modern_card(ft.Column([
            section_title(ft.Icons.EMAIL_OUTLINED, "Gmail Configuration"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            gmail_method,
            gmail_email_field,
            gmail_app_password_field,
            gmail_credentials_path_field,
            secondary_button("Test Gmail Connection", icon=ft.Icons.WIFI_TETHERING, on_click=test_gmail),
            gmail_status,
        ], spacing=12)),

        ft.Container(height=14),
        email_history_card,
        ft.Container(height=14),
        hr_ref_card,
        ft.Container(height=14),
        emp_ref_card,
        ft.Container(height=14),
        about_section,
        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
