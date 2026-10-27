#!/usr/bin/env python3
"""Scorecard: reader measures from the existing study data (counts only).

    measures.py

Free: no model is called. Writes scorecard/measures.json.

For each system, question and in total, and for each judge separately and
averaged:

  citation fidelity (M1, the sampled claim-like sentences): supported,
    cited but not supported, uncited, as shares of the countable items;
  overstatement (M2): key conclusions labelled Overstates;
  omission (M2): key conclusions labelled Understates or Omits;
  contradiction (M2): key conclusions labelled Contradicts.

RULES. analyse.py's, as analyse_eight.py applies them (results/eight_ai_only.json):
each judge's first-read label after the refusal rule (analyse.per_judge_labels);
Uncited counts in the denominator; Unreachable, INCOMPLETE_SOURCES and
NOT_VERIFIABLE_ABSTRACT are excluded and counted apart, with
NOT_VERIFIABLE_ABSTRACT kept only when EVERY cited snapshot is abstract only
(cross_company.abstract_correct, via analyse_eight.items_m1_every).
"Averaged" is analyse.py's two-judge combined score split by category: each
item counts 1, shared equally among the judges that gave it a countable label
(so an item one judge could not label counts fully under the other). Its
failures equal eight_ai_only.json's combined-view failures; this script checks
that, and each judge's, before writing.

ChatGPT performed no web search on WHU-S05 to WHU-S08 (deviations 2026-10-26):
its totals are given for all eight and for S01-S04 only. Perplexity (exploratory
add-on) has WHU-S01 to WHU-S04 only, from its own run directory
(results/perplexity/analyse_perplexity.rows_from).
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E = _load("analyse_eight_sc", STUDY / "scripts" / "analyse_eight.py")
P = _load("analyse_perplexity_sc", STUDY / "results" / "perplexity" / "analyse_perplexity.py")
A = E.A
J = A.JUDGES
VIEWS = ["claude", "openai", "averaged"]
CITED_FAIL = A.M1_FAIL - {A.UNCITED}
M2_CAT = {"Matches": "matches", "Overstates": "overstates", "Understates": "omits_or_understates",
          "Omits": "omits_or_understates", "Contradicts": "contradicts"}

PRIV = "~/Projects/whu-study-private/scoring"
PROVENANCE = {
    "M1": {
        "items": [PRIV + "/m1/items.json (cited draws)", PRIV + "/m1/uncited.json (uncited draws)",
                  PRIV + "/m1/key_map.json (question, system)"],
        "labels": PRIV + "/m1/replies{,_ext}/<judge>/<item>.json, field 'label' (first read; "
                         "replies_repeat not used, as analyse.py)",
        "rules": "scripts/analyse.py per_judge_labels, M1_PASS/M1_FAIL/M1_EXCL; "
                 "results/machine_only/cross_company.py abstract_correct (EVERY rule)",
        "supported": "label == 'Supported'",
        "cited_not_supported": "label in {Overstates, Understates, Absent, Wrong source, Contradicted}",
        "uncited": "item in uncited.json (label UNCITED for both judges)",
        "excluded": "label in {Unreachable, INCOMPLETE_SOURCES, NOT_VERIFIABLE_ABSTRACT} or no usable "
                    "reply (no source held, refused by both)",
        "n": "supported + cited_not_supported + uncited",
        "check": "results/eight_ai_only.json sets.<set>.M1.views.{combined,claude_judge,openai_judge}"
                 ".systems.<system>.{failures,countable}",
    },
    "M2": {
        "items": [PRIV + "/m2/items.json", PRIV + "/m2/key_map.json"],
        "labels": PRIV + "/m2/replies{,_ext}/<judge>/<item>.json, field 'label' (first read)",
        "rules": "scripts/analyse.py per_judge_labels, M2_PASS/M2_FAIL",
        "overstates": "label == 'Overstates'",
        "omits_or_understates": "label in {Understates, Omits}",
        "contradicts": "label == 'Contradicts'",
        "n": "conclusions with a usable label (matches + the three)",
        "check": "results/eight_ai_only.json sets.<set>.M2.views.{combined,claude_judge,openai_judge}"
                 ".systems.<system>.{failures,countable}",
    },
    "Perplexity": PRIV + "/perplexity/m1 and m2, same fields; checked against results/perplexity/perplexity_ai_only.json M1_citation_support / M2_conclusion_calibration .views.<view>.systems.Perplexity.{failures,countable}",
}


def zero(keys):
    return {v: {k: 0.0 for k in keys} for v in VIEWS}


def add_m1(t, r):
    labs = r["labels"]
    cats = {}
    for j in J:
        lab = labs[j]
        cats[j] = ("uncited" if lab == A.UNCITED else "supported" if lab in A.M1_PASS
                   else "cited_not_supported" if lab in CITED_FAIL else None)
        t[j][cats[j] or "excluded"] += 1
    got = [c for c in cats.values() if c]
    if not got:
        t["averaged"]["excluded"] += 1
    for c in got:
        t["averaged"][c] += 1 / len(got)


def add_m2(t, r):
    cats = {j: M2_CAT.get(r["labels"][j]) for j in J}
    for j in J:
        t[j][cats[j] or "no_usable_label"] += 1
    got = [c for c in cats.values() if c]
    if not got:
        t["averaged"]["no_usable_label"] += 1
    for c in got:
        t["averaged"][c] += 1 / len(got)


M1_KEYS = ["supported", "cited_not_supported", "uncited", "excluded"]
M2_KEYS = ["matches", "overstates", "omits_or_understates", "contradicts", "no_usable_label"]


def finish_m1(t):
    out = {}
    for v in VIEWS:
        c = {k: round(t[v][k], 4) for k in M1_KEYS}
        n = c["supported"] + c["cited_not_supported"] + c["uncited"]
        c["n"] = round(n, 4)
        c["drawn"] = round(n + c["excluded"], 4)
        for k in ("supported", "cited_not_supported", "uncited"):
            c[k + "_share"] = round(c[k] / n, 4) if n else None
        out[v] = c
    return out


def finish_m2(t):
    out = {}
    for v in VIEWS:
        c = {k: round(t[v][k], 4) for k in M2_KEYS}
        n = c["matches"] + c["overstates"] + c["omits_or_understates"] + c["contradicts"]
        c["n"] = round(n, 4)
        for k in ("overstates", "omits_or_understates", "contradicts"):
            c[k + "_share"] = round(c[k] / n, 4) if n else None
        out[v] = c
    return out


def tabulate(m1, m2, systems, qs):
    per = {}
    for s in systems:
        per[s] = {"per_question": {}, "totals": {}}
        for q in qs:
            a, b = zero(M1_KEYS), zero(M2_KEYS)
            for r in m1:
                if r["system"] == s and r["question"] == q:
                    add_m1(a, r)
            for r in m2:
                if r["system"] == s and r["question"] == q:
                    add_m2(b, r)
            if any(a[J[0]].values()) or any(b[J[0]].values()):
                per[s]["per_question"][q] = {"citation_fidelity": finish_m1(a), "conclusions": finish_m2(b)}
    return per


def total(m1, m2, s, qs):
    a, b = zero(M1_KEYS), zero(M2_KEYS)
    for r in m1:
        if r["system"] == s and r["question"] in qs:
            add_m1(a, r)
    for r in m2:
        if r["system"] == s and r["question"] in qs:
            add_m2(b, r)
    return {"questions": qs, "citation_fidelity": finish_m1(a), "conclusions": finish_m2(b)}


def check(out, eight):
    """Failures and countable per judge and averaged must equal eight_ai_only.json's."""
    bad = []
    pairs = {"claude": "claude_judge", "openai": "openai_judge", "averaged": "combined"}
    for set_name, qs in (("all_eight", E.S1 + E.EXT), ("S01-S04", E.S1), ("S05-S08", E.EXT)):
        for s in A.SYSTEMS:
            mine = total(*ROWS, s, qs)
            for v, ev in pairs.items():
                for meas, f_keys in (("M1", ("cited_not_supported", "uncited")),
                                     ("M2", ("overstates", "omits_or_understates", "contradicts"))):
                    ref = eight["sets"][set_name][meas]["views"][ev]["systems"][s]
                    blk = mine["citation_fidelity" if meas == "M1" else "conclusions"][v]
                    f = round(sum(blk[k] for k in f_keys), 4)
                    if abs(f - ref["failures"]) > 1e-3 or abs(blk["n"] - ref["countable"]) > 1e-3:
                        bad.append((set_name, s, meas, v, f, blk["n"], ref["failures"], ref["countable"]))
    return bad


def main() -> int:
    global ROWS
    eight = json.loads((STUDY / "results" / "eight_ai_only.json").read_text())
    qs = E.S1 + E.EXT
    E.configure(qs)
    m1 = E.every_rule(lambda: A.items_m1())
    m2 = A.items_m2()
    ROWS = (m1, m2)
    bad = check(None, eight)
    if bad:
        for b in bad:
            print("MISMATCH", b)
        print("STOP: the measures do not reproduce eight_ai_only.json; nothing written")
        return 1
    pm1, pm2 = P.rows_from(P.PPLX, "Perplexity")
    pref = json.loads((STUDY / "results" / "perplexity" / "perplexity_ai_only.json").read_text())
    mine = total(pm1, pm2, "Perplexity", E.S1)
    for v, ev in (("claude", "claude_judge"), ("openai", "openai_judge"), ("averaged", "combined")):
        for meas, key, _, f_keys in (
                ("M1_citation_support", "citation_fidelity", None, ("cited_not_supported", "uncited")),
                ("M2_conclusion_calibration", "conclusions", None, ("overstates", "omits_or_understates", "contradicts"))):
            ref = pref[meas]["views"][ev]["systems"]["Perplexity"]
            b = mine[key][v]
            if abs(sum(b[k] for k in f_keys) - ref["failures"]) > 1e-3 or abs(b["n"] - ref["countable"]) > 1e-3:
                print("STOP: Perplexity %s %s does not reproduce perplexity_ai_only.json; nothing written" % (meas, v))
                return 1
    out = {
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "Judged by AI models only, not checked by people. Reader measures from the WHU reliability "
                 "study (exploratory presentation of the study's M1 and M2 labels; outside H1 and H2).",
        "script": "study/whu-reliability/scorecard/measures.py",
        "chatgpt_note": "ChatGPT performed no web search on WHU-S05 to WHU-S08 (0 searches, 0 citations; "
                        "deviations 2026-10-26): every one of its S05-S08 sampled sentences is uncited. Its "
                        "totals are given for all eight and for S01-S04 only.",
        "perplexity_note": "Exploratory add-on (perplexity_plan.md): WHU-S01 to WHU-S04 only; compare it with "
                           "the other systems' S01-S04 totals.",
        "views": {"claude": "Claude judge (claude-opus-5-5) alone",
                  "openai": "OpenAI judge (gpt-6-astra) alone",
                  "averaged": "two-judge combined: each item split equally among the judges that labelled it"},
        "denominators": "citation fidelity: n = supported + cited_not_supported + uncited (excluded items "
                        "counted apart); conclusions: n = conclusions with a usable label",
        "provenance": PROVENANCE,
        "reproduces": "failures and n per judge and averaged equal results/eight_ai_only.json "
                      "sets.{all_eight,S01-S04,S05-S08}.{M1,M2}.views.{claude_judge,openai_judge,combined} "
                      "for every system (checked by this script before writing)",
        "systems": tabulate(m1, m2, A.SYSTEMS, qs),
    }
    for s in A.SYSTEMS:
        out["systems"][s]["totals"] = {"all_eight": total(m1, m2, s, qs), "S01-S04": total(m1, m2, s, E.S1),
                                       "S05-S08": total(m1, m2, s, E.EXT)}
    out["systems"]["Perplexity"] = tabulate(pm1, pm2, ["Perplexity"], E.S1)["Perplexity"]
    out["systems"]["Perplexity"]["totals"] = {"S01-S04": total(pm1, pm2, "Perplexity", E.S1)}
    (HERE / "measures.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote", HERE / "measures.json")
    return 0


ROWS = None

if __name__ == "__main__":
    raise SystemExit(main())
