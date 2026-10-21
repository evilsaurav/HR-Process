"""
Page: document_generation_page.py
Purpose: Interactive HR interface for generating, previewing, and finalizing:
- Offer Letters, Extension Letters, Increment Letters, Termination Letters
- Experience & Salary Certificates
Supports pre-filled editable candidate details, dynamic event fields,
template fallbacks, and audit history export.
"""

import os
import subprocess
import traceback
import flet as ft

from config import PRIMARY_COLOR, DESKTOP_APP_DIR
from database import db_manager
from services import document_generation_service
from services import excel_export_service
from services import email_service
from utils.email_preview_modal import open_email_preview_modal
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
    COLOR_PRIMARY_LIGHT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ERROR,
)


DOC_TYPE_OPTIONS = [
    ("Offer Letter", "offer"),
    ("Appointment Letter", "appointment"),
    ("Increment Letter", "increment"),
    ("Extension Letter", "extension"),
    ("Internship Letter", "internship"),
    ("Consultant Agreement", "consultant"),
    ("Experience Certificate", "experience"),
    ("Salary Certificate", "salary"),
    ("Termination Letter", "termination"),
]


def open_file_safe(file_path: str):
    """Safely opens a file or directory using the OS default application."""
    if not file_path or not os.path.exists(file_path):
        return False
    try:
        if hasattr(os, "startfile"):
            os.startfile(file_path)
            return True
        else:
            subprocess.Popen(["xdg-open", file_path])
            return True
    except Exception as ex:
        print(f"Error opening file {file_path}: {ex}")
        return False


def document_generation_view(page: ft.Page):
    db_manager.init_db()

    # State
    state = {
        "selected_candidate_id": None,
        "selected_candidate": None,
        "selected_doc_type": "offer",
        "manual_override_desig": None,
        "preview_generated": False,
        "last_preview_path": None,
        "last_final_path": None,
        # Batch Document Generation state
        "selected_ids": set(),
        "batch_doc_type": "offer",
        "batch_preview_results": [],
    }

    # Snackbar helper
    def show_message(text: str, is_success: bool = True):
        page.open(
            ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED,
            )
        )
        page.update()

    # ---------------- UI Controls ----------------

    # Candidate search and selection
    candidate_dropdown = ft.Dropdown(
        label="Select Candidate",
        expand=True,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    search_text = ft.TextField(
        label="Search candidate (Name or Mobile)...",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    candidate_info_container = ft.Container(visible=False)

    # Document type dropdown
    doc_type_dropdown = ft.Dropdown(
        label="Document Type",
        value="offer",
        options=[ft.dropdown.Option(val, text) for text, val in DOC_TYPE_OPTIONS],
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    # Base candidate editable fields
    father_name_field = ft.TextField(
        label="Father's Name", expand=True, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    gender_dropdown = ft.Dropdown(
        label="Gender",
        options=[ft.dropdown.Option("Male"), ft.dropdown.Option("Female"), ft.dropdown.Option("Other")],
        width=150,
        border_radius=8,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )
    address_field = ft.TextField(
        label="Full Address (comma separated)", multiline=True, min_lines=2, max_lines=3,
        expand=True, border_radius=8, border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    department_field = ft.TextField(
        label="Department", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    date_joined_field = ft.TextField(
        label="Date Joined (YYYY-MM-DD)", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    salary_field = ft.TextField(
        label="Negotiated Monthly Salary (₹)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    employee_number_field = ft.TextField(
        label="Employee Number", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )

    # Dynamic extra fields
    ext_start_date_field = ft.TextField(
        label="Extension Start Date (YYYY-MM-DD)", width=250, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_date_field = ft.TextField(
        label="Termination Date (YYYY-MM-DD)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_notice_field = ft.TextField(
        label="Notice Period (e.g. 30 Days)", width=200, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    term_reason_field = ft.TextField(
        label="Termination Reason", multiline=True, min_lines=2, expand=True, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_effective_field = ft.TextField(
        label="Effective From Date (YYYY-MM-DD)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_revised_salary_field = ft.TextField(
        label="Revised Monthly Salary (₹)", width=220, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    inc_offer_doc_date_field = ft.TextField(
        label="Offer Letter Document Date (YYYY-MM-DD)", width=250, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )
    cert_exit_date_field = ft.TextField(
        label="Exit / Relieving Date (leave blank if currently working)", width=320, border_radius=8,
        border_color=COLOR_CARD_BORDER, focused_border_color=COLOR_PRIMARY_LIGHT
    )

    dynamic_fields_container = ft.Container()
    template_override_container = ft.Container(visible=False)
    result_container = ft.Container()
    history_container = ft.Container()
    email_history_container = ft.Container()

    # ---------------- Helpers & Logic ----------------

    def load_candidates_into_dropdown(filter_text=""):
        candidates = db_manager.get_all_candidates(search_term=filter_text)
        options = []
        for c in candidates:
            c_name = c.get("candidate_name") or "Unnamed"
            c_mob = c.get("mobile") or "No Mobile"
            c_desig = c.get("applied_designation") or "No Role"
            options.append(ft.dropdown.Option(str(c["id"]), f"{c_name} ({c_mob}) - {c_desig}"))
        candidate_dropdown.options = options
        if not options:
            candidate_dropdown.value = None

    def refresh_candidate_info_card(cand):
        if not cand:
            candidate_info_container.visible = False
            candidate_info_container.content = None
            return

        candidate_info_container.visible = True
        c_name = cand.get("candidate_name") or "-"
        c_mob = cand.get("mobile") or "-"
        c_desig = cand.get("applied_designation") or "-"
        c_status = cand.get("status") or "-"
        c_emp = cand.get("employee_number") or "Not Assigned"

        candidate_info_container.content = ft.Container(
            bgcolor=COLOR_CARD_BG_HOVER,
            padding=14,
            border_radius=10,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.PERSON_PIN_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                    padding=8,
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.15, COLOR_PRIMARY_LIGHT),
                ),
                ft.Column([
                    ft.Text(f"{c_name}  •  {c_desig}", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXT_PRIMARY),
                    ft.Text(f"Mobile: {c_mob}  |  Status: {c_status}  |  Employee ID: {c_emp}", size=12, color=COLOR_TEXT_SECONDARY),
                ], spacing=2, expand=True),
            ], spacing=12),
        )

    def populate_form_from_candidate(cand):
        if not cand:
            return
        father_name_field.value = cand.get("father_name") or ""
        gender_dropdown.value = cand.get("gender") if cand.get("gender") in ["Male", "Female", "Other"] else "Male"
        address_field.value = cand.get("full_address") or ""
        department_field.value = cand.get("department") or ""
        date_joined_field.value = cand.get("date_joined") or ""
        salary_field.value = str(cand.get("negotiated_salary") or "")
        employee_number_field.value = cand.get("employee_number") or ""
        cert_exit_date_field.value = cand.get("relieving_date") or ""

    def save_candidate_edits():
        """Saves edited candidate details back to SQLite."""
        cid = state["selected_candidate_id"]
        if not cid:
            return
        db_manager.update_candidate_extra_details(
            candidate_id=cid,
            father_name=father_name_field.value.strip(),
            full_address=address_field.value.strip(),
            gender=gender_dropdown.value or "Male",
            department=department_field.value.strip(),
            date_joined=date_joined_field.value.strip(),
            employee_number=employee_number_field.value.strip(),
        )
        # Refresh state candidate
        state["selected_candidate"] = db_manager.get_candidate_by_id(cid)

    def collect_extra_fields():
        doc_type = state["selected_doc_type"]
        extra = {}
        if doc_type == "extension":
            extra["extension_start_date"] = ext_start_date_field.value.strip()
        elif doc_type == "increment":
            extra["effective_from"] = inc_effective_field.value.strip()
            extra["revised_pay_grade"] = inc_revised_salary_field.value.strip()
            extra["offer_letter_document_date"] = inc_offer_doc_date_field.value.strip()
        elif doc_type == "termination":
            extra["termination_date"] = term_date_field.value.strip()
            extra["notice_period"] = term_notice_field.value.strip()
            extra["reason"] = term_reason_field.value.strip()
        elif doc_type in ["experience", "salary"]:
            exit_val = cert_exit_date_field.value.strip()
            extra["exit_date"] = exit_val if exit_val else None
        return extra

    def update_dynamic_fields():
        doc_type = state["selected_doc_type"]
        if doc_type == "offer":
            dynamic_fields_container.content = ft.Text(
                "ℹ️ Offer letters use base candidate details and negotiated monthly salary.",
                size=12, color=COLOR_TEXT_SECONDARY, italic=True
            )
        elif doc_type == "extension":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Extension Period Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([ext_start_date_field], spacing=12),
            ], spacing=6)
        elif doc_type == "increment":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Increment Event Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([inc_effective_field, inc_revised_salary_field, inc_offer_doc_date_field], spacing=12),
            ], spacing=6)
        elif doc_type == "termination":
            dynamic_fields_container.content = ft.Column([
                ft.Text("Termination Event Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([term_date_field, term_notice_field], spacing=12),
                term_reason_field,
            ], spacing=6)
        elif doc_type in ["experience", "salary"]:
            cert_name = "Experience Certificate" if doc_type == "experience" else "Salary Certificate"
            dynamic_fields_container.content = ft.Column([
                ft.Text(f"{cert_name} Details", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXT_PRIMARY),
                ft.Row([cert_exit_date_field], spacing=12),
                ft.Text(
                    "💡 If left blank, the certificate will state that the employee 'is currently working' up to Till Date.",
                    size=12, color=COLOR_TEXT_SECONDARY, italic=True
                ),
            ], spacing=6)
        page.update()

    def check_template_availability():
        cid = state["selected_candidate_id"]
        doc_type = state["selected_doc_type"]
        if not cid:
            template_override_container.visible = False
            return

        cand = state["selected_candidate"]
        res = document_generation_service.resolve_template(
            doc_type, cand, state["manual_override_desig"]
        )

        if not res.get("found"):
            avail = res.get("available_designations", [])
            override_dropdown = ft.Dropdown(
                label="Choose Matching Template",
                options=[ft.dropdown.Option(d) for d in avail],
                width=350,
                border_radius=8,
                border_color=COLOR_CARD_BORDER,
                focused_border_color=COLOR_PRIMARY_LIGHT,
                on_select=lambda e: set_manual_override(getattr(e.control, "value", None) or getattr(e, "data", None)),
            )
            cand_desig = cand.get("applied_designation") or "Unspecified"
            template_override_container.visible = True
            template_override_container.content = ft.Container(
                bgcolor=ft.Colors.ORANGE_900,
                padding=12,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.ORANGE_700),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_200, size=20),
                        ft.Text(
                            f"We couldn't find an exact template match for '{cand_desig}'. "
                            "Please choose one manually below:",
                            color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_500
                        ),
                    ], spacing=8),
                    override_dropdown,
                ], spacing=8),
            )
        else:
            template_override_container.visible = False
            template_override_container.content = None

    def set_manual_override(desig):
        state["manual_override_desig"] = desig
        page.update()

    def refresh_history_table():
        cid = state["selected_candidate_id"]
        if not cid:
            history_container.visible = False
            return

        history = db_manager.get_generation_history(cid)
        if not history:
            history_container.visible = True
            history_container.content = modern_card(ft.Column([
                section_title(ft.Icons.HISTORY_ROUNDED, "Recent Documents for this Candidate"),
                ft.Divider(height=10, color=COLOR_CARD_BORDER),
                ft.Text("No documents have been generated for this candidate yet.", size=13, color=COLOR_TEXT_SECONDARY),
            ], spacing=8))
            page.update()
            return

        rows = []
        for h in history:
            doc_type_cap = (h.get("document_type") or "").replace("_", " ").title()
            ref_num = h.get("reference_number") or "-"
            gen_date = h.get("generated_date") or "-"
            fpath = h.get("file_path") or ""

            def create_open_handler(fp=fpath):
                return lambda e: open_file_safe(fp)

            def create_email_handler(doc_t=h.get("document_type"), r_num=ref_num, fp=fpath):
                return lambda e: open_email_preview_flow(state["selected_candidate"], doc_t, r_num, fp)

            action_btn = ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                icon_color=COLOR_PRIMARY_LIGHT,
                tooltip="Open Generated Document",
                on_click=create_open_handler(),
            )
            email_btn = ft.IconButton(
                icon=ft.Icons.EMAIL_OUTLINED,
                icon_color=COLOR_SUCCESS,
                tooltip="Send Document via Email",
                on_click=create_email_handler(),
            )

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(doc_type_cap, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)),
                ft.DataCell(ft.Text(ref_num, color=COLOR_SUCCESS, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(gen_date, size=12, color=COLOR_TEXT_MUTED)),
                ft.DataCell(ft.Row([action_btn, email_btn], spacing=4)),
            ]))

        history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Reference Number", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Generated Date", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=24,
        )

        def export_history_clicked(e):
            out_path = os.path.join(DESKTOP_APP_DIR, "output", f"candidate_{cid}_documents_history.xlsx")
            export_data = [
                {
                    "Document Type": r.get("document_type", ""),
                    "Reference Number": r.get("reference_number", ""),
                    "Generated Date": r.get("generated_date", ""),
                    "File Path": r.get("file_path", ""),
                }
                for r in history
            ]
            excel_export_service.export_to_excel(export_data, out_path, sheet_name="Documents")
            show_message(f"Document history exported to {os.path.basename(out_path)}!", True)

        history_container.visible = True
        history_container.content = modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.HISTORY_ROUNDED, "Recent Documents for this Candidate"),
                ft.Container(expand=True),
                secondary_button(
                    "Export History to Excel",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=export_history_clicked,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([history_table], scroll=ft.ScrollMode.AUTO),
        ], spacing=10))
        page.update()

    def refresh_email_logs_for_candidate():
        cid = state["selected_candidate_id"]
        if not cid:
            email_history_container.visible = False
            return

        logs = db_manager.get_email_logs(candidate_id=cid)
        if not logs:
            email_history_container.visible = False
            page.update()
            return

        def export_cand_email_history(e):
            out_path = os.path.join(DESKTOP_APP_DIR, "output", f"candidate_{cid}_email_log.xlsx")
            export_data = [
                {
                    "Date & Time": r.get("timestamp", ""),
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
            excel_export_service.export_to_excel(export_data, out_path, sheet_name="Email Log")
            show_message(f"Candidate email log exported to {os.path.basename(out_path)}!", True)

        table_rows = []
        for r in logs:
            is_ok = r.get("status") == "Success"
            badge = status_badge("Success") if is_ok else status_badge("Failed")
            table_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(r.get("timestamp", "-"), size=12, color=COLOR_TEXT_MUTED)),
                ft.DataCell(ft.Text(r.get("recipient_email", "-"), color=COLOR_TEXT_PRIMARY)),
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

        email_history_container.visible = True
        email_history_container.content = modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.MARK_EMAIL_READ_ROUNDED, "Email Dispatch History for this Candidate"),
                ft.Container(expand=True),
                secondary_button("Export Email Log to Excel", icon=ft.Icons.DOWNLOAD_ROUNDED, on_click=export_cand_email_history),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([dt], scroll=ft.ScrollMode.AUTO),
        ], spacing=10))
        page.update()

    # ---------------- Event Handlers ----------------

    def on_search_change(e):
        load_candidates_into_dropdown(filter_text=e.control.value)
        page.update()

    def on_candidate_selected(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if not val:
            state["selected_candidate_id"] = None
            state["selected_candidate"] = None
            refresh_candidate_info_card(None)
            page.update()
            return

        try:
            cid = int(val)
        except (ValueError, TypeError):
            return

        state["selected_candidate_id"] = cid
        cand = db_manager.get_candidate_by_id(cid)
        state["selected_candidate"] = cand
        state["manual_override_desig"] = None
        state["preview_generated"] = False
        result_container.content = None

        refresh_candidate_info_card(cand)
        populate_form_from_candidate(cand)
        check_template_availability()
        refresh_history_table()
        refresh_email_logs_for_candidate()
        page.update()

    def on_doc_type_change(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if val:
            state["selected_doc_type"] = val
        state["manual_override_desig"] = None
        state["preview_generated"] = False
        result_container.content = None
        update_dynamic_fields()
        check_template_availability()
        page.update()

    # ---------------- Email Dispatch Flow ----------------
    def open_email_preview_flow(candidate: dict, doc_type: str, ref_num: str, file_path: str):
        if not candidate:
            show_message("Please select a candidate first.", False)
            return

        open_email_preview_modal(
            page=page,
            candidate=candidate,
            document_type=doc_type,
            attachment_path=file_path,
            on_dispatch_complete=refresh_email_logs_for_candidate,
        )

    def on_preview_clicked(e):
        cid = state["selected_candidate_id"]
        if not cid:
            show_message("Please select a candidate first.", False)
            return

        save_candidate_edits()
        extra = collect_extra_fields()

        res = document_generation_service.generate_preview_document(
            candidate_id=cid,
            document_type=state["selected_doc_type"],
            extra_fields=extra,
            manual_designation_override=state["manual_override_desig"]
        )

        if not res.get("success"):
            if res.get("needs_template_selection"):
                check_template_availability()
            err = res.get("error", "Failed to generate preview.")
            result_container.content = ft.Container(
                bgcolor=ft.Colors.RED_900,
                padding=14,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.RED_700),
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                    ft.Text(err, color=ft.Colors.WHITE, size=13),
                ], spacing=10),
            )
            show_message(err, False)
        else:
            state["preview_generated"] = True
            state["last_preview_path"] = res["preview_file_path"]
            preview_ref = res.get("previewed_reference_number", "-")

            def open_preview(e):
                open_file_safe(state["last_preview_path"])

            result_container.content = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_PRIMARY_LIGHT),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.VISIBILITY_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=24),
                        ft.Column([
                            ft.Text("Preview Ready!", size=15, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                            ft.Text(f"Estimated Reference Number (not yet assigned): {preview_ref}", size=12, color=COLOR_TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        primary_button(
                            "Open Preview in Word",
                            icon=ft.Icons.DESCRIPTION_ROUNDED,
                            on_click=open_preview,
                        ),
                    ], spacing=12),
                    ft.Text(
                        "ℹ️ Preview generated successfully. No reference number was consumed from your sequence. "
                        "Review the document in Word, then click 'Confirm & Generate Final Document' below.",
                        size=12, color=COLOR_TEXT_SECONDARY, italic=True
                    ),
                ], spacing=8),
            )
            show_message("Preview ready! Check the Word document.", True)

        page.update()

    def on_finalize_clicked(e):
        cid = state["selected_candidate_id"]
        if not cid:
            show_message("Please select a candidate first.", False)
            return

        save_candidate_edits()
        extra = collect_extra_fields()

        res = document_generation_service.finalize_document(
            candidate_id=cid,
            document_type=state["selected_doc_type"],
            extra_fields=extra,
            manual_designation_override=state["manual_override_desig"]
        )

        if not res.get("success"):
            err = res.get("error", "Failed to generate final document.")
            result_container.content = ft.Container(
                bgcolor=ft.Colors.RED_900,
                padding=14,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.RED_700),
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                    ft.Text(err, color=ft.Colors.WHITE, size=13),
                ], spacing=10),
            )
            show_message(err, False)
        else:
            state["last_final_path"] = res["file_path"]
            final_ref = res.get("reference_number", "-")
            file_name = os.path.basename(res["file_path"])

            def open_doc(e):
                open_file_safe(state["last_final_path"])

            def open_folder(e):
                open_file_safe(os.path.dirname(state["last_final_path"]))

            result_container.content = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUCCESS),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=28),
                        ft.Column([
                            ft.Text("Final Document Generated Successfully! 🎉", size=16, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS),
                            ft.Text(f"Assigned Reference Number: {final_ref}", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                            ft.Text(f"Saved File: {file_name}", size=12, color=COLOR_TEXT_SECONDARY),
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.ElevatedButton(
                                "Open Document",
                                icon=ft.Icons.DESCRIPTION_ROUNDED,
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                on_click=open_doc,
                            ),
                            secondary_button(
                                "Open Folder",
                                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                                on_click=open_folder,
                            ),
                            ft.ElevatedButton(
                                "Send via Email",
                                icon=ft.Icons.EMAIL_ROUNDED,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                on_click=lambda e: open_email_preview_flow(
                                    state["selected_candidate"],
                                    state["selected_doc_type"],
                                    final_ref,
                                    state["last_final_path"]
                                ),
                            ),
                        ], spacing=8),
                    ], spacing=12),
                ], spacing=8),
            )
            show_message(f"Document finalized with Reference #{final_ref}!", True)
            refresh_history_table()
            refresh_email_logs_for_candidate()

        page.update()

    # =========================================================================
    # PHASE F1: BATCH DOCUMENT GENERATION CONTROLS & LOGIC
    # =========================================================================

    batch_count_text = ft.Text("0 candidates selected", weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY, size=13)
    batch_count_label = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        bgcolor=COLOR_CARD_BG_HOVER,
        border_radius=8,
        border=ft.Border.all(1, COLOR_CARD_BORDER),
        content=ft.Row([
            ft.Icon(ft.Icons.PEOPLE_ALT_ROUNDED, color=COLOR_PRIMARY_LIGHT, size=18),
            batch_count_text,
        ], spacing=6, tight=True),
    )

    batch_doc_type_dropdown = ft.Dropdown(
        label="Batch Document Type",
        value="offer",
        options=[ft.dropdown.Option(val, text) for text, val in DOC_TYPE_OPTIONS],
        width=250,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    batch_preview_btn = ft.ElevatedButton(
        "Generate Preview for Selected",
        icon=ft.Icons.PREVIEW_ROUNDED,
        bgcolor=ft.Colors.BLUE_GREY_700,
        color=ft.Colors.WHITE,
        disabled=True,
    )

    batch_search_input = ft.TextField(
        label="Search candidate name, mobile, designation...",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
    )

    batch_select_all_checkbox = ft.Checkbox(
        label="Select All",
    )

    batch_table_container = ft.Container()
    batch_results_container = ft.Container(visible=False)

    def update_batch_toolbar_state():
        n = len(state["selected_ids"])
        batch_count_text.value = f"{n} candidate{'s' if n != 1 else ''} selected"
        batch_preview_btn.disabled = (n == 0)
        batch_preview_btn.text = f"Generate Preview for Selected ({n})" if n > 0 else "Generate Preview for Selected"

    def make_row_toggle(cand_id):
        def toggle_handler(e):
            val = getattr(e.control, "value", False)
            if val:
                state["selected_ids"].add(cand_id)
            else:
                state["selected_ids"].discard(cand_id)
            update_batch_toolbar_state()
            all_cands = db_manager.get_all_candidates()
            filter_text = getattr(batch_search_input, "value", "")
            if filter_text:
                ft_low = filter_text.strip().lower()
                all_cands = [
                    c for c in all_cands
                    if ft_low in str(c.get("candidate_name") or "").lower()
                    or ft_low in str(c.get("mobile") or "").lower()
                    or ft_low in str(c.get("applied_designation") or "").lower()
                    or ft_low in str(c.get("email") or "").lower()
                ]
            if all_cands and len(state["selected_ids"]) > 0 and all(c["id"] in state["selected_ids"] for c in all_cands):
                batch_select_all_checkbox.value = True
            else:
                batch_select_all_checkbox.value = False
            page.update()
        return toggle_handler

    def on_select_all_toggle(e):
        val = getattr(e.control, "value", False)
        all_cands = db_manager.get_all_candidates()
        filter_text = getattr(batch_search_input, "value", "")
        if filter_text:
            ft_low = filter_text.strip().lower()
            all_cands = [
                c for c in all_cands
                if ft_low in str(c.get("candidate_name") or "").lower()
                or ft_low in str(c.get("mobile") or "").lower()
                or ft_low in str(c.get("applied_designation") or "").lower()
                or ft_low in str(c.get("email") or "").lower()
            ]
        if val:
            for c in all_cands:
                state["selected_ids"].add(c["id"])
        else:
            for c in all_cands:
                state["selected_ids"].discard(c["id"])
        update_batch_toolbar_state()
        refresh_batch_candidates_table(filter_text=filter_text)
        page.update()

    def refresh_batch_candidates_table(filter_text=""):
        cands = db_manager.get_all_candidates()
        if filter_text:
            ft_low = filter_text.strip().lower()
            cands = [
                c for c in cands
                if ft_low in str(c.get("candidate_name") or "").lower()
                or ft_low in str(c.get("mobile") or "").lower()
                or ft_low in str(c.get("applied_designation") or "").lower()
                or ft_low in str(c.get("email") or "").lower()
            ]

        rows = []
        for cand in cands:
            cid = cand["id"]
            cname = cand.get("candidate_name") or f"Candidate #{cid}"
            cmobile = cand.get("mobile") or "-"
            cemail = cand.get("email") or "-"
            cdesig = cand.get("applied_designation") or "-"
            cstatus = cand.get("status") or "Applied"

            row_chk = ft.Checkbox(
                value=(cid in state["selected_ids"]),
                on_change=make_row_toggle(cid),
            )

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(row_chk),
                    ft.DataCell(ft.Text(cname, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(cmobile, color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(cemail, size=12, color=COLOR_TEXT_MUTED)),
                    ft.DataCell(ft.Text(cdesig, color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(cstatus, size=12, color=COLOR_SUCCESS if cstatus == "Joined" else COLOR_TEXT_MUTED)),
                ])
            )

        if not rows:
            batch_table_container.content = ft.Container(
                padding=20,
                content=ft.Text("No candidates found in database matching search criteria.", color=COLOR_TEXT_MUTED, italic=True),
            )
            return

        if cands and len(state["selected_ids"]) > 0 and all(c["id"] in state["selected_ids"] for c in cands):
            batch_select_all_checkbox.value = True
        else:
            batch_select_all_checkbox.value = False

        batch_table = ft.DataTable(
            columns=[
                ft.DataColumn(batch_select_all_checkbox),
                ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=18,
        )

        batch_table_container.content = ft.Row([batch_table], scroll=ft.ScrollMode.AUTO)

    def make_view_preview_handler(path):
        def on_view_clicked(e):
            if path and os.path.exists(path):
                open_file_safe(path)
            else:
                show_message("Document file is not accessible or does not exist.", False)
        return on_view_clicked

    def make_approve_handler(row_item):
        def on_approve_clicked(e):
            cid = row_item["candidate_id"]
            doc_type = row_item["doc_type"]
            cname = row_item["candidate_name"]

            try:
                res = document_generation_service.finalize_document(
                    candidate_id=cid,
                    document_type=doc_type,
                )
                if res.get("success"):
                    row_item["finalized"] = True
                    row_item["reference_number"] = res.get("reference_number")
                    row_item["final_file_path"] = res.get("file_path")
                    show_message(f"Document finalized for {cname}! Assigned Reference #{row_item['reference_number']}.", True)
                else:
                    err = res.get("error", "We couldn't finalize the document. Please try again.")
                    show_message(err, False)
            except Exception as ex:
                show_message(f"We couldn't finalize the document for {cname}. Please try again.", False)

            refresh_batch_results_table()
            if state.get("selected_candidate_id") == cid:
                refresh_history_table()
            page.update()
        return on_approve_clicked

    def refresh_batch_results_table():
        results = state["batch_preview_results"]
        if not results:
            batch_results_container.visible = False
            return

        rows = []
        for item in results:
            cid = item["candidate_id"]
            cname = item.get("candidate_name") or f"Candidate #{cid}"
            dtype = item.get("doc_type") or "offer"
            dtype_display = dtype.replace("_", " ").title()
            is_success = item.get("success", False)
            is_finalized = item.get("finalized", False)
            err = item.get("error")
            ref_num = item.get("reference_number")

            if is_finalized:
                status_ctrl = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLOR_SUCCESS, size=18),
                    ft.Text(f"✅ Finalized (#{ref_num})", color=COLOR_SUCCESS, weight=ft.FontWeight.BOLD, size=12),
                ], spacing=6)
            elif is_success:
                status_ctrl = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=COLOR_SUCCESS, size=18),
                    ft.Text("✅ Ready", color=COLOR_SUCCESS, weight=ft.FontWeight.W_500, size=12),
                ], spacing=6)
            else:
                status_ctrl = ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=18),
                    ft.Text(f"❌ {err or 'Error'}", color=ft.Colors.RED_400, size=12),
                ], spacing=6)

            preview_path = item.get("preview_file_path")
            view_btn = ft.OutlinedButton(
                "View/Edit Preview",
                icon=ft.Icons.DESCRIPTION_OUTLINED,
                disabled=(not is_success or not preview_path),
                on_click=make_view_preview_handler(preview_path),
            )

            if is_finalized:
                final_path = item.get("final_file_path")
                approve_btn = ft.ElevatedButton(
                    "Open Final",
                    icon=ft.Icons.TASK_ALT_ROUNDED,
                    bgcolor=COLOR_SUCCESS,
                    color=ft.Colors.WHITE,
                    on_click=make_view_preview_handler(final_path),
                )
            else:
                approve_btn = ft.ElevatedButton(
                    "Approve & Finalize",
                    icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    disabled=(not is_success),
                    on_click=make_approve_handler(item),
                )

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(cname, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(dtype_display, color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(status_ctrl),
                    ft.DataCell(ft.Row([view_btn, approve_btn], spacing=8)),
                ])
            )

        res_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Document Type", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
            ],
            rows=rows,
            heading_row_color=COLOR_CARD_BG_HOVER,
            border=ft.Border.all(1, COLOR_CARD_BORDER),
            border_radius=10,
            column_spacing=20,
        )

        batch_results_container.visible = True
        batch_results_container.content = modern_card(ft.Column([
            ft.Row([
                section_title(ft.Icons.FACT_CHECK_ROUNDED, "Batch Document Results & Approval"),
                ft.Container(expand=True),
                status_badge(f"{len(results)} in batch"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(
                "Review previews in Microsoft Word by clicking 'View/Edit Preview'. "
                "Click 'Approve & Finalize' on any candidate to assign an official reference number and issue the final document.",
                size=12, color=COLOR_TEXT_SECONDARY
            ),
            ft.Row([res_table], scroll=ft.ScrollMode.AUTO),
        ], spacing=10))

    def on_batch_generate_preview_clicked(e):
        sel_ids = sorted(list(state["selected_ids"]))
        if not sel_ids:
            show_message("Please select at least one candidate first.", False)
            return

        doc_type = batch_doc_type_dropdown.value or "offer"
        batch_preview_btn.disabled = True
        batch_preview_btn.text = "Generating Previews..."
        page.update()

        all_cands_map = {c["id"]: c for c in db_manager.get_all_candidates()}
        results = []

        for cid in sel_ids:
            cand = all_cands_map.get(cid) or db_manager.get_candidate_by_id(cid)
            cand_name = cand.get("candidate_name") if cand else f"Candidate #{cid}"
            try:
                res = document_generation_service.generate_preview_document(
                    candidate_id=cid,
                    document_type=doc_type,
                )
                if res.get("success"):
                    results.append({
                        "candidate_id": cid,
                        "candidate_name": cand_name,
                        "doc_type": doc_type,
                        "preview_file_path": res.get("preview_file_path"),
                        "previewed_ref": res.get("previewed_reference_number"),
                        "success": True,
                        "error": None,
                        "finalized": False,
                        "reference_number": None,
                        "final_file_path": None,
                    })
                else:
                    err_msg = res.get("error", "We couldn't generate the preview document.")
                    results.append({
                        "candidate_id": cid,
                        "candidate_name": cand_name,
                        "doc_type": doc_type,
                        "preview_file_path": None,
                        "previewed_ref": None,
                        "success": False,
                        "error": err_msg,
                        "finalized": False,
                        "reference_number": None,
                        "final_file_path": None,
                    })
            except Exception as ex:
                results.append({
                    "candidate_id": cid,
                    "candidate_name": cand_name,
                    "doc_type": doc_type,
                    "preview_file_path": None,
                    "previewed_ref": None,
                    "success": False,
                    "error": "We couldn't generate the preview document. Please check candidate details.",
                    "finalized": False,
                    "reference_number": None,
                    "final_file_path": None,
                })

        state["batch_preview_results"] = results
        update_batch_toolbar_state()
        refresh_batch_results_table()

        success_cnt = sum(1 for r in results if r["success"])
        fail_cnt = len(results) - success_cnt
        if fail_cnt == 0:
            show_message(f"Generated {success_cnt} document preview(s) successfully! Review them below.", True)
        else:
            show_message(f"Generated {success_cnt} preview(s); {fail_cnt} candidate(s) could not be generated. See details below.", False)

        page.update()

    def on_batch_search_change(e):
        val = getattr(e.control, "value", "")
        refresh_batch_candidates_table(filter_text=val)
        page.update()

    def on_batch_doc_type_change(e):
        val = getattr(e.control, "value", None) or getattr(e, "data", None)
        if val:
            state["batch_doc_type"] = val
        page.update()

    batch_generation_card = modern_card(ft.Column([
        section_title(ft.Icons.AUTO_AWESOME_MOTION_ROUNDED, "Step 4: Batch Document Generation"),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        ft.Text(
            "Select multiple candidates below to generate document previews in batch. "
            "Batch previews do NOT consume reference numbers until you explicitly approve each candidate individually.",
            size=12, color=COLOR_TEXT_SECONDARY
        ),
        # Batch Toolbar
        ft.Row([
            batch_count_label,
            ft.Container(width=5),
            batch_doc_type_dropdown,
            batch_preview_btn,
            ft.Container(expand=True),
            batch_search_input,
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
        ft.Divider(height=10, color=COLOR_CARD_BORDER),
        # Candidate selection table
        batch_table_container,
        ft.Container(height=10),
        # Batch preview results
        batch_results_container,
    ], spacing=12))

    # Wire event callbacks
    search_text.on_change = on_search_change
    candidate_dropdown.on_select = on_candidate_selected
    candidate_dropdown.on_change = on_candidate_selected
    doc_type_dropdown.on_select = on_doc_type_change
    doc_type_dropdown.on_change = on_doc_type_change
    batch_doc_type_dropdown.on_select = on_batch_doc_type_change
    batch_search_input.on_change = on_batch_search_change
    batch_preview_btn.on_click = on_batch_generate_preview_clicked
    batch_select_all_checkbox.on_change = on_select_all_toggle

    # Initial candidate load
    load_candidates_into_dropdown()
    update_dynamic_fields()
    refresh_batch_candidates_table()
    update_batch_toolbar_state()

    # ---------------- Layout Assembly ----------------

    view_column = ft.Column([
        # Header
        page_header(
            icon=ft.Icons.DESCRIPTION_ROUNDED,
            title="📄 Document Generator",
            subtitle="Generate official HR documents, letters, and certificates. "
                     "Review previews without consuming reference numbers, then confirm to issue final documents.",
        ),

        ft.Container(height=10),

        # Selection Card
        modern_card(ft.Column([
            section_title(ft.Icons.BADGE_ROUNDED, "Step 1: Select Candidate & Document Type"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([search_text, candidate_dropdown], spacing=12),
            candidate_info_container,
            ft.Row([doc_type_dropdown], spacing=12),
        ], spacing=12)),

        ft.Container(height=10),

        # Details & Form Card
        modern_card(ft.Column([
            section_title(ft.Icons.EDIT_NOTE_ROUNDED, "Step 2: Review & Fill Document Details"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(
                "These details pre-fill from the candidate record. Any corrections you make here will be saved back to the database.",
                size=12, color=COLOR_TEXT_SECONDARY
            ),
            ft.Row([father_name_field, gender_dropdown, department_field], spacing=12),
            address_field,
            ft.Row([date_joined_field, salary_field, employee_number_field], spacing=12),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            dynamic_fields_container,
            template_override_container,
        ], spacing=12)),

        ft.Container(height=10),

        # Action Buttons & Result Card
        modern_card(ft.Column([
            section_title(ft.Icons.PRINT_ROUNDED, "Step 3: Preview & Confirm Final Generation"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([
                ft.ElevatedButton(
                    "👁️ Preview Document (Safe)",
                    icon=ft.Icons.VISIBILITY_ROUNDED,
                    bgcolor=ft.Colors.BLUE_GREY_700,
                    color=ft.Colors.WHITE,
                    on_click=on_preview_clicked,
                ),
                ft.ElevatedButton(
                    "✅ Confirm & Generate Final Document",
                    icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    on_click=on_finalize_clicked,
                ),
            ], spacing=12),
            result_container,
        ], spacing=12)),

        ft.Container(height=10),

        # History Card
        history_container,
        email_history_container,

        ft.Container(height=10),

        # Batch Document Generation Card
        batch_generation_card,

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)

    # Expose state and batch controls for inspection & testing
    view_column.state = state
    view_column.batch_preview_btn = batch_preview_btn
    view_column.batch_doc_type_dropdown = batch_doc_type_dropdown
    view_column.batch_select_all_checkbox = batch_select_all_checkbox
    view_column.refresh_batch_candidates_table = refresh_batch_candidates_table
    view_column.refresh_batch_results_table = refresh_batch_results_table
    view_column.batch_results_container = batch_results_container

    return view_column
