"""
Unit & UI Flow Test: test_joining_upload_preview_ui.py
Verifies:
1. Multi-sheet Excel upload renders sheet switcher tabs, 4-card KPI strip, and 10-row candidate preview DataTable.
2. Clicking sheet switcher tabs changes the active preview sheet and refreshes the preview DataTable.
3. Post-ingestion completed panel displays success header, sheet breakdown chips, and quick-action buttons.
4. Quick-action buttons successfully transition filter state and dismiss the upload panel.
"""

import os
import sys
import pandas as pd

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from database import db_manager
from pages.joining_process_page import joining_process_view


class MockPage:
    def __init__(self):
        self.title = "Joining Process Preview Test"
        self.overlay = []
        self.services = []
        self.controls = []
        self.messages = []
        self.snack_bar = None

    def open(self, control):
        if isinstance(control, ft.SnackBar):
            self.snack_bar = control
            if hasattr(control.content, "value"):
                self.messages.append(control.content.value)
        elif hasattr(control, "content") and hasattr(control.content, "value"):
            self.messages.append(control.content.value)

    def close(self, control=None):
        pass

    def update(self):
        pass


class MockPickedFile:
    def __init__(self, path, name):
        self.path = path
        self.name = name


def create_multisheet_excel(file_path: str):
    """Creates an Excel workbook with two sheets: UP (3 candidates) and Bihar (2 candidates)."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    up_rows = [
        {
            "Candidate Name": "Aarav PreviewTest",
            "Mobile": "9811002201",
            "Email": "aarav.test@example.com",
            "Applied Designation": "Community Mobilizer",
            "Negotiated Salary": "24000",
            "Recent Designation": "Mobilizer",
            "Highest Education Qualification": "Graduate",
            "Total Years of Experience (Inferred)": "2",
            "Core Technical Skills": "Outreach",
            "Key Responsibilities": "Field work",
            "Contact Location": "Lucknow",
        },
        {
            "Candidate Name": "Pooja PreviewTest",
            "Mobile": "9811002202",
            "Email": "pooja.test@example.com",
            "Applied Designation": "District Coordinator",
            "Negotiated Salary": "32000",
            "Recent Designation": "Coordinator",
            "Highest Education Qualification": "Post Graduate",
            "Total Years of Experience (Inferred)": "4",
            "Core Technical Skills": "Project Coordination",
            "Key Responsibilities": "District oversight",
            "Contact Location": "Varanasi",
        },
        {
            "Candidate Name": "Rohan PreviewTest",
            "Mobile": "9811002203",
            "Email": "rohan.test@example.com",
            "Applied Designation": "Field Executive",
            "Negotiated Salary": "21000",
            "Recent Designation": "Field Worker",
            "Highest Education Qualification": "12th Pass",
            "Total Years of Experience (Inferred)": "1",
            "Core Technical Skills": "Communication",
            "Key Responsibilities": "Survey",
            "Contact Location": "Kanpur",
        },
    ]

    bihar_rows = [
        {
            "Candidate Name": "Manoj PreviewTest",
            "Mobile": "9822003301",
            "Email": "manoj.test@example.com",
            "Applied Designation": "Pharmacist",
            "Negotiated Salary": "28000",
            "Recent Designation": "Pharmacist",
            "Highest Education Qualification": "B.Pharm",
            "Total Years of Experience (Inferred)": "3",
            "Core Technical Skills": "Medicine Dispensing",
            "Key Responsibilities": "Pharmacy management",
            "Contact Location": "Patna",
        },
        {
            "Candidate Name": "Anjali PreviewTest",
            "Mobile": "9822003302",
            "Email": "anjali.test@example.com",
            "Applied Designation": "Staff Nurse",
            "Negotiated Salary": "26000",
            "Recent Designation": "Nurse",
            "Highest Education Qualification": "GNM",
            "Total Years of Experience (Inferred)": "2",
            "Core Technical Skills": "Patient Care",
            "Key Responsibilities": "Triage & Vitals",
            "Contact Location": "Gaya",
        },
    ]

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.DataFrame(up_rows).to_excel(writer, sheet_name="UP", index=False)
        pd.DataFrame(bihar_rows).to_excel(writer, sheet_name="Bihar", index=False)


def find_controls_by_type(root, target_type):
    """Recursively search for controls of a given class."""
    results = []
    if isinstance(root, target_type):
        results.append(root)

    content = getattr(root, "content", None)
    if content:
        results.extend(find_controls_by_type(content, target_type))

    controls = getattr(root, "controls", None)
    if controls and isinstance(controls, list):
        for c in controls:
            results.extend(find_controls_by_type(c, target_type))

    rows = getattr(root, "rows", None)
    if rows and isinstance(rows, list):
        for r in rows:
            results.extend(find_controls_by_type(r, target_type))

    cells = getattr(root, "cells", None)
    if cells and isinstance(cells, list):
        for cell in cells:
            results.extend(find_controls_by_type(cell, target_type))

    return results


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 6 TESTS: INLINE MULTI-SHEET PREVIEW & ACTION CARDS")
    print("=" * 70)

    db_manager.init_db()
    test_excel = os.path.join(DESKTOP_APP_DIR, "output", "test_multisheet_joining.xlsx")

    # Clean existing test candidates from database
    mobiles = ["9811002201", "9811002202", "9811002203", "9822003301", "9822003302"]
    conn = db_manager.get_connection()
    placeholders = ",".join("?" for _ in mobiles)
    conn.execute(f"DELETE FROM candidates WHERE mobile IN ({placeholders}) OR candidate_name LIKE '%PreviewTest%'", mobiles)
    conn.commit()
    conn.close()

    create_multisheet_excel(test_excel)

    page = MockPage()
    view = joining_process_view(page)
    assert isinstance(view, ft.Column), "joining_process_view must return ft.Column"

    picker = page.services[0] if page.services else page.overlay[0]

    # 1. Trigger upload of multi-sheet spreadsheet
    print("\n[TEST 1] Triggering multi-sheet spreadsheet upload...")
    picker.on_result([MockPickedFile(test_excel, "test_multisheet_joining.xlsx")])

    upload_card = view.controls[2]
    upload_status_col = upload_card.content.controls[-1]
    assert len(upload_status_col.controls) > 0, "upload_status_column should not be empty after upload"

    preview_container = upload_status_col.controls[0]

    # Verify Sheet Switcher Tabs
    print("\n[TEST 2] Verifying Sheet Switcher Tabs...")
    buttons = find_controls_by_type(preview_container, ft.ElevatedButton)
    button_texts = [b.text for b in buttons if b.text]
    has_up_tab = any("UP" in (b.text or "") for b in buttons)
    has_bihar_tab = any("Bihar" in (b.text or "") for b in buttons)
    assert has_up_tab, f"UP sheet tab missing from buttons: {button_texts}"
    assert has_bihar_tab, f"Bihar sheet tab missing from buttons: {button_texts}"
    print("  ✓ UP and Bihar sheet switcher tabs found.")

    # Verify KPI Metrics Strip
    print("\n[TEST 3] Verifying KPI Metrics Strip...")
    all_texts = [t.value for t in find_controls_by_type(preview_container, ft.Text) if t.value]
    text_blob = " ".join(all_texts)
    assert "Total" in text_blob or "5" in text_blob, "KPI Total missing"
    assert "New" in text_blob, "KPI New Additions missing"
    assert "Duplicates" in text_blob, "KPI Duplicates missing"
    assert "Columns" in text_blob or "Mapped" in text_blob, "KPI Column Health missing"
    print("  ✓ KPI metrics strip contains Total, New, Duplicates, and Column Health.")

    # Verify 10-Row Candidate Preview DataTable
    print("\n[TEST 4] Verifying Candidate Preview DataTable...")
    data_tables = find_controls_by_type(preview_container, ft.DataTable)
    assert len(data_tables) > 0, "Preview DataTable not found inside preview container"
    preview_dt = data_tables[0]
    preview_col_names = [col.label.value for col in preview_dt.columns if hasattr(col.label, "value")]
    for expected_col in ["Candidate Name", "Mobile", "Applied Designation", "Salary", "Location"]:
        assert expected_col in preview_col_names, f"Column '{expected_col}' missing from preview DataTable: {preview_col_names}"

    # Active sheet default is UP (3 candidates)
    assert len(preview_dt.rows) == 3, f"Expected 3 rows for UP sheet preview, got {len(preview_dt.rows)}"
    first_row_name = preview_dt.rows[0].cells[0].content.value
    assert "Aarav PreviewTest" in first_row_name, f"Expected Aarav PreviewTest in UP preview, got {first_row_name}"
    print(f"  ✓ UP preview table rendered with 3 candidate rows (first: {first_row_name}).")

    # Verify Tab Switching to "Bihar"
    print("\n[TEST 5] Testing tab switching to Bihar...")
    bihar_btn = next(b for b in buttons if "Bihar" in (b.text or ""))
    assert bihar_btn.on_click is not None, "Bihar button missing on_click handler"
    bihar_btn.on_click(None)

    # Re-fetch preview container
    preview_container = upload_status_col.controls[0]
    data_tables = find_controls_by_type(preview_container, ft.DataTable)
    assert len(data_tables) > 0, "Preview DataTable missing after tab switch"
    preview_dt = data_tables[0]
    assert len(preview_dt.rows) == 2, f"Expected 2 rows for Bihar sheet preview, got {len(preview_dt.rows)}"
    bihar_first_name = preview_dt.rows[0].cells[0].content.value
    assert "Manoj PreviewTest" in bihar_first_name, f"Expected Manoj PreviewTest in Bihar preview, got {bihar_first_name}"
    print(f"  ✓ Bihar tab switch successful: DataTable updated to 2 rows (first: {bihar_first_name}).")

    # Verify Ingestion and Post-Ingestion Completion Panel
    print("\n[TEST 6] Confirming ingestion and testing completion panel...")
    confirm_buttons = [b for b in find_controls_by_type(preview_container, ft.ElevatedButton) if "Confirm" in (b.text or "")]
    assert len(confirm_buttons) > 0, "Confirm & Ingest button not found"
    confirm_btn = confirm_buttons[0]
    confirm_btn.on_click(None)

    # Inspect post-ingestion completed panel
    assert len(upload_status_col.controls) > 0, "upload_status_column should contain completion panel"
    completed_panel = upload_status_col.controls[0]
    completed_texts = [t.value for t in find_controls_by_type(completed_panel, ft.Text) if t.value]
    completed_blob = " ".join(completed_texts)

    assert "Successfully processed" in completed_blob or "Added" in completed_blob, \
        f"Success header missing in completion panel: {completed_blob}"
    assert "UP" in completed_blob and "Bihar" in completed_blob, \
        f"Sheet breakdown chips missing from completion panel: {completed_blob}"
    print("  ✓ Post-ingestion completion badge displays success header and sheet breakdown chips.")

    # Verify Quick Action Buttons
    print("\n[TEST 7] Verifying post-ingestion quick action buttons...")
    completed_buttons = find_controls_by_type(completed_panel, ft.ElevatedButton) + find_controls_by_type(completed_panel, ft.OutlinedButton)
    welcome_btn = None
    pipeline_btn = None
    for b in completed_buttons:
        txt = b.text or ""
        if not txt and hasattr(b.content, "value"):
            txt = b.content.value
        elif not txt and hasattr(b.content, "controls"):
            txt = " ".join([c.value for c in b.content.controls if hasattr(c, "value")])
        if "Review Welcome Emails" in txt:
            welcome_btn = b
        elif "View In Pipeline" in txt:
            pipeline_btn = b

    assert welcome_btn is not None, "Quick-action button 'Review Welcome Emails' not found"
    assert pipeline_btn is not None, "Quick-action button 'View In Pipeline' not found"
    print("  ✓ Both quick-action buttons ('Review Welcome Emails', 'View In Pipeline') present.")

    # Test clicking 'View In Pipeline' resets upload panel to idle
    pipeline_btn.on_click(None)
    assert len(upload_status_col.controls) == 0, "Upload status column should be idle (empty) after clicking 'View In Pipeline'"
    print("  ✓ Quick-action dismisses upload panel cleanly.")

    print("\n" + "=" * 70)
    print("ALL TASK 6 PREVIEW & ACTION CARD TESTS PASSED! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
