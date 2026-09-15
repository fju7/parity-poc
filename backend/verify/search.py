"""search(title, ...) -> an Identifier the registry issued for that title, or None.

Provenance.SEARCHED, the third kind in types.py, finally has an implementation.

WHY THIS EXISTS
---------------
00_discover_sources.py asked a model with no tools for "url":
"https://doi.org/..." and told it not to fabricate DOIs. 59 of the 381 frozen
corpus identifiers resolve to nothing and 33 to a different paper: the model
did exactly what a model does with a slot for an identifier it has never
seen. The fix is not a better warning; it is to take the slot away. The model
proposes what it can actually know -- a title, a first author, a year, a
container -- and this module asks the registries whether such a thing exists.
A title that resolves to nothing is reported as UNRESOLVED and never guessed.

REGISTRIES
----------
    Europe PMC   search?query=TITLE:"..."           journal articles (PMID / DOI / PMCID)
    Crossref     works?query.bibliographic=...      anything with a DOI
    ClinicalTrials.gov v2  studies?query.term=...  trials (NCT)

THE MATCH RULE
--------------
A candidate is accepted only if its registry title shares enough distinctive
words with the proposed title: containment (every distinctive word of the
shorter is in the longer) or ratio >= MATCH_RATIO with at least MATCH_MIN
shared words -- the same word arithmetic as verify.bind.bind_heading, tuned
stricter because here a wrong match would MINT an identifier rather than
refuse one. A first author or year, when the model gave one and the registry
has one, must agree if present. Ties between registries: Europe PMC first
(it carries PMID and DOI together), then Crossref, then trials.

No model is called. Every call is a recorded HTTP request through verify.http.
"""
from __future__ import annotations

import datetime as dt
import re
import urllib.parse
from dataclasses import dataclass, field

from . import http
from .text import agreement, content_tokens, LITERATURE_BOILERPLATE
from .types import Identifier, Provenance

MATCH_RATIO = 0.6
MATCH_MIN = 3
# A trial registry match must be near-exact. Trial titles are generic:
# "Vaccines for measles, mumps and rubella in children" word-matched
# "Immunogenicity and Safety Study of ... Measles Mumps Rubella Varicella
# Vaccine (PriorixTetra)" at 0.8 on 2026-09-15 and minted NCT01506193 for a
# Cochrane review. Pinned by tests/verify/golden_search.json known_bad.
TRIAL_MATCH_RATIO = 0.9
TRIAL_MATCH_MIN = 4
_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731


@dataclass
class Found:
    identifier: Identifier
    registry: str
    heading: str
    canonical: str
    shared: set = field(default_factory=set)
    ratio: float = 0.0
    year: int | None = None
    first_author: str | None = None
    extra: dict = field(default_factory=dict)
    checked_at: str = ""


@dataclass
class Unresolved:
    title: str
    reason: str
    candidates: list = field(default_factory=list)   # (registry, heading) of near-misses, for a reviewer
    checked_at: str = ""


def _json(body: bytes):
    import json
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None


def _title_matches(proposed: str, candidate: str) -> tuple[bool, float, set]:
    ratio, shared = agreement(proposed, candidate, LITERATURE_BOILERPLATE)
    ours = len(content_tokens(proposed, LITERATURE_BOILERPLATE))
    theirs = len(content_tokens(candidate, LITERATURE_BOILERPLATE))
    if ratio == 1.0 and shared and min(ours, theirs) >= 2:
        return True, ratio, shared                       # containment
    return (ratio >= MATCH_RATIO and len(shared) >= MATCH_MIN), ratio, shared


def _author_ok(proposed: str | None, found: str | None) -> bool:
    if not proposed or not found:
        return True                                      # nothing to compare: not a refusal
    p = re.sub(r"[^a-z]", "", proposed.split(",")[0].split(" ")[-1].lower())
    f = re.sub(r"[^a-z]", "", found.lower())
    return bool(p and f and (p == f or p in f or f in p))


def _year_ok(proposed: int | None, found: int | None) -> bool:
    if not proposed or not found:
        return True
    return abs(int(proposed) - int(found)) <= 1           # epub vs print year


def _epmc(title: str, first_author: str | None, year: int | None, near: list) -> Found | None:
    q = f'TITLE:"{title}"'
    st, body, _ = http.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                           + urllib.parse.quote(q) + "&format=json&pageSize=5&resultType=lite")
    d = _json(body) if st == 200 else None
    for r in ((d or {}).get("resultList") or {}).get("result") or []:
        ok, ratio, shared = _title_matches(title, r.get("title") or "")
        fa = (r.get("authorString") or "").split(",")[0].split(" ")[0] or None
        yr = int(r["pubYear"]) if str(r.get("pubYear") or "").isdigit() else None
        if ok and _author_ok(first_author, fa) and _year_ok(year, yr):
            if r.get("doi"):
                ident = Identifier("doi", r["doi"].lower(), r["doi"], Provenance.SEARCHED)
                canon = "https://doi.org/" + r["doi"]
            elif r.get("pmid"):
                ident = Identifier("pmid", r["pmid"], r["pmid"], Provenance.SEARCHED)
                canon = f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/"
            else:
                continue
            return Found(ident, "europepmc", r.get("title") or "", canon, shared, ratio, yr, fa,
                         {"pmid": r.get("pmid"), "doi": r.get("doi"), "journal": r.get("journalTitle")}, _NOW())
        near.append(("europepmc", r.get("title") or ""))
    return None


def _crossref(title: str, first_author: str | None, year: int | None, near: list) -> Found | None:
    st, body, _ = http.get("https://api.crossref.org/works?rows=5&query.bibliographic=" + urllib.parse.quote(title))
    d = _json(body) if st == 200 else None
    for m in ((d or {}).get("message") or {}).get("items") or []:
        cand = (m.get("title") or [""])[0]
        ok, ratio, shared = _title_matches(title, cand)
        authors = m.get("author") or []
        fa = authors[0].get("family") if authors else None
        parts = (m.get("published") or m.get("issued") or {}).get("date-parts", [[None]])[0]
        yr = parts[0] if parts and parts[0] else None
        if ok and _author_ok(first_author, fa) and _year_ok(year, yr) and m.get("DOI"):
            ident = Identifier("doi", m["DOI"].lower(), m["DOI"], Provenance.SEARCHED)
            return Found(ident, "crossref", cand, "https://doi.org/" + m["DOI"], shared, ratio, yr, fa,
                         {"container": (m.get("container-title") or [None])[0], "type": m.get("type")}, _NOW())
        near.append(("crossref", cand))
    return None


def _ctgov(title: str, year: int | None, near: list) -> Found | None:
    st, body, _ = http.get("https://clinicaltrials.gov/api/v2/studies?pageSize=5&fields=protocolSection.identificationModule"
                           "&query.term=" + urllib.parse.quote(title))
    d = _json(body) if st == 200 else None
    for s in (d or {}).get("studies") or []:
        idm = (s.get("protocolSection") or {}).get("identificationModule") or {}
        for cand in (idm.get("officialTitle"), idm.get("briefTitle"), idm.get("acronym")):
            if not cand:
                continue
            ok, ratio, shared = _title_matches(title, cand)
            ok = ok and (ratio >= TRIAL_MATCH_RATIO and len(shared) >= TRIAL_MATCH_MIN or ratio == 1.0)
            if ok and idm.get("nctId"):
                nct = idm["nctId"]
                return Found(Identifier("nct", nct, nct, Provenance.SEARCHED), "clinicaltrials.gov", cand,
                             f"https://clinicaltrials.gov/study/{nct}", shared, ratio, None, None, {}, _NOW())
        near.append(("clinicaltrials.gov", idm.get("briefTitle") or ""))
    return None


def search(title: str, first_author: str | None = None, year: int | None = None,
           kind: str | None = None) -> Found | Unresolved:
    """Find the registry identifier for a proposed publication. `kind` in
    {"trial", "article", None}: trials are asked of ClinicalTrials.gov first."""
    title = (title or "").strip()
    if len(content_tokens(title, LITERATURE_BOILERPLATE)) < 2:
        return Unresolved(title, "title has fewer than two distinctive words; nothing to search on", [], _NOW())
    near: list = []
    # ClinicalTrials.gov is consulted only for a proposal the caller says is a
    # registered trial; it is never a fallback for an article.
    order = [_ctgov, _epmc, _crossref] if kind == "trial" else [_epmc, _crossref]
    for fn in order:
        try:
            found = fn(title, first_author, year, near) if fn is not _ctgov else fn(title, year, near)
        except Exception as exc:                          # a registry outage is "unresolved", never a guess
            near.append((fn.__name__.strip("_"), f"error: {exc}"))
            continue
        if found:
            return found
    return Unresolved(title, "no registry title matched the proposed title (author/year checked where given)", near[:6], _NOW())
