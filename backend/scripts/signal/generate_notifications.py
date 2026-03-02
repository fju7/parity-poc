"""
Parity Signal: Notification Generation.

Reads signal_evidence_updates rows that don't yet have corresponding
signal_notifications, generates user-facing notification text via Claude,
and writes to signal_notifications for each subscribed user.

Handles gracefully when no subscribers exist (auth not built yet) —
prints a message and exits cleanly, making it safe to include in the
pipeline now.

Note: Actual delivery (push/SMS/email) is NOT handled here — only
notification record creation.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/generate_notifications.py --dry-run
    python scripts/signal/generate_notifications.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add backend/ to sys.path so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

GENERATION_MODEL = "claude-sonnet-4-6"
BACKOFF_DELAYS = [2, 5, 10]


# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_anthropic_client():
    """Lazy singleton for Anthropic client. Reads ANTHROPIC_API_KEY from env."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set.")
            print("  export ANTHROPIC_API_KEY=your_key_here")
            sys.exit(1)
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 4096) -> dict | list | None:
    """Call Claude API with retry on 529, return parsed JSON."""
    client = _get_anthropic_client()
    response = None

    for attempt in range(len(BACKOFF_DELAYS) + 1):
        try:
            response = client.messages.create(
                model=GENERATION_MODEL,
                max_tokens=max_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(BACKOFF_DELAYS):
                delay = BACKOFF_DELAYS[attempt]
                print(f"  [RETRY] Claude overloaded (529), attempt {attempt + 1}/{len(BACKOFF_DELAYS)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"  [ERROR] Claude API error: {exc}")
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"  [ERROR] Invalid JSON from Claude: {raw_text[:500]}")
        return None


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _get_supabase():
    """Import and return the Supabase client, or exit with message."""
    from supabase_client import supabase as sb
    if sb is None:
        print("ERROR: Supabase client not initialized.")
        print("Set SUPABASE_SERVICE_KEY environment variable before running.")
        sys.exit(1)
    return sb


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_unnotified_updates(sb) -> list[dict]:
    """Find evidence updates that don't yet have notifications.

    Returns list of update dicts from signal_evidence_updates.
    """
    # Get all evidence updates
    resp = (
        sb.table("signal_evidence_updates")
        .select("id, issue_id, change_type, claim_id, details, created_at")
        .order("created_at", desc=False)
        .execute()
    )
    all_updates = resp.data or []

    if not all_updates:
        return []

    # Get update IDs that already have notifications
    update_ids = [u["id"] for u in all_updates]
    notified_ids: set[str] = set()

    chunk_size = 50
    for i in range(0, len(update_ids), chunk_size):
        chunk = update_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_notifications")
            .select("evidence_update_id")
            .in_("evidence_update_id", chunk)
            .execute()
        )
        for row in (resp.data or []):
            notified_ids.add(row["evidence_update_id"])

    # Filter to unnotified
    unnotified = [u for u in all_updates if u["id"] not in notified_ids]
    return unnotified


def get_subscribed_users(sb, issue_id: str) -> list[dict]:
    """Get active subscribers for the given issue.

    Returns list of {user_id, subscription_id} dicts.
    """
    resp = (
        sb.table("signal_topic_subscriptions")
        .select("id, user_id")
        .eq("issue_id", issue_id)
        .eq("status", "active")
        .execute()
    )
    return resp.data or []


def get_user_preferences(sb, user_ids: list[str]) -> dict[str, dict]:
    """Get notification preferences per user.

    Returns {user_id: {delivery_method, ...}} or empty dict entries for defaults.
    """
    if not user_ids:
        return {}

    preferences: dict[str, dict] = {}
    chunk_size = 50

    for i in range(0, len(user_ids), chunk_size):
        chunk = user_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_notification_preferences")
            .select("user_id, delivery_method")
            .in_("user_id", chunk)
            .execute()
        )
        for row in (resp.data or []):
            preferences[row["user_id"]] = row

    return preferences


# ---------------------------------------------------------------------------
# Notification text generation
# ---------------------------------------------------------------------------

NOTIFICATION_SYSTEM_PROMPT = """You are generating short notification messages for users who subscribe to evidence updates about medical topics.

## Rules
- Title must be <= 60 characters
- Body is 1-2 sentences in plain language describing what changed
- deep_link is a URL path fragment in the format /signal/{issue_slug}#{anchor}
- Be factual and neutral — describe what changed, not whether it's good or bad
- Do not use medical jargon

## Output Format

Return a JSON array with one object per update:
[
  {
    "update_id": "the update ID provided",
    "title": "Short notification title",
    "body": "1-2 sentence description of the change.",
    "deep_link": "/signal/glp1-drugs#section"
  }
]"""


def _build_notification_prompt(updates: list[dict], issue_slug: str) -> str:
    """Build user prompt for a batch of updates."""
    parts = [
        f"Issue: {issue_slug}",
        f"Updates to generate notifications for: {len(updates)}",
        "",
    ]

    for i, update in enumerate(updates, 1):
        parts.append(f"--- Update {i} ---")
        parts.append(f"ID: {update['id']}")
        parts.append(f"Type: {update['change_type']}")
        details = update.get("details", {})
        parts.append(f"Details: {json.dumps(details)}")
        parts.append("")

    return "\n".join(parts)


def generate_notification_text(updates: list[dict], issue_slug: str) -> list[dict] | None:
    """Send updates to Claude to generate notification titles and bodies.

    Returns list of {update_id, title, body, deep_link} or None on failure.
    """
    user_text = _build_notification_prompt(updates, issue_slug)
    result = _call_claude(NOTIFICATION_SYSTEM_PROMPT, user_text)

    if result is None:
        return None

    if isinstance(result, dict):
        result = result.get("notifications", [result])

    return result if isinstance(result, list) else None


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def store_notifications(sb, notifications: list[dict], user_id: str,
                        delivery_method: str) -> int:
    """Insert notification rows for a single user. Returns count inserted."""
    inserted = 0

    for notif in notifications:
        row = {
            "user_id": user_id,
            "evidence_update_id": notif["update_id"],
            "title": notif.get("title", "Evidence update"),
            "body": notif.get("body", ""),
            "deep_link": notif.get("deep_link", ""),
            "delivery_method": delivery_method,
            "status": "pending",
        }
        try:
            sb.table("signal_notifications").insert(row).execute()
            inserted += 1
        except Exception as exc:
            print(f"  [ERROR] Failed to insert notification for user {user_id[:8]}...: {exc}")

    return inserted


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate notifications for unnotified evidence updates."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without API calls or DB writes",
    )
    args = parser.parse_args()

    sb = _get_supabase()

    # Step 1: Find unnotified updates
    unnotified = get_unnotified_updates(sb)

    if not unnotified:
        print("No new updates — nothing to notify.")
        return

    print(f"Found {len(unnotified)} unnotified updates")

    # Group by issue
    by_issue: dict[str, list[dict]] = defaultdict(list)
    for update in unnotified:
        by_issue[update["issue_id"]].append(update)

    # Step 2: For each issue, check subscribers
    total_notifications = 0
    total_api_calls = 0

    for issue_id, updates in by_issue.items():
        # Get issue slug for deep links
        resp = sb.table("signal_issues").select("slug").eq("id", issue_id).execute()
        issue_slug = resp.data[0]["slug"] if resp.data else "unknown"

        print(f"\nIssue: {issue_slug} ({len(updates)} updates)")

        # Get subscribers
        subscribers = get_subscribed_users(sb, issue_id)

        if not subscribers:
            print(f"  No subscribers — 0 notifications generated")
            continue

        user_ids = list({s["user_id"] for s in subscribers})
        preferences = get_user_preferences(sb, user_ids)

        print(f"  Subscribers: {len(user_ids)}")

        # --- Dry run ---
        if args.dry_run:
            print(f"\n  --- DRY RUN MODE (no API calls, no DB writes) ---")
            print(f"  Updates to process: {len(updates)}")
            by_type = defaultdict(int)
            for u in updates:
                by_type[u["change_type"]] += 1
            for ct, count in sorted(by_type.items()):
                print(f"    {ct}: {count}")
            print(f"  Would make 1 Claude API call")
            print(f"  Would create {len(updates) * len(user_ids)} notification rows "
                  f"({len(updates)} updates x {len(user_ids)} users)")
            continue

        # Step 3: Generate notification text (one API call per issue batch)
        print(f"  Generating notification text...", end=" ", flush=True)
        notifications = generate_notification_text(updates, issue_slug)
        total_api_calls += 1

        if notifications is None:
            print("FAILED")
            continue
        print(f"OK ({len(notifications)} notifications)")

        # Step 4: Create notification rows per subscriber
        for user_id in user_ids:
            prefs = preferences.get(user_id, {})
            delivery_method = prefs.get("delivery_method", "in_app")
            inserted = store_notifications(sb, notifications, user_id, delivery_method)
            total_notifications += inserted

        print(f"  Created {total_notifications} notification rows for {len(user_ids)} users")

    # --- Dry run summary ---
    if args.dry_run:
        print(f"\n--- DRY RUN COMPLETE ---")
        print(f"Total unnotified updates: {len(unnotified)}")
        print(f"Issues with updates: {len(by_issue)}")
        return

    # --- Summary ---
    print(f"\n{'='*60}")
    print("NOTIFICATION GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Updates processed: {len(unnotified)}")
    print(f"API calls: {total_api_calls}")
    print(f"Notifications created: {total_notifications}")


if __name__ == "__main__":
    main()
