import os
import sys
import tempfile
import openpyxl

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import excel_export_service


def test_excel_export_styling():
    print("Testing Excel Export Styling...")
    sample_data = [
        {"Candidate Name": "Aarav Patel", "Mobile": "9876543210", "Salary": 35000, "Date Joined": "2026-11-01", "Status": "Selected"},
        {"Candidate Name": "Diya Sharma", "Mobile": "9876543211", "Salary": 42000, "Date Joined": "2026-11-05", "Status": "Selected"},
        {"Candidate Name": "Kabir Khan", "Mobile": "9876543212", "Salary": 28000, "Date Joined": "2026-11-10", "Status": "Applied"},
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "test_styled_export.xlsx")
        excel_export_service.export_to_excel(sample_data, out_path, sheet_name="Candidates")

        assert os.path.exists(out_path), "Excel file was not created"
        wb = openpyxl.load_workbook(out_path)
        ws = wb["Candidates"]

        # 1. Header Banner Check
        assert ws.cell(row=1, column=1).value is not None, "Missing title banner in row 1"
        assert "DOCTORS FOR YOU" in str(ws.cell(row=1, column=1).value), "Banner missing DOCTORS FOR YOU"

        # 2. Table Headers Check (Row 5)
        header_vals = [ws.cell(row=5, column=col).value for col in range(1, 6)]
        assert "Candidate Name" in header_vals
        assert "Salary" in header_vals

        # 3. Freeze panes check
        assert ws.freeze_panes in ["A6", "A5"], f"Unexpected freeze panes: {ws.freeze_panes}"

        # 4. Auto-filter check
        assert ws.auto_filter.ref is not None, "Auto-filter not set on table"

        # 5. Styling Check (Row 5 header background)
        header_cell = ws.cell(row=5, column=1)
        assert header_cell.fill.fill_type == "solid", "Header cell should have solid fill"
        assert header_cell.fill.start_color.rgb in ["FF1E3A8A", "1E3A8A", "FF0A2540", "0A2540"], f"Unexpected header color: {header_cell.fill.start_color.rgb}"

        # 6. Zebra striping check
        row6_cell = ws.cell(row=6, column=1)
        row7_cell = ws.cell(row=7, column=1)
        # One of row 6 / row 7 should have the alternating background
        assert row7_cell.fill.fill_type == "solid", "Row 7 cell should have zebra fill"
        assert row7_cell.fill.start_color.rgb in ["FFF8FAFC", "F8FAFC"], f"Unexpected zebra color: {row7_cell.fill.start_color.rgb}"

        # 7. Number format check (Salary & Date)
        salary_col_idx = header_vals.index("Salary") + 1
        date_col_idx = header_vals.index("Date Joined") + 1
        salary_cell = ws.cell(row=6, column=salary_col_idx)
        date_cell = ws.cell(row=6, column=date_col_idx)

        assert "₹" in str(salary_cell.number_format) or "#,##0" in str(salary_cell.number_format), f"Salary number format invalid: {salary_cell.number_format}"
        assert "YY" in str(date_cell.number_format).upper() or "MMM" in str(date_cell.number_format).upper(), f"Date format invalid: {date_cell.number_format}"

        # 8. Empty data check
        empty_out = os.path.join(tmp_dir, "test_empty.xlsx")
        excel_export_service.export_to_excel([], empty_out, sheet_name="Empty")
        assert os.path.exists(empty_out), "Empty export failed to create file"

        print("  ✓ All Excel styling verifications passed!")


if __name__ == "__main__":
    test_excel_export_styling()
