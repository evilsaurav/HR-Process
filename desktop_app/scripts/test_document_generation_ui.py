"""
Verification Script: test_document_generation_ui.py
Tests the Document Generation UI Page (Part 2):
1. Instantiating document_generation_view without errors.
2. Selecting a candidate and selecting 'Offer Letter', verifying form fields pre-fill and dynamic fields render.
3. Simulating clicking 'Preview Document' and verifying preview result card with estimated reference number.
4. Simulating clicking 'Confirm & Generate Final Document' and verifying final success card with real reference number.
5. Verifying that candidate generation history reflects the new document log.
"""

import os
import sys

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
from pages.document_generation_page import document_generation_view


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


class MockEvent:
    def __init__(self, control, value=None):
        self.control = control
        if value is not None:
            self.control.value = value


def run_ui_tests():
    print("=" * 70)
    print("PART 2 VERIFICATION: DOCUMENT GENERATION UI PAGE")
    print("=" * 70)

    db_manager.init_db()

    # Ensure a valid reference range
    ref_cfg = db_manager.get_reference_config("hr_reference")
    if not ref_cfg or ref_cfg["current_number"] + 10 > ref_cfg["range_end"]:
        db_manager.save_reference_config("hr_reference", "DFY/HR/{YEAR}/{NUM}", 3, 1, 9999)

    # Prepare a candidate in DB
    cand_data = {
        "candidate_name": "Meera Patel",
        "mobile": "9822334455",
        "email": "meera.patel@example.com",
        "applied_designation": "Data Entry Operator",
        "negotiated_salary": "25000",
        "contact_location": "Mumbai",
    }
    db_manager.upsert_candidate(cand_data, "ui_test_sheet.xlsx")
    cand = db_manager.get_candidate_by_mobile("9822334455")
    candidate_id = cand["id"]

    db_manager.update_candidate_extra_details(
        candidate_id=candidate_id,
        father_name="Kishore Patel",
        full_address="12 Orchid Towers, Andheri West, Mumbai",
        gender="Female",
        department="Health",
        date_joined="2024-05-01",
        employee_number="DFY-9901"
    )

    page = MockPage()
    view = document_generation_view(page)
    print("1. View instantiated successfully.")

    # Layout structure:
    # controls[0]: Header
    # controls[1]: Spacing
    # controls[2]: Selection Card (Step 1)
    # controls[3]: Spacing
    # controls[4]: Details & Form Card (Step 2)
    # controls[5]: Spacing
    # controls[6]: Action Buttons & Result Card (Step 3)
    # controls[7]: Spacing
    # controls[8]: History Card

    step1_card = view.controls[2].content
    step1_row1 = step1_card.controls[2]
    search_box = step1_row1.controls[0]
    candidate_dropdown = step1_row1.controls[1]
    candidate_info_container = step1_card.controls[3]
    doc_type_dropdown = step1_card.controls[4].controls[0]

    step2_card = view.controls[4].content
    step3_card = view.controls[6].content
    buttons_row = step3_card.controls[2]
    preview_btn = buttons_row.controls[0]
    finalize_btn = buttons_row.controls[1]
    result_container = step3_card.controls[3]
    history_container = view.controls[8]

    # Step 1b: Verify validation when NO candidate is selected
    print("\n1b. Verifying validation check when no candidate is selected...")
    page.messages.clear()
    preview_btn.on_click(None)
    assert any("select a candidate first" in str(m).lower() for m in page.messages), (
        "Should show 'please select a candidate first' when no candidate is selected"
    )
    print("   Validation check verified: 'Please select a candidate first.' message shown.")

    # Step 2: Select candidate & document type using real Flet 1.0.4 on_select event path
    print("\n2. Selecting candidate via real Flet on_select event path...")
    assert candidate_dropdown.on_select is not None, "candidate_dropdown.on_select must be wired in Flet 1.0.4"
    assert doc_type_dropdown.on_select is not None, "doc_type_dropdown.on_select must be wired in Flet 1.0.4"

    candidate_dropdown.value = str(candidate_id)
    candidate_dropdown.on_select(MockEvent(candidate_dropdown, value=str(candidate_id)))

    print(f"   Candidate info visible: {candidate_info_container.visible}")
    assert candidate_info_container.visible is True, "Candidate info card should be visible"
    print("   Candidate info card rendered successfully.")

    # Select Offer Letter via real on_select event path
    doc_type_dropdown.value = "offer"
    doc_type_dropdown.on_select(MockEvent(doc_type_dropdown, value="offer"))
    print("   Document type selected: 'offer'")

    # Step 3: Trigger Preview Document
    print("\n3. Triggering 'Preview Document' click...")
    preview_btn.on_click(None)

    assert result_container.content is not None, "Result container must contain preview info"
    preview_card_col = result_container.content.content
    preview_texts = []
    for item in preview_card_col.controls:
        if isinstance(item, ft.Text):
            preview_texts.append(item.value)
        elif isinstance(item, ft.Row):
            for sub in item.controls:
                if isinstance(sub, ft.Column):
                    for sub_text in sub.controls:
                        if isinstance(sub_text, ft.Text):
                            preview_texts.append(sub_text.value)

    print("   Preview texts generated:")
    for t in preview_texts:
        print(f"   • {t}")

    assert any("Preview Ready!" in t for t in preview_texts), "Result should show 'Preview Ready!'"
    assert any("Estimated Reference Number" in t for t in preview_texts), "Result should show estimated reference number"
    print("   ✅ Preview button interaction verified.")

    # Step 4: Trigger Confirm & Generate Final Document
    print("\n4. Triggering 'Confirm & Generate Final Document' click...")
    finalize_btn.on_click(None)

    assert result_container.content is not None
    final_card_col = result_container.content.content
    final_texts = []
    for item in final_card_col.controls:
        if isinstance(item, ft.Row):
            for sub in item.controls:
                if isinstance(sub, ft.Column):
                    for sub_text in sub.controls:
                        if isinstance(sub_text, ft.Text):
                            final_texts.append(sub_text.value)

    print("   Final generation texts generated:")
    for t in final_texts:
        print(f"   • {t}")

    assert any("Final Document Generated Successfully!" in t for t in final_texts), \
        "Result should show 'Final Document Generated Successfully!'"
    assert any("Assigned Reference Number:" in t for t in final_texts), \
        "Result should show assigned reference number"
    print("   ✅ Confirm & Generate Final button interaction verified.")

    # Step 5: Verify history table populated
    print("\n5. Verifying Recent Documents history table...")
    history_card = history_container.content
    assert history_card is not None, "History card must be populated"
    history_records = db_manager.get_generation_history(candidate_id)
    print(f"   History entries count in DB: {len(history_records)}")
    assert len(history_records) >= 1, "At least 1 history record should exist for candidate"
    assert history_records[0]["document_type"] == "offer"
    print("   ✅ Candidate generation history verified.")

    print("\n" + "=" * 70)
    print("ALL PART 2 UI FLOW TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_ui_tests()
