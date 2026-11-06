"""Per-question cost with no drafting agent (item 4; docs/whu-orchestrator.md §5). $0: it reads stored records and
the ledger, and calls nothing.

likely = pipeline (the run's own ledger total: every stage the orchestrator runs, as measured)
       + the new model steps that replace the drafting agent, sized from the stored records
       + the overstatement check (every bound sentence-passage pair on the stored page)
worst  = the sum of every step's cap (orch/steps.py): the most the guard lets a run spend.

Token sizes are approximate (characters / 4 for Claude, / 3.0 for Google, both erring high for English prose);
prices are spend_ledger.rates at the date of the estimate, and the Google figure is also given at the price that
applies after 2026-11-30.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
_sp = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend/scripts/spend_ledger.py")
S = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(S)

from orch import steps as ST  # noqa: E402
from orch import model_steps as M  # noqa: E402
from orch import overstatement as O  # noqa: E402

CLAUDE_CPT = 4.0
GOOGLE_CPT = 3.0
RUN_CAP = 10.0                   # the lean run cap (validity_plan.md §10)
GOOGLE_OUT_LIKELY = 400          # reply + thinking, per call (an assumption: no Google call has been made)


def _usd(model: str, tin: int, tout: int, at=None) -> float:
    p = S.rates(model, tin, at) if at else S.rates(model, tin)
    return (tin * p["input"] + tout * p["output"]) / 1e6


def _tok(s: str, cpt: float = CLAUDE_CPT) -> int:
    return int(len(s or "") / cpt) + 1


def one(slug: str) -> dict:
    import bindings as B
    import ruling as R
    import audit_stage as A
    case = next((ROOT / "issues").glob("WHU-*-%s" % slug))
    issue = json.loads((case / "issue.json").read_text(encoding="utf-8"))
    q = issue.get("question") or ""
    ledger = [e for e in S.entries() if e.get("issue") == slug]
    pipeline = round(sum(float(e.get("usd") or 0) for e in ledger), 4)
    recency = [float(e.get("usd") or 0) for e in ledger if e.get("role") == "recency"]
    premise = json.loads((case / "premise.json").read_text(encoding="utf-8"))
    fixed = {k: premise.get(k) for k in ("belief", "kill_condition", "reader_with_a_decision", "scope",
                                         "evidence_standard")}
    page = (case / "draft" / ("%s.html" % slug)).read_text(encoding="utf-8")
    import changecheck
    sentences = changecheck.sentences_of(page, drop_tags=True)
    body_chars = sum(len(s) for s in sentences)
    cov = json.loads((case / "coverage.json").read_text(encoding="utf-8")) if (case / "coverage.json").exists() \
        else {}
    n_decl = len(cov.get("declarations") or {})
    jd = json.loads((case / "judgements.json").read_text(encoding="utf-8"))
    n_rel = sum(1 for c in (jd.get("candidates") or {}).values() if c.get("relevant"))
    held = R.held_texts(slug)
    rows = B.load(slug).get("bindings") or {}
    pairs = [p for p in O.pairs(rows, held, A.locate) if p.get("passage")]
    g_in = [_tok(O.PROMPT % (p["passage"], p["sentence"]), GOOGLE_CPT) for p in pairs]

    new = {}
    new["premise"] = _usd(ST.DRAFT_MODEL, _tok(M.PREMISE_PROMPT + q), int(_tok(json.dumps(fixed)) * 1.3))
    new["discover"] = (sum(recency) / len(recency)) if recency else ST.BY_NAME["discover"].cap_usd
    draft_in = _tok(M.DRAFT_PROMPT + q) + _tok("x" * 60000)
    new["draft"] = _usd(ST.DRAFT_MODEL, draft_in, int(_tok("x" * body_chars) * 1.6))
    new["coverage"] = n_decl * _usd(ST.STEP_MODEL, _tok(M.COVERAGE_PROMPT) + 250, 120)
    new["judgement_sentences"] = n_rel * _usd(ST.STEP_MODEL, _tok(M.JUDGEMENT_PROMPT) + 120, 80)
    google_now = sum(_usd(ST.GOOGLE, t, GOOGLE_OUT_LIKELY) for t in g_in) + _usd(ST.GOOGLE, 10, 10)
    later = datetime(2026, 12, 1, tzinfo=timezone.utc)
    google_later = sum(_usd(ST.GOOGLE, t, GOOGLE_OUT_LIKELY, later) for t in g_in) + _usd(ST.GOOGLE, 10, 10, later)
    worst_google = sum(_usd(ST.GOOGLE, t, 2 * 1024, later) for t in g_in)   # a re-ask on every pair, later price
    new = {k: round(v, 4) for k, v in new.items()}
    likely = round(pipeline + sum(new.values()) + google_now, 2)
    # PESSIMISTIC: the draft and premise asked twice (a reply outside the schema), discover at its cap, every
    # overstatement pair asked twice at the later price, and the repeat group's audit and changecheck spend
    # once more (one repeat of steps 12-18).
    repeat = sum(float(e.get("usd") or 0) for e in ledger
                 if e.get("role") in ("audit", "changecheck") or str(e.get("role", "")).startswith("conclusion"))
    pess = round(pipeline + repeat + 2 * new["premise"] + ST.BY_NAME["discover"].cap_usd + 2 * new["draft"]
                 + new["coverage"] + new["judgement_sentences"] + worst_google, 2)
    # WORST: the issue's run cap, which every paid call checks (spend_ledger.check_cap via cap_for); the
    # orchestrator refuses an issue without one. The step caps sum higher and never bind before it.
    run_cap = float(issue.get("run_cap_usd") or RUN_CAP)
    worst = round(min(run_cap, sum(s.cap_usd for s in ST.STEPS)), 2)
    return {"slug": slug, "pipeline_ledger": pipeline, "new_model_steps": new,
            "overstatement": {"pairs": len(pairs), "input_tokens_approx": sum(g_in),
                              "likely_usd_now": round(google_now, 4),
                              "likely_usd_after_2026_11_30": round(google_later, 4),
                              "pessimistic_usd_reask_every_pair_after_2026_11_30": round(worst_google, 4)},
            "likely_total": likely, "pessimistic_total": pess, "sum_of_step_caps": round(sum(x.cap_usd for x in ST.STEPS), 2),
            "likely_total_after_2026_11_30": round(pipeline + sum(new.values()) + google_later, 2),
            "worst_total_caps": worst,
            "inputs": {"page_sentences": len(sentences), "coverage_declarations": n_decl,
                       "relevant_judgements": n_rel, "recency_calls_measured": len(recency)}}


def estimate_all(slugs) -> dict:
    rows = [one(s) for s in slugs]
    ls = sorted(r["likely_total"] for r in rows)
    med = ls[len(ls) // 2] if len(ls) % 2 else round((ls[len(ls) // 2 - 1] + ls[len(ls) // 2]) / 2, 2)
    return {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "questions": rows,
            "summary": {"likely": {r["slug"]: r["likely_total"] for r in rows}, "likely_median": med,
                        "pessimistic": {r["slug"]: r["pessimistic_total"] for r in rows},
                        "worst_each": rows[0]["worst_total_caps"] if rows else None,
                        "overstatement_pairs": {r["slug"]: r["overstatement"]["pairs"] for r in rows}}}
