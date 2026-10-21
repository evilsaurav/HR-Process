import os
import sys
import inspect
import asyncio

# Configure UTF-8 encoding for Windows console output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

import flet as ft
from database import db_manager
from pages.joining_process_page import joining_process_view
from pages.keka_sync_page import keka_sync_view
from pages.document_generation_page import document_generation_view
from utils.flet_compat import apply_flet_compat_shims


class MockPage:
    def __init__(self):
        self.title = "Test"
        self.overlay = []
        self.services = []
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


class MockFile:
    def __init__(self, path, name):
        self.path = path
        self.name = name


class MockEvent:
    def __init__(self, control, value=None, data=None):
        self.control = control
        self.data = data or value
        if value is not None:
            self.control.value = value


def test_fix1_joining_process_file_picker():
    print("--- TEST 1: Joining Process FilePicker Real Click Path ---")
    page = MockPage()
    view = joining_process_view(page)
    
    # Service registered in page.services
    assert len(page.services) >= 1, "FilePicker should be registered in page.services"
    file_picker = page.services[0]
    
    # Upload Card: view.controls[2]
    upload_card = view.controls[2]
    upload_btn = upload_card.content.controls[3].controls[0]
    
    # Prepare a test spreadsheet
    test_sheet = os.path.join(DESKTOP_APP_DIR, "output", "test_keka_export.xlsx")
    assert os.path.exists(test_sheet), f"Test sheet must exist at {test_sheet}"
    
    # Mock pick_files returning test file
    mock_file = MockFile(path=test_sheet, name=os.path.basename(test_sheet))
    async def mock_pick_files(**kwargs):
        return [mock_file]
    file_picker.pick_files = mock_pick_files
    
    # Trigger real button on_click
    click_res = upload_btn.on_click(None)
    assert inspect.iscoroutine(click_res), "pick_sheet_clicked must be an async coroutine"
    asyncio.run(click_res)
    
    print("✅ Joining Process upload_btn.on_click executed asynchronously and processed sheet successfully.")


def test_fix1_keka_sync_file_picker():
    print("\n--- TEST 2: Keka Sync FilePicker & SavePicker Real Click Path ---")
    page = MockPage()
    view = keka_sync_view(page)
    
    assert len(page.services) >= 2, "FilePicker and SavePicker should be registered in page.services"
    file_picker = page.services[0]
    save_picker = page.services[1]
    
    upload_card = view.controls[2]
    buttons_row = upload_card.content.controls[3]
    choose_button = buttons_row.controls[0]
    
    test_sheet = os.path.join(DESKTOP_APP_DIR, "output", "test_keka_export.xlsx")
    mock_file = MockFile(path=test_sheet, name="test_keka_export.xlsx")
    
    async def mock_pick_files(**kwargs):
        return [mock_file]
    file_picker.pick_files = mock_pick_files
    
    # Trigger choose_button on_click
    res = choose_button.on_click(None)
    assert inspect.iscoroutine(res), "pick_file_clicked must be an async coroutine"
    asyncio.run(res)
    
    file_info = upload_card.content.controls[4]
    assert "test_keka_export.xlsx" in file_info.value
    print("✅ Keka Sync choose_button.on_click executed asynchronously and registered file.")


def test_fix2_document_generation_dropdown_selection():
    print("\n--- TEST 3: Document Generator Real on_select Dropdown Flow ---")
    db_manager.init_db()
    
    # Ensure test candidate in DB
    cand_data = {
        "candidate_name": "Test Candidate DocGen",
        "mobile": "9988776655",
        "email": "test.docgen@example.com",
        "applied_designation": "Data Entry Operator",
        "negotiated_salary": "22000",
        "contact_location": "Delhi",
    }
    db_manager.upsert_candidate(cand_data, "test.xlsx")
    cand = db_manager.get_candidate_by_mobile("9988776655")
    assert cand is not None
    candidate_id = cand["id"]
    
    page = MockPage()
    view = document_generation_view(page)
    
    step1_card = view.controls[2].content
    step1_row1 = step1_card.controls[2]
    candidate_dropdown = step1_row1.controls[1]
    doc_type_dropdown = step1_card.controls[4].controls[0]
    
    step3_card = view.controls[6].content
    buttons_row = step3_card.controls[2]
    preview_btn = buttons_row.controls[0]
    
    # Test 1: When no candidate is selected, clicking Preview fails with friendly message
    page.messages.clear()
    preview_btn.on_click(None)
    assert any("select a candidate first" in str(m).lower() for m in page.messages), (
        "Preview should warn if no candidate is selected"
    )
    print("✅ Step 1: Pre-selection validation confirmed ('Please select a candidate first').")
    
    # Test 2: Trigger on_select for candidate dropdown
    assert candidate_dropdown.on_select is not None, "candidate_dropdown.on_select must be wired"
    candidate_dropdown.value = str(candidate_id)
    candidate_dropdown.on_select(MockEvent(candidate_dropdown, value=str(candidate_id)))
    
    candidate_info_container = step1_card.controls[3]
    assert candidate_info_container.visible is True, "Candidate info card must be visible after on_select"
    print("✅ Step 2: candidate_dropdown.on_select updated state and showed candidate card.")
    
    # Test 3: Trigger on_select for doc_type dropdown
    assert doc_type_dropdown.on_select is not None, "doc_type_dropdown.on_select must be wired"
    doc_type_dropdown.value = "offer"
    doc_type_dropdown.on_select(MockEvent(doc_type_dropdown, value="offer"))
    print("✅ Step 3: doc_type_dropdown.on_select successfully set document type to 'offer'.")
    
    # Test 4: Clicking Preview succeeds now that candidate is selected
    page.messages.clear()
    preview_btn.on_click(None)
    assert not any("select a candidate first" in str(m).lower() for m in page.messages), (
        "Preview must succeed once candidate is selected"
    )
    result_container = step3_card.controls[3]
    assert result_container.content is not None, "Preview result card must be populated"
    print("✅ Step 4: Preview generated successfully after candidate selection!")


def test_flet_compat_dropdown_property():
    print("\n--- TEST 4: flet_compat Dropdown on_change <-> on_select Property ---")
    apply_flet_compat_shims()
    
    # Constructing with on_change
    d1 = ft.Dropdown(on_change=lambda e: "handled_init")
    assert d1.on_select is not None
    assert d1.on_change is not None
    
    # Setting .on_change property afterwards
    d2 = ft.Dropdown()
    def my_handler(e):
        return "handled_prop"
    d2.on_change = my_handler
    assert d2.on_select == my_handler, "Setting .on_change must update .on_select"
    assert d2.on_change == my_handler, "Getting .on_change must return .on_select"
    print("✅ Dropdown compatibility property verified in flet_compat.")


def test_flet_alignment_compat():
    print("\n--- TEST 5: ft.alignment lowercase constants <-> ft.Alignment ---")
    apply_flet_compat_shims()

    # Verify ft.Alignment.CENTER exists
    assert hasattr(ft.Alignment, "CENTER")
    assert ft.Alignment.CENTER is not None

    # Verify ft.alignment.center backwards compatibility shim
    assert hasattr(ft.alignment, "center"), "ft.alignment must support .center via flet_compat"
    assert ft.alignment.center == ft.Alignment.CENTER

    # Verify Container with both syntaxes
    c1 = ft.Container(alignment=ft.Alignment.CENTER)
    c2 = ft.Container(alignment=ft.alignment.center)
    assert c1.alignment == c2.alignment
    print("✅ Alignment compatibility verified in flet_compat.")


if __name__ == "__main__":
    print("======================================================================")
    print("RUNNING FLET 1.0.4 FIXES & REAL-EVENT-PATH VERIFICATION SUITE")
    print("======================================================================\n")

    test_fix1_joining_process_file_picker()
    test_fix1_keka_sync_file_picker()
    test_fix2_document_generation_dropdown_selection()
    test_flet_compat_dropdown_property()
    test_flet_alignment_compat()

    print("\n======================================================================")
    print("ALL FLET FIX VERIFICATION TESTS PASSED SUCCESSFULLY! ✅")
    print("======================================================================")
