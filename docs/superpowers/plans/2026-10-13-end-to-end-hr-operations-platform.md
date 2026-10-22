# End-to-End HR Operations Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade, non-overcomplicated, end-to-end HR Operations pipeline supporting Option C (Hybrid): Candidate Screening & Joining -> Rich Keka 25+ Field Master Ingestion -> Template Document Generation with Full Keka Placeholders -> Human-in-the-Loop Pre-Mail Review & Fix -> Immediate & Scheduled Email Dispatch with AI Assistance.

**Architecture:** A layered architecture using SQLite for persistent storage, Python-Docx for placeholder templating, smtplib for email delivery with schedule queueing, Flet for responsive desktop UI, and an offline-first AI service (heuristic regex rules with optional LLM API fallback for column auto-mapping, anomaly auditing, and email cover drafting).

**Tech Stack:** Python 3.11+, Flet 1.0.4, SQLite 3, python-docx, pandas, openpyxl, smtplib, requests.

**Spec:** In-conversation requirements agreed with HR lead Suraj Mani and Engineering lead Saurav Kumar (Option C Hybrid Architecture).

## Global Constraints
- Plain language in all UI dialogs, notices, and errors (zero technical jargon, zero raw tracebacks).
- 100% data preservation guarantee: empty Excel cells must never overwrite existing database values.
- Atomic database transactions with rollback on failures.
- Non-breaking backward compatibility with existing Joining Process, Doc Gen, and Keka Sync pages.
- Offline-resilient: core operations (matching, doc generation, validation) must function 100% offline; AI features use deterministic heuristic rules when no API key or internet is present.

---

### Task 1: Keka Master Data Schema Migration in SQLite

**Files:**
- Modify: `desktop_app/database/db_manager.py:45-90`
- Test: `desktop_app/scripts/test_keka_schema_migration.py`

**Interfaces:**
- Consumes: Existing `candidates` table in SQLite (`DB_PATH`).
- Produces: 25+ new nullable columns in `candidates` table supporting Keka Master Report fields, plus `get_keka_master_fields()` specification helper.

- [ ] **Step 1: Write the test script for schema migration**

Create `desktop_app/scripts/test_keka_schema_migration.py`:
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_manager

def test_migration():
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(candidates)")
    cols = {row[1] for row in cur.fetchall()}
    conn.close()

    expected_cols = [
        "employee_number", "first_name", "last_name", "display_name",
        "work_email", "personal_email", "date_of_birth", "gender",
        "marital_status", "marriage_date", "current_address", "permanent_address",
        "father_name", "mother_name", "spouse_name", "department",
        "job_title", "reporting_to", "reporting_manager_emp_no", "date_joined",
        "employment_status", "worker_type", "time_type", "leave_plan",
        "shift_policy", "weekly_off_policy", "notice_period", "pan_number",
        "aadhaar_number", "pf_number", "uan_number", "exit_date",
        "exit_status", "termination_type", "termination_reason", "cost_center"
    ]
    for col in expected_cols:
        assert col in cols, f"Missing column: {col}"
    print("Schema migration verification: PASS")

if __name__ == "__main__":
    test_migration()
```

- [ ] **Step 2: Run test to verify it fails on missing columns**

Run: `python desktop_app/scripts/test_keka_schema_migration.py`
Expected: Assertion error indicating missing Keka columns.

- [ ] **Step 3: Update `db_manager.py` with idempotent migration**

In `desktop_app/database/db_manager.py`, expand `new_candidate_columns` inside `init_db()`:
```python
        # Rich Keka Master Fields
        ("first_name", "TEXT"),
        ("last_name", "TEXT"),
        ("display_name", "TEXT"),
        ("work_email", "TEXT"),
        ("personal_email", "TEXT"),
        ("date_of_birth", "TEXT"),
        ("marital_status", "TEXT"),
        ("marriage_date", "TEXT"),
        ("current_address", "TEXT"),
        ("permanent_address", "TEXT"),
        ("mother_name", "TEXT"),
        ("spouse_name", "TEXT"),
        ("job_title", "TEXT"),
        ("reporting_to", "TEXT"),
        ("reporting_manager_emp_no", "TEXT"),
        ("employment_status", "TEXT"),
        ("worker_type", "TEXT"),
        ("time_type", "TEXT"),
        ("leave_plan", "TEXT"),
        ("shift_policy", "TEXT"),
        ("weekly_off_policy", "TEXT"),
        ("notice_period", "TEXT"),
        ("pan_number", "TEXT"),
        ("aadhaar_number", "TEXT"),
        ("pf_number", "TEXT"),
        ("uan_number", "TEXT"),
        ("exit_date", "TEXT"),
        ("exit_status", "TEXT"),
        ("termination_type", "TEXT"),
        ("termination_reason", "TEXT"),
        ("cost_center", "TEXT"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python desktop_app/scripts/test_keka_schema_migration.py`
Expected: `Schema migration verification: PASS`

---

### Task 2: Rich Keka Sheet Ingestion & Smart Auto-Mapper

**Files:**
- Modify: `desktop_app/services/keka_sync_service.py`
- Create: `desktop_app/services/keka_mapper.py`
- Test: `desktop_app/scripts/test_keka_rich_ingestion.py`

**Interfaces:**
- Consumes: Any Keka Excel/CSV export with 25+ standard columns.
- Produces: `process_rich_keka_sheet(file_path: str, allow_new_inserts: bool = True) -> dict` returning matched count, updated count, newly inserted count, and unmatched rows.

- [ ] **Step 1: Write the failing test for rich Keka sheet processing**

Create `desktop_app/scripts/test_keka_rich_ingestion.py` generating a mock Keka dataframe with standard headers (e.g., `Employee Number`, `First Name`, `Last Name`, `Mobile Phone`, `PAN Number`, `Department`, etc.), calling `keka_sync_service.process_rich_keka_sheet()`, and verifying DB insertion and field mapping.

- [ ] **Step 2: Run test to verify it fails**

Run: `python desktop_app/scripts/test_keka_rich_ingestion.py`
Expected: FAIL (`process_rich_keka_sheet` not found).

- [ ] **Step 3: Implement `keka_mapper.py` with multi-variant column mapping**

Create `desktop_app/services/keka_mapper.py` defining dictionary aliases for all Keka fields and normalized column resolver.

- [ ] **Step 4: Implement `process_rich_keka_sheet` in `keka_sync_service.py`**

Support:
1. Matching by normalized mobile number OR employee code.
2. Updating existing candidate records while preserving non-empty values.
3. If `allow_new_inserts=True` (Option C Hybrid), inserting genuine new employees with status "Joined".
4. Safe date and currency formatting.

- [ ] **Step 5: Run test to verify it passes**

Run: `python desktop_app/scripts/test_keka_rich_ingestion.py`
Expected: PASS with 100% data fidelity.

---

### Task 3: Keka Placeholder Engine Expansion for Document Generation

**Files:**
- Modify: `desktop_app/services/document_generation_service.py:58-150`
- Test: `desktop_app/scripts/test_keka_placeholder_generation.py`

**Interfaces:**
- Consumes: Candidate dictionary populated with Keka master fields.
- Produces: `build_placeholder_mapping()` updated to output `{{pan_number}}`, `{{aadhaar_number}}`, `{{pf_number}}`, `{{uan_number}}`, `{{current_address}}`, `{{permanent_address}}`, `{{reporting_to}}`, `{{worker_type}}`, `{{notice_period}}`, etc.

- [ ] **Step 1: Write test for full Keka placeholder resolution**

Create `desktop_app/scripts/test_keka_placeholder_generation.py` testing that all 25+ placeholder tokens resolve properly into sample DOCX template without missing braces or None strings.

- [ ] **Step 2: Run test to verify failure on missing placeholders**

Run: `python desktop_app/scripts/test_keka_placeholder_generation.py`
Expected: Assertion failure for unmapped tokens.

- [ ] **Step 3: Implement extended mappings in `build_placeholder_mapping()`**

Update `document_generation_service.py` to map both lowercase and standard title-case tokens for all new Keka attributes.

- [ ] **Step 4: Run test to verify pass**

Run: `python desktop_app/scripts/test_keka_placeholder_generation.py`
Expected: PASS.

---

### Task 4: AI Anomaly Detector & Email Cover Drafter

**Files:**
- Modify: `desktop_app/services/ai_service.py`
- Test: `desktop_app/scripts/test_ai_hr_utilities.py`

**Interfaces:**
- Consumes: Candidate record dictionary and document type.
- Produces:
  - `audit_candidate_data_completeness(candidate: dict, doc_type: str) -> list[str]`
  - `generate_email_cover(candidate: dict, doc_type: str) -> dict {"subject": str, "body": str}`

- [ ] **Step 1: Write test verifying anomaly detector and draft generator**

Create `desktop_app/scripts/test_ai_hr_utilities.py` verifying that missing PAN or email triggers warnings, and that email cover generator returns polished professional text with candidate name and role.

- [ ] **Step 2: Implement offline-first rule engine with LLM API enhancement**

In `ai_service.py`:
- Implement deterministic regex/rule-based validation for missing PAN, Aadhaar, email syntax, and phone length.
- Implement polite, professional email templates for Offer, Appointment, Extension, and Increment letters.
- If API key (Gemini/Groq/OpenAI) is configured in Settings, optionally enhance the email draft with personalized tone; otherwise return high-grade rule template instantly.

- [ ] **Step 3: Run test to verify pass**

Run: `python desktop_app/scripts/test_ai_hr_utilities.py`
Expected: PASS (runs 100% offline without network dependency).

---

### Task 5: Pre-Mail Verification & Fix Dialog ("Review Before Send")

**Files:**
- Modify: `desktop_app/pages/document_generation_page.py`
- Create: `desktop_app/utils/email_preview_modal.py`
- Test: `desktop_app/scripts/test_pre_mail_verification_flow.py`

**Interfaces:**
- Consumes: Finalized document generation result (candidate, attachment path, reference number).
- Produces: Interactive modal allowing HR to:
  1. Inspect candidate email, subject, body, and attachment.
  2. Edit email address or subject inline on the spot if needed.
  3. View any data warnings detected by the anomaly auditor.
  4. Choose: "Send Immediately" or "Schedule for Later".

- [ ] **Step 1: Write test for email preview and inline edit logic**

Create `desktop_app/scripts/test_pre_mail_verification_flow.py` mocking the pre-mail verification state and confirming validation gates.

- [ ] **Step 2: Implement `email_preview_modal.py` Flet UI component**

Construct clean Flet modern dialog following `ui_theme.py`:
- Recipient email text input (editable).
- Subject text input (editable).
- Body text area (editable, populated by AI/template).
- Attachment pill showing filename, size, and view button.
- Action buttons: "Schedule...", "Send Immediately", "Cancel".

- [ ] **Step 3: Wire into Document Generation Page and Joining Process Page**

Add "Email Letter" button next to finalized letters that launches the verification modal.

- [ ] **Step 4: Run test to verify pass**

Run: `python desktop_app/scripts/test_pre_mail_verification_flow.py`
Expected: PASS.

---

### Task 6: Email Scheduling & Dispatch Queue

**Files:**
- Modify: `desktop_app/database/db_manager.py` (add `scheduled_emails` table)
- Modify: `desktop_app/services/email_service.py`
- Create: `desktop_app/services/email_scheduler_service.py`
- Test: `desktop_app/scripts/test_email_scheduling_queue.py`

**Interfaces:**
- Consumes: Verified email payload (to, subject, body, attachment, schedule_time).
- Produces:
  - `schedule_email(candidate_id, to_email, subject, body, attachment_path, send_at)`
  - `get_pending_scheduled_emails()`
  - `dispatch_due_scheduled_emails()`

- [ ] **Step 1: Write test for scheduling and queue processing**

Create `desktop_app/scripts/test_email_scheduling_queue.py` verifying future scheduling, immediate queueing, and dispatch logging.

- [ ] **Step 2: Add `scheduled_emails` table to `db_manager.py`**

Create table tracking `id`, `candidate_id`, `recipient_email`, `subject`, `body`, `attachment_path`, `scheduled_time`, `status` ('Pending', 'Sent', 'Failed'), `created_at`.

- [ ] **Step 3: Implement `email_scheduler_service.py`**

Methods to enqueue, cancel, list, and trigger dispatch for due items.

- [ ] **Step 4: Run test to verify pass**

Run: `python desktop_app/scripts/test_email_scheduling_queue.py`
Expected: PASS.

---

### Task 7: Full UI Integration & Hybrid Workflow Polish

**Files:**
- Modify: `desktop_app/pages/keka_sync_page.py` (add toggle to import new employees vs update only)
- Modify: `desktop_app/pages/joining_process_page.py` (integrate Option C hybrid navigation pills)
- Modify: `desktop_app/pages/document_generation_page.py` (allow source selection: Pipeline Candidates vs Keka Master)
- Test: `desktop_app/scripts/test_full_platform_end_to_end.py`

**Interfaces:**
- Consumes: All modules from Tasks 1-6.
- Produces: Polished, unified desktop UI with zero crashes, intuitive navigation, and clean production styling.

- [ ] **Step 1: Write end-to-end integration test script**

Create `desktop_app/scripts/test_full_platform_end_to_end.py` simulating full lifecycle:
Candidate sheet upload -> Candidate selection -> Keka sheet ingestion -> Template letter generation -> Pre-mail anomaly check & review -> Instant send & scheduling.

- [ ] **Step 2: Polish Keka Sync page with Rich 25+ field visual indicators**

Show summary cards: Total Ingested, Updated, Newly Onboarded, and Missing Data Alerts.

- [ ] **Step 3: Run end-to-end test and regression test suite**

Run all test scripts in `desktop_app/scripts/` to verify zero regressions.
