#!/usr/bin/env python3
"""Build the study's sampling frames (protocol, "Question selection"; rev 33).

    frames.py cochrane|campbell|nasem|ipcc [--out DIR]
    frames.py nasem-practice [--out DIR]          National Academies, 2017-2023

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
import sys
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
    "T04 vitamin D (over 60)": r"vitamin D|cholecalciferol|ergocalciferol|calcifediol|calcitriol",
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


def nap_listing(F: Fetcher, y0: int, y1: int, query: dict) -> dict:
    """The National Academies' own catalogue listing, filtered to publication
    years y0..y1: {id: {title, type, year}} from each card (its type label, e.g.
    "Consensus Study Report", and its year). Pages are read until one adds
    nothing new."""
    out: dict = {}
    base = "https://www.nationalacademies.org/publications/all?" + urllib.parse.urlencode(
        {"publication_date[from]": y0, "publication_date[to]": y1})
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
# IPCC AR6 headline statements
# --------------------------------------------------------------------------

IPCC_REPORTS = [
    ("WGI", "Climate Change 2021: The Physical Science Basis", 2021, "https://www.ipcc.ch/report/ar6/wg1/resources/spm-headline-statements/"),
    ("WGII", "Climate Change 2022: Impacts, Adaptation and Vulnerability", 2022, "https://www.ipcc.ch/report/ar6/wg2/resources/spm-headline-statements/"),
    ("WGIII", "Climate Change 2022: Mitigation of Climate Change", 2022, "https://www.ipcc.ch/report/ar6/wg3/resources/spm-headline-statements/"),
    ("SYR", "Climate Change 2023: Synthesis Report", 2023, "https://www.ipcc.ch/report/ar6/syr/resources/spm-headline-statements/"),
]


def ipcc_frame(F: Fetcher, name: str) -> dict:
    rows, query = [], {"pages": [r[3] for r in IPCC_REPORTS], "api": "none: IPCC publishes no API; the official headline-statement pages are fetched"}
    for wg, title, year, url in IPCC_REPORTS:
        _c, body = F.get(url, kind="ipcc")
        t = re.sub(r"(?s)<(script|style|header|footer|nav).*?</\1>", " ", body.decode("utf-8", "replace"))
        x = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
        marks = list(re.finditer(r"(?<![\w.])(?:SPM\.)?([A-E]\.\d{1,2})(?=\s+[A-Z])", x))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(x)
            s = x[m.end():end]
            s = re.split(r"\s(?:Download|Share|Related|Footnotes?|Sections?)\b|\s\{[^}]*\}\s*\.?\s*(?=[A-Z][a-z]+ [A-Z])", s)[0].strip()
            cal = sorted({c.group(0).lower() for c in IPCC_CALIBRATED.finditer(s)})
            tests = {"published_in_window": {"pass": 2021 <= year <= 2023, "why": "AR6 %s, %d" % (wg, year)},
                     "states_a_certainty_grade": {"pass": bool(cal), "why": cal or "no calibrated confidence or likelihood term in the statement"},
                     "public_abstract": {"pass": True, "why": "the headline statement is published in full on ipcc.ch"},
                     "not_a_whu_topic": {"pass": not topic_exclusion(s), "why": topic_exclusion(s) or "no match"}}
            rows.append({"id": "AR6-%s-%s" % (wg, m.group(1)), "report": title, "year": year, "url": url,
                         "statement_chars": len(s), "statement_sha256": sha(s), "first_words": " ".join(s.split()[:10]),
                         "tests": tests, "eligible": all(v["pass"] for v in tests.values())})
    return finish(name, F, rows, query, {
        "published_in_window": "AR6 report year, 2021 to 2023",
        "states_a_certainty_grade": "the headline statement itself carries IPCC calibrated language: a confidence level "
                                    "('high confidence') or a likelihood term ('very likely'); 'unequivocal' alone does not count",
        "public_abstract": "IPCC publishes every headline statement in full",
        "not_a_whu_topic": "the statement matches none of the excluded-topic patterns (EXCLUDED_TOPICS)"})


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


def nasem_list(F: Fetcher, name: str, window: tuple[str, str]) -> dict:
    """The National Academies frame as a CANDIDATE list only (2026-10-21): every
    publication the catalogue labels a Consensus Study Report in the window's
    years, from the listing pages alone. Eligibility is not tested here; the
    draw tests candidates one at a time in seeded order (draw())."""
    lo, hi = window
    query: dict = {"api": "none: the National Academies publish no API; their catalogue listing is read"}
    cards = nap_listing(F, int(lo[:4]), int(hi[:4]), query)
    cand = sorted(((nid, c) for nid, c in cards.items() if c["type"] == CONSENSUS), key=lambda kv: int(kv[0]))
    types: dict = {}
    for c in cards.values():
        types[c["type"] or "(no label)"] = types.get(c["type"] or "(no label)", 0) + 1
    rows = [{"n": i, "id": nid, "doi": "10.17226/%s" % nid, "title": c["title"], "year": c["year"],
             "url": "https://www.nationalacademies.org/publications/%s" % nid}
            for i, (nid, c) in enumerate(cand, 1)]
    return {"frame": name, "kind": "candidate list (no eligibility tested; see draw)", "built_at": now(),
            "script": "study/whu-reliability/scripts/frames.py", "window": {"from": lo, "to": hi},
            "query": query, "listing_cards_by_type": dict(sorted(types.items(), key=lambda x: -x[1])),
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


def draw(F: Fetcher, frame_file: Path, seed: int, window: tuple[str, str]) -> dict:
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
    return {"frame_file": str(frame_file.relative_to(STUDY)), "frame_sha256": sha(frame_file.read_bytes()),
            "seed": seed, "procedure": "random.Random(seed).shuffle of the candidate numbers n; eligibility tested in that "
                                       "order; the first eligible candidate is the draw",
            "shuffled_order_first_50": order[:50], "candidates": len(order), "checked": len(log),
            "drawn": {k: drawn[k] for k in ("n", "id", "doi", "title", "year", "url")} if drawn else None,
            "drawn_at": now(), "log": log, "queries_logged": F.log}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frame", choices=["cochrane", "campbell", "nasem", "ipcc", "nasem-practice",
                                      "nasem-list", "nasem-practice-list", "draw-nasem-practice", "draw-nasem"])
    ap.add_argument("--seed", type=int, help="for a draw")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--cache", required=True, help="scratch directory for fetched pages (never committed)")
    a = ap.parse_args()
    F = Fetcher(Path(a.cache), nap_pause=20.0)
    out = Path(a.out)
    if a.frame.startswith("draw-"):
        if a.seed is None:
            raise SystemExit("a draw needs --seed")
        which = a.frame[len("draw-"):]
        f = out / "draws" / ("%s-seed%d.json" % (which, a.seed))
        if f.exists():
            raise SystemExit("%s exists: a draw is made once" % f)
        res = draw(F, out / ("%s.json" % which), a.seed,
                   PRACTICE_WINDOW if which == "nasem-practice" else STUDY_WINDOW)
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
