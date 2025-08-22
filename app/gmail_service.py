import os
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app import config

def get_gmail_creds() -> Credentials:
    creds = None
    if os.path.exists(config.GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN_FILE, config.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.GOOGLE_CREDENTIALS_FILE):
                raise RuntimeError("Missing Google OAuth client file 'credentials.json' (or set GOOGLE_CREDENTIALS_FILE).")
            flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.GOOGLE_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def gmail_service():
    return build("gmail", "v1", credentials=get_gmail_creds(), cache_discovery=False)

def list_recent_messages(max_results: int = 5) -> List[Dict[str, Any]]:
    svc = gmail_service()
    res = svc.users().messages().list(userId="me", maxResults=max_results).execute()
    return res.get("messages", [])

def get_message(msg_id: str) -> Dict[str, Any]:
    svc = gmail_service()
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
