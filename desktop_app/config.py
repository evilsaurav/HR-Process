import os

DESKTOP_APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(DESKTOP_APP_DIR)

# Intelligent Directory Resolution:
# Supports both:
# 1. Full workspace repo execution (uses parent database/ and assets/)
# 2. Standalone zipped desktop_app folder execution (uses self-contained desktop_app/data/ and desktop_app/assets/)
parent_db_dir = os.path.join(BASE_DIR, "database")
local_db_dir = os.path.join(DESKTOP_APP_DIR, "data")

if os.path.exists(os.path.join(parent_db_dir, "hrms.db")):
    DATABASE_DIR = parent_db_dir
elif os.path.exists(os.path.join(local_db_dir, "hrms.db")):
    DATABASE_DIR = local_db_dir
else:
    DATABASE_DIR = local_db_dir

DB_PATH = os.path.join(DATABASE_DIR, "hrms.db")
SECRET_KEY_PATH = os.path.join(DATABASE_DIR, "secret.key")
GMAIL_TOKEN_PATH = os.path.join(DATABASE_DIR, "gmail_token.pickle")

local_assets_dir = os.path.join(DESKTOP_APP_DIR, "assets")
parent_assets_dir = os.path.join(BASE_DIR, "assets")
ASSETS_DIR = local_assets_dir if os.path.exists(local_assets_dir) else parent_assets_dir

TEMPLATES_DIR = os.path.join(DESKTOP_APP_DIR, "templates")

os.makedirs(DATABASE_DIR, exist_ok=True)

REQUIRED_CANDIDATE_COLUMNS = [
    "Candidate Name", "Mobile", "Email", "Applied Designation",
    "Negotiated Salary", "Recent Designation", "Highest Education Qualification",
    "Total Years of Experience (Inferred)", "Core Technical Skills",
    "Key Responsibilities", "Contact Location"
]

STATUS_OPTIONS = ["Applied", "Shortlisted", "Interview", "Selected", "Offer Sent", "Joined", "Rejected"]

AI_PROVIDERS = ["Gemini", "Groq", "NVIDIA", "OpenRouter", "Together AI", "Unknown"]

GMAIL_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file"
]

APP_TITLE = "DFY HRMS - Desktop"
PRIMARY_COLOR = "#0B5ED7"
