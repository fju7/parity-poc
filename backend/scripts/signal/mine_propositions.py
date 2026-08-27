"""
Step 1 — what falsifiable propositions can a corpus actually settle?

WHY
---
These topics were commissioned as subject headings: "Breast Cancer Therapies",
"Diet and Breast Cancer Risk", "Health Impacts of Climate Change". A subject
collects everything ABOUT itself. A proposition collects only what could change
its answer. The audit of 2026-08-27 measured the difference:

    topic                         bears on no category the topic asks
    mmr-vaccine-autism                    2%     (one falsifiable question)
    car-t-cell-therapy                    2%
    social-media-teen-mental-health       7%
    breast-cancer-therapies              18%
    health-impacts-of-climate-change     26%     (a subject, no question)

and the misplacement it found survived a source-context control: shown the
passage each claim came from, the model changed its answer for 8 of 207 claims.
The categories are not mislabelled. They are the wrong shape.

The seam is visible in a single claim. "The 5-year relative survival rate across
all stages is approximately 90%" belongs squarely under a heading called
survival_outcomes if that heading means "how long do patients live", and belongs
nowhere if it means "do these therapies extend life". One heading, two
questions, and the claims split along the seam depending on which one is being
answered on a given call. That is the same fault as social-media/methodology,
whose side attribution inverts between two mirror-image readings.

So: rather than sorting claims into headings that are themselves the problem,
ask what the evidence could settle, and measure how much of it bears on each
answer.

WHAT IT DOES
------------
1. PROPOSE. Reads the claims in large batches and asks for candidate
   propositions each batch's evidence could settle — stated so they could be
   false.
2. MERGE. Collapses the candidates into one deduplicated set.
3. MAP. Puts every claim to every proposition at once and records which ones it
   supports or opposes, K times.
4. REPORT. Per proposition: how much evidence bears on it, how it divides, and
   whether that division held across runs — reusing map_consensus.classify_sides
   so a near-tie is not mistaken for an instability. Plus the RESIDUE: claims
   bearing on nothing proposed, which is the share of a subject-heading corpus
   that was never evidence in the first place.

A proposition with a lot of evidence bearing on it and a stable division is an
issue. One with a lot of evidence and no division is settled, and worth saying
so. One with little evidence is not yet a story.

STRICTLY READ-ONLY. No database writes. One local JSON report.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/mine_propositions.py --issue-slug breast-cancer-therapies --dry-run
    python scripts/signal/mine_propositions.py --issue-slug breast-cancer-therapies
    python scripts/signal/mine_propositions.py --issue-slug glp1-drugs --category pricing
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import map_consensus as mc
from signal_model import MODEL as SIGNAL_MODEL, prompt_version, warn_if_unpinned
from topic_config import get_topic

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "signal"

PAGE = 1000
PROPOSE_BATCH = 40      # claims per proposal call — short texts, so these can be large
MAP_BATCH = 20          # claims per mapping call — the model must answer per claim
DEFAULT_RUNS = 2
DEFAULT_MAX_PROPOSITIONS = 8


def load_claims(sb, slug: str, category: str | None) -> tuple[str, list[dict]]:
    """Claims for one issue with their composite scores, paged past the row cap."""
    resp = sb.table("signal_issues").select("id").eq("slug", slug).execute()
    if not resp.data:
        print(f"[ERROR] No issue with slug '{slug}'.")
        return "", []
    issue_id = resp.data[0]["id"]

    rows, offset = [], 0
    while True:
        q = (sb.table("signal_claims")
               .select("id, claim_text, category")
               .eq("issue_id", issue_id))
        if category:
            q = q.eq("category", category)
        page = q.range(offset, offset + PAGE - 1).execute().data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    ids = [r["id"] for r in rows]
    for i in range(0, len(ids), 50):
        got = (sb.table("signal_claim_composites")
                 .select("claim_id, composite_score")
                 .in_("claim_id", ids[i:i + 50]).execute()).data or []
        by_id = {g["claim_id"]: g for g in got}
        for r in rows[i:i + 50]:
            comp = by_id.get(r["id"])
            r["composite_score"] = float(comp["composite_score"]) if comp else None
    return issue_id, rows


# ---------------------------------------------------------------------------
# 1. Propose
# ---------------------------------------------------------------------------

PROPOSE_SYSTEM = """You are finding the questions a body of evidence can answer.

You will be shown factual claims collected under one research topic. Propose the
propositions this evidence could SETTLE — statements that could turn out to be
false, and that the claims shown bear on one way or the other.

A proposition must:
  - name what, specifically. Not "diet affects cancer" but "dietary fat
    reduction after a breast cancer diagnosis reduces recurrence".
  - be capable of being wrong. If no evidence could contradict it, it is a
    subject heading, not a proposition.
  - be answerable from evidence of the kind shown, not from values.

Do NOT propose:
  - restatements of the topic's title
  - two questions joined by "and"
  - anything so broad that every claim shown supports it

Prefer propositions where the evidence shown actually looks divided. A live
disagreement is more useful than a settled one, though say so if the evidence
appears one-sided.

Return ONLY JSON:
[{"proposition": "...", "why_it_could_be_false": "...", "evidence_seen": "what
in these claims bears on it"}]
Propose at most 6 from this batch."""

MERGE_SYSTEM = """You are consolidating candidate propositions into one set.

Several batches of evidence each produced candidates. Many will be near
duplicates or differ only in wording. Produce the smallest set that keeps every
distinct question, discarding any that:
  - restate another with different words
  - are too broad to be false
  - join two questions with "and" (split them instead, if both are real)

Keep the sharpest wording of each surviving question. Order by how likely the
evidence is to be genuinely divided on it.

Return ONLY JSON:
[{"proposition": "...", "why_it_could_be_false": "...", "merged_from": <count>}]
Return at most %d."""


def propose(claims: list[dict], batch: int) -> list[dict]:
    out: list[dict] = []
    batches = [claims[i:i + batch] for i in range(0, len(claims), batch)]
    print(f"  proposing from {len(batches)} batch(es): ", end="", flush=True)
    for group in batches:
        body = "\n".join(f"- {c['claim_text']}" for c in group)
        got = mc._call_claude(PROPOSE_SYSTEM, body, max_tokens=3000)
        if not isinstance(got, list):
            print("x", end="", flush=True)
            continue
        for item in got:
            if isinstance(item, dict) and item.get("proposition"):
                out.append(item)
        print(".", end="", flush=True)
        time.sleep(0.3)
    print(f"  -> {len(out)} candidates")
    return out


def merge(candidates: list[dict], limit: int) -> list[dict]:
    if not candidates:
        return []
    body = "\n".join(
        f"- {c['proposition']}  (could be false because: "
        f"{c.get('why_it_could_be_false', '')})" for c in candidates)
    got = mc._call_claude(MERGE_SYSTEM % limit, body, max_tokens=3000)
    if not isinstance(got, list):
        print("  [ERROR] merge failed; falling back to the raw candidate list.")
        return candidates[:limit]
    merged = [g for g in got if isinstance(g, dict) and g.get("proposition")]
    print(f"  merged {len(candidates)} candidates -> {len(merged)} propositions")
    return merged[:limit]


# ---------------------------------------------------------------------------
# 2. Map every claim to every proposition
# ---------------------------------------------------------------------------

def map_system(props: list[dict]) -> str:
    listed = "\n".join(f"  P{i}: {p['proposition']}" for i, p in enumerate(props, 1))
    return (
        "You are deciding which propositions each claim bears on.\n\n"
        f"PROPOSITIONS:\n{listed}\n\n"
        "For each claim, list every proposition it bears on and whether it "
        "supports or opposes it. A claim may bear on several, one, or none.\n\n"
        "Answer with an EMPTY list when the claim bears on none of them. Most "
        "corpora contain background — incidence rates, population statistics, "
        "descriptions of how a trial was designed — that is true and useful and "
        "settles nothing. Saying so is the point of this exercise, not a "
        "failure to try hard enough.\n\n"
        "Bearing means the claim would move a reasonable person's confidence in "
        "the proposition. A claim that merely mentions the same subject does not "
        "bear on it.\n\n"
        "Return ONLY JSON, one object per claim, in the order given:\n"
        "[{\"n\": 1, \"bears_on\": [{\"p\": 1, \"stance\": \"supports\"|\"opposes\"}]}]"
    )


def map_batch(batch: list[dict], system_prompt: str, n_props: int) -> dict[str, set] | None:
    body = "\n\n".join(f"--- Claim {i} ---\n{c['claim_text']}"
                       for i, c in enumerate(batch, 1))
    got = mc._call_claude(system_prompt, body, max_tokens=4096)
    if not isinstance(got, list):
        return None
    result: dict[str, set] = {c["id"]: set() for c in batch}
    for item in got:
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        if not isinstance(n, int) or not (1 <= n <= len(batch)):
            continue
        cid = batch[n - 1]["id"]
        for b in (item.get("bears_on") or []):
            if not isinstance(b, dict):
                continue
            p, stance = b.get("p"), b.get("stance")
            if isinstance(p, int) and 1 <= p <= n_props and stance in ("supports", "opposes"):
                result[cid].add((p, stance))
    return result


def reconcile_bearing(runs: list[dict[str, set]], claim_ids: list[str],
                      n_runs: int) -> dict[str, set]:
    """A (proposition, stance) counts only if it appears in a MAJORITY of runs.

    Same discipline as map_consensus: one call's opinion is a sample. A claim
    the model attaches to a proposition once and not again is not evidence that
    bears on it, and reporting it as such would inflate every coverage figure
    in the output.
    """
    tally: dict[str, Counter] = {cid: Counter() for cid in claim_ids}
    for run in runs:
        for cid, pairs in run.items():
            for pair in pairs:
                tally[cid][pair] += 1
    need = n_runs // 2 + 1
    return {cid: {pair for pair, n in c.items() if n >= need} for cid, c in tally.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issue-slug", required=True, help="Topic slug (no default: "
                    "a default here would silently mine the wrong corpus).")
    ap.add_argument("--category", help="Restrict to one category. Omit to mine the "
                    "whole topic, which is the point.")
    ap.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                    help=f"Mapping passes (default {DEFAULT_RUNS}). A claim bears on "
                         "a proposition only if a majority of runs say so.")
    ap.add_argument("--max-propositions", type=int, default=DEFAULT_MAX_PROPOSITIONS,
                    help=f"Cap on the merged set (default {DEFAULT_MAX_PROPOSITIONS}).")
    ap.add_argument("--propose-batch", type=int, default=PROPOSE_BATCH)
    ap.add_argument("--map-batch", type=int, default=MAP_BATCH)
    ap.add_argument("--dry-run", action="store_true",
                    help="Report the API cost and exit. No calls, no writes.")
    ap.add_argument("--report", help="Where to write the JSON report.")
    args = ap.parse_args()

    if args.runs < 1:
        ap.error("--runs must be at least 1")

    warn_if_unpinned()
    print("READ-ONLY — nothing is written to the database.")

    sb = mc._get_supabase()
    topic = get_topic(args.issue_slug)
    issue_id, claims = load_claims(sb, args.issue_slug, args.category)
    if not claims:
        sys.exit("No claims found. Nothing to mine.")

    scope = f" / {args.category}" if args.category else ""
    print(f"\n{'=' * 70}")
    print(f"{topic['title']}  ({args.issue_slug}{scope})")
    print(f"{'=' * 70}")
    n_propose = -(-len(claims) // args.propose_batch)
    n_map = -(-len(claims) // args.map_batch)
    calls = n_propose + 1 + n_map * args.runs
    print(f"  {len(claims)} claims")
    print(f"  API calls: {calls}  ({n_propose} propose + 1 merge + "
          f"{n_map} map x {args.runs} runs)")
    if args.dry_run:
        print("\n--- DRY RUN — no API calls, no writes ---")
        return

    print("\nSTEP 1 — propose")
    candidates = propose(claims, args.propose_batch)
    if not candidates:
        sys.exit("No propositions proposed. Nothing to map.")

    print("\nSTEP 2 — merge")
    props = merge(candidates, args.max_propositions)
    if not props:
        sys.exit("Merge produced nothing.")
    for i, p in enumerate(props, 1):
        print(f"  P{i}: {p['proposition']}")

    print(f"\nSTEP 3 — map {len(claims)} claims to {len(props)} propositions, "
          f"{args.runs} run(s)")
    system_prompt = map_system(props)
    batches = [claims[i:i + args.map_batch] for i in range(0, len(claims), args.map_batch)]
    runs, failed = [], 0
    for r in range(args.runs):
        print(f"  run {r + 1}/{args.runs}: ", end="", flush=True)
        acc: dict[str, set] = {}
        for b in batches:
            got = map_batch(b, system_prompt, len(props))
            if got is None:
                failed += 1
                print("x", end="", flush=True)
                continue
            acc.update(got)
            print(".", end="", flush=True)
            time.sleep(0.3)
        print()
        runs.append(acc)
    if failed:
        print(f"  [WARN] {failed} mapping call(s) failed. Claims in them were "
              "measured fewer times and may be under-counted below.")

    ids = [c["id"] for c in claims]
    final = reconcile_bearing(runs, ids, args.runs)
    score = {c["id"]: c["composite_score"] for c in claims}
    text = {c["id"]: c["claim_text"] for c in claims}

    # Per-run side counts, so a proposition's balance is judged the same way a
    # category's is — including telling a near-tie apart from an instability.
    per_run_sides = []
    for run in runs:
        counts = {i: [0, 0] for i in range(1, len(props) + 1)}
        for pairs in run.values():
            for p, stance in pairs:
                counts[p][0 if stance == "supports" else 1] += 1
        per_run_sides.append(counts)

    rows = []
    for i, p in enumerate(props, 1):
        bearing = [cid for cid, pairs in final.items()
                   if any(pp == i for pp, _ in pairs)]
        sup = [cid for cid in bearing if (i, "supports") in final[cid]]
        opp = [cid for cid in bearing if (i, "opposes") in final[cid]]
        observed = [list(s[i]) for s in per_run_sides]
        # No evidence is not a tie. classify_sides on [[0,0],[0,0]] returns
        # "tie" because nothing clears the decisiveness floor, and printing that
        # would say a proposition is finely balanced when the truth is that
        # nothing bears on it at all.
        #
        # A one-sided result IS reported as a lean here, unlike in
        # map_consensus.reconcile where a side collapsing to zero is treated as
        # a coverage failure. The difference is deliberate: a category called
        # "debated" with no opposing claims is broken, whereas a proposition
        # that all the evidence supports is simply settled, and saying so is a
        # useful answer.
        balance = (mc.classify_sides(observed)
                   if args.runs > 1 and len(bearing) > 0 else None)
        scored = [score[c] for c in bearing if score.get(c) is not None]
        rows.append({
            "n": i,
            "proposition": p["proposition"],
            "why_it_could_be_false": p.get("why_it_could_be_false"),
            "bearing": len(bearing),
            "supports": len(sup),
            "opposes": len(opp),
            "sides_observed": observed,
            "sides_balance": balance,
            "mean_composite": round(sum(scored) / len(scored), 2) if scored else None,
            "bearing_claim_ids": bearing,
        })

    residue = [cid for cid, pairs in final.items() if not pairs]

    print(f"\n{'=' * 70}")
    print("PROPOSITIONS THIS CORPUS CAN SETTLE")
    print(f"{'=' * 70}")
    print(f"{'':4}{'bears':>6}{'sup':>5}{'opp':>5}{'mean':>6}  balance")
    for r in sorted(rows, key=lambda x: -x["bearing"]):
        bal = r["sides_balance"] or "—"
        mean = f"{r['mean_composite']:.2f}" if r["mean_composite"] is not None else "—"
        print(f"\n  P{r['n']} {r['proposition']}")
        print(f"{'':4}{r['bearing']:>6}{r['supports']:>5}{r['opposes']:>5}{mean:>6}  "
              f"{bal}   {r['sides_observed']}")

    print(f"\n  RESIDUE: {len(residue)} of {len(claims)} claims "
          f"({len(residue) / len(claims):.0%}) bear on none of these.")
    print("  That share is how much of a subject-heading corpus was never "
          "evidence for anything askable.")
    for cid in residue[:5]:
        print(f"    e.g. {text[cid][:120]}")

    out = Path(args.report) if args.report else DATA_DIR / (
        f"propositions_{args.issue_slug}"
        + (f"_{args.category}" if args.category else "") + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "slug": args.issue_slug,
        "category": args.category,
        "issue_id": issue_id,
        "claims": len(claims),
        "runs": args.runs,
        "failed_calls": failed,
        "model": mc.LAST_RESOLVED_MODEL or SIGNAL_MODEL,
        "prompt_version": prompt_version(system_prompt),
        "candidates_proposed": len(candidates),
        "propositions": rows,
        "residue_claim_ids": residue,
    }, indent=2) + "\n")
    print(f"\nFull report: {out}")
    print("Nothing was written to the database.")


if __name__ == "__main__":
    main()
