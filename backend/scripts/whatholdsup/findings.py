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


def is_study(slug: str) -> bool:
    """issue.json says "study": true (protocol rev 27)."""
    try:
        return json.loads((store.case_dir(slug) / "issue.json").read_text(encoding="utf-8")).get("study") is True
    except (Exception, SystemExit):
        return False


def open_findings(report: dict) -> list[dict]:
    """Everything in a gate report that blocks: a verdict that is not VERIFIED
    or INTERNAL, a serious objection, a serious inference, a serious coverage
    contradiction. recency_findings() is added to these (_opens)."""
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


def recency_findings(report: dict) -> list[dict]:
    """Every gate recency study that is not CURRENT, UNKNOWN included (GAP-014,
    2026-10-20). The gate's prompt treats UNKNOWN as a failure, but a recency
    failure produced no finding: a warn on the same text, nothing after an edit.
    Added on every issue (_opens): on a study issue the ruling model rules it
    (ruling.py gate), on a published issue a person decides it, as every other
    gate finding. Until 2026-10-20 (evening) it was added on study issues only."""
    out = []
    for i, s in enumerate((report.get("recency") or {}).get("studies") or [], 1):
        if not isinstance(s, dict) or s.get("status") == "CURRENT":
            continue
        what = "%s is %s: the draft uses %s; the latest known is %s%s" % (
            s.get("name") or "a study", s.get("status") or "not established as current",
            s.get("draft_uses") or "?", s.get("latest_known") or "?",
            ("; what changes: %s" % s["what_changed"]) if s.get("what_changed") else "")
        out.append({"id": recency_id(report, i), "legacy_id": "rec-%d" % i, "kind": "recency",
                    "verdict": s.get("status") or "UNKNOWN", "what": what[:400],
                    "study": s.get("name") or ""})
    return out


# A RECENCY FINDING IS ABOUT THE SENTENCES THAT USE THE SOURCE (2026-10-22).
#
# The gate's recency role names a study, not a sentence. ruling.py looked the
# name up among the page's sentences, and the one that carries a study's name
# is its title line in the source list -- so on WHU-S02 the recency finding was
# ruled on the source-list line, with no bound passage, while the body
# sentences printing the study's figures went unexamined. recency_targets finds
# the one source the study names and returns every body sentence whose binding
# rests on it (its span, a premise, or also_rests_on). A source-list line is
# never a target.
#
# THE STUDY IS MATCHED TO ONE SOURCE, AUTHORS AND TITLE TOGETHER (2026-10-22,
# later). The gate writes a study as "Cuijpers, Karyotaki, Ciharova et al. --
# Psychological treatments of depression in children and adolescents: ...",
# and the page prints the entry as two lines, the authors and the title, so no
# single line named it and WHU-S02's finding was attached to nothing. Each
# candidate is now one unit: a source-list entry (its author line and title
# line together, with the source its links name) or a sources.json record (its
# authors, or the "Surname X et al. --" head of its title, with the rest of the
# title). A unit matches when
#   - its first author's surname (the family name before the first comma,
#     "et al." and initials dropped, diacritics folded) is a word of the study
#     name, and
#   - the title words overlap strongly: at least TITLE_MIN_SHARED distinctive
#     title words (not stop words, not GENERIC_TITLE words) in common, and
#     shared / min(title words, study words) >= TITLE_OVERLAP.
# The single best-scoring source is the match. No source matching, two sources
# matching equally, or a match no body sentence rests on is RECENCY_UNMATCHED:
# the finding carries no targets, ruling.py does not rule it, and the
# preflight STOPs on it, naming the study, for a person to attach.
#
# A TRIAL NAMED BY ITS ACRONYM (2026-10-22, later). The gate also writes a
# study as "the MONALEESA-2 trial", with no author. When no source's first
# author is a word of the study name, each all-caps token of the name (3 or
# more characters, uppercase letters or letters and digits, hyphen-joined
# parts allowed: "MONALEESA-2", "SPARX") is looked for as a whole word,
# case folded, in every source's text: its source-list entry (author and title
# lines) and its sources.json title and notes. A token found in exactly one
# source names it; tokens found in two or more sources name none. Exactly one
# source named that way is the match; none, or two named by different tokens,
# stays RECENCY_UNMATCHED.

RECENCY_UNMATCHED = "RECENCY_UNMATCHED"
TITLE_OVERLAP = 0.6
TITLE_MIN_SHARED = 3
GENERIC_TITLE = {"trial", "study", "review", "systematic", "meta-analysis", "metaanalysis", "meta",
                 "analysis", "effect", "effects", "effectiveness", "randomised", "randomized",
                 "controlled", "results", "outcomes", "with", "among", "their", "this", "that"}


def _fold(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.replace("—", " — ").split()).lower()


def source_list_text(slug: str) -> list[str]:
    """The plain text of each source-list entry (<div class="src">) on the
    page, tag included; [] if the page cannot be read."""
    try:
        import bindings as B
        import source_ledger as ledger
        raw = B.HEAD.sub(" ", B._page_html(slug))
    except Exception:
        return []
    return [_fold(ledger.plain(b)) for b in re.findall(r'<div class="src">(.*?)</div>', raw, re.S)]


def _entry_sources(slug: str, srcs: list[dict]) -> list[tuple[str, str, list[str]]]:
    """(author line, title line(s), the sources its links name) for each
    source-list entry: bibbind's lines, an author line and the title lines
    after it taken together."""
    try:
        import bibbind
        lines = bibbind.lines(slug)
    except Exception:
        return []
    out: list = []
    for l in lines:
        if l.get("kind") == "author" or not out:
            out.append([_fold(l["sentence"]), "", list(l.get("sources") or [])])
        else:
            out[-1][1] = (out[-1][1] + " " + _fold(l["sentence"])).strip()
    return [tuple(x) for x in out]


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9'-]{2,}", _fold(text))
            if w not in store.STOP and w not in GENERIC_TITLE}


def first_surname(authors: str) -> str:
    """The first author's family name: the text before the first comma (or
    before "et al."), initials dropped; its last word. "" if none."""
    a = _fold(authors).split(" — ")[0]
    a = re.split(r",|\bet al\b|;", a)[0]
    toks = [t for t in re.findall(r"[a-z][a-z'-]*", a)]
    while len(toks) > 1 and len(toks[-1]) <= 2:
        toks.pop()                                      # "cuijpers p", "merry sn"
    return toks[-1] if toks else ""


def _units(srcs: list[dict], entry_sources) -> list[tuple[str, str, str, str]]:
    """(source id, author text, title text, where) for every candidate."""
    out = []
    for author, title, ids in entry_sources:
        for i in ids:
            out.append((i, author, title, "source-list entry"))
    for s in srcs:
        t = s.get("title") or ""
        auth = s.get("authors") or s.get("author") or ""
        if isinstance(auth, list):
            auth = ", ".join(str(a) for a in auth)
        if not auth and " — " in t:
            auth, t = t.split(" — ", 1)
        if s.get("id"):
            out.append((s["id"], auth, t, "sources.json"))
    return out


def recency_match(study: str, srcs: list[dict], entry_sources) -> dict:
    """{"status": "matched", "source": sid, "score", "why"} or
    {"status": RECENCY_UNMATCHED, "why", "candidates"}: the one source STUDY
    names, by first author's surname and title overlap together."""
    name_words = set(re.findall(r"[a-z][a-z'-]*", _fold(study)))
    sw = _words(study)
    best: dict = {}
    units = _units(srcs, entry_sources)
    for sid, author, title, where in units:
        sur = first_surname(author)
        if not sur or sur not in name_words:
            continue
        tw = _words(title) - {sur}
        shared = tw & sw
        if not tw or not sw or len(shared) < TITLE_MIN_SHARED:
            continue
        score = len(shared) / min(len(tw), len(sw))
        if score < TITLE_OVERLAP:
            continue
        if score > best.get(sid, (0,))[0]:
            best[sid] = (score, sur, len(shared), where)
    if not best and not any(first_surname(a) in name_words for _s, a, _t, _w in units):
        return acronym_match(study, srcs, entry_sources)
    if not best:
        return {"status": RECENCY_UNMATCHED, "candidates": [],
                "why": "no source's first author and title both match the study name (surname a "
                       "word of the name; >= %d title words shared, overlap >= %.1f)"
                       % (TITLE_MIN_SHARED, TITLE_OVERLAP)}
    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
    top = ranked[0][1][0]
    tied = [sid for sid, v in ranked if v[0] == top]
    if len(tied) > 1:
        return {"status": RECENCY_UNMATCHED, "candidates": tied,
                "why": "%d sources match equally (%s, overlap %.2f)" % (len(tied), ", ".join(tied), top)}
    sid, (score, sur, n, where) = ranked[0]
    return {"status": "matched", "source": sid, "score": round(score, 3),
            "why": "first author %r and %d title words (overlap %.2f), %s" % (sur, n, score, where)}


ACRONYM = re.compile(r"(?<![A-Za-z0-9])[A-Z0-9]+(?:-[A-Z0-9]+)*(?![A-Za-z0-9])")


def acronyms(study: str) -> list[str]:
    """The all-caps tokens of a study name: 3+ characters, at least one
    letter, no lowercase letter."""
    out = []
    for m in ACRONYM.finditer(study or ""):
        tok = m.group(0)
        if len(tok.replace("-", "")) >= 3 and re.search(r"[A-Z]", tok) and tok not in out:
            out.append(tok)
    return out


def _source_texts(srcs: list[dict], entry_sources) -> dict:
    """{source id: its folded text}: source-list entry lines, sources.json
    title and notes."""
    out: dict = {}
    for author, title, ids in entry_sources:
        for i in ids:
            out[i] = (out.get(i, "") + " " + author + " " + title).strip()
    for s in srcs:
        if s.get("id"):
            extra = " ".join(str(s.get(k) or "") for k in ("title", "notes", "note"))
            out[s["id"]] = (out.get(s["id"], "") + " " + _fold(extra)).strip()
    return out


def acronym_match(study: str, srcs: list[dict], entry_sources) -> dict:
    """recency_match for a study named with no author: by a trial acronym
    found as a whole word in exactly one source."""
    toks = acronyms(study)
    if not toks:
        return {"status": RECENCY_UNMATCHED, "candidates": [],
                "why": "no source's first author is named in the study, and the name has no "
                       "all-caps trial acronym"}
    texts = _source_texts(srcs, entry_sources)
    named, seen = {}, {}
    for tok in toks:
        pat = re.compile(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(_fold(tok)))
        hits = sorted(sid for sid, txt in texts.items() if pat.search(txt))
        seen[tok] = hits
        if len(hits) == 1:
            named.setdefault(hits[0], []).append(tok)
    if len(named) == 1:
        sid, by = next(iter(named.items()))
        return {"status": "matched", "source": sid, "score": None,
                "why": "no author named; trial acronym %s found in %s alone" % (", ".join(by), sid)}
    if named:
        return {"status": RECENCY_UNMATCHED, "candidates": sorted(named),
                "why": "acronyms name different sources (%s)"
                       % "; ".join("%s: %s" % (t, ", ".join(h)) for t, h in seen.items() if h)}
    return {"status": RECENCY_UNMATCHED,
            "candidates": sorted({s for h in seen.values() for s in h}),
            "why": "no author named; acronym %s" % "; ".join(
                "%s in %s" % (t, ", ".join(h) if h else "no source") for t, h in seen.items())}


def _rests_on(row: dict, sids: set) -> bool:
    if row.get("source_id") in sids:
        return True
    return any(isinstance(x, dict) and x.get("source_id") in sids
               for k in ("premises", "also_rests_on") for x in (row.get(k) or []))


def recency_attach(slug: str, study: str, rows: dict, *, srcs: list[dict] | None = None,
                   entries: list[str] | None = None,
                   entry_sources: list | None = None) -> dict:
    """recency_match, plus the keys of every on-page body row whose binding
    rests on the matched source ("rows"). A match no body row rests on is
    RECENCY_UNMATCHED."""
    if srcs is None:
        try:
            srcs = store.sources(slug)
        except (OSError, ValueError, SystemExit):
            srcs = []
    entries = source_list_text(slug) if entries is None else entries
    entry_sources = _entry_sources(slug, srcs) if entry_sources is None else entry_sources
    m = recency_match(study, srcs, entry_sources)
    m["rows"] = []
    if m["status"] != "matched":
        return m

    def body(r):
        sent = _fold(r.get("sentence"))
        return r.get("on_page") and sent and not any(sent in e for e in entries)
    m["rows"] = [k for k, r in rows.items() if body(r) and _rests_on(r, {m["source"]})]
    if not m["rows"]:
        return {"status": RECENCY_UNMATCHED, "candidates": [m["source"]], "rows": [],
                "why": "matched %s (%s), but no body sentence's binding rests on it" % (m["source"], m["why"])}
    return m


def recency_targets(slug: str, study: str, rows: dict, **kw) -> tuple[list[str], list[str]]:
    """([the source STUDY names], the keys of every on-page body row whose
    binding rests on it), in row order; ([], []) when RECENCY_UNMATCHED.
    Never a source-list line."""
    m = recency_attach(slug, study, rows, **kw)
    return ([m["source"]], m["rows"]) if m["status"] == "matched" else ([], [])


# RECENCY IDS NAME THEIR DRAFT (2026-10-22, protocol rev 38): f<draft sha>-rec-N,
# as a --changed-since run names its claims. A gate run numbers its recency
# studies rec-1, rec-2, ... afresh, and scan() skips an id it already holds,
# so a later run's rec-1 would have read as the earlier run's, already decided.
REC_ID = re.compile(r"^(?:f[0-9a-f]{8}-)?rec-(\d+)$")


def recency_id(report: dict, i: int) -> str:
    d = (report.get("sha256") or "")[:8]
    return ("f%s-rec-%d" % (d, i)) if re.fullmatch(r"[0-9a-f]{8}", d) else "rec-%d" % i


def recency_index(fid: str) -> int | None:
    """N of rec-N or f<sha>-rec-N, else None."""
    m = REC_ID.match(fid or "")
    return int(m.group(1)) if m else None


def record_for(have: dict, f: dict) -> dict | None:
    """The record for finding F: by its id; for a recency finding, else by the
    pre-2026-10-22 id rec-N when that record is about the same text (the same
    finding, recorded before ids named their draft)."""
    r = have.get(f["id"])
    if r is None and f.get("legacy_id"):
        old = have.get(f["legacy_id"])
        if old is not None and (old.get("gate_said") or "") == (f.get("what") or ""):
            r = old
    return r


def _opens(slug: str, report: dict) -> list[dict]:
    return open_findings(report) + recency_findings(report)


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
    opens = _opens(slug, report)
    if not opens:
        return [("gate findings settled", OK, "the last run left nothing open")]
    doc = load(slug)
    have = {f.get("id"): f for f in (doc.get("findings") or [])}
    claims = {c.get("id"): c for c in (report.get("claims") or [])}
    unmatched = _unmatched_recency(slug, opens, have)
    missing, unsettled, unverified, judged, unevaluable, partly = [], [], [], [], [], []
    undecided = []
    for f in opens:
        r = record_for(have, f)
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
            if d:
                undecided.append("%s: decision %r is not one of %s"
                                 % (f["id"], d, ", ".join(DECISIONS)))
            else:
                undecided.append("%s (%s)" % (f["id"], f["kind"]))
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
    # A row that EXISTS but carries no decision is not a settled finding.
    # Before 2026-09-15 `missing` meant "no row at all", so the forty skeleton
    # rows scan() wrote made this row read "each with a decision" while the
    # forty empty strings fell through to the row below. Blocked either way;
    # the board nonetheless said something false, in the direction of
    # reassurance. Two blocking states, reported apart. See
    # tests/whatholdsup/test_findings_skeleton_not_settled.py.
    blocked = missing + undecided
    if not blocked:
        _detail = "%d open finding(s), each with a decision" % len(opens)
    else:
        _bits = []
        if missing:
            _bits.append("%d never recorded (%s)"
                         % (len(missing), ", ".join(missing[:4])))
        if undecided:
            _bits.append("%d recorded with no decision yet (%s)"
                         % (len(undecided), ", ".join(undecided[:4])))
        _detail = ("%d of %d open finding(s) carry no decision: %s"
                   % (len(blocked), len(opens), "; ".join(_bits)))
    rows = [("gate findings settled", OK if not blocked else BAD, _detail)]
    if unmatched:
        rows.append(("recency findings attached", BAD,
                     "%d recency finding(s) %s: no body sentence to rule on, so none is ruled "
                     "until a person attaches it: %s" % (len(unmatched), RECENCY_UNMATCHED,
                                                         " || ".join(unmatched[:4]))))
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


def _unmatched_recency(slug: str, opens: list[dict], have: dict) -> list[str]:
    """'<id>: <study> (why)' for every undecided recency finding that
    recency_attach cannot attach to a body sentence, judged now from the
    current page, sources and rows."""
    out, rows = [], None
    for f in opens:
        if f["kind"] != "recency":
            continue
        r = record_for(have, f)
        if r and (r.get("decision") or "").strip():
            continue
        if rows is None:
            try:
                import bindings as B
                rows = B.load(slug).get("bindings") or {}
            except Exception:
                rows = {}
        m = recency_attach(slug, f.get("study") or "", rows)
        if m["status"] != "matched":
            out.append("%s: %s (%s)" % (f["id"], f.get("study") or "a study", m["why"]))
    return out


def scan(slug: str, report: dict) -> dict:
    doc = load(slug)
    have = {f.get("id"): f for f in (doc.get("findings") or [])}
    rows = None

    def attach(f):
        # the body sentences it is about, recorded when it is opened and
        # refreshed while it is undecided (ruling.py recomputes them from the
        # current rows); RECENCY_UNMATCHED when there are none
        nonlocal rows
        if rows is None:
            try:
                import bindings as B
                rows = B.load(slug).get("bindings") or {}
            except Exception:
                rows = {}
        m = recency_attach(slug, f.get("study") or "", rows)
        a = {"study": f.get("study") or "", "sources": [m["source"]] if m.get("source") else [],
             "rows": m["rows"]}
        if m["status"] != "matched":
            a.update(status=RECENCY_UNMATCHED, why=m["why"])
        return a
    for f in _opens(slug, report):
        r = record_for(have, f)
        if r is not None:
            if f["kind"] == "recency" and not (r.get("decision") or "").strip():
                r["attached_to"] = attach(f)
            continue
        rec = {
            "id": f["id"], "kind": f["kind"], "gate_verdict": f["verdict"],
            "gate_said": f["what"],
            "decision": "", "source_id": "", "quote": "", "why": "",
            "by": "", "on": date.today().isoformat(),
            "_fill_in": "decision: %s. accepted/rejected need source_id AND a "
                        "quote that is in that document." % ", ".join(DECISIONS),
        }
        if f["kind"] == "recency":
            rec["attached_to"] = attach(f)
        doc["findings"].append(rec)
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
    for f in _opens(slug, report):
        rec = record_for(have, f)
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
