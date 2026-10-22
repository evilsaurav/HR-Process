"""
Unit Test: test_candidate_tags_and_batch_db.py
Verifies database enhancements:
1. Safe idempotent migration of 'tag' column on 'candidates' table.
2. Candidate tag updates and querying by tag.
3. Upcoming joinees filter (next N days).
4. Distinct source sheets retrieval for batch navigation.
"""

import os
import sys
import datetime
import tempfile
import shutil

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from database import db_manager


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 4 TESTS: CANDIDATE TAGS & DATABASE ENHANCEMENTS")
    print("=" * 70)

    # Use isolated temporary database for test
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_tags.db")
    orig_db = db_manager.DB_PATH
    db_manager.DB_PATH = test_db

    try:
        print("\n[TEST 1] Initializing DB and testing migration...")
        db_manager.init_db()

        # Check 'tag' column exists
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(candidates)")
        cols = {row[1] for row in cur.fetchall()}
        conn.close()

        assert "tag" in cols, "'tag' column was not created in candidates table"
        print("  ✓ 'tag' column present in candidates schema.")

        # 2. Insert test candidates
        print("\n[TEST 2] Inserting candidates and testing tag updates...")
        c1_id = db_manager.insert_candidate({
            "candidate_name": "Pooja Verma",
            "mobile": "9998887771",
            "email": "pooja@example.com",
            "applied_designation": "Lab Technician",
            "status": "Selected",
            "department": "PPSA UP",
            "source_sheet_name": "PPSA UP",
            "date_joined": (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
        })

        c2_id = db_manager.insert_candidate({
            "candidate_name": "Aman Singh",
            "mobile": "9998887772",
            "email": "aman@example.com",
            "applied_designation": "Field Coordinator",
            "status": "Interview",
            "department": "PPSA Bihar",
            "source_sheet_name": "PPSA Bihar",
            "date_joined": (datetime.datetime.now() + datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
        })

        # Update tags
        ok1 = db_manager.update_candidate_tag(c1_id, "Immediate Joiner")
        ok2 = db_manager.update_candidate_tag(c2_id, "On Hold")
        assert ok1 is True and ok2 is True, "Failed to update candidate tags"

        # Fetch candidate to verify tag persistence
        c1 = db_manager.get_candidate_by_id(c1_id)
        assert c1.get("tag") == "Immediate Joiner"
        c2 = db_manager.get_candidate_by_id(c2_id)
        assert c2.get("tag") == "On Hold"
        print(f"  ✓ Tag persistence verified: C1={c1.get('tag')}, C2={c2.get('tag')}")

        # Fetch by tag
        immediate_list = db_manager.get_candidates_by_tag("Immediate Joiner")
        assert len(immediate_list) == 1
        assert immediate_list[0]["candidate_name"] == "Pooja Verma"
        print("  ✓ get_candidates_by_tag('Immediate Joiner') returned exactly 1 candidate.")

        # 3. Test upcoming joinees (within next 7 days)
        print("\n[TEST 3] Testing get_upcoming_joinees(days=7)...")
        upcoming = db_manager.get_upcoming_joinees(days=7)
        assert len(upcoming) == 1, f"Expected 1 joinee in next 7 days, got {len(upcoming)}"
        assert upcoming[0]["candidate_name"] == "Pooja Verma"
        print(f"  ✓ Upcoming joinee verified: {upcoming[0]['candidate_name']} (joining in ~3 days)")

        # 4. Test distinct source sheets
        print("\n[TEST 4] Testing get_distinct_source_sheets()...")
        sheets = db_manager.get_distinct_source_sheets()
        assert "PPSA UP" in sheets
        assert "PPSA Bihar" in sheets
        print(f"  ✓ Distinct sheets returned: {sheets}")

    finally:
        db_manager.DB_PATH = orig_db
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("ALL TASK 4 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
