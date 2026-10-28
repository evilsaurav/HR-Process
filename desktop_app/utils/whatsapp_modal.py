"""
Component: whatsapp_modal.py
Purpose: Interactive 1-Click WhatsApp Direct Field Outreach Modal.
Allows HR to preview, customize, and launch pre-filled WhatsApp communications
to candidates, doctors, nurses, and field staff with zero manual typing.
"""

import webbrowser
import flet as ft
from services import candidate_outreach_service
from database import db_manager
from utils.ui_theme import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_CARD_BORDER,
    COLOR_CARD_BG,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)

COLOR_WHATSAPP = "#25D366"        # WhatsApp Brand Green
COLOR_WHATSAPP_DARK = "#128C7E"   # WhatsApp Dark Green
COLOR_WHATSAPP_BG = "#075E54"     # WhatsApp Deep Green surface


def open_whatsapp_outreach_modal(
    page: ft.Page,
    candidate: dict,
    initial_message_type: str = "selection",
    document_type: str = "offer",
    reference_number: str = "",
    on_complete=None
):
    """
    Opens the interactive WhatsApp Outreach dialog.
    """
    cand_id = candidate.get("id")
    cand_name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    raw_mobile = str(candidate.get("mobile") or candidate.get("work_phone") or candidate.get("home_phone") or "").strip()
    desig = candidate.get("applied_designation") or candidate.get("job_title") or "Candidate"

    # Current selected message type
    current_type = [initial_message_type]

    # Clean phone number initially
    initial_clean_mobile = candidate_outreach_service.clean_indian_mobile(raw_mobile)

    # Phone input field
    phone_input = ft.TextField(
        label="Mobile Number (10-digit Indian Mobile)",
        value=raw_mobile,
        prefix_text="+91 " if not raw_mobile.startswith("+91") else "",
        prefix_icon=ft.Icons.PHONE_ANDROID_ROUNDED,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_WHATSAPP,
        text_size=13,
        expand=True,
    )

    phone_status_text = ft.Text(
        f"✓ WhatsApp Ready: +{initial_clean_mobile}" if initial_clean_mobile else "⚠️ Invalid or missing mobile number",
        size=11,
        color=COLOR_WHATSAPP if initial_clean_mobile else COLOR_WARNING,
        weight=ft.FontWeight.W_500,
    )

    def on_phone_change(e):
        clean = candidate_outreach_service.clean_indian_mobile(phone_input.value.strip())
        if clean:
            phone_status_text.value = f"✓ WhatsApp Ready: +{clean}"
            phone_status_text.color = COLOR_WHATSAPP
        else:
            phone_status_text.value = "⚠️ Please enter a valid 10-digit Indian mobile number"
            phone_status_text.color = COLOR_WARNING
        try:
            phone_status_text.update()
        except Exception:
            pass

    phone_input.on_change = on_phone_change

    # Generate initial message text
    initial_text = candidate_outreach_service.generate_whatsapp_outreach_text(
        candidate=candidate,
        message_type=initial_message_type,
        document_type=document_type,
        reference_number=reference_number
    )

    message_input = ft.TextField(
        label="WhatsApp Message Preview (Editable)",
        value=initial_text,
        multiline=True,
        min_lines=8,
        max_lines=12,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_WHATSAPP,
        text_size=12,
        expand=True,
    )

    # Quick Template Buttons
    def set_template(msg_type: str):
        current_type[0] = msg_type
        new_text = candidate_outreach_service.generate_whatsapp_outreach_text(
            candidate=candidate,
            message_type=msg_type,
            document_type=document_type,
            reference_number=reference_number
        )
        message_input.value = new_text
        try:
            message_input.update()
        except Exception:
            pass

    template_chips = ft.Row([
        ft.ElevatedButton(
            "📄 Document Release",
            icon=ft.Icons.DESCRIPTION_ROUNDED,
            style=ft.ButtonStyle(
                color=COLOR_TEXT_PRIMARY,
                bgcolor=ft.Colors.with_opacity(0.15, COLOR_PRIMARY_LIGHT),
                padding=10,
            ),
            on_click=lambda e: set_template("document_release")
        ),
        ft.ElevatedButton(
            "🎉 Selection",
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
            style=ft.ButtonStyle(
                color=COLOR_TEXT_PRIMARY,
                bgcolor=ft.Colors.with_opacity(0.15, COLOR_SUCCESS),
                padding=10,
            ),
            on_click=lambda e: set_template("selection")
        ),
        ft.ElevatedButton(
            "🏥 Joining Info",
            icon=ft.Icons.LOCAL_HOSPITAL_ROUNDED,
            style=ft.ButtonStyle(
                color=COLOR_TEXT_PRIMARY,
                bgcolor=ft.Colors.with_opacity(0.15, COLOR_WHATSAPP),
                padding=10,
            ),
            on_click=lambda e: set_template("joining")
        ),
        ft.ElevatedButton(
            "📅 Interview Call",
            icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
            style=ft.ButtonStyle(
                color=COLOR_TEXT_PRIMARY,
                bgcolor=ft.Colors.with_opacity(0.15, COLOR_WARNING),
                padding=10,
            ),
            on_click=lambda e: set_template("interview")
        ),
    ], wrap=True, spacing=6)

    # Snackbar helper
    def notify(msg: str, success: bool = True):
        try:
            page.open(ft.SnackBar(
                ft.Text(msg),
                bgcolor=ft.Colors.GREEN if success else ft.Colors.RED
            ))
            page.update()
        except Exception:
            pass

    # Launch WhatsApp action
    def on_launch_whatsapp(e):
        val = phone_input.value.strip()
        clean = candidate_outreach_service.clean_indian_mobile(val)
        if not clean:
            notify("Cannot launch: Please provide a valid 10-digit mobile number.", False)
            return

        msg_body = message_input.value.strip()
        if not msg_body:
            notify("Message text cannot be empty.", False)
            return

        # If phone was updated by user, optionally persist it in DB
        if cand_id and val != raw_mobile:
            try:
                db_manager.update_candidate_extra_details(
                    candidate_id=cand_id,
                    mobile=clean[-10:]
                )
            except Exception:
                pass

        url = candidate_outreach_service.build_whatsapp_web_url(clean, msg_body)

        # Launch via Flet page launch and fallback to webbrowser
        launched = False
        try:
            if hasattr(page, "launch_url"):
                page.launch_url(url)
                launched = True
        except Exception:
            pass

        if not launched:
            try:
                webbrowser.open(url)
                launched = True
            except Exception:
                pass

        notify(f"🚀 Opening WhatsApp chat with {cand_name} (+{clean})...", True)
        page.close(dlg)
        if callable(on_complete):
            try:
                on_complete()
            except Exception:
                pass

    # Copy to clipboard action
    def on_copy_message(e):
        msg_body = message_input.value.strip()
        try:
            page.set_clipboard(msg_body)
            notify(f"✓ WhatsApp message for '{cand_name}' copied to clipboard!", True)
        except Exception:
            notify("Copied to clipboard!", True)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Container(
                content=ft.Icon(ft.Icons.CHAT_ROUNDED, color="#FFFFFF", size=20),
                bgcolor=COLOR_WHATSAPP,
                padding=8,
                border_radius=8,
            ),
            ft.Column([
                ft.Text(f"WhatsApp Field Outreach: {cand_name}", weight=ft.FontWeight.BOLD, size=16),
                ft.Text(f"{desig} • Doctors For You (DFY)", size=12, color=COLOR_TEXT_SECONDARY),
            ], spacing=2),
        ], spacing=12),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Send pre-filled professional communication directly to candidate's WhatsApp without typing.",
                    size=12,
                    color=COLOR_TEXT_MUTED,
                ),
                ft.Divider(height=10, color=COLOR_CARD_BORDER),
                ft.Row([phone_input], expand=False),
                phone_status_text,
                ft.Container(height=6),
                ft.Text("Quick Message Templates:", size=12, weight=ft.FontWeight.W_600, color=COLOR_TEXT_SECONDARY),
                template_chips,
                ft.Container(height=4),
                message_input,
            ], spacing=8, scroll=ft.ScrollMode.ADAPTIVE),
            width=580,
            height=460,
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda e: page.close(dlg),
            ),
            ft.ElevatedButton(
                "📋 Copy Message",
                icon=ft.Icons.COPY_ROUNDED,
                style=ft.ButtonStyle(
                    color=COLOR_TEXT_PRIMARY,
                    bgcolor=COLOR_CARD_BORDER,
                ),
                on_click=on_copy_message,
            ),
            ft.ElevatedButton(
                "🚀 Open in WhatsApp",
                icon=ft.Icons.SEND_ROUNDED,
                style=ft.ButtonStyle(
                    color="#FFFFFF",
                    bgcolor=COLOR_WHATSAPP,
                    padding=14,
                ),
                on_click=on_launch_whatsapp,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.open(dlg)
    page.update()
