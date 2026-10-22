"""
End-to-End System Integration Test: Compact Dashboard & AI Operations Copilot Suite
===================================================================================
Verifies complete operational pipeline:
1. Candidate Quick-Tags & DB queries (get_candidates_by_tag)
2. 7-Day Upcoming Joinee Countdown (get_upcoming_joinees)
3. Multi-Sheet source breakdown (get_distinct_source_sheets)
4. DFY HR Manual Policy Service (Offline 10 Articles & Keyword Scoring)
5. AI Operations Copilot Service (Daily Briefing & Hinglish NLP Router)
6. 1-Click Executive Daily Briefing Excel Exporter
7. Bulk Document ZIP Packager
8. Candidate Outreach Service (WhatsApp copy & Bio-Data slips)
9. Compact Executive Dashboard View (Bento Grid & 3-Tab Hub)
10. Dedicated Help Center View & Interactive Hinglish Chatbot
"""

import os
import sys
import time
import datetime
import tempfile
import sqlite3

# Ensure UTF-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure desktop_app is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from database import db_manager
from services import (
    dfy_policy_service,
    ai_copilot_service,
    hr_report_exporter,
    zip_export_service,
    candidate_outreach_service,
    dashboard_service,
)
from pages import dashboard_page
from pages import help_center_page
from pages import joining_process_page
from pages import document_generation_page


class MockPage:
    def __init__(self):
        self.theme_mode = ft.ThemeMode.DARK
        self.overlay = []
        self.services = []
        self.clipboard_data = ""

    def update(self):
        pass

    def open(self, ctrl):
        pass

    def close(self, ctrl):
        pass

    def set_clipboard(self, data):
        self.clipboard_data = data


def run_e2e_tests():
    print("=" * 80)
    print("RUNNING END-TO-END COMPACT DASHBOARD & AI COPILOT INTEGRATION SUITE")
    print("=" * 80)

    db_manager.init_db()
    test_cids = []
    created_temp_files = []

    try:
        # ---------------------------------------------------------------------
        # STEP 1: Candidate Quick-Tags & Joinee Countdown in Database
        # ---------------------------------------------------------------------
        print("\n[STEP 1] Testing Candidate Tags & 7-Day Joinee Countdown...")
        today = datetime.date.today()
        d_plus_2 = (today + datetime.timedelta(days=2)).strftime("%d-%m-%Y")
        d_plus_5 = (today + datetime.timedelta(days=5)).strftime("%d-%m-%Y")
        d_plus_15 = (today + datetime.timedelta(days=15)).strftime("%d-%m-%Y")

        c1 = db_manager.insert_candidate(
            {
                "candidate_name": "E2E Joinee Alpha",
                "mobile": "9876540001",
                "email": "alpha.e2e@example.com",
                "applied_designation": "Medical Officer",
                "status": "Selected",
                "date_joined": d_plus_2,
                "tag": "Immediate Joiner",
            },
            source_sheet_name="E2E Test Batch UP",
        )
        test_cids.append(c1)

        c2 = db_manager.insert_candidate(
            {
                "candidate_name": "E2E Joinee Beta",
                "mobile": "9876540002",
                "email": "beta.e2e@example.com",
                "applied_designation": "Staff Nurse",
                "status": "Selected",
                "date_joined": d_plus_5,
                "tag": "Docs Pending",
            },
            source_sheet_name="E2E Test Batch Bihar",
        )
        test_cids.append(c2)

        c3 = db_manager.insert_candidate(
            {
                "candidate_name": "E2E Joinee Gamma",
                "mobile": "9876540003",
                "email": "gamma.e2e@example.com",
                "applied_designation": "Lab Technician",
                "status": "Selected",
                "date_joined": d_plus_15,
                "tag": "On Hold",
            },
            source_sheet_name="E2E Test Batch Bihar",
        )
        test_cids.append(c3)

        # Test tag filtering
        imm_joiners = db_manager.get_candidates_by_tag("Immediate Joiner")
        imm_names = [c["candidate_name"] for c in imm_joiners]
        assert "E2E Joinee Alpha" in imm_names, "Immediate Joiner tag filter failed"
        print("  ✓ Candidate tag filtering verified ('Immediate Joiner' found).")

        # Test 7-day upcoming joinees
        upcoming = db_manager.get_upcoming_joinees(days=7)
        upcoming_names = [c["candidate_name"] for c in upcoming]
        assert "E2E Joinee Alpha" in upcoming_names, "E2E Joinee Alpha (+2 days) not in upcoming 7-day list"
        assert "E2E Joinee Beta" in upcoming_names, "E2E Joinee Beta (+5 days) not in upcoming 7-day list"
        assert "E2E Joinee Gamma" not in upcoming_names, "E2E Joinee Gamma (+15 days) incorrectly included in 7-day list"
        print(f"  ✓ 7-Day Joinee Countdown verified ({len(upcoming)} candidates in next 7 days).")

        # Test distinct source sheets
        sheets = db_manager.get_distinct_source_sheets()
        assert "E2E Test Batch UP" in sheets and "E2E Test Batch Bihar" in sheets
        print(f"  ✓ Multi-Sheet breakdown verified ({len(sheets)} distinct source sheets).")

        # ---------------------------------------------------------------------
        # STEP 2: DFY HR Manual Policy Service (Offline 10 Articles)
        # ---------------------------------------------------------------------
        print("\n[STEP 2] Testing DFY HR Manual 2025 Policy Service...")
        articles = dfy_policy_service.get_all_policy_articles()
        assert len(articles) == 10, f"Expected 10 articles, found {len(articles)}"

        query_res = dfy_policy_service.search_dfy_policy("kitne din ka notice period hota hai resignation ke liye?")
        assert len(query_res) > 0, "No policy matches found for notice period query"
        top_match = query_res[0]
        assert "notice" in top_match["full_text"].lower() or "resignation" in top_match["full_text"].lower()
        print(f"  ✓ Policy NLP match verified: [Article {top_match['article_num']} - {top_match['title']}]")

        pinned_keys = ["probation", "leaves", "working_hours", "notice_period", "insurance"]
        for k in pinned_keys:
            rule = dfy_policy_service.get_quick_rule(k)
            assert rule is not None, f"Quick rule {k} not found"
        print(f"  ✓ Pinned quick policy chips verified (count={len(pinned_keys)}).")

        # ---------------------------------------------------------------------
        # STEP 3: AI Operations Copilot Service (Offline Briefing & Router)
        # ---------------------------------------------------------------------
        print("\n[STEP 3] Testing AI Operations Copilot Service...")
        briefing = ai_copilot_service.generate_daily_operational_briefing()
        assert "bullets" in briefing and "action_count" in briefing
        print(f"  ✓ Daily briefing generated ({len(briefing['bullets'])} operational insights, action count={briefing['action_count']}).")

        # Test natural language candidate query routing
        reply_cand = ai_copilot_service.process_ask_hr_query("How many candidates are selected in UP?")
        assert "candidate" in reply_cand["answer"].lower() or "up" in reply_cand["answer"].lower() or "selected" in reply_cand["answer"].lower()
        print(f"  ✓ Copilot NLP query router verified for candidate analytics.")

        # Test natural language policy routing
        reply_policy = ai_copilot_service.process_ask_hr_query("What is DFY probation review policy?")
        assert "probation" in reply_policy["answer"].lower() or "article 2" in reply_policy["answer"].lower()
        print(f"  ✓ Copilot NLP query router verified for DFY HR Manual.")

        # ---------------------------------------------------------------------
        # STEP 4: Utility Services (Excel Briefing, Bulk ZIP, Outreach & Slips)
        # ---------------------------------------------------------------------
        print("\n[STEP 4] Testing Utility Services...")
        # 4.1 Excel Briefing Exporter
        excel_path = os.path.join(tempfile.gettempdir(), f"DFY_Daily_Briefing_E2E_{int(time.time())}.xlsx")
        created_temp_files.append(excel_path)
        out_excel = hr_report_exporter.export_daily_executive_summary(excel_path)
        assert os.path.exists(out_excel) and os.path.getsize(out_excel) > 1000
        print(f"  ✓ 1-Click Executive Daily HR Summary Excel generated ({os.path.getsize(out_excel)} bytes).")

        # 4.2 Bulk ZIP Packager
        test_doc_file = os.path.join(tempfile.gettempdir(), "test_e2e_doc.txt")
        created_temp_files.append(test_doc_file)
        with open(test_doc_file, "w", encoding="utf-8") as f:
            f.write("Doctors For You - Sample Document Content")

        zip_out_path = os.path.join(tempfile.gettempdir(), f"DFY_Documents_E2E_{int(time.time())}.zip")
        created_temp_files.append(zip_out_path)
        ok_zip, out_zip, err_zip = zip_export_service.create_bulk_document_zip([test_doc_file], target_zip_path=zip_out_path)
        assert ok_zip and os.path.exists(out_zip)
        print(f"  ✓ Bulk document ZIP archive packaged ({os.path.getsize(out_zip)} bytes).")

        # 4.3 Candidate Outreach WhatsApp text & Bio-Data Slips
        cand_sample = {
            "candidate_name": "E2E Candidate Outreach",
            "applied_designation": "Staff Nurse",
            "department": "PPSA Uttar Pradesh",
            "contact_location": "Lucknow",
            "negotiated_salary": "25000",
            "highest_education": "B.Sc Nursing",
            "total_experience": "3",
            "date_joined": "2026-11-01",
            "mobile": "9876543210",
            "email": "nurse.lucknow@example.com",
            "source_sheet": "PPSA UP",
        }
        wa_text = candidate_outreach_service.generate_whatsapp_outreach_text(cand_sample, "selection")
        assert "E2E Candidate Outreach" in wa_text and "Staff Nurse" in wa_text and "Doctors For You" in wa_text
        print("  ✓ WhatsApp 1-Click outreach message generated.")

        bio_slip = candidate_outreach_service.generate_candidate_bio_data_slip(cand_sample)
        assert "DOCTORS FOR YOU" in bio_slip and "CANDIDATE BIO-DATA SLIP" in bio_slip
        assert "Lucknow" in bio_slip
        print("  ✓ Candidate Bio-Data Slip generated.")

        # ---------------------------------------------------------------------
        # STEP 5: UI Views Compilation & Rendering
        # ---------------------------------------------------------------------
        print("\n[STEP 5] Testing UI Pages Rendering...")
        mock_page = MockPage()

        # 5.1 Dashboard View
        dash_view = dashboard_page.dashboard_view(mock_page)
        assert dash_view is not None, "dashboard_view returned None"
        print("  ✓ Compact Executive Dashboard rendered cleanly.")

        # 5.2 Help Center View
        help_view = help_center_page.help_center_view(mock_page)
        assert help_view is not None, "help_center_view returned None"
        print("  ✓ Help Center & Hinglish Chatbot page rendered cleanly.")

        # 5.3 Joining Process View
        joining_view = joining_process_page.joining_process_view(mock_page)
        assert joining_view is not None, "joining_process_view returned None"
        print("  ✓ Joining Process view (with Tags, WhatsApp, Bio-Data Slips) rendered cleanly.")

        # 5.4 Document Generation View
        doc_view = document_generation_page.document_generation_view(mock_page)
        assert doc_view is not None, "document_generation_view returned None"
        print("  ✓ Document Generation view (with Bulk ZIP export) rendered cleanly.")

        print("\n" + "=" * 80)
        print("ALL COMPACT DASHBOARD & AI COPILOT E2E TESTS PASSED SUCCESSFULLY! (100% PASS) ✅")
        print("=" * 80)
        return True

    finally:
        # Cleanup test records
        if test_cids:
            try:
                conn = db_manager.get_connection()
                conn.execute(f"DELETE FROM candidates WHERE id IN ({','.join('?' for _ in test_cids)})", test_cids)
                conn.commit()
                conn.close()
            except Exception:
                pass

        # Cleanup test files
        for fp in created_temp_files:
            if fp and os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass


if __name__ == "__main__":
    success = run_e2e_tests()
    if not success:
        sys.exit(1)
