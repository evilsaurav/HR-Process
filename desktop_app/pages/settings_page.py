import flet as ft
from database import db_manager
from services.api_key_detector import detect_provider
from services import ai_service, email_service


def section_title(icon, text):
    return ft.Row([
        ft.Icon(icon, color="#0B5ED7", size=22),
        ft.Text(text, size=18, weight=ft.FontWeight.BOLD),
    ], spacing=8)


def card(content):
    return ft.Container(
        content=content,
        padding=20,
        border_radius=14,
        bgcolor=ft.Colors.GREY_900,
        border=ft.border.all(1, ft.Colors.GREY_800),
    )


def settings_view(page: ft.Page):
    api_key_input = ft.TextField(
        label="Paste any AI API Key here", password=True, can_reveal_password=True,
        expand=True, border_radius=10,
    )
    detected_text = ft.Text("", size=12, color=ft.Colors.GREY_400)
    keys_list_column = ft.Column(spacing=10)

    gmail_method = ft.RadioGroup(
        value="app_password",
        content=ft.Row([
            ft.Radio(value="app_password", label="App Password"),
            ft.Radio(value="oauth", label="OAuth2 (also enables Drive Backup)"),
        ])
    )
    gmail_email_field = ft.TextField(label="Gmail Address", width=350, border_radius=10)
    gmail_app_password_field = ft.TextField(label="Gmail App Password (16-digit)", password=True,
                                             can_reveal_password=True, width=350, border_radius=10)
    gmail_credentials_path_field = ft.TextField(label="OAuth credentials.json path", width=350, border_radius=10)
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

    def refresh_keys_list():
        keys_list_column.controls.clear()
        for item in db_manager.get_all_api_keys():
            if item["provider"] == "Gmail":
                continue

            status_icon = ft.Icon(
                ft.Icons.CHECK_CIRCLE if item["verified"] else ft.Icons.CANCEL,
                color=ft.Colors.GREEN if item["verified"] else ft.Colors.RED_400, size=20
            )
            masked = item["api_key"][:6] + "••••••" + item["api_key"][-4:] if len(item["api_key"]) > 10 else "••••"

            def make_test(k_id=item["key_id"], provider=item["provider"], key_val=item["api_key"]):
                def _test(e):
                    success, msg = ai_service.test_connection(provider, key_val)
                    db_manager.mark_verified(k_id, success)
                    refresh_keys_list()
                    page.open(ft.SnackBar(ft.Text(msg), bgcolor=ft.Colors.GREEN if success else ft.Colors.RED))
                    page.update()
                return _test

            def make_delete(k_id=item["key_id"]):
                def _del(e):
                    db_manager.delete_api_key(k_id)
                    refresh_keys_list()
                    page.update()
                return _del

            keys_list_column.controls.append(
                ft.Container(
                    padding=14, border_radius=10, bgcolor=ft.Colors.GREY_800,
                    content=ft.Row([
                        status_icon,
                        ft.Column([
                            ft.Text(item["provider"], weight=ft.FontWeight.BOLD),
                            ft.Text(masked, size=12, color=ft.Colors.GREY_400),
                        ], expand=True, spacing=2),
                        ft.TextButton("Test Connection", on_click=make_test(), icon=ft.Icons.WIFI_TETHERING),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_300, on_click=make_delete()),
                    ])
                )
            )
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
        refresh_keys_list()
        page.update()

    def on_key_change(e):
        val = api_key_input.value.strip()
        if val:
            provider = detect_provider(val)
            detected_text.value = f"🔍 Detected Provider: {provider}"
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
        gmail_status.color = ft.Colors.GREEN if success else ft.Colors.RED_400

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

    refresh_keys_list()

    # ---------------- HR Reference Number Section ----------------

    ref_format_field = ft.TextField(
        label="Reference No Format (use {YEAR} and {NUM})",
        value="DFY/HR/{YEAR}/{NUM}", width=350, border_radius=10
    )
    ref_padding_field = ft.TextField(label="Number Padding (e.g. 3 = 001)", value="3", width=200, border_radius=10)
    ref_start_field = ft.TextField(label="Range Start", width=150, border_radius=10)
    ref_end_field = ft.TextField(label="Range End", width=150, border_radius=10)
    ref_preview_text = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
    ref_remaining_text = ft.Text("", size=12, color=ft.Colors.GREY_400)

    def load_ref_preview():
        preview = db_manager.preview_next_reference()
        if not preview:
            ref_preview_text.value = "⚠️ No reference range configured yet."
            ref_preview_text.color = ft.Colors.GREY_400
            ref_remaining_text.value = ""
        elif preview["exhausted"]:
            ref_preview_text.value = "🔴 Range Exhausted! Please add a new range above."
            ref_preview_text.color = ft.Colors.RED_400
            ref_remaining_text.value = f"0 of {preview['total']} remaining"
        else:
            ref_preview_text.value = f"🟢 Next Reference No: {preview['formatted']}"
            ref_preview_text.color = ft.Colors.GREEN
            ref_remaining_text.value = f"{preview['remaining']} of {preview['total']} remaining"
        page.update()

    def save_ref_config(e):
        try:
            padding = int(ref_padding_field.value)
            start = int(ref_start_field.value)
            end = int(ref_end_field.value)
            if start > end:
                raise ValueError("Range Start cannot be greater than Range End")
            db_manager.save_reference_config(ref_format_field.value, padding, start, end)
            load_ref_preview()
            page.open(ft.SnackBar(ft.Text("Reference number range saved successfully!"), bgcolor=ft.Colors.GREEN))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ft.Colors.RED))
        page.update()

    existing_ref_config = db_manager.get_reference_config()
    if existing_ref_config:
        ref_format_field.value = existing_ref_config["format_template"]
        ref_padding_field.value = str(existing_ref_config["padding_width"])
        ref_start_field.value = str(existing_ref_config["range_start"])
        ref_end_field.value = str(existing_ref_config["range_end"])
    load_ref_preview()

    about_section = card(
        ft.Column([
            section_title(ft.Icons.INFO_OUTLINE, "About"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ft.Text("DFY HRMS Desktop", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Version 1.0.0", size=12, color=ft.Colors.GREY_400),
            ft.Container(height=12),
            ft.Row([
                ft.Icon(ft.Icons.CODE, color="#0B5ED7", size=20),
                ft.Text("Designed by Insomniac", size=14, weight=ft.FontWeight.W_600, color="#0B5ED7"),
            ], spacing=8),
            ft.Container(height=10),
            ft.Text("Saurav Kumar", size=15, weight=ft.FontWeight.BOLD),
            ft.Text("Data Professional & Full-Stack Software Engineer", size=12,
                    color=ft.Colors.GREY_300, italic=True),
            ft.Container(height=6),
            ft.Text(
                "I bridge rigorous public health analytics with scalable software "
                "engineering. With 3+ years architecting data systems across 22+ "
                "districts in Bihar, I build offline-first clinical platforms, "
                "high-performance dashboards, and AI-integrated applications that "
                "turn complex, unstructured operations into structured efficiency.",
                size=12, color=ft.Colors.GREY_400,
            ),
            ft.Container(height=14),
            ft.Row([
                ft.Icon(ft.Icons.VISIBILITY_OUTLINED, color="#0B5ED7", size=20),
                ft.Text("Vision: Suraj Mani", size=14, weight=ft.FontWeight.W_600, color="#0B5ED7"),
            ], spacing=8),
        ], spacing=4)
    )

    return ft.Column([
        ft.Text("⚙️ Settings", size=28, weight=ft.FontWeight.BOLD),
        ft.Text("Configure AI providers, Gmail, Reference Numbers, and backups", size=13, color=ft.Colors.GREY_400),
        ft.Container(height=10),

        card(ft.Column([
            section_title(ft.Icons.SMART_TOY_OUTLINED, "AI Provider API Keys"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ft.Text("Koi bhi AI provider ki API key paste karo — system khud pehchan lega.",
                    size=12, color=ft.Colors.GREY_400),
            ft.Row([api_key_input, ft.ElevatedButton("Add Key", icon=ft.Icons.ADD, on_click=add_key)]),
            detected_text,
            keys_list_column,
        ], spacing=10)),

        ft.Container(height=14),

        card(ft.Column([
            section_title(ft.Icons.EMAIL_OUTLINED, "Gmail Configuration"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            gmail_method,
            gmail_email_field,
            gmail_app_password_field,
            gmail_credentials_path_field,
            ft.ElevatedButton("Test Gmail Connection", icon=ft.Icons.WIFI_TETHERING, on_click=test_gmail),
            gmail_status,
        ], spacing=10)),

        ft.Container(height=14),

        card(ft.Column([
            section_title(ft.Icons.TAG, "HR Reference Number Configuration"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ft.Text("Format mein {YEAR} aur {NUM} placeholders use karo. Jaise: DFY/HR/{YEAR}/{NUM}",
                    size=12, color=ft.Colors.GREY_400),
            ref_format_field,
            ft.Row([ref_padding_field, ref_start_field, ref_end_field]),
            ft.ElevatedButton("Save Range", icon=ft.Icons.SAVE, on_click=save_ref_config),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ref_preview_text,
            ref_remaining_text,
        ], spacing=10)),

        ft.Container(height=14),
        about_section,
        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
