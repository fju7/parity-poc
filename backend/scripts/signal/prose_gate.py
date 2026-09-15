"""The response-boundary gate for Signal's four prose surfaces.

Shared assertion policy (verify/policy.py), surfaces:
    scripts.signal.score_claims::generate_summaries       plain summary per claim
    scripts.signal.map_consensus::map_category            consensus prose per category
    scripts.signal.generate_summary::generate_narrative   overall summary + takeaways
    scripts.signal.generate_summary::generate_glossary    glossary definitions

Why these needed their own gate: publish_topic binds every CLAIM to its
fetched source (FIGURE, HEADING, SPAN, CHRONOLOGY) and withholds what does
not bind. The prose ABOUT the claims -- what the topic page mostly shows --
was never checked. Measured on the frozen mmr-vaccine-autism record on
2026-09-15 (docs/shared-assertion-policy-phase-a-inventory.md, Signal
section): narrative, takeaways, consensus and glossary bound fully; the
plain summaries carried 26 unbound figures of 98, of which 22 were counting
words ("two theories") and 4 were facts the model added ("before 37 weeks",
"over half a million US dollars", "1.0 would mean identical risk"). Two of
those four render.

Rules, all deterministic (verify.policy.check):
    identifiers   must be ones the prompt carried (there are none: refuse)
    named sources must appear in the material handed over, by lexicon term
                  ("CDC" binds "Centers for Disease Control")
    figures       digit-form must be in the claim(s) handed over or the
                  sources' text (integer rounding of a handed number allowed);
                  word-form counting numbers <= 12 are FLAGGED, not refused
A refused plain summary is not stored -- the claim renders without one. A
refused consensus or narrative is not stored -- the run fails, loudly.

Every run writes its verdicts to data/signal/verification/<slug>/ so a
person can see what was refused and why. That directory is gitignored: it
is a run artefact, like the pipeline's other outputs.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND))

from verify.policy import check, Held  # noqa: E402
from verify.types import Document, Identifier  # noqa: E402

RUN_DIR = BACKEND / "data" / "signal" / "verification"


def _doc(text: str, label: str) -> Document:
    return Document(Identifier("url", label), "", text or "", kind="record", text_layer="DECLARED_SOUND")


def source_texts(sb, claim_ids: list[str]) -> dict[str, list[str]]:
    """claim_id -> [title + content_text of each linked source]. One query
    per call; callers pass a batch."""
    if not claim_ids:
        return {}
    links = sb.table("signal_claim_sources").select("claim_id, source_id").in_("claim_id", claim_ids).execute().data or []
    sids = sorted({l["source_id"] for l in links})
    srcs = {}
    if sids:
        rows = sb.table("signal_sources").select("id, title, content_text").in_("id", sids).execute().data or []
        srcs = {r["id"]: (r.get("title") or "") + "\n" + (r.get("content_text") or "") for r in rows}
    out: dict[str, list[str]] = {}
    for l in links:
        out.setdefault(l["claim_id"], []).append(srcs.get(l["source_id"], ""))
    return out


# ---------------------------------------------------------------------------
# the four gates
# ---------------------------------------------------------------------------
SURF_SUMMARIES = "scripts.signal.score_claims::generate_summaries"
SURF_CONSENSUS = "scripts.signal.map_consensus::map_category"
SURF_NARRATIVE = "scripts.signal.generate_summary::generate_narrative"
SURF_GLOSSARY = "scripts.signal.generate_summary::generate_glossary"


def gate_plain_summaries(sb, batch: list[dict], summaries: list[dict]) -> tuple[list[dict], list[dict]]:
    """(kept, verdicts). A summary whose figures or names are not in its claim
    or its sources is dropped; the claim keeps rendering without it."""
    by_id = {str(c["id"]): c for c in batch}
    srcs = source_texts(sb, list(by_id))
    kept, verdicts = [], []
    for item in summaries:
        cid = str(item.get("claim_id") or "")
        text = item.get("plain_summary") or ""
        claim = by_id.get(cid)
        if not claim or not text:
            continue
        held = Held(inputs={"claim_text": claim.get("claim_text", "")},
                    documents=[_doc(t, f"source:{cid}") for t in srcs.get(cid, [])])
        v = check(SURF_SUMMARIES, {"plain_summary": text}, held)
        rec = v.to_dict(); rec["claim_id"] = cid
        verdicts.append(rec)
        if v.ok:
            kept.append(item)
        else:
            print(f"  [REFUSED] plain summary for {cid[:8]}: {v.note()[:200]}")
    return kept, verdicts


def gate_consensus(result: dict, category: str, claims: list[dict], sources: list[str] | None = None) -> dict | None:
    """The consensus prose (summary_text, arguments_for/against) must bind to
    the claims the model was handed. Returns the verdict record; None on ok."""
    held = Held(inputs={"claims": [c.get("claim_text", "") for c in claims], "category": category},
                documents=[_doc(t, f"source:{category}") for t in (sources or [])])
    text = {k: result.get(k) or "" for k in ("summary_text", "arguments_for", "arguments_against")}
    v = check(SURF_CONSENSUS, text, held)
    rec = v.to_dict(); rec["category"] = category
    if not v.ok:
        print(f"  [REFUSED] consensus prose for {category}: {v.note()[:300]}")
    return rec


def gate_narrative(narrative: dict, user_text: str) -> dict:
    """overall_summary + every category takeaway bind to the stats and
    sections the model was handed (which already include the claims)."""
    held = Held(documents=[_doc(user_text, "narrative_input")])
    text = {"overall_summary": narrative.get("overall_summary") or "",
            "category_takeaways": narrative.get("category_takeaways") or {}}
    v = check(SURF_NARRATIVE, text, held)
    rec = v.to_dict()
    if not v.ok:
        print(f"  [REFUSED] narrative: {v.note()[:300]}")
    return rec


def gate_glossary(glossary: dict, all_text: str) -> dict:
    held = Held(documents=[_doc(all_text, "glossary_input")])
    v = check(SURF_GLOSSARY, {"glossary": glossary or {}}, held)
    rec = v.to_dict()
    if not v.ok:
        print(f"  [REFUSED] glossary: {v.note()[:300]}")
    return rec


def write_run_record(slug: str, script: str, verdicts) -> Path | None:
    try:
        d = RUN_DIR / slug
        d.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        p = d / f"{script}-{ts}.json"
        p.write_text(json.dumps({"slug": slug, "script": script, "written_at": ts, "verdicts": verdicts}, indent=1), encoding="utf-8")
        return p
    except Exception as exc:
        print(f"  [WARN] could not write verification record: {exc}")
        return None
