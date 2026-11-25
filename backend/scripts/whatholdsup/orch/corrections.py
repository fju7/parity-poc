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


class RegistryUnavailable(RuntimeError):
    """A registry did not answer (after the orchestrator's retries): no status is recorded from the others."""


UNANSWERED = re.compile(r"^HTTP (5\d\d|429) from|^[A-Za-z_.]*(Error|Exception|Timeout)\b|^timed out", re.I)


def _answered_or_raise(rec, why: str, what: str):
    """lookup/crossref return (None, why) both for 'no record' (an answer) and for an outage (not one)."""
    if rec is None and UNANSWERED.search(why or ""):
        raise RegistryUnavailable("%s: %s" % (what, why))
    return rec, why


def _ids(src: dict) -> list[tuple[str, str]]:
    out = []
    for kind, key in (("PMCID", "pmcid"), ("PMID", "pmid"), ("DOI", "doi")):
        if src.get(key):
            out.append((kind, str(src[key])))
    got = E.identifier_of(src)
    if got and got not in out:
        out.append(got)
    return out


MIN_ANSWERING = 2            # ruling 2 after attempt 24: a status needs answers from two of the three registries
NOT_CHECKABLE = "no registry record; retraction status not checkable"     # ruling 4 after the fallback build
RETRACTION_PUBMED = {"RetractionIn", "RetractionofPublicationIn"}
CONCERN_PUBMED = {"ExpressionOfConcernIn"}
CORRECTION_PUBMED = {"ErratumIn", "RepublishedIn", "CorrectedandRepublishedIn"}


def _as_answer(registry: str, got):
    """An injected lookup's (record, why) as a registries.Answer: an outage when WHY reads like one."""
    import registries as RG
    if isinstance(got, RG.Answer):
        return got
    rec, why = got
    return RG.Answer(registry, not (rec is None and UNANSWERED.search(why or "")), rec, why=why or "")


def _default_clients():
    import registries as RG
    return (lambda k, v: RG.epmc_id(k, v), lambda d: RG.crossref_work(d), lambda k, v: RG.pubmed_record(k, v))


def status(src: dict, lookup=None, crossref=None, pubmed=None) -> dict:
    """{"retracted", "concern", "why", "corrections": [{"id", "registry", "type"}], "answered": [...], "doi",
    "registries": [{"registry", "asked", "answered", "record", "why"}]}.

    Ruling 2 after attempt 24 (2026-11-24): Europe PMC, PubMed and Crossref are each asked (each retried by the
    orchestrator); a registry ANSWERS when it replies -- with this source's record, or a definite "no record" -- and
    does not when it is still unavailable after its retries. With fewer than two answering, RegistryUnavailable (the
    run stops "registry unavailable; run again later"); otherwise the status is the union of what the answering
    registries record, every registry's answer is recorded, and an outage among them is marked covered.
    Ruling 4 after the fallback build: a status also needs at least one registry returning THIS source's record
    (each record held to errata.resolves_to_us); the status is taken from every registry that returned it
    (`status_from`; each correction carries `found_by`; each registry row its `findings`). With two answering and
    no record anywhere -- or no identifier to ask by -- the status is "no registry record; retraction status not
    checkable" (`checkable` False, `retracted` None), never clean. LOOKUP / CROSSREF / PUBMED are injected in
    tests; given LOOKUP or CROSSREF without PUBMED, PubMed is recorded "not asked"."""
    import registries as RG
    injected = lookup is not None or crossref is not None
    d_lookup, d_crossref, d_pubmed = _default_clients()
    lookup = lookup or d_lookup
    crossref = crossref or d_crossref
    if pubmed is None and not injected:
        pubmed = d_pubmed
    out = {"retracted": False, "concern": False, "why": [], "corrections": [], "answered": [], "doi": src.get("doi"),
           "registries": []}
    ids = _ids(src)
    if not ids:
        out.update(checkable=False, state=NOT_CHECKABLE, retracted=None, status_from=[],
                   why=["no DOI, PMID or PMCID to ask any registry by"])
        return out
    answers, outages = [], []          # (Answer, asked) per registry; every unanswered call, to cover
    # Europe PMC: each identifier until one gives this source's record
    rec, epmc_answered, epmc_url = None, False, None
    for kind, value in ids:
        ans = _as_answer(RG.EUROPE_PMC, lookup(kind, value))
        if not ans.answered:
            outages.append(ans)
            out["answered"].append("Europe PMC %s %s: %s" % (kind, value, ans.why))
            continue
        epmc_answered, epmc_url = True, ans.url
        if ans.record is not None:
            same, why_same = E.resolves_to_us(ans.record, src)
            if not same:
                out["answered"].append("Europe PMC %s %s: %s (not used)" % (kind, value, why_same))
                continue
            rec = ans.record
            out["answered"].append("Europe PMC %s %s" % (kind, value))
            break
        out["answered"].append("Europe PMC %s %s: %s" % (kind, value, ans.why))
    answers.append((RG.Answer(RG.EUROPE_PMC, epmc_answered, rec, url=epmc_url,
                              why="; ".join(a for a in out["answered"] if a.startswith("Europe PMC"))),
                    ", ".join("%s %s" % i for i in ids)))
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
                out["corrections"].append({"id": str(a.get("id")), "registry": a.get("source") or "MED", "type": t,
                                           "found_by": ["Europe PMC"]})
        out["doi"] = out["doi"] or rec.get("doi")
    # PubMed: by PMID, else by DOI or PMCID
    if pubmed is None:
        answers.append((RG.Answer(RG.PUBMED, False, why="not asked (no PubMed client given)"), "-"))
    else:
        pid = next(((k, v) for k, v in ids if k == "PMID"), None) or \
            (("PMID", str(rec["pmid"])) if rec is not None and rec.get("pmid") else None) or \
            next(((k, v) for k, v in ids if k in ("DOI", "PMCID")), None)
        ans = _as_answer(RG.PUBMED, pubmed(*pid)) if pid else RG.Answer(RG.PUBMED, False, why="no identifier")
        if pid and not ans.answered:
            outages.append(ans)
        pm = ans.record
        if pm is not None:
            same, why_same = E.resolves_to_us(pm, src)
            if not same:
                ans = RG.Answer(RG.PUBMED, True, None, why="%s (not used)" % why_same, url=ans.url)
                pm = None
        out["answered"].append("PubMed %s %s%s" % (pid[0], pid[1], "" if pm is not None else ": " + ans.why)
                               if pid else "PubMed: no identifier to ask by")
        answers.append((ans, "%s %s" % pid if pid else "-"))
        if pm is not None:
            if "Retracted Publication" in pm.get("pubtypes") or []:
                out["retracted"] = True
                out["why"].append("PubMed publication type: Retracted Publication")
            for link in pm.get("links") or []:
                ty = link.get("type") or ""
                if ty in RETRACTION_PUBMED:
                    out["retracted"] = True
                    out["why"].append("PubMed: %s %s" % (ty, link.get("pmid")))
                elif ty in CONCERN_PUBMED:
                    out["concern"] = True
                    out["why"].append("PubMed: %s %s" % (ty, link.get("pmid")))
                elif ty in CORRECTION_PUBMED and link.get("pmid"):
                    out["corrections"].append({"id": str(link["pmid"]), "registry": "MED", "type": ty,
                                               "found_by": ["PubMed"]})
            out["doi"] = out["doi"] or pm.get("doi")
    # Crossref: by DOI
    if out["doi"]:
        ans = _as_answer(RG.CROSSREF_NAME, crossref(out["doi"]))
        if not ans.answered:
            outages.append(ans)
        answers.append((ans, "DOI %s" % out["doi"]))
        msg = ans.record
        if msg is not None:
            same, why_same = E.resolves_to_us(E.crossref_title_record(msg), src)
            if not same:                        # a record that is not this source says nothing about it
                ans = RG.Answer(RG.CROSSREF_NAME, True, None, why="%s (not used)" % why_same, url=ans.url)
                answers[-1] = (ans, answers[-1][1])
                msg = None
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
                    out["corrections"].append({"id": str(ident), "registry": "DOI", "type": t,
                                               "found_by": ["Crossref"]})
        else:
            out["answered"].append("Crossref %s: %s" % (out["doi"], ans.why))
    else:
        answers.append((RG.Answer(RG.CROSSREF_NAME, False, why="no DOI to ask by"), "-"))
    rows = []
    for a, asked in answers:
        r = a.row(asked)
        r["findings"] = [w for w in out["why"] if w.startswith(a.registry)]
        rows.append(r)
    out["registries"] = rows
    answering = [a.registry for a, _ in answers if a.answered]
    if len(answering) < MIN_ANSWERING:
        raise RegistryUnavailable("%d of 3 registries answered (%s): %s" % (
            len(answering), ", ".join(answering) or "none",
            "; ".join("%s %s" % (a.registry, a.why) for a, _ in answers if not a.answered)))
    for a in outages:
        RG.covered(a, answering)
    out["status_from"] = [a.registry for a, _ in answers if a.answered and a.record is not None]
    if not out["status_from"]:
        out.update(checkable=False, state=NOT_CHECKABLE, retracted=None)
        out["why"].append("%s answered; none holds this source's record" % ", ".join(answering))
        return out
    out.update(checkable=True, state="checked")
    seen, uniq = {}, []
    for c in out["corrections"]:
        k = c["id"].lower()
        if k not in seen:
            seen[k] = c
            uniq.append(c)
        else:
            seen[k]["found_by"] = list(dict.fromkeys(seen[k].get("found_by", []) + c.get("found_by", [])))
    out["corrections"] = uniq
    return out


def _plain(xml_or_html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", xml_or_html or "").split())


def notice_text(c: dict, lookup=None, fulltext=None, pubmed=None, pmc=None) -> tuple[str | None, str]:
    """(the notice's text, how it was got), or (None, why not).

    Ruling 2 after the fallback build (2026-11-24): with LOOKUP not injected, a Europe PMC outage on the notice's
    record falls back to PubMed's record (its abstract and PMCID), and a Europe PMC outage on its full text falls
    back to NCBI PMC's copy (registries.pmc_fulltext, the same copy rule); a fallback that answers covers the
    outage. Nothing answering raises RegistryUnavailable, as before."""
    kind = "PMID" if c.get("registry") in ("MED", "PMID") else "DOI"
    injected = lookup is not None               # a test's lookup: no real registry is asked unless also injected
    if lookup is None and pubmed is not False:
        import registries as RG
        first = RG.epmc_id(kind, c["id"])
        if first.answered:
            rec, why = first.record, first.why
        else:
            alt = (pubmed or RG.pubmed_record)(kind, c["id"])
            if not alt.answered:
                raise RegistryUnavailable("Europe PMC and PubMed %s %s (correction notice): %s; %s" % (
                    kind, c["id"], first.why, alt.why))
            RG.covered(first, ["PubMed"])
            if alt.record is None:
                return None, "Europe PMC unavailable; PubMed has no record of the notice (%s)" % alt.why
            pm = alt.record
            text = _plain(pm.get("abstract") or "")
            pmcid = pm.get("pmcid")
            if pmcid:
                got = (pmc or RG.pmc_fulltext)(pmcid)
                if not got.answered:
                    raise RegistryUnavailable("NCBI PMC full text %s (correction notice): %s" % (pmcid, got.why))
                body = _notice_body(got.record["xml"]) if got.record else None
                if body and len(body) > len(text):
                    return body, "NCBI PMC full text %s (Europe PMC unavailable)" % pmcid
            if len(text) >= MIN_NOTICE_CHARS and not text.startswith("[This corrects the article"):
                return text, "PubMed abstract of %s %s (Europe PMC unavailable)" % (kind, c["id"])
            return None, "no text of the notice could be held (Europe PMC unavailable; PubMed abstract %d " \
                         "characters%s)" % (len(text), "; NCBI PMC serves no full text" if pmcid else "")
    else:
        lookup = lookup or E.lookup
        rec, why = _answered_or_raise(*lookup(kind, c["id"]), "Europe PMC %s %s (correction notice)" % (kind,
                                                                                                         c["id"]))
    if rec is None:
        return None, why
    text = _plain(rec.get("abstractText") or "")
    pmcid = rec.get("pmcid")
    served = bool(pmcid) and E.epmc_full_text_served(rec)     # the record's own metadata, read first (ruling, attempt 13)
    body, pmc_why = None, ""
    if served:
        body, how = (fulltext or _fulltext)(pmcid)
        if body is None and UNANSWERED.search(how or "") and not re.search(r"HTTP Error 4\d\d", how or ""):
            if fulltext is not None or pmc is False:
                raise RegistryUnavailable("Europe PMC full text %s: %s" % (pmcid, how))
            import registries as RG
            got = (pmc or RG.pmc_fulltext)(pmcid)           # ruling 2 after the fallback build
            if not got.answered:
                raise RegistryUnavailable("Europe PMC and NCBI PMC full text %s: %s; %s" % (pmcid, how, got.why))
            RG.covered(RG.Answer(RG.EUROPE_PMC, False, url=_fulltext_url(pmcid)), ["PMC"])
            body = _notice_body(got.record["xml"]) if got.record else None
            if body and len(body) > len(text):
                return body, "NCBI PMC full text %s (Europe PMC unavailable)" % pmcid
        elif body and len(body) > len(text):
            return body, "Europe PMC full text %s" % pmcid
    if pmcid and fulltext is None and pmc is not False and (not injected or pmc) and (not served or body is None):
        # Europe PMC lacks the copy (its metadata says not served, or a 4xx): NCBI PMC under the same rule (ruling 3
        # after P091); an outage there stops the run
        import registries as RG
        got = (pmc or RG.pmc_fulltext)(pmcid)
        if not got.answered:
            raise RegistryUnavailable("NCBI PMC full text %s (correction notice): %s" % (pmcid, got.why))
        pbody = _notice_body(got.record["xml"]) if got.record else None
        if pbody and len(pbody) > len(text):
            return pbody, "NCBI PMC full text %s (Europe PMC does not serve it)" % pmcid
        pmc_why = "; NCBI PMC: %s" % got.why[:160]
    if len(text) >= MIN_NOTICE_CHARS and not text.startswith("[This corrects the article"):
        return text, "Europe PMC abstract of %s %s" % (kind, c["id"])
    return None, "no text of the notice could be held (abstract %d characters%s%s)" % (
        len(text), "; full text not served (Europe PMC metadata: isOpenAccess %s)" % rec.get("isOpenAccess")
        if pmcid and not served else "; full text not served" if pmcid else "; no full text", pmc_why)


def _fulltext_url(pmcid: str) -> str:
    return "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % pmcid


def _fulltext(pmcid: str) -> tuple[str | None, str]:
    import urllib.request
    url = _fulltext_url(pmcid)
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


def _fold(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"[\u2010-\u2015\u2212]", "-", t)
    t = re.sub(r"[^a-z0-9.\-/ ]+", " ", t)
    return " ".join(t.split())


def names_source(text: str, src: dict) -> bool:
    """Ruling 2026-11-07 (after attempt 4): a notice applies to a held source only if the part of it that describes
    a correction -- its text as held, the body, never the front matter -- names that source by title, DOI or PMID."""
    body = _fold(text)
    title = _fold((src.get("title") or "").rstrip(". "))
    if title and len(title.split()) >= 4 and title in body:
        return True
    for k in ("doi", "pmid", "pmcid"):
        v = str(src.get(k) or "").strip().lower()
        if v and re.search(r"(?<![\w.])%s(?![\w])" % re.escape(v), body):
            return True
    return False


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
