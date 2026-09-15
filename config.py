import os

GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

KNOWLEDGE_BASE_FILE = "Claude_KB.md"

LABEL_INBOX = "LAPTOP returns"
LABEL_PROCESSED = "AutoResponder/Processed"
CHECK_INTERVAL_SECONDS = 60
MAX_EMAILS_PER_RUN = 10
