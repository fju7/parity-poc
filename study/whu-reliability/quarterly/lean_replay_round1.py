#!/usr/bin/env python3
"""What lean WHU would have cost on quarterly round 1: a $0 replay (no model call, no count_tokens call).

Plan doc "WHU next phase", Part B, the estimate after items 1-6. Inputs are only the round-1 case
folders' own records -- issues/WHU-Q1-0*/audit/<run>/{manifest.json, verdicts.jsonl,
second_reads.jsonl}, rulings/rulings.jsonl, rulings/consistency.jsonl, judgements.json -- the held
texts they were read against, the spend ledger's lines for those issues, and
round1_scoring/process_measures_round1.json for the actual totals. No answer key, judge reply or file
under ~/Projects/whu-study-private/ is read.

METHOD, per question
  Audit runs (audit_stage.py). For every run, each round's read units (verdicts.jsonl) are batched as
  the audit batches them (audit_stage.batches / fit_batches) and the reading prompt is rebuilt twice:
  as the run sent it (audit_stage.batch_inputs: trim of the held text) and as lean WHU would
  (lean_audit: bound passages + top-k, a stable group document). Tokens per character are calibrated
  per run from the run's own recorded input tokens over the rebuilt current prompts; lean input
  tokens are that rate times the lean prompts' length. Output tokens are as recorded.
    - tiering: first reads (and re-quotes, and the card/meta summary read) priced at
      lean.STAGE_MODELS["audit_first"]; ESCALATION re-reads, at the current model, for the sentences
      the recorded read did not hold (finding, FAILED_READ, updated_by_source, not_a_correction on a
      bound sentence) -- BASE assumes the smaller model flags those; PESSIMISTIC adds a quarter of the
      remaining read sentences. Rulings and the second reader stay on the current model, as recorded.
    - caching: a group of two or more batches with a stable group document writes its prefix once
      (cache_write) and reads it after (cache_read), at the ledger's cache prices.
    - incremental re-audit: from the second run on, reaudit.plan against the run before decides which
      sentences are read; the rest carry. The second reader reads only the sentences read this run
      (their findings plus the seeded 10%).
  ruling.py (the rest of audit_stage.py's ledger spend). Relevance rulings re-priced at the smaller
  model from their recorded usage, each "not relevant" one escalated (a current-model call of the
  same size); every other ruling, and the consistency samples, as recorded.
  The gate (factcheck_draft.py). advocate-requote and advocate-reask-omission calls see LEAN_K
  retrieved passages in place of trim(): recorded input minus the trimmed text's estimated tokens plus
  the passages'. Every other gate call as recorded (the gate already runs on the smaller model).
Prices are spend_ledger.PRICES only (with its rates() step: claude-haiku-5-5 over 100,000 tokens).

TIERS (advisor's ruling, 2026-10-30). The smaller tier (lean.SMALL_STAGES: audit_first, advocate,
judgements) is replayed three times -- claude-sonnet-4-6 (the first lean default), claude-sonnet-5-5
(the default now), claude-haiku-5-5 (a variant) -- escalation to claude-opus-5-5 unchanged. Under a
5.5 model every advocate call (brief, re-quote, re-ask) is re-priced at that model, its web searches
as recorded. Recorded on claude-sonnet-4-6, those calls carry no thinking and that model's tokenizer:
PESSIMISTIC also counts their input x TOKENIZER_PESS and their output x THINKING_PESS.

CHECK PILOT v4 (check_pilot_v4 in the output): from the ledger's own lines for whu-check-pilot-v3
(8 answers; judge_m1 caches the source text, so a line's cost beyond its input and output is cache
writes). v4 replaces each call's cache-write tokens with its passages: base one source x TOP_K
passages; pessimistic two sources x (TOP_K + 4 top-ups); never more than v3 wrote. Priced at
claude-opus-5-5 (v4 as built: judge_m1.CLAUDE_MODEL) and, for the estimate only, the two 5.5 tiers.

    python3 study/whu-reliability/quarterly/lean_replay_round1.py   writes round1_scoring/lean_replay_round1.json
"""
from __future__ import annotations

import glob
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import audit_stage as A          # noqa: E402
import bindings as B             # noqa: E402
import lean                      # noqa: E402
import lean_audit as LA          # noqa: E402
import passage_index as PI       # noqa: E402
import reaudit as RA             # noqa: E402
import source_advocate as SA     # noqa: E402
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
S_LEDGER = lean._ledger()

QUESTIONS = ("01", "02", "03", "04")
OUT = Path(__file__).resolve().parent / "round1_scoring" / "lean_replay_round1.json"
PM = Path(__file__).resolve().parent / "round1_scoring" / "process_measures_round1.json"
PESSIMISTIC_EXTRA = 0.25
TOKENIZER_PESS = 1.35          # Opus 4.7-family tokenizer vs Sonnet 4.6: ~1x-1.35x tokens (API docs)
THINKING_PESS = 2.0            # output of a call recorded without thinking, on a model that thinks
TIERS = ("sonnet-4-6", "sonnet-5-5", "haiku-5-5")


def price(model, i=0, o=0, cw=0, cr=0):
    return lean.usd(model, i, o, cw, cr)


def run_units(run_dir: Path, rows: dict) -> tuple[list[dict], dict[int, list[dict]], dict[str, str]]:
    """(the run's units in order, {round: units read in it}, {unit: its recorded first verdict})."""
    vs = [json.loads(l) for l in (run_dir / "verdicts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    first = {}
    for v in vs:
        if v.get("round") in (0, 1) and v["unit"] not in first:
            first[v["unit"]] = v
    order = sorted(first, key=lambda i: int(i.lstrip("u")))
    us = [{"id": i, "part": first[i].get("part"), "sentence": first[i]["sentence"], "sha": first[i]["sha"],
           "row": rows.get(first[i]["sha"])} for i in order]
    row_of = {u["id"]: u["row"] for u in us}
    rounds: dict[int, list[dict]] = defaultdict(list)
    for v in vs:
        rd = v.get("round")
        if isinstance(rd, int) and rd >= 1 and v.get("verdict") != A.HUMAN_READ_REQUIRED:
            rounds[rd].append({"id": v["unit"], "part": v.get("part"), "sentence": v["sentence"],
                               "sha": v["sha"], "row": row_of.get(v["unit"])})
    return us, dict(rounds), {i: first[i].get("verdict") for i in first}


def prompt_lengths(slug, units, held, lic, ctx, body):
    """[(current prompt chars, lean prompt chars, lean cached-prefix chars or 0, n units, batch)] per batch."""
    bs = A.fit_batches(slug, A.batches(units), held, lic)
    gd = LA.group_documents(slug, bs, held, lic)
    out = []
    for i, b in enumerate(bs):
        if all(u["part"] in A.SUMMARY_PARTS for u in b):
            p = A.build_summary_prompt(b, body)
            out.append((len(p), len(p), 0, len(b), b, None))
            continue
        docs, recs = A.batch_inputs(slug, b, held, lic)
        cur = A.build_read_prompt(b, docs, recs, ctx, lic)
        ldocs, lrecs = LA.batch_inputs(slug, b, held, lic, group_docs=gd.get(i))
        lp = A.build_read_prompt(b, ldocs, lrecs, ctx, lic)
        pre = LA.cache_prefix(lp, next(iter(gd[i]))) if i in gd else None
        out.append((len(cur), len(lp), len(pre or ""), len(b), b, (ldocs, lrecs, next(iter(gd[i])) if i in gd else None)))
    return out


def escalate_ids(units, first, extra_share, seed=1):
    bound = [u for u in units if A.sources_of(u.get("row"))]
    flagged = {u["id"] for u in units if LA.needs_escalation(u, {"verdict": first.get(u["id"])})}
    rest = [u["id"] for u in bound if u["id"] not in flagged]
    k = round(extra_share * len(rest))
    return flagged | set(random.Random(seed).sample(rest, k) if k else [])


def audit_run(slug, run_dir, prev_dir, held, lic, rows, small, cur):
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    us, rounds, first = run_units(run_dir, rows)
    ctx = A.context_map(us)
    body = A.page_body(us)
    calls = m["calls"]
    rec = {r: [c for c in calls if c["role"] == r] for r in {c["role"] for c in calls}}
    tin = lambda r: sum(c["input"] for c in rec.get(r, []))
    tout = lambda r: sum(c["output"] for c in rec.get(r, []))
    # what this run reads under lean: everything, or the incremental plan against the run before
    plan = {"mode": "full", "why": "first audit of the issue"}
    read_ids = {u["id"] for u in us}
    if prev_dir is not None:
        plan = RA.plan(slug, us, held, {**m, "inputs": m.get("inputs") or {}}, prev_dir)
        read_ids = set(plan["read"])
    r1 = [u for u in rounds.get(1, []) if u["id"] in read_ids]
    later = [u for rd in sorted(rounds) if rd > 1 for u in rounds[rd] if u["id"] in read_ids]
    # calibration: recorded read input tokens / rebuilt current prompt chars, all rounds of the run
    all_read = rounds.get(1, []) + [u for rd in sorted(rounds) if rd > 1 for u in rounds[rd]]
    cal = prompt_lengths(slug, all_read, held, lic, ctx, body)
    cur_chars = sum(c for c, *_ in cal if True)
    read_roles = [r for r in rec if r.startswith("read") and "requote" not in r]
    rate = sum(tin(r) for r in read_roles) / max(1, cur_chars)
    out_per_unit = sum(tout(r) for r in read_roles) / max(1, len(all_read))
    res = {"run": run_dir.name, "recorded_usd": round(m.get("usd") or 0, 4), "units": len(us),
           "read_under_lean": len(read_ids), "plan": plan.get("mode"), "plan_why": plan.get("why"),
           "tokens_per_char": round(rate, 4)}
    for scen, extra in (("base", 0.0), ("pessimistic", PESSIMISTIC_EXTRA)):
        usd = 0.0
        lens = prompt_lengths(slug, r1 + later, held, lic, ctx, body)
        esc = escalate_ids(r1 + later, first, extra)
        seen_group = set()
        lean_in_total = 0
        for curc, leanc, prec, n, b, info in lens:
            out_t = out_per_unit * n
            tokens = rate * leanc
            lean_in_total += tokens
            if prec:
                sid = info[2]
                pre_t = rate * prec
                if sid in seen_group:
                    usd += price(small, tokens - pre_t, out_t, 0, pre_t)
                else:
                    usd += price(small, tokens - pre_t, out_t, pre_t, 0)
                    seen_group.add(sid)
            else:
                usd += price(small, tokens, out_t)
            e = [u for u in b if u["id"] in esc]
            if e and info is not None:
                ep = A.build_read_prompt(e, info[0], info[1], ctx, lic)
                usd += price(cur, rate * len(ep), out_per_unit * len(e))
        # re-quotes: recorded, scaled by lean / current prompt size, on the smaller model
        share = (sum(l for _c, l, *_ in lens) / max(1, sum(c for c, *_ in lens))) if lens else 0
        frac = len(r1 + later) / max(1, len(all_read))
        rq = [c for c in calls if "requote" in c["role"] and not c["role"].startswith("second")]
        usd += sum(price(small, c["input"] * share, c["output"]) for c in rq) * frac
        # rulings of findings: as recorded (current model), only for the sentences read
        usd += sum(price(cur, c["input"], c["output"]) for c in calls if c["role"] in ("rule",)) * frac
        # second reader: findings among the read sentences + the seeded 10%, lean documents, current model
        sr = [json.loads(l) for l in (run_dir / "second_reads.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()] \
            if (run_dir / "second_reads.jsonl").exists() else []
        by = {u["id"]: u for u in us}
        sec = [dict(by[s["unit"]], row=by[s["unit"]]["row"]) for s in sr if s["unit"] in by and s["unit"] in read_ids]
        if prev_dir is not None:
            keep = {s["unit"] for s in sr if s.get("why_read") == "had a finding"}
            sec = [u for u in sec if u["id"] in keep] + [u for u in sec if u["id"] not in keep][:max(1, round(0.1 * len(read_ids)))]
        if sec:
            sl = prompt_lengths(slug, sec, held, lic, ctx, body)
            sec_units_rec = max(1, len(sr))
            sout = (tout("second-read") + tout("second-read-summary")) / sec_units_rec
            usd += sum(price(cur, rate * l, sout * n) for _c, l, _p, n, _b, _i in sl)
            usd += sum(price(cur, c["input"], c["output"]) for c in calls if c["role"] == "rule-second") \
                * (len(sec) / sec_units_rec)
        res[scen + "_usd"] = round(usd, 4)
        res["lean_read_input_tokens"] = round(lean_in_total)
    res["recorded_read_input_tokens"] = sum(tin(r) for r in read_roles)
    return res


def ledger_lines(issue):
    out = []
    for line in (ROOT / "backend" / "data" / "spend" / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if e.get("issue") == issue:
                out.append(e)
    return out


def question(q):
    case = Path(glob.glob(str(ROOT / "issues" / ("WHU-Q1-%s-*" % q)))[0])
    slug = "whu-quarterly-r1-" + q
    rows = B.load(slug)["bindings"]
    held = A.held_for_audit(slug)
    lic = frozenset(A.licensed_ids(slug))
    held = {k: v for k, v in held.items() if k.split(":")[-1] not in lic}
    small, cur = lean.model_for("audit_first"), lean.model_for("audit_escalate")
    runs = sorted(p for p in (case / "audit").iterdir() if (p / "manifest.json").exists())
    audits, prev = [], None
    for r in runs:
        audits.append(audit_run(slug, r, prev, held, lic, rows, small, cur))
        prev = r
    led = ledger_lines(slug)
    audit_script = sum(float(e.get("usd") or 0) for e in led if e.get("script") == "audit_stage.py")
    manifests = sum(a["recorded_usd"] for a in audits)
    # ruling.py: relevance re-priced and escalated; everything else as recorded
    rul = [json.loads(l) for l in (case / "rulings" / "rulings.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rel = [r for r in rul if r.get("ruling_kind") == "relevance"]
    rel_rec = sum((r.get("usage") or {}).get("usd") or 0 for r in rel)
    jm = lean.model_for("judgements")
    jtop = lean.model_for("judgements_escalate")
    rel_lean = sum(price(jm, (r.get("usage") or {}).get("input", 0), (r.get("usage") or {}).get("output", 0))
                   for r in rel)
    rel_lean += sum(price(jtop, (r.get("usage") or {}).get("input", 0), (r.get("usage") or {}).get("output", 0))
                    for r in rel if r.get("ruling") == "not_relevant")
    ruling_other = audit_script - manifests - rel_rec
    # the gate: re-quotes and re-asks see retrieved passages
    gate, gate_lean, gate_pess = 0.0, 0.0, 0.0
    brief = {"calls": 0, "web_searches": 0, "recorded_usd": 0.0, "lean_usd": 0.0, "lean_pessimistic_usd": 0.0}
    srate = sum(a["tokens_per_char"] for a in audits) / len(audits)
    am = lean.model_for("advocate")
    gate_model = "claude-sonnet-4-6"           # factcheck_draft.SIGNAL_MODEL (signal_model.DEFAULT_MODEL)
    for e in led:
        if e.get("script") != "factcheck_draft.py":
            continue
        usd = float(e.get("usd") or 0)
        gate += usd
        role = e.get("role") or ""
        if not role.startswith("advocate"):
            gate_lean += usd; gate_pess += usd
            continue
        inp, out, ws = e.get("input", 0), e.get("output", 0), e.get("web_searches", 0) or 0
        if role.startswith(("advocate-requote:", "advocate-reask-omission:")):
            sid = role.split(":", 1)[1]
            text = held.get("%s:%s" % (slug, sid)) or held.get(sid) or ""
            trimmed = min(len(text), A.MAX_DOC_CHARS) * srate
            ps = PI.index_of(text).passages if text else []
            avg = (sum(p.end - p.start for p in ps) / len(ps)) if ps else 900
            inp = max(0.0, inp - trimmed + SA.LEAN_K * avg * srate)
        search = ws * 10.0 / 1000
        newer = am != gate_model
        base = lean.usd(am, inp, out) + search
        pess = lean.usd(am, inp * (TOKENIZER_PESS if newer else 1), out * (THINKING_PESS if newer else 1)) + search
        gate_lean += base; gate_pess += pess
        if role.startswith("advocate:"):
            brief["calls"] += 1; brief["web_searches"] += ws; brief["recorded_usd"] += usd
            brief["lean_usd"] += base; brief["lean_pessimistic_usd"] += pess
    actual = json.loads(PM.read_text(encoding="utf-8"))["M4"]["WHU"]["WHU-Q1-%s" % q]["usd"]
    out = {"actual_usd": actual, "ledger_usd": round(audit_script + gate, 2),
           "audit_runs": audits,
           "audit_runs_recorded_usd": round(manifests, 2),
           "audit_runs_lean_base_usd": round(sum(a["base_usd"] for a in audits), 2),
           "audit_runs_lean_pessimistic_usd": round(sum(a["pessimistic_usd"] for a in audits), 2),
           "ruling_py_recorded_usd": round(audit_script - manifests, 2),
           "ruling_py_lean_usd": round(ruling_other + rel_lean, 2),
           "relevance": {"rulings": len(rel), "not_relevant_escalated": sum(r.get("ruling") == "not_relevant" for r in rel),
                         "recorded_usd": round(rel_rec, 3), "lean_usd": round(rel_lean, 3)},
           "gate_recorded_usd": round(gate, 2), "gate_lean_usd": round(gate_lean, 2),
           "gate_lean_pessimistic_usd": round(gate_pess, 2),
           "advocate_brief": {"model_recorded": gate_model, "model_lean": am,
                              **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in brief.items()}}}
    out["lean_base_usd"] = round(out["audit_runs_lean_base_usd"] + out["ruling_py_lean_usd"] + gate_lean, 2)
    out["lean_pessimistic_usd"] = round(out["audit_runs_lean_pessimistic_usd"] + out["ruling_py_lean_usd"]
                                        + gate_pess, 2)
    # audit_stage.py spend in no run folder and no rulings record (carried as recorded, unchanged)
    attributed = sum(((json.loads(l).get("usage") or {}).get("usd") or 0)
                     for f in ("rulings.jsonl", "consistency.jsonl")
                     for l in ((case / "rulings" / f).read_text(encoding="utf-8").splitlines()
                               if (case / "rulings" / f).exists() else []) if l.strip())
    out["audit_stage_spend_in_no_record_usd"] = round(audit_script - manifests - attributed, 2)
    if q == "02":
        out["note"] = ("$2.21 of audit_stage.py spend is the drafter's dry-run audit (study_log.md step 7, "
                       "'DRAFTER ERROR', written to a scratchpad); carried unchanged in the lean figure")
    return out


def check_pilot_v4() -> dict:
    """v4 per answer from the ledger's whu-check-pilot-v3 lines (see the docstring)."""
    import pipeline_v4 as V4
    rows = [json.loads(l) for l in (ROOT / "backend" / "data" / "spend" / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip() and '"whu-check-pilot-v3"' in l]
    rows = [r for r in rows if r.get("role") == "check-pilot-v3-primary"]
    p = S_LEDGER.PRICES["claude-opus-5-5"]
    out = {"answers": 8, "calls": len(rows), "v3_recorded_usd": round(sum(r["usd"] for r in rows), 2),
           "v3_per_answer_usd": round(sum(r["usd"] for r in rows) / 8, 2), "bar_per_answer_usd": 2.0}
    for scen, docs, k, rate in (("base", 1, V4.TOP_K, 0.30), ("pessimistic", 2, V4.TOP_K + 4, 0.42)):
        passage_tokens = docs * k * PI.PASSAGE_CHARS * rate
        for model in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"):
            usd = 0.0
            for r in rows:
                cw = max(0.0, (r["usd"] - (r["input"] * p["input"] + r["output"] * p["output"]) / 1e6)
                         / p["cache_write"] * 1e6)
                cw4 = min(cw, passage_tokens)
                usd += lean.usd(model, r["input"], r["output"], cw4, 0)
            out["v4_%s_%s_per_answer_usd" % (model, scen)] = round(usd / 8, 2)
    return out


def main() -> int:
    lean.enable(True)
    res = {"label": "Lean WHU on quarterly round 1: a $0 replay of recorded token counts (no model call)",
           "method": "study/whu-reliability/quarterly/lean_replay_round1.py docstring",
           "prices": "backend/scripts/spend_ledger.py PRICES (rates() step)",
           "pessimistic_extra_escalation": PESSIMISTIC_EXTRA, "tokenizer_pessimistic": TOKENIZER_PESS,
           "thinking_pessimistic": THINKING_PESS, "bars": {"median_usd": 5.0, "max_usd": 10.0}, "tiers": {}}
    import os
    import statistics
    for t in TIERS:
        os.environ[lean.ENV_MODELS] = json.dumps(lean.variant_models(t))
        tier = {"models": lean.stage_models(), "questions": {}}
        for q in QUESTIONS:
            tier["questions"]["WHU-Q1-%s" % q] = r = question(q)
            print("[%s] WHU-Q1-%s actual $%.2f -> lean $%.2f (pessimistic $%.2f): audit %.2f->%.2f, ruling.py "
                  "%.2f->%.2f, gate %.2f->%.2f/%.2f; advocate brief %.2f->%.2f" % (
                      t, q, r["actual_usd"], r["lean_base_usd"], r["lean_pessimistic_usd"],
                      r["audit_runs_recorded_usd"], r["audit_runs_lean_base_usd"], r["ruling_py_recorded_usd"],
                      r["ruling_py_lean_usd"], r["gate_recorded_usd"], r["gate_lean_usd"],
                      r["gate_lean_pessimistic_usd"], r["advocate_brief"]["recorded_usd"],
                      r["advocate_brief"]["lean_usd"]))
        for sc in ("base", "pessimistic"):
            v = [r["lean_%s_usd" % sc] for r in tier["questions"].values()]
            tier[sc] = {"median_usd": round(statistics.median(v), 2), "max_usd": max(v),
                        "median_under_5": statistics.median(v) < 5.0, "none_over_10": max(v) <= 10.0}
        print("[%s] median base $%.2f max $%.2f | pessimistic median $%.2f max $%.2f" % (
            t, tier["base"]["median_usd"], tier["base"]["max_usd"], tier["pessimistic"]["median_usd"],
            tier["pessimistic"]["max_usd"]))
        res["tiers"][t] = tier
    os.environ.pop(lean.ENV_MODELS, None)
    res["check_pilot_v4"] = check_pilot_v4()
    print("check pilot v4:", json.dumps(res["check_pilot_v4"]))
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
