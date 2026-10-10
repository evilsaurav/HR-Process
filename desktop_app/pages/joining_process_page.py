import os
import flet as ft
from config import STATUS_OPTIONS, PRIMARY_COLOR
from database import db_manager
from services import sheet_processor


def section_title(icon, text):
    return ft.Row([
        ft.Icon(icon, color=PRIMARY_COLOR, size=22),
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


def joining_process_view(page: ft.Page):
    # Ensure DB is initialized
    db_manager.init_db()

    # Feedback message helper matching settings_page.py style
    def show_message(text: str, is_success: bool = True):
        page.open(ft.SnackBar(ft.Text(text), bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED))
        page.update()

    # Upload Feedback Area
    upload_status_column = ft.Column(spacing=6)

    # Candidate table container
    table_container = ft.Container()

    # Search & Filter Fields
    search_field = ft.TextField(
        label="Search candidates (Name, Mobile, Designation, Location)...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        border_radius=10,
        on_change=lambda e: refresh_candidates(),
    )

    status_filter = ft.Dropdown(
        label="Status Filter",
        value="All",
        width=200,
        border_radius=10,
        options=[ft.dropdown.Option("All")] + [ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
        on_change=lambda e: refresh_candidates(),
    )

    candidate_count_text = ft.Text("Candidates: 0", size=13, color=ft.Colors.GREY_400)

    # ---------------- Delete Confirmation Dialog ----------------
    def confirm_delete(cand_id: int, cand_name: str):
        def do_delete(e):
            db_manager.delete_candidate(cand_id)
            page.close(dlg)
            refresh_candidates()
            show_message(f"Candidate '{cand_name}' deleted.", True)
            page.update()

        def cancel_delete(e):
            page.close(dlg)
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.RED_400, size=24),
                ft.Text("Confirm Deletion", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            content=ft.Text(f"Are you sure you want to delete candidate '{cand_name}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_delete),
                ft.ElevatedButton("Delete", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_700, on_click=do_delete),
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
        selected_status = status_filter.value if status_filter.value else "All"
        candidates = db_manager.get_all_candidates(search_term=term, status_filter=selected_status)

        candidate_count_text.value = f"Total Candidates: {len(candidates)}"

        if not candidates:
            table_container.content = ft.Container(
                alignment=ft.alignment.center,
                padding=30,
                content=ft.Column([
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=48, color=ft.Colors.GREY_600),
                    ft.Text("No candidates found matching the selected filter/search.",
                            size=14, color=ft.Colors.GREY_400),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
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

                # Status dropdown per row
                status_dd = ft.Dropdown(
                    value=curr_status if curr_status in STATUS_OPTIONS else "Applied",
                    options=[ft.dropdown.Option(opt) for opt in STATUS_OPTIONS],
                    width=150,
                    dense=True,
                    border_radius=8,
                    on_change=make_status_change(cand_id, cand_name),
                )

                # Delete action button
                def create_del_handler(cid=cand_id, cname=cand_name):
                    return lambda e: confirm_delete(cid, cname)

                del_btn = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_300,
                    tooltip="Delete Candidate",
                    on_click=create_del_handler(),
                )

                rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(cand_name, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(cand_mobile)),
                        ft.DataCell(ft.Text(cand_email, size=12)),
                        ft.DataCell(ft.Text(cand_applied)),
                        ft.DataCell(ft.Text(f"₹{cand_salary}" if cand_salary != "N/A" else "N/A")),
                        ft.DataCell(ft.Text(cand_loc)),
                        ft.DataCell(status_dd),
                        ft.DataCell(del_btn),
                    ])
                )

            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Applied Designation", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Salary", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Location", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
                ],
                rows=rows,
                heading_row_color=ft.Colors.GREY_800,
                border=ft.border.all(1, ft.Colors.GREY_800),
                border_radius=10,
                column_spacing=20,
            )

            table_container.content = ft.Row([data_table], scroll=ft.ScrollMode.AUTO)

        page.update()

    # ---------------- File Upload Processing ----------------
    def on_file_result(e: ft.FilePickerResultEvent):
        if not e.files or len(e.files) == 0:
            return

        picked = e.files[0]
        file_path = picked.path
        file_name = picked.name or os.path.basename(file_path)

        upload_status_column.controls.clear()
        upload_status_column.controls.append(
            ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2),
                ft.Text(f"Processing sheet '{file_name}'...", size=13, color=ft.Colors.GREY_400),
            ], spacing=8)
        )
        page.update()

        result = sheet_processor.process_sheet(file_path, file_name)

        upload_status_column.controls.clear()

        if not result.get("success"):
            err_msg = result.get("error", "Failed to process sheet.")
            upload_status_column.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.RED_900,
                    padding=12,
                    border_radius=8,
                    content=ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=20),
                        ft.Text(f"Validation Error: {err_msg}", color=ft.Colors.WHITE, size=13),
                    ], spacing=8)
                )
            )
            show_message(f"Error: {err_msg}", False)
        else:
            total = result.get("total_rows", 0)
            processed = result.get("processed", 0)
            errors = result.get("errors", [])

            summary_text = f"✅ Successfully processed {processed} of {total} rows from '{file_name}'."
            if errors:
                summary_text += f" ({len(errors)} warnings/errors skipped)"

            summary_controls = [
                ft.Text(summary_text, color=ft.Colors.GREEN_300, weight=ft.FontWeight.BOLD, size=14),
            ]

            if errors:
                error_list = ft.Column(
                    controls=[ft.Text(f"• {err}", size=12, color=ft.Colors.ORANGE_300) for err in errors[:10]],
                    spacing=2,
                )
                if len(errors) > 10:
                    error_list.controls.append(
                        ft.Text(f"... and {len(errors) - 10} more rows with errors.", size=11, color=ft.Colors.GREY_400)
                    )
                summary_controls.append(ft.Container(height=4))
                summary_controls.append(ft.Text("Skipped rows / Issues:", size=12, weight=ft.FontWeight.BOLD))
                summary_controls.append(error_list)

            upload_status_column.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.GREY_800,
                    padding=12,
                    border_radius=8,
                    content=ft.Column(summary_controls, spacing=4)
                )
            )
            show_message(f"Processed {processed} candidates successfully!", True)

        refresh_candidates()
        page.update()

    # FilePicker setup
    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)
    page.update()

    def pick_sheet_clicked(e):
        file_picker.pick_files(
            dialog_title="Select Candidate Spreadsheet (.xlsx or .csv)",
            allowed_extensions=["xlsx", "xls", "csv"],
            allow_multiple=False,
        )

    # Initial load of candidates
    refresh_candidates()

    # ---------------- Layout ----------------
    return ft.Column([
        # Header
        ft.Row([
            ft.Icon(ft.Icons.BADGE_OUTLINED, color=PRIMARY_COLOR, size=32),
            ft.Column([
                ft.Text("📋 Joining Process", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Upload candidate sheets, manage candidate pipelines, and track onboarding status",
                        size=13, color=ft.Colors.GREY_400),
            ], spacing=2),
        ], spacing=10),

        ft.Container(height=10),

        # Upload Card
        card(ft.Column([
            section_title(ft.Icons.UPLOAD_FILE, "Upload Candidate Spreadsheet"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ft.Text(
                "Upload a .xlsx or .csv sheet containing candidates. The sheet must include required columns: "
                "Candidate Name, Mobile, Email, Applied Designation, Negotiated Salary, etc.",
                size=12, color=ft.Colors.GREY_400
            ),
            ft.Row([
                ft.ElevatedButton(
                    "Upload Sheet (.xlsx / .csv)",
                    icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                    bgcolor=PRIMARY_COLOR,
                    color=ft.Colors.WHITE,
                    on_click=pick_sheet_clicked,
                ),
            ]),
            upload_status_column,
        ], spacing=10)),

        ft.Container(height=14),

        # Search & Filter Card
        card(ft.Column([
            section_title(ft.Icons.FILTER_LIST, "Candidate Pipeline"),
            ft.Divider(height=10, color=ft.Colors.GREY_800),
            ft.Row([
                search_field,
                status_filter,
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="Refresh List",
                    on_click=lambda e: refresh_candidates(),
                ),
            ], spacing=12),
            candidate_count_text,
            table_container,
        ], spacing=12)),

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
