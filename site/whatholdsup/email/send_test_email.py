"""
Send one What Holds Up issue as a test, through Resend.

WHY THIS EXISTS
---------------
Resend's dashboard has no compose window. It shows you mail you have already
sent and nothing else, so the only ways to send are the API, an SDK, SMTP or
the CLI. This is the smallest possible SDK path.

It also exists because the artifact preview of an issue is NOT a sendable
email. That version uses CSS custom properties, flexbox and grid, all of which
Gmail strips — it would arrive as unstyled text. The file this sends is a
separate, table-based, fully inline version built for mail clients.

WHAT TO CHECK WHEN IT ARRIVES
-----------------------------
Not that it arrived. Open it in Gmail, click the three dots, choose "Show
original", and look for:

    dkim=pass   header.i=@whatholdsup.org
    spf=pass    smtp.mailfrom=send.whatholdsup.org
    dmarc=pass  header.from=whatholdsup.org

The SPF line naming the send. subdomain rather than the root is correct.
DMARC passes on the DKIM alignment.

Usage:
    export RESEND_WHATHOLDSUP_KEY="re_..."       # the domain-scoped key
    python send_test_email.py you@example.com

    python send_test_email.py you@example.com --dry-run   # no send, checks only
    python send_test_email.py you@example.com --html path/to/other.html
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_HTML = Path(__file__).resolve().parent / "issue1-melanoma.html"
FROM = "What Holds Up <issues@whatholdsup.org>"
SUBJECT = "The melanoma trial that succeeded without showing its work"
REPLY_TO = "corrections@whatholdsup.org"

# Anything in here means the file is a preview, not a sendable email. Gmail
# strips all three, and the result is a wall of unstyled text.
UNSAFE = {
    "CSS custom properties": r"var\(--",
    "flexbox": r"display:\s*flex",
    "grid": r"display:\s*grid",
    "a <style> block": r"<style",
    "web fonts": r"fonts\.googleapis\.com",
}

# Where an unsubscribe request actually lands.
#
# Two mechanisms, and both are offered because clients differ:
#
#   RFC 2369  the mailto. Works with no infrastructure and is the fallback when
#             the HTTPS endpoint is down or the secret is unset.
#   RFC 8058  one-click. Requires an HTTPS URL that accepts POST, plus the
#             List-Unsubscribe-Post header. Gmail and Outlook surface a native
#             unsubscribe control for it and treat its absence as a mild
#             negative signal on bulk mail.
#
# The header pair is ONLY emitted when a per-recipient signed URL could be
# built. Claiming one-click for a mailto is a protocol violation and some
# providers will treat it as a broken unsubscribe, which is worse than not
# claiming it at all.
UNSUBSCRIBE = "unsubscribe@whatholdsup.org"
MAILTO_UNSUBSCRIBE = f"<mailto:{UNSUBSCRIBE}?subject=Unsubscribe>"
UNSUBSCRIBE_ENDPOINT = "https://whatholdsup.org/api/unsubscribe"


def unsubscribe_url(email: str, secret: str) -> str:
    """Per-recipient one-click URL.

    The token is HMAC-SHA256 of the lowercased, stripped address, base64url
    without padding — byte-for-byte what site/whatholdsup/api/unsubscribe.js
    computes. The two are tested against each other rather than assumed to
    agree, because a silent mismatch would produce an unsubscribe link that
    looks right in every message and works in none.
    """
    import base64
    import hashlib
    import hmac
    from urllib.parse import quote

    addr = email.lower().strip()
    mac = hmac.new(secret.encode(), addr.encode(), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(mac).decode().rstrip("=")
    e = base64.urlsafe_b64encode(email.encode()).decode().rstrip("=")
    return f"{UNSUBSCRIBE_ENDPOINT}?e={quote(e)}&t={quote(token)}"


def unsubscribe_headers(email: str, secret: str | None) -> dict[str, str]:
    """List-Unsubscribe headers for one recipient.

    Without a secret this degrades to the mailto alone — deliberately, and
    without List-Unsubscribe-Post. Degrading loudly is the caller's job; see
    where this is called.
    """
    if not secret:
        return {"List-Unsubscribe": MAILTO_UNSUBSCRIBE}
    url = unsubscribe_url(email, secret)
    return {
        "List-Unsubscribe": f"<{url}>, {MAILTO_UNSUBSCRIBE}",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }

# Anything matching these left in a draft means a merge field was never
# filled. The melanoma issue went out to a test address with a literal
# %%unsubscribe%% in both the HTML and the plain text; nothing caught it
# because nothing was looking. This is what looks.
PLACEHOLDERS = r"%%[^%\s]{1,40}%%|\{\{[^}\s]{1,40}\}\}|\[\[[^\]\s]{1,40}\]\]"


def check(html: str) -> list[str]:
    return [name for name, pat in UNSAFE.items() if re.search(pat, html, re.I)]


def check_unsubscribe(parts: dict[str, str]) -> list[str]:
    """Every reason this must not be sent. Empty list means it may go."""
    problems = []
    for label, body in parts.items():
        if not body:
            continue
        left = sorted(set(re.findall(PLACEHOLDERS, body)))
        if left:
            problems.append(f"unfilled placeholder in the {label} part: {', '.join(left)}")
        if "unsubscribe" not in body.lower():
            problems.append(f"no unsubscribe mechanism in the {label} part")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Send one issue as a test through Resend.")
    ap.add_argument("to", help="Recipient. Use an address OUTSIDE civicscale.ai so it is a real external test.")
    ap.add_argument("--html", default=str(DEFAULT_HTML), help="HTML file to send.")
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--from", dest="sender", default=FROM)
    ap.add_argument("--key-var", default="RESEND_WHATHOLDSUP_KEY",
                    help="Environment variable holding the Resend API key.")
    ap.add_argument("--dry-run", action="store_true", help="Validate everything, send nothing.")
    args = ap.parse_args()

    path = Path(args.html)
    if not path.exists():
        print(f"[ERROR] Not found: {path}")
        here = sorted(q.name for q in path.parent.glob("*.html")) if path.parent.exists() else []
        if here:
            print(f"        HTML files in {path.parent}:")
            for q in here:
                print(f"          {q}")
            print("        Pass one with --html, or rename it to the default above.")
        sys.exit(1)
    html = path.read_text(encoding="utf-8")

    problems = check(html)
    print(f"file     : {path.name} ({len(html):,} bytes)")
    if problems:
        print("\n[BLOCKED] This file is a preview, not a sendable email. It uses:")
        for p in problems:
            print(f"            - {p}")
        print("\n          Gmail strips these. Send the table-based version instead.")
        sys.exit(1)
    print("markup   : table-based, inline styles, no stripped CSS  OK")
    if len(html) > 102_400:
        print(f"[WARN]   : {len(html):,} bytes — Gmail clips above 102,400 and hides the footer.")

    key = os.environ.get(args.key_var, "").strip()
    print(f"key      : {args.key_var} {'set' if key else 'MISSING'}")
    print(f"from     : {args.sender}")
    print(f"to       : {args.to}")
    print(f"reply-to : {REPLY_TO}")
    print(f"subject  : {args.subject}")

    if args.to.lower().endswith("@civicscale.ai"):
        print("\n[WARN]   : that is an internal address. Mail between two addresses on the")
        print("           same Workspace can pass without proving anything about how the")
        print("           outside world sees you. Use an external recipient.")

    if args.dry_run:
        txt = path.with_suffix(".txt")
        blockers = check_unsubscribe({
            "HTML": html,
            "text": txt.read_text(encoding="utf-8") if txt.exists() else "",
        })
        if blockers:
            print("\n[BLOCKED] Unsubscribe is not usable:")
            for b in blockers:
                print(f"            - {b}")
            sys.exit(1)
        print("unsub    : present in every part, no unfilled placeholders  OK")
        print(f"unsub    : {MAILTO_UNSUBSCRIBE}")
        print("\nDRY RUN — nothing sent.")
        return
    if not key:
        sys.exit(f"\n[ERROR] {args.key_var} is not set. Export the domain-scoped key first.")

    try:
        import resend
    except ImportError:
        sys.exit("[ERROR] pip install resend")

    resend.api_key = key
    payload = {
        "from": args.sender,
        "to": [args.to],
        "reply_to": REPLY_TO,
        "subject": args.subject,
        "html": html,
    }
    # Resend derives a plain-text part from the HTML when none is given, and
    # that derivation drags the hidden preheader padding — a run of nbsp and
    # zero-width joiners — into the top of the text body, where it is visible.
    # Supplying the text part explicitly is the fix, and it is better practice
    # regardless: the plain-text alternative is what a screen reader and a
    # text-only client actually get.
    txt = path.with_suffix(".txt")
    if txt.exists():
        payload["text"] = txt.read_text(encoding="utf-8")
        print(f"text part: {txt.name} ({len(payload['text']):,} bytes)")
    else:
        print(f"[WARN]   : no {txt.name} — Resend will derive the plain-text part,")
        print("           which pulls the preheader padding into the body.")
    # The headers are set here, not typed into each issue, so they cannot be
    # forgotten. Gmail and Outlook surface them as their own unsubscribe control.
    secret = os.environ.get("UNSUBSCRIBE_SECRET")
    payload["headers"] = unsubscribe_headers(args.to, secret)
    if secret:
        print(f"unsub    : one-click (RFC 8058) + mailto fallback")
        print(f"           {unsubscribe_url(args.to, secret)}")
    else:
        print("[WARN]   : UNSUBSCRIBE_SECRET is not set, so this goes out with the")
        print("           mailto only. That is valid RFC 2369 and it is NOT")
        print("           one-click: Gmail and Outlook will not show their native")
        print("           unsubscribe control. Fine for a test to yourself; set the")
        print("           secret before sending to a list.")

    blockers = check_unsubscribe({"HTML": payload.get("html", ""), "text": payload.get("text", "")})
    if blockers:
        print("\n[BLOCKED] This would go out with an unsubscribe that does not work:")
        for b in blockers:
            print(f"            - {b}")
        print("\n          Fix the file. Nothing was sent.")
        sys.exit(1)
    print("unsub    : present in every part, no unfilled placeholders  OK")

    try:
        r = resend.Emails.send(payload)
    except Exception as exc:
        print(f"\n[ERROR] Resend rejected the send: {exc}")
        print("        A 403 or 'domain not verified' means whatholdsup.org has not")
        print("        finished verifying, or the key is scoped to another domain.")
        sys.exit(1)

    print(f"\nSENT — id {r.get('id') if isinstance(r, dict) else r}")
    print("\nNow open it in Gmail, choose 'Show original', and check for")
    print("dkim=pass, spf=pass and dmarc=pass before trusting the setup.")


if __name__ == "__main__":
    main()
