#!/usr/bin/env python3
"""The fresh set, stage 2: the two M1 judges on the frozen-sample sentences v8 judged (docs/whu-check-an-answer-
pilot.md §16.3, §16.9; advisor ruling and Fred's line "fresh-set stage 2", 2026-11-04).

    fresh_judge.py scope                       once, before any judging: the scope, written and never redrawn
    fresh_judge.py snapshot                    free: prepare_scoring.py snapshot on the scoped items (snapshot.py)
    fresh_judge.py routes [IDS]                free: retrieve_sources.py routes (a) to (c) for unreachable sources
    fresh_judge.py estimate                    free: likely and worst; STOP if likely passes the line
    fresh_judge.py run --today X [--vp-planned Y]   PAID, ledger issue whu-check-fresh-judge (line cap $80):
                                               judge_m1.py, both judges, first reads only; room rule; resumes
    fresh_judge.py agree                       counts: the three agreements with CIs over answers, disagreements

SCOPE (decided before any judging, ruling item 2). The frozen sample's M1 items (fresh_samples.py, efaf6de) whose
sentence is among v8's checked claims with the same text and whose v8 label is BACKED or NOT BACKED: agreement is
undefined elsewhere. Uncited items are not M1 items. The scoped run root (private) holds m1/items.json and
m1/key_map.json for those items only, so the study's code runs on them unchanged.

JUDGES. judge_m1.py as the study and round 1 ran it (M1 prompt, both judges, its refusal, abstract-only, length and
incomplete-sources rules), with --consistency-share 0: each judge reads each item once.

ESTIMATE. Priced from round 1's measured first reads (scoring/quarterly/round1/m1/replies, both judges, 217 items):
per item usd = A + B x its cited sources' tokens, each source's tokens = its characters / round 1's measured
characters per token, capped at judge_m1.MAX_SOURCE_TOKENS (a longer source is chunked to that). Chosen before the
fresh sources were snapshotted. Held out by question on round 1 (each question priced from the other three):
$130.55 against $126.79 measured (1.030); a flat mean per item gave 1.004. Worst: every call at judge_m1's own
worst (all input at Claude's cache-write price or OpenAI's input price, plus each judge's output ceiling), with
tokens at 1.9 characters per token.

AGREEMENT (§16.3, ruling item 3). A judge's label is mapped by pipeline.study_label_to_check; a pair counts where
both v8 and the judge give BACKED or NOT BACKED. Three figures: v8 against the Claude judge (the bar), against the
OpenAI judge, and on the sentences where the two judges agree. Each with a 95% interval over answers: a seeded
bootstrap that resamples the answers (each with all its pairs), so sentences from one answer are not treated as
independent. Disagreements are listed by direction (v8 BACKED / judge not supported, and the reverse).
Private: ~/Projects/whu-study-private/check_fresh_set/scoring/stage2/ (replies, pairs.json). Committed: counts and
the disagreements' item ids only, fresh_judge_counts.json; no sentence or source text.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fresh_samples as FS  # noqa: E402
import run_fresh_v8 as F  # noqa: E402

V1, R, R5, S = F.V1, F.R, F.R5, F.S
ISSUE = "whu-check-fresh-judge"
LINE_CAP = 80.0                                  # "fresh-set stage 2", outside the phase (2026-11-04)
JUDGES = ("claude", "openai")
ROOT2 = F.OUT / "scoring" / "stage2"             # private: m1/{items,key_map,uncited}.json, sources/, replies/
RUN = ROOT2 / "m1"
LOG2 = HERE / "fresh_set" / "scoring" / "stage2"  # committed: hashes and counts only
SCOPE = LOG2 / "scope.json"
COUNTS = HERE / "fresh_judge_counts.json"
JUDGE_M1 = FS.SCRIPTS / "judge_m1.py"
ROUND1_M1 = R.PRIVATE / "scoring" / "quarterly" / "round1" / "m1"
FRESH_M1 = FS.RUN_ROOT / "m1"
PROMPT_TOKENS_WORST = 2500                       # the M1 prompt around the documents, generously
BOOT, BOOT_SEED = 10000, 20261104


def _load_judge():
    return FS._load("judge_m1_fresh", JUDGE_M1)


def sentence_texts(q: str, s: str) -> dict[int, str]:
    f = FS.RUN_ROOT / "blinded" / q / ("%s.sentences.jsonl" % s.lower())
    return {r["idx"]: r["text"] for r in (json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x)}


def v8_rows(q: str, s: str) -> dict[int, dict]:
    return {r["idx"]: r for r in json.loads((F.work(q, s) / "results.json").read_text())["results"]}


def draw_scope() -> dict:
    """Every frozen-sample item, classified; the scope is the v8-judged ones."""
    km = json.loads((FRESH_M1 / "key_map.json").read_text())
    uncited = {r["item"] for r in json.loads((FRESH_M1 / "uncited.json").read_text())}
    why, scope, cache = {}, [], {}
    for item, k in sorted(km.items()):
        q, s, idx = k["question"], k["system"], int(k["sentence"].rsplit("/", 1)[1])
        if (q, s) not in cache:
            cache[q, s] = (sentence_texts(q, s), v8_rows(q, s))
        texts, rows = cache[q, s]
        r = rows.get(idx)
        if item in uncited:
            why[item] = "uncited (not an M1 item)"
        elif r is None:
            why[item] = "not among v8's checked claims"
        elif r["claim"] != texts.get(idx):
            why[item] = "v8's claim text differs from the sampled sentence"
        elif r["label"] not in F.JUDGED:
            why[item] = "v8 " + r["label"]
        else:
            why[item] = "in scope: v8 " + r["label"]
            scope.append(item)
    return {"scope": scope, "why": why, "key_map": km}


def do_scope(_a) -> int:
    if SCOPE.exists():
        raise SystemExit("%s exists: the scope is decided once, before any judging" % SCOPE)
    if any((RUN / "replies").glob("*/*.json")):
        raise SystemExit("a judge reply exists: the scope must be decided before any judging")
    if not FS.FROZEN.exists():
        raise SystemExit("the frozen sample is missing")
    d = draw_scope()
    items = [it for it in json.loads((FRESH_M1 / "items.json").read_text()) if it["item"] in set(d["scope"])]
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (RUN / "key_map.json").write_text(json.dumps({i: d["key_map"][i] for i in d["scope"]}, indent=1))
    (RUN / "uncited.json").write_text("[]")
    counts, per = {}, {}
    for item, w in d["why"].items():
        counts[w] = counts.get(w, 0) + 1
        k = d["key_map"][item]
        if item in d["scope"]:
            a = "%s/%s" % (k["question"], k["system"])
            per[a] = per.get(a, 0) + 1
    LOG2.mkdir(parents=True, exist_ok=True)
    SCOPE.write_text(json.dumps({
        "written": R.now(), "by": "study/whu-reliability/check_pilot/fresh_judge.py scope",
        "rule": "frozen-sample M1 items whose sentence v8 checked with the same text and judged BACKED or NOT BACKED "
                "(advisor ruling 2026-11-04, item 2); decided before any judging",
        "frozen_sample_sha256": hashlib.sha256(FS.FROZEN.read_bytes()).hexdigest(),
        "items": len(d["scope"]), "scope_sha256": hashlib.sha256("\n".join(d["scope"]).encode()).hexdigest(),
        "classified": dict(sorted(counts.items())), "per_answer": dict(sorted(per.items()))}, indent=1) + "\n")
    print("SCOPE: %d items -> %s" % (len(d["scope"]), RUN))
    for w, n in sorted(counts.items()):
        print("  %-55s %d" % (w, n))
    return 0


def prep():
    """fresh_samples' prepare_scoring, pointed at the scoped run root (snapshot, snapshot report)."""
    if not SCOPE.exists():
        raise SystemExit("no scope: run fresh_judge.py scope first")
    ps = FS.prep()
    ps.SCORING, ps.LOG = ROOT2, LOG2
    return ps


def do_snapshot(_a) -> int:
    return prep().do_snapshot(None)


def do_routes(a) -> int:
    rs = FS._load("retrieve_sources_fresh", FS.SCRIPTS / "retrieve_sources.py")
    rs.RUN = RUN
    rows = json.loads((RUN / "sources" / "manifest.json").read_text())
    ids = a.ids or ",".join(r["source_id"] for r in rows if r["extent"] == "unreachable")
    if not ids:
        print("  no unreachable source")
        return 0
    sys.argv = ["retrieve_sources.py", "--only", ids]
    rc = rs.main()
    prep().snapshot_report()
    return rc


# -- the free estimate ----------------------------------------------------------------------------------------------

def held_chars(it: dict, man: dict) -> list[int] | None:
    """Characters of each cited source held; None if any cited work is not held (judge_m1: INCOMPLETE_SOURCES, no
    call)."""
    out = []
    for c in it["citations"]:
        m = man.get(c.get("url") or "")
        if not m or m["extent"] == "unreachable" or not m.get("text_chars"):
            return None
        out.append(m["text_chars"])
    return out


def round1_rates() -> dict:
    """Round 1's measured first reads: characters per token (Claude's measured input on unchunked items) and the
    fit usd = A + B x capped source tokens per item, both judges together."""
    J = _load_judge()
    items = {i["item"]: i for i in json.loads((ROUND1_M1 / "items.json").read_text())}
    man = {r["url"]: r for r in json.loads((ROUND1_M1 / "sources" / "manifest.json").read_text())}
    reps = {j: {} for j in JUDGES}
    for j in JUDGES:
        for f in glob.glob(str(ROUND1_M1 / "replies" / j / "*.json")):
            r = json.loads(Path(f).read_text())
            if r.get("attempts"):
                reps[j][r["item"]] = r
    ratios = []
    for i, r in reps["claude"].items():
        ch = held_chars(items[i], man)
        u = r["attempts"][0]["usage"]
        t = (u.get("input") or 0) + (u.get("cache_write") or 0) + (u.get("cache_read") or 0)
        if ch and t and not any(d.get("chunked") for d in r.get("sources") or []):
            ratios.append(sum(ch) / t)
    cpt = st.median(ratios)
    rows = []
    for i in set(reps["claude"]) & set(reps["openai"]):
        ch = held_chars(items[i], man) or []
        x = sum(min(c / cpt, J.MAX_SOURCE_TOKENS) for c in ch)
        rows.append((x, sum(a["usd"] for j in JUDGES for a in reps[j][i]["attempts"])))
    mx, my = st.mean(x for x, _ in rows), st.mean(y for _, y in rows)
    b = sum((x - mx) * (y - my) for x, y in rows) / sum((x - mx) ** 2 for x, _ in rows)
    return {"chars_per_token": cpt, "usd_per_item": my - b * mx, "usd_per_source_token": b, "items": len(rows),
            "measured_usd": round(sum(y for _, y in rows), 4)}


def estimate() -> dict:
    J = _load_judge()
    rates = round1_rates()
    items = json.loads((RUN / "items.json").read_text())
    man = {r["url"]: r for r in json.loads((RUN / "sources" / "manifest.json").read_text())}
    pc, po = S.PRICES[J.CLAUDE_MODEL], J.OPENAI_PRICE
    likely = worst = 0.0
    called = not_held = 0
    for it in items:
        ch = held_chars(it, man)
        if ch is None:
            not_held += 1
            continue
        called += 1
        likely += rates["usd_per_item"] + rates["usd_per_source_token"] * sum(
            min(c / rates["chars_per_token"], J.MAX_SOURCE_TOKENS) for c in ch)
        n_in = sum(min(c / 1.9, J.MAX_SOURCE_TOKENS) for c in ch) + PROMPT_TOKENS_WORST
        worst += 2 * ((n_in * pc["cache_write"] + J.CLAUDE_MAX_OUT * pc["output"])
                      + (n_in * po["input"] + J.OPENAI_MAX_OUT * po["output"])) / 1e6     # a refusal's one retry
    return {"at": R.now(), "items": len(items), "judged": called, "not_held": not_held,
            "likely_usd": round(likely, 4), "worst_usd": round(worst, 4), "rates": rates}


def do_estimate(_a) -> int:
    est = estimate()
    (ROOT2 / "estimate.json").write_text(json.dumps(est, indent=1))
    left = LINE_CAP - spent()
    print("ESTIMATE: %d items, %d with every cited source held (judged by both judges), %d not held (no call); "
          "likely $%.2f, worst $%.2f (round 1's measured first reads: $%.4f per item + $%.3g per source token, %.2f "
          "characters per token)" % (est["items"], est["judged"], est["not_held"], est["likely_usd"],
                                     est["worst_usd"], est["rates"]["usd_per_item"],
                                     est["rates"]["usd_per_source_token"], est["rates"]["chars_per_token"]))
    if est["likely_usd"] > left:
        print("STOP: likely $%.2f passes what is left on the line ($%.2f of $%.0f); no judging" % (
            est["likely_usd"], left, LINE_CAP))
        return 5
    print("GATE: likely $%.2f within $%.2f left of $%.0f" % (est["likely_usd"], left, LINE_CAP))
    return 0


# -- the paid run ---------------------------------------------------------------------------------------------------

def spent(entries=None) -> float:
    return sum(e.get("usd") or 0 for e in (S.entries() if entries is None else entries) if e.get("issue") == ISSUE)


def do_run(a) -> int:
    est_f = ROOT2 / "estimate.json"
    if not est_f.exists():
        print("STOP: no estimate; run fresh_judge.py estimate first; nothing was called")
        return 4
    est = json.loads(est_f.read_text())
    done = {p.stem for j in JUDGES for p in (RUN / "replies" / j).glob("*.json")} if (RUN / "replies").exists() else set()
    left_share = est["likely_usd"] * (1 - len(done) / max(1, est["items"]))
    print("ESTIMATE: likely $%.2f, worst $%.2f (%s); about $%.2f left to judge" % (
        est["likely_usd"], est["worst_usd"], est["at"], left_share))
    if spent() + left_share > LINE_CAP:
        print("STOP: spent $%.2f + likely $%.2f passes the $%.0f line; nothing was called" % (spent(), left_share,
                                                                                         LINE_CAP))
        return 5
    room_ok, why = R5.room(a.today + a.vp_planned, R5.today_total(), float(S.caps()["default_per_day"]))
    print("ROOM: %s (this run's $%.2f + VP's planned $%.2f)" % (why, a.today, a.vp_planned))
    if not room_ok:
        print("STOP: no room under the day cap; nothing was called. Check again later; no cap is raised.")
        return 3
    cap = min(LINE_CAP, spent() + a.today)
    cmd = [sys.executable, str(JUDGE_M1), str(RUN), "--cap", "%.4f" % cap, "--judges", ",".join(JUDGES),
           "--ledger-issue", ISSUE, "--consistency-share", "0"]
    print("RUN: judge_m1.py --cap %.2f (spent $%.2f + today's $%.2f, at most the $%.0f line), first reads only"
          % (cap, spent(), a.today, LINE_CAP))
    rc = subprocess.run(cmd).returncode
    print("%s spent: $%.4f of $%.0f" % (ISSUE, spent(), LINE_CAP))
    return rc


# -- agreement ------------------------------------------------------------------------------------------------------

def judge_label(item: str, judge: str) -> tuple[str | None, str | None]:
    f = RUN / "replies" / judge / (item + ".json")
    if not f.exists():
        return None, None
    raw = json.loads(f.read_text())["label"]
    return raw, V1.study_label_to_check(raw)


def share(pairs: list[dict], key: str) -> dict:
    both = [p for p in pairs if p[key] in F.JUDGED]
    agree = sum(p[key] == p["v8"] for p in both)
    return {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None}


def interval(pairs: list[dict], key: str) -> list[float] | None:
    """95% percentile interval of the pooled share, resampling answers (each with all its pairs)."""
    by = {}
    for p in pairs:
        if p[key] in F.JUDGED:
            by.setdefault(p["answer"], []).append(p[key] == p["v8"])
    answers = sorted(by)
    if len(answers) < 2:
        return None
    rnd, out = random.Random(BOOT_SEED), []
    for _ in range(BOOT):
        pick = [rnd.choice(answers) for _ in answers]
        n = sum(len(by[x]) for x in pick)
        out.append(sum(sum(by[x]) for x in pick) / n)
    out.sort()
    return [round(out[int(0.025 * BOOT)], 4), round(out[int(0.975 * BOOT) - 1], 4)]


def directions(pairs: list[dict], key: str) -> dict:
    rows = [p for p in pairs if p[key] in F.JUDGED and p[key] != p["v8"]]
    pick = lambda v8: [{"answer": p["answer"], "item": p["item"], "sentence": p["idx"], "judge_raw": p[key + "_raw"]}
                       for p in rows if p["v8"] == v8]
    return {"v8 BACKED, judge NOT BACKED": pick(F.P.BACKED), "v8 NOT BACKED, judge BACKED": pick(F.P.NOT_BACKED)}


def not_judged(pairs: list[dict]) -> dict:
    """Items a judge did not judge (no call): count, ids, which judge, and each source's length, from the reply's
    undelivered sources and the source manifest (advisor ruling, 2026-11-04). They are excluded from every agreement
    the judge's label enters and counted as such."""
    man = {r["source_id"]: r for r in json.loads((RUN / "sources" / "manifest.json").read_text())}
    rows, by_label = [], {}
    for p in pairs:
        judges = [j for j in JUDGES if p[j] not in F.JUDGED]
        for j in judges:
            by_label.setdefault(j, {}).setdefault(str(p[j + "_raw"]), 0)
            by_label[j][str(p[j + "_raw"])] += 1
        if not judges:
            continue
        srcs = {}
        for j in judges:
            r = json.loads((RUN / "replies" / j / (p["item"] + ".json")).read_text())
            toks = {d["source_id"]: d.get("tokens") for d in r.get("sources") or [] if isinstance(d, dict)}
            for u in (r.get("undelivered_sources") or []) + (r.get("unreachable_sources") or []):
                sid = u.get("source_id")
                srcs.setdefault(sid or u.get("url"), {
                    "source_id": sid, "url": u.get("url"), "text_chars": (man.get(sid) or {}).get("text_chars"),
                    "tokens": toks.get(sid), "why": u.get("why") or "unreachable", "judges": []})["judges"].append(j)
        rows.append({"item": p["item"], "answer": p["answer"], "sentence": p["idx"], "v8": p["v8"],
                     "judges": judges, "labels": {j: p[j + "_raw"] for j in judges}, "sources": list(srcs.values())})
    return {"items": len(rows), "ids": [r["item"] for r in rows], "by_judge_label": by_label, "detail": rows,
            "rule": "excluded from each agreement whose judge did not judge the item (and from two-judge-agreed if "
                    "either did not); counted here, never imputed"}


def agree() -> dict:
    km = json.loads((RUN / "key_map.json").read_text())
    pairs, missing = [], []
    for item, k in sorted(km.items()):
        q, s, idx = k["question"], k["system"], int(k["sentence"].rsplit("/", 1)[1])
        r = v8_rows(q, s)[idx]
        c_raw, c = judge_label(item, "claude")
        o_raw, o = judge_label(item, "openai")
        if c_raw is None or o_raw is None:
            missing.append(item)
        both = c if c in F.JUDGED and c == o else None
        pairs.append({"answer": "%s/%s" % (q, s), "item": item, "idx": idx, "v8": r["label"], "claude": c,
                      "claude_raw": c_raw, "openai": o, "openai_raw": o_raw, "two_judges": both,
                      "two_judges_raw": c_raw if both else None})
    if missing:
        raise F.P.Stop("%d of %d scoped items have no reply from both judges: a partial set is not analysed"
                       % (len(missing), len(km)))
    out = {}
    for key, name in (("claude", "vs_claude_judge"), ("openai", "vs_openai_judge"), ("two_judges", "two_judge_agreed")):
        out[name] = {**share(pairs, key), "ci95_over_answers": interval(pairs, key),
                     "disagreements": directions(pairs, key)}
    for v in out.values():
        v["disagreement_counts"] = {d: len(x) for d, x in v["disagreements"].items()}
    labels = lambda key: dict(sorted({str(p[key + "_raw"]): 0 for p in pairs}.items()))
    raw_counts = {}
    for key in ("claude", "openai"):
        c = labels(key)
        for p in pairs:
            c[str(p[key + "_raw"])] += 1
        raw_counts[key] = c
    bar = F.R3.PASS_AGREEMENT
    ready_parts = {k: (v["share"] is not None and v["share"] >= bar) for k, v in out.items()}
    v8c = json.loads(F.COUNTS.read_text())
    coverage = v8c["pass_bar"]["couldnt_check_at_most_20"]
    return {
        "written": R.now(), "by": "study/whu-reliability/check_pilot/fresh_judge.py agree",
        "label": "Counts only. The fresh set, stage 2 (pilot doc §16.9): v8 against the two M1 judges, first reads "
                 "only, on the frozen-sample sentences v8 judged BACKED or NOT BACKED. Judged by AI models only; no "
                 "human has checked the judgements. Blinding was partial: writing style allowed a model to identify "
                 "systems, and WHU's scope notes were left in.",
        "ledger_issue": ISSUE, "usd": round(spent(), 4), "scope_items": len(pairs),
        "judge_labels": raw_counts,
        "not_judged": not_judged(pairs),
        "agreement": out,
        "ci_method": "seeded bootstrap (%d resamples, seed %d) over the answers, each resampled with all its pairs; "
                     "95%% percentile interval" % (BOOT, BOOT_SEED),
        "bar": {"agreement_at_least": bar, **{k + "_at_least_90": v for k, v in ready_parts.items()},
                "couldnt_check_at_most_20 (stage 1)": coverage},
        "ready": all(ready_parts.values()) and coverage,
        "ready_rule": "all three agreements >= 90% and the coverage bar (COULDN'T CHECK <= 20%); the coverage bar "
                      "failed in stage 1 (27.9%), so the tool is not ready whatever the agreements"}, pairs


def do_agree(_a) -> int:
    out, pairs = agree()
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    (ROOT2 / "pairs.json").write_text(json.dumps(pairs, indent=1))
    nj = out["not_judged"]
    print("NOT JUDGED: %d item(s), excluded and counted: %s" % (nj["items"], ", ".join(
        "%s (%s; %s)" % (r["item"], "+".join(r["judges"]), "; ".join(
            "%s chars, %s tokens" % (x["text_chars"], x["tokens"]) for x in r["sources"])) for r in nj["detail"])))
    row = F.log_estimate("fresh-set stage 2 (judging)", ISSUE, json.loads((ROOT2 / "estimate.json").read_text()),
                         out["usd"])
    print("ESTIMATE vs ACTUAL: $%.2f vs $%.2f, ratio %s (%s)" % (
        row["estimate_usd"], row["actual_usd"], row["ratio"], "out of sample" if row["out_of_sample"] else "IN SAMPLE"))
    for k, v in out["agreement"].items():
        print("%-18s %3d of %3d = %s  CI %s  %s" % (k, v["agree"], v["n"], v["share"], v["ci95_over_answers"],
                                                  v["disagreement_counts"]))
    print("READY: %s (%s)" % (out["ready"], out["ready_rule"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("scope", "snapshot", "estimate", "agree"):
        sub.add_parser(c)
    r = sub.add_parser("routes")
    r.add_argument("ids", nargs="?")
    r = sub.add_parser("run")
    r.add_argument("--today", type=float, required=True, help="what this run may spend today (room rule)")
    r.add_argument("--vp-planned", type=float, default=0.0)
    a = ap.parse_args()
    return {"scope": do_scope, "snapshot": do_snapshot, "routes": do_routes, "estimate": do_estimate,
            "run": do_run, "agree": do_agree}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
