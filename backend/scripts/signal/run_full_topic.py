"""
Parity Signal: End-to-end pipeline for a new topic request.

Called as a subprocess from FastAPI when an admin clicks "Start Processing".
Runs source discovery, registers the topic, runs the 7-step pipeline,
updates the request record, and sends notifications.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/run_full_topic.py \\
        --slug ozempic-kidney \\
        --title "Ozempic & Kidney Disease" \\
        --description "Evidence on semaglutide for chronic kidney disease" \\
        --request-id "uuid-here" \\
        --requester-id "uuid-here"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPTS_DIR.parent.parent

# Add backend/ to sys.path (for supabase_client, routers, etc.)
# Add scripts/signal/ to sys.path (for topic_config)
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

# Load .env file automatically when running locally.
# On Render, env vars are injected by the platform so this is a no-op.
try:
    from dotenv import load_dotenv
    _env_path = BACKEND_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"[Pipeline] Loaded env from {_env_path}")
    else:
        _env_path2 = BACKEND_ROOT.parent / ".env"
        if _env_path2.exists():
            load_dotenv(_env_path2)
            print(f"[Pipeline] Loaded env from {_env_path2}")
except ImportError:
    pass  # python-dotenv not installed — rely on shell env vars
    
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_supabase():
    """Get Supabase client."""
    from supabase_client import supabase
    return supabase


def _send_email(to: str, subject: str, html: str):
    """Send an email via Resend."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[Pipeline] RESEND_API_KEY not set, skipping email")
            return
        resend.api_key = resend_key
        resend.Emails.send({
            "from": "Parity Signal <notifications@civicscale.ai>",
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": html,
        })
        print(f"[Pipeline] Email sent: {subject} -> {to}")
    except Exception as exc:
        print(f"[Pipeline] Email failed: {exc}")


def _get_requester_email(sb, user_id: str) -> str | None:
    """Fetch user email from Supabase Auth."""
    try:
        resp = sb.auth.admin.get_user_by_id(user_id)
        user = getattr(resp, "user", None)
        if user:
            return getattr(user, "email", None)
    except Exception as exc:
        print(f"[Pipeline] Failed to get email for user {user_id[:8]}...: {exc}")
    return None


def _update_request_status(sb, request_id: str, status: str, **extra):
    """Update signal_topic_requests row."""
    data = {"status": status, **extra}
    sb.table("signal_topic_requests").update(data).eq("id", request_id).execute()
    print(f"[Pipeline] Request {request_id[:8]}... -> {status}")


def _run_subprocess(cmd: list[str], label: str) -> tuple[bool, str, str]:
    """Run a subprocess and return (success, stdout, stderr)."""
    print(f"\n[Pipeline] Running: {label}")
    print(f"  Command: {' '.join(cmd)}")
    start = time.time()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
    )

    elapsed = time.time() - start
    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"  {status} in {elapsed:.1f}s")

    if result.stdout:
        for line in result.stdout.strip().split("\n")[-10:]:
            print(f"    {line}")

    if result.returncode != 0 and result.stderr:
        for line in result.stderr.strip().split("\n")[-10:]:
            print(f"    [stderr] {line}")

    return result.returncode == 0, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step_discover_sources(slug: str, title: str, description: str) -> tuple[bool, list[str]]:
    """Step 0: Run source discovery and extract categories from output."""
    success, stdout, stderr = _run_subprocess(
        [
            sys.executable, str(SCRIPTS_DIR / "00_discover_sources.py"),
            "--slug", slug,
            "--title", title,
            "--description", description,
            "--count", "35",
        ],
        "Source Discovery (00_discover_sources.py)",
    )

    if not success:
        return False, []

    # Extract categories from the sentinel line in stdout
    categories = []
    for line in stdout.split("\n"):
        if line.startswith("__CATEGORIES_JSON__:"):
            try:
                categories = json.loads(line.split(":", 1)[1])
            except (json.JSONDecodeError, IndexError):
                pass
            break

    if not categories:
        categories = ["efficacy", "safety", "outcomes", "access", "regulatory", "emerging"]
        print(f"  Using fallback categories: {categories}")

    return True, categories


def step_register_topic(slug: str, title: str, description: str, categories: list[str]):
    """Step 1: Register the topic in topic_config at runtime."""
    from topic_config import register_topic
    manifest_filename = f"{slug}_sources.json"
    register_topic(slug, title, description, categories, manifest_filename)
    print(f"[Pipeline] Registered topic: {slug} with {len(categories)} categories")


def step_run_pipeline(slug: str) -> bool:
    """Step 2: Run the full 8-step pipeline."""
    success, stdout, stderr = _run_subprocess(
        [
            sys.executable, str(SCRIPTS_DIR / "run_pipeline.py"),
            "--issue-slug", slug,
            "--force",
        ],
        "Full Pipeline (run_pipeline.py --force)",
    )
    return success


def step_get_issue_id(sb, slug: str) -> str | None:
    """Step 3: Fetch the issue ID from signal_issues."""
    try:
        result = sb.table("signal_issues").select("id").eq("slug", slug).execute()
        if result.data:
            issue_id = result.data[0]["id"]
            print(f"[Pipeline] Issue ID: {issue_id}")
            return issue_id
    except Exception as exc:
        print(f"[Pipeline] Failed to get issue ID: {exc}")
    return None


def step_complete_request(sb, request_id: str, issue_id: str):
    """Step 4: Mark the request as completed."""
    _update_request_status(
        sb, request_id, "completed",
        issue_id=issue_id,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )


def step_auto_subscribe(sb, requester_id: str, issue_id: str):
    """Step 5: Auto-subscribe the requester to the new topic."""
    try:
        sb.table("signal_topic_subscriptions").upsert(
            {"user_id": requester_id, "issue_id": issue_id},
            on_conflict="user_id,issue_id",
        ).execute()
        print(f"[Pipeline] Auto-subscribed requester to issue")
    except Exception as exc:
        print(f"[Pipeline] Auto-subscribe failed (non-fatal): {exc}")


def step_notify_requester(sb, requester_id: str, title: str, slug: str):
    """Step 6: Create notification and send email to requester."""
    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")
    deep_link = f"/signal/{slug}"

    # In-app notification
    try:
        sb.table("signal_notifications").insert({
            "user_id": requester_id,
            "title": f"Topic Ready: {title}",
            "body": f"Your requested topic '{title}' is ready! View the full evidence dashboard now.",
            "deep_link": deep_link,
            "delivery_method": "email",
        }).execute()
    except Exception as exc:
        print(f"[Pipeline] Notification insert failed: {exc}")

    # Direct email
    email = _get_requester_email(sb, requester_id)
    if email:
        full_link = f"{frontend_url}{deep_link}"
        _send_email(
            email,
            f"Your Topic is Ready: {title}",
            f"""<h2>Your topic research is complete!</h2>
            <p>The evidence dashboard for <strong>{title}</strong> is now live on Parity Signal.</p>
            <p><a href="{full_link}" style="display:inline-block;padding:12px 24px;background:#0D7377;color:white;text-decoration:none;border-radius:6px;">View Evidence Dashboard</a></p>
            <hr>
            <p style="color:#666;font-size:12px;">Parity Signal by CivicScale &mdash; Evidence-based intelligence for healthcare decisions.</p>""",
        )


def step_notify_admin(title: str, slug: str, source_count: int, categories: list[str]):
    """Step 7: Send completion stats to admin."""
    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")
    _send_email(
        "fred@civicscale.ai",
        f"Pipeline Complete: {title}",
        f"""<h2>Topic Pipeline Complete</h2>
        <p><strong>Topic:</strong> {title}</p>
        <p><strong>Slug:</strong> {slug}</p>
        <p><strong>Sources ingested:</strong> {source_count}</p>
        <p><strong>Categories:</strong> {', '.join(categories)}</p>
        <p><a href="{frontend_url}/signal/{slug}">View Dashboard</a> |
           <a href="{frontend_url}/signal/admin/requests">Admin Dashboard</a></p>
        <hr>
        <p style="color:#666;font-size:12px;">Parity Signal by CivicScale</p>""",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run full topic pipeline for a new Signal topic request."
    )
    parser.add_argument("--slug", required=True, help="Topic slug")
    parser.add_argument("--title", required=True, help="Topic title")
    parser.add_argument("--description", required=True, help="Topic description")
    parser.add_argument("--request-id", required=True, help="signal_topic_requests UUID")
    parser.add_argument("--requester-id", required=True, help="Requester user UUID")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"FULL TOPIC PIPELINE: {args.title}")
    print(f"Slug: {args.slug}")
    print(f"Request: {args.request_id[:8]}...")
    print(f"{'='*60}")

    total_start = time.time()
    sb = _get_supabase()

    try:
        # Step 0: Discover sources
        ok, categories = step_discover_sources(args.slug, args.title, args.description)
        if not ok:
            raise RuntimeError("Source discovery failed")

        # Count sources from the generated manifest
        sources_path = (
            BACKEND_ROOT.parent / "data" / "signal" / "sources" / f"{args.slug}_sources.json"
        )
        source_count = 0
        if sources_path.exists():
            with open(sources_path) as f:
                source_count = len(json.load(f))

        # Step 1: Register topic in config
        step_register_topic(args.slug, args.title, args.description, categories)

        # Step 2: Run the full 7-step pipeline
        ok = step_run_pipeline(args.slug)
        if not ok:
            raise RuntimeError("Pipeline execution failed")

        # Step 3: Get the issue ID
        issue_id = step_get_issue_id(sb, args.slug)
        if not issue_id:
            raise RuntimeError(f"No issue found for slug '{args.slug}' after pipeline run")

        # Step 4: Mark request completed
        step_complete_request(sb, args.request_id, issue_id)

        # Step 5: Auto-subscribe requester
        step_auto_subscribe(sb, args.requester_id, issue_id)

        # Step 6: Notify requester
        step_notify_requester(sb, args.requester_id, args.title, args.slug)

        # Step 7: Notify admin with stats
        step_notify_admin(args.title, args.slug, source_count, categories)

        elapsed = time.time() - total_start
        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETE in {elapsed:.0f}s")
        print(f"  Sources: {source_count}")
        print(f"  Categories: {categories}")
        print(f"  Issue ID: {issue_id}")
        print(f"{'='*60}")

    except Exception as exc:
        elapsed = time.time() - total_start
        print(f"\n{'='*60}")
        print(f"PIPELINE FAILED after {elapsed:.0f}s: {exc}")
        print(f"{'='*60}")

        # Revert request status to approved so admin can retry
        try:
            _update_request_status(sb, args.request_id, "approved")
        except Exception:
            print("[Pipeline] Failed to revert request status")

        # Notify admin of failure
        try:
            _send_email(
                "fred@civicscale.ai",
                f"Pipeline FAILED: {args.title}",
                f"""<h2>Topic Pipeline Failed</h2>
                <p><strong>Topic:</strong> {args.title} ({args.slug})</p>
                <p><strong>Error:</strong> {exc}</p>
                <p><strong>Duration:</strong> {elapsed:.0f}s</p>
                <p>The request has been reverted to "approved" status so you can retry.</p>
                <hr>
                <p style="color:#666;font-size:12px;">Parity Signal by CivicScale</p>""",
            )
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
