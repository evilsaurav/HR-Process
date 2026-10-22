import os
import sys
import tempfile
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import sheet_processor


def test_synthetic_multi_sheet_workbook():
    print("--- Test 1: Synthetic Multi-Sheet Excel Workbook ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_excel = os.path.join(tmpdir, "multi_test.xlsx")

        # Create Sheet A with 3 candidates
        data_a = {
            "Candidate Name": ["Aarav Sharma", "Neha Patel", "Rohan Gupta"],
            "Mobile": ["9876543210", "9876543211", "9876543212"],
            "Email": ["aarav@example.com", "neha@example.com", "rohan@example.com"],
            "Designation": ["Software Engineer", "QA Engineer", "DevOps Engineer"],
            "Salary": ["50000", "45000", "55000"],
            "Location": ["Noida", "Delhi", "Gurgaon"],
        }
        # Create Sheet B with 4 candidates
        data_b = {
            "Applicant Name": ["Sita Verma", "Gita Rao", "Karan Singh", "Pooja Das"],
            "Contact No": ["9123456780", "9123456781", "9123456782", "9123456783"],
            "Email ID": ["sita@example.com", "gita@example.com", "karan@example.com", "pooja@example.com"],
            "Role": ["HR Executive", "Recruiter", "HR Manager", "Coordinator"],
            "Offered Salary": ["35000", "30000", "60000", "32000"],
            "City": ["Lucknow", "Patna", "Mumbai", "Pune"],
        }

        with pd.ExcelWriter(temp_excel, engine="openpyxl") as writer:
            pd.DataFrame(data_a).to_excel(writer, sheet_name="Sheet A", index=False)
            pd.DataFrame(data_b).to_excel(writer, sheet_name="Sheet B", index=False)

        res = sheet_processor.extract_candidate_rows_from_sheet(temp_excel)

        assert res.get("success") is True, f"Extraction failed: {res.get('error')}"
        assert "sheet_names" in res, "Missing 'sheet_names' in result dictionary"
        assert "sheet_counts" in res, "Missing 'sheet_counts' in result dictionary"
        assert "rows_by_sheet" in res, "Missing 'rows_by_sheet' in result dictionary"
        assert "detected_columns" in res, "Missing 'detected_columns' in result dictionary"

        assert res["sheet_names"] == ["Sheet A", "Sheet B"], f"Unexpected sheet_names: {res.get('sheet_names')}"
        assert res["sheet_counts"] == {"Sheet A": 3, "Sheet B": 4}, f"Unexpected sheet_counts: {res.get('sheet_counts')}"
        assert len(res["rows_by_sheet"]["Sheet A"]) == 3, f"Expected 3 rows in Sheet A, got {len(res['rows_by_sheet'].get('Sheet A', []))}"
        assert len(res["rows_by_sheet"]["Sheet B"]) == 4, f"Expected 4 rows in Sheet B, got {len(res['rows_by_sheet'].get('Sheet B', []))}"
        assert res["total_sheet_rows"] == 7, f"Expected 7 total rows, got {res.get('total_sheet_rows')}"
        assert len(res["valid_rows"]) == 7

        # Check _source_sheet tag
        assert res["rows_by_sheet"]["Sheet A"][0]["_source_sheet"] == "Sheet A"
        assert res["rows_by_sheet"]["Sheet B"][0]["_source_sheet"] == "Sheet B"

        # Check detected columns
        detected = set(res["detected_columns"])
        assert "candidate_name" in detected
        assert "mobile" in detected
        assert "email" in detected

        print("  ✓ Synthetic multi-sheet test passed successfully!")


def test_synthetic_csv_fallback():
    print("--- Test 2: Synthetic CSV Fallback ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_csv = os.path.join(tmpdir, "candidates.csv")
        data = {
            "Candidate Name": ["Vikram Malhotra", "Ananya Sen"],
            "Mobile": ["9811122233", "9811122244"],
            "Email": ["vikram@example.com", "ananya@example.com"],
            "Designation": ["Sales Lead", "Sales Manager"],
        }
        pd.DataFrame(data).to_csv(temp_csv, index=False)

        res = sheet_processor.extract_candidate_rows_from_sheet(temp_csv)

        assert res.get("success") is True, f"CSV extraction failed: {res.get('error')}"
        assert "sheet_names" in res
        assert "sheet_counts" in res
        assert "rows_by_sheet" in res
        assert "detected_columns" in res
        assert res["total_sheet_rows"] == 2
        sheet_key = res["sheet_names"][0]
        assert res["sheet_counts"][sheet_key] == 2
        assert len(res["rows_by_sheet"][sheet_key]) == 2
        assert res["rows_by_sheet"][sheet_key][0]["_source_sheet"] == sheet_key

        print("  ✓ Synthetic CSV test passed successfully!")


def test_live_ppsa_interview_chart():
    print("--- Test 3: Live PPSA INTERVIEW CHART.xlsx Check ---")
    live_excel = r"C:\Users\Saurav\Downloads\PPSA INTERVIEW CHART.xlsx"
    if not os.path.exists(live_excel):
        print("  ⚠️ Live file not found in Downloads, skipping.")
        return

    res = sheet_processor.extract_candidate_rows_from_sheet(live_excel)
    assert res.get("success") is True, f"Failed to extract live chart: {res.get('error')}"
    assert "PPSA UP" in res["sheet_names"]
    assert "PPSA Bihar" in res["sheet_names"]
    assert "PPSA Maharashtra" in res["sheet_names"]

    assert res["sheet_counts"]["PPSA UP"] == 11, f"Expected 11 UP candidates, got {res['sheet_counts'].get('PPSA UP')}"
    assert res["sheet_counts"]["PPSA Bihar"] == 14, f"Expected 14 Bihar candidates, got {res['sheet_counts'].get('PPSA Bihar')}"
    assert res["sheet_counts"]["PPSA Maharashtra"] == 19, f"Expected 19 Maharashtra candidates, got {res['sheet_counts'].get('PPSA Maharashtra')}"
    assert res["total_sheet_rows"] == 44

    assert len(res["rows_by_sheet"]["PPSA UP"]) == 11
    assert len(res["rows_by_sheet"]["PPSA Bihar"]) == 14
    assert len(res["rows_by_sheet"]["PPSA Maharashtra"]) == 19

    assert res["rows_by_sheet"]["PPSA UP"][0]["_source_sheet"] == "PPSA UP"
    assert res["rows_by_sheet"]["PPSA Bihar"][0]["_source_sheet"] == "PPSA Bihar"
    assert res["rows_by_sheet"]["PPSA Maharashtra"][0]["_source_sheet"] == "PPSA Maharashtra"

    print("  ✓ Live PPSA Interview Chart metadata verified successfully (UP: 11, Bihar: 14, Maharashtra: 19)!")


if __name__ == "__main__":
    test_synthetic_multi_sheet_workbook()
    test_synthetic_csv_fallback()
    test_live_ppsa_interview_chart()
    print("\nALL MULTI-SHEET PROCESSOR TESTS PASSED!")
