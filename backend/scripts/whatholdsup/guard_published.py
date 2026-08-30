#!/usr/bin/env python3
"""Refuse to push a change to a published page that nobody signed off on.

WHY THIS EXISTS
---------------
On 2026-08-29 issue two was published at 14:26 and the record says so. At
14:56 one word was changed in the page -- a wrong first author, a correct
fix -- and it went to the world in an ordinary commit and push. The deploy
takes whatever is on the default branch. No preflight ran, no gate was
re-accepted, and published.json still described the version from half an
hour earlier. The live page was at a content hash that nothing in the
repository had ever approved, and nothing anywhere noticed.

Every gate we have runs inside publish.py. That is the whole hole: they
only fire when you go through the front door, and `git push` is a side
door that opens onto the same street.

WHAT IT CHECKS
--------------
For each issue that has ever been published: does the page file, AS IT
WILL EXIST ON THE BRANCH BEING PUSHED, still hash to the sha recorded by
the last `publish` entry? If not, the push is refused.

Unpublished issues are not touched -- drafts are meant to change. Email
files are reported as a warning and never block, because an email that
diverges is a re-send decision, not a publication: nothing reaches a
reader until somebody presses send.

WHAT IT DOES NOT CHECK
----------------------
It does not re-run the gates, the preflight, or the fact-checker. It is
deliberately dumb, deterministic and fast: no model, no network. It
answers one question -- has this been signed off at this exact content --
and refers you to the machinery that does the signing off.

HOW A LEGITIMATE PUBLISH GETS THROUGH
-------------------------------------
publish.py publishes by pushing and then waiting for the deploy, so its
own push would be blocked by this guard. It sets WHATHOLDSUP_PUBLISHING=1
around that push, and the guard stands aside when it sees it. That marker
is a note between two of our own scripts, not a security boundary; the
thing it protects against is an ordinary afternoon, not an attacker.

USAGE
-----
    python3 backend/scripts/whatholdsup/guard_published.py
    python3 backend/scripts/whatholdsup/guard_published.py --ref <commit>

Exit 0 clean, 1 blocked, 2 could not tell.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent          # backend/scripts/whatholdsup -> repo root
RECORD = ROOT / "backend" / "data" / "whatholdsup" / "published.json"


def _git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout


def _issues() -> dict:
    """The issue table, read from publish.py without importing it.

    publish.py imports seven sibling modules and touches the network on
    import in some paths. A pre-push hook must be fast and must not fail
    because something unrelated is broken, so the table is read out of the
    source with the module's own parser rather than by importing it.
    """
    src = (HERE / "publish.py").read_text(encoding="utf-8")
    import ast
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "ISSUES":
                    return ast.literal_eval(node.value)
    raise SystemExit("could not find ISSUES in publish.py")


def _blob(ref: str | None, rel: str) -> bytes | None:
    """The file's bytes at `ref`, or from the working tree when ref is None."""
    if ref is None:
        f = ROOT / rel
        return f.read_bytes() if f.exists() else None
    code, out = _git("show", "%s:%s" % (ref, rel))
    if code != 0:
        return None
    # git show on a text blob through capture_output=text would mangle CRLF;
    # go back for bytes so the hash matches what sha() computes on disk.
    p = subprocess.run(["git", "show", "%s:%s" % (ref, rel)],
                       cwd=ROOT, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def _record(ref: str | None) -> list[dict]:
    raw = _blob(ref, str(RECORD.relative_to(ROOT)))
    if raw is None:
        return []
    try:
        return json.loads(raw.decode("utf-8")).get("published", [])
    except Exception:
        return []


def _last(rows: list[dict], slug: str, action: str) -> dict | None:
    """The most recent record of `action` for `slug`.

    "publish" also matches "republish": a republish is a smaller sign-off --
    a person read a short diff and stood behind it, with the diff stored in
    the record -- but it is a sign-off, and the guard's only question is
    whether the content on the branch is content somebody approved.
    """
    # "update" counts too: a living issue changes on purpose, and publish.py
    # update signs the change off with the checks a change actually needs.
    # If the guard did not accept it, every update would have to be forced
    # past with --no-verify, which records nothing -- the exact hole this
    # guard exists to close.
    wanted = ({"publish", "republish", "update"} if action == "publish"
              else {action})
    hits = [r for r in rows if r.get("issue") == slug and r.get("action") in wanted]
    return hits[-1] if hits else None


ACK_FILE = ROOT / "backend" / "data" / "whatholdsup" / "known_divergences.json"


def _acknowledged(slug: str) -> dict:
    """{content_sha: record} for divergences somebody has deliberately accepted.

    WHY THIS EXISTS, AND WHY IT IS NOT A BACK DOOR
    ----------------------------------------------
    The guard warns on every push when a published page is live at a version
    the ledger does not record. That is right: it is how issue two's silent
    divergence was found. But a warning that fires on every push forever, for a
    divergence somebody has looked at and decided not to act on yet, trains the
    reader to skip the whole block -- and the next real one goes with it.

    So a divergence can be ACKNOWLEDGED. Not published, not recorded as
    published: acknowledged, with a reason and a date, BOUND TO THE EXACT
    CONTENT HASH. The warning still prints, once, saying it is known. The
    moment the live content changes by one byte, the hash no longer matches and
    the full warning returns.

    It cannot be used to silence a divergence the pusher is creating: that path
    is `blocking`, not `warnings`, and this function is never consulted there.
    """
    if not ACK_FILE.exists():
        return {}
    try:
        data = json.loads(ACK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {r["content"]: r for r in data.get("acknowledged", [])
            if r.get("issue") == slug and r.get("content")}


def check(ref: str | None = None,
          against: str | None = None) -> tuple[list[str], list[str]]:
    """(blocking problems, warnings).

    `against` is what the remote already has. It matters because the guard's
    job is to stop unreviewed content reaching a reader, and content that is
    already live is already there: refusing the push does not unpublish it,
    it only stops whatever else was in the push. Issue two has been live at
    an unrecorded hash since 2026-08-29 and will be until somebody does the
    work to re-publish it properly. Blocking every push in the meantime
    would make the guard something to be disabled rather than obeyed.

    So a divergence this push CREATES is a block, and a divergence this push
    merely INHERITS is a warning that names itself and does not go away.
    """
    issues, rows = _issues(), _record(ref)
    blocking: list[str] = []
    warnings: list[str] = []

    for slug, cfg in issues.items():
        pub = _last(rows, slug, "publish")
        if not pub:
            continue                       # never published; drafts may change freely

        rel = cfg.get("page")
        raw = _blob(ref, rel)
        if raw is None:
            blocking.append(
                "%s: the published page %s is missing from the commit being pushed."
                % (slug, rel))
            continue

        now = hashlib.sha256(raw).hexdigest()
        was = pub.get("sha", "")
        if now != was:
            already = None
            if against and set(against) != {"0"}:
                prev = _blob(against, rel)
                if prev is not None:
                    already = hashlib.sha256(prev).hexdigest()
            if already == now and now in _acknowledged(slug):
                ack = _acknowledged(slug)[now]
                warnings.append(
                    "%s: %s is live at a version recorded as KNOWN AND UNPUBLISHED "
                    "on %s.\n        reason: %s\n        This is an acknowledgement, "
                    "not a publication. It is bound to content\n        %s and returns "
                    "the moment that content changes."
                    % (slug, rel, ack.get("on", "?"), ack.get("reason", "")[:150],
                       now[:16]))
            elif already == now:
                warnings.append(
                    "%s: %s has been live at an unrecorded version since before this "
                    "push.\n        published %s  content %s\n        live now"
                    "                       content %s\n        This push does not "
                    "change it, so it is not blocked here. It is still\n        "
                    "outstanding: run `publish.py publish %s --yes`, or\n        "
                    "`publish.py record-live %s --reason \"...\"` if the change is "
                    "small enough."
                    % (slug, rel, pub.get("at", "?")[:19], was[:16], now[:16],
                       slug, slug))
                continue
            blocking.append(
                "%s: %s has changed since it was published.\n"
                "        published %s  content %s\n"
                "        this push  %s  content %s\n"
                "        Nothing has signed off on the new content. The deploy "
                "takes whatever\n        lands on this branch, so pushing puts it "
                "in front of a reader unreviewed."
                % (slug, rel, pub.get("at", "?")[:19], was[:16], "(pending)", now[:16]))

        ann = _last(rows, slug, "announce")
        for key in ("email_html", "email_txt"):
            erel = cfg.get(key)
            if not (ann and erel):
                continue
            if key != "email_html":
                continue                   # the record binds to the html only
            eraw = _blob(ref, erel)
            if eraw is None:
                continue
            if hashlib.sha256(eraw).hexdigest() != ann.get("sha", ""):
                warnings.append(
                    "%s: %s differs from the version sent on %s. Subscribers hold "
                    "the older one.\n        Not blocking -- an email reaches nobody "
                    "until somebody sends it."
                    % (slug, erel, ann.get("at", "?")[:19]))

    # An unpublished page on the deploy branch.
    #
    # The check above asks whether a PUBLISHED page still matches its record.
    # It is blind to a page that has never been published, because such a page
    # has no record to differ from -- and on 2026-08-30 that blindness put an
    # ungated, un-reviewed draft of issue three on the public web for six
    # commits, under a masthead reading "Published 30 August 2026". Nothing
    # linked to it and it was not in the sitemap, which is luck rather than a
    # control.
    #
    # So: every top-level page under site/whatholdsup must be either a standing
    # site page or an issue with a publication record. A draft lives in its
    # issue directory until it publishes, and the publish step is what moves it.
    STANDING = {"index.html", "what-this-is.html", "who-pays-for-this.html"}
    published_pages = {
        Path(cfg["page"]).name
        for slug, cfg in issues.items()
        if cfg.get("page") and _last(rows, slug, "publish")
    }
    _c, listing = _git("ls-tree", "--name-only",
                       (ref or "HEAD"), "site/whatholdsup/")
    for line in listing.splitlines():
        name = Path(line.strip()).name
        if not name.endswith(".html"):
            continue
        if name in STANDING or name in published_pages:
            continue
        blocking.append(
            "site/whatholdsup/%s is on the deploy branch and is not a standing "
            "site page\n        or a published issue. Anything at that path is "
            "served to readers the\n        moment this is pushed. A draft lives "
            "in its issue directory until\n        publish.py moves it." % name)

    return blocking, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default=None,
                    help="commit to check (default: the working tree)")
    ap.add_argument("--against", default=None,
                    help="the commit the remote already has. A divergence this push "
                         "creates blocks; one it inherits warns.")
    ap.add_argument("--quiet", action="store_true",
                    help="print nothing when there is nothing to say")
    args = ap.parse_args(argv)

    if os.environ.get("WHATHOLDSUP_PUBLISHING") == "1":
        if not args.quiet:
            print("guard: publish.py is doing this push; standing aside.")
        return 0

    try:
        blocking, warnings = check(args.ref, args.against)
    except Exception as e:                  # never wedge a push on our own bug
        print("guard: could not check (%s). Not blocking, but this is worth fixing."
              % e, file=sys.stderr)
        return 0

    for w in warnings:
        print("\n  WARN  %s" % w, file=sys.stderr)

    if not blocking:
        if not args.quiet:
            print("guard: every published page on this branch is the one that was "
                  "signed off.")
        return 0

    print("\nPUSH REFUSED — a published page would change without a publication "
          "record.\n", file=sys.stderr)
    for b in blocking:
        print("  BLOCK %s\n" % b, file=sys.stderr)
    print("  Do one of these:\n", file=sys.stderr)
    print("    Publishing this change on purpose — run the front door, which\n"
          "    re-runs preflight, pushes, waits for the deploy and records it:\n",
          file=sys.stderr)
    print("        python3 backend/scripts/whatholdsup/publish.py publish <slug> --yes\n",
          file=sys.stderr)
    print("    Not meant to go out yet — put the page back and push the rest:\n",
          file=sys.stderr)
    print("        git checkout -- <the page file>\n", file=sys.stderr)
    print("    You have decided anyway — bypass, and know that nothing will\n"
          "    record what went live or why:\n", file=sys.stderr)
    print("        git push --no-verify\n", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
