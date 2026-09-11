#!/usr/bin/env python3
"""
What Holds Up: the source sweep — citations and corrections.

WHY THIS EXISTS
---------------
On 2026-08-30 an outside reviewer found a study we had said did not exist.

The page for issue three said "the honest position on a null result is that we
do not have one." Pedersen et al., a prospective multicentre trial that removed
CADe and measured what happened, had been published in Endoscopy on 3 June 2026
— nearly three months earlier. It cites our central study. Yuichi Mori, that
study's senior author, is on it. Two fact-check gate runs at roughly $18, five
counterexample hunts, a source-advocate pass and a lint pass all went over the
page without finding it.

The same day we discovered that the central study had carried a correction
since 11 September 2025 — eleven months — which we found only because a gate's
coverage role stumbled over the PubMed record.

Neither was hidden. Both were one free API call away:

    /MED/40816301/citations   ->  126 citing papers, Pedersen among them
    /search?query=DOI:...     ->  commentCorrectionList: [Erratum in, 40946709]

WHAT WAS ACTUALLY BROKEN
------------------------
The weekly scanner (scan_leads.py) watches GDELT and Wikipedia pageviews. Both
measure ATTENTION — what is being published and read in the news. That is the
right instrument for finding a SUBJECT, and it is the wrong one for watching a
subject we have already published. Nothing we owned looked at the literature.

Meanwhile watch.json for issue three named 28 specific queries across 8
questions and nothing executed any of them. The 2026-08-30 watch entry records,
in writing, under not_checked: "W1 — no registry search run" and "W2 — no
citation sweep run". The record existed. Nothing consulted it. That is the same
failure shape as an unrun check reported as a pass, one layer up.

WHAT THIS DOES
--------------
    citations   For every source with a resolvable identifier, ask Europe PMC
                who has cited it since the last sweep. New citations only — the
                baseline is stored, so a sweep that finds nothing says so, and
                a sweep that finds four says which four.

    status      For the same sources, read commentCorrectionList: errata,
                retractions, corrections, expressions of concern, and comments.
                This is the check that had been available for eleven months.

THE RULE THIS FILE IS BUILT AROUND
----------------------------------
An unrun check is not a pass, and a source this cannot reach is not a source
with nothing to report. Only 13 of issue three's 42 sources carry a DOI, a PMID
or an arXiv id. The other 29 are news articles, labels, institutional reports
and preprints outside the index. This tool reports them as UNSWEEPABLE, by name,
every run. A sweep covering a third of the ledger that prints "nothing new"
without saying so would be worse than no sweep, because it would look like
diligence.

No model, no API key, no cost. Europe PMC's REST service is open.

WHAT CHANGED ON 2026-09-11, AND WHY
-----------------------------------
The 31 August and 11 September runs reported 19 of cdk46's 26 sources, 23 of
melanoma's 29 and 24 of deskilling's 44 as NOT SWEEPABLE. Roughly twenty of
those were journal articles with an identifier in the world: the held URL
carried a PMCID, a Europe PMC MED path, a publisher PII or a nature.com slug,
and identifiers() read only DOIs, PubMed URLs and arXiv ids. MONARCH 3's final
overall-survival paper -- whose corrigendum cost this issue ten days -- was
one of them. A sweep that could never have found the one correction it was
built after is not a sweep.

Three rules for the widening, in order of how easily each could go wrong:

  * NEVER SYNTHESISE AN IDENTIFIER. A nature.com slug is not a DOI until the
    registration agency says the DOI exists AND its registered landing URL is
    the URL we hold. Humanities & Social Sciences Communications' slug
    s41599-026-07019-z looks exactly like a DOI suffix and is 404 at Crossref.
    A shape that implies an identifier is a CANDIDATE; `resolve --write`
    turns it into an identifier only after Europe PMC or Crossref confirms it,
    and records what confirmed it, and when, in the source's own ledger entry.
    A candidate nothing confirms stays unsweepable and is reported as such.

  * ONE PARSER. errata.py (B10) already reads PMCIDs, PIIs and /doi/ paths
    out of URLs, reads a DOI out of the bytes we hold, and tests identity with
    resolves_to_us. This file imports those rather than growing a second
    parser that disagrees with the first.

  * A FAILED CALL NEVER TOUCHES A GOOD BASELINE. Europe PMC returned 503s for
    most of an hour on 11 September. Every call now retries with backoff, and a
    baseline is written only after every page of it arrived.

The citations endpoint returns at most 1000 per page and is paged with `page`
(it ignores cursorMark; checked against the live API on 2026-09-11). Before
today one page was fetched and stored as though it were the whole set: PALOMA-2
has 2,282 citing papers and the baseline held 1,000, so "new since last sweep"
against it was undecidable. Every baseline that sat at exactly 1000 with no
recorded hitCount is marked UNRELIABLE, reported as re-baselined rather than
compared, and replaced by the full set.

Usage:

    sweep_sources.py citations <slug> [--all]
    sweep_sources.py status    <slug> [--quiet]
    sweep_sources.py resolve   <slug> [--write]   which sources can be swept;
                                                  --write records confirmed
                                                  identifiers in sources.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ISSUES = ROOT / "issues"
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
CROSSREF = "https://api.crossref.org"
UA = "whatholdsup-source-sweep/1.0 (corrections@whatholdsup.org)"
TIMEOUT = 30
PAUSE = 0.34          # Europe PMC asks for courtesy; three a second is polite.
PAGE = 1000           # the endpoint's maximum page; paged with `page`, below
MAX_PAGES = 50        # 50,000 citations; a cap on a runaway, not an estimate
RETRIES = 4
BACKOFF = (2, 5, 12)  # seconds before attempts 2, 3, 4

# Sibling modules, imported for one parser and one identity test rather than
# two of each. errata.py imports nothing at load and touches no network, which
# the launchd job needs; the sys.path line is for when this file is run by
# path rather than from its directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import errata                    # noqa: E402

# Correction types worth waking someone up for, versus ones that are just
# scholarly conversation. Both are reported; only the first group is loud.
LOUD = {"retraction in", "erratum in", "expression of concern in",
        "corrected and republished in", "republished in"}


# ----------------------------------------------------------------- identifiers

def verified_identifier(src: dict) -> dict | None:
    """The identifier `resolve --write` recorded on this source, if any.

    A block counts only if it says what resolved it and when. A bare
    kind/value with no provenance is exactly the "identifier nobody verified"
    this file refuses to trust, so it is ignored and the source is treated as
    though the block were absent.
    """
    v = src.get("identifier")
    if not isinstance(v, dict):
        return None
    if v.get("kind") not in ("pmid", "doi", "pmcid") or not v.get("value"):
        return None
    if not (v.get("resolved_by") and v.get("resolved_on")):
        return None
    return {"kind": v["kind"], "value": str(v["value"]), "verified": True}


def identifiers(src: dict) -> dict | None:
    """(kind, value) for a source, from a verified ledger block, an explicit
    field, or its URL.

    Explicit fields win. A DOI dug out of a URL is still a DOI, but a URL that
    merely CONTAINS digits is not a PMID, so the patterns are anchored. Shapes
    that only IMPLY an identifier -- a PMCID, a PII, a nature slug, a DOI in
    the bytes we hold -- are not read here. They are candidates, and
    candidate_shape() / resolve_candidate() below turn them into a verified
    block or refuse.
    """
    vb = verified_identifier(src)
    if vb:
        return vb
    url = src.get("url") or ""
    doi = src.get("doi")
    if not doi:
        m = re.search(r"(10\.\d{4,9}/[^\s\"'<>?&#]+)", url)
        if m:
            doi = m.group(1).rstrip(").,;")
    pmid = src.get("pmid")
    if not pmid:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", url)
        if m:
            pmid = m.group(1)
    # arXiv ids are read from the URL and the TITLE only, never from the whole
    # record. The first version searched json.dumps(src), and resolved the
    # scoping review (S029) to arXiv 2411.00998 — an id quoted inside its own
    # notes, belonging to a different paper. A sweep that silently swaps one
    # paper for another is worse than a sweep that reports a gap.
    arxiv = None
    for field in (url, src.get("title") or ""):
        m = (re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", field)
             or re.search(r"\barXiv[:\s]\s*(\d{4}\.\d{4,5})\b", field))
        if m:
            arxiv = m.group(1)
            break
    if pmid:
        return {"kind": "pmid", "value": str(pmid)}
    if doi:
        return {"kind": "doi", "value": doi}
    if arxiv:
        return {"kind": "arxiv", "value": arxiv}
    return None


RETRY_HTTP = {429, 500, 502, 503, 504}


def _get(path: str, params: dict | None = None, *, base: str = BASE) -> dict:
    """One JSON GET, retried on the failures that mean "try again" and not on
    the ones that mean "no".

    5xx, 429, a reset, a timeout and a truncated body are retried with backoff.
    A 404 is an answer -- for Crossref it means the DOI does not exist, which
    is the answer this file most needs to hear -- and is raised at once. After
    the last attempt the last error is raised; the caller records the source
    as unresolved and leaves its baseline alone.
    """
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    last: Exception | None = None
    for attempt in range(RETRIES):
        if attempt:
            time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in RETRY_HTTP:
                continue
            raise
        except (urllib.error.URLError, OSError, ValueError) as exc:
            # URLError: DNS/refused; OSError: socket timeout, reset;
            # ValueError: JSONDecodeError on a body cut off mid-stream.
            last = exc
            continue
    assert last is not None
    raise last


def lookup(ident: dict) -> dict | None:
    """Resolve an identifier to a Europe PMC record (source + id + core fields).

    Three things learned by getting each of them wrong on 2026-08-30:

    PMIDs must NOT be quoted. `EXT_ID:"42235541" AND SRC:"MED"` returns zero
    hits; `EXT_ID:42235541 AND SRC:MED` returns the paper. The first form
    reported the Pedersen study — the one this whole file exists because of —
    as "not in the index".

    A bare arXiv number must never be searched as a phrase. `"2506.08872"`
    returns 31 unrelated hits, the first of which is a different paper
    entirely. Silently resolving a source to somebody else's article is the
    worst thing this tool could do, so an arXiv id is looked up only through
    its registered DOI, and anything else is reported unresolved.

    Some DOIs are genuinely absent: Europe PMC does not index MDPI's Societies
    or Wiley's Journal of Computer Assisted Learning. That is a real gap in
    coverage and is reported as one, not smoothed over.
    """
    if ident["kind"] == "pmid":
        q = "EXT_ID:%s AND SRC:MED" % ident["value"]
    elif ident["kind"] == "doi":
        q = 'DOI:"%s"' % ident["value"]
    elif ident["kind"] == "pmcid":
        q = "PMCID:%s" % ident["value"]
    else:
        q = 'DOI:"10.48550/arXiv.%s"' % ident["value"]
    time.sleep(PAUSE)
    d = _get("/search", {"query": q, "resultType": "core", "format": "json",
                         "pageSize": 1})
    hits = d.get("resultList", {}).get("result", [])
    return hits[0] if hits else None


# ------------------------------------------------- candidate shapes, resolved

# URL shapes that IMPLY an identifier. Each is a claim that somebody could
# check; none is an identifier until resolve_candidate() checks it.
EPMC_MED_RE = re.compile(r"europepmc\.org/(?:article|abstract)/MED/(\d{6,9})\b", re.I)
EPMC_PMC_RE = re.compile(r"europepmc\.org/(?:article|abstract)/PMC/(PMC\d{4,9})\b", re.I)
PMCID_RE = re.compile(r"\b(PMC\d{4,9})\b")
# Elsevier's PII, with or without the "PII" prefix the Lancet puts in front
# of it. errata.identifier_of reads the bare form; the Lancet form is the one
# MONALEESA-7's Lancet Oncology paper (cdk46 S006) is held under.
PII_RE = re.compile(r"/article/(?:PII)?(S\d{4}-\d{4}\(\d{2}\)\d{5}-[\dX])", re.I)
NATURE_RE = re.compile(r"nature\.com/articles/([a-z]\d{5}-\d{3}-\d{4,5}-[a-z0-9])\b", re.I)


def _norm_url(u: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", (u or "").strip(), flags=re.I)
    return u.split("#", 1)[0].rstrip("/").lower()


def candidate_shapes(src: dict, slug: str) -> list[dict]:
    """Every shape that implies an identifier, in the order to try them.

    Each is {"shape": what was seen and where, "route": how it would be
    confirmed, "kind": pmid|pmcid|pii|doi, "value": ...}. A list, not one
    shape: MONARCH 3's URL carries an Annals PII that resolves nowhere, and
    the DOI in the PDF we hold resolves everywhere. The first shape that
    confirms wins; the refusals are reported.

    Order is by how directly the shape names a record: a PMID or PMCID in a
    URL names one record; a PII names one for its publisher and may or may
    not be findable in an index; a nature slug names a DOI only if the DOI
    exists; a DOI read out of held bytes is errata.py's route and keeps
    errata.py's guards (form must be `article`; never coverage, never a
    corrigendum, because those print somebody else's DOI).
    """
    url = src.get("url") or ""
    out = []
    m = EPMC_MED_RE.search(url)
    if m:
        out.append({"shape": "Europe PMC MED path in the held URL", "route": "europepmc",
                    "kind": "pmid", "value": m.group(1)})
    m = EPMC_PMC_RE.search(url) or PMCID_RE.search(url)
    if m:
        out.append({"shape": "PMCID %s in the held URL" % m.group(1), "route": "europepmc",
                    "kind": "pmcid", "value": m.group(1)})
    m = PII_RE.search(url)
    if m:
        out.append({"shape": "publisher PII %s in the held URL" % m.group(1),
                    "route": "europepmc-then-crossref", "kind": "pii", "value": m.group(1)})
    m = NATURE_RE.search(url)
    if m:
        # nature.com hosts Nature Portfolio journals (prefix 10.1038) and
        # Palgrave journals (10.1057) under one URL shape. Both are tried;
        # neither is written unless Crossref's registered landing URL for the
        # DOI equals the URL we hold. Humanities & Social Sciences
        # Communications is 10.1057 and was three refusals on 2026-09-11
        # until the second prefix was tried under the same test.
        for prefix in ("10.1038/", "10.1057/"):
            out.append({"shape": "nature.com slug %s in the held URL" % m.group(1),
                        "route": "crossref", "kind": "doi", "value": prefix + m.group(1)})
    held = errata.identifier_from_held(slug, src)
    if held:
        kind, value = held
        out.append({"shape": "%s read out of the document we hold" % kind,
                    "route": "europepmc-then-crossref", "kind": kind.lower(), "value": value})
    return out


def candidate_shape(src: dict, slug: str) -> dict | None:
    """The first shape, for listing. resolve tries all of them."""
    shapes = candidate_shapes(src, slug)
    return shapes[0] if shapes else None


def _epmc_hits(query: str, n: int = 5) -> list:
    time.sleep(PAUSE)
    d = _get("/search", {"query": query, "resultType": "core", "format": "json",
                         "pageSize": n})
    return d.get("resultList", {}).get("result", []) or []


def _crossref_work(doi: str) -> dict | None:
    """Crossref's record for a DOI, or None when the DOI does not exist.
    Raises on a transport failure, so a down Crossref is never read as 'no
    such DOI'."""
    try:
        d = _get("/works/" + urllib.parse.quote(doi, safe=""), base=CROSSREF)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    msg = d.get("message")
    return msg if isinstance(msg, dict) else None


def _block(kind: str, value: str, cand: dict, resolved_by: str, identity: str,
           title: str, extra: dict | None = None) -> dict:
    b = {"kind": kind, "value": value, "shape": cand["shape"],
         "resolved_by": resolved_by, "identity": identity,
         "resolved_on": date.today().isoformat(),
         "resolved_title": (title or "")[:160],
         "by": "sweep_sources.py resolve --write"}
    if extra:
        b.update(extra)
    return b


def resolve_candidate(cand: dict, src: dict) -> tuple[dict | None, str]:
    """(verified block, why) or (None, why). Never invents; never guesses.

    Identity is established one of three ways, and the block says which:
      * the identifier is literally in the URL a person put in the ledger
        (a PMID or PMCID) -- the URL is the identity claim;
      * Crossref's registered landing URL for the DOI equals the held URL;
      * the resolved record's title shares distinctive words with ours
        (errata.resolves_to_us -- the test the estate already applies).
    A candidate that reaches an index but fails identity is refused with the
    reason, because that is the case where a wrong identifier would be
    trusted downstream by every check.
    """
    kind, value = cand["kind"], cand["value"]

    if kind in ("pmid", "pmcid"):
        q = ("EXT_ID:%s AND SRC:MED" % value) if kind == "pmid" else ("PMCID:%s" % value)
        hits = _epmc_hits(q, 1)
        if not hits:
            return None, "Europe PMC has no record for %s %s" % (kind.upper(), value)
        h = hits[0]
        pmid = h.get("pmid") or (h.get("id") if h.get("source") == "MED" else None)
        if pmid:
            return _block("pmid", str(pmid), cand,
                          "Europe PMC search %s -> %s/%s" % (q, h.get("source"), h.get("id")),
                          "the %s is literally in the URL we hold" % kind.upper(),
                          h.get("title") or "",
                          {"pmcid": h.get("pmcid"), "doi": h.get("doi")}), "resolved"
        return _block("pmcid", value, cand,
                      "Europe PMC search %s -> %s/%s" % (q, h.get("source"), h.get("id")),
                      "the PMCID is literally in the URL we hold", h.get("title") or "",
                      {"doi": h.get("doi")}), "resolved"

    if kind == "pii":
        # A phrase search for a PII returns the paper whose DOI embeds it
        # (Lancet) and also anything that cites it. Only a hit whose own DOI
        # contains the PII is the paper.
        hits = _epmc_hits('"%s"' % value, 5)
        for h in hits:
            if value.lower() in (h.get("doi") or "").lower():
                return _block("doi", h["doi"], cand,
                              'Europe PMC search "%s" -> %s/%s whose DOI embeds the PII'
                              % (value, h.get("source"), h.get("id")),
                              "the PII in the held URL is embedded in the resolved DOI",
                              h.get("title") or "",
                              {"pmid": h.get("pmid"), "pmcid": h.get("pmcid")}), "resolved"
        # Elsevier deposits the PII as Crossref's alternative-id for some
        # journals. For Annals of Oncology it does not; that was checked on
        # 2026-09-11 and came back empty, so this branch is here for the
        # journals where it works and reports honestly where it does not.
        d = _get("/works", {"filter": "alternative-id:" + value, "rows": 3,
                            "select": "DOI,title,alternative-id,resource"}, base=CROSSREF)
        for it in (d.get("message") or {}).get("items") or []:
            alts = [a.lower() for a in (it.get("alternative-id") or [])]
            if value.lower() in alts and it.get("DOI"):
                land = ((it.get("resource") or {}).get("primary") or {}).get("URL") or ""
                same_url = _norm_url(land) == _norm_url(src.get("url") or "")
                ok, why = errata.resolves_to_us({"title": (it.get("title") or [""])[0]}, src)
                if same_url or ok:
                    return _block("doi", it["DOI"], cand,
                                  "Crossref works?filter=alternative-id:%s -> DOI %s"
                                  % (value, it["DOI"]),
                                  "Crossref's landing URL equals the held URL" if same_url
                                  else why, (it.get("title") or [""])[0]), "resolved"
                return None, ("Crossref alternative-id matched DOI %s but identity failed: %s"
                              % (it["DOI"], why))
        return None, ("PII %s: no Europe PMC record whose DOI embeds it, and Crossref "
                      "holds no alternative-id for it. Not resolvable from what we hold."
                      % value)

    if kind == "doi":
        # A DOI from a nature slug or from held bytes. The registration agency
        # must say it exists, and identity must hold.
        try:
            msg = _crossref_work(value)
        except Exception as exc:
            msg, cr_err = None, "%s: %s" % (type(exc).__name__, exc)
        else:
            cr_err = None
        if msg is None and cr_err is None and cand["route"] == "crossref":
            return None, ("Crossref has no DOI %s -- that prefix and slug are not a DOI."
                          % value)
        if msg is not None:
            land = ((msg.get("resource") or {}).get("primary") or {}).get("URL") or ""
            same_url = _norm_url(land) == _norm_url(src.get("url") or "")
            title = (msg.get("title") or [""])[0]
            ok, why = errata.resolves_to_us({"title": title}, src)
            if same_url or ok:
                return _block("doi", value, cand,
                              "Crossref works/%s exists; registered landing URL %s"
                              % (value, land or "(none)"),
                              "Crossref's landing URL equals the held URL" if same_url else why,
                              title), "resolved"
            return None, ("Crossref has DOI %s but it resolves to a different document "
                          "(landing %s; %s)" % (value, land or "?", why))
        # Crossref unreachable: Europe PMC can still confirm, with identity.
        hits = _epmc_hits('DOI:"%s"' % value, 1)
        if hits:
            ok, why = errata.resolves_to_us(hits[0], src)
            if ok:
                return _block("doi", value, cand,
                              'Europe PMC search DOI:"%s" -> %s/%s (Crossref unreachable: %s)'
                              % (value, hits[0].get("source"), hits[0].get("id"), cr_err),
                              why, hits[0].get("title") or "",
                              {"pmid": hits[0].get("pmid"), "pmcid": hits[0].get("pmcid")}), "resolved"
            return None, "Europe PMC has DOI %s but identity failed: %s" % (value, why)
        if cr_err:
            return None, ("could not confirm DOI %s: Crossref unreachable (%s) and Europe "
                          "PMC has no record. Try again; not written." % (value, cr_err))
        return None, ("could not confirm DOI %s: not registered at Crossref (a DataCite "
                      "DOI, e.g. arXiv, would be) and not in Europe PMC. Not written."
                      % value)

    return None, "unknown candidate kind %r" % kind


def write_identifier(slug_dir: Path, sid: str, block: dict) -> None:
    """Record a verified identifier on the source's ledger entry. The only
    writer of sources.json in this file, and it writes only blocks that
    resolve_candidate() returned."""
    p = slug_dir / "sources.json"
    raw = p.read_text(encoding="utf-8")
    doc = json.loads(raw)
    rows = doc["sources"] if isinstance(doc, dict) else doc
    for r in rows:
        if r.get("id") == sid:
            r["identifier"] = block
            break
    else:
        raise SystemExit("no source %s in %s" % (sid, p))
    # Keep the file's own indent: melanoma's ledger is written at one space,
    # the others at two, and a reformat would bury a nine-line addition in a
    # fifteen-hundred-line diff nobody can review.
    lines = raw.split("\n")
    indent = 2
    for ln in lines[1:]:
        if ln.strip():
            indent = max(1, len(ln) - len(ln.lstrip(" ")))
            break
    out = json.dumps(doc, indent=indent, ensure_ascii=False)
    p.write_text(out + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")


def published_version(src: dict) -> list:
    """Candidate published versions of a preprint, by exact title.

    For the preprints this page leans on, the question that matters is watch
    question W3: has it been peer reviewed, revised or withdrawn? A title
    search can answer that, and can also match the wrong paper, so results are
    returned as CANDIDATES for a person to confirm and are never written into a
    baseline as a resolution.
    """
    title = (src.get("title") or "")
    m = re.search(r"\u2014\s*(.+?)(?:\.|,|\s+arXiv|\s+\d{4};)", title)
    phrase = (m.group(1) if m else title).strip()
    phrase = re.sub(r'["\\]', " ", phrase)[:120].strip()
    if len(phrase) < 25:
        return []
    try:
        time.sleep(PAUSE)
        d = _get("/search", {"query": 'TITLE:"%s"' % phrase, "resultType": "lite",
                             "format": "json", "pageSize": 5})
    except Exception:
        return []
    return d.get("resultList", {}).get("result", []) or []


# ---------------------------------------------------------------------- state

def state_path(slug_dir: Path) -> Path:
    return slug_dir / "sweeps.json"


def load_state(slug_dir: Path) -> dict:
    p = state_path(slug_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"what_this_is": ("Baselines for sweep_sources.py. Which citations and "
                            "which correction notices we had already seen, so a "
                            "later run can report what is NEW rather than "
                            "re-reporting the world."),
            "citations": {}, "status": {}, "runs": []}


def save_state(slug_dir: Path, st: dict) -> None:
    state_path(slug_dir).write_text(
        json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_issue(slug: str) -> Path:
    for d in sorted(ISSUES.glob("WHU-*")):
        if (d / "sources.json").exists() and slug.lower() in d.name.lower():
            return d
    for d in sorted(ISSUES.glob("*")):
        if (d / "sources.json").exists() and slug.lower() in d.name.lower():
            return d
    raise SystemExit("no issue directory matching %r under %s" % (slug, ISSUES))


def short_slug(slug_dir: Path) -> str:
    """WHU-002-cdk46 -> cdk46, the form source_store and errata take."""
    parts = slug_dir.name.split("-", 2)
    return parts[2] if len(parts) == 3 else slug_dir.name


def sweepable(slug_dir: Path):
    """-> (sweepable [(src, ident)], candidates [(src, shape)], unsweepable [src]).

    Three lists, never two: a source with a shape nobody has confirmed is not
    sweepable and is not hopeless either, and folding it into either list
    would misreport it. Never silently drops.
    """
    doc = json.loads((slug_dir / "sources.json").read_text(encoding="utf-8"))
    rows = doc["sources"] if isinstance(doc, dict) else doc
    slug = short_slug(slug_dir)
    ok, cands, no = [], [], []
    for r in rows:
        ident = identifiers(r)
        if ident:
            ok.append((r, ident))
            continue
        shape = candidate_shape(r, slug)
        (cands.append((r, shape)) if shape else no.append(r))
    return ok, cands, no


def last_refusals(st: dict) -> dict:
    """{source id: (date, why)} from the most recent `resolve --write` run, so
    a shape that was tried and refused is never printed as untried."""
    for run in reversed(st.get("runs", [])):
        if run.get("command") == "resolve --write":
            return {r["id"]: (run.get("on"), r.get("why", "")) for r in run.get("refused", [])}
    return {}


def _print_gap(cands: list, no: list, verb: str, st: dict | None = None) -> None:
    refused = last_refusals(st or {})
    if cands:
        print("\n  SHAPE SEEN, NOT CONFIRMED — an identifier is implied and nothing has")
        print("  confirmed it; these are NOT swept:")
        for r, shape in cands:
            if r["id"] in refused:
                on, why = refused[r["id"]]
                print("    %-6s %-40s %s" % (r["id"], shape["shape"][:40], _title(r)[:40]))
                print("           refused %s: %s" % (on, why[:100]))
            else:
                print("    %-6s %-40s %s" % (r["id"], shape["shape"][:40], _title(r)[:40]))
                print("           not yet tried — run `resolve <slug> --write`")
    if no:
        print("\n  NOT SWEEPABLE — no DOI, PMID, PMCID, PII or slug we could confirm.")
        print("  These are %s by hand or not at all, and this list is the honest" % verb)
        print("  size of that gap:")
        for r in no:
            print("    %-6s %s" % (r["id"], _title(r)[:64]))


def all_citations(source: str, pid: str) -> tuple[list, int]:
    """Every citing record, paged with `page` until hitCount is reached.

    Raises if any page fails after retries: a partial set must never become a
    baseline, because the next run would report the missing tail as NEW.
    """
    out, page, hit = [], 1, 0
    while True:
        time.sleep(PAUSE)
        c = _get("/%s/%s/citations" % (source, pid),
                 {"format": "json", "pageSize": PAGE, "page": page})
        hit = int(c.get("hitCount") or 0)
        cits = c.get("citationList", {}).get("citation", []) or []
        out.extend(cits)
        if not cits or len(out) >= hit or page >= MAX_PAGES:
            break
        page += 1
    return out, hit


TRUNCATED_NOTE = ("captured with pageSize 1000 and no paging before 2026-09-11; the "
                  "citing set may have been larger, so 'new since this baseline' is "
                  "undecidable against it")


def mark_truncated(base: dict, today: str) -> list[str]:
    """Flag every prior baseline that sat at exactly one page and never
    recorded a hitCount. Returns the ids flagged this run."""
    flagged = []
    for sid, b in base.items():
        if b.get("count") == PAGE and "hit_count" not in b and not b.get("unreliable"):
            b["unreliable"] = {"reason": TRUNCATED_NOTE, "marked": today}
            flagged.append(sid)
    return flagged


def _title(r: dict) -> str:
    return (r.get("title") or "").strip()


# ------------------------------------------------------------------ citations

def cmd_citations(args) -> int:
    d = find_issue(args.slug)
    ok, cands, no = sweepable(d)
    st = load_state(d)
    base = st.setdefault("citations", {})
    today = date.today().isoformat()

    print("\n  CITATION SWEEP — %s" % d.name)
    print("  %d source(s) with an identifier, %d with a shape awaiting confirmation, "
          "%d without\n" % (len(ok), len(cands), len(no)))

    flagged = mark_truncated(base, today)
    if flagged:
        print("  BASELINES MARKED UNRELIABLE (one page of %d, no hitCount recorded): %s"
              % (PAGE, ", ".join(flagged)))
        print("  Their 'new since last sweep' is undecidable; they are re-baselined below.\n")

    new_total, rebaselined, unresolved, checked, incomplete = 0, [], [], 0, []
    first_sweep = {}
    for src, ident in ok:
        sid = src["id"]
        try:
            rec = lookup(ident)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            unresolved.append((sid, "%s: %s" % (ident["value"], exc)))
            continue
        if not rec:
            unresolved.append((sid, "%s not in the index" % ident["value"]))
            continue
        source, pid = rec.get("source"), rec.get("id")
        try:
            cits, hit = all_citations(source, pid)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            # Rule 30: nothing is written for this source. Its prior baseline,
            # reliable or flagged, stands untouched.
            unresolved.append((sid, "citations call failed: %s" % exc))
            continue
        checked += 1
        prior = base.get(sid, {})
        truncated = bool(prior.get("unreliable"))
        seen = set(prior.get("ids", []))
        fresh = [x for x in cits if str(x.get("id")) not in seen]
        if args.all:
            fresh = cits
        complete = len(cits) >= hit
        if not complete:
            incomplete.append(sid)
        if fresh:
            print("  %s  %s" % (sid, _title(src)[:66]))
            if truncated and not args.all:
                rebaselined.append(sid)
                print("      %d citing paper(s) not in the truncated baseline of %d — whether "
                      "they are NEW is undecidable;" % (len(fresh), prior.get("count", 0)))
                print("      full set now held: %d of hitCount %d" % (len(cits), hit))
            elif not seen and not args.all:
                # A source watched for the first time has a history, not news.
                first_sweep[sid] = len(fresh)
                print("      %d citing paper(s) — FIRST SWEEP: a baseline, not new citations"
                      % len(fresh))
            else:
                new_total += len(fresh)
                print("      %d citing paper(s) NEW since last sweep" % len(fresh))
            for x in sorted(fresh, key=lambda z: str(z.get("pubYear") or ""), reverse=True)[:args.show]:
                print("        %s  %-11s %s" % (x.get("pubYear") or "????",
                                                (x.get("journalAbbreviation") or "")[:11],
                                                (x.get("title") or "")[:62]))
                print("                              %s" % (x.get("authorString") or "")[:62])
            if len(fresh) > args.show:
                print("        ... and %d more, in sweeps.json" % (len(fresh) - args.show))
            print()
        entry = {"ids": [str(x.get("id")) for x in cits],
                 "count": len(cits), "hit_count": hit, "complete": complete,
                 "swept": today, "resolved_as": "%s/%s" % (source, pid)}
        if truncated:
            entry["prior_truncated"] = {"count": prior.get("count"),
                                        "swept": prior.get("swept"),
                                        "marked_unreliable": prior["unreliable"].get("marked")}
        base[sid] = entry

    print("  " + "-" * 66)
    print("  %d source(s) queried, %d new citation(s)." % (checked, new_total))
    if rebaselined:
        print("  %d source(s) re-baselined from a truncated page: %s — not counted as new."
              % (len(rebaselined), ", ".join(rebaselined)))
    if first_sweep:
        print("  %d source(s) baselined for the first time: %s — not counted as new."
              % (len(first_sweep), ", ".join("%s (%d)" % kv for kv in first_sweep.items())))
    if incomplete:
        print("  INCOMPLETE — fewer records than hitCount after %d pages: %s"
              % (MAX_PAGES, ", ".join(incomplete)))
    if unresolved:
        print("\n  COULD NOT RESOLVE — not the same as nothing to report:")
        for sid, why in unresolved:
            print("    %-6s %s" % (sid, why))
    _print_gap(cands, no, "watched", st)
    st["runs"].append({"on": today, "command": "citations",
                       "sources_queried": checked, "new_citations": new_total,
                       "first_sweep": first_sweep,
                       "rebaselined_from_truncated": rebaselined,
                       "incomplete": incomplete,
                       "unresolved": [s for s, _ in unresolved],
                       "candidates_unconfirmed": [r["id"] for r, _ in cands],
                       "unsweepable": [r["id"] for r in no]})
    save_state(d, st)
    print("\n  baseline written to %s\n" % state_path(d).relative_to(ROOT))
    return 0


# --------------------------------------------------------------------- status

def cmd_status(args) -> int:
    d = find_issue(args.slug)
    ok, cands, no = sweepable(d)
    st = load_state(d)
    base = st.setdefault("status", {})
    today = date.today().isoformat()

    print("\n  CORRECTION AND RETRACTION SWEEP — %s" % d.name)
    print("  %d source(s) with an identifier, %d with a shape awaiting confirmation, "
          "%d without\n" % (len(ok), len(cands), len(no)))

    loud, quiet, unresolved, candidates, checked = [], [], [], [], 0
    for src, ident in ok:
        try:
            rec = lookup(ident)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            # Rule 30: the prior status baseline for this source stands.
            unresolved.append((src["id"], str(exc)))
            continue
        if not rec:
            unresolved.append((src["id"], "%s not in the index" % ident["value"]))
            if ident["kind"] == "arxiv":
                for cand in published_version(src):
                    candidates.append((src, cand))
            continue
        checked += 1
        notes = rec.get("commentCorrectionList", {}).get("commentCorrection", []) or []
        prev = set(base.get(src["id"], {}).get("seen", []))
        for n in notes:
            key = "%s:%s" % (n.get("type"), n.get("id"))
            row = (src, n, key not in prev)
            (loud if (n.get("type") or "").lower() in LOUD else quiet).append(row)
        base[src["id"]] = {"seen": ["%s:%s" % (n.get("type"), n.get("id")) for n in notes],
                           "swept": today,
                           "resolved_as": "%s/%s" % (rec.get("source"), rec.get("id"))}

    if loud:
        print("  CORRECTIONS, ERRATA AND RETRACTIONS")
        for src, n, is_new in loud:
            print("    %s%s  %s" % ("NEW " if is_new else "    ", src["id"], _title(src)[:58]))
            print("           %s — europepmc.org/article/MED/%s" % (n.get("type"), n.get("id")))
        print()
    else:
        print("  No corrections, errata or retractions on any source we could resolve.\n")

    if quiet and not args.quiet:
        print("  COMMENTS AND REPLIES (conversation, not correction)")
        for src, n, is_new in quiet[:args.show]:
            print("    %s%s  %s — MED/%s" % ("NEW " if is_new else "    ",
                                             src["id"], n.get("type"), n.get("id")))
        if len(quiet) > args.show:
            print("    ... and %d more" % (len(quiet) - args.show))
        print()

    if candidates:
        print("  POSSIBLE PUBLISHED VERSIONS OF PREPRINTS — CANDIDATES ONLY")
        print("  A title search finds these. It also finds the wrong paper: on")
        print("  2026-08-30 a search for \"Your Brain on ChatGPT\" returned a")
        print("  different 2025 article with almost the same title. Nothing here")
        print("  is recorded as a resolution. Open it, or leave it.")
        for src, cand in candidates[:args.show]:
            print("    %-6s -> %s/%s (%s)  %s" % (src["id"], cand.get("source"),
                                                  cand.get("id"), cand.get("pubYear"),
                                                  (cand.get("title") or "")[:48]))
        print()

    print("  " + "-" * 66)
    print("  %d source(s) queried." % checked)
    if unresolved:
        print("\n  COULD NOT RESOLVE — not the same as nothing to report:")
        for sid, why in unresolved:
            print("    %-6s %s" % (sid, why))
        print("    Europe PMC indexes the biomedical literature. It does not")
        print("    carry MDPI's Societies, Wiley's J Comput Assist Learn,")
        print("    Elsevier's Computers & Education, OSF preprints, or arXiv")
        print("    computer-science preprints. Those are watched by hand.")
    _print_gap(cands, no, "watched", st)
    st["runs"].append({"on": today, "command": "status", "sources_queried": checked,
                       "loud": len(loud), "quiet": len(quiet),
                       "preprint_candidates": len(candidates),
                       "unresolved": [s for s, _ in unresolved],
                       "candidates_unconfirmed": [r["id"] for r, _ in cands],
                       "unsweepable": [r["id"] for r in no]})
    save_state(d, st)
    print("\n  baseline written to %s\n" % state_path(d).relative_to(ROOT))
    return 0


def cmd_resolve(args) -> int:
    """Which sources can be swept; with --write, confirm candidate shapes
    against Europe PMC / Crossref and record the confirmed identifier on the
    source's ledger entry. Nothing unconfirmed is ever written."""
    d = find_issue(args.slug)
    ok, cands, no = sweepable(d)
    today = date.today().isoformat()
    print("\n  %s — what can be swept at all\n" % d.name)
    for src, ident in ok:
        how = "ledger" if ident.get("verified") else "url/field"
        print("    %-6s %-5s %-34s %-9s %s" % (src["id"], ident["kind"],
                                               ident["value"][:34], how, _title(src)[:36]))
    print("\n  %d of %d sweepable as held." % (len(ok), len(ok) + len(cands) + len(no)))

    resolved, refused, failed = [], [], []
    if cands:
        print("\n  %d source(s) carry a shape that implies an identifier. %s\n"
              % (len(cands), "Confirming each:" if args.write else
                 "Run with --write to confirm and record:"))
        for src, shape in cands:
            sid = src["id"]
            if not args.write:
                print("    %-6s %-44s %s" % (sid, shape["shape"][:44], _title(src)[:34]))
                continue
            block, why, errored = None, "", False
            for cand in candidate_shapes(src, short_slug(d)):
                try:
                    block, w = resolve_candidate(cand, src)
                except Exception as exc:
                    errored = True
                    w = "%s: lookup failed: %s: %s" % (cand["shape"], type(exc).__name__, exc)
                why = (why + " | " if why else "") + w
                if block:
                    break
            if not block and errored:
                failed.append((sid, why))
                print("    %-6s FAILED     %s" % (sid, why[:110]))
                continue
            if block:
                write_identifier(d, sid, block)
                resolved.append((sid, block))
                print("    %-6s RESOLVED   %s %s" % (sid, block["kind"], block["value"]))
                print("           via: %s" % block["resolved_by"][:90])
                print("           identity: %s" % block["identity"][:90])
                print("           title: %s" % block["resolved_title"][:80])
            else:
                refused.append((sid, why))
                print("    %-6s REFUSED    %s" % (sid, why[:100]))
        if args.write:
            print("\n  %d confirmed and recorded in sources.json; %d refused (shape does not "
                  "resolve, stays unsweepable); %d lookups failed (try again)."
                  % (len(resolved), len(refused), len(failed)))
    if no:
        print("\n  %d carry nothing that implies an identifier:\n" % len(no))
        for r in no:
            print("    %-6s %-9s %s" % (r["id"], (r.get("type") or "")[:9], _title(r)[:56]))
    print("\n  That gap is the honest limit of this instrument. News articles,")
    print("  labels, registry records, institutional reports and off-index")
    print("  preprints are watched by hand or not at all.\n")
    if args.write:
        st = load_state(d)
        st["runs"].append({"on": today, "command": "resolve --write",
                           "resolved": [s for s, _ in resolved],
                           "refused": [{"id": s, "why": w} for s, w in refused],
                           "failed": [{"id": s, "why": w} for s, w in failed],
                           "unsweepable": [r["id"] for r in no]})
        save_state(d, st)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (
            ("citations", cmd_citations, "who has cited our sources since the last sweep"),
            ("status", cmd_status, "corrections, errata and retractions on our sources"),
            ("resolve", cmd_resolve, "which sources carry an identifier at all")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug", help="issue slug or directory fragment, e.g. deskilling")
        p.add_argument("--show", type=int, default=6, help="how many to print per source")
        if name == "citations":
            p.add_argument("--all", action="store_true",
                           help="print every citation, not only new ones")
        if name == "status":
            p.add_argument("--quiet", action="store_true",
                           help="corrections only; hide comments and replies")
        if name == "resolve":
            p.add_argument("--write", action="store_true",
                           help="confirm candidate shapes against Europe PMC / Crossref "
                                "and record confirmed identifiers in sources.json")
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
