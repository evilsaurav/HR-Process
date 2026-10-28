import os
from typing import Optional, List, Dict, Any
import flet as ft
from config import STATUS_OPTIONS, PRIMARY_COLOR, DESKTOP_APP_DIR
from database import db_manager
from services import sheet_processor
from services import excel_export_service
from services import email_service
from services import ai_service
from services import candidate_outreach_service
from utils.whatsapp_modal import open_whatsapp_outreach_modal
from utils.flet_compat import register_overlay_control
from utils.ui_theme import (
    modern_card,
    page_header,
    section_title,
    status_badge,
    primary_button,
    secondary_button,
    show_export_success_dialog,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_BG_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_PRIMARY_LIGHT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
    COLOR_WARNING_BG,
)


def joining_process_view(page: ft.Page, initial_filter: Optional[str] = None):
    # Feedback message helper matching app style
    def show_message(text: str, is_success: bool = True):
        page.open(
            ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED,
            )
        )
        page.update()

    # Upload Feedback Area
    upload_status_column = ft.Column(spacing=10)

    # Candidate table container
    table_container = ft.Container()

    # Pagination state
    pagination_state = {
        "page": 1,
        "page_size": 25,
        "total_pages": 1,
        "total_records": 0,
    }

    def on_page_size_change(e):
        try:
            pagination_state["page_size"] = int(e.control.value)
        except Exception:
            pagination_state["page_size"] = 25
        refresh_candidates(reset_page=True)

    def change_page(delta: int):
        new_page = pagination_state["page"] + delta
        if 1 <= new_page <= pagination_state["total_pages"]:
            pagination_state["page"] = new_page
            refresh_candidates(reset_page=False)

    page_size_dropdown = ft.Dropdown(
        value="25",
        width=95,
        dense=True,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        options=[
            ft.dropdown.Option("15"),
            ft.dropdown.Option("25"),
            ft.dropdown.Option("50"),
            ft.dropdown.Option("100"),
        ],
        on_change=on_page_size_change,
    )

    btn_prev_page = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        tooltip="Previous Page",
        icon_color=COLOR_PRIMARY_LIGHT,
        disabled=True,
        on_click=lambda e: change_page(-1),
    )

    btn_next_page = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        tooltip="Next Page",
        icon_color=COLOR_PRIMARY_LIGHT,
        disabled=True,
        on_click=lambda e: change_page(1),
    )

    page_indicator_text = ft.Text("Page 1 of 1", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)
    record_range_text = ft.Text("Showing 0–0 of 0 candidates", size=12, color=COLOR_TEXT_SECONDARY)

    pagination_container = ft.Container(
        padding=ft.padding.only(top=10, bottom=4, left=4, right=4),
        content=ft.Row([
            ft.Row([
                ft.Text("Rows per page:", size=12, color=COLOR_TEXT_SECONDARY),
                page_size_dropdown,
                record_range_text,
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                btn_prev_page,
                page_indicator_text,
                btn_next_page,
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
    )

    # Search & Filter Fields
    search_field = ft.TextField(
        label="Search candidates (Name, Mobile, Designation, Location)...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        on_change=lambda e: refresh_candidates(reset_page=True),
    )

    status_filter = ft.Dropdown(
        label="Status Filter",
        value="All",
        width=200,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        options=[ft.dropdown.Option("All")] + [ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
        on_change=lambda e: refresh_candidates(reset_page=True),
    )

    candidate_count_text = ft.Text("Candidates: 0", size=13, color=COLOR_TEXT_SECONDARY)

    show_archived_switch = ft.Switch(
        label="Show Archived",
        value=False,
        active_color=COLOR_WARNING,
        tooltip="Toggle between active and archived candidates",
        on_change=lambda e: refresh_candidates(reset_page=True),
    )

    # Selection state for candidate checkboxes
    selected_candidate_ids = set()

    # Quick filter tab state: "all" or "pending_welcome"
    init_mode = "all"
    if initial_filter:
        flt_str = str(initial_filter).lower().strip()
        if "selected" in flt_str or "pending" in flt_str:
            init_mode = "pending_welcome"

    quick_filter_state = {"mode": init_mode}
    is_pending_init = (init_mode == "pending_welcome")

    # Current candidate list cache for select-all operations
    current_candidates_cache = {"list": []}

    tab_all_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED, size=16),
            ft.Text("All Candidates", weight=ft.FontWeight.W_600),
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=COLOR_CARD_BG_HOVER if is_pending_init else PRIMARY_COLOR,
        color=COLOR_TEXT_PRIMARY if is_pending_init else ft.Colors.WHITE,
        on_click=lambda e: set_quick_filter("all"),
    )

    pending_welcome_badge_text = ft.Text("0", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    pending_welcome_badge_container = ft.Container(
        content=pending_welcome_badge_text,
        bgcolor=COLOR_WARNING,
        padding=ft.padding.symmetric(horizontal=7, vertical=2),
        border_radius=10,
    )

    tab_pending_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.MARK_EMAIL_UNREAD_OUTLINED, size=16, color=COLOR_WARNING),
            ft.Text("🎉 Selected (Pending Welcome Email)", weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
            pending_welcome_badge_container,
        ], spacing=6, tight=True, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=PRIMARY_COLOR if is_pending_init else COLOR_CARD_BG_HOVER,
        color=ft.Colors.WHITE if is_pending_init else COLOR_TEXT_PRIMARY,
        on_click=lambda e: set_quick_filter("pending_welcome"),
    )

    def set_quick_filter(mode: str):
        quick_filter_state["mode"] = mode
        if mode == "pending_welcome":
            tab_pending_button.bgcolor = PRIMARY_COLOR
            tab_pending_button.color = ft.Colors.WHITE
            tab_all_button.bgcolor = COLOR_CARD_BG_HOVER
            tab_all_button.color = COLOR_TEXT_PRIMARY
        else:
            tab_all_button.bgcolor = PRIMARY_COLOR
            tab_all_button.color = ft.Colors.WHITE
            tab_pending_button.bgcolor = COLOR_CARD_BG_HOVER
            tab_pending_button.color = COLOR_TEXT_PRIMARY
        refresh_candidates(reset_page=True)

    btn_review_send_welcome_text = ft.Text("✉️ Review & Send Welcome Emails", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    btn_review_send_welcome = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.MARK_EMAIL_READ_OUTLINED, size=16, color=ft.Colors.WHITE),
            btn_review_send_welcome_text,
        ], spacing=6, tight=True),
        bgcolor=COLOR_SUCCESS,
        color=ft.Colors.WHITE,
        tooltip="Review and stage/dispatch official selection welcome email",
        on_click=lambda e: open_welcome_email_modal_for_selected(),
    )

    select_all_checkbox = ft.Checkbox(
        tooltip="Select / Deselect all displayed candidates",
    )

    def on_select_all_toggle(e):
        val = bool(e.control.value)
        displayed = current_candidates_cache.get("list", [])
        if val:
            for c in displayed:
                selected_candidate_ids.add(c["id"])
        else:
            for c in displayed:
                selected_candidate_ids.discard(c["id"])
        refresh_candidates(reset_page=True)

    select_all_checkbox.on_change = on_select_all_toggle

    # ---------------- Export to Excel Handler ----------------
    def export_candidates_clicked(e):
        term = search_field.value.strip() if search_field.value else ""
        is_archived = bool(show_archived_switch.value)
        if is_archived:
            candidates = db_manager.get_archived_candidates(search_term=term)
            sheet_title = "Archived Candidates"
            out_filename = "archived_candidates.xlsx"
        else:
            selected_status = status_filter.value if status_filter.value else "All"
            candidates = db_manager.get_all_candidates(search_term=term, status_filter=selected_status)
            sheet_title = "Candidate Pipeline"
            out_filename = "candidate_pipeline.xlsx"

        if not candidates:
            show_message("No records to export.", False)
            return
        out_path = os.path.join(DESKTOP_APP_DIR, "output", out_filename)
        export_data = []
        for c in candidates:
            row = {
                "Candidate Name": c.get("candidate_name") or "",
                "Mobile": c.get("mobile") or "",
                "Email": c.get("email") or "",
                "Applied Designation": c.get("applied_designation") or "",
                "Salary": c.get("negotiated_salary") or "",
                "Location": c.get("contact_location") or "",
                "Status": c.get("status") or "Applied",
                "Welcome Email": "Sent" if c.get("welcome_email_sent") else ("Pending" if c.get("status") == "Selected" else "N/A"),
                "Welcome Email Sent At": c.get("welcome_email_sent_at") or "",
            }
            if is_archived:
                row["Archived At"] = c.get("archived_at") or ""
            export_data.append(row)

        excel_export_service.export_to_excel(export_data, out_path, sheet_name=sheet_title)
        show_message(f"Candidate list exported to {os.path.basename(out_path)}!", True)
        show_export_success_dialog(page, out_path, record_count=len(export_data), report_title=sheet_title)

    # ---------------- Archive Confirmation Dialog (Soft Delete) ----------------
    def confirm_delete(cand_id: int, cand_name: str):
        def do_archive(e):
            ok = db_manager.archive_candidate(cand_id)
            page.close(dlg)
            refresh_candidates(reset_page=True)
            if ok:
                show_message(f"Candidate '{cand_name}' archived.", True)
            else:
                show_message(f"Could not archive candidate '{cand_name}'. Please try again.", False)
            page.update()

        def cancel_archive(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ARCHIVE_OUTLINED, color=COLOR_WARNING, size=24),
                ft.Text("Archive Candidate", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ], spacing=8),
            content=ft.Text(
                f"This candidate will be archived and removed from this list. "
                "You can restore it later from the Archive view. Continue?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_archive),
                ft.ElevatedButton("Archive", color=ft.Colors.WHITE, bgcolor=COLOR_WARNING, on_click=do_archive),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
        page.update()

    # ---------------- Restore Confirmation Dialog ----------------
    def confirm_restore(cand_id: int, cand_name: str):
        def do_restore(e):
            ok = db_manager.restore_candidate(cand_id)
            page.close(dlg)
            refresh_candidates(reset_page=True)
            if ok:
                show_message(f"Candidate '{cand_name}' restored to active list.", True)
            else:
                show_message(f"Could not restore candidate '{cand_name}'. Please try again.", False)
            page.update()

        def cancel_restore(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.UNARCHIVE_OUTLINED, color=COLOR_SUCCESS, size=24),
                ft.Text("Restore Candidate", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ], spacing=8),
            content=ft.Text(
                f"Restore candidate '{cand_name}' back to the active list? "
                "Their previous status and details will be preserved."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_restore),
                ft.ElevatedButton("Restore", color=ft.Colors.WHITE, bgcolor=COLOR_SUCCESS, on_click=do_restore),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
        page.update()

    # ---------------- Permanent Delete Confirmation Dialog (Archive View Only) ----------------
    def confirm_permanent_delete(cand_id: int, cand_name: str):
        # Strict constraint: only archived candidates can be permanently deleted
        cand = db_manager.get_candidate_by_id(cand_id)
        if not cand or not cand.get("archived"):
            show_message("Only archived candidates can be permanently deleted.", False)
            return

        counts = db_manager.get_candidate_related_counts(cand_id)
        n_docs = counts.get("documents", 0)
        n_emails = counts.get("emails", 0)

        if n_docs > 0 or n_emails > 0:
            dialog_message = (
                f"'{cand_name}' has {n_docs} generated document(s) and {n_emails} sent email record(s). "
                "Permanently deleting this candidate will also delete ALL of these records. "
                "This cannot be undone. Are you sure you want to continue?"
            )
        else:
            dialog_message = f"Permanently delete '{cand_name}'? This cannot be undone."

        def do_perm_delete(e):
            ok = db_manager.permanently_delete_candidate(cand_id)
            page.close(dlg)
            refresh_candidates(reset_page=True)
            if ok:
                show_message(f"'{cand_name}' has been permanently deleted.", True)
            else:
                show_message(f"Could not delete '{cand_name}'. Please try again.", False)
            page.update()

        def cancel_perm_delete(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.DELETE_FOREVER, color=COLOR_ERROR, size=24),
                ft.Text("Permanently Delete Candidate", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ], spacing=8),
            content=ft.Text(dialog_message),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_perm_delete),
                ft.ElevatedButton(
                    "Permanently Delete",
                    color=ft.Colors.WHITE,
                    bgcolor=COLOR_ERROR,
                    on_click=do_perm_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
        page.update()

    # ---------------- Welcome Email Review & Dispatch Modal ----------------
    def show_welcome_email_review_modal(target_candidates: list[dict]):
        if not target_candidates:
            show_message("Please select at least one candidate.", False)
            return

        is_bulk = len(target_candidates) > 1
        first_cand = target_candidates[0]

        # If single candidate, pre-fill with their exact details
        if not is_bulk:
            c_name = first_cand.get("candidate_name") or "Candidate"
            c_desig = first_cand.get("applied_designation") or "the position"
            c_loc = first_cand.get("contact_location") or "our project office"
            default_subject = "Welcome to Doctors For You (DFY) - Selection Confirmation"
            default_body = (
                f"Dear {c_name},\n\n"
                f"Congratulations! We are delighted to inform you that you have been selected for the position of {c_desig} "
                f"with Doctors For You (DFY), based at {c_loc}.\n\n"
                f"Our selection committee was impressed by your qualifications and experience. We believe your commitment "
                f"will be a valuable addition to our healthcare and humanitarian mission.\n\n"
                f"Next Steps & Onboarding Guidance:\n"
                f"1. Formal Documentation: Our HR Operations team will prepare and issue your official Offer / Appointment Letter shortly.\n"
                f"2. Document Verification: Please ensure your KYC documents (Aadhaar Card, PAN Card, educational certificates, experience letters, and bank details) are ready for submission.\n"
                f"3. Acceptance Confirmation: Kindly reply to this email to confirm your acceptance of this selection and your earliest tentative joining date.\n\n"
                f"If you have any questions or require any assistance, please feel free to reply directly to this email.\n\n"
                f"We look forward to welcoming you to the Doctors For You team!\n\n"
                f"Warm regards,\n"
                f"Human Resources Team\n"
                f"Doctors For You (DFY)\n"
                f"https://doctorsforyou.org"
            )
        else:
            default_subject = "Welcome to Doctors For You (DFY) - Selection Confirmation"
            default_body = (
                f"Dear {{candidate_name}},\n\n"
                f"Congratulations! We are delighted to inform you that you have been selected for the position of {{job_title}} "
                f"with Doctors For You (DFY), based at {{location}}.\n\n"
                f"Our selection committee was impressed by your qualifications and experience. We believe your commitment "
                f"will be a valuable addition to our healthcare and humanitarian mission.\n\n"
                f"Next Steps & Onboarding Guidance:\n"
                f"1. Formal Documentation: Our HR Operations team will prepare and issue your official Offer / Appointment Letter shortly.\n"
                f"2. Document Verification: Please ensure your KYC documents (Aadhaar Card, PAN Card, educational certificates, experience letters, and bank details) are ready for submission.\n"
                f"3. Acceptance Confirmation: Kindly reply to this email to confirm your acceptance of this selection and your earliest tentative joining date.\n\n"
                f"If you have any questions or require any assistance, please feel free to reply directly to this email.\n\n"
                f"We look forward to welcoming you to the Doctors For You team!\n\n"
                f"Warm regards,\n"
                f"Human Resources Team\n"
                f"Doctors For You (DFY)\n"
                f"https://doctorsforyou.org"
            )

        # Recipients display pills
        recipient_pills = []
        missing_email_count = 0
        for cand in target_candidates:
            cand_name = cand.get("candidate_name") or "Candidate"
            cand_email = cand.get("work_email") or cand.get("email") or cand.get("personal_email") or ""
            valid_email = bool(cand_email and "@" in cand_email)
            if not valid_email:
                missing_email_count += 1
            recipient_pills.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if valid_email else ft.Icons.WARNING_AMBER_ROUNDED,
                            color=COLOR_SUCCESS if valid_email else COLOR_WARNING,
                            size=14,
                        ),
                        ft.Text(cand_name, size=12, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                        ft.Text(f"<{cand_email}>" if valid_email else "<No Email>", size=11, color=COLOR_TEXT_MUTED if valid_email else COLOR_WARNING),
                    ], spacing=6, tight=True),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border_radius=8,
                    bgcolor=COLOR_CARD_BG_HOVER,
                    border=ft.Border.all(1, COLOR_CARD_BORDER if valid_email else COLOR_WARNING),
                )
            )

        subject_input = ft.TextField(
            label="Email Subject",
            value=default_subject,
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )

        body_input = ft.TextField(
            label="Email Message Body",
            value=default_body,
            multiline=True,
            min_lines=8,
            max_lines=14,
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )

        offline_override_chk = ft.Checkbox(
            label="Mark as Sent without SMTP (e.g. sent via external mail or offline)",
            value=False,
        )

        modal_status_text = ft.Text("", size=12, color=COLOR_TEXT_SECONDARY, visible=False)
        modal_progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)

        def close_dialog(e=None):
            page.close(dlg)
            page.update()

        def do_send_welcome_emails(e):
            modal_status_text.visible = True
            modal_status_text.value = f"Dispatching welcome emails to {len(target_candidates)} candidate(s)..."
            modal_progress.visible = True
            send_btn.disabled = True
            cancel_btn.disabled = True
            page.update()

            subj_tmpl = subject_input.value.strip() or "Welcome to Doctors For You (DFY) - Selection Confirmation"
            body_tmpl = body_input.value or ""
            use_offline_override = bool(offline_override_chk.value)

            success_cands = []
            fail_cands = []

            for cand in target_candidates:
                cid = cand.get("id")
                c_name = cand.get("candidate_name") or "Candidate"
                c_email = cand.get("work_email") or cand.get("email") or cand.get("personal_email") or ""
                c_desig = cand.get("applied_designation") or "the position"
                c_loc = cand.get("contact_location") or "our project office"

                cand_subject = subj_tmpl.replace("{candidate_name}", c_name).replace("{job_title}", c_desig).replace("{location}", c_loc)
                cand_body = body_tmpl.replace("{candidate_name}", c_name).replace("{job_title}", c_desig).replace("{location}", c_loc)

                if use_offline_override:
                    db_manager.update_candidate_welcome_email_status(cid, True)
                    success_cands.append(c_name)
                    continue

                if not c_email or "@" not in c_email:
                    fail_cands.append(f"{c_name} (Missing email address)")
                    continue

                ok, msg = email_service.send_email_smtp(
                    to_addr=c_email,
                    subject=cand_subject,
                    body=cand_body,
                    candidate_id=cid,
                    document_type="welcome_email",
                    recipient_name=c_name,
                )

                if ok:
                    db_manager.update_candidate_welcome_email_status(cid, True)
                    success_cands.append(c_name)
                else:
                    fail_cands.append(f"{c_name} ({msg})")

            page.close(dlg)

            # Uncheck processed candidates
            for cand in target_candidates:
                selected_candidate_ids.discard(cand.get("id"))

            refresh_candidates(reset_page=True)

            if success_cands and not fail_cands:
                show_message(f"🎉 Welcome email sent successfully to {len(success_cands)} candidate(s)!", True)
            elif success_cands and fail_cands:
                show_message(
                    f"Sent to {len(success_cands)} candidate(s). {len(fail_cands)} failed: {fail_cands[0]}",
                    False,
                )
            else:
                err_msg = fail_cands[0] if fail_cands else "Failed to send welcome email."
                show_message(f"Could not send welcome email: {err_msg}", False)

            page.update()

        send_btn = ft.ElevatedButton(
            f"🚀 Send Welcome {'Emails' if is_bulk else 'Email'} ({len(target_candidates)})",
            color=ft.Colors.WHITE,
            bgcolor=COLOR_SUCCESS,
            on_click=do_send_welcome_emails,
        )
        cancel_btn = ft.TextButton("Cancel", on_click=close_dialog)

        hints = []
        if is_bulk:
            hints.append(
                ft.Text(
                    "💡 Tip: Tags {candidate_name}, {job_title}, and {location} will be personalized automatically for each candidate.",
                    size=12,
                    color=COLOR_PRIMARY_LIGHT,
                )
            )
        if missing_email_count > 0:
            hints.append(
                ft.Text(
                    f"⚠️ Warning: {missing_email_count} candidate(s) do not have a valid email address.",
                    size=12,
                    color=COLOR_WARNING,
                    weight=ft.FontWeight.BOLD,
                )
            )

        content_column = ft.Column([
            ft.Text(
                f"Stage and dispatch official selection confirmation welcome email to {len(target_candidates)} candidate{'s' if is_bulk else ''}.",
                size=13,
                color=COLOR_TEXT_SECONDARY,
            ),
            ft.Container(height=4),
            ft.Text("Recipients:", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ft.Container(
                content=ft.Row(recipient_pills, wrap=True, spacing=6),
            ),
            *hints,
            ft.Container(height=4),
            subject_input,
            body_input,
            offline_override_chk,
            ft.Row([modal_progress, modal_status_text], spacing=8),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.MARK_EMAIL_READ_OUTLINED, color=PRIMARY_COLOR, size=24),
                ft.Text("Review & Send Welcome Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
            ], spacing=8),
            content=ft.Container(content=content_column, width=680, height=480),
            actions=[cancel_btn, send_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
        page.update()

    def open_welcome_email_modal_for_selected():
        if selected_candidate_ids:
            cands_to_stage = [db_manager.get_candidate_by_id(cid) for cid in selected_candidate_ids]
            cands_to_stage = [c for c in cands_to_stage if c]
            if cands_to_stage:
                show_welcome_email_review_modal(cands_to_stage)
                return

        # If none checked, but user is on pending_welcome tab:
        if quick_filter_state.get("mode") == "pending_welcome":
            pending_list = db_manager.get_selected_candidates_pending_welcome()
            if pending_list:
                show_welcome_email_review_modal(pending_list)
                return
            else:
                show_message("No candidates currently pending welcome email.", False)
                return

        show_message("Please select at least one candidate using the checkboxes.", False)

    def update_selection_counts():
        n = len(selected_candidate_ids)
        btn_review_send_welcome_text.value = f"✉️ Review & Send Welcome Emails ({n})" if n > 0 else "✉️ Review & Send Welcome Emails"
        displayed = current_candidates_cache.get("list", [])
        select_all_checkbox.value = len(displayed) > 0 and all(c["id"] in selected_candidate_ids for c in displayed)
        page.update()

    # ---------------- Edit Candidate Profile Modal ----------------
    def show_edit_candidate_modal(cand_item: dict):
        cand_id = cand_item["id"]
        fresh_cand = db_manager.get_candidate_by_id(cand_id) or cand_item

        c_name = fresh_cand.get("candidate_name") or ""
        name_field = ft.TextField(
            label="Candidate Full Name",
            value=c_name,
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        mob_field = ft.TextField(
            label="Mobile Number (10 digits)",
            value=str(fresh_cand.get("mobile") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        email_field = ft.TextField(
            label="Email Address",
            value=str(fresh_cand.get("email") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        desig_field = ft.TextField(
            label="Applied Designation / Role",
            value=str(fresh_cand.get("applied_designation") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        salary_field = ft.TextField(
            label="Monthly Salary (₹)",
            value=str(fresh_cand.get("negotiated_salary") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        dept_field = ft.TextField(
            label="Department",
            value=str(fresh_cand.get("department") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        addr_field = ft.TextField(
            label="Full Address / Location",
            value=str(fresh_cand.get("full_address") or fresh_cand.get("contact_location") or ""),
            multiline=True,
            min_lines=2,
            max_lines=3,
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
        )
        date_joined_field = ft.TextField(
            label="Date Joined (YYYY-MM-DD)",
            value=str(fresh_cand.get("date_joined") or ""),
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )
        curr_status = fresh_cand.get("status") or "Applied"
        status_field = ft.Dropdown(
            label="Pipeline Status",
            value=curr_status if curr_status in STATUS_OPTIONS else "Applied",
            options=[ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
            border_radius=8,
            border_color=COLOR_CARD_BORDER,
            focused_border_color=COLOR_PRIMARY_LIGHT,
            expand=True,
        )

        def on_save_candidate_details(e):
            n_val = (name_field.value or "").strip()
            m_val = (mob_field.value or "").strip()
            em_val = (email_field.value or "").strip()
            des_val = (desig_field.value or "").strip()
            sal_val = (salary_field.value or "").strip()
            dep_val = (dept_field.value or "").strip()
            addr_val = (addr_field.value or "").strip()
            dj_val = (date_joined_field.value or "").strip()
            st_val = status_field.value

            if not n_val:
                show_message("Candidate name cannot be empty.", False)
                return

            update_data = {
                "candidate_name": n_val,
                "mobile": m_val,
                "email": em_val,
                "applied_designation": des_val,
                "department": dep_val,
                "full_address": addr_val,
                "contact_location": addr_val,
                "date_joined": dj_val,
                "status": st_val,
            }
            if sal_val:
                try:
                    update_data["negotiated_salary"] = float(sal_val)
                except ValueError:
                    pass

            ok = db_manager.update_candidate(cand_id, update_data)
            page.close(dlg)
            if ok:
                show_message(f"Candidate details for '{n_val}' updated successfully!", True)
                refresh_candidates(reset_page=False)
            else:
                show_message("Failed to update candidate details.", False)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                ft.Text(f"Edit Candidate Profile (#{cand_id})", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY, size=17),
            ], spacing=8),
            content=ft.Container(
                width=580,
                content=ft.Column([
                    ft.Text(
                        "Updating these details updates the candidate database record across the pipeline and document generator.",
                        size=12, color=COLOR_TEXT_SECONDARY
                    ),
                    ft.Divider(height=10, color=COLOR_CARD_BORDER),
                    ft.Row([name_field, desig_field], spacing=10),
                    ft.Row([email_field, mob_field], spacing=10),
                    ft.Row([dept_field, salary_field], spacing=10),
                    addr_field,
                    ft.Row([date_joined_field, status_field], spacing=10),
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                secondary_button("Cancel", on_click=lambda ev: page.close(dlg)),
                primary_button("Save & Update", icon=ft.Icons.SAVE_OUTLINED, on_click=on_save_candidate_details),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)
        page.update()

    # ---------------- Inline Status Change Handler ----------------
    def make_status_change(cand_id: int, cand_name: str):
        def on_change(e):
            new_status = e.control.value
            db_manager.update_candidate_status(cand_id, new_status)
            show_message(f"Status for '{cand_name}' updated to '{new_status}'", True)
            refresh_candidates(reset_page=True)
        return on_change

    # ---------------- Refresh Candidates Table ----------------
    def refresh_candidates(reset_page: bool = False):
        if reset_page:
            pagination_state["page"] = 1

        term = search_field.value.strip() if search_field.value else ""
        is_archived = bool(show_archived_switch.value)

        # Update pending welcome emails counter badge
        pending_welcome_list = db_manager.get_selected_candidates_pending_welcome()
        pending_count = len(pending_welcome_list)
        pending_welcome_badge_text.value = str(pending_count)

        is_pending_tab = (quick_filter_state.get("mode") == "pending_welcome") and not is_archived

        # UI visibility and disabled states
        status_filter.disabled = is_archived or is_pending_tab
        tab_pending_button.visible = not is_archived

        # Tab button styling
        if is_pending_tab:
            tab_all_button.bgcolor = ft.Colors.TRANSPARENT
            tab_all_button.color = COLOR_TEXT_PRIMARY
            tab_pending_button.bgcolor = ft.Colors.with_opacity(0.18, COLOR_WARNING)
            tab_pending_button.color = COLOR_TEXT_PRIMARY
        else:
            tab_all_button.bgcolor = PRIMARY_COLOR
            tab_all_button.color = ft.Colors.WHITE
            tab_pending_button.bgcolor = ft.Colors.TRANSPARENT
            tab_pending_button.color = COLOR_TEXT_PRIMARY

        # Fetch candidate dataset based on active mode
        if is_archived:
            candidates = db_manager.get_archived_candidates(search_term=term)
            candidate_count_text.value = f"Archived Candidates: {len(candidates)}"
            btn_review_send_welcome.visible = False
        elif is_pending_tab:
            # Filter pending welcome candidates by search term if provided
            if term:
                t_low = term.lower()
                candidates = [
                    c for c in pending_welcome_list
                    if t_low in str(c.get("candidate_name") or "").lower()
                    or t_low in str(c.get("mobile") or "").lower()
                    or t_low in str(c.get("applied_designation") or "").lower()
                    or t_low in str(c.get("contact_location") or "").lower()
                    or t_low in str(c.get("email") or "").lower()
                ]
            else:
                candidates = pending_welcome_list
            candidate_count_text.value = f"🎉 Selected Pending Welcome Email: {len(candidates)} (Total Pending: {pending_count})"
            btn_review_send_welcome.visible = True
        else:
            selected_status = status_filter.value if status_filter.value else "All"
            candidates = db_manager.get_all_candidates(search_term=term, status_filter=selected_status)
            candidate_count_text.value = f"Total Candidates: {len(candidates)} | Pending Welcome Emails: {pending_count}"
            btn_review_send_welcome.visible = True

        # Pagination calculations
        total_records = len(candidates)
        pagination_state["total_records"] = total_records
        page_size = pagination_state["page_size"]
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        pagination_state["total_pages"] = total_pages
        if pagination_state["page"] > total_pages:
            pagination_state["page"] = total_pages
        if pagination_state["page"] < 1:
            pagination_state["page"] = 1

        curr_page = pagination_state["page"]
        start_idx = (curr_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        visible_candidates = candidates[start_idx:end_idx] if total_records > 0 else []

        # Cache currently displayed page candidates and all filtered candidates
        current_candidates_cache["list"] = visible_candidates
        current_candidates_cache["all"] = candidates

        # Update select all checkbox state (reflects visible page rows)
        if visible_candidates and all(c["id"] in selected_candidate_ids for c in visible_candidates):
            select_all_checkbox.value = True
        else:
            select_all_checkbox.value = False

        # Update review & send button label with selected count
        sel_count = len(selected_candidate_ids)
        if sel_count > 0:
            btn_review_send_welcome_text.value = f"✉️ Review & Send Welcome Emails ({sel_count})"
        else:
            btn_review_send_welcome_text.value = "✉️ Review & Send Welcome Emails"

        # Update pagination controls
        page_indicator_text.value = f"Page {curr_page} of {total_pages}"
        btn_prev_page.disabled = (curr_page <= 1)
        btn_next_page.disabled = (curr_page >= total_pages)
        if total_records > 0:
            record_range_text.value = f"Showing {start_idx + 1}–{end_idx} of {total_records} candidates"
            pagination_container.visible = True
        else:
            record_range_text.value = "Showing 0 candidates"
            pagination_container.visible = False

        if not candidates:
            empty_msg = (
                "No archived candidates found."
                if is_archived
                else "No candidates found matching the selected filter/search."
            )
            empty_icon = ft.Icons.ARCHIVE_OUTLINED if is_archived else ft.Icons.PEOPLE_OUTLINE
            table_container.content = ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=36,
                content=ft.Column([
                    ft.Icon(empty_icon, size=52, color=COLOR_TEXT_MUTED),
                    ft.Text(empty_msg, size=14, color=COLOR_TEXT_SECONDARY),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            )
        else:
            rows = []
            for c in visible_candidates:
                cand_id = c["id"]
                cand_name = c["candidate_name"] or "N/A"
                cand_mobile = c["mobile"] or "N/A"
                cand_email = c["email"] or "N/A"
                cand_applied = c["applied_designation"] or "N/A"
                cand_salary = c["negotiated_salary"] or "N/A"
                cand_loc = c["contact_location"] or "N/A"
                curr_status = c["status"] or "Applied"
                archived_at = c.get("archived_at") or "N/A"
                welcome_sent = bool(c.get("welcome_email_sent"))
                welcome_sent_at = c.get("welcome_email_sent_at")

                if is_archived:
                    # In archived view: read-only status badge, Restore and Permanent Delete buttons
                    def create_restore_handler(cid=cand_id, cname=cand_name):
                        return lambda e: confirm_restore(cid, cname)

                    restore_btn = ft.IconButton(
                        icon=ft.Icons.UNARCHIVE_OUTLINED,
                        icon_color=COLOR_SUCCESS,
                        tooltip="Restore Candidate",
                        on_click=create_restore_handler(),
                    )

                    def create_perm_delete_handler(cid=cand_id, cname=cand_name):
                        return lambda e: confirm_permanent_delete(cid, cname)

                    delete_perm_btn = ft.IconButton(
                        icon=ft.Icons.DELETE_FOREVER,
                        icon_color=COLOR_ERROR,
                        tooltip="Delete Permanently",
                        on_click=create_perm_delete_handler(),
                    )

                    action_buttons = ft.Row([restore_btn, delete_perm_btn], spacing=4)

                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(cand_name, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(cand_mobile, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(cand_email, size=12, color=COLOR_TEXT_MUTED)),
                            ft.DataCell(ft.Text(cand_applied, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(f"₹{cand_salary}" if cand_salary != "N/A" else "N/A", color=COLOR_SUCCESS)),
                            ft.DataCell(ft.Text(cand_loc, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(status_badge(curr_status)),
                            ft.DataCell(ft.Text(archived_at, size=12, color=COLOR_TEXT_MUTED)),
                            ft.DataCell(action_buttons),
                        ])
                    )
                else:
                    # Active view: selection checkbox, welcome email status badge, status dropdown & action buttons
                    if welcome_sent:
                        email_badge = ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLOR_SUCCESS, size=13),
                                ft.Text("Sent", size=11, weight=ft.FontWeight.W_600, color=COLOR_SUCCESS),
                            ], spacing=4, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.12, COLOR_SUCCESS),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, COLOR_SUCCESS)),
                            tooltip=f"Welcome email sent on {welcome_sent_at}" if welcome_sent_at else "Welcome email sent",
                        )
                    elif curr_status == "Selected":
                        email_badge = ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.MARK_EMAIL_UNREAD, color=COLOR_WARNING, size=13),
                                ft.Text("Pending", size=11, weight=ft.FontWeight.W_600, color=COLOR_WARNING),
                            ], spacing=4, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.12, COLOR_WARNING),
                            border=ft.Border.all(1, ft.Colors.with_opacity(0.3, COLOR_WARNING)),
                            tooltip="Candidate selected - welcome email not sent yet",
                        )
                    else:
                        email_badge = ft.Container(
                            content=ft.Text("—", size=12, color=COLOR_TEXT_MUTED),
                            alignment=ft.Alignment.CENTER,
                        )

                    def make_chk_handler(cid=cand_id):
                        def on_toggle(e):
                            val = bool(e.control.value)
                            if val:
                                selected_candidate_ids.add(cid)
                            else:
                                selected_candidate_ids.discard(cid)
                            update_selection_counts()
                        return on_toggle

                    row_chk = ft.Checkbox(
                        value=(cand_id in selected_candidate_ids),
                        on_change=make_chk_handler(),
                    )

                    status_dd = ft.Dropdown(
                        value=curr_status if curr_status in STATUS_OPTIONS else "Applied",
                        options=[ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
                        width=140,
                        dense=True,
                        border_radius=8,
                        border_color=COLOR_CARD_BORDER,
                        focused_border_color=COLOR_PRIMARY_LIGHT,
                        on_change=make_status_change(cand_id, cand_name),
                    )

                    def create_archive_handler(cid=cand_id, cname=cand_name):
                        return lambda e: confirm_delete(cid, cname)

                    archive_btn = ft.IconButton(
                        icon=ft.Icons.ARCHIVE_OUTLINED,
                        icon_color=COLOR_WARNING,
                        tooltip="Archive Candidate",
                        on_click=create_archive_handler(),
                    )

                    def create_email_handler(cand_item=c):
                        return lambda e: show_welcome_email_review_modal([cand_item])

                    email_action_btn = ft.IconButton(
                        icon=ft.Icons.MARK_EMAIL_READ_OUTLINED,
                        icon_color=COLOR_PRIMARY_LIGHT,
                        tooltip="Review & Send Welcome Email",
                        on_click=create_email_handler(),
                    )

                    def make_whatsapp_handler(cand_item=c):
                        def on_open_whatsapp(e):
                            open_whatsapp_outreach_modal(
                                page=page,
                                candidate=cand_item,
                                initial_message_type="selection",
                                on_complete=load_candidates_data
                            )
                        return on_open_whatsapp

                    whatsapp_btn = ft.IconButton(
                        icon=ft.Icons.CHAT_ROUNDED,
                        icon_color="#25D366",
                        tooltip="Open 1-Click WhatsApp Direct Outreach",
                        on_click=make_whatsapp_handler(),
                    )

                    def make_slip_handler(cand_item=c):
                        def on_show_slip(e):
                            slip_text = candidate_outreach_service.generate_candidate_bio_data_slip(cand_item)
                            dlg = ft.AlertDialog(
                                modal=True,
                                title=ft.Row([
                                    ft.Icon(ft.Icons.BADGE_ROUNDED, color=PRIMARY_COLOR, size=22),
                                    ft.Text(f"Bio-Data Slip: {cand_name}", weight=ft.FontWeight.BOLD, size=15),
                                ], spacing=8),
                                content=ft.Container(
                                    width=500,
                                    content=ft.Column([
                                        ft.TextField(value=slip_text, multiline=True, min_lines=12, max_lines=16, read_only=True, text_size=11),
                                    ], tight=True),
                                ),
                                actions=[
                                    ft.TextButton("Copy Slip", on_click=lambda ev: (page.set_clipboard(slip_text), show_message("Copied candidate bio-data slip!", True))),
                                    ft.ElevatedButton("Close", on_click=lambda ev: page.close(dlg)),
                                ],
                                actions_alignment=ft.MainAxisAlignment.END,
                            )
                            page.open(dlg)
                            page.update()
                        return on_show_slip

                    slip_btn = ft.IconButton(
                        icon=ft.Icons.PRINT_ROUNDED,
                        icon_color=COLOR_PRIMARY_LIGHT,
                        tooltip="View Candidate Bio-Data Slip",
                        on_click=make_slip_handler(),
                    )

                    cand_curr_tag = c.get("tag") or ""
                    TAG_OPTIONS = ["", "Immediate Joiner", "Docs Pending", "On Hold", "Top Priority"]
                    def make_tag_change_handler(cid=cand_id, cname=cand_name):
                        def on_tag_change(e):
                            new_tag = e.control.value
                            db_manager.update_candidate_tag(cid, new_tag)
                            show_message(f"Updated tag for '{cname}' to '{new_tag or 'None'}'", True)
                            refresh_candidates(reset_page=True)
                        return on_tag_change

                    tag_dd = ft.Dropdown(
                        value=cand_curr_tag if cand_curr_tag in TAG_OPTIONS else "",
                        options=[
                            ft.dropdown.Option("", "🏷️ No Tag"),
                            ft.dropdown.Option("Immediate Joiner", "⚡ Immediate"),
                            ft.dropdown.Option("Docs Pending", "📄 Docs Pend"),
                            ft.dropdown.Option("On Hold", "⏸️ On Hold"),
                            ft.dropdown.Option("Top Priority", "⭐ Priority"),
                        ],
                        width=115,
                        dense=True,
                        border_radius=8,
                        border_color=COLOR_CARD_BORDER,
                        on_change=make_tag_change_handler(),
                    )

                    def make_edit_handler(cand_item=c):
                        return lambda e: show_edit_candidate_modal(cand_item)

                    edit_btn = ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_color=COLOR_PRIMARY_LIGHT,
                        tooltip="Edit Candidate Details (Fix Missing Fields)",
                        on_click=make_edit_handler(),
                    )

                    action_buttons = ft.Row([edit_btn, whatsapp_btn, email_action_btn, slip_btn, archive_btn], spacing=2)

                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(row_chk),
                            ft.DataCell(ft.Text(cand_name, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(cand_mobile, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(cand_email, size=12, color=COLOR_TEXT_MUTED)),
                            ft.DataCell(ft.Text(cand_applied, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(f"₹{cand_salary}" if cand_salary != "N/A" else "N/A", color=COLOR_SUCCESS)),
                            ft.DataCell(ft.Text(cand_loc, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(status_dd),
                            ft.DataCell(tag_dd),
                            ft.DataCell(email_badge),
                            ft.DataCell(action_buttons),
                        ])
                    )

            if is_archived:
                columns = [
                    ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Applied Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Salary", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Location", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Archived At", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ]
            else:
                columns = [
                    ft.DataColumn(select_all_checkbox),
                    ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Applied Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Salary", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Location", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Tag", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Welcome Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ]

            try:
                data_table = ft.DataTable(
                    columns=columns,
                    rows=rows,
                    heading_row_color=COLOR_CARD_BG_HOVER,
                    border=ft.Border.all(1, COLOR_CARD_BORDER),
                    border_radius=12,
                    column_spacing=20,
                )
                table_container.content = ft.Row([data_table], scroll=ft.ScrollMode.AUTO)
            except Exception as ex:
                table_container.content = ft.Container(
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=COLOR_ERROR, size=36),
                        ft.Text(f"Could not render candidate table: {ex}", color=COLOR_TEXT_PRIMARY, size=13),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                )

        page.update()

    # ---------------- Upload State & Duplicate Review Logic ----------------
    upload_state = {
        "view_mode": "idle",  # "idle", "processing", "scenario_b_prompt", "scenario_a_review", "no_duplicates", "completed", "error"
        "file_path": None,
        "file_name": None,
        "sheet_names": [],
        "sheet_counts": {},
        "rows_by_sheet": {},
        "active_preview_sheet": "",
        "detected_columns": [],
        "mapped_columns_count": 0,
        "valid_rows": [],
        "new_rows": [],
        "duplicates": [],
        "total_sheet_rows": 0,
        "duplicate_percentage": 0.0,
        "sheet_errors": [],
        "error_message": None,
        "completion_summary": None,
    }

    def cancel_upload():
        upload_state["view_mode"] = "idle"
        render_upload_ui()
        show_message("Upload cancelled. No changes were made to the database.", True)

    def build_upload_preview_panel(
        show_action_bar: bool = True,
        confirm_label: str = None,
        on_confirm = None,
        on_cancel = None,
    ):
        sheet_names = upload_state.get("sheet_names") or []
        sheet_counts = upload_state.get("sheet_counts") or {}
        rows_by_sheet = upload_state.get("rows_by_sheet") or {}
        active_sheet = upload_state.get("active_preview_sheet")
        if not active_sheet and sheet_names:
            active_sheet = sheet_names[0]
            upload_state["active_preview_sheet"] = active_sheet

        total_sheet_rows = upload_state.get("total_sheet_rows", 0)
        duplicates = upload_state.get("duplicates") or []
        new_rows = upload_state.get("new_rows") or []
        mapped_columns_count = upload_state.get("mapped_columns_count", 0)
        file_name = upload_state.get("file_name") or "Spreadsheet"

        # Section A: Sheet Switcher Tabs
        sheet_tabs = []
        for sname in sheet_names:
            scount = sheet_counts.get(sname, len(rows_by_sheet.get(sname, [])))
            is_active = (sname == active_sheet)

            def make_tab_handler(sn=sname):
                def on_tab_click(e):
                    upload_state["active_preview_sheet"] = sn
                    render_upload_ui()
                return on_tab_click

            sheet_tabs.append(
                ft.ElevatedButton(
                    text=f"📄 {sname} ({scount})",
                    bgcolor=PRIMARY_COLOR if is_active else COLOR_CARD_BG_HOVER,
                    color=ft.Colors.WHITE if is_active else COLOR_TEXT_PRIMARY,
                    on_click=make_tab_handler(),
                )
            )

        sheet_switcher_row = ft.Row(
            sheet_tabs,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

        # Section B: KPI Metrics Strip
        def make_kpi_card(title: str, value_text: str, icon_data, accent_color):
            return ft.Container(
                bgcolor=COLOR_CARD_BG,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border_radius=8,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                expand=True,
                content=ft.Row([
                    ft.Icon(icon_data, color=accent_color, size=22),
                    ft.Column([
                        ft.Text(title, size=11, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_500),
                        ft.Text(value_text, size=13, color=COLOR_TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
                    ], spacing=2, tight=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            )

        kpi_strip = ft.Row([
            make_kpi_card("Total Extracted", f"📊 Total: {total_sheet_rows}", ft.Icons.ANALYTICS_OUTLINED, PRIMARY_COLOR),
            make_kpi_card("New Additions", f"✨ New: {len(new_rows)}", ft.Icons.PERSON_ADD_ALT_1_ROUNDED, COLOR_SUCCESS),
            make_kpi_card("Duplicate Records", f"🔄 Duplicates: {len(duplicates)}", ft.Icons.COPY_ALL_ROUNDED, COLOR_WARNING),
            make_kpi_card("Column Health", f"✅ Columns: {mapped_columns_count} Mapped", ft.Icons.VIEW_COLUMN_ROUNDED, COLOR_PRIMARY_LIGHT),
        ], spacing=10)

        # Section C: 10-Row Extracted Candidate Preview DataTable
        target_rows = rows_by_sheet.get(active_sheet) if (active_sheet and active_sheet in rows_by_sheet) else upload_state.get("valid_rows", [])
        preview_rows = target_rows[:10] if target_rows else []

        dt_columns = [
            ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ft.DataColumn(ft.Text("Applied Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ft.DataColumn(ft.Text("Salary", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ft.DataColumn(ft.Text("Location", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
        ]

        table_rows = []
        for r in preview_rows:
            c_name = r.get("candidate_name") or "N/A"
            c_mob = r.get("mobile") or "N/A"
            c_desig = r.get("applied_designation") or "N/A"
            c_sal = r.get("negotiated_salary") or "N/A"
            c_loc = r.get("contact_location") or "N/A"

            table_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(c_name, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(c_mob, color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(c_desig, color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(f"₹{c_sal}" if c_sal != "N/A" else "N/A", color=COLOR_SUCCESS)),
                    ft.DataCell(ft.Text(c_loc, color=COLOR_TEXT_SECONDARY)),
                ])
            )

        if not table_rows:
            table_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text("No candidates found in this sheet", italic=True, color=COLOR_TEXT_MUTED)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                ])
            )

        try:
            preview_dt = ft.DataTable(
                columns=dt_columns,
                rows=table_rows,
                heading_row_color=COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                border_radius=8,
                column_spacing=18,
            )
            table_container = ft.Container(
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                border_radius=8,
                content=ft.Row([preview_dt], scroll=ft.ScrollMode.AUTO),
            )
        except Exception as ex:
            table_container = ft.Container(
                padding=16,
                content=ft.Text(f"Could not render preview table: {ex}", color=COLOR_ERROR),
            )

        panel_items = [
            ft.Row([
                ft.Icon(ft.Icons.PREVIEW_ROUNDED, color=PRIMARY_COLOR, size=20),
                ft.Text(f"Visual File Preview: {file_name}", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                ft.Text(
                    f"Showing first {min(10, len(target_rows))} of {len(target_rows)} in '{active_sheet}'" if target_rows else "",
                    size=11, color=COLOR_TEXT_MUTED
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ]

        if sheet_tabs:
            panel_items.extend([
                ft.Text("Worksheet Tabs:", size=11, weight=ft.FontWeight.W_600, color=COLOR_TEXT_SECONDARY),
                sheet_switcher_row,
            ])

        panel_items.extend([
            kpi_strip,
            table_container,
        ])

        if show_action_bar:
            c_label = confirm_label or f"🚀 Confirm & Ingest {total_sheet_rows} Candidate(s)"
            action_bar = ft.Row([
                primary_button(
                    c_label,
                    icon=ft.Icons.CLOUD_UPLOAD_ROUNDED,
                    bgcolor=COLOR_SUCCESS,
                    on_click=on_confirm or (lambda e: apply_confirmed_changes()),
                ),
                secondary_button(
                    "Cancel Upload",
                    icon=ft.Icons.CLOSE_ROUNDED,
                    on_click=on_cancel or (lambda e: cancel_upload()),
                ),
            ], spacing=10)
            panel_items.append(action_bar)

        return ft.Container(
            bgcolor=COLOR_CARD_BG,
            padding=16,
            border_radius=12,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            content=ft.Column(panel_items, spacing=12),
        )

    def render_upload_ui():
        upload_status_column.controls.clear()
        mode = upload_state.get("view_mode", "idle")

        if mode == "idle":
            page.update()
            return

        if mode == "processing":
            upload_status_column.controls.append(
                ft.Row([
                    ft.ProgressRing(width=18, height=18, stroke_width=2),
                    ft.Text(f"Checking sheet '{upload_state['file_name']}' for duplicates...", size=13, color=COLOR_TEXT_SECONDARY),
                ], spacing=10)
            )
            page.update()
            return

        if mode == "error":
            err_msg = upload_state.get("error_message") or "We couldn't process this file. Please check the file and try again."
            upload_status_column.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.RED_900,
                    padding=16,
                    border_radius=10,
                    border=ft.Border.all(1, ft.Colors.RED_700),
                    content=ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                        ft.Column([
                            ft.Text("File Notice", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=14),
                            ft.Text(err_msg, color=ft.Colors.WHITE, size=13),
                        ], spacing=2, expand=True),
                    ], spacing=12),
                )
            )
            page.update()
            return

        if mode == "completed":
            sum_data = upload_state.get("completion_summary") or {}
            added = sum_data.get("added_count", 0)
            updated = sum_data.get("updated_count", 0)
            kept = sum_data.get("kept_count", 0)
            file_name = upload_state.get("file_name") or "Spreadsheet"
            sheet_counts = upload_state.get("sheet_counts") or {}

            # Sheet breakdown chips
            sheet_chips = []
            for sname, scnt in sheet_counts.items():
                sheet_chips.append(
                    ft.Container(
                        content=ft.Text(f"📄 {sname}: {scnt} candidate(s)", size=12, color=COLOR_TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                        bgcolor=COLOR_CARD_BG,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        border_radius=8,
                        border=ft.Border.all(1, COLOR_CARD_BORDER),
                    )
                )

            def on_review_welcome_emails(e):
                set_quick_filter("pending_welcome")
                upload_state["view_mode"] = "idle"
                render_upload_ui()

            def on_view_in_pipeline(e):
                set_quick_filter("all")
                upload_state["view_mode"] = "idle"
                render_upload_ui()

            btn_welcome = primary_button(
                "✉️ Review Welcome Emails",
                icon=ft.Icons.MARK_EMAIL_READ,
                bgcolor=COLOR_SUCCESS,
                on_click=on_review_welcome_emails,
            )

            btn_pipeline = secondary_button(
                "👥 View In Pipeline",
                icon=ft.Icons.PEOPLE_ALT,
                on_click=on_view_in_pipeline,
            )

            completion_card = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=18,
                border_radius=12,
                border=ft.Border.all(1, COLOR_SUCCESS),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=28),
                        ft.Column([
                            ft.Text(
                                f"🎉 Successfully processed '{file_name}': {added} Added, {updated} Updated, {kept} Kept.",
                                color=COLOR_SUCCESS,
                                weight=ft.FontWeight.BOLD,
                                size=15,
                            ),
                            ft.Text(
                                f"{added} new candidates added. {updated} existing candidates updated. {kept} duplicates left unchanged.",
                                color=COLOR_TEXT_SECONDARY,
                                size=12,
                            ),
                        ], spacing=2, expand=True),
                    ], spacing=12),
                    *( [ft.Row(sheet_chips, wrap=True, spacing=8)] if sheet_chips else [] ),
                    ft.Container(height=4),
                    ft.Row([btn_welcome, btn_pipeline], spacing=10),
                ], spacing=10),
            )

            upload_status_column.controls.append(completion_card)
            page.update()
            return

        # ---------------- Scenario B: Duplicates > 50% ----------------
        if mode == "scenario_b_prompt":
            dup_count = len(upload_state["duplicates"])
            new_count = len(upload_state["new_rows"])
            total_rows = upload_state["total_sheet_rows"]

            def on_bulk_skip(e):
                # HR clicked: "Yes, skip duplicates & add new only"
                # Keep all duplicates unchanged, add new only
                for d in upload_state["duplicates"]:
                    d["action"] = "keep"
                apply_confirmed_changes()

            def on_review_each(e):
                # HR clicked: "No, let me review each one" -> fall back to Scenario A
                upload_state["view_mode"] = "scenario_a_review"
                render_upload_ui()

            def on_cancel(e):
                cancel_upload()

            banner = ft.Container(
                bgcolor=COLOR_WARNING_BG,
                padding=18,
                border_radius=12,
                border=ft.Border.all(1, COLOR_WARNING),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=COLOR_WARNING, size=28),
                        ft.Text(
                            f"⚠️ {dup_count} out of {total_rows} candidates in this file already exist in the system.",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=COLOR_TEXT_PRIMARY,
                        ),
                    ], spacing=10),
                    ft.Text(
                        f"Do you want to skip all {dup_count} duplicates and add only the {new_count} new candidates?",
                        size=13,
                        color=COLOR_TEXT_SECONDARY,
                    ),
                    ft.Container(height=6),
                    ft.Row([
                        primary_button(
                            f"Yes, skip duplicates & add only the {new_count} new candidates",
                            icon=ft.Icons.CHECK_ROUNDED,
                            bgcolor=PRIMARY_COLOR,
                            on_click=on_bulk_skip,
                        ),
                        secondary_button(
                            "No, let me review each one",
                            icon=ft.Icons.RATE_REVIEW_OUTLINED,
                            on_click=on_review_each,
                        ),
                        secondary_button(
                            "Cancel Upload",
                            icon=ft.Icons.CLOSE_ROUNDED,
                            on_click=on_cancel,
                        ),
                    ], spacing=10, wrap=True),
                ], spacing=10),
            )

            preview_panel = build_upload_preview_panel(show_action_bar=False)

            upload_status_column.controls.append(banner)
            upload_status_column.controls.append(preview_panel)
            page.update()
            return

        # ---------------- Scenario A: Duplicates <= 50% (or requested via Scenario B) ----------------
        if mode == "scenario_a_review":
            duplicates = upload_state["duplicates"]
            new_rows = upload_state["new_rows"]
            dup_count = len(duplicates)
            new_count = len(new_rows)
            dup_pct = upload_state.get("duplicate_percentage", 0.0)

            def set_all_duplicates_action(act: str):
                for d in duplicates:
                    d["action"] = act
                render_upload_ui()

            def on_cancel(e):
                cancel_upload()

            # Toolbar with bulk helpers
            toolbar = ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.FACT_CHECK_OUTLINED, color=COLOR_PRIMARY_LIGHT, size=20),
                    ft.Text(
                        f"Reviewing {dup_count} Duplicate Candidates ({dup_pct}% of uploaded file)",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_TEXT_PRIMARY,
                    ),
                ], spacing=8),
                ft.Row([
                    secondary_button(
                        "Keep All Existing",
                        icon=ft.Icons.SHIELD_OUTLINED,
                        on_click=lambda e: set_all_duplicates_action("keep"),
                    ),
                    secondary_button(
                        "Replace All with New",
                        icon=ft.Icons.SWAP_HORIZ_ROUNDED,
                        on_click=lambda e: set_all_duplicates_action("replace"),
                    ),
                ], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)

            # Helper to build one side-by-side card
            def build_duplicate_item_card(item, idx):
                exist = item.get("existing_record") or {}
                uploaded = item.get("uploaded_row") or {}
                name = uploaded.get("candidate_name") or exist.get("candidate_name") or "Candidate"
                curr_action = item.get("action", "keep")
                reason = item.get("match_reason") or "Duplicate detected"

                # Side-by-side comparison data
                exist_salary = exist.get("negotiated_salary") or "N/A"
                exist_desig = exist.get("applied_designation") or "N/A"
                exist_mobile = exist.get("mobile") or "N/A"
                exist_email = exist.get("email") or "N/A"
                exist_loc = exist.get("contact_location") or "N/A"

                new_salary = uploaded.get("negotiated_salary") or "N/A"
                new_desig = uploaded.get("applied_designation") or "N/A"
                new_mobile = uploaded.get("mobile") or "N/A"
                new_email = uploaded.get("email") or "N/A"
                new_loc = uploaded.get("contact_location") or "N/A"

                def make_toggle_handler(chosen_action):
                    def handler(e):
                        item["action"] = chosen_action
                        render_upload_ui()
                    return handler

                if curr_action == "keep":
                    keep_btn = primary_button(
                        "✓ Keep Existing",
                        icon=ft.Icons.CHECK_CIRCLE,
                        bgcolor=COLOR_SUCCESS,
                        on_click=make_toggle_handler("keep"),
                    )
                    replace_btn = secondary_button(
                        "Replace with New",
                        icon=ft.Icons.REFRESH_ROUNDED,
                        on_click=make_toggle_handler("replace"),
                    )
                    status_note = ft.Text(
                        "Decision: Candidate in database will remain completely unchanged.",
                        size=12, color=COLOR_SUCCESS, weight=ft.FontWeight.W_500
                    )
                else:
                    keep_btn = secondary_button(
                        "Keep Existing",
                        icon=ft.Icons.SHIELD_OUTLINED,
                        on_click=make_toggle_handler("keep"),
                    )
                    replace_btn = primary_button(
                        "✓ Replace with New",
                        icon=ft.Icons.SWAP_HORIZ,
                        bgcolor=COLOR_WARNING,
                        on_click=make_toggle_handler("replace"),
                    )
                    status_note = ft.Text(
                        "Decision: Candidate in database will be updated with new uploaded values.",
                        size=12, color=COLOR_WARNING, weight=ft.FontWeight.W_500
                    )

                existing_col = ft.Container(
                    bgcolor=COLOR_CARD_BG,
                    padding=12,
                    border_radius=8,
                    border=ft.Border.all(1, COLOR_CARD_BORDER),
                    content=ft.Column([
                        ft.Text("EXISTING IN SYSTEM", size=11, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_MUTED),
                        ft.Text(f"Salary: ₹{exist_salary}", size=13, color=COLOR_TEXT_PRIMARY),
                        ft.Text(f"Designation: {exist_desig}", size=13, color=COLOR_TEXT_PRIMARY),
                        ft.Text(f"Mobile: {exist_mobile}", size=13, color=COLOR_TEXT_SECONDARY),
                        ft.Text(f"Email: {exist_email}", size=12, color=COLOR_TEXT_MUTED),
                        ft.Text(f"Location: {exist_loc}", size=12, color=COLOR_TEXT_MUTED),
                    ], spacing=4),
                    expand=True,
                )

                new_col = ft.Container(
                    bgcolor=COLOR_CARD_BG,
                    padding=12,
                    border_radius=8,
                    border=ft.Border.all(1, COLOR_CARD_BORDER),
                    content=ft.Column([
                        ft.Text("IN YOUR NEW FILE", size=11, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY_LIGHT),
                        ft.Text(f"Salary: ₹{new_salary}", size=13, weight=ft.FontWeight.BOLD if new_salary != exist_salary else ft.FontWeight.NORMAL, color=COLOR_SUCCESS if new_salary != exist_salary else COLOR_TEXT_PRIMARY),
                        ft.Text(f"Designation: {new_desig}", size=13, weight=ft.FontWeight.BOLD if new_desig != exist_desig else ft.FontWeight.NORMAL, color=COLOR_TEXT_PRIMARY),
                        ft.Text(f"Mobile: {new_mobile}", size=13, color=COLOR_TEXT_SECONDARY),
                        ft.Text(f"Email: {new_email}", size=12, color=COLOR_TEXT_MUTED),
                        ft.Text(f"Location: {new_loc}", size=12, color=COLOR_TEXT_MUTED),
                    ], spacing=4),
                    expand=True,
                )

                return ft.Container(
                    bgcolor=COLOR_CARD_BG_HOVER,
                    padding=14,
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_WARNING if curr_action == "replace" else COLOR_CARD_BORDER),
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{idx+1}. {name}", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                            status_badge(reason),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([existing_col, new_col], spacing=12),
                        ft.Row([
                            keep_btn,
                            replace_btn,
                            status_note,
                        ], spacing=10, alignment=ft.MainAxisAlignment.START, wrap=True),
                    ], spacing=10),
                )

            duplicate_cards = [build_duplicate_item_card(item, idx) for idx, item in enumerate(duplicates)]

            # Genuinely new candidates summary
            new_summary_card = ft.Container(
                bgcolor=COLOR_CARD_BG,
                padding=12,
                border_radius=8,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON_ADD_ALT_1_ROUNDED, color=COLOR_SUCCESS, size=20),
                    ft.Text(
                        f"✨ {new_count} genuinely new candidate(s) will be added automatically to the database.",
                        size=13,
                        color=COLOR_TEXT_PRIMARY,
                        weight=ft.FontWeight.W_500,
                    ),
                ], spacing=10),
            )

            # Skipped rows warning if any
            skipped_warnings = []
            if upload_state.get("sheet_errors"):
                err_list = upload_state["sheet_errors"]
                skipped_warnings.append(
                    ft.Container(
                        bgcolor=COLOR_CARD_BG,
                        padding=10,
                        border_radius=8,
                        border=ft.Border.all(1, COLOR_CARD_BORDER),
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_WARNING, size=18),
                            ft.Text(
                                f"⚠️ {len(err_list)} row(s) skipped in file due to invalid or missing mobile numbers.",
                                size=12,
                                color=COLOR_TEXT_SECONDARY,
                            ),
                        ], spacing=8),
                    )
                )

            # Action Bar
            action_bar = ft.Row([
                primary_button(
                    "Confirm & Apply Changes",
                    icon=ft.Icons.SAVE_OUTLINED,
                    bgcolor=COLOR_SUCCESS,
                    on_click=lambda e: apply_confirmed_changes(),
                ),
                secondary_button(
                    "Cancel Upload",
                    icon=ft.Icons.CANCEL_OUTLINED,
                    on_click=on_cancel,
                ),
            ], spacing=12)

            preview_panel = build_upload_preview_panel(show_action_bar=False)

            review_panel = ft.Container(
                bgcolor=COLOR_CARD_BG,
                padding=16,
                border_radius=12,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                content=ft.Column([
                    toolbar,
                    ft.Divider(height=1, color=COLOR_CARD_BORDER),
                    ft.Column(duplicate_cards, spacing=10),
                    new_summary_card,
                    *skipped_warnings,
                    ft.Divider(height=1, color=COLOR_CARD_BORDER),
                    preview_panel,
                    ft.Divider(height=1, color=COLOR_CARD_BORDER),
                    action_bar,
                ], spacing=14),
            )

            upload_status_column.controls.append(review_panel)
            page.update()
            return

        # ---------------- Case: 0 Duplicates (All new) ----------------
        if mode == "no_duplicates":
            total_sheet_rows = upload_state.get("total_sheet_rows", len(upload_state["new_rows"]))
            new_count = len(upload_state["new_rows"])

            success_banner = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=12,
                border_radius=8,
                border=ft.Border.all(1, COLOR_SUCCESS),
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=20),
                    ft.Text(
                        f"No duplicates found! All {new_count} candidates in this file are genuinely new.",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_SUCCESS,
                    ),
                ], spacing=10),
            )

            preview_panel = build_upload_preview_panel(
                show_action_bar=True,
                confirm_label=f"🚀 Confirm & Ingest {total_sheet_rows} Candidate(s)",
                on_confirm=lambda e: apply_confirmed_changes(),
                on_cancel=lambda e: cancel_upload(),
            )
            preview_panel.content.controls.insert(0, success_banner)

            upload_status_column.controls.append(preview_panel)
            page.update()
            return

    def apply_confirmed_changes():
        file_name = upload_state.get("file_name") or "Spreadsheet"
        dups = upload_state.get("duplicates") or []
        news = upload_state.get("new_rows") or []

        res = sheet_processor.apply_joining_decisions(
            duplicates=dups,
            new_rows=news,
            source_sheet_name=file_name,
        )

        upload_state["view_mode"] = "completed"
        upload_state["completion_summary"] = res
        render_upload_ui()

        summary_msg = f"{res['added_count']} new candidates added. {res['updated_count']} existing candidates updated. {res['kept_count']} duplicates left unchanged."
        show_message(summary_msg, True)
        refresh_candidates(reset_page=True)

    # ---------------- File Upload Processing ----------------
    _is_processing_upload = False

    def handle_spreadsheet_files(files):
        nonlocal _is_processing_upload
        if _is_processing_upload or not files or len(files) == 0:
            return
        _is_processing_upload = True
        try:
            picked = files[0]
            file_path = getattr(picked, "path", None)
            file_name = getattr(picked, "name", None) or (os.path.basename(file_path) if file_path else "unknown")

            upload_state["file_path"] = file_path
            upload_state["file_name"] = file_name
            upload_state["view_mode"] = "processing"
            render_upload_ui()

            # Step 1: Read & validate file without modifying database
            extracted = sheet_processor.extract_candidate_rows_from_sheet(file_path)
            if not extracted.get("success"):
                upload_state["view_mode"] = "error"
                upload_state["error_message"] = extracted.get("error") or "We couldn't process this file. Please check the file and try again."
                render_upload_ui()
                show_message(upload_state["error_message"], False)
                return

            valid_rows = extracted.get("valid_rows", [])
            sheet_errors = extracted.get("errors", [])
            total_sheet_rows = extracted.get("total_sheet_rows", len(valid_rows))
            sheet_names = extracted.get("sheet_names", [])
            sheet_counts = extracted.get("sheet_counts", {})
            rows_by_sheet = extracted.get("rows_by_sheet", {})
            detected_columns = extracted.get("detected_columns", [])
            mapped_columns_count = extracted.get("mapped_columns_count", len(detected_columns))

            if not sheet_names and valid_rows:
                default_sheet = file_name or "Sheet1"
                sheet_names = [default_sheet]
                sheet_counts = {default_sheet: len(valid_rows)}
                rows_by_sheet = {default_sheet: valid_rows}

            # Step 2: Detect duplicates
            dup_res = sheet_processor.detect_duplicates(valid_rows)

            upload_state["file_path"] = file_path
            upload_state["file_name"] = file_name
            upload_state["sheet_names"] = sheet_names
            upload_state["sheet_counts"] = sheet_counts
            upload_state["rows_by_sheet"] = rows_by_sheet
            upload_state["active_preview_sheet"] = sheet_names[0] if sheet_names else ""
            upload_state["detected_columns"] = detected_columns
            upload_state["mapped_columns_count"] = mapped_columns_count
            upload_state["total_sheet_rows"] = total_sheet_rows
            upload_state["valid_rows"] = valid_rows
            upload_state["duplicates"] = dup_res.get("duplicates", [])
            upload_state["new_rows"] = dup_res.get("new_rows", [])
            upload_state["duplicate_percentage"] = dup_res.get("duplicate_percentage", 0.0)
            upload_state["sheet_errors"] = sheet_errors

            dup_count = len(upload_state["duplicates"])
            pct = upload_state["duplicate_percentage"]

            if dup_count == 0:
                upload_state["view_mode"] = "no_duplicates"
            elif pct > 50.0:
                upload_state["view_mode"] = "scenario_b_prompt"
            else:
                upload_state["view_mode"] = "scenario_a_review"

            render_upload_ui()
        finally:
            _is_processing_upload = False

    def on_file_result(e):
        files = getattr(e, "files", e) if not isinstance(e, list) else e
        handle_spreadsheet_files(files)

    # FilePicker setup
    file_picker = ft.FilePicker(on_result=on_file_result)
    register_overlay_control(page, file_picker)
    page.update()

    async def pick_sheet_clicked(e):
        try:
            files = await file_picker.pick_files(
                dialog_title="Select Candidate Spreadsheet (.xlsx or .csv)",
                allowed_extensions=["xlsx", "xls", "csv"],
                allow_multiple=False,
            )
            if files:
                handle_spreadsheet_files(files)
        except Exception as ex:
            print("Error picking spreadsheet:", ex)
            show_message("We couldn't open the file selector. Please try again.", False)

    # Initial load of candidates
    refresh_candidates()

    # ---------------- Layout ----------------
    return ft.Column([
        # Header
        page_header(
            icon=ft.Icons.BADGE_OUTLINED,
            title="📋 Joining Process",
            subtitle="Upload candidate sheets, manage candidate pipelines, and track onboarding status",
        ),

        ft.Container(height=10),

        # Upload Card
        modern_card(ft.Column([
            section_title(ft.Icons.UPLOAD_FILE, "Upload Candidate Spreadsheet"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(
                "Upload a .xlsx or .csv sheet containing candidates. The sheet must include required columns: "
                "Candidate Name, Mobile, Email, Applied Designation, Negotiated Salary, etc.",
                size=12, color=COLOR_TEXT_SECONDARY
            ),
            ft.Row([
                primary_button(
                    "Upload Sheet (.xlsx / .csv)",
                    icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                    on_click=pick_sheet_clicked,
                ),
            ]),
            upload_status_column,
        ], spacing=12)),

        ft.Container(height=14),

        # Search & Filter Card
        modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.FILTER_LIST, "Candidate Pipeline"),
                ft.Row([
                    btn_review_send_welcome,
                    secondary_button(
                        "Export to Excel",
                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                        on_click=export_candidates_clicked,
                    ),
                ], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([
                tab_all_button,
                tab_pending_button,
                ft.Container(expand=True),
            ], spacing=10),
            ft.Row([
                search_field,
                status_filter,
                show_archived_switch,
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Refresh List",
                    icon_color=COLOR_PRIMARY_LIGHT,
                    on_click=lambda e: refresh_candidates(reset_page=False),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            candidate_count_text,
            table_container,
            pagination_container,
        ], spacing=12)),

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
