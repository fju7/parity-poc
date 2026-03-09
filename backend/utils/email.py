"""Shared email helper using Resend."""

import os


def send_email(to: str, subject: str, html: str):
    """Send an email via Resend. Fails silently with a log message."""
    try:
        import resend

        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print(f"[Email] RESEND_API_KEY not set, skipping send to {to}")
            return
        resend.api_key = resend_key

        resend.Emails.send({
            "from": "Parity Employer <notifications@civicscale.ai>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        print(f"[Email] Sent '{subject}' to {to}")
    except Exception as e:
        print(f"[Email] Failed to send to {to}: {e}")
