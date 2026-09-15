import base64
import mimetypes
import os
import re
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config


def get_gmail_service():
    creds = None
    if os.path.exists(config.GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            config.GMAIL_TOKEN_FILE, config.GMAIL_SCOPES
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(config.GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_or_create_label(service, label_name: str) -> str:
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"].lower() == label_name.lower():
            return label["id"]
    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    created = service.users().labels().create(userId="me", body=label_body).execute()
    return created["id"]


def fetch_unprocessed_emails(service, max_results: int = 10) -> list[dict]:
    inbox_label_id = get_or_create_label(service, config.LABEL_INBOX)
    processed_label_id = get_or_create_label(service, config.LABEL_PROCESSED)

    results = (
        service.users()
        .threads()
        .list(userId="me", labelIds=[inbox_label_id], maxResults=max_results * 2)
        .execute()
    )
    threads = results.get("threads", [])

    emails = []
    for thread_meta in threads:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_meta["id"], format="full")
            .execute()
        )
        messages = thread.get("messages", [])
        if not messages:
            continue

        last_msg = messages[-1]
        headers = {h["name"]: h["value"] for h in last_msg["payload"]["headers"]}

        if "laptop-return@redhat.com" in headers.get("From", "").lower():
            continue

        if processed_label_id in last_msg.get("labelIds", []):
            continue

        body = _extract_body(last_msg["payload"])
        emails.append(
            {
                "id": last_msg["id"],
                "thread_id": thread_meta["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "body": body,
                "date": headers.get("Date", ""),
            }
        )
        if len(emails) >= max_results:
            break

    return emails


def _extract_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    for part in parts:
        body = _extract_body(part)
        if body:
            return body
    return ""


def is_already_replied(service, thread_id: str) -> bool:
    thread = service.users().threads().get(userId="me", id=thread_id, format="metadata", metadataHeaders=["From"]).execute()
    messages = thread.get("messages", [])
    if not messages:
        return False
    last_msg = messages[-1]
    headers = {h["name"]: h["value"] for h in last_msg["payload"]["headers"]}
    return "laptop-return@redhat.com" in headers.get("From", "")


def _markdown_links_to_html(text: str) -> str:
    html = re.sub(r'\[([^\]]+)\]\s*\((\S+?)\)', r'<a href="\2">\1</a>', text)
    html = html.replace("\n", "<br>\n")
    return html


def create_draft(service, to: str, subject: str, body: str, thread_id: str, attachments: list[str] | None = None) -> dict:
    html_body = _markdown_links_to_html(body)

    if attachments:
        message = MIMEMultipart()
        message.attach(MIMEText(html_body, "html"))
        for filepath in attachments:
            if not os.path.exists(filepath):
                print(f"  [!] Attachment not found: {filepath}")
                continue
            mime_type, _ = mimetypes.guess_type(filepath)
            main_type, sub_type = (mime_type or "application/octet-stream").split("/", 1)
            with open(filepath, "rb") as f:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(filepath))
            message.attach(attachment)
    else:
        message = MIMEText(html_body, "html")

    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft_body = {"message": {"raw": raw, "threadId": thread_id}}
    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return draft


def mark_as_processed(service, message_id: str):
    label_id = get_or_create_label(service, config.LABEL_PROCESSED)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]},
    ).execute()
