"""Independent check of the WHU reliability study's Stage 1 analysis.

Written without reading scripts/analyse.py or results/. Works only from
docs/whu-reliability-protocol.md, study/whu-reliability/deviations.md, the raw
judge replies, the sampling log and the snapshot manifests.

Reads (PRIVATE, never copied): ~/Projects/whu-study-private/scoring/
  m1/items.json, m1/uncited.json, m1/key_map.json, m1/sources/manifest.json,
  m1/replies/<judge>/*.json, m2/items.json, m2/key_map.json,
  m2/replies/<judge>/*.json
Writes: check/stage1_check.json (aggregate numbers only; no item ids, no text).

Label rules (protocol M1/M2 tables and rulings; deviations.md row 45):
  * Per judge, the FIRST-read reply (replies/, not replies_repeat/). The label
    is re-parsed from the raw reply text, not taken from the stored label.
  * M1 Unreachable: any cited source whose snapshot extent is "unreachable" in
    the sources manifest (protocol: "An item whose cited source has no
    snapshot is recorded as INCOMPLETE_SOURCES and is not judged"), or a judge
    label "Unreachable". Excluded from the rate.
  * M1 NOT_VERIFIABLE_ABSTRACT: judge says Absent and every cited snapshot is
    abstract only (the protocol: "If the snapshot holds only an abstract").
    Excluded from that judge's reading. The runner's stored labels apply it
    when ANY cited snapshot is abstract only; that reading is reported as a
    sensitivity (sens_abstract_any_rule).
  * M1 undelivered (held but not sent whole; deviations row 49): excluded,
    counted apart.
  * Uncited (sampled with no marker): failure, weight 1 for both judges.
  * Combining two judges (row 45): the item scores the mean of the two judges'
    failure indicators (0, 0.5, 1). A judge whose reading is excluded
    (NOT_VERIFIABLE_ABSTRACT, refusal twice) leaves the other judge's label
    standing alone (the protocol's refusal rule); excluded only if both are.
    A sensitivity with "excluded if either" is also reported.
  * Rates are pooled over a system's items (sum of scores / items scored).
  * Bootstrap: 10,000 resamples of the 4 questions with replacement, paired
    across systems, random.Random(int(freeze hash, 16)). Percentile 95%.
    With 4 questions there are only 256 equally likely resamples, so the exact
    bootstrap distribution is also enumerated.
  * Decision: WHU rate <= 0.5 x Claude rate AND difference interval upper < 0.
"""
import collections
import itertools
import json
import math
import random
import re
from pathlib import Path

PRIVATE = Path.home() / "Projects" / "whu-study-private" / "scoring"
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
FREEZE = "5d83e9b8025312923f3fb8ea2d5de3b47c212362"
SEED = int(FREEZE, 16)
N_BOOT = 10_000
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini"]
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
JUDGES = ["claude", "openai"]
M1_LABELS = {"Supported", "Overstates", "Understates", "Absent", "Wrong source",
             "Contradicted", "Unreachable"}
M2_LABELS = {"Matches", "Overstates", "Understates", "Contradicts", "Omits"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def parse_label(reply, allowed):
    """Label from the raw text of the last attempt; None if refused/unparsable."""
    att = reply.get("attempts") or []
    if not att or att[-1].get("refused"):
        return None
    raw = att[-1].get("raw") or ""
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        lab = json.loads(s).get("label")
    except Exception:
        m = re.search(r'"label"\s*:\s*"([^"]+)"', raw)
        lab = m.group(1) if m else None
    return lab if lab in allowed else None


def m1_items(abstract_rule=all):
    km = load(PRIVATE / "m1/key_map.json")
    items = {i["item"]: i for i in load(PRIVATE / "m1/items.json")}
    uncited = {i["item"] for i in load(PRIVATE / "m1/uncited.json")}
    man = load(PRIVATE / "m1/sources/manifest.json")
    by_url = {m["url"]: m for m in man}
    out, checks = [], collections.Counter()
    for iid, meta in km.items():
        rec = {"q": meta["question"], "sys": meta["system"]}
        if iid in uncited:
            rec["kind"] = "uncited"
            out.append(rec)
            continue
        it = items[iid]
        snaps = [by_url.get(c["url"]) or by_url.get(c["url"].split("#:~:text=")[0])
                 for c in it["citations"]]
        assert all(snaps), iid
        if any(s["extent"] == "unreachable" for s in snaps):
            rec["kind"] = "unreachable"
            # cross-check: either no reply, or the runner's INCOMPLETE_SOURCES
            p = PRIVATE / "m1/replies/claude" / (iid + ".json")
            checks["unreachable_no_reply" if not p.exists() else
                   "unreachable_reply_" + load(p)["label"]] += 1
            out.append(rec)
            continue
        all_abs = abstract_rule(s.get("abstract_only") for s in snaps)
        rec["labels"] = {}
        for j in JUDGES:
            p = PRIVATE / "m1/replies" / j / (iid + ".json")
            if not p.exists():
                rec["labels"][j] = "NO_REPLY"
                checks["held_but_no_reply"] += 1
                continue
            r = load(p)
            if r.get("undelivered_sources") or (r["label"] == "INCOMPLETE_SOURCES"
                                                and not r.get("attempts")):
                rec["labels"][j] = "UNDELIVERED"
                continue
            lab = parse_label(r, M1_LABELS)
            if lab is None:
                rec["labels"][j] = "REFUSED_OR_UNPARSED"
            elif lab == "Absent" and all_abs:
                rec["labels"][j] = "NOT_VERIFIABLE_ABSTRACT"
            else:
                rec["labels"][j] = lab
            # compare with the runner's own stored fields
            checks["parsed==judge_label" if lab == r.get("judge_label") else
                   "parsed!=judge_label"] += 1
            checks["mine==stored_label" if rec["labels"][j] == r.get("label") else
                   "mine!=stored_label"] += 1
        labs = set(rec["labels"].values())
        rec["kind"] = "undelivered" if "UNDELIVERED" in labs else "judged"
        out.append(rec)
    return out, checks


M1_EXCL = {"NOT_VERIFIABLE_ABSTRACT", "REFUSED_OR_UNPARSED", "Unreachable", "NO_REPLY"}


def m1_score(rec, mode="combined", either_excludes=False):
    """Return failure score in [0,1], or None if excluded. mode: combined|claude|openai."""
    k = rec["kind"]
    if k == "uncited":
        return 1.0
    if k != "judged":
        return None
    labs = rec["labels"]
    if any(v == "Unreachable" for v in labs.values()):
        return None
    js = JUDGES if mode == "combined" else [mode]
    use = [labs[j] for j in js if labs[j] not in M1_EXCL]
    if not use or (either_excludes and len(use) < len(js)):
        return None
    return sum(0.0 if v == "Supported" else 1.0 for v in use) / len(use)


def m2_items():
    it = load(PRIVATE / "m2/items.json")
    km = load(PRIVATE / "m2/key_map.json")
    out, checks = [], collections.Counter()
    for x in it["items"]:
        a = km[x["answer"]]
        rec = {"q": a["question"], "sys": a["system"], "labels": {}}
        for j in JUDGES:
            r = load(PRIVATE / "m2/replies" / j / (x["item"] + ".json"))
            lab = parse_label(r, M2_LABELS)
            rec["labels"][j] = lab or "REFUSED_OR_UNPARSED"
            checks["parsed==judge_label" if lab == r.get("judge_label") else
                   "parsed!=judge_label"] += 1
        out.append(rec)
    return out, checks


def m2_score(rec, mode="combined"):
    js = JUDGES if mode == "combined" else [mode]
    use = [rec["labels"][j] for j in js if rec["labels"][j] in M2_LABELS]
    if not use:
        return None
    return sum(0.0 if v == "Matches" else 1.0 for v in use) / len(use)


def tallies(recs, scorer):
    """{(q, sys): [sum, n]}"""
    t = collections.defaultdict(lambda: [0.0, 0])
    for r in recs:
        s = scorer(r)
        if s is not None:
            t[(r["q"], r["sys"])][0] += s
            t[(r["q"], r["sys"])][1] += 1
    return t


def rate(t, sysname, qs):
    s = sum(t[(q, sysname)][0] for q in qs)
    n = sum(t[(q, sysname)][1] for q in qs)
    return s / n if n else float("nan")


def pct(xs, p):
    xs = sorted(x for x in xs if not math.isnan(x))
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def compare(t, a="WHU", b="Claude"):
    ra, rb = rate(t, a, QUESTIONS), rate(t, b, QUESTIONS)
    rng = random.Random(SEED)
    diffs, ratios, undefined = [], [], 0
    for _ in range(N_BOOT):
        qs = [rng.choice(QUESTIONS) for _ in QUESTIONS]
        x, y = rate(t, a, qs), rate(t, b, qs)
        diffs.append(x - y)
        if y > 0:
            ratios.append(x / y)
        else:
            undefined += 1
    # exact bootstrap: all 4^4 ordered resamples, equally likely
    ed, er = [], []
    for qs in itertools.product(QUESTIONS, repeat=4):
        x, y = rate(t, a, qs), rate(t, b, qs)
        ed.append(x - y)
        if y > 0:
            er.append(x / y)
    lo, hi = pct(diffs, 0.025), pct(diffs, 0.975)
    holds = (ra <= 0.5 * rb) and (hi < 0)
    r = lambda v: round(100 * v, 2)
    return {
        "rate_" + a: r(ra), "rate_" + b: r(rb),
        "difference_pts": r(ra - rb),
        "difference_95ci_pts": [r(lo), r(hi)],
        "ratio": round(ra / rb, 4) if rb else None,
        "ratio_95ci": [round(pct(ratios, 0.025), 4), round(pct(ratios, 0.975), 4)],
        "ratio_resamples_undefined": undefined,
        "exact_bootstrap_difference_95ci_pts": [r(pct(ed, 0.025)), r(pct(ed, 0.975))],
        "exact_bootstrap_ratio_95ci": [round(pct(er, 0.025), 4), round(pct(er, 0.975), 4)],
        "half_threshold_met": ra <= 0.5 * rb,
        "interval_excludes_zero_below": hi < 0,
        "holds": holds,
    }


def main():
    m1, c1 = m1_items()
    m2, c2 = m2_items()
    res = {"freeze_commit": FREEZE, "n_boot": N_BOOT, "consistency_checks": {
        "m1": dict(c1), "m2": dict(c2)}}

    # composition
    comp = {}
    for s in SYSTEMS:
        rs = [r for r in m1 if r["sys"] == s]
        kc = collections.Counter(r["kind"] for r in rs)
        lab = {j: dict(collections.Counter(r["labels"][j] for r in rs if r["kind"] == "judged"))
               for j in JUDGES}
        cited = len(rs) - kc["uncited"]
        comp[s] = {"sampled": len(rs), "kinds": dict(kc), "labels_by_judge": lab,
                   "cited": cited}
    res["m1_composition"] = comp

    # M1 rates
    m1r = {}
    for s in SYSTEMS:
        rs = [r for r in m1 if r["sys"] == s]
        comb = [m1_score(r) for r in rs]
        comb = [x for x in comb if x is not None]
        cited_only = [m1_score(r) for r in rs if r["kind"] == "judged"]
        cited_only = [x for x in cited_only if x is not None]
        unc = comp[s]["kinds"].get("uncited", 0)
        unr = comp[s]["kinds"].get("unreachable", 0)
        m1r[s] = {
            "failure_rate_pct": round(100 * sum(comb) / len(comb), 2), "n": len(comb),
            "failure_sum": sum(comb),
            "cited_only_failure_rate_pct": round(100 * sum(cited_only) / len(cited_only), 2),
            "cited_only_n": len(cited_only),
            "uncited_share_of_sampled_pct": round(100 * unc / len(rs), 2),
            "uncited_share_of_rate_denominator_pct": round(100 * unc / len(comb), 2),
            "unreachable_items": unr,
            "unreachable_share_of_cited_items_pct": round(100 * unr / comp[s]["cited"], 2),
            "reachability_of_cited_items_pct": round(100 * (1 - unr / comp[s]["cited"]), 2),
            "unreachable_flag_over_20pct": unr / comp[s]["cited"] > 0.20,
        }
        for j in JUDGES:
            xs = [m1_score(r, j) for r in rs]
            xs = [x for x in xs if x is not None]
            m1r[s]["judge_" + j + "_failure_rate_pct"] = round(100 * sum(xs) / len(xs), 2)
            m1r[s]["judge_" + j + "_n"] = len(xs)
        xs = [m1_score(r, either_excludes=True) for r in rs]
        xs = [x for x in xs if x is not None]
        m1r[s]["sens_either_excludes_failure_rate_pct"] = round(100 * sum(xs) / len(xs), 2)
    res["m1_rates"] = m1r

    # source-level reachability (distinct sources each system's cited items cite)
    man = {m["url"]: m for m in load(PRIVATE / "m1/sources/manifest.json")}
    km = load(PRIVATE / "m1/key_map.json")
    srcs = collections.defaultdict(set)
    for i in load(PRIVATE / "m1/items.json"):
        for c in i["citations"]:
            m = man.get(c["url"]) or man[c["url"].split("#:~:text=")[0]]
            srcs[km[i["item"]]["system"]].add((m["source_id"], m["extent"]))
    res["source_level"] = {s: {"distinct": len(v), "unreachable": sum(e == "unreachable" for _, e in v),
                               "unreachable_pct": round(100 * sum(e == "unreachable" for _, e in v) / len(v), 2)}
                           for s, v in srcs.items()}

    # M2 rates
    m2r = {}
    for s in SYSTEMS:
        rs = [r for r in m2 if r["sys"] == s]
        xs = [m2_score(r) for r in rs]
        m2r[s] = {"failure_rate_pct": round(100 * sum(xs) / len(xs), 2), "n": len(xs),
                  "failure_sum": sum(xs),
                  "labels_by_judge": {j: dict(collections.Counter(r["labels"][j] for r in rs)) for j in JUDGES}}
        for j in JUDGES:
            ys = [m2_score(r, j) for r in rs]
            m2r[s]["judge_" + j + "_failure_rate_pct"] = round(100 * sum(ys) / len(ys), 2)
    res["m2_rates"] = m2r

    # Bootstrap + decision
    t1 = tallies(m1, m1_score)
    t2 = tallies(m2, m2_score)
    res["H1_M1_WHU_vs_Claude"] = compare(t1)
    res["H2_M2_WHU_vs_Claude"] = compare(t2)
    res["H4_secondary"] = {f"M1_WHU_vs_{b}": compare(t1, "WHU", b) for b in ["ChatGPT", "Gemini"]}
    res["H4_secondary"].update({f"M2_WHU_vs_{b}": compare(t2, "WHU", b) for b in ["ChatGPT", "Gemini"]})
    res["per_judge"] = {j: {"H1": compare(tallies(m1, lambda r, j=j: m1_score(r, j))),
                            "H2": compare(tallies(m2, lambda r, j=j: m2_score(r, j)))} for j in JUDGES}
    res["sens_either_excludes_H1"] = compare(tallies(m1, lambda r: m1_score(r, either_excludes=True)))

    # Sensitivity: unjudged (undelivered) WHU items all failures
    def sens(r):
        if r["kind"] == "undelivered" and r["sys"] == "WHU":
            return 1.0
        return m1_score(r)
    n_und = {s: sum(1 for r in m1 if r["sys"] == s and r["kind"] == "undelivered") for s in SYSTEMS}
    res["sens_undelivered_WHU_as_failures"] = {"undelivered_by_system": n_und, "H1": compare(tallies(m1, sens))}

    # Sensitivity: NOT_VERIFIABLE_ABSTRACT when ANY (not every) cited snapshot is
    # abstract only -- the reading the runner's stored labels follow.
    m1_any, _ = m1_items(any)
    res["sens_abstract_any_rule"] = {
        "m1_failure_rate_pct": {s: round(100 * sum(x for x in xs) / len(xs), 2) for s in SYSTEMS
                                for xs in [[v for v in (m1_score(r) for r in m1_any if r["sys"] == s) if v is not None]]},
        "m1_n": {s: sum(1 for r in m1_any if r["sys"] == s and m1_score(r) is not None) for s in SYSTEMS},
        "H1": compare(tallies(m1_any, m1_score)),
    }

    (HERE / "stage1_check.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
