"""
Verification Script: test_archive_candidate.py
Step 1 Test Suite for Soft Delete / Candidate Archiving.

Tests:
1. Idempotent database schema migration: init_db() runs safely twice without error.
2. archive_candidate() sets archived=1 and archived_at timestamp, leaving all other fields untouched.
3. Foreign key safety: Archiving a candidate who has existing document_generation_log / email_log
   records does NOT throw any foreign key constraint errors (no records deleted).
4. Default candidate listing: get_all_candidates() excludes archived candidates.
5. include_archived=True flag returns both active and archived candidates.
6. Un-archived candidates are completely unaffected.
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


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 1 TESTS: CANDIDATE ARCHIVING (SOFT DELETE)")
    print("=" * 70)

    # -------------------------------------------------------------
    # TEST 1: Schema migration idempotency
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing idempotent database migration...")
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(candidates)")
    cols = {row[1]: row[2] for row in cur.fetchall()}
    conn.close()

    assert "archived" in cols, f"Column 'archived' not found in candidates table: {list(cols.keys())}"
    assert "archived_at" in cols, f"Column 'archived_at' not found in candidates table: {list(cols.keys())}"

    # Run migration a second time to guarantee idempotency
    db_manager.init_db()
    print("  ✓ Columns 'archived' and 'archived_at' exist; init_db() ran twice without error.")

    # -------------------------------------------------------------
    # TEST 2: Foreign key safety on candidate with logs (Candidate ID 1)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing archive_candidate() on candidate with existing FK logs...")
    # Verify candidate 1 exists and has FK log records
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = 1")
    doc_log_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM email_log WHERE candidate_id = 1")
    email_log_count = cur.fetchone()[0]
    conn.close()

    print(f"  • Candidate #1 has {doc_log_count} document logs and {email_log_count} email logs.")

    c1_before = db_manager.get_candidate_by_id(1)
    assert c1_before is not None, "Candidate #1 not found in test database"

    # Soft-delete Candidate 1 via archive_candidate()
    ok = db_manager.archive_candidate(1)
    assert ok is True, "archive_candidate(1) returned False"

    c1_after = db_manager.get_candidate_by_id(1)
    assert c1_after["archived"] == 1, f"Expected archived=1, got {c1_after['archived']}"
    assert c1_after["archived_at"] is not None and len(str(c1_after["archived_at"]).strip()) > 0, "archived_at timestamp was not set"

    # Verify all other fields are completely untouched
    preserved_fields = [
        "candidate_name", "mobile", "email", "applied_designation",
        "negotiated_salary", "contact_location", "status",
        "father_name", "date_joined", "employee_number"
    ]
    for field in preserved_fields:
        assert c1_after.get(field) == c1_before.get(field), \
            f"Field '{field}' was modified during archiving! Before: {c1_before.get(field)}, After: {c1_after.get(field)}"

    # Verify foreign key records in child tables are 100% intact
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = 1")
    assert cur.fetchone()[0] == doc_log_count, "document_generation_log records were modified!"
    cur.execute("SELECT COUNT(*) FROM email_log WHERE candidate_id = 1")
    assert cur.fetchone()[0] == email_log_count, "email_log records were modified!"
    conn.close()
    print("  ✓ Candidate #1 archived with ZERO foreign key errors; all fields & logs strictly preserved.")

    # -------------------------------------------------------------
    # TEST 3: Candidate list excludes archived candidates by default
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing get_all_candidates() default exclusion...")
    default_candidates = db_manager.get_all_candidates()
    assert not any(c["id"] == 1 for c in default_candidates), \
        "Archived candidate #1 was still returned in default get_all_candidates()!"

    # Testing with search term
    search_res = db_manager.get_all_candidates(search_term="Rohan")
    assert not any(c["id"] == 1 for c in search_res), \
        "Archived candidate #1 was returned in search results!"

    # Testing include_archived=True flag
    all_incl = db_manager.get_all_candidates(include_archived=True)
    assert any(c["id"] == 1 for c in all_incl), \
        "include_archived=True failed to return archived candidate #1!"
    print("  ✓ Archived candidate #1 correctly excluded from default list and search results.")

    # -------------------------------------------------------------
    # TEST 4: Existing un-archived candidates are unaffected
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing un-archived candidates...")
    c2 = db_manager.get_candidate_by_id(2)
    if c2:
        assert any(c["id"] == 2 for c in default_candidates), "Un-archived candidate #2 was missing from default list!"
        print(f"  ✓ Active candidate #{c2['id']} ('{c2['candidate_name']}') remains visible.")

    # -------------------------------------------------------------
    # CLEANUP: Restore Candidate 1 to active state
    # -------------------------------------------------------------
    conn = db_manager.get_connection()
    conn.execute("UPDATE candidates SET archived = 0, archived_at = NULL WHERE id = 1")
    conn.commit()
    conn.close()

    restored = db_manager.get_candidate_by_id(1)
    assert restored["archived"] == 0
    print("  ✓ Restored Candidate #1 to active state for subsequent tests.")

    print("\n" + "=" * 70)
    print("ALL ARCHIVE CANDIDATE TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
