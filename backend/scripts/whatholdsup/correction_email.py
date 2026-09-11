#!/usr/bin/env python3
"""Render a drafted correction to sendable HTML and text, and send it.

WHY THIS EXISTS
---------------
On 2026-09-10 a correction email was assembled, verified against held bytes,
passed through the passage stage four times and authorised to send — and there
was **no way to send it.** `update_email.py` assembled the body. `sent.json`
recorded sends. `publish.py announce` sends an ISSUE's email file to the
audience, and there is no configuration for a correction and no command that
takes an arbitrary body.

**The available shortcut was the dangerous one.** `announce melanoma --yes` is a
working sender with a warm key; it would have sent the melanoma issue email —
the document containing the errors the correction describes — to the audience the
correction was meant for. **A sender that exists and sends the wrong thing is
more dangerous than no sender, because it satisfies the instruction.**

WHAT IT DOES
------------
    render   the drafted Markdown -> the site's own email HTML and a text part
    check    every guard `announce` runs, plus the ones specific to a correction
    test     a broadcast to a segment holding only test addresses -- the
             shipping path exactly, differing only in the list
    send     a Resend broadcast to the audience, RECORDED BEFORE IT IS SENT

THE RECORD IS WRITTEN FIRST, AND THAT IS DELIBERATE
----------------------------------------------------
`publish.py` learned this the hard way: *"A record written before the act it
records is not a record"* — its first version wrote the row and then printed an
instruction to send, and a publication record carried a broadcast that had never
been transmitted.

**The opposite failure is the one that applies here**, and it is worse. A send is
irreversible and a record is not. If the send succeeds and the record was never
written, the next assembly re-sends corrections readers already have — and
nothing anywhere says they were sent. So the row is written first with
`state: "sending"`, and updated to `sent` or `failed` afterwards. **An interrupted
send leaves evidence rather than silence**, which is the only outcome that can be
recovered from.

THE REHEARSAL IS A BROADCAST TO A TEST SEGMENT, NOT AN EMAIL TO ONE ADDRESS
---------------------------------------------------------------------------
The first version of this file rehearsed through `send_test_email.py`, and that
path **blocked** -- correctly, and the block is the design working.

The two senders handle unsubscribe in opposite ways, and `send_broadcast.py` says
why in its own docstring. A broadcast is expanded by Resend at send time, so only
Resend can personalise the link; the HTML must carry `{{{RESEND_UNSUBSCRIBE_URL}}}`
and nothing hardcoded. `send_test_email.py` names one recipient, so it builds a
signed per-recipient URL itself, and an unfilled merge tag is an unusable
unsubscribe.

**So the broadcast body cannot be test-sent through the email path.** Rendering a
second variant with a real unsubscribe URL would test bytes that are not the bytes
that go out, which defeats the purpose of testing at all -- the difference would
sit in exactly the element most likely to be wrong.

The rehearsal is therefore a **broadcast to a segment containing only test
addresses**: same API, same body, same merge tag, same code path, a different
list. That is the only rehearsal that proves the thing being sent.

WHAT IT REFUSES
---------------
    * a body that is not the reviewed draft (sha-pinned at render time)
    * an HTML part without Resend's `{{{RESEND_UNSUBSCRIBE_URL}}}` merge tag, or
      with a hardcoded unsubscribe competing with it
    * a `covers:` list naming a correction that is not in any corrections.md
    * sending to the real audience before a test BROADCAST of the same
      sha has been recorded as sent
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_dates as I                                   # noqa: E402
import update_email as U                                  # noqa: E402

ROOT = I.ROOT
SENT = ROOT / "backend" / "data" / "whatholdsup" / "sent.json"
DRAFTS = ROOT / "site" / "whatholdsup" / "email" / "drafts"
OUT = ROOT / "site" / "whatholdsup" / "email" / "corrections"
BROADCAST = ROOT / "site" / "whatholdsup" / "email" / "send_broadcast.py"

MERGE = "{{{RESEND_UNSUBSCRIBE_URL}}}"
BG, INK, RULE, MUTED, LINK = "#DCDEDA", "#1A1A1A", "#C9CDC6", "#7C858B", "#2C4A63"


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def body_markdown(draft: Path) -> str:
    """The `## Body` blockquote of a draft, with the quote markers stripped.

    Only the blockquote. Everything else in a draft file -- the covers list, the
    notes to the sender, the passage-stage run -- is working material and must
    never reach a reader, which is why the body is fenced in the draft at all.
    """
    s = draft.read_text(encoding="utf-8")
    if "## Body" not in s:
        raise SystemExit("no '## Body' section in %s" % draft)
    seg = s[s.index("## Body"):]
    end = seg.find("\n## ", 3)
    seg = seg[:end] if end > 0 else seg
    lines = [re.sub(r"^> ?", "", l) for l in seg.splitlines() if l.startswith(">")]
    return "\n".join(lines).strip()


def _inline(t: str) -> str:
    t = _html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)",
               r'<a href="\2" style="color:%s;">\1</a>' % LINK, t)
    return t


def _blocks(md: str) -> list[list[str]]:
    """Blank-line-separated blocks. Shared by both renderings so the HTML and the
    text part can never disagree about where a paragraph ends."""
    blocks, cur = [], []
    for line in md.split("\n"):
        if not line.strip():
            if cur: blocks.append(cur); cur = []
        else:
            cur.append(line.rstrip())
    if cur: blocks.append(cur)
    return blocks


def to_html(md: str, subject: str, preheader: str) -> str:
    blocks = _blocks(md)

    parts = []
    for b in blocks:
        text = " ".join(b)
        if text.strip() == "---":
            parts.append('<hr style="border:0; border-top:1px solid %s; margin:26px 0;">' % RULE)
        elif text.startswith("### "):
            parts.append('<h2 style="margin:30px 0 12px; font-size:19px; line-height:1.35; '
                         'color:%s; font-weight:600;">%s</h2>' % (INK, _inline(text[4:])))
        else:
            parts.append('<p style="margin:0 0 16px; font-size:16px; line-height:1.62; '
                         'color:%s;">%s</p>' % (INK, _inline(text)))

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>%s</title>
</head>
<body style="margin:0; padding:0; background-color:%s; -webkit-text-size-adjust:100%%;">
<div style="display:none; font-size:1px; color:%s; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">%s</div>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%" style="background-color:%s;">
<tr><td align="center" style="padding:28px 14px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%%" style="max-width:600px; background-color:#FFFFFF;">
<tr><td style="padding:34px 34px 10px;">
<p style="margin:0 0 22px; font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:%s;">What Holds Up &middot; corrections</p>
%s
</td></tr>
<tr><td style="padding:6px 34px 32px;">
<hr style="border:0; border-top:1px solid %s; margin:0 0 16px;">
<p style="margin:0 0 8px; font-size:13px; line-height:1.6; color:%s;">Published by CivicScale. Think we got something wrong? <a href="mailto:corrections@whatholdsup.org" style="color:%s;">corrections@whatholdsup.org</a> &mdash; acknowledged in 48 hours. &middot; <a href="%s" style="color:%s;">Unsubscribe</a></p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
""" % (_html.escape(subject), BG, BG, _html.escape(preheader), BG, MUTED,
       "\n".join(parts), RULE, MUTED, LINK, MERGE, MUTED)


def to_text(md: str) -> str:
    # PARAGRAPHS FIRST, THEN EMPHASIS. The draft wraps at 78 columns, so a bold
    # or italic span routinely straddles a line break and `.` does not match a
    # newline. The first version of this stripped only the spans that happened
    # to fit on one line, and shipped `**A reader had no way to see...**` into
    # the text part with its asterisks intact -- markup leaking into the one
    # rendering where markup is not a thing.
    paras = ["\n".join(b) for b in _blocks(md)]
    paras = [" ".join(p.split()) if p.strip() != "---" else "---" for p in paras]
    t = "\n\n".join(paras)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", t, flags=re.S)
    t = re.sub(r"^### ", "", t, flags=re.M)
    t = t.replace("---", "-" * 52)
    return (t.strip() +
            "\n\n" + "-" * 52 +
            "\n\nPublished by CivicScale. Think we got something wrong?"
            "\ncorrections@whatholdsup.org - acknowledged in 48 hours."
            "\n\nUnsubscribe: %s\n" % MERGE)


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def guards(html: str, covers: list[str]) -> list[str]:
    bad = []
    if MERGE not in html:
        bad.append("the HTML has no %s merge tag; Resend cannot personalise the "
                   "unsubscribe and a broadcast without one is unsendable" % MERGE)
    hard = [u for u in re.findall(r'href="([^"]+)"', html)
            if "unsubscribe" in u.lower() and u != MERGE]
    if hard:
        bad.append("a hardcoded unsubscribe link competes with the merge tag: %s" % hard[:2])
    known = {c["heading"] for s in ("melanoma", "cdk46", "deskilling")
             for c in U.corrections(s)}
    for c in covers:
        if c not in known:
            bad.append("covers names a correction that is in no corrections.md: %r" % c[:70])
    if not covers:
        bad.append("covers is empty; a send that carries nothing should not be sent")
    try:
        import markup
        for f in markup.check(html):
            bad.append("markup %s at line %d: %s" % (f["kind"], f["line"], f["detail"]))
    except Exception as exc:                              # noqa: BLE001
        bad.append("the markup check did not run: %s. Unknown, not clean." % exc)
    return bad


def covers_from(draft: Path) -> list[str]:
    s = draft.read_text(encoding="utf-8")
    seg = s[:s.index("---")] if "---" in s else s
    return [" ".join(m.split()) for m in re.findall(r"^- \S+ — \*(.+?)\*", seg, re.M)]


# ---------------------------------------------------------------------------
# the record, written BEFORE the send
# ---------------------------------------------------------------------------

def open_row(subject, covers, html_sha, audience, kind, attestation="",
             gate_waived="") -> dict:
    import jsonio
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "issue": "corrections", "kind": kind, "subject": subject,
           "sha": html_sha, "audience": audience, "covers": covers,
           "state": "sending",
           **({"attested": attestation} if attestation else {}),
           # A waived gate is a decision, and a decision that leaves no trace is
           # not one. send_broadcast.py prints the reason; this keeps it beside
           # the send it excused, in the record the next assembly reads.
           **({"gate_waived": gate_waived} if gate_waived else {}),
           "note": "Written BEFORE the send. A send is irreversible and a record "
                   "is not: if the send succeeds and no row exists, the next "
                   "assembly re-sends what readers already have and nothing says "
                   "they were sent. Updated to sent or failed below."}
    def patch(doc):
        doc.setdefault("sends", []).append(row); return doc
    jsonio.edit(SENT, patch)
    return row


def close_row(at: str, state: str, detail: str = "") -> None:
    import jsonio
    def patch(doc):
        for s in doc.get("sends", []):
            if s.get("at") == at:
                s["state"] = state
                if detail: s["result"] = detail[:400]
        return doc
    jsonio.edit(SENT, patch)


# ---------------------------------------------------------------------------

def production_audiences() -> set:
    """Every segment id the publication has ever used to reach real subscribers.

    Derived from publish.ISSUES and the publication record, never transcribed --
    a copy of the id here would be one more place to keep in step, and the
    remedy list is explicit that the point of use derives.

    Why this exists. On 10 September 2026 the id offered as a TEST segment was
    the live subscriber list, and the guard below could not tell: it verified
    that a rehearsal had been recorded, never that the rehearsal had gone
    somewhere other than the real list. The same id in --test-segment and
    --audience satisfied it perfectly, which made the rehearsal a real send and
    then unlocked a second one.
    """
    import publish as P
    out = {i["audience"] for i in P.ISSUES.values() if i.get("audience")}
    try:
        rec = json.loads((ROOT / "backend" / "data" / "whatholdsup"
                          / "published.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for row in rec.get("published", []):
        m = re.search(r"sent to segment ([0-9a-f-]{36})", row.get("note", "") or "")
        if m:
            out.add(m.group(1))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", help="the reviewed draft under email/drafts/")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--preheader", default="Corrections to issues you have already read.")
    ap.add_argument("--audience", help="Resend segment id, for a real send")
    ap.add_argument("--audience-is-test-list", metavar="REASON",
                    help="Operator attestation that the audience currently holds "
                         "ONLY test addresses. Lifts the production-segment refusal "
                         "and the prior-test requirement, because when the audience "
                         "IS the test list the rehearsal and the send are the same "
                         "act -- and running both would mail the same people twice. "
                         "The reason is recorded in sent.json with the send.")
    ap.add_argument("--test-segment",
                    help="a Resend segment containing only test addresses. The "
                         "rehearsal is a BROADCAST to this segment, not an email "
                         "to one address -- see the note below.")
    ap.add_argument("--gate-waived", metavar="REASON",
                    help="passed through to send_broadcast.py: send without a "
                         "passing gate report on these bytes. The reason is "
                         "printed there and recorded in sent.json beside the row.")
    ap.add_argument("--send", action="store_true", help="actually send")
    a = ap.parse_args()

    draft = Path(a.draft)
    if not draft.is_absolute():
        draft = ROOT / draft
    md = body_markdown(draft)
    covers = covers_from(draft)
    html = to_html(md, a.subject, a.preheader)
    text = to_text(md)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = draft.stem.replace("-DRAFT", "")
    hp, tp = OUT / (stem + ".html"), OUT / (stem + ".txt")
    hp.write_text(html, encoding="utf-8")
    tp.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(html.encode("utf-8")).hexdigest()

    print("\n  rendered  %s  (%d bytes)" % (hp.relative_to(ROOT), len(html)))
    print("  rendered  %s  (%d bytes)" % (tp.relative_to(ROOT), len(text)))
    print("  sha256    %s" % sha[:32])
    print("  covers    %d correction(s)" % len(covers))
    for c in covers:
        print("     - %s" % c[:88])

    bad = guards(html, covers)
    print()
    for b in bad:
        print("  BLOCKED  %s" % b)
    if bad:
        print("\n  Nothing sent, nothing recorded.\n")
        return 1
    print("  every guard passes: merge tag present, no competing unsubscribe,")
    print("  every covered correction is in a corrections.md, markup valid.")

    if not a.send:
        print("\n  Rehearsal only. Nothing sent, nothing recorded.")
        print("  Re-run with --send, and with --test-segment before --audience.\n")
        return 0

    live = production_audiences()
    attest = (a.audience_is_test_list or "").strip()

    if attest and a.audience in live:
        print("\n  EXEMPTION IN FORCE — the production-segment refusal is lifted.")
        print("  Attested: %s" % attest)
        print("  This send goes to the real audience %s." % a.audience)
        print("  It is BOTH the rehearsal and the send: sending twice would mail")
        print("  the same people the same correction twice. One send only.")
        print("  The attestation is recorded in sent.json beside the row.\n")

    if a.test_segment and a.test_segment in live:
        print("\n  BLOCKED — %s is a production subscriber segment." % a.test_segment)
        print("  A rehearsal to the real list is not a rehearsal; it is the send.")
        print("  Worse, recording it would then unlock the broadcast and mail the")
        print("  same people twice. Use a segment containing only test addresses.")
        print("  Nothing sent, nothing recorded.\n")
        return 1

    if a.test_segment and a.audience and a.test_segment == a.audience:
        print("\n  BLOCKED — --test-segment and --audience are the same id.")
        print("  Nothing sent, nothing recorded.\n")
        return 1

    if a.test_segment:
        row = open_row(a.subject, covers, sha, a.test_segment, "test")
        cmd = [sys.executable, str(BROADCAST), "--segment", a.test_segment,
               "--subject", a.subject, "--html", str(hp), "--text", str(tp), "--send"]
    elif a.audience:
        prior = [s for s in json.loads(SENT.read_text()).get("sends", [])
                 if s.get("kind") == "test" and s.get("sha") == sha
                 and s.get("state") == "sent"]
        if not prior and not attest:
            print("\n  BLOCKED — no recorded test send of this exact body (sha %s)."
                  % sha[:12])
            print("  Broadcast it to a test segment first: --test-segment <id> --send")
            print("  Nothing sent, nothing recorded.\n")
            return 1
        row = open_row(a.subject, covers, sha, a.audience, "broadcast", attest,
                       (a.gate_waived or "").strip())
        cmd = [sys.executable, str(BROADCAST), "--segment", a.audience,
               "--subject", a.subject, "--html", str(hp), "--text", str(tp), "--send"]
        if (a.gate_waived or "").strip():
            cmd += ["--gate-waived", a.gate_waived.strip()]
    else:
        print("\n  --send needs either --test-segment or --audience. Nothing sent.\n")
        return 1

    import publish as P
    print("\n  record written first: sent.json row at %s, state=sending" % row["at"])
    print("  running: %s\n" % " ".join(cmd[1:]))
    proc = subprocess.run(cmd, cwd=str(BROADCAST.parent), capture_output=True,
                          text=True, env=P.sender_env())
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    print(out)
    close_row(row["at"], "sent" if proc.returncode == 0 else "failed", out)
    print("\n  sent.json row updated to state=%s"
          % ("sent" if proc.returncode == 0 else "failed"))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
