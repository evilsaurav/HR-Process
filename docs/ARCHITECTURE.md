# DFY HRMS Platform — System Architecture & Technical Design

## 1. System Overview

The **Doctors For You (DFY) HR Operations Platform** is an enterprise-grade, offline-first desktop application engineered in Python and [Flet](https://flet.dev/) (Flutter-backed UI framework). It automates and streamlines the entire end-to-end human resources lifecycle across 50+ designations:

1. **Candidate Screening & Joining Pipeline**: Ingests multi-sheet recruitment trackers, detects multi-round interviews, and stages welcome communications.
2. **Keka Master Sync & Duplicate Protection**: Ingests 74-column Keka reports with dynamic banner offset handling and interactive duplicate employee resolution.
3. **Smart Rule Engine**: Evaluates staff employment metrics against 5 core document categories (Offer, Extension, Increment, Relieving/Experience, and Termination).
4. **Staging Review Queue ("Quality Gate")**: Allows human-in-the-loop review, inline editing with real-time document regeneration, and PDF/DOCX format selection before official numbers are committed.
5. **Bulk Dispatch & Audit Hub**: Sequentially burns official reference numbers, renders Word and PDF letters, dispatches via SMTP or Gmail OAuth, and writes immutable audit logs.
6. **Executive Analytics & Professional Export Engine**: Live Bento command center with openpyxl professional styling (DFY navy branding, zebra striping, currency formatting) and 1-click OS file/folder launchers.
7. **Offline DFY HR Policy & Help Copilot**: Built-in 10-Article DFY manual search with Hinglish fallback support that functions with zero internet and without requiring third-party AI keys.

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph UI_Layer [Presentation Layer - Flet Desktop GUI]
        DASH[Executive Bento Dashboard]
        JOIN[Candidate Joining & Multi-Sheet Preview]
        KEKA[Keka Master Sync & Duplicate Guard]
        STAGE[Smart Rule Detector & Staging Hub]
        MANUAL[Manual Document Generator]
        HELP[Help Center & Offline Hinglish Copilot]
        SETT[Settings & Encrypted Credentials]
    end

    subgraph Service_Layer [Business Logic & Service Layer]
        DASH_SVC[Dashboard & Metrics Service]
        SHEET_SVC[Sheet Processor & Column Normalizer]
        KEKA_SVC[Keka Sync & Conflict Resolver]
        RULE_SVC[Smart Rule Detector Service]
        STAGE_SVC[Document Staging & Dispatch Engine]
        DOC_SVC[Document Generation & Formatting Service]
        PDF_SVC[Word COM PDF Converter]
        EXCEL_SVC[Professional OpenPyXL Excel Styler]
        LAUNCH_SVC[Native OS File & Explorer Launcher]
        COPILOT_SVC[Offline Policy Search & AI Copilot]
        EMAIL_SVC[Encrypted SMTP & Gmail Dispatcher]
    end

    subgraph Data_Layer [Data & Persistence Layer]
        SQLITE[(SQLite hrms.db)]
        CIPHER[Fernet Encrypted Secrets]
        DOCX_TPL[Word Template Bank: 50+ Letters]
        POLICY_DB[DFY Policy Knowledge Base JSON]
    end

    subgraph External_Layer [External & Operating System Automation]
        WINWORD[Microsoft Word COM Automation]
        EXPLORER[Windows Shell Explorer & File Association]
        SMTP_SRV[Corporate SMTP / Gmail API]
        AI_GATEWAY[Optional Gemini / Groq / OpenAI API]
    end

    UI_Layer --> Service_Layer
    Service_Layer --> Data_Layer
    Service_Layer --> External_Layer
```

---

## 3. Core Operational Workflows

### Flow 1: Candidate Ingestion & Welcome Staging
```mermaid
sequenceDiagram
    autonumber
    actor HR as HR Executive
    participant UI as Joining Process UI
    participant Parser as Sheet Processor
    participant DB as SQLite Database
    participant Email as Email Service

    HR->>UI: Upload Candidate Excel (.xlsx / .csv)
    UI->>Parser: Parse sheets & normalize 74 columns
    Parser-->>UI: Return multi-sheet breakdown & metrics
    UI-->>HR: Display interactive tab switcher & preview table
    HR->>UI: Filter "Selected (Pending Welcome Email)"
    HR->>UI: Click "Review & Send Welcome Emails"
    UI->>Email: Batch dispatch personalized welcome emails
    Email->>DB: Update candidate welcome_email_sent timestamp
    UI-->>HR: Show success feedback & update metrics
```

### Flow 2: Keka Ingestion with Zero-Duplicate Guard
```mermaid
sequenceDiagram
    autonumber
    actor HR as HR Executive
    participant UI as Keka Sync UI
    participant Keka as Keka Sync Service
    participant DB as SQLite Database

    HR->>UI: Upload Keka 74-Column Master Sheet
    UI->>Keka: Detect header row offset (0, 1, or 2)
    Keka->>DB: Check for matching Employee Numbers
    alt Conflicts Detected (Duplicate Staff)
        Keka-->>UI: Return list of conflicts with field differences
        UI-->>HR: Prompt Warning & Conflict Resolution Modal
        HR->>UI: Choose "Update Existing" OR "Keep Current DB"
        UI->>Keka: Execute chosen resolution strategy
    else No Conflicts
        Keka->>DB: Insert new employee records
    end
    Keka-->>UI: Display Sync Summary (Added, Updated, Skipped)
```

### Flow 3: Smart Rule Detection & Staging Quality Gate
```mermaid
sequenceDiagram
    autonumber
    actor HR as HR Executive
    participant UI as Staging Hub UI
    participant Rules as Smart Rule Detector
    participant Staging as Staging Service
    participant Word as Document Generation Service
    participant DB as SQLite Database

    HR->>UI: Open Tab 1: Smart Detector
    UI->>Rules: Scan employees against business rules
    Rules-->>UI: Propose letters (Offer, Extension, Increment, Relieving, Termination)
    HR->>UI: Click "Generate Drafts to Staging"
    UI->>Staging: Create staging records with temporary drafts
    Staging->>Word: Render draft Word docx (DO NOT burn sequence number)
    Staging->>DB: Save draft path & status='staged'
    UI-->>HR: Move to Tab 2: Staging Final Review
    HR->>UI: Click "Preview" (Launches OS Word/PDF)
    opt User makes inline correction
        HR->>UI: Click "Fix Details" & update salary/dates
        UI->>Staging: inline_fix_and_regenerate()
        Staging->>Word: Re-render draft with updated values
    end
    HR->>UI: Click "🚀 Final Go: Dispatch Selected"
    UI->>Staging: Execute Final Go
    Staging->>DB: Atomically increment and burn Reference Number
    Staging->>Word: Re-stamp document with permanent Ref Number
    Staging->>PDF: Convert to PDF via Word COM (if enabled)
    Staging->>Email: Dispatch email with attached letter
    Staging->>DB: Write permanent audit log & mark status='dispatched'
```

---

## 4. Key Engineering Highlights

### 4.1 Word Header Alignment via 2-Column Table
Prior versions suffered from fragile text-padding where spaces between `Ref: DFY/...` and `Date: DD/MM/YYYY` would wrap across lines depending on printer margins and font rendering.
- **Engineered Solution**: In `document_generation_service.py`, header lines are rendered inside an invisible 1-row, 2-column borderless Word table (`w:cantSplit`, left column left-aligned, right column right-aligned). This guarantees 100% horizontal alignment and zero line-wrapping across all Word template variations.

### 4.2 Executive Excel Styler (`excel_export_service.py`)
All Excel exports across the application (Candidate tables, Keka sync logs, Audit trails, and Daily Briefing workbooks) utilize a unified `openpyxl` styling pipeline:
- **Header Banner**: DFY Corporate Navy (`#0B5ED7`), white bold text, centered vertical alignment, 30pt row height.
- **Zebra Striping**: Alternating rows shaded with soft ice-blue (`#F1F5F9`) for readability.
- **Number & Currency Formatting**: Auto-formats salary figures into Indian Rupee style (`₹#,##0`).
- **Autofit Columns**: Dynamically calculates column width based on content length with safety padding.

### 4.3 Native OS File & Explorer Launcher (`utils/file_launcher.py`)
Provides cross-environment desktop actions without external dependencies:
- **`launch_file(path)`**: Uses Windows `os.startfile(abs_path)` to trigger the system's default viewer (Excel, Word, Acrobat).
- **`reveal_in_explorer(path)`**: Invokes `explorer /select,"path"` so the user is immediately taken to the exact folder with the generated file selected.

### 4.4 Offline-First Architecture & Standalone Portability
The system operates completely decoupled from any external cloud server:
- Local SQLite database stored at `data/hrms.db`.
- Local cryptographic key at `data/secret.key`.
- Intelligent directory resolver in `config.py` automatically detects whether the app is executing inside the full Git development repository or as a standalone extracted `desktop_app/` folder.
- Fallback Copilot uses pre-indexed DFY HR Manual JSON (`knowledge/dfy_hr_policy.json`) with keyword and phrase matching in English and Hinglish when no cloud AI API keys are configured.

---

## 5. Repository File Structure

```
Suraj HR Project/
├── Launch_DFY_HRMS.bat            # 1-Click root launcher (probes env & auto-installs deps)
├── Install_Dependencies.bat       # Manual 1-click dependency installer
├── requirements.txt               # Pinned package requirements
├── README.md                      # Comprehensive repository documentation
├── docs/
│   ├── ARCHITECTURE.md            # System architecture and technical design (this file)
│   └── superpowers/               # Implementation plans and design specifications
├── templates/                     # Master Word templates categorized by document type
│   ├── certificate/               # Experience & Relieving certificate templates
│   ├── extension/                 # Service extension templates
│   ├── increment/                 # Salary increment letter templates
│   ├── offer/                     # New hire offer letter templates
│   └── termination/               # Notice & termination templates
├── knowledge/                     # Offline HR manual and help guides
│   ├── dfy_hr_policy.json         # 10 Articles of DFY HR Manual
│   └── app_help_guide.json        # Step-by-step workflow navigation guide
└── desktop_app/                   # Standalone self-contained application package
    ├── Launch_DFY_HRMS.bat        # Standalone 1-click desktop runner
    ├── Install_Dependencies.bat   # Standalone 1-click dependency installer
    ├── requirements.txt           # Standalone dependencies
    ├── main.py                    # Flet GUI application entry point
    ├── config.py                  # Portable configuration & directory resolver
    ├── assets/                    # Organization logos and icons
    ├── data/                      # SQLite database and encryption key
    ├── templates/                 # Self-contained template bank
    ├── knowledge/                 # Self-contained offline knowledge base
    ├── database/                  # SQLite migrations and CRUD operations
    │   └── db_manager.py
    ├── services/                  # Business logic services
    │   ├── ai_service.py
    │   ├── dashboard_service.py
    │   ├── document_formatters.py
    │   ├── document_generation_service.py
    │   ├── document_staging_service.py
    │   ├── email_service.py
    │   ├── excel_export_service.py
    │   ├── hr_report_exporter.py
    │   ├── keka_sync_service.py
    │   ├── pdf_converter_service.py
    │   ├── security.py
    │   ├── sheet_processor.py
    │   └── smart_rule_detector.py
    ├── pages/                     # Flet views and user interfaces
    │   ├── dashboard_page.py
    │   ├── joining_process_page.py
    │   ├── keka_sync_page.py
    │   ├── document_generation_page.py
    │   ├── help_page.py
    │   └── settings_page.py
    ├── utils/                     # UI components, themes, and OS helpers
    │   ├── file_launcher.py
    │   ├── offline_copilot.py
    │   └── ui_theme.py
    └── scripts/                   # Integration tests and regression suites
```
