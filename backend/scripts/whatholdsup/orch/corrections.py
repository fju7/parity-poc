"""Retractions and corrections of an orchestrated run's sources (advisor's ruling 2026-11-07).

At `acquire`, every source's bibliographic record is read (Europe PMC: pubType and commentCorrection; Crossref:
updated-by and relation):
  - a RETRACTED source is not held: nothing on the page draws on it and the page says so
    (lean_sentences.RETRACTED_FRAME);
  - a correction to a source NOT HELD needs no action (errata.preflight_rows passes it: nothing draws on the source);
  - a correction to a HELD source is fetched as a linked record on that source (`correction_notices`, the notice's
    text in the case folder's corrections/), not a new source. A notice that cannot be held makes the source not
    held (lean_sentences.CORRECTION_NOT_HELD_FRAME).
After the bound sentences exist (steps `corrections_3b` and, in the repeat group, `corrections`), every page sentence
whose bound passage shares a figure or a run of 5+ consecutive content words with a notice leaves the page under the
fail-safe ("removed: affected by correction <notice id>"), unless it re-binds against the notice's corrected text:
its own figures all appear in the notice's corrected text (or, with no figure, it shares a 5-word run with it).

Identifiers come from the registry-given fields of the source and from its URL (errata.identifier_of); nothing is
typed. Lookups are injected in tests (recorded responses).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import errata as E

RETRACTION_EPMC = {"Retraction in"}
# Expression of concern (advisor's ruling 2026-11-07, after attempt 4): treated like a retraction.
CONCERN_EPMC = {"Expression of concern in"}
CONCERN_PUBTYPES = {"Expression of Concern"}
CONCERN_CROSSREF = {"expression_of_concern", "expression-of-concern", "expressionofconcern", "concern"}
CORRECTION_EPMC = {"Erratum in", "Corrected and republished in"}
RETRACTION_CROSSREF = {"is-retracted-by", "retraction", "withdrawal", "removal"}
CORRECTION_CROSSREF = {"is-corrected-by", "has-correction", "is-expressed-by-erratum", "correction", "erratum",
                       "corrigendum"}
MIN_NOTICE_CHARS = 40
REASON = "removed: affected by correction %s"
PATH = "correction"
NOTICE_DIR = "corrections"


def _ids(src: dict) -> list[tuple[str, str]]:
    out = []
    for kind, key in (("PMCID", "pmcid"), ("PMID", "pmid"), ("DOI", "doi")):
        if src.get(key):
            out.append((kind, str(src[key])))
    got = E.identifier_of(src)
    if got and got not in out:
        out.append(got)
    return out


def status(src: dict, lookup=None, crossref=None) -> dict:
    """{"retracted", "why", "corrections": [{"id", "registry", "type"}], "answered": [...], "doi"}."""
    lookup = lookup or E.lookup
    crossref = crossref or E.crossref
    out = {"retracted": False, "concern": False, "why": [], "corrections": [], "answered": [], "doi": src.get("doi")}
    rec = None
    for kind, value in _ids(src):
        rec, why = lookup(kind, value)
        if rec is not None:
            same, why_same = E.resolves_to_us(rec, src)
            if not same:
                out["answered"].append("Europe PMC %s %s: %s (not used)" % (kind, value, why_same))
                rec = None
                continue
            out["answered"].append("Europe PMC %s %s" % (kind, value))
            break
        out["answered"].append("Europe PMC %s %s: %s" % (kind, value, why))
    if rec is not None:
        types = (rec.get("pubTypeList") or {}).get("pubType") or []
        types = [types] if isinstance(types, str) else types
        if "Retracted Publication" in types:
            out["retracted"] = True
            out["why"].append("Europe PMC pubType: Retracted Publication")
        for t in CONCERN_PUBTYPES & set(types):
            out["concern"] = True
            out["why"].append("Europe PMC pubType: %s" % t)
        amend, _disc = E.amendments(rec)
        for a in amend:
            t = a.get("type") or ""
            if t in RETRACTION_EPMC:
                out["retracted"] = True
                out["why"].append("Europe PMC: %s %s" % (t, a.get("id")))
            elif t in CONCERN_EPMC:
                out["concern"] = True
                out["why"].append("Europe PMC: %s %s" % (t, a.get("id")))
            elif t in CORRECTION_EPMC:
                out["corrections"].append({"id": str(a.get("id")), "registry": a.get("source") or "MED", "type": t})
        out["doi"] = out["doi"] or rec.get("doi")
    if out["doi"]:
        msg, why = crossref(out["doi"])
        if msg is not None:
            out["answered"].append("Crossref %s" % out["doi"])
            for a in E.crossref_amendments(msg):
                t = (a.get("type") or "").lower()
                ident = a.get("id")
                if not ident or str(ident).lower() == str(out["doi"]).lower():
                    continue                    # a record pointing at the work itself
                if t in RETRACTION_CROSSREF:
                    out["retracted"] = True
                    out["why"].append("Crossref: %s %s" % (t, ident))
                elif t in CONCERN_CROSSREF:
                    out["concern"] = True
                    out["why"].append("Crossref: %s %s" % (t, ident))
                elif t in CORRECTION_CROSSREF:
                    out["corrections"].append({"id": str(ident), "registry": "DOI", "type": t})
        else:
            out["answered"].append("Crossref %s: %s" % (out["doi"], why))
    seen, uniq = set(), []
    for c in out["corrections"]:
        k = c["id"].lower()
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    out["corrections"] = uniq
    return out


def _plain(xml_or_html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", xml_or_html or "").split())


def notice_text(c: dict, lookup=None, fulltext=None) -> tuple[str | None, str]:
    """(the notice's text, how it was got), or (None, why not)."""
    lookup = lookup or E.lookup
    kind = "PMID" if c.get("registry") in ("MED", "PMID") else "DOI"
    rec, why = lookup(kind, c["id"])
    if rec is None:
        return None, why
    text = _plain(rec.get("abstractText") or "")
    pmcid = rec.get("pmcid")
    if pmcid:
        body, how = (fulltext or _fulltext)(pmcid)
        if body and len(body) > len(text):
            return body, "Europe PMC full text %s" % pmcid
    if len(text) >= MIN_NOTICE_CHARS and not text.startswith("[This corrects the article"):
        return text, "Europe PMC abstract of %s %s" % (kind, c["id"])
    return None, "no text of the notice could be held (abstract %d characters%s)" % (
        len(text), "; full text not served" if pmcid else "; no full text")


def _fulltext(pmcid: str) -> tuple[str | None, str]:
    import urllib.request
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": E.UA}), timeout=30) as fh:
            body = fh.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    return _notice_body(body), url


def _notice_body(xml: str) -> str | None:
    """The notice's own words: the article <body> (else its <abstract>), never the front matter, whose volume,
    dates, PMCID and PMID are numbers the page sweep would otherwise match (found on attempt 4's held notice)."""
    for tag in ("body", "abstract"):
        m = re.search(r"<%s\b[^>]*>(.*?)</%s>" % (tag, tag), xml or "", re.S)
        if m:
            text = _plain(m.group(1))
            if len(text) >= MIN_NOTICE_CHARS:
                return text
    return None


def hold_notice(case: Path, c: dict, text: str, how: str) -> dict:
    d = Path(case) / NOTICE_DIR
    d.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    name = re.sub(r"[^A-Za-z0-9._-]", "_", c["id"]) + ".txt"
    (d / name).write_text(text, encoding="utf-8")
    return dict(c, held=True, file="%s/%s" % (NOTICE_DIR, name), sha256=sha, how=how)


# -------------------------------------------------------------------------------------------- the page sweep

STOP_WORDS = set("""a an the and or of to in on for with by at from as is are was were be been being this that these
those it its their there which who whom whose than then into over under between among about after before during not no
nor but if so such can could may might must should would will shall do does did done has have had having also more most
less least very each per we our they them he she his her you your""".split())
FIGURE_RE = re.compile(r"(?<![\w.])(\d+(?:[.,·]\d+)*)(\s*%)?")
NOT_A_FIGURE_BEFORE = re.compile(r"(?:table|figure|fig\.|page|p\.|section|appendix|supplement(?:ary)?)\s*$", re.I)


def figures(text: str) -> set[str]:
    out = set()
    for m in FIGURE_RE.finditer(text or ""):
        raw = m.group(1).replace("·", ".")
        if NOT_A_FIGURE_BEFORE.search((text or "")[max(0, m.start() - 14):m.start()]):
            continue
        digits = raw.replace(",", "").replace(".", "")
        is_int = "." not in raw
        if is_int and not m.group(2):
            n = int(raw.replace(",", "")) if raw.replace(",", "").isdigit() else 0
            if n < 10 or (1900 <= n <= 2099 and len(digits) == 4):
                continue                         # a count word's worth, or a year
        out.add(raw.replace(",", "") + ("%" if m.group(2) else ""))
    return out


def runs(text: str, n: int = 5) -> set[tuple]:
    words = [w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 3 and w not in STOP_WORDS]
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


CORRECTED_MARK = re.compile(r"(?:should (?:have )?read|should be|has been corrected to|is corrected to|"
                            r"correct(?:ed)? (?:value|text|version|figure)s? (?:is|are|reads?)|now reads?)\s*[:\-–]?",
                            re.I)


def corrected_text(notice: str) -> str:
    """What the notice says is right: the text after each "should read" (and the like) to the end of its sentence."""
    out = []
    for m in CORRECTED_MARK.finditer(notice or ""):
        rest = notice[m.end():]
        end = re.search(r"(?<=[.;])\s+(?=[A-Z\"“])|\n", rest)
        out.append(rest[:end.start()] if end else rest)
    return " ".join(out)


def affected(span: str, notice: str) -> bool:
    return bool(figures(span) & figures(notice)) or bool(runs(span) & runs(notice))


def rebinds(sentence: str, notice: str) -> bool:
    fixed = corrected_text(notice)
    if not fixed:
        return False
    sf = figures(sentence)
    if sf:
        return sf <= figures(fixed)
    return bool(runs(sentence) & runs(fixed))


def sweep(case: Path, rows: dict, page_sentences: list[str], removal) -> dict:
    """Every bound sentence on the page against its source's held notices. REMOVAL(it) records the fail-safe
    (lean_failsafe.record). Returns counts and the decisions (also written to rulings/corrections.jsonl)."""
    from orch.page import norm
    doc = json.loads((Path(case) / "sources.json").read_text(encoding="utf-8"))
    notices = {}
    for s in doc.get("sources") or []:
        for c in s.get("correction_notices") or []:
            if c.get("held") and c.get("file"):
                notices.setdefault(s["id"], []).append(
                    (c["id"], (Path(case) / c["file"]).read_text(encoding="utf-8")))
    on_page = {norm(x) for x in page_sentences}
    counts = {"checked": 0, "removed": 0, "rebound": 0}
    log = Path(case) / "rulings" / "corrections.jsonl"
    for sha, row in sorted(rows.items()):
        sentence = norm(row.get("sentence") or "")
        if sentence not in on_page or not row.get("span"):
            continue
        spans = [(row.get("source_id"), row.get("span"))] + [
            (x.get("source_id"), x.get("span")) for x in row.get("also_rests_on") or []]
        for sid, span in spans:
            for nid, text in notices.get(sid) or []:
                counts["checked"] += 1
                if not affected(span or "", text):
                    continue
                decision = "rebound" if rebinds(sentence, text) else "removed"
                counts[decision] += 1
                rec = {"sentence": sentence, "sentence_sha": sha, "source_id": sid, "notice": nid,
                       "decision": decision}
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if decision == "rebound":
                    row["corrected_by"] = nid
                else:
                    removal({"kind": "correction", "sentence": row.get("sentence") or sentence,
                             "ref": {"finding_key": "correction:%s:%s" % (nid, sha), "notice": nid,
                                     "reason": REASON % nid}, "protected": None})
    return counts
