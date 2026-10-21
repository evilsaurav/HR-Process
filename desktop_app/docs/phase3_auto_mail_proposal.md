# Phase 3 Proposal: Auto Mail System for DFY HRMS Desktop

**Document Version:** 1.0.0 (Proposal & Feasibility Review)  
**Status:** DRAFT / UNDER REVIEW  
**Author:** AI Pair Programmer & System Architect  
**Audience:** Suraj Mani (HR & Product Lead), Saurav Kumar (Engineering Lead)  

---

## Executive Summary

Phase 3 introduces an automated and assisted email dispatch mechanism to the DFY HRMS Desktop platform. The objective is to eliminate repetitive manual emailing of offer letters, onboarding packets, increment letters, experience certificates, and interview communications, while strictly maintaining DFY's core principles: **non-technical HR simplicity, preview-before-dispatch safety, zero data loss, and rock-solid privacy**.

This document reviews existing infrastructure, outlines workflow trigger points, proposes minimal schema extensions, explores UI placement options, and surfaces crucial open questions for executive alignment prior to writing any implementation code.

---

## 1. Existing Email Infrastructure Review

### 1.1 In `desktop_app/`
A review of the active desktop codebase reveals that foundational email credentials and basic SMTP/OAuth connectivity are already present:

1. **Service Layer (`desktop_app/services/email_service.py`)**:
   - `test_app_password(email_address, app_password)`:
     - Connects via `smtplib.SMTP_SSL("smtp.gmail.com", 465)` with a 10s timeout.
     - Authenticates and returns `(success: bool, message: str)`.
   - `send_mail_app_password(email_address, app_password, to_addr, subject, body, attachment_path=None)`:
     - Uses Python's standard `email.mime.multipart.MIMEMultipart`, `MIMEText("plain")`, and `MIMEBase`.
     - Supports attaching a single binary file with base64 encoding and `Content-Disposition`.
     - Dispatches via `smtplib.SMTP_SSL("smtp.gmail.com", 465)`.
   - `test_oauth(credentials_json_path)` and `get_oauth_credentials(credentials_json_path)`:
     - Implements Google OAuth2 `InstalledAppFlow` using `google_auth_oauthlib`.
     - Requests scopes for both Gmail Send (`gmail.send`) and Google Drive Backup.
     - Persists token pickle at `desktop_app/credentials/token.pickle`.
   - `backup_database_to_drive(...)`:
     - Operational backup routine uploading `hrms.db` to Google Drive.

2. **Settings Layer (`desktop_app/pages/settings_page.py` & `desktop_app/database/db_manager.py`)**:
   - The Settings page already provides a dedicated **Gmail Configuration** card with a radio toggle (`App Password` vs `OAuth2`).
   - Input fields exist for `Gmail Address`, `16-digit App Password`, and `OAuth credentials.json path`.
   - Credentials are saved and verified in SQLite's `api_keys` table under provider `"Gmail"` (`gmail_method`, `gmail_email`, `gmail_app_password`, `gmail_credentials_path`).
   - A live "Test Gmail Connection" button verifies authentication before use.

3. **Candidate Email Storage (`desktop_app/database/db_manager.py`)**:
   - The `candidates` table contains an indexed `email` column populated during spreadsheet ingestion (`sheet_processor.py`) and editable in Document Generator.

### 1.2 In Legacy Parent Repository (`main.py` CustomTkinter)
The parent project contains a mature batch email dispatch implementation in the root `main.py` (lines 1215–1470):
- **Port flexibility:** Supports both SSL (Port 465) and STARTTLS (Port 587) with fallback.
- **CC / BCC support:** Handles comma-separated CC and BCC recipients.
- **Template substitutions:** Uses basic placeholder replacement in subject and body.
- **Asynchronous worker thread:** Runs mail dispatch in background threads (`threading.Thread`) via a progress queue to prevent freezing the GUI.
- **Batch throttling:** Employs pauses between sends to stay under Gmail daily relay rate limits.

### 1.3 Reusable vs. Needed From Scratch

| Component | Status | Details |
| :--- | :--- | :--- |
| **Credential Storage & Test** | ✅ **Reusable** | Already functional in `settings_page.py` and `db_manager.py`. |
| **Basic SMTP Send Logic** | ✅ **Reusable** | `email_service.send_mail_app_password` works for plain text + single attachment. |
| **Candidate Email Data** | ✅ **Reusable** | Candidates already have email addresses stored in SQLite. |
| **Generated Document Files** | ✅ **Reusable** | `document_generation_log` records exact filesystem paths to generated `.docx` letters. |
| **HTML Email Templating** | ⚠️ **Needs Building** | Current service only sends plain-text emails. Professional corporate communications require clean HTML layouts with styling, DFY branding, and dynamic placeholders. |
| **Document Format for Attachments** | ⚠️ **Needs Building** | Currently documents are generated as `.docx`. Candidates typically expect `.pdf` attachments. A conversion or attachment strategy is required. |
| **Email Audit Log (`email_log`)** | ⚠️ **Needs Building** | No historical table tracks when emails were sent, to whom, with what attachment, or if delivery failed. |
| **Pre-Send Review Modal / UI** | ⚠️ **Needs Building** | An interactive confirmation dialog where HR can review the recipient, subject, body, and attachment before pressing "Send". |
| **Error Handling & Plain Messages** | ⚠️ **Needs Building** | The current `email_service.py` returns raw exception strings (`str(e)`). A user-friendly error translator is required. |

---

## 2. Candidate Trigger Points for Auto Mail

Below is a systematic breakdown of realistic email trigger points across the DFY HRMS lifecycle.

> [!IMPORTANT]
> **Philosophy Note:** In alignment with our Document Generator workflow (Preview → Verify → Confirm), all external candidate-facing communications are recommended as **HR-reviewed-then-click-send** rather than silent background triggers. Silent automation risks emailing candidates incomplete drafts or incorrect offer terms.

### 2.1 Workflow Triggers & Recommended Automation Modes

| # | Trigger Event | Target Recipient | Email Purpose & Attachment | Proposed Mode | Recommendation Rationale |
| :- | :--- | :--- | :--- | :--- | :--- |
| **T1** | **Offer Letter Finalized** (Doc Gen) | Candidate | Official Offer Letter delivery with compensation summary, joining date, and acceptance deadline. Attachment: Generated Offer Letter. | **HR-Reviewed-Then-Send** *(Recommended)* | **Highest sensitivity.** HR must inspect the finalized letter, confirm candidate email address, and optionally add personalized notes before sending. |
| **T2** | **Candidate Marked "Interview"** (Joining Process) | Candidate | Interview Invitation with date, time, interview mode (virtual/office), reporting location, and contact person. | **HR-Reviewed-Then-Send** *(Recommended)* | Requires interview scheduling details (date/time/interviewer) not currently stored in the candidate table. A prompt/modal is essential. |
| **T3** | **Candidate Marked "Joined"** (Joining Process or Keka Sync) | Candidate & Internal HR/IT | Welcome Email & Onboarding Packet. Welcome message, reporting guidelines, document submission checklist. | **HR-Reviewed-Then-Send** *(Option A)* or **Automatic** *(Option B)* | Safe for templated welcoming, but HR may prefer reviewing to ensure joining was physically verified. |
| **T4** | **Candidate Marked "Rejected"** (Joining Process) | Candidate | Courteous Rejection Notice thanking the applicant for their time and interest. | **HR-Reviewed-Then-Send** *(Recommended)* | Accidental status toggles shouldn't immediately trigger rejection emails to candidates. |
| **T5** | **Annual Increment Letter Finalized** (Doc Gen) | Active Employee | Official Annual Increment Notice with revised salary structure and effective date. Attachment: Increment Letter. | **HR-Reviewed-Then-Send** *(Recommended)* | Executive compensation communication. HR must verify figures before delivery. |
| **T6** | **Experience / Salary Certificate Finalized** (Doc Gen) | Relieved Employee | Official Relieving & Experience Certificate delivery. Attachment: Experience Certificate. | **HR-Reviewed-Then-Send** *(Recommended)* | Relieved employees often communicate via personal email. Delivery must be explicitly confirmed by HR. |
| **T7** | **Increment Due / Certificate Due Reminder** (Dashboard) | Internal HR / Management | Internal Reminder Digest: List of upcoming tenure milestones (e.g., 3 candidates completing 1 year next month). | **Automatic Digest** *(Recommended)* | Safe for internal eyes only. Can be triggered on app launch or weekly summary without emailing candidates. |

---

## 3. Proposed Database Changes (Conceptual Schema)

To ensure audit compliance, idempotency (never accidentally re-sending the same offer letter), and transparent history, the following two tables are conceptually proposed:

### 3.1 `email_log` (Audit & Dispatch History)
Tracks every email sent through the application.

```sql
CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER REFERENCES candidates(id),
    recipient_email TEXT NOT NULL,
    recipient_name TEXT,
    email_type TEXT NOT NULL,          -- e.g. 'offer_letter', 'interview_invite', 'welcome', 'increment', 'experience_cert'
    subject TEXT NOT NULL,
    body_text TEXT,                    -- Sanitized plain text or HTML snapshot
    attachment_name TEXT,              -- e.g. 'DFY-102_Rohan_Sharma_offer_letter.docx'
    attachment_path TEXT,              -- Full filesystem path to attached file
    status TEXT NOT NULL,              -- 'SENT', 'FAILED', 'QUEUED'
    error_message TEXT,                -- Plain language error if failed
    sent_by TEXT DEFAULT 'HR Admin',   -- User / actor
    sent_at TEXT NOT NULL              -- ISO timestamp: YYYY-MM-DD HH:MM:SS
);

CREATE INDEX IF NOT EXISTS idx_email_log_candidate ON email_log(candidate_id);
CREATE INDEX IF NOT EXISTS idx_email_log_sent_at ON email_log(sent_at);
```

### 3.2 `email_templates` (Standardized Communications)
Stores editable default email templates so HR doesn't have to retype boilerplate emails.

```sql
CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key TEXT UNIQUE NOT NULL, -- e.g. 'offer_letter', 'interview', 'welcome', 'rejection', 'increment', 'experience_cert'
    title TEXT NOT NULL,               -- e.g. 'Official Offer Letter Template'
    subject_template TEXT NOT NULL,    -- e.g. 'Job Offer: {DESIGNATION} at Doctors For You - {CANDIDATE_NAME}'
    body_template TEXT NOT NULL,       -- Template string with {CANDIDATE_NAME}, {JOINING_DATE}, {SALARY}, etc.
    default_cc TEXT,                   -- Optional default CC (e.g. hr@doctorsforyou.org)
    is_active INTEGER DEFAULT 1,
    last_updated TEXT NOT NULL
);
```

---

## 4. Proposed UI Touchpoints

### Architecture Dilemma: Dedicated Page vs. In-Context Actions?
- **Option 1: Dedicated 6th Page ("Mail Center") on Sidebar**
  - *Pros:* Centralized view for browsing sent email logs, viewing failed dispatches, and editing global email templates.
  - *Cons:* Disconnects the action from where documents are created. HR would have to finalize an offer on page 4, then navigate to page 6 to search for the candidate and send the email.
- **Option 2: Purely In-Context Buttons on Existing Pages**
  - *Pros:* Natural flow. Finalize offer → click "Send Email to Candidate" immediately.
  - *Cons:* No place to view sent history or manage templates.

### Recommended Hybrid Layout:
1. **Primary Trigger Touchpoint: In-Context inside `document_generation_page.py`**
   - In the "Final Document Generated Successfully!" confirmation card, add a primary green action button:  
     `✉️ Send Document via Email to Candidate`
   - Clicking this opens a **Review & Send Email Modal**:
     - Pre-fills Candidate Email, Candidate Name.
     - Pre-fills Subject and Body using the relevant template.
     - Displays attached document pill (`DFY-102_Rohan_Sharma_offer_letter.docx`).
     - Includes editable message field and "Send Email" / "Cancel" buttons.
   - Updates the recent history table on that page with an "Email Status" badge (`Sent ✅` or `Not Sent`).

2. **Secondary Touchpoint: Quick Send in `dashboard_page.py` & `joining_process_page.py`**
   - Candidate row action or due-list row action can have a subtle `✉️` button for direct dispatch.

3. **Management & Audit Touchpoint: Integrated Tab in `settings_page.py` or 6th Page (`Mail Center`)**
   - If keeping to 5 pages: Expand `settings_page.py` or add a sub-tab for "Email Templates & Sent History".
   - If expanding to 6 pages: Add "Mail Center" to Navigation Rail showing an executive dispatch log table with filter by candidate / date / status, plus a template editor.

---

## 5. Open Questions for Human Decision

Before Phase 3 implementation begins, executive decisions are requested on the following strategic questions:

1. **Attachment File Format (.docx vs .pdf):**
   - Currently, all documents are generated in `.docx` format using `python-docx`.
   - Candidates opening `.docx` files on mobile devices frequently encounter formatting glitches or accidental edits.
   - *Question:* Should we send `.docx` files directly, or should Phase 3 incorporate a headless `.docx` → `.pdf` conversion pipeline (e.g. via LibreOffice CLI, `docx2pdf` requiring MS Word installed, or a python renderer) so candidates receive immutable PDFs?

2. **Degree of Automation (Manual Confirmation vs Background Daemon):**
   - *Question:* Should **all** emails strictly require an HR user to review in a dialog and click "Send", or should any specific emails (e.g. automated welcome email when status becomes "Joined") fire silently in the background?
   - *Recommendation:* Strict manual preview-and-send for all candidate communications.

3. **Email Formatting & Corporate Branding:**
   - *Question:* Should emails be clean, high-deliverability plain text, or formatted HTML with the official "Doctors For You" header banner, contact card, and signature?

4. **Sender Identity & CC/BCC Policy:**
   - *Question:* When emails are sent, which address should be the `From:` sender?
     - Individual HR user's Gmail?
     - A centralized corporate mailbox (e.g., `hr@doctorsforyou.org`)?
     - Should every offer letter email automatically BCC a centralized HR archive inbox for compliance?

5. **Template Customization:**
   - *Question:* Should email templates be hardcoded defaults with dynamic placeholders, or do HR users need an in-app visual template editor in Settings to adjust standard phrasing per project?

6. **Daily Gmail Sending Limits & Rate Throttling:**
   - Standard free Gmail accounts have a sending limit of 500 emails/day; Google Workspace accounts have 2,000/day.
   - *Question:* Is individual dispatch sufficient, or does DFY HR anticipate needing bulk mass-dispatch (e.g., emailing 100 interview candidates at once)?

---

## 6. Next Steps

1. **Review & Decisions:** Human leadership reviews the 6 open questions above and indicates preferences.
2. **Phase 3 Specification:** Finalize the precise feature scope based on decisions.
3. **Execution Plan:** Break down Phase 3 into isolated, test-driven implementation chunks (Service layer → Database schema → UI modal integration → Audit logging).
