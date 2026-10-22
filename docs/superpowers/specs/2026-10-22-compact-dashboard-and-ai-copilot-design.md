# Design Specification: Compact Executive Dashboard & DFY AI Policy Copilot

- **Date**: 2026-10-22
- **Topic**: Compact Dashboard Redesign, AI Operations Copilot, DFY HR Manual 2025 Integration & Official Branding
- **Status**: Approved by User

---

## 1. Executive Summary

The current Executive Dashboard (`dashboard_page.py`) contains extensive real-time data but suffers from extreme vertical scrolling due to 5 large data tables stacked sequentially (Experience Certificates Due, Overdue Increments, Upcoming Increments, Email Dispatches, Document Generations).

This redesign achieves two major milestones:
1. **Compact Dashboard UX (~70% Vertical Space Reduction)**: Consolidates stacked tables into a single high-density **3-Tab Operations Hub** (`Due Reminders` | `Operations Log` | `Breakdown`), while organizing the top and middle sections into an executive Bento Grid layout.
2. **AI Operations & DFY Policy Copilot**: Embeds an intelligent Dual-Engine assistant (100% offline rule-based heuristics + online LLM upgrade) that provides:
   - **AI Daily Operational Briefing**: 3–4 instant bullet points pinpointing urgent tasks (pending welcome emails, unassigned Keka numbers, overdue increments, missing contact fields).
   - **Ask-HR Natural Language Query Box**: Instant conversational answers for candidate queries (*"Kitne candidates Bihar sheet se hain?"*) and official policy queries (*"Probation period kitna hota hai DFY me?"*).
   - **DFY HR Manual (Updated 2025) Integration**: Deep knowledge ingestion of `HR Manual DFY 2025.pdf` across 10 official Articles (probation, leaves, notice periods, benefits, relieving rules).
3. **Official DFY Branding**: Replaces generic placeholder icons with the official Doctors For You logo (`desktop_app/assets/dfy_logo112.png`) in the desktop navigation rail, dashboard header, and application window.

---

## 2. Layout Architecture & Wireframe

### Compact High-Density Grid Structure

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  DFY LOGO  •  Executive HR Command Center                               [ 🔄 Refresh ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  ⚡ LIVE OPERATIONAL ACTION CARDS (Top Row - 4 Interactive Cards):                     │
│  [ 🎉 Pending Welcome ]  [ 🔍 Letters to Gen ]  [ 🚀 Staged Ready ]  [ 👥 In Pipeline ]│
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│  🤖 AI OPERATIONS & POLICY COPILOT (55%)  │  📊 HRMS HEALTH & PIPELINE STATS (45%)     │
│  ┌─────────────────────────────────────┐  │  ┌──────────────────────────────────────┐  │
│  │ 💡 Daily Briefing:                  │  │  │ Funnel: Applied ➔ Interv ➔ Sel ➔ Join│  │
│  │ • 3 Selected pending welcome emails │  │  │ Keka Sync: ✅ 43/43 Employees Synced │  │
│  │ • 1 Increment overdue (DFY Art. 2)  │  │  │ Fast Status Pills: [Offer Sent: 12]  │  │
│  │ • 0 Missing candidate mobiles       │  │  └──────────────────────────────────────┘  │
│  │ 🔍 Ask HR Query Bar:                │  │                                            │
│  │ [ Ask candidate data or DFY policy] │  │                                            │
│  └─────────────────────────────────────┘  │                                            │
├───────────────────────────────────────────┴────────────────────────────────────────────┤
│  📑 UNIFIED OPERATIONS HUB (3-Tab High-Density Container):                             │
│  [ 🔔 Due Reminders ]    [ 📜 Operations Log ]    [ 📊 Sheet Breakdown ]                │
│  ────────────────────────────────────────────────────────────────────────────────────  │
│  • Tab 1: Experience/Relieving Certificates Due & Overdue/Upcoming Annual Increments   │
│  • Tab 2: Recent Email Dispatches & Staged Document Generations Log                   │
│  • Tab 3: Sheet/Department Distribution (PPSA UP, Bihar, Maharashtra) + Conversion %   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component & Subsystem Design

### Subsystem A: DFY Policy Knowledge Base (`dfy_policy_service.py`)
- **Source**: `C:\Users\Saurav\Downloads\HR Manual DFY 2025.pdf`
- **Indexed Articles**:
  - `Article 1`: Introduction, Vision & Mission, Guiding Principles
  - `Article 2`: Policies, Selection, Probation & Performance Reviews
  - `Article 3`: Employment Equity, Contract Types & Job Descriptions
  - `Article 4`: Working Hours (9:30 AM - 5:30 PM), Holidays & Leaves (Casual, Sick, Maternity, Unpaid)
  - `Article 5`: Termination, Resignation, Notice Periods & Relieving/Settlement Rules
  - `Article 6`: Benefits, Medical Insurance, PF & Reimbursements
  - `Article 7`: Harassment & POSH Policy
  - `Article 8`: Training & Capacity Building
  - `Article 9`: Internal Committees
  - `Article 10`: Miscellaneous, Confidentiality & Code of Conduct
- **Storage**: Clean JSON index stored at `desktop_app/knowledge/dfy_hr_policy.json` with extracted article summaries, full text sections, and keyword metadata for instant sub-millisecond retrieval.
- **Search API**: `search_dfy_policy(query: str) -> List[Dict]` returning matched articles, relevance scores, and direct policy answers.

---

### Subsystem B: AI Operations Copilot (`ai_copilot_service.py`)
- **Capability 1 — Daily Operational Briefing**:
  - Computes database state across candidates, staging records, increment schedules, and Keka synchronization.
  - Generates 3–4 bulleted action points.
  - Offline mode uses deterministic rule-based analysis; Online mode (Gemini/Groq/OpenRouter) crafts polished executive language.
- **Capability 2 — Natural Language Ask-HR Query**:
  - Accepts user questions in English or Hinglish (e.g., *"Bihar candidates kitne hain?"*, *"Who needs offer letter?"*, *"Probation rule kya hai?"*).
  - Routes query intelligently:
    - If question relates to DFY policy ➔ calls `dfy_policy_service.py`.
    - If question relates to operational data ➔ queries SQLite database (`candidates`, `document_staging`, `email_log`) and returns concise summaries with direct navigation actions.

---

### Subsystem C: Compact Tabbed Operations Hub (`dashboard_page.py`)
- Replaces individual vertical full-width cards with an elegant Flet `Tabs` container:
  - **Tab 1: Due Reminders**:
    - Relieving & Experience Certificates Due table (with Export to Excel button).
    - Overdue & Upcoming Annual Increments tables (with Export to Excel buttons).
  - **Tab 2: Operations Log**:
    - Recent Email Dispatches (live status, timestamps, recipients).
    - Recent Generated Documents (reference numbers, candidate names).
  - **Tab 3: Sheet & Department Breakdown**:
    - State breakdown chips: `PPSA UP (11)`, `PPSA Bihar (14)`, `PPSA Maharashtra (18)`.
    - Stage conversion metrics (Interviewed ➔ Selected ➔ Joined).

---

### Subsystem D: Official DFY Branding & Logo Integration
- **Asset**: `desktop_app/assets/dfy_logo112.png`
- **Application Window**: Set `page.window.icon` to the DFY logo path.
- **Navigation Rail**: Replaces `ft.Icon(ft.Icons.LOCAL_HOSPITAL_ROUNDED)` with `ft.Image(src="assets/dfy_logo112.png", width=44, height=44)`.
- **Dashboard Header**: Displays the DFY logo prominently next to the title.

---

## 4. Testing & Verification Plan

1. **DFY Policy Knowledge Verification (`test_dfy_policy_knowledge.py`)**:
   - Verify all 10 articles parsed accurately from `HR Manual DFY 2025.pdf`.
   - Test queries: "probation", "casual leave", "working hours", "notice period", "resignation".
   - Confirm citation accuracy (Article number and text match).
2. **AI Copilot & Natural Language Query Test (`test_ai_copilot_service.py`)**:
   - Verify daily operational briefing generation on live DB state.
   - Verify offline natural language routing for candidate stats and policy questions.
3. **Dashboard Compact UI Layout Test (`test_compact_dashboard_ui.py`)**:
   - Verify dashboard view instantiates cleanly with tabs and Bento grid.
   - Verify tab switching (`Due Reminders` ➔ `Operations Log` ➔ `Breakdown`).
   - Verify Ask-HR search bar responds and updates the UI.
4. **Full Pipeline Regression**:
   - Run `test_task9_full_pipeline_e2e.py` and `test_ppsa_interview_chart_upload.py` to ensure 100% test pass rate across all existing HRMS capabilities.
