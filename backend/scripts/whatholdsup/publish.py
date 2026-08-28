#!/usr/bin/env python3
"""
What Holds Up: publication control.

WHY THIS EXISTS
---------------
Until now the only way to know what had been published was to open the site and
read it. The pieces existed — a gate, a broadcast sender, a git remote that
Vercel watches — and nothing joined them or wrote down what happened. On
2026-08-27 the live melanoma page had been wrong for hours in a way that had
been fixed in the repo, and nothing anywhere said so.

This is the join. It answers three questions:

    what have we published, and is it still what we meant?   -> status
    is this issue safe to publish right now?                 -> check
    publish it, and write down that we did                   -> publish / announce

THE PREFLIGHT IS THE POINT
--------------------------
Every check below exists because something got past its absence:

  gate report present, passed, and matching the file
      An email went to subscribers carrying none of the corrections made to the
      page that afternoon. require_gate in send_broadcast.py closed that for the
      send; this closes it for the site too.

  every figure in the email appears on the page
      "Met both of its endpoints" was right on the page and wrong in the email,
      because the email was written from the page and compressed it. Nothing
      compared the two. Recorded as ENDPOINT_ROLE_CONFLATED, caught_by: nothing.

  html and text versions carry the same figures
      They have already drifted once in a single editing pass.

  no orphaned adjudications
      A decision whose sentence no longer exists is dead weight, and its absence
      means a finding that reads as settled is not.

  the live page matches the repo
      The failure this file was written after.

Usage:
    cd backend && source venv/bin/activate

    python scripts/whatholdsup/publish.py status
    python scripts/whatholdsup/publish.py check melanoma
    python scripts/whatholdsup/publish.py publish melanoma          # site
    python scripts/whatholdsup/publish.py announce melanoma         # email
    python scripts/whatholdsup/publish.py log

Nothing irreversible happens without --yes.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import os
import importlib.util
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root
GATE = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"
RECORD = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
REVIEWS = ROOT / "backend" / "data" / "whatholdsup" / "reviews.json"
CASES = ROOT / "issues"
REGISTER = ROOT / "issue-register.csv"

_spec = importlib.util.spec_from_file_location("factcheck_draft", GATE)
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)

# The registry lives in code rather than in the served directory: a JSON file
# under site/ is deployed and fetchable, and this names files, not content.
ISSUES = {
    "melanoma": {
        "number": 1,
        "title": "The Melanoma Result",
        "page": "site/whatholdsup/melanoma.html",
        "url": "https://whatholdsup.org/melanoma",
        "email_html": "site/whatholdsup/email/issue1-melanoma.html",
        "email_txt": "site/whatholdsup/email/issue1-melanoma.txt",
    },
}

NUM = re.compile(r"\d+\.\d+|\d+(?:,\d{3})+|\d+%|\bn=\d+\b")
OK, BAD, WARN = "ok", "BLOCKED", "warn"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def figures(text: str) -> set[str]:
    return set(NUM.findall(text))


# ---------------------------------------------------------------------------
# gate analysis
#
# A gate verdict means nothing on its own. It is a statement about one exact
# version of one file, made by an instrument with recorded defects. Reading
# `passed` alone gets it wrong in both directions: it blocks a draft whose
# findings were fixed an hour ago, and it clears a draft that changed after the
# run. On 2026-08-28 the board sent us back to re-run a gate on five findings
# that had already been fixed, and the report it was reading had never been
# opened past its `passed` flag. Two of the seven claim verdicts underneath it
# were live errors nobody had seen.
#
# So this reads four things and keeps them apart:
#
#   what the run found        objections, inferences AND claim verdicts, which
#                             are where fact errors actually live
#   whether it still applies  the report's sha against the file's sha now
#   whether it still bites    is each finding's quote still in the text
#   whether it is the tool    findings matching a recorded instrument defect
#
# Nothing here can turn a failed run on the CURRENT text into a pass. The most
# it can do is say that a stale run's findings are all gone from the text, and
# that is a question put to a human, not a default. Answering it is `accept-gate`,
# which writes the answer down.
# ---------------------------------------------------------------------------

RECORDS_ONLY = {"CALIBRATION"}          # recorded and published, never blocks

# Which role owns each part of a report, so a finding can be looked up in the
# decisions file. This mapping is the whole reason the board can stop asking
# about things already settled: draft_decisions.json is keyed on (role, quote),
# and until now nothing on the board consulted it. Sixteen recorded judgments
# about this one page sat there while the board demanded they be made again.
ROLE_OF = {"objections": "ADVOCATE", "inferences": "INFERENCE", "verdict": "SOURCE"}


def decided_by_figure(f: dict, decisions: dict) -> dict | None:
    """Match a SOURCE verdict to a recorded decision on figure, not wording.

    A claim quote is the extractor's paraphrase of a sentence, not the sentence.
    It is rewritten on every run, so a decision keyed on last run's phrasing
    reads as NEW this run, and a judgment made once has to be made again. This
    is the same reason carry_verdicts keys on (figure, attributed_to), and the
    same key is used here.

    Both the figure and, when the claim names one, the source have to appear in
    the recorded quote. A figure alone is too weak: "19 August" appears in four
    unrelated sentences on this page.
    """
    fig = fc._norm(f.get("figure") or "")
    if len(fig) < 5:
        return None
    src = fc._norm(f.get("source") or "")
    for (role, quote), dec in decisions.items():
        if role != "SOURCE" or fig not in quote:
            continue
        if src and len(src) >= 5 and src not in quote:
            continue
        return dec
    return None
VERDICT_OK = {"VERIFIED", "INTERNAL"}   # INTERNAL = the piece citing itself

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SUBS = {"–": "-", "—": "-", "−": "-", "‘": "'",
         "’": "'", "“": '"', "”": '"', " ": " "}
_MISSING = ("not appear", "could not be", "cannot be found", "not be located",
            "no entity called", "not found", "could not find", "unreachable",
            "does not exist")


def flatten(s: str) -> str:
    """Draft text and gate quotes reduced to something comparable.

    `&ndash;` on a page and an en dash in a quote are the same character to a
    reader and different bytes to `in`. An earlier version of this comparison
    missed exactly that and retired a decision that was still live.
    """
    s = _html.unescape(s or "")
    s = _TAG.sub(" ", s)
    for a, b in _SUBS.items():
        s = s.replace(a, b)
    return _WS.sub(" ", s).strip().casefold()


def slug_for(target: Path) -> str | None:
    rel = str(target.relative_to(ROOT)) if str(target).startswith(str(ROOT)) else str(target)
    for slug, cfg in ISSUES.items():
        if rel in (cfg.get("page"), cfg.get("email_html")):
            return slug
    return None


def coverage_sources(r: dict) -> list[tuple[str, str]]:
    """(outlet, url) pairs the COVERAGE role reported in this same run."""
    out = []
    for c in ((r.get("coverage") or {}).get("best_coverage") or []):
        if isinstance(c, dict):
            name = (c.get("outlet") or c.get("name") or "").strip()
            url = (c.get("url") or "").strip()
            if name and url:
                out.append((name, url))
    return out


def gate_findings(r: dict) -> list[dict]:
    """Every blocking-capable thing the run produced, in one shape.

    Objections and inferences carry a class. Claim verdicts do not — they are
    the SOURCE role's per-figure result, and NOT_FOUND or WRONG_VALUE there is
    a fact finding whatever the objections say. Leaving them out is how a run
    with three wrong figures reads as four phrasing notes.
    """
    out = []
    for section, prob, pfx in (("objections", "why", "o"), ("inferences", "problem", "i")):
        n = 0
        for f in (r.get(section) or []):
            if not isinstance(f, dict):
                continue
            n += 1
            cls = (f.get("class") or "").strip().upper() or "UNCLASSIFIED"
            out.append({
                "id": "%s%d" % (pfx, n), "kind": section, "class": cls,
                "severity": (f.get("severity") or "").upper(),
                "quote": f.get("quote") or "",
                "figure": "", "why": f.get(prob) or f.get("objection") or "",
                "fix": f.get("fix") or "",
                # unclassified fails closed: an unlabelled finding is not a
                # calibration note until somebody says it is.
                "blocking": cls not in RECORDS_ONLY,
            })
    claims = {c.get("id"): c for c in (r.get("claims") or []) if isinstance(c, dict)}
    for cid, v in (r.get("verdicts") or {}).items():
        if not isinstance(v, dict):
            continue
        verdict = (v.get("verdict") or "").upper()
        if verdict in VERDICT_OK:
            continue
        c = claims.get(cid, {})
        out.append({
            "id": cid, "kind": "verdict", "class": verdict,
            "severity": "SERIOUS" if verdict == "WRONG_VALUE" else "",
            "quote": c.get("claim") or "",
            "figure": c.get("figure") or "",
            "source": c.get("attributed_to") or "",
            "why": v.get("note") or "",
            "fix": v.get("found_value") or "",
            "blocking": True,
        })
    return out


def still_in_text(f: dict, body: str) -> str:
    """present / partial / gone / unknown — and unknown never reads as gone.

    Claim text is a paraphrase: the extractor rewrites the sentence, so a
    containment test on it fails on drafts that never changed. Figures do not
    get paraphrased, which is why carry-forward keys on them, and why this does.
    """
    fig = [x.strip() for x in re.split(r"[,;]", f.get("figure") or "") if x.strip()]
    if fig:
        hit = [x for x in fig if flatten(x) in body]
        if len(hit) == len(fig):
            return "figure"
        return "partial" if hit else "gone"
    q = flatten(f.get("quote") or "")
    if not q:
        return "unknown"
    if q in body:
        return "present"
    if len(q) > 90 and (q[:80] in body or q[-80:] in body):
        return "partial"
    if f["kind"] == "verdict":
        return "unknown"        # a paraphrase that does not match proves nothing
    return "gone"


# What each answer means in words, because "still in the text" said of a
# paraphrase we could not find is a claim we have not earned.
WHERE = {
    "present": "still in the text",
    "figure":  "its figures are still in the text",
    "partial": "partly still in the text",
    "unknown": "could not be located — the claim is the extractor's paraphrase, "
               "so absence of a match proves nothing either way",
    "gone":    "no longer in the text",
}


def instrument_flags(f: dict, sources: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Recorded defects this finding looks like. A flag, never a dismissal.

    Both patterns below cost us real time before they were named, and both are
    invisible from inside a single role: they are contradictions between roles,
    or between a role and the calendar.
    """
    flags = []
    blob = flatten(" ".join(str(f.get(k) or "") for k in ("why", "quote", "fix")))
    if any(m in blob for m in _MISSING):
        for name, url in sources:
            n = flatten(name)
            if len(n) >= 6 and n in blob:
                flags.append(("SOURCE_FALSE_NEGATIVE",
                              "COVERAGE cites %s with a URL in this same run: %s" % (name, url)))
                break
    if f["class"] == "NOT_FOUND" and any(w in blob for w in (
            "internal editorial", "internal disclosure", "publication's own",
            "not verifiable against any external", "cannot be verified against a primary",
            "cannot be verified against any external", "editorial claim")):
        flags.append(("INTERNAL_MISCLASSED_AS_NOT_FOUND",
                      "the role has an INTERNAL verdict for claims about ourselves and "
                      "returned NOT_FOUND instead; absence of an external source is the "
                      "expected result, not a finding"))
    if f["class"] in ("WRONG_VALUE", "FACT"):
        phrase = any(w in blob for w in ("primary analysis", "three-year", "3-year",
                                         "interim", "earlier readout", "first readout"))
        years = [int(y) for y in re.findall(r"\b(20[12]\d)\b", blob)]
        stale = years and min(years) <= datetime.now().year - 2
        if phrase or stale:
            flags.append(("WRONG_READOUT_COMPARISON",
                          "the figures it offers are sourced to %s — check it describes the "
                          "same data cut before believing it"
                          % ("an earlier readout" if phrase else str(min(years)))))
    return flags


def acceptance_file(slug: str | None) -> Path | None:
    case = case_dir(slug) if slug else None
    return (case / "gate-acceptances.json") if case else None


def acceptance_for(slug: str | None, target: Path, digest: str) -> dict | None:
    """A recorded human decision to proceed on a stale gate, bound to this sha.

    Bound, so it dies the moment the file changes again. An acceptance that
    outlived its content would be worse than no acceptance at all: it would
    read as a check.
    """
    fp = acceptance_file(slug)
    if not fp or not fp.exists():
        return None
    try:
        rows = json.loads(fp.read_text()).get("acceptances", [])
    except Exception:
        return None
    for a in reversed(rows):
        if a.get("file") == target.name and a.get("sha") == digest:
            return a
    return None


def gate_state(target: Path, slug: str | None = None) -> dict:
    """Everything knowable about this file's gate without spending a run."""
    slug = slug or slug_for(target)
    rp = target.with_suffix(target.suffix + ".gate.json")
    d = {"report": rp, "target": target, "exists": rp.exists(), "fresh": False,
         "findings": [], "blocking": [], "outstanding": [], "resolved": [],
         "suspect": [], "unlocatable": [], "settled": [], "calibration": 0, "accepted": None,
         "state": BAD, "detail": "", "notes": []}
    if not rp.exists():
        d["detail"] = "never gated — there is no %s" % rp.name
        return d
    try:
        r = json.loads(rp.read_text())
    except Exception as exc:
        d["detail"] = "%s is unreadable: %s" % (rp.name, exc)
        return d

    d["checked_at"] = r.get("checked_at", "?")
    d["recorded_sha"] = r.get("sha256") or ""
    d["current_sha"] = sha(target)
    d["fresh"] = d["recorded_sha"] == d["current_sha"]
    d["passed_flag"] = r.get("passed")

    body = flatten(target.read_text(encoding="utf-8"))
    sources = coverage_sources(r)
    decisions = fc.load_decisions(fc.DECISIONS, target.name)
    for f in gate_findings(r):
        f["where"] = still_in_text(f, body)
        f["flags"] = instrument_flags(f, sources)
        f["decided"], dec, _how = fc.classify(ROLE_OF.get(f["kind"], ""), f["quote"],
                                              f["severity"], decisions)
        if f["decided"] == "NEW" and f["kind"] == "verdict":
            byfig = decided_by_figure(f, decisions)
            if byfig:
                f["decided"], dec = "ADJUDICATED", byfig
        f["decision"] = (dec or {}).get("decision", "")
        f["reason"] = (dec or {}).get("reason", "")
        d["findings"].append(f)
        if not f["blocking"]:
            d["calibration"] += 1
            continue
        d["blocking"].append(f)
        if f["flags"]:
            d["suspect"].append(f)
        if f["where"] == "gone":
            d["resolved"].append(f)
        elif f["decided"] in ("ADJUDICATED", "OVERLAP"):
            # Read, judged, and written down with a reason. Asking again is not
            # rigour, it is the board failing to read its own record.
            d["settled"].append(f)
        else:
            d["outstanding"].append(f)
            if f["where"] == "unknown":
                d["unlocatable"].append(f)

    d["accepted"] = acceptance_for(slug, target, d["current_sha"])
    nb, no_, nr = len(d["blocking"]), len(d["outstanding"]), len(d["resolved"])
    ns = len(d["settled"])
    settled_note = (", %d already decided" % ns) if ns else ""
    kinds = ", ".join(sorted({f["class"] for f in d["outstanding"]})) or "none"

    if d["passed_flag"] is True and nb:
        d["notes"].append("the report says passed=True and carries %d blocking finding(s); "
                          "believe the findings" % nb)

    if d["fresh"]:
        if no_ == 0 and d["passed_flag"] is True:
            d["state"] = OK
            d["detail"] = "gated %s on this exact text, clean%s" % (
                d["checked_at"],
                " — %d calibration note(s)" % d["calibration"] if d["calibration"] else "")
        elif nb == 0:
            d["state"] = WARN
            d["detail"] = ("gated %s on this exact text; no blocking findings, but the run "
                           "recorded passed=%r" % (d["checked_at"], d["passed_flag"]))
        else:
            d["state"] = BAD
            d["detail"] = ("%d unresolved on this exact text%s — %s"
                           % (no_, settled_note, kinds))
        return d

    old = (d["recorded_sha"] or "?")[:8]
    if nb == 0:
        base = ("gated %s on an older draft (%s); nothing it raised is open%s"
                % (d["checked_at"], old, settled_note))
    elif no_ == 0:
        base = ("gated %s on an older draft (%s); all %d finding(s) it raised are "
                "resolved — %d gone from the text%s"
                % (d["checked_at"], old, nb, nr, settled_note))
    else:
        d["state"] = BAD
        nu = len(d["unlocatable"])
        d["detail"] = ("gated %s on an older draft (%s); %d of %d open — %d in the text, "
                       "%d unlocatable, %d gone%s"
                       % (d["checked_at"], old, no_, nb, no_ - nu, nu, nr, settled_note))
        return d
    if d["accepted"]:
        d["state"] = WARN
        d["detail"] = "%s — accepted %s by %s" % (base, d["accepted"].get("at", "?")[:10],
                                                  d["accepted"].get("by", "?"))
    else:
        d["state"] = BAD
        d["detail"] = "%s — needs an explicit acceptance, or a fresh run" % base
    return d


def gate_report(target: Path) -> tuple[str, str]:
    """(state, detail) — the two-value view the preflight and the board use."""
    d = gate_state(target)
    return d["state"], d["detail"]

def live_body(url: str, timeout: int = 20) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "whatholdsup-publish"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def load_record() -> list[dict]:
    if not RECORD.exists():
        return []
    try:
        return json.loads(RECORD.read_text()).get("published", [])
    except Exception:
        return []


def append_record(entry: dict) -> None:
    rows = load_record()
    rows.append(entry)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({
        "what_this_is": "Every publication and every send, appended. This is the "
                        "answer to 'what have we published', and it is in the repo "
                        "so it is versioned and diffable rather than only true on "
                        "a server somewhere.",
        "published": rows,
    }, indent=2), encoding="utf-8")



def outside_review(page: Path, slug: str) -> tuple[str, str]:
    """Has an independent reviewer read THIS version of the assessment?

    The gate is five roles that share an instrument and therefore share its
    blind spots — measured, not assumed: the recall fixture has a class no role
    finds. The outside review of issue one raised the direction-versus-magnitude
    defect that none of the six phases had, and that became rule 8. It is the
    only check that can find what the others are constitutionally unable to see,
    so it is a STOP and not a warning.

    A review is bound to the content hash it read. If the piece changed
    afterwards the review is not void — the changes were probably the ones it
    asked for — but a human has to say so, which is the point.
    """
    if not REVIEWS.exists():
        return BAD, "no outside review has ever been recorded"
    try:
        rows = json.loads(REVIEWS.read_text()).get("reviews", [])
    except Exception as exc:
        return BAD, f"reviews.json is unreadable: {exc}"
    mine = [r for r in rows if r.get("issue") == slug]
    if not mine:
        return BAD, f"no outside review recorded for {slug}"
    latest = mine[-1]
    if latest.get("sha") == sha(page):
        return OK, (f"reviewed {latest.get('at', '?')[:10]} by "
                    f"{latest.get('reviewer', 'unnamed')}, "
                    f"{latest.get('findings', '?')} finding(s), all adjudicated")
    return WARN, (f"the last review read a different version "
                  f"({latest.get('at', '?')[:10]}, sha {str(latest.get('sha'))[:8]}). "
                  f"Confirm the only changes since were the ones it asked for.")


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def preflight(slug: str, *, for_email: bool) -> list[tuple[str, str, str]]:
    cfg = ISSUES[slug]
    page = ROOT / cfg["page"]
    ehtml = ROOT / cfg["email_html"]
    etxt = ROOT / cfg["email_txt"]
    out: list[tuple[str, str, str]] = []

    for label, f in (("page file", page), ("email html", ehtml), ("email text", etxt)):
        out.append((label, OK if f.exists() else BAD,
                    str(f.relative_to(ROOT)) if f.exists() else f"missing: {f}"))
    if not (page.exists() and ehtml.exists() and etxt.exists()):
        return out

    st, detail = gate_report(page)
    out.append(("page gate", st, detail))
    st, detail = gate_report(ehtml)
    out.append(("email gate", st, detail))

    ptext, etext, ttext = fc.read_draft(page), fc.read_draft(ehtml), etxt.read_text(encoding="utf-8")

    stray = figures(etext) - figures(ptext)
    out.append(("email figures on page", OK if not stray else BAD,
                "every figure in the email appears on the page" if not stray
                else f"in the email and not on the page: {', '.join(sorted(stray))}"))

    drift = figures(etext) ^ figures(ttext)
    out.append(("html/text parity", OK if not drift else BAD,
                "same figures in both" if not drift
                else f"differ: {', '.join(sorted(drift))}"))

    for label, f, text in (("page", page, ptext), ("email", ehtml, etext)):
        dec = fc.load_decisions(fc.DECISIONS, f.name)
        orph = fc.orphaned(dec, text)
        out.append((f"{label} adjudications", OK if not orph else WARN,
                    f"{len(dec)} decisions, none orphaned" if not orph
                    else f"{len(orph)} quote a sentence that is gone: "
                         + "; ".join(q[:44] for _r, q in orph)))

    st, detail = outside_review(page, slug)
    out.append(("outside review", st, detail))

    body = live_body(cfg["url"])
    if body is None:
        out.append(("live page", WARN, f"could not reach {cfg['url']}"))
    else:
        same = hashlib.sha256(body.encode()).hexdigest() == sha(page)
        out.append(("live page", OK if same else WARN,
                    "matches the repo" if same
                    else "DIFFERS from the repo — the site is behind"))
    return out


def show(rows: list[tuple[str, str, str]], waive: str | None = None) -> bool:
    mark = {OK: "  ok ", BAD: " STOP", WARN: " warn"}
    for label, st, detail in rows:
        m = " WAIVED" if (waive and st == BAD) else mark[st]
        print(f"{m:>7}  {label:24} {detail}")
    blocked = [l for l, st, _d in rows if st == BAD]
    if blocked and waive:
        print()
        print(f"  WAIVED: {', '.join(blocked)}")
        print(f"  Reason: {waive}")
        print("  This goes into the publication record. It is not a pass; it is a")
        print("  decision to publish without one, on the record, with a name on it.")
        return True
    return not blocked


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_status(_args) -> int:
    rec = load_record()
    print()
    print(f"{'issue':12} {'page':10} {'live':10} {'email':10} {'last sent':12}")
    print("-" * 60)
    for slug, cfg in ISSUES.items():
        page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]
        pg = gate_report(page)[0] if page.exists() else BAD
        eg = gate_report(ehtml)[0] if ehtml.exists() else BAD
        body = live_body(cfg["url"])
        if body is None:
            live = "unreachable"
        elif hashlib.sha256(body.encode()).hexdigest() == sha(page):
            live = "current"
        else:
            live = "BEHIND"
        sent = [r for r in rec if r["issue"] == slug and r["action"] == "announce"]
        print(f"{slug:12} {('gated' if pg == OK else 'ungated'):10} "
              f"{live:10} {('gated' if eg == OK else 'ungated'):10} "
              f"{(sent[-1]['at'][:10] if sent else 'never'):12}")
    print()
    if not rec:
        print("Nothing has been recorded as published yet.")
    return 0


def cmd_check(args) -> int:
    print(f"\nPreflight: {args.slug}\n")
    ok = show(preflight(args.slug, for_email=False), args.waive)
    print()
    print("Ready." if ok else "BLOCKED — fix every STOP above.")
    return 0 if ok else 1


def cmd_log(_args) -> int:
    rec = load_record()
    if not rec:
        print("\nNo publications recorded.\n")
        return 0
    print()
    for r in rec:
        print(f"  {r['at'][:19]}  {r['action']:9} {r['issue']:12} {r.get('note', '')}")
        print(f"{'':21}  content {r.get('sha', '?')[:16]}  commit {r.get('commit', '-')[:9]}")
    print()
    return 0


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def cmd_publish(args) -> int:
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    print(f"\nPreflight: {args.slug}\n")
    if not show(preflight(args.slug, for_email=False), args.waive):
        print("\nBLOCKED — nothing published.")
        return 1
    if not args.yes:
        print("\nPreflight passed. Re-run with --yes to commit, push and wait for the deploy.")
        return 0

    code, out = git("status", "--porcelain")
    if code != 0:
        print(f"\ngit status failed: {out}")
        return 2
    if out.strip():
        for f in ("page", "email_html", "email_txt"):
            git("add", cfg[f])
        git("add", "site/whatholdsup")
        code, out = git("commit", "-m",
                        f"whatholdsup: publish {args.slug} (issue {cfg['number']})")
        if code != 0 and "nothing to commit" not in out:
            print(f"\ncommit failed: {out}")
            return 2
    code, out = git("push", "origin", "HEAD")
    if code != 0:
        print(f"\npush failed: {out}")
        return 2
    print("  pushed. waiting for the deploy to serve it...")

    want = sha(page)
    for attempt in range(40):
        body = live_body(cfg["url"])
        if body and hashlib.sha256(body.encode()).hexdigest() == want:
            print(f"  live matches the repo after {attempt * 15}s")
            break
        time.sleep(15)
    else:
        print("  the live page still differs after 10 minutes. Not recorded as published.")
        return 3

    _c, commit = git("rev-parse", "HEAD")
    append_record({
        "issue": args.slug, "action": "publish",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": want, "commit": commit, "url": cfg["url"],
        "note": f"issue {cfg['number']} — {cfg['title']}",
        "waived": args.waive or None,
    })
    print(f"\nPublished and recorded. {cfg['url']}")
    return 0


def cmd_announce(args) -> int:
    cfg = ISSUES[args.slug]
    ehtml = ROOT / cfg["email_html"]
    print(f"\nPreflight: {args.slug}\n")
    rows = preflight(args.slug, for_email=True)
    if not show(rows, args.waive):
        print("\nBLOCKED — nothing sent.")
        return 1
    live = [d for l, _s, d in rows if l == "live page"]
    if live and "DIFFERS" in live[0]:
        print("\nBLOCKED — the site is behind the repo. Publish before announcing, or "
              "subscribers will follow a link to something older than the email.")
        return 1
    if not args.yes:
        print("\nPreflight passed. Re-run with --yes to send.")
        print("send_broadcast.py performs the send and enforces its own gate guard.")
        return 0

    append_record({
        "issue": args.slug, "action": "announce",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": sha(ehtml), "commit": git("rev-parse", "HEAD")[1],
        "note": "recorded here; the send itself is send_broadcast.py --send",
        "waived": args.waive or None,
    })
    print("\nRecorded. Now run send_broadcast.py to perform the send.")
    return 0




def case_dir(slug: str) -> Path | None:
    for d in sorted(CASES.glob("*/issue.json")):
        try:
            if json.loads(d.read_text()).get("slug") == slug:
                return d.parent
        except Exception:
            continue
    return None


def cmd_send_for_review(args) -> int:
    """Snapshot exactly what the reviewer is about to read, then hand it over.

    reviews.json stores the hash, which proves a later version differed. Only
    the bytes say what it actually said. Six months on, deciding whether a
    reviewer was objecting to sentence A or to the sentence that replaced it
    is not a question a hash can answer.
    """
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    case = case_dir(args.slug)
    if case is None:
        print(f"No case file for {args.slug} under {CASES}/ — create issue.json first.")
        return 2
    digest = sha(page)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap = case / "review" / f"{day}-sent.html"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(page.read_bytes())

    adj = case / "review" / f"{day}-adjudication.md"
    if not adj.exists():
        adj.write_text(f"""# {args.slug} — adjudication of the outside review, {day}

Reviewed content: `{snap.name}`, sha256 `{digest[:16]}`
Standard: version {json.loads((case / 'issue.json').read_text()).get('standards_version', '?')}

The review itself is in `{day}-review.md` and is never edited after the fact,
including by us. This file sits beside it and is where our decisions go.

One block per finding. Every REJECT also goes into `draft_decisions.json` with
a `what_would_change_it`, so a rejection is a judgment on the record rather
than a thing we chose not to do.

---

## OR-001

**Finding**

> _paste the reviewer's finding_

**Disposition** — ACCEPT / ACCEPT-IN-PART / REJECT

**Reason**

**Change** — the exact edit, or "none"

**Sources considered** — S00x, S00y
""", encoding="utf-8")

    print(f"\nSnapshot: {snap.relative_to(ROOT)}")
    print(f"sha256   : {digest}")
    print(f"Adjudication template: {adj.relative_to(ROOT)}")
    print(f"\nSend the reviewer {cfg['page']} and the prompt at")
    print("docs/whatholdsup-outside-review-prompt.md. Not the email, and not the")
    print("gate report — a reader shown our findings anchors on them.")
    print("Save their report verbatim as", (case / 'review' / f'{day}-review.md').relative_to(ROOT))
    return 0


def cmd_review(args) -> int:
    """Record that an outside review happened and was adjudicated."""
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    if not page.exists():
        print(f"missing: {page}")
        return 2
    rows = []
    if REVIEWS.exists():
        try:
            rows = json.loads(REVIEWS.read_text()).get("reviews", [])
        except Exception:
            rows = []
    case = case_dir(args.slug)
    snaps = sorted((case / "review").glob("*-sent.html")) if case else []
    match = [f for f in snaps if hashlib.sha256(f.read_bytes()).hexdigest() == sha(page)]
    if not match:
        print("\nNo snapshot matches the current page. Run send-for-review first, or —")
        print("if the page changed after review — say which snapshot was reviewed and")
        print("record the review against that version, not this one.")
        for f in snaps:
            print(f"  have: {f.name}  sha {hashlib.sha256(f.read_bytes()).hexdigest()[:16]}")
        return 2

    rows.append({
        "issue": args.slug,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": sha(page),
        "reviewed_file": str(match[-1].relative_to(ROOT)),
        "standards_version": json.loads((case / "issue.json").read_text()).get("standards_version"),
        "reviewer": args.reviewer,
        "findings": args.findings,
        "accepted": args.accepted,
        "note": args.note or "",
    })
    REVIEWS.parent.mkdir(parents=True, exist_ok=True)
    REVIEWS.write_text(json.dumps({
        "what_this_is": "Outside reviews of full assessments, and what we did with "
                        "them. Bound to the content hash the reviewer actually read, "
                        "because a review of an earlier draft is not a review of this "
                        "one. Findings we rejected belong in draft_decisions.json with "
                        "a reason, like every other finding we reject.",
        "reviews": rows,
    }, indent=2), encoding="utf-8")
    rej = args.findings - args.accepted
    print(f"\nRecorded: {args.findings} finding(s), {args.accepted} accepted, {rej} rejected.")
    if rej:
        print(f"Those {rej} rejected finding(s) belong in draft_decisions.json with a")
        print("reason and a what_would_change_it, or this record is the only trace")
        print("that somebody decided to publish anyway.")
    return 0



def cmd_register(_args) -> int:
    """Regenerate issue-register.csv from the case files.

    Generated, never hand-edited. A register somebody updates by hand is wrong
    by the fifth issue and nobody notices which row — and the whole value of a
    register is that you can trust it without opening anything else.
    """
    import csv
    rows = []
    for d in sorted(CASES.glob("*/issue.json")):
        try:
            m = json.loads(d.read_text())
        except Exception as exc:
            print(f"[WARN] {d} unreadable: {exc}")
            continue
        dates, rev = m.get("dates", {}), m.get("review", {})
        rows.append({
            "id": m.get("id", ""), "slug": m.get("slug", ""),
            "title": m.get("title", ""), "topic": m.get("topic", ""),
            "status": m.get("status", ""),
            "standards": m.get("standards_version", ""),
            "drafted": dates.get("draft_started") or "",
            "reviewed": dates.get("outside_review") or "",
            "published": dates.get("published") or "",
            "findings": rev.get("findings") if rev.get("findings") is not None else "",
            "accepted": rev.get("accepted") if rev.get("accepted") is not None else "",
            "rejected": rev.get("rejected") if rev.get("rejected") is not None else "",
            "corrections": (m.get("corrections") or {}).get("count", ""),
            "url": m.get("url", ""),
        })
    if not rows:
        print(f"No issue.json found under {CASES}/")
        return 1
    with REGISTER.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{REGISTER.name}: {len(rows)} issue(s)")
    for r in rows:
        print(f"  {r['id']:8} {r['status']:10} {r['slug']:22} {r['title']}")
    return 0



# The steps are gates, and a gate that passes should hand straight to the next
# one. Until now each was a separate command a human had to remember, in order,
# which is how the outside review got skipped: not by a decision, but by nobody
# reaching that line. `next` says what the single next action is. `run` performs
# every step that is reversible and stops at the first thing that is not.

GATE = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"


def next_action(slug: str) -> tuple[str, str]:
    """(what to do next, the command that does it)."""
    cfg = ISSUES[slug]
    page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]

    for label, f in (("assessment", page), ("email", ehtml)):
        g = gate_state(f, slug)
        if g["state"] == BAD:
            rel = f.relative_to(ROOT)
            since = (" --since ../%s.gate.json" % rel
                     if f.with_suffix(f.suffix + ".gate.json").exists() else "")
            # A run is not always the answer. Read what the last one found
            # first: on 2026-08-28 six of its twelve findings were already
            # fixed, two were the instrument, and a re-run would have cost
            # money to rediscover that.
            if g["exists"] and not g["fresh"] and not g["outstanding"]:
                # Nothing is open. What is missing is a signature on text the
                # run never saw, and offering a re-run here is how this board
                # sent us back to spend money rediscovering settled findings.
                return ("sign off the %s gate — %s" % (label, g["detail"]),
                        'python scripts/whatholdsup/publish.py accept-gate %s --file %s '
                        '--reason "..."' % (slug, "assessment" if label == "assessment" else "email"))
            hint = ("\n        read them first: publish.py gate-status %s" % slug
                    if g["exists"] else "")
            return ("gate the %s — %s%s" % (label, g["detail"], hint),
                    "python scripts/signal/factcheck_draft.py ../%s%s --report ../%s.gate.json"
                    % (rel, since, rel))

    st, detail = outside_review(page, slug)
    if st == BAD:
        return ("outside review — the only check that finds what our own roles cannot "
                "see, and it has never run",
                "python scripts/whatholdsup/publish.py send-for-review %s" % slug)
    if st == WARN:
        return ("confirm the outside review still applies — %s" % detail,
                "python scripts/whatholdsup/publish.py send-for-review %s" % slug)

    blocked = [l for l, s_, _d in preflight(slug, for_email=False) if s_ == BAD]
    if blocked:
        return ("resolve: %s" % ", ".join(blocked),
                "python scripts/whatholdsup/publish.py check %s" % slug)

    rec = [r for r in load_record() if r["issue"] == slug]
    if not any(r["action"] == "publish" for r in rec):
        return ("PUBLISH — everything upstream is clear. This one is yours.",
                "python scripts/whatholdsup/publish.py publish %s --yes" % slug)
    if not any(r["action"] == "announce" for r in rec):
        return ("ANNOUNCE — the site is live and recorded. This one is yours, and it "
                "cannot be taken back.",
                "python scripts/whatholdsup/publish.py announce %s --yes" % slug)
    return ("nothing — published and announced.", "")


def cmd_next(args) -> int:
    what, how = next_action(args.slug)
    print()
    print("  next: %s" % what)
    if how:
        print()
        print("      %s" % how)
        print()
    return 0


def cmd_run(args) -> int:
    """Walk the chain, doing everything reversible, stopping before anything not.

    The two irreversible acts — pushing the site live and sending to a list —
    are never performed here however clear the path looks. They cannot be taken
    back, so they stay something a human types.
    """
    for _ in range(6):
        what, how = next_action(args.slug)
        if what.startswith(("PUBLISH", "ANNOUNCE", "nothing")):
            print()
            print("  stopping here: %s" % what)
            if how:
                print()
                print("      %s" % how)
                print()
            return 0
        if not how.startswith("python scripts/signal/factcheck_draft.py"):
            print()
            print("  stopping here: %s" % what)
            print()
            print("      %s" % how)
            print()
            return 1
        if not args.yes:
            print()
            print("  next step spends API calls: %s" % what)
            print()
            print("      %s" % how)
            print()
            print("  Re-run with --yes to let it work through the gates.")
            print()
            return 0
        print()
        print(">>> %s" % what)
        if subprocess.run(how.split(), cwd=ROOT / "backend").returncode != 0:
            print()
            print("  the gate blocked. Read it, fix or record, then run again.")
            print()
            return 1
    print()
    print("  six steps without reaching a decision point — stopping rather than looping.")
    return 1


DASH_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What Holds Up &mdash; publication board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;600&family=Karla:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--paper:#F1F2F0;--card:#FBFBFA;--card-2:#E7E9E6;--ink:#15181A;--ink-2:#4C545A;
--ink-3:#7C858B;--rule:#CFD3CE;--rule-soft:#E0E3DF;--accent:#2C4A63;--accent-bg:#E3E9EE;
--holds:#2E6E52;--partly:#9A6C1C;--nope:#9B3B32;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--paper:#14171A;--card:#1B1F23;--card-2:#23282D;--ink:#E9ECEA;--ink-2:#AFB8BD;
--ink-3:#7B858C;--rule:#333A40;--rule-soft:#262C31;--accent:#8FB4D0;--accent-bg:#1C2A36;
--holds:#6CB795;--partly:#D2A15A;--nope:#D9827A;}}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:0 1.25rem 4rem;
font:400 16px/1.6 Karla,system-ui,-apple-system,sans-serif}
.wrap{max-width:50rem;margin:0 auto}
header.top{padding:3rem 0 1.5rem;border-bottom:1px solid var(--rule)}
h1{font:600 2rem/1.15 Bitter,Georgia,serif;margin:0 0 .5rem;letter-spacing:-.015em}
.mono{font:400 .82rem/1.5 "IBM Plex Mono",ui-monospace,monospace;color:var(--ink-3)}
.eyebrow{font:500 .7rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.12em;
text-transform:uppercase;color:var(--ink-3)}
.issue{margin-top:2.75rem}
.issue>header{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;
border-bottom:1px solid var(--rule);padding-bottom:.6rem}
.issue h2{font:600 1.3rem/1.2 Bitter,Georgia,serif;margin:.3rem 0 0}
.count{font:500 .85rem/1 "IBM Plex Mono",ui-monospace,monospace;color:var(--ink-3);
font-variant-numeric:tabular-nums;white-space:nowrap}
.nextup{background:var(--accent-bg);border:1px solid var(--rule-soft);border-radius:3px;
padding:1rem 1.2rem;margin:1.1rem 0 .8rem}
.nextup .kicker{font:500 .68rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent);display:block;margin-bottom:.5rem}
.nextup p{margin:0 0 .7rem;font-weight:500}
.nextup p:last-child{margin-bottom:0}
code{display:block;font:400 .78rem/1.5 "IBM Plex Mono",ui-monospace,monospace;
background:var(--card-2);color:var(--ink-2);padding:.5rem .7rem;border-radius:2px;
margin-top:.5rem;white-space:pre-wrap;overflow-wrap:anywhere}
.cmd{position:relative}
.cmd button{position:absolute;top:.35rem;right:.35rem;font:500 .62rem/1 "IBM Plex Mono",
ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
padding:.28rem .5rem;border:1px solid var(--rule);border-radius:2px;
background:var(--card);color:var(--ink-3)}
.cmd button:hover{color:var(--ink);border-color:var(--ink-3)}
.livestate{font:400 .85rem/1.5 "IBM Plex Mono",ui-monospace,monospace;margin:0 0 1.2rem}
.livestate.done{color:var(--holds)}.livestate.warn{color:var(--partly)}
.livestate.blocked{color:var(--nope)}
ol.steps{list-style:none;margin:0;padding:0;display:grid;gap:.35rem}
li.step{display:grid;grid-template-columns:auto 1fr;gap:.85rem;align-items:start;
padding:.7rem .9rem;background:var(--card);border:1px solid var(--rule-soft);border-radius:3px}
li.step .dot{width:.7rem;height:.7rem;border-radius:50%%;margin-top:.42rem;
background:var(--card-2);border:1.5px solid var(--ink-3)}
li.step.done .dot{background:var(--holds);border-color:var(--holds)}
li.step.blocked .dot{background:var(--nope);border-color:var(--nope)}
li.step.warn .dot{background:var(--partly);border-color:var(--partly)}
li.step.done{background:transparent;border-color:transparent}
li.step.done b{color:var(--ink-3)}
li.step b{display:block;font-weight:600}
.detail{display:block;font:400 .85rem/1.5 "IBM Plex Mono",ui-monospace,monospace;
color:var(--ink-2);margin-top:.15rem;overflow-wrap:anywhere}
.why{display:block;font-size:.87rem;color:var(--ink-3);margin-top:.2rem}
ul.finds{list-style:none;margin:.6rem 0 0;padding:0;display:grid;gap:.3rem}
li.f{font:400 .84rem/1.45 Karla,system-ui,sans-serif;padding:.45rem .6rem;
border-left:2px solid var(--rule);background:var(--card-2);border-radius:2px}
li.f b{display:block;font:500 .7rem/1.4 "IBM Plex Mono",ui-monospace,monospace;
letter-spacing:.06em;text-transform:uppercase;margin-bottom:.15rem}
li.f span{color:var(--ink-2);overflow-wrap:anywhere}
li.f.settled{border-left-color:var(--accent);opacity:.72}
li.f.settled b{color:var(--accent)}
details.more{margin-top:.5rem}
details.more summary{cursor:pointer;font:500 .68rem/1 "IBM Plex Mono",ui-monospace,monospace;
letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);padding:.2rem 0}
details.more[open] summary{margin-bottom:.4rem}
li.f.bad{border-left-color:var(--nope)}li.f.bad b{color:var(--nope)}
li.f.gone{border-left-color:var(--holds)}li.f.gone b{color:var(--holds)}
li.f.tool{border-left-color:var(--partly)}li.f.tool b{color:var(--partly)}
li.f.note b{color:var(--ink-3)}
footer{margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--rule);
font-size:.87rem;color:var(--ink-3)}
</style></head><body><div class="wrap">
<header class="top">
<span class="eyebrow">What Holds Up &middot; internal</span>
<h1>Publication board</h1>
<p class="mono">Generated %(when)s from live state &mdash; gate reports, the publication
record, the review archive, and the site itself. A snapshot: it is baked into the
route at generation time, so regenerate it after anything below changes.</p>
</header>
%(issues)s
<section class="issue"><header><div><span class="eyebrow">not yet built</span>
<h2>Subscriptions</h2></div></header>
<p class="why" style="margin-top:1rem">Counts, growth, unsubscribes and the changelog's
last run belong here. Deliberately absent until the changelog delivers something:
a number on a board is not a working product, and a board full of numbers about a
thing that has never run would be worse than an empty section.</p></section>
<script>
document.addEventListener("click", function (e) {
  var b = e.target.closest("button.copy");
  if (!b) return;
  var c = b.parentNode.querySelector("code");
  if (!c || !navigator.clipboard) return;
  navigator.clipboard.writeText(c.textContent).then(function () {
    b.textContent = "copied";
    setTimeout(function () { b.textContent = "copy"; }, 1200);
  });
});
</script>
<footer>Regenerate with <code style="display:inline;padding:.15rem .35rem">python
scripts/whatholdsup/publish.py dashboard</code>. It reads state, never changes it.</footer>
</div></body></html>"""


# The publication process as a board rather than a sequence of commands to
# remember. Generated fresh on every run from the same functions the CLI uses,
# so it cannot drift from what `check` and `next` say — there is one source of
# truth and this is a rendering of it.
#
# Written to backend/data/, never to site/. It will carry subscriber counts, and
# a page at /admin on a static host protects nothing. The rule from the day
# send_broadcast.py was found being served at a public URL: a directory is not
# an access policy.

DASHBOARD = ROOT / "backend" / "data" / "whatholdsup" / "dashboard.html"

STEPS = [
    ("Draft", "The assessment and the email exist."),
    ("Gate the assessment", "Five adversarial roles. Blocks on fact, contradiction and unevidenced claims about third parties; records phrasing."),
    ("Gate the email", "The same, on the summary that reaches inboxes. It cannot be recalled once sent."),
    ("Outside review", "An independent reader, given the assessment and the standards, and neither our findings nor our adjudication."),
    ("Adjudicate", "We read the review together and decide. Every rejection goes on the record with a reason."),
    ("Publish the site", "Commits, pushes, and waits for the deploy to actually serve it before recording anything."),
    ("Announce", "The broadcast. Refuses if the site is behind the repo, so nobody follows a link to something older than their email."),
]


def _step_states(slug: str) -> list[dict]:
    cfg = ISSUES[slug]
    page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]
    rec = [r for r in load_record() if r["issue"] == slug]
    out = []

    def add(name, why, state, detail, cmd="", finds=None):
        out.append({"name": name, "why": why, "state": state, "detail": detail,
                    "cmd": cmd, "finds": finds or [], "fold": ""})

    add(*STEPS[0], "done" if page.exists() and ehtml.exists() else "blocked",
        "assessment and email present" if page.exists() and ehtml.exists() else "missing")

    for (name, why), f, rel, which in ((STEPS[1], page, cfg["page"], "assessment"),
                                       (STEPS[2], ehtml, cfg["email_html"], "email")):
        g = gate_state(f, slug)
        since = (" --since ../%s.gate.json" % rel
                 if f.with_suffix(f.suffix + ".gate.json").exists() else "")
        # A stale run whose findings are all gone has already answered the
        # question. Sending someone to re-run it is the expensive answer, and
        # it is the one this board used to give.
        if g["exists"] and not g["fresh"] and not g["outstanding"]:
            cmd = ('python scripts/whatholdsup/publish.py accept-gate %s --file %s '
                   '--reason "..."' % (slug, which))
        else:
            cmd = ("python scripts/signal/factcheck_draft.py ../%s%s --report ../%s.gate.json"
                   % (rel, since, rel))
        st = out.__len__()
        add(name, why, {OK: "done", WARN: "warn", BAD: "blocked"}[g["state"]],
            g["detail"], cmd, finds=_finding_rows(g))
        srows = _settled_rows(g)
        out[st]["fold"] = _fold(srows, "%d already dealt with" % len(srows)) if srows else ""

    st, detail = outside_review(page, slug)
    add(*STEPS[3], {OK: "done", WARN: "warn", BAD: "blocked"}[st], detail,
        "python scripts/whatholdsup/publish.py send-for-review %s" % slug)

    case = case_dir(slug)
    adj = sorted((case / "review").glob("*-adjudication.md")) if case else []
    add(*STEPS[4], "done" if st == OK else "pending",
        ("%s on file" % adj[-1].name) if adj else "no adjudication recorded",
        "python scripts/whatholdsup/publish.py review %s --reviewer NAME --findings N --accepted M" % slug)

    pub = [r for r in rec if r["action"] == "publish"]
    add(*STEPS[5], "done" if pub else "pending",
        ("published %s" % pub[-1]["at"][:10]) if pub else "not published",
        "python scripts/whatholdsup/publish.py publish %s --yes" % slug)

    ann = [r for r in rec if r["action"] == "announce"]
    add(*STEPS[6], "done" if ann else "pending",
        ("sent %s" % ann[-1]["at"][:10]) if ann else "not sent",
        "python scripts/whatholdsup/publish.py announce %s --yes" % slug)
    return out


def _esc(t) -> str:
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _fold(rows: list[dict], label: str) -> str:
    if not rows:
        return ""
    return ('<details class="more"><summary>%s</summary><ul class="finds">%s</ul></details>'
            % (_esc(label),
               "".join('<li class="f %s"><b>%s</b><span>%s</span></li>'
                       % (_esc(x["tone"]), _esc(x["head"]), _esc(x["text"])) for x in rows)))


def _finding_rows(g: dict) -> list[dict]:
    """What the run found, in the order a person needs it.

    Outstanding first, because that is the only part that stops anything.
    Resolved next, because it is the evidence that a stale report is stale.
    Instrument flags recolour a row rather than adding one: the finding and the
    reason to doubt it belong in the same place, or the doubt gets lost.
    """
    """Open items in full; everything already dealt with behind one fold.

    A board that shows twelve findings when five need a decision is a board that
    gets skimmed. The seven that are gone or already judged are evidence, not
    work, and evidence belongs one click away.
    """
    rows = []
    for f in (g.get("outstanding") or []):
        head = "%s%s \u2014 %s" % (f["class"], (" " + f["id"]) if f["id"] else "",
                                   WHERE.get(f["where"], ""))
        body = (f["why"] or f["quote"] or "").strip()
        for cls, why in f["flags"]:
            body += "   [recorded defect %s: %s]" % (cls, why)
        rows.append({"tone": "tool" if f["flags"] else "bad", "head": head,
                     "text": body[:420]})
    for n in g.get("notes") or []:
        rows.append({"tone": "bad", "head": "report inconsistency", "text": n})
    return rows


def _settled_rows(g: dict) -> list[dict]:
    rows = []
    for f in (g.get("settled") or []):
        rows.append({"tone": "settled",
                     "head": "%s %s \u2014 decided" % (f["class"], f["id"]),
                     "text": (f["decision"] or "recorded in draft_decisions.json")})
    for f in (g.get("resolved") or []):
        rows.append({"tone": "gone", "head": "%s %s \u2014 gone from the text" % (f["class"], f["id"]),
                     "text": (f["quote"] or f["why"] or "")[:160]})
    if g.get("calibration"):
        rows.append({"tone": "note", "head": "%d calibration note(s)" % g["calibration"],
                     "text": "Phrasing and framing. Recorded, published, never blocking."})
    return rows


def _cmd(c: str) -> str:
    return ('<div class="cmd"><code>%s</code><button class="copy">copy</button></div>'
            % _esc(c)) if c else ""


def _row(s: dict) -> str:
    finds = "".join('<li class="f %s"><b>%s</b><span>%s</span></li>'
                    % (_esc(x["tone"]), _esc(x["head"]), _esc(x["text"]))
                    for x in (s.get("finds") or []))
    return ('<li class="step %s"><div class="dot"></div><div>'
            '<b>%s</b><span class="detail">%s</span><span class="why">%s</span>%s%s%s'
            '</div></li>'
            % (s["state"], _esc(s["name"]), _esc(s["detail"]), _esc(s["why"]),
               ('<ul class="finds">%s</ul>' % finds) if finds else "",
               s.get("fold", ""),
               _cmd(s["cmd"]) if s["state"] != "done" and s["cmd"] else ""))



ADMIN_ROUTE = ROOT / "site" / "whatholdsup" / "api" / "admin.js"

ADMIN_JS = """// The publication board, behind a password.
//
// WHY THE BOARD IS EMBEDDED IN THE FUNCTION
// -----------------------------------------
// A static file under site/ is served at its own URL whether or not anything
// links to it, so putting the board there and guarding a different route would
// guard nothing. Files under api/ are functions, not static assets. Generating
// this file with the board inlined means there is exactly one path to the
// content and it runs through the check below.
//
// Regenerate with:  python scripts/whatholdsup/publish.py dashboard --web
// It is a snapshot at generation time, which is honest: the board reads gate
// reports and a publication record that live in the repo, and a serverless
// function cannot see those.
//
// WHY BASIC AUTH AND NOT A LOGIN PAGE
// -----------------------------------
// One operator, one secret, no session to store and nothing to get wrong.
// Comparison is constant-time. If ADMIN_PASSWORD is unset the route serves
// nothing at all rather than defaulting open — the failure mode of a guard
// that quietly stops guarding is worse than one that is plainly broken.

const crypto = require("crypto");

const BOARD = %(board)s;

function ok(header, expected) {
  if (!header || !header.startsWith("Basic ")) return false;
  let decoded = "";
  try {
    decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  } catch { return false; }
  const given = decoded.slice(decoded.indexOf(":") + 1);
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = function handler(req, res) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
    console.error("ADMIN_PASSWORD is not set; refusing to serve the board.");
    res.status(500).send("Not configured.");
    return;
  }
  if (!ok(req.headers.authorization, expected)) {
    res.setHeader("WWW-Authenticate", 'Basic realm="What Holds Up", charset="UTF-8"');
    res.status(401).send("Authentication required.");
    return;
  }
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  // Never cached anywhere but the reader's own tab: this is operational state,
  // and a CDN copy of it would outlive the password check.
  res.setHeader("Cache-Control", "no-store, private");
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  res.status(200).send(BOARD);
};
"""

def cmd_dashboard(args) -> int:
    parts = []
    for slug in sorted(ISSUES):
        cfg = ISSUES[slug]
        steps = _step_states(slug)
        what, how = next_action(slug)
        done = sum(1 for s in steps if s["state"] == "done")
        body = live_body(cfg["url"])
        page = ROOT / cfg["page"]
        if body is None:
            live = ("warn", "could not reach the site")
        elif hashlib.sha256(body.encode()).hexdigest() == sha(page):
            live = ("done", "live matches the repo")
        else:
            live = ("blocked", "live is behind the repo")

        rows = "".join(_row(s) for s in steps)

        parts.append(
            '<section class="issue"><header><div>'
            '<span class="eyebrow">%s &middot; %s</span><h2>%s</h2></div>'
            '<span class="count">%d / %d</span></header>'
            '<div class="nextup"><span class="kicker">Next</span><p>%s</p>%s</div>'
            '<p class="livestate %s">%s</p>'
            '<ol class="steps">%s</ol></section>'
            % (_esc(slug), _esc(cfg.get("number", "")), _esc(cfg["title"]),
               done, len(steps), _esc(what),
               _cmd(how) if how else "",
               live[0], _esc(live[1]), rows))

    html = DASH_TEMPLATE % {
        "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "issues": "".join(parts),
    }
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(html, encoding="utf-8")

    if args.web:
        ADMIN_ROUTE.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_ROUTE.write_text(ADMIN_JS % {"board": json.dumps(html)}, encoding="utf-8")
        print()
        print("  %s" % ADMIN_ROUTE.relative_to(ROOT))
        print("  -> https://whatholdsup.org/api/admin, behind ADMIN_PASSWORD")
    print()
    print("  %s" % DASHBOARD)
    print()
    print("  Regenerate any time; it reads live state. The copy under backend/data")
    print("  is local. The copy at /api/admin is served, behind ADMIN_PASSWORD, and")
    print("  is a snapshot — it is only as current as the last --web run.")
    print()
    return 0


def cmd_gate_status(args) -> int:
    """Everything the last gate run says, without spending another one.

    The runs cost money and stopped buying findings some time ago. What they
    already produced had never been read past a boolean. This reads it.
    """
    cfg = ISSUES[args.slug]
    for label, f in (("assessment", ROOT / cfg["page"]), ("email", ROOT / cfg["email_html"])):
        g = gate_state(f, args.slug)
        print()
        print("  %s  %s" % (label.upper(), f.name))
        print("  %s" % ("-" * (len(label) + len(f.name) + 2)))
        print("    state      %s" % {OK: "ok", WARN: "warn", BAD: "STOP"}[g["state"]])
        print("    %s" % g["detail"])
        if g["exists"]:
            print("    report sha %s" % (g.get("recorded_sha") or "?")[:16])
            print("    file sha   %s%s" % (g.get("current_sha", "?")[:16],
                                           "" if g["fresh"] else "   <- differs"))
        for tone, group in (("open", g["outstanding"]), ("done", g["resolved"])):
            for x in group:
                print()
                print("    [%s] %s %s -- %s"
                      % (tone, x["class"], x["id"], WHERE.get(x["where"], x["where"])))
                q = (x["quote"] or "").strip().replace("\n", " ")
                if q:
                    print("      quote  %s" % q[:150])
                if x["why"]:
                    print("      why    %s" % x["why"].strip()[:220])
                for cls, why in x["flags"]:
                    print("      DEFECT %s -- %s" % (cls, why[:150]))
        if g["calibration"]:
            print()
            print("    %d calibration note(s) -- recorded, published, never blocking"
                  % g["calibration"])
        for n in g["notes"]:
            print("    !! %s" % n)
    print()
    return 0


def cmd_accept_gate(args) -> int:
    """Record a decision to proceed on a stale gate whose findings are all gone.

    Not a pass and not a waiver. A waiver publishes past a check that failed;
    this is the narrower case where the check failed against text that no longer
    exists and every finding it raised has been verified out of the file. It is
    bound to the sha, so the next edit voids it, and it carries a name and a
    reason because an acceptance nobody signed is just a default with paperwork.
    """
    cfg = ISSUES[args.slug]
    f = ROOT / (cfg["page"] if args.file == "assessment" else cfg["email_html"])
    g = gate_state(f, args.slug)
    if not g["exists"]:
        print("\n  %s has never been gated. Accepting nothing is not a decision.\n" % f.name)
        return 2
    if g["fresh"]:
        print("\n  The report already describes this exact text. Nothing to accept:")
        print("  %s\n" % g["detail"])
        return 2
    named = {t.strip() for t in (args.despite or "").split(",") if t.strip()}
    open_ids = {x["id"] for x in g["outstanding"]}
    unnamed = open_ids - named
    if unnamed:
        print("\n  %d finding(s) from that run are not resolved in the current text."
              % len(g["outstanding"]))
        print("  Fix them, re-run the gate, or name each one you are accepting past")
        print("  with --despite. Naming them is the point: a blanket override records")
        print("  a decision without recording what was decided.\n")
        for x in g["outstanding"]:
            mark = "named" if x["id"] in named else "     "
            print("    [%s] %-4s %-14s %s -- %s"
                  % (mark, x["id"], x["class"], WHERE.get(x["where"], ""),
                     (x["why"] or x["quote"] or "")[:100]))
        print()
        print("    --despite %s" % ",".join(sorted(open_ids)))
        print()
        return 2
    stray = named - open_ids
    if stray:
        print("\n  --despite names %s, which is not open on this run. Check the ids"
              % ", ".join(sorted(stray)))
        print("  with gate-status before accepting past anything.\n")
        return 2
    fp = acceptance_file(args.slug)
    if fp is None:
        print("\n  no case directory for %s\n" % args.slug)
        return 2
    rows = []
    if fp.exists():
        try:
            rows = json.loads(fp.read_text()).get("acceptances", [])
        except Exception:
            rows = []
    rows.append({
        "file": f.name,
        "sha": g["current_sha"],
        "gate_report_sha": g.get("recorded_sha", ""),
        "gate_checked_at": g.get("checked_at", ""),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "by": args.by,
        "reason": args.reason,
        "findings_in_that_run": len(g["blocking"]),
        "verified_gone": len(g["resolved"]),
        "accepted_despite": sorted(named),
    })
    fp.write_text(json.dumps({
        "what_this_is": "Decisions to proceed on a gate run that judged an earlier "
                        "version of the file, taken only where every blocking finding "
                        "from that run was verified absent from the current text. Bound "
                        "to the content hash, so the next edit voids the acceptance.",
        "acceptances": rows,
    }, indent=2), encoding="utf-8")
    print("\n  Accepted: %s, %d finding(s) from the %s run, %d verified gone%s."
          % (f.name, len(g["blocking"]), g.get("checked_at", "?"), len(g["resolved"]),
             ", %d accepted past: %s" % (len(named), ", ".join(sorted(named))) if named else ""))
    print("  Bound to sha %s. Any edit to the file voids it.\n" % g["current_sha"][:16])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="what is published, and is it still what we meant").set_defaults(fn=cmd_status)
    sub.add_parser("log", help="every publication and send, in order").set_defaults(fn=cmd_log)
    sub.add_parser("register", help="regenerate issue-register.csv from the case files").set_defaults(fn=cmd_register)
    db = sub.add_parser("dashboard", help="write the publication board")
    db.add_argument("--web", action="store_true",
                    help="also regenerate the password-protected route at /api/admin")
    db.set_defaults(fn=cmd_dashboard)
    nx = sub.add_parser("next", help="what is the single next action for this issue")
    nx.add_argument("slug", choices=sorted(ISSUES))
    nx.set_defaults(fn=cmd_next)
    rn = sub.add_parser("run", help="walk the chain, stopping before anything irreversible")
    rn.add_argument("slug", choices=sorted(ISSUES))
    rn.add_argument("--yes", action="store_true", help="let it spend API calls on gate runs")
    rn.set_defaults(fn=cmd_run)
    rn.set_defaults(fn=cmd_run)
    sfr = sub.add_parser("send-for-review",
                         help="snapshot the assessment and prepare the adjudication file")
    sfr.add_argument("slug", choices=sorted(ISSUES))
    sfr.set_defaults(fn=cmd_send_for_review)

    r = sub.add_parser("review", help="record an outside review and its adjudication")
    r.add_argument("slug", choices=sorted(ISSUES))
    r.add_argument("--reviewer", required=True, help="who or what reviewed it")
    r.add_argument("--findings", type=int, required=True, help="how many findings it returned")
    r.add_argument("--accepted", type=int, required=True, help="how many we acted on")
    r.add_argument("--note", help="one line on what the review changed")
    r.set_defaults(fn=cmd_review)

    for name, fn, helptext in (("check", cmd_check, "run the preflight and stop"),
                               ("publish", cmd_publish, "preflight, push, wait for live, record"),
                               ("announce", cmd_announce, "preflight the email and record the send")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug", choices=sorted(ISSUES))
        p.add_argument("--yes", action="store_true", help="actually do it")
        p.add_argument("--waive", metavar="REASON",
                       help="Publish despite blocking preflight items. Requires a reason, "
                            "which is written into the publication record beside what was "
                            "waived. Use it when a check has stopped buying anything, not "
                            "when it is inconvenient.")
        p.set_defaults(fn=fn)
    gs = sub.add_parser("gate-status",
                        help="read what the last gate run found, without running one")
    gs.add_argument("slug", choices=sorted(ISSUES))
    gs.set_defaults(fn=cmd_gate_status)

    ag = sub.add_parser("accept-gate",
                        help="record a decision to proceed on a stale gate whose "
                             "findings are all verified gone from the current text")
    ag.add_argument("slug", choices=sorted(ISSUES))
    ag.add_argument("--file", choices=("assessment", "email"), required=True)
    ag.add_argument("--reason", required=True,
                    help="why proceeding is right, in one line, on the record")
    ag.add_argument("--by", default=os.environ.get("USER") or "operator",
                    help="who is deciding")
    ag.add_argument("--despite", metavar="IDS",
                    help="comma-separated finding ids being accepted past, from "
                         "gate-status. Each must be dispositioned somewhere a reader "
                         "can find it: the adjudication file, or draft_decisions.json.")
    ag.set_defaults(fn=cmd_accept_gate)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
