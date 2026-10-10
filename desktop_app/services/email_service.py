import smtplib
import pickle
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from config import GMAIL_TOKEN_PATH, GMAIL_OAUTH_SCOPES


# ---------- METHOD 1: App Password (SMTP) ----------

def test_app_password(email_address: str, app_password: str):
    """Returns (success: bool, message: str)"""
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(email_address, app_password)
        server.quit()
        return True, "Gmail (App Password) connected successfully"
    except Exception as e:
        return False, str(e)


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

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
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
        with open(GMAIL_TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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
            return True, "Gmail + Drive (OAuth2) connected & authorized successfully"
        return False, "OAuth2 authorization failed"
    except Exception as e:
        return False, str(e)


def backup_database_to_drive(credentials_json_path: str, file_path: str, drive_folder_name: str = "DFY_HRMS_Backups"):
    """Uploads given file (e.g. hrms.db) to Google Drive using existing OAuth2 token."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import datetime

        creds = get_oauth_credentials(credentials_json_path)
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
        return False, str(e)
