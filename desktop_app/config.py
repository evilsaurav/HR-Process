import os

DESKTOP_APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(DESKTOP_APP_DIR)

DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DATABASE_DIR, "hrms.db")
SECRET_KEY_PATH = os.path.join(DATABASE_DIR, "secret.key")
GMAIL_TOKEN_PATH = os.path.join(DATABASE_DIR, "gmail_token.pickle")

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(DATABASE_DIR, exist_ok=True)

REQUIRED_CANDIDATE_COLUMNS = [
    "Candidate Name", "Mobile", "Email", "Applied Designation",
    "Negotiated Salary", "Recent Designation", "Highest Education Qualification",
    "Total Years of Experience (Inferred)", "Core Technical Skills",
    "Key Responsibilities", "Contact Location"
]

STATUS_OPTIONS = ["Applied", "Shortlisted", "Interview", "Offer Sent", "Joined", "Rejected"]

AI_PROVIDERS = ["Gemini", "Groq", "NVIDIA", "OpenRouter", "Together AI", "Unknown"]

GMAIL_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file"
]

APP_TITLE = "DFY HRMS - Desktop"
PRIMARY_COLOR = "#0B5ED7"
