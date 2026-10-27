"""Independent check of the WHU reliability study's analysis on all eight questions.

Written without reading scripts/analyse.py, scripts/analyse_eight.py,
results/machine_only/*.py or anything in results/. Extends check_stage1.py's
method (same label parsing, exclusions, two-judge combination and bootstrap)
to WHU-S01..S08, from the raw judge replies. No model is called.

Reads (PRIVATE, never copied): ~/Projects/whu-study-private/scoring/
  m1/items.json, m1/uncited.json, m1/key_map.json, m1/sources/manifest.json,
  m1/sources/<source_id>.txt (quote check only),
  m1/replies{,_ext}/<judge>/*.json, m1_quotecheck/replies{,_ext}/<judge>/*.json,
  m2/items.json, m2/key_map.json, m2/replies{,_ext}/<judge>/*.json
Writes: check/eight_check.json (counts and rates only; no item ids, no text).

Rules (protocol; deviations.md; machine_only_plan.md), as in check_stage1.py:
  * Per judge, the FIRST-read reply (replies/ for S01-S04, replies_ext/ for
    S05-S08; never *_repeat). The label is re-parsed from the raw reply text.
  * Uncited: failure, weight 1.
  * Unreachable (any cited snapshot "unreachable" in the manifest, or a judge
    label "Unreachable"): excluded.
  * NOT_VERIFIABLE_ABSTRACT: a judge's Absent when EVERY cited snapshot is
    abstract only; that judge's reading is excluded.
  * Too long to send (INCOMPLETE_SOURCES with every source held): excluded.
  * Two judges: mean of the failure indicators; a judge whose reading is
    excluded (abstract, refused twice) leaves the other's label standing.
    In a single judge's view, a twice-refused read takes the other judge's
    label (refusal rule); an abstract-only exclusion stays excluded.
  * WHU-S07's Creutzig 2015 (PMC4443311) is full text: the manifest already
    says so; asserted below, no override.
  * Quote check (spec (a), narrowed to WHU): the re-judge reply's label; a
    Supported with a missing/empty 'evidence' field, or with no passage found
    in the held text of any cited source after normalising whitespace, quote
    marks and dashes (no tag stripping), is a failure ("not demonstrated").
  * Cross-company (spec (b)): WHU and Claude Research by the OpenAI judge,
    ChatGPT by the Claude judge, Gemini by both (combined).
  * Bootstrap over whole questions within the set, 10,000 resamples,
    random.Random(int(freeze hash, 16)); plus the exact bootstrap over all
    n^n ordered resamples, enumerated as multisets with multinomial weights.
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
FREEZE = "5d83e9b8025312923f3fb8ea2d5de3b47c212362"
SEED = int(FREEZE, 16)
N_BOOT = 10_000
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini"]
Q_ALL = [f"WHU-S0{i}" for i in range(1, 9)]
SETS = {"S01-S04": Q_ALL[:4], "S05-S08": Q_ALL[4:], "all_eight": Q_ALL}
EXT = set(Q_ALL[4:])
JUDGES = ["claude", "openai"]
M1_LABELS = {"Supported", "Overstates", "Understates", "Absent", "Wrong source",
             "Contradicted", "Unreachable"}
M2_LABELS = {"Matches", "Overstates", "Understates", "Contradicts", "Omits"}
LANCET = ["10.1016/S0140-6736(23)01231-X", "10.1016/S0140-6736(24)01500-9"]
CROSS = {"WHU": "openai", "Claude": "openai", "ChatGPT": "claude", "Gemini": "combined"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def raw_json(reply):
    """Parsed JSON of the last attempt's raw text; None if refused/unparsable."""
    att = reply.get("attempts") or []
    if not att or att[-1].get("refused"):
        return None
    raw = att[-1].get("raw") or ""
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r'"label"\s*:\s*"([^"]+)"', raw)
        return {"label": m.group(1)} if m else None


def parse_label(reply, allowed):
    obj = raw_json(reply)
    lab = obj.get("label") if isinstance(obj, dict) else None
    return lab if lab in allowed else None


def reply_path(kind, q, judge, iid):
    d = "replies_ext" if q in EXT else "replies"
    return PRIVATE / kind / d / judge / (iid + ".json")


# ---------------------------------------------------------------- quote check

_QUOTES = str.maketrans({c: "'" for c in "‘’‚‛′`´"} |
                        {c: '"' for c in "“”„‟″«»"} |
                        {c: "-" for c in "‐‑‒–—―−﹘﹣－"})


def norm(s):
    return re.sub(r"\s+", " ", s.translate(_QUOTES)).strip()


_TEXT = {}


def held_text(source_id):
    if source_id not in _TEXT:
        p = PRIVATE / "m1/sources" / (source_id + ".txt")
        _TEXT[source_id] = norm(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else ""
    return _TEXT[source_id]


def evidence_list(obj):
    ev = obj.get("evidence") if isinstance(obj, dict) else None
    if isinstance(ev, str):
        ev = [ev]
    if not isinstance(ev, list):
        return []
    out = []
    for e in ev:
        if isinstance(e, dict):
            e = e.get("passage") or e.get("text") or e.get("quote") or ""
        if isinstance(e, str) and e.strip():
            out.append(e)
    return out


# ---------------------------------------------------------------------- M1

def m1_items():
    km = load(PRIVATE / "m1/key_map.json")
    items = {i["item"]: i for i in load(PRIVATE / "m1/items.json")}
    uncited = {i["item"] for i in load(PRIVATE / "m1/uncited.json")}
    by_url = {m["url"]: m for m in load(PRIVATE / "m1/sources/manifest.json")}
    snap = lambda u: by_url.get(u) or by_url.get(u.split("#:~:text=")[0])
    creutzig = [m for u, m in by_url.items() if "PMC4443311" in u]
    assert creutzig and all(m["extent"] == "full text" for m in creutzig)
    out, checks = [], collections.Counter()
    for iid, meta in km.items():
        q, s = meta["question"], meta["system"]
        rec = {"q": q, "sys": s}
        if iid in uncited:
            rec["kind"] = "uncited"
            out.append(rec)
            continue
        it = items[iid]
        snaps = [snap(c["url"]) for c in it["citations"]]
        assert all(snaps), "citation without manifest row"
        rec["lancet"] = q == "WHU-S05" and s == "WHU" and any(
            d.lower() in c["url"].lower() for c in it["citations"] for d in LANCET)
        rec["source_ids"] = sorted({m["source_id"] for m in snaps})
        if any(m["extent"] == "unreachable" for m in snaps):
            rec["kind"] = "unreachable"
            p = reply_path("m1", q, "claude", iid)
            checks["unreachable_no_reply" if not p.exists() else
                   "unreachable_reply_" + str(load(p).get("label"))] += 1
            out.append(rec)
            continue
        all_abs = all(m.get("abstract_only") for m in snaps)
        rec["all_abstract"] = all_abs
        rec["labels"], rec["raw_labels"] = {}, {}
        for j in JUDGES:
            p = reply_path("m1", q, j, iid)
            if not p.exists():
                rec["labels"][j] = "NO_REPLY"
                checks["held_but_no_reply"] += 1
                continue
            r = load(p)
            if r.get("undelivered_sources") or (r.get("label") == "INCOMPLETE_SOURCES"
                                                and not r.get("attempts")):
                rec["labels"][j] = "UNDELIVERED"
                continue
            lab = parse_label(r, M1_LABELS)
            rec["raw_labels"][j] = lab
            if lab is None:
                rec["labels"][j] = "REFUSED_OR_UNPARSED"
            elif lab == "Absent" and all_abs:
                rec["labels"][j] = "NOT_VERIFIABLE_ABSTRACT"
            else:
                rec["labels"][j] = lab
            checks["parsed==judge_label" if lab == r.get("judge_label") else
                   "parsed!=judge_label"] += 1
            checks["mine==stored_label" if rec["labels"][j] == r.get("label") else
                   "mine!=stored_label"] += 1
        labs = set(rec["labels"].values())
        rec["kind"] = ("undelivered" if "UNDELIVERED" in labs else
                       "no_reply" if "NO_REPLY" in labs else "judged")
        if s == "WHU" and rec["kind"] == "judged":
            rec["qc_labels"] = quote_check(q, iid, rec, checks)
        out.append(rec)
    return out, checks


def quote_check(q, iid, rec, checks):
    d = "replies_ext" if q in EXT else "replies"
    labs = {}
    paths = {j: PRIVATE / "m1_quotecheck" / d / j / (iid + ".json") for j in JUDGES}
    if not all(p.exists() for p in paths.values()):
        checks["qc_missing_reply_keeps_first_labels"] += 1
        return dict(rec["labels"])
    for j, p in paths.items():
        r = load(p)
        obj = raw_json(r)
        lab = obj.get("label") if isinstance(obj, dict) else None
        if lab not in M1_LABELS:
            labs[j] = "REFUSED_OR_UNPARSED"
            checks["qc_refused_or_unparsed"] += 1
            continue
        if lab == "Supported":
            ev = evidence_list(obj)
            texts = [held_text(sid) for sid in rec["source_ids"]]
            found = [any(norm(e) and norm(e) in t for t in texts) for e in ev]
            if not ev:
                checks[f"qc_downgrade_missing_evidence_{j}"] += 1
                lab = "NOT_DEMONSTRATED"
            elif not any(found):
                checks[f"qc_downgrade_no_passage_found_{j}"] += 1
                lab = "NOT_DEMONSTRATED"
            elif not all(found):
                checks[f"qc_supported_some_passages_not_found_{j}"] += 1
        if lab == "Absent" and rec["all_abstract"]:
            lab = "NOT_VERIFIABLE_ABSTRACT"
        labs[j] = lab
        checks[f"qc_first_label_{'same' if lab == rec['labels'][j] else 'changed'}"] += 1
    return labs


M1_EXCL = {"NOT_VERIFIABLE_ABSTRACT", "REFUSED_OR_UNPARSED", "Unreachable", "NO_REPLY"}


def m1_score(rec, mode="combined", qc=False):
    """Failure score in [0,1], or None if excluded. mode: combined|claude|openai."""
    k = rec["kind"]
    if k == "uncited":
        return 1.0
    if k != "judged":
        return None
    labs = rec["qc_labels"] if qc and "qc_labels" in rec else rec["labels"]
    if any(v == "Unreachable" for v in labs.values()):
        return None
    if mode != "combined" and labs[mode] == "REFUSED_OR_UNPARSED":
        # refusal rule: a twice-refused read takes the other judge's label
        mode = next(j for j in JUDGES if j != mode)
    js = JUDGES if mode == "combined" else [mode]
    use = [labs[j] for j in js if labs[j] not in M1_EXCL]
    if not use:
        return None
    return sum(0.0 if v == "Supported" else 1.0 for v in use) / len(use)


def cross_mode(sysname):
    return CROSS[sysname]


# ---------------------------------------------------------------------- M2

def m2_items():
    it = load(PRIVATE / "m2/items.json")
    km = load(PRIVATE / "m2/key_map.json")
    out, checks = [], collections.Counter()
    for x in it["items"]:
        a = km[x["answer"]]
        rec = {"q": a["question"], "sys": a["system"], "labels": {}}
        for j in JUDGES:
            r = load(reply_path("m2", rec["q"], j, x["item"]))
            lab = parse_label(r, M2_LABELS)
            rec["labels"][j] = lab or "REFUSED_OR_UNPARSED"
            checks["parsed==judge_label" if lab == r.get("judge_label") else
                   "parsed!=judge_label"] += 1
        out.append(rec)
    return out, checks


def m2_score(rec, mode="combined"):
    if mode != "combined" and rec["labels"][mode] == "REFUSED_OR_UNPARSED":
        mode = next(j for j in JUDGES if j != mode)
    js = JUDGES if mode == "combined" else [mode]
    use = [rec["labels"][j] for j in js if rec["labels"][j] in M2_LABELS]
    if not use:
        return None
    return sum(0.0 if v == "Matches" else 1.0 for v in use) / len(use)


# ------------------------------------------------------------- rates, tests

def tallies(recs, scorer):
    t = collections.defaultdict(lambda: [0.0, 0])
    for r in recs:
        s = scorer(r)
        if s is not None:
            t[(r["q"], r["sys"])][0] += s
            t[(r["q"], r["sys"])][1] += 1
    return t


def rate_counts(t, sysname, counts):
    """counts: {question: multiplicity}"""
    s = sum(c * t[(q, sysname)][0] for q, c in counts.items())
    n = sum(c * t[(q, sysname)][1] for q, c in counts.items())
    return s / n if n else float("nan")


def rate(t, sysname, qs):
    return rate_counts(t, sysname, collections.Counter(qs))


def pct(xs, p):
    xs = sorted(x for x in xs if not math.isnan(x))
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def wpct(vw, p):
    """Percentile of the expanded list of (value, weight) pairs, same
    interpolation as pct() on the list with each value repeated weight times."""
    vw = sorted((v, w) for v, w in vw if not math.isnan(v) and w)
    n = sum(w for _, w in vw)
    if not n:
        return float("nan")
    k = (n - 1) * p
    lo, hi = math.floor(k), math.ceil(k)

    def at(idx):
        c = 0
        for v, w in vw:
            c += w
            if idx < c:
                return v
        return vw[-1][0]
    a, b = at(lo), at(hi)
    return a + (b - a) * (k - lo)


def multisets(qs):
    """All multisets of size len(qs) drawn from qs, with the number of ordered
    resamples giving each (multinomial coefficient)."""
    n = len(qs)
    fact = math.factorial
    for combo in itertools.combinations_with_replacement(range(n), n):
        c = collections.Counter(combo)
        w = fact(n)
        for v in c.values():
            w //= fact(v)
        yield {qs[i]: k for i, k in c.items()}, w


def compare(t, qs, a="WHU", b="Claude"):
    ra, rb = rate(t, a, qs), rate(t, b, qs)
    rng = random.Random(SEED)
    diffs, ratios, undefined = [], [], 0
    for _ in range(N_BOOT):
        smp = [rng.choice(qs) for _ in qs]
        x, y = rate(t, a, smp), rate(t, b, smp)
        diffs.append(x - y)
        if y > 0:
            ratios.append(x / y)
        else:
            undefined += 1
    ed, er = [], []
    total = 0
    for counts, w in multisets(qs):
        x, y = rate_counts(t, a, counts), rate_counts(t, b, counts)
        ed.append((x - y, w))
        total += w
        if y > 0:
            er.append((x / y, w))
    assert total == len(qs) ** len(qs)
    lo, hi = pct(diffs, 0.025), pct(diffs, 0.975)
    r = lambda v: round(100 * v, 2)
    na = sum(t[(q, a)][1] for q in qs)
    nb = sum(t[(q, b)][1] for q in qs)
    return {
        "rate_" + a: r(ra), "n_" + a: na, "rate_" + b: r(rb), "n_" + b: nb,
        "difference_pts": r(ra - rb),
        "difference_95ci_pts": [r(lo), r(hi)],
        "ratio": round(ra / rb, 4) if rb else None,
        "ratio_95ci": [round(pct(ratios, 0.025), 4), round(pct(ratios, 0.975), 4)],
        "ratio_resamples_undefined": undefined,
        "exact_bootstrap_resamples": total,
        "exact_bootstrap_difference_95ci_pts": [r(wpct(ed, 0.025)), r(wpct(ed, 0.975))],
        "exact_bootstrap_ratio_95ci": [round(wpct(er, 0.025), 4), round(wpct(er, 0.975), 4)],
        "half_threshold_met": ra <= 0.5 * rb,
        "interval_excludes_zero_below": hi < 0,
        "exact_interval_excludes_zero_below": wpct(ed, 0.975) < 0,
        "holds": (ra <= 0.5 * rb) and (hi < 0),
    }


def summary(xs):
    xs = [x for x in xs if x is not None]
    return {"rate_pct": round(100 * sum(xs) / len(xs), 2) if xs else None,
            "failure_sum": sum(xs), "n": len(xs)}


def kappa(pairs):
    """Cohen's kappa and raw agreement over (label_a, label_b) pairs."""
    n = len(pairs)
    if not n:
        return {"n": 0}
    po = sum(a == b for a, b in pairs) / n
    ca = collections.Counter(a for a, _ in pairs)
    cb = collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return {"n": n, "agree": sum(a == b for a, b in pairs), "agreement_pct": round(100 * po, 2),
            "kappa": round((po - pe) / (1 - pe), 4) if pe < 1 else None}


# ---------------------------------------------------------------------- main

def main():
    m1, c1 = m1_items()
    m2, c2 = m2_items()
    res = {"freeze_commit": FREEZE, "n_boot": N_BOOT,
           "consistency_checks": {"m1": dict(sorted(c1.items())), "m2": dict(sorted(c2.items()))}}

    in_set = lambda recs, qs: [r for r in recs if r["q"] in qs]

    # ---- M1 composition and rates, per set
    m1_out, m2_out = {}, {}
    for name, qs in SETS.items():
        rs_all = in_set(m1, qs)
        block = {}
        for s in SYSTEMS:
            rs = [r for r in rs_all if r["sys"] == s]
            kinds = collections.Counter(r["kind"] for r in rs)
            cited = len(rs) - kinds["uncited"]
            unr = kinds["unreachable"]
            excluded = sum(1 for r in rs if r["kind"] != "uncited" and m1_score(r) is None)
            b = {
                "sampled": len(rs), "cited": cited, "kinds": dict(kinds),
                "excluded_cited_items": excluded,
                "combined": summary(m1_score(r) for r in rs),
                "cited_only": summary(m1_score(r) for r in rs if r["kind"] != "uncited"),
                "judge_claude": summary(m1_score(r, "claude") for r in rs),
                "judge_openai": summary(m1_score(r, "openai") for r in rs),
                "cross_company": summary(m1_score(r, cross_mode(s)) for r in rs),
                "uncited_share_of_sampled_pct": round(100 * kinds["uncited"] / len(rs), 2) if rs else None,
                "unreachable_items": unr,
                "reachability_of_cited_items_pct": round(100 * (1 - unr / cited), 2) if cited else None,
                "unreachable_flag_over_20pct": (unr / cited > 0.20) if cited else None,
                "labels_by_judge": {j: dict(sorted(collections.Counter(
                    r["labels"][j] for r in rs if r["kind"] == "judged").items())) for j in JUDGES},
            }
            if s == "WHU":
                b["quote_checked_combined"] = summary(m1_score(r, qc=True) for r in rs)
                b["quote_checked_openai"] = summary(m1_score(r, "openai", qc=True) for r in rs)
                b["quote_checked_claude"] = summary(m1_score(r, "claude", qc=True) for r in rs)
                b["quote_checked_labels_by_judge"] = {j: dict(sorted(collections.Counter(
                    r["qc_labels"][j] for r in rs if "qc_labels" in r).items())) for j in JUDGES}
            block[s] = b
        # source-level reachability
        srcs = collections.defaultdict(set)
        by_url = {m["url"]: m for m in load(PRIVATE / "m1/sources/manifest.json")}
        km = load(PRIVATE / "m1/key_map.json")
        for i in load(PRIVATE / "m1/items.json"):
            if km[i["item"]]["question"] not in qs:
                continue
            for c in i["citations"]:
                m = by_url.get(c["url"]) or by_url[c["url"].split("#:~:text=")[0]]
                srcs[km[i["item"]]["system"]].add((m["source_id"], m["extent"]))
        block["source_level"] = {s: {"distinct": len(v),
                                     "unreachable": sum(e == "unreachable" for _, e in v),
                                     "abstract_only": sum(e == "abstract only" for _, e in v)}
                                 for s, v in sorted(srcs.items())}
        m1_out[name] = block

        rs2_all = in_set(m2, qs)
        b2 = {}
        for s in SYSTEMS:
            rs = [r for r in rs2_all if r["sys"] == s]
            b2[s] = {"combined": summary(m2_score(r) for r in rs),
                     "judge_claude": summary(m2_score(r, "claude") for r in rs),
                     "judge_openai": summary(m2_score(r, "openai") for r in rs),
                     "cross_company": summary(m2_score(r, cross_mode(s)) for r in rs),
                     "labels_by_judge": {j: dict(sorted(collections.Counter(
                         r["labels"][j] for r in rs).items())) for j in JUDGES}}
        m2_out[name] = b2
    res["m1"] = m1_out
    res["m2"] = m2_out

    # ---- judge agreement and kappa (first reads, raw parsed labels)
    # Items where both judges returned a parsable label. M1 labels are taken
    # after the abstract-only rule (NOT_VERIFIABLE_ABSTRACT is its own category).
    fail1 = lambda v: v != "Supported"
    fail2 = lambda v: v != "Matches"
    agr = {}
    for name, qs in SETS.items():
        blk = {}
        for s in [None] + SYSTEMS:
            keep = lambda r: r["q"] in qs and (s is None or r["sys"] == s)
            p1 = [(r["labels"]["claude"], r["labels"]["openai"]) for r in m1
                  if keep(r) and r.get("raw_labels") and all(r["raw_labels"].get(j) for j in JUDGES)]
            p2 = [(r["labels"]["claude"], r["labels"]["openai"]) for r in m2
                  if keep(r) and all(r["labels"][j] in M2_LABELS for j in JUDGES)]
            blk[s or "all"] = {
                "m1_labels": kappa(p1),
                "m1_fail_vs_supported": kappa([(fail1(a), fail1(b)) for a, b in p1]),
                "m2_labels": kappa(p2),
                "m2_fail_vs_matches": kappa([(fail2(a), fail2(b)) for a, b in p2]),
            }
        agr[name] = blk
    res["judge_agreement"] = agr

    # ---- tests
    def sc_cross(r):
        return m1_score(r, cross_mode(r["sys"]))

    def sc2_cross(r):
        return m2_score(r, cross_mode(r["sys"]))

    tests = {}
    for name, qs in SETS.items():
        T = {
            "H1_combined": compare(tallies(m1, m1_score), qs),
            "H2_combined": compare(tallies(m2, m2_score), qs),
            "H1_judge_claude": compare(tallies(m1, lambda r: m1_score(r, "claude")), qs),
            "H1_judge_openai": compare(tallies(m1, lambda r: m1_score(r, "openai")), qs),
            "H2_judge_claude": compare(tallies(m2, lambda r: m2_score(r, "claude")), qs),
            "H2_judge_openai": compare(tallies(m2, lambda r: m2_score(r, "openai")), qs),
            "H1_cross_company": compare(tallies(m1, sc_cross), qs),
            "H2_cross_company": compare(tallies(m2, sc2_cross), qs),
            # WHU quote-checked against Claude Research as originally labelled
            "H1_quote_checked_combined": compare(tallies(
                m1, lambda r: m1_score(r, qc=r["sys"] == "WHU")), qs),
            "H1_quote_checked_cross_company": compare(tallies(
                m1, lambda r: m1_score(r, cross_mode(r["sys"]), qc=r["sys"] == "WHU")), qs),
        }

        def sens_excluded(r):
            if r["sys"] == "WHU" and r["kind"] != "uncited" and m1_score(r) is None:
                return 1.0
            return m1_score(r)

        def sens_lancet(r):
            if r.get("lancet"):
                return 1.0
            return m1_score(r)
        whu = [r for r in in_set(m1, qs) if r["sys"] == "WHU"]
        T["sens_i_all_excluded_WHU_as_failures"] = {
            "excluded_WHU_items": sum(1 for r in whu if r["kind"] != "uncited" and m1_score(r) is None),
            "WHU_rate": summary(sens_excluded(r) for r in whu),
            "H1": compare(tallies(m1, sens_excluded), qs)}
        T["sens_ii_lancet_items_as_failures"] = {
            "lancet_items": sum(1 for r in whu if r.get("lancet")),
            "lancet_items_already_excluded": sum(1 for r in whu if r.get("lancet") and m1_score(r) is None),
            "WHU_rate": summary(sens_lancet(r) for r in whu),
            "H1": compare(tallies(m1, sens_lancet), qs)}
        tests[name] = T
    res["tests_WHU_vs_Claude"] = tests

    (HERE / "eight_check.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
