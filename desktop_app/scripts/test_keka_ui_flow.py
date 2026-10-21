"""
Verification Script: test_keka_ui_flow.py
Tests the complete end-to-end user interaction flow of keka_sync_page:
1. Instantiating keka_sync_view.
2. Picking the test Keka file (simulating FilePicker on_result event).
3. Clicking 'Upload & Sync' and verifying the rendered 2-line result summary card.
4. Clicking 'Download Unmatched Report' and verifying save dialog export.
5. Re-uploading the exact SAME file to verify re-sync behavior:
   - Matched count stays accurate
   - '0 record(s) updated with new information. X record(s) were already up to date.' clearly displayed
6. Simulating a sheet with NO matching records to verify the 0-match warning message.
7. Simulating >20 pending candidates to verify the table truncation notice.
"""

import os
import sys
import inspect
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
from pages.keka_sync_page import keka_sync_view
from services import keka_sync_service


class MockPage:
    def __init__(self):
        self.title = "Test"
        self.overlay = []
        self.controls = []
        self.messages = []

    def open(self, control):
        if hasattr(control, "content") and hasattr(control.content, "value"):
            self.messages.append(control.content.value)
        elif hasattr(control, "text"):
            self.messages.append(control.text)

    def close(self, control=None):
        pass

    def update(self):
        pass


class MockFilePickerFile:
    def __init__(self, path, name):
        self.path = path
        self.name = name


class MockFilePickerResultEvent:
    def __init__(self, files=None, path=None):
        self.files = files or []
        self.path = path


def run_ui_flow_tests():
    print("=" * 70)
    print("TESTING KEKA SYNC UI FLOW & SUMMARY CLARITY")
    print("=" * 70)

    page = MockPage()
    view = keka_sync_view(page)
    print("1. View instantiated successfully.")
    print(f"   Overlay controls count: {len(page.overlay)} (FilePicker & SavePicker)")

    file_picker = page.overlay[0]
    save_picker = page.overlay[1]

    # Find the upload card and its controls
    # View layout:
    # controls[0]: Header Row
    # controls[1]: Container spacing
    # controls[2]: Upload Card
    # controls[3]: Container spacing
    # controls[4]: Pending Container
    upload_card = view.controls[2]
    upload_card_column = upload_card.content
    buttons_row = upload_card_column.controls[3]
    choose_button = buttons_row.controls[0]
    sync_button = buttons_row.controls[1]
    file_info_text = upload_card_column.controls[4]
    result_container = upload_card_column.controls[6]

    print(f"   Initial Sync button disabled: {sync_button.disabled}")
    assert sync_button.disabled is True, "Sync button must initially be disabled"

    # Step 2: Simulate file selection via real choose_button.on_click
    test_sheet_path = os.path.join(DESKTOP_APP_DIR, "output", "test_keka_export.xlsx")
    mock_file = MockFilePickerFile(path=test_sheet_path, name="test_keka_export.xlsx")

    async def mock_pick_files(**kwargs):
        return [mock_file]
    file_picker.pick_files = mock_pick_files

    res = choose_button.on_click(None)
    if inspect.iscoroutine(res):
        import asyncio
        asyncio.run(res)
    else:
        file_picker.on_result(MockFilePickerResultEvent(files=[mock_file]))

    print("\n2. Simulated file selection via choose_button.on_click:")
    print(f"   File info text: {repr(file_info_text.value)}")
    print(f"   Sync button disabled now: {sync_button.disabled}")
    assert sync_button.disabled is False, "Sync button should be enabled after file selection"
    assert "test_keka_export.xlsx" in file_info_text.value

    # Step 3: Simulate clicking 'Upload & Sync' (First time)
    print("\n3. Triggering 'Upload & Sync' (First time)...")
    sync_button.on_click(None)

    print("   First sync completed. Inspecting result container:")
    assert result_container.content is not None, "Result container must contain summary after sync"
    summary_col = result_container.content.content
    text_values = []
    for item in summary_col.controls:
        if isinstance(item, ft.Text):
            text_values.append(item.value)
            print(f"   • Text: {item.value}")
        elif isinstance(item, ft.Row):
            for sub in item.controls:
                if isinstance(sub, ft.ElevatedButton):
                    print(f"   • Button: {sub.text}")

    # Verify 2-line clarity format
    assert any("records matched with employees in the system" in t for t in text_values), \
        "First line must clearly display matched count vs total rows"
    assert any("record(s) updated with new information" in t for t in text_values), \
        "Second line must clearly display updated vs already up to date counts"

    # Step 4: Simulate clicking 'Download Unmatched Report' via download_btn.on_click
    download_btn = None
    for item in summary_col.controls:
        if isinstance(item, ft.Row):
            for sub in item.controls:
                if isinstance(sub, ft.ElevatedButton) and "Download" in (sub.text or ""):
                    download_btn = sub
                    break

    assert download_btn is not None, "Download Unmatched Report button should be visible when unmatched rows exist"
    print("\n4. Triggering 'Download Unmatched Report' click via download_btn.on_click:")

    export_dest = os.path.join(DESKTOP_APP_DIR, "output", "ui_flow_unmatched_report.xlsx")
    async def mock_save_file(**kwargs):
        return export_dest
    save_picker.save_file = mock_save_file

    res = download_btn.on_click(None)
    if inspect.iscoroutine(res):
        import asyncio
        asyncio.run(res)
    else:
        save_picker.on_result(MockFilePickerResultEvent(path=export_dest))
    print(f"   Save result handled. File created: {os.path.exists(export_dest)}")
    assert os.path.exists(export_dest), "Exported Excel file must exist"

    df_check = pd.read_excel(export_dest)
    print(f"   Report shape: {df_check.shape}")
    assert "Row Number" in df_check.columns
    assert "Mobile Number" in df_check.columns
    assert "Candidate Name (from sheet)" in df_check.columns
    assert "Reason" in df_check.columns

    # Step 5: Simulate RE-UPLOADING THE EXACT SAME FILE (No changes needed)
    print("\n5. Triggering RE-UPLOAD of the EXACT SAME file...")
    sync_button.on_click(None)

    print("   Re-upload sync completed. Inspecting result container:")
    assert result_container.content is not None
    summary_col_re = result_container.content.content
    re_text_values = []
    for item in summary_col_re.controls:
        if isinstance(item, ft.Text):
            re_text_values.append(item.value)
            print(f"   • Text: {item.value}")

    # Verification: matched_count is accurate and 0 updated / already up to date is clear
    line1 = re_text_values[0]
    line2 = re_text_values[1]
    print(f"   Line 1: {line1}")
    print(f"   Line 2: {line2}")

    assert "records matched with employees in the system" in line1, "Line 1 must show matched count"
    assert "0 record(s) updated with new information" in line2, \
        "Line 2 must show 0 records updated on re-upload"
    assert "were already up to date" in line2, \
        "Line 2 must state that records were already up to date"

    # Step 6: Simulate uploading a file with ZERO matching records
    print("\n6. Simulating upload of sheet with ZERO matching records...")
    no_match_file_path = os.path.join(DESKTOP_APP_DIR, "output", "zero_match_test.xlsx")
    no_match_df = pd.DataFrame([
        {"Employee Code": "EMP-9991", "Mobile Number": "9999900001", "Relieving Date": ""},
        {"Employee Code": "EMP-9992", "Mobile Number": "9999900002", "Relieving Date": ""},
    ])
    no_match_df.to_excel(no_match_file_path, index=False)

    mock_zero_file = MockFilePickerFile(path=no_match_file_path, name="zero_match_test.xlsx")
    file_picker.on_result(MockFilePickerResultEvent(files=[mock_zero_file]))
    sync_button.on_click(None)

    summary_col_zero = result_container.content.content
    zero_text_values = [it.value for it in summary_col_zero.controls if isinstance(it, ft.Text)]
    for val in zero_text_values:
        print(f"   • Text: {val}")

    assert any("None of the records in this sheet matched any employee in the system" in t for t in zero_text_values), \
        "Zero-match special message must be displayed when matched_count == 0 and total_rows > 0"

    # Step 7: Verify Pending Queue Truncation Notice when > 20 candidates
    print("\n7. Verifying Pending Queue Truncation Notice (> 20 candidates)...")
    orig_pending_func = keka_sync_service.get_candidates_pending_keka_sync

    # Mock 25 pending candidates
    mock_25_pending = [
        {"candidate_name": f"Candidate {i}", "mobile": f"98000000{i:02d}", "applied_designation": "Role", "date_joined": "2026-10-01"}
        for i in range(1, 26)
    ]
    keka_sync_service.get_candidates_pending_keka_sync = lambda: mock_25_pending

    try:
        # Re-trigger sync which calls refresh_pending_queue()
        sync_button.on_click(None)

        pending_container = view.controls[4]
        pending_card = pending_container.content
        pending_col = pending_card.content
        pending_texts = [it.value for it in pending_col.controls if isinstance(it, ft.Text)]

        for p_text in pending_texts:
            print(f"   • Pending Section Text: {p_text}")

        expected_notice = "Showing first 20 of 25 pending employees. Upload Keka data to sync them, or check the Joining Process page for full list."
        assert any(expected_notice in t for t in pending_texts), \
            f"Truncation notice '{expected_notice}' must be visible in pending section when count > 20"
        print("   ✅ Truncation notice verified successfully!")
    finally:
        keka_sync_service.get_candidates_pending_keka_sync = orig_pending_func

    print("\n" + "=" * 70)
    print("ALL 7 UI FLOW & VERIFICATION TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_ui_flow_tests()
