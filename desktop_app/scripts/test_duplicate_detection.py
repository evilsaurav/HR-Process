"""
Verification Script: test_duplicate_detection.py
Step 1 TDD Test Suite for Duplicate Candidate Detection in Joining Process.

Tests:
1. Exact mobile number matching against existing candidates.
2. Exact name matching with a different mobile number.
3. Fuzzy near-match in candidate name (e.g. spelling/typo variants like Mitlesh vs Mithlesh).
4. Genuinely new candidate detection (no match on mobile or name).
5. Accurate math for total rows, duplicate count, new count, and duplicate percentage.
6. Scenario threshold checks (Scenario A <= 50% vs Scenario B > 50%).
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

from services.sheet_processor import (
    detect_duplicates,
    compute_name_similarity,
    normalize_name_for_comparison,
)


def run_tests():
    print("=" * 70)
    print("RUNNING STEP 1 TESTS: DUPLICATE DETECTION LOGIC")
    print("=" * 70)

    # 1. Existing candidate database fixtures (mocked for fast isolated testing)
    existing_candidates = [
        {
            "id": 1,
            "candidate_name": "Mithlesh Kumar",
            "mobile": "9471804845",
            "email": "mithlesh@example.com",
            "applied_designation": "District Coordinator",
            "negotiated_salary": "30000",
            "contact_location": "Patna",
            "status": "Applied",
        },
        {
            "id": 2,
            "candidate_name": "Pooja Kumari",
            "mobile": "9876543210",
            "email": "pooja@example.com",
            "applied_designation": "Lab Technician",
            "negotiated_salary": "25000",
            "contact_location": "Gaya",
            "status": "Shortlisted",
        },
        {
            "id": 3,
            "candidate_name": "Ramesh Kumar Singh",
            "mobile": "9123456789",
            "email": "ramesh@example.com",
            "applied_designation": "MIS Executive",
            "negotiated_salary": "28000",
            "contact_location": "Ranchi",
            "status": "Joined",
        },
    ]

    # 2. Test name similarity helper
    print("\n[TEST 1] Testing name normalization & similarity calculation...")
    sim_identical = compute_name_similarity("Mithlesh Kumar", "Mithlesh  Kumar")
    assert sim_identical == 1.0, f"Expected 1.0, got {sim_identical}"

    sim_typo = compute_name_similarity("Mithlesh Kumar", "Mitlesh Kumar")
    assert sim_typo >= 0.85, f"Expected >= 0.85 for Mithlesh vs Mitlesh typo, got {sim_typo}"

    sim_diff = compute_name_similarity("Rahul Sharma", "Rahul Verma")
    assert sim_diff < 0.85, f"Expected < 0.85 for Rahul Sharma vs Rahul Verma, got {sim_diff}"
    print(f"  ✓ Exact: {sim_identical:.2f}, Typo: {sim_typo:.3f}, Different: {sim_diff:.3f}")

    # 3. Simulate an uploaded batch of candidates (5 rows total)
    uploaded_rows_batch1 = [
        # Match (a): Exact mobile number match
        {
            "candidate_name": "Mithlesh Kumar",
            "mobile": "9471804845",
            "email": "mithlesh.new@example.com",
            "applied_designation": "Senior DC",
            "negotiated_salary": "35000",
            "contact_location": "Patna",
        },
        # Match (b): Exact name match, different mobile
        {
            "candidate_name": "Pooja Kumari",
            "mobile": "9998887776",
            "email": "pooja.new@example.com",
            "applied_designation": "Senior Lab Tech",
            "negotiated_salary": "28000",
            "contact_location": "Gaya",
        },
        # Match (c): Fuzzy near-match in name ("Mitlesh Kumar"), different mobile
        {
            "candidate_name": "Mitlesh Kumar",
            "mobile": "8887776665",
            "email": "mitlesh@example.com",
            "applied_designation": "DC",
            "negotiated_salary": "32000",
            "contact_location": "Patna",
        },
        # Genuinely new candidate 1
        {
            "candidate_name": "Anita Verma",
            "mobile": "7776665554",
            "email": "anita@example.com",
            "applied_designation": "Staff Nurse",
            "negotiated_salary": "22000",
            "contact_location": "Muzaffarpur",
        },
        # Genuinely new candidate 2
        {
            "candidate_name": "Vikram Sethi",
            "mobile": "6665554443",
            "email": "vikram@example.com",
            "applied_designation": "Accountant",
            "negotiated_salary": "26000",
            "contact_location": "Patna",
        },
    ]

    print("\n[TEST 2] Testing detect_duplicates with mixed batch (5 rows: 3 duplicates, 2 new)...")
    result = detect_duplicates(uploaded_rows_batch1, existing_candidates=existing_candidates, fuzzy_threshold=0.85)

    assert result["total_rows"] == 5, f"Expected total_rows=5, got {result['total_rows']}"
    assert result["duplicate_count"] == 3, f"Expected duplicate_count=3, got {result['duplicate_count']}"
    assert result["new_count"] == 2, f"Expected new_count=2, got {result['new_count']}"
    assert result["duplicate_percentage"] == 60.0, f"Expected duplicate_percentage=60.0, got {result['duplicate_percentage']}"

    # Verify duplicate classifications
    dups = result["duplicates"]
    assert len(dups) == 3

    # Check match 1 (Mobile match)
    m1 = dups[0]
    assert m1["match_type"] == "mobile", f"Expected match_type='mobile', got {m1['match_type']}"
    assert m1["existing_record"]["id"] == 1
    assert m1["uploaded_row"]["mobile"] == "9471804845"
    print(f"  ✓ Row 1 detected as mobile match: {m1['match_reason']}")

    # Check match 2 (Exact name match with different mobile)
    m2 = dups[1]
    assert m2["match_type"] == "name", f"Expected match_type='name', got {m2['match_type']}"
    assert m2["existing_record"]["id"] == 2
    assert m2["similarity"] == 1.0
    print(f"  ✓ Row 2 detected as exact name match: {m2['match_reason']}")

    # Check match 3 (Fuzzy name match)
    m3 = dups[2]
    assert m3["match_type"] == "name", f"Expected match_type='name', got {m3['match_type']}"
    assert m3["existing_record"]["id"] == 1
    assert m3["similarity"] >= 0.85
    print(f"  ✓ Row 3 detected as fuzzy name match ({m3['similarity']:.3f}): {m3['match_reason']}")

    # Check genuinely new rows
    new_rows = result["new_rows"]
    assert len(new_rows) == 2
    assert new_rows[0]["candidate_name"] == "Anita Verma"
    assert new_rows[1]["candidate_name"] == "Vikram Sethi"
    print("  ✓ Genuinely new candidates identified: Anita Verma, Vikram Sethi")

    # 4. Test Scenario A threshold (<= 50% duplicates)
    print("\n[TEST 3] Testing Scenario A threshold (1 duplicate out of 4 rows = 25%)...")
    uploaded_rows_batch2 = [
        uploaded_rows_batch1[0], # Mithlesh (duplicate)
        uploaded_rows_batch1[3], # Anita (new)
        uploaded_rows_batch1[4], # Vikram (new)
        {
            "candidate_name": "Suresh Patel",
            "mobile": "5554443332",
            "email": "suresh@example.com",
            "applied_designation": "Hub Agent",
            "negotiated_salary": "20000",
            "contact_location": "Darbhanga",
        },
    ]
    result2 = detect_duplicates(uploaded_rows_batch2, existing_candidates=existing_candidates)
    assert result2["total_rows"] == 4
    assert result2["duplicate_count"] == 1
    assert result2["new_count"] == 3
    assert result2["duplicate_percentage"] == 25.0
    print(f"  ✓ Batch 2 duplicate percentage: {result2['duplicate_percentage']}% (<= 50% -> Scenario A)")

    print("\n" + "=" * 70)
    print("ALL STEP 1 TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
