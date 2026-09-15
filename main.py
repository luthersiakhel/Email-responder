#!/usr/bin/env python3
"""
Email Autoresponder — reads incoming emails from Gmail, classifies them using Claude,
and creates draft replies for approval.
"""
import argparse
import time
import sys

import os

import config
from gmail_client import (
    get_gmail_service,
    fetch_unprocessed_emails,
    create_draft,
    mark_as_processed,
)
from classifier import classify_and_draft


def process_emails(service, dry_run: bool = False):
    print(f"\nChecking for new emails...")
    emails = fetch_unprocessed_emails(service, max_results=config.MAX_EMAILS_PER_RUN)

    if not emails:
        print("No new emails.")
        return 0

    print(f"Found {len(emails)} new email(s).\n")
    drafted = 0

    for email in emails:
        print(f"--- Email from: {email['from']}")
        print(f"    Subject: {email['subject']}")

        from_lower = email["from"].lower()
        subject_lower = email["subject"].lower()
        skip_senders = ["noreply", "no-reply", "mailer-daemon", "postmaster", "dhl", "notification"]
        skip_subjects = ["sn sla", "catalog task", "shipment processed", "group assignment notification",
                         "customer update notification", "approval notification", "your dhl"]
        if any(s in from_lower for s in skip_senders) or any(s in subject_lower for s in skip_subjects):
            print(f"    -> Skipped (automated notification)")
            mark_as_processed(service, email["id"])
            continue

        result = classify_and_draft(email)

        if result is None:
            print(f"    -> No KB match, skipping (needs manual reply)")
            continue

        print(f"    -> Category: {result['category']} (confidence: {result['confidence']:.0%})")
        print(f"    -> Region: {result.get('region', 'unknown')}")
        print(f"    -> Matched: {result.get('matched_response_title', 'N/A')}")
        print(f"    -> Reason: {result['reason']}")
        if result.get("requires_action"):
            print(f"    -> [!] REQUIRES MANUAL ACTION before sending")

        attachments = []
        is_external = "@redhat.com" not in email["from"].lower()
        if result.get("attach_expense_form") and is_external:
            expense_form = os.path.join(os.path.dirname(__file__), "Expense Claim Form.pdf")
            if os.path.exists(expense_form):
                attachments.append(expense_form)
                print(f"    -> Attaching Expense Claim Form.pdf (external sender)")
            else:
                print(f"    -> [!] Expense Claim Form.pdf not found in project folder")

        if dry_run:
            print(f"    -> [DRY RUN] Draft would be created:")
            print(f"       {result['draft_reply'][:150]}...")
        else:
            reply_subject = email["subject"]
            if not reply_subject.lower().startswith("re:"):
                reply_subject = f"Re: {reply_subject}"

            create_draft(
                service,
                to=email["from"],
                subject=reply_subject,
                body=result["draft_reply"],
                thread_id=email["thread_id"],
                attachments=attachments or None,
            )
            mark_as_processed(service, email["id"])
            print(f"    -> Draft created in Gmail!")
            drafted += 1

        print()

    return drafted


def run_once(dry_run: bool = False):
    service = get_gmail_service()
    drafted = process_emails(service, dry_run=dry_run)
    print(f"\nDone. Created {drafted} draft(s).")


def run_watch(interval: int):
    service = get_gmail_service()
    print(f"Watch mode — checking every {interval}s. Ctrl+C to stop.\n")
    try:
        while True:
            process_emails(service)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Email Autoresponder with Claude AI")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without creating drafts",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously, checking for new emails",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=config.CHECK_INTERVAL_SECONDS,
        help=f"Check interval in seconds (default: {config.CHECK_INTERVAL_SECONDS})",
    )
    args = parser.parse_args()

    if args.watch:
        run_watch(args.interval)
    else:
        run_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
