import json
import subprocess

import config


def load_knowledge_base() -> str:
    with open(config.KNOWLEDGE_BASE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def classify_and_draft(email: dict) -> dict | None:
    kb = load_knowledge_base()

    prompt = f"""You are an assistant for the Red Hat Endpoint Systems / Laptop Returns team.
Your job is to classify incoming emails and select the best matching canned response.

You will be given a knowledge base document organized by REGION, then by TOPIC, each with:
- Keywords: hints for matching
- Answer: the canned response to use

Instructions:
- Match the incoming email to the BEST canned response from the knowledge base.
- Consider the person's region (look for clues in their email, signature, or address).
- Consider whether they still have Red Hat system access or are a former employee (leaver).
  Key signal: if the sender's email domain is @redhat.com, they likely still have access.
  If it's a personal email (gmail, outlook, etc.), they are likely a former employee.
- If the email clearly matches a canned response, use it as the draft reply.
- Personalize the response: if the sender's name is visible, add it after "Hello" (e.g. "Hello John,").
- If the response contains placeholders like (XXXX) or {{{{Associate Name}}}}, leave them as-is
  and set requires_action to true so the team knows to fill them in before sending.
- If the email does NOT match any canned response perfectly, still pick the closest one
  and set requires_action to true. ALWAYS produce a draft_reply — never return null for it.
- IMPORTANT: All URLs must be hidden inside markdown links. Never show a raw URL in the reply.
  Use the exact markdown link format from the knowledge base, e.g. [this form](https://...)
  or [Source page](https://...). The recipient should see clickable text, never a bare URL.
- If the sender mentions they don't have a box, packaging, or something to ship the laptop in,
  include the reimbursement info from the KB in the reply AND set "attach_expense_form" to true.

Respond ONLY as a valid JSON object, no other text:
{{
  "category": "short description of the matched category (string or null)",
  "region": "detected region (EU/CZ/UK/Canada/Israel/UAE/India/Switzerland/All regions/unknown)",
  "confidence": 0.0-1.0,
  "requires_action": true/false,
  "attach_expense_form": true/false,
  "matched_response_title": "the exact heading of the matched canned response (e.g. 'EU > Laptop Returns > Leaver still has access')",
  "draft_reply": "the response text to send (string or null)",
  "reason": "brief explanation of why this match was chosen"
}}

=== KNOWLEDGE BASE ===
{kb}

=== INCOMING EMAIL ===
From: {email['from']}
To: {email['to']}
Subject: {email['subject']}
Date: {email['date']}

{email['body'][:4000]}
=== END OF EMAIL ===

Classify this email and select the best matching canned response. Return ONLY valid JSON."""

    result_proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result_proc.returncode != 0:
        print(f"  [!] Claude CLI error: {result_proc.stderr[:200]}")
        return None

    text = result_proc.stdout.strip()

    try:
        wrapper = json.loads(text)
        if isinstance(wrapper, dict) and "result" in wrapper:
            text = wrapper["result"]
    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print(f"  [!] Claude returned invalid JSON: {text[:200]}")
        return None

    if not result.get("draft_reply"):
        return None

    return result
