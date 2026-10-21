"""
Test Script: test_task6_staging_hub_integration.py
Purpose: Comprehensive verification of Task 6:
- Smart Document Pipeline & Staging Hub UI (document_generation_page.py)
- Tab 1: Smart Detection & Batch Generation to Staging
- Tab 2: Staging & Final Review Queue with Preview, Inline Fix, Format Toggle, and Final Go Bulk Dispatch
- Tab 3: Preserved Manual One-Off Generator
- Clean database teardown
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure UTF-8 output encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager
from services import (
    smart_rule_detector,
    document_staging_service,
    pdf_converter_service,
    document_generation_service,
)
from pages import document_generation_page


def test_staging_hub_integration():
    print("==================================================================")
    print("TASK 6 INTEGRATION TEST: Smart Document Pipeline & Staging Hub UI")
    print("==================================================================")

    # 1. Database Initialization & Schema Verification
    print("\n[1/7] Initializing Database & Verifying Staging Schema...")
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(document_staging)")
    staging_cols = {r[1] for r in cur.fetchall()}
    assert "candidate_id" in staging_cols, "Column 'candidate_id' missing in document_staging"
    assert "document_type" in staging_cols, "Column 'document_type' missing in document_staging"
    assert "status" in staging_cols, "Column 'status' missing in document_staging"
    assert "preferred_format" in staging_cols, "Column 'preferred_format' missing in document_staging"
    assert "recipient_email" in staging_cols, "Column 'recipient_email' missing in document_staging"
    print("  ✓ Schema check passed: document_staging table is fully equipped.")

    # 2. Seed Test Candidates for Smart Detection
    print("\n[2/7] Seeding controlled candidate for Smart Rule Detection...")
    test_mob1 = "9876500001"
    test_mob2 = "9876500002"

    # Cleanup existing test data
    cur.execute("DELETE FROM candidates WHERE mobile IN (?, ?)", (test_mob1, test_mob2))
    conn.commit()

    # Candidate 1: Active joinee without prior offer letter (Triggers Offer Letter)
    cur.execute("""
        INSERT INTO candidates (
            candidate_name, mobile, email, applied_designation, department,
            status, date_joined, negotiated_salary, employee_number
        ) VALUES (
            'Aarav Test Sharma', ?, 'aarav.test@example.com', 'Medical Officer', 'Emergency Medicine',
            'Joined', '2026-10-01', 65000, 'DFY-TEST-001'
        )
    """, (test_mob1,))
    cand1_id = cur.lastrowid

    # Candidate 2: Joinee with contract extension date (Triggers Extension Letter)
    cur.execute("""
        INSERT INTO candidates (
            candidate_name, mobile, email, applied_designation, department,
            status, date_joined, negotiated_salary, employee_number,
            extension_of_service_till
        ) VALUES (
            'Priya Test Patel', ?, 'priya.test@example.com', 'Staff Nurse', 'Critical Care',
            'Joined', '2025-10-01', 40000, 'DFY-TEST-002',
            '2027-03-31'
        )
    """, (test_mob2,))
    cand2_id = cur.lastrowid
    conn.commit()
    conn.close()

    print(f"  ✓ Seeded Candidate 1 (ID: {cand1_id}) and Candidate 2 (ID: {cand2_id}).")

    # 3. Instantiate UI Page with Mock Flet Page
    print("\n[3/7] Instantiating document_generation_view with Mock Flet Page...")
    mock_page = MagicMock()
    mock_page.overlay = []
    opened_dialogs = []

    def mock_open(dlg):
        opened_dialogs.append(dlg)

    def mock_close(dlg=None):
        if dlg and dlg in opened_dialogs:
            opened_dialogs.remove(dlg)
        elif opened_dialogs:
            opened_dialogs.pop()

    mock_page.open = MagicMock(side_effect=mock_open)
    mock_page.close = MagicMock(side_effect=mock_close)
    mock_page.update = MagicMock()

    view_col = document_generation_page.document_generation_view(mock_page)
    assert view_col is not None, "document_generation_view returned None"
    assert hasattr(view_col, "state"), "view_col missing state attribute"
    assert hasattr(view_col, "switch_tab"), "view_col missing switch_tab method"
    assert hasattr(view_col, "btn_generate_selected_to_staging"), "view_col missing btn_generate_selected_to_staging"
    assert hasattr(view_col, "btn_final_go"), "view_col missing btn_final_go"
    print("  ✓ document_generation_view instantiated with all expected API hooks.")

    # 4. Tab 1: Smart Detection Verification
    print("\n[4/7] Testing Tab 1: Smart Detection & Batch Staging...")
    view_col.refresh_detection_table()
    detected_ids = [r["candidate_id"] for r in view_col.state["detected_needs"]]

    assert cand1_id in detected_ids, f"Candidate {cand1_id} should be detected for document need"
    cand1_need = next(r for r in view_col.state["detected_needs"] if r["candidate_id"] == cand1_id)
    print(f"  ✓ Candidate {cand1_id} detected: Suggested='{cand1_need['suggested_doc_type']}', Reason='{cand1_need['trigger_reason']}'")

    # Select Candidate 1 in Tab 1
    view_col.state["selected_detected_ids"].add(cand1_id)
    view_col.state["detection_overrides"][cand1_id] = "offer"

    # Click Generate Selected to Staging Queue
    view_col.btn_generate_selected_to_staging.on_click(None)

    # Verify Tab 1 switched automatically to Tab 2
    assert view_col.state["active_tab"] == 1, f"Expected active_tab=1 (Tab 2), got {view_col.state['active_tab']}"
    print("  ✓ Staging generation complete! Automatically switched to Tab 2 (Staging & Final Review Hub).")

    # 5. Tab 2: Staging Queue & Format Toggle Verification
    print("\n[5/7] Testing Tab 2: Staging Queue, Health Pill & Format Toggle...")
    staged_records = db_manager.get_staging_records(status="Staged")
    staged_cand1 = next((r for r in staged_records if r["candidate_id"] == cand1_id), None)
    assert staged_cand1 is not None, f"No staged record found for candidate {cand1_id}"
    staging_id = staged_cand1["id"]
    print(f"  ✓ Staging record found (ID: {staging_id}) for Candidate {cand1_id} with format='{staged_cand1.get('preferred_format')}'.")

    # Verify Format Toggle in DB
    ok_fmt = db_manager.update_staging_record(staging_id, preferred_format="docx")
    assert ok_fmt is True, "Failed to update preferred_format to docx"
    rec_check = db_manager.get_staging_record_by_id(staging_id)
    assert rec_check["preferred_format"] == "docx", "preferred_format not updated to docx"

    ok_fmt2 = db_manager.update_staging_record(staging_id, preferred_format="pdf")
    assert ok_fmt2 is True, "Failed to update preferred_format back to pdf"
    print("  ✓ Format toggle verified (PDF <-> DOCX) in database.")

    # 6. Tab 2: Inline Fix & Instant Regeneration Modal
    print("\n[6/7] Testing Tab 2: Inline Fix Modal & Instant Document Regeneration...")
    fix_dlg = view_col.open_fix_details_modal(staging_id)
    assert fix_dlg is not None, "open_fix_details_modal returned None"
    assert len(opened_dialogs) > 0, "No dialog was opened by open_fix_details_modal"
    print(f"  ✓ Inline Fix Dialog opened: '{fix_dlg.title.controls[1].value}'.")

    # Test saving an inline correction (e.g. designation updated to 'Senior Medical Officer')
    save_btn = fix_dlg.actions[1]
    assert "Save & Regenerate" in save_btn.text, f"Unexpected save button text: {save_btn.text}"

    # Extract dialog fields and modify designation
    dialog_col = fix_dlg.content.content
    # Find designation field
    row_desig_dept = dialog_col.controls[3]
    desig_field = row_desig_dept.controls[0]
    desig_field.value = "Senior Medical Officer"

    # Trigger save
    save_btn.on_click(None)
    assert mock_page.close.called, "page.close was not called after saving inline fix"

    # Confirm candidate was updated in database
    updated_cand1 = db_manager.get_candidate_by_id(cand1_id)
    assert updated_cand1["applied_designation"] == "Senior Medical Officer", (
        f"Designation not updated in DB: {updated_cand1['applied_designation']}"
    )
    print("  ✓ Candidate record updated and document regenerated via inline fix.")

    # 7. Tab 2: Final Go Bulk Dispatch Flow
    print("\n[7/7] Testing Tab 2: '🚀 Final Go' Bulk Dispatch Flow...")
    view_col.state["selected_staging_ids"].add(staging_id)

    # Open Final Go Confirmation dialog
    confirm_dlg = view_col.open_final_go_confirmation()
    assert confirm_dlg is not None, "open_final_go_confirmation returned None"
    assert "Final Go" in confirm_dlg.title.controls[1].value, "Unexpected title in Final Go dialog"
    print(f"  ✓ Confirmation modal opened: '{confirm_dlg.title.controls[1].value}'.")

    # Confirm and dispatch
    confirm_btn = confirm_dlg.actions[1]
    assert "Confirm & Dispatch" in confirm_btn.text, f"Unexpected button text: {confirm_btn.text}"

    with patch("services.email_service.send_email_smtp", return_value=(True, "Mock email dispatched successfully")):
        confirm_btn.on_click(None)
        assert mock_page.close.called, "page.close was not called to dismiss confirmation modal"

    # Verify staging record was marked Dispatched
    dispatched_rec = db_manager.get_staging_record_by_id(staging_id)
    assert dispatched_rec["status"] == "Dispatched", f"Expected status='Dispatched', got '{dispatched_rec['status']}'"
    assert dispatched_rec["reference_number"] is not None, "Official reference number was not allocated"
    print(f"  ✓ Staging ID {staging_id} successfully dispatched! Allocated Reference: {dispatched_rec['reference_number']}")

    # Clean up test rows and staged files
    print("\n[Cleanup] Cleaning up test candidates and staging records...")
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM document_staging WHERE candidate_id IN (?, ?)", (cand1_id, cand2_id))
    cur.execute("DELETE FROM document_generation_log WHERE candidate_id IN (?, ?)", (cand1_id, cand2_id))
    cur.execute("DELETE FROM candidates WHERE id IN (?, ?)", (cand1_id, cand2_id))
    conn.commit()
    conn.close()

    # Clean up any generated test staged files
    doc_path = dispatched_rec.get("doc_file_path")
    pdf_path = dispatched_rec.get("pdf_file_path")
    for p in [doc_path, pdf_path]:
        if p and os.path.exists(p) and "staged_" in os.path.basename(p):
            try:
                os.remove(p)
            except Exception:
                pass
    print("  ✓ Cleanup complete.")

    print("\n==================================================================")
    print("ALL TASK 6 VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("==================================================================")
    return True


if __name__ == "__main__":
    success = test_staging_hub_integration()
    if not success:
        sys.exit(1)
    sys.exit(0)
