# Doctors For You (DFY) — HR Operations Platform & Smart Document Staging Pipeline

A production-ready, offline-first Desktop HRMS Application built with Python and Flet for managing candidate interviews, Keka HRMS synchronization, smart document generation (Offer Letters, Extension Letters, Increment Letters, Experience & Relieving Certificates, Termination Letters), human-in-the-loop review staging, and automated email dispatch.

---

## 🚀 Quick Start Guide (For Any Windows Computer)

You do **NOT** need to open a command prompt or type commands manually. Everything is automated via 1-click batch scripts.

### Step 1: Install Python (If not already installed)
1. Download Python 3.10 or higher from: https://www.python.org/downloads/
2. **IMPORTANT**: During installation on the very first screen, check the box:
   `☑ Add python.exe to PATH`
3. Click **Install Now**.

### Step 2: Install Required Libraries (One-Time Setup)
- Double-click on:
  ```
  Install_Dependencies.bat
  ```
  *(This automatically installs Flet, Pandas, python-docx, PyWin32, OpenPyXL, and Cryptography).*

### Step 3: Run the Application
- Double-click on:
  ```
  Launch_DFY_HRMS.bat
  ```
- **Optional**: To place a shortcut directly on your Windows Desktop, open Command Prompt in this folder and run:
  ```cmd
  Launch_DFY_HRMS.bat --create-shortcut
  ```

---

## 📦 How to Share / Zip This App to Another System

### Option A: Zip the Entire Project Folder (Recommended)
Simply right-click the project folder `Suraj HR Project` ➔ **Send to** ➔ **Compressed (zipped) folder**.
- Send that `.zip` file to any other computer.
- Unzip it anywhere (e.g. `C:\DFY_HRMS` or Desktop).
- Double-click `Install_Dependencies.bat` (first time only) then double-click `Launch_DFY_HRMS.bat`.
- Everything works out of the box with all databases, logos, and templates included!

### Option B: Zip Only the `desktop_app` Folder
We have made `desktop_app` **100% self-contained**:
- Inside `desktop_app`, it now contains:
  - `Launch_DFY_HRMS.bat` (1-click desktop runner)
  - `Install_Dependencies.bat` (1-click dependency installer)
  - `requirements.txt` (exact package list)
  - `data/` (`hrms.db` and encryption keys)
  - `assets/` (organization logos)
  - `templates/` (all Word document templates for Offer, Extension, Increment, Termination, and Certificates)
  - `pages/` & `services/` (complete application logic)
- If you zip only `desktop_app`, the recipient simply extracts it and runs `Launch_DFY_HRMS.bat`.

---

## 🛠️ Key Modules & Capabilities

### 1. Executive Dashboard (`pages/dashboard_page.py`)
- Real-time command center showing live counts:
  - **🎉 Pending Welcome Emails**: Count of selected candidates needing welcome emails. Click navigates directly to the review queue.
  - **🔍 Letters to Generate**: Staff detected from Keka sheets needing official letters. Click opens Smart Detector.
  - **🚀 Staged Ready for Final Go**: Letters generated and waiting in the staging quality gate. Click opens Staging Review Queue.
  - **👥 In Pipeline / Interviews**: Active applicants across the interview lifecycle.
- Live operations activity log showing recent email dispatches and generated documents.

### 2. Candidate Joining Process (`pages/joining_process_page.py`)
- Ingest candidate screening sheets (`.xlsx` or `.csv`).
- Handles candidates who interview 2–5 times across different rounds/roles with duplicate detection warnings.
- Filter tab: **`🎉 Selected (Pending Welcome Email) [N]`** displays selected candidates.
- Click **`✉️ Review & Send Welcome Emails`** to preview personalized congratulatory emails, edit text if needed, and dispatch in bulk.

### 3. Keka Master Synchronization & Duplicate Protection (`pages/keka_sync_page.py`)
- Ingest 74-column Keka Master Sheets (`.xlsx`, `.csv`).
- **Auto-Offset Detection**: Automatically detects report headers even if Keka inserts company banners on Row 0 and Row 1.
- **Zero Duplicate Employee Guarantee**:
  - Employee IDs are strictly unique per staff member.
  - **Pre-Sync Warning & Resolution Dialog**: If the same employee ID or a sheet re-upload is detected, the system gives a clear warning showing field-by-field differences (e.g. Salary, Designation) and asks:
    - `🔄 Update Existing with Sheet Data`: Updates the existing database record cleanly.
    - `🛡️ Keep Database Records (Skip Sheet Duplicates)`: Preserves current database records and only imports new staff.

### 4. Smart Document Pipeline & Staging Hub (`pages/document_generation_page.py`)
- **Tab 1: 🔍 Smart Detection & Generator**
  - Evaluates employee status against Keka data:
    - *Joined / Active without prior offer* ➔ **Offer Letter**
    - *Extension of Service Till present* ➔ **Extension Letter**
    - *Salary revision detected* ➔ **Increment Letter**
    - *Exit Date / Resignation present* ➔ **Experience & Relieving Certificate**
    - *Termination reason present* ➔ **Termination Letter**
  - Inline HR dropdown override for any document type.
  - Generates drafts into the staging queue with non-consuming sequence numbers.
- **Tab 2: 📋 Staging & Final Review Hub (Human-in-the-Loop Quality Gate)**
  - Review all generated drafts before anything is sent.
  - **👁️ Preview**: 1-click preview in Microsoft Word or default PDF viewer.
  - **✏️ Fix Details**: Edit name, salary, dates, or designation ➔ **instantly regenerates the document** and updates the preview.
  - **Format Toggle**: Select `PDF` (default) or `DOCX` per candidate.
  - **`[ 🚀 Final Go: Dispatch Selected ]`**: Atomically consumes official reference numbers sequentially, re-stamps documents, sends emails with attachments, and records permanent audit logs.
- **Tab 3: ✍️ Manual One-Off Generator**
  - Manually select any candidate and generate custom letters on demand.

### 5. Settings & Configurations (`pages/settings_page.py`)
- **SMTP Email Configuration**: Configure company email (Gmail, Outlook, DFY server) with encrypted password storage.
- **AI API Keys**: Optional integration for Gemini, Groq, NVIDIA, OpenAI for smart letter summaries (works 100% offline if no API key is provided).
- **Reference Number Sequence**: Configure organization reference format (e.g., `DFY/HR/{YYYY}/{SEQ}`) and current counter.

---

## 📋 System Requirements
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10, 3.11, 3.12, or higher
- **Microsoft Word / Office** (Recommended for automated Word-to-PDF conversion via Word COM automation; if Word is not installed, the system automatically falls back to `.docx` delivery without crashing).

---

## 📞 Support & Maintenance
Developed for **Doctors For You (DFY)** HR Operations.  
Maintained by the HR Technical Automation Team.
