"""
Verification Script: test_dashboard_service.py
Tests the Dashboard Backend Service (Part 3):
1. Status overview count calculations.
2. Experience certificate due list (candidates with relieving_date).
3. Increment due list:
   - Candidate joined 400 days ago -> overdue.
   - Candidate joined 340 days ago -> upcoming.
   - Candidate with relieving_date -> excluded from increment lists.
   - Candidate with recent increment log -> flagged already_issued=True.
4. Keka pending sync summary.
"""

import os
import sys
import datetime

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database import db_manager
from services import dashboard_service


def run_tests():
    print("=" * 70)
    print("PART 3 VERIFICATION: DASHBOARD BACKEND SERVICE")
    print("=" * 70)

    db_manager.init_db()
    today = datetime.date.today()

    # Set up specific test candidates
    # Candidate A: Overdue increment (joined 400 days ago, status Joined, no relieving_date)
    date_400_days_ago = (today - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
    cand_a_data = {
        "candidate_name": "Dash Candidate Overdue",
        "mobile": "9900000001",
        "applied_designation": "Field Coordinator",
        "status": "Joined",
    }
    db_manager.upsert_candidate(cand_a_data, "dash_test.xlsx")
    cand_a = db_manager.get_candidate_by_mobile("9900000001")
    db_manager.update_candidate_status(cand_a["id"], "Joined")
    db_manager.update_candidate_extra_details(
        candidate_id=cand_a["id"],
        father_name="Father A",
        full_address="Address A",
        gender="Male",
        department="Operations",
        date_joined=date_400_days_ago,
        employee_number="DFY-D01"
    )

    # Candidate B: Upcoming increment (joined 340 days ago, status Joined, no relieving_date)
    date_340_days_ago = (today - datetime.timedelta(days=340)).strftime("%Y-%m-%d")
    cand_b_data = {
        "candidate_name": "Dash Candidate Upcoming",
        "mobile": "9900000002",
        "applied_designation": "Data Entry Operator",
        "status": "Joined",
    }
    db_manager.upsert_candidate(cand_b_data, "dash_test.xlsx")
    cand_b = db_manager.get_candidate_by_mobile("9900000002")
    db_manager.update_candidate_status(cand_b["id"], "Joined")
    db_manager.update_candidate_extra_details(
        candidate_id=cand_b["id"],
        father_name="Father B",
        full_address="Address B",
        gender="Female",
        department="Health",
        date_joined=date_340_days_ago,
        employee_number="DFY-D02"
    )

    # Candidate C: Relieved candidate (has relieving_date, should appear in exp cert due list, excluded from increment)
    cand_c_data = {
        "candidate_name": "Dash Candidate Relieved",
        "mobile": "9900000003",
        "applied_designation": "Project Coordinator",
        "status": "Joined",
    }
    db_manager.upsert_candidate(cand_c_data, "dash_test.xlsx")
    cand_c = db_manager.get_candidate_by_mobile("9900000003")
    db_manager.update_candidate_status(cand_c["id"], "Joined")
    db_manager.update_candidate_extra_details(
        candidate_id=cand_c["id"],
        father_name="Father C",
        full_address="Address C",
        gender="Male",
        department="Operations",
        date_joined=date_400_days_ago,
        employee_number="DFY-D03"
    )
    db_manager.update_employee_lifecycle_data(
        mobile="9900000003",
        relieving_date=(today - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    )

    # Candidate D: Joined 400 days ago, but has an increment letter generated recently (already_issued=True)
    cand_d_data = {
        "candidate_name": "Dash Candidate Already Incremented",
        "mobile": "9900000004",
        "applied_designation": "Field Officer",
        "status": "Joined",
    }
    db_manager.upsert_candidate(cand_d_data, "dash_test.xlsx")
    cand_d = db_manager.get_candidate_by_mobile("9900000004")
    db_manager.update_candidate_status(cand_d["id"], "Joined")
    db_manager.update_candidate_extra_details(
        candidate_id=cand_d["id"],
        father_name="Father D",
        full_address="Address D",
        gender="Male",
        department="Operations",
        date_joined=date_400_days_ago,
        employee_number="DFY-D04"
    )
    # Log an increment document for D
    db_manager.log_document_generation(
        candidate_id=cand_d["id"],
        document_type="increment",
        reference_number="DFY/HR/INC/TEST",
        extra_fields_dict={},
        file_path="test_path.docx"
    )

    # 1. Test get_status_overview()
    print("\n1. Testing get_status_overview()...")
    status_overview = dashboard_service.get_status_overview()
    print(f"   Status counts: {status_overview}")
    assert "total" in status_overview, "Overview must contain 'total'"
    assert "Joined" in status_overview, "Overview must contain 'Joined'"
    assert status_overview["Joined"] >= 4, "Joined count must include test candidates"
    assert status_overview["total"] >= 4, "Total count must be valid"
    print("   ✅ Status overview verified.")

    # 2. Test get_experience_certificate_due_list()
    print("\n2. Testing get_experience_certificate_due_list()...")
    exp_due = dashboard_service.get_experience_certificate_due_list()
    print(f"   Experience cert due count: {len(exp_due)}")
    matching_c = [c for c in exp_due if c["candidate_id"] == cand_c["id"]]
    assert len(matching_c) == 1, "Candidate C (with relieving date) must be in experience cert due list"
    assert matching_c[0]["already_issued"] is False, "Candidate C has not been issued a certificate yet"
    print(f"   Found Candidate C: {matching_c[0]}")
    print("   ✅ Experience certificate due list verified.")

    # 3. Test get_increment_due_list()
    print("\n3. Testing get_increment_due_list()...")
    inc_due = dashboard_service.get_increment_due_list()
    upcoming = inc_due["upcoming"]
    overdue = inc_due["overdue"]
    print(f"   Upcoming count: {len(upcoming)}")
    print(f"   Overdue count: {len(overdue)}")

    # Check Candidate A in overdue
    match_a = [c for c in overdue if c["candidate_id"] == cand_a["id"]]
    assert len(match_a) == 1, "Candidate A (joined 400 days ago) must be in overdue list"
    assert match_a[0]["days_since_joining"] >= 400
    assert match_a[0]["already_issued"] is False
    print(f"   Found Candidate A in overdue: {match_a[0]}")

    # Check Candidate B in upcoming
    match_b = [c for c in upcoming if c["candidate_id"] == cand_b["id"]]
    assert len(match_b) == 1, "Candidate B (joined 340 days ago) must be in upcoming list"
    assert 335 <= match_b[0]["days_since_joining"] < 365
    print(f"   Found Candidate B in upcoming: {match_b[0]}")

    # Check Candidate C is EXCLUDED from increment lists (since relieving_date is set)
    all_inc_ids = [c["candidate_id"] for c in upcoming + overdue]
    assert cand_c["id"] not in all_inc_ids, "Relieved Candidate C must be excluded from increment reminders"
    print("   Candidate C is properly excluded from increment lists.")

    # Check Candidate D in overdue has already_issued=True
    match_d = [c for c in overdue if c["candidate_id"] == cand_d["id"]]
    assert len(match_d) == 1, "Candidate D must be in overdue list"
    assert match_d[0]["already_issued"] is True, "Candidate D must have already_issued=True"
    print(f"   Candidate D has already_issued=True: {match_d[0]}")
    print("   ✅ Increment due list (upcoming, overdue, exclusions, already_issued) verified.")

    # 4. Test get_keka_pending_summary()
    print("\n4. Testing get_keka_pending_summary()...")
    keka_summary = dashboard_service.get_keka_pending_summary()
    print(f"   Pending Keka sync count: {keka_summary['count']}")
    assert "count" in keka_summary
    assert "candidates" in keka_summary
    print("   ✅ Keka pending summary verified.")

    print("\n" + "=" * 70)
    print("ALL PART 3 DASHBOARD SERVICE TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
