# Implementation Plan: End-to-End HR Operations Platform & Smart Document Staging Pipeline

**Date**: 2026-10-21  
**Spec Reference**: [`docs/superpowers/specs/2026-10-21-end-to-end-hr-pipeline-redesign-design.md`](file:///d:/ignou/Suraj%20HR%20Project/docs/superpowers/specs/2026-10-21-end-to-end-hr-pipeline-redesign-design.md)  
**Target Environment**: Windows (PowerShell), Python 3.10+, Flet, SQLite, `python-docx`, `win32com.client`  

---

## 1. Plan Overview & Architectural Principles

This plan operationalizes the complete redesign approved in the specification into bite-sized, verifiable tasks following Test-Driven Development (TDD).

### Core Architectural Guarantees:
1. **Zero Data Loss**: Uploading sheets or syncing data never overwrites populated fields with blank/null values.
2. **Reference Sequence Conservation**: Sequence numbers are strictly incremented only when documents are approved for Final Go dispatch, never during draft preview or staging generation.
3. **Format Flexibility with Graceful Fallback**: Default to PDF via Word COM (`win32com.client`); if Word is unavailable or conversion encounters an error, automatically fall back to `.docx` without crashing.
4. **Human-in-the-Loop Staging**: Generated letters reside in `document_staging`. HR can preview, inspect AI data health checks, fix candidate details with instant regeneration, and execute bulk dispatch via the **"🚀 Final Go"** button.
5. **Non-Technical Language**: Plain English in all alerts, confirmation modals, and error messages.

---

## 2. Bite-Sized Implementation Tasks

### Task 1: Database Migration — `document_staging` Table & Welcome Email Tracking

**Files to modify**:
- [`desktop_app/database/db_manager.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/database/db_manager.py)

**Step-by-step instructions**:
1. Open `desktop_app/database/db_manager.py`.
2. In `init_db()`, add safe column migrations for `candidates`:
   - `welcome_email_sent INTEGER DEFAULT 0`
   - `welcome_email_sent_at TEXT`
3. In `init_db()`, create the `document_staging` table if it does not exist:
   ```sql
   CREATE TABLE IF NOT EXISTS document_staging (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       candidate_id INTEGER NOT NULL,
       document_type TEXT NOT NULL,
       status TEXT DEFAULT 'Staged',
       doc_file_path TEXT NOT NULL,
       pdf_file_path TEXT,
       preferred_format TEXT DEFAULT 'pdf',
       recipient_email TEXT NOT NULL,
       recipient_name TEXT NOT NULL,
       email_subject TEXT NOT NULL,
       email_body TEXT NOT NULL,
       reference_number TEXT,
       extra_fields_json TEXT,
       discrepancy_warnings_json TEXT,
       created_at TEXT NOT NULL,
       updated_at TEXT NOT NULL,
       dispatched_at TEXT,
       FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
   );
   ```
4. Implement CRUD and helper functions in `db_manager.py`:
   - `create_staging_record(...) -> int`
   - `get_staging_records(status='Staged') -> List[Dict]`
   - `get_staging_record_by_id(staging_id: int) -> Optional[Dict]`
   - `update_staging_record(staging_id: int, **kwargs) -> bool`
   - `delete_staging_record(staging_id: int) -> bool`
   - `update_candidate_welcome_email_status(candidate_id: int, sent: bool = True) -> bool`
   - `get_selected_candidates_pending_welcome() -> List[Dict]`
   - `get_dashboard_staging_counts() -> Dict[str, int]`

**Verification script**:
Create `desktop_app/scripts/test_task1_staging_db.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager

def run_test():
    print("Initializing database...")
    db_manager.init_db()
    
    # Verify candidate welcome email columns
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(candidates)")
    cols = {r[1] for r in cur.fetchall()}
    assert "welcome_email_sent" in cols, "welcome_email_sent column missing"
    assert "welcome_email_sent_at" in cols, "welcome_email_sent_at column missing"

    # Verify document_staging table
    cur.execute("PRAGMA table_info(document_staging)")
    staging_cols = {r[1] for r in cur.fetchall()}
    expected_staging = {"id", "candidate_id", "document_type", "status", "doc_file_path", 
                        "pdf_file_path", "preferred_format", "recipient_email", "recipient_name", 
                        "email_subject", "email_body", "created_at", "updated_at"}
    assert expected_staging.issubset(staging_cols), f"Missing staging cols: {expected_staging - staging_cols}"

    # Test Staging CRUD
    staging_id = db_manager.create_staging_record(
        candidate_id=1,
        document_type="offer_letter",
        status="Staged",
        doc_file_path="output/test.docx",
        pdf_file_path=None,
        preferred_format="pdf",
        recipient_email="test@example.com",
        recipient_name="Test Candidate",
        email_subject="Offer Letter",
        email_body="Congratulations",
        extra_fields={"salary": "50000"},
        discrepancy_warnings=["Missing PAN"]
    )
    assert staging_id > 0, "Failed to create staging record"
    
    record = db_manager.get_staging_record_by_id(staging_id)
    assert record is not None
    assert record["recipient_name"] == "Test Candidate"
    assert record["status"] == "Staged"
    
    # Test update
    db_manager.update_staging_record(staging_id, preferred_format="docx", status="Approved")
    updated = db_manager.get_staging_record_by_id(staging_id)
    assert updated["preferred_format"] == "docx"
    assert updated["status"] == "Approved"

    # Cleanup test record
    db_manager.delete_staging_record(staging_id)
    assert db_manager.get_staging_record_by_id(staging_id) is None
    
    print("SUCCESS: Task 1 Database Migration verified successfully.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task1_staging_db.py`

---

### Task 2: PDF Conversion Engine with Graceful Word COM Fallback

**Files to create**:
- [`desktop_app/services/pdf_converter_service.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/services/pdf_converter_service.py)

**Step-by-step instructions**:
1. Implement `convert_docx_to_pdf(docx_path: str, pdf_path: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]`:
   - Checks if `docx_path` exists.
   - Computes default `pdf_path` (same directory, `.pdf` extension) if not supplied.
   - Attempts conversion via `win32com.client.Dispatch("Word.Application")`:
     - Sets `word.Visible = False` and `word.DisplayAlerts = 0`.
     - Opens docx read-only: `doc = word.Documents.Open(os.path.abspath(docx_path), ReadOnly=True)`.
     - Saves as PDF: `doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)`.
     - Closes doc and quits Word cleanly in a `finally` block to prevent lingering Word processes.
   - Handles exceptions (Word not installed, permission errors, etc.):
     - Logs descriptive warning.
     - Returns `(False, None, error_message)`.
2. Implement helper `is_pdf_conversion_available() -> bool` to proactively test if Word COM is responsive on the host.

**Verification script**:
Create `desktop_app/scripts/test_task2_pdf_converter.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import docx
from services import pdf_converter_service

def run_test():
    test_docx = os.path.abspath("desktop_app/output/pdf_test.docx")
    test_pdf = os.path.abspath("desktop_app/output/pdf_test.pdf")
    
    os.makedirs("desktop_app/output", exist_ok=True)
    doc = docx.Document()
    doc.add_heading("PDF Conversion Test", 0)
    doc.add_paragraph("Doctors For You - Document Pipeline Test")
    doc.save(test_docx)
    
    success, result_path, error = pdf_converter_service.convert_docx_to_pdf(test_docx, test_pdf)
    print(f"Conversion result: success={success}, path={result_path}, error={error}")
    
    if success:
        assert os.path.exists(test_pdf), "PDF file was not created"
        assert os.path.getsize(test_pdf) > 0, "PDF file is empty"
        print("SUCCESS: PDF conversion succeeded with Word COM.")
    else:
        print(f"INFO: Word COM conversion gracefully failed ({error}). Fallback active.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task2_pdf_converter.py`

---

### Task 3: Smart Rule Detector Service

**Files to create**:
- [`desktop_app/services/smart_rule_detector.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/services/smart_rule_detector.py)

**Step-by-step instructions**:
1. Implement `classify_candidate_document_need(candidate: Dict[str, Any], history: Optional[List[Dict]] = None) -> Dict[str, Any]`:
   - Inputs: Candidate dictionary (from DB or Keka parsed row) and optional previous document generation history.
   - Evaluates rule hierarchy:
     1. **Termination Letter**: If `termination_type` or `termination_reason` is non-empty $\rightarrow$ Suggestion: `"termination_letter"`, Reason: `"Involuntary separation / Termination recorded"`.
     2. **Experience / Relieving Certificate**: If `exit_date` or `exit_status` is populated $\rightarrow$ Suggestion: `"experience_certificate"`, Reason: `"Employee separation / Exit date recorded"`.
     3. **Extension Letter**: If `extension_of_service_till` or `extension_of_service_months` is populated, OR contract ends within 30 days $\rightarrow$ Suggestion: `"extension_letter"`, Reason: `"Service extension date or tenure recorded"`.
     4. **Increment Letter**: If `pay_grade` has changed or salary increment detected $\rightarrow$ Suggestion: `"increment_letter"`, Reason: `"Salary/Pay Grade revision detected"`.
     5. **Offer Letter**: If candidate `status == 'Joined'` or `employment_status == 'Active'`, and candidate has no prior offer letter in history $\rightarrow$ Suggestion: `"offer_letter"`, Reason: `"Active joinee without prior offer letter on file"`.
     6. **Default / None**: If none match $\rightarrow$ Suggestion: `"none"`, Reason: `"Profile up to date / No document triggered"`.
   - Returns:
     ```python
     {
         "candidate_id": candidate.get("id"),
         "employee_number": candidate.get("employee_number"),
         "name": candidate.get("candidate_name") or candidate.get("display_name"),
         "suggested_doc_type": suggested_type,
         "trigger_reason": reason,
         "priority": "High" if suggested_type in ["termination_letter", "offer_letter"] else "Normal",
         "missing_fields": audit_warnings  # from ai_service.audit_candidate_data_completeness
     }
     ```
2. Implement batch scanner `scan_all_candidates_for_document_needs() -> List[Dict[str, Any]]`:
   - Fetches active candidates from `db_manager`.
   - Fetches prior document logs.
   - Returns aggregated actionable suggestions for all employees requiring attention.

**Verification script**:
Create `desktop_app/scripts/test_task3_smart_rule_detector.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import smart_rule_detector

def run_test():
    # Case 1: Active joinee -> Offer Letter
    c1 = {"id": 101, "candidate_name": "Aarav Patel", "status": "Joined", "employment_status": "Active"}
    res1 = smart_rule_detector.classify_candidate_document_need(c1, history=[])
    assert res1["suggested_doc_type"] == "offer_letter"

    # Case 2: Extension till -> Extension Letter
    c2 = {"id": 102, "candidate_name": "Pooja Shah", "extension_of_service_till": "2026-12-31"}
    res2 = smart_rule_detector.classify_candidate_document_need(c2)
    assert res2["suggested_doc_type"] == "extension_letter"

    # Case 3: Exit date -> Experience Certificate
    c3 = {"id": 103, "candidate_name": "Rahul Verma", "exit_date": "2026-09-30", "exit_status": "Resigned"}
    res3 = smart_rule_detector.classify_candidate_document_need(c3)
    assert res3["suggested_doc_type"] == "experience_certificate"

    # Case 4: Termination reason -> Termination Letter
    c4 = {"id": 104, "candidate_name": "Karan Mehra", "termination_reason": "Performance shortfall"}
    res4 = smart_rule_detector.classify_candidate_document_need(c4)
    assert res4["suggested_doc_type"] == "termination_letter"

    print("SUCCESS: Task 3 Smart Rule Detector classified all scenarios accurately.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task3_smart_rule_detector.py`

---

### Task 4: Staging Service & Bulk Dispatch Engine

**Files to create**:
- [`desktop_app/services/document_staging_service.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/services/document_staging_service.py)

**Step-by-step instructions**:
1. Implement `generate_draft_to_staging(candidate_id: int, document_type: str, extra_fields: dict = None, preferred_format: str = 'pdf') -> Dict[str, Any]`:
   - Validates candidate exists.
   - Generates `.docx` with a non-consuming reference placeholder (`DFY/HR/DRAFT/...`).
   - Runs `pdf_converter_service.convert_docx_to_pdf(...)`.
   - Generates personalized email draft using `ai_service.generate_email_cover(...)`.
   - Runs `ai_service.audit_candidate_data_completeness(...)` to detect anomalies.
   - Inserts record into `document_staging` table with status `'Staged'`.
   - Returns summary dictionary with staging ID and file paths.
2. Implement `inline_fix_and_regenerate(staging_id: int, updated_candidate_fields: dict, updated_extra_fields: dict = None) -> Dict[str, Any]`:
   - Updates candidate record in `candidates` table with corrected fields.
   - Re-generates draft `.docx` and converts to `.pdf`.
   - Re-runs data completeness check.
   - Updates `document_staging` record with new file paths, updated timestamps, and refreshed warning list.
   - Returns success status and regenerated paths.
3. Implement `final_go_dispatch(staging_ids: List[int], send_async: bool = False, on_progress_callback = None) -> Dict[str, Any]`:
   - For each staging item:
     - Atomically consumes official sequence number via `db_manager.consume_next_reference("hr_reference")`.
     - Re-stamps the `.docx` document with the official Reference Number and re-exports `.pdf` (if format is PDF).
     - Chooses attachment based on `preferred_format`: `.pdf` if exists, fallback to `.docx`.
     - Sends email using `email_service.send_email_smtp(...)`.
     - Updates staging status to `'Dispatched'`, logs to `email_log` and `document_generation_log`.
     - If email sending fails, marks staging status as `'Failed'` with error message.
   - Returns summary: `{"total": len(staging_ids), "sent": count_sent, "failed": count_failed, "errors": [...]}`.

**Verification script**:
Create `desktop_app/scripts/test_task4_staging_service.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager
from services import document_staging_service

def run_test():
    db_manager.init_db()
    # 1. Fetch or create a test candidate
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM candidates WHERE email IS NOT NULL LIMIT 1")
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO candidates (candidate_name, email, mobile, applied_designation, status)
            VALUES ('Staging Test User', 'staging_test@doctorsforyou.org', '9876543210', 'Medical Officer', 'Joined')
        """)
        conn.commit()
        cand_id = cur.lastrowid
    else:
        cand_id = row[0]

    # 2. Generate Draft to Staging
    res = document_staging_service.generate_draft_to_staging(
        candidate_id=cand_id,
        document_type="offer_letter",
        preferred_format="docx"
    )
    assert res["success"] is True, f"Draft generation failed: {res.get('error')}"
    staging_id = res["staging_id"]
    print(f"Draft generated in staging with ID: {staging_id}")

    # 3. Test Inline Fix & Instant Regeneration
    fix_res = document_staging_service.inline_fix_and_regenerate(
        staging_id=staging_id,
        updated_candidate_fields={"negotiated_salary": "75000", "department": "Pediatrics"}
    )
    assert fix_res["success"] is True, f"Inline fix failed: {fix_res.get('error')}"
    print("Inline fix and instant regeneration succeeded.")

    # 4. Clean up staging record
    db_manager.delete_staging_record(staging_id)
    print("SUCCESS: Task 4 Staging Service lifecycle verified.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task4_staging_service.py`

---

### Task 5: Joining Process Welcome Email Staging UI

**Files to modify**:
- [`desktop_app/pages/joining_process_page.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/pages/joining_process_page.py)

**Step-by-step instructions**:
1. Open `joining_process_page.py`.
2. Add a prominent filter / toggle bar at the top of the Candidate Table:
   - Button 1: **"All Candidates"**
   - Button 2: **"🎉 Selected (Pending Welcome Mail) [N]"** (badge showing count of `status == 'Selected' AND welcome_email_sent == 0`).
3. Add a batch action button: **"✉️ Review & Send Welcome Emails"** when Selected filter is active or candidates are selected.
4. Build the Welcome Email Staging & Review Modal (`show_welcome_email_review_modal`):
   - Shows recipient email, subject: `Welcome to Doctors For You - Selection Confirmation`.
   - Rich editable text body welcoming the candidate, outlining required joining documents, and stating contact person.
   - Buttons: **"🚀 Send Welcome Email"** and **"Cancel"**.
   - On send:
     - Calls `email_service.send_email_smtp(...)` with friendly non-blocking progress indicator.
     - Calls `db_manager.update_candidate_welcome_email_status(candidate_id, True)`.
     - Logs event in `email_log`.
     - Displays success snackbar and refreshes the candidate list.

**Verification script**:
Create `desktop_app/scripts/test_task5_welcome_email_ui.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager

def run_test():
    db_manager.init_db()
    # Insert candidate marked as Selected
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO candidates (candidate_name, email, mobile, applied_designation, status, welcome_email_sent)
        VALUES ('Welcome Email Test', 'welcome_test@example.com', '9811122233', 'Staff Nurse', 'Selected', 0)
    """)
    conn.commit()
    cand_id = cur.lastrowid

    # Verify candidate appears in pending welcome list
    pending = db_manager.get_selected_candidates_pending_welcome()
    pending_ids = [p["id"] for p in pending]
    assert cand_id in pending_ids, "Candidate not found in pending welcome email list"

    # Update status to sent
    db_manager.update_candidate_welcome_email_status(cand_id, sent=True)
    pending_after = db_manager.get_selected_candidates_pending_welcome()
    assert cand_id not in [p["id"] for p in pending_after], "Candidate still in pending list after marking sent"

    # Cleanup
    cur.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
    conn.commit()
    print("SUCCESS: Task 5 Welcome Email Staging logic verified.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task5_welcome_email_ui.py`

---

### Task 6: Smart Document Pipeline & Staging Hub UI

**Files to modify**:
- [`desktop_app/pages/document_generation_page.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/pages/document_generation_page.py)

**Step-by-step instructions**:
1. Transform `document_generation_page.py` into a 2-Tab Power Hub:
   - **Tab 1: 🔍 Smart Detection & Generator**
     - Displays candidates requiring documents detected by `smart_rule_detector`.
     - Table Columns: Checkbox, Employee No, Candidate Name, Trigger Reason, Suggested Document Badge, Override Dropdown, Actions.
     - Action Bar: **"⚡ Generate Selected to Staging Queue"** (with progress indicator).
   - **Tab 2: 📋 Staging & Final Review Hub (Human-in-the-Loop)**
     - Displays all records from `document_staging` with status `'Staged'`.
     - Table Columns:
       1. Select Checkbox.
       2. Candidate Name & Employee Code.
       3. Document Type Badge.
       4. Recipient Email.
       5. Health Check Pill (`✅ Ready` or `⚠️ Issues` with tooltip).
       6. Format Toggle: PDF / DOCX radio or dropdown (defaults to PDF).
       7. Actions:
          - 👁️ **Preview**: Opens generated `.pdf` or `.docx` in OS default application.
          - ✏️ **Fix Details**: Opens modal to edit Name, Salary, Designation, or Email $\rightarrow$ instantly saves and triggers `document_staging_service.inline_fix_and_regenerate`.
          - 🗑️ **Discard**: Removes from staging without sending.
     - Sticky Footer Action Bar:
       - Selected count pill.
       - **`[ 🚀 Final Go: Dispatch Selected (N Documents) ]`** button in primary branding color with rocket icon.
       - Confirmation modal summarizing recipient names, document types, and format before dispatching.
       - Asynchronous execution with live progress bar and final summary dialog.

**Verification script**:
Create `desktop_app/scripts/test_task6_staging_hub_integration.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager
from services import smart_rule_detector, document_staging_service

def run_test():
    db_manager.init_db()
    # 1. Run detection
    suggestions = smart_rule_detector.scan_all_candidates_for_document_needs()
    print(f"Smart Detector found {len(suggestions)} actionable suggestions.")

    # 2. Verify staging queue fetch
    staged = db_manager.get_staging_records(status="Staged")
    print(f"Staging Queue currently has {len(staged)} staged records.")
    print("SUCCESS: Task 6 Staging Hub UI backend integration verified.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task6_staging_hub_integration.py`

---

### Task 7: Executive Dashboard Live Action Cards

**Files to modify**:
- [`desktop_app/pages/dashboard_page.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/pages/dashboard_page.py)
- [`desktop_app/services/dashboard_service.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/services/dashboard_service.py)

**Step-by-step instructions**:
1. Open `dashboard_service.py`:
   - Add metrics:
     - `pending_welcome_emails`: count of candidates `status = 'Selected' AND welcome_email_sent = 0`.
     - `letters_to_generate`: count from `smart_rule_detector.scan_all_candidates_for_document_needs()`.
     - `staged_letters_ready`: count of `document_staging` where `status = 'Staged'`.
     - `dispatched_today`: count of emails dispatched today from `email_log`.
2. Open `dashboard_page.py`:
   - Replace or enhance the top stat cards with 4 clickable Action Cards:
     1. **"Pending Welcome Emails"** (Gold badge) $\rightarrow$ clicking navigates to Joining Process with Selected filter active.
     2. **"Identified Letters to Generate"** (Blue badge) $\rightarrow$ clicking navigates to Document Generation (Tab 1: Smart Detector).
     3. **"Staged Letters Ready for Final Go"** (Green badge with rocket) $\rightarrow$ clicking navigates to Document Generation (Tab 2: Staging Queue).
     4. **"Total Candidates in Pipeline"** (Indigo badge) $\rightarrow$ clicking navigates to Joining Process.
   - Add a recent dispatch history preview card at the bottom.

**Verification script**:
Create `desktop_app/scripts/test_task7_dashboard_metrics.py`:
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import dashboard_service

def run_test():
    stats = dashboard_service.get_dashboard_stats()
    print("Dashboard Stats retrieved:", stats)
    assert "pending_welcome_emails" in stats
    assert "staged_letters_ready" in stats
    assert "letters_to_generate" in stats
    print("SUCCESS: Task 7 Dashboard action metrics verified.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task7_dashboard_metrics.py`

---

### Task 8: 1-Click Desktop Launcher

**Files to create**:
- [`Launch_DFY_HRMS.bat`](file:///d:/ignou/Suraj%20HR%20Project/Launch_DFY_HRMS.bat)

**Step-by-step instructions**:
1. Create `Launch_DFY_HRMS.bat` in the repository root.
2. Script logic:
   - Disables command echoing (`@echo off`).
   - Sets title to `Doctors For You - HR Operations Platform`.
   - Locates Python interpreter:
     - Checks local virtual environments (`.venv\Scripts\python.exe` or `venv\Scripts\python.exe`).
     - Falls back to system `python` in `PATH`.
   - Checks if dependencies are present; if `flet` or `docx` is missing, displays a helpful prompt.
   - Launches `desktop_app\main.py` seamlessly without requiring terminal knowledge.
   - Keeps window open with a friendly message if Python encounters a startup error.

**Verification script**:
Create `desktop_app/scripts/test_task8_launcher.py`:
```python
import os

def run_test():
    launcher_path = "Launch_DFY_HRMS.bat"
    assert os.path.exists(launcher_path), "Launch_DFY_HRMS.bat does not exist"
    with open(launcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "main.py" in content, "Launcher does not target main.py"
    assert "python" in content.lower(), "Launcher does not reference python"
    print("SUCCESS: Task 8 Desktop Launcher exists and contains proper bootstrap commands.")

if __name__ == "__main__":
    run_test()
```
**Verification command**:
`python desktop_app/scripts/test_task8_launcher.py`

---

### Task 9: End-to-End Integration Verification & Full Regression Suite

**Files to create**:
- [`desktop_app/scripts/test_task9_full_pipeline_e2e.py`](file:///d:/ignou/Suraj%20HR%20Project/desktop_app/scripts/test_task9_full_pipeline_e2e.py)

**Step-by-step instructions**:
1. Run end-to-end integration flow programmatically:
   - Simulate Flow 1: Ingest candidate $\rightarrow$ Mark Selected $\rightarrow$ Queue welcome email $\rightarrow$ Mark dispatched.
   - Simulate Flow 2: Smart detect document type from Keka data.
   - Simulate Flow 3: Generate draft to Staging Queue $\rightarrow$ Inspect anomaly warnings $\rightarrow$ Perform inline fix $\rightarrow$ Verify instant re-generation.
   - Simulate Flow 4: Trigger Final Go dispatch $\rightarrow$ Verify sequence number consumption and audit logging.
2. Run full regression suite across existing test files:
   - `test_74_column_keka_master.py`
   - `test_document_generation.py`
   - `test_email_improvements.py`
   - `test_full_platform_end_to_end.py`

**Verification command**:
`python desktop_app/scripts/test_task9_full_pipeline_e2e.py`

---

## 3. Self-Review & Adherence to Constraints

- **YAGNI / Simplicity**: Built directly on top of existing SQLite database, Flet components, and Word templates. No external microservices or heavy message brokers needed.
- **Reference Number Safety**: Sequence numbers are strictly protected and incremented only upon final dispatch ("Final Go").
- **Windows File Safety**: All file writes and reads use safe contexts to prevent Windows `[WinError 32]` file locking.
- **Graceful PDF Fallback**: Utilizes `win32com.client` Word COM automation already present on the system; falls back gracefully to `.docx` if Word is unavailable.
- **User Tone**: Zero technical error messages shown to HR users; plain English throughout.
