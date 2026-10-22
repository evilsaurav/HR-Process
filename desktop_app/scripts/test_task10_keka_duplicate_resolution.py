"""
Test Suite: test_task10_keka_duplicate_resolution.py
Purpose: Comprehensive verification for Task 10:
1. get_candidate_by_employee_number retrieval and sanitation.
2. Direct DB duplicate prevention in insert_keka_employee (no duplicate rows).
3. Pre-sync conflict detection (detect_keka_conflicts_and_duplicates).
4. Sheet-internal duplicate detection (same employee ID in multiple sheet rows).
5. Sheet re-upload detection flag (is_sheet_reupload >= 50% match).
6. Interactive conflict resolution behaviors: 'keep' vs 'update' strategies.
"""

import os
import sys
import pandas as pd

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database import db_manager
from services import keka_sync_service


def run_tests():
    print("=" * 70)
    print("TESTING TASK 10: KEKA DUPLICATE DETECTION & CONFLICT RESOLUTION")
    print("=" * 70)

    db_manager.init_db()

    test_emp1 = "TEST_T10_01"
    test_emp2 = "TEST_T10_02"
    test_emp3 = "TEST_T10_03"
    test_emp_keep = "TEST_T10_KEEP"
    test_emp_new = "TEST_T10_NEW"
    test_mob1 = "9811100001"
    test_mob2 = "9811100002"
    test_mob3 = "9811100003"
    test_mob_keep = "9811100004"
    test_mob_new = "9811100005"

    # Clean test records
    conn = db_manager.get_connection()
    conn.execute(
        "DELETE FROM candidates WHERE employee_number IN (?, ?, ?, ?, ?) OR mobile IN (?, ?, ?, ?, ?)",
        (test_emp1, test_emp2, test_emp3, test_emp_keep, test_emp_new,
         test_mob1, test_mob2, test_mob3, test_mob_keep, test_mob_new)
    )
    conn.commit()
    conn.close()

    output_dir = os.path.join(PROJECT_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)

    # -------------------------------------------------------------
    # Test 1: get_candidate_by_employee_number & insert_keka_employee duplicate prevention
    # -------------------------------------------------------------
    print("\n[1/5] Testing direct DB duplicate prevention & employee number lookup...")
    id1 = db_manager.insert_keka_employee({
        "employee_number": test_emp1,
        "mobile": test_mob1,
        "candidate_name": "Sanjay Verma",
        "applied_designation": "Staff Nurse",
        "department": "ICU",
        "negotiated_salary": "35000",
    }, source_sheet_name="Initial_Import.xlsx")
    assert id1 is not None, "Failed to insert initial employee"

    # Query by clean employee_number
    c1 = db_manager.get_candidate_by_employee_number(test_emp1)
    assert c1 is not None, "get_candidate_by_employee_number failed to find record"
    assert c1["id"] == id1
    assert c1["department"] == "ICU"

    # Query with float suffix '.0'
    c1_float = db_manager.get_candidate_by_employee_number(f"{test_emp1}.0")
    assert c1_float is not None and c1_float["id"] == id1, "Failed to lookup candidate with .0 float suffix"

    # Attempt second insert with same employee_number but different department
    id1_dup = db_manager.insert_keka_employee({
        "employee_number": test_emp1,
        "mobile": test_mob1,
        "candidate_name": "Sanjay Verma",
        "applied_designation": "Senior Staff Nurse",
        "department": "Critical Care Unit",
        "negotiated_salary": "45000",
    }, source_sheet_name="Second_Import.xlsx")

    # MUST return existing ID and NOT insert a duplicate row
    assert id1_dup == id1, f"Expected returned ID {id1}, got {id1_dup}"

    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM candidates WHERE employee_number = ?", (test_emp1,))
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1, f"Expected exactly 1 candidate row for employee_number, found {count}!"

    # Verify existing row was updated
    c1_updated = db_manager.get_candidate_by_id(id1)
    assert c1_updated["department"] == "Critical Care Unit"
    assert c1_updated["applied_designation"] == "Senior Staff Nurse"
    print("✓ insert_keka_employee guarantees zero duplicate rows & updates existing record correctly!")

    # -------------------------------------------------------------
    # Test 2: detect_keka_conflicts_and_duplicates (field differences & internal sheet duplicates)
    # -------------------------------------------------------------
    print("\n[2/5] Testing pre-sync conflict & sheet-internal duplicate detection...")
    headers = [
        "Employee Number", "Full Name", "Mobile Phone", "Job Title",
        "Department", "Location", "Employment Status"
    ]

    # Sheet rows:
    # Row 1: test_emp1 with different Job Title (triggers conflict)
    # Row 2: test_emp2 (new employee)
    # Row 3: test_emp2 duplicate (same employee number in multiple rows!)
    row1 = {h: "" for h in headers}
    row1["Employee Number"] = test_emp1
    row1["Full Name"] = "Sanjay Verma"
    row1["Mobile Phone"] = f"91-{test_mob1}"
    row1["Job Title"] = "ICU Supervisor"  # Differing from "Senior Staff Nurse"
    row1["Department"] = "Critical Care Unit"

    row2 = {h: "" for h in headers}
    row2["Employee Number"] = test_emp2
    row2["Full Name"] = "Pooja Sharma"
    row2["Mobile Phone"] = f"91-{test_mob2}"
    row2["Job Title"] = "Pharmacist"
    row2["Department"] = "Pharmacy"

    row3 = {h: "" for h in headers}
    row3["Employee Number"] = test_emp2  # Same employee ID!
    row3["Full Name"] = "Pooja Sharma Duplicate"
    row3["Mobile Phone"] = f"91-{test_mob2}"
    row3["Job Title"] = "Pharmacist"
    row3["Department"] = "Pharmacy"

    sheet1_path = os.path.join(output_dir, "test_t10_conflicts.xlsx")
    df1 = pd.DataFrame([row1, row2, row3])
    df1.to_excel(sheet1_path, index=False)

    det = keka_sync_service.detect_keka_conflicts_and_duplicates(sheet1_path)
    assert det["success"] is True, f"Conflict detection failed: {det.get('error')}"
    assert det["total_rows"] == 3

    # Check internal sheet duplicates
    internal_dups = det["internal_duplicates"]
    assert len(internal_dups) == 1, f"Expected 1 internal duplicate group, found {len(internal_dups)}"
    assert internal_dups[0]["employee_number"] == test_emp2
    assert internal_dups[0]["count"] == 2

    # Check conflicting employees
    conflicts = det["conflicting_employees"]
    assert len(conflicts) == 1, f"Expected 1 conflicting employee, found {len(conflicts)}"
    assert conflicts[0]["employee_number"] == test_emp1
    assert "applied_designation" in conflicts[0]["changed_fields"]
    assert conflicts[0]["changed_fields"]["applied_designation"]["old"] == "Senior Staff Nurse"
    assert conflicts[0]["changed_fields"]["applied_designation"]["new"] == "ICU Supervisor"
    print("✓ Conflicts and internal sheet duplicates detected with precision!")

    # -------------------------------------------------------------
    # Test 3: is_sheet_reupload detection flag
    # -------------------------------------------------------------
    print("\n[3/5] Testing sheet re-upload threshold flag (>= 50% match)...")
    # In sheet1: 1 of 3 rows matched test_emp1 (1/3 = 33% < 50%)
    assert det["is_sheet_reupload"] is False, "Expected False for 33% match"

    # Now create sheet with 2 rows where both match existing candidates
    db_manager.insert_keka_employee({
        "employee_number": test_emp3,
        "mobile": test_mob3,
        "candidate_name": "Ramesh Patel",
    }, source_sheet_name="Test.xlsx")

    row_re1 = {h: "" for h in headers}
    row_re1["Employee Number"] = test_emp1
    row_re1["Mobile Phone"] = test_mob1
    row_re1["Full Name"] = "Sanjay Verma"

    row_re2 = {h: "" for h in headers}
    row_re2["Employee Number"] = test_emp3
    row_re2["Mobile Phone"] = test_mob3
    row_re2["Full Name"] = "Ramesh Patel"

    sheet_reupload_path = os.path.join(output_dir, "test_t10_reupload.xlsx")
    pd.DataFrame([row_re1, row_re2]).to_excel(sheet_reupload_path, index=False)

    det_reupload = keka_sync_service.detect_keka_conflicts_and_duplicates(sheet_reupload_path)
    assert det_reupload["is_sheet_reupload"] is True, "Expected True when 100% of rows match existing candidates"
    print("✓ is_sheet_reupload flag accurately triggers when >= 50% rows match existing employees!")

    # -------------------------------------------------------------
    # Test 4: Conflict Resolution 'Keep' Strategy
    # -------------------------------------------------------------
    print("\n[4/5] Testing resolution strategy 'keep' (preserves current DB record)...")
    id_keep = db_manager.insert_keka_employee({
        "employee_number": test_emp_keep,
        "mobile": test_mob_keep,
        "candidate_name": "Anita Roy",
        "applied_designation": "Medical Officer",
        "department": "Pediatrics",
        "negotiated_salary": "75000",
    }, source_sheet_name="Keep_Test.xlsx")

    # Incoming sheet proposes to change department to "Emergency" and salary to "90000"
    row_keep = {h: "" for h in headers}
    row_keep["Employee Number"] = test_emp_keep
    row_keep["Mobile Phone"] = test_mob_keep
    row_keep["Full Name"] = "Anita Roy"
    row_keep["Job Title"] = "Senior Medical Officer"
    row_keep["Department"] = "Emergency"

    row_new = {h: "" for h in headers}
    row_new["Employee Number"] = test_emp_new
    row_new["Mobile Phone"] = test_mob_new
    row_new["Full Name"] = "Gaurav Singh"
    row_new["Job Title"] = "Lab Technician"
    row_new["Department"] = "Diagnostics"

    sheet_res_path = os.path.join(output_dir, "test_t10_resolution.xlsx")
    pd.DataFrame([row_keep, row_new]).to_excel(sheet_res_path, index=False)

    # Execute with default_action='keep'
    res_keep = keka_sync_service.sync_rich_keka_sheet_with_resolutions(
        file_path=sheet_res_path,
        resolutions={test_emp_keep: "keep"},
        default_action="keep",
        allow_new_inserts=True
    )

    assert res_keep["success"] is True
    assert res_keep["kept_count"] == 1, f"Expected kept_count=1, got {res_keep['kept_count']}"
    assert res_keep["updated_count"] == 0, f"Expected updated_count=0, got {res_keep['updated_count']}"
    assert res_keep["inserted_count"] == 1, f"Expected inserted_count=1, got {res_keep['inserted_count']}"

    # Verify DB was NOT overwritten for test_emp_keep
    cand_kept = db_manager.get_candidate_by_id(id_keep)
    assert cand_kept["department"] == "Pediatrics", f"DB overwritten! Found {cand_kept['department']}"
    assert cand_kept["applied_designation"] == "Medical Officer"
    assert cand_kept["negotiated_salary"] == "75000"

    # Verify new employee was still inserted
    cand_new = db_manager.get_candidate_by_employee_number(test_emp_new)
    assert cand_new is not None, "New employee was not imported"
    assert cand_new["status"] == "Joined"
    print("✓ 'Keep' strategy preserved existing DB records completely while importing new staff!")

    # -------------------------------------------------------------
    # Test 5: Conflict Resolution 'Update' Strategy
    # -------------------------------------------------------------
    print("\n[5/5] Testing resolution strategy 'update' (applies incoming sheet data)...")
    res_update = keka_sync_service.sync_rich_keka_sheet_with_resolutions(
        file_path=sheet_res_path,
        resolutions={test_emp_keep: "update"},
        default_action="update",
        allow_new_inserts=True
    )

    assert res_update["success"] is True
    # In Test 4, test_emp_new was already inserted.
    # Therefore in Test 5, test_emp_keep is updated and test_emp_new is matched without duplicate insertion!
    assert res_update["matched_count"] == 2, f"Expected matched_count=2, got {res_update['matched_count']}"
    assert res_update["updated_count"] == 2, f"Expected updated_count=2, got {res_update['updated_count']}"
    assert res_update["inserted_count"] == 0, f"Expected inserted_count=0 (no duplicate rows), got {res_update['inserted_count']}"
    assert res_update["kept_count"] == 0

    # Verify DB candidate was updated with incoming sheet data
    cand_updated = db_manager.get_candidate_by_id(id_keep)
    assert cand_updated["department"] == "Emergency", f"Expected 'Emergency', got {cand_updated['department']}"
    assert cand_updated["applied_designation"] == "Senior Medical Officer"

    # Verify total candidate count for test_emp_keep is STILL strictly 1
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM candidates WHERE employee_number = ?", (test_emp_keep,))
    total_keep_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM candidates WHERE employee_number = ?", (test_emp_new,))
    total_new_count = cur.fetchone()[0]
    conn.close()
    assert total_keep_count == 1, f"Duplicate candidates created for {test_emp_keep}! Found {total_keep_count}"
    assert total_new_count == 1, f"Duplicate candidates created for {test_emp_new}! Found {total_new_count}"
    print("✓ 'Update' strategy updated the existing candidate without creating duplicates!")

    # Cleanup temp files and test rows
    for p in [sheet1_path, sheet_reupload_path, sheet_res_path]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    conn = db_manager.get_connection()
    conn.execute(
        "DELETE FROM candidates WHERE employee_number IN (?, ?, ?, ?, ?) OR mobile IN (?, ?, ?, ?, ?)",
        (test_emp1, test_emp2, test_emp3, test_emp_keep, test_emp_new,
         test_mob1, test_mob2, test_mob3, test_mob_keep, test_mob_new)
    )
    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("ALL TASK 10 TESTS PASSED! ZERO DUPLICATES GUARANTEED! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
