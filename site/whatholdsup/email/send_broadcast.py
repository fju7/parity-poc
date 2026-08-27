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
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

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


def gate_report_path(args, html_path: Path | None) -> Path:
    if args.gate_report:
        return Path(args.gate_report)
    base = html_path if html_path else Path(args.html)
    return base.with_suffix(base.suffix + ".gate.json")


def require_gate(content: str, report_path: Path, waived: str | None,
                 what: str) -> None:
    """Refuse to send content the fact-check gate has not passed.

    On 2026-08-27 issue one's web page went through six-role checking three
    times and collected seventeen corrections. The EMAIL is a different file.
    It was never checked, and the broadcast that went out still said a hazard
    ratio was "consistent with the therapy preventing five deaths in six" —
    corrected on the page hours earlier — and still accused seven named outlets
    of something two of them had not done, which our own COVERAGE role had
    already established.

    Nothing tied the artifact that publishes to the checks that were run. This
    does. The report records the sha256 of the exact bytes it checked and
    whether it passed; both must match what is about to be mailed.

    Waivable, because a rule with no exit gets worked around rather than
    followed — but only out loud, and only with a reason that lands in the
    output where a person has to read it.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

    if waived:
        print(f"[WAIVED] : gate check skipped — {waived}")
        print(f"           content sha256 {digest[:16]}…")
        return

    if not report_path.exists():
        sys.exit(
            f"\n[BLOCKED] No fact-check report at {report_path}\n"
            f"          {what} has not been through the gate, and the last time we\n"
            "          skipped it the email went out with errors the web page no\n"
            "          longer had. Run:\n\n"
            f"            python scripts/signal/factcheck_draft.py <the html> \\\n"
            f"              --report {report_path}\n\n"
            "          Then send. Or pass --gate-waived \"your reason\" to proceed anyway.")

    try:
        rep = json.loads(report_path.read_text())
    except Exception as exc:
        sys.exit(f"\n[BLOCKED] Could not read {report_path}: {exc}")

    if not rep.get("passed"):
        sys.exit(
            f"\n[BLOCKED] The gate report at {report_path} records a FAILED run.\n"
            "          Resolve its findings, re-run the gate, then send.")

    if rep.get("sha256") != digest:
        sys.exit(
            f"\n[BLOCKED] {what} is not the content that was checked.\n"
            f"          gate report : {str(rep.get('sha256'))[:16]}…\n"
            f"          about to send: {digest[:16]}…\n\n"
            "          Either the file changed after it was gated — re-run the gate —\n"
            "          or the copy stored at Resend differs from the local file, in\n"
            "          which case check the draft in the dashboard before trusting it.")

    print(f"gate     : passed {rep.get('checked_at', '?')}, sha matches  OK")


def run_guards(html: str, text: str, what: str) -> None:
    """Every pre-send check. Exits 1 on the first category that fails.

    Called for content about to be created AND for content already sitting in
    Resend as a draft. The second case matters: a draft can be edited in the
    dashboard after this script created it, so checking the local file proves
    nothing about what would actually go out.
    """
    bad_css = check_css(html)
    if bad_css:
        print(f"\n[BLOCKED] The HTML in {what} uses CSS that Gmail strips:")
        for b in bad_css:
            print(f"            - {b}")
        sys.exit(1)
    print("css      : no variables, flex, grid or style blocks  OK")

    problems = check_broadcast(html, text)
    if problems:
        print(f"\n[BLOCKED] {what} would go to a list with a broken unsubscribe:")
        for pr in problems:
            print(f"            - {pr}")
        print("\n          Nothing was created or sent.")
        sys.exit(1)
    print(f"unsub    : {MERGE_TAG} present in every part, nothing hardcoded  OK")


def _client(key: str):
    """The official SDK, not a hand-rolled HTTP call.

    The first version of this script built the request by hand and got HTTP 403
    with Cloudflare error 1010 — "access denied based on browser signature".
    That is Cloudflare in front of api.resend.com refusing the request before
    Resend sees it, because the standard-library HTTP client announces itself as
    Python-urllib and that fingerprint is blocked. No amount of correct auth
    would have helped, and the error carried no JSON body to explain itself.

    send_test_email.py already used the SDK and worked, which is the whole
    diagnosis: use the same client for the same API rather than reimplementing
    the transport and inheriting a problem the SDK has already solved.
    """
    try:
        import resend
    except ImportError:
        sys.exit("[ERROR] The resend package is missing. Run: pip install resend")
    resend.api_key = key
    return resend


def list_broadcasts(args) -> None:
    """Show every broadcast on the account, newest information first.

    Exists because "the create command printed an id and I cannot find it" is a
    normal thing to happen — the id scrolls away, or the terminal was closed, or
    the run failed after creating. Asking Resend is more reliable than asking
    the person to remember.
    """
    key = os.environ.get(args.key_var)
    if not key:
        sys.exit(f"[ERROR] {args.key_var} is not set.")
    resend = _client(key)
    try:
        res = resend.Broadcasts.list()
    except Exception as exc:
        sys.exit(f"[ERROR] Could not list broadcasts: {exc}")

    rows = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if not rows:
        print("No broadcasts exist on this account.")
        print("Nothing was created — run the create command and read the last line.")
        return

    print(f"{len(rows)} broadcast(s):\n")
    for r in rows:
        def f(n):
            return r.get(n) if isinstance(r, dict) else getattr(r, n, None)
        status = (f("status") or "?")
        print(f"  {f('id')}")
        print(f"      status  : {status}")
        print(f"      subject : {f('subject')}")
        if f("name"):
            print(f"      name    : {f('name')}")
        if f("created_at"):
            print(f"      created : {f('created_at')}")
        if f("sent_at"):
            print(f"      sent    : {f('sent_at')}")
        if status.lower() in ("draft", "queued", "scheduled"):
            print(f"      -> check it:  --broadcast-id {f('id')}")
        print()


def send_existing(args) -> None:
    """Check, and optionally send, a broadcast that already exists.

    Create and send were separate from the start so a mistake produces a draft
    rather than a delivery. Until this existed only the create half could be run
    on its own, so sending the draft you had just inspected meant creating a
    second one — which is the opposite of what the separation was for.
    """
    key = os.environ.get(args.key_var)
    if not key:
        sys.exit(f"[ERROR] {args.key_var} is not set.")
    resend = _client(key)

    try:
        bc = resend.Broadcasts.get(args.broadcast_id)
    except Exception as exc:
        sys.exit(f"[ERROR] Could not fetch broadcast {args.broadcast_id}: {exc}")

    def field(name):
        return bc.get(name) if isinstance(bc, dict) else getattr(bc, name, None)

    status = field("status")
    print(f"broadcast: {args.broadcast_id}")
    print(f"status   : {status}")
    print(f"subject  : {field('subject')}")
    print(f"segment  : {field('segment_id') or field('audience_id')}")
    if field("sent_at"):
        print(f"sent_at  : {field('sent_at')}")

    # Resend's own record of whether this already went out. Sending twice is the
    # one mistake here that cannot be undone.
    if status and status.lower() not in ("draft", "queued", "scheduled"):
        sys.exit(f"\n[BLOCKED] This broadcast is '{status}', not a draft. Refusing to "
                 "touch it — a second send to a real list cannot be recalled.")

    html = field("html") or ""
    text = field("text") or ""
    if not html:
        sys.exit("\n[BLOCKED] Resend returned no HTML for this broadcast. Nothing to "
                 "check, so nothing to approve.")
    print(f"html     : {len(html):,} bytes as stored by Resend")
    print(f"text     : {len(text):,} bytes as stored by Resend" if text
          else "[WARN]   : no plain-text part stored")

    run_guards(html, text, "the stored draft")

    if not (args.send or args.scheduled_at):
        print("\nCHECKED ONLY — nothing has been mailed.")
        print("Re-run with --send to transmit this same broadcast.")
        return

    # The stored copy is what will actually be mailed, so that is what has to
    # match a passing report — not the file on disk it was created from.
    require_gate(html, gate_report_path(args, None), args.gate_waived,
                 "The HTML stored at Resend")

    params = {"broadcast_id": args.broadcast_id}
    if args.scheduled_at:
        params["scheduled_at"] = args.scheduled_at
    try:
        resend.Broadcasts.send(params)
    except Exception as exc:
        sys.exit(f"\n[ERROR] Send failed: {exc}\n        The broadcast is unchanged "
                 "and still a draft.")
    if args.scheduled_at:
        print(f"\nscheduled: {args.scheduled_at}  (broadcast {args.broadcast_id})")
    else:
        print(f"\nSENT     : broadcast {args.broadcast_id}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segment",
                    help="Resend segment id (audiences are called segments now). "
                         "Required when creating, with no default: a default here "
                         "would one day mail the wrong list and report success.")
    ap.add_argument("--subject")
    ap.add_argument("--list", action="store_true", dest="list_all",
                    help="List every broadcast on the account with its id and "
                         "status, and stop. Use this when the id from a create "
                         "run has scrolled away.")
    ap.add_argument("--broadcast-id",
                    help="Act on a broadcast that already exists instead of creating "
                         "one. Without --send this fetches the draft from Resend and "
                         "runs every check against the content Resend actually holds "
                         "— which is not necessarily the local file, since a draft can "
                         "be edited in the dashboard. With --send it checks, then "
                         "sends that same broadcast.")
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
    ap.add_argument("--gate-report",
                    help="Fact-check report for the content being sent. Defaults to "
                         "the HTML path with .gate.json appended. Required to send.")
    ap.add_argument("--gate-waived", metavar="REASON",
                    help="Send without a passing gate report. Requires a reason, "
                         "which is printed. Use it knowingly.")
    ap.add_argument("--key-var", default="RESEND_WHATHOLDSUP_KEY")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run every check and print what would be created. No API "
                         "call is made.")
    args = ap.parse_args()

    if args.list_all:
        list_broadcasts(args)
        return

    if args.broadcast_id:
        for flag, val in (("--segment", args.segment), ("--subject", args.subject)):
            if val:
                ap.error(f"{flag} is meaningless with --broadcast-id: the broadcast "
                         "already has one. Remove it so it is clear which broadcast "
                         "this command acts on.")
        if args.dry_run:
            ap.error("--dry-run makes no API call, but --broadcast-id has to fetch "
                     "the draft to check it. Run it without --dry-run; without "
                     "--send it still sends nothing.")
        send_existing(args)
        return

    if not args.segment or not args.subject:
        ap.error("--segment and --subject are required when creating a broadcast")

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

    run_guards(html, text, "this draft")

    # Before credentials, before any network call: a local check that fails
    # fast and cannot be masked by an unrelated error such as a missing key.
    if args.send or args.scheduled_at:
        require_gate(html, gate_report_path(args, html_path), args.gate_waived,
                     f"The HTML in {html_path.name}")

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

    resend = _client(key)
    try:
        created = resend.Broadcasts.create(body)
    except Exception as exc:
        sys.exit(f"\n[ERROR] Resend rejected the broadcast: {exc}")
    bid = created.get("id") if isinstance(created, dict) else getattr(created, "id", None)
    if not bid:
        sys.exit(f"\n[ERROR] Broadcast created but no id came back: {created!r}")
    print(f"\ncreated  : broadcast {bid}")

    if not (args.send or args.scheduled_at):
        print("\nDRAFT ONLY — nothing has been mailed.")
        print("Open it in the Resend dashboard and read it as a subscriber would.")
        print(f"Then re-run with --send to transmit.")
        return

    send_params = {"broadcast_id": bid}
    if args.scheduled_at:
        send_params["scheduled_at"] = args.scheduled_at
    try:
        resend.Broadcasts.send(send_params)
    except Exception as exc:
        sys.exit(f"\n[ERROR] Broadcast {bid} was created but NOT sent: {exc}\n"
                 f"        It is a draft in the dashboard; nothing was mailed.")
    if args.scheduled_at:
        print(f"scheduled: {args.scheduled_at}  (broadcast {bid})")
    else:
        print(f"SENT     : to segment {args.segment}  (broadcast {bid})")
    print("\nCheck the Resend dashboard for delivery, and your own inbox for the")
    print("unsubscribe link Resend substituted — click it and confirm it works")
    print("before this goes to anyone who is not you.")


if __name__ == "__main__":
    main()
