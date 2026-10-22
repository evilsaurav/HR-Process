# Professional Excel Styling, Word Template Date Alignment, File Launcher & Upload Visual Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Excel reports into professionally formatted DFY executive workbooks, fix Word template date alignment permanently with a 2-column borderless table, add 1-click OS file/folder opening post-export, and render an interactive inline multi-sheet visual preview on candidate spreadsheet uploads.

**Architecture:**
- **Excel Styling Engine**: `openpyxl` custom styler applied in `excel_export_service.py` and `hr_report_exporter.py` with DFY Navy title banners (`#0A2540`), table headers (`#1E3A8A`), zebra striping, currency/date formatting, auto-filters, and freeze panes.
- **Word Template Header Styler**: Replaces fragile space-padding strings in `document_generation_service.py` with a native 1-row, 2-column borderless Word table, guaranteeing that `Reference No` and `Dated: ...` sit on the exact same baseline at opposite margins with zero line-wrapping.
- **OS File Launcher**: `file_launcher.py` and reusable `show_export_success_dialog` in `ui_theme.py` using `os.startfile` and `explorer.exe /select` to let users launch exported files or open their folder with 1 click.
- **Multi-Sheet Upload Preview**: Enhances `sheet_processor.py` and `joining_process_page.py` with sheet switcher tabs (`PPSA UP`, `PPSA Bihar`, `PPSA Maharashtra`), metric KPI badges, a 10-row scrollable data table preview, and post-ingestion action buttons.

**Tech Stack:** Python 3.14, Flet, openpyxl, python-docx, pandas, Windows OS APIs (`os.startfile`, `subprocess.Popen`)

**Spec:** [`docs/superpowers/specs/2026-10-22-excel-styling-word-date-alignment-and-visual-feedback-design.md`](file:///d:/ignou/Suraj%20HR%20Project/docs/superpowers/specs/2026-10-22-excel-styling-word-date-alignment-and-visual-feedback-design.md)

## Global Constraints

- 100% offline fallback compatibility: zero external web dependencies or blocking cloud calls.
- Clean typography: Times New Roman in Word documents, Segoe UI / Calibri in Excel workbooks.
- Zero data loss: Existing candidate data and reference number sequences must never be altered or consumed prematurely.
- Windows file safety: Guard all file open/browse calls with `os.path.exists` checks to avoid OS dialog errors.

---

### Task 1: Professional Excel Styling Engine (`excel_export_service.py`)

**Files:**
- Modify: `desktop_app/services/excel_export_service.py`
- Test: `desktop_app/scripts/test_excel_styling.py`

**Interfaces:**
- Consumes: `List[Dict[str, Any]]`, `output_path: str`, `sheet_name: str`
- Produces: Polished `.xlsx` workbook with DFY Navy banner, zebra striping, currency formatting, auto-filter, and freeze panes.

- [ ] **Step 1: Write the failing test**

Create `desktop_app/scripts/test_excel_styling.py`:
```python
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
        assert ws.freeze_panes == "A6" or ws.freeze_panes == "A5", f"Unexpected freeze panes: {ws.freeze_panes}"

        # 4. Auto-filter check
        assert ws.auto_filter.ref is not None, "Auto-filter not set on table"

        # 5. Styling Check (Row 5 header background)
        header_cell = ws.cell(row=5, column=1)
        assert header_cell.fill.fill_type == "solid", "Header cell should have solid fill"
        assert header_cell.fill.start_color.rgb in ["FF1E3A8A", "1E3A8A", "FF0A2540", "0A2540"], f"Unexpected header color: {header_cell.fill.start_color.rgb}"

        print("  ✓ Excel styling verification passed!")


if __name__ == "__main__":
    test_excel_export_styling()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_excel_styling.py`
Expected: FAIL (Row 1 banner missing, freeze panes not set).

- [ ] **Step 3: Implement professional styling in `excel_export_service.py`**

Update `desktop_app/services/excel_export_service.py` to:
1. Write DFY Header Banner in rows 1–3 (`DOCTORS FOR YOU — HR & RECRUITMENT OPERATIONS`, Report Name, Generation Timestamp).
2. Write Table Column Headers in row 5 with `#1E3A8A` fill, white bold font, thin border.
3. Write Data Rows starting at row 6 with alternating zebra striping (`#FFFFFF` and `#F8FAFC`).
4. Apply number formats: currency `₹ #,##,##0` for salary/fee columns, dates `DD-MMM-YYYY` for date columns.
5. Set `ws.auto_filter.ref = f"A5:{get_column_letter(num_cols)}5"`.
6. Set `ws.freeze_panes = "A6"`.
7. Auto-adjust column widths with bounds `[14, 55]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_excel_styling.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/services/excel_export_service.py desktop_app/scripts/test_excel_styling.py
git commit -m "feat(excel): add professional openpyxl styling engine with DFY branding and zebra striping"
```

---

### Task 2: Executive HR Daily Briefing Excel Styler (`hr_report_exporter.py`)

**Files:**
- Modify: `desktop_app/services/hr_report_exporter.py`
- Test: `desktop_app/scripts/test_excel_styling.py`

**Interfaces:**
- Consumes: `export_daily_executive_summary(target_path: Optional[str])`
- Produces: Polished 2-sheet executive briefing workbook with DFY branding and zebra striping across both sheets (`Executive Overview` & `Action Priorities`).

- [ ] **Step 1: Update `test_excel_styling.py` to test `hr_report_exporter`**

Add test function `test_daily_briefing_styling()` to `desktop_app/scripts/test_excel_styling.py`:
```python
def test_daily_briefing_styling():
    print("Testing Daily Executive Summary Excel Styling...")
    from services import hr_report_exporter
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = os.path.join(tmp_dir, "test_briefing.xlsx")
        hr_report_exporter.export_daily_executive_summary(report_path)
        wb = openpyxl.load_workbook(report_path)
        assert "Executive Overview" in wb.sheetnames
        assert "Action Priorities" in wb.sheetnames
        ws1 = wb["Executive Overview"]
        assert ws1.cell(row=1, column=1).value is not None
        assert "DOCTORS FOR YOU" in str(ws1.cell(row=1, column=1).value)
        ws2 = wb["Action Priorities"]
        assert ws2.cell(row=1, column=1).value is not None
        print("  ✓ Daily briefing styling verified!")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_excel_styling.py`
Expected: FAIL on `test_daily_briefing_styling`.

- [ ] **Step 3: Implement professional multi-sheet styling in `hr_report_exporter.py`**

Refactor `hr_report_exporter.py` to apply the same styling helper or reuse `excel_export_service.style_worksheet` to format both `Executive Overview` and `Action Priorities` sheets with DFY header banners, styled table headers, zebra striping, and auto-adjusted widths.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_excel_styling.py`
Expected: PASS with 100% success.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/services/hr_report_exporter.py desktop_app/scripts/test_excel_styling.py
git commit -m "feat(report): apply executive DFY styling to daily briefing 2-sheet workbook"
```

---

### Task 3: Word Template Header Date Alignment Fix (`document_generation_service.py`)

**Files:**
- Modify: `desktop_app/services/document_generation_service.py`
- Modify: `desktop_app/services/document_formatters.py`
- Test: `desktop_app/scripts/test_word_date_alignment.py`

**Interfaces:**
- Consumes: `insert_reference_and_date(doc, reference_number: str, date_text: str, document_type: str)`
- Produces: 1-row, 2-column borderless Word table inserted directly below top anchor paragraph. Left cell contains Reference No; right cell contains right-aligned Date. 0% line wrap.

- [ ] **Step 1: Write the failing test**

Create `desktop_app/scripts/test_word_date_alignment.py`:
```python
import os
import sys
import docx
from docx.shared import Inches

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import document_generation_service, db_manager


def test_reference_and_date_table_alignment():
    print("Testing Word Template Reference & Date Table Alignment...")
    db_manager.init_db()

    # Create dummy candidate
    mock_cand = {
        "candidate_name": "Dr. Sameer Verma",
        "gender": "Male",
        "applied_designation": "Field Coordinator",
        "contact_location": "Patna",
        "negotiated_salary": "45000",
        "date_joined": "2026-11-01",
        "department": "PPSA Bihar",
        "full_address": "House 12, Boring Road, Patna, Bihar",
    }

    # Generate preview offer letter
    res = document_generation_service.generate_document_preview(mock_cand, "offer")
    assert res.get("success"), f"Failed to generate preview: {res.get('error')}"

    preview_path = res["preview_file_path"]
    assert os.path.exists(preview_path), f"File missing: {preview_path}"

    doc = docx.Document(preview_path)

    # 1. Verify table exists at the top
    assert len(doc.tables) >= 1, "Expected header table to be created"
    header_table = doc.tables[0]
    assert len(header_table.rows) == 1, "Header table should have exactly 1 row"
    assert len(header_table.columns) == 2, "Header table should have exactly 2 columns"

    # 2. Verify left cell has Reference No and right cell has Date/Dated
    left_cell = header_table.cell(0, 0)
    right_cell = header_table.cell(0, 1)

    assert "Reference No:" in left_cell.text, f"Left cell missing 'Reference No:': {left_cell.text}"
    assert "Dated:" in right_cell.text or "Date:" in right_cell.text, f"Right cell missing 'Dated:': {right_cell.text}"

    # 3. Verify right cell paragraph is right-aligned
    assert right_cell.paragraphs[0].alignment == docx.enum.text.WD_ALIGN_PARAGRAPH.RIGHT

    # 4. Clean up
    if os.path.exists(preview_path):
        os.remove(preview_path)

    print("  ✓ Word reference & date table alignment verified successfully!")


if __name__ == "__main__":
    test_reference_and_date_table_alignment()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_word_date_alignment.py`
Expected: FAIL (doc.tables is empty or table 0 is not the header table).

- [ ] **Step 3: Implement 1-row, 2-column borderless header table in `document_generation_service.py`**

In `desktop_app/services/document_generation_service.py`, rewrite `insert_reference_and_date`:
1. Remove string concatenation `text = f"Reference No: {clean_ref}" + (" " * 81) + ...`.
2. Insert a 1-row, 2-column table directly below `doc.paragraphs[0]._element` (using `first_para_element.addnext(tbl_element)` or `doc.add_table`).
3. Set table width to `Inches(6.5)`. Column 0 width `Inches(3.6)`, Column 1 width `Inches(2.9)`.
4. Hide all borders via `w:tblBorders` XML element with `val="none"`.
5. In Cell 0: Left-align paragraph, add bold run `f"Reference No: {clean_ref}"`, Times New Roman font.
6. In Cell 1: Right-align paragraph (`WD_ALIGN_PARAGRAPH.RIGHT`), add bold run `f"Dated: {clean_date}"` (or `Date:` for certificates), Times New Roman font.
7. Also ensure `format_date_long` and `calculate_end_date` in `document_formatters.py` strictly return clean `DD MMMM YYYY` without trailing timestamps.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_word_date_alignment.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/services/document_generation_service.py desktop_app/services/document_formatters.py desktop_app/scripts/test_word_date_alignment.py
git commit -m "fix(docx): replace space padding with 2-column borderless header table for date alignment"
```

---

### Task 4: OS File Launcher & Reusable Export Success Modal (`file_launcher.py` & `ui_theme.py`)

**Files:**
- Create: `desktop_app/utils/file_launcher.py`
- Modify: `desktop_app/utils/ui_theme.py`
- Modify: `desktop_app/pages/joining_process_page.py`
- Modify: `desktop_app/pages/dashboard_page.py`
- Modify: `desktop_app/pages/document_generation_page.py`
- Test: `desktop_app/scripts/test_file_launcher_and_export_modal.py`

**Interfaces:**
- Consumes: `file_path: str`, `page: ft.Page`, `record_count: Optional[int]`, `report_title: str`
- Produces: `open_file_externally(file_path: str)`, `open_folder_and_select(file_path: str)`, and `show_export_success_dialog(page, file_path, ...)` popup dialog with direct launch buttons.

- [ ] **Step 1: Write the failing test**

Create `desktop_app/scripts/test_file_launcher_and_export_modal.py`:
```python
import os
import sys
import tempfile
import flet as ft

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

from utils import file_launcher
from utils import ui_theme


def test_file_launcher_and_modal():
    print("Testing File Launcher & Export Modal...")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        tf.write(b"dummy content")
        tf_path = tf.name

    try:
        # 1. Test launcher function existence
        assert hasattr(file_launcher, "open_file_externally")
        assert hasattr(file_launcher, "open_folder_and_select")

        # 2. Test modal instantiation
        class MockPage:
            opened_dialog = None
            def open(self, dlg):
                self.opened_dialog = dlg
            def close(self, dlg):
                self.opened_dialog = None
            def update(self):
                pass

        page = MockPage()
        ui_theme.show_export_success_dialog(page, tf_path, record_count=25, report_title="Candidate Pipeline")
        assert page.opened_dialog is not None, "Export dialog was not opened"
        assert "Candidate Pipeline" in page.opened_dialog.title.controls[1].value
        print("  ✓ File launcher & export modal verified successfully!")
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)


if __name__ == "__main__":
    test_file_launcher_and_modal()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_file_launcher_and_export_modal.py`
Expected: FAIL (No module named `utils.file_launcher`).

- [ ] **Step 3: Implement `file_launcher.py` and `show_export_success_dialog`**

1. Create `desktop_app/utils/file_launcher.py`:
   - `open_file_externally(file_path: str) -> Tuple[bool, str]`: calls `os.startfile(os.path.abspath(file_path))` with `os.path.exists` safety.
   - `open_folder_and_select(file_path: str) -> Tuple[bool, str]`: calls `subprocess.Popen(f'explorer /select,"{os.path.abspath(file_path)}"')`.
2. In `desktop_app/utils/ui_theme.py`, add `show_export_success_dialog`:
   - Creates an `ft.AlertDialog` with file details, record count, `📄 Open File` button, `📁 Open Folder` button, and `Close` button.
3. In `joining_process_page.py` (`export_candidates_clicked`), `dashboard_page.py` (`export_exp_due_clicked`, `export_inc_clicked`, `export_daily_summary_clicked`), and `document_generation_page.py` (`on_bulk_zip_export`), invoke `ui_theme.show_export_success_dialog(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_file_launcher_and_export_modal.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/utils/file_launcher.py desktop_app/utils/ui_theme.py desktop_app/pages/joining_process_page.py desktop_app/pages/dashboard_page.py desktop_app/pages/document_generation_page.py desktop_app/scripts/test_file_launcher_and_export_modal.py
git commit -m "feat(ui): add 1-click OS file and folder launcher dialog for all Excel and ZIP exports"
```

---

### Task 5: Multi-Sheet Candidate Data Extractor & Metadata Parser (`sheet_processor.py`)

**Files:**
- Modify: `desktop_app/services/sheet_processor.py`
- Test: `desktop_app/scripts/test_multi_sheet_processor.py`

**Interfaces:**
- Consumes: `extract_candidate_rows_from_sheet(file_path: str)`
- Produces: Enhanced return dictionary containing:
  - `sheet_names`: list of all detected sheet names (e.g. `["PPSA UP", "PPSA Bihar", "PPSA Maharashtra"]`)
  - `sheet_counts`: dict of `{sheet_name: row_count}`
  - `rows_by_sheet`: dict of `{sheet_name: list_of_parsed_candidate_rows}`
  - `total_sheet_rows`: total candidate count across all sheets
  - `valid_rows`: aggregated list of valid candidate rows
  - `mapped_columns_count`: count of recognized columns

- [ ] **Step 1: Write the failing test**

Create `desktop_app/scripts/test_multi_sheet_processor.py`:
```python
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from services import sheet_processor


def test_multi_sheet_extraction_metadata():
    print("Testing Multi-Sheet Extraction Metadata...")
    test_excel = r"C:\Users\Saurav\Downloads\PPSA INTERVIEW CHART.xlsx"
    if not os.path.exists(test_excel):
        print("  ⚠️ Test file not found in Downloads, skipping live chart check.")
        return

    extracted = sheet_processor.extract_candidate_rows_from_sheet(test_excel)
    assert extracted.get("success") is True
    assert "sheet_names" in extracted, "Missing 'sheet_names' in result"
    assert "sheet_counts" in extracted, "Missing 'sheet_counts' in result"
    assert "rows_by_sheet" in extracted, "Missing 'rows_by_sheet' in result"

    assert len(extracted["sheet_names"]) == 3
    assert "PPSA UP" in extracted["sheet_names"]
    assert "PPSA Bihar" in extracted["sheet_names"]
    assert "PPSA Maharashtra" in extracted["sheet_names"]
    assert extracted["total_sheet_rows"] == 44
    print("  ✓ Multi-sheet extraction metadata verified successfully!")


if __name__ == "__main__":
    test_multi_sheet_extraction_metadata()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_multi_sheet_processor.py`
Expected: FAIL (missing `sheet_names` or `rows_by_sheet`).

- [ ] **Step 3: Enhance `sheet_processor.py` to preserve and return per-sheet candidate collections**

In `desktop_app/services/sheet_processor.py`:
- Update `extract_candidate_rows_from_sheet`:
  - When iterating sheets, populate `rows_by_sheet[sheet_name] = valid_rows_for_sheet`.
  - Include `sheet_names`, `sheet_counts`, and `rows_by_sheet` in the return dictionary alongside `valid_rows` and `total_sheet_rows`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_multi_sheet_processor.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/services/sheet_processor.py desktop_app/scripts/test_multi_sheet_processor.py
git commit -m "feat(sheets): enhance sheet processor to return per-sheet collections and metadata"
```

---

### Task 6: Inline Multi-Sheet Visual Preview in Joining Process Page (`joining_process_page.py`)

**Files:**
- Modify: `desktop_app/pages/joining_process_page.py`
- Test: `desktop_app/scripts/test_joining_upload_preview_ui.py`

**Interfaces:**
- Consumes: `upload_state` containing `sheet_names`, `sheet_counts`, `rows_by_sheet`, `new_rows`, `duplicates`
- Produces: Interactive visual preview panel in `joining_process_view` with:
  1. Sheet switcher tabs (`[PPSA UP (11)]`, `[PPSA Bihar (14)]`, `[PPSA Maharashtra (19)]`)
  2. KPI metrics strip (Total, New, Duplicates, Mapped Columns)
  3. 10-row scrollable DataTable preview of candidate rows for the selected sheet
  4. Primary `Confirm & Ingest` action button and post-ingestion success card

- [ ] **Step 1: Write the failing test**

Create `desktop_app/scripts/test_joining_upload_preview_ui.py`:
```python
import os
import sys
import flet as ft

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)
sys.stdout.reconfigure(encoding="utf-8")

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

from pages import joining_process_page


def test_joining_upload_preview_ui():
    print("Testing Joining Process Upload Preview UI...")
    class MockPage:
        theme_mode = ft.ThemeMode.DARK
        overlay = []
        services = []
        def update(self):
            pass
        def open(self, ctrl):
            pass
        def close(self, ctrl):
            pass

    page = MockPage()
    view = joining_process_page.joining_process_view(page)
    assert view is not None

    jp_py = os.path.join(DESKTOP_APP_DIR, "pages", "joining_process_page.py")
    with open(jp_py, "r", encoding="utf-8") as f:
        content = f.read()

    assert "build_upload_preview_panel" in content or "preview_table" in content or "rows_by_sheet" in content
    print("  ✓ Joining Process upload preview UI verified!")


if __name__ == "__main__":
    test_joining_upload_preview_ui()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_joining_upload_preview_ui.py`
Expected: FAIL (`preview_table` or `rows_by_sheet` not found).

- [ ] **Step 3: Implement inline multi-sheet preview panel in `joining_process_page.py`**

1. In `joining_process_page.py`:
   - When spreadsheet is parsed in `handle_spreadsheet_files`:
     - Set `upload_state["view_mode"] = "upload_preview"`.
     - Save `upload_state["rows_by_sheet"] = extracted.get("rows_by_sheet", {})`.
     - Save `upload_state["sheet_names"] = extracted.get("sheet_names", [])`.
     - Save `upload_state["active_preview_sheet"] = sheet_names[0] if sheet_names else ""`.
2. In `render_upload_ui`:
   - Add handler for `mode == "upload_preview"`:
     - Render Sheet Switcher Segmented Button / Tabs for all sheets.
     - Render KPI metric cards: Total, New, Duplicates, Mapped Columns.
     - Render a scrollable `ft.DataTable` displaying the first 10 candidate rows from the active sheet (`Name`, `Mobile`, `Role`, `Salary`, `Location`).
     - Render action buttons: `🚀 Confirm & Ingest Candidates (N)` and `❌ Cancel Upload`.
   - On completion (`mode == "completed"`):
     - Display a rich completion card with sheet breakdown and 2 quick-action pills: `[✉️ Review Welcome Emails]` and `[👥 View In Pipeline]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_joining_upload_preview_ui.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desktop_app/pages/joining_process_page.py desktop_app/scripts/test_joining_upload_preview_ui.py
git commit -m "feat(ui): add inline multi-sheet preview panel and post-ingestion action cards on Excel upload"
```

---

### Task 7: End-to-End System Integration & Regression Suite

**Files:**
- Create: `desktop_app/scripts/test_workflow_upgrade_e2e.py`
- Test: All regression suites

**Interfaces:**
- Consumes: Tasks 1 through 6
- Produces: 100% verified operational pipeline with zero regressions.

- [ ] **Step 1: Create `desktop_app/scripts/test_workflow_upgrade_e2e.py`**

Comprehensive test script covering:
1. Excel export styling & openpyxl workbook properties.
2. Word template 2-column borderless header table date alignment across all 5 letter types.
3. File launcher utility functions & export modal rendering.
4. Multi-sheet extraction & inline preview rendering.
5. Full regression run of `test_task9_full_pipeline_e2e.py` and `test_compact_dashboard_and_ai_copilot_e2e.py`.

- [ ] **Step 2: Run `test_workflow_upgrade_e2e.py`**

Run: `python desktop_app/scripts/test_workflow_upgrade_e2e.py`
Expected: PASS (100% success rate).

- [ ] **Step 3: Commit**

```bash
git add desktop_app/scripts/test_workflow_upgrade_e2e.py
git commit -m "test(e2e): add comprehensive integration and regression suite for workflow upgrade"
```
