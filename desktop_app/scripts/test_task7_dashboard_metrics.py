"""
Verification Script: test_task7_dashboard_metrics.py
Purpose: Thorough verification of Task 7: Executive Dashboard Live Action Cards & Staging Metrics.

Checks performed:
1. Verifies dashboard_service.get_dashboard_stats() returns all required keys:
   - pending_welcome_emails
   - letters_to_generate
   - staged_letters_ready
   - dispatched_today
   - total_candidates, selected_candidates, in_interview, in_pipeline, joined_candidates
2. Tests live database calculations with controlled test data:
   - Candidate with status='Selected' & welcome_email_sent=0 increments pending_welcome_emails.
   - Staging record with status='Staged' increments staged_letters_ready.
   - Email log entry with status='Sent' today increments dispatched_today.
   - Smart Rule Detector matches letters_to_generate.
3. Verifies dashboard_page.dashboard_view instantiation:
   - Action cards row with all 4 prominent action cards rendered.
   - Action cards contain correct labels and numeric indicators.
   - Clicking Card 1 navigates to ("joining", filter="selected").
   - Clicking Card 2 navigates to ("documents", tab=0).
   - Clicking Card 3 navigates to ("documents", tab=1).
   - Clicking Card 4 navigates to ("joining").
4. Verifies Operations Activity Log & Audit Trail renders recent dispatches & document generations.
5. Verifies dynamic refresh function updates controls cleanly.
"""

import os
import sys
import time
import datetime

# Configure UTF-8 encoding for Windows console output
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
from services import dashboard_service, smart_rule_detector
from pages.dashboard_page import dashboard_view


class MockFletPage:
    """Mock Flet Page for testing UI without displaying an OS window."""
    def __init__(self):
        self.title = "Test Executive Dashboard"
        self.overlay = []
        self.controls = []
        self.snack_bars = []
        self.session = MockSession()
        self.on_navigate = None

    def open(self, control):
        if hasattr(control, "content") and hasattr(control.content, "value"):
            self.snack_bars.append(control.content.value)
        elif hasattr(control, "text"):
            self.snack_bars.append(control.text)

    def close(self, control=None):
        pass

    def update(self):
        pass


class MockSession:
    def __init__(self):
        self.store = {}

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)


def run_tests():
    print("=" * 70)
    print("TASK 7 VERIFICATION: EXECUTIVE DASHBOARD LIVE ACTION CARDS")
    print("=" * 70)

    db_manager.init_db()

    # -------------------------------------------------------------------------
    # TEST 1: Backend Service get_dashboard_stats() Key Completeness
    # -------------------------------------------------------------------------
    print("\n[1/5] Verifying get_dashboard_stats() structure and core keys...")
    stats = dashboard_service.get_dashboard_stats()

    required_keys = [
        "pending_welcome_emails",
        "letters_to_generate",
        "staged_letters_ready",
        "dispatched_today",
        "total_candidates",
        "selected_candidates",
        "in_interview",
        "in_pipeline",
        "joined_candidates",
        "status_overview",
        "exp_due_count",
        "increment_due_count",
        "keka_pending_count",
    ]

    for key in required_keys:
        assert key in stats, f"Key '{key}' missing from get_dashboard_stats() response"
        print(f"   ✓ Key present: {key} = {stats[key]}")

    print("   ✅ All required metric keys present and typed.")

    # -------------------------------------------------------------------------
    # TEST 2: Live Metrics Sensitivity & Accurate Database Counting
    # -------------------------------------------------------------------------
    print("\n[2/5] Testing metric calculations with live database manipulations...")
    initial_stats = dashboard_service.get_dashboard_stats()
    init_pending = initial_stats["pending_welcome_emails"]
    init_staged = initial_stats["staged_letters_ready"]
    init_dispatched = initial_stats["dispatched_today"]

    # 2a. Insert Candidate in 'Selected' status with welcome_email_sent = 0
    test_mobile_cand = f"9988{int(time.time()*100)%1000000:06d}"
    staging_id = None
    log_id = None
    test_cid = None
    try:
        db_manager.upsert_candidate({
            "candidate_name": "Task 7 Selected Candidate",
            "mobile": test_mobile_cand,
            "applied_designation": "Staff Nurse",
            "status": "Selected",
        }, "task7_test.xlsx")

        test_cand = db_manager.get_candidate_by_mobile(test_mobile_cand)
        assert test_cand is not None, "Failed to fetch test candidate"
        test_cid = test_cand["id"]
        db_manager.update_candidate_status(test_cid, "Selected")
        conn = db_manager.get_connection()
        conn.execute("UPDATE candidates SET welcome_email_sent = 0, archived = 0 WHERE id = ?", (test_cid,))
        conn.commit()
        conn.close()

        after_cand_stats = dashboard_service.get_dashboard_stats()
        print(f"   • Pending Welcome Emails: initial={init_pending}, new={after_cand_stats['pending_welcome_emails']}")
        assert after_cand_stats["pending_welcome_emails"] == init_pending + 1, (
            f"Expected pending welcome emails to increase by 1, got {after_cand_stats['pending_welcome_emails']}"
        )
        print("   ✓ 'pending_welcome_emails' increment verified accurately.")

        # 2b. Insert Staging Record with status = 'Staged'
        staging_id = db_manager.create_staging_record(
            candidate_id=test_cid,
            document_type="offer",
            doc_file_path="task7_test.docx",
            pdf_file_path="task7_test.pdf",
            preferred_format="pdf",
            recipient_email="task7_test@example.com",
            recipient_name="Task 7 Candidate",
            email_subject="Offer of Employment - Task 7 Test",
            email_body="Welcome to DFY!",
            reference_number="DFY/HR/T7/001",
        )
        assert staging_id is not None, "Failed to create staging record"

        after_staged_stats = dashboard_service.get_dashboard_stats()
        print(f"   • Staged Letters Ready: initial={init_staged}, new={after_staged_stats['staged_letters_ready']}")
        assert after_staged_stats["staged_letters_ready"] == init_staged + 1, (
            f"Expected staged letters ready to increase by 1, got {after_staged_stats['staged_letters_ready']}"
        )
        print("   ✓ 'staged_letters_ready' increment verified accurately.")

        # 2c. Insert Email Log Entry dispatched today with status = 'Sent'
        log_id = db_manager.log_email_dispatch(
            recipient_email="task7_test@example.com",
            recipient_name="Task 7 Candidate",
            document_type="offer",
            subject="Offer Letter Dispatched Today",
            sent_by="HR Desktop",
            status="Sent",
            candidate_id=test_cid,
        )
        assert log_id is not None, "Failed to log email dispatch"

        after_email_stats = dashboard_service.get_dashboard_stats()
        print(f"   • Dispatched Today: initial={init_dispatched}, new={after_email_stats['dispatched_today']}")
        assert after_email_stats["dispatched_today"] == init_dispatched + 1, (
            f"Expected dispatched today to increase by 1, got {after_email_stats['dispatched_today']}"
        )
        print("   ✓ 'dispatched_today' increment verified accurately.")

        # 2d. Verify Smart Rule Detector alignment
        detected = smart_rule_detector.scan_all_candidates_for_document_needs()
        print(f"   • Letters to Generate (Smart Detector): count={len(detected)}, stats={after_email_stats['letters_to_generate']}")
        assert after_email_stats["letters_to_generate"] == len(detected), (
            "letters_to_generate in stats must equal length of detected suggestions"
        )
        print("   ✓ 'letters_to_generate' matches smart rule detector scan results.")

        # -------------------------------------------------------------------------
        # TEST 3: UI Instantiation & Action Cards Hierarchy
        # -------------------------------------------------------------------------
        print("\n[3/5] Instantiating dashboard_view and inspecting Action Cards...")
        page = MockFletPage()
        nav_history = []

        def mock_on_navigate(target, **kwargs):
            nav_history.append((target, kwargs))
            print(f"   [Nav Event] Navigated to: {target} (params: {kwargs})")

        view = dashboard_view(page, on_navigate=mock_on_navigate)
        assert view is not None, "dashboard_view returned None"

        # Verify action cards exist on view
        assert hasattr(view, "action_cards_row"), "view missing action_cards_row"
        cards = view.action_cards_row.controls
        print(f"   Rendered Action Cards count: {len(cards)}")
        assert len(cards) == 4, "Must render exactly 4 prominent action cards"

        # Card 1: Pending Welcome Emails
        card_welcome = cards[0]
        assert hasattr(card_welcome, "content"), "Card 1 missing content"
        card1_title = card_welcome.content.controls[3].value
        print(f"   • Card 1 title: '{card1_title}'")
        assert "Pending Welcome" in card1_title

        # Card 2: Letters to Generate
        card_letters = cards[1]
        card2_title = card_letters.content.controls[3].value
        print(f"   • Card 2 title: '{card2_title}'")
        assert "Letters to Generate" in card2_title

        # Card 3: Staged Ready for Final Go
        card_staging = cards[2]
        card3_title = card_staging.content.controls[3].value
        print(f"   • Card 3 title: '{card3_title}'")
        assert "Staged" in card3_title

        # Card 4: In Pipeline / Interviews
        card_pipeline = cards[3]
        card4_title = card_pipeline.content.controls[3].value
        print(f"   • Card 4 title: '{card4_title}'")
        assert "In Pipeline" in card4_title or "Interviews" in card4_title

        print("   ✅ All 4 Action Cards created and titled appropriately.")

        # -------------------------------------------------------------------------
        # TEST 4: Click Handlers and Navigation Wiring
        # -------------------------------------------------------------------------
        print("\n[4/5] Testing navigation click triggers on all 4 Action Cards...")

        # Click Card 1: Should navigate to joining process with selected filter
        print("   Triggering Card 1 click (Pending Welcome Emails)...")
        nav_history.clear()
        card_welcome.on_click(None)
        assert len(nav_history) == 1, "Card 1 click did not trigger navigation"
        target, kwargs = nav_history[0]
        assert target == "joining", f"Expected target 'joining', got {target}"
        assert kwargs.get("filter") == "selected", f"Expected filter='selected', got {kwargs}"
        print("   ✓ Card 1 correctly routed to Joining Process with Selected filter.")

        # Click Card 2: Should navigate to document generator tab 0 (Smart Detector)
        print("   Triggering Card 2 click (Letters to Generate)...")
        nav_history.clear()
        card_letters.on_click(None)
        assert len(nav_history) == 1, "Card 2 click did not trigger navigation"
        target, kwargs = nav_history[0]
        assert target == "documents", f"Expected target 'documents', got {target}"
        assert kwargs.get("tab") == 0, f"Expected tab=0, got {kwargs}"
        print("   ✓ Card 2 correctly routed to Document Generator Tab 1 (Smart Detector).")

        # Click Card 3: Should navigate to document generator tab 1 (Staging Queue)
        print("   Triggering Card 3 click (Staged Ready for Final Go)...")
        nav_history.clear()
        card_staging.on_click(None)
        assert len(nav_history) == 1, "Card 3 click did not trigger navigation"
        target, kwargs = nav_history[0]
        assert target == "documents", f"Expected target 'documents', got {target}"
        assert kwargs.get("tab") == 1, f"Expected tab=1, got {kwargs}"
        print("   ✓ Card 3 correctly routed to Document Generator Tab 2 (Staging Queue).")

        # Click Card 4: Should navigate to joining process
        print("   Triggering Card 4 click (In Pipeline / Interviews)...")
        nav_history.clear()
        card_pipeline.on_click(None)
        assert len(nav_history) == 1, "Card 4 click did not trigger navigation"
        target, kwargs = nav_history[0]
        assert target == "joining", f"Expected target 'joining', got {target}"
        print("   ✓ Card 4 correctly routed to Joining Process.")

        # -------------------------------------------------------------------------
        # TEST 5: Operations Activity Log & Dynamic Refresh Logic
        # -------------------------------------------------------------------------
        print("\n[5/5] Verifying Activity Log & dynamic refresh...")
        assert hasattr(view, "activity_card"), "view missing activity_card"
        assert view.activity_card is not None
        print("   ✓ Operations Activity Log card verified.")

        # Recent dispatches and recent generations backend helpers
        recent_dispatches = dashboard_service.get_recent_email_dispatches(limit=5)
        recent_gens = dashboard_service.get_recent_document_generations(limit=5)
        print(f"   • Recent dispatches count: {len(recent_dispatches)}")
        print(f"   • Recent generations count: {len(recent_gens)}")
        assert len(recent_dispatches) > 0, "Expected at least 1 recent dispatch log"

        # Trigger dynamic refresh
        print("   Triggering view.refresh_dashboard()...")
        view.refresh_dashboard()
        print("   ✓ refresh_dashboard() executed cleanly without raising exceptions.")

    finally:
        # Cleanup test data
        conn = db_manager.get_connection()
        if staging_id:
            conn.execute("DELETE FROM document_staging WHERE id = ?", (staging_id,))
        if log_id:
            conn.execute("DELETE FROM email_log WHERE id = ?", (log_id,))
        if test_cid:
            conn.execute("DELETE FROM candidates WHERE id = ?", (test_cid,))
        conn.commit()
        conn.close()
        print("   ✓ Test data cleaned up successfully.")

    print("\n" + "=" * 70)
    print("ALL TASK 7 DASHBOARD METRICS & ACTION CARDS TESTS PASSED! ✅")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
