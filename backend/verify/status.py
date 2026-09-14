"""The fifth check: retraction, correction, withdrawal, amendment — STATUS.

The four binding kinds read the document. A retracted paper's text is
unchanged, so HEADING, FIGURE, SPAN and APPLICABILITY all pass it. Retraction
is a status query against the registry's metadata, and it is its own check
with its own verdict (design doc, Phase 3 §3). If it is not separate it does
not exist.

Verdicts: retracted | withdrawn | concern | corrected | trial_status_changed |
record_updated | amended | reissued | unchanged | unknown. `unknown` means the
query failed; it is never reported as unchanged -- an absence reported by
something not in a position to observe it is this project's recurring error.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
from dataclasses import dataclass, field

from . import http
from .types import Identifier

_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731

RETRACTION_TYPES = {"retraction", "retracted", "withdrawal", "withdrawn", "removal"}
CORRECTION_TYPES = {"correction", "corrigendum", "erratum", "addendum", "new_edition", "new_version", "partial_retraction"}
CONCERN_TYPES = {"expression_of_concern", "expression-of-concern", "concern"}


@dataclass
class Status:
    identifier: Identifier
    verdict: str
    checked_at: str = ""
    registry: str = ""
    detail: str = ""
    events: list = field(default_factory=list)     # [{type, date, doi/id, source}]
    frozen: dict = field(default_factory=dict)     # what we compared against, when given

    @property
    def alerts(self) -> bool:
        return self.verdict in ("retracted", "withdrawn", "concern", "corrected", "trial_status_changed",
                                "amended", "reissued")


def _json(body: bytes):
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None


def _classify(types: set[str]) -> str:
    if types & RETRACTION_TYPES:
        return "retracted"
    if types & CONCERN_TYPES:
        return "concern"
    if types & CORRECTION_TYPES:
        return "corrected"
    return "unchanged"


# ---------------------------------------------------------------------------
# literature
# ---------------------------------------------------------------------------
def _crossref(ident: Identifier, st: Status) -> Status:
    code, body, _ = http.get("https://api.crossref.org/works/" + urllib.parse.quote(ident.value))
    d = _json(body) if code == 200 else None
    if d is None:
        st.verdict = "unknown"; st.detail = f"crossref HTTP {code}"; return st
    msg = d.get("message", {})
    st.registry = "crossref"
    types = set()
    for u in msg.get("update-to") or []:
        t = (u.get("type") or "").lower().replace(" ", "_")
        types.add(t)
        st.events.append({"type": t, "date": "-".join(str(x) for x in (u.get("updated") or {}).get("date-parts", [[None]])[0]),
                          "doi": u.get("DOI"), "source": "crossref update-to", "label": u.get("label")})
    rel = msg.get("relation") or {}
    for key, t in (("is-retracted-by", "retraction"), ("has-erratum", "erratum"), ("has-correction", "correction"),
                   ("is-corrected-by", "correction")):
        for r in rel.get(key) or []:
            types.add(t); st.events.append({"type": t, "date": None, "doi": r.get("id"), "source": f"crossref relation {key}"})
    # A retraction NOTICE resolves as its own work whose update-to points at
    # the retracted paper. That is not the notice being retracted: it is a
    # notice. Report it as such, and never as an alert on itself.
    targets = {(u.get("DOI") or "").lower() for u in msg.get("update-to") or []}
    if targets and ident.value.lower() not in targets:
        st.verdict = "retraction_notice" if types & RETRACTION_TYPES else "correction_notice"
        st.detail = "this DOI is a notice about " + ", ".join(sorted(targets))
        return st
    # THE PAPER'S OWN RECORD DOES NOT CARRY ITS RETRACTION. Wakefield 1998
    # (10.1016/S0140-6736(97)11096-0, retracted 2010) has no update-to and no
    # is-retracted-by on its record; the notice points at it, not the other
    # way. So ask Crossref the reverse question: which works UPDATE this DOI.
    code, body, _ = http.get("https://api.crossref.org/works?filter=updates:" + urllib.parse.quote(ident.value) + "&rows=10")
    d2 = _json(body) if code == 200 else None
    for w in ((d2 or {}).get("message") or {}).get("items") or []:
        for u in w.get("update-to") or []:
            if (u.get("DOI") or "").lower() != ident.value.lower():
                continue
            t = (u.get("type") or "").lower().replace(" ", "_")
            types.add(t)
            st.events.append({"type": t, "date": "-".join(str(x) for x in (u.get("updated") or {}).get("date-parts", [[None]])[0]),
                              "doi": w.get("DOI"), "source": "crossref filter=updates", "label": u.get("label"),
                              "title": (w.get("title") or [None])[0]})
    st.verdict = _classify(types)
    st.detail = f"{len(st.events)} update/relation event(s)" if st.events else "no update-to, relation, or updating work"
    return st


def _europepmc(ident: Identifier, st: Status) -> Status:
    # The DOI is quoted: parentheses in an Elsevier PII DOI otherwise break
    # the query and the search returns nothing, which read as "no record".
    q = {"doi": f'DOI:"{ident.value}"', "pmid": f"EXT_ID:{ident.value} AND SRC:MED", "pmcid": f"PMCID:{ident.value}"}[ident.system]
    code, body, _ = http.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                             + urllib.parse.quote(q) + "&format=json&pageSize=1&resultType=core")
    d = _json(body) if code == 200 else None
    hits = ((d or {}).get("resultList") or {}).get("result") or []
    if d is None or not hits:
        if st.verdict == "unchanged" and d is None:
            st.verdict = "unknown"; st.detail += "; europepmc unavailable"
        return st
    r0 = hits[0]
    types = set()
    for c in (r0.get("commentCorrectionList") or {}).get("commentCorrection") or []:
        t = (c.get("type") or "").lower()
        if "retraction in" in t or "retracted" in t:
            types.add("retraction")
        elif "erratum" in t or "correction" in t:
            types.add("erratum")
        elif "concern" in t:
            types.add("expression_of_concern")
        st.events.append({"type": t, "date": None, "id": c.get("id"), "source": "europepmc commentCorrectionList"})
    for pt in (r0.get("pubTypeList") or {}).get("pubType") or []:
        if pt.lower() in ("retracted publication", "retraction of publication"):
            types.add("retracted"); st.events.append({"type": pt, "source": "europepmc pubType"})
    v = _classify(types)
    order = ["unchanged", "corrected", "concern", "retracted"]
    if order.index(v) > order.index(st.verdict if st.verdict in order else "unchanged"):
        st.verdict = v
    st.registry = (st.registry + "+" if st.registry else "") + "europepmc"
    return st


def _nct(ident: Identifier, st: Status, frozen: dict | None) -> Status:
    code, body, _ = http.get(f"https://clinicaltrials.gov/api/v2/studies/{ident.value}?fields=protocolSection.statusModule")
    d = _json(body) if code == 200 else None
    if d is None:
        st.verdict = "unknown"; st.detail = f"clinicaltrials.gov HTTP {code}"; return st
    sm = (d.get("protocolSection") or {}).get("statusModule") or {}
    st.registry = "clinicaltrials.gov"
    now = {"overallStatus": sm.get("overallStatus"), "whyStopped": sm.get("whyStopped"),
           "lastUpdatePostDate": (sm.get("lastUpdatePostDateStruct") or {}).get("date"),
           "resultsFirstPostDate": (sm.get("resultsFirstPostDateStruct") or {}).get("date")}
    st.events.append({"type": "status", **now, "source": "ctgov statusModule"})
    if sm.get("overallStatus") in ("WITHDRAWN",):
        st.verdict = "withdrawn"
    elif frozen:
        if frozen.get("overallStatus") and frozen["overallStatus"] != now["overallStatus"]:
            st.verdict = "trial_status_changed"; st.detail = f"{frozen['overallStatus']} -> {now['overallStatus']}"
        elif frozen.get("lastUpdatePostDate") and now["lastUpdatePostDate"] and now["lastUpdatePostDate"] > frozen["lastUpdatePostDate"]:
            st.verdict = "record_updated"; st.detail = f"record updated {now['lastUpdatePostDate']} (frozen {frozen['lastUpdatePostDate']})"
        else:
            st.verdict = "unchanged"
    else:
        st.verdict = "unchanged"; st.detail = now["overallStatus"] or ""
    return st


# ---------------------------------------------------------------------------
# law
# ---------------------------------------------------------------------------
def _cfr(ident: Identifier, st: Status, frozen: dict | None) -> Status:
    title, rest = ident.value.split(":", 1)
    section = re.match(r"[\d.]+", rest).group(0)
    code, body, _ = http.get(f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?section={section}")
    d = _json(body) if code == 200 else None
    if d is None:
        st.verdict = "unknown"; st.detail = f"ecfr versions HTTP {code}"; return st
    st.registry = "ecfr"
    dates = sorted({v.get("date") for v in d.get("content_versions") or [] if v.get("date")})
    st.events = [{"type": "version", "date": x, "source": "ecfr content_versions"} for x in dates]
    as_of = (frozen or {}).get("as_of")
    newer = [x for x in dates if as_of and x > as_of]
    st.verdict = "amended" if newer else "unchanged"
    st.detail = f"latest version {dates[-1] if dates else 'none'}; frozen as_of {as_of}"
    return st


def _ohio(ident: Identifier, st: Status, frozen: dict | None) -> Status:
    url = (f"https://codes.ohio.gov/ohio-revised-code/section-{ident.value}" if ident.system == "orc"
           else f"https://codes.ohio.gov/ohio-administrative-code/rule-{ident.value}")
    code, body, _ = http.get(url)
    if code != 200:
        st.verdict = "unknown"; st.detail = f"codes.ohio.gov HTTP {code}"; return st
    page = body.decode("utf-8", "replace")
    st.registry = "codes.ohio.gov"
    eff = re.search(r"Effective:\s*</?[^>]*>?\s*([A-Za-z]+ \d{1,2}, \d{4})", re.sub(r"\s+", " ", page))
    leg = re.search(r"Latest Legislation:\s*</?[^>]*>?\s*([^<]{3,80})", re.sub(r"\s+", " ", page))
    now = {"effective": eff.group(1).strip() if eff else None, "latest_legislation": leg.group(1).strip() if leg else None}
    st.events.append({"type": "effective", **now, "source": "codes.ohio.gov page"})
    f = frozen or {}
    if f.get("effective") and now["effective"] and f["effective"] != now["effective"]:
        st.verdict = "amended"; st.detail = f"effective {f['effective']} -> {now['effective']}"
    else:
        st.verdict = "unchanged"; st.detail = f"effective {now['effective']}"
    return st


def _iom(ident: Identifier, st: Status, frozen: dict | None) -> Status:
    # The section's transmittal line "(Rev. NNNN, Issued: MM-DD-YY ...)" is
    # what changes when CMS reissues it. It is read from the fetched section
    # text at publish time and again here by refetching through law.fetch.
    from . import law
    res = law.resolve(ident); doc = law.fetch(res)
    if doc is None:
        st.verdict = "unknown"; st.detail = "chapter not fetched"; return st
    st.registry = "cms.gov"
    m = re.search(r"\(Rev\.\s*(\d+)[^)]*\)", doc.text)
    now = m.group(0) if m else None
    st.events.append({"type": "transmittal", "rev": now, "source": "section text"})
    f = frozen or {}
    if f.get("rev") and now and f["rev"] != now:
        st.verdict = "reissued"; st.detail = f"{f['rev']} -> {now}"
    else:
        st.verdict = "unchanged"; st.detail = now or "no transmittal line"
    return st


def _ncci(ident: Identifier, st: Status, frozen: dict | None) -> Status:
    from . import law
    res = law.resolve(ident)
    year = (res.extra or {}).get("year")
    st.registry = "cms.gov"
    f = frozen or {}
    if year is None:
        st.verdict = "unknown"; st.detail = "manual not fetched"; return st
    st.events.append({"type": "manual_year", "year": year})
    st.verdict = "reissued" if f.get("year") and f["year"] != year else "unchanged"
    st.detail = f"manual year {year}" + (f" (frozen {f['year']})" if f.get("year") else "")
    return st


def check(ident: Identifier, frozen: dict | None = None) -> Status:
    """The status of one identifier now, compared with what was frozen (if given)."""
    st = Status(ident, "unchanged", _NOW(), frozen=frozen or {})
    if ident.system == "doi":
        st = _crossref(ident, st)
        return _europepmc(ident, st)
    if ident.system in ("pmid", "pmcid"):
        return _europepmc(ident, st)
    if ident.system == "nct":
        return _nct(ident, st, frozen)
    if ident.system == "cfr":
        return _cfr(ident, st, frozen)
    if ident.system in ("orc", "oac"):
        return _ohio(ident, st, frozen)
    if ident.system == "cms_iom":
        return _iom(ident, st, frozen)
    if ident.system == "ncci":
        return _ncci(ident, st, frozen)
    st.verdict = "unknown"; st.detail = "no status adapter for this system"
    return st
