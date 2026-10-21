#!/usr/bin/env python3
"""Run the M2 (conclusion calibration) judge prompt with a Claude and a ChatGPT judge.

Usage:
    judge_m2.py RUN_DIR [--cap USD] [--only ID,ID] [--judges claude,openai]
                [--tag SUFFIX] [--ledger-issue NAME]
    judge_m2.py RUN_DIR --score [--tag SUFFIX]

RUN_DIR holds items.json:
    {"answers": {"<answer id>": {"file": "<blinded answer, relative to RUN_DIR>"}},
     "conclusions": [{"id", "statement", "direction", "size", "certainty",
                      "scope", "quote", "from_answer"?}],
     "items": [{"item", "answer", "conclusion"}]}
Each item is one blinded answer and one conclusion, as the protocol's M2
prescribes: the judge reads the whole answer and labels what it says about
that conclusion. Replies go to RUN_DIR/replies<tag>/<judge>/<item>.json.

THE RUNNER, as judge_m1.py (protocol, "Rulings from prep round 1"):
  Refusal. Retried once, unchanged. Refused again, the label is REFUSED and
  the item goes to a person. The input is never reworded.
  One read per judge (budget ruling, rev 26); this runner draws no repeat
  sample, because the M2 behaviour check asks for one read each.
  Caching. The answer comes first in the prompt, so the ten conclusions of
  one answer share a cached block: on Claude with an explicit cache_control
  breakpoint after the answer, on OpenAI by prefix caching with a
  prompt_cache_key naming the answer.
  Spend. Every call lands in backend/data/spend/ledger.jsonl under
  --ledger-issue; before each call the worst case is added to what that issue
  has spent, and the runner stops if it would pass --cap.

--score prints the behaviour check (protocol rev 33, "Pre-freeze rulings"):
valid JSON, quotations verbatim in the answer, refusals, agreement between
the judges, and cost per call. Free.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import statistics as st
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
_spec = importlib.util.spec_from_file_location("judge_m1", HERE / "judge_m1.py")
J1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J1)
S = J1.S

PROMPT = STUDY / "prompts" / "m2_conclusion_calibration.md"
# M2 v2, frozen 2026-10-21 (advisor ruling on the framing paragraph; behaviour
# check: judges agree 45 of 48). A changed prompt is refused. v1 is kept as
# prompts/m2_conclusion_calibration_v1.md (sha256 aebfffc1...), with its replies.
PROMPT_SHA256 = "64a5a5b667e697b55e4f42f2473b3b5516c5e9ceec0f0d88a878cdc9eb38bb33"
PROMPT_VERSION = "v2"
LABELS = ["Matches", "Overstates", "Understates", "Contradicts", "Omits"]
REFUSED = "REFUSED"
SCRIPT = "study/whu-reliability/judge_m2.py"
CLAUDE_MODEL = J1.CLAUDE_MODEL
CLAUDE_MAX_OUT = 1024
OPENAI_MODEL = J1.OPENAI_MODEL
OPENAI_MAX_OUT = J1.OPENAI_MAX_OUT
OPENAI_PRICE = J1.OPENAI_PRICE
FIELDS = ("statement", "direction", "size", "certainty", "scope", "quote")


def build(answer: str, c: dict) -> tuple[str, str]:
    """(cacheable prefix, rest): the prefix is everything up to the end of the
    answer, so it is identical for every conclusion judged against it."""
    t = PROMPT.read_text(encoding="utf-8")
    head, tail = t.split("{answer}", 1)
    rest = tail
    for k in FIELDS:
        rest = rest.replace("{%s}" % k, str(c.get(k) or "not stated"))
    return head + answer, rest


def parse(text: str) -> tuple[dict | None, list[str]]:
    """The reply as JSON, and every way it departs from the required form."""
    obj, problems = J1.parse(text)
    problems = [p for p in problems if not p.startswith("label ")]
    if obj is not None and obj.get("label") not in LABELS:
        problems.append("label %r not in the label set" % obj.get("label"))
    if obj is not None and obj.get("label") == "Omits" and obj.get("span"):
        problems.append("a span with Omits")
    if obj is not None and obj.get("label") in LABELS and obj.get("label") != "Omits" and not obj.get("span"):
        problems.append("no span")
    if obj is not None and len(obj.get("span") or "") > 300:
        problems.append("span over 300 characters")
    return obj, problems


def span_verbatim(span: str, answer: str) -> bool:
    """The span is in the answer, after judge_m1's normalisation (quotes,
    dashes, ligatures, whitespace, case); an ellipsis joins parts that must
    each be in the answer, in order."""
    if not span:
        return False
    a = J1.norm(answer)
    pos = 0
    for part in [p for p in J1.norm(span).replace("...", "…").split("…") if p.strip()]:
        i = a.find(part.strip(), pos)
        if i < 0:
            return False
        pos = i + len(part.strip())
    return True


def call_claude(client, prefix: str, rest: str) -> tuple[str, dict, float, bool]:
    r = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=CLAUDE_MAX_OUT,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": rest}]}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    usd, counts = S.price(getattr(r, "model", CLAUDE_MODEL), r.usage)
    return text, {**counts, "model": r.model, "stop": r.stop_reason}, usd or 0.0, r.stop_reason == "refusal"


def call_openai(key: str, prefix: str, rest: str, issue: str) -> tuple[str, dict, float, bool]:
    resp = httpx.post("https://api.openai.com/v1/responses", timeout=600,
                      headers={"Authorization": "Bearer " + key},
                      json={"model": OPENAI_MODEL, "input": prefix + rest,
                            "max_output_tokens": OPENAI_MAX_OUT,
                            "prompt_cache_key": "m2-" + hashlib.sha256(prefix.encode()).hexdigest()[:40]})
    resp.raise_for_status()
    d = resp.json()
    refused, texts = False, []
    for o in d.get("output", []):
        if o.get("type") != "message":
            continue
        for c in o.get("content", []):
            if c.get("type") == "refusal":
                refused = True
            elif c.get("type") in ("output_text", "text"):
                texts.append(c.get("text", ""))
    text = d.get("output_text") or "".join(texts)
    u = d.get("usage") or {}
    cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
    inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
    usd = ((inp - cached) * OPENAI_PRICE["input"] + cached * OPENAI_PRICE["cached_input"]
           + out * OPENAI_PRICE["output"]) / 1e6
    counts = {"input": inp, "cache_read": cached, "output": out,
              "reasoning": int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0),
              "model": d.get("model"), "stop": d.get("status"), "incomplete": d.get("incomplete_details")}
    S.record(script=SCRIPT, role="m2-judge-openai", issue=issue, usd=usd,
             input_tokens=inp, output_tokens=out,
             note="%s; cached_input=%d" % (d.get("model") or OPENAI_MODEL, cached))
    return text, counts, usd, refused


def load_run(run: Path) -> tuple[dict, dict, list[dict]]:
    spec = json.loads((run / "items.json").read_text(encoding="utf-8"))
    answers = {k: (run / v["file"]).read_text(encoding="utf-8") for k, v in spec["answers"].items()}
    concl = {c["id"]: c for c in spec["conclusions"]}
    return answers, concl, spec["items"]


def judge(a) -> int:
    run = Path(a.run_dir)
    answers, concl, items = load_run(run)
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["item"] in keep]
    keys = J1.env_keys()
    import anthropic
    raw = anthropic.Anthropic(api_key=keys["ANTHROPIC_API_KEY"])
    client = S.metered(raw, script=SCRIPT, issue=a.ledger_issue, role="m2-judge-claude")
    prompt_sha = hashlib.sha256(PROMPT.read_bytes()).hexdigest()
    if prompt_sha != PROMPT_SHA256:
        print("STOP: %s has sha256 %s, not the frozen M2 %s %s" % (PROMPT, prompt_sha, PROMPT_VERSION, PROMPT_SHA256))
        return 6
    # One answer's conclusions in a row, so the cached answer block is reused.
    items = sorted(items, key=lambda i: (i["answer"], i["item"]))
    for it in items:
        answer, c = answers[it["answer"]], concl[it["conclusion"]]
        prefix, rest = build(answer, c)
        n_in = raw.messages.count_tokens(model=CLAUDE_MODEL,
                                         messages=[{"role": "user", "content": prefix + rest}]).input_tokens
        for jd in a.judges.split(","):
            out = run / ("replies" + a.tag) / jd / (it["item"] + ".json")
            if out.exists():
                continue
            attempts = []
            for attempt in (1, 2):                    # the second only after a refusal
                if jd == "claude":
                    p = S.PRICES[CLAUDE_MODEL]
                    worst = (n_in * p["cache_write"] + CLAUDE_MAX_OUT * p["output"]) / 1e6
                else:
                    worst = (n_in * OPENAI_PRICE["input"] + OPENAI_MAX_OUT * OPENAI_PRICE["output"]) / 1e6
                so_far = J1.spent(a.ledger_issue)
                if so_far + worst > a.cap:
                    print("STOP: %s on %s could cost up to $%.3f; %s has spent $%.3f of $%.2f"
                          % (jd, it["item"], worst, a.ledger_issue, so_far, a.cap))
                    return 3
                t0 = time.time()
                for net in range(3):
                    try:
                        if jd == "claude":
                            text, usage, usd, refused = call_claude(client, prefix, rest)
                        else:
                            text, usage, usd, refused = call_openai(keys["OPENAI_API_KEY"], prefix, rest,
                                                                    a.ledger_issue)
                        break
                    except Exception as e:
                        if net == 2:
                            raise
                        print("  network retry %s %s: %s" % (jd, it["item"], str(e)[:160]))
                        time.sleep(10)
                attempts.append({"attempt": attempt, "seconds": round(time.time() - t0, 1),
                                 "usage": usage, "usd": round(usd, 6), "refused": refused, "raw": text})
                if not refused:
                    break
            last = attempts[-1]
            refused = last["refused"]
            obj, problems = (None, []) if refused else parse(last["raw"])
            span = (obj or {}).get("span") or ""
            label = REFUSED if refused else (obj or {}).get("label")
            rec = {"item": it["item"], "judge": jd, "model": last["usage"].get("model"),
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "prompt_sha256": prompt_sha, "prompt_version": PROMPT_VERSION, "answer": it["answer"], "conclusion": it["conclusion"],
                   "from_answer": c.get("from_answer"), "input_tokens_counted": n_in,
                   "attempts": attempts, "usd": round(sum(x["usd"] for x in attempts), 6),
                   "judge_label": (obj or {}).get("label"), "label": label, "parsed": obj,
                   "form_problems": problems, "span_verbatim_in_answer": span_verbatim(span, answer),
                   "human_review": label == REFUSED}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
            u = last["usage"]
            print("%-12s %-7s %-12s $%.4f  in %6d cached %6d write %6d out %5d  %s%s" % (
                it["item"], jd, label, rec["usd"], u.get("input", 0), u.get("cache_read", 0),
                u.get("cache_write", 0), u.get("output", 0),
                "span ok" if rec["span_verbatim_in_answer"] else ("-" if refused or label == "Omits" else "SPAN NOT VERBATIM"),
                ("  FORM: " + "; ".join(problems)) if problems else ""))
    print("%s spent: $%.4f" % (a.ledger_issue, J1.spent(a.ledger_issue)))
    return 0


def score(run: Path, tag: str = "") -> dict:
    out: dict = {}
    recs = {}
    for jd in ("claude", "openai"):
        rows = [json.load(open(f)) for f in sorted(glob.glob(str(run / ("replies" + tag) / jd / "*.json")))]
        recs[jd] = {r["item"]: r for r in rows}
        calls = [x for r in rows for x in r["attempts"]]
        labelled = [r for r in rows if r["label"] != REFUSED]
        spanned = [r for r in labelled if r["label"] != "Omits"]
        own = [r for r in labelled if r.get("from_answer") == r["answer"]]
        usd = [x["usd"] for x in calls] or [0.0]
        out[jd] = {
            "items": len(rows), "calls": len(calls),
            "valid_json": "%d/%d" % (sum(not r["form_problems"] for r in labelled), len(labelled)),
            "form_problems": sorted({p for r in labelled for p in r["form_problems"]}),
            "spans_verbatim": "%d/%d" % (sum(r["span_verbatim_in_answer"] for r in spanned), len(spanned)),
            "refused_items": sum(r["label"] == REFUSED for r in rows),
            "refused_calls": sum(x["refused"] for x in calls),
            "labels": {l: sum(r["label"] == l for r in rows) for l in LABELS + [REFUSED]},
            "own_answer_matches": "%d/%d" % (sum(r["label"] == "Matches" for r in own), len(own)),
            "calls_with_cache_hit": "%d/%d" % (sum((x["usage"].get("cache_read") or 0) > 0 for x in calls), len(calls)),
            "usd_total": round(sum(usd), 4), "usd_mean_per_call": round(st.mean(usd), 4),
            "usd_median_per_call": round(st.median(usd), 4), "usd_max_per_call": round(max(usd), 4)}
    both = sorted(set(recs["claude"]) & set(recs["openai"]))
    agree = [i for i in both if recs["claude"][i]["label"] == recs["openai"][i]["label"]]
    out["judge_vs_judge"] = "%d/%d" % (len(agree), len(both))
    out["disagreements"] = [{"item": i, "claude": recs["claude"][i]["label"], "openai": recs["openai"][i]["label"]}
                            for i in both if i not in agree]
    pairs: dict = {}
    for i in both:
        k = (recs["claude"][i]["label"], recs["openai"][i]["label"])
        pairs["%s / %s" % k] = pairs.get("%s / %s" % k, 0) + 1
    out["claude_by_openai"] = dict(sorted(pairs.items(), key=lambda x: -x[1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cap", type=float, default=8.0)
    ap.add_argument("--only")
    ap.add_argument("--judges", default="claude,openai")
    ap.add_argument("--tag", default="")
    ap.add_argument("--ledger-issue", default="whu-reliability-prefreeze2")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.score:
        print(json.dumps(score(Path(a.run_dir), a.tag), indent=1))
        return 0
    return judge(a)


if __name__ == "__main__":
    raise SystemExit(main())
