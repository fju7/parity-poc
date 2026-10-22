#!/usr/bin/env python3
"""Build the study's sampling frames (protocol, "Question selection"; rev 33,
rev 34 and rev 34 amended 2026-10-21).

    frames.py cochrane|campbell|ipcc [--out DIR]    the study frames (STUDY_DRAW_PLAN)
    frames.py ipcc-ar5-practice [--out DIR]          the practice frame (IPCC AR5 SPMs)
    frames.py draw-ipcc-ar5-practice --seed N        the practice draw
    frames.py draw-cochrane|draw-campbell|draw-ipcc --commit HASH --cache DIR
                                                     the study draw (protocol rev 38)
    frames.py nasem-list|nasem-practice-list         National Academies (dropped; kept for the record)

Each frame is written to DIR/<frame>.json (default study/whu-reliability/frames/):
every candidate the registry returned, numbered in a fixed order, with each
eligibility test's result and what it rested on, and every query made, with
its URL and UTC date. The eligible entries are numbered 1..N in "eligible"
(the order the draw uses); nothing is drawn here.

ELIGIBILITY (protocol): published January 2024 to September 2026 (IPCC AR6:
2021 to 2023); states its main conclusion with a certainty grade; has at least
its full abstract publicly readable; not on a topic WHU has published or
tested. Each test is mechanical and the same for every entry of a frame; how
each is applied is in the frame file's "tests". "can be put as one plain
question a non-expert would ask" is not tested here: the protocol leaves it to
the closer reading after the draw ("If a drawn review fails eligibility on
closer reading, draw the next, and log why").

REGISTRIES. Cochrane and Campbell: PubMed E-utilities (esearch + efetch).
National Academies: Crossref (prefix 10.17226) for the list, then each
publication's own page on nationalacademies.org for its type (the page's
publicationsDataLayer "sub_type") and year, and its OpenBook Summary chapter
for the certainty test. IPCC AR6: there is no API; the four official
"SPM headline statements" pages on ipcc.ch are fetched, and each statement is
one entry. Fetched pages are cached under the scratch directory --cache (not
committed: other people's text) and identified here by sha256.

Nothing here calls a model. Free.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html as H
import json
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
OUT = STUDY / "frames"
UA = "WHU-reliability-study frames.py (mailto:fred.ugast@uspv.co)"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

STUDY_WINDOW = ("2024-01-01", "2026-09-30")

# The study's draw plan, protocol rev 34 (amended 2026-10-21): questions per
# study frame. The National Academies frame is dropped: outside health, its
# reports do not grade conclusions on an evidence scale, so the frame is empty
# under the grade test (the stopped practice redraw: 227 of 262 checked, none
# eligible). Nothing is drawn for the study here.
STUDY_DRAW_PLAN = {"cochrane": 1, "campbell": 1, "ipcc": 2}
DROPPED_FRAMES = {"nasem": "protocol rev 34 (amended 2026-10-21): outside health, National Academies reports do not "
                           "grade conclusions on an evidence scale, so the frame is empty under the grade test"}
# The practice frame (rev 34, amended): IPCC AR5 numbered SPM statements (ipcc_ar5_frame).
PRACTICE_FRAME = "ipcc-ar5-practice"
IPCC_WINDOW = ("2021-01-01", "2023-12-31")
PRACTICE_WINDOW = ("2017-01-01", "2023-12-31")

# Topics WHU has published (melanoma, cdk46, deskilling) or tested (the
# pilot's four questions, T01-T04, and the practice run WHU-P02), as title
# patterns. A match excludes the entry; the matched words are recorded.
EXCLUDED_TOPICS = {
    "WHU-001 melanoma (personalised mRNA cancer vaccine)": r"\bmelanoma|\bm?RNA[- ](?:based )?(?:cancer )?vaccin|personali[sz]ed (?:cancer )?vaccin",
    "WHU-002 cdk46 (CDK4/6 inhibitors)": r"\bCDK ?4/6|\bCDK4\b|palbociclib|ribociclib|abemaciclib|cyclin[- ]dependent kinase 4",
    "WHU-003 deskilling (AI use and human cognition)": r"(?:artificial intelligence|\bAI\b|large language model|\bLLMs?\b|chatbot|ChatGPT|generative)"
                                                        r".{0,80}(?:cogniti|critical thinking|deskill|skill|learning|memory|reasoning)"
                                                        r"|(?:cogniti|critical thinking|deskill)\w*.{0,80}(?:artificial intelligence|\bAI\b|large language model|chatbot)",
    "T01 exercise and depression": r"(?:exercise|physical activity|physical training|yoga|walking).{0,80}depress|depress\w*.{0,80}(?:exercise|physical activity)",
    "T02 / WHU-P02 ultra-processed foods": r"ultra-?processed|\bprocessed foods?\b|\bNOVA\b",
    "T03 intermittent fasting": r"intermittent fasting|time-restricted (?:eating|feeding)|alternate[- ]day fasting|\b5:2\b|periodic fasting",
    # Protocol rev 34: narrowed from every vitamin D review to reviews of vitamin
    # D supplementation in older adults (T04 asked about people over 60). The
    # title must name vitamin D and an older population.
    "T04 vitamin D (supplementation in older adults)": r"^(?=.*\b(?:vitamin D|cholecalciferol|ergocalciferol|calcifediol|calcitriol)\b)"
                                                       r"(?=.*\b(?:older (?:adults?|people|persons?|women|men|individuals|patients)"
                                                       r"|elderly|aged (?:60|65|70)|over (?:60|65|70)|(?:60|65|70) years (?:and|or) (?:over|older)"
                                                       r"|later life|old age|seniors?|geriatric|nursing homes?|care homes?|long-term care))",
}

# Certainty grade in a review abstract: GRADE certainty or quality terms, or
# an explicit strength-of-evidence statement.
GRADE_TERMS = re.compile(
    r"\b(?:high|moderate|low|very[- ]low)[- ](?:certainty|quality)\b"
    r"|\bcertainty of (?:the )?evidence\b|\bquality of (?:the )?evidence\b|\bGRADE\b"
    r"|\bstrength of (?:the )?evidence\b", re.I)

# Graded conclusions in a National Academies Summary: at least three levels of
# one evidence scale ("conclusive / substantial / moderate / limited evidence
# of ..."), or two levels of confidence or certainty language.
EVIDENCE_LEVEL = re.compile(
    r"\b(conclusive|substantial|moderate|limited|insufficient|inadequate|sufficient|suggestive|strong|weak)"
    r"(?:\s*(?:/|or|and)\s*\w+)?\s+evidence\s+(?:of|that|for|to|exists|is)\b", re.I)
CONFIDENCE_LEVEL = re.compile(r"\b(very high|high|medium|moderate|low|very low)\s+(confidence|certainty)\b", re.I)

# IPCC AR6 calibrated language (Mastrandrea et al. 2010 guidance note).
IPCC_CALIBRATED = re.compile(
    r"\b(?:very high|high|medium|low|very low)\s+confidence\b"
    r"|\b(?:virtually certain|extremely likely|very likely|likely|more likely than not|about as likely as not"
    r"|unlikely|very unlikely|extremely unlikely|exceptionally unlikely)\b", re.I)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(b: bytes | str) -> str:
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


class Fetcher:
    """GET with a polite pause, a cache on disk, and a log of every query."""

    def __init__(self, cache: Path, pause: float = 0.35, nap_pause: float = 3.0):
        self.cache, self.pause, self.nap_pause, self.log = cache, pause, nap_pause, []
        self.offline = False          # cache only: an uncached page is returned as status 0, unfetched
        self.client = httpx.Client(headers={"User-Agent": UA, "Accept-Encoding": "gzip"},
                                   timeout=60, follow_redirects=True)
        cache.mkdir(parents=True, exist_ok=True)

    def pause_for(self, url: str) -> float:
        return self.nap_pause if "nationalacademies.org" in url else self.pause

    def get(self, url: str, log: bool = True, kind: str = "") -> tuple[int, bytes]:
        f = self.cache / (sha(url)[:32] + ".gz")
        if f.exists():
            body = gzip.decompress(f.read_bytes())
            code = 200
        elif self.offline:
            code, body = 0, b""
        else:
            # A rate limit (429) or server error is waited out, 30 s doubling to
            # 10 minutes; a page still not fetched is returned with its status
            # and never cached, and the caller marks its test undetermined.
            wait = 30
            for attempt in range(7):
                try:
                    r = self.client.get(url)
                    code, body = r.status_code, r.content
                except httpx.HTTPError:
                    code, body = 0, b""
                if code not in (0, 429, 500, 502, 503, 504):
                    break
                print("  HTTP %s on %s; waiting %d s" % (code, url, wait), file=sys.stderr)
                time.sleep(wait)
                wait = min(wait * 2, 600)
            time.sleep(self.pause_for(url))
            if code == 200:
                f.write_bytes(gzip.compress(body))
        if log:
            self.log.append({"url": url, "at": now(), "status": code, "bytes": len(body),
                             "sha256": sha(body), **({"kind": kind} if kind else {})})
        return code, body


def topic_exclusion(title: str) -> list[str]:
    return [k for k, pat in EXCLUDED_TOPICS.items() if re.search(pat, title, re.I)]


# --------------------------------------------------------------------------
# Cochrane and Campbell (PubMed)
# --------------------------------------------------------------------------

def pubmed_records(F: Fetcher, term: str) -> tuple[dict, list[dict]]:
    q = {"db": "pubmed", "term": term, "retmode": "json", "retmax": "10000", "sort": "pub_date"}
    url = EUTILS + "esearch.fcgi?" + urllib.parse.urlencode(q)
    _c, body = F.get(url, kind="esearch")
    res = json.loads(body)["esearchresult"]
    ids = sorted(res["idlist"], key=int)
    recs = []
    for i in range(0, len(ids), 200):
        q = {"db": "pubmed", "id": ",".join(ids[i:i + 200]), "retmode": "xml"}
        _c, body = F.get(EUTILS + "efetch.fcgi?" + urllib.parse.urlencode(q), kind="efetch")
        for art in ET.fromstring(body).findall("PubmedArticle"):
            recs.append(parse_pubmed(art))
    return {"term": term, "count": int(res["count"]), "query_translation": res.get("querytranslation")}, recs


def _text(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def parse_pubmed(art) -> dict:
    mc = art.find("MedlineCitation")
    a = mc.find("Article")
    pmid = mc.findtext("PMID")
    doi = next((e.text for e in art.findall(".//ArticleIdList/ArticleId") if e.get("IdType") == "doi"), None)
    abstract = " ".join(_text(x) for x in a.findall("Abstract/AbstractText"))
    ad = a.find("ArticleDate")
    pd = a.find("Journal/JournalIssue/PubDate")
    date = None
    if ad is not None:
        date = "%s-%02d-%02d" % (ad.findtext("Year"), int(ad.findtext("Month") or 1), int(ad.findtext("Day") or 1))
    elif pd is not None and pd.findtext("Year"):
        months = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                                               "Oct", "Nov", "Dec"], 1)}
        mo = pd.findtext("Month") or "1"
        date = "%s-%02d-01" % (pd.findtext("Year"), months.get(mo[:3], int(mo) if mo.isdigit() else 1))
    return {"pmid": pmid, "doi": doi, "title": _text(a.find("ArticleTitle")), "date": date,
            "publication_types": sorted({_text(p) for p in a.findall("PublicationTypeList/PublicationType")}),
            "abstract_chars": len(abstract), "abstract_sha256": sha(abstract) if abstract else None,
            "_abstract": abstract}


NOT_A_REVIEW = re.compile(r"^\s*(?:protocol\b|evidence (?:and )?gap map|withdrawn\b|correction\b|corrigendum|erratum"
                          r"|retracted\b|editorial\b)|\(protocol\)|(?:review|study) protocol|\bprotocol for (?:a|an|the)\b|\bprotocol\.?$"
                          r"|title registrations|evidence and gap map|\bevidence gap map\b"
                          r"|\bmapping review\b|\bscoping review\b", re.I)
# A protocol's abstract in PubMed says so ("This is a protocol for a Cochrane Review").
PROTOCOL_ABSTRACT = re.compile(r"\s*This is (?:a|the) protocol\b", re.I)
NOT_A_REVIEW_TYPES = {"Editorial", "Comment", "Published Erratum", "Retraction of Publication",
                      "Retracted Publication", "News", "Letter"}


def review_frame(F: Fetcher, name: str, journal: str) -> dict:
    lo, hi = STUDY_WINDOW
    term = '"%s"[ta] AND %s:%s[dp]' % (journal, lo.replace("-", "/"), hi.replace("-", "/"))
    query, recs = pubmed_records(F, term)
    rows = []
    for r in sorted(recs, key=lambda x: (x["date"] or "", int(x["pmid"]))):
        tests = {}
        kind_bad = (NOT_A_REVIEW.search(r["title"]) or PROTOCOL_ABSTRACT.match(r["_abstract"])
                    or (set(r["publication_types"]) & NOT_A_REVIEW_TYPES))
        tests["is_a_review"] = {"pass": not kind_bad,
                                "why": ("title or type: %s" % (kind_bad.group(0) if hasattr(kind_bad, "group")
                                                               else sorted(kind_bad))) if kind_bad else "systematic review"}
        tests["published_in_window"] = {"pass": bool(r["date"]) and lo <= r["date"] <= hi, "why": r["date"]}
        hits = sorted({m.group(0).lower() for m in GRADE_TERMS.finditer(r["_abstract"])})
        tests["states_a_certainty_grade"] = {"pass": bool(hits), "why": hits[:6] or "no certainty or quality grade in the abstract"}
        tests["public_abstract"] = {"pass": r["abstract_chars"] > 0, "why": "%d characters in PubMed" % r["abstract_chars"]}
        ex = topic_exclusion(r["title"])
        tests["not_a_whu_topic"] = {"pass": not ex, "why": ex or "no match"}
        rows.append({**{k: v for k, v in r.items() if not k.startswith("_")}, "tests": tests,
                     "eligible": all(t["pass"] for t in tests.values())})
    return finish(name, F, rows, query, {
        "is_a_review": "title, the abstract's first words ('This is a protocol for a Cochrane Review') and PubMed publication type: protocols, evidence and gap maps, scoping or mapping reviews, "
                       "withdrawn reviews, corrections, editorials and retractions are not reviews with a conclusion",
        "published_in_window": "PubMed electronic publication date (ArticleDate), else the issue date, within %s to %s" % STUDY_WINDOW,
        "states_a_certainty_grade": "the PubMed abstract contains a GRADE certainty or quality term ('low-certainty', "
                                    "'moderate quality', 'certainty of the evidence', 'GRADE', 'strength of evidence')",
        "public_abstract": "PubMed holds an abstract (PubMed abstracts are public)",
        "not_a_whu_topic": "the title matches none of the excluded-topic patterns (EXCLUDED_TOPICS)"})


# --------------------------------------------------------------------------
# National Academies (Crossref + the publication pages)
# --------------------------------------------------------------------------

BOOK_TYPES = {"book", "edited-book", "monograph", "report", "reference-book"}
# A title that names the publication as something other than a consensus study
# ("Proceedings of a Workshop", "Workshop in Brief") is not one; it is excluded
# on its Crossref title without fetching its page.
NOT_CONSENSUS_TITLE = re.compile(r"\bProceedings of (?:a|the) (?:Workshop|Symposium|Conference|Colloquium|Forum)"
                                 r"|\b(?:Workshop|Symposium|Webinar|Forum)(?:\s+Series)? in Brief\b|\bin Brief\b"
                                 r"|\bProceedings of a\b|\bWorkshop Summary\b|\bRapid Expert Consultation\b"
                                 r"|\bLetter Report\b|\bDiscussion Paper\b", re.I)


def crossref_nap(F: Fetcher, lo: str, hi: str) -> tuple[dict, list[dict]]:
    items, cursor, queries = [], "*", []
    while True:
        q = {"filter": "from-pub-date:%s,until-pub-date:%s" % (lo, hi), "rows": "1000", "cursor": cursor,
             "select": "DOI,title,type,published,resource"}
        url = "https://api.crossref.org/prefixes/10.17226/works?" + urllib.parse.urlencode(q)
        _c, body = F.get(url, kind="crossref")
        m = json.loads(body)["message"]
        queries.append(url)
        items += m["items"]
        cursor = m.get("next-cursor")
        if not m["items"] or not cursor or len(items) >= m["total-results"]:
            break
    return {"crossref": queries, "count": len(items)}, items


def nap_page(F: Fetcher, nid: str) -> dict:
    code, body = F.get("https://www.nationalacademies.org/publications/%s" % nid, log=False)
    t = body.decode("utf-8", "replace")
    m = re.search(r"publicationsDataLayer\[%s\]\s*=\s*(\{.*?\});" % nid, t)
    meta = json.loads(m.group(1)) if m else {}
    og = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    title = H.unescape(og.group(1)) if og else ""
    year = re.search(r"\s((?:19|20)\d\d)\s*$", title)
    desc = re.search(r'<meta name="description" content="([^"]*)"', t)
    return {"status": code, "page_sha256": sha(body), "sub_type": meta.get("sub_type"),
            "title": re.sub(r"\s+(?:19|20)\d\d\s*$", "", title), "year": int(year.group(1)) if year else None,
            "description_chars": len(H.unescape(desc.group(1))) if desc else 0,
            "topics": meta.get("topics") or []}


CARD = re.compile(r'href="https://www\.nationalacademies\.org/(?:projects/[^"/]+/)?publications?/(\d+)"[^>]*>'
                  r'(?:(?!</a>).)*?<p class="f-heading-09[^"]*">\s*(.*?)\s*</p>\s*'
                  r'<div class="f-ui-02 text-secondary[^"]*">(.*?)</div>', re.S)


def nap_listing(F: Fetcher, y0: int, y1: int, query: dict, unit: str | None = None) -> dict:
    """The National Academies' own catalogue listing, filtered to publication
    years y0..y1 (and, with unit, to one organisational unit of the catalogue's
    "unit" filter): {id: {title, type, year}} from each card (its type label,
    e.g. "Consensus Study Report", and its year). Pages are read until one adds
    nothing new."""
    out: dict = {}
    base = "https://www.nationalacademies.org/publications/all?" + urllib.parse.urlencode(
        {"publication_date[from]": y0, "publication_date[to]": y1, **({"unit[]": unit} if unit else {})})
    query.setdefault("listing", []).append(base + "&page=<n>")
    page = 1
    while True:
        code, body = F.get(base + "&page=%d" % page, kind="nap-listing")
        if code != 200:
            query["listing_stopped"] = "page %d: HTTP %s" % (page, code)
            break
        new = 0
        for nid, title, meta in CARD.findall(body.decode("utf-8", "replace")):
            ps = [H.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<p>(.*?)</p>", meta, re.S)]
            year = next((int(x) for x in ps if re.fullmatch(r"(?:19|20)\d\d", x)), None)
            typ = next((x for x in ps if not re.fullmatch(r"(?:19|20)\d\d", x)), None)
            if nid not in out:
                new += 1
                out[nid] = {"title": H.unescape(" ".join(title.split())), "type": typ, "year": year}
        last = max([int(x) for x in re.findall(r"[?&](?:amp;)?page=(\d+)", body.decode("utf-8", "replace"))] or [page])
        if not new or page >= last:
            break
        page += 1
    query["listing_pages"] = page
    query["listing_cards"] = len(out)
    return out


def nap_summary(F: Fetcher, nid: str) -> dict:
    """The Summary chapter's text (OpenBook), found by its table-of-contents
    entry; the graded-evidence terms in it."""
    # The Summary is usually chapter 2 (after the front matter); the page's
    # suggested citation names its chapter ('Suggested Citation: "Summary."').
    # Otherwise the contents, on chapter 1, name it.
    code, body = F.get("https://www.nationalacademies.org/read/%s/chapter/2" % nid, kind="openbook")
    if code == 200 and chapter_name(body) in SUMMARY_TITLES:
        return _graded(body, 2)
    code, body = F.get("https://www.nationalacademies.org/read/%s/chapter/1" % nid, kind="openbook")
    if code != 200:
        return {"found": False, "why": "OpenBook HTTP %s" % code, "unfetched": True}
    t = body.decode("utf-8", "replace")
    chapters = re.findall(r'href="(?:https://(?:www|nap)\.nationalacademies\.org)?/read/%s/chapter/(\d+)[^"]*"[^>]*>(.*?)</a>' % nid,
                          t, re.S)
    ch = next((n for n, x in chapters if re.sub(r"<[^>]+>|\s+", " ", x).strip().lower() in SUMMARY_TITLES), None)
    if not ch:
        return {"found": False, "why": "no Summary chapter in the OpenBook contents"}
    code, body = F.get("https://www.nationalacademies.org/read/%s/chapter/%s" % (nid, ch), kind="openbook")
    if code != 200:
        return {"found": False, "why": "Summary chapter HTTP %s" % code, "unfetched": True}
    return _graded(body, int(ch))


SUMMARY_TITLES = ("summary", "executive summary", "summary and recommendations")


def chapter_name(body: bytes) -> str:
    t = H.unescape(re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace")))
    m = re.search(r"Suggested Citation:\s*[\"“]\s*([^\"”]+?)\.?\s*[\"”]", t)
    return " ".join(m.group(1).split()).lower() if m else ""


def _graded(body: bytes, ch: int) -> dict:
    t = re.sub(r"(?s)<(script|style).*?</\1>", " ", body.decode("utf-8", "replace"))
    x = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    ev = sorted({m.group(1).lower() for m in EVIDENCE_LEVEL.finditer(x)})
    cf = sorted({m.group(1).lower() for m in CONFIDENCE_LEVEL.finditer(x)})
    return {"found": True, "chapter": ch, "chars": len(x), "sha256": sha(x),
            "evidence_levels": ev, "confidence_levels": cf,
            "graded": len(ev) >= 3 or len(cf) >= 2}


def nasem_frame(F: Fetcher, name: str, window: tuple[str, str]) -> dict:
    lo, hi = window
    query, items = crossref_nap(F, lo, hi)
    books = sorted({i["DOI"].split("/", 1)[1]: i for i in items if i.get("type") in BOOK_TYPES}.items(),
                   key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0))
    query["books"] = len(books)
    listing = nap_listing(F, int(lo[:4]), int(hi[:4]), query)
    have = {nid for nid, _ in books}
    # A catalogue entry Crossref did not return is a candidate too.
    books += [(nid, {"DOI": "10.17226/%s" % nid, "title": [c["title"]], "type": "catalogue only"})
              for nid, c in sorted(listing.items(), key=lambda kv: int(kv[0])) if nid not in have]
    query["candidates_from_catalogue_only"] = len(books) - query["books"]
    query["publication_pages"] = ("https://www.nationalacademies.org/publications/<id>, only for a book the catalogue "
                                  "listing does not show")
    query["summary_pages"] = "https://www.nationalacademies.org/read/<id>/chapter/<n> for each consensus report in the window"
    rows = []
    for k, (nid, it) in enumerate(books, 1):
        ctitle = " ".join((it.get("title") or [""])[0].split())
        if NOT_CONSENSUS_TITLE.search(ctitle):
            rows.append({"id": nid, "doi": it["DOI"], "title": ctitle, "year": None, "crossref_type": it.get("type"),
                         "tests": {"is_a_consensus_report": {"pass": False, "why": "Crossref title: %s"
                                                             % NOT_CONSENSUS_TITLE.search(ctitle).group(0)}},
                         "eligible": False})
            continue
        c = listing.get(nid)
        if c:
            p = {"status": 200, "sub_type": "Consensus" if c["type"] == "Consensus Study Report" else c["type"],
                 "title": c["title"], "year": c["year"], "page_sha256": None, "description_chars": None,
                 "from": "catalogue listing"}
        else:
            p = dict(nap_page(F, nid), **{"from": "publication page"})
        tests = {}
        if p["status"] != 200:
            tests["is_a_consensus_report"] = {"pass": False, "undetermined": True,
                                              "why": "publication page not fetched (HTTP %s)" % p["status"]}
        else:
            tests["is_a_consensus_report"] = {"pass": p["sub_type"] == "Consensus",
                                              "why": p["sub_type"] or "no type on the page"}
        tests["published_in_window"] = {"pass": bool(p["year"]) and int(lo[:4]) <= p["year"] <= int(hi[:4])
                                        and not (p["year"] == 2026 and hi.startswith("2026") and _month(it) > 9),
                                        "why": "year %s on the page; Crossref %s" % (p["year"], _pubdate(it))}
        row = {"id": nid, "doi": it["DOI"], "title": p["title"] or (it.get("title") or [""])[0],
               "year": p["year"], "crossref_type": it.get("type"), "type_from": p["from"],
               "page_sha256": p["page_sha256"]}
        if tests["is_a_consensus_report"]["pass"] and tests["published_in_window"]["pass"]:
            s = nap_summary(F, nid)
            row["summary"] = {k2: v for k2, v in s.items()}
            tests["states_a_certainty_grade"] = {
                "pass": bool(s.get("graded")),
                "why": ({"evidence_levels": s["evidence_levels"], "confidence_levels": s["confidence_levels"]}
                        if s.get("found") else s["why"]),
                **({} if s.get("found") else {"undetermined": True})}
            tests["public_abstract"] = {"pass": bool(s.get("found")),
                                        "why": ("its Summary chapter is free to read online (OpenBook, %d characters)" % s["chars"])
                                        if s.get("found") else "no Summary chapter read online",
                                        **({} if s.get("found") or not s.get("unfetched") else {"undetermined": True})}
        ex = topic_exclusion(row["title"])
        tests["not_a_whu_topic"] = {"pass": not ex, "why": ex or "no match"}
        row["tests"] = tests
        row["eligible"] = all(t["pass"] for t in tests.values()) and "states_a_certainty_grade" in tests
        rows.append(row)
        if k % 50 == 0:
            print("  %s: %d of %d" % (name, k, len(books)), file=sys.stderr)
    return finish(name, F, rows, query, {
        "is_a_consensus_report": "the National Academies catalogue listing (publications/all filtered to the window's years) "
                                 "labels it \"Consensus Study Report\"; a book the listing does not show is checked on its "
                                 "own publication page, whose publicationsDataLayer record must have sub_type \"Consensus\" "
                                 "(Consensus Study Report); proceedings, workshops, rapid expert consultations and journals are not. "
                                 "A Crossref title naming it proceedings, a workshop or symposium summary, an 'in Brief', a "
                                 "rapid expert consultation, a letter report or a discussion paper excludes it without a fetch; "
                                 "a page that could not be fetched is undetermined",
        "published_in_window": "the year the catalogue (or the publication page) gives, within %s to %s" % window,
        "states_a_certainty_grade": "the OpenBook Summary chapter grades its conclusions: at least three levels of one "
                                    "evidence scale ('conclusive', 'substantial', 'moderate', 'limited', 'insufficient' ... "
                                    "'evidence of/that/for'), or at least two levels of confidence or certainty language; "
                                    "a report with no Summary chapter online is undetermined, not eligible",
        "public_abstract": "its Summary chapter is publicly readable online (OpenBook), which is more than an abstract",
        "not_a_whu_topic": "the title matches none of the excluded-topic patterns (EXCLUDED_TOPICS)"})


def _pubdate(it: dict) -> str | None:
    dp = ((it.get("published") or {}).get("date-parts") or [[None]])[0]
    return "-".join("%02d" % x if i else str(x) for i, x in enumerate(dp) if x) or None


def _month(it: dict) -> int:
    dp = ((it.get("published") or {}).get("date-parts") or [[None]])[0]
    return dp[1] if len(dp) > 1 and dp[1] else 0


# --------------------------------------------------------------------------
# IPCC AR6 numbered SPM statements
# --------------------------------------------------------------------------

# Protocol rev 34: the unit is a numbered SPM statement, a headline (A.1) or a
# numbered sub-statement (A.1.1), in AR6 WGI, WGII, WGIII or the Synthesis
# Report, that carries IPCC calibrated language. Read from each report's
# Summary for Policymakers chapter page on ipcc.ch (rev 33 read the headline
# statements pages only).
IPCC_REPORTS = [
    ("WGI", "Climate Change 2021: The Physical Science Basis", 2021, "https://www.ipcc.ch/report/ar6/wg1/chapter/summary-for-policymakers/"),
    ("WGII", "Climate Change 2022: Impacts, Adaptation and Vulnerability", 2022, "https://www.ipcc.ch/report/ar6/wg2/chapter/summary-for-policymakers/"),
    ("WGIII", "Climate Change 2022: Mitigation of Climate Change", 2022, "https://www.ipcc.ch/report/ar6/wg3/chapter/summary-for-policymakers/"),
    ("SYR", "Climate Change 2023: Synthesis Report", 2023, "https://www.ipcc.ch/report/ar6/syr/summary-for-policymakers/"),
]
# Protocol rev 34 (2026-10-21, advisor ruling): a likelihood term counts only
# where IPCC sets it as calibrated, in italics. The chapter pages carry no
# reliable typography, so a statement whose only calibrated language is a
# likelihood term is checked in the report's SPM PDF: the term must be set in
# an italic face there (pdftohtml <i>, or a font family named "...Ita..."). A
# confidence level needs no check. A statement the PDF check cannot locate is
# undetermined and not eligible.
IPCC_SPM_PDFS = {
    "WGI": "https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_SPM.pdf",
    "WGII": "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_SummaryForPolicymakers.pdf",
    "WGIII": "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_SummaryForPolicymakers.pdf",
    "SYR": "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_SPM.pdf",
}
LIKELIHOOD = re.compile(r"\b(?:virtually certain|extremely likely|very likely|likely|more likely than not|about as likely as not"
                        r"|unlikely|very unlikely|extremely unlikely|exceptionally unlikely)\b", re.I)


def pdf_chars(xml: str) -> tuple[str, list[bool]]:
    """The PDF's text as letters and digits only, lower case, in content order,
    with a parallel list: is each character set in an italic face."""
    spec: dict = {}
    lines, pg = [], 0
    for m in re.finditer(r'<fontspec id="(\d+)" size="(-?\d+)" family="([^"]+)"|<page number="(\d+)"'
                         r'|<text top="(\d+)" left="(\d+)"[^>]*font="(\d+)">(.*?)</text>', xml, re.S):
        if m.group(1):
            spec[m.group(1)] = bool(re.search(r"Ita|Italic|Oblique", m.group(3)))
        elif m.group(4):
            pg = int(m.group(4))
        else:
            lines.append((pg, int(m.group(5)), int(m.group(6)), spec.get(m.group(7), False), m.group(8)))
    text, ital = [], []
    for _pg, _t, _l, fit, raw in lines:      # the PDF's own content order: SPM pages run in two columns
        for seg in re.finditer(r"(<i>)?((?:(?!</?i>).)*)(</i>)?", raw, re.S):
            it = fit or bool(seg.group(1))
            for ch in H.unescape(re.sub(r"<[^>]+>", "", seg.group(2))).lower():
                if ch.isalnum():
                    text.append(ch)
                    ital.append(it)
    return "".join(text), ital


def italic_likelihood(statement: str, chars: tuple[str, list[bool]]) -> dict:
    """Each likelihood term of the statement, and whether the SPM PDF sets it in
    italics. The statement is found in the PDF by its first 60 letters and digits."""
    text, ital = chars
    norm = re.sub(r"[^a-z0-9]", "", statement.lower())
    at = text.find(norm[:60])
    if at < 0:
        return {"found": False}
    terms = []
    for m in LIKELIHOOD.finditer(statement):
        key = re.sub(r"[^a-z0-9]", "", m.group(0).lower())
        pre = re.sub(r"[^a-z0-9]", "", statement[:m.start()].lower())
        j = text.find(key, at + max(0, len(pre) - 3))   # the PDF only adds (footnote marks), so the term is at or after
        terms.append({"term": m.group(0).lower(), "italic": j >= 0 and j < at + len(norm) + 40 and all(ital[j:j + len(key)])})
    return {"found": True, "terms": terms}


SPM_LABEL = re.compile(r"(?:SPM\.)?([A-E]\.\d{1,2}(?:\.\d{1,2})?)\.?\s*(?=[A-Z(])")


def spm_statements(body: bytes) -> dict:
    """{label: statement text} for every paragraph of an SPM page that opens
    with a statement number. The first paragraph carrying a label is the
    statement (a cross-reference such as "WGI AR6 SPM A.1.2" never opens a
    paragraph). The chapter-link list ("Links to chapters ...", "{...}") and the
    page's "Expand" control are not part of the statement."""
    t = re.sub(r"(?s)<(script|style)\b.*?</\1>|<!--.*?-->", " ", body.decode("utf-8", "replace"))
    out: dict = {}
    for p in re.findall(r"(?s)<p\b[^>]*>(.*?)</p>", t):
        x = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p))).strip()
        m = SPM_LABEL.match(x)
        if not m or m.group(1) in out:
            continue
        st = re.split(r"\s(?:Expand|Links to (?:chapters|longer report))\b", x[m.end():])[0]
        out[m.group(1)] = re.sub(r"\s+", " ", re.sub(r"\{[^{}]*\}", " ", st)).strip()
    return out


def numbering_gaps(labels: list[str]) -> list[str]:
    """Statement numbers missing from a contiguous run (B.2 present, B.1
    absent; A.1.3 present, A.1.2 absent)."""
    have, gaps = set(labels), []
    for lab in labels:
        *head, last = lab.split(".")
        for k in range(1, int(last)):
            prev = ".".join([*head, str(k)])
            if prev not in have and prev not in gaps:
                gaps.append(prev)
        if len(head) == 2 and ".".join(head) not in have and ".".join(head) not in gaps:
            gaps.append(".".join(head))
    return gaps


def ipcc_frame(F: Fetcher, name: str) -> dict:
    rows, query = [], {"pages": [r[3] for r in IPCC_REPORTS], "protocol": "rev 34",
                       "api": "none: IPCC publishes no API; each report's Summary for Policymakers chapter page is fetched",
                       "per_report": {}}
    query["italic_check"] = {}
    for wg, title, year, url in IPCC_REPORTS:
        code, body = F.get(url, kind="ipcc")
        sts = spm_statements(body) if code == 200 else {}
        n0, chars = len(rows), None
        for lab, s in sts.items():
            cal = sorted({c.group(0).lower() for c in IPCC_CALIBRATED.finditer(s)})
            grade = {"pass": bool(cal), "why": cal or "no calibrated confidence or likelihood term in the statement"}
            if cal and all(LIKELIHOOD.fullmatch(c) for c in cal):
                if chars is None:
                    pcode, pdf = F.get(IPCC_SPM_PDFS[wg], kind="ipcc-pdf")
                    chars = pdf_chars(pdf_xml(pdf)) if pcode == 200 else ("", [])
                    query["italic_check"][wg] = {"pdf": IPCC_SPM_PDFS[wg], "http_status": pcode, "pdf_sha256": sha(pdf)}
                chk = italic_likelihood(s, chars)
                kept = sorted({t["term"] for t in chk.get("terms", []) if t["italic"]})
                grade = {"pass": bool(kept), "italic_check": chk,
                         "why": (kept if kept else "a likelihood term only, not set in italics (IPCC's calibrated term) "
                                                   "in the SPM PDF") if chk["found"] else
                                "a likelihood term only, and the statement was not found in the SPM PDF",
                         **({} if chk["found"] else {"undetermined": True})}
            tests = {"published_in_window": {"pass": 2021 <= year <= 2023, "why": "AR6 %s, %d" % (wg, year)},
                     "states_a_certainty_grade": grade,
                     "public_abstract": {"pass": True, "why": "the Summary for Policymakers is published in full on ipcc.ch"},
                     "not_a_whu_topic": {"pass": not topic_exclusion(s), "why": topic_exclusion(s) or "no match"}}
            rows.append({"id": "AR6-%s-%s" % (wg, lab), "report": title, "year": year, "url": url,
                         "level": "headline" if lab.count(".") == 1 else "sub-statement",
                         "statement_chars": len(s), "statement_sha256": sha(s), "first_words": " ".join(s.split()[:10]),
                         "tests": tests, "eligible": all(v["pass"] for v in tests.values())})
        mine = rows[n0:]
        query["per_report"][wg] = {
            "http_status": code, "statements": len(mine),
            "headlines": sum(1 for r in mine if r["level"] == "headline"),
            "sub_statements": sum(1 for r in mine if r["level"] == "sub-statement"),
            "eligible": sum(1 for r in mine if r["eligible"]),
            "eligible_headlines": sum(1 for r in mine if r["eligible"] and r["level"] == "headline"),
            "numbering_gaps": numbering_gaps(list(sts))}
    return finish(name, F, rows, query, {
        "published_in_window": "AR6 report year, 2021 to 2023",
        "states_a_certainty_grade": "the numbered statement itself (headline or sub-statement) carries IPCC calibrated language: "
                                    "a confidence level ('high confidence') or a likelihood term ('very likely'); 'unequivocal' "
                                    "alone does not count (protocol rev 34). A likelihood term counts only where IPCC sets "
                                    "it as calibrated, in italics: a statement whose only calibrated language is a "
                                    "likelihood term is checked in the report's SPM PDF (protocol rev 34, 2026-10-21)",
        "public_abstract": "IPCC publishes every Summary for Policymakers in full",
        "not_a_whu_topic": "the statement matches none of the excluded-topic patterns (EXCLUDED_TOPICS)"})


# --------------------------------------------------------------------------
# IPCC AR5 practice frame (protocol rev 34, amended 2026-10-21)
# --------------------------------------------------------------------------

# The practice frame: the numbered statements (headlines and numbered
# sub-statements) in the Summaries for Policymakers of AR5 WGI, WGII, WGIII and
# the AR5 Synthesis Report that carry IPCC calibrated language, read from the
# four SPM PDFs on ipcc.ch (no crawl). AR5 numbers its SPM SECTIONS, not its
# statements: a statement is a bold summary statement in the body text (the
# SPM's own typography for its findings), labelled by the numbered section it
# sits in ("SYR 1.1", "WGI B.1", "WGII A-1", "WGIII 4.2.3"), with #k where a
# section holds more than one. Under a top-level section (SYR "SPM 1.", WGI
# "B.", WGIII "SPM.3") it is a headline; under a numbered subsection, a
# sub-statement. Where the bold text stops mid-sentence (WGII, WGIII: a bold
# lead-in followed by "(high confidence)." in plain type) the statement runs to
# the end of that sentence. Figure and table text, box titles and headings are
# not statements.
AR5_REPORTS = [
    ("WGI", "Climate Change 2013: The Physical Science Basis", 2013,
     "https://www.ipcc.ch/site/assets/uploads/2018/02/WG1AR5_SPM_FINAL.pdf"),
    ("WGII", "Climate Change 2014: Impacts, Adaptation, and Vulnerability", 2014,
     "https://www.ipcc.ch/site/assets/uploads/2018/02/ar5_wgII_spm_en.pdf"),
    ("WGIII", "Climate Change 2014: Mitigation of Climate Change", 2014,
     "https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_summary-for-policymakers.pdf"),
    ("SYR", "Climate Change 2014: Synthesis Report", 2014,
     "https://www.ipcc.ch/site/assets/uploads/2018/02/AR5_SYR_FINAL_SPM.pdf"),
]
AR5_HEADING = re.compile(r"^\s*(?:SPM ?\.?\s?(\d+(?:\.\d+)*)\.?(?=\s|$)|([A-E])(?:\.(\d+))?\.?(?=\s+[A-Z])|([A-C])-(\d+)\.|([A-C]):)")
AR5_BRACE = re.compile(r"^\s*\{[^{}]*\}\s*$")
AR5_NOT_STATEMENT = re.compile(r"^(?:\(?[A-Z]\)|(?:Figure|Table)\s+SPM|(?:Assessment|Background)\s+Box\s+SPM|Box\s+SPM)")


def pdf_xml(pdf: bytes) -> str:
    """poppler's pdftohtml -xml of a PDF: every text line with its page,
    position and font (size, family, colour; bold marked <b>)."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.pdf").write_bytes(pdf)
        subprocess.run(["pdftohtml", "-xml", "-i", "-q", "a.pdf", "a"], cwd=d, check=True)
        return (Path(d) / "a.xml").read_text(encoding="utf-8", errors="replace")


def ar5_label(t: str) -> str | None:
    m = AR5_HEADING.match(t)
    if not m:
        return None
    g = m.groups()
    return g[0] or (g[1] + ("." + g[2] if g[2] else "") if g[1] else None) or (g[3] + "-" + g[4] if g[3] else g[5])


def ar5_statements(xml: str) -> list[tuple[str, str]]:
    """[(section label, statement)] in reading order. The statement font is the
    bold font (size, family, colour) most used on long lines; a heading is a
    bold line in another font that opens with a section number. A statement is
    followed by its own paragraph's geometry (left margin, line spacing), so a
    neighbouring column or a figure is not read into it; where its bold text
    stops mid-sentence it runs on, in plain type, to the end of the sentence. A
    run that never ends a sentence (a figure title) is not a statement."""
    spec: dict = {}
    lines, pg = [], 0
    for m in re.finditer(r'<fontspec id="(\d+)" size="(-?\d+)" family="([^"]+)" color="([^"]+)"|<page number="(\d+)"'
                         r'|<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)" font="(\d+)">(.*?)</text>', xml, re.S):
        if m.group(1):
            spec[m.group(1)] = (int(m.group(2)), m.group(3).split("+")[-1], m.group(4))
        elif m.group(5):
            pg = int(m.group(5))
        else:
            raw = m.group(11)
            lines.append({"pg": pg, "top": int(m.group(6)), "left": int(m.group(7)), "w": int(m.group(8)),
                          "h": int(m.group(9)), "font": spec.get(m.group(10)), "bold": "<b>" in raw,
                          "t": H.unescape(re.sub(r"<[^>]+>", "", raw))})
    lines.sort(key=lambda x: (x["pg"], x["top"], x["left"]))
    counts: dict = {}
    for x in lines:
        if x["bold"] and len(x["t"].strip()) > 40:
            counts[x["font"]] = counts.get(x["font"], 0) + 1
    stf = max(counts, key=counts.get)
    small = stf[0] * 0.75                    # superscripts, subscripts, footnote marks
    out, cur, run = [], None, None

    def close() -> None:
        nonlocal run
        if run:
            s = re.sub(r"\s+", " ", re.sub(r"(\w)- (\w)", r"\1\2", " ".join(run["parts"])))
            s = re.sub(r"\s+([,.;:)])", r"\1", re.sub(r"\(\s+", "(", s)).strip()
            if cur and run["ended"] and len(s.split()) >= 6 and not AR5_NOT_STATEMENT.match(s):
                out.append((cur, s))
        run = None

    for x in lines:
        t = x["t"].strip()
        if not t or re.fullmatch(r"SPM|Summary for Policymakers|\d+", t):
            continue
        if run and (x["pg"] != run["pg"] or x["top"] - run["top"] > 1.9 * run["h"]):
            close()
        if x["font"] and x["font"][0] < small:
            if run and abs(x["top"] - run["top"]) <= run["h"] and run["right"] - 2 <= x["left"] <= run["right"] + 3:
                run["parts"][-1] += t        # CO + 2 stays one word
                run["right"] = x["left"] + x["w"]
            continue
        if x["bold"] and x["font"] != stf and not AR5_BRACE.match(t) and not run:
            lab = ar5_label(t)
            if lab and len(t) < 140:
                cur = lab
            continue
        if run:
            same_line = abs(x["top"] - run["top"]) <= 3 and run["right"] - 2 <= x["left"] <= run["right"] + 15
            next_line = 0 < x["top"] - run["top"] <= 1.9 * run["h"] and abs(x["left"] - run["margin"]) <= 12
            if not (same_line or next_line) or x["font"][0] < stf[0] - 1:
                continue                     # another column or a figure: not this paragraph
            if AR5_BRACE.match(t):
                run["ended"] = True
                close()
                continue
            if x["bold"] and x["font"] == stf and not run["tail"]:
                run["parts"].append(t)
            elif not x["bold"]:
                if run["ended"] and not run["tail"]:
                    close()                  # the bold statement ended its sentence; the plain text is the elaboration
                    continue
                run["tail"] = True
                stop = re.search(r"[.!?](?:\s|$)", t)
                run["parts"].append(t[:stop.end()] if stop else t)
                if stop:
                    run["ended"] = True
                    close()
                    continue
            else:
                close()
                continue
            run.update(top=x["top"], right=x["left"] + x["w"])
            if not run["tail"] and re.search(r"[.!?]\)?$", t):
                run["ended"] = True          # the bold text ends its own sentence; a brace or plain text may follow
            continue
        if x["bold"] and x["font"] == stf and re.match(r"[A-Z0-9(]", t):
            run = {"pg": x["pg"], "top": x["top"], "h": x["h"], "margin": x["left"], "right": x["left"] + x["w"],
                   "parts": [t], "tail": False, "ended": bool(re.search(r"[.!?]\)?$", t))}
    close()
    seen, uniq = set(), []
    for lab, s in out:                      # a statement printed twice (a repeated box) is one statement
        key = re.sub(r"[^a-z]+", "", s.lower())[:60]
        if key not in seen:
            seen.add(key)
            uniq.append((lab, s))
    return uniq


def ipcc_ar5_frame(F: Fetcher, name: str) -> dict:
    rows, query = [], {"pages": [r[3] for r in AR5_REPORTS], "protocol": "rev 34 (amended 2026-10-21)",
                       "api": "none: the four AR5 Summary for Policymakers PDFs on ipcc.ch, read with poppler's pdftohtml",
                       "pdftohtml": subprocess.run(["pdftohtml", "-v"], capture_output=True, text=True).stderr.split("\n")[0],
                       "per_report": {}}
    for wg, title, year, url in AR5_REPORTS:
        code, body = F.get(url, kind="ipcc-pdf")
        sts = ar5_statements(pdf_xml(body)) if code == 200 else []
        n0, k = len(rows), {}
        for lab, s in sts:
            k[lab] = k.get(lab, 0) + 1
            cal = sorted({c.group(0).lower() for c in IPCC_CALIBRATED.finditer(s)})
            tests = {"states_a_certainty_grade": {"pass": bool(cal), "why": cal or "no calibrated confidence or likelihood term in the statement"},
                     "public_abstract": {"pass": True, "why": "the Summary for Policymakers is published in full on ipcc.ch"},
                     "not_a_whu_topic": {"pass": not topic_exclusion(s), "why": topic_exclusion(s) or "no match"}}
            rows.append({"id": "AR5-%s-%s#%d" % (wg, lab, k[lab]), "report": title, "year": year, "url": url,
                         "section": lab, "level": "headline" if not re.search(r"[.-]", lab) else "sub-statement",
                         "statement_chars": len(s), "statement_sha256": sha(s), "first_words": " ".join(s.split()[:10]),
                         "tests": tests, "eligible": all(v["pass"] for v in tests.values())})
        mine = rows[n0:]
        query["per_report"][wg] = {
            "http_status": code, "pdf_sha256": sha(body), "statements": len(mine),
            "headlines": sum(1 for r in mine if r["level"] == "headline"),
            "sub_statements": sum(1 for r in mine if r["level"] == "sub-statement"),
            "eligible": sum(1 for r in mine if r["eligible"]),
            "sections": sorted(k, key=lambda x: [int(p) if p.isdigit() else p for p in re.split(r"[.-]", x)])}
    return finish(name, F, rows, query, {
        "states_a_certainty_grade": "the statement itself carries IPCC calibrated language: a confidence level ('high "
                                    "confidence') or a likelihood term ('very likely'); the same test as the AR6 frame",
        "public_abstract": "IPCC publishes every Summary for Policymakers in full",
        "not_a_whu_topic": "the statement matches none of the excluded-topic patterns (EXCLUDED_TOPICS)"})


def draw_listed(frame_file: Path, seed: int) -> dict:
    """The draw procedure on a frame whose eligibility is already in the file:
    shuffle the candidate numbers with random.Random(seed); the first eligible
    in that order is the draw. Every candidate passed over is logged."""
    frame = json.loads(frame_file.read_text(encoding="utf-8"))
    order = [r["n"] for r in frame["rows"]]
    random.Random(seed).shuffle(order)
    by_n = {r["n"]: r for r in frame["rows"]}
    log, drawn = [], None
    for k, n in enumerate(order, 1):
        r = by_n[n]
        log.append({"checked": k, "n": n, "id": r["id"], "eligible": r["eligible"],
                    "failed": [t for t, v in r["tests"].items() if not v["pass"]]})
        if r["eligible"]:
            drawn = r
            break
    return {"frame_file": str(frame_file.relative_to(STUDY)), "frame_sha256": sha(frame_file.read_bytes()),
            "seed": seed, "procedure": "random.Random(seed).shuffle of the candidate numbers n; the first eligible "
                                       "candidate in that order is the draw",
            "shuffled_order_first_50": order[:50], "candidates": len(order), "checked": len(log),
            "drawn": {x: drawn[x] for x in ("n", "id", "report", "year", "url", "section", "level", "statement_sha256")}
            if drawn else None, "drawn_at": now(), "log": log}


# --------------------------------------------------------------------------
# The study draw (protocol rev 38)
# --------------------------------------------------------------------------
#
# seed = int(<full 40-character freeze commit hash>, 16). Each frame's
# numbered eligible list (its "k" numbers) is shuffled with
# random.Random(seed); the first entry that passes the draw-time test is the
# draw. IPCC's second question is the next entry in the same shuffle that
# passes and comes from a different AR6 report than the first. Every candidate
# checked is logged.
#
# THE DRAW-TIME TEST: a candidate whose question would duplicate one WHU has
# published or tested is ineligible, and why is logged. WHU's questions: the
# three published issues, the pilot's four (T01-T04; T02 is WHU-P02's), and
# WHU-P04. The frames already applied EXCLUDED_TOPICS to each title or
# statement; the draw applies them again, and adds WHU-P04, to the statement's
# FIRST SENTENCE (the claim a question is put from): on the whole statement
# the WHU-P04 test also caught statements about something else that mention
# past emissions in passing (AR6-WGIII-C.1.4, on 1.5 degC pathways).

WHU_QUESTIONS = {
    **{k: (v, "text") for k, v in EXCLUDED_TOPICS.items()},
    "WHU-P04 (have the world's greenhouse gas emissions grown faster in recent decades than in earlier ones?)": (
        r"(?=.*\b(?:greenhouse gas|GHG|CO ?2|CO₂|carbon dioxide)\b[^.]{0,60}\bemissions?\b"
        r"[^.]{0,120}\b(?:ha(?:ve|s) (?:continued to )?(?:rise|risen|increased|grown)|grew|rose|growth|higher than in))"
        r"(?=.*\b(?:since (?:18|19|20)\d\d|(?:19|20)\d\d\s*[–-]\s*(?:19|20)\d\d|(?:previous|past|last) decades?"
        r"|between (?:19|20)\d\d and)\b)", "first sentence"),
}
STUDY_DRAW_FRAMES = ("cochrane", "campbell", "ipcc")
SEED_RULE = "seed = int(<full 40-character freeze commit hash>, 16) (protocol rev 38)"


def seed_from_commit(commit: str) -> int:
    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        raise ValueError("the seed needs the full 40-character commit hash, lower-case hex; got %r" % commit)
    return int(commit, 16)


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+(?=[A-Z(])", (text or "").strip(), maxsplit=1)[0]


def duplicates(text: str) -> list[str]:
    """The WHU questions TEXT's question would duplicate (WHU_QUESTIONS)."""
    out = []
    for name, (pat, scope) in WHU_QUESTIONS.items():
        if re.search(pat, first_sentence(text) if scope == "first sentence" else text, re.I | re.S):
            out.append(name)
    return out


def ipcc_texts(F: "Fetcher") -> dict[str, str]:
    """{statement id: text} from the four AR6 SPM pages, as ipcc_frame read them."""
    out = {}
    for wg, _title, _year, url in IPCC_REPORTS:
        code, body = F.get(url, kind="ipcc")
        for lab, st in (spm_statements(body) if code == 200 else {}).items():
            out["AR6-%s-%s" % (wg, lab)] = st
    return out


def draw_study(frame_file: Path, commit: str, texts: dict[str, str] | None = None, n_draws: int = 1) -> dict:
    """The study draw on one frame. TEXTS: {id: statement} for IPCC (each
    checked against the frame's statement_sha256); Cochrane and Campbell are
    tested on the title the frame holds."""
    seed = seed_from_commit(commit)
    frame = json.loads(frame_file.read_text(encoding="utf-8"))
    rows = {r["n"]: r for r in frame["rows"]}
    elig = {e["k"]: e for e in frame["eligible"]}
    order = sorted(elig)
    random.Random(seed).shuffle(order)
    log, drawn = [], []
    for i, k in enumerate(order, 1):
        if len(drawn) >= n_draws:
            break
        r = rows[elig[k]["n"]]
        rid = r.get("id") or r.get("pmid")
        rec = {"checked": i, "k": k, "n": r["n"], "id": rid}
        if texts is not None:
            t = texts.get(rid)
            if t is None or sha(t) != r.get("statement_sha256"):
                rec.update(result="undetermined", why="the statement as fetched now is %s"
                           % ("missing" if t is None else "not the one the frame hashed (sha256 differs)"))
                log.append(rec)
                continue
        else:
            t = r.get("title") or ""
        rec["text_sha256"] = sha(t)
        dup = duplicates(t)
        if dup:
            rec.update(result="ineligible", why="its question would duplicate one WHU has published or tested: "
                                                 + "; ".join(dup))
        elif drawn and r.get("report") and any(d.get("report") == r.get("report") for d in drawn):
            rec.update(result="passed over", why="from the same AR6 report as an earlier draw (%s)" % r["report"])
        else:
            rec.update(result="drawn", draw=len(drawn) + 1)
            drawn.append(r)
        log.append(rec)
    keep = ("n", "id", "pmid", "doi", "title", "date", "report", "year", "url", "level", "statement_sha256")
    return {"frame_file": str(frame_file.relative_to(STUDY)) if frame_file.is_relative_to(STUDY) else str(frame_file),
            "frame_sha256": sha(frame_file.read_bytes()), "commit": commit, "seed": seed, "seed_rule": SEED_RULE,
            "procedure": "random.Random(seed).shuffle of the frame's eligible numbers k; in that order, each "
                         "candidate is tested against WHU's published and tested questions; the first that "
                         "passes is the draw" + ("; the next that passes from a different AR6 report is the "
                                                 "second" if n_draws > 1 else ""),
            "whu_questions": {k: {"pattern": v[0], "applied_to": v[1]} for k, v in WHU_QUESTIONS.items()},
            "draws_wanted": n_draws, "eligible": len(order), "checked": len(log),
            "drawn": [{x: d[x] for x in keep if x in d} for d in drawn], "drawn_at": now(), "log": log}


def frame_at_commit(frame_file: Path, commit: str) -> str | None:
    """sha256 of FRAME_FILE as committed in COMMIT, or None if the commit or
    the file is not there."""
    rel = frame_file.resolve().relative_to(STUDY.parents[1])
    r = subprocess.run(["git", "-C", str(STUDY.parents[1]), "show", "%s:%s" % (commit, rel)],
                       capture_output=True)
    return sha(r.stdout) if r.returncode == 0 else None


# --------------------------------------------------------------------------

def finish(name: str, F: Fetcher, rows: list[dict], query: dict, tests: dict) -> dict:
    for i, r in enumerate(rows, 1):
        r["n"] = i
    elig = [r for r in rows if r["eligible"]]
    counts = {t: {"pass": sum(1 for r in rows if t in r["tests"] and r["tests"][t]["pass"]),
                  "fail": sum(1 for r in rows if t in r["tests"] and not r["tests"][t]["pass"]),
                  "undetermined": sum(1 for r in rows if r["tests"].get(t, {}).get("undetermined"))}
              for t in tests}
    return {"frame": name, "built_at": now(), "script": "study/whu-reliability/scripts/frames.py",
            "query": query, "tests": tests, "excluded_topics": EXCLUDED_TOPICS,
            "candidates": len(rows), "eligible_count": len(elig), "test_counts": counts,
            "eligible": [{"k": k, "n": r["n"], **{x: r[x] for x in ("id", "pmid", "doi", "title", "date", "year") if x in r}}
                         for k, r in enumerate(elig, 1)],
            "queries_logged": F.log, "rows": rows}


# --------------------------------------------------------------------------
# A frame with no full eligible list: the candidate list, and the draw
# --------------------------------------------------------------------------

CONSENSUS = "Consensus Study Report"

# Protocol rev 34: reports of the Health and Medicine Division are not in the
# National Academies frame. The division is read from the catalogue's own
# "unit" filter (publications/all?unit[]=<code>), one listing per unit: the
# division itself and each board the filter lists under it (read from the
# filter on 21 October 2026). A candidate on any of these listings is excluded,
# and the units it was listed under are recorded.
HMD_UNITS = {
    "HMD": "Health and Medicine Division",
    "BGH": "Board on Global Health",
    "HCS": "Board on Health Care Services",
    "HPDP": "Board on Health Promotion and Disease Prevention",
    "HSP": "Board on Health Sciences Policy",
    "NBH": "Board on Neuroscience and Behavioral Health",
    "BPH": "Board on Population Health and Public Health Practice",
    "BSP": "Board on the Health of Select Populations",
    "FNB": "Food and Nutrition Board",
    "EO": "Health and Medicine Division Executive Office",
    "MFUA": "Medical Follow-Up Agency",
    "NCPB": "National Cancer Policy Board",
}
# Protocol rev 34 (extended 2026-10-21), on the advisor's rulings of 21 October
# 2026. Rule: a unit of the catalogue's filter is excluded if its remit is human
# health or medicine; a report listed under several units is excluded if any one
# of them is excluded. Every unit on the filter whose name contains "Health" or
# "Medicine" was classified by name below; the filter is re-read on each build
# (nap_unit_filter) and any such unit not classified here is reported as
# unclassified, never silently kept.
RULED_EXCLUDED = {
    # The Center for Health, People, and Places (the 2024 reorganisation's health
    # centre; the catalogue lists it on older reports too) and its health units.
    "CHPP": "Center for Health, People, and Places",
    "BHS": "Biomedical and Health Sciences Program Area",
    "HCPH": "Health Care and Public Health Program Area",
    "CHPP EO": "Center for Health, People, and Places Executive Office",
    # The Institute of Medicine (the division's name before 2016) and its board.
    "IOM": "Institute of Medicine",
    "BMVH": "Board on Military and Veterans Health",
    # The National Academy of Medicine and all its offices and programs.
    "NAM": "National Academy of Medicine",
    "NAMEND": "National Academy of Medicine Endowments",
    "NAMEO": "National Academy of Medicine Executive Office",
    "LC": "National Academy of Medicine Leadership Consortium",
    "NAMMO": "National Academy of Medicine Membership Office",
    "NAMPO": "National Academy of Medicine President's Office",
    "NAM PRGM": "National Academy of Medicine Programs",
    "HPFLP": "Health Policy Fellowships and Leadership Programs",
    "GHRB": "Gulf Health and Resilience Board",
}
# Kept: "Health" or "Medicine" in the name, but the remit is not human health or
# medicine. The Center's other program areas are kept too (their names carry
# neither word, so they are not listed here or queried).
RULED_KEPT = {
    "COSEMPUP": "Committee on Science, Engineering, Medicine, and Public Policy",
    "CWSE": "Committee on Women in Science, Engineering, and Medicine",
    "BAHSCR": "Board on Animal Health Sciences, Conservation, and Research",
}
EXCLUDED_UNITS = {**HMD_UNITS, **RULED_EXCLUDED}
HEALTH_OR_MEDICINE = re.compile(r"\b(?:Health|Medicine)\b")


def nap_unit_filter(F: Fetcher, y0: int, y1: int) -> list[dict]:
    """The catalogue's "unit" filter (Program Centers), as the listing page
    offers it: [{code, name, group}] in the filter's order, each unit with the
    group heading it sits under."""
    url = "https://www.nationalacademies.org/publications/all?" + urllib.parse.urlencode(
        {"publication_date[from]": y0, "publication_date[to]": y1}) + "&page=1"
    _c, body = F.get(url, kind="nap-unit-filter")
    page = body.decode("utf-8", "replace")
    seg = page[page.find('id="filter-unit"'):] if 'id="filter-unit"' in page else ""
    out, group = [], None
    for m in re.finditer(r'data-accordion-trigger[^>]*>\s*<span[^>]*>\s*([^<]+?)\s*</span>'
                         r'|type="checkbox"[^>]*value="([^"]*)"\s*/?>.*?inline-flex relative">\s*([^<]+?)\s*</span>',
                         seg, re.S):
        if m.group(1):
            group = H.unescape(m.group(1))
        elif not any(u["code"] == H.unescape(m.group(2)) for u in out):
            out.append({"code": H.unescape(m.group(2)), "name": H.unescape(m.group(3)), "group": group})
    return out


def nasem_list(F: Fetcher, name: str, window: tuple[str, str]) -> dict:
    """The National Academies frame as a CANDIDATE list only (2026-10-21): every
    publication the catalogue labels a Consensus Study Report in the window's
    years, from the listing pages alone. Eligibility is not tested here; the
    draw tests candidates one at a time in seeded order (draw())."""
    lo, hi = window
    query: dict = {"api": "none: the National Academies publish no API; their catalogue listing is read"}
    cards = nap_listing(F, int(lo[:4]), int(hi[:4]), query)
    filt = nap_unit_filter(F, int(lo[:4]), int(hi[:4]))
    unclassified = {u["code"]: u["name"] for u in filt if HEALTH_OR_MEDICINE.search(u["name"])
                    and u["code"] not in EXCLUDED_UNITS and u["code"] not in RULED_KEPT}
    reported = {**RULED_KEPT, **unclassified}
    groups = {u["code"]: u["group"] for u in filt}
    units: dict = {}
    by_unit: dict = {}
    for code in [*EXCLUDED_UNITS, *reported]:
        uq: dict = {}
        ids = nap_listing(F, int(lo[:4]), int(hi[:4]), uq, unit=code)
        by_unit[code] = {"name": {**EXCLUDED_UNITS, **reported}[code], "group": groups.get(code),
                         "excluded": code in EXCLUDED_UNITS,
                         "classification": ("excluded: protocol rev 34" if code in HMD_UNITS else
                                            "excluded: protocol rev 34 (extended 2026-10-21)" if code in EXCLUDED_UNITS else
                                            "kept: protocol rev 34 (extended 2026-10-21)" if code in RULED_KEPT else
                                            "unclassified: awaiting a ruling"),
                         "listing": uq["listing"][0], "listing_pages": uq["listing_pages"], "listing_cards": len(ids),
                         **({"listing_stopped": uq["listing_stopped"]} if "listing_stopped" in uq else {})}
        for nid in ids:
            units.setdefault(nid, []).append(code)
    consensus = sorted(((nid, c) for nid, c in cards.items() if c["type"] == CONSENSUS), key=lambda kv: int(kv[0]))
    exc = lambda nid: [u for u in units.get(nid, []) if u in EXCLUDED_UNITS]
    excluded = [{"id": nid, "title": c["title"], "year": c["year"], "units": exc(nid)} for nid, c in consensus if exc(nid)]
    cand = [(nid, c) for nid, c in consensus if not exc(nid)]
    for code, u in by_unit.items():
        u["consensus_reports_listed"] = sum(1 for nid, _c in consensus if code in units.get(nid, []))
        if not u["excluded"]:
            u["of_these_left_in_frame"] = sum(1 for nid, _c in cand if code in units.get(nid, []))
    types: dict = {}
    for c in cards.values():
        types[c["type"] or "(no label)"] = types.get(c["type"] or "(no label)", 0) + 1
    rows = [{"n": i, "id": nid, "doi": "10.17226/%s" % nid, "title": c["title"], "year": c["year"],
             "url": "https://www.nationalacademies.org/publications/%s" % nid}
            for i, (nid, c) in enumerate(cand, 1)]
    return {"frame": name, "kind": "candidate list (no eligibility tested; see draw)", "protocol": "rev 34", "built_at": now(),
            "script": "study/whu-reliability/scripts/frames.py", "window": {"from": lo, "to": hi},
            "query": query, "listing_cards_by_type": dict(sorted(types.items(), key=lambda x: -x[1])),
            "consensus_reports": len(consensus),
            "division_exclusion": {
                "rule": "protocol rev 34: a report of the Health and Medicine Division is not a candidate; "
                        "protocol rev 34 (extended 2026-10-21): nor is a report listed under any unit whose remit "
                        "is human health or medicine; a report listed under several units is excluded if any one "
                        "of them is excluded",
                "how_recorded": "the catalogue's own 'unit' filter, one listing query per unit; every unit of the "
                                "Health and Medicine Division and every unit whose name contains 'Health' or "
                                "'Medicine' is queried and classified (units[code].classification); a report on any "
                                "excluded unit's listing is excluded and the units are recorded with it",
                "kept_units": sorted(RULED_KEPT), "unclassified_units": sorted(unclassified),
                "units": by_unit, "excluded": len(excluded), "excluded_reports": excluded},
            "candidates": len(rows),
            "order": "by National Academies publication id, ascending",
            "note": ("the catalogue gives a year, not a date: a candidate dated after %s within %s is caught by "
                     "the draw's date test" % (hi, hi[:4])) if hi[5:] != "12-31" else "",
            "excluded_topics": EXCLUDED_TOPICS, "queries_logged": F.log, "rows": rows}


def check_nasem(F: Fetcher, row: dict, window: tuple[str, str]) -> dict:
    """The protocol's eligibility tests on one National Academies candidate,
    as nasem_frame applies them; each result with what it rested on."""
    lo, hi = window
    tests = {}
    ex = topic_exclusion(row["title"])
    tests["not_a_whu_topic"] = {"pass": not ex, "why": ex or "no match"}
    yr_ok = bool(row["year"]) and int(lo[:4]) <= row["year"] <= int(hi[:4])
    tests["published_in_window"] = {"pass": yr_ok, "why": "catalogue year %s" % row["year"]}
    if yr_ok and row["year"] == int(hi[:4]) and hi[5:] != "12-31":
        # The catalogue gives a year only; in the window's last year the month
        # comes from the DOI's Crossref record.
        code, body = F.get("https://api.crossref.org/works/%s" % row["doi"], kind="crossref")
        dp = (((json.loads(body).get("message") or {}).get("published") or {}).get("date-parts") or [[None]])[0] \
            if code == 200 else [None]
        if len(dp) > 1 and dp[1]:
            ok = "%04d-%02d" % (dp[0], dp[1]) <= hi[:7]
            tests["published_in_window"] = {"pass": ok, "why": "catalogue year %s; Crossref %04d-%02d" % (row["year"], dp[0], dp[1])}
        else:
            tests["published_in_window"] = {"pass": False, "undetermined": True,
                                            "why": "catalogue year %s; no month in Crossref (HTTP %s)" % (row["year"], code)}
    s = nap_summary(F, row["id"])
    tests["states_a_certainty_grade"] = {
        "pass": bool(s.get("graded")),
        "why": ({"summary_chapter": s["chapter"], "evidence_levels": s["evidence_levels"],
                 "confidence_levels": s["confidence_levels"]} if s.get("found") else s["why"]),
        **({} if s.get("found") else {"undetermined": True})}
    tests["public_abstract"] = {"pass": bool(s.get("found")),
                                "why": ("its Summary chapter is free to read online (OpenBook, %d characters, sha256 %s)"
                                        % (s["chars"], s["sha256"][:16])) if s.get("found") else "no Summary chapter read online",
                                **({} if s.get("found") or not s.get("unfetched") else {"undetermined": True})}
    return tests


def draw(F: Fetcher, frame_file: Path, seed: int, window: tuple[str, str], stop_after: int | None = None,
         stopped_why: str = "") -> dict:
    """THE DRAW for a frame with no full eligible list (study README, "Draw
    procedure"): shuffle the candidate list with random.Random(seed), test
    eligibility in that order, and the first eligible candidate is the draw.
    Every candidate checked is logged with its result and reason. A candidate
    whose test could not be completed (a page not fetched) is logged as
    undetermined and passed over, never drawn."""
    frame = json.loads(frame_file.read_text(encoding="utf-8"))
    order = [r["n"] for r in frame["rows"]]
    random.Random(seed).shuffle(order)
    by_n = {r["n"]: r for r in frame["rows"]}
    log, drawn = [], None
    for k, n in enumerate(order, 1):
        row = by_n[n]
        tests = check_nasem(F, row, window)
        ok = all(t["pass"] for t in tests.values())
        und = [t for t, v in tests.items() if v.get("undetermined")]
        log.append({"checked": k, "n": n, "id": row["id"], "title": row["title"], "year": row["year"],
                    "eligible": ok, "undetermined": und, "tests": tests, "at": now()})
        print("  %3d. n=%-4d %-6s %s %s" % (k, n, row["id"], "ELIGIBLE" if ok else ("undetermined" if und else "not eligible"),
                                         row["title"][:80]), file=sys.stderr)
        if ok:
            drawn = row
            break
        if stop_after and k >= stop_after:
            break
    stopped = ({"after_checking": len(log), "why": stopped_why}
               if stop_after and not drawn and len(log) < len(order) else None)
    return {"frame_file": str(frame_file.relative_to(STUDY)), "frame_sha256": sha(frame_file.read_bytes()),
            "seed": seed, "procedure": "random.Random(seed).shuffle of the candidate numbers n; eligibility tested in that "
                                       "order; the first eligible candidate is the draw",
            "shuffled_order_first_50": order[:50], "candidates": len(order), "checked": len(log),
            "drawn": {k: drawn[k] for k in ("n", "id", "doi", "title", "year", "url")} if drawn else None,
            "drawn_at": now(), **({"stopped": stopped} if stopped else {}), "log": log, "queries_logged": F.log}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frame", choices=["cochrane", "campbell", "nasem", "ipcc", "nasem-practice", "ipcc-ar5-practice",
                                      "draw-ipcc-ar5-practice", "draw-cochrane", "draw-campbell", "draw-ipcc",
                                      "nasem-list", "nasem-practice-list", "draw-nasem-practice", "draw-nasem"])
    ap.add_argument("--seed", type=int, help="for a practice draw")
    ap.add_argument("--commit", help="for a study draw: the full 40-character freeze commit hash (the seed)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--cache", required=True, help="scratch directory for fetched pages (never committed)")
    ap.add_argument("--stop-after", type=int, help="a draw stopped by a ruling: write the log after this many candidates")
    ap.add_argument("--stopped-why", default="", help="the ruling that stopped the draw (recorded in the log)")
    ap.add_argument("--offline", action="store_true", help="read the cache only; fetch nothing")
    a = ap.parse_args()
    F = Fetcher(Path(a.cache), nap_pause=20.0)
    F.offline = a.offline
    out = Path(a.out)
    if a.frame in ("draw-cochrane", "draw-campbell", "draw-ipcc"):
        which = a.frame[len("draw-"):]
        try:
            seed_from_commit(a.commit or "")
        except ValueError as e:
            raise SystemExit(str(e))
        ff = out / ("%s.json" % which)
        # The frame drawn from must be the one the freeze commit holds.
        if frame_at_commit(ff, a.commit) != sha(ff.read_bytes()):
            raise SystemExit("%s is not as committed in %s (or that commit does not hold it): the draw uses "
                             "the frozen frame" % (ff, a.commit))
        f = out / "draws" / ("%s-%s.json" % (which, a.commit))
        if f.exists():
            raise SystemExit("%s exists: a draw is made once" % f)
        res = draw_study(ff, a.commit, ipcc_texts(F) if which == "ipcc" else None, STUDY_DRAW_PLAN[which])
        (out / "draws").mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("draw %s from commit %s: checked %d of %d eligible; drawn %s -> %s"
              % (which, a.commit[:12], res["checked"], res["eligible"],
                 ", ".join(str(d.get("id") or d.get("pmid")) for d in res["drawn"]) or "nothing", f))
        return 0 if len(res["drawn"]) == STUDY_DRAW_PLAN[which] else 1
    if a.frame.startswith("draw-"):
        if a.seed is None:
            raise SystemExit("a draw needs --seed")
        which = a.frame[len("draw-"):]
        f = out / "draws" / ("%s-seed%d.json" % (which, a.seed))
        if f.exists():
            raise SystemExit("%s exists: a draw is made once" % f)
        if which == "ipcc-ar5-practice":
            res = draw_listed(out / ("%s.json" % which), a.seed)
            (out / "draws").mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            print("draw %s seed %d: checked %d of %d; drawn %s -> %s" % (which, a.seed, res["checked"], res["candidates"],
                                                                      (res["drawn"] or {}).get("id"), f))
            return 0
        res = draw(F, out / ("%s.json" % which), a.seed,
                   PRACTICE_WINDOW if which == "nasem-practice" else STUDY_WINDOW, a.stop_after, a.stopped_why)
        if a.offline:
            res["offline_replay"] = ("written from the fetch cache with no network: each 'at' is the replay's time; "
                                     "an uncached page is logged with status 0 and its test is undetermined")
        (out / "draws").mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("draw %s seed %d: checked %d of %d; drawn %s -> %s" % (which, a.seed, res["checked"], res["candidates"],
                                                                  (res["drawn"] or {}).get("id"), f))
        return 0
    if a.frame in ("nasem-list", "nasem-practice-list"):
        which = a.frame[:-len("-list")]
        res = nasem_list(F, which, PRACTICE_WINDOW if which == "nasem-practice" else STUDY_WINDOW)
        f = out / ("%s.json" % which)
        out.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("%s: %d consensus-report candidates of %d catalogue entries -> %s"
              % (which, res["candidates"], res["query"].get("listing_cards", 0), f))
        return 0
    if a.frame == "cochrane":
        res = review_frame(F, "cochrane", "Cochrane Database Syst Rev")
    elif a.frame == "campbell":
        res = review_frame(F, "campbell", "Campbell Syst Rev")
    elif a.frame == "nasem":
        res = nasem_frame(F, "nasem", STUDY_WINDOW)
    elif a.frame == "nasem-practice":
        res = nasem_frame(F, "nasem-practice", PRACTICE_WINDOW)
    elif a.frame == "ipcc-ar5-practice":
        res = ipcc_ar5_frame(F, "ipcc-ar5-practice")
    else:
        res = ipcc_frame(F, "ipcc")
    out.mkdir(parents=True, exist_ok=True)
    f = out / ("%s.json" % a.frame)
    f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("%s: %d candidates, %d eligible -> %s" % (a.frame, res["candidates"], res["eligible_count"], f))
    print(json.dumps(res["test_counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
