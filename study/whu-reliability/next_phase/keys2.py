#!/usr/bin/env python3
"""Check 4, second answer keys (validity plan §4): drafted and checked by gemini-4-argon, then M2 rescored.

    keys2.py prepare                 free: each question's texts (as given) and Gemini token counts; the estimate
    keys2.py draft --cap 12          PAID (whu-validity-c4-keys): draft, verify quotes by code, check, apply by code
    keys2.py freeze                  sha256 of every second key -> next_phase/keys2_manifest.txt (commit it)
    keys2.py build                   free: M2 run folders for rescoring (round 1; study S01-S02), private

Rescoring then runs the study's runners on those folders (judge_m2.py: claude, openai; judge_google.py m2), ledger
issue whu-reliability-judging-validity-c4m2, cap $28 for the three together.

TEXTS. The first key's own folder (keys/.../<q>/source/), each file checked against its sources.sha256 first; the
.txt files only, in the order sources.sha256 lists them (an XML or PDF is given as the .txt beside it; spm_page.html
is not given, its text being statement.txt and the SPM .txt). Over CUT_TOKENS (Gemini's count) the text is cut at
that length (by the APPROXIMATION judge_google.approx_tokens: no count_tokens call), and the cut is logged.

KEYS. A quote is verified when judge_m1.norm(quote) is in judge_m1.norm(the text as given). A drafted conclusion
with any unverified quote is dropped and logged; so is a checker's correction or addition with one (a correction
that fails leaves the conclusion dropped, not restored). At most five conclusions. Nothing here reads a first key's
conclusions; the drafter and checker see only the question, the citation and the texts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
import judge_google as G  # noqa: E402
import judge_m1 as J1  # noqa: E402

S = J1.S
REPO = HERE.parents[2]
PRIV = Path.home() / "Projects" / "whu-study-private"
KEYS1 = {**{q: PRIV / "keys" / "quarterly" / "round1" / q for q in ("WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03", "WHU-Q1-04")},
         **{q: PRIV / "keys" / q for q in ("WHU-S01", "WHU-S02")}}
OUT = PRIV / "keys2"
CHECK4 = PRIV / "validity" / "check4"
ISSUE = "whu-validity-c4-keys"
SCRIPT = "study/whu-reliability/next_phase/keys2.py"
CUT_TOKENS = 900_000
# Exempt from the cut (advisor approval 2026-10-30, next_phase/deviations.md): the full text is sent; if Google
# refuses it as too long, the question is reported as not run, with the reason. It is never cut.
CUT_EXEMPT = {"WHU-Q1-04"}
MAX_OUT = 32_768
PROMPTS = {"draft": (HERE / "prompts" / "key2_draft.md", "0f8668721f38c7413104b88081309daf0cd2af0405660d5cd7d29512935a88b1"),
           "check": (HERE / "prompts" / "key2_check.md", "55c0fbcab5530c00d7536cb33e8bd0c85f38e074a0513968ead3bb20cf9c6620")}
FIELDS = ("statement", "direction", "size", "certainty", "scope")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def prompt(which: str) -> str:
    p, want = PROMPTS[which]
    if sha(p.read_bytes()) != want:
        raise SystemExit("STOP: %s is not the frozen prompt (sha256 %s)" % (p, want))
    return p.read_text(encoding="utf-8")


def question(q: str) -> str:
    d = next((REPO / "issues").glob(q + "-*"))
    return json.loads((d / "issue.json").read_text())["question"]


def citation(q: str) -> str:
    return json.loads((KEYS1[q] / "key.json").read_text())["source"]["citation"]


def texts(q: str) -> list[tuple[str, str]]:
    """[(file, text)]: the .txt files in sources.sha256 order, each hash-checked."""
    base = KEYS1[q]
    out = []
    for line in (base / "sources.sha256").read_text().splitlines():
        if not line.strip():
            continue
        h, rel = line.split(None, 1)
        f = base / rel.strip()
        if sha(f.read_bytes()) != h:
            raise SystemExit("STOP: %s does not match sources.sha256" % f)
        if f.suffix == ".txt":
            out.append((rel.strip(), f.read_text(encoding="utf-8")))
    return out


def given(q: str, gc) -> dict:
    parts, blocks, total, cut = texts(q), [], 0, None
    for rel, t in parts:
        block = "=== %s ===\n%s" % (rel, t)
        n = int(G.approx_tokens(block))                    # APPROXIMATION (no count_tokens call)
        if total + n > CUT_TOKENS and q not in CUT_EXEMPT:
            keep = int(len(block) * (CUT_TOKENS - total) / n)
            blocks.append(block[:max(keep, 0)])
            cut = {"file": rel, "kept_chars": max(keep, 0), "of_chars": len(block), "tokens_before": total + n}
            total = CUT_TOKENS
            break
        blocks.append(block)
        total += n
    return {"files": [r for r, _ in parts], "text": "\n\n".join(blocks), "tokens": total, "cut": cut}


def generate(gc, text: str, role: str, guard: G.Guard) -> tuple[str, dict]:
    from google.genai import types
    n = int(G.approx_tokens(text))                           # APPROXIMATION, for the worst case only
    p = S.rates(G.MODEL, n)
    worst = (n * p["input"] + MAX_OUT * p["output"]) / 1e6
    guard.take(worst)
    try:
        r = gc.models.generate_content(model=G.MODEL, contents=text,
                                       config=types.GenerateContentConfig(max_output_tokens=MAX_OUT))
    finally:
        guard.done(worst)
    mv = getattr(r, "model_version", "") or ""
    if mv and not mv.startswith(G.MODEL):
        raise G.Stop("reply from %r" % mv)
    u = r.usage_metadata
    prompt_t = int(u.prompt_token_count or 0)
    cached = int(getattr(u, "cached_content_token_count", 0) or 0)
    out_t = int(u.candidates_token_count or 0) + int(getattr(u, "thoughts_token_count", 0) or 0)
    usd = ((prompt_t - cached) * p["input"] + cached * p["cache_read"] + out_t * p["output"]) / 1e6
    S.record(script=SCRIPT, role=role, issue=ISSUE, usd=usd, input_tokens=prompt_t, output_tokens=out_t,
             note="%s; cached=%d" % (mv or G.MODEL, cached))
    cands = getattr(r, "candidates", None) or []
    return (r.text or ""), {"usd": round(usd, 6), "input": prompt_t, "output": out_t, "model": mv,
                            "finish": str(getattr(cands[0], "finish_reason", "")) if cands else ""}


def parse(raw: str) -> dict | None:
    s = re.sub(r"^```(json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except Exception:
            return None


def verified(c: dict, hay: str) -> list[str]:
    """Problems with one conclusion: missing fields or quotes not found word for word."""
    bad = [f for f in FIELDS if not str(c.get(f) or "").strip()]
    qs = c.get("quotes") or []
    if not qs:
        bad.append("no quotation")
    for x in qs:
        if not x.get("text") or J1.norm(x["text"]) not in hay:
            bad.append("quote not found: %r" % (x.get("text") or "")[:80])
    return bad


def draft(cap: float) -> int:
    cuts = {q: given(q, None)["cut"] for q in KEYS1}           # no Google call: the approximation
    cuts = {q: c for q, c in cuts.items() if c}
    if cuts:
        print("STOP: under the token APPROXIMATION (chars/3) these texts would be cut at %d tokens: %s. Google's own "
              "count (2026-10-30) gave no cut. A cut needs the advisor's ruling; nothing was called." % (CUT_TOKENS, cuts))
        return 9
    try:
        gc = G.client()                                      # the preflight, before any other Google call
    except G.Stop as e:
        print("STOP: %s" % e)
        return 8
    guard = G.Guard(ISSUE, cap)
    pd, pc = prompt("draft"), prompt("check")
    for q in KEYS1:
        d = OUT / q
        if (d / "key.json").exists():
            print("%s: second key exists; kept" % q)
            continue
        if (d / "not_run.json").exists():
            print("%s: recorded as not run; kept" % q)
            continue
        d.mkdir(parents=True, exist_ok=True)
        g = given(q, gc)
        hay = J1.norm(g["text"])
        log = {"question": q, "files_given": g["files"], "tokens_given": g["tokens"], "cut": g["cut"], "steps": []}
        try:
            text = pd.replace("{question}", question(q)).replace("{review}", citation(q)).replace("{documents}", g["text"])
            raw, use = generate(gc, text, "key2-draft", guard)
            (d / "draft_reply.txt").write_text(raw, encoding="utf-8")
            obj = parse(raw) or {}
            kept = []
            for c in (obj.get("conclusions") or [])[:5]:
                bad = verified(c, hay)
                log["steps"].append({"stage": "draft", "n": c.get("n"), "dropped": bool(bad), "why": bad})
                if not bad:
                    kept.append(c)
            log["draft_usage"] = use
            ktext = json.dumps({"conclusions": kept}, indent=1, ensure_ascii=False)
            text = (pc.replace("{question}", question(q)).replace("{review}", citation(q))
                    .replace("{key}", ktext).replace("{documents}", g["text"]))
            raw, use = generate(gc, text, "key2-check", guard)
            (d / "check_reply.txt").write_text(raw, encoding="utf-8")
            log["check_usage"] = use
        except (G.Stop, S.OverCap) as e:
            print("STOP on %s: %s" % (q, e))
            return 3
        except Exception as e:                                # a refusal, e.g. the input over the model's limit
            if q in CUT_EXEMPT and getattr(e, "code", None) == 400:
                (d / "not_run.json").write_text(json.dumps({
                    "question": q, "at": now(), "reason": "the full text was refused by %s (HTTP 400): %s; under the "
                    "advisor's exemption it is not cut, so check 4 is not run for this question" % (G.MODEL, str(e)[:300]),
                    "tokens_given_approx": g["tokens"]}, indent=1))
                print("%s: NOT RUN (full text refused, HTTP 400); recorded" % q, flush=True)
                continue
            raise
        chk = parse(raw) or {}
        by_n = {c.get("n"): c for c in kept}
        final = []
        for ch in chk.get("checks") or []:
            v, n = ch.get("verdict"), ch.get("n")
            if v == "keep" and n in by_n:
                final.append(by_n.pop(n))
            elif v in ("correct", "add") and ch.get("conclusion"):
                bad = verified(ch["conclusion"], hay)
                log["steps"].append({"stage": "check", "n": n, "verdict": v, "reason": ch.get("reason"),
                                     "dropped": bool(bad), "why": bad})
                by_n.pop(n, None) if v == "correct" else None
                if not bad:
                    final.append(ch["conclusion"])
            elif v == "drop":
                by_n.pop(n, None)
                log["steps"].append({"stage": "check", "n": n, "verdict": "drop", "reason": ch.get("reason")})
        for n, c in by_n.items():                         # a conclusion the checker did not mention is kept
            log["steps"].append({"stage": "check", "n": n, "verdict": "not mentioned; kept"})
            final.append(c)
        final = final[:5]
        for i, c in enumerate(final, 1):
            c["n"] = i
        key = {"question_id": q, "source": {"citation": citation(q)}, "drafted_by": G.MODEL, "checked_by": G.MODEL,
               "drafted_on": now(), "prompts": {k: v[1] for k, v in PROMPTS.items()}, "conclusions": final}
        (d / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
        (d / "check_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
        print("%s: %d conclusions (drafted %d, kept after quotes %d); $%.3f; cut %s" % (
            q, len(final), len(obj.get("conclusions") or []), len(kept),
            log["draft_usage"]["usd"] + log["check_usage"]["usd"], g["cut"]), flush=True)
    print("%s spent: $%.4f" % (ISSUE, J1.spent(ISSUE)))
    return 0


def prepare() -> int:
    gc = None                                                # no Google call: the counts are approximations
    total, worst = 0, 0.0
    for q in KEYS1:
        g = given(q, gc)
        p = S.rates(G.MODEL, g["tokens"])
        w = 2 * (g["tokens"] * p["input"] + MAX_OUT * p["output"]) / 1e6
        total += g["tokens"]
        worst += w
        print("%s: %s; %d tokens given (APPROXIMATION, chars/3); cut %s; worst $%.2f" % (q, g["files"], g["tokens"], g["cut"], w))
    likely = 2 * total * 2.0 / 1e6 + 12 * 6000 * 10.0 / 1e6
    print("ESTIMATE keys: likely $%.2f (two reads of %d tokens, 6,000 output a call), worst $%.2f; cap $12"
          % (likely, total, worst))
    return 0


def freeze() -> int:
    lines = ["# WHU validity check 4: second answer keys (gemini-4-argon), sha256 manifest. Keys and logs are private,",
             "# ~/Projects/whu-study-private/keys2/<question>/; only these hashes are committed (validity_plan.md §4).",
             "# sha256  path (relative to ~/Projects/whu-study-private/keys2/)"]
    for q in KEYS1:
        for f in ("key.json", "check_log.json", "draft_reply.txt", "check_reply.txt"):
            p = OUT / q / f
            if not p.exists():
                raise SystemExit("STOP: %s missing" % p)
            lines.append("%s  %s/%s" % (sha(p.read_bytes()), q, f))
    (HERE / "keys2_manifest.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def build() -> int:
    """Two M2 run folders in judge_m2's layout, one item per (answer, second-key conclusion)."""
    sets = {"round1": (PRIV / "scoring" / "quarterly" / "round1" / "m2", ["WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03", "WHU-Q1-04"]),
            "study": (None, ["WHU-S01", "WHU-S02"])}
    for name, (src, qs) in sets.items():
        srcs = [src] if src else [PRIV / "scoring" / "m2", PRIV / "scoring" / "perplexity" / "m2"]
        run = CHECK4 / ("m2_" + name)
        (run / "answers").mkdir(parents=True, exist_ok=True)
        answers, km, concl, items = {}, {}, [], []
        for s in srcs:
            spec = json.loads((s / "items.json").read_text())
            kmap = json.loads((s / "key_map.json").read_text())
            for a, v in spec["answers"].items():
                if kmap[a]["question"] in qs:
                    t = (s / v["file"]).read_text(encoding="utf-8")
                    (run / "answers" / (a + ".txt")).write_text(t, encoding="utf-8")
                    answers[a] = {"file": "answers/%s.txt" % a}
                    km[a] = kmap[a]
        for q in qs:
            for c in json.loads((OUT / q / "key.json").read_text())["conclusions"]:
                quote = "; ".join('"%s" (%s)' % (x["text"], x.get("section") or "") for x in c.get("quotes") or [])
                concl.append({"id": "%s-K2C%d" % (q, c["n"]), "statement": c["statement"], "direction": c["direction"],
                              "size": c["size"], "certainty": c["certainty"], "scope": c["scope"], "quote": quote})
        for a in sorted(answers):
            for c in concl:
                if c["id"].startswith(km[a]["question"] + "-"):
                    items.append({"item": "M2K2-" + sha(("%d/%s/%s" % (G.SEED, a, c["id"])).encode())[:10],
                                  "answer": a, "conclusion": c["id"]})
        (run / "items.json").write_text(json.dumps({"answers": answers, "conclusions": concl, "items": items}, indent=1,
                                                   ensure_ascii=False))
        (run / "key_map.json").write_text(json.dumps(km, indent=1))
        print("%s: %d answers, %d conclusions, %d items -> %s" % (name, len(answers), len(concl), len(items), run))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "draft" and "--cap" in sys.argv:
        raise SystemExit(draft(float(sys.argv[sys.argv.index("--cap") + 1])))
    fn = {"prepare": prepare, "freeze": freeze, "build": build}.get(cmd)
    raise SystemExit(fn() if fn else (print(__doc__) or 2))
