import os
import flet as ft
from config import STATUS_OPTIONS, PRIMARY_COLOR, DESKTOP_APP_DIR
from database import db_manager
from services import sheet_processor
from services import excel_export_service
from utils.flet_compat import register_overlay_control
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
    COLOR_WARNING_BG,
)


def joining_process_view(page: ft.Page):
    # Ensure DB is initialized
    db_manager.init_db()

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

    # Search & Filter Fields
    search_field = ft.TextField(
        label="Search candidates (Name, Mobile, Designation, Location)...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        on_change=lambda e: refresh_candidates(),
    )

    status_filter = ft.Dropdown(
        label="Status Filter",
        value="All",
        width=200,
        border_radius=10,
        border_color=COLOR_CARD_BORDER,
        focused_border_color=COLOR_PRIMARY_LIGHT,
        options=[ft.dropdown.Option("All")] + [ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
        on_change=lambda e: refresh_candidates(),
    )

    candidate_count_text = ft.Text("Candidates: 0", size=13, color=COLOR_TEXT_SECONDARY)

    show_archived_switch = ft.Switch(
        label="Show Archived",
        value=False,
        active_color=COLOR_WARNING,
        tooltip="Toggle between active and archived candidates",
        on_change=lambda e: refresh_candidates(),
    )

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
            }
            if is_archived:
                row["Archived At"] = c.get("archived_at") or ""
            export_data.append(row)

        excel_export_service.export_to_excel(export_data, out_path, sheet_name=sheet_title)
        show_message(f"Candidate list exported to {os.path.basename(out_path)}!", True)

    # ---------------- Archive Confirmation Dialog (Soft Delete) ----------------
    def confirm_delete(cand_id: int, cand_name: str):
        def do_archive(e):
            ok = db_manager.archive_candidate(cand_id)
            page.close(dlg)
            refresh_candidates()
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
            refresh_candidates()
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
            refresh_candidates()
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

    # ---------------- Inline Status Change Handler ----------------
    def make_status_change(cand_id: int, cand_name: str):
        def on_change(e):
            new_status = e.control.value
            db_manager.update_candidate_status(cand_id, new_status)
            show_message(f"Status for '{cand_name}' updated to '{new_status}'", True)
            refresh_candidates()
        return on_change

    # ---------------- Refresh Candidates Table ----------------
    def refresh_candidates():
        term = search_field.value.strip() if search_field.value else ""
        is_archived = bool(show_archived_switch.value)

        # Disable status filter in archive mode (archived view shows all archived candidates)
        status_filter.disabled = is_archived

        if is_archived:
            candidates = db_manager.get_archived_candidates(search_term=term)
            candidate_count_text.value = f"Archived Candidates: {len(candidates)}"
        else:
            selected_status = status_filter.value if status_filter.value else "All"
            candidates = db_manager.get_all_candidates(search_term=term, status_filter=selected_status)
            candidate_count_text.value = f"Total Candidates: {len(candidates)}"

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
            for c in candidates:
                cand_id = c["id"]
                cand_name = c["candidate_name"] or "N/A"
                cand_mobile = c["mobile"] or "N/A"
                cand_email = c["email"] or "N/A"
                cand_applied = c["applied_designation"] or "N/A"
                cand_salary = c["negotiated_salary"] or "N/A"
                cand_loc = c["contact_location"] or "N/A"
                curr_status = c["status"] or "Applied"
                archived_at = c.get("archived_at") or "N/A"

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
                    # Active view: status dropdown & archive action button
                    status_dd = ft.Dropdown(
                        value=curr_status if curr_status in STATUS_OPTIONS else "Applied",
                        options=[ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
                        width=150,
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

                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(cand_name, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY)),
                            ft.DataCell(ft.Text(cand_mobile, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(cand_email, size=12, color=COLOR_TEXT_MUTED)),
                            ft.DataCell(ft.Text(cand_applied, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(ft.Text(f"₹{cand_salary}" if cand_salary != "N/A" else "N/A", color=COLOR_SUCCESS)),
                            ft.DataCell(ft.Text(cand_loc, color=COLOR_TEXT_SECONDARY)),
                            ft.DataCell(status_dd),
                            ft.DataCell(archive_btn),
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
                    ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Applied Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Salary", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Location", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ]

            data_table = ft.DataTable(
                columns=columns,
                rows=rows,
                heading_row_color=COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                border_radius=12,
                column_spacing=20,
            )

            table_container.content = ft.Row([data_table], scroll=ft.ScrollMode.AUTO)

        page.update()

    # ---------------- Upload State & Duplicate Review Logic ----------------
    upload_state = {
        "file_path": None,
        "file_name": None,
        "total_sheet_rows": 0,
        "valid_rows": [],
        "duplicates": [],
        "new_rows": [],
        "duplicate_percentage": 0.0,
        "sheet_errors": [],
        "view_mode": "idle",  # "idle", "processing", "scenario_b_prompt", "scenario_a_review", "no_duplicates", "completed", "error"
        "error_message": "",
        "completion_summary": None,
    }

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
            upload_status_column.controls.append(
                ft.Container(
                    bgcolor=COLOR_CARD_BG_HOVER,
                    padding=16,
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_SUCCESS),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=24),
                            ft.Text(
                                f"{added} new candidates added. {updated} existing candidates updated. {kept} duplicates left unchanged.",
                                color=COLOR_SUCCESS,
                                weight=ft.FontWeight.BOLD,
                                size=14,
                            ),
                        ], spacing=10),
                    ], spacing=6),
                )
            )
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
                upload_state["view_mode"] = "idle"
                render_upload_ui()
                show_message("Upload cancelled. No changes were made to the database.", True)

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
            upload_status_column.controls.append(banner)
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
                upload_state["view_mode"] = "idle"
                render_upload_ui()
                show_message("Upload cancelled. No changes were made to the database.", True)

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
                ft.Container(expand=True),
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
                            ft.Container(expand=True),
                            status_badge(reason),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([existing_col, new_col], spacing=12),
                        ft.Row([
                            keep_btn,
                            replace_btn,
                            ft.Container(expand=True),
                            status_note,
                        ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True),
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
                    action_bar,
                ], spacing=14),
            )

            upload_status_column.controls.append(review_panel)
            page.update()
            return

        # ---------------- Case: 0 Duplicates (All new) ----------------
        if mode == "no_duplicates":
            new_count = len(upload_state["new_rows"])

            def on_add_all_new(e):
                apply_confirmed_changes()

            def on_cancel(e):
                upload_state["view_mode"] = "idle"
                render_upload_ui()
                show_message("Upload cancelled. No changes were made to the database.", True)

            panel = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=18,
                border_radius=12,
                border=ft.Border.all(1, COLOR_SUCCESS),
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=COLOR_SUCCESS, size=24),
                        ft.Text(
                            f"No duplicates found! All {new_count} candidates in this file are genuinely new.",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=COLOR_TEXT_PRIMARY,
                        ),
                    ], spacing=10),
                    ft.Text(
                        "Click below to add these new candidates to the database pipeline.",
                        size=13,
                        color=COLOR_TEXT_SECONDARY,
                    ),
                    ft.Container(height=4),
                    ft.Row([
                        primary_button(
                            f"Add {new_count} New Candidate(s)",
                            icon=ft.Icons.PERSON_ADD_ROUNDED,
                            bgcolor=PRIMARY_COLOR,
                            on_click=on_add_all_new,
                        ),
                        secondary_button(
                            "Cancel Upload",
                            icon=ft.Icons.CLOSE_ROUNDED,
                            on_click=on_cancel,
                        ),
                    ], spacing=10),
                ], spacing=10),
            )
            upload_status_column.controls.append(panel)
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
        refresh_candidates()

    # ---------------- File Upload Processing ----------------
    def handle_spreadsheet_files(files):
        if not files or len(files) == 0:
            return

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

        # Step 2: Detect duplicates
        dup_res = sheet_processor.detect_duplicates(valid_rows)

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
                ft.Container(expand=True),
                secondary_button(
                    "Export to Excel",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=export_candidates_clicked,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Row([
                search_field,
                status_filter,
                show_archived_switch,
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Refresh List",
                    icon_color=COLOR_PRIMARY_LIGHT,
                    on_click=lambda e: refresh_candidates(),
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            candidate_count_text,
            table_container,
        ], spacing=12)),

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
