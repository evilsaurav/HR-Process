"""
Test script for Task 4: Staging Service & Bulk Dispatch Engine
Verifies draft generation to staging, non-consuming sequence safety,
inline fix with instant regeneration, and sequence-safe bulk dispatch.
"""

import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager
from services import document_staging_service


def run_test():
    print("Initializing test database...")
    db_manager.init_db()

    # Ensure a reference sequence configuration exists for testing
    ref_cfg = db_manager.get_reference_config("hr_reference")
    if not ref_cfg:
        db_manager.save_reference_config("hr_reference", "DFY/HR/2026/{SEQ}", 4, 1, 9999)
        ref_cfg = db_manager.get_reference_config("hr_reference")

    seq_before_draft = ref_cfg["current_number"]

    # 1. Fetch or create a test candidate
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM candidates WHERE email IS NOT NULL LIMIT 1")
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO candidates (candidate_name, email, mobile, applied_designation, status)
            VALUES ('Staging Test User', 'staging_test@doctorsforyou.org', '9876543210', 'Medical Officer', 'Joined')
        """)
        conn.commit()
        cand_id = cur.lastrowid
        created_test_cand = True
    else:
        cand_id = row[0]
        created_test_cand = False
    conn.close()

    print(f"Using candidate ID: {cand_id}")

    # 2. Generate Draft to Staging
    print("\n--- Testing generate_draft_to_staging ---")
    res = document_staging_service.generate_draft_to_staging(
        candidate_id=cand_id,
        document_type="offer_letter",
        preferred_format="docx"
    )
    assert res["success"] is True, f"Draft generation failed: {res.get('error')}"
    staging_id = res["staging_id"]
    print(f"Draft generated in staging with ID: {staging_id}")
    assert os.path.exists(res["doc_file_path"]), f"Generated DOCX does not exist at {res['doc_file_path']}"

    # Verify sequence was NOT consumed during draft generation
    cfg_after_draft = db_manager.get_reference_config("hr_reference")
    assert cfg_after_draft["current_number"] == seq_before_draft, (
        f"Sequence was prematurely consumed during draft generation! "
        f"Before: {seq_before_draft}, After: {cfg_after_draft['current_number']}"
    )
    print("Verified: Reference number sequence was NOT consumed during draft generation.")

    # 3. Test Inline Fix & Instant Regeneration
    print("\n--- Testing inline_fix_and_regenerate ---")
    fix_res = document_staging_service.inline_fix_and_regenerate(
        staging_id=staging_id,
        updated_candidate_fields={"negotiated_salary": "75000", "department": "Pediatrics"}
    )
    assert fix_res["success"] is True, f"Inline fix failed: {fix_res.get('error')}"
    print("Inline fix and instant regeneration succeeded.")

    # Verify candidate fields were updated in DB
    updated_cand = db_manager.get_candidate_by_id(cand_id)
    assert updated_cand["negotiated_salary"] == "75000", f"Expected salary 75000, got {updated_cand['negotiated_salary']}"
    assert updated_cand["department"] == "Pediatrics", f"Expected department Pediatrics, got {updated_cand['department']}"
    print("Verified: Candidate fields updated in database correctly.")

    # Verify sequence was still NOT consumed during inline fix
    cfg_after_fix = db_manager.get_reference_config("hr_reference")
    assert cfg_after_fix["current_number"] == seq_before_draft, (
        f"Sequence was prematurely consumed during inline fix! "
        f"Before: {seq_before_draft}, After: {cfg_after_fix['current_number']}"
    )
    print("Verified: Reference number sequence was NOT consumed during inline regeneration.")

    # 4. Test Final Go Bulk Dispatch (with mocked email transport)
    print("\n--- Testing final_go_dispatch ---")
    with unittest.mock.patch("services.email_service.send_email_smtp", return_value=(True, "Mock email sent successfully")):
        dispatch_res = document_staging_service.final_go_dispatch(
            staging_ids=[staging_id],
            send_async=False
        )

    assert dispatch_res["total"] == 1, f"Expected total 1, got {dispatch_res['total']}"
    assert dispatch_res["sent"] == 1, f"Expected sent 1, got {dispatch_res['sent']} (errors: {dispatch_res.get('errors')})"
    print(f"Dispatch summary: {dispatch_res}")

    # Verify sequence WAS consumed during dispatch
    cfg_after_dispatch = db_manager.get_reference_config("hr_reference")
    assert cfg_after_dispatch["current_number"] == seq_before_draft + 1, (
        f"Sequence was not consumed during final dispatch! "
        f"Expected {seq_before_draft + 1}, got {cfg_after_dispatch['current_number']}"
    )
    print(f"Verified: Official reference number atomically consumed (+1: {cfg_after_dispatch['current_number']}).")

    # Verify staging record marked as Dispatched
    staged_after_dispatch = db_manager.get_staging_record_by_id(staging_id)
    assert staged_after_dispatch["status"] == "Dispatched", f"Expected Dispatched, got {staged_after_dispatch['status']}"
    assert staged_after_dispatch["reference_number"] is not None
    assert "DRAFT" not in staged_after_dispatch["reference_number"]
    print(f"Verified: Staging status is 'Dispatched' with official reference '{staged_after_dispatch['reference_number']}'.")

    # 5. Clean up staging record
    print("\n--- Cleaning up ---")
    db_manager.delete_staging_record(staging_id)
    assert db_manager.get_staging_record_by_id(staging_id) is None, "Staging record was not deleted."

    if created_test_cand:
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
        conn.commit()
        conn.close()

    print("\nSUCCESS: Task 4 Staging Service lifecycle verified.")


if __name__ == "__main__":
    run_test()
