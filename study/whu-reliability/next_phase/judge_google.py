#!/usr/bin/env python3
"""The third judge (validity plan §1, check 1; also check 4's rescoring): gemini-4-argon, first reads only.

    judge_google.py m1 RUN_DIR --cap 55 [--estimate] [--ledger-issue whu-reliability-judging-validity-c1]
    judge_google.py m2 RUN_DIR --cap 55 [--estimate] [--tag ...]

Everything but the call is the study's: judge_m1's documents (the same snapshots, the same chunking with Claude's
token counts, the same delivery check), judge_m1.build / judge_m2.build, their parsers, judge_m1.final_label and
the refusal rule (a second attempt only after a refusal). The frozen prompts are verified by sha256 before any key
is read. An item judge_m1 would not judge (no reachable source; unreachable or undelivered source) gets the same
INCOMPLETE_SOURCES record and no call. Replies go to RUN_DIR/replies<tag>/google/, beside the other judges';
analyse.py's JUDGES ("claude", "openai") do not read them.

SPEND. Before every call: caps.json's all-spend day cap (spend_ledger.check_day_cap), the judging day cap
(judge_m1.day_cap_stop, for whu-reliability-judging* issues) and --cap on the ledger issue, each against the call's
worst case: counted input at the input rate + MAX_OUT at the output rate (spend_ledger.rates on the call's date).
Cost recorded from the reply's usage: uncached prompt at the input rate, cached at the cache-read rate, candidates
plus thinking at the output rate. A reply from any model other than MODEL stops the run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import judge_m1 as J1  # noqa: E402
import judge_m2 as J2  # noqa: E402

S = J1.S
MODEL = "gemini-4-argon"
MAX_OUT = 8192                       # a runner setting (thinking counts toward it); a cut-off reply is recorded
SCRIPT = "study/whu-reliability/next_phase/judge_google.py"
PLAN_FREEZE = "b4cf31ad19046a63073461fc5195415bc496594b"
SEED = int(PLAN_FREEZE, 16)
WORKERS = 6


class Stop(RuntimeError):
    pass


def client():
    from google import genai
    return genai.Client(api_key=J1.env_keys()["GEMINI_API_KEY"])


def worst_usd(n_in: int) -> float:
    p = S.rates(MODEL, n_in)
    return (n_in * p["input"] + MAX_OUT * p["output"]) / 1e6


def call(gc, text: str, issue: str, role: str) -> tuple[str, dict, float, bool]:
    from google.genai import types
    r = gc.models.generate_content(model=MODEL, contents=text,
                                   config=types.GenerateContentConfig(max_output_tokens=MAX_OUT))
    mv = getattr(r, "model_version", None) or ""
    if mv and not mv.startswith(MODEL):
        raise Stop("the reply came from model %r, not %s" % (mv, MODEL))
    u = r.usage_metadata
    prompt = int(getattr(u, "prompt_token_count", 0) or 0)
    cached = int(getattr(u, "cached_content_token_count", 0) or 0)
    cand = int(getattr(u, "candidates_token_count", 0) or 0)
    think = int(getattr(u, "thoughts_token_count", 0) or 0)
    p = S.rates(MODEL, prompt)
    usd = ((prompt - cached) * p["input"] + cached * p["cache_read"] + (cand + think) * p["output"]) / 1e6
    fb = getattr(r, "prompt_feedback", None)
    cands = getattr(r, "candidates", None) or []
    finish = str(getattr(cands[0], "finish_reason", "")) if cands else ""
    refused = bool(fb and getattr(fb, "block_reason", None)) or "SAFETY" in finish or "PROHIBITED" in finish \
        or "BLOCKLIST" in finish
    try:
        text_out = r.text or ""
    except Exception:
        text_out = ""
    S.record(script=SCRIPT, role=role, issue=issue, usd=usd, input_tokens=prompt, output_tokens=cand + think,
             note="%s; cached=%d; thinking=%d; finish=%s" % (mv or MODEL, cached, think, finish))
    return text_out, {"input": prompt, "cache_read": cached, "output": cand, "thinking": think, "model": mv,
                      "stop": finish}, usd, refused


class Guard:
    """The three caps, checked under a lock before every call, with in-flight worst cases reserved."""

    def __init__(self, issue: str, cap: float):
        self.issue, self.cap, self.lock, self.reserved = issue, cap, threading.Lock(), 0.0

    def take(self, worst: float) -> None:
        with self.lock:
            S.check_day_cap(self.reserved + worst)
            why = J1.day_cap_stop(self.reserved + worst)
            if why:
                raise Stop(why)
            so_far = J1.spent(self.issue)
            if so_far + self.reserved + worst > self.cap:
                raise Stop("%s has spent $%.3f, $%.3f in flight; the next call could cost up to $%.3f (cap $%.2f)"
                           % (self.issue, so_far, self.reserved, worst, self.cap))
            self.reserved += worst

    def done(self, worst: float) -> None:
        with self.lock:
            self.reserved -= worst


def attempts_for(gc, text: str, n_in: int, guard: Guard, role: str) -> list[dict]:
    out = []
    for attempt in (1, 2):                    # the second only after a refusal
        w = worst_usd(n_in)
        guard.take(w)
        try:
            t0 = time.time()
            for net in range(4):
                try:
                    reply, usage, usd, refused = call(gc, text, guard.issue, role)
                    break
                except Stop:
                    raise
                except Exception as e:
                    if net == 3:
                        raise
                    print("  network/API retry: %s" % str(e)[:160], flush=True)
                    time.sleep(15 * (net + 1))
        finally:
            guard.done(w)
        out.append({"attempt": attempt, "seconds": round(time.time() - t0, 1), "usage": usage,
                    "usd": round(usd, 6), "refused": refused, "raw": reply})
        if not refused:
            break
    return out


# ---------------------------------------------------------------------------------------------------------------
# M1
# ---------------------------------------------------------------------------------------------------------------

def m1_docs(it: dict, run: Path, manifest: dict, tokens: dict, count) -> tuple[list, list, list]:
    """judge_m1.main's document step, unchanged in substance: (docs, unreachable, undelivered)."""
    docs, unreachable, undelivered = [], [], []
    cites = it.get("citations") or [{"label": "", "url": u} for u in it["urls"]]
    for c in cites:
        if not c.get("url"):
            unreachable.append({"label": c.get("label"), "url": None, "why": c.get("note") or "no URL in the answer"})
    for u in [c["url"] for c in cites if c.get("url")]:
        m = manifest[u]
        if m["extent"] == "unreachable":
            unreachable.append({"url": u, "why": m["extent_why"]})
            continue
        text = (run / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")
        if m["source_id"] not in tokens:
            tokens[m["source_id"]] = count(text)
        d = {"source_id": m["source_id"], "url": u, "extent": m["extent"], "abstract_only": bool(m.get("abstract_only")),
             "tokens": tokens[m["source_id"]], "text_sha256": m["text_sha256"], "chunked": False, "text": text}
        spans = [s for s in [it.get("span")] + list(it.get("spans") or []) if s]
        if d["tokens"] > J1.MAX_SOURCE_TOKENS:
            d["text"], d["chunk"] = J1.chunk(text, it["claim"], J1.MAX_SOURCE_TOKENS, count, spans)
            d["chunked"] = True
        bad = J1.delivery_problems(text, d["text"], it["claim"], spans)
        if bad:
            undelivered.append({"url": u, "source_id": m["source_id"], "why": "; ".join(bad)})
        docs.append(d)
    return docs, unreachable, undelivered


def m1(a) -> int:
    if hashlib.sha256(J1.PROMPT.read_bytes()).hexdigest() != J1.PROMPT_SHA256:
        print("STOP: the M1 prompt is not the frozen v3")
        return 6
    run = Path(a.run_dir)
    items = json.loads((run / "items.json").read_text())
    manifest = {r["url"]: r for r in json.loads((run / "sources" / "manifest.json").read_text())}
    import anthropic
    raw = anthropic.Anthropic(api_key=J1.env_keys()["ANTHROPIC_API_KEY"])

    def count(text: str) -> int:      # Claude's count, as judge_m1 chunks with it (free)
        return raw.messages.count_tokens(model=J1.CLAUDE_MODEL, messages=[{"role": "user", "content": text}]).input_tokens

    tok_file = run / "sources" / "tokens.json"
    tokens = json.loads(tok_file.read_text()) if tok_file.exists() else {}
    gc = client()
    plan = []
    for it in items:
        docs, unreachable, undelivered = m1_docs(it, run, manifest, tokens, count)
        if not docs:
            continue
        plan.append((it, docs, unreachable, undelivered))
    random.Random("%d/check1" % SEED).shuffle(plan)
    calls = [p for p in plan if not (p[2] or p[3])]
    est_in = {}
    for it, docs, _, _ in calls:
        prefix, rest = J1.build(it, docs)
        est_in[it["item"]] = gc.models.count_tokens(model=MODEL, contents=prefix + rest).total_tokens
    worst = sum(worst_usd(n) for n in est_in.values())
    likely = sum((n * S.rates(MODEL, n)["input"] + 2000 * S.rates(MODEL, n)["output"]) / 1e6 for n in est_in.values())
    print("M1: %d items, %d to judge, %d not judged (INCOMPLETE_SOURCES); %d input tokens (Gemini count)" % (
        len(plan), len(calls), len(plan) - len(calls), sum(est_in.values())))
    print("ESTIMATE M1: likely $%.2f (2,000 output tokens a call), worst $%.2f (%d output tokens a call); cap $%.2f"
          % (likely, worst, MAX_OUT, a.cap))
    if a.estimate:
        return 0
    if likely > a.cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    guard = Guard(a.ledger_issue, a.cap)
    outdir = run / ("replies" + a.tag) / "google"
    outdir.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()

    def one(p):
        it, docs, unreachable, undelivered = p
        out = outdir / (it["item"] + ".json")
        if out.exists() or stop.is_set():
            return
        base = {"item": it["item"], "judge": "google", "prompt_version": J1.PROMPT_VERSION,
                "prompt_sha256": J1.PROMPT_SHA256, "reference": it["reference"],
                "sources": [{k: v for k, v in d.items() if k != "text"} for d in docs],
                "unreachable_sources": unreachable}
        if unreachable or undelivered:
            out.write_text(json.dumps({**base, "at": J1_now(), "label": J1.INCOMPLETE_SOURCES, "judge_label": None,
                                       "attempts": [], "usd": 0.0, "undelivered_sources": undelivered,
                                       "human_review": True, "form_problems": [], "parsed": None},
                                      indent=1, ensure_ascii=False), encoding="utf-8")
            return
        prefix, rest = J1.build(it, docs)
        try:
            att = attempts_for(gc, prefix + rest, est_in[it["item"]], guard, "m1-judge-google")
        except (Stop, S.OverCap) as e:
            stop.set()
            print("STOP before a call on %s: %s" % (it["item"], e), flush=True)
            return
        last = att[-1]
        obj, problems = (None, []) if last["refused"] else J1.parse(last["raw"])
        span = (obj or {}).get("span") or ""
        label = J1.final_label((obj or {}).get("label"), last["refused"], docs)
        rec = {**base, "model": last["usage"].get("model"), "at": J1_now(), "chunked": any(d["chunked"] for d in docs),
               "input_tokens_counted": est_in[it["item"]], "attempts": att,
               "usd": round(sum(x["usd"] for x in att), 6), "judge_label": (obj or {}).get("label"), "label": label,
               "parsed": obj, "form_problems": problems,
               "span_verbatim_in_documents": bool(span) and any(J1.norm(span) in J1.norm(d["text"]) for d in docs),
               "human_review": label == J1.REFUSED}
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        print("%-15s %-14s $%.4f in %6d think %5d out %4d %s%s" % (
            it["item"], label, rec["usd"], last["usage"]["input"], last["usage"]["thinking"], last["usage"]["output"],
            last["usage"]["stop"], ("  FORM: " + "; ".join(problems)) if problems else ""), flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(one, plan))
    print("%s spent: $%.4f" % (a.ledger_issue, J1.spent(a.ledger_issue)))
    return 3 if stop.is_set() else 0


# ---------------------------------------------------------------------------------------------------------------
# M2
# ---------------------------------------------------------------------------------------------------------------

def m2(a) -> int:
    prompt = Path(a.prompt) if a.prompt else J2.PROMPT
    want = a.prompt_sha256 or J2.PROMPT_SHA256
    got = hashlib.sha256(prompt.read_bytes()).hexdigest()
    if got != want:
        print("STOP: %s has sha256 %s, not %s" % (prompt, got, want))
        return 6
    J2.PROMPT = prompt                   # J2.build reads J2.PROMPT; the file itself is never written
    run = Path(a.run_dir)
    answers, concl, items = J2.load_run(run)
    gc = client()
    plan = []
    for it in sorted(items, key=lambda i: (i["answer"], i["item"])):
        prefix, rest = J2.build(answers[it["answer"]], concl[it["conclusion"]])
        plan.append((it, prefix + rest))
    random.Random("%d/check1/m2" % SEED).shuffle(plan)
    est_in = {it["item"]: gc.models.count_tokens(model=MODEL, contents=t).total_tokens for it, t in plan}
    worst = sum(worst_usd(n) for n in est_in.values())
    likely = sum((n * S.rates(MODEL, n)["input"] + 2000 * S.rates(MODEL, n)["output"]) / 1e6 for n in est_in.values())
    print("M2: %d items; %d input tokens. ESTIMATE likely $%.2f, worst $%.2f; cap $%.2f"
          % (len(plan), sum(est_in.values()), likely, worst, a.cap))
    if a.estimate:
        return 0
    if likely > a.cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    guard = Guard(a.ledger_issue, a.cap)
    outdir = run / ("replies" + a.tag) / "google"
    outdir.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()

    def one(p):
        it, text = p
        out = outdir / (it["item"] + ".json")
        if out.exists() or stop.is_set():
            return
        try:
            att = attempts_for(gc, text, est_in[it["item"]], guard, "m2-judge-google")
        except (Stop, S.OverCap) as e:
            stop.set()
            print("STOP before a call on %s: %s" % (it["item"], e), flush=True)
            return
        last = att[-1]
        obj, problems = (None, []) if last["refused"] else J2.parse(last["raw"])
        label = J2.REFUSED if last["refused"] else (obj or {}).get("label")
        span = (obj or {}).get("span") or ""
        rec = {"item": it["item"], "judge": "google", "model": last["usage"].get("model"), "at": J1_now(),
               "prompt_sha256": got, "prompt_path": str(prompt.relative_to(J1.STUDY.parent.parent))
               if prompt.is_relative_to(J1.STUDY.parent.parent) else str(prompt),
               "answer": it["answer"], "conclusion": it["conclusion"], "input_tokens_counted": est_in[it["item"]],
               "attempts": att, "usd": round(sum(x["usd"] for x in att), 6), "judge_label": (obj or {}).get("label"),
               "label": label, "parsed": obj, "form_problems": problems,
               "span_verbatim_in_answer": J2.span_verbatim(span, answers[it["answer"]]),
               "human_review": label == J2.REFUSED}
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        print("%-15s %-12s $%.4f in %6d think %5d %s%s" % (
            it["item"], label, rec["usd"], last["usage"]["input"], last["usage"]["thinking"], last["usage"]["stop"],
            ("  FORM: " + "; ".join(problems)) if problems else ""), flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(one, plan))
    print("%s spent: $%.4f" % (a.ledger_issue, J1.spent(a.ledger_issue)))
    return 3 if stop.is_set() else 0


def J1_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("measure", choices=["m1", "m2"])
    ap.add_argument("run_dir")
    ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--ledger-issue", default="whu-reliability-judging-validity-c1")
    ap.add_argument("--tag", default="")
    ap.add_argument("--estimate", action="store_true", help="count tokens (free), print the estimate, call nothing")
    ap.add_argument("--prompt", help="M2 only: another prompt file (its sha256 must be given)")
    ap.add_argument("--prompt-sha256")
    a = ap.parse_args()
    return m1(a) if a.measure == "m1" else m2(a)


if __name__ == "__main__":
    raise SystemExit(main())
