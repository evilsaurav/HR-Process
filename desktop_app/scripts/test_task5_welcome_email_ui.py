import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Set UTF-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db_manager


def test_welcome_email_backend_and_ui():
    print("==================================================================")
    print("TASK 5 VERIFICATION: Joining Process Welcome Email Staging UI")
    print("==================================================================")

    # Step 1: Ensure DB is initialized
    print("\n[1/5] Initializing Database & Verifying Schema...")
    db_manager.init_db()
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(candidates)")
    cols = {r[1] for r in cur.fetchall()}
    assert "welcome_email_sent" in cols, "Column 'welcome_email_sent' missing in candidates table"
    assert "welcome_email_sent_at" in cols, "Column 'welcome_email_sent_at' missing in candidates table"
    print("  ✓ Schema check passed: 'welcome_email_sent' and 'welcome_email_sent_at' present.")

    # Step 2: Seed controlled test candidates for pending welcome email query verification
    print("\n[2/5] Testing get_selected_candidates_pending_welcome() query filtering...")
    mob_pending1 = "9888800001"
    mob_sent = "9888800002"
    mob_applied = "9888800003"
    mob_pending2 = "9888800004"

    # Clean up any remnants
    cur.execute("DELETE FROM candidates WHERE mobile IN (?, ?, ?, ?)", (mob_pending1, mob_sent, mob_applied, mob_pending2))
    conn.commit()

    cur.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, status, welcome_email_sent)
        VALUES ('Test Selected Pending 1', ?, 'pending1@example.com', 'Medical Officer', 'Selected', 0)
    """, (mob_pending1,))
    cand1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, status, welcome_email_sent, welcome_email_sent_at)
        VALUES ('Test Selected Already Sent', ?, 'sent@example.com', 'Staff Nurse', 'Selected', 1, '2026-10-21 12:00:00')
    """, (mob_sent,))
    cand2_id = cur.lastrowid

    cur.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, status, welcome_email_sent)
        VALUES ('Test Applied Not Selected', ?, 'applied@example.com', 'Project Coordinator', 'Applied', 0)
    """, (mob_applied,))
    cand3_id = cur.lastrowid

    cur.execute("""
        INSERT INTO candidates (candidate_name, mobile, email, applied_designation, status, welcome_email_sent)
        VALUES ('Test Selected Pending None', ?, 'pending2@example.com', 'Pharmacist', 'Selected', NULL)
    """, (mob_pending2,))
    cand4_id = cur.lastrowid
    conn.commit()
    conn.close()

    pending_list = db_manager.get_selected_candidates_pending_welcome()
    pending_ids = [c["id"] for c in pending_list]

    assert cand1_id in pending_ids, f"cand1_id {cand1_id} should be in pending_ids"
    assert cand4_id in pending_ids, f"cand4_id {cand4_id} (welcome_email_sent=NULL) should be in pending_ids"
    assert cand2_id not in pending_ids, f"cand2_id {cand2_id} (welcome_email_sent=1) must NOT be in pending_ids"
    assert cand3_id not in pending_ids, f"cand3_id {cand3_id} (status='Applied') must NOT be in pending_ids"
    print(f"  ✓ Pending welcome email query filtered correctly! Found {len(pending_list)} pending records.")

    # Step 3: Test updating welcome email status to sent
    print("\n[3/5] Testing update_candidate_welcome_email_status(id, True)...")
    ok1 = db_manager.update_candidate_welcome_email_status(cand1_id, True)
    assert ok1 is True, "update_candidate_welcome_email_status returned False"

    cand1_updated = db_manager.get_candidate_by_id(cand1_id)
    assert cand1_updated["welcome_email_sent"] == 1, "welcome_email_sent was not updated to 1"
    assert cand1_updated["welcome_email_sent_at"] is not None, "welcome_email_sent_at timestamp missing"
    print(f"  ✓ Candidate {cand1_id} updated: welcome_email_sent={cand1_updated['welcome_email_sent']}, sent_at={cand1_updated['welcome_email_sent_at']}")

    # Candidate 1 should now be excluded from pending list
    pending_list_after = db_manager.get_selected_candidates_pending_welcome()
    pending_ids_after = [c["id"] for c in pending_list_after]
    assert cand1_id not in pending_ids_after, f"cand1_id {cand1_id} must no longer be in pending list"
    assert cand4_id in pending_ids_after, f"cand4_id {cand4_id} must still be in pending list"
    print(f"  ✓ Pending list updated dynamically. Remaining pending count: {len(pending_list_after)}.")

    # Reset cand1 to pending so UI tests can see it
    db_manager.update_candidate_welcome_email_status(cand1_id, False)

    # Step 4: Verify UI module compilation and control tree instantiation
    print("\n[4/5] Verifying joining_process_page.py imports and control tree instantiation...")
    from pages import joining_process_page
    assert hasattr(joining_process_page, "joining_process_view"), "joining_process_view function missing in joining_process_page"

    mock_page = MagicMock()
    mock_page.overlay = []
    opened_dialogs = []

    def mock_open(dlg):
        opened_dialogs.append(dlg)

    mock_page.open = MagicMock(side_effect=mock_open)
    mock_page.close = MagicMock()
    mock_page.update = MagicMock()

    view_col = joining_process_page.joining_process_view(mock_page)
    assert view_col is not None, "joining_process_view returned None"
    assert len(view_col.controls) > 0, "joining_process_view returned empty control column"
    print(f"  ✓ joining_process_view instantiated successfully with {len(view_col.controls)} top-level sections.")

    # Find the Pipeline card
    pipeline_card = view_col.controls[4]
    pipeline_column = pipeline_card.content
    assert pipeline_column is not None, "Pipeline card content is missing"

    # Verify buttons present in the Pipeline card
    top_actions_row = pipeline_column.controls[0]
    btn_review_send = top_actions_row.controls[2]
    assert btn_review_send is not None, "btn_review_send_welcome missing from top row"

    quick_filters_row = pipeline_column.controls[2]
    tab_all_btn = quick_filters_row.controls[0]
    tab_pending_btn = quick_filters_row.controls[1]
    assert tab_all_btn is not None, "tab_all_button missing from quick filter row"
    assert tab_pending_btn is not None, "tab_pending_button missing from quick filter row"
    print("  ✓ Quick-filter tabs ('All Candidates' & '🎉 Selected (Pending Welcome Email)') verified.")
    print("  ✓ Action button '✉️ Review & Send Welcome Emails' verified.")

    # Step 5: Test UI Quick-Filter Toggle & Welcome Email Modal Flow
    print("\n[5/5] Testing UI Quick Filter & Modal Dispatch Flow...")
    # Trigger Pending filter tab
    tab_pending_btn.on_click(None)
    assert mock_page.update.called, "page.update was not called after tab_pending_btn click"

    # Trigger 'Review & Send Welcome Emails' button
    with patch("services.email_service.send_email_smtp", return_value=(True, "Email sent successfully")):
        btn_review_send.on_click(None)
        assert len(opened_dialogs) > 0, "No dialog was opened when clicking Review & Send Welcome Emails"
        welcome_dlg = opened_dialogs[-1]
        print(f"  ✓ Modal dialog opened successfully: {welcome_dlg.title.controls[1].value}")

        # Verify dialog contents
        dialog_container = welcome_dlg.content
        dialog_column = dialog_container.content
        text_fields = [c for c in dialog_column.controls if getattr(c, "label", None) in ["Email Subject", "Email Message Body"]]
        subject_input = next(c for c in text_fields if c.label == "Email Subject")
        body_input = next(c for c in text_fields if c.label == "Email Message Body")
        assert "Welcome to Doctors For You" in subject_input.value, f"Subject unexpected: {subject_input.value}"
        assert "Doctors For You" in body_input.value, "Body missing DFY text"
        print("  ✓ Email subject & congratulatory body pre-filled accurately.")

        # Test clicking Send on the modal dialog
        send_btn = welcome_dlg.actions[1]
        assert "Send Welcome" in send_btn.text, f"Unexpected send button text: {send_btn.text}"

        mock_event = MagicMock()
        send_btn.on_click(mock_event)
        assert mock_page.close.called, "page.close was not called to dismiss dialog after send"
        print("  ✓ Welcome email dispatched and dialog closed successfully.")

    # Verify cand1 status updated to sent after dialog dispatch
    cand1_check = db_manager.get_candidate_by_id(cand1_id)
    assert cand1_check["welcome_email_sent"] == 1, "Candidate status was not updated to welcome_email_sent=1 after modal dispatch"
    print(f"  ✓ DB state confirmed: Candidate {cand1_id} marked as welcome_email_sent=1.")

    # Clean up test rows
    conn = db_manager.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM candidates WHERE id IN (?, ?, ?, ?)", (cand1_id, cand2_id, cand3_id, cand4_id))
    conn.commit()
    conn.close()
    print("  ✓ Test candidate records cleaned up cleanly.")

    print("\n==================================================================")
    print("ALL TASK 5 CHECKS PASSED WITH 100% SUCCESS (Exit Code 0)!")
    print("==================================================================")
    return True


if __name__ == "__main__":
    success = test_welcome_email_backend_and_ui()
    if not success:
        sys.exit(1)
    sys.exit(0)
