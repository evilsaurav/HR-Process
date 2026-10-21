import smtplib
import pickle
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from config import GMAIL_TOKEN_PATH, GMAIL_OAUTH_SCOPES


# ---------- VALIDATION HELPERS ----------

def validate_recipient_email(email_address: str) -> tuple[bool, str]:
    """
    Validates recipient email address format.
    Returns (is_valid: bool, plain_message: str).
    Never exposes regex details or technical jargon.
    """
    if not email_address or not str(email_address).strip():
        return False, "Recipient email address is required. Please enter an email address."
    clean_email = str(email_address).strip()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, clean_email) or clean_email.endswith(".") or ".." in clean_email:
        return False, "Please enter a valid recipient email address (for example: candidate@example.com)."
    return True, ""


def validate_attachment_file(attachment_path: str, max_size_mb: int = 25) -> tuple[bool, str]:
    """
    Validates attachment file presence, integrity, and size.
    Returns (is_valid: bool, plain_message: str).
    """
    if not attachment_path:
        return True, ""
    if not os.path.exists(attachment_path):
        return False, "The selected attachment file could not be found. Please check that the file exists and try again."
    try:
        size_bytes = os.path.getsize(attachment_path)
    except Exception as ex:
        print("Attachment access error:", ex)
        return False, "We could not access the attachment file. Please make sure it is not in use by another program and try again."
    if size_bytes == 0:
        return False, "The attachment file appears to be empty (0 bytes). Please check the file and try again."
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        actual_mb = round(size_bytes / (1024 * 1024), 1)
        return False, f"The attachment is too large ({actual_mb} MB). Email services allow a maximum of {max_size_mb} MB. Please use a smaller file."
    return True, ""


# ---------- METHOD 1: App Password (SMTP) ----------

def test_app_password(email_address: str, app_password: str):
    """Returns (success: bool, message: str)"""
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(email_address, app_password)
        server.quit()
        return True, "Email connected successfully! Your account is ready to send messages."
    except Exception as e:
        print("Gmail App Password test connection error:", e)
        return False, "We couldn't connect to this email account. Please check the email address and password (or app password), then try again."


def send_mail_app_password(email_address, app_password, to_addr, subject, body, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = email_address
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path:
        part = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
        msg.attach(part)

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
    server.login(email_address, app_password)
    server.sendmail(email_address, to_addr, msg.as_string())
    server.quit()


# ---------- METHOD 2: OAuth2 (Gmail Send + Google Drive Backup) ----------

def get_oauth_credentials(credentials_json_path: str):
    """Loads or creates OAuth2 credentials. Scopes include Gmail send + Drive file access (for DB backup)."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        try:
            with open(GMAIL_TOKEN_PATH, "rb") as f:
                creds = pickle.load(f)
        except Exception as ex:
            print("Error loading stored token:", ex)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(GMAIL_TOKEN_PATH, "wb") as f:
                    pickle.dump(creds, f)
            except Exception as ex:
                print("OAuth2 token refresh failed:", ex)
                return None
        else:
            if not credentials_json_path or not os.path.exists(credentials_json_path):
                print("OAuth credentials file does not exist:", credentials_json_path)
                return None
            flow = InstalledAppFlow.from_client_secrets_file(credentials_json_path, GMAIL_OAUTH_SCOPES)
            creds = flow.run_local_server(port=0)
            with open(GMAIL_TOKEN_PATH, "wb") as f:
                pickle.dump(creds, f)

    return creds


def test_oauth(credentials_json_path: str):
    """Returns (success: bool, message: str). Authorizes Gmail send + Drive backup scopes together."""
    try:
        creds = get_oauth_credentials(credentials_json_path)
        if creds and creds.valid:
            return True, "Email and Google Drive connected successfully! Your account is ready."
        return False, "Your email authorization has expired or is no longer valid. Please go to Settings and reconnect your email account, then try again."
    except Exception as e:
        print("Gmail OAuth test connection error:", e)
        return False, "We couldn't connect to this email account. Please check the email address and authorization, then try again."


def send_mail_oauth(credentials_json_path: str, to_addr: str, subject: str, body: str, attachment_path: str = None):
    """Sends an email using the Gmail REST API with OAuth2 credentials."""
    import base64
    from googleapiclient.discovery import build

    creds = get_oauth_credentials(credentials_json_path)
    if not creds or not creds.valid:
        raise RuntimeError("Your email authorization has expired or is no longer valid. Please go to Settings and reconnect your email account, then try again.")

    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart()
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path:
        part = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
        msg.attach(part)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw_message}).execute()


def backup_database_to_drive(credentials_json_path: str, file_path: str, drive_folder_name: str = "DFY_HRMS_Backups"):
    """Uploads given file (e.g. hrms.db) to Google Drive using existing OAuth2 token."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import datetime

        creds = get_oauth_credentials(credentials_json_path)
        if not creds or not creds.valid:
            return False, "Your email authorization has expired or is no longer valid. Please go to Settings and reconnect your email account, then try again."

        service = build("drive", "v3", credentials=creds)

        # Find or create backup folder
        query = f"name='{drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get("files", [])

        if folders:
            folder_id = folders[0]["id"]
        else:
            folder_metadata = {
                "name": drive_folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder["id"]

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"hrms_backup_{timestamp}.db"

        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        return True, f"Backup uploaded successfully: {file_name} (File ID: {uploaded_file.get('id')})"
    except Exception as e:
        print("Google Drive backup error:", e)
        return False, "We couldn't back up the database to Google Drive. Please check your credentials and connection, then try again."


# ---------- HIGH-LEVEL DOCUMENT EMAIL DISPATCH ----------

def send_document_email(
    to_addr: str,
    subject: str,
    body: str,
    attachment_path: str = None,
    candidate_id: int = None,
    document_type: str = None,
    recipient_name: str = None,
    sent_by: str = "HR Desktop"
) -> tuple[bool, str, bool]:
    """
    High-level dispatch function with validation, credential lookup,
    transient failure detection, and audit logging into email_log.
    Returns: (success: bool, message: str, is_transient: bool)
    """
    from database import db_manager

    # 1. Validate recipient email
    val_ok, val_err = validate_recipient_email(to_addr)
    if not val_ok:
        return False, val_err, False

    # 2. Validate attachment
    val_att_ok, val_att_err = validate_attachment_file(attachment_path)
    if not val_att_ok:
        return False, val_att_err, False

    # 3. Retrieve configured Gmail credentials
    gmail_settings = {k["key_id"]: k["api_key"] for k in db_manager.get_all_api_keys() if k["provider"] == "Gmail"}
    method = gmail_settings.get("gmail_method", "app_password")
    att_name = os.path.basename(attachment_path) if attachment_path else None

    try:
        if method == "app_password":
            email_addr = gmail_settings.get("gmail_email")
            app_pass = gmail_settings.get("gmail_app_password")
            if not email_addr or not app_pass:
                msg = "Email sending is not configured. Please enter your Gmail address and App Password in Settings first."
                db_manager.log_email_dispatch(
                    recipient_email=to_addr, recipient_name=recipient_name,
                    document_type=document_type, subject=subject, attachment_filename=att_name,
                    attachment_path=attachment_path, sent_by=sent_by, status="Failed",
                    error_message=msg, candidate_id=candidate_id
                )
                return False, msg, False
            send_mail_app_password(email_addr, app_pass, to_addr, subject, body, attachment_path)

        elif method == "oauth":
            creds_path = gmail_settings.get("gmail_credentials_path")
            if not creds_path:
                msg = "OAuth2 credentials file is not configured. Please set it up in the Settings page first."
                db_manager.log_email_dispatch(
                    recipient_email=to_addr, recipient_name=recipient_name,
                    document_type=document_type, subject=subject, attachment_filename=att_name,
                    attachment_path=attachment_path, sent_by=sent_by, status="Failed",
                    error_message=msg, candidate_id=candidate_id
                )
                return False, msg, False
            send_mail_oauth(creds_path, to_addr, subject, body, attachment_path)

        else:
            msg = "Unknown email method configured in Settings. Please review your email settings."
            db_manager.log_email_dispatch(
                recipient_email=to_addr, recipient_name=recipient_name,
                document_type=document_type, subject=subject, attachment_filename=att_name,
                attachment_path=attachment_path, sent_by=sent_by, status="Failed",
                error_message=msg, candidate_id=candidate_id
            )
            return False, msg, False

        # Success
        success_msg = f"Email sent successfully to {to_addr}!"
        db_manager.log_email_dispatch(
            recipient_email=to_addr, recipient_name=recipient_name,
            document_type=document_type, subject=subject, attachment_filename=att_name,
            attachment_path=attachment_path, sent_by=sent_by, status="Success",
            error_message=None, candidate_id=candidate_id
        )
        return True, success_msg, False

    except Exception as ex:
        print("Email dispatch error:", ex)
        err_str = str(ex).lower()

        # Check for expired OAuth2 token
        if "expired" in err_str or "invalid_grant" in err_str or "reconnect" in err_str:
            user_msg = "Your email authorization has expired or is no longer valid. Please go to Settings and reconnect your email account, then try again."
            db_manager.log_email_dispatch(
                recipient_email=to_addr, recipient_name=recipient_name,
                document_type=document_type, subject=subject, attachment_filename=att_name,
                attachment_path=attachment_path, sent_by=sent_by, status="Failed",
                error_message=user_msg, candidate_id=candidate_id
            )
            return False, user_msg, False

        # Check for transient network issues
        is_transient = isinstance(ex, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError, ConnectionError, OSError)) or any(
            term in err_str for term in ["timeout", "connection refused", "temporarily unavailable", "network", "reset by peer", "disconnected"]
        )

        if is_transient:
            user_msg = "We couldn't send the email because the connection to Gmail was interrupted. Please check your internet connection and try again."
        else:
            user_msg = "We couldn't send the email. Please check your email credentials and recipient details in Settings, then try again."

        db_manager.log_email_dispatch(
            recipient_email=to_addr, recipient_name=recipient_name,
            document_type=document_type, subject=subject, attachment_filename=att_name,
            attachment_path=attachment_path, sent_by=sent_by, status="Failed",
            error_message=user_msg, candidate_id=candidate_id
        )
        return False, user_msg, is_transient
