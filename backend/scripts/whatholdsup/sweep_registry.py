#!/usr/bin/env python3
"""
What Holds Up: the registry sweep — watching the trial records a page cites.

WHY THIS EXISTS
---------------
The citation sweep (sweep_sources.py) asks one question — who cited this, in
Europe PMC — and on 2026-09-11 it reached 8 of melanoma's 30 sources and 13
of cdk46's 26. It cannot see a registry record change, and registry records
are where melanoma's central claim will be falsified: the page says INTerpath-
001's record "carries no posted results at all", that "its record has not been
updated since 24 September 2025", and that KEYNOTE-054's overall survival is
NOT_POSTED with a posting date anticipated for November 2026. Every one of
those is a structured field on ClinicalTrials.gov, and until this file nothing
we owned re-read any of them after the day they were typed. Nine registry
sources across two issues were unwatched.

WHAT THIS DOES
--------------
For every source whose held URL literally carries an NCT id, one free GET to
the ClinicalTrials.gov v2 API, capturing a fixed set of fields:

    status          overallStatus, statusVerifiedDate, lastUpdatePostDate,
                    primaryCompletionDate (+type), completionDate (+type)
    results         hasResults, resultsFirstPostDate, and EVERY outcome
                    measure's title, type, reportingStatus and
                    anticipatedPostingDate
    identity        briefTitle and officialTitle, compared with ours
    version         derivedSection.miscInfoModule.versionHolder

OUTCOME GRANULARITY IS NOT OPTIONAL. hasResults is true for KEYNOTE-054 while
its overall-survival outcome is NOT_POSTED. A watch that stopped at hasResults
would report that trial as reported and be wrong about the only thing the
melanoma page says about it. An outside reviewer already made exactly this
mistake on that page — "the reviewer had read one field and not the one that
mattered" is in the 9 September change log. This file reads the field that
matters, per outcome, every run.

THE RULES, IN THE ORDER THEY COULD GO WRONG
-------------------------------------------
  * THE NCT IN OUR HELD URL IS THE IDENTITY — the same standing as "the PMCID
    is literally in the URL we hold" for melanoma S029. It is never
    synthesised, inferred, or typed from a title. A registry-typed source with
    no NCT in its held URL is recorded UNSWEEPABLE with that reason, by name,
    every run, exactly as sweep_sources.py does. The record's own titles are
    fetched and compared with ours; a mismatch is REPORTED, never silently
    accepted, and never treated as a failure to find the record — the NCT
    found the record, and the mismatch is a fact about our title.

  * THE FIRST RUN IS A BASELINE, NOT A FINDING. A source captured for the
    first time is reported `undecidable`, never "no change": an absence you
    have never measured against is not a finding. Same rule as the truncated
    citation baselines.

  * A DIFF NAMES THE FIELD. On later runs every captured field that changed
    is reported by name with before and after. Never "changed"/"unchanged".

  * A FAILED CALL NEVER TOUCHES A GOOD BASELINE. Rule 30: a source whose call
    fails after retries is reported unresolved and its capture stands.

  * NO MODEL, NO KEY, NO COST. Deterministic. Results go to the issue's own
    sweeps.json under a "registry" key beside "citations", runs appended with
    command "registry": same shape, same file, one history.

ALARMS, printed at the top of the run and never buried:
    (a) an outcome whose reportingStatus leaves NOT_POSTED
    (b) an outcome whose anticipatedPostingDate falls within 60 days of today
        (a YYYY-MM date is read as the first of that month — the earliest day
        it could mean)
    (c) hasResults false -> true
    (d) overallStatus change
    (e) lastUpdatePostDate advancing AT ALL — the melanoma page cites that
        field directly, so a change there falsifies a printed sentence.

THE CHECK ROW (publish.py: `registry claims match the registry`)
----------------------------------------------------------------
Blocks when a claim the page makes about a registry record CONTRADICTS the
last captured state: the page says NOT_POSTED and the capture says POSTED; the
page names an anticipated posting date the record no longer carries; the page
cites a last-update date the record has moved past; the page says no results
are posted and hasResults is true; the page gives a status or a primary
completion date the record does not. A claim is read only inside a text scope
tied to exactly ONE record — the rule registry_facts.py arrived at the hard
way — and the change log is excluded, because it recounts what we believed
and is not the page believing it now.

IT NEVER BLOCKS ON AGE. A sweep that is stale, old, or has never run is Class
3 — nothing has checked this yet — and under the operator's modest-promise
ruling (issues/WHU-003-deskilling/review/2026-09-12-modest-promise-ruling.md)
the page makes no currency claim for a staleness row to enforce. With
no capture the row says "not checked" and does not block. It blocks on
contradiction, never on the calendar.

Usage:

    sweep_registry.py registry <slug>            fetch, diff, alarm, record
    sweep_registry.py status   <slug>            what was last captured; no network
    sweep_registry.py check    <slug> --page <html>   the check row, offline
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sweep_sources as S        # noqa: E402  _get, find_issue, state, ONE http path
import errata                    # noqa: E402  resolves_to_us, ONE identity test
import registry_facts as RF      # noqa: E402  scopes, date parsing, ONE scope rule
from source_ledger import body_only  # noqa: E402

ROOT = S.ROOT
CTGOV = "https://clinicaltrials.gov"
OK, BAD, WARN = "ok", "BLOCKED", "warn"
ROW = "registry claims match the registry"
NCT_RE = re.compile(r"\b(NCT\d{8})\b", re.I)
SOON_DAYS = 60

FIELDS = ",".join([
    "protocolSection.identificationModule.briefTitle",
    "protocolSection.identificationModule.officialTitle",
    "protocolSection.statusModule.overallStatus",
    "protocolSection.statusModule.statusVerifiedDate",
    "protocolSection.statusModule.lastUpdatePostDateStruct",
    "protocolSection.statusModule.primaryCompletionDateStruct",
    "protocolSection.statusModule.completionDateStruct",
    "protocolSection.statusModule.resultsFirstPostDateStruct",
    "hasResults",
    "derivedSection.miscInfoModule.versionHolder",
    "resultsSection.outcomeMeasuresModule.outcomeMeasures",
])

# Scalar fields in the flat capture, in the order they are printed. versionHolder
# is captured but kept out of the record diff: it is the registry's data-version
# date and moves every day whether or not this record does.
SCALARS = ("briefTitle", "officialTitle", "overallStatus", "statusVerifiedDate",
           "lastUpdatePostDate", "primaryCompletionDate", "primaryCompletionDateType",
           "completionDate", "completionDateType", "resultsFirstPostDate", "hasResults")


# ----------------------------------------------------------------- selection

def nct_in_url(src: dict) -> str | None:
    """The NCT literally in the URL we hold, or None. Nothing else counts."""
    m = NCT_RE.search(src.get("url") or "")
    return m.group(1).upper() if m else None


def sweepable(slug_dir: Path) -> tuple[list[tuple[dict, str]], list[tuple[dict, str]]]:
    """-> (sweepable [(src, nct)], unsweepable [(src, why)]).

    Any source with an NCT in its held URL is sweepable, whatever its type. A
    registry-TYPED source without one is the gap this list exists to show.
    Sources that are neither are not registry sources and are not listed.
    """
    doc = json.loads((slug_dir / "sources.json").read_text(encoding="utf-8"))
    rows = doc["sources"] if isinstance(doc, dict) else doc
    ok, no = [], []
    for r in rows:
        nct = nct_in_url(r)
        if nct:
            ok.append((r, nct))
        elif r.get("type") == "registry":
            no.append((r, "typed 'registry' but no NCT id appears literally in the "
                          "URL we hold (%s) — nothing is synthesised from a title"
                          % ((r.get("url") or "")[:60] or "no url")))
    return ok, no


# ------------------------------------------------------------------- capture

def fetch(nct: str) -> dict:
    """One GET, no key, retried the way sweep_sources retries. Raises on failure."""
    return S._get("/api/v2/studies/" + nct, {"fields": FIELDS}, base=CTGOV)


def _struct_date(mod: dict, key: str) -> tuple[str | None, str | None]:
    d = mod.get(key) or {}
    return d.get("date"), d.get("type")


def capture(raw: dict) -> dict:
    """The flat state this file diffs. Absent fields are None, not omitted, so
    a field that appears later is a named change rather than a silent one."""
    ps = raw.get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    st = ps.get("statusModule") or {}
    pc_date, pc_type = _struct_date(st, "primaryCompletionDateStruct")
    c_date, c_type = _struct_date(st, "completionDateStruct")
    lu_date, _ = _struct_date(st, "lastUpdatePostDateStruct")
    rf_date, _ = _struct_date(st, "resultsFirstPostDateStruct")
    outs = []
    for o in ((raw.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}) \
            .get("outcomeMeasures") or []:
        outs.append({"title": o.get("title"), "type": o.get("type"),
                     "reportingStatus": o.get("reportingStatus"),
                     "anticipatedPostingDate": o.get("anticipatedPostingDate")})
    return {
        "briefTitle": ident.get("briefTitle"),
        "officialTitle": ident.get("officialTitle"),
        "overallStatus": st.get("overallStatus"),
        "statusVerifiedDate": st.get("statusVerifiedDate"),
        "lastUpdatePostDate": lu_date,
        "primaryCompletionDate": pc_date, "primaryCompletionDateType": pc_type,
        "completionDate": c_date, "completionDateType": c_type,
        "resultsFirstPostDate": rf_date,
        "hasResults": raw.get("hasResults"),
        "versionHolder": ((raw.get("derivedSection") or {}).get("miscInfoModule") or {})
        .get("versionHolder"),
        "outcomes": outs,
    }


def _distinctive_aliases(src: dict) -> list[str]:
    """Aliases that name a trial: a digit or a hyphen in them (KEYNOTE-054,
    PALOMA-2), never an NCT and never 'the registry'."""
    return [a for a in (src.get("also_called") or [])
            if len(a) >= 6 and re.search(r"[\d-]", a) and not NCT_RE.fullmatch(a)]


def identity(src: dict, state: dict, others: list[tuple[dict, str]] | None = None) -> dict:
    """How the record's own titles relate to ours. Three answers, never two.

    The NCT in our held URL settled WHICH record; the title comparison can
    only add to that or fail to. So:

      agree         errata.resolves_to_us finds our title in the record's, or
                    the record's titles carry one of our trial names
      disagree      the record's titles carry a trial name that belongs to a
                    DIFFERENT record of ours -- the NCT resolves to somebody
                    else's trial, and that is a real finding
      inconclusive  neither: the registry titles its record by a code name
                    (LEE011 for MONALEESA-2) and ours by the trial name. The
                    identity stands on the NCT; the comparison had nothing to
                    add. Reported as such, never as a disagreement -- a check
                    that cries wolf weekly is not read on the week it is right.

    `others` is the issue's other sweepable sources [(src, nct)], for the
    disagree test.
    """
    rec_title = " ".join(x for x in (state.get("briefTitle"), state.get("officialTitle")) if x)
    low = rec_title.lower()
    base = {"identity": "the NCT is literally in the URL we hold"}
    ok, why = errata.resolves_to_us({"title": rec_title}, src)
    mine = [a for a in _distinctive_aliases(src) if a.lower() in low]
    if ok or mine:
        return {**base, "titles": "agree", "titles_agree": True,
                "why": why if ok else "the record's titles carry our trial name %s" % mine[0]}
    for other, onct in others or []:
        if other.get("id") == src.get("id"):
            continue
        hit = [a for a in _distinctive_aliases(other) if a.lower() in low]
        if hit:
            return {**base, "titles": "disagree", "titles_agree": False,
                    "why": "the record's titles carry %s, the trial name of %s (%s) -- the "
                           "NCT resolves to a different record of ours"
                           % (hit[0], other.get("id"), onct)}
    return {**base, "titles": "inconclusive", "titles_agree": False,
            "why": "identity established by the NCT; title comparison inconclusive -- the "
                   "registry titles this record %r, which carries neither our trial name "
                   "nor another's" % rec_title[:70]}


# ---------------------------------------------------------------------- diff

def _outcome_keys(outs: list[dict]) -> dict[str, dict]:
    """Outcomes keyed by type + title, duplicates numbered, so a reordered list
    is not reported as a change and a renamed one is."""
    seen: dict[str, int] = {}
    out = {}
    for o in outs:
        k = "%s: %s" % (o.get("type") or "?", (o.get("title") or "?").strip())
        seen[k] = seen.get(k, 0) + 1
        if seen[k] > 1:
            k += " [%d]" % seen[k]
        out[k] = o
    return out


def diff(before: dict, after: dict) -> list[dict]:
    """Every captured field that differs, by name, with before and after."""
    out = []
    for f in SCALARS:
        if before.get(f) != after.get(f):
            out.append({"field": f, "before": before.get(f), "after": after.get(f)})
    b, a = _outcome_keys(before.get("outcomes") or []), _outcome_keys(after.get("outcomes") or [])
    for k in sorted(set(b) | set(a)):
        if k not in b:
            out.append({"field": "outcome[%s]" % k, "before": None, "after": a[k]})
        elif k not in a:
            out.append({"field": "outcome[%s]" % k, "before": b[k], "after": None})
        else:
            for sub in ("reportingStatus", "anticipatedPostingDate"):
                if b[k].get(sub) != a[k].get(sub):
                    out.append({"field": "outcome[%s].%s" % (k, sub),
                                "before": b[k].get(sub), "after": a[k].get(sub)})
    return out


def _earliest(d: str | None) -> date | None:
    """A registry date, read as the earliest day it could mean."""
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(d, fmt).date()
        except ValueError:
            continue
    return None


def alarms(sid: str, nct: str, before: dict | None, after: dict, today: date) -> list[str]:
    """The conditions worth waking someone for. (b) needs no baseline; the
    rest compare against one and are silent on a first capture."""
    out = []
    for o in after.get("outcomes") or []:
        soon = _earliest(o.get("anticipatedPostingDate"))
        if soon and o.get("reportingStatus") == "NOT_POSTED" and \
                today <= soon <= today + timedelta(days=SOON_DAYS):
            out.append("%s %s: anticipated posting date %s is within %d days — "
                       "outcome %r" % (sid, nct, o.get("anticipatedPostingDate"),
                                       SOON_DAYS, (o.get("title") or "")[:60]))
        elif soon and o.get("reportingStatus") == "NOT_POSTED" and soon < today:
            out.append("%s %s: anticipated posting date %s has PASSED and the outcome "
                       "is still NOT_POSTED — %r" % (sid, nct, o.get("anticipatedPostingDate"),
                                                    (o.get("title") or "")[:60]))
    if before is None:
        return out
    b, a = _outcome_keys(before.get("outcomes") or []), _outcome_keys(after.get("outcomes") or [])
    for k in a:
        if k in b and b[k].get("reportingStatus") == "NOT_POSTED" \
                and a[k].get("reportingStatus") != "NOT_POSTED":
            out.append("%s %s: outcome %r left NOT_POSTED -> %s"
                       % (sid, nct, k[:70], a[k].get("reportingStatus")))
    if before.get("hasResults") is False and after.get("hasResults") is True:
        out.append("%s %s: hasResults false -> true" % (sid, nct))
    if before.get("overallStatus") != after.get("overallStatus"):
        out.append("%s %s: overallStatus %s -> %s"
                   % (sid, nct, before.get("overallStatus"), after.get("overallStatus")))
    if before.get("lastUpdatePostDate") != after.get("lastUpdatePostDate"):
        out.append("%s %s: lastUpdatePostDate %s -> %s — a page citing that date is "
                   "now wrong" % (sid, nct, before.get("lastUpdatePostDate"),
                                  after.get("lastUpdatePostDate")))
    return out


# --------------------------------------------------------------------- state

def registry_state(slug_dir: Path) -> dict:
    return S.load_state(slug_dir).get("registry") or {}


def cmd_registry(args) -> int:
    d = S.find_issue(args.slug)
    ok, no = sweepable(d)
    st = S.load_state(d)
    reg = st.setdefault("registry", {})
    today = date.today()
    tday = today.isoformat()

    print("\n  REGISTRY SWEEP — %s" % d.name)
    print("  %d source(s) with an NCT id in the URL we hold, %d registry source(s) without\n"
          % (len(ok), len(no)))

    results, all_alarms, unresolved = [], [], []
    for src, nct in ok:
        sid = src["id"]
        try:
            raw = fetch(nct)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            unresolved.append((sid, "%s: %s" % (nct, exc)))
            continue
        after = capture(raw)
        ident = identity(src, after, ok)
        prior = reg.get(sid)
        before = (prior or {}).get("state")
        changes = diff(before, after) if before else []
        version_moved = (before or {}).get("versionHolder") != after.get("versionHolder") \
            if before else False
        al = alarms(sid, nct, before, after, today)
        all_alarms.extend(al)
        results.append((sid, nct, src, after, ident, before, changes, version_moved, al))
        reg[sid] = {"nct": nct, "identity": ident, "state": after, "swept": tday,
                    "baselined": (prior or {}).get("baselined") or tday}

    if all_alarms:
        print("  ALARM — %d condition(s):" % len(all_alarms))
        for a in all_alarms:
            print("    ! %s" % a)
        print()

    for sid, nct, src, after, ident, before, changes, version_moved, _al in results:
        print("  %s  %s  %s" % (sid, nct, (src.get("title") or "")[:52]))
        print("      %s; titles %s: %s"
              % (ident["identity"],
                 {"agree": "agree", "inconclusive": "INCONCLUSIVE",
                  "disagree": "DISAGREE"}[ident["titles"]], ident["why"][:110]))
        if before is None:
            print("      FIRST CAPTURE — baseline recorded; change since is undecidable")
        elif not changes:
            print("      no captured field changed since %s" % (reg[sid].get("swept") or "?"))
        else:
            print("      %d field(s) changed:" % len(changes))
            for c in changes:
                print("        %-52s %s -> %s" % (c["field"][:52],
                                                 _short(c["before"]), _short(c["after"])))
        if version_moved:
            print("      (registry data version %s -> %s — the registry's snapshot date, "
                  "not this record)" % ((before or {}).get("versionHolder"),
                                        after.get("versionHolder")))
        print("      status %s | last update posted %s | primary completion %s (%s) | "
              "hasResults %s" % (after["overallStatus"], after["lastUpdatePostDate"],
                                 after["primaryCompletionDate"],
                                 after["primaryCompletionDateType"], after["hasResults"]))
        not_posted = [o for o in after["outcomes"] if o.get("reportingStatus") == "NOT_POSTED"]
        posted = [o for o in after["outcomes"] if o.get("reportingStatus") == "POSTED"]
        if after["outcomes"]:
            print("      outcomes: %d posted, %d NOT_POSTED" % (len(posted), len(not_posted)))
            for o in not_posted:
                print("        NOT_POSTED  anticipated %-8s %s"
                      % (o.get("anticipatedPostingDate") or "—", (o.get("title") or "")[:60]))
        else:
            print("      outcomes: none in the record (no results section)")
        print()

    if unresolved:
        print("  COULD NOT RESOLVE — not the same as nothing to report; prior captures untouched:")
        for sid, why in unresolved:
            print("    %-6s %s" % (sid, why))
        print()
    if no:
        print("  NOT SWEEPABLE — typed 'registry', no NCT id in the held URL:")
        for src, why in no:
            print("    %-6s %s" % (src["id"], why))
        print()

    st.setdefault("runs", []).append({
        "on": tday, "command": "registry",
        "sources_queried": len(results),
        "first_capture": [r[0] for r in results if r[5] is None],
        "changes": {r[0]: r[6] for r in results if r[6]},
        "alarms": all_alarms,
        "titles_disagree": [r[0] for r in results if r[4]["titles"] == "disagree"],
        "titles_inconclusive": [r[0] for r in results if r[4]["titles"] == "inconclusive"],
        "unresolved": [s for s, _ in unresolved],
        "unsweepable": [s["id"] for s, _ in no],
    })
    S.save_state(d, st)
    print("  %d record(s) captured; written to %s\n"
          % (len(results), S.state_path(d).relative_to(ROOT)))
    return 0


def _short(v) -> str:
    s = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
    return s if len(s) <= 40 else s[:37] + "..."


def cmd_status(args) -> int:
    d = S.find_issue(args.slug)
    reg = registry_state(d)
    print("\n  REGISTRY CAPTURE — %s" % d.name)
    if not reg:
        print("  nothing captured yet: run `sweep_registry.py registry %s`\n" % args.slug)
        return 0
    for sid, r in sorted(reg.items()):
        s = r.get("state") or {}
        print("  %s  %s  captured %s (baseline %s)" % (sid, r.get("nct"), r.get("swept"),
                                                     r.get("baselined")))
        print("      status %s | last update posted %s | hasResults %s | %d outcome(s), "
              "%d NOT_POSTED" % (s.get("overallStatus"), s.get("lastUpdatePostDate"),
                                 s.get("hasResults"), len(s.get("outcomes") or []),
                                 sum(1 for o in s.get("outcomes") or []
                                     if o.get("reportingStatus") == "NOT_POSTED")))
    print()
    return 0


# ----------------------------------------------------------------- the check

OUTCOME_WORDS = (
    ("overall survival", "overall survival"), ("overall-survival", "overall survival"),
    ("distant metastas", "distant metastas"), ("recurrence-free", "recurrence-free"),
    ("recurrence free", "recurrence-free"), ("progression-free", "progression-free"),
    ("progression free", "progression-free"), ("disease-free", "disease-free"),
    ("event-free", "event-free"),
)
STATUS_WORDS = [
    (r"\bactive,? not recruiting\b", "ACTIVE_NOT_RECRUITING"),
    (r"\bnot yet recruiting\b", "NOT_YET_RECRUITING"),
    (r"\benrolling by invitation\b", "ENROLLING_BY_INVITATION"),
    (r"\bterminated\b", "TERMINATED"),
    (r"\b(?:still |is |was |remains )recruiting\b", "RECRUITING"),
    (r"\b(?:is|was|remains|has been) (?:suspended)\b", "SUSPENDED"),
    (r"\b(?:is|was|remains|has been) (?:withdrawn)\b", "WITHDRAWN"),
    (r"\b(?:status is|status of|is|was|remains) completed\b", "COMPLETED"),
]
CUE = re.compile(r"\b(registry|register|clinicaltrials\.gov|record|posting|posted|"
                 r"NOT_POSTED)\b", re.I)
MONTH = r"(january|february|march|april|may|june|july|august|september|october|november|december)"
DATE_RX = r"(?:(\d{1,2})\s+)?" + MONTH + r"\s+(\d{4})"
LAST_UPDATE = re.compile(r"(?:last updated(?: on)?|not been updated since|updated since|"
                         r"last update(?:d)? (?:was|is|on|of))\s+" + DATE_RX, re.I)
NO_RESULTS = re.compile(r"\b(?:no posted results|carries no (?:posted )?results|"
                        r"no results (?:have been |are |were )?posted|"
                        r"has not posted (?:any )?results|results are not posted)\b", re.I)
NOT_POSTED = re.compile(r"\b(?:NOT_POSTED|not posted|unposted)\b", re.I)
# "neither ... has posted an overall-survival result" is a NOT_POSTED claim
# about every record the quantifier covers; "has posted" alone is POSTED.
NEITHER_POSTED = re.compile(r"\b(?:neither|none|nor|no)\b[^;:]{0,160}?\bha(?:s|ve) posted\b", re.I)
IS_POSTED = re.compile(r"\b(?:is|are|was|were|has been|have been|has|have) posted\b", re.I)
ANTICIPATED = re.compile(r"anticipated(?: posting date(?: of| for)?| in its registry record for|"
                         r" for| posting in)\s+" + DATE_RX, re.I)
# "November 2026 for KEYNOTE-054": a date bound to a record by its own clause.
# Read as an anticipated posting date only where the sentence says so.
DATE_FOR = re.compile(DATE_RX + r"\s+for\s+([^\s,;.]+)", re.I)
POSTING_CONTEXT = re.compile(r"\b(?:anticipated|posting date)\b", re.I)
PRIMARY_COMPLETION = re.compile(r"(estimated|actual)?\s*primary completion(?: date)?(?: of| is| was)?"
                                r"\s+" + DATE_RX, re.I)
# A quantifier that makes one clause a statement about every record it names.
DISTRIBUTIVE = re.compile(r"\b(?:neither|both|each|every|all|none)\b", re.I)
CLAUSE_SPLIT = re.compile(r"\s*[;:]\s*")


def _iso(m, offset=0) -> str:
    day, month, year = m.group(1 + offset), m.group(2 + offset), m.group(3 + offset)
    return RF._iso(day, month, year)


def _outcome_terms(sentence: str) -> set[str]:
    low = sentence.lower()
    return {t for w, t in OUTCOME_WORDS if w in low}


def claims_in(sentence: str) -> list[dict]:
    """Every registry assertion in one sentence. {kind, value, words, at}.
    `at` is the match's character offset, which attribution below uses."""
    out = []
    terms = _outcome_terms(sentence)
    for m in LAST_UPDATE.finditer(sentence):
        out.append({"kind": "last_update", "value": _iso(m), "words": m.group(0), "at": m.start()})
    for m in NO_RESULTS.finditer(sentence):
        out.append({"kind": "no_results", "value": False, "words": m.group(0), "at": m.start()})
    np_ = NOT_POSTED.search(sentence) or NEITHER_POSTED.search(sentence)
    if np_ and terms:
        out.append({"kind": "not_posted", "value": sorted(terms), "words": np_.group(0),
                    "at": np_.start()})
    elif terms and not np_:
        m = IS_POSTED.search(sentence)
        if m:
            out.append({"kind": "posted", "value": sorted(terms), "words": m.group(0),
                        "at": m.start()})
    seen_at = set()
    for m in ANTICIPATED.finditer(sentence):
        out.append({"kind": "anticipated", "value": _iso(m), "terms": sorted(terms),
                    "words": m.group(0), "at": m.start()})
        seen_at.add(m.start(2))
    if POSTING_CONTEXT.search(sentence):
        for m in DATE_FOR.finditer(sentence):
            if m.start(2) in seen_at:
                continue
            out.append({"kind": "anticipated", "value": _iso(m), "terms": sorted(terms),
                        "words": m.group(0).strip(), "at": m.start(), "bound_after": m.start(4)})
    for m in PRIMARY_COMPLETION.finditer(sentence):
        out.append({"kind": "primary_completion", "value": _iso(m, 1),
                    "type": (m.group(1) or "").upper() or None, "words": m.group(0),
                    "at": m.start()})
    for pat, val in STATUS_WORDS:
        m = re.search(pat, sentence, re.I)
        if m:
            out.append({"kind": "status", "value": val, "words": m.group(0), "at": m.start()})
            break
    return out


def _aliases(slug_dir: Path) -> dict[str, str]:
    """alias -> NCT for every sweepable source; only aliases distinctive enough
    to name a trial (a digit or a hyphen in them, e.g. KEYNOTE-054)."""
    ok, _ = sweepable(slug_dir)
    out = {}
    for src, nct in ok:
        for a in _distinctive_aliases(src):
            out[a] = nct
    return out


def records_named(sentence: str, aliases: dict[str, str]) -> list[tuple[int, int, str]]:
    """(start, end, nct) for every record mention, NCT or alias, in order."""
    out = []
    for m in NCT_RE.finditer(sentence):
        out.append((m.start(), m.end(), m.group(1).upper()))
    for a, nct in aliases.items():
        for m in re.finditer(r"(?<![\w-])%s(?![\w-])" % re.escape(a), sentence):
            out.append((m.start(), m.end(), nct))
    return sorted(out)


def attribute(claim: dict, sentence: str, mentions: list[tuple[int, int, str]]) -> tuple[list[str], str]:
    """Which record(s) a claim in a multi-record sentence is about.

    -> (ncts, how). Empty ncts means UNATTRIBUTED: the claim is reported and
    not checked. Nothing here guesses, and nothing falls back to "every
    record named". Four rules, strongest first:

      adjacent      "November 2026 for KEYNOTE-054": the record named
                    immediately after the claim's own words
      clause        the ;- or :-delimited clause holding the claim names
                    exactly one record
      distributive  the clause carries neither/both/each/every/all and names
                    every record in the sentence, or names none (the
                    quantifier's antecedent is then the sentence's records).
                    This is the sentence saying "each of them", not a guess.
      unattributed  anything else
    """
    ncts_all = list(dict.fromkeys(n for _s, _e, n in mentions))
    if len(ncts_all) == 1:
        return ncts_all, "the sentence names one record"
    if claim.get("bound_after") is not None:
        after = [n for s, _e, n in mentions if s >= claim["bound_after"]
                 and not sentence[claim["bound_after"]:s].strip()]
        if after:
            return [after[0]], "the record named immediately after the claim"
    # the clause holding the claim
    lo, hi = 0, len(sentence)
    for m in CLAUSE_SPLIT.finditer(sentence):
        if m.end() <= claim["at"]:
            lo = m.end()
        elif m.start() > claim["at"]:
            hi = m.start()
            break
    in_clause = list(dict.fromkeys(n for s, _e, n in mentions if lo <= s < hi))
    if len(in_clause) == 1:
        return in_clause, "the clause names one record"
    clause = sentence[lo:hi]
    if DISTRIBUTIVE.search(clause) and (not in_clause or set(in_clause) == set(ncts_all)):
        return ncts_all, "the clause says %s of them" % DISTRIBUTIVE.search(clause).group(0).lower()
    return [], "UNATTRIBUTED: the clause names %d records and no quantifier covers them" % len(in_clause)


def scoped_sentences(slug_dir: Path, page_html: str) -> list[tuple[str, list, str]]:
    """(sentence, mentions, how) for every sentence carrying a registry cue
    that names at least one record. Ties, from strongest to weakest:
      - the sentence names one or more NCTs or distinctive trial aliases;
      - the sentence names none, but sits in a block naming exactly one NCT
        (the block's record is then the sentence's).
    A sentence naming N records is checked against all N; attribute() binds
    each claim to the record its own clause names, or reports it UNATTRIBUTED.
    The change log is stripped first: it recounts what we believed."""
    aliases = _aliases(slug_dir)
    out, seen = [], set()
    for block in RF.blocks(body_only(page_html)):
        block_ncts = {n.upper() for n in NCT_RE.findall(block)}
        for sent in RF._SENT.split(block):
            if not CUE.search(sent):
                continue
            sent = RF.norm(sent)
            mentions = records_named(sent, aliases)
            how = "names the record(s)"
            if not mentions:
                if len(block_ncts) != 1:
                    continue
                mentions, how = [(-1, -1, next(iter(block_ncts)))], "in a block naming one NCT"
            key = (RF.norm(sent), tuple(n for _s, _e, n in mentions))
            if key not in seen:
                seen.add(key)
                out.append((sent, mentions, how))
    return out


def contradictions(claim: dict, state: dict) -> str | None:
    """The one sentence explaining how `claim` contradicts `state`, or None."""
    outs = state.get("outcomes") or []
    k = claim["kind"]
    if k == "last_update":
        rec = state.get("lastUpdatePostDate") or ""
        if not RF.date_agrees(claim["value"], rec):
            moved = rec > claim["value"][:len(rec)] if rec else False
            return ("the page cites a last-update date of %s and the record's "
                    "lastUpdatePostDate is %s%s" % (claim["value"], rec or "absent",
                                                    " — the record has moved past it"
                                                    if moved else ""))
    elif k == "no_results":
        if state.get("hasResults") is True:
            return ("the page says no results are posted and the record's hasResults "
                    "is true (results first posted %s)" % state.get("resultsFirstPostDate"))
    elif k in ("not_posted", "posted"):
        want = "NOT_POSTED" if k == "not_posted" else "POSTED"
        matched = [o for o in outs if any(t in (o.get("title") or "").lower()
                                          for t in claim["value"])]
        if not matched:
            return None   # no outcome by that name: not checkable, never a contradiction
        if not any(o.get("reportingStatus") == want for o in matched):
            got = sorted({o.get("reportingStatus") or "?" for o in matched})
            return ("the page says %s is %s and every matching outcome in the record is %s"
                    % (" / ".join(claim["value"]), want, ", ".join(got)))
    elif k == "anticipated":
        pool = [o for o in outs if o.get("reportingStatus") == "NOT_POSTED"]
        if claim.get("terms"):
            pool = [o for o in pool if any(t in (o.get("title") or "").lower()
                                           for t in claim["terms"])]
        if not pool:
            return None
        dates = sorted({o.get("anticipatedPostingDate") or "" for o in pool})
        if not any(RF.date_agrees(claim["value"], d) or RF.date_agrees(d, claim["value"])
                   for d in dates if d):
            return ("the page names an anticipated posting date of %s and the record "
                    "carries %s for %s" % (claim["value"], ", ".join(x or "none" for x in dates),
                                           " / ".join(claim.get("terms") or ["its NOT_POSTED outcomes"])))
    elif k == "primary_completion":
        rec = state.get("primaryCompletionDate") or ""
        if not RF.date_agrees(claim["value"], rec):
            return ("the page gives a primary completion date of %s and the record gives %s"
                    % (claim["value"], rec or "none"))
        if claim.get("type") and state.get("primaryCompletionDateType") \
                and claim["type"] != state["primaryCompletionDateType"]:
            return ("the page calls the primary completion date %s and the record marks it %s"
                    % (claim["type"].lower(), state["primaryCompletionDateType"].lower()))
    elif k == "status":
        if state.get("overallStatus") and claim["value"] != state["overallStatus"]:
            return ("the page says the trial is %s and the record's overallStatus is %s"
                    % (claim["value"], state["overallStatus"]))
    return None


def findings(slug_dir: Path, page_html: str) -> dict:
    """{checked, contradicted, unchecked, unattributed}: every scoped claim
    against the last capture. `contradicted` rows name the sentence AND the
    clause -- the claim's own words -- so a two-record sentence is reported by
    the half that is wrong."""
    reg = registry_state(slug_dir)
    by_nct = {r.get("nct"): r for r in reg.values() if r.get("nct")}
    checked, bad, unchecked, unattributed = [], [], [], []
    for sent, mentions, how in scoped_sentences(slug_dir, page_html):
        for c in claims_in(sent):
            ncts, bound = attribute(c, sent, mentions)
            if not ncts:
                unattributed.append({"sentence": sent, "claim": c["kind"], "words": c["words"],
                                     "why": bound})
                continue
            for nct in ncts:
                cap = by_nct.get(nct)
                row = {"nct": nct, "sentence": sent, "claim": c["kind"], "words": c["words"],
                       "how": how if len(ncts) == 1 and len(mentions) <= 1 else bound}
                if not cap:
                    unchecked.append({**row, "why": "no capture for %s" % nct})
                    continue
                row["captured"] = cap.get("swept")
                why = contradictions(c, cap.get("state") or {})
                if why:
                    bad.append({**row, "why": why})
                else:
                    checked.append(row)
    return {"checked": checked, "contradicted": bad, "unchecked": unchecked,
            "unattributed": unattributed}


def _label(slug_dir: Path, nct: str) -> str:
    """'KEYNOTE-054 (NCT02362594)' -- the trial name a reader knows, then the id."""
    ok, _ = sweepable(slug_dir)
    for src, n in ok:
        if n == nct:
            names = _distinctive_aliases(src)
            return "%s (%s)" % (names[0], nct) if names else nct
    return nct


def _outcome_class(title: str) -> str:
    low = (title or "").lower()
    for w, term in OUTCOME_WORDS:
        if w in low:
            return {"overall survival": "overall survival", "distant metastas": "DMFS",
                    "recurrence-free": "RFS", "progression-free": "PFS",
                    "disease-free": "DFS", "event-free": "EFS"}[term]
    return (title or "?")[:40]


def live_alarms(slug_dir: Path, today: date | None = None) -> list[str]:
    """What a person should know from the last capture, worded for a person.

    Two sources, both from sweeps.json: (b) is recomputed from the captured
    state against today, so the day count is live; (a), (c), (d), (e) need a
    before and an after and are taken from the latest registry run's own
    alarm list, which is the only place they exist."""
    today = today or date.today()
    reg = registry_state(slug_dir)
    out = []
    for sid, r in sorted(reg.items()):
        st = r.get("state") or {}
        soon: dict[str, list[str]] = {}
        for o in st.get("outcomes") or []:
            d = _earliest(o.get("anticipatedPostingDate"))
            if d and o.get("reportingStatus") == "NOT_POSTED" and \
                    today <= d <= today + timedelta(days=SOON_DAYS):
                soon.setdefault(o.get("anticipatedPostingDate"), []).append(_outcome_class(o.get("title")))
            elif d and o.get("reportingStatus") == "NOT_POSTED" and d < today:
                out.append("%s — %s was anticipated to post %s and is still NOT_POSTED"
                           % (_label(slug_dir, r.get("nct")), _outcome_class(o.get("title")),
                              o.get("anticipatedPostingDate")))
        for when, classes in sorted(soon.items()):
            names = list(dict.fromkeys(classes))
            out.append("%s — %s anticipated to post %s, %d days away"
                       % (_label(slug_dir, r.get("nct")), " and ".join(names), when,
                          (_earliest(when) - today).days))
    runs = [x for x in (S.load_state(slug_dir).get("runs") or []) if x.get("command") == "registry"]
    if runs:
        for a in runs[-1].get("alarms") or []:
            if "within %d days" % SOON_DAYS in a:
                continue   # recomputed above with a live day count
            out.append("%s (run of %s)" % (a, runs[-1].get("on")))
    return out


ALARM_ROW = "registry alarms"


def preflight_rows(slug: str, page_html: str) -> list[tuple[str, str, str]]:
    """Two rows. `registry claims match the registry`: BLOCKED on
    contradiction; WARN 'not checked' with no capture; never anything on age.
    `registry alarms`: WARN, never BLOCKED, naming every live alarm from the
    last capture -- a thing to know, not a false sentence -- and OK when there
    is none. Class 3 does not block: 2026-09-12-modest-promise-ruling.md."""
    try:
        d = RF.case_dir(slug)
    except SystemExit as exc:
        return [(ROW, WARN, "not checked: %s" % exc)]
    reg = registry_state(d)
    if not reg:
        return [(ROW, WARN,
                 "not checked — no registry capture in sweeps.json for this issue; "
                 "run sweep_registry.py registry %s. Nothing has compared the page's "
                 "registry claims to the records, and not checked is not passed"
                 % slug)]
    f = findings(d, page_html)
    rows = []
    if f["contradicted"]:
        rows.append((ROW, BAD,
                     "%d claim(s) on the page contradict the registry as last captured: "
                     % len(f["contradicted"])
                     + " || ".join("%s — %s — clause: %r — page: %s"
                                   % (r["nct"], r["why"], r["words"][:60], r["sentence"][:110])
                                   for r in f["contradicted"][:4])))
    else:
        swept = sorted({r.get("swept") for r in reg.values() if r.get("swept")})
        detail = ("%d claim(s) about %d record(s) agree with the capture of %s"
                  % (len(f["checked"]), len({r["nct"] for r in f["checked"]}),
                     swept[-1] if swept else "?"))
        if f["unchecked"]:
            detail += ("; %d claim(s) name a record with no capture and are NOT checked: %s"
                       % (len(f["unchecked"]), ", ".join(sorted({u["nct"] for u in f["unchecked"]}))))
        if f["unattributed"]:
            detail += ("; %d claim(s) in multi-record sentences could not be bound to one "
                       "record by their own clause and are UNATTRIBUTED, not checked: %s"
                       % (len(f["unattributed"]),
                          " || ".join("%r in: %s" % (u["words"][:40], u["sentence"][:70])
                                      for u in f["unattributed"][:3])))
        if not f["checked"] and not f["unchecked"] and not f["unattributed"]:
            detail = ("no sentence on the page makes a registry claim tied to a record; "
                      "capture of %s held" % (swept[-1] if swept else "?"))
        rows.append((ROW, OK, detail))
    al = live_alarms(d)
    rows.append((ALARM_ROW, WARN if al else OK,
                 ("%d thing(s) to know from the last capture — none makes a sentence "
                  "false, so this does not block: " % len(al)) + " || ".join(al)
                 if al else "nothing anticipated within %d days, and the last sweep "
                            "reported no change in status, results or last-update date"
                            % SOON_DAYS))
    return rows


def cmd_check(args) -> int:
    d = S.find_issue(args.slug)
    page = Path(args.page).read_text(encoding="utf-8")
    f = findings(d, page)
    print()
    for r in f["contradicted"]:
        print("  CONTRADICTED  %s  %s" % (r["nct"], r["why"]))
        print("                page (%s): %s" % (r["how"], r["sentence"][:160]))
    for r in f["checked"]:
        print("  agrees        %s  %-18s %-40s (%s)" % (r["nct"], r["claim"], r["words"][:40], r["how"]))
    for r in f["unchecked"]:
        print("  not checked   %s  %s — %s" % (r["nct"], r["why"], r["sentence"][:100]))
    for r in f["unattributed"]:
        print("  unattributed  %-18s %r — %s" % (r["claim"], r["words"][:40], r["why"]))
        print("                page: %s" % r["sentence"][:160])
    print()
    for name, state, detail in preflight_rows(S.short_slug(d), page):
        print("  %-8s %s\n           %s\n" % (state, name, detail))
    return 1 if f["contradicted"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (
            ("registry", cmd_registry, "fetch every record, diff against the capture, alarm"),
            ("status", cmd_status, "what was last captured; no network"),
            ("check", cmd_check, "the check row against a page; no network")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug")
        if name == "check":
            p.add_argument("--page", required=True)
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
