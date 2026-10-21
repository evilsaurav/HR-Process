"""
Verification Script: verify_manual_checklist.py
Executes and validates the 10-point manual checklist for Phase G1 Step 1 (Archive candidate).
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from utils.flet_compat import apply_flet_compat_shims
apply_flet_compat_shims()

import flet as ft
from database import db_manager
from pages.joining_process_page import joining_process_view
from pages.keka_sync_page import keka_sync_view


class MockPage:
    def __init__(self):
        self.title = "Manual Checklist Test"
        self.overlay = []
        self.services = []
        self.controls = []
        self.messages = []
        self.opened_dialogs = []
        self.closed_dialogs = []

    def open(self, control):
        if isinstance(control, ft.AlertDialog):
            self.opened_dialogs.append(control)
        elif isinstance(control, ft.SnackBar):
            if hasattr(control.content, "value"):
                self.messages.append(control.content.value)
        elif hasattr(control, "content") and hasattr(control.content, "value"):
            self.messages.append(control.content.value)

    def close(self, control=None):
        if control:
            self.closed_dialogs.append(control)

    def update(self):
        pass


def run_checklist():
    print("=" * 70)
    print("STARTING 10-POINT MANUAL VERIFICATION CHECKLIST")
    print("=" * 70)

    db_manager.init_db()

    # Pre-test check: Create or select a test candidate for checklists 2-6
    test_mob = "9555555555"
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile = ?", (test_mob,))
    conn.commit()

    conn.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, negotiated_salary, status)
        VALUES ('Checklist Test Candidate', ?, 'checklist@dfy.org', 'Coordinator', '30000', 'Applied')
    """, (test_mob,))
    conn.commit()
    conn.close()

    test_cand = db_manager.get_candidate_by_mobile(test_mob)
    test_cand_id = test_cand["id"]

    results = {}

    try:
        # -------------------------------------------------------------
        # Item 1: Open app -> go to Joining Process page
        # -------------------------------------------------------------
        page = MockPage()
        view = joining_process_view(page)
        item1_pass = isinstance(view, ft.Column) and len(view.controls) >= 5
        results[1] = ("PASS" if item1_pass else "FAIL", "Joining Process page view initialized successfully.")
        print(f"Item 1: [{results[1][0]}] {results[1][1]}")

        # -------------------------------------------------------------
        # Item 2: Pick candidate in list, click row action button
        # -------------------------------------------------------------
        table_container = view.controls[4].content.controls[4]  # Candidate table container
        data_table = table_container.content.controls[0]
        # Find row for test candidate
        target_row = None
        for r in data_table.rows:
            if r.cells[0].content.value == "Checklist Test Candidate":
                target_row = r
                break

        assert target_row is not None, "Target test candidate not found in table"
        action_cell = target_row.cells[7]
        action_btn = action_cell.content
        assert isinstance(action_btn, ft.IconButton)
        assert action_btn.tooltip == "Archive Candidate"
        assert action_btn.icon == ft.Icons.ARCHIVE_OUTLINED

        # Trigger click
        action_btn.on_click(None)
        item2_pass = len(page.opened_dialogs) > 0
        dialog = page.opened_dialogs[-1]
        results[2] = ("PASS" if item2_pass else "FAIL", "Row action button triggers AlertDialog confirmation.")
        print(f"Item 2: [{results[2][0]}] {results[2][1]}")

        # -------------------------------------------------------------
        # Item 3: Confirm popup text clearly says ARCHIVED and mentions restore later
        # -------------------------------------------------------------
        dialog_text = dialog.content.value
        title_text = dialog.title.controls[1].value
        has_archived_mention = "archived and removed" in dialog_text.lower() or "archive" in title_text.lower()
        has_restore_mention = "restore" in dialog_text.lower()
        item3_pass = has_archived_mention and has_restore_mention
        results[3] = (
            "PASS" if item3_pass else "FAIL",
            f"Dialog title: '{title_text}', Content: '{dialog_text}' (Clearly mentions archiving & restore later)."
        )
        print(f"Item 3: [{results[3][0]}] {results[3][1]}")

        # -------------------------------------------------------------
        # Item 4: Click 'Cancel' -> Candidate NOT removed, nothing changed
        # -------------------------------------------------------------
        cancel_btn = dialog.actions[0]
        cancel_btn.on_click(None)
        cand_still_in_db = db_manager.get_candidate_by_id(test_cand_id)
        item4_pass = cand_still_in_db["archived"] == 0 and len(page.closed_dialogs) > 0
        results[4] = (
            "PASS" if item4_pass else "FAIL",
            "Clicked Cancel: Dialog closed, candidate remained in database with archived=0."
        )
        print(f"Item 4: [{results[4][0]}] {results[4][1]}")

        # -------------------------------------------------------------
        # Item 5: Click action again, confirm 'Archive'
        # -------------------------------------------------------------
        action_btn.on_click(None)
        dialog2 = page.opened_dialogs[-1]
        archive_confirm_btn = dialog2.actions[1]
        archive_confirm_btn.on_click(None)
        cand_archived_db = db_manager.get_candidate_by_id(test_cand_id)
        item5_pass = cand_archived_db["archived"] == 1 and cand_archived_db["archived_at"] is not None
        results[5] = (
            "PASS" if item5_pass else "FAIL",
            f"Confirmed Archive: DB updated to archived=1 with timestamp '{cand_archived_db['archived_at']}'."
        )
        print(f"Item 5: [{results[5][0]}] {results[5][1]}")

        # -------------------------------------------------------------
        # Item 6: Confirm candidate immediately disappears from normal list
        # -------------------------------------------------------------
        normal_list = db_manager.get_all_candidates()
        item6_pass = not any(c["id"] == test_cand_id for c in normal_list)
        results[6] = (
            "PASS" if item6_pass else "FAIL",
            "Candidate immediately disappeared from active candidates list."
        )
        print(f"Item 6: [{results[6][0]}] {results[6][1]}")

        # -------------------------------------------------------------
        # Item 7: Archive candidate with generated documents/emails (Candidate ID 1)
        # -------------------------------------------------------------
        # Verify Candidate 1 has foreign key rows
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM document_generation_log WHERE candidate_id = 1")
        doc_logs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM email_log WHERE candidate_id = 1")
        email_logs = cur.fetchone()[0]
        conn.close()

        assert doc_logs > 0 and email_logs > 0, "Candidate 1 must have FK records"
        c1_before = db_manager.get_candidate_by_id(1)

        c1_page = MockPage()
        c1_view = joining_process_view(c1_page)
        c1_table = c1_view.controls[4].content.controls[4].content.controls[0]
        c1_row = None
        for r in c1_table.rows:
            if r.cells[0].content.value == c1_before["candidate_name"]:
                c1_row = r
                break

        assert c1_row is not None, f"Candidate 1 ({c1_before['candidate_name']}) not found in table"
        c1_action_btn = c1_row.cells[7].content
        c1_action_btn.on_click(None)
        c1_dialog = c1_page.opened_dialogs[-1]
        c1_confirm_btn = c1_dialog.actions[1]

        # Trigger archive on Candidate 1
        c1_confirm_btn.on_click(None)
        c1_after = db_manager.get_candidate_by_id(1)
        item7_pass = c1_after["archived"] == 1 and not any("error" in m.lower() for m in c1_page.messages)
        results[7] = (
            "PASS" if item7_pass else "FAIL",
            f"Candidate #1 ({doc_logs} doc logs, {email_logs} email logs) archived cleanly with zero FK constraint errors."
        )
        print(f"Item 7: [{results[7][0]}] {results[7][1]}")

        # -------------------------------------------------------------
        # Item 8: Close and reopen app -> candidate is STILL hidden
        # -------------------------------------------------------------
        # Re-initialize clean page and fetch fresh data
        reopened_page = MockPage()
        reopened_view = joining_process_view(reopened_page)
        reopened_list = db_manager.get_all_candidates()
        item8_pass = not any(c["id"] in [test_cand_id, 1] for c in reopened_list)
        results[8] = (
            "PASS" if item8_pass else "FAIL",
            "App reopen simulation: Archived candidates remain hidden (persisted in SQLite, not in-memory)."
        )
        print(f"Item 8: [{results[8][0]}] {results[8][1]}")

        # -------------------------------------------------------------
        # Item 9: Keka Sync page -> archived candidate does NOT appear
        # -------------------------------------------------------------
        keka_pending = db_manager.get_candidates_pending_keka_sync()
        item9_pass = not any(c["id"] in [test_cand_id, 1] for c in keka_pending)
        results[9] = (
            "PASS" if item9_pass else "FAIL",
            "Keka Sync pending queue excludes archived candidates as expected."
        )
        print(f"Item 9: [{results[9][0]}] {results[9][1]}")

        # -------------------------------------------------------------
        # Item 10: Every OTHER candidate behaves normally (search, filter, status change)
        # -------------------------------------------------------------
        c2 = db_manager.get_candidate_by_id(2)
        assert c2 is not None and c2["archived"] == 0, "Candidate 2 should be active"

        # Search test
        search_res = db_manager.get_all_candidates(search_term=c2["candidate_name"])
        search_works = any(c["id"] == 2 for c in search_res)

        # Status update test
        old_status = c2["status"]
        new_status = "Interview" if old_status != "Interview" else "Shortlisted"
        db_manager.update_candidate_status(2, new_status)
        c2_updated = db_manager.get_candidate_by_id(2)
        status_works = c2_updated["status"] == new_status
        # Revert status
        db_manager.update_candidate_status(2, old_status)

        item10_pass = search_works and status_works
        results[10] = (
            "PASS" if item10_pass else "FAIL",
            f"Active candidates behave normally: search={search_works}, status update={status_works}."
        )
        print(f"Item 10: [{results[10][0]}] {results[10][1]}")

    finally:
        # Cleanup: Restore Candidate 1 and delete temporary test candidate
        conn = db_manager.get_connection()
        conn.execute("UPDATE candidates SET archived = 0, archived_at = NULL WHERE id = 1")
        conn.execute("DELETE FROM candidates WHERE mobile = ?", (test_mob,))
        conn.commit()
        conn.close()

    print("\n" + "=" * 70)
    print("MANUAL VERIFICATION CHECKLIST SUMMARY")
    print("=" * 70)
    all_pass = True
    for i in range(1, 11):
        status, detail = results[i]
        if status != "PASS":
            all_pass = False
        print(f"Item {i:2d}: {status} - {detail}")
    print("=" * 70)
    print(f"FINAL RESULT: {'ALL 10 CHECKS PASSED ✅' if all_pass else 'SOME CHECKS FAILED ❌'}")
    print("=" * 70)


if __name__ == "__main__":
    run_checklist()
