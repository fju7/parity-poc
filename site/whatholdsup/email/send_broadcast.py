"""
Send an issue of What Holds Up to a Resend segment, as a Broadcast.

WHY THIS IS A DIFFERENT SCRIPT FROM send_test_email.py
------------------------------------------------------
send_test_email.py uses the emails API: you name one recipient, so the sender
can build a per-recipient signed unsubscribe URL at compose time and set the
RFC 8058 headers itself.

A Broadcast does not work that way. Resend expands the segment at send time, so
only Resend can personalise a link. It substitutes {{{RESEND_UNSUBSCRIBE_URL}}}
per recipient and sets the List-Unsubscribe headers itself. That makes Resend's
unsubscribe the correct mechanism here, and our own endpoint the wrong one: a
hardcoded link in a broadcast would be the same URL for every reader, which
either unsubscribes nobody or the wrong person.

So the guards below are the inverse of the ones in send_test_email.py. There,
the check is that an unsubscribe is present in every part. Here, the check is
that the RESEND MERGE TAG is present in the HTML and that no hardcoded
unsubscribe link is competing with it.

CREATE AND SEND ARE SEPARATE ON PURPOSE
---------------------------------------
Running this creates a DRAFT broadcast and stops. Nothing is mailed until you
re-run with --send. A mistake in a script that mails a list should produce a
draft you can inspect, not a delivery you cannot recall.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    # what would be sent, no API call at all
    python ../site/whatholdsup/email/send_broadcast.py \
        --segment bae12ea6-cbad-4b91-b250-81991bf6b4b5 \
        --subject "The melanoma trial that succeeded without showing its work" \
        --dry-run

    # create the draft in Resend, still not sent
    python ../site/whatholdsup/email/send_broadcast.py --segment <id> --subject "..."

    # actually transmit
    python ../site/whatholdsup/email/send_broadcast.py --segment <id> --subject "..." --send
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://api.resend.com"

FROM_DEFAULT = "What Holds Up <issues@whatholdsup.org>"
REPLY_TO = "corrections@whatholdsup.org"

# Resend substitutes this per recipient. Three braces, not two.
MERGE_TAG = "{{{RESEND_UNSUBSCRIBE_URL}}}"

# CSS Gmail strips. Same list as the single-send script: a broadcast is read in
# the same clients and fails the same way.
UNSAFE = {
    "CSS variable": r"var\(--",
    "flexbox": r"display\s*:\s*flex",
    "grid": r"display\s*:\s*grid",
    "style block": r"<style[\s>]",
}

PLACEHOLDERS = r"%%[^%\s]{1,40}%%|\{\{[^}\s]{1,40}\}\}|\[\[[^\]\s]{1,40}\]\]"

# A mailto or a link to our own endpoint, hardcoded into a broadcast body. Every
# recipient would get the identical URL.
HARDCODED_UNSUB = r"mailto:unsubscribe@|/api/unsubscribe"


def check_css(html: str) -> list[str]:
    return [name for name, pat in UNSAFE.items() if re.search(pat, html, re.I)]


def check_broadcast(html: str, text: str) -> list[str]:
    """Every reason this must not become a broadcast. Empty list means it may."""
    problems: list[str] = []

    if MERGE_TAG not in html:
        problems.append(
            f"the HTML part does not contain {MERGE_TAG} — Resend has nothing to "
            "turn into a per-reader unsubscribe link")

    # PLACEHOLDERS matches {{...}}, which would also match the merge tag. Remove
    # the tag before looking, or the guard fires on the very thing it requires.
    for label, body in (("HTML", html), ("text", text)):
        if not body:
            continue
        stripped = body.replace(MERGE_TAG, "")
        left = sorted(set(re.findall(PLACEHOLDERS, stripped)))
        if left:
            problems.append(f"unfilled placeholder in the {label} part: {', '.join(left)}")

    for label, body in (("HTML", html), ("text", text)):
        if body and re.search(HARDCODED_UNSUB, body, re.I):
            problems.append(
                f"the {label} part still has a hardcoded unsubscribe. In a broadcast "
                "every reader receives the identical link, so it unsubscribes nobody "
                "or the wrong person. Replace it with the merge tag.")

    if text and MERGE_TAG not in text:
        problems.append(
            f"the plain-text part does not contain {MERGE_TAG}. A reader in a "
            "text-only client would have no way out.")

    return problems


def post(path: str, key: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        print(f"\n[ERROR] {e.code} from {path}\n        {detail}")
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segment", required=True,
                    help="Resend segment id (audiences are called segments now). "
                         "Required, with no default: a default here would one day "
                         "mail the wrong list and report success.")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--html", default=str(HERE / "issue1-melanoma.html"))
    ap.add_argument("--text", default=str(HERE / "issue1-melanoma.txt"))
    ap.add_argument("--from", dest="sender", default=FROM_DEFAULT)
    ap.add_argument("--name", help="Internal label shown in the Resend dashboard.")
    ap.add_argument("--send", action="store_true",
                    help="Transmit. Without this the broadcast is created as a "
                         "draft and nothing is mailed.")
    ap.add_argument("--scheduled-at",
                    help="Defer: ISO 8601, or natural language such as 'in 5 min'. "
                         "Implies --send.")
    ap.add_argument("--key-var", default="RESEND_WHATHOLDSUP_KEY")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run every check and print what would be created. No API "
                         "call is made.")
    args = ap.parse_args()

    html_path, text_path = Path(args.html), Path(args.text)
    if not html_path.exists():
        sys.exit(f"[ERROR] No HTML part at {html_path}")
    html = html_path.read_text(encoding="utf-8")
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""

    print(f"segment  : {args.segment}")
    print(f"subject  : {args.subject}")
    print(f"from     : {args.sender}")
    print(f"html     : {html_path.name} ({len(html):,} bytes)")
    print(f"text     : {text_path.name} ({len(text):,} bytes)" if text
          else "[WARN]   : no plain-text part")

    bad_css = check_css(html)
    if bad_css:
        print("\n[BLOCKED] The HTML uses CSS that Gmail strips:")
        for b in bad_css:
            print(f"            - {b}")
        sys.exit(1)
    print("css      : no variables, flex, grid or style blocks  OK")

    problems = check_broadcast(html, text)
    if problems:
        print("\n[BLOCKED] This would go to a list with a broken unsubscribe:")
        for p in problems:
            print(f"            - {p}")
        print("\n          Fix the files. Nothing was created.")
        sys.exit(1)
    print(f"unsub    : {MERGE_TAG} present in every part, nothing hardcoded  OK")

    if args.dry_run:
        print("\n--- DRY RUN — no broadcast created, nothing sent ---")
        return

    key = os.environ.get(args.key_var)
    if not key:
        sys.exit(f"[ERROR] {args.key_var} is not set.")

    body = {
        "segment_id": args.segment,
        "from": args.sender,
        "subject": args.subject,
        "reply_to": REPLY_TO,
        "html": html,
    }
    if text:
        body["text"] = text
    if args.name:
        body["name"] = args.name

    created = post("/broadcasts", key, body)
    bid = created.get("id")
    print(f"\ncreated  : broadcast {bid}")

    if not (args.send or args.scheduled_at):
        print("\nDRAFT ONLY — nothing has been mailed.")
        print("Open it in the Resend dashboard and read it as a subscriber would.")
        print(f"Then re-run with --send to transmit.")
        return

    sent = post(f"/broadcasts/{bid}/send", key,
                {"scheduled_at": args.scheduled_at} if args.scheduled_at else {})
    if args.scheduled_at:
        print(f"scheduled: {args.scheduled_at}  ({sent.get('id', bid)})")
    else:
        print(f"SENT     : to segment {args.segment}  ({sent.get('id', bid)})")
    print("\nCheck the Resend dashboard for delivery, and your own inbox for the")
    print("unsubscribe link Resend substituted — click it and confirm it works")
    print("before this goes to anyone who is not you.")


if __name__ == "__main__":
    main()
