#!/usr/bin/env python3
"""Protected sentences: none leaves the page without a person's sign-off.

WHY THIS EXISTS
---------------
On WHU-S08 (the reliability study, October 2026) accepted rulings, applied word
for word as the process requires, narrowed the page's statement of its question
to the stocktake's own subject and removed every statement of what WHU had not
read: conclusion rulings b6caee39a4c1249d and 125d538dde6fcc01, audit units u46,
u47 and u45 (the last cut after three rounds), and u14's reading clause. Each
was a source-support ruling on a sentence no source can support -- no document
records what WHU read. docs/whu-omissions-investigation-2026-10.md, section 3.

Post-study fix 1 (2026-10-27) keeps those sentences away from source-support
rulings (bindings.protected_kind; conclusion_judge.judged_rows; the audit's
queue; ruling._conclusion_items). This row is the backstop for every other
path a sentence can change by: the advocate, the gate, changecheck, a
drafting session's own edit.

THE ROW
-------
Every protected sentence of the first full draft (RUN.md step 3b) must still be
on the page word for word (typography and spacing folded), or carry a sign-off
in issues/<case>/protected_signoffs.json:

    {"signoffs": [{"sentence_sha": "<fingerprint of the first-draft sentence>",
                   "first_draft": "<its text>", "now": "<the text that replaced it, or null>",
                   "why": "<reason>", "by": "<a person>",
                   "signature": {"statement": "...", "source": "<path>:<line>"}}]}

A sign-off is a PERSON's: `by` must not be an agent's name (signers.AGENTS), and
must pass signers.check_value -- a committed acceptance line written by a commit
with no Claude trailer (process doc section 8). Anything else is not a sign-off
and the row STOPs.

The first full draft is issue.json's `first_draft` (a commit) when set, else
the commit that added the page. An issue first published before ADOPTED is
SKIPPED by name, as the conclusion judge and the audit stage do.

    python3 protected.py <slug>        print the row
"""
from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

OK, BAD, WARN = "ok", "BLOCKED", "warn"   # publish.py's vocabulary
ROW_LABEL = "protected sentences kept"
SIGNOFF_FILE = "protected_signoffs.json"
ADOPTED = "2026-10-27T17:30:00+00:00"
PUBLISHED_ACTIONS = ("publish", "republish")


def _B():
    import bindings as B
    return B


def words(s: str) -> str:
    """Typography and spacing folded; case and every word kept (as
    audit_stage._words, restated so this module needs no audit import)."""
    s = unicodedata.normalize("NFKC", s or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return " ".join(s.split())


def _git(root: Path, *args) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def page_path(slug: str) -> str:
    return _B()._publish().issue_cfg(slug)["page"]


def first_draft(slug: str, root: Path = ROOT) -> tuple[str | None, str]:
    """(commit, how it was found). issue.json `first_draft` wins; else the
    commit that added the page."""
    import source_store as store
    ij = store.case_dir(slug) / "issue.json"
    cfg = json.loads(ij.read_text(encoding="utf-8")) if ij.exists() else {}
    if (cfg.get("first_draft") or "").strip():
        return cfg["first_draft"].strip(), "issue.json first_draft"
    code, out = _git(root, "log", "--diff-filter=A", "--format=%H", "--", page_path(slug))
    lines = [x for x in out.split() if x]
    if code != 0 or not lines:
        return None, "no commit adds %s" % page_path(slug)
    return lines[-1], "the commit that added the page"


def protected_sentences(slug: str, html: str, rows: dict | None = None) -> list[dict]:
    """[{sha, kind, sentence}] for every protected sentence of HTML's body. A
    row marker on the current bindings (by fingerprint) counts as well."""
    B = _B()
    rows = rows or {}
    out = []
    for s in B.page_sentences(slug, html=html):
        sha = B.fingerprint(s)
        kind = B.protected_kind(s, rows.get(sha))
        if kind:
            out.append({"sha": sha, "kind": kind, "sentence": s})
    return out


def missing(slug: str, first_html: str, now_html: str, rows: dict | None = None) -> list[dict]:
    """Protected sentences of the first draft that are not on the page now."""
    now = {words(s) for s in _B().page_sentences(slug, html=now_html)}
    return [p for p in protected_sentences(slug, first_html, rows) if words(p["sentence"]) not in now]


def load_signoffs(slug: str) -> dict:
    import source_store as store
    p = store.case_dir(slug) / SIGNOFF_FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"signoffs": []}


def signed(entry: dict, root: Path = ROOT) -> tuple[bool, str]:
    """Is ENTRY a person's sign-off?"""
    import signers
    by = (entry.get("by") or "").strip()
    if not by:
        return False, "no signer"
    if signers.is_agent(by):
        return False, "%r is an agent; a protected sentence needs a person's sign-off" % by
    if not (entry.get("why") or "").strip():
        return False, "no reason given"
    return signers.check_value(by, entry.get("signature"), root)


def published_before_adoption(slug: str, record_rows: list[dict]) -> str:
    first = [r for r in record_rows if r.get("issue") == slug and r.get("action") in PUBLISHED_ACTIONS]
    return first[0]["at"] if first and first[0]["at"] < ADOPTED else ""


def preflight_rows(slug: str, record_rows: list[dict] | None = None, *,
                   first_html: str | None = None, now_html: str | None = None,
                   signoffs: dict | None = None, rows: dict | None = None,
                   root: Path = ROOT) -> list[tuple[str, str, str]]:
    """One row, fail closed: BLOCKED if a protected sentence of the first full
    draft is gone from the page with no person's sign-off, or if the first
    draft cannot be found."""
    first = published_before_adoption(slug, record_rows or [])
    if first:
        return [(ROW_LABEL, OK, "SKIPPED — first published %s, before protected sentences were adopted (%s)"
                 % (first[:10], ADOPTED[:10]))]
    how = "given"
    if first_html is None:
        commit, how = first_draft(slug, root)
        if commit is None:
            return [(ROW_LABEL, BAD, "cannot find the first full draft (%s); set issue.json "
                     "\"first_draft\" to the step-3b commit" % how)]
        code, first_html = _git(root, "show", "%s:%s" % (commit, page_path(slug)))
        if code != 0:
            return [(ROW_LABEL, BAD, "cannot read the page at %s (%s)" % (commit[:7], how))]
        how = "%s, %s" % (commit[:7], how)
    if now_html is None:
        now_html = _B()._page_html(slug)
    if rows is None:
        rows = (_B().load(slug).get("bindings") or {})
    gone = missing(slug, first_html, now_html, rows)
    doc = signoffs if signoffs is not None else load_signoffs(slug)
    by_sha: dict[str, list[dict]] = {}
    for e in doc.get("signoffs") or []:
        by_sha.setdefault(e.get("sentence_sha") or "", []).append(e)
    unsigned, refused = [], []
    for g in gone:
        verdicts = [signed(e, root) for e in by_sha.get(g["sha"], [])]
        if any(ok for ok, _ in verdicts):
            continue
        unsigned.append(g)
        refused += [why for ok, why in verdicts if not ok]
    n = len(protected_sentences(slug, first_html, rows))
    if unsigned:
        return [(ROW_LABEL, BAD,
                 "%d protected sentence(s) of the first full draft (%s) changed or removed with no person's "
                 "sign-off in %s (e.g. %s %r)%s" % (
                     len(unsigned), how, SIGNOFF_FILE, unsigned[0]["kind"], unsigned[0]["sentence"][:90],
                     ("; sign-offs refused: %s" % "; ".join(refused[:3])) if refused else ""))]
    return [(ROW_LABEL, OK, "%d protected sentence(s) in the first full draft (%s); %s" % (
        n, how, "all still on the page" if not gone else
        "%d changed or removed, each with a person's sign-off" % len(gone)))]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.split("\n\n")[0])
        print("usage: protected.py <slug>")
        return 2
    for label, status, detail in preflight_rows(argv[0]):
        print("%s  %s  %s" % (status, label, detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
