"""Resolve a discover proposal through Europe PMC, PubMed and Crossref (registries.py), matched by title_match.py.
WHU's modules do not import the shared verify package (backend/tests/verify/test_units.py, design doc §8).

A proposal resolves only when a registry returns a record whose title agrees, whose first author agrees and whose
year is within one of the proposal's -- verify/search.py's rules, ported in title_match.py (ruling after P091). The identifiers
come from that record and nowhere else. Anything else is Unresolved, with the reason.

Every registry, every time (advisor's ruling 3 after the fallback build, 2026-11-24; it replaces ruling 2 after
attempt 24's fallback-only lookup): the title is looked up at Europe PMC, PubMed (NCBI E-utilities) and Crossref,
each record held to the same title, author and year checks, and the proposal is confirmed if any registry's record
passes. Every result names each registry asked, whether it answered and whether its record matched (`answered`);
an outage is marked covered (registries.covered) when another registry answered. With no registry answering, the
outages stay and the run stops "registry unavailable; run again later".
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


@dataclass
class Ident:
    kind: str
    value: str


@dataclass
class Found:
    identifier: Ident
    heading: str
    registry: str = "europepmc"
    extra: dict = field(default_factory=dict)


@dataclass
class Unresolved:
    reason: str
    status: str = "NOT_FOUND"
    answered: list = field(default_factory=list)


def _surname(name: str | None) -> str:
    parts = [p for p in (name or "").replace(",", " ").split() if len(p) > 1 or p.isalpha()]
    return parts[0].lower() if parts else ""


def search(title: str, first_author: str | None = None, year: int | None = None, kind: str | None = None,
           lookup=None, registries=None, container: str | None = None):
    """LOOKUP (tests; find_access.epmc's shape, a record or None) keeps the Europe-PMC-only path. Otherwise
    REGISTRIES (default registries.py): Europe PMC, PubMed and Crossref are ALL asked (ruling 3 after the fallback
    build) and the proposal is confirmed if any registry's record passes the checks."""
    if lookup is not None:
        rec = lookup(title, "TITLE")
        if rec is None:
            return Unresolved("Europe PMC returned no record for the title (or did not answer)", "NOT_FOUND")
        return _checked(rec, title, first_author, year, container=container)
    RG = registries or _registries()
    return _every(RG, "title", [lambda: RG.epmc_title(title), lambda: RG.pubmed_title(title),
                                lambda: RG.crossref_title(title, _surname_of(first_author))],
                  title, first_author, year, container=container)


def search_pmcid(pmcid: str, title: str, first_author: str | None = None, year: int | None = None, lookup=None,
                 registries=None, container: str | None = None):
    """An article hosted on PMC (ruling (c), 2026-11-07): confirmed as an article by its PMCID, then held to the
    same title, author and year checks as a title search. Europe PMC and PubMed are both asked by the PMCID; Crossref
    has no PMCID lookup, which is recorded."""
    if lookup is not None:
        rec = lookup(pmcid, "PMCID")
        if rec is None:
            return Unresolved("Europe PMC returned no record for %s (or did not answer)" % pmcid, "NOT_FOUND")
        got = _checked(rec, title, first_author, year, pmcid=pmcid, container=container)
    else:
        RG = registries or _registries()
        got = _every(RG, pmcid, [lambda: RG.epmc_id("PMCID", pmcid), lambda: RG.pubmed_pmcid(pmcid)],
                     title, first_author, year, pmcid=pmcid, container=container,
                     not_asked=[{"registry": "Crossref", "asked": pmcid, "answered": None, "record": None,
                                 "matched": None, "why": "not asked: Crossref has no PMCID lookup"}])
    if isinstance(got, Found):
        got.extra["pmcid"] = got.extra.get("pmcid") or pmcid
    return got


def _registries():
    import registries as RG
    return RG


def _surname_of(name):
    return _surname(name) or None


def _answered(got, rows: list) -> None:
    if isinstance(got, Found):
        got.extra["answered"] = rows
    else:
        got.answered = rows


ORDER = ("europepmc", "pubmed", "crossref")
WORK_KINDS = ("protocol", "erratum", "corrigendum", "correction", "retraction", "review for", "comment on",
              "reply to", "response to", "editorial")


def _norm(s: str) -> str:
    import re
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).split())


def _kind_of(title: str) -> str | None:
    """A title that names a DIFFERENT kind of work about the proposal's subject ("PROTOCOL: ...", "Erratum: ...",
    "Review for ..."), by its lead word."""
    n = _norm(title)
    return next((k for k in WORK_KINDS if n.startswith(k)), None)


def _best_first(records: list, title: str) -> list:
    """A registry's candidates, an exact title match first (found in rehearsal after the fallback build: Crossref's
    first agreeing candidate for "Teacher professional development ... evidence and gap map" was its PROTOCOL), and
    without any record that is a different kind of work (a protocol, an erratum, a review report) unless the proposal
    itself names that kind."""
    want = _kind_of(title)
    keep = [r for r in records if _kind_of(r.get("title") or "") == want]
    exact = [r for r in keep if _norm(r.get("title")) == _norm(title)]
    return exact + [r for r in keep if r not in exact]


def _merge_identifiers(got, others: list) -> None:
    """Identifiers another registry's matching record gives for the SAME work (same DOI, or no DOI on either side)
    are added to the source, each named with the registry that gave it (found in rehearsal after the fallback build:
    Europe PMC's record of S004 had no PMCID and PubMed's had one, so the source depended on which registry was up).
    Nothing the chosen record gives is replaced."""
    mine = (got.identifier.value if got.identifier.kind == "doi" else got.extra.get("doi") or "").lower()
    src = {}
    for f in others:
        theirs = (f.identifier.value if f.identifier.kind == "doi" else "").lower()
        if mine and theirs and mine != theirs:
            continue
        for k in ("pmcid", "pmid"):
            v = f.extra.get(k)
            if v and not got.extra.get(k):
                got.extra[k] = v
                src[k] = f.registry
    if src:
        got.extra["identifiers_from"] = src


def _every(RG, asked: str, asks, title, first_author, year, pmcid=None, not_asked=(), container=None):
    """Every registry in ASKS is asked; each answer's records are held to the checks. The source is the first
    registry's passing record in Europe PMC, PubMed, Crossref order (its identifiers and source-list record); every
    registry asked is recorded with answered and matched. An outage is covered when any registry answered; with
    none answering the outages stay and the run stops "registry unavailable; run again later"."""
    rows, found, reasons, answered, down = [], [], [], [], []
    for ask in asks:
        ans = ask()
        hit = None
        if ans.answered:
            answered.append(ans.registry)
            for rec in _best_first(ans.records or ([ans.record] if ans.record else []), title):
                reg = rec.get("registry") or {"Europe PMC": "europepmc", "PubMed": "pubmed",
                                              "Crossref": "crossref"}.get(ans.registry, ans.registry.lower())
                got = _checked(rec, title, first_author, year, pmcid=pmcid, registry=reg, container=container)
                if isinstance(got, Found):
                    hit = got
                    break
                reasons.append("%s: %s" % (ans.registry, got.reason))
            if hit is None and not (ans.records or ans.record):
                reasons.append("%s: %s" % (ans.registry, ans.why))
        else:
            down.append(ans)
        rows.append(ans.row(asked, matched=hit is not None if ans.answered else None))
        if hit is not None:
            found.append(hit)
    rows += list(not_asked)
    if not answered:
        return Unresolved("no registry answered (%s)" % ", ".join(r["registry"] for r in rows if r.get("answered")
                                                                   is not None), "REGISTRY_UNAVAILABLE", rows)
    for d in down:
        RG.covered(d, answered)
    if found:
        got = found[0]
        got.extra["matched_by"] = [f.registry for f in found]
        _merge_identifiers(got, found[1:])
        _answered(got, rows)
        return got
    return Unresolved("no registry's record agrees (%s answered%s)%s" % (
        ", ".join(answered), "; %s did not" % ", ".join(d.registry for d in down) if down else "",
        (": " + "; ".join(reasons[:4])) if reasons else ""), "NOT_FOUND", rows)


def _checked(rec: dict, title: str, first_author, year, pmcid: str | None = None, registry: str = "europepmc",
             container: str | None = None):
    # advisor's ruling 1 after the P091 build: verify/search.py's rules, ported (title_match.py), replace
    # find_access.titles_agree's shared-words test and the surname-anywhere-in-the-authors test
    import title_match as TM
    ok, why = TM.check(title, first_author, year, rec, proposed_container=container)   # ruling 1 on P118-P121
    if not ok:
        return Unresolved(why)
    if rec.get("doi"):
        ident = Ident("doi", rec["doi"])
    elif rec.get("pmid"):
        ident = Ident("pmid", rec["pmid"])
    elif pmcid and rec.get("pmcid") == pmcid:
        ident = Ident("pmcid", pmcid)
    else:
        return Unresolved("the record carries no DOI or PMID")
    extra = {k: rec.get(k) for k in ("pmcid", "pmid", "license") if rec.get(k)}
    import source_entries as SE
    extra["record"] = SE.record_from_epmc(rec) if registry == "europepmc" else SE.record_from_fallback(rec, registry)
    return Found(ident, rec.get("title") or title, registry, extra)
