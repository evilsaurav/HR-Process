"""
Verification Script: test_email_scheduling_queue.py
Task 6 Test Suite: Email Scheduling & Dispatch Queue.
"""

import sys
import os
import datetime

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_APP_DIR = os.path.dirname(SCRIPT_DIR)
if DESKTOP_APP_DIR not in sys.path:
    sys.path.insert(0, DESKTOP_APP_DIR)

from database import db_manager
from services.email_scheduler_service import (
    enqueue_scheduled_email,
    list_scheduled_emails,
    cancel_schedule,
    process_due_scheduled_emails,
)


def run_tests():
    print("=" * 70)
    print("RUNNING TASK 6 TESTS: EMAIL SCHEDULING & QUEUE")
    print("=" * 70)

    db_manager.init_db()

    mob = "9822233344"
    conn = db_manager.get_connection()
    conn.execute("DELETE FROM candidates WHERE mobile = ?", (mob,))
    conn.commit()
    conn.close()

    db_manager.upsert_candidate({
        "candidate_name": "Scheduler Test Person",
        "mobile": mob,
        "email": "sched.test@example.com",
    }, "Test Script")
    cand = db_manager.get_candidate_by_mobile(mob)
    cand_id = cand["id"]

    try:
        # 1. Enqueue future email
        future_time = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        sched_id1 = enqueue_scheduled_email(
            candidate_id=cand_id,
            recipient_email="sched.test@example.com",
            recipient_name="Scheduler Test Person",
            document_type="offer",
            subject="Future Offer Letter",
            body="This is scheduled for the future.",
            attachment_path=None,
            scheduled_time=future_time
        )
        assert sched_id1 is not None, "Failed to enqueue future email"
        print(f"  ✓ Enqueued future scheduled email (ID {sched_id1}) for {future_time}.")

        # 2. Verify pending queue retrieval
        pending = list_scheduled_emails(status="Scheduled")
        assert any(item["id"] == sched_id1 for item in pending), "Scheduled item not found in pending queue"
        print("  ✓ Pending queue correctly contains scheduled item.")

        # 3. Test cancel schedule
        ok_cancel = cancel_schedule(sched_id1)
        assert ok_cancel is True, "Failed to cancel schedule"
        cancelled_item = [x for x in list_scheduled_emails(status="Cancelled") if x["id"] == sched_id1]
        assert len(cancelled_item) == 1, "Status was not updated to Cancelled"
        print("  ✓ Successfully cancelled future scheduled email.")

        # 4. Enqueue already-due email
        past_time = (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        sched_id2 = enqueue_scheduled_email(
            candidate_id=cand_id,
            recipient_email="sched.test@example.com",
            recipient_name="Scheduler Test Person",
            document_type="offer",
            subject="Past Due Offer Letter",
            body="This is ready to dispatch.",
            attachment_path=None,
            scheduled_time=past_time
        )
        assert sched_id2 is not None

        # Process due scheduled emails (will attempt send and catch/record status)
        result = process_due_scheduled_emails()
        assert result["processed"] >= 1, "Due email was not processed by scheduler"
        print(f"  ✓ Processed due email via scheduler: {result}.")

        # Check item status is updated (either Sent or Failed depending on configured Gmail credentials, but NOT left Scheduled)
        conn = db_manager.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM scheduled_emails WHERE id = ?", (sched_id2,))
        status_after = cur.fetchone()[0]
        conn.close()

        assert status_after in ["Sent", "Failed"], f"Expected status 'Sent' or 'Failed', got: {status_after}"
        print(f"  ✓ Due email queue status transitioned cleanly to '{status_after}'.")

        print("=" * 70)
        print("ALL TASK 6 TESTS PASSED SUCCESSFULLY! ✅")
        print("=" * 70)

    finally:
        db_manager.permanently_delete_candidate(cand_id)


if __name__ == "__main__":
    run_tests()
