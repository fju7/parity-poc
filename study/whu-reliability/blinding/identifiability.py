#!/usr/bin/env python3
"""The paid identifiability check (blinding ruling, 19 October 2026).

A model sees blinded sentences and guesses which of the four systems wrote
each. With four systems chance is 25%. Since protocol rev 24 ("Rulings from
prep round 2") the result is reported, not a gate: the bias test replaced the
50% threshold. The result still says whether WHU was identified more than half
the time, and how far each system's rate is from chance (a one-sided binomial
tail).

Usage:
    identifiability.py SENTENCES_DIR OUT_DIR [--n 20] [--seed 20261019]
                       [--batch 20] [--cap 25] [--ledger-issue NAME]

SENTENCES_DIR holds the *.sentences.blind.jsonl files blind.py --sentences
wrote, one row per sentence with its system. For each system, N sentences (or all
of them, if it has fewer) are drawn at random (fixed seed) from those that may be sampled and are claim-like
(a number or a citation marker, 8 to 70 words): what M1 samples. Each is shown
as an M1 judge sees it, with the ~400 characters before it. All of them are
shuffled together and sent in batches.

Writes OUT_DIR/sample.json, OUT_DIR/replies/*.json and OUT_DIR/result.json
(the confusion table, each system's identification rate against chance, and
the clues the guesser named for each system it identified).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

MODEL = "claude-opus-5-5"
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini"]
SCRIPT = "study/whu-reliability/identifiability.py"

PROMPT = """Below are {k} short passages. Each is one sentence (marked SENTENCE) from a written answer to a health research question, with the text that came just before it (marked BEFORE). Formatting, headings and some phrasing have been normalised.

Each answer was written by one of four systems:
- WHU: "What Holds Up", an independent publication that writes evidence assessments for general readers.
- Claude: Anthropic's Claude in its Research mode.
- ChatGPT: OpenAI's ChatGPT deep research.
- Gemini: Google's Gemini Deep Research.

For each passage, guess which system wrote the SENTENCE. Guess even when unsure. Use anything in the text: wording, style, citation format, what is said and how.

{passages}

Reply with ONE JSON array and nothing else, one object per passage, in order:
[{{"id": "<passage id>", "guess": "<WHU, Claude, ChatGPT or Gemini>", "confidence": "<low, medium or high>", "clue": "<what in the text made you guess this, in a few words>"}}, ...]
"""


def env_key() -> str:
    for line in (ROOT / "backend" / ".env").read_text().splitlines():
        m = re.match(r"^ANTHROPIC_API_KEY=(.*)$", line.strip())
        if m:
            return m.group(1).strip().strip("'\"")
    raise SystemExit("no ANTHROPIC_API_KEY in backend/.env")


def claim_like(r: dict) -> bool:
    t = r["text"]
    n = len(t.split())
    return r["samplable"] and 8 <= n <= 70 and bool(re.search(r"\d|\[\d+\]", t))


def draw(sent_dir: Path, n: int, seed: int) -> list[dict]:
    pools: dict[str, list[dict]] = {s: [] for s in SYSTEMS}
    for f in sorted(sent_dir.glob("*.sentences.blind.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if claim_like(r):
                pools[r["system"]].append(r)
    rng = random.Random(seed)
    out = []
    for s in SYSTEMS:
        pool = pools[s]
        if not pool:
            raise SystemExit("%s has no claim-like samplable sentences" % s)
        out += rng.sample(pool, min(n, len(pool)))
    rng.shuffle(out)
    for i, r in enumerate(out, 1):
        r["id"] = "X%02d" % i
    return out


def binom_tail(k: int, n: int, p: float = 0.25) -> float:
    """P(X >= k) for X ~ Binomial(n, p): how likely k or more correct guesses
    of n would be by chance."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def tally(sample: list[dict], guesses: dict[str, dict]) -> dict:
    """The confusion table and, per system, its identification rate against
    chance and the clues the guesser gave when it identified that system."""
    conf = {s: Counter() for s in SYSTEMS}
    n = Counter(r["system"] for r in sample)
    identified_clues = {s: [] for s in SYSTEMS}
    all_clues = {s: [] for s in SYSTEMS}
    for r in sample:
        g = guesses.get(r["id"], {})
        conf[r["system"]][g.get("guess", "(none)")] += 1
        all_clues[r["system"]].append({"id": r["id"], "guess": g.get("guess"), "confidence": g.get("confidence"),
                                       "clue": g.get("clue", "")})
        if g.get("guess") == r["system"]:
            identified_clues[r["system"]].append(g.get("clue", ""))
    rates = {s: {"identified": conf[s][s], "n": n[s], "rate": round(conf[s][s] / n[s], 3) if n[s] else None,
                 "p_by_chance": float("%.3g" % binom_tail(conf[s][s], n[s])) if n[s] else None,
                 "guessed_as_this": sum(c[s] for c in conf.values())}
             for s in SYSTEMS}
    total = sum(n.values())
    return {"n_per_system": {s: n[s] for s in SYSTEMS},
            "confusion_rows_true_cols_guess": {s: dict(conf[s]) for s in SYSTEMS},
            "rates": rates, "chance": 0.25,
            "whu_identification_rate": rates["WHU"]["rate"],
            "whu_precision": "%d/%d" % (conf["WHU"]["WHU"], rates["WHU"]["guessed_as_this"]),
            "overall_accuracy": round(sum(conf[s][s] for s in SYSTEMS) / total, 3) if total else None,
            "whu_above_half": bool(n["WHU"]) and conf["WHU"]["WHU"] / n["WHU"] > 0.5,
            "gate": False, "note": "reported, not a gate (protocol rev 24)",
            "clues_when_identified": identified_clues,
            "all_clues_by_true_system": all_clues}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sent_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261019)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--cap", type=float, default=25.0)
    ap.add_argument("--ledger-issue", default="whu-reliability-prep2")
    a = ap.parse_args()
    out = Path(a.out_dir); (out / "replies").mkdir(parents=True, exist_ok=True)
    sample = draw(Path(a.sent_dir), a.n, a.seed)
    (out / "sample.json").write_text(json.dumps(sample, indent=1, ensure_ascii=False), encoding="utf-8")
    import anthropic
    raw = anthropic.Anthropic(api_key=env_key())
    client = S.metered(raw, script=SCRIPT, issue=a.ledger_issue, role="identifiability")
    guesses: dict[str, dict] = {}
    for b in range(0, len(sample), a.batch):
        chunk = sample[b:b + a.batch]
        passages = "\n\n".join("[%s]\nBEFORE: %s\nSENTENCE: %s" % (r["id"], r["context"].strip() or "(start of answer)", r["text"])
                               for r in chunk)
        prompt = PROMPT.format(k=len(chunk), passages=passages)
        f = out / "replies" / ("batch%02d.json" % (b // a.batch + 1))
        if f.exists():
            rep = json.loads(f.read_text())
        else:
            n_in = raw.messages.count_tokens(model=MODEL, messages=[{"role": "user", "content": prompt}]).input_tokens
            p = S.PRICES[MODEL]
            worst = (n_in * p["input"] + 4000 * p["output"]) / 1e6
            so_far = sum(float(e.get("usd") or 0) for e in S.entries() if e.get("issue") == a.ledger_issue)
            if so_far + worst > a.cap:
                print("STOP: batch would take %s past $%.2f (spent $%.3f)" % (a.ledger_issue, a.cap, so_far))
                return 3
            r = client.messages.create(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
            text = "".join(getattr(x, "text", "") for x in r.content)
            rep = {"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "raw": text,
                   "stop": r.stop_reason, "usage": {"input": r.usage.input_tokens, "output": r.usage.output_tokens}}
            f.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
        m = re.search(r"\[.*\]", rep["raw"], re.S)
        for g in json.loads(m.group(0)) if m else []:
            guesses[g["id"]] = g
    res = dict({"model": MODEL, "seed": a.seed, "n_asked_per_system": a.n}, **tally(sample, guesses))
    (out / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n_per_system", "confusion_rows_true_cols_guess", "rates",
                                          "whu_precision", "overall_accuracy", "whu_above_half", "note")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
