"""
Step 0 — does a narrow question get answered more consistently than a broad one,
and does the residue tell us how to ask it better?

WHY THIS RUNS BEFORE ANYTHING IS BUILT
--------------------------------------
The two-reading design rests on one untested assumption: that classifying a
single claim against a stated proposition is more stable than judging forty
claims holistically. Plausible. Unproven. If claims move between `supports` and
`opposes` across runs, the design is wrong, and it is far cheaper to learn that
here than after a migration.

It tests a second thing at the same time, because the two cannot be separated:
a bad proposition produces unstable classification no matter how good the
classifier is. So the run also measures the RESIDUE — claims that come back
`unclear`, claims that are mostly `context`, and claims whose label changes
between runs — and then asks what distinction the proposition is missing.

That residue is the refinement signal. If a revised proposition shrinks it, the
loop is real: the engine can propose better questions from its own failures,
with a human approving each revision. If the residue does not shrink, either
the signal is not there or reframing does not help, and that is worth knowing
before it becomes a schema.

STRICTLY READ-ONLY. No database writes. One local JSON report.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    # generate a proposition, classify 3x, diagnose the residue
    python scripts/signal/step0_proposition.py \
        --issue-slug social-media-teen-mental-health --category depression_anxiety

    # supply your own proposition instead of generating one
    python scripts/signal/step0_proposition.py ... --proposition "Social media use causes ..."

    # also test whether the suggested revision shrinks the residue
    python scripts/signal/step0_proposition.py ... --test-revision
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc
from signal_model import MODEL, prompt_version, warn_if_unpinned
from topic_config import get_topic

REPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "signal"
BATCH = 25
LABELS = ("supports", "opposes", "context", "unclear")


# ---------------------------------------------------------------------------
# Prompts — local to this experiment, deliberately not shared with production
# ---------------------------------------------------------------------------

def proposition_prompt(topic: dict, category: str) -> str:
    return f"""You are defining the question a body of evidence is meant to answer.

Topic: {topic['title']}
Context: {topic['prompt_detail']}
Category: {category}

Write ONE proposition that the claims in this category bear on. It must be:
- FALSIFIABLE — evidence could in principle show it false
- SPECIFIC — a reader can tell what would count for and against it
- SINGULAR — one claim, not two joined by "and"
- NEUTRAL — not phrased to favour either answer

Be careful with causal language. "causes" and "is associated with" are different
propositions, and evidence for one is not evidence for the other. Choose the one
this evidence actually speaks to.

If the disagreement in this category is not empirical at all — if it turns on
which outcome to prioritise, or on a value judgement no amount of evidence
settles — say so instead of forcing a proposition.

Return JSON only:
{{"proposition": "...", "is_values_question": false, "note": "one line on why this framing"}}"""


def classify_prompt(proposition: str) -> str:
    return f"""You are labelling individual evidence claims against one proposition.

PROPOSITION: {proposition}

For EACH claim, return exactly one label:
- "supports" — if true, this claim makes the proposition more likely
- "opposes"  — if true, this claim makes the proposition less likely
- "context"  — true and relevant background, but bears on the proposition neither
               way. Prevalence figures, definitions, descriptions of practice.
- "unclear"  — you cannot tell, or the claim is ambiguous relative to this
               proposition. USE THIS HONESTLY. A high unclear count tells us the
               proposition is badly framed, which is information we want.

Judge each claim ON ITS OWN. Do not balance the labels, do not aim for a
distribution, and do not let earlier claims influence later ones.

Return JSON only — an array, one object per claim, every id echoed back:
[{{"id": "<claim id>", "label": "supports|opposes|context|unclear", "why": "at most 12 words"}}]"""


def reframe_prompt(proposition: str) -> str:
    return f"""A proposition was used to label evidence claims. Some claims could not be
labelled, or were labelled inconsistently across repeated runs.

CURRENT PROPOSITION: {proposition}

Below are the claims that did not classify cleanly. They are the evidence that
the question is framed wrongly — read them as a group and find what they have in
common.

Ask specifically: is there a DISTINCTION these claims turn on that the
proposition fails to make? Common cases: conflating causation with association;
conflating a population effect with an individual one; leaving the outcome or
the exposure undefined; bundling two questions into one.

If the residue has no common structure and is just miscellaneous, say so — do
not invent a pattern.

HOW TO RESPOND WHEN A DISTINCTION IS MISSING — this matters, and every attempt
so far has got it wrong. A missing distinction almost always means there are TWO
questions, not one badly-worded question. Do NOT resolve it by writing a longer
proposition.

- revised_proposition must be SINGULAR. One claim. NEVER two joined by "and",
  "though", "while", "with", or a subordinate clause carrying a second claim.
  Measured: compound revisions classify WORSE than the original.
- Do NOT broaden. Adding "varies by context" or "effects differ by subgroup"
  absorbs every claim and asks nothing. Measured: one such revision cut unclear
  from 15% to 6% while cutting the share of evidence able to CONTRADICT it from
  26% to 15%. It looked like an improvement and was the worst question tried.
- If the distinction calls for two questions — which it usually does — set
  revised_proposition to null and put both in splits_into. That is the expected
  answer, not a fallback.
- Only supply revised_proposition when a single word or phrase is genuinely
  wrong ("causes" where the evidence supports "is associated with") and fixing
  it needs no second clause.

Return JSON only:
{{"diagnosis": "2-3 sentences on what the residue has in common, or that it has no common structure",
  "missing_distinction": "the distinction the proposition fails to make, or null",
  "revised_proposition": "a SINGULAR replacement, or null — null is the usual answer",
  "splits_into": ["each a singular, falsifiable proposition", "..."] }}"""


# ---------------------------------------------------------------------------

def classify_once(claims: list[dict], proposition: str, run: int) -> dict[str, str]:
    """One full labelling pass. Returns {claim_id: label}."""
    system = classify_prompt(proposition)
    labels: dict[str, str] = {}

    for start in range(0, len(claims), BATCH):
        batch = claims[start:start + BATCH]
        sent = {str(c["id"]) for c in batch}
        lines = [f'{{"id": "{c["id"]}"}}  {c["claim_text"]}' for c in batch]
        user = "Claims:\n\n" + "\n\n".join(lines)

        print(f"    run {run}: claims {start + 1}-{start + len(batch)} ...", end=" ", flush=True)
        out = mc._call_claude(system, user, max_tokens=4096)
        if not isinstance(out, list):
            print("FAILED")
            continue

        kept = 0
        for row in out:
            if not isinstance(row, dict):
                continue
            cid, label = str(row.get("id", "")), row.get("label")
            # An id we never sent is a hallucination; a label outside the set is
            # a protocol violation. Neither is silently accepted.
            if cid in sent and label in LABELS:
                labels[cid] = label
                kept += 1
        missing = len(sent) - kept
        print(f"{kept} labelled" + (f", {missing} missing" if missing else ""))
        time.sleep(0.4)

    # Anything the model declined to return is unclear by omission, not absent.
    for c in claims:
        labels.setdefault(str(c["id"]), "unclear")
    return labels


def analyse(claims: list[dict], runs: list[dict[str, str]]) -> dict:
    """Per-claim stability and label distribution across K runs."""
    by_claim: dict[str, list[str]] = defaultdict(list)
    for r in runs:
        for cid, label in r.items():
            by_claim[cid].append(label)

    stable, unstable = [], []
    modal: dict[str, str] = {}
    for cid, labels in by_claim.items():
        counts = Counter(labels)
        modal[cid] = counts.most_common(1)[0][0]
        (stable if len(counts) == 1 else unstable).append(cid)

    dist = Counter(modal.values())
    bearing = dist["supports"] + dist["opposes"]
    total = len(modal) or 1
    return {
        # The share of bearing evidence that OPPOSES the proposition. This is a
        # falsifiability measure, and it is the guard against the refinement
        # loop's failure mode: a vaguer proposition absorbs more claims and so
        # shrinks the residue, while asking less. Measured on 26 Aug, a revision
        # cut unclear from 15% to 6% and simultaneously cut the opposing share
        # from 26% to 15% — it bought clarity by becoming harder to contradict.
        # A revision that lowers this is not an improvement, whatever else moved.
        "opposing_share": (dist["opposes"] / bearing) if bearing else 0.0,
        "n_claims": total,
        "agreement": len(stable) / total,
        "stable": stable,
        "unstable": unstable,
        "distribution": dict(dist),
        "bearing_rate": bearing / total,
        "unclear_rate": dist["unclear"] / total,
        "context_rate": dist["context"] / total,
        "modal": modal,
        "per_claim": {cid: by_claim[cid] for cid in by_claim},
    }


def residue_claims(claims: list[dict], a: dict) -> list[dict]:
    """The claims that did not classify cleanly — the refinement signal."""
    ids = set(a["unstable"]) | {cid for cid, m in a["modal"].items() if m == "unclear"}
    return [c for c in claims if str(c["id"]) in ids]


def report_pass(label: str, a: dict) -> None:
    print(f"\n  {label}")
    print(f"    per-claim agreement across runs : {a['agreement']:.0%}  "
          f"({len(a['stable'])}/{a['n_claims']} identical every run)")
    print(f"    labels                          : " +
          "  ".join(f"{k}={a['distribution'].get(k, 0)}" for k in LABELS))
    print(f"    bearing / context / unclear     : "
          f"{a['bearing_rate']:.0%} / {a['context_rate']:.0%} / {a['unclear_rate']:.0%}")
    print(f"    opposing share of bearing       : {a['opposing_share']:.0%}  "
          f"(how falsifiable the proposition is)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue-slug", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--proposition", help="Supply one instead of generating it")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--test-revision", action="store_true",
                    help="Re-classify against the suggested revision and compare residue")
    args = ap.parse_args()

    topic = get_topic(args.issue_slug)
    sb = mc._get_supabase()
    _issue_id, by_category = mc.load_scored_claims(sb, args.issue_slug)
    claims = by_category.get(args.category, [])
    if not claims:
        return print(f"No claims in '{args.category}'. Have: {sorted(by_category)}") or 1

    print(f"\nTopic    : {topic['title']}")
    print(f"Category : {args.category}  ({len(claims)} claims)")
    print(f"Model    : {MODEL}")
    warn_if_unpinned(MODEL)
    print("READ-ONLY — nothing is written to the database.\n")

    # --- the proposition ---------------------------------------------------
    if args.proposition:
        proposition, prop_meta = args.proposition, {"source": "supplied"}
    else:
        print("Writing a proposition...", end=" ", flush=True)
        out = mc._call_claude(proposition_prompt(topic, args.category), "Write the proposition.")
        if not isinstance(out, dict) or not out.get("proposition"):
            return print("FAILED — could not generate a proposition.") or 1
        proposition, prop_meta = out["proposition"], {**out, "source": "generated"}
        print("done")
        if out.get("is_values_question"):
            print("\n  [NOTE] Flagged as a VALUES question, not an empirical one.")
            print(f"         {out.get('note', '')}")

    print(f"\nPROPOSITION\n  {proposition}\n")

    # --- classify K times --------------------------------------------------
    print(f"Classifying {len(claims)} claims, {args.runs} times:")
    runs = [classify_once(claims, proposition, i + 1) for i in range(args.runs)]
    a1 = analyse(claims, runs)
    report_pass("PASS 1", a1)

    if a1["unstable"]:
        print(f"\n    claims whose label CHANGED between runs ({len(a1['unstable'])}):")
        for c in claims:
            cid = str(c["id"])
            if cid in a1["unstable"]:
                print(f"      {' → '.join(a1['per_claim'][cid])}")
                print(f"        {c['claim_text'][:150]}")

    # --- diagnose the residue ---------------------------------------------
    residue = residue_claims(claims, a1)
    revision = None
    if not residue:
        print("\n  No residue — every claim classified cleanly and identically. "
              "Nothing to reframe.")
    else:
        print(f"\nDiagnosing {len(residue)} residue claims...", end=" ", flush=True)
        body = "\n\n".join(f"- {c['claim_text']}" for c in residue)
        revision = mc._call_claude(reframe_prompt(proposition), body)
        print("done")
        if isinstance(revision, dict):
            rp = revision.get("revised_proposition") or ""
            # Compound revisions have been the failure mode on every run so far,
            # so flag conjunctions that USUALLY introduce a second claim. This is
            # a HINT, not a verdict: a keyword scan cannot tell "depression and
            # anxiety symptoms" (one claim, two outcomes) from "X is true and Y
            # is stronger" (two claims). " with " is excluded outright — it is
            # almost always "associated with" or "compared with". A human reads
            # the sentence; this just makes sure they look.
            joins = [w for w in (" though ", " while ", " whereas ", " although ")
                     if w in f" {rp.lower()} "]
            if rp and joins:
                revision["_compound_hint"] = joins
            print(f"\n  DIAGNOSIS\n    {revision.get('diagnosis', '(none)')}")
            if revision.get("missing_distinction"):
                print(f"\n  MISSING DISTINCTION\n    {revision['missing_distinction']}")
            if revision.get("revised_proposition"):
                print(f"\n  SUGGESTED REVISION\n    {revision['revised_proposition']}")
                if revision.get("_compound_hint"):
                    joined = ", ".join(w.strip() for w in revision["_compound_hint"])
                    print(f"    [CHECK] contains \"{joined}\" — read it: is that one claim or two?")
                    print("            Compounds classify worse than either half. Prefer a split.")
                elif revision.get("splits_into"):
                    print("    [CHECK] a split was also offered below — compare them before choosing.")
            for s in revision.get("splits_into") or []:
                print(f"\n  SPLITS INTO\n    - {s}")

    # --- does the revision actually shrink the residue? -------------------
    a2 = None
    if args.test_revision and isinstance(revision, dict) and revision.get("revised_proposition"):
        rev = revision["revised_proposition"]
        print(f"\nRe-classifying against the revision, {args.runs} times:")
        runs2 = [classify_once(claims, rev, i + 1) for i in range(args.runs)]
        a2 = analyse(claims, runs2)
        report_pass("PASS 2 (revised proposition)", a2)

        print("\n  DID THE REVISION HELP?")
        for name, k, better in (("agreement", "agreement", "up"),
                                ("bearing", "bearing_rate", "up"),
                                ("unclear", "unclear_rate", "down"),
                                ("opposing", "opposing_share", "up")):
            d = a2[k] - a1[k]
            arrow = "improved" if (d > 0) == (better == "up") and abs(d) > 0.005 else \
                    "worse" if abs(d) > 0.005 else "unchanged"
            print(f"    {name:10s} {a1[k]:.0%} -> {a2[k]:.0%}   {arrow}")

        # --- the guard --------------------------------------------------
        residue_fell = a2["unclear_rate"] < a1["unclear_rate"] - 0.005
        opposing_fell = a2["opposing_share"] < a1["opposing_share"] - 0.05
        print("\n  VERDICT ON THE REVISION")
        if residue_fell and opposing_fell:
            print("    REJECT. The residue shrank, but the opposing share fell with it:")
            print(f"    {a1['opposing_share']:.0%} -> {a2['opposing_share']:.0%}. The revision absorbed more claims by")
            print("    becoming harder to contradict, not by asking a sharper question.")
            print("    This is the loop optimising toward vagueness. Prefer SPLITTING the")
            print("    question over broadening it.")
        elif residue_fell:
            print("    ACCEPT (pending human review). Residue fell and the proposition")
            print("    remained as falsifiable as before.")
        elif opposing_fell:
            print("    REJECT. Falsifiability fell and the residue did not improve.")
        else:
            print("    NO CHANGE WARRANTED. The revision did not reduce the residue.")

    # --- verdict -----------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("STEP 0 — what this tells you")
    print(f"{'=' * 70}")
    agree = a1["agreement"]
    if agree >= 0.90:
        print(f"Per-claim classification is STABLE ({agree:.0%}). The core assumption")
        print("behind the two-reading design holds for this category.")
    elif agree >= 0.75:
        print(f"Per-claim classification is MARGINAL ({agree:.0%}). Usable, but the")
        print("aggregation thresholds need to tolerate this much movement.")
    else:
        print(f"Per-claim classification is UNSTABLE ({agree:.0%}). The design's core")
        print("assumption does NOT hold here. Do not build on it — reconsider first.")

    if a1["bearing_rate"] < 0.25:
        print(f"\nOnly {a1['bearing_rate']:.0%} of claims bear on the proposition. Either the")
        print("category is mostly background, or the question does not match its evidence.")
    if a1["opposing_share"] < 0.10 and a1["distribution"].get("supports", 0) > 5:
        print(f"\nOnly {a1['opposing_share']:.0%} of bearing claims oppose the proposition. Either the")
        print("question is nearly unfalsifiable as posed, or the claim corpus contains")
        print("no opposing literature — and those need different fixes.")
    if a1["unclear_rate"] > 0.15:
        print(f"\n{a1['unclear_rate']:.0%} unclear — high. Read the diagnosis above; the")
        print("proposition is probably the problem, not the classifier.")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"step0_{args.issue_slug}_{args.category}.json"
    out_path.write_text(json.dumps({
        "topic": args.issue_slug, "category": args.category, "model": MODEL,
        "runs": args.runs,
        "proposition": proposition, "proposition_meta": prop_meta,
        "classify_prompt_version": prompt_version(classify_prompt(proposition)),
        "pass1": {k: v for k, v in a1.items() if k != "per_claim"},
        "per_claim_labels": a1["per_claim"],
        "revision": revision,
        "pass2": ({k: v for k, v in a2.items() if k != "per_claim"} if a2 else None),
    }, indent=2) + "\n")
    print(f"\nReport: {out_path}")
    print("No database rows were written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
