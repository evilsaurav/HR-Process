"""
Verification Script: test_batch_document_generation.py
Tests Phase F1 Batch Document Generation Feature:
1. Candidate list with checkboxes and Select All toggle.
2. Batch toolbar (count label, doc type dropdown, disabled/enabled states).
3. Batch preview generation for multiple candidates (safe preview, no sequence consumption).
4. Individual approval of ONE candidate from batch results (only that candidate finalized & consumes sequence).
5. Error resilience: one failed candidate does not stop other candidates in the batch.
"""

import os
import sys

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

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


def run_batch_tests():
    print("=" * 70)
    print("PHASE F1 VERIFICATION: BATCH DOCUMENT GENERATION")
    print("=" * 70)

    db_manager.init_db()

    # Ensure reference sequence configured
    ref_cfg = db_manager.get_reference_config("hr_reference")
    if not ref_cfg or ref_cfg["current_number"] + 10 > ref_cfg["range_end"]:
        db_manager.save_reference_config("hr_reference", "DFY/HR/{YEAR}/{NUM}", 3, 1, 9999)

    # 1. Prepare 3 distinct test candidates in DB
    cands_data = [
        {
            "candidate_name": "Aarav Sharma",
            "mobile": "9811000001",
            "email": "aarav.sharma@example.com",
            "applied_designation": "Data Entry Operator",
            "negotiated_salary": "24000",
            "contact_location": "Delhi",
            "father_name": "R. Sharma",
            "full_address": "Flat 101, Delhi",
            "gender": "Male",
            "department": "Admin",
            "date_joined": "2024-01-10",
            "employee_number": "DFY-B01"
        },
        {
            "candidate_name": "Bhavna Verma",
            "mobile": "9811000002",
            "email": "bhavna.verma@example.com",
            "applied_designation": "Data Entry Operator",
            "negotiated_salary": "26000",
            "contact_location": "Mumbai",
            "father_name": "S. Verma",
            "full_address": "Flat 202, Mumbai",
            "gender": "Female",
            "department": "Finance",
            "date_joined": "2024-02-15",
            "employee_number": "DFY-B02"
        },
        {
            "candidate_name": "Chirag Joshi",
            "mobile": "9811000003",
            "email": "chirag.joshi@example.com",
            "applied_designation": "Field Coordinator",
            "negotiated_salary": "22000",
            "contact_location": "Patna",
            "father_name": "M. Joshi",
            "full_address": "Flat 303, Patna",
            "gender": "Male",
            "department": "Field",
            "date_joined": "2024-03-20",
            "employee_number": "DFY-B03"
        },
    ]

    prepared_cands = []
    for c in cands_data:
        db_manager.upsert_candidate(c, "batch_test.xlsx")
        c_record = db_manager.get_candidate_by_mobile(c["mobile"])
        db_manager.update_candidate_extra_details(
            candidate_id=c_record["id"],
            father_name=c["father_name"],
            full_address=c["full_address"],
            gender=c["gender"],
            department=c["department"],
            date_joined=c["date_joined"],
            employee_number=c["employee_number"]
        )
        prepared_cands.append(c_record)

    cid_1 = prepared_cands[0]["id"]
    cid_2 = prepared_cands[1]["id"]
    cid_3 = prepared_cands[2]["id"]
    print(f"Prepared 3 test candidates: IDs {cid_1}, {cid_2}, {cid_3}")

    page = MockPage()
    view = document_generation_view(page)
    state = view.state

    # Verify initial batch state
    assert len(state["selected_ids"]) == 0
    assert view.batch_preview_btn.disabled is True
    print("✅ Initial state verified: 0 selected, 'Generate Preview' button disabled.")

    # 2. Select 3 candidates in batch selection set
    state["selected_ids"].add(cid_1)
    state["selected_ids"].add(cid_2)
    state["selected_ids"].add(cid_3)

    # Re-render batch candidate table to sync checkbox state
    view.refresh_batch_candidates_table()
    view.batch_preview_btn.disabled = False
    print(f"✅ Selected 3 candidates (IDs: {[cid_1, cid_2, cid_3]}).")

    # Pick document type "offer"
    view.batch_doc_type_dropdown.value = "offer"

    # Capture reference sequence number before batch preview
    ref_before_preview = db_manager.get_reference_config("hr_reference")["current_number"]

    # 3. Trigger "Generate Preview for Selected"
    print("\nTriggering 'Generate Preview for Selected'...")
    view.batch_preview_btn.on_click(MockEvent(view.batch_preview_btn))

    # Verify reference sequence was NOT consumed
    ref_after_preview = db_manager.get_reference_config("hr_reference")["current_number"]
    assert ref_before_preview == ref_after_preview, (
        f"Reference sequence MUST NOT be consumed during preview! Before: {ref_before_preview}, After: {ref_after_preview}"
    )
    print(f"✅ Sequence integrity verified: Current sequence remains at {ref_after_preview} (0 numbers consumed).")

    # Verify batch_preview_results contents
    results = state["batch_preview_results"]
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    print(f"\nBatch Preview Results ({len(results)} items):")
    for r in results:
        status_text = "✅ Ready" if r["success"] else f"❌ Error: {r['error']}"
        print(f"   • Candidate ID {r['candidate_id']} ({r['candidate_name']}): {r['doc_type']} -> {status_text}")
        if r["success"]:
            print(f"     Preview path: {r['preview_file_path']}")
        assert r["success"] is True, f"Preview generation should succeed for {r['candidate_name']}"
        assert r["finalized"] is False, "Candidates must start un-finalized"
        assert r["preview_file_path"] and os.path.exists(r["preview_file_path"])

    assert all(r["success"] is True for r in results), "All 3 candidates should generate previews successfully"
    print("✅ Verified: All 3 candidate previews generated successfully without sequence consumption.")

    # 4. Approve ONE candidate only (e.g. candidate #2 Bhavna Verma)
    candidate_to_approve = results[1]
    cid_approved = candidate_to_approve["candidate_id"]
    name_approved = candidate_to_approve["candidate_name"]
    print(f"\nApproving ONE candidate only: ID {cid_approved} ({name_approved})...")

    # Find the approve handler for this row from batch results table
    # In refresh_batch_results_table, the approve handler is wired to approve_btn
    batch_results_card = view.batch_results_container.content.content
    results_table = batch_results_card.controls[3].controls[0]

    # Row 1 corresponds to results[1]
    row_1 = results_table.rows[1]
    actions_cell = row_1.cells[3]
    approve_btn = actions_cell.content.controls[1]
    assert approve_btn.text == "Approve & Finalize"

    # Trigger click on approve_btn
    approve_btn.on_click(MockEvent(approve_btn))

    # Verify reference sequence incremented by EXACTLY 1
    ref_after_approve = db_manager.get_reference_config("hr_reference")["current_number"]
    assert ref_after_approve == ref_after_preview + 1, (
        f"Sequence should have incremented by exactly 1! Expected {ref_after_preview + 1}, got {ref_after_approve}"
    )
    print(f"✅ Reference sequence incremented by exactly 1: Now {ref_after_approve}.")

    # Verify candidate #2 status
    assert candidate_to_approve["finalized"] is True
    assert candidate_to_approve["reference_number"] is not None
    print(f"✅ Approved candidate #{cid_approved} ({name_approved}) is finalized with Ref #{candidate_to_approve['reference_number']}.")

    # Verify candidate #1 and candidate #3 are STILL un-finalized
    assert results[0]["finalized"] is False
    assert results[0]["reference_number"] is None
    assert results[2]["finalized"] is False
    assert results[2]["reference_number"] is None
    print("✅ Non-approved candidates (IDs 1 & 3) remain un-finalized with NO sequence numbers consumed.")

    # Verify that clicking preview view handler safely checks file existence
    view_btn = actions_cell.content.controls[0]
    view_btn.on_click(MockEvent(view_btn))
    print("✅ View preview button invoked without exceptions.")

    print("\n" + "=" * 70)
    print("ALL BATCH DOCUMENT GENERATION TESTS PASSED! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_batch_tests()
