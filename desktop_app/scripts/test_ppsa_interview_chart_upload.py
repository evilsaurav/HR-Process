"""
Test script to verify extraction, auto-detection, multi-sheet handling,
and database ingestion for 'PPSA INTERVIEW CHART.xlsx'.
"""
import os
import sys
import tempfile
import shutil

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services.sheet_processor import (
    extract_candidate_rows_from_sheet,
    detect_duplicates,
    apply_joining_decisions,
)
from database import db_manager

TARGET_EXCEL = r"C:\Users\Saurav\Downloads\PPSA INTERVIEW CHART.xlsx"

def run_test():
    print(f"=== Testing PPSA Interview Chart Ingestion ===")
    print(f"Target Excel File: {TARGET_EXCEL}")

    if not os.path.exists(TARGET_EXCEL):
        print(f"ERROR: Target file does not exist at {TARGET_EXCEL}")
        sys.exit(1)

    # 1. Test Multi-Sheet Extraction & Auto-Detection
    print("\n--- Step 1: Extracting from all sheets ---")
    extracted = extract_candidate_rows_from_sheet(TARGET_EXCEL)

    assert extracted["success"] is True, f"Extraction failed: {extracted.get('error')}"
    rows = extracted["valid_rows"]
    sheets = extracted["sheets_processed"]
    total = extracted["total_sheet_rows"]

    print(f"Successfully processed sheets: {sheets}")
    print(f"Total candidate rows extracted: {total}")

    assert "PPSA UP" in sheets, "PPSA UP sheet not processed!"
    assert "PPSA Bihar" in sheets, "PPSA Bihar sheet not processed!"
    assert "PPSA Maharashtra" in sheets, "PPSA Maharashtra sheet not processed!"
    assert total == 44, f"Expected 44 candidates across all sheets, got {total}"

    # Verify data cleaning and normalization
    up_count = sum(1 for r in rows if r["department"] == "PPSA UP")
    bihar_count = sum(1 for r in rows if r["department"] == "PPSA Bihar")
    maha_count = sum(1 for r in rows if r["department"] == "PPSA Maharashtra")

    print(f"Sheet counts -> UP: {up_count}, Bihar: {bihar_count}, Maharashtra: {maha_count}")
    assert up_count == 11, f"Expected 11 candidates in PPSA UP, got {up_count}"
    assert bihar_count == 14, f"Expected 14 candidates in PPSA Bihar, got {bihar_count}"
    assert maha_count == 19, f"Expected 19 candidates in PPSA Maharashtra, got {maha_count}"

    for i, r in enumerate(rows):
        mob = r["mobile"]
        sal = r["negotiated_salary"]
        name = r["candidate_name"]

        # Assert no '.0' suffixes in mobile
        assert not mob.endswith(".0"), f"Mobile has '.0' suffix: {mob} (candidate: {name})"
        # Assert clean 10-digit mobile if present
        if mob:
            assert len(mob) == 10 and mob.isdigit(), f"Invalid mobile format: {mob} for {name}"
        # Assert no placeholder text
        for k, v in r.items():
            if isinstance(v, str):
                assert "not in source" not in v.lower(), f"Placeholder '{v}' leaked in {k} for {name}"
                assert "not mentioned in source" not in v.lower(), f"Placeholder '{v}' leaked in {k} for {name}"

    print("Data normalization checks passed: 0 float .0 leaks, 0 placeholder leaks, all mobiles clean.")

    # 2. Test Ingestion into an Isolated Test DB
    print("\n--- Step 2: Ingesting into Isolated Database ---")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_ppsa.db")

    # Patch DB path
    orig_db_path = db_manager.DB_PATH
    db_manager.DB_PATH = test_db
    db_manager.init_db()

    try:
        dup_result = detect_duplicates(rows)
        print(f"Initial upload duplicate check: {dup_result['duplicate_count']} duplicates, {dup_result['new_count']} new")
        assert dup_result["duplicate_count"] == 0, "Expected 0 duplicates on empty database"
        assert dup_result["new_count"] == 44, f"Expected 44 new rows, got {dup_result['new_count']}"

        ingest_res = apply_joining_decisions(
            duplicates=dup_result["duplicates"],
            new_rows=dup_result["new_rows"],
            source_sheet_name="PPSA INTERVIEW CHART.xlsx"
        )
        assert ingest_res["success"] is True, f"Ingestion errors: {ingest_res['errors']}"
        assert ingest_res["added_count"] == 44, f"Expected 44 added, got {ingest_res['added_count']}"

        # Verify DB records
        all_cands = db_manager.get_all_candidates()
        print(f"Total unique candidates in DB: {len(all_cands)}")
        assert len(all_cands) == 43, f"Expected 43 unique candidates in DB (1 repeated interview merged), got {len(all_cands)}"

        dept_counts = {}
        for c in all_cands:
            dept = c.get("department")
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        print(f"Database departments: {dept_counts}")
        assert dept_counts.get("PPSA UP") == 11
        assert dept_counts.get("PPSA Bihar") == 14
        assert dept_counts.get("PPSA Maharashtra") == 18

        # Verify repeated interview candidate merged properly
        vaidya = next((c for c in all_cands if "Vaidya" in c["candidate_name"]), None)
        assert vaidya is not None, "Vaidya Yash Namdev not found in DB"
        assert vaidya["negotiated_salary"] == "15000", f"Expected merged salary 15000, got {vaidya['negotiated_salary']}"
        assert vaidya["contact_location"] == "Palghar", f"Expected merged location Palghar, got {vaidya['contact_location']}"
        print(f"Verified merged candidate: {vaidya['candidate_name']} -> Salary: {vaidya['negotiated_salary']}, Location: {vaidya['contact_location']}")

        # 3. Test Re-upload Duplicate Detection
        print("\n--- Step 3: Testing Duplicate Detection on Re-Upload ---")
        reupload_dup = detect_duplicates(rows)
        print(f"Re-upload check: {reupload_dup['duplicate_count']} duplicates detected out of {reupload_dup['total_rows']}")
        assert reupload_dup["duplicate_count"] == 44, f"Expected 44 duplicates on re-upload, got {reupload_dup['duplicate_count']}"
        assert reupload_dup["new_count"] == 0, f"Expected 0 new rows on re-upload, got {reupload_dup['new_count']}"

        print("Re-upload duplicate detection passed with 100% precision.")

    finally:
        db_manager.DB_PATH = orig_db_path
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\nALL PPSA INTERVIEW CHART TESTS PASSED SUCCESSFULLY! (100% PASS)")

if __name__ == "__main__":
    run_test()
