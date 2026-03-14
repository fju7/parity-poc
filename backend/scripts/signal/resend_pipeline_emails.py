"""
One-time script to re-send missed Signal pipeline emails.
Run from backend/ directory:
  export $(grep -v "^#" .env | xargs) && python3 scripts/signal/resend_pipeline_emails.py
"""
import os, sys
from pathlib import Path
try:
    from dotenv import load_dotenv
    env = Path(__file__).parent.parent.parent / ".env"
    if env.exists(): load_dotenv(env)
except ImportError: pass
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
TOPIC_TITLE  = "Diet and Breast Cancer Risk: Prevention and Recurrence"
TOPIC_SLUG   = "diet-and-breast-cancer-risk-prevention-and-recurrence"
REQUESTER_ID = "4c62234e-86cc-4b8d-a782-c54fe1d11eb0"
SIGNAL_URL   = "https://signal.civicscale.ai"
DEEP_LINK    = f"{SIGNAL_URL}/{TOPIC_SLUG}"
ADMIN_EMAIL  = "fred@civicscale.ai"
def send_email(to, subject, html):
    import resend
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend.api_key: print(f"  ERROR: RESEND_API_KEY not set"); return False
    resend.Emails.send({"from":"Parity Signal <notifications@civicscale.ai>","to":[to],"subject":subject,"html":html})
    print(f"  Sent: {subject} -> {to}"); return True
def get_requester_email():
    from supabase_client import supabase as sb
    try:
        resp = sb.auth.admin.get_user_by_id(REQUESTER_ID)
        user = getattr(resp, "user", None)
        return getattr(user, "email", None) if user else None
    except Exception as e: print(f"  Could not fetch requester email: {e}"); return None
if __name__ == "__main__":
    print(f"Re-sending missed emails for: {TOPIC_TITLE}")
    email = get_requester_email()
    if email:
        send_email(email, f"Your Topic is Ready: {TOPIC_TITLE}",
    else: print("  Could not find requester email")
    send_email(ADMIN_EMAIL, f"Pipeline Complete: {TOPIC_TITLE}",
        f"<h2>Pipeline Complete</h2><p>{TOPIC_TITLE} - pipeline ran successfully. Email was delayed due to missing RESEND_API_KEY during local run.</p><p><a href='{DEEP_LINK}'>View Dashboard</a></p>")
    print("Done.")
