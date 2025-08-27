import os
from dotenv import load_dotenv
load_dotenv()

APP_TITLE = "WorkInFlow (Gmail + Personal KB)"
APP_VERSION = "1.0"

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in your environment (or .env).")
GEN_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
EMBED_MODEL = os.getenv("GEMBED_MODEL", "models/text-embedding-004")

# Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# Chroma
CHROMA_PERSIST = os.getenv("CHROMA_PERSIST", "false").lower() == "true"
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma")
KB_COLLECTION = os.getenv("KB_COLLECTION", "knowledge_base")

# CORS
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

# --- Project Management providers (Jira) ---
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")  # e.g., https://your-domain.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
