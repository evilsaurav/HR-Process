"""
Verification Script: test_keka_sync.py
Comprehensive test suite verifying:
1. Pending Keka sync detection for 'Joined' candidates.
2. Keka sync sheet processing with fuzzy column resolution and phone normalization.
3. Strict data preservation (blank sheet values never overwrite existing database data).
4. Unmatched candidate reporting and non-insertion.
5. Excel export of unmatched candidate report using excel_export_service.
6. Post-sync pending list status.
"""

import os
import sys
import json
import pandas as pd

# Configure UTF-8 encoding for Windows console output
sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database.db_manager import (
    init_db,
    get_connection,
    get_candidate_by_mobile,
    get_candidates_pending_keka_sync
)
from services.keka_sync_service import (
    process_keka_sync_sheet,
    export_unmatched_report
)


def run_tests():
    init_db()
    test_sheet_path = os.path.join(DESKTOP_APP_DIR, "output", "test_keka_export.xlsx")
    unmatched_report_path = os.path.join(DESKTOP_APP_DIR, "output", "test_unmatched_report.xlsx")

    print("=" * 70)
    print("STEP 1: PRE-SYNC SETUP & DATA PRESERVATION PREPARATION")
    print("=" * 70)

    conn = get_connection()
    # 1. Priya Sharma: Mark as 'Joined' with NULL employee number to test pending queue
    conn.execute("""
        UPDATE candidates
        SET status = 'Joined', employee_number = NULL, relieving_date = NULL
        WHERE mobile = '9123456789'
    """)

    # 2. Test Kumar: Manually set a pre-existing relieving_date in DB.
    # The sheet has a BLANK relieving date for Test Kumar.
    # Our data-preservation rule requires that this value is PRESERVED and not wiped out!
    conn.execute("""
        UPDATE candidates
        SET employee_number = NULL, relieving_date = '31 December 2025'
        WHERE mobile = '9876543210'
    """)

    # 3. Anjali Singh: Reset employee number and relieving date
    conn.execute("""
        UPDATE candidates
        SET employee_number = NULL, relieving_date = NULL
        WHERE mobile = '9822334455'
    """)
    conn.commit()
    conn.close()

    # Verify pending candidates before sync
    pre_pending = get_candidates_pending_keka_sync()
    print(f"Candidates pending Keka sync before processing ({len(pre_pending)} found):")
    for cand in pre_pending:
        print(f"  • ID {cand['id']}: {cand['candidate_name']} ({cand['mobile']}) - Status: {cand['status']}, Emp#: {repr(cand['employee_number'])}")

    assert any(c["mobile"] == "9123456789" for c in pre_pending), "Priya Sharma must be in pre-sync pending list"

    # Verify Test Kumar's pre-sync state
    c_kumar_pre = get_candidate_by_mobile("9876543210")
    print(f"\nTest Kumar pre-sync state:")
    print(f"  • Pre-existing Relieving Date: {repr(c_kumar_pre['relieving_date'])}")
    assert c_kumar_pre["relieving_date"] == "31 December 2025"

    print("\n" + "=" * 70)
    print("STEP 2: RUNNING process_keka_sync_sheet()")
    print("=" * 70)
    print(f"Reading file: {test_sheet_path}")

    summary = process_keka_sync_sheet(test_sheet_path)
    print("\nSummary Result:")
    print(json.dumps(summary, indent=2))

    # Assertions on summary
    assert summary["success"] is True, "process_keka_sync_sheet should return success: True"
    assert summary["total_rows"] == 4, f"Expected 4 rows, got {summary['total_rows']}"
    assert summary["matched_count"] == 3, f"Expected 3 matched, got {summary['matched_count']}"
    assert summary["updated_count"] == 3, f"Expected 3 updated, got {summary['updated_count']}"
    assert len(summary["unmatched_rows"]) == 1, f"Expected 1 unmatched row, got {len(summary['unmatched_rows'])}"
    assert summary["unmatched_rows"][0]["name"] == "Rohit Deshmukh"
    assert summary["unmatched_rows"][0]["mobile"] == "9998887776"
    assert len(summary["errors"]) == 0, f"Expected 0 errors, got {len(summary['errors'])}"

    print("\n" + "=" * 70)
    print("STEP 3: VERIFYING DATABASE UPDATES & DATA PRESERVATION")
    print("=" * 70)

    # 1. Test Kumar (Active in sheet -> blank date should NOT overwrite existing date)
    c1 = get_candidate_by_mobile("9876543210")
    print("Candidate 1 (Test Kumar):")
    print(f"  • Employee Number : {c1['employee_number']} (Expected: DFY-1001)")
    print(f"  • Relieving Date   : {c1['relieving_date']} (Expected: '31 December 2025' [PRESERVED!])")
    assert c1["employee_number"] == "DFY-1001", "Employee number should be updated"
    assert c1["relieving_date"] == "31 December 2025", "Pre-existing relieving_date must NOT be overwritten with blank!"

    # 2. Priya Sharma (Resigned -> date updated)
    c2 = get_candidate_by_mobile("9123456789")
    print("\nCandidate 2 (Priya Sharma):")
    print(f"  • Employee Number : {c2['employee_number']} (Expected: DFY-1002)")
    print(f"  • Relieving Date   : {c2['relieving_date']} (Expected: 30 November 2024)")
    assert c2["employee_number"] == "DFY-1002"
    assert c2["relieving_date"] == "30 November 2024"

    # 3. Anjali Singh (Resigned -> DD/MM/YYYY date updated to long format)
    c3 = get_candidate_by_mobile("9822334455")
    print("\nCandidate 3 (Anjali Singh):")
    print(f"  • Employee Number : {c3['employee_number']} (Expected: DFY-1006)")
    print(f"  • Relieving Date   : {c3['relieving_date']} (Expected: 15 December 2024)")
    assert c3["employee_number"] == "DFY-1006"
    assert c3["relieving_date"] == "15 December 2024"

    # 4. Rohit Deshmukh (Unmatched -> NO candidate created)
    c_unmatched = get_candidate_by_mobile("9998887776")
    print("\nUnmatched Mobile (Rohit Deshmukh - 9998887776):")
    print(f"  • Exists in DB : {c_unmatched is not None} (Expected: False - no INSERT allowed)")
    assert c_unmatched is None, "Unmatched records must NEVER be inserted into database"

    print("\n" + "=" * 70)
    print("STEP 4: EXPORTING & VERIFYING UNMATCHED REPORT EXCEL FILE")
    print("=" * 70)
    out_file = export_unmatched_report(summary["unmatched_rows"], unmatched_report_path)
    print(f"Unmatched report generated at: {out_file}")
    assert os.path.exists(out_file), "Unmatched report Excel file must exist"

    # Read back generated Excel report with pandas
    report_df = pd.read_excel(out_file)
    print("\nRead-back Excel Report Content:")
    print(report_df.to_string(index=False))

    expected_cols = ["Row Number", "Mobile Number", "Candidate Name (from sheet)", "Reason"]
    for col in expected_cols:
        assert col in report_df.columns, f"Expected column '{col}' missing from report"
    assert len(report_df) == 1, "Report should contain exactly 1 unmatched row"
    assert report_df.iloc[0]["Mobile Number"] == 9998887776 or str(report_df.iloc[0]["Mobile Number"]) == "9998887776"
    assert "Rohit Deshmukh" in str(report_df.iloc[0]["Candidate Name (from sheet)"])

    print("\n" + "=" * 70)
    print("STEP 5: POST-SYNC PENDING QUEUE CHECK")
    print("=" * 70)
    post_pending = get_candidates_pending_keka_sync()
    print(f"Candidates pending Keka sync after processing ({len(post_pending)} found):")
    for cand in post_pending:
        print(f"  • ID {cand['id']}: {cand['candidate_name']} ({cand['mobile']}) - Status: {cand['status']}, Emp#: {repr(cand['employee_number'])}")

    assert not any(c["mobile"] == "9123456789" for c in post_pending), "Priya Sharma must no longer be pending"

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
