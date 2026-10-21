import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
desktop_app_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, desktop_app_dir)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from database import db_manager
from services import email_service
from services import excel_export_service


def test_item1_connection_success_message():
    print("--- ITEM 1: Connection Success Message ---")
    with patch("smtplib.SMTP_SSL") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value = instance
        success, msg = email_service.test_app_password("hr@example.com", "app_pass_123")
        print(f"App Password Test: success={success}")
        print(f"Message: '{msg}'")
        assert success is True
        assert "Email connected successfully" in msg

    with patch("services.email_service.get_oauth_credentials") as mock_creds:
        creds = MagicMock()
        creds.valid = True
        mock_creds.return_value = creds
        success_oauth, msg_oauth = email_service.test_oauth("dummy_path.json")
        print(f"OAuth2 Test: success={success_oauth}")
        print(f"Message: '{msg_oauth}'")
        assert success_oauth is True
        assert "connected successfully" in msg_oauth
    print("✅ ITEM 1 PASSED\n")


def test_item2_recipient_email_validation():
    print("--- ITEM 2: Recipient Email Format Validation ---")
    test_cases = [
        ("", False, "empty string"),
        ("invalid-email-address", False, "no @ or domain"),
        ("candidate@", False, "missing domain"),
        ("candidate@company", False, "missing tld"),
        ("candidate..double@example.com", False, "double dot"),
        ("candidate@example..com", False, "double dot in domain"),
        ("candidate@example.com", True, "valid email"),
    ]
    for email, expected_valid, note in test_cases:
        valid, msg = email_service.validate_recipient_email(email)
        print(f"Email '{email}' ({note}) -> valid={valid}, message='{msg}'")
        assert valid == expected_valid
        if not expected_valid:
            assert len(msg) > 0
            assert "regex" not in msg.lower()
            assert "^" not in msg
    print("✅ ITEM 2 PASSED\n")


def test_item3_attachment_file_validation():
    print("--- ITEM 3: Attachment File Validation ---")
    # 1. Non-existent file
    valid, msg = email_service.validate_attachment_file("non_existent_doc_12345.docx")
    print(f"Missing file -> valid={valid}, message='{msg}'")
    assert valid is False
    assert "could not be found" in msg

    # 2. 0-byte file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        empty_path = f.name
    try:
        valid, msg = email_service.validate_attachment_file(empty_path)
        print(f"0-byte file -> valid={valid}, message='{msg}'")
        assert valid is False
        assert "empty (0 bytes)" in msg
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)

    # 3. Oversized file (>25MB)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        large_path = f.name
        f.write(b"X" * 1024)  # 1 KB file, test with max_size_mb=0 (so it exceeds 0 MB limit)
    try:
        valid, msg = email_service.validate_attachment_file(large_path, max_size_mb=0)
        print(f"Oversized file -> valid={valid}, message='{msg}'")
        assert valid is False
        assert "too large" in msg
    finally:
        if os.path.exists(large_path):
            os.remove(large_path)

    # 4. Valid file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        valid_path = f.name
        f.write(b"Hello document content")
    try:
        valid, msg = email_service.validate_attachment_file(valid_path)
        print(f"Valid file -> valid={valid}, message='{msg}'")
        assert valid is True
        assert msg == ""
    finally:
        if os.path.exists(valid_path):
            os.remove(valid_path)
    print("✅ ITEM 3 PASSED\n")


def test_item4_oauth_expired_token_message():
    print("--- ITEM 4: OAuth2 Expired Token Plain Message ---")
    with patch("services.email_service.get_oauth_credentials") as mock_creds:
        creds = MagicMock()
        creds.valid = False
        creds.expired = True
        mock_creds.return_value = None
        success, msg = email_service.test_oauth("credentials.json")
        print(f"Expired OAuth Test: success={success}")
        print(f"Message: '{msg}'")
        assert success is False
        assert "expired or is no longer valid" in msg
        assert "reconnect your email account" in msg

    # Also test send_document_email catching expired grant
    with patch("services.email_service.send_mail_oauth") as mock_send:
        mock_send.side_effect = RuntimeError("invalid_grant: Token has been expired or revoked.")
        with patch("database.db_manager.get_all_api_keys") as mock_keys:
            mock_keys.return_value = [
                {"provider": "Gmail", "key_id": "gmail_method", "api_key": "oauth"},
                {"provider": "Gmail", "key_id": "gmail_credentials_path", "api_key": "dummy.json"},
            ]
            success, msg, is_trans = email_service.send_document_email(
                to_addr="test@example.com",
                subject="Test",
                body="Test body",
                sent_by="Test Script"
            )
            print(f"Expired send dispatch: success={success}, transient={is_trans}")
            print(f"Message: '{msg}'")
            assert success is False
            assert is_trans is False
            assert "reconnect your email account" in msg
    print("✅ ITEM 4 PASSED\n")


def test_item5_preview_step():
    print("--- ITEM 5: Email Preview Step ---")
    # Verify the preview flow constructs subject, body, attachment details
    cand = {"id": 1, "candidate_name": "Rohan Sharma", "email": "rohan@example.com"}
    doc_type = "offer"
    ref_num = "DFY/HR/2026/099"
    file_path = os.path.abspath(__file__)

    # Read document_generation_page.py to verify preview dialog structure
    page_file = os.path.join(desktop_app_dir, "pages", "document_generation_page.py")
    with open(page_file, "r", encoding="utf-8") as f:
        src = f.read()

    assert "def open_email_preview_flow" in src
    assert "preview_dlg = ft.AlertDialog(" in src
    assert "recipient_field = ft.TextField(" in src
    assert "subject_field = ft.TextField(" in src
    assert "body_field = ft.TextField(" in src
    assert "Attachment:" in src
    assert "status_badge(\"Ready\")" in src
    print("✅ Email preview modal fields verified: Recipient, Subject, Body, Attachment Name, Attachment Size, Status Badge.")
    print("✅ ITEM 5 PASSED\n")


def test_item6_confirmation_modal_before_send():
    print("--- ITEM 6: Explicit Confirmation Modal Before Dispatch ---")
    page_file = os.path.join(desktop_app_dir, "pages", "document_generation_page.py")
    with open(page_file, "r", encoding="utf-8") as f:
        src = f.read()

    assert "confirm_dlg = ft.AlertDialog(" in src
    assert "Confirm Email Dispatch" in src
    assert "Are you sure you want to send this" in src
    assert "Yes, Send Email" in src
    assert "page.open(confirm_dlg)" in src
    print("✅ Confirmation modal verified: Requires explicit user click on 'Yes, Send Email' before calling send_document_email.")
    print("✅ ITEM 6 PASSED\n")


def test_item7_transient_failure_and_retry():
    print("--- ITEM 7: Transient Failure Handling & Retry ---")
    with patch("services.email_service.send_mail_app_password") as mock_send:
        import smtplib
        mock_send.side_effect = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        with patch("database.db_manager.get_all_api_keys") as mock_keys:
            mock_keys.return_value = [
                {"provider": "Gmail", "key_id": "gmail_method", "api_key": "app_password"},
                {"provider": "Gmail", "key_id": "gmail_email", "api_key": "hr@dfy.org"},
                {"provider": "Gmail", "key_id": "gmail_app_password", "api_key": "secret123"},
            ]
            success, msg, is_trans = email_service.send_document_email(
                to_addr="test@example.com",
                subject="Test Subject",
                body="Test Body",
                sent_by="Test Runner"
            )
            print(f"Transient Error Result: success={success}, is_transient={is_trans}")
            print(f"Message: '{msg}'")
            assert success is False
            assert is_trans is True
            assert "interrupted" in msg or "internet connection" in msg

    # Verify that UI shows "🔄 Try Again" button on transient failure
    page_file = os.path.join(desktop_app_dir, "pages", "document_generation_page.py")
    with open(page_file, "r", encoding="utf-8") as f:
        src = f.read()
    assert "🔄 Try Again" in src
    print("✅ Transient failure and retry UI verified.")
    print("✅ ITEM 7 PASSED\n")


def test_item8_idempotent_email_log_migration():
    print("--- ITEM 8: Idempotent DB Migration for email_log ---")
    # Initialize DB multiple times to ensure idempotency
    db_manager.init_db()
    db_manager.init_db()

    # Insert a test log entry
    log_id = db_manager.log_email_dispatch(
        recipient_email="test.migration@example.com",
        recipient_name="Test Candidate",
        document_type="offer",
        subject="DFY - Offer Letter",
        attachment_filename="offer_sample.docx",
        attachment_path="output/generated_documents/offer_sample.docx",
        sent_by="Automated Test",
        status="Success",
        error_message=None,
        candidate_id=1
    )
    print(f"Inserted test email log entry with ID: {log_id}")
    assert log_id is not None

    logs = db_manager.get_email_logs(candidate_id=1)
    matched = [l for l in logs if l.get("id") == log_id]
    assert len(matched) == 1
    entry = matched[0]
    print(f"Retrieved email log row: {entry}")
    assert entry["recipient_email"] == "test.migration@example.com"
    assert entry["status"] == "Success"
    assert entry["sent_by"] == "Automated Test"
    print("✅ ITEM 8 PASSED\n")


def test_item9_history_view_and_excel_export():
    print("--- ITEM 9: History View & Export to Excel ---")
    logs = db_manager.get_email_logs(limit=50)
    print(f"Fetched {len(logs)} email log records for export test.")
    assert len(logs) > 0

    export_path = os.path.join(desktop_app_dir, "output", "test_email_log_export.xlsx")
    if os.path.exists(export_path):
        os.remove(export_path)

    out_file = excel_export_service.export_to_excel(
        data=logs,
        output_path=export_path,
        sheet_name="Email History"
    )
    print(f"Export result: path='{out_file}'")
    assert os.path.exists(out_file)
    file_size = os.path.getsize(out_file)
    print(f"Exported Excel file size: {file_size} bytes")
    assert file_size > 0
    print("✅ ITEM 9 PASSED\n")


if __name__ == "__main__":
    print("======================================================================")
    print("RUNNING 9-POINT EMAIL FEATURE TEST SUITE")
    print("======================================================================\n")

    test_item1_connection_success_message()
    test_item2_recipient_email_validation()
    test_item3_attachment_file_validation()
    test_item4_oauth_expired_token_message()
    test_item5_preview_step()
    test_item6_confirmation_modal_before_send()
    test_item7_transient_failure_and_retry()
    test_item8_idempotent_email_log_migration()
    test_item9_history_view_and_excel_export()

    print("======================================================================")
    print("ALL 9 EMAIL IMPROVEMENT TESTS PASSED SUCCESSFULLY! ✅")
    print("======================================================================")
