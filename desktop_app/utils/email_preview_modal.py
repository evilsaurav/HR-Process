"""
Component: email_preview_modal.py
Purpose: Human-in-the-loop Pre-Mail Verification & Fix Dialog.
Allows HR to inspect and inline-edit recipient email, subject, cover body,
view AI anomaly warnings, inspect attachment, and either Send Immediately
or Schedule for later.
"""

import os
import datetime
import flet as ft
from services import email_service
from services import email_scheduler_service
from services import ai_service
from database import db_manager
from utils.ui_theme import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_CARD_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)


def open_email_preview_modal(
    page: ft.Page,
    candidate: dict,
    document_type: str,
    attachment_path: str,
    on_dispatch_complete=None
):
    """
    Opens the interactive Pre-Mail Verification & Dispatch modal.
    """
    cand_id = candidate.get("id")
    cand_name = candidate.get("candidate_name") or candidate.get("display_name") or "Candidate"
    init_email = candidate.get("work_email") or candidate.get("email") or candidate.get("personal_email") or ""

    # Generate initial draft using AI / template engine
    draft = ai_service.generate_email_cover(candidate, doc_type=document_type)
    init_subject = draft.get("subject", "")
    init_body = draft.get("body", "")

    # Run AI anomaly auditor
    warnings = ai_service.audit_candidate_data_completeness(candidate, doc_type=document_type)

    # UI Controls
    recipient_input = ft.TextField(
        label="Recipient Email Address",
        value=init_email,
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        expand=True,
    )

    subject_input = ft.TextField(
        label="Email Subject",
        value=init_subject,
        prefix_icon=ft.Icons.SUBJECT_OUTLINED,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        expand=True,
    )

    body_input = ft.TextField(
        label="Email Body / Message",
        value=init_body,
        multiline=True,
        min_lines=6,
        max_lines=12,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        expand=True,
    )

    # Schedule date/time input (defaults to tomorrow 10:00 AM)
    default_schedule_time = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d 10:00:00")
    schedule_input = ft.TextField(
        label="Schedule Dispatch (YYYY-MM-DD HH:MM)",
        value=default_schedule_time[:16],
        prefix_icon=ft.Icons.SCHEDULE,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        visible=False,
        width=280,
    )

    status_text = ft.Text("", size=12, color=COLOR_TEXT_SECONDARY, visible=False)

    # Attachment info pill
    att_name = os.path.basename(attachment_path) if attachment_path else "No attachment"
    att_size_kb = round(os.path.getsize(attachment_path) / 1024, 1) if attachment_path and os.path.exists(attachment_path) else 0

    attachment_chip = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.ATTACH_FILE, color=COLOR_PRIMARY_LIGHT, size=18),
            ft.Text(f"{att_name} ({att_size_kb} KB)", size=12, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border_radius=8,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        bgcolor=ft.Colors.with_opacity(0.1, COLOR_PRIMARY),
    )

    # Warning box if anomalies found
    warning_controls = []
    if warnings:
        for w in warnings:
            warning_controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=16, color=COLOR_WARNING),
                    ft.Text(w, size=12, color=COLOR_TEXT_SECONDARY, expand=True),
                ], spacing=6)
            )

    warning_box = ft.Container(
        content=ft.Column([
            ft.Text("⚠️ Verification & Discrepancy Alerts:", size=12, weight=ft.FontWeight.BOLD, color=COLOR_WARNING),
            ft.Column(warning_controls, spacing=4),
        ], spacing=6),
        padding=10,
        border_radius=8,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.3, COLOR_WARNING)),
        bgcolor=ft.Colors.with_opacity(0.08, COLOR_WARNING),
        visible=bool(warnings),
    )

    # Handlers
    def do_send_now(e):
        target_email = recipient_input.value.strip()
        is_valid, err_msg = email_service.validate_recipient_email(target_email)
        if not is_valid:
            status_text.value = err_msg
            status_text.color = COLOR_ERROR
            status_text.visible = True
            page.update()
            return

        status_text.value = "Sending email..."
        status_text.color = COLOR_PRIMARY_LIGHT
        status_text.visible = True
        send_btn.disabled = True
        page.update()

        # Update candidate's email in DB if HR modified it inline
        if cand_id and target_email != init_email:
            db_manager.update_candidate_keka_master(cand_id, {"email": target_email, "work_email": target_email})

        success, message, _ = email_service.send_document_email(
            to_addr=target_email,
            subject=subject_input.value.strip(),
            body=body_input.value.strip(),
            attachment_path=attachment_path,
            candidate_id=cand_id,
            document_type=document_type,
            recipient_name=cand_name,
            sent_by="HR Desktop"
        )

        send_btn.disabled = False
        if success:
            page.close(dlg)
            page.open(ft.SnackBar(ft.Text(f"Email sent successfully to {target_email}!"), bgcolor=ft.Colors.GREEN))
            if on_dispatch_complete:
                on_dispatch_complete()
        else:
            status_text.value = message
            status_text.color = COLOR_ERROR
            status_text.visible = True
        page.update()

    def toggle_schedule(e):
        schedule_input.visible = not schedule_input.visible
        confirm_schedule_btn.visible = schedule_input.visible
        page.update()

    def do_confirm_schedule(e):
        target_email = recipient_input.value.strip()
        is_valid, err_msg = email_service.validate_recipient_email(target_email)
        if not is_valid:
            status_text.value = err_msg
            status_text.color = COLOR_ERROR
            status_text.visible = True
            page.update()
            return

        sched_val = schedule_input.value.strip()
        if not sched_val:
            status_text.value = "Please enter a valid scheduled date & time."
            status_text.color = COLOR_ERROR
            status_text.visible = True
            page.update()
            return

        # Update candidate's email if changed
        if cand_id and target_email != init_email:
            db_manager.update_candidate_keka_master(cand_id, {"email": target_email, "work_email": target_email})

        sched_id = email_scheduler_service.enqueue_scheduled_email(
            candidate_id=cand_id,
            recipient_email=target_email,
            recipient_name=cand_name,
            document_type=document_type,
            subject=subject_input.value.strip(),
            body=body_input.value.strip(),
            attachment_path=attachment_path,
            scheduled_time=sched_val
        )

        if sched_id:
            page.close(dlg)
            page.open(ft.SnackBar(ft.Text(f"Email scheduled for {sched_val} successfully!"), bgcolor=ft.Colors.BLUE))
            if on_dispatch_complete:
                on_dispatch_complete()
        else:
            status_text.value = "Could not schedule email. Please try again."
            status_text.color = COLOR_ERROR
            status_text.visible = True
        page.update()

    def cancel_modal(e):
        page.close(dlg)
        page.update()

    send_btn = ft.ElevatedButton(
        "Send Immediately",
        icon=ft.Icons.SEND_ROUNDED,
        color=ft.Colors.WHITE,
        bgcolor=COLOR_SUCCESS,
        on_click=do_send_now,
    )

    sched_toggle_btn = ft.ElevatedButton(
        "Schedule...",
        icon=ft.Icons.SCHEDULE,
        color=ft.Colors.WHITE,
        bgcolor=COLOR_PRIMARY,
        on_click=toggle_schedule,
    )

    confirm_schedule_btn = ft.ElevatedButton(
        "Confirm Schedule",
        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
        color=ft.Colors.WHITE,
        bgcolor=COLOR_PRIMARY_LIGHT,
        visible=False,
        on_click=do_confirm_schedule,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.MARK_EMAIL_READ_OUTLINED, color=COLOR_PRIMARY_LIGHT, size=24),
            ft.Text("Review & Dispatch Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
        ], spacing=8),
        content=ft.Container(
            width=680,
            content=ft.Column([
                warning_box,
                ft.Row([recipient_input], spacing=10),
                ft.Row([subject_input], spacing=10),
                body_input,
                ft.Row([attachment_chip, schedule_input], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10),
                status_text,
            ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_modal),
            sched_toggle_btn,
            confirm_schedule_btn,
            send_btn,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.open(dlg)
    page.update()
