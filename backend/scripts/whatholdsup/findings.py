#!/usr/bin/env python3
"""B15 -- A FINDING IS SETTLED BY A DOCUMENT, NEVER BY THE FINDING.

WHY THIS EXISTS
---------------
MEL-11, the error of 2026-09-01: a check reported three figures as being "in
nothing we hold", and the correction notice published on a live page said they
"came from no document". Two were real. The check had qualified its verdict
precisely and printed, under every run, that a miss is not a falsehood. The
prose written about it did not.

The rule that would have stopped it was already adopted -- "WRITE THE CORRECTION
FROM THE SOURCE RECORD, NOT FROM THE FINDING", error_taxonomy.py, 2026-09-01 --
and it gated nothing, so it did not stop anything.

It is not a rare failure. Every one of these is the same shape:

  2026-08-31  a correction written from a gate finding withdrew a true sentence
              the paper actually contains (CORR-13)
  2026-08-31  "Jacot and colleagues" published from gate output; the paper is
              by Tanguy et al.
  2026-09-01  a review file here claimed a blind spot in B9 that B9 already
              reports, on one binder's say-so
  2026-09-01  an ipilimumab result nearly written into the page from the
              counterexample hunt's citation, for a paper we cannot open
  2026-09-01  the correction notice above -- the only one that reached a reader
  2026-09-02  THE GATE DID IT TOO: it reported the page's account of MLQ News
              as "contradicted" because no MLQ News article appeared in its
              search results. We hold that document. It says, verbatim, what
              the page says it says.

The last one matters most. This is not a failure of one writer being careless
with one check's output. Roles do it to each other, and a role's finding reads
like evidence because it arrives in the same shape as evidence.

THE RULE
--------
A finding may be closed only by a QUOTATION FROM A DOCUMENT WE HOLD, and the
quotation is checked -- mechanically, here -- against the bytes.

    accepted   the finding is right and the page changed. Name the source and
               the sentence in it that shows so.
    rejected   the finding is wrong. Name the source and the sentence that
               shows so. "The check could not reach it" is not a rejection;
               "we hold it and it reads as follows" is.
    judgement  neither the finding nor its rebuttal is a matter of fact. Say
               what the question is and who decided. No quotation required, and
               the count of these is printed, because a bucket with no evidence
               requirement is the one that will silently absorb everything.

WHAT THIS FORECLOSES, BY CONSTRUCTION
-------------------------------------
You cannot cite a document for an absence. There is no sentence in any paper
reading "68.8% appears nowhere". So a claim of that shape can never be settled
under this rule, and therefore can never be published as settled -- which is
exactly the outcome wanted, arrived at without anybody having to remember the
lesson. Absence about our own library is a different claim, it is B13's, and it
is recorded in deletions.json where the search itself is the evidence.

WHAT IT DOES NOT DO
-------------------
It does not check that the quotation SUPPORTS the decision -- only that it
exists, in the document named, as printed. B2's limit, one level up: presence is
not warrant. A person still has to read it. What they can no longer do is close
a finding with prose.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_store as store    # noqa: E402
import spancheck as SC          # noqa: E402
import quotations as Q          # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
DECISIONS = ("accepted", "rejected", "judgement", "attested", "moot")
# Two decisions added 2026-09-12, each with its own evidence requirement:
#   attested   the finding is about a source no automated reader may open, and
#              an operator's recorded answer in an advocate adjudication covers
#              the figure or claim. Needs `attested_by` -- "<file>:<question id>"
#              -- that resolves to an answer for THAT source (see attestations()).
#   moot       the sentence the finding attacked is gone from the page and the
#              finding was never answered. Needs `vanished` (the sentence) and
#              is recorded, not closed: the same distinction as the withdrawal
#              ruling -- a withdrawal is not an answer.


# ---------------------------------------------------------------------------
# operator attestations -- the durable state for a licence-barred source
# ---------------------------------------------------------------------------
#
# S001 (NCCN) is human_read under a licence that forbids any automated tool
# from ever reading it. Every gate run therefore re-raises findings about it
# that the operator has already answered -- c82 was raised on 31 August by a
# gate that could not see the answer given as S001-07 on 29 August -- and
# every close-out routed them back to him. The advocate adjudication files are
# already structured, dated and attributed; this reads them as the record they
# are. No new file format.
#
# THE CONSTRAINT THAT MAKES THIS SAFE: an attestation closes a finding only
# when the finding's attributed_to IS the licence-barred source whose
# adjudication carries the answer. An answer the operator read in S001 closes
# nothing about S015, however many figures they share.

_ANS = re.compile(r"^### (?P<qid>(?P<sid>S\d{3})-\d{2})\b.*?$(?P<body>.*?)(?=^### |^## |\Z)",
                  re.M | re.S)
_FIELD = re.compile(r"^(ANSWERED BY|ON|ANSWER|LOCATOR|EFFECT):\s*(.*)$", re.M)


def attestations(slug: str) -> list[dict]:
    """Every answered question in the issue's advocate adjudications:
    {qid, sid, file, by, on, answer, locator}. Unanswered or withdrawn
    questions are not attestations."""
    out = []
    d = store.case_dir(slug) / "advocate"
    if not d.exists():
        return out
    for f in sorted(d.glob("*-adjudication.md")):
        if "TEST" in f.name:
            continue
        text = f.read_text(encoding="utf-8")
        for m in _ANS.finditer(text):
            fields = {k: v.strip() for k, v in _FIELD.findall(m.group("body"))}
            if not fields.get("ANSWER") or not fields.get("ANSWERED BY"):
                continue
            out.append({"qid": m.group("qid"), "sid": m.group("sid"),
                        "file": str(f.relative_to(store.ROOT)), "by": fields["ANSWERED BY"],
                        "on": fields.get("ON", ""), "answer": fields["ANSWER"],
                        "locator": fields.get("LOCATOR", "")})
    return out


def barred_sources(slug: str) -> dict[str, dict]:
    """Sources no automated reader may open: licence-barred AND human_read."""
    return {s["id"]: s for s in store.sources(slug)
            if s.get("licence_forbids_machine_reading")
            and (s.get("access") or {}).get("state") == "human_read"}


def source_for_attribution(slug: str, attributed_to: str) -> str | None:
    """The source id a gate claim's `attributed_to` names, by exact title or
    a distinctive alias. None when it names nothing we can identify."""
    at = " ".join((attributed_to or "").split()).lower()
    if not at:
        return None
    for s in store.sources(slug):
        if " ".join((s.get("title") or "").split()).lower() == at:
            return s["id"]
    for s in store.sources(slug):
        for a in s.get("also_called") or []:
            if len(a) >= 6 and re.search(r"[\d-]", a) and a.lower() in at:
                return s["id"]
    return None


def _figure_tokens(figure: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", figure or "")


def _norm_dash(s: str) -> str:
    return s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")


def attestation_for(slug: str, claim: dict) -> dict | None:
    """The operator's answer that covers this claim, if the claim is about a
    licence-barred source and an answer for THAT source carries every figure
    token the claim does (or, for a figure-less claim, a distinctive phrase).
    Returns None -- to the operator -- otherwise."""
    sid = source_for_attribution(slug, claim.get("attributed_to") or "")
    if not sid or sid not in barred_sources(slug):
        return None
    toks = _figure_tokens(claim.get("figure") or "")
    for a in attestations(slug):
        if a["sid"] != sid:
            continue                       # the constraint: never another source
        ans = _norm_dash(a["answer"])
        if toks:
            if all(re.search(r"(?<![\d.])%s(?![\d.])" % re.escape(x), ans) for x in toks):
                return a
        else:
            fig = _norm_dash(claim.get("figure") or "")
            if fig and fig.lower() in ans.lower():
                return a
    return None
SETTLED_BY_QUOTE = ("accepted", "rejected")


def path(slug: str) -> Path:
    return store.case_dir(slug) / "gate-findings.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
            "Every blocking finding a gate run made, and the DOCUMENT that "
            "settled it. See findings.py: a finding is not evidence, and the "
            "quotation below is checked against the bytes.",
            "findings": []}


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def open_findings(report: dict) -> list[dict]:
    """Everything in a gate report that blocks: a verdict that is not VERIFIED
    or INTERNAL, a serious objection, a serious inference, a serious coverage
    contradiction."""
    out = []
    for vid, v in (report.get("verdicts") or {}).items():
        if v.get("verdict") in ("VERIFIED", "INTERNAL"):
            continue
        out.append({"id": vid, "kind": "claim", "verdict": v.get("verdict"),
                    "what": (v.get("found_value") or "")[:400]})
    for i, o in enumerate(report.get("objections") or [], 1):
        if (o.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "obj-%d" % i, "kind": "fairness",
                        "verdict": o.get("class"),
                        "what": (o.get("objection") or "")[:400]})
    for i, f in enumerate(report.get("inferences") or [], 1):
        if (f.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "inf-%d" % i, "kind": "inference",
                        "verdict": f.get("class"),
                        "what": (f.get("problem") or "")[:400]})
    cov = (report.get("coverage") or {}).get("contradictions") or []
    for i, c in enumerate(cov, 1):
        if (c.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "cov-%d" % i, "kind": "coverage",
                        "verdict": "contradicted",
                        "what": (c.get("but") or c.get("quote") or "")[:400]})
    return out


def quote_is_in_source(slug: str, sid: str, quote: str) -> tuple[bool, str]:
    if sid not in store.held(slug):
        return False, "%s is not in the library" % sid
    # every rendition the library holds of the source, primary first (S015's
    # Table 1 is a second rendition; the article HTML does not contain it)
    for f, text in SC._texts(slug, sid):
        if Q.norm(quote) in Q.norm(SC._norm(text)):
            return True, "found in %s (%s)" % (sid, f[:12])
    defective, why = SC.defective_renditions(slug, sid)
    if defective:
        return SC.UNDETERMINED, ("cannot evaluate -- rendition text layer defective, see the "
                                 "record for %s: %s" % (sid, why))
    return False, "not in %s as printed" % sid


def check(slug: str, report: dict) -> list[tuple[str, str, str]]:
    opens = open_findings(report)
    if not opens:
        return [("gate findings settled", OK, "the last run left nothing open")]
    doc = load(slug)
    have = {f.get("id"): f for f in (doc.get("findings") or [])}
    claims = {c.get("id"): c for c in (report.get("claims") or [])}
    missing, unsettled, unverified, judged, unevaluable, partly = [], [], [], [], [], []
    for f in opens:
        r = have.get(f["id"])
        if not r or r.get("decision") not in DECISIONS:
            # AUTO-CLOSE BY ATTESTATION, DURABLY. A finding about a licence-
            # barred source that an operator answer already covers is closed
            # here, written to the record with the answer's id, so the next
            # gate run does not route it back to him. Only for the barred
            # source itself (attestation_for enforces that); everything else
            # is missing and stays missing.
            a = attestation_for(slug, claims.get(f["id"], {}))
            if a:
                rec = r or {"id": f["id"], "kind": f["kind"], "gate_verdict": f["verdict"],
                            "gate_said": f["what"]}
                rec.update({"decision": "attested", "source_id": a["sid"], "quote": "",
                            "attested_by": "%s:%s" % (a["file"], a["qid"]),
                            "why": "Closed automatically 2026-09-12 or later by the operator's "
                                   "recorded answer %s (%s, %s), which carries the figure this "
                                   "finding disputes. The gate could not see it: the licence "
                                   "forbids any automated reader opening %s. ANSWER: %s"
                                   % (a["qid"], a["by"], a["on"], a["sid"], a["answer"]),
                            "by": "findings.attestation_for", "on": date.today().isoformat()})
                if not r:
                    doc.setdefault("findings", []).append(rec)
                save(slug, doc)
                continue
        if not r:
            missing.append("%s (%s)" % (f["id"], f["kind"]))
            continue
        d = r.get("decision")
        if d not in DECISIONS:
            if ((r.get("retest") or {}).get("outcome") == "partly"):
                # Revised wording, undecided claim: not a STOP. It is a
                # question for a person, and the row below asks it by name.
                partly.append("%s: %s" % (f["id"], (r.get("retest") or {}).get("result", "")))
                continue
            unsettled.append("%s: decision %r is not one of %s"
                             % (f["id"], d, ", ".join(DECISIONS)))
            continue
        if d == "judgement":
            judged.append(f["id"])
            if not (r.get("why") or "").strip() or not (r.get("by") or "").strip():
                unsettled.append("%s: a judgement needs a reason and a name"
                                 % f["id"])
            continue
        if d == "attested":
            # The durable state for a licence-barred source: the answer must
            # exist, be about the source the finding is about, and be the
            # answer named. Anything less is a judgement wearing a better name.
            qid = (r.get("attested_by") or "").strip()
            claim = claims.get(f["id"], {})
            a = attestation_for(slug, claim)
            if not qid or not a or a["qid"] != qid.split(":")[-1]:
                unsettled.append("%s: 'attested' names %r and no answer for the "
                                 "source this finding is about carries its figure"
                                 % (f["id"], qid))
            continue
        if d == "moot":
            if not (r.get("vanished") or "").strip():
                unsettled.append("%s: 'moot' must record the sentence that vanished"
                                 % f["id"])
            continue
        sid, quote = r.get("source_id"), r.get("quote") or ""
        if not sid or not quote:
            unsettled.append("%s: %r must name a source AND quote the sentence "
                             "in it that settles this" % (f["id"], d))
            continue
        ok, why = quote_is_in_source(slug, sid, quote)
        if ok is SC.UNDETERMINED:
            unevaluable.append("%s: %s" % (f["id"], why))
        elif not ok:
            unverified.append("%s: %s" % (f["id"], why))
    rows = [("gate findings settled", OK if not missing else BAD,
             "%d open finding(s), each with a decision" % len(opens)
             if not missing else
             "%d finding(s) from the last run have no decision: %s"
             % (len(missing), ", ".join(missing[:6])))]
    rows.append(("findings settled by a document", OK if not unsettled else BAD,
                 "every accepted or rejected finding names a source and a "
                 "quotation" if not unsettled else
                 "%d unsettled: %s" % (len(unsettled), " || ".join(unsettled[:3]))))
    rows.append(("those quotations are in the bytes",
                 OK if not unverified else BAD,
                 "every quotation used to settle a finding is in the document "
                 "named" if not unverified else
                 "%d quotation(s) are not: %s"
                 % (len(unverified), " || ".join(unverified[:3]))))
    if partly:
        rows.append(("findings partly still in the text", WARN,
                     "%d finding(s) whose attacked sentence was revised: the opening survives, "
                     "the rest does not. Neither live nor settled -- a disposition naming the "
                     "current sentence is required: %s" % (len(partly), " || ".join(partly[:3]))))
    if unevaluable:
        rows.append(("quotations this check cannot evaluate", WARN,
                     "%d quotation(s) settle a finding against a source whose only held "
                     "rendition has a defective text layer, declared on its record; "
                     "not verified and not failed: %s" % (len(unevaluable), " || ".join(unevaluable[:3]))))
    if judged:
        rows.append(("findings closed as judgement", WARN,
                     "%d of %d closed without a document, by name: %s — the "
                     "bucket with no evidence requirement is the one to watch"
                     % (len(judged), len(opens), ", ".join(judged[:6]))))
    return rows


def scan(slug: str, report: dict) -> dict:
    doc = load(slug)
    have = {f.get("id") for f in (doc.get("findings") or [])}
    for f in open_findings(report):
        if f["id"] in have:
            continue
        doc["findings"].append({
            "id": f["id"], "kind": f["kind"], "gate_verdict": f["verdict"],
            "gate_said": f["what"],
            "decision": "", "source_id": "", "quote": "", "why": "",
            "by": "", "on": date.today().isoformat(),
            "_fill_in": "decision: %s. accepted/rejected need source_id AND a "
                        "quote that is in that document." % ", ".join(DECISIONS),
        })
    save(slug, doc)
    return doc


# ---------------------------------------------------------------------------
# re-test: a finding whose sentence changed is re-tested, not closed on "moved"
# ---------------------------------------------------------------------------
#
# On 2026-09-12 eleven of cdk46's fifteen open findings attacked a sentence
# that had been rewritten since the gate ran, and had been queued for the
# operator as though the rewrite were the answer. It is not: a reworded
# sentence can carry the same defect, and closing on "the text moved" is how a
# real objection is dropped quietly. So each finding's OWN test is re-run
# against the current page and the held documents:
#
#   NOT_FOUND / WRONG_VALUE / WRONG_SOURCE   is the figure in the source the
#                                            claim is attributed to, now?
#                                            (held bytes; or the operator's
#                                            attestation for a barred source)
#   CONTRADICTION (inference)                is the attacked sentence still on
#                                            the page? gone -> MOOT; present ->
#                                            LIVE, and only a person can say
#                                            whether the two still conflict
#   fairness / judgement kinds               not auto-testable; to the operator
#
# Outcomes: closed by re-test (recorded as `rejected`, with the source and the
# quote that carries the figure); attested; LIVE (reported, not decided);
# MOOT (the sentence is gone and the finding was never answered -- recorded,
# not closed, the withdrawal ruling's distinction); to the operator.

TESTABLE = ("NOT_FOUND", "WRONG_VALUE", "WRONG_SOURCE")


def _page_plain(slug: str) -> str:
    import bindings as B
    import html as _html
    raw = B._page_html(slug)
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def _figure_in_source(slug: str, sid: str, figure: str) -> tuple[bool, str]:
    """Every figure token of `figure` in the held text of `sid`, and the
    shortest stretch of that text that carries them all."""
    text = SC._text(slug, sid)
    if text is None:
        return False, "%s is not in the library" % sid
    norm = SC._norm(text)
    toks = _figure_tokens(figure)
    if not toks:
        return False, "the finding names no figure to test"
    where = [re.search(r"(?<![\d.])%s(?![\d.])" % re.escape(x), norm) for x in toks]
    if not all(where):
        return False, "%s not in %s" % (", ".join(x for x, w in zip(toks, where) if not w), sid)
    lo, hi = min(m.start() for m in where), max(m.end() for m in where)
    if hi - lo > 400:
        return False, ("the figures are in %s but %d characters apart, not one "
                       "statement" % (sid, hi - lo))
    return True, norm[max(0, lo - 60):hi + 40]


def _attacked_sentence_state(quote: str, page: str) -> str:
    """'live' (the whole attacked sentence is on the page), 'gone' (not even
    its opening is), or 'partly' (its opening is and the rest is not). Three
    answers because the middle one was being reported as the first: a prefix
    match is not the sentence, and a revised sentence is exactly the case a
    finding's re-test exists to notice."""
    q = " ".join((quote or "").split())
    if not q:
        return "live"
    if q in page:
        return "live"
    if q[:80] in page:
        return "partly"
    return "gone"


def retest(slug: str, report: dict, write: bool = True) -> dict:
    """Re-test every open finding whose decision is not yet recorded.
    Returns {closed, attested, live, partly, moot, operator} lists of ids."""
    doc = load(slug)
    have = {f.get("id"): f for f in (doc.get("findings") or [])}
    claims = {c.get("id"): c for c in (report.get("claims") or [])}
    verd = report.get("verdicts") or {}
    page = _page_plain(slug)
    out = {"closed": [], "attested": [], "live": [], "partly": [], "moot": [], "operator": []}
    today = date.today().isoformat()
    for f in open_findings(report):
        rec = have.get(f["id"])
        if rec and rec.get("decision") in DECISIONS:
            continue
        if rec is None:
            rec = {"id": f["id"], "kind": f["kind"], "gate_verdict": f["verdict"],
                   "gate_said": f["what"], "decision": "", "source_id": "",
                   "quote": "", "why": "", "by": "", "on": today}
            doc.setdefault("findings", []).append(rec)
        c = claims.get(f["id"], {})
        v = verd.get(f["id"], {})
        if f["kind"] == "claim" and f["verdict"] in TESTABLE \
                and (c.get("kind") or "") in ("figure", "attribution"):
            # Only a FIGURE or an ATTRIBUTION is a string test. A
            # `characterisation` claim ("spent under an O'Brien-Fleming spending
            # function") carries a stray numeral or two, and the first run of
            # this closed c95 on finding "0.05" in S003 -- a token, not the
            # dispute. Characterisations go to the operator.
            a = attestation_for(slug, c)
            if a:
                rec.update({"decision": "attested", "source_id": a["sid"],
                            "attested_by": "%s:%s" % (a["file"], a["qid"]),
                            "why": "Re-test %s: the claim is about a licence-barred source and the "
                                   "operator's answer %s (%s) carries its figure. ANSWER: %s"
                                   % (today, a["qid"], a["on"], a["answer"]),
                            "by": "findings.retest", "on": today})
                out["attested"].append(f["id"]); continue
            sid = source_for_attribution(slug, c.get("attributed_to") or "")
            if not sid:
                rec.update({"retest": {"on": today, "outcome": "operator",
                                       "why": "the claim's attributed_to names no source the ledger can identify"}})
                out["operator"].append(f["id"]); continue
            ok, why = _figure_in_source(slug, sid, c.get("figure") or "")
            if ok:
                rec.update({"decision": "rejected", "source_id": sid, "quote": why.strip(),
                            "why": "CLOSED BY RE-TEST %s: the gate said %s; the figure %r is in the held "
                                   "bytes of %s, which the gate could not reach. Tested: every figure token "
                                   "of the claim against the held text of the source the claim is attributed to."
                                   % (today, f["verdict"], c.get("figure"), sid),
                            "by": "findings.retest", "on": today})
                out["closed"].append(f["id"]); continue
            rec.update({"retest": {"on": today, "outcome": "live", "tested": "figure %r against %s" % (c.get("figure"), sid), "result": why}})
            out["live"].append(f["id"]); continue
        if f["kind"] == "inference":
            quote = " ".join(((report.get("inferences") or [])[int(f["id"].split("-")[1]) - 1].get("quote") or "").split())
            outcome = _attacked_sentence_state(quote, page)
            if outcome == "gone":
                rec.update({"decision": "moot", "vanished": quote,
                            "why": "MOOT %s: the sentence the finding attacked is no longer on the page. "
                                   "The finding was never answered; recorded, not closed -- a withdrawal is not an answer."
                                   % today, "by": "findings.retest", "on": today})
                out["moot"].append(f["id"]); continue
            if outcome == "partly":
                # A STRING TEST STANDING IN FOR A JUDGEMENT ABOUT MEANING. The
                # opening of the attacked sentence survived and the rest did
                # not: the wording was revised. Whether the attacked CLAIM
                # survived under different words is not a string question, so
                # this is neither live nor settled. It does not block; it
                # requires a disposition that names the current sentence.
                # 13 September 2026: inf-10 sat as "live" on an 80-character
                # prefix while the page already said what the gate asked for.
                rec.update({"retest": {"on": today, "outcome": "partly",
                                       "tested": "is the attacked sentence still on the page",
                                       "result": "partly still in the text -- the attacked wording may have been "
                                                 "revised; a disposition naming the current sentence is required"}})
                out["partly"].append(f["id"]); continue
            rec.update({"retest": {"on": today, "outcome": "live", "tested": "is the attacked sentence still on the page", "result": "yes; whether the two sentences still conflict is a reading, not a string test"}})
            out["live"].append(f["id"]); continue
        if f["kind"] == "fairness":
            quote = " ".join(((report.get("objections") or [])[int(f["id"].split("-")[1]) - 1].get("quote") or "").split())
            if quote and quote[:60] not in page:
                rec.update({"decision": "moot", "vanished": quote,
                            "why": "MOOT %s: the quoted sentence is gone; the objection was never answered on the record." % today,
                            "by": "findings.retest", "on": today})
                out["moot"].append(f["id"]); continue
        rec.update({"retest": {"on": today, "outcome": "operator", "why": "kind %r / verdict %r is not a string test" % (f["kind"], f["verdict"])}})
        out["operator"].append(f["id"])
    if write:
        save(slug, doc)
    return out


def preflight_rows(slug: str, report_path: Path) -> list[tuple[str, str, str]]:
    if not report_path.exists():
        return [("gate findings settled", WARN, "no gate report to read")]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [("gate findings settled", WARN, "unreadable report: %s" % exc)]
    return check(slug, report)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--report", required=True)
    ap.add_argument("--scan", action="store_true")
    a = ap.parse_args()
    report = json.loads(Path(a.report).read_text(encoding="utf-8"))
    if a.scan:
        doc = scan(a.slug, report)
        print("\n  %d finding(s) recorded in %s\n"
              % (len(doc["findings"]), path(a.slug)))
        return 0
    print()
    for label, st, detail in check(a.slug, report):
        print("  %-7s %-34s %s" % ({OK: "ok", BAD: "STOP", WARN: "warn"}[st],
                                   label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
