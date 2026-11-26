"""Europe PMC, PubMed and Crossref, asked one way (advisor's rulings after orchestrator trial 1 attempt 24,
2026-11-24).

In an orchestrated run every registry call is retried by orch/registry_http.py (4 attempts, backoff 2/4/8 s) and a
registry still unavailable is written to the run's outage log, which stops the run after the step. The rulings:

  * identity / existence lookups fall back from Europe PMC to PubMed (NCBI E-utilities) and Crossref when Europe
    PMC is still unavailable after its retries (orch/resolve.py);
  * retraction and correction status needs answers from at least two of Europe PMC, PubMed and Crossref; with fewer
    answering the run stops "registry unavailable; run again later" (orch/corrections.status, errata.sweep);
  * every status records which registries answered.

So each function here returns an Answer saying whether the registry ANSWERED (a record, or a definite "no record":
HTTP 200 with no hit, or HTTP 404 for a DOI) or did not (HTTP 5xx / 429, a timeout, a connection error: an outage).
When a fallback covers an outage, `covered(answer)` marks that outage line in the run's log so it does not stop the
run; an outage nothing covers still does. Nothing here is typed from memory: identifiers come from the registry's
reply.

Client name: tls.USER_AGENT (generic, no email), and for NCBI `tool=` the same generic name; no API key is sent, so
none can be printed or logged.

Rulings after the fallback build (2026-11-24, P090): identity asks all three registries every time (orch/resolve.py);
a "no record" reply is an answer, an error or timeout never is; Europe PMC's full text falls back to NCBI PMC through
E-utilities (`pmc_fulltext`: the PMC OA Web Service was retired on 2026-08-25 -- NCBI's page says "the PMC OA Web
Service is no longer available" -- and NCBI names E-utilities among the services that may be used for automated
retrieval); every NCBI request, in every mode and from every process, is paced within NCBI's published limit for a
client with no API key, three requests a second (`ncbi_pace`, a lock file shared by all processes).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tls  # noqa: E402

UA = tls.USER_AGENT
NCBI_TOOL = "whu-fetch"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CROSSREF = "https://api.crossref.org/works"
TIMEOUT = 25
PAUSE = {"crossref": 1.0}                      # Crossref asks for restraint; NCBI is paced by ncbi_pace
NCBI_INTERVAL = 0.35          # seconds between NCBI requests: under 3 a second, NCBI's limit with no API key
NCBI_HOSTS = ("eutils.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov")
EUROPE_PMC, PUBMED, CROSSREF_NAME = "Europe PMC", "PubMed", "Crossref"
# PubMed's title search: content words, each [ti]; a quoted title with punctuation finds nothing (checked live
# 2026-11-24: '"<title with a colon>"[ti]' -> 0 hits where the words find it).
STOP = {"and", "the", "for", "with", "from", "into", "of", "in", "on", "a", "an", "to", "or", "not", "by", "at",
        "its", "their", "than", "versus", "vs"}
NOT_A_WORK = {"peer-review", "component", "grant"}      # Crossref types that are never the work itself


@dataclass
class Answer:
    registry: str
    answered: bool
    record: dict | None = None
    records: list = field(default_factory=list)
    why: str = ""
    url: str | None = None

    def row(self, asked: str, matched: bool | None = None) -> dict:
        """What a lookup records about this registry: asked, answered, and (identity) whether its record matched."""
        r = {"registry": self.registry, "asked": asked, "answered": self.answered,
             "record": "found" if (self.record or self.records) else ("none" if self.answered else None),
             "why": self.why[:300]}
        if matched is not None:
            r["matched"] = matched
        return r


def transient(e: Exception) -> bool:
    """An outage, not an answer (the same classes orch/registry_http.py retries)."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code == 429
    return isinstance(e, (TimeoutError, ConnectionError, urllib.error.URLError, OSError, ValueError))


def pace_file() -> Path:
    import os
    return Path(os.environ.get("WHU_NCBI_PACE_FILE") or (Path.home() / ".cache" / "whu" / "ncbi_pace"))


def ncbi_pace(now=time.time, sleep=time.sleep) -> float:
    """Wait until NCBI_INTERVAL has passed since the last NCBI request from ANY process on this machine, then record
    this one. Returns the seconds waited."""
    import fcntl
    p = pace_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            last = float(fh.read().strip() or 0)
        except ValueError:
            last = 0.0
        wait = max(0.0, last + NCBI_INTERVAL - now())
        if wait:
            sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write("%.6f" % now())
        fh.flush()
    return wait


def is_ncbi(url: str) -> bool:
    return (urllib.parse.urlsplit(url).hostname or "").lower() in NCBI_HOSTS


def served_locally(url: str) -> bool:
    """In a rehearsal (WHU_ORCH_MODE=rehearse), whether URL is answered without the network: offline, or already in
    the rehearsal's record-then-replay cache (orch/rehearsal._key of a GET). A request that is never sent needs no
    pacing; a live one is paced by the rehearsal's cache before it goes out (advisor's ruling 2 on the replay gate)."""
    import hashlib
    import os
    if os.environ.get("WHU_ORCH_MODE") != "rehearse":
        return False
    if os.environ.get("WHU_REHEARSE_OFFLINE") == "1":
        return True
    d = Path(os.environ.get("WHU_REHEARSE_HTTP") or (Path.home() / "Projects" / "whu-study-private" / "rehearsal_http"))
    return (d / (hashlib.sha256((url + "\n").encode()).hexdigest() + ".json")).exists()


def _get(url: str) -> tuple[bool, bytes | None, str]:
    """(answered, body or None, why). A 4xx other than 429 is an answer with no body (404: no such record)."""
    if is_ncbi(url) and not served_locally(url):
        ncbi_pace()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with tls.urlopen(req, timeout=TIMEOUT) as fh:          # verified, as every WHU fetch
            return True, fh.read(), "HTTP 200"
    except urllib.error.HTTPError as e:
        if transient(e):
            return False, None, "HTTP %s" % e.code
        return True, None, "HTTP %s" % e.code
    except Exception as e:                       # timeouts, resets, DNS: an outage
        return False, None, "%s: %s" % (type(e).__name__, e)


def _json(url: str) -> tuple[bool, dict | None, str]:
    ok, body, why = _get(url)
    if not ok or body is None:
        return ok, None, why
    try:
        return True, json.loads(body.decode("utf-8", "replace")), why
    except ValueError:                           # a body cut off mid-stream is not an answer
        return False, None, "unparseable JSON reply"


def _pause(reg: str, url: str | None = None) -> None:
    if url and served_locally(url):
        return                                   # never sent (a rehearsal's cache or offline): nothing to restrain
    time.sleep(PAUSE.get(reg, 0))


# ---- the outage log ------------------------------------------------------------------------------------------

def _wrapper():
    """orch/registry_http.py as loaded in this process: by the orchestrator (orch.registry_http) or by a step's
    subprocess through orch/site/sitecustomize.py (whu_registry_http). None outside an orchestrated run."""
    for name in ("whu_registry_http", "orch.registry_http"):
        m = sys.modules.get(name)
        if m is not None and getattr(m, "installed", lambda: False)():
            return m
    return None


def covered(answer: Answer, by: list[str]) -> None:
    """ANSWER's outage was covered by the registries BY (which answered): it does not stop the run."""
    m = _wrapper()
    if m is not None and answer.url and not answer.answered:
        m.covered(answer.url, by)


# ---- Europe PMC --------------------------------------------------------------------------------------------

def epmc_query(query: str, page_size: int | None = 1) -> Answer:
    params = {"query": query, "resultType": "core", "format": "json"}
    if page_size:
        params["pageSize"] = str(page_size)
    url = EPMC + "?" + urllib.parse.urlencode(params)
    ok, d, why = _json(url)
    if not ok:
        return Answer(EUROPE_PMC, False, why="Europe PMC did not answer (%s)" % why, url=url)
    hits = ((d or {}).get("resultList") or {}).get("result") or []
    return Answer(EUROPE_PMC, True, hits[0] if hits else None, hits,
                  "matched" if hits else "Europe PMC has no record (%s)" % query[:120], url)


def epmc_title(title: str) -> Answer:
    """The request find_access.epmc makes for a title (the same URL, so recorded replies still match)."""
    url = EPMC + "?query=%s&resultType=core&format=json" % urllib.parse.quote('TITLE:"%s"' % title)
    ok, d, why = _json(url)
    if not ok:
        return Answer(EUROPE_PMC, False, why="Europe PMC did not answer (%s)" % why, url=url)
    hits = ((d or {}).get("resultList") or {}).get("result") or []
    return Answer(EUROPE_PMC, True, hits[0] if hits else None, hits,
                  "matched" if hits else "Europe PMC has no record for the title", url)


def epmc_id(kind: str, value: str) -> Answer:
    q = {"DOI": 'DOI:"%s"', "PMID": "EXT_ID:%s", "PMCID": "PMCID:%s", "PII": '"%s"'}[kind] % value
    return epmc_query(q)


# ---- PubMed (NCBI E-utilities) -----------------------------------------------------------------------------

def _eutils(name: str, **params) -> str:
    return EUTILS + name + ".fcgi?" + urllib.parse.urlencode(dict(params, tool=NCBI_TOOL))


def _esearch(term: str, retmax: int = 5) -> Answer:
    url = _eutils("esearch", db="pubmed", term=term, retmode="json", retmax=retmax)
    ok, d, why = _json(url)
    if not ok:
        return Answer(PUBMED, False, why="PubMed did not answer (%s)" % why, url=url)
    ids = ((d or {}).get("esearchresult") or {}).get("idlist") or []
    return Answer(PUBMED, True, records=list(ids), why="%d hit(s)" % len(ids), url=url)


def _summaries(pmids: list[str]) -> Answer:
    url = _eutils("esummary", db="pubmed", id=",".join(pmids), retmode="json")
    ok, d, why = _json(url)
    if not ok:
        return Answer(PUBMED, False, why="PubMed did not answer (%s)" % why, url=url)
    res = (d or {}).get("result") or {}
    return Answer(PUBMED, True, records=[epmc_shaped_from_summary(res[i]) for i in pmids if i in res],
                  why="summaries", url=url)


def epmc_shaped_from_summary(r: dict) -> dict:
    """A PubMed esummary record in the fields orch/resolve.py checks (title, authorString, pubYear, doi, pmid,
    pmcid, journalTitle)."""
    ids = {a.get("idtype"): a.get("value") for a in r.get("articleids") or []}
    pmc = ids.get("pmc") or ""
    m = re.search(r"PMC\d+", pmc)
    names = [" ".join((a.get("name") or "").split()) for a in r.get("authors") or [] if (a.get("name") or "").strip()]
    return {"title": (r.get("title") or "").rstrip(), "authorString": ", ".join(names), "authors": names,
            "pubYear": (r.get("pubdate") or "")[:4], "doi": ids.get("doi"), "pmid": str(r.get("uid") or ""),
            "pmcid": m.group(0) if m else None, "journalTitle": r.get("fulljournalname") or r.get("source"),
            "registry": "pubmed"}


def title_term(title: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", title or "") if len(w) > 2 and w.lower() not in STOP]
    return " AND ".join("%s[ti]" % w for w in words[:20])


def pubmed_title(title: str) -> Answer:
    s = _esearch(title_term(title))
    if not s.answered or not s.records:
        return Answer(PUBMED, s.answered, why=s.why if not s.answered else "PubMed has no record for the title",
                      url=s.url)
    return _summaries(s.records[:5])


def pubmed_pmcid(pmcid: str) -> Answer:
    s = _esearch("%s[pmcid]" % pmcid, 1)
    if not s.answered or not s.records:
        return Answer(PUBMED, s.answered, why=s.why if not s.answered else "PubMed has no record for %s" % pmcid,
                      url=s.url)
    return _summaries(s.records[:1])


def parse_efetch(xml: str) -> dict:
    """The status fields of one PubMed record (efetch, retmode xml): title, publication types, the
    CommentsCorrections links, and its DOI / PMCID."""
    def one(pat):
        m = re.search(pat, xml, re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None
    links = []
    for m in re.finditer(r'<CommentsCorrections RefType="([^"]+)">(.*?)</CommentsCorrections>', xml, re.S):
        pm = re.search(r"<PMID[^>]*>(\d+)</PMID>", m.group(2))
        src = re.search(r"<RefSource>(.*?)</RefSource>", m.group(2), re.S)
        links.append({"type": m.group(1), "pmid": pm.group(1) if pm else None,
                      "source": (src.group(1).strip() if src else "")[:200]})
    # the record's own identifiers: the first ArticleIdList in PubmedData (a ReferenceList's ArticleIds are the
    # cited works')
    m = re.search(r"<PubmedData>.*?<ArticleIdList>(.*?)</ArticleIdList>", xml, re.S)
    own = m.group(1) if m else ""
    doi = re.search(r'<ArticleId IdType="doi">([^<]+)</ArticleId>', own)
    pmc = re.search(r'<ArticleId IdType="pmc">([^<]+)</ArticleId>', own)
    abst = re.search(r"<Abstract>(.*?)</Abstract>", xml, re.S)
    return {"title": one(r"<ArticleTitle[^>]*>(.*?)</ArticleTitle>") or "",
            "abstract": " ".join(re.sub(r"<[^>]+>", " ", abst.group(1)).split()) if abst else "",
            "pmid": one(r"<PMID[^>]*>(\d+)</PMID>"),
            "pubtypes": re.findall(r"<PublicationType[^>]*>([^<]+)</PublicationType>", xml),
            "links": links,
            "doi": doi.group(1).strip() if doi else None,
            "pmcid": pmc.group(1).strip() if pmc else None}


def pubmed_record(kind: str, value: str) -> Answer:
    """One PubMed record by PMID, or found by DOI / PMCID, with its status fields."""
    pmid = value if kind == "PMID" else None
    if pmid is None:
        if kind not in ("DOI", "PMCID"):
            return Answer(PUBMED, True, why="PubMed is not asked for a %s" % kind)
        s = _esearch('"%s"[%s]' % (value, "doi" if kind == "DOI" else "pmcid"), 2)
        if not s.answered:
            return Answer(PUBMED, False, why=s.why, url=s.url)
        if len(s.records) != 1:
            return Answer(PUBMED, True, why="PubMed has %s record for %s %s" % (
                "no" if not s.records else "more than one", kind, value), url=s.url)
        pmid = s.records[0]
    url = _eutils("efetch", db="pubmed", id=pmid, retmode="xml")
    ok, body, why = _get(url)
    if not ok:
        return Answer(PUBMED, False, why="PubMed did not answer (%s)" % why, url=url)
    xml = (body or b"").decode("utf-8", "replace")
    if "<PubmedArticle>" not in xml and "<PubmedArticle " not in xml:
        return Answer(PUBMED, True, why="PubMed has no record for PMID %s" % pmid, url=url)
    return Answer(PUBMED, True, parse_efetch(xml), why="matched on PMID %s" % pmid, url=url)


def pmc_fulltext_url(pmcid: str) -> str:
    return _eutils("efetch", db="pmc", id=re.sub(r"^PMC", "", pmcid.upper()), retmode="xml")


def pmc_fulltext(pmcid: str) -> Answer:
    """NCBI PMC's copy of an article through E-utilities (efetch db=pmc), the fallback when Europe PMC's full text is
    unavailable (ruling 2 after the fallback build). The copy rule is Europe PMC's (only the open-access subset is
    requested there, isOpenAccess "Y"): efetch returns the article <body> only where the publisher allows it --
    otherwise "The publisher of this article does not allow downloading of the full text in XML form" -- and a copy is
    used only if it has a body AND a licence statement (<license>), which is recorded. record = {"xml", "licence"}."""
    url = pmc_fulltext_url(pmcid)
    ok, body, why = _get(url)
    if not ok:
        return Answer("PMC", False, why="NCBI PMC did not answer (%s)" % why, url=url)
    xml = (body or b"").decode("utf-8", "replace")
    if "<body" not in xml:
        m = re.search(r"<!--\s*(The publisher[^>]*?)\s*-->", xml)
        return Answer("PMC", True, why="not served: NCBI PMC %s" % (
            m.group(1) if m else "returned no article body for %s" % pmcid), url=url)
    lic = re.search(r"<license\b[^>]*>(.*?)</license>", xml, re.S)
    if not lic:
        return Answer("PMC", True, why="not served: NCBI PMC's copy of %s carries no licence statement" % pmcid,
                      url=url)
    href = re.search(r'(https?://creativecommons\.org/[^"<\s]+)', lic.group(0))
    text = " ".join(re.sub(r"<[^>]+>", " ", lic.group(1)).split())[:300]
    return Answer("PMC", True, {"xml": xml, "licence": {"url": href.group(1) if href else None, "statement": text}},
                  why="NCBI PMC full text %s (E-utilities efetch)" % pmcid, url=url)


# ---- Crossref ----------------------------------------------------------------------------------------------

# A trailing tenure qualifier on an organisational author name, as library name authorities write it:
# "UNESCO. Assistant Director-General for Education, 2010-2018 (Qian Tang)" (attempt 24's S006).
TENURE = re.compile(r",\s*(?:19|20)\d{2}\s*[-\u2013]\s*(?:(?:19|20)\d{2})?\s*\([^()]*\)\s*$")


def crossref_authors(it: dict) -> tuple[list[str], list[str]]:
    """(shown, registry) author names from Crossref's structured fields (advisor's ruling 1 after attempt 24's fresh
    run): a person is family + initials of given; an organisation is its `name`, with a trailing tenure qualifier
    (", YYYY-YYYY (...)") dropped from the shown name only. `registry` keeps each name exactly as Crossref gives it.
    Names are kept as list items -- never joined and split again, so a comma inside a name stays inside it."""
    shown, full = [], []
    for a in it.get("author") or []:
        if a.get("family"):
            ini = "".join(p[0] for p in re.split(r"[\s.\-]+", a.get("given") or "") if p)
            name = ("%s %s" % (a["family"].strip(), ini)).strip()
            raw = ("%s, %s" % (a["family"].strip(), (a.get("given") or "").strip())).strip(", ")
        elif a.get("name"):
            raw = " ".join(a["name"].split())
            name = TENURE.sub("", raw).strip()
        else:
            continue
        if name:
            shown.append(name)
            full.append(raw)
    return shown, full


def epmc_shaped_from_crossref(it: dict) -> dict:
    authors, registry_authors = crossref_authors(it)
    parts = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
    return {"title": (it.get("title") or [""])[0], "authorString": ", ".join(a for a in authors if a),
            "authors": authors, "authors_registry": registry_authors,
            "pubYear": str(parts[0]) if parts and parts[0] else "", "doi": it.get("DOI"),
            "journalTitle": (it.get("container-title") or [None])[0], "registry": "crossref",
            "type": it.get("type")}


def crossref_title(title: str, first_author: str | None = None) -> Answer:
    params = {"query.bibliographic": title, "rows": 10,
              "select": "DOI,title,author,issued,container-title,type"}
    if first_author:
        params["query.author"] = first_author
    url = CROSSREF + "?" + urllib.parse.urlencode(params)
    ok, d, why = _json(url)
    _pause("crossref", url)
    if not ok:
        return Answer(CROSSREF_NAME, False, why="Crossref did not answer (%s)" % why, url=url)
    items = [it for it in ((d or {}).get("message") or {}).get("items") or [] if it.get("type") not in NOT_A_WORK]
    return Answer(CROSSREF_NAME, True, records=[epmc_shaped_from_crossref(it) for it in items],
                  why="%d candidate(s)" % len(items), url=url)


def crossref_work(doi: str) -> Answer:
    url = CROSSREF + "/" + urllib.parse.quote(doi, safe="")
    ok, d, why = _json(url)
    _pause("crossref", url)
    if not ok:
        return Answer(CROSSREF_NAME, False, why="Crossref did not answer (%s)" % why, url=url)
    msg = (d or {}).get("message")
    if not isinstance(msg, dict):
        return Answer(CROSSREF_NAME, True, why="Crossref has no record for DOI %s (%s)" % (doi, why), url=url)
    return Answer(CROSSREF_NAME, True, msg, why="matched on DOI %s at Crossref" % doi, url=url)
