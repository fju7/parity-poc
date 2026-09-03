"""What Holds Up: sentences no gate run has ever seen.

WHY THIS EXISTS
---------------
Found on 2026-08-31, while measuring how much of a page is anchored to a
source. Issue two's board reads:

    state      ok
    gated 2026-08-29 on an earlier draft (3d7c7f85); every one of its 7
    finding(s) is resolved

Every finding resolved. And the page it describes is not the page that is
live. The gate report was written on 28 August. On 30 August the commit
"issue two said no head-to-head trial existed, and two do" added the Shaaban
trial and HARMONIA -- 116 patients randomised 58 and 58, clinical benefit
58.6% in both arms, median PFS 13.67 against 12.69 months, NCT05207709. The
gate report does not contain the word Shaaban.

So the most serious correction issue two ever made introduced a block of hard
figures that no model role has ever examined, and the board called the page ok,
because every finding it knew about was resolved and it knew about nothing
else.

THE PATTERN, WHICH IS WORSE THAN THE INSTANCE
---------------------------------------------
    ANCHORING DEGRADES EXACTLY WHERE WE CORRECT.

The gate runs on a draft. Corrections come after it. So the newest text on a
page is the least-checked text on that page -- and it is written under time
pressure, about the thing we just got wrong, which is precisely where a second
error is most likely and least expected. All three published issues carry a
gate report bound to a different sha than the page being served.

The gate already reports the mismatch; it says "<- differs" in plain sight.
What it does not do is act on it, because a resolved finding count is computed
from the findings that exist, and text nobody looked at generates none. An
absence of findings about a sentence is not a verdict about that sentence.

WHAT THIS DOES
--------------
Compares the page against the draft the gate report actually judged, and lists
the sentences that did not exist then. Empirical ones block. Deterministic --
a diff, no model, nothing to re-measure.

Going forward the gate records a fingerprint per sentence so the comparison
needs nothing else. For reports written before that existed, the judged draft
is recovered from git.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

OK, BAD, WARN = "ok", "BLOCKED", "warn"

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")

# A sentence that asserts something checkable about the world. Deliberately
# narrower than anchor_audit's, because this one BLOCKS: a number, a named
# trial, a registry id, a proportion, a survival quantity.
EMPIRICAL = re.compile(
    r"(\d+(\.\d+)?\s?%|\bHR\s?=?\s?\d|\bp\s?[=<]\s?0?\.\d|\bNCT\d{8}\b|"
    r"\b\d+(\.\d+)?\s?months?\b|\b\d{2,5}\s+(patients?|participants?|women|men)\b|"
    r"\bhazard ratio\b|\b\d+\.\d+\s+to\s+\d+\.\d+\b)", re.I)


def norm(t: str) -> str:
    return " ".join(t.split())


def sentences(page_text: str) -> list[str]:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    blocks = re.split(r"</(?:p|li|h[1-6]|td|div|blockquote|figcaption)\s*>", t, flags=re.I)
    out = []
    for b in blocks:
        txt = norm(html.unescape(re.sub(r"<[^>]+>", " ", b)))
        for s in _SENT.split(txt):
            s = norm(s)
            if len(s.split()) >= 6:
                out.append(s)
    return out


def fingerprint(sentence: str) -> str:
    """Stable identity for a sentence, insensitive to punctuation and case.

    Rewording counts as new, which is right: a sentence whose words changed is
    a sentence the role did not read. Fixing a comma does not.
    """
    key = re.sub(r"[^a-z0-9 ]", "", sentence.lower())
    return hashlib.sha256(" ".join(key.split()).encode()).hexdigest()[:16]


def fingerprints(page_text: str) -> dict:
    return {fingerprint(s): s for s in sentences(page_text)}


def _git(args: list[str]) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(ROOT)] + args,
                           capture_output=True, text=True, timeout=25)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def judged_text(page: Path, report: dict) -> tuple[str | None, str]:
    """The draft the gate actually judged, and how it was obtained."""
    fps = report.get("sentence_fingerprints")
    if fps:
        return None, "fingerprints"          # caller uses report's own list
    rel = page.relative_to(ROOT).as_posix()
    gate_rel = rel + ".gate.json"
    log = _git(["log", "-1", "--format=%H", "--", gate_rel])
    if not log or not log.strip():
        return None, "no git history for the gate report"
    commit = log.strip()
    old = _git(["show", f"{commit}:{rel}"])
    if old is None:
        return None, f"the page did not exist at {commit[:8]}"
    return old, f"recovered from git at {commit[:8]}"


def regate_cost(page: Path, report: dict, n_unjudged: int) -> str:
    """What re-gating this page would cost, counted rather than rated.

    THIRD VERSION. The first two were wrong in opposite directions, and both
    were wrong for the same underlying reason: they estimated from a proxy
    instead of counting the thing itself.

      v1 counted CHANGED SENTENCES and predicted 7 claims, $2.18. The run
         re-checked 46 and cost $5.20. Rewording a sentence breaks a claim's
         key even when its figure never moved, so changed sentences understate
         the work.

      v2 used the LAST RUN'S CARRY RATE -- 46 of 92 fresh, so 50% -- and
         predicted $13.86 to re-check three corrected sentences. But a carry
         rate is not a property of the page. It is a property of how much
         changed, and last time 155 sentences had changed against three now.
         Applying it here overstated the cost five-fold, which is worse than
         useless: it is a number that argues against running a check.

    --since carries a verdict forward when the claim's (figure, source) key
    still matches. So the claims that CANNOT carry are the ones whose figure is
    no longer on the page, and that is not a rate to be guessed at. It is a set
    to be counted.

      v3 counted the claims whose FIGURE IS GONE from the page, on the
         docstring's belief that "--since carries a verdict forward when the
         claim's (figure, source) key still matches". That is not what the
         carry does. carry_forward() keeps a claim only when it finds a prior
         entry AND that entry's verdict is VERIFIED. So two whole populations
         re-run that v3 charged nothing for:

           * every claim the last run did NOT verify. Issue one's last report
             held 54 claims, 42 VERIFIED — so twelve were going to re-run
             before anyone touched the page.
           * every claim the last run never extracted. Extraction is a model
             call and its output is not stable: the same page yielded 54
             claims one run and 59 the next.

         On 3 September v3 predicted $2.90 for a one-sentence edit. The run
         re-checked 35 of 59 claims and cost $6.59, and it was quoted to the
         editor as $2.90 because the number came from here.

    So v4 counts what CAN carry rather than what cannot: a claim with a
    VERIFIED verdict whose figure is still on the page. Everything else is
    charged for.

    IT IS A FLOOR AND SAYS SO. Extraction drift is the part no counting can
    reach — the claims the next run invents are not in this report to be
    counted — and a number offered without that caveat is how $2.90 became
    $6.59 in a sentence somebody budgeted against.
    """
    usage = (report.get("usage") or {})
    by = usage.get("by_role") or {}
    total = (usage.get("total") or {}).get("usd")
    if not by or not total:
        return ""
    doc_roles = sum(u.get("usd") or 0 for r, u in by.items()
                    if r.split(":")[0] in ("advocate", "inference", "extract"))
    src = [u for r, u in by.items() if r.split(":")[0] == "source"]
    per_claim = (sum(u.get("usd") or 0 for u in src) / len(src)) if src else 0.0

    flat = " ".join(html.unescape(re.sub(r"<[^>]+>", " ",
                    page.read_text(encoding="utf-8"))).split())
    claims = report.get("claims") or []
    if not claims:
        return ""
    verdicts = report.get("verdicts") or {}

    def _verdict(c):
        v = verdicts.get(c.get("id") or "")
        return (v or {}).get("verdict") if isinstance(v, dict) else None

    carries = [c for c in claims
               if _verdict(c) == "VERIFIED"
               and (not (c.get("figure") or "").strip()
                    or " ".join((c["figure"] or "").split()) in flat)]
    recheck = max(len(claims) - len(carries), 1)
    est = doc_roles + per_claim * recheck
    unverified = len(claims) - sum(1 for c in claims if _verdict(c) == "VERIFIED")
    return ("re-gating costs AT LEAST $%.2f — $%.2f for the roles that must read the "
            "whole page, plus %d claim(s) that cannot carry forward, at $%.2f each. "
            "%d of those were not VERIFIED last run and would re-run whatever the page "
            "says. A floor, not an estimate: extraction is a model call and the claims "
            "the next run invents are not in this report to be counted. Last full run: "
            "$%.2f for %d claims."
            % (est, doc_roles, recheck, per_claim, unverified, total, len(claims)))


def preflight_rows(slug: str, page: Path) -> list[tuple[str, str, str]]:
    rp = page.with_suffix(page.suffix + ".gate.json")
    if not rp.exists():
        return [("sentences the gate has seen", BAD,
                 "no gate report — every sentence on this page is unjudged")]
    try:
        report = json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:
        return [("sentences the gate has seen", BAD, f"{rp.name} is unreadable: {exc}")]

    now = fingerprints(page.read_text(encoding="utf-8"))
    if report.get("sha256") == hashlib.sha256(page.read_bytes()).hexdigest():
        return [("sentences the gate has seen", OK,
                 "the report judged this exact file; nothing has changed since")]

    known = set(report.get("sentence_fingerprints") or [])
    how = "fingerprints recorded by the gate"
    if not known:
        old, how = judged_text(page, report)
        if old is None:
            return [("sentences the gate has seen", BAD,
                     "the page differs from the report's sha and the judged draft could "
                     "not be recovered (%s), so there is no way to tell which sentences "
                     "were examined" % how)]
        # THE RECOVERY CAN SILENTLY PROVE NOTHING. If the gate report was
        # committed in the same commit as the final page, `git show` returns
        # that final page, and comparing it to itself yields zero new
        # sentences and a clean pass. deskilling did exactly this: its sha
        # does not match the report's, so the report was NOT produced on this
        # file, yet the check reported "the report judged this exact file".
        #
        # An unmeasurable difference is not the absence of a difference. The
        # gate's own rule -- an unrun check is not a pass -- applies to the
        # recovery too.
        if norm(re.sub(r"<[^>]+>", " ", old)) == norm(re.sub(
                r"<[^>]+>", " ", page.read_text(encoding="utf-8"))):
            return [("sentences the gate has seen", BAD,
                     "the page differs from the report's sha (%s vs %s), so the report was "
                     "not produced on this file — but the draft %s is identical to it, so "
                     "the comparison proves nothing. Which sentences were judged is UNKNOWN, "
                     "and unknown is not a pass. Re-gate."
                     % ((report.get("sha256") or "?")[:8],
                        hashlib.sha256(page.read_bytes()).hexdigest()[:8], how))]
        known = set(fingerprints(old))

    new = [s for fp, s in now.items() if fp not in known]
    empirical = [s for s in new if EMPIRICAL.search(s)]

    rows = [("sentences the gate has seen", OK if not new else WARN,
             "no sentence changed since the draft the gate judged; the file differs only "
             "in markup or formatting" if not new else
             "%d sentence(s) on the page did not exist in the draft the gate judged (%s)"
             % (len(new), how))]
    # The empirical ones, not every new sentence: prose generates no claims and
    # counting it inflated the first estimate to more than a full run.
    note = regate_cost(page, report, len(empirical))
    rows.append(("empirical sentences never judged",
                 OK if not empirical else BAD,
                 "every new sentence is prose, not a claim about the world"
                 if not empirical else
                 "%d sentence(s) carrying figures, trials or registry ids have never been "
                 "examined by any role: %s%s"
                 % (len(empirical), " || ".join(s[:90] for s in empirical[:3]),
                    ("  —  " + note) if note else "")))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", required=True)
    ap.add_argument("--slug", default="")
    ap.add_argument("--list", action="store_true", help="print every unjudged sentence")
    args = ap.parse_args()
    page = ROOT / args.page
    if not page.exists():
        sys.exit(f"no such page: {page}")
    bad = 0
    for name, state, detail in preflight_rows(args.slug, page):
        print(f"  {state:8s} {name}\n           {detail}")
        bad += state == BAD
    if args.list:
        rp = page.with_suffix(page.suffix + ".gate.json")
        report = json.loads(rp.read_text(encoding="utf-8"))
        old, how = judged_text(page, report)
        known = set(report.get("sentence_fingerprints") or (fingerprints(old) if old else []))
        print(f"\n  unjudged sentences ({how}):")
        for fp, s in fingerprints(page.read_text(encoding="utf-8")).items():
            if fp not in known:
                mark = "!" if EMPIRICAL.search(s) else " "
                print(f"   {mark} {s[:150]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
