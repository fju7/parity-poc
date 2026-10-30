#!/usr/bin/env python3
"""Check 3, identifiability (validity plan §3): each judge model guesses which system wrote round-1 text.

    identify.py --cap 5 [--estimate]

blinding/identifiability.py's method, with the plan's two runner changes: five systems (chance 1/5; its prompt names
four, so PROMPT below adds Perplexity, and the M1 wording "health research question" becomes "research question",
round 1 having IPCC questions), and three guessers (claude-opus-5-5, gpt-6-astra, gemini-4-argon). Sample: for each
system, 20 of its round-1 M1 items (the drawn sentence and the context the judges saw), random.Random("%d/check3/%s"
% (SEED, system)); shuffled together; batches of 20. Plus each of the 19 blinded answers the M2 judges saw, one per
call. Ledger issue whu-validity-c3-ident; before every call, caps.json's day cap and --cap.
Outputs: ~/Projects/whu-study-private/validity/check3/ (sample, replies); counts to next_phase/results/check3.json.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
import judge_google as G  # noqa: E402
import judge_m1 as J1  # noqa: E402

S = J1.S
_i = importlib.util.spec_from_file_location("identifiability_v", HERE.parent / "blinding" / "identifiability.py")
I = importlib.util.module_from_spec(_i)
_i.loader.exec_module(I)
SEED = G.SEED
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "quarterly" / "round1"
OUT = Path.home() / "Projects" / "whu-study-private" / "validity" / "check3"
ISSUE = "whu-validity-c3-ident"
SCRIPT = "study/whu-reliability/next_phase/identify.py"
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini", "Perplexity"]
GUESSERS = ["claude", "openai", "google"]
MAX_OUT = 6000
WHO = """Each answer was written by one of five systems:
- WHU: "What Holds Up", an independent publication that writes evidence assessments for general readers.
- Claude: Anthropic's Claude in its Research mode.
- ChatGPT: OpenAI's ChatGPT deep research.
- Gemini: Google's Gemini Deep Research.
- Perplexity: Perplexity's Deep Research."""
PROMPT = """Below are {k} short passages. Each is one sentence (marked SENTENCE) from a written answer to a research question, with the text that came just before it (marked BEFORE). Formatting, headings and some phrasing have been normalised.

""" + WHO + """

For each passage, guess which system wrote the SENTENCE. Guess even when unsure. Use anything in the text: wording, style, citation format, what is said and how.

{passages}

Reply with ONE JSON array and nothing else, one object per passage, in order:
[{{"id": "<passage id>", "guess": "<WHU, Claude, ChatGPT, Gemini or Perplexity>", "confidence": "<low, medium or high>", "clue": "<what in the text made you guess this, in a few words>"}}, ...]
"""
ANSWER_PROMPT = """Below is a written answer to a research question. Formatting, headings and some phrasing have been normalised.

""" + WHO + """

Guess which system wrote it. Guess even when unsure. Use anything in the text: wording, style, citation format, what is said and how.

<<<ANSWER
{answer}
ANSWER>>>

Reply with ONE JSON object and nothing else:
{{"guess": "<WHU, Claude, ChatGPT, Gemini or Perplexity>", "confidence": "<low, medium or high>", "clue": "<what in the text made you guess this, in a few words>"}}
"""


def sample() -> list[dict]:
    km = json.loads((RUN / "m1" / "key_map.json").read_text())
    rows = json.loads((RUN / "m1" / "items.json").read_text()) + json.loads((RUN / "m1" / "uncited.json").read_text())
    out = []
    for s in SYSTEMS:
        pool = sorted((r for r in rows if km[r["item"]]["system"] == s), key=lambda r: r["item"])
        out += [{"item": r["item"], "system": s, "question": km[r["item"]]["question"], "text": r["claim"],
                 "context": r.get("context") or ""}
                for r in random.Random("%d/check3/%s" % (SEED, s)).sample(pool, min(20, len(pool)))]
    random.Random("%d/check3/order" % SEED).shuffle(out)
    for i, r in enumerate(out, 1):
        r["id"] = "X%03d" % i
    return out


def answers() -> list[dict]:
    spec = json.loads((RUN / "m2" / "items.json").read_text())
    km = json.loads((RUN / "m2" / "key_map.json").read_text())
    out = [{"answer": k, "system": km[k]["system"], "question": km[k]["question"], "file": v["file"]}
           for k, v in spec["answers"].items()]
    return sorted(out, key=lambda a: a["answer"])


class Caller:
    def __init__(self, cap: float):
        self.cap, self.keys = cap, J1.env_keys()
        import anthropic
        self.raw = anthropic.Anthropic(api_key=self.keys["ANTHROPIC_API_KEY"])
        self.claude = S.metered(self.raw, script=SCRIPT, issue=ISSUE, role="identifiability-claude")
        self.gc = G.client()

    def n_in(self, text: str) -> int:
        return self.raw.messages.count_tokens(model=J1.CLAUDE_MODEL,
                                              messages=[{"role": "user", "content": text}]).input_tokens

    def worst(self, who: str, n: int) -> float:
        if who == "claude":
            p = S.PRICES[J1.CLAUDE_MODEL]
            return (n * p["input"] + MAX_OUT * p["output"]) / 1e6
        if who == "openai":
            return (n * J1.OPENAI_PRICE["input"] + MAX_OUT * J1.OPENAI_PRICE["output"]) / 1e6
        return G.worst_usd(int(n * 1.2))

    def ask(self, who: str, text: str) -> dict:
        n = self.n_in(text)
        w = self.worst(who, n)
        S.check_day_cap(w)
        so_far = J1.spent(ISSUE)
        if so_far + w > self.cap:
            raise G.Stop("%s: $%.3f spent; the next call could cost up to $%.3f (cap $%.2f)" % (ISSUE, so_far, w, self.cap))
        if who == "claude":
            r = self.claude.messages.create(model=J1.CLAUDE_MODEL, max_tokens=MAX_OUT,
                                            messages=[{"role": "user", "content": text}])
            return {"raw": "".join(getattr(x, "text", "") for x in r.content), "model": r.model}
        if who == "openai":
            d = J1.post_openai({"model": J1.OPENAI_MODEL, "input": text, "max_output_tokens": MAX_OUT},
                               self.keys["OPENAI_API_KEY"]).json()
            u = d.get("usage") or {}
            cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
            inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
            usd = ((inp - cached) * J1.OPENAI_PRICE["input"] + cached * J1.OPENAI_PRICE["cached_input"]
                   + out * J1.OPENAI_PRICE["output"]) / 1e6
            S.record(script=SCRIPT, role="identifiability-openai", issue=ISSUE, usd=usd, input_tokens=inp,
                     output_tokens=out, note=d.get("model") or J1.OPENAI_MODEL)
            texts = [c.get("text", "") for o in d.get("output", []) if o.get("type") == "message"
                     for c in o.get("content", []) if c.get("type") in ("output_text", "text")]
            return {"raw": d.get("output_text") or "".join(texts), "model": d.get("model")}
        raw, usage, _usd, _ref = G.call(self.gc, text, ISSUE, "identifiability-google")
        return {"raw": raw, "model": usage.get("model")}


def binom_tail(k: int, n: int) -> float:
    return I.binom_tail(k, n, 0.2)


def tally(smp: list[dict], guesses: dict) -> dict:
    I.SYSTEMS = SYSTEMS
    t = I.tally(smp, guesses)
    for s in SYSTEMS:                                    # the module's tail is against 1/4; the plan's is 1/5
        r = t["rates"][s]
        r["p_by_chance"] = float("%.3g" % binom_tail(r["identified"], r["n"])) if r["n"] else None
    t["chance"] = 0.2
    t.pop("all_clues_by_true_system", None)
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--estimate", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    smp = sample()
    (OUT / "sample.json").write_text(json.dumps(smp, indent=1, ensure_ascii=False), encoding="utf-8")
    batches = []
    for b in range(0, len(smp), 20):
        chunk = smp[b:b + 20]
        passages = "\n\n".join("[%s]\nBEFORE: %s\nSENTENCE: %s" % (r["id"], r["context"].strip() or "(start of answer)",
                                                                   r["text"]) for r in chunk)
        batches.append(("batch%02d" % (b // 20 + 1), PROMPT.format(k=len(chunk), passages=passages)))
    ans = answers()
    for x in ans:
        batches.append(("answer-" + x["answer"], ANSWER_PROMPT.format(
            answer=(RUN / "m2" / x["file"]).read_text(encoding="utf-8"))))
    c = Caller(a.cap)
    est = sum(c.worst(w, c.n_in(t)) for _n, t in batches for w in GUESSERS)
    likely = 0.0
    for _n, t in batches:
        n = c.n_in(t)
        p = S.PRICES[J1.CLAUDE_MODEL]
        likely += (n * p["input"] + 800 * p["output"]) / 1e6
        likely += (n * 0.62 * J1.OPENAI_PRICE["input"] + 1500 * J1.OPENAI_PRICE["output"]) / 1e6
        gp = S.rates(G.MODEL, n)
        likely += (n * gp["input"] + 2000 * gp["output"]) / 1e6
    print("check 3: %d sentences in %d batches, %d answers, 3 guessers; ESTIMATE likely $%.2f, worst $%.2f; cap $%.2f"
          % (len(smp), (len(smp) + 19) // 20, len(ans), likely, est, a.cap))
    if a.estimate:
        return 0
    if likely > a.cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    for who in GUESSERS:
        d = OUT / "replies" / who
        d.mkdir(parents=True, exist_ok=True)
        for name, text in batches:
            f = d / (name + ".json")
            if f.exists():
                continue
            try:
                rep = c.ask(who, text)
            except (G.Stop, S.OverCap) as e:
                print("STOP before %s %s: %s" % (who, name, e))
                return 3
            f.write_text(json.dumps({"prompt_sha256": hashlib.sha256(text.encode()).hexdigest(), **rep}, indent=1,
                                    ensure_ascii=False), encoding="utf-8")
            print("  %s %s done" % (who, name), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
