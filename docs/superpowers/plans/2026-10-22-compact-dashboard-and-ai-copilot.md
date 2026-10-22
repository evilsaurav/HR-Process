# Compact Executive Dashboard, DFY AI Policy Copilot & Non-Technical Help Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the desktop application into an executive-level, zero-complexity HR Command Center featuring a compact 3-tier Bento layout (~70% space saved), dual-engine AI Operations Copilot with 100% offline fallback, deep ingestion of `HR Manual DFY 2025.pdf`, official DFY branding, and a dedicated Help Center with a Hinglish AI assistant.

**Architecture:** 
1. Build local knowledge extraction and fast retrieval services for DFY HR Manual 2025 and workflow user guides.
2. Build dual-engine AI Copilot (offline deterministic heuristics + online LLM upgrade) for daily briefing and natural language query routing.
3. Build executive utility exporters (Executive Briefing PDF/Excel, bulk letter ZIP package, WhatsApp candidate outreach).
4. Upgrade the database schema with candidate tagging and batch tracking.
5. Implement the dedicated Help Center with Hinglish AI Chatbot.
6. Redesign the Executive Dashboard into a compact 3-tier Bento grid and 3-Tab Operations Hub.
7. Integrate official DFY branding across navigation rail, window icon, and header.

**Tech Stack:** Python 3.11+, Flet (Flutter desktop UI), SQLite3, openpyxl, pypdf, reportlab / xlsxwriter.

**Spec:** [`docs/superpowers/specs/2026-10-22-compact-dashboard-and-ai-copilot-design.md`](file:///d:/ignou/Suraj%20HR%20Project/docs/superpowers/specs/2026-10-22-compact-dashboard-and-ai-copilot-design.md)

## Global Constraints
- **Zero Technical Jargon**: UI text, tooltips, and dialogues must be in plain, friendly English and Hinglish suitable for non-technical HR users.
- **100% Offline Guarantee**: The system must run flawlessly without internet or API keys, using local rules and indexed JSON stores, while automatically upgrading to online LLMs when an API key is available.
- **Data Integrity**: Never overwrite non-empty fields with blanks; preserve atomic sequential reference numbering for dispatched documents.
- **Responsive & Compact**: Dashboard height must be reduced by ~70% without stacked full-width tables.
- **Strict TDD & Verification**: Every task must have an isolated test script that exits with code 0 before task completion.

---

### Task 1: DFY HR Manual 2025 Knowledge Ingestion & Policy Search Service

**Files:**
- Create: `desktop_app/knowledge/dfy_hr_policy.json`
- Create: `desktop_app/services/dfy_policy_service.py`
- Create: `desktop_app/scripts/test_dfy_policy_service.py`

**Interfaces:**
- Consumes: `C:\Users\Saurav\Downloads\HR Manual DFY 2025.pdf`
- Produces: 
  - `dfy_policy_service.get_all_policy_articles() -> List[Dict]`
  - `dfy_policy_service.search_dfy_policy(query: str, max_results: int = 3) -> List[Dict]`
  - `dfy_policy_service.get_quick_rule(rule_key: str) -> Optional[Dict]` (e.g. `'probation'`, `'leaves'`, `'working_hours'`, `'notice_period'`, `'insurance'`)

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_dfy_policy_service.py` testing:
  - Policy JSON file existence and 10 articles parsed.
  - Queries for "probation", "casual leave", "working hours 9:30", "notice period", "insurance" return matching articles with Article citations.
  - Quick rule retrieval for top 5 pinned rules.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_dfy_policy_service.py` (fails because service does not exist).

- [ ] **Step 3: Implement extraction script & `dfy_policy_service.py`**
  - Extract all 10 Articles from `C:\Users\Saurav\Downloads\HR Manual DFY 2025.pdf` into `desktop_app/knowledge/dfy_hr_policy.json` with fields: `article_num`, `title`, `summary`, `full_text`, `keywords`.
  - Implement `desktop_app/services/dfy_policy_service.py` with fast local keyword/TF-IDF inverted scoring that operates 100% offline.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_dfy_policy_service.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/knowledge/dfy_hr_policy.json desktop_app/services/dfy_policy_service.py desktop_app/scripts/test_dfy_policy_service.py`
  `git commit -m "feat(policy): ingest DFY HR Manual 2025 and implement offline policy search service"`

---

### Task 2: AI Operations Copilot Engine & Dual-Engine Query Router

**Files:**
- Create: `desktop_app/services/ai_copilot_service.py`
- Modify: `desktop_app/services/ai_service.py` (integrate copilot router)
- Create: `desktop_app/scripts/test_ai_copilot_service.py`

**Interfaces:**
- Consumes: `dfy_policy_service`, `db_manager`, `dashboard_service`
- Produces:
  - `ai_copilot_service.generate_daily_operational_briefing() -> Dict[str, Any]` (returns `{"bullets": List[Dict], "action_count": int, "hygiene_alerts": List[Dict]}`)
  - `ai_copilot_service.process_ask_hr_query(query: str) -> Dict[str, Any]` (returns `{"type": "candidate_stat"|"policy_rule"|"general", "answer": str, "details": Any, "navigation_action": Optional[str]}`)

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_ai_copilot_service.py` testing:
  - Daily briefing generates 3–4 bullet points from DB state (pending welcome, unassigned keka, overdue increments, missing contact fields).
  - Natural language queries in English and Hinglish:
    - Candidate count query (*"Bihar candidates kitne hain?"*)
    - Policy query (*"Probation period kya hai?"*)
    - Action query (*"Who needs offer letter?"*)
  - Verify 100% offline execution without internet/API key.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_ai_copilot_service.py`.

- [ ] **Step 3: Implement `ai_copilot_service.py`**
  - Implement deterministic DB rules engine for operational briefing.
  - Implement regex + intent classifier for natural language candidate queries.
  - Route policy questions to `dfy_policy_service.search_dfy_policy`.
  - Add optional online LLM wrapper if API key is present.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_ai_copilot_service.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/services/ai_copilot_service.py desktop_app/services/ai_service.py desktop_app/scripts/test_ai_copilot_service.py`
  `git commit -m "feat(copilot): add AI operations copilot and dual-engine natural language query router"`

---

### Task 3: Operational Utility Services (Executive Summary, Bulk ZIP, WhatsApp Outreach)

**Files:**
- Create: `desktop_app/services/hr_report_exporter.py`
- Create: `desktop_app/services/zip_export_service.py`
- Create: `desktop_app/services/candidate_outreach_service.py`
- Create: `desktop_app/scripts/test_utility_services.py`

**Interfaces:**
- Produces:
  - `hr_report_exporter.export_daily_executive_summary(target_path: Optional[str] = None) -> str`
  - `zip_export_service.create_bulk_document_zip(staging_or_cand_ids: List[int], zip_filename: str) -> str`
  - `candidate_outreach_service.generate_whatsapp_outreach_text(candidate: Dict, message_type: str = 'selection') -> str`

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_utility_services.py` verifying:
  - Generation of Excel executive briefing summary.
  - Creation of a clean ZIP file containing test document files with sanitized naming.
  - Generation of personalized Hinglish WhatsApp selection text with candidate name, designation, and location.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_utility_services.py`.

- [ ] **Step 3: Implement the three utility services**
  - `hr_report_exporter.py`: Excel workbook with 2 sheets ("Executive Summary" and "Action Needed Items").
  - `zip_export_service.py`: Standard `zipfile` module bundling letters into `desktop_app/output/`.
  - `candidate_outreach_service.py`: Friendly Hinglish templates for WhatsApp/SMS copy.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_utility_services.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/services/hr_report_exporter.py desktop_app/services/zip_export_service.py desktop_app/services/candidate_outreach_service.py desktop_app/scripts/test_utility_services.py`
  `git commit -m "feat(utilities): add executive report exporter, bulk ZIP packager, and WhatsApp outreach generator"`

---

### Task 4: Database Enhancements (Candidate Tags, Batch Dates & Data Hygiene Helpers)

**Files:**
- Modify: `desktop_app/database/db_manager.py`
- Create: `desktop_app/scripts/test_candidate_tags_and_batch_db.py`

**Interfaces:**
- Produces:
  - `db_manager.update_candidate_tag(candidate_id: int, tag: str) -> bool`
  - `db_manager.get_candidates_by_tag(tag: str) -> List[Dict]`
  - `db_manager.get_upcoming_joinees(days: int = 7) -> List[Dict]`
  - `db_manager.get_distinct_source_sheets() -> List[str]`

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_candidate_tags_and_batch_db.py` asserting:
  - Migration idempotently adds `tag` column to `candidates` table.
  - Setting candidate tag (`Immediate Joiner`, `Docs Pending`, `On Hold`, `Top Priority`) works and persists.
  - `get_upcoming_joinees(7)` correctly filters candidates whose `date_joined` is within next 7 days.
  - `get_distinct_source_sheets()` returns all unique sheet origins.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_candidate_tags_and_batch_db.py`.

- [ ] **Step 3: Update `db_manager.py`**
  - In `init_db()`, add safe column migration `("tag", "TEXT")`.
  - Implement helper functions with proper parameterized queries and connection cleanup.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_candidate_tags_and_batch_db.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/database/db_manager.py desktop_app/scripts/test_candidate_tags_and_batch_db.py`
  `git commit -m "feat(db): add candidate tags, upcoming joinees lookup, and sheet origins"`

---

### Task 5: Dedicated Help Center & Hinglish AI Help Chatbot

**Files:**
- Create: `desktop_app/knowledge/app_help_guide.json`
- Create: `desktop_app/pages/help_center_page.py`
- Create: `desktop_app/scripts/test_help_center_ui.py`

**Interfaces:**
- Produces:
  - `help_center_page.help_center_view(page: ft.Page, on_navigate: Optional[Callable] = None) -> ft.Control`
  - Embedded Hinglish chatbot answering workflow and policy questions with instant responses.

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_help_center_ui.py` verifying:
  - Instantiation of `help_center_view`.
  - Visual cards render for Excel Upload, Welcome Emails, Document Generator, Keka Sync, and DFY Policies.
  - Chatbot responds to Hinglish questions (e.g. *"Offer letter kaise banate hain?"*, *"Duplicate candidate warning ka kya matlab hai?"*).

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_help_center_ui.py`.

- [ ] **Step 3: Implement `app_help_guide.json` and `help_center_page.py`**
  - Create step-by-step visual cards with screenshots/icons and plain Hinglish explanations.
  - Build interactive chat UI with message bubble history, quick suggestion chips, and offline response fallback using `ai_copilot_service` and `dfy_policy_service`.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_help_center_ui.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/knowledge/app_help_guide.json desktop_app/pages/help_center_page.py desktop_app/scripts/test_help_center_ui.py`
  `git commit -m "feat(ui): add dedicated Help Center with interactive Hinglish AI chatbot"`

---

### Task 6: Compact Executive Dashboard Redesign (3-Tier Bento & Tabbed Hub)

**Files:**
- Modify: `desktop_app/services/dashboard_service.py`
- Modify: `desktop_app/pages/dashboard_page.py`
- Create: `desktop_app/scripts/test_compact_dashboard_ui.py`

**Interfaces:**
- Consumes: `ai_copilot_service`, `dfy_policy_service`, `hr_report_exporter`, `db_manager`
- Produces:
  - Redesigned `dashboard_view` featuring:
    - Tier 1: 4 prominent interactive Action Cards.
    - Tier 2: 55% Left Bento = AI Daily Briefing + Policy Quick-Chips + Ask-HR Bar + 1-Click Hygiene Fixer; 45% Right Bento = Funnel Stats + Keka Sync Pill + Upcoming Joinees + 1-Click Executive Report button.
    - Tier 3: High-Density 3-Tab Operations Hub (`Due Reminders` | `Operations Log` | `Sheet & Batch Breakdown`).

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_compact_dashboard_ui.py` verifying:
  - Instantiation of the redesigned compact `dashboard_view`.
  - Verification of Tier 1 action cards, Tier 2 Bento grid controls, and Tier 3 tabs (`Due Reminders`, `Operations Log`, `Breakdown`).
  - Verification of 1-Click Data Hygiene Fixer opening dialog.
  - Verification of Ask-HR search box returning answers and updating UI dynamically.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_compact_dashboard_ui.py`.

- [ ] **Step 3: Implement redesigned `dashboard_service.py` & `dashboard_page.py`**
  - Update `dashboard_service.py` with department/sheet breakdown calculations and joinee countdowns.
  - Rebuild `dashboard_page.py` with the 3-Tier Bento Layout and Flet Tabs. Ensure zero raw exceptions and full reactivity.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_compact_dashboard_ui.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/services/dashboard_service.py desktop_app/pages/dashboard_page.py desktop_app/scripts/test_compact_dashboard_ui.py`
  `git commit -m "feat(ui): redesign executive dashboard into compact 3-tier Bento layout and tabbed hub"`

---

### Task 7: Official DFY Branding & Joining Page Enhancements

**Files:**
- Modify: `desktop_app/main.py`
- Modify: `desktop_app/pages/joining_process_page.py`
- Modify: `desktop_app/pages/document_generation_page.py` (add bulk ZIP export button)
- Create: `desktop_app/scripts/test_branding_and_joining_enhancements.py`

**Interfaces:**
- Uses: `desktop_app/assets/dfy_logo112.png`
- Adds:
  - Navigation Rail: DFY logo image + Help Center destination.
  - Window icon: DFY logo.
  - Joining Process page: Tag badges, WhatsApp copy button, Interview date batch selector.
  - Document Generation page: Export selected letters as ZIP button.

- [ ] **Step 1: Write the failing test**
  Create `desktop_app/scripts/test_branding_and_joining_enhancements.py` asserting:
  - Navigation rail includes the Help Center tab and DFY logo widget.
  - Joining page controls include Candidate Tag options and WhatsApp copy button.
  - Document generation staging view includes Bulk ZIP exporter button.

- [ ] **Step 2: Run test to verify failure**
  Run `python desktop_app/scripts/test_branding_and_joining_enhancements.py`.

- [ ] **Step 3: Implement branding and joining page upgrades**
  - In `main.py`: Update `leading` container with `ft.Image(src=...)` and register index 5 for `help_center_view`.
  - In `joining_process_page.py`: Add tag chip rendering, WhatsApp copy button with clipboard copy and feedback snackbar, and interview batch dropdown filter.
  - In `document_generation_page.py`: Wire up `zip_export_service` button.

- [ ] **Step 4: Run test to verify pass**
  Run `python desktop_app/scripts/test_branding_and_joining_enhancements.py` and ensure exit code 0.

- [ ] **Step 5: Commit**
  `git add desktop_app/main.py desktop_app/pages/joining_process_page.py desktop_app/pages/document_generation_page.py desktop_app/scripts/test_branding_and_joining_enhancements.py`
  `git commit -m "feat(branding): apply DFY logo, add Help Center to navigation rail, and add tags/WhatsApp copy"`

---

### Task 8: End-to-End System Integration & Full Regression Suite

**Files:**
- Create: `desktop_app/scripts/test_compact_dashboard_and_ai_copilot_e2e.py`

**Interfaces:**
- End-to-end operational verification across all 7 tasks:
  1. Policy retrieval from DFY Manual 2025.
  2. AI daily briefing & Ask-HR natural language query (offline mode).
  3. Executive summary export and bulk ZIP package creation.
  4. Candidate tagging and upcoming joinee countdown.
  5. Compact Dashboard layout rendering and tab switching.
  6. Help Center view and Hinglish chatbot response.
  7. Full regression test across Task 1-10 suites (`test_task9_full_pipeline_e2e.py` and `test_ppsa_interview_chart_upload.py`).

- [ ] **Step 1: Implement the E2E verification script**
  Create `desktop_app/scripts/test_compact_dashboard_and_ai_copilot_e2e.py` testing all flows in sequence.

- [ ] **Step 2: Run the full integration test and regression suite**
  Run `python desktop_app/scripts/test_compact_dashboard_and_ai_copilot_e2e.py` and ensure 100% test pass rate with exit code 0.

- [ ] **Step 3: Commit**
  `git add desktop_app/scripts/test_compact_dashboard_and_ai_copilot_e2e.py`
  `git commit -m "test(e2e): add end-to-end verification and full regression suite for compact dashboard and AI copilot"`
