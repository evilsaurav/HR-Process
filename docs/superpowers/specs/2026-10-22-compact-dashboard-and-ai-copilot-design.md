# Design Specification: Non-Technical Executive HR Operations Platform, Compact Dashboard, DFY Policy Engine & Hinglish AI Help Copilot

- **Date**: 2026-10-22
- **Topic**: Compact Dashboard, 100% Offline Fallback, DFY HR Manual 2025 Knowledge Base, Non-Technical User Experience, and Hinglish AI Help Center
- **Status**: Approved by User
- **Target Users**: Non-technical HR managers and field coordinators (Zero IT/technical knowledge required)

---

## 1. Executive Summary & Design Philosophy

The primary objective is to transform the desktop application into an **intuitive, executive-level, zero-complexity HR Command Center** that anyone without IT knowledge can operate effortlessly. 

### Key Principles
1. **Zero Technical Jargon**: Everything is labeled in simple, clear business terms with dual-language tooltips (Hinglish + English).
2. **Deeply Connected Dashboard**: Every metric, alert, and counter is directly interactive. Clicking an alert immediately opens the relevant action (e.g. clicking "1 candidate missing location" opens an instant 1-click fixer dialog right on the dashboard).
3. **Guaranteed 100% Offline Fallback**: The system functions completely without internet or API keys (using fast local rule engines, SQLite heuristics, and local TF-IDF search on the DFY HR Manual), while automatically upgrading to online LLMs (Gemini/Groq/OpenAI) whenever an API key is present.
4. **Official DFY Branding**: Incorporates the official Doctors For You logo (`desktop_app/assets/dfy_logo112.png`) across the navigation rail, window icon, and header.

---

## 2. Compact Dashboard Layout (~70% Space Saved)

Instead of 5 stacked full-width tables causing endless vertical scrolling, the dashboard is organized into an executive 3-tier hierarchy:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [DFY LOGO]  Doctors For You — Executive HR Command Center            [ 🔄 Refresh Data]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ⚡ LIVE OPERATIONAL ACTION CARDS (Top Row - 4 Interactive 1-Click Cards):              │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐ │
│ │ 🎉 Welcome Queue │ │ 🔍 Letters to Gen│ │ 🚀 Staged Ready  │ │ 👥 In Pipeline      │ │
│ │ Count: 3 Pending │ │ Count: 2 Detected│ │ Count: 4 Ready   │ │ Count: 43 Active    │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────────────┘ │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│ 🤖 AI OPERATIONS & POLICY COPILOT (55%)   │ 📊 HRMS HEALTH & PIPELINE STATS (45%)      │
│ ┌──────────────────────────────────────┐  │ ┌────────────────────────────────────────┐ │
│ │ 💡 Daily Operational Briefing:       │  │ │ • Fast Stage Pills:                    │ │
│ │  • 3 Candidates awaiting welcome     │  │ │   [Applied: 10] [Interview: 15]        │ │
│ │  • 1 Increment overdue (DFY Art. 2)  │  │ │   [Selected: 6] [Joined: 12]           │ │
│ │  • 1 Missing contact location [Fix]  │  │ │ • Keka Sync Status:                    │ │
│ │                                      │  │ │   ✅ 43/43 Employees Synced            │ │
│ │ 📌 DFY Policy Quick-Chips (1-Click): │  │ │ • ⏳ Joining Countdown (Next 7 Days):  │ │
│ │ [🏥 Insurance] [⏱️ Hours] [📅 Leaves] │  │ │   "3 Field staff joining this week"    │ │
│ │ [⏳ Probation] [🚪 Notice Period]     │  │ └────────────────────────────────────────┘ │
│ │                                      │  │                                            │
│ │ 🔍 Ask HR Query Bar (Hinglish/Eng):  │  │ [ 📄 Download Daily HR Summary (PDF/XLS) ]│
│ │ [ Ask candidate stats or DFY policy ]│  │ [ 📦 Export Selected Letters as ZIP      ]│
│ └──────────────────────────────────────┘  │                                            │
├───────────────────────────────────────────┴────────────────────────────────────────────┤
│ 📑 UNIFIED OPERATIONS HUB (3 Clean High-Density Tabs):                                 │
│ [ 🔔 Due Reminders ]    [ 📜 Operations Activity Log ]    [ 📊 State & Batch Breakdown ]│
│ ────────────────────────────────────────────────────────────────────────────────────── │
│ • Tab 1: Experience & Relieving Certificates Due + Overdue & Upcoming Annual Increments│
│ • Tab 2: Recent Email Dispatches & Staged Document Generations Live Audit Trail        │
│ • Tab 3: Sheet/State Distribution (PPSA UP: 11, Bihar: 14, Maharashtra: 18) + Batches │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Approved Feature Specification

### 1. 📄 One-Click "Executive Daily HR Summary" (Printable PDF & Excel)
- Button on the Dashboard header: `[📄 Download Daily HR Briefing]`.
- Generates a clean 1-page summary containing:
  - Date & time of report.
  - Active candidates in pipeline by stage (Applied, Shortlisted, Selected, Joined).
  - Selected candidates pending welcome email.
  - Active staff due for annual increments.
  - Relieved staff awaiting certificates.
  - Top 3 actionable priorities.
- Formats: Excel (`.xlsx`) and printable formatted summary for Directors/Project Leads.

### 2. ⚡ Quick "Data Hygiene 1-Click Fixer"
- When the Daily Briefing detects missing fields (e.g., *"1 candidate missing location"* or *"1 candidate missing email"*), the alert displays an interactive `[⚡ Fix Now]` pill.
- Clicking it opens a focused modal with only the missing fields pre-targeted, saving it directly to SQLite without requiring the user to navigate to the Joining page.

### 3. 📌 DFY Policy Quick-Chips (Top 5 Pinned Rules)
- Quick-access buttons directly under the search bar:
  - `[🏥 Medical Insurance (Art. 6)]`
  - `[⏱️ Working Hours & Overtime (Art. 4)]`
  - `[📅 Casual & Sick Leaves (Art. 4)]`
  - `[⏳ Probation Duration (Art. 2)]`
  - `[🚪 Resignation Notice Period (Art. 5)]`
- 1-click opens an instant card showing the exact Article text, plain Hinglish explanation, and operational instructions.

### 4. 📱 One-Click WhatsApp / SMS Candidate Outreach
- In the candidate table and staging review cards, a `[📱 Copy WhatsApp Message]` button is added.
- Generates personalized text ready to paste into WhatsApp Web or mobile:
  > *"Namaste {candidate_name}, Doctors For You ki taraf se aapka selection {applied_designation} post ({contact_location}) ke liye ho gaya hai. Formal welcome details aapke email {email} par bhej di gayi hain. Joining date: {date_joined}. DFY HR Team."*

### 5. 📦 One-Click "Bulk Document ZIP Exporter" (Audit & Accounts Package)
- In the Document Staging Hub: a button `[📦 Export Staged/Dispatched as ZIP]`.
- Bundles all selected PDF/DOCX letters into a timestamped ZIP archive:
  - Folder: `desktop_app/output/DFY_Letters_Package_<YYYYMMDD>.zip`
  - Filenames: `DFY_PPSA_UP_001_Amit_Kumar_Offer.pdf`, etc.

### 6. 🏷️ Custom Candidate Quick-Tags (Field Operations Tracking)
- Color-coded status tags assignable with 1-click in the table:
  - `[⚡ Immediate Joiner]` (Green)
  - `[📄 Docs Pending]` (Amber)
  - `[⏸️ On Hold]` (Purple)
  - `[⭐ Top Priority]` (Blue)
- Persisted in the `candidates` database table (`tag` column) with instant filtering.

### 7. ⏳ "Joining Countdown & Upcoming Joinee Tracker"
- Dashboard metric card tracking candidates whose `date_joined` falls within the next 7 days.
- Displays countdown pills: *"Aarav Sharma — Joining in 2 days (Patna)"*.

### 8. 📅 Interview Date & Batch Quick-Filter
- Joining Process page filter allowing HR to switch between interview dates extracted from sheets (e.g., `2026-08-22`, `2026-08-25`).

### 9. 🖨️ One-Click Candidate Bio-Data / Summary Slip
- Generates a neat 1-page candidate interview summary slip for the interview panel or project director before the interview.

---

## 4. Dedicated Help Center & Hinglish AI Chatbot

A new navigation item **"Help & User Guide"** (icon: `ft.Icons.HELP_OUTLINE_ROUNDED`) added to the main navigation rail:

### Section A: Visual Step-by-Step Interactive Guide (Visual Cards)
1. **Excel Sheet Upload & Joining**: How to upload multi-sheet interview charts, understand duplicate warnings, and avoid duplicates.
2. **Welcome Emails**: How to review, personalize, and send selection welcome emails.
3. **Smart Document Generation**: How to create Offer Letters, Extensions, Increments, and Relieving Certificates with atomic reference numbers.
4. **Keka HRMS Sync**: How to import Keka 74-column master sheets and assign Employee Numbers.
5. **DFY HR Policy Rules**: Overview of official DFY 2025 guidelines.

### Section B: Embedded Hinglish AI Help Chatbot
- An interactive chat interface embedded in the Help Page (and available as an expandable floating widget on the Dashboard).
- Trained on the app's user manual, workflow logic, and the complete **`HR Manual DFY 2025.pdf`**.
- Natural language queries in Hindi, Hinglish, or English:
  - *"Offer letter kaise banate hain?"*
  - *"Agar candidate ka mobile duplicate ho to kya hoga?"*
  - *"Casual leave kitni milti hain DFY me?"*
  - *"Excel sheet upload karne par error aaye to kya karein?"*
- **Offline Capability**: Answers app questions and policy questions from local knowledge base without needing an internet connection. If an online API key is configured, provides conversational expanded guidance.

---

## 5. Architectural Subsystems & Code Organization

```
desktop_app/
├── assets/
│   └── dfy_logo112.png                 # Official Doctors For You logo
├── knowledge/
│   ├── dfy_hr_policy.json              # Extracted 10 Articles from HR Manual 2025
│   └── app_help_guide.json             # Step-by-step user guide for HR workflows
├── services/
│   ├── dfy_policy_service.py           # Fast local policy search & citation engine
│   ├── ai_copilot_service.py           # Dual-engine Daily Briefing & Ask-HR router
│   ├── hr_report_exporter.py           # Executive PDF/Excel briefing generator
│   └── zip_export_service.py           # Bulk document package ZIP creator
├── pages/
│   ├── dashboard_page.py               # Redesigned compact 3-tier Bento & Tabbed Hub
│   ├── help_center_page.py             # Dedicated Help Center & Hinglish Chatbot
│   └── joining_process_page.py         # Enhanced with Tags, WhatsApp copy, Date filter
└── main.py                             # Branded with DFY logo & Help navigation item
```

---

## 6. Implementation & Verification Plan

1. **Policy & Help Knowledge Ingestion**: Extract `HR Manual DFY 2025.pdf` and app guide into structured JSON indexes.
2. **Offline AI Copilot Service**: Implement daily briefing, natural language parser, and policy retriever with 100% offline fallback.
3. **Utility Services**: Implement Executive Daily Summary exporter, ZIP packager, and WhatsApp message generator.
4. **Compact Dashboard Page**: Rebuild `dashboard_page.py` with the 3-Tier Bento Layout, top Action Cards, and Tabbed Operations Hub.
5. **Help Center & Hinglish Chatbot**: Build `help_center_page.py` with visual workflow cards and interactive chatbot.
6. **DFY Official Branding**: Apply `dfy_logo112.png` to `main.py`, header, and window icon.
7. **Comprehensive Verification**:
   - `test_dfy_policy_knowledge.py`
   - `test_ai_copilot_service.py`
   - `test_compact_dashboard_ui.py`
   - `test_help_center_ui.py`
   - Regression suite: `test_task9_full_pipeline_e2e.py` and `test_ppsa_interview_chart_upload.py`.
