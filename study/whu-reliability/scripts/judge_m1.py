#!/usr/bin/env python3
"""Run the M1 (citation support) judge prompt with a Claude and a ChatGPT judge.

Usage:
    judge_m1.py RUN_DIR [--cap USD] [--only P01,P03]

RUN_DIR holds items.json (claim, context, reference label) and snapshots/
(from snapshot.py). Each judge reads the SAME snapshot text. Replies go to
RUN_DIR/replies/<judge>/<item>.json, each with the prompt's sha256, the
snapshot's sha256, the raw reply, the parsed label, token usage and cost.

SPEND. Every call is written to backend/data/spend/ledger.jsonl under issue
LEDGER_ISSUE. Before each call the script adds the call's worst case (its
input tokens, counted free by Anthropic's count_tokens and padded for the
other tokenizer, plus the output ceiling) to what this round has already
spent, and stops if that would pass --cap. A call is never made on the hope
that it will come in cheap.

Items whose snapshot is unreachable are skipped and counted, never judged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
# By file path: putting backend/scripts on sys.path would shadow the standard
# library's `signal` with backend/scripts/signal/, which breaks httpx's imports.
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

PROMPT = STUDY / "prompts" / "m1_citation_support.md"
LABELS = ["Supported", "Overstates", "Understates", "Absent", "Wrong source",
          "Contradicted", "Unreachable"]
LEDGER_ISSUE = "whu-reliability-prep1"
SCRIPT = "study/whu-reliability/judge_m1.py"
CONTEXT_CHARS = 400

CLAUDE_MODEL = "claude-fable-5-1"
CLAUDE_MAX_OUT = 1024
OPENAI_MODEL = "gpt-6-astra"
OPENAI_MAX_OUT = 6000           # reasoning tokens count as output
# Standard tier, checked 2026-10-19 at developers.openai.com/api/docs/pricing.
OPENAI_PRICE = {"input": 10.00, "cached_input": 1.00, "output": 50.00}
TOKEN_PAD = 1.15                # count_tokens is Claude's tokenizer; pad for OpenAI's


def env_keys() -> dict:
    out = {}
    for line in (ROOT / "backend" / ".env").read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def round_spent() -> float:
    return sum(float(e.get("usd") or 0) for e in S.entries() if e.get("issue") == LEDGER_ISSUE)


def build(item: dict, document: str, extent: str) -> str:
    ctx = item.get("context") or ""
    if len(ctx) > CONTEXT_CHARS:
        ctx = "…" + ctx[-CONTEXT_CHARS:].lstrip()
    t = PROMPT.read_text(encoding="utf-8")
    for k, v in (("{claim}", item["claim"]), ("{context}", ctx),
                 ("{extent}", extent), ("{document}", document)):
        t = t.replace(k, v)
    return t


def parse(text: str) -> tuple[dict | None, list[str]]:
    """The reply as JSON, and every way it departs from the required form."""
    problems = []
    s = text.strip()
    if s.startswith("```"):
        problems.append("code fence")
        s = re.sub(r"^```(json)?\s*|\s*```$", "", s)
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None, problems + ["not JSON"]
        problems.append("text around the JSON")
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return None, problems + ["not JSON"]
    if set(obj) != {"label", "span", "reason"}:
        problems.append("keys %s" % sorted(obj))
    if obj.get("label") not in LABELS:
        problems.append("label %r not in the label set" % obj.get("label"))
    return obj, problems


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("−", "-").replace("·", ".")
    return " ".join(s.split()).lower()


def call_claude(client, prompt: str, model: str = CLAUDE_MODEL) -> tuple[str, dict, float]:
    r = client.messages.create(model=model, max_tokens=CLAUDE_MAX_OUT,
                               messages=[{"role": "user", "content": prompt}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    usd, counts = S.price(getattr(r, "model", model), r.usage)
    return text, {**counts, "model": r.model, "stop": r.stop_reason}, usd or 0.0


def call_openai(key: str, prompt: str) -> tuple[str, dict, float]:
    resp = httpx.post("https://api.openai.com/v1/responses", timeout=600,
                      headers={"Authorization": "Bearer " + key},
                      json={"model": OPENAI_MODEL, "input": prompt,
                            "max_output_tokens": OPENAI_MAX_OUT})
    resp.raise_for_status()
    d = resp.json()
    text = d.get("output_text") or "".join(
        c.get("text", "") for o in d.get("output", []) if o.get("type") == "message"
        for c in o.get("content", []) if c.get("type") in ("output_text", "text"))
    u = d.get("usage") or {}
    cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
    inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
    usd = ((inp - cached) * OPENAI_PRICE["input"] + cached * OPENAI_PRICE["cached_input"]
           + out * OPENAI_PRICE["output"]) / 1e6
    counts = {"input": inp, "cached_input": cached, "output": out,
              "reasoning": int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0),
              "model": d.get("model"), "stop": d.get("status"),
              "incomplete": d.get("incomplete_details")}
    S.record(script=SCRIPT, role="m1-judge-openai", issue=LEDGER_ISSUE, usd=usd,
             input_tokens=inp, output_tokens=out, note=d.get("model") or OPENAI_MODEL)
    return text, counts, usd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cap", type=float, default=10.0)
    ap.add_argument("--only")
    ap.add_argument("--judges", default="claude,openai")
    ap.add_argument("--claude-model", default=CLAUDE_MODEL,
                    help="diagnostics only; replies go to replies/claude@<model>")
    ap.add_argument("--tag", default="", help="suffix for the replies folder, e.g. a retry")
    a = ap.parse_args()
    run = Path(a.run_dir)
    items = json.loads((run / "items.json").read_text())
    manifest = {r["item"]: r for r in json.loads((run / "snapshots" / "manifest.json").read_text())}
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["item"] in keep]
    keys = env_keys()
    import anthropic
    raw_client = anthropic.Anthropic(api_key=keys["ANTHROPIC_API_KEY"])
    client = S.metered(raw_client, script=SCRIPT, issue=LEDGER_ISSUE, role="m1-judge-claude")
    prompt_sha = hashlib.sha256(PROMPT.read_bytes()).hexdigest()
    skipped = []
    for it in items:
        m = manifest[it["item"]]
        if m["extent"] == "unreachable":
            skipped.append((it["item"], m["extent_why"]))
            continue
        doc = (run / "snapshots" / (it["item"] + ".txt")).read_text(encoding="utf-8")
        prompt = build(it, doc, m["extent"])
        n_in = raw_client.messages.count_tokens(
            model=CLAUDE_MODEL, messages=[{"role": "user", "content": prompt}]).input_tokens
        for judge in a.judges.split(","):
            jdir = judge + ("@" + a.claude_model if judge == "claude" and a.claude_model != CLAUDE_MODEL else "")
            out = run / "replies" / (jdir + a.tag) / (it["item"] + ".json")
            if out.exists():
                continue
            if judge == "claude":
                p = S.PRICES[a.claude_model]
                worst = (n_in * p["input"] + CLAUDE_MAX_OUT * p["output"]) / 1e6
            else:
                worst = (n_in * TOKEN_PAD * OPENAI_PRICE["input"] + OPENAI_MAX_OUT * OPENAI_PRICE["output"]) / 1e6
            spent = round_spent()
            if spent + worst > a.cap:
                print("STOP: %s on %s could cost up to $%.3f; this round has spent $%.3f of $%.2f"
                      % (judge, it["item"], worst, spent, a.cap))
                return 3
            t0 = time.time()
            for attempt in range(3):
                try:
                    text, usage, usd = (call_claude(client, prompt, a.claude_model) if judge == "claude"
                                        else call_openai(keys["OPENAI_API_KEY"], prompt))
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    print("  retry %s %s: %s" % (judge, it["item"], str(e)[:160]))
                    time.sleep(10)
            obj, problems = parse(text)
            span_ok = bool(obj and obj.get("span") and norm(obj["span"]) in norm(doc))
            rec = {"item": it["item"], "judge": judge, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "seconds": round(time.time() - t0, 1), "prompt_sha256": prompt_sha,
                   "snapshot_text_sha256": m["text_sha256"], "extent": m["extent"],
                   "input_tokens_counted": n_in, "usage": usage, "usd": round(usd, 6),
                   "raw": text, "parsed": obj, "form_problems": problems,
                   "span_verbatim_in_document": span_ok, "reference": it["reference"]}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
            print("%-5s %-7s %-13s ref %-11s $%.4f  in %6d out %5d  %s%s" % (
                it["item"], judge, (obj or {}).get("label"), it["reference"], usd,
                usage.get("input", 0), usage.get("output", 0),
                "span ok" if span_ok else "SPAN NOT VERBATIM",
                ("  FORM: " + "; ".join(problems)) if problems else ""))
    for s in skipped:
        print("skipped (unreachable): %s  %s" % s)
    print("round spent: $%.4f" % round_spent())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
