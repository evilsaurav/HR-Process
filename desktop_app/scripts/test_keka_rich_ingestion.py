"""
Verification Script: test_keka_rich_ingestion.py
Task 2 Test Suite: Rich Keka Sheet Ingestion & Smart Auto-Mapper.
"""

import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database import db_manager
from services.keka_sync_service import process_rich_keka_sheet


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 2 TESTS: RICH KEKA INGESTION & AUTO-MAPPER")
    print("=" * 70)

    db_manager.init_db()

    mob_match = "9111122222"
    mob_new = "9111133333"

    # Clean up test rows
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?)", (mob_match, mob_new))
    conn.commit()
    conn.close()

    temp_sheet = os.path.join(DESKTOP_APP_DIR, "output", "temp_keka_test.xlsx")
    os.makedirs(os.path.dirname(temp_sheet), exist_ok=True)

    try:
        # Pre-seed existing candidate to test update & preservation
        db_manager.upsert_candidate({
            "candidate_name": "Shailesh Initial",
            "mobile": mob_match,
            "email": "shailesh.old@example.com",
            "applied_designation": "Old Role",
            "contact_location": "Buxar",
        }, "Initial Candidate Sheet")

        # Create rich Keka sheet dataframe matching user's exact specification
        keka_data = [
            {
                "Employee Number": "EP00021",
                "First Name": "Shailesh",
                "Last Name": "Dubey",
                "Display Name": "Shailesh Dubey",
                "Work Email": "shaileshdubey9211420@gmail.com",
                "Personal Email": "shailesh.pvt@example.com",
                "Mobile Phone": mob_match,
                "Date Of Birth": "1995-05-12",
                "Gender": "Male",
                "Marital Status": "Married",
                "Current Address": "Flat 201, Buxar, Bihar",
                "Permanent Address": "Vill Pipra, Buxar, Bihar",
                "Father Name": "Ramesh Dubey",
                "Department": "DFY - PPSA Bihar Project",
                "Job Title": "Community Health Resource",
                "Reporting To": "Pankaj Kumar",
                "Reporting Manager Employee Number": "EP00041",
                "Date Joined": "2022-07-15",
                "Employment Status": "Working",
                "Worker Type": "Contract",
                "Time Type": "FullTime",
                "Leave Plan": "Standard Leave Plan",
                "Shift Policy Name": "9-5 Shift",
                "Attendance Time Tracking & Weekly Off Policy": "Standard Weekly Off",
                "Notice Period": "30 Days",
                "PAN Number": "ABCDE1234F",
                "Aadhaar Number": "123456789012",
                "PF Number": "MH/BAN/12345",
                "UAN Number": "100123456789",
                "Cost Center": "PPSA-Accounts",
            },
            {
                "Employee Number": "EP00022",
                "First Name": "Pooja",
                "Last Name": "Kumari",
                "Display Name": "Pooja Kumari",
                "Work Email": "pooja.k@dfy.org",
                "Mobile Phone": mob_new,
                "Department": "DFY - Health Care",
                "Job Title": "Staff Nurse",
                "Date Joined": "2023-01-10",
                "PAN Number": "PQRSX9876Z",
                "Aadhaar Number": "987654321098",
            }
        ]

        df = pd.DataFrame(keka_data)
        df.to_excel(temp_sheet, index=False)
        print(f"Created temporary Keka export test sheet: {temp_sheet}")

        # Process the rich Keka sheet
        result = process_rich_keka_sheet(temp_sheet, allow_new_inserts=True)
        assert result["success"] is True, f"Processing failed: {result.get('error')}"
        assert result["total_rows"] == 2, f"Expected 2 rows, got {result['total_rows']}"
        assert result["matched_count"] == 1, f"Expected 1 matched row, got {result['matched_count']}"
        assert result["inserted_count"] == 1, f"Expected 1 newly inserted employee, got {result['inserted_count']}"

        print("  ✓ Matched existing employee count verified (1).")
        print("  ✓ Inserted new onboarded employee count verified (1).")

        # Verify DB state of updated candidate
        cand1 = db_manager.get_candidate_by_mobile(mob_match)
        assert cand1["employee_number"] == "EP00021"
        assert cand1["pan_number"] == "ABCDE1234F"
        assert cand1["department"] == "DFY - PPSA Bihar Project"
        assert cand1["job_title"] == "Community Health Resource"
        assert cand1["father_name"] == "Ramesh Dubey"
        assert cand1["reporting_to"] == "Pankaj Kumar"
        print("cand1 uan_number:", cand1.get("uan_number"))
        assert cand1["uan_number"] == "100123456789"
        print("  ✓ Existing candidate fields successfully updated with full Keka master data.")

        # Verify DB state of newly inserted employee
        cand2 = db_manager.get_candidate_by_mobile(mob_new)
        assert cand2 is not None, "Newly inserted employee not found in database!"
        assert cand2["employee_number"] == "EP00022"
        assert cand2["pan_number"] == "PQRSX9876Z"
        assert cand2["status"] == "Joined", f"New employee status should be 'Joined', got {cand2['status']}"
        print("  ✓ Newly onboarded employee successfully created with full profile and status 'Joined'.")

        print("=" * 70)
        print("ALL TASK 2 TESTS PASSED SUCCESSFULLY! ✅")
        print("=" * 70)

    finally:
        # Cleanup
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?)", (mob_match, mob_new))
        conn.commit()
        conn.close()
        if os.path.exists(temp_sheet):
            os.remove(temp_sheet)


if __name__ == "__main__":
    run_tests()
