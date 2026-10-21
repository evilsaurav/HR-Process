"""
Service: email_scheduler_service.py
Purpose: Background and on-demand dispatcher for scheduled emails.
Monitors the scheduled_emails queue, dispatches due emails, logs to email_log,
and updates queue statuses.
"""

import datetime
from typing import Dict, Any, List

from database import db_manager
from services import email_service


def enqueue_scheduled_email(
    candidate_id: int,
    recipient_email: str,
    recipient_name: str,
    document_type: str,
    subject: str,
    body: str,
    attachment_path: str,
    scheduled_time: str
) -> int | None:
    """
    Enqueues an email to be sent at scheduled_time (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM).
    """
    return db_manager.schedule_email(
        candidate_id=candidate_id,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        document_type=document_type,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
        scheduled_time=scheduled_time
    )


def process_due_scheduled_emails() -> Dict[str, int]:
    """
    Checks all pending scheduled emails whose scheduled_time is <= now.
    Dispatches them using email_service.send_document_email and updates their status.
    Returns: {"processed": int, "sent": int, "failed": int}
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending = db_manager.get_scheduled_emails(status="Scheduled")

    sent_count = 0
    failed_count = 0
    processed_count = 0

    for item in pending:
        sched_time = str(item.get("scheduled_time") or "").strip()
        # Normalization if only date and hour:minute without seconds
        if len(sched_time) == 16:
            sched_time += ":00"

        if sched_time <= now_str:
            processed_count += 1
            sched_id = item["id"]
            cand_id = item.get("candidate_id")
            to_addr = item.get("recipient_email")
            recip_name = item.get("recipient_name")
            doc_type = item.get("document_type")
            subject = item.get("subject")
            body = item.get("body")
            attachment_path = item.get("attachment_path")

            success, message, is_transient = email_service.send_document_email(
                to_addr=to_addr,
                subject=subject,
                body=body,
                attachment_path=attachment_path,
                candidate_id=cand_id,
                document_type=doc_type,
                recipient_name=recip_name,
                sent_by="Email Scheduler"
            )

            if success:
                db_manager.update_scheduled_email_status(sched_id, "Sent")
                sent_count += 1
            else:
                db_manager.update_scheduled_email_status(sched_id, "Failed", error_message=message)
                failed_count += 1

    return {
        "processed": processed_count,
        "sent": sent_count,
        "failed": failed_count,
    }


def list_scheduled_emails(status: str = "All") -> List[Dict[str, Any]]:
    """Returns scheduled emails for UI display."""
    return db_manager.get_scheduled_emails(status=status)


def cancel_schedule(schedule_id: int) -> bool:
    """Cancels a scheduled email."""
    return db_manager.cancel_scheduled_email(schedule_id)
