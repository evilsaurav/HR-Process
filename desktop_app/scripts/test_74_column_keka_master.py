"""
Test Suite: test_74_column_keka_master.py
Verifies parsing and ingestion of 74-column Keka Master Sheets with:
- Top banner metadata (Row 0: Company, Row 1: Report Title)
- Header at Row 2 (Employee Number, First Name, Middle Name, ...)
- Detailed multi-line address composition (Line 1, Line 2, City, State, Zip)
- Full Option C ingestion (Update existing pipeline staff + import new employees)
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


def run_test():
    print("=" * 70)
    print("TESTING 74-COLUMN KEKA MASTER INGESTION & HEADER OFFSET AUTO-DETECTION")
    print("=" * 70)

    db_manager.init_db()

    test_mobile_exist = "9800112233"
    test_mobile_new = "9800445566"
    test_emp_exist = "TEST_EP991"
    test_emp_new = "TEST_EP992"

    # Clean existing
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile IN (?, ?) OR employee_number IN (?, ?)", 
                 (test_mobile_exist, test_mobile_new, test_emp_exist, test_emp_new))
    conn.commit()
    conn.close()

    # Create candidate in pipeline
    db_manager.upsert_candidate({
        "candidate_name": "Shailesh Kumar",
        "mobile": test_mobile_exist,
        "email": "shailesh.pipeline@dfy.org",
        "applied_designation": "Community Health Resource",
    }, source_sheet_name="Pipeline.xlsx")
    c_exist = db_manager.get_candidate_by_mobile(test_mobile_exist)
    exist_id = c_exist["id"]
    db_manager.update_candidate_status(exist_id, "Joined")

    # Build 74-column DataFrame matching real Keka portal export
    headers = [
        "Employee Number", "First Name", "Middle Name", "Last Name", "Display Name", "Full Name",
        "Work Email", "Date Of Birth", "Gender", "Marital Status", "Marriage Date", "Blood Group",
        "Physically Handicapped", "Nationality", "Mobile Phone", "Work Phone", "Home Phone", "Personal Email",
        "Current Address Line 1", "Current Address Line 2", "Current Address City", "Current Address State",
        "Current Address Zip", "Current Address Country", "Permanent Address Line 1", "Permanent Address Line 2",
        "Permanent Address City", "Permanent Address State", "Permanent Address Zip", "Permanent Address Country",
        "Father Name", "Mother Name", "Spouse Name", "Children Names", "Attendance Number", "Location",
        "Location Country", "Legal Entity", "Business Unit", "Department", "Sub Department", "Job Title",
        "Secondary Job Title", "Reporting To", "Reporting Manager Employee Number", "Dotted Line Manager",
        "Date Joined", "Leave Plan", "Band", "Pay Grade", "Time Type", "Worker Type", "Shift Policy Name",
        "Weekly Off Policy Name", "Attendance Time Tracking Policy", "Attendance Capture Scheme", "Holiday List Name",
        "Expense Policy Name", "Notice Period", "PAN Number", "Aadhaar Number", "PF Number", "UAN Number",
        "Employment Status", "Exit Date", "Comments", "Exit Status", "Termination Type", "Termination Reason",
        "Resignation Note", "Cost Center", "Extension of Service Till (IN)", "Extension of Service Months (IN)",
        "Project Test"
    ]

    row_exist = {h: "" for h in headers}
    row_exist["Employee Number"] = test_emp_exist
    row_exist["First Name"] = "Shailesh"
    row_exist["Last Name"] = "Kumar"
    row_exist["Display Name"] = "Shailesh Kumar"
    row_exist["Full Name"] = "Shailesh Kumar"
    row_exist["Mobile Phone"] = f"91-{test_mobile_exist}"
    row_exist["Work Email"] = "shaileshdubey9211420@gmail.com"
    row_exist["Date Of Birth"] = "1999-08-25 00:00:00"
    row_exist["Gender"] = "Male"
    row_exist["Blood Group"] = "B+"
    row_exist["Current Address Line 1"] = "Vill:- Dhawan"
    row_exist["Current Address Line 2"] = "PO:- Durgadih"
    row_exist["Current Address City"] = "PS:- Bikramganj"
    row_exist["Current Address State"] = "Bihar"
    row_exist["Current Address Zip"] = 802212.0
    row_exist["Department"] = "DFY - PPSA Bihar Project"
    row_exist["Job Title"] = "Community Health Resource"
    row_exist["PAN Number"] = "ABCDE1234F"
    row_exist["UAN Number"] = 100123456789.0

    row_new = {h: "" for h in headers}
    row_new["Employee Number"] = test_emp_new
    row_new["First Name"] = "Gunjan"
    row_new["Last Name"] = "Kumar"
    row_new["Display Name"] = "Gunjan Kumar"
    row_new["Full Name"] = "Gunjan Kumar"
    row_new["Mobile Phone"] = f"91-{test_mobile_new}"
    row_new["Department"] = "DFY - Telehealth"
    row_new["Job Title"] = "Health Officer"
    row_new["Legal Entity"] = "Doctors For You"

    # Write Excel with Row 0 = Company Banner, Row 1 = Report Title, Row 2 = Header
    test_file_path = os.path.join(PROJECT_DIR, "output", "test_74_col_keka_banner.xlsx")
    with pd.ExcelWriter(test_file_path, engine="openpyxl") as writer:
        meta_df = pd.DataFrame([["Doctors for you"], ["All Employees Master Data"]])
        meta_df.to_excel(writer, sheet_name="Master", header=False, index=False, startrow=0)
        data_df = pd.DataFrame([row_exist, row_new])
        data_df.to_excel(writer, sheet_name="Master", header=True, index=False, startrow=2)

    # Ingest using process_rich_keka_sheet
    res = keka_sync_service.process_rich_keka_sheet(test_file_path, allow_new_inserts=True)
    assert res["success"] is True, f"Ingestion failed: {res.get('error')}"
    assert res["total_rows"] == 2
    assert res["matched_count"] == 1
    assert res["updated_count"] == 1
    assert res["inserted_count"] == 1
    assert len(res["detected_fields"]) >= 40

    # Verify updated candidate
    updated = db_manager.get_candidate_by_id(exist_id)
    assert updated["employee_number"] == test_emp_exist
    assert updated["pan_number"] == "ABCDE1234F"
    assert updated["uan_number"] == "100123456789"  # float .0 cleanly stripped
    assert updated["blood_group"] == "B+"
    assert "Bikramganj" in updated["current_address"]
    assert "802212" in updated["current_address"]
    assert updated["date_of_birth"] == "1999-08-25"  # 00:00:00 stripped

    # Verify newly inserted candidate
    new_cand = db_manager.get_candidate_by_mobile(test_mobile_new)
    assert new_cand is not None
    assert new_cand["status"] == "Joined"
    assert new_cand["employee_number"] == test_emp_new
    assert new_cand["legal_entity"] == "Doctors For You"

    # Cleanup
    try:
        os.remove(test_file_path)
    except Exception:
        pass

    print("✓ 74-column header offset auto-detection verified successfully!")
    print("✓ Float stripping, datetime sanitation, address composition verified!")
    print("✓ Existing candidate enriched & new employee safely imported!")
    print("=" * 70)
    print("ALL 74-COLUMN TESTS PASSED! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_test()
