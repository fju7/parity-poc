"""publish_topic: gate every source and every claim of a Signal topic and
freeze a reproducible record of what each claim rested on.

Phase 3 design §1. The record, not the date, is the freeze: a person can
answer "what did claim N rest on, on the day it was published" from the
record and the content-addressed documents it names, offline, later.

This module never flips signal_issues.status. The CLI does, only with
--flip, only after the record is written, and only if the operator says so.
"""
from __future__ import annotations

import datetime as dt
import getpass
import gzip
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__, literature, law, generic, supplied
from .bind import bind_figure, bind_heading, bind_span, _QUOTE
from .chronology import bind_chronology
from .numbers import figures, canonical_numbers
from .status import check as status_check
from .types import Document, Exists, Provenance

BACKEND = Path(__file__).resolve().parents[1]
PUBLISHED = BACKEND / "data" / "verify" / "published"
DOCS = BACKEND / "data" / "verify" / "docs"

SUPPORT_ORDER = ["UNSUPPORTED", "IDENTITY_ONLY", "SPAN_BOUND", "FIGURE_BOUND"]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def gate_version() -> dict:
    """The package version and the committed sha of backend/verify. Refuses a dirty tree:
    the record must name a gate that exists in the repository."""
    root = BACKEND.parent
    sha = subprocess.run(["git", "log", "-1", "--format=%h", "--", "backend/verify"], cwd=root,
                         capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "backend/verify"], cwd=root,
                           capture_output=True, text=True).stdout.strip()
    if not sha or dirty:
        raise SystemExit("backend/verify has uncommitted changes (or no commit); the record must name a "
                         "committed gate. Commit first.")
    tree = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    return {"package": __version__, "verify_sha": sha, "tree_sha": tree}


def store_document(doc: Document) -> str:
    DOCS.mkdir(parents=True, exist_ok=True)
    sub = DOCS / doc.sha256[:2]; sub.mkdir(exist_ok=True)
    p = sub / (doc.sha256 + ".txt.gz")
    if not p.exists():
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.write(doc.text)
    return str(p.relative_to(BACKEND))


def _b(binding) -> dict:
    return {"kind": binding.kind.value, "ok": binding.ok, "abstained": binding.abstained,
            "evidence": binding.evidence, "reason": binding.reason}


def _frozen_status_fields(res) -> dict:
    ident = res.identifier
    if ident.system == "nct":
        sm = (res.extra.get("status") or {})
        return {"overallStatus": sm.get("overallStatus"),
                "lastUpdatePostDate": (sm.get("lastUpdatePostDateStruct") or {}).get("date")}
    if ident.system == "cfr":
        return {"as_of": res.extra.get("as_of")}
    return {}


_run_cache: dict[str, tuple] = {}   # identifier -> (resolution, document, status): one fetch per identifier per run


def gate_source(row: dict) -> dict:
    """One signal_sources row through identify -> resolve -> fetch -> HEADING -> status.

    Two rows with the same identifier (mmr stores several papers twice under
    different source types) share one resolve/fetch/status within a run, so a
    transient on the second call cannot make the same document survive on one
    row and fail on the other."""
    out = {"source_id": row["id"], "url": row.get("url"), "title": row.get("title"),
           "source_type": row.get("source_type"), "identifier": None, "resolution": None,
           "document": None, "bindings": [], "status": None, "survives": False, "withheld_reason": None}
    ident = literature.identify(row.get("url") or "", Provenance.RESOLVED_FROM_HELD) or \
        law.identify(row.get("url") or "", Provenance.RESOLVED_FROM_HELD) or \
        generic.identify(row.get("url") or "", Provenance.RESOLVED_FROM_HELD)
    if ident is None:
        out["withheld_reason"] = "UNVERIFIABLE: no identifier and no fetchable URL"
        return out
    out["identifier"] = {"system": ident.system, "value": ident.value, "provenance": ident.provenance.value}
    mod = {"literature": literature, "law": law, "generic": generic}[ident.registry]
    key = ident.system + ":" + ident.value
    if key in _run_cache:
        res, doc, st_cached = _run_cache[key]
    else:
        res, doc, st_cached = mod.resolve(ident), None, None
    out["resolution"] = {"exists": res.exists.value, "heading": res.heading, "canonical": res.canonical,
                         "registry": res.registry, "registry_id": res.registry_id, "checked_at": res.checked_at,
                         "generic_fetch": res.registry == "generic_fetch",
                         "published": (res.extra or {}).get("published") or ((res.extra or {}).get("year") and [(res.extra or {}).get("year")]),
                         "effective": (res.extra or {}).get("effective"),
                         "first_author": (res.extra or {}).get("first_author"),
                         "container": (res.extra or {}).get("container") or (res.extra or {}).get("journal")}
    out["_res"] = res
    if res.exists != Exists.EXISTS:
        # UNCHECKED with a registry_unavailable note is "the registry did not
        # answer" -- a fact about the network, kept apart from NONEXISTENT,
        # which is the registry's answer about the source.
        unavailable = (res.extra or {}).get("registry_unavailable")
        out["withheld_reason"] = (f"fetch: HTTP {res.extra.get('http')} {res.extra.get('reason') or res.extra.get('error') or ''}".strip()
                                  if res.registry == "generic_fetch" else
                                  ("resolve: REGISTRY_UNAVAILABLE " + "; ".join(f"{k}: {v}" for k, v in unavailable.items())) if unavailable
                                  else f"resolve: {res.exists.value}")
        if unavailable:
            out["resolution"]["registry_unavailable"] = unavailable
        return out
    # HEADING before fetch: a DOI that names a different paper is withheld as
    # WRONG_DOCUMENT, not as a fetch failure of the wrong paper.
    head = bind_heading(row.get("title") or "", res)
    out["bindings"].append(_b(head))
    if not head.ok and not head.abstained:
        out["withheld_reason"] = "HEADING: " + head.reason
        return out
    doc = doc if doc is not None else mod.fetch(res)
    if doc is None and ident.registry == "literature" and res.canonical:
        # No registry text (a notice, a feature article, a report): one more
        # attempt through the generic adapter at the publisher, via doi.org.
        # The record says which route got the bytes.
        g = generic.resolve(generic.identify(res.canonical))
        gdoc = generic.fetch(g)
        if gdoc is not None:
            doc = gdoc
            out["resolution"]["fallback"] = {"route": "generic_fetch via doi.org", "final_url": g.extra.get("final_url")}
        else:
            out["resolution"]["fallback"] = {"route": "generic_fetch via doi.org", "http": g.extra.get("http"),
                                             "reason": g.extra.get("reason") or g.extra.get("error")}
    supplied_entry = None
    if doc is None and ident.registry == "literature":
        # A document a person fetched by hand (verify/supplied.py), admitted
        # only after its title matched the registry's. Used last, and the
        # record says so: provenance, hash, who, and where from.
        got = supplied.lookup(ident)
        if got is not None:
            doc, supplied_entry = got
            out["resolution"]["fallback"] = {"route": "operator_supplied", "sha256": supplied_entry["sha256"],
                                             "supplied_by": supplied_entry["supplied_by"], "source_url": supplied_entry["source_url"],
                                             "retrieved_at": supplied_entry["retrieved_at"], "record": supplied_entry["record"]}
    if doc is None:
        fb = out["resolution"].get("fallback") or {}
        unavailable = (res.extra or {}).get("fetch_unavailable")
        if unavailable:
            # the registry that serves the text did not answer: a fact about
            # the network, recorded apart from "the publisher served nothing"
            out["resolution"]["fetch_unavailable"] = unavailable
            out["withheld_reason"] = "fetch: REGISTRY_UNAVAILABLE " + "; ".join(f"{k}: {v}" for k, v in unavailable.items()) \
                + (f" (publisher: HTTP {fb.get('http')} {fb.get('reason') or ''})".rstrip() if fb else "")
        else:
            out["withheld_reason"] = "fetch: nothing retrieved" + (f" (publisher: HTTP {fb.get('http')} {fb.get('reason') or ''})".rstrip() if fb else "")
        return out
    _run_cache[key] = (res, doc, st_cached)
    out["document"] = {"sha256": doc.sha256, "route": doc.route, "kind": doc.kind, "retrieved_at": doc.retrieved_at,
                       "chars": len(doc.text), "text_layer": doc.text_layer, "path": store_document(doc),
                       "final_url": doc.final_url,
                       # who got the bytes: the machine, or a named person (Provenance.OPERATOR_SUPPLIED)
                       "provenance": "OPERATOR_SUPPLIED" if supplied_entry else "MACHINE_FETCH",
                       "supplied_by": supplied_entry["supplied_by"] if supplied_entry else None}
    out["registry_text"] = " ".join(str(x) for x in ((res.heading or ""), res.extra.get("year") or "") if x)
    if ident.registry == "generic":
        # No registry can report a retraction or amendment for a bare URL;
        # the monthly re-check is the only watch it has, and the record says so.
        out["status"] = {"verdict": "no_registry", "registry": "generic_fetch",
                         "detail": "no status registry for a generic URL; watched by the binding re-check only",
                         "checked_at": _now(), "events": [], "frozen": {}}
    else:
        st = st_cached or status_check(ident)
        _run_cache[key] = (res, doc, st)
        out["status"] = {"verdict": st.verdict, "registry": st.registry, "detail": st.detail,
                         "checked_at": st.checked_at, "events": st.events, "frozen": _frozen_status_fields(res)}
    out["survives"] = True
    out["_doc"] = doc
    return out


# Statuses that, found at publication on a SUPPORT link, refuse the link. The
# red marker then only ever means "this changed after we froze it".
REFUSING_STATUS_AT_PUBLISH = {"retracted", "withdrawn", "concern", "corrected", "superseded",
                              "trial_status_changed", "amended", "reissued"}


def link_role(claim_text: str, src: dict) -> tuple[str, dict]:
    """subject | support, and the rule that decided it, recorded for audit.

    A claim is ABOUT the source when it names it: the first author's surname
    (from the registry) or a distinctive word of the registry heading appears
    in the claim text. Otherwise the source is claimed as support. The
    heuristic will misclassify eventually; the record says what matched."""
    from .text import content_tokens, normalise, LITERATURE_BOILERPLATE
    text = normalise(claim_text)
    res = src.get("_res")
    fa = ((res.extra or {}).get("first_author") if res else None) or ""
    if fa and re.search(r"\b" + re.escape(normalise(fa)) + r"\b", text):
        return "subject", {"matched": fa, "kind": "first_author"}
    heading = (res.heading if res else None) or src.get("title") or ""
    from .text import TITLE_COMMON
    for w in sorted(content_tokens(heading.split(" || ")[0], LITERATURE_BOILERPLATE), key=len, reverse=True):
        # A title word names the source only if it is not the topic's own
        # vocabulary: "children" and "vaccination" are in every heading here;
        # "hyperplasia" is in one. The list is explicit so a misclassification
        # is traceable to a word, and the record says which word fired.
        if len(w) >= 8 and w not in TITLE_COMMON and re.search(r"\b" + re.escape(w) + r"\b", text):
            return "subject", {"matched": w, "kind": "title_word"}
    return "support", {"matched": None, "kind": "no_name_in_claim"}


_erratum_cache: dict[str, list] = {}


def erratum_texts(src: dict) -> list[dict]:
    """The erratum notices the registry lists for this source, with their text
    when it can be read: [{doi, pmid, title, date, text | None, route}]."""
    key = src.get("id") or src.get("source_id")
    if key in _erratum_cache:
        return _erratum_cache[key]
    out = []
    for ev in (src.get("status") or {}).get("events") or []:
        t = (ev.get("type") or "").lower()
        if not (t.startswith("erratum") or t.startswith("correction")):
            continue
        raw = ev.get("doi") or ev.get("id")
        if not raw:
            continue
        ident = literature.identify(raw)
        if ident is None:
            continue
        res = literature.resolve(ident)
        doc = literature.fetch(res) if res.exists == Exists.EXISTS else None
        route = doc.route if doc else None
        if doc is None and res.exists == Exists.EXISTS and res.canonical:
            g = generic.resolve(generic.identify(res.canonical)); gdoc = generic.fetch(g)
            if gdoc:
                doc, route = gdoc, "generic_fetch via doi.org"
            else:
                route = f"unretrievable (publisher HTTP {g.extra.get('http')})"
        out.append({"doi": (res.extra or {}).get("doi") or (ident.value if ident.system == "doi" else None),
                    "pmid": (res.extra or {}).get("pmid") or (ident.value if ident.system == "pmid" else None),
                    "title": res.heading, "date": ev.get("date") or (res.extra or {}).get("year"),
                    "text": doc.text if doc else None, "route": route})
    _erratum_cache[key] = out
    return out


def erratum_check(figs: list[str], src: dict) -> dict:
    """Does the erratum touch a figure the claim asserts? A binding-shaped record."""
    errata = erratum_texts(src)
    if not errata:
        return {"kind": "ERRATUM", "ok": False, "abstained": False, "evidence": "",
                "reason": "the registry reports a correction but names no erratum record to read"}
    unread = [e for e in errata if not e["text"]]
    if unread:
        return {"kind": "ERRATUM", "ok": False, "abstained": False,
                "evidence": "; ".join(f"{e['title']} ({e['doi'] or e['pmid']})" for e in unread),
                "reason": "erratum text could not be read (" + "; ".join(e["route"] or "no route" for e in unread)
                          + "); it cannot be said not to touch the asserted figure",
                "erratum": errata}
    touched = []
    for e in errata:
        have = canonical_numbers(e["text"])
        touched += [f for f in figs if f in have]
    if touched:
        return {"kind": "ERRATUM", "ok": False, "abstained": False, "evidence": ", ".join(sorted(set(touched))),
                "reason": "the erratum mentions a figure this claim asserts: " + ", ".join(sorted(set(touched))),
                "erratum": errata}
    return {"kind": "ERRATUM", "ok": True, "abstained": False,
            "evidence": "; ".join(f"{e['title']} ({e['doi'] or e['pmid']}, {e['date']})" for e in errata),
            "reason": "the erratum does not mention any figure this claim asserts", "erratum": errata}


def gate_claim(claim: dict, links: list[dict], sources: dict[str, dict]) -> dict:
    """One signal_claims row against each of its surviving sources."""
    text = claim.get("claim_text") or ""
    # The figures a claim commits to, LESS the years CHRONOLOGY owns. Before
    # 2026-09-15 "the Smeeth 2004 study found no ..." counted 2004 as a figure,
    # FIGURE then said "no figure in assertion" once the date was stripped, and
    # the claim was levelled FIGURE_BOUND -- the page's strongest label -- on a
    # year alone: 29 of 64 on the mmr record, one of them a false bind (a
    # payment-by-lawyers claim on a notice that never mentions lawyers, which
    # happened to contain 1998). A claim whose only figure is a year is
    # source-confirmed (IDENTITY_ONLY), never figure-bound.
    from .chronology import claim_dates
    years = {str(d.year) for d, _ in claim_dates(text)}
    figs = sorted(figures(text) - years)
    quoted = bool(_QUOTE.search(text))
    out = {"claim_id": claim["id"], "claim_text": text, "category": claim.get("category"),
           "figures": figs, "years": sorted(years), "quotation": quoted, "per_source": [], "support": "UNSUPPORTED", "supported_by": []}
    for link in links:
        src = sources.get(link["source_id"])
        if not src:
            continue
        entry = {"source_id": link["source_id"], "source_survives": bool(src.get("survives")), "bindings": []}
        if not src.get("survives"):
            entry["bindings"].append({"kind": "SOURCE", "ok": False, "abstained": False, "evidence": "",
                                      "reason": src.get("withheld_reason") or "source did not survive"})
            out["per_source"].append(entry); continue
        doc = src["_doc"]
        level = "IDENTITY_ONLY"
        role, rule = link_role(text, src)
        entry["role"] = role; entry["role_rule"] = rule
        chrono = bind_chronology(text, src["_res"], (src.get("status") or {}).get("events"))
        entry["bindings"].append(_b(chrono))
        if not chrono.ok:
            entry["level"] = "UNSUPPORTED"
            out["per_source"].append(entry)
            continue
        verdict = (src.get("status") or {}).get("verdict")
        if role == "support" and verdict == "corrected":
            # AN ERRATUM CORRECTS SOMETHING INSIDE A WORK THAT OTHERWISE STANDS
            # (ruling of 2026-09-15). Fetch the erratum and ask whether any
            # figure the claim asserts appears in what it corrects: touched ->
            # UNSUPPORTED; untouched -> publish with an information marker
            # naming the erratum. An erratum that cannot be read cannot be
            # said not to touch the figure: fail closed, and say why.
            er = erratum_check(figs, src)
            entry["bindings"].append(er)
            if not er["ok"]:
                entry["level"] = "UNSUPPORTED"
                out["per_source"].append(entry)
                continue
            entry["erratum"] = er.get("erratum")
        elif role == "support" and verdict in REFUSING_STATUS_AT_PUBLISH:
            # Retraction, withdrawal, concern, superseded, amended: about the
            # work as a whole. A support link is refused at publish, not
            # published with a warning.
            entry["bindings"].append({"kind": "STATUS_AT_PUBLISH", "ok": False, "abstained": False, "evidence": verdict,
                                      "reason": f"support link to a source whose status was {verdict} before publication"})
            entry["level"] = "UNSUPPORTED"
            out["per_source"].append(entry)
            continue
        if role == "subject" and verdict in REFUSING_STATUS_AT_PUBLISH:
            entry["bindings"].append({"kind": "STATUS_AT_PUBLISH", "ok": True, "abstained": False, "evidence": verdict,
                                      "reason": f"subject link: the claim is about a source whose status was {verdict}; publishable, marked as information"})
        if figs:
            fb = bind_figure(text, doc, src.get("registry_text", "")); entry["bindings"].append(_b(fb))
            level = "FIGURE_BOUND" if fb.ok else "UNSUPPORTED"
        if quoted:
            sb = bind_span(text, doc); entry["bindings"].append(_b(sb))
            if sb.ok and level != "UNSUPPORTED":
                level = "SPAN_BOUND" if level == "IDENTITY_ONLY" else level
            elif not sb.ok:
                level = "UNSUPPORTED"
        entry["level"] = level
        out["per_source"].append(entry)
        if SUPPORT_ORDER.index(level) > SUPPORT_ORDER.index(out["support"]):
            out["support"] = level
        if level != "UNSUPPORTED":
            out["supported_by"].append(link["source_id"])
    return out


def publish(sb, slug: str, argv: list[str]) -> dict:
    gv = gate_version()
    issue = sb.table("signal_issues").select("id,slug,title,status").eq("slug", slug).single().execute().data
    iid = issue["id"]
    sources = sb.table("signal_sources").select("id,title,url,source_type,publication_date").eq("issue_id", iid).execute().data
    claims = []
    off = 0
    while True:
        page = sb.table("signal_claims").select("id,claim_text,category,claim_type").eq("issue_id", iid).range(off, off + 999).execute().data
        claims += page
        if len(page) < 1000: break
        off += 1000
    cids = [c["id"] for c in claims]
    links = []
    for i in range(0, len(cids), 100):
        links += sb.table("signal_claim_sources").select("claim_id,source_id,source_context").in_("claim_id", cids[i:i+100]).execute().data
    by_claim: dict[str, list] = {}
    for l in links:
        by_claim.setdefault(l["claim_id"], []).append(l)

    print(f"{slug}: {len(sources)} sources, {len(claims)} claims, {len(links)} claim-source links")
    gated = {}
    for i, row in enumerate(sources, 1):
        g = gate_source(row); gated[row["id"]] = g
        tag = "SURVIVES" if g["survives"] else "withheld"
        st = (g.get("status") or {}).get("verdict") or ""
        print(f"  [{i:2}/{len(sources)}] {tag:9} {(g['identifier'] or {}).get('system','-'):5} {str(row['title'])[:60]:60} "
              f"{g['withheld_reason'] or ((g['document'] or {}).get('kind','') + ' ' + st)}")
    claim_recs = [gate_claim(c, by_claim.get(c["id"], []), gated) for c in claims]

    from collections import Counter
    src_summary = Counter("survived" if g["survives"] else (g["withheld_reason"] or "").split(":")[0] for g in gated.values())
    claim_summary = Counter(c["support"] for c in claim_recs)
    status_summary = Counter((g.get("status") or {}).get("verdict") for g in gated.values() if g["survives"])
    publish_id = _now().replace(":", "").replace("-", "") + "-" + gv["tree_sha"]
    record = {
        "topic": {"slug": slug, "title": issue["title"], "issue_id": iid, "status_before": issue["status"]},
        "publish_id": publish_id, "published_at": _now(),
        "published_by": {"login": getpass.getuser(), "host": platform.node(), "argv": argv},
        "gate_version": gv,
        "rate_limits_rps": __import__("verify.http", fromlist=["rate_limits_in_force"]).rate_limits_in_force(),
        "sources": [{k: v for k, v in g.items() if k not in ("_doc", "_res")} for g in gated.values()],
        "claims": claim_recs,
        "summary": {"sources": {"total": len(sources), "survived": src_summary.get("survived", 0),
                                "withheld_by_reason": {k: v for k, v in src_summary.items() if k != "survived"},
                                "status_of_survivors": dict(status_summary)},
                    "claims": {"total": len(claims), "by_support": dict(claim_summary),
                               "identity_only_rate": round(claim_summary.get("IDENTITY_ONLY", 0) / max(len(claims), 1), 3)}},
        "flipped": False,
    }
    out_dir = PUBLISHED / slug; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{publish_id}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    (out_dir / "latest.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    record["_stored"] = store_publication(sb, record)
    return record


def publication_row(record: dict) -> dict:
    """The topic_publications row: the record plus the two arrays the page filters by."""
    return {
        "slug": record["topic"]["slug"], "publish_id": record["publish_id"],
        "published_at": record["published_at"], "published_by": record["published_by"],
        "gate_version": record["gate_version"], "record": record,
        "supported_claim_ids": [c["claim_id"] for c in record["claims"] if c["support"] != "UNSUPPORTED"],
        "surviving_source_ids": [s["source_id"] for s in record["sources"] if s["survives"]],
        "flipped": record.get("flipped", False),
    }


def store_publication(sb, record: dict) -> str:
    """Upsert the row the site reads. The file is the record of record; this is its mirror."""
    try:
        sb.table("topic_publications").upsert(publication_row(record), on_conflict="slug,publish_id").execute()
        return "stored in topic_publications"
    except Exception as e:  # noqa: BLE001
        return f"NOT stored ({type(e).__name__}: {str(e)[:80]}) -- is migration 080 applied?"
