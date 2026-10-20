#!/usr/bin/env python3
"""Who may be named in a signed field of a binding row.

WHY THIS EXISTS
---------------
On 18 and 19 October 2026 an agent wrote "Fred Ugast" into 979 signed fields on
437 deskilling rows (verdicts.locatable / faithful / warranted), and into 105
disposition fields beside them. Fred had read none of those rows. The notes
said "with Claude (advisor)" or "by Claude Code"; the name said otherwise, and
the name is the part a reader of the record trusts. Nothing in the repository
read the field, so nothing stopped it.

THE RULE (process doc §8, "Who may be named in a signed field")
---------------------------------------------------------------
For every NEW or CHANGED signer value in a staged bindings.json -- or a changed
signature object beside one:

  * an agent's name from AGENTS, optionally followed by "(session <id>)",
    passes;
  * a person's name passes only with a signature object {statement, source},
    where source is "<path>:<line>" naming a COMMITTED acceptance line --
    "Accepted by <name>, ..., stated in session", or "Accepted by <name>,
    <date>." followed by the transcription marker ("*Transcribed verbatim into
    this file by ...") -- whose line was last written by a commit WITHOUT a
    Claude Co-Authored-By trailer;
  * a blank value is not a signature, exactly as before.

Values already in HEAD are not re-judged: the guard is about what is written
from now on. The 20 October re-attribution is what dealt with what was there.

ITS LIMIT
---------
An agent can still fake this: write an acceptance line and commit it without
the trailer, then cite it. The test cannot see who typed. What it guarantees is
that doing so takes two deliberate false statements -- a fabricated acceptance
and a stripped attribution -- rather than one convenient default.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# The agents that write into these records. A value is an agent's name when it
# is one of these exactly, or one of these followed by " (session <id>)".
AGENTS = ("Claude Code", "Claude (advisor)", "Claude (Opus 5)")
_SESSION = re.compile(r"^\(session [0-9A-Za-z][0-9A-Za-z_-]*\)$")

ACCEPT_IN_SESSION = re.compile(r"^\s*Accepted by (?P<name>[^,]+),.*\bstated in session\b")
ACCEPT_DATED = re.compile(r"^\s*Accepted by (?P<name>[^,]+), [^.]*\d{4}\.\s*$")
TRANSCRIBED = re.compile(r"^\s*\*Transcribed verbatim into this file by\b")
CLAUDE_TRAILER = re.compile(r"(?im)^co-authored-by:.*\bclaude\b")


def is_agent(value: str) -> bool:
    v = " ".join((value or "").split())
    for a in AGENTS:
        if v == a:
            return True
        if v.startswith(a + " ") and _SESSION.match(v[len(a) + 1:]):
            return True
    return False


def slots(row: dict) -> dict:
    """Every signer value on a row: slot id -> (value, signature object)."""
    out = {}
    for q, v in ((row.get("verdicts") or {}).items()):
        if isinstance(v, dict):
            out["verdicts.%s" % q] = (v.get("by"), v.get("signature"))
    for field in ("scope_words", "hedge_dispositions"):
        seen = {}
        for d in row.get(field) or []:
            if not isinstance(d, dict):
                continue
            w = " ".join(str(d.get("word") or "").lower().split())
            n = seen[w] = seen.get(w, -1) + 1
            out["%s[%s#%d]" % (field, w, n)] = (d.get("by"), d.get("signature"))
    if isinstance(row.get("framing"), dict):
        out["framing"] = (row["framing"].get("by"), row["framing"].get("signature"))
    sigs = row.get("signatures") if isinstance(row.get("signatures"), dict) else {}
    for field in ("attested_by", "deferred_by"):
        if field in row:
            out[field] = (row.get(field), sigs.get(field))
    return out


def _git(root: Path, *args) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def _name_matches(signer: str, accepted: str) -> bool:
    s, a = signer.strip().casefold(), " ".join(accepted.split()).casefold()
    return bool(s) and (s == a or s in a.split())


def check_source(signer: str, source: str, root: Path = ROOT) -> tuple[bool, str]:
    """Does `source` ("path:line") name a committed acceptance by `signer`,
    written by a commit with no Claude trailer?"""
    m = re.match(r"^(?P<path>[^:]+):(?P<line>\d+)$", (source or "").strip())
    if not m:
        return False, "source %r is not <path>:<line>" % source
    path, line = m.group("path"), int(m.group("line"))
    code, text = _git(root, "show", "HEAD:%s" % path)
    if code != 0:
        return False, "%s is not committed" % path
    lines = text.splitlines()
    if not 1 <= line <= len(lines):
        return False, "%s has no line %d as committed" % (path, line)
    here = lines[line - 1]
    a = ACCEPT_IN_SESSION.match(here)
    if not a:
        a = ACCEPT_DATED.match(here)
        if not (a and any(TRANSCRIBED.match(x) for x in lines[line:line + 4])):
            return False, ("%s:%d is not an acceptance line (%r)" % (path, line, here.strip()[:80]))
    if not _name_matches(signer, a.group("name")):
        return False, "%s:%d accepts for %r, not %r" % (path, line, a.group("name"), signer)
    code, blame = _git(root, "blame", "-L", "%d,%d" % (line, line), "--porcelain", "HEAD", "--", path)
    if code != 0 or not blame:
        return False, "cannot find the commit that wrote %s:%d" % (path, line)
    sha = blame.split()[0]
    _, body = _git(root, "log", "-1", "--format=%B", sha)
    if CLAUDE_TRAILER.search(body):
        return False, ("%s:%d was written by %s, which carries a Claude Co-Authored-By "
                       "trailer" % (path, line, sha[:7]))
    return True, "accepted at %s:%d in %s" % (path, line, sha[:7])


def check_value(value, signature, root: Path = ROOT) -> tuple[bool, str]:
    if not (value or "").strip():
        return True, "blank: not a signature"
    if is_agent(value):
        return True, "an agent's name"
    if not isinstance(signature, dict) or not (signature.get("statement") or "").strip() \
            or not (signature.get("source") or "").strip():
        return False, ("%r is a person's name with no signature object {statement, source}"
                       % value)
    return check_source(value, signature["source"], root)


def failures(old: dict, new: dict, root: Path = ROOT) -> list[str]:
    """Every new or changed signer value in `new` that does not pass."""
    old_rows = (old or {}).get("bindings") or {}
    out = []
    for key, row in ((new or {}).get("bindings") or {}).items():
        before = slots(old_rows.get(key) or {})
        for slot, (value, sig) in slots(row).items():
            if before.get(slot) == (value, sig):
                continue
            ok, why = check_value(value, sig, root)
            if not ok:
                out.append("%s %s: %s" % (key[:8], slot, why))
    return out


def staged_failures(root: Path = ROOT) -> list[str]:
    """Run `failures` on every staged bindings.json against HEAD."""
    out = []
    code, listing = _git(root, "ls-files", "--", "issues/*/bindings.json")
    for path in listing.split():
        code, new_text = _git(root, "show", ":%s" % path)
        if code != 0:
            continue
        code, old_text = _git(root, "show", "HEAD:%s" % path)
        if code == 0 and old_text == new_text:
            continue
        old = json.loads(old_text) if code == 0 else {}
        out += ["%s: %s" % (path, f) for f in failures(old, json.loads(new_text), root)]
    return out


if __name__ == "__main__":
    bad = staged_failures()
    for b in bad:
        print("  BAD  %s" % b)
    print("  %d signer value(s) refused" % len(bad))
    raise SystemExit(1 if bad else 0)
