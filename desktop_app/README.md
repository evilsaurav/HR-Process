# Doctors For You (DFY) — HR Operations Platform

An enterprise-ready, offline-first Desktop HRMS Application built with Python and [Flet](https://flet.dev/) for managing candidate recruitment pipelines, Keka HRMS synchronization, automated document generation (Offer Letters, Extension Letters, Increment Letters, Experience & Relieving Certificates, Termination Letters), human-in-the-loop review staging, and automated email dispatch.

---

## 🚀 Quick Start Guide (For Any Windows Computer)

You do **NOT** need technical knowledge or to type commands into a command prompt. The application handles virtual environments, dependencies, and execution with a single double-click.

### Step 1: Install Python (If Not Already Installed)
1. Download Python 3.10, 3.11, or 3.12 from: **[https://www.python.org/downloads/](https://www.python.org/downloads/)**
2. **IMPORTANT**: On the very first screen of the Python installer, check the box:  
   `☑ Add python.exe to PATH`
3. Click **Install Now**.

### Step 2: Launch the Application (1-Click)
- Simply double-click on:
  ```
  Launch_DFY_HRMS.bat
  ```
- **What happens behind the scenes:**
  - It automatically checks if Python is available.
  - If any required packages (`flet`, `pandas`, `openpyxl`, `python-docx`, `pywin32`, etc.) are missing, it installs them automatically from `requirements.txt`.
  - It launches the modern desktop application window immediately.

### Step 3 (Optional): Create a Windows Desktop Shortcut
To place a permanent shortcut directly on your Windows Desktop:
- Open a Command Prompt or Terminal in this folder and run:
  ```cmd
  Launch_DFY_HRMS.bat --create-shortcut
  ```
- A shortcut named **"DFY HR Operations Platform"** will instantly appear on your Windows Desktop.

---

## 📦 How to Share & Test This App on Another Computer

This `desktop_app` folder is **100% self-contained and portable**:
- It contains its own local SQLite database (`data/hrms.db`), encryption keys (`data/secret.key`), company assets (`assets/dfy_logo112.png`), complete Word document templates (`templates/`), and offline knowledge base (`knowledge/`).
- **To test on another computer:**
  1. Right-click the `desktop_app` folder ➔ **Send to** ➔ **Compressed (zipped) folder** (or use 7-Zip / WinRAR).
  2. Send the `.zip` file via email, Google Drive, or USB drive to the testing machine.
  3. Extract the `.zip` anywhere on the new machine (e.g. `C:\Users\<Name>\Desktop\DFY_HRMS`).
  4. Double-click `Launch_DFY_HRMS.bat`.
  5. The app will launch smoothly without needing any parent repository files!

---

## 🌟 Key Features & Workflow Guide

### 1. Executive Bento Dashboard (`pages/dashboard_page.py`)
- Real-time command center displaying 4 live, clickable action cards:
  - **🎉 Pending Welcome Emails**: Count of selected interview candidates awaiting official welcome emails. Clicking navigates directly to the review queue.
  - **🔍 Letters to Generate**: Staff members detected from Keka sheets needing official letters. Clicking opens the Smart Detector.
  - **🚀 Staged Ready for Final Go**: Letters generated and waiting in the human-in-the-loop review queue. Clicking opens the Staging Hub.
  - **👥 Total in Pipeline**: Active candidates currently in the screening and interview process.
- **Operations Activity Feed**: Real-time log of recent document dispatches, candidate status changes, and sync events.

### 2. Candidate Joining Process & Multi-Sheet Preview (`pages/joining_process_page.py`)
- **Excel & CSV Upload**: Ingest multi-sheet interview charts (e.g., `PPSA INTERVIEW CHART.xlsx`).
- **Inline Multi-Sheet Visual Inspection**:
  - Interactive tab switcher across workbook sheets (e.g., *Phase 1*, *Phase 2*, *Interview Round 2*).
  - KPI metrics strip showing Candidate Count, Selected, and In-Process tallies.
  - 10-row visual preview data table.
  - Post-ingestion action cards for instant next steps.
- **Multi-Round Interview Tracking**: Candidates who interview 2–5 times across different rounds/roles are tracked with interview history without creating duplicate employee records.
- **Welcome Email Review & Bulk Dispatch**:
  - Filter: `🎉 Selected (Pending Welcome Email) [N]`.
  - Click `✉️ Review & Send Welcome Emails` to preview personalized congratulations emails, edit subject or body text, and dispatch in bulk with a progress bar.

### 3. Keka Master Sync & Zero-Duplicate Protection (`pages/keka_sync_page.py`)
- **74-Column Keka Ingestion**: Supports full Keka HRMS employee master exports (`.xlsx`, `.csv`).
- **Dynamic Header Offset Detection**: Automatically identifies header rows even if Keka inserts multi-row corporate banners at the top of the worksheet.
- **Zero Duplicate Employee Guarantee**:
  - Employee IDs are strictly unique per staff member.
  - **Pre-Sync Warning & Resolution Dialog**: If duplicate employee numbers or a sheet re-upload is detected, the system displays an interactive side-by-side comparison (Current DB vs Incoming Sheet) and offers two clear choices:
    1. `🔄 Update Existing with Sheet Data`: Updates designation, salary, or dates while preserving employee history.
    2. `🛡️ Keep Database Records (Skip Sheet Duplicates)`: Preserves current database records and only imports brand-new employees.

### 4. Smart Document Pipeline & Staging Hub (`pages/document_generation_page.py`)
- **Tab 1: 🔍 Smart Detection & Generator**
  - Analyzes employee records against HR business rules to classify required documents:
    - *Active / Joined without prior offer* ➔ **Offer Letter**
    - *Extension of Service Till present* ➔ **Extension Letter**
    - *Salary revision detected* ➔ **Increment Letter**
    - *Exit Date / Resignation present* ➔ **Experience & Relieving Certificate**
    - *Disciplinary or termination recorded* ➔ **Termination Letter**
  - Allows HR users to override suggested letter types via an inline dropdown.
  - Generates draft letters into the staging queue **without consuming official reference sequence numbers**.
- **Tab 2: 📋 Staging & Final Review Hub (Quality Gate)**
  - **👁️ Preview**: 1-click preview in Microsoft Word or default PDF viewer.
  - **✏️ Fix Details**: Edit employee name, salary, dates, or designation ➔ **instantly regenerates the document** and updates the preview.
  - **Format Selector**: Choose `PDF` (default) or `DOCX` per candidate.
  - **`[ 🚀 Final Go: Dispatch Selected ]`**:
    - Atomically increments and commits official reference numbers sequentially.
    - Re-stamps documents with permanent reference numbers.
    - Converts to PDF (via Microsoft Word COM automation).
    - Dispatches email with the document attached via encrypted SMTP / Gmail API.
    - Writes permanent audit log records.
- **Tab 3: ✍️ Manual One-Off Generator**
  - Select any employee and generate single customized letters on demand.

### 5. Professional Excel Styling & Native OS File Launcher
- **Executive OpenPyXL Styling Engine**:
  - All Excel exports (Candidate lists, Daily Briefings, Unmatched reports) feature DFY Corporate Navy (`#0B5ED7`) headers with bold white text.
  - Subtle ice-blue zebra striping (`#F1F5F9`) for easy reading.
  - Indian Rupee currency formatting (`₹#,##0`) on compensation columns.
  - Auto-fitted column widths preventing cell truncation (`###`).
- **1-Click Native OS File & Folder Launcher**:
  - Every export displays an interactive completion modal with:
    - `📂 Open File`: Instantly opens the file in Excel, Word, or Adobe Reader.
    - `📁 Open Folder`: Opens Windows Explorer with the generated file highlighted.

### 6. Help Center & Offline Hinglish AI Copilot (`pages/help_page.py`)
- **Interactive Knowledge Center**: Searchable step-by-step guides for all platform workflows.
- **100% Offline Hinglish HR Copilot**:
  - Built-in knowledge base containing all 10 Articles of the official **Doctors For You (DFY) HR Policy Manual** (Attendance, Leave Policy, Code of Conduct, Travel Reimbursement, Disciplinary Policy, etc.).
  - Works with zero internet and without requiring third-party AI API keys.
  - HR staff can type questions in English or Hinglish (e.g., *"Casual leave kitni milti hai?"*, *"Travel allowance claim kaise karein?"*) and get instant, accurate answers citing policy articles.

---

## 🛠️ System Requirements & Hardware Support

| Component | Minimum Requirement | Recommended |
|-----------|---------------------|-------------|
| **OS** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Python** | Python 3.10+ | Python 3.11 or 3.12 |
| **Microsoft Office** | Optional (saves as `.docx`) | Microsoft Word 2016+ (enables automated Word-to-PDF conversion) |
| **RAM** | 4 GB | 8 GB or higher |
| **Disk Space** | 250 MB free | 500 MB free |

---

## 🔧 Troubleshooting & FAQ

#### Q: The batch file closes immediately or shows "Python was not found".
**A:** Python is either not installed or was not added to your system PATH. Re-run the Python installer, select **Modify**, and make sure **Add Python to PATH** is checked.

#### Q: How does automated PDF conversion work?
**A:** The application uses Microsoft Word COM automation (`win32com.client`) to convert Word templates to high-fidelity PDF documents. If Microsoft Word is not installed on the machine, the application gracefully saves and emails the `.docx` file instead without crashing.

#### Q: Where are generated files and logs stored?
**A:** 
- Generated documents: `desktop_app/output/generated_documents/`
- Exported Excel reports: `desktop_app/output/`
- Application logs: `desktop_app/logs/hrms_app.log`

---

## 📞 Support & Contacts
Developed for **Doctors For You (DFY)** HR Operations.  
Maintained by the HR Technical Automation Team.
