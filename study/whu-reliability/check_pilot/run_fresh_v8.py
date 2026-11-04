#!/usr/bin/env python3
"""The check pilot's fresh set, stage 1: v8 end to end on the 18 fresh answers (docs/whu-check-an-answer-pilot.md
§16, §16.9-§16.11).

    run_fresh_v8.py build Q SYSTEM META.json   the capture file around <system>.raw.md (round 1's build_capture_r1.py)
    run_fresh_v8.py verify                     every capture present, its raw copy's sha256 as in the manifest
    run_fresh_v8.py prepare                    free: fetch and plan each answer in a scratch folder (no model call);
                                               likely and worst printed and written (§16.11)
    run_fresh_v8.py run --today X [--vp-planned Y]   PAID, ledger issue whu-check-fresh-v8 (line cap $75):
                                               answers in order, each only if this run's spend + its likely <= X;
                                               a finished answer is kept and never re-run
    run_fresh_v8.py compare                    §10.7's bars except agreement (stage 2), per-answer distributions,
                                               each mean also without the largest answer (§16.3)

Each answer runs through pipeline_v8.check from the capture: fetch, stage 1, re-reads, windows; wall time measured
end to end (§16.5). Answers run one at a time so each time is its own. Private outputs:
~/Projects/whu-study-private/check_fresh_set/. Committed: counts only, check_pilot/fresh_v8_counts.json.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v5 as V5  # noqa: E402
import pipeline_v6 as V6  # noqa: E402
import pipeline_v8 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v3 as R3  # noqa: E402
import run_pilot_v4 as R4  # noqa: E402
import run_pilot_v5 as R5  # noqa: E402
import run_pilot_v7 as R7  # noqa: E402

J, S = V1.J, R3.S
ISSUE = "whu-check-fresh-v8"
ROLE = "check-fresh-v8"
SCRIPT = "study/whu-reliability/check_pilot/run_fresh_v8.py"
LINE_CAP = 75.0                                  # §16.9: "fresh-set stage 1", outside the phase; $75 from 2026-11-04
OUT = R.PRIVATE / "check_fresh_set"
ANSWERS = R.PRIVATE / "answers" / "check_fresh_set"
QUESTIONS = HERE / "fresh_set" / "questions.json"
MANIFEST = HERE / "fresh_set" / "answers_manifest.txt"
COUNTS = HERE / "fresh_v8_counts.json"
SAMPLES = HERE / "fresh_set" / "scoring" / "sampling_log.json"     # fresh_samples.py sample: frozen before any call
SYSTEMS = ("Claude", "Gemini", "Perplexity")
TOOL = {"Claude": "claude", "Gemini": "gemini", "Perplexity": "perplexity"}
BUILD = R.PRIVATE / "scoring" / "quarterly" / "round1" / "tools" / "build_capture_r1.py"
PILOT = {v: R.PRIVATE / ("check_pilot_v%d" % v) for v in (4, 5, 6)}
JUDGED = (P.BACKED, P.NOT_BACKED)


def questions() -> list[dict]:
    return json.loads(QUESTIONS.read_text())["questions"]


def sample() -> list[tuple[str, str]]:
    """The 18 answers, question by question in id order, systems in SYSTEMS' order."""
    return [(q["id"], s) for q in questions() for s in SYSTEMS]


def work(q: str, s: str) -> Path:
    return OUT / "run" / ("%s-%s" % (q, s))


def capture(q: str, s: str) -> tuple[str, str]:
    """(capture file text, adapter format): round 1's adapters. Perplexity's report export ("## References") reads
    with perplexity_sources, its thread export with perplexity_footnotes, as round 1 read each."""
    md = (ANSWERS / q / (TOOL[s] + ".md")).read_text(encoding="utf-8")
    if s == "Claude":
        return md, "claude_sources_r1"
    if s == "Gemini":
        return md, "gemini_works_cited"
    return md, ("perplexity_sources" if re.search(r"(?m)^#{1,6}\s*References\s*$", md) else "perplexity_footnotes")


def clients(role: str = ROLE):
    import anthropic
    raw = anthropic.Anthropic(api_key=J.env_keys()["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script=SCRIPT, issue=ISSUE, role=role)


def spent(entries=None) -> float:
    return sum(e.get("usd") or 0 for e in (S.entries() if entries is None else entries) if e.get("issue") == ISSUE)


def role_lines(entries=None) -> list[dict]:
    return [e for e in (S.entries() if entries is None else entries) if e.get("role") == ROLE]


def counter_blind(spent_usd: float, lines: list[dict]) -> str | None:
    paid = [e for e in lines if (e.get("usd") or 0) > 0]
    if spent_usd == 0 and paid:
        return ("the spend counter for %s reads $0 while the ledger holds %d priced line(s) for role %s (issue %r)"
                % (ISSUE, len(paid), ROLE, paid[0].get("issue")))
    return None


class Budget(R7.Budget):
    """v7's budget (v5's per-call cap on the issue + the day cap via caps.json + the blind-counter stop), on this
    issue."""

    def __init__(self, cap, spent_fn, lines_fn, check_cap=None, no_call_after=None, clock=None):
        R5.Budget.__init__(self, cap, spent_fn, check_cap, no_call_after, clock, issue=ISSUE)
        self.lines_fn, self.returned_n = lines_fn, 0


# -- build and verify ----------------------------------------------------------------------------------------------

def do_build(a) -> int:
    meta = json.loads(Path(a.meta).read_text())
    meta.setdefault("adapt_py", str(HERE.parent / "blinding" / "adapt.py"))
    tmp = OUT / "build_meta" / ("%s-%s.json" % (a.q, a.system))
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return subprocess.run([sys.executable, str(BUILD), str(ANSWERS), a.q, TOOL[a.system], str(tmp)]).returncode


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def do_verify(_a=None) -> int:
    want = {}
    for line in MANIFEST.read_text().splitlines() if MANIFEST.exists() else []:
        if line.strip() and not line.startswith("#"):
            h, rel = line.split(None, 1)
            want[rel.strip()] = h
    bad = []
    for q, s in sample():
        rel = "%s/%s.raw.md" % (q, TOOL[s])
        p = ANSWERS / rel
        if not p.exists():
            bad.append("%s missing" % rel)
        elif want.get(rel) != sha_file(p):
            bad.append("%s sha256 %s, manifest %s" % (rel, sha_file(p)[:12], (want.get(rel) or "none")[:12]))
        elif not (ANSWERS / q / (TOOL[s] + ".md")).exists():
            bad.append("%s/%s.md (capture file) missing" % (q, TOOL[s]))
    print("\n".join(bad) or "all %d captures present and as in the manifest" % len(sample()))
    return 1 if bad else 0


# -- the free estimate (§16.11) ------------------------------------------------------------------------------------

def pilot_rates() -> dict:
    """Measured on the pilot (private outputs of v4-v6, read, not re-run): $ per input token over every paid call
    (stage 1, v5's re-reads, v6's windows; Opus throughout) and the share of stage-1-called claims re-read."""
    usd = tokens = called = reread = 0
    for f in glob.glob(str(PILOT[4] / "WHU-*" / "results.json")):
        for r in json.loads(Path(f).read_text())["results"]:
            if r.get("usd"):
                usd, tokens, called = usd + r["usd"], tokens + (r.get("n_in") or 0), called + 1
    for f in glob.glob(str(PILOT[5] / "WHU-*" / "results.json")):
        for r in json.loads(Path(f).read_text())["results"]:
            if r.get("usd_reread"):
                usd, tokens, reread = usd + r["usd_reread"], tokens + (r.get("n_in") or 0), reread + 1
    for f in glob.glob(str(PILOT[6] / "WHU-*" / "results.json")):
        for j in json.loads(Path(f).read_text())["jobs"]:
            if j.get("usd"):
                usd, tokens = usd + j["usd"], tokens + (j.get("n_in") or 0)
    if not tokens or not called:
        raise P.Stop("the pilot's outputs are not where the estimate reads them (%s)" % PILOT[4])
    return {"usd_per_input_token": usd / tokens, "reread_share": reread / called, "pilot_usd": round(usd, 4),
            "pilot_input_tokens": tokens, "pilot_stage1_calls": called, "pilot_rereads": reread}


def estimate_answer(prep: dict, wdir: Path, count, rates: dict) -> dict:
    """§16.11. Likely: stage 1's planned input x the pilot's $/token; each re-read at the pilot's re-read share, a
    claim's short sources read whole, each long source's windows once if any claim citing it is re-read
    (1 - (1 - share)^k). Worst: every stage-1 call at its own worst, every claim re-read whole, every long source
    read in every window for every batch of its claims, each a cache write + v6's maximum output."""
    rate, p = rates["usd_per_input_token"], rates["reread_share"]
    stage1 = [x for x in prep["planned"] if x["label"] is None]
    likely, worst = sum(x["n_in"] for x in stage1) * rate, sum(x["worst"] or 0 for x in stage1)
    long_src, windows = {}, 0
    for c in stage1:
        short = 0
        for ct in c["citations"]:
            m = prep["manifest"].get(ct.get("url") or "")
            if not m or m["extent"] == "unreachable":
                continue
            text = (wdir / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")
            n = count(text)
            if n > J.MAX_SOURCE_TOKENS:
                long_src.setdefault(m["source_id"], [text, 0])[1] += 1
            else:
                short += n
        if short:
            likely += p * (short + P.PROMPT_ALLOWANCE) * rate
            worst += V6.worst_cost(short + P.PROMPT_ALLOWANCE)
    for sid, (text, k) in long_src.items():
        ws = V6.windows(text, count, size=P.WINDOW_EST)
        windows += len(ws)
        n_in = sum(count(text[a:b]) for a, b in ws) + len(ws) * P.PROMPT_ALLOWANCE
        likely += (1 - (1 - p) ** k) * n_in * rate
        worst += sum(V6.worst_cost(count(text[a:b]) + P.PROMPT_ALLOWANCE) for a, b in ws) * math.ceil(k / V6.BATCH)
    return {"claims": len(prep["claims"]), "stage1_calls": len(stage1), "long_sources": len(long_src),
            "windows": windows, "likely_usd": round(likely, 4), "worst_usd": round(worst, 4)}


def do_prepare(_a) -> int:
    if do_verify():
        print("STOP: the captures are not complete and as fingerprinted; nothing estimated")
        return 4
    rates = pilot_rates()
    likely = worst = 0.0
    rows = []
    for q, s in sample():
        count = P.LocalCount(OUT / "prepare" / "token_counts.json")
        wdir = OUT / "prepare" / ("%s-%s" % (q, s))
        text, fmt = capture(q, s)
        prep = P.V4.prepare(text, wdir, fmt, count, s)
        est = estimate_answer(prep, wdir, count, rates)
        count.save()
        likely, worst = likely + est["likely_usd"], worst + est["worst_usd"]
        rows.append({"answer": "%s/%s" % (q, s), "format": fmt, **est})
        print("  %s %-10s %2d claims, %2d stage-1 calls, %d long source(s) in %2d windows; likely $%.2f, worst $%.2f"
              % (q, s, est["claims"], est["stage1_calls"], est["long_sources"], est["windows"], est["likely_usd"],
                 est["worst_usd"]))
    print("ESTIMATE: likely $%.2f, worst $%.2f (pilot rate $%.2f per million input tokens on v8's local estimate; "
          "re-read share %.2f)" % (likely, worst, rates["usd_per_input_token"] * 1e6, rates["reread_share"]))
    (OUT / "estimate.json").write_text(json.dumps({
        "at": R.now(), "likely_usd": round(likely, 4), "worst_usd": round(worst, 4), "rates": rates, "rows": rows,
        "estimator": P.ESTIMATOR, "batched_prompt_sha256": V6.batched_prompt_sha()}, indent=1))
    return 0


# -- the held-source format (§16.12): recorded beside v8, never read by it -----------------------------------------

class FormatLog:
    """pipeline_v3.NET with "get" and "render" wrapped to record, per response, the address, final address, status,
    content type and whether the body is a PDF. The response is passed on unchanged: v8 decides nothing differently."""

    def __init__(self, net: dict | None = None):
        import threading
        self.base = dict(net or P.V4.V3.NET)
        self.rows, self.lock = [], threading.Lock()

    def _log(self, url: str, **kw) -> None:
        with self.lock:
            self.rows.append({"url": url, **kw})

    def net(self) -> dict:
        def get(url, *a, **k):
            r = self.base["get"](url, *a, **k)
            self._log(url, final_url=r.get("final_url"), status=r.get("status"),
                      content_type=r.get("content_type") or "", pdf=(r.get("body") or b"")[:5] == b"%PDF-",
                      via="get")
            return r

        def render(url, *a, **k):
            data = self.base["render"](url, *a, **k)
            self._log(url, final_url=url, status=200, content_type="text/html (rendered)",
                      pdf=(data or b"")[:5] == b"%PDF-", via="render")
            return data
        return {**self.base, "get": get, "render": render}


def held_format(row: dict | None, fetches: list[dict]) -> str:
    """PDF, HTML or other (XML, plain text, a registry abstract with no fetch of its own); 'unreachable' when no
    copy is held; 'unknown' when no fetch of the copy's address was recorded."""
    if not row or row.get("extent") == "unreachable":
        return "unreachable"
    via = row.get("retrieved_from") or row.get("url")
    seen = [f for f in fetches if via in (f["url"], f.get("final_url")) and (f.get("status") or 0) < 400]
    if not seen:
        return "other" if not str(via).startswith("http") else "unknown"
    f = seen[-1]
    ct = (f.get("content_type") or "").lower()
    if f.get("pdf") or "pdf" in ct:
        return "PDF"
    if "html" in ct:
        return "HTML"
    return "other"


def by_format(per_answer: list[tuple[dict, list[dict]]]) -> dict:
    """Coverage and verdict distribution by held-source format (§16.12): per source, and per claim (a claim whose
    held sources differ in format is 'mixed'). Reported, nothing decided from it."""
    sources, claims = {}, {}
    for res, fetches in per_answer:
        man = res.get("manifest") or {}
        fmt = {u: held_format(row, fetches) for u, row in man.items()}
        for f in fmt.values():
            sources[f] = sources.get(f, 0) + 1
        for r in res["results"]:
            kinds = {fmt.get(ct.get("url")) for ct in r.get("citations") or [] if ct.get("url") in fmt}
            kinds.discard("unreachable")
            k = (kinds.pop() if len(kinds) == 1 else "mixed") if kinds else "no source held"
            c = claims.setdefault(k, {"claims": 0, "labels": {}})
            c["claims"] += 1
            c["labels"][r["label"]] = c["labels"].get(r["label"], 0) + 1
    for c in claims.values():
        cc = c["labels"].get(P.COULDNT, 0) + c["labels"].get(P.NOT_FOUND, 0)
        c["couldnt_check_share"] = round(cc / c["claims"], 4)
    return {"sources": sources, "claims": claims,
            "note": "Format of the copy v8 held, from the runner's fetch record (FormatLog). COULDN'T CHECK here "
                    "counts NOT FOUND as §10.7 does. Reported as seen; nothing decided from it in advance."}


# -- the paid run ---------------------------------------------------------------------------------------------------

def gate(likely: float, spent_usd: float, cap: float) -> tuple[bool, str]:
    return R7.gate(likely, spent_usd, cap)


def do_run(a) -> int:
    if do_verify():
        print("STOP: the captures are not complete and as fingerprinted; nothing was called")
        return 4
    if not SAMPLES.exists():
        print("STOP: the 20-sentence samples are not drawn and frozen (§16.9 item 2); nothing was called")
        return 4
    est = json.loads((OUT / "estimate.json").read_text())
    left = {r["answer"]: r for r in est["rows"]}
    todo = [(q, s) for q, s in sample() if not (work(q, s) / "results.json").exists()]
    likely_left = sum(left["%s/%s" % qs]["likely_usd"] for qs in todo)
    ok, why = gate(likely_left, spent(), LINE_CAP)
    print("ESTIMATE: likely $%.2f, worst $%.2f (from %s); %d answer(s) left, likely $%.2f\nGATE: %s"
          % (est["likely_usd"], est["worst_usd"], est["at"], len(todo), likely_left, why))
    if not ok:
        print("STOP: likely over the line's cap; nothing was called")
        return 5
    room_ok, rwhy = R5.room(a.today + a.vp_planned, R5.today_total(), float(S.caps()["default_per_day"]))
    print("ROOM: %s (this run's $%.2f + VP's planned $%.2f)" % (rwhy, a.today, a.vp_planned))
    if not room_ok:
        print("STOP: no room under the day cap; nothing was called. Check again later; no cap is raised.")
        return 3
    V1.prompt_ok()
    start = spent()
    budget = Budget(min(LINE_CAP, start + a.today), spent, role_lines, S.check_cap)
    _raw, metered = clients()
    client = budget.wrap(metered)
    for q, s in todo:
        lk = left["%s/%s" % (q, s)]["likely_usd"]
        if spent() - start + lk > a.today:
            print("  %s %-10s not started: this run has spent $%.2f; + likely $%.2f passes today's $%.2f"
                  % (q, s, spent() - start, lk, a.today))
            break
        text, fmt = capture(q, s)
        w = work(q, s)
        if w.exists():                                   # an interrupted answer starts again from nothing
            w.rename(w.with_name(w.name + ".interrupted-%s" % datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")))
        fl = FormatLog()
        try:
            res = P.check(text, w, client, fmt, s, net=fl.net(), before_call=budget.before_call)
        except P.Stop as e:
            print("  %s %-10s STOPPED: %s (the answer is not kept; it runs again from the start)" % (q, s, e))
            break
        (w / "results.json").write_text(json.dumps({"question": q, "system": s, "at": R.now(), "format": fmt,
                                                    **res, "fetches": fl.rows}, indent=1, ensure_ascii=False,
                                                   default=str))
        print("  %s %-10s %6.1f s  %s%s" % (q, s, res["seconds"], res["summary"],
                                           "  (%d over_limit call(s))" % len(res["over_limit"])
                                           if res["over_limit"] else ""))
    why = counter_blind(spent(), role_lines())
    if why:
        print("STOP: " + why)
        return 4
    print("%s spent: $%.4f of $%.0f; %d of %d answers done" % (
        ISSUE, spent(), LINE_CAP, sum((work(q, s) / "results.json").exists() for q, s in sample()), len(sample())))
    return 0


# -- the comparison (stage 1: every bar but agreement) -------------------------------------------------------------

def dist(xs: list[float]) -> dict:
    """Every answer's figure, median, minimum, maximum, mean, and the mean without the largest answer (§16.3)."""
    xs = sorted(xs)
    n = len(xs)
    return {"n": n, "values": [round(x, 4) for x in xs], "mean": round(sum(xs) / n, 4) if n else None,
            "median": round((xs[(n - 1) // 2] + xs[n // 2]) / 2, 4) if n else None,
            "min": xs[0] if n else None, "max": xs[-1] if n else None,
            "mean_without_largest": round(sum(xs[:-1]) / (n - 1), 4) if n > 1 else None}


def answer_usd(res: dict) -> float:
    return round(sum(r.get("usd") or 0 for r in res["results"]) + sum(r.get("usd_reread") or 0 for r in res["results"])
                 + sum(j.get("usd") or 0 for j in res["jobs"]), 6)


def compare() -> dict:
    """§10.7's bars, counted as v4-v7 count them (R4.bars; COULDN'T CHECK includes NOT FOUND; a passage is a quote
    under 60 words on a BACKED or NOT BACKED verdict), on all 18 answers; agreement waits for stage 2."""
    done = [(q, s) for q, s in sample() if (work(q, s) / "results.json").exists()]
    if len(done) != len(sample()):
        raise P.Stop("%d of %d answers run: a partial set is not analysed" % (len(done), len(sample())))
    per, reasons, n_claims, nf, passages, held = [], {}, 0, 0, [0, 0], []
    for q, s in done:
        res = json.loads((work(q, s) / "results.json").read_text())
        held.append((res, res.get("fetches") or []))
        rows = res["results"]
        cc = 0
        for r in rows:
            if r["label"] == P.COULDNT:
                reasons[r.get("reason_kind") or "?"] = reasons.get(r.get("reason_kind") or "?", 0) + 1
                cc += 1
            nf += r["label"] == P.NOT_FOUND
            cc += r["label"] == P.NOT_FOUND
            if r["label"] in JUDGED:
                passages[0] += 1
                pg = r.get("passage") or {}
                passages[1] += bool(pg.get("quote")) and (pg.get("words") or 99) < 60
        n_claims += len(rows)
        per.append({"answer": "%s/%s" % (q, s), "claims": len(rows), "found": res.get("found"),
                    "totals": V5.totals(rows), "couldnt_check_share": round(cc / len(rows), 4) if rows else None,
                    "usd": answer_usd(res), "seconds": res["seconds"], "seconds_windows": res["seconds_windows"],
                    "over_limit_calls": len(res["over_limit"])})
    n = len(per)
    cc_n = sum(reasons.values())
    cc = {"n": cc_n + nf, "of": n_claims, "share": round((cc_n + nf) / n_claims, 4) if n_claims else None,
          "couldnt_check": cc_n, "not_found_in_passages_checked": nf, "reasons": reasons}
    usd_total = sum(p["usd"] for p in per)
    secs = [p["seconds"] for p in per]
    no_agreement = {"share": None}
    pass_bar = R4.bars(cc, n, no_agreement, tuple(passages), usd_total, sum(secs) / n)
    pass_bar.pop("agreement_at_least_90")
    return {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. The fresh set, stage 1 (pilot doc §16.9): v8 end to end on 18 answers no version has "
                 "seen. Agreement is stage 2 (judging), not approved; this file decides only whether stage 2 may be "
                 "asked for. Judged by AI models only; no human has checked the judgements.",
        "design": "docs/whu-check-an-answer-pilot.md §15, §16", "ledger_issue": ISSUE, "answers": n,
        "claims": n_claims, "estimator": P.ESTIMATOR, "batched_prompt_sha256": V6.batched_prompt_sha(),
        "couldnt_check": cc, "passages": {"verdicts": passages[0], "with_passage": passages[1]},
        "usd": {"total": round(usd_total, 4), "per_answer": round(usd_total / n, 4), "ledger": round(spent(), 4)},
        "distributions": {"usd": dist([p["usd"] for p in per]), "seconds": dist(secs),
                          "couldnt_check_share": dist([p["couldnt_check_share"] or 0 for p in per]),
                          "note": "each mean is also shown without the largest answer (§16.3); the bars are judged "
                                  "on all answers"},
        "over_limit_calls": sum(p["over_limit_calls"] for p in per),
        "by_held_format": by_format(held),
        "pass_bar": pass_bar, "agreement": "stage 2 (judging) not approved; not computed",
        "stop_rule": "§16.9 item 2: if cost or time fails, stop; no judging",
        "per_answer": per}


def do_compare(_a) -> int:
    out = compare()
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("answers", "claims", "couldnt_check", "passages", "usd", "distributions",
                                          "over_limit_calls", "by_held_format", "pass_bar")}, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("q")
    b.add_argument("system", choices=SYSTEMS)
    b.add_argument("meta")
    sub.add_parser("verify")
    sub.add_parser("prepare")
    r = sub.add_parser("run")
    r.add_argument("--today", type=float, required=True, help="what this run may spend today (room rule)")
    r.add_argument("--vp-planned", type=float, default=0.0)
    sub.add_parser("compare")
    a = ap.parse_args()
    return {"build": do_build, "verify": do_verify, "prepare": do_prepare, "run": do_run,
            "compare": do_compare}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
