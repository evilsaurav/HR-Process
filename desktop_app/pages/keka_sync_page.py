"""
Page: keka_sync_page.py
Purpose: Non-technical HR interface for uploading Keka HRMS reports,
synchronizing employee numbers and relieving dates, downloading unmatched
reports in Excel, and tracking joined employees awaiting sync.
"""

import os
import inspect
import traceback
import flet as ft
from config import PRIMARY_COLOR, DESKTOP_APP_DIR
from services import keka_sync_service
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
)


def keka_sync_view(page: ft.Page):
    # State tracking
    selected_file = {"path": None, "name": None}
    last_unmatched_rows = []

    # Feedback message helper
    def show_message(text: str, is_success: bool = True):
        page.open(
            ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.GREEN if is_success else ft.Colors.RED,
            )
        )
        page.update()

    # UI controls
    file_info_text = ft.Text(
        "No file selected yet. Please choose an Excel or CSV file.",
        size=13,
        color=COLOR_TEXT_SECONDARY,
    )

    progress_indicator = ft.Row([
        ft.ProgressRing(width=18, height=18, stroke_width=2),
        ft.Text("Matching and syncing records with database...", size=13, color=COLOR_TEXT_SECONDARY),
    ], spacing=10, visible=False)

    result_container = ft.Container()
    pending_container = ft.Container()

    import_new_switch = ft.Switch(
        label="Option C Hybrid: Also import new staff from Keka who did not go through pipeline",
        value=True,
        active_color=COLOR_SUCCESS,
    )

    # ---------------- File Pickers ----------------
    def handle_picked_files(files):
        if not files or len(files) == 0:
            return
        picked = files[0]
        file_path = getattr(picked, "path", None)
        file_name = getattr(picked, "name", None) or (os.path.basename(file_path) if file_path else "unknown")
        selected_file["path"] = file_path
        selected_file["name"] = file_name

        file_info_text.value = f"Selected File: {selected_file['name']}"
        file_info_text.color = COLOR_SUCCESS
        sync_button.disabled = False
        result_container.content = None
        page.update()

    def on_file_picked(e):
        files = getattr(e, "files", e) if not isinstance(e, list) else e
        handle_picked_files(files)

    file_picker = ft.FilePicker(on_result=on_file_picked)
    register_overlay_control(page, file_picker)

    def handle_save_path(dest_path):
        if not dest_path:
            return
        if not dest_path.lower().endswith(".xlsx"):
            dest_path = f"{dest_path}.xlsx"
        try:
            keka_sync_service.export_unmatched_report(last_unmatched_rows, dest_path)
            show_message(f"Unmatched report downloaded successfully to {os.path.basename(dest_path)}!", True)
        except Exception as ex:
            print("Export error:", traceback.format_exc())
            show_message("Unable to save the report file. Please try again.", False)

    def on_save_result(e):
        dest_path = getattr(e, "path", e) if not isinstance(e, str) else e
        handle_save_path(dest_path)

    save_picker = ft.FilePicker(on_result=on_save_result)
    register_overlay_control(page, save_picker)
    page.update()

    async def pick_file_clicked(e):
        try:
            files = await file_picker.pick_files(
                dialog_title="Select Keka HRMS Export (.xlsx or .csv)",
                allowed_extensions=["xlsx", "xls", "csv"],
                allow_multiple=False,
            )
            if files:
                handle_picked_files(files)
        except Exception as ex:
            print("Pick file error:", ex)

    async def download_unmatched_clicked(e):
        if not last_unmatched_rows:
            show_message("No unmatched records to download.", False)
            return
        try:
            dest_path = await save_picker.save_file(
                dialog_title="Save Unmatched Keka Records Report",
                file_name="unmatched_keka_records.xlsx",
                allowed_extensions=["xlsx"],
            )
            if dest_path:
                handle_save_path(dest_path)
        except Exception as ex:
            print("Save file error:", ex)

    # ---------------- Upload & Sync Handler ----------------
    def sync_clicked(e):
        if not selected_file["path"]:
            show_message("Please select a Keka export file first.", False)
            return

        sync_button.disabled = True
        progress_indicator.visible = True
        result_container.content = None
        page.update()

        try:
            res = keka_sync_service.process_rich_keka_sheet(
                selected_file["path"],
                allow_new_inserts=import_new_switch.value
            )
        except Exception as ex:
            print("Keka sync exception:", traceback.format_exc())
            res = {
                "success": False,
                "error": "Something went wrong while processing the file. Please check the file format and try again."
            }

        progress_indicator.visible = False
        sync_button.disabled = False

        if not res.get("success"):
            error_message = res.get("error", "Unable to process the file. Please check your sheet headers.")
            result_container.content = ft.Container(
                bgcolor=ft.Colors.RED_900,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, ft.Colors.RED_700),
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_200, size=24),
                    ft.Text(error_message, color=ft.Colors.WHITE, size=13, weight=ft.FontWeight.W_500),
                ], spacing=10),
            )
            show_message("Sync failed. Please check the error message below.", False)
        else:
            nonlocal last_unmatched_rows
            last_unmatched_rows = res.get("unmatched_rows", [])
            total_rows = res.get("total_rows", 0)
            matched_count = res.get("matched_count", 0)
            updated_count = res.get("updated_count", 0)
            inserted_count = res.get("inserted_count", 0)
            detected_fields = res.get("detected_fields", [])
            unmatched_count = len(last_unmatched_rows)
            errors = res.get("errors", [])

            summary_items = []

            # Summary Message Clarity (UX Fix)
            if matched_count == 0 and inserted_count == 0 and total_rows > 0:
                summary_items.append(
                    ft.Text(
                        "⚠️ None of the records in this sheet matched any employee in the system. Please check the Mobile Numbers or Employee Numbers in your file.",
                        size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_300
                    )
                )
            else:
                if matched_count > 0:
                    summary_items.append(
                        ft.Text(
                            f"✅ {matched_count} of {total_rows} records matched with existing employees in the system.",
                            size=15, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS
                        )
                    )
                    already_up_to_date = matched_count - updated_count
                    summary_items.append(
                        ft.Text(
                            f"→ {updated_count} record(s) updated with Keka master data. {already_up_to_date} record(s) were already up to date.",
                            size=12, color=COLOR_TEXT_SECONDARY
                        )
                    )

                if inserted_count > 0:
                    summary_items.append(
                        ft.Text(
                            f"✨ {inserted_count} new employee(s) imported directly into system records with status 'Joined' (Option C).",
                            size=13, weight=ft.FontWeight.W_500, color=ft.Colors.LIGHT_BLUE_300
                        )
                    )

            if detected_fields:
                sample_fields = ", ".join(detected_fields[:8])
                if len(detected_fields) > 8:
                    sample_fields += f" (+{len(detected_fields) - 8} more)"
                summary_items.append(
                    ft.Text(
                        f"📋 Detected {len(detected_fields)} Keka fields: {sample_fields}",
                        size=11, color=COLOR_TEXT_MUTED, italic=True
                    )
                )

            if unmatched_count > 0:
                summary_items.append(
                    ft.Text(
                        f"⚠️ {unmatched_count} records in the sheet could not be matched with any candidate in the system.",
                        size=13, color=ft.Colors.ORANGE_300
                    )
                )
                summary_items.append(
                    ft.Row([
                        ft.ElevatedButton(
                            "📥 Download Unmatched Report (Excel)",
                            icon=ft.Icons.DOWNLOAD_ROUNDED,
                            bgcolor=ft.Colors.ORANGE_800,
                            color=ft.Colors.WHITE,
                            on_click=download_unmatched_clicked,
                        ),
                    ])
                )

            if errors:
                summary_items.append(
                    ft.Text(f"❌ {len(errors)} rows had formatting issues and were skipped:",
                            size=13, color=ft.Colors.RED_300, weight=ft.FontWeight.BOLD)
                )
                for err in errors[:5]:
                    summary_items.append(
                        ft.Text(f"• {err.get('error', 'Row issue')}", size=12, color=COLOR_TEXT_SECONDARY)
                    )
                if len(errors) > 5:
                    summary_items.append(
                        ft.Text(f"... and {len(errors) - 5} more rows with issues.", size=11, color=COLOR_TEXT_MUTED)
                    )

            if unmatched_count == 0 and len(errors) == 0 and (matched_count > 0 or inserted_count > 0):
                summary_items.append(
                    ft.Text("🎉 All employee records in the sheet processed and synchronized perfectly!",
                            size=13, color=COLOR_SUCCESS)
                )

            result_container.content = ft.Container(
                bgcolor=COLOR_CARD_BG_HOVER,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                content=ft.Column(summary_items, spacing=8),
            )

            if matched_count == 0 and inserted_count == 0 and total_rows > 0:
                show_message("Sync complete: No matching employee records found.", False)
            elif (updated_count + inserted_count) > 0:
                show_message(f"Sync complete! {updated_count} updated, {inserted_count} new employees added.", True)
            else:
                show_message("Sync complete! All matching records were already up to date.", True)

        refresh_pending_queue()
        page.update()

    sync_button = primary_button(
        "Upload & Sync",
        icon=ft.Icons.SYNC_ROUNDED,
        disabled=True,
        on_click=sync_clicked,
    )

    # ---------------- Pending Sync Section ----------------
    def refresh_pending_queue():
        try:
            pending_candidates = keka_sync_service.get_candidates_pending_keka_sync()
        except Exception as ex:
            print("Pending sync fetch error:", ex)
            pending_candidates = []

        if not pending_candidates:
            pending_container.content = modern_card(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=COLOR_SUCCESS, size=24),
                ft.Column([
                    ft.Text("All Joined Employees Are Synced", weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXT_PRIMARY),
                    ft.Text("There are currently no joined employees waiting for Keka Employee Numbers.",
                            size=12, color=COLOR_TEXT_SECONDARY),
                ], spacing=2),
            ], spacing=10))
        else:
            def export_pending_clicked(e):
                if not pending_candidates:
                    show_message("No records to export.", False)
                    return
                out_path = os.path.join(DESKTOP_APP_DIR, "output", "pending_keka_sync_employees.xlsx")
                export_data = [
                    {
                        "Candidate Name": c.get("candidate_name") or "",
                        "Mobile": c.get("mobile") or "",
                        "Designation": c.get("applied_designation") or "",
                        "Date Joined": c.get("date_joined") or "",
                    }
                    for c in pending_candidates
                ]
                excel_export_service.export_to_excel(export_data, out_path, sheet_name="Pending Keka Sync")
                show_message(f"Pending sync list exported to {os.path.basename(out_path)}!", True)

            table_rows = []
            for cand in pending_candidates[:20]:
                table_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(cand.get("candidate_name", "-") or "-", weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY)),
                    ft.DataCell(ft.Text(cand.get("mobile", "-") or "-", color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(cand.get("applied_designation", "-") or "-", color=COLOR_TEXT_SECONDARY)),
                    ft.DataCell(ft.Text(cand.get("date_joined", "-") or "-", color=COLOR_TEXT_MUTED)),
                ]))

            pending_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Candidate Name", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Mobile", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Designation", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                    ft.DataColumn(ft.Text("Date Joined", weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)),
                ],
                rows=table_rows,
                heading_row_color=COLOR_CARD_BG_HOVER,
                border=ft.Border.all(1, COLOR_CARD_BORDER),
                border_radius=10,
                column_spacing=24,
            )

            pending_column_items = [
                ft.Row([
                    section_title(ft.Icons.PENDING_ACTIONS_ROUNDED, "Joined Employees Awaiting Keka Sync"),
                    ft.Container(expand=True),
                    secondary_button(
                        "Export to Excel",
                        icon=ft.Icons.DOWNLOAD_ROUNDED,
                        on_click=export_pending_clicked,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=COLOR_CARD_BORDER),
                ft.Text(
                    f"ℹ️ {len(pending_candidates)} employee(s) have status 'Joined' but do not have an Employee Number assigned yet. "
                    "Once you export their details from Keka and upload here, their employee numbers will be linked automatically.",
                    size=12, color=COLOR_TEXT_SECONDARY
                ),
            ]

            # Pending Table Truncation Notice if candidates > 20
            if len(pending_candidates) > 20:
                pending_column_items.append(
                    ft.Text(
                        f"Showing first 20 of {len(pending_candidates)} pending employees. Upload Keka data to sync them, or check the Joining Process page for full list.",
                        size=12,
                        color=ft.Colors.ORANGE_300,
                        italic=True,
                    )
                )

            pending_column_items.append(ft.Row([pending_table], scroll=ft.ScrollMode.AUTO))

            pending_container.content = modern_card(ft.Column(pending_column_items, spacing=10))

    # Initial load of pending queue
    refresh_pending_queue()

    # ---------------- Layout ----------------
    return ft.Column([
        # Header Section
        page_header(
            icon=ft.Icons.SYNC_ROUNDED,
            title="🔄 Keka HRMS Master Sync",
            subtitle="Upload Keka HRMS reports (simple sync or comprehensive 25+ column master exports). "
                     "We match candidates by Mobile Number or Employee ID and enrich their profiles without losing any existing data. "
                     "Option C also safely imports new staff not yet in the pipeline.",
        ),

        ft.Container(height=10),

        # Upload & Sync Card
        modern_card(ft.Column([
            section_title(ft.Icons.UPLOAD_FILE_ROUNDED, "Upload Keka Export Sheet"),
            ft.Divider(height=10, color=COLOR_CARD_BORDER),
            ft.Text(
                "Select the .xlsx or .csv sheet downloaded from Keka HRMS. "
                "Supports standard Keka master files (Identity, Contact, Job Details, Statutory IDs, Relieving Dates).",
                size=12, color=COLOR_TEXT_SECONDARY
            ),
            import_new_switch,
            ft.Row([
                secondary_button(
                    "Choose Keka Export File (Excel/CSV)",
                    icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                    on_click=pick_file_clicked,
                ),
                sync_button,
            ], spacing=12),
            file_info_text,
            progress_indicator,
            result_container,
        ], spacing=12)),

        ft.Container(height=10),

        # Informational Pending Sync Section
        pending_container,

        ft.Container(height=20),
    ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True)
