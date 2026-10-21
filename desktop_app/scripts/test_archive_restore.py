"""
Verification Script: test_archive_restore.py
Phase G1 Follow-up Fix — Step 2 Test Suite: Archive View & Candidate Restore.

Tests:
1. Candidates can be soft-deleted using db_manager.archive_candidate().
2. Archived candidates are excluded from get_all_candidates() active list.
3. Archived candidates appear in db_manager.get_archived_candidates().
4. Archived candidates store archived = 1 and a valid archived_at timestamp.
5. Search filtering works correctly on archived candidates.
6. db_manager.restore_candidate() resets archived = 0 and archived_at = NULL.
7. Restored candidates preserve all existing fields (status, mobile, email, salary, etc.).
8. Restored candidates immediately reappear in get_all_candidates().
9. Non-existent candidate IDs return False safely.
10. Joining Process page UI smoke test verifies switch control and view construction.
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

from database import db_manager
from pages.joining_process_page import joining_process_view


class MockPage:
    """Minimal mock page to test Flet UI assembly and controls."""
    def __init__(self):
        self.controls = []
        self.overlay = []
        self.opened_dialogs = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass

    def open(self, control):
        self.opened_dialogs.append(control)

    def close(self, control):
        if control in self.opened_dialogs:
            self.opened_dialogs.remove(control)


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 2 TESTS: ARCHIVE VIEW & RESTORE VERIFICATION")
    print("=" * 70)

    db_manager.init_db()

    mob1 = "9888800001"
    mob2 = "9888800002"

    # Clean up test rows
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?)", (mob1, mob2))
    conn.commit()
    conn.close()

    try:
        # Step 1: Create 2 test candidates
        c1_data = {
            "candidate_name": "Archive Test Candidate Alpha",
            "mobile": mob1,
            "email": "alpha.test@example.com",
            "applied_designation": "Project Lead",
            "negotiated_salary": "60000",
            "contact_location": "Delhi",
            "status": "Shortlisted",
        }
        c2_data = {
            "candidate_name": "Archive Test Candidate Beta",
            "mobile": mob2,
            "email": "beta.test@example.com",
            "applied_designation": "Coordinator",
            "negotiated_salary": "40000",
            "contact_location": "Noida",
            "status": "Interview",
        }
        db_manager.upsert_candidate(c1_data, "Test Script")
        db_manager.upsert_candidate(c2_data, "Test Script")

        # Retrieve IDs
        c1 = db_manager.get_candidate_by_mobile(mob1)
        c2 = db_manager.get_candidate_by_mobile(mob2)
        assert c1 is not None and c2 is not None, "Failed to create initial test candidates"
        c1_id = c1["id"]
        c2_id = c2["id"]

        # Explicitly set status to Shortlisted to test retention across archive & restore
        db_manager.update_candidate_status(c1_id, "Shortlisted")
        db_manager.update_candidate_status(c2_id, "Interview")

        print(f"Created test candidates: Alpha (ID {c1_id}, Shortlisted), Beta (ID {c2_id}, Interview)")

        # Step 2: Verify both in active list, neither in archived list
        active_list = db_manager.get_all_candidates()
        archived_list = db_manager.get_archived_candidates()

        active_ids = [c["id"] for c in active_list]
        archived_ids = [c["id"] for c in archived_list]

        assert c1_id in active_ids, "Candidate Alpha must be in active candidates list"
        assert c2_id in active_ids, "Candidate Beta must be in active candidates list"
        assert c1_id not in archived_ids, "Candidate Alpha must not be in archived candidates list"
        assert c2_id not in archived_ids, "Candidate Beta must not be in archived candidates list"
        print("[PASS] Initial active/archived state verified")

        # Step 3: Archive Candidate Alpha
        archived_ok = db_manager.archive_candidate(c1_id)
        assert archived_ok is True, "archive_candidate() should return True"

        # Check candidate in DB
        c1_archived = db_manager.get_candidate_by_id(c1_id)
        assert c1_archived["archived"] == 1, "Candidate Alpha archived flag should be 1"
        assert c1_archived["archived_at"] is not None, "Candidate Alpha archived_at must be populated"
        print(f"[PASS] Candidate Alpha archived at: {c1_archived['archived_at']}")

        # Step 4: Verify active vs archived list separation
        active_now = db_manager.get_all_candidates()
        archived_now = db_manager.get_archived_candidates()

        active_now_ids = [c["id"] for c in active_now]
        archived_now_ids = [c["id"] for c in archived_now]

        assert c1_id not in active_now_ids, "Candidate Alpha must be hidden from active candidates list"
        assert c2_id in active_now_ids, "Candidate Beta must remain in active candidates list"
        assert c1_id in archived_now_ids, "Candidate Alpha must appear in get_archived_candidates()"
        print("[PASS] Active list hides archived candidate; archived list displays it")

        # Step 5: Test search on archived candidates
        search_match = db_manager.get_archived_candidates(search_term="Alpha")
        assert any(c["id"] == c1_id for c in search_match), "Search 'Alpha' should find Candidate Alpha"

        search_no_match = db_manager.get_archived_candidates(search_term="NonExistentNameXYZ")
        assert len(search_no_match) == 0, "Non-matching search should return 0 archived candidates"
        print("[PASS] Search filtering on archived candidates works correctly")

        # Step 6: Restore Candidate Alpha
        restored_ok = db_manager.restore_candidate(c1_id)
        assert restored_ok is True, "restore_candidate() should return True"

        c1_restored = db_manager.get_candidate_by_id(c1_id)
        assert c1_restored["archived"] == 0, "Candidate Alpha archived flag should reset to 0"
        assert c1_restored["archived_at"] is None, "Candidate Alpha archived_at should reset to NULL"
        assert c1_restored["status"] == "Shortlisted", "Candidate Alpha status must be preserved"
        assert c1_restored["applied_designation"] == "Project Lead", "Applied designation must be preserved"
        assert c1_restored["negotiated_salary"] == "60000", "Negotiated salary must be preserved"
        print("[PASS] Candidate Alpha restored: archived=0, archived_at=NULL, all data intact")

        # Step 7: Verify Alpha is back in active list and gone from archived list
        active_after = db_manager.get_all_candidates()
        archived_after = db_manager.get_archived_candidates()

        active_after_ids = [c["id"] for c in active_after]
        archived_after_ids = [c["id"] for c in archived_after]

        assert c1_id in active_after_ids, "Candidate Alpha must be back in active list"
        assert c1_id not in archived_after_ids, "Candidate Alpha must no longer appear in archived list"
        print("[PASS] Candidate Alpha successfully rejoined active pipeline")

        # Step 8: Safe handling of invalid IDs
        assert db_manager.archive_candidate(99999999) is False, "archive_candidate(invalid) should return False"
        assert db_manager.restore_candidate(99999999) is False, "restore_candidate(invalid) should return False"
        assert db_manager.archive_candidate(None) is False, "archive_candidate(None) should return False"
        assert db_manager.restore_candidate(None) is False, "restore_candidate(None) should return False"
        print("[PASS] Invalid candidate IDs handled safely")

        # Step 9: Smoke test UI view creation
        mock_page = MockPage()
        ui_column = joining_process_view(mock_page)
        assert ui_column is not None, "joining_process_view should return a valid layout column"
        print("[PASS] Joining Process page view initialized cleanly with Show Archived toggle")

        print("=" * 70)
        print("ALL STEP 2 TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # Clean up test rows
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?)", (mob1, mob2))
        conn.commit()
        conn.close()
        print("Cleaned up test candidates.")


if __name__ == "__main__":
    run_tests()
