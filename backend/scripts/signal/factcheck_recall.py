#!/usr/bin/env python3
"""
Recall test for the fact-check gate.

WHY THIS EXISTS
---------------
factcheck_known_errors.json records twenty error classes the gate exists to
catch. factcheck_broken_fixture.html is a copy of the published melanoma
article with instances of those classes seeded back into it. Both were
committed and neither was ever read by anything: the fixture's own header said
"Eight known errors have been reintroduced" and no file recorded which eight,
so it could not be run against.

golden_set.py does this job for Signal's consensus mapping — it turns "the
model quietly started answering differently" into a failing test. The gate had
no equivalent. Four passes over one email is not a measurement of an
instrument; this is.

WHAT IT MEASURES, AND WHAT IT DOES NOT
--------------------------------------
RECALL only: of the seeded errors, how many does the gate find, and does the
role that should find each one find it. A class that goes unfound is the
result — it means the gate is blind to that kind of mistake and the named
role's prompt is what has to change.

It does NOT measure precision. The fixture is full of real errors, so a role
returning many findings here is not thereby wrong. Precision comes from the
adjudication records of real drafts, where a finding can be judged against a
draft believed to be correct.

Costs one run of the selected roles (~6 API calls with search). Writes nothing
except the report file if asked.

Usage:
    cd backend && source venv/bin/activate
    export ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)"

    python scripts/signal/factcheck_recall.py                 # all four roles
    python scripts/signal/factcheck_recall.py --roles INFERENCE
    python scripts/signal/factcheck_recall.py --report recall.json

Exit 0 if every seeded error is found by the role expected to find it, 1 if
any is missed, 2 if the run could not complete.
"""

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # backend/
FIXTURE = ROOT / "tests" / "fixtures" / "factcheck_broken_fixture.html"
EXPECTED = ROOT / "tests" / "fixtures" / "factcheck_broken_fixture.expected.json"

_spec = importlib.util.spec_from_file_location("factcheck_draft",
                                               HERE / "factcheck_draft.py")
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)

ROLES = ("SOURCE", "RECENCY", "ADVOCATE", "INFERENCE")

# A seeded error is FOUND when a role's finding is about the same sentence.
# Containment first, for the case where the role quotes a span of the seeded
# quote or the other way round; then word overlap, because the roles paraphrase
# and a seeded quote spanning a table row will never appear verbatim.
MIN_CONTAINMENT = 24

# Calibrated on hand-written paraphrases of each seeded error, not on real role
# output: fifteen paraphrases that should match scored 0.30 to 1.00, and five
# unrelated findings scored 0.00 to 0.16. 0.28 sits in the gap. Revisit once
# real runs exist — and note the errors are asymmetric. A false FOUND makes the
# gate look better than it is; a false MISS only sends a human to read one more
# finding. Anything between NEAR_MISS and MIN_OVERLAP is printed and counted as
# a miss, so the tie goes against the instrument.
MIN_OVERLAP = 0.28
NEAR_MISS = 0.18


STOP = {
    "the", "and", "that", "this", "with", "for", "from", "was", "were", "are",
    "not", "but", "its", "it's", "than", "which", "what", "when", "how", "has",
    "had", "have", "one", "two", "all", "any", "only", "also", "into", "over",
    "under", "more", "less", "same", "other", "would", "could", "should",
}

# A seeded error is FOUND when a role's finding is about the same sentence.
# Three channels, because the roles report in three different shapes:
#   containment  — the role quoted a span of the seeded sentence, or vice versa
#   words        — the role paraphrased, which ADVOCATE and INFERENCE do
#   figures      — RECENCY reports a study and its newer readout and never
#                  quotes the draft at all; what a stale figure and a staleness
#                  finding always share is the figures themselves
# Figures need TWO in common. One is not evidence: HR 0.510 appears all over
# this draft, and a single shared number would make everything match everything.


def numbers(text: str) -> set:
    """Distinctive numeric tokens: 0.288, 0.906, 37.5%, 1,137."""
    return {t for t in re.findall(r"\d+\.\d+|\d+(?:,\d{3})+|\d+%", text)
            if len(t) > 2}


def words(text: str) -> set:
    return {w for w in fc._norm(text).split() if len(w) > 2 and w not in STOP}


def shingles(text: str) -> set:
    w = [x for x in fc._norm(text).split() if len(x) > 2]
    return set(zip(w, w[1:]))


def similarity(a: str, b: str) -> float:
    na, nb = fc._norm(a), fc._norm(b)
    if not na or not nb:
        return 0.0
    if len(na) >= MIN_CONTAINMENT and na in nb:
        return 1.0
    if len(nb) >= MIN_CONTAINMENT and nb in na:
        return 1.0

    sa, sb = shingles(a), shingles(b)
    pairs = len(sa & sb) / min(len(sa), len(sb)) if sa and sb else 0.0

    wa, wb = words(a), words(b)
    # Discounted: shared content words are weaker evidence than shared phrases.
    single = (len(wa & wb) / min(len(wa), len(wb)) * 0.8) if wa and wb else 0.0

    fa, fb = numbers(a), numbers(b)
    figs = (len(fa & fb) / len(fa)) if len(fa & fb) >= 2 else 0.0

    return max(pairs, single, figs)


def findings_from(role, payload) -> list[dict]:
    """Normalise each role's output into {quote, text} so one matcher fits all."""
    out = []
    if role == "SOURCE":
        verdicts, by_id = payload
        for cid, v in verdicts.items():
            if v.get("verdict") in ("VERIFIED", "INTERNAL"):
                continue
            c = by_id.get(cid, {})
            out.append({
                "quote": c.get("claim") or c.get("figure") or "",
                "text": " ".join(str(x) for x in (
                    c.get("claim"), c.get("figure"), v.get("verdict"),
                    v.get("found_value"), v.get("actual_source"), v.get("note")) if x),
                "severity": v.get("verdict", ""),
            })
    elif role == "RECENCY":
        for s in (payload or {}).get("studies", []) or []:
            if (s.get("status") or "").upper() == "CURRENT":
                continue
            out.append({
                # draft_uses is the readout the draft leans on, which is the
                # closest thing this role produces to a quotation of it.
                "quote": s.get("draft_uses") or s.get("name") or "",
                "text": " ".join(str(x) for x in s.values() if isinstance(x, str)),
                "severity": s.get("status", ""),
            })
    else:                                     # ADVOCATE, INFERENCE
        for f in (payload or []):
            out.append({
                "quote": f.get("quote", ""),
                "text": " ".join(str(x) for x in (
                    f.get("quote"), f.get("objection"), f.get("problem"),
                    f.get("why"), f.get("correct_reading"), f.get("fix")) if x),
                "severity": f.get("severity", ""),
                "class": f.get("class", "UNCLASSIFIED"),
            })
    return out


def assign(seeded: list[dict], found: dict[str, list[dict]]) -> dict[str, tuple]:
    """One finding satisfies at most one seeded error.

    The first version of this scored each seed against every finding
    independently, and the first real run credited a single INFERENCE finding
    about a hazard ratio converted into lives to BOTH the RATIO_AS_LIVES seed
    and the HAZARD_AS_RISK seed, four paragraphs apart. Recall read 12 of 14
    when it was 11. A measurement that flatters the instrument is worse than
    no measurement, because it is believed.

    Highest-scoring pair first, then the finding is spent.
    """
    pairs = []
    for seed in seeded:
        for role, items in found.items():
            for i, f in enumerate(items):
                on_quote = similarity(seed["quote"], f["quote"])
                on_text = similarity(seed["quote"], f["text"])
                score = max(on_quote, min(on_text * 0.55, 0.5))
                if score > 0:
                    pairs.append((score, seed["id"], role, i, f))
    pairs.sort(key=lambda x: -x[0])

    out, spent, blocked = {}, set(), {}
    for score, sid, role, i, f in pairs:
        if sid in out:
            continue
        if (role, i) in spent:
            if sid not in blocked and score >= MIN_OVERLAP:
                blocked[sid] = (role, score, f)
            continue
        out[sid] = (role, score, f)
        spent.add((role, i))
    return out, blocked


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roles", default=",".join(ROLES),
                    help="Comma-separated subset to run. Seeded errors expecting a "
                         "role that was not run are reported as NOT RUN, never as found "
                         "or missed.")
    ap.add_argument("--today", default="2026-08-27",
                    help="Date for the recency sweep. Fixed by default: the fixture is "
                         "a snapshot and the five-year data it ignores was published "
                         "1 June 2026, so a moving date would change what STALE means.")
    ap.add_argument("--report", help="Write the full result here as JSON.")
    args = ap.parse_args()

    for f in (FIXTURE, EXPECTED):
        if not f.exists():
            print(f"[ERROR] Missing: {f}")
            sys.exit(2)

    run = [r.strip().upper() for r in args.roles.split(",") if r.strip()]
    bad = [r for r in run if r not in ROLES]
    if bad:
        print(f"[ERROR] Unknown role(s): {', '.join(bad)}. Known: {', '.join(ROLES)}")
        sys.exit(2)

    key = json.loads(EXPECTED.read_text(encoding="utf-8"))
    seeded = key["seeded"]
    draft = fc.read_draft(FIXTURE)

    print(f"\nRecall test · {len(seeded)} seeded errors · roles: {', '.join(run)}")
    print(f"{FIXTURE.name} ({len(draft):,} chars of prose), as of {args.today}\n")

    found: dict[str, list[dict]] = {}
    if "SOURCE" in run:
        print("[SOURCE] extracting claims and auditing...")
        claims = fc.extract_claims(draft)
        if claims is None:
            print("[ERROR] Claim extraction failed. An unrun check is not a result.")
            sys.exit(2)
        verdicts = fc.audit_sources(claims, FIXTURE.name)
        found["SOURCE"] = findings_from("SOURCE", (verdicts, {c["id"]: c for c in claims}))
    if "RECENCY" in run:
        found["RECENCY"] = findings_from("RECENCY", fc.sweep_recency(draft, args.today))
    if "ADVOCATE" in run:
        found["ADVOCATE"] = findings_from("ADVOCATE", fc.advocate(draft))
    if "INFERENCE" in run:
        found["INFERENCE"] = findings_from("INFERENCE", fc.inference(draft))

    matched, blocked = assign([s for s in seeded if s["expect"] in run], found)

    results, hits, misses, notrun = [], 0, 0, 0
    for seed in seeded:
        want = seed["expect"]
        if want not in run:
            verdict = "NOT RUN"
            notrun += 1
            role, score, f = "", 0.0, None
        else:
            role, score, f = matched.get(seed["id"], ("", 0.0, None))
            if score >= MIN_OVERLAP and role == want:
                verdict, hits = "FOUND", hits + 1
            elif score >= MIN_OVERLAP:
                verdict, hits = "FOUND BY ANOTHER ROLE", hits + 1
            elif score >= NEAR_MISS:
                verdict, misses = "NEAR MISS — read it", misses + 1
            else:
                verdict, misses = "MISSED", misses + 1
        results.append({**seed, "verdict": verdict, "matched_role": role,
                        "score": round(score, 2),
                        "matched_quote": (f or {}).get("quote", ""),
                        "matched_severity": (f or {}).get("severity", ""),
                        "matched_class": (f or {}).get("class", "")})

    print("\n" + "=" * 72)
    print(f"RECALL   {hits} of {len(seeded) - notrun} found"
          + (f" · {notrun} not run" if notrun else ""))
    print("=" * 72)
    for r in results:
        print(f"\n  [{r['verdict']}] {r['class']} — expect {r['expect']}")
        print(f"     seeded  : {r['quote'][:110]}")
        if r["verdict"] == "NOT RUN":
            continue
        if r["matched_quote"]:
            print(f"     {r['matched_role']:<9}: {r['matched_quote'][:110]}"
                  f"  ({r['matched_severity']}, {r['score']})")
        else:
            print("     nothing came close.")
        if r["id"] in blocked:
            brole, bscore, bf = blocked[r["id"]]
            print(f"     a {brole} finding scoring {bscore:.2f} was already counted for")
            print(f"     another seeded error: {bf.get('quote','')[:80]}")
            print("     Read it. If that finding is genuinely about both faults, this one")
            print("     is found; if it is about the other sentence, this one is missed.")
        if r["verdict"] != "FOUND":
            print(f"     why it matters: {r['why_it_is_wrong'][:150]}")

    mislabelled = [r for r in results
                   if r["verdict"].startswith("FOUND") and r["matched_class"] == "CALIBRATION"]
    if mislabelled:
        print("\n" + "=" * 72)
        print(f"MISLABELLED  {len(mislabelled)} seeded error(s) found but called CALIBRATION")
        print("=" * 72)
        print("\n  Every error in this fixture would require a published correction.")
        print("  A blocking class called CALIBRATION does not block, so this is the")
        print("  failure mode that would let a real error publish. It matters more")
        print("  than a miss: a miss is silence, this is a false all-clear.")
        for r in mislabelled:
            print(f"\n  {r['class']} — {r['quote'][:90]}")
            print(f"     the gate called it CALIBRATION via {r['matched_role']}")

    by_class = {}
    for r in results:
        if r["verdict"] == "NOT RUN":
            continue
        by_class.setdefault(r["class"], []).append(r["verdict"].startswith("FOUND"))
    blind = sorted(c for c, v in by_class.items() if not any(v))
    if blind:
        print("\n" + "=" * 72)
        print("BLIND SPOTS — no instance of these classes was found")
        print("=" * 72)
        for c in blind:
            print(f"  {c}")
        print("\n  This is the result. Change the prompt for the role that owns each")
        print("  class, then run this again. A class the gate cannot see will not")
        print("  announce itself on a real draft.")

    # What the measurement cost. factcheck_draft records usage on every API
    # response and this script drives those same roles, so the numbers are
    # already collected -- they were simply never written down here. A test you
    # cannot price is a test nobody schedules: on 2026-08-28 the answer to "how
    # much does it cost to check the checker" was unknown, which is why it had
    # been run once in its life.
    print(fc.format_usage())

    if args.report:
        Path(args.report).write_text(json.dumps({
            "fixture": str(FIXTURE), "roles_run": run, "today": args.today,
            "found": hits, "missed": misses, "not_run": notrun,
            "mislabelled": [r["id"] for r in mislabelled],
            "blind_classes": blind, "results": results,
            "usage": fc.usage_summary(),
            "recall_brief": {r: sorted(set(re.findall(r"^- ([A-Z][A-Z0-9_]+)",
                                                      fc.recall_brief(r), re.M)))
                             for r in run},
            "raw": {k: v for k, v in found.items()},
        }, indent=2), encoding="utf-8")
        print(f"\nFull result written to {args.report}")

    print("")
    if mislabelled:
        print(f"MISLABELLED — {len(mislabelled)} seeded error(s) found but not blocking.")
        sys.exit(1)
    if misses:
        print(f"INCOMPLETE — {misses} seeded error(s) not found by the expected role.")
        sys.exit(1)
    if notrun:
        print(f"PARTIAL — every seeded error in the roles run was found; "
              f"{notrun} await the roles not run.")
        sys.exit(0)
    print("COMPLETE — every seeded error found.")
    sys.exit(0)


if __name__ == "__main__":
    main()
