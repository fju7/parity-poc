"""
Audit which category each claim actually belongs to.

WHY THIS EXISTS
---------------
extract_claims.py assigns a category at extraction. When the model returns a
category that is missing or not one of the topic's own, the code does this:

    cat = c.get("category", categories[-1])
    if cat not in categories:
        cat = categories[-1]          # fallback to last category

Silently. Nothing is printed, nothing is counted, and the claim lands in
whichever category happens to be listed last for that topic. Those are:

    glp1-drugs                        emerging
    social-media-teen-mental-health   methodology
    breast-cancer-therapies           guidelines

The first two are exactly the categories found broken on 2026-08-27:
glp1/emerging is eight-elevenths obesity prevalence statistics, and
social-media/methodology is the one whose side attribution inverts between
runs. That is suggestive and it is not proof — glp1/emerging holds only 11 of
that topic's 153 claims, which is small for a dumping ground. This script
settles it with evidence instead of inference.

WHAT IT MEASURES
----------------
Every stored claim is shown to the model WITHOUT its current category, mixed
into batches that deliberately straddle categories so the grouping gives
nothing away, and the model is asked which of the topic's categories it bears
on — or none of them. That happens K times. A claim is only reported as
misplaced when the runs agree with each other AND disagree with what is
stored, which keeps single-call noise out of the finding.

The output is per-category: how many claims stay, how many would move and
where to, and how many bear on no category in the topic at all. That last
number is the one to watch. A category whose contents the model would mostly
relocate is not a category, and any consensus label computed over it is a
label about the wrong question.

WHAT IT DOES NOT DO
-------------------
It writes nothing. Recategorisation is a separate, reviewed step, because
moving a claim changes which consensus label it feeds and therefore what a
reader is told.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/audit_categories.py --issue-slug glp1-drugs --dry-run
    python scripts/signal/audit_categories.py --issue-slug glp1-drugs
    python scripts/signal/audit_categories.py --all-topics --runs 3
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import map_consensus as mc
from signal_model import MODEL as SIGNAL_MODEL, prompt_version, warn_if_unpinned
from topic_config import get_topic, list_slugs


def approved_slugs(sb) -> list[str]:
    """Slugs of every quality-approved topic, the same set stability_sweep uses.

    Deliberately NOT topic_config.list_slugs(), which returns every row in
    signal_issues including drafts. The audit's numbers have to be comparable
    with the sweep's, and a set that silently includes topics the sweep never
    measures would make them look like they disagree.
    """
    res = (
        sb.table("signal_issues")
        .select("slug, quality_review_status")
        .eq("quality_review_status", "approved")
        .execute()
    )
    return sorted(r["slug"] for r in (res.data or []) if r.get("slug"))

REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "signal" / "category_audit.json"

PAGE = 1000
DEFAULT_BATCH = 20
DEFAULT_RUNS = 3

# Deterministic shuffling. The batches must straddle categories so that a batch
# of claims that all came from one category cannot itself hint at the answer,
# and the shuffle must be reproducible so a re-run audits the same batches.
SHUFFLE_SEED = 20260827

NONE_KEY = "__none__"


def load_claims(sb, slug: str) -> tuple[str, list[dict]]:
    """Every claim for one issue, paged past the PostgREST row cap."""
    resp = sb.table("signal_issues").select("id").eq("slug", slug).execute()
    if not resp.data:
        print(f"[ERROR] No issue with slug '{slug}'.")
        return "", []
    issue_id = resp.data[0]["id"]

    rows, offset = [], 0
    while True:
        page = (sb.table("signal_claims")
                  .select("id, claim_text, category")
                  .eq("issue_id", issue_id)
                  .range(offset, offset + PAGE - 1).execute()).data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return issue_id, rows


def load_contexts(sb, claim_ids: list[str]) -> dict[str, str]:
    """The passage each claim was extracted from, keyed by claim_id.

    Why this option exists: the audit shows the model a claim's TEXT and nothing
    else, while the stored category was chosen at extraction time with the whole
    source document in view. A claim that reads as one category stripped of its
    surroundings may have been correctly filed as another with them. Running the
    audit both ways separates "the category is wrong" from "the claim does not
    carry its own context", and those need different fixes: the first is a move,
    the second is a rewrite of the claim.

    Chunked by 50 claim ids rather than paged: an .in_() list much longer than
    that risks a URL-length failure, and each chunk returns well under the
    PostgREST row cap.
    """
    out: dict[str, str] = {}
    for i in range(0, len(claim_ids), 50):
        rows = (sb.table("signal_claim_sources")
                  .select("claim_id, source_context")
                  .in_("claim_id", claim_ids[i:i + 50]).execute()).data or []
        for r in rows:
            ctx = (r.get("source_context") or "").strip()
            if not ctx:
                continue
            # A claim can come from several sources. Keep the first non-empty
            # passage rather than concatenating: the point is to restore the
            # claim's setting, not to hand the model a dossier.
            out.setdefault(r["claim_id"], ctx)
    return out


def build_system_prompt(topic: dict) -> str:
    cats = topic["categories"]
    lines = "\n".join(f"  - {c}" for c in cats)
    return (
        "You are sorting individual evidence claims into the categories of one "
        "research topic.\n\n"
        f"TOPIC: {topic['title']}\n"
        f"{topic.get('description', '')}\n\n"
        f"CATEGORIES:\n{lines}\n\n"
        "For each claim you are given, decide which ONE category it bears on "
        "most directly.\n\n"
        "Answer \"none\" when the claim bears on no category above. Be willing "
        "to say none. A claim that is background about the disease, the "
        "population or the market may be true and useful and still belong to no "
        "category in this list; forcing it into the nearest one is what this "
        "audit exists to detect. Judge the claim on what it asserts, not on "
        "what topic it mentions.\n\n"
        "Return ONLY a JSON array, one object per claim, in the order given:\n"
        "[{\"n\": 1, \"category\": \"<one of the categories above, or none>\", "
        "\"confidence\": \"high\"|\"medium\"|\"low\"}]"
    )


def build_batch_prompt(batch: list[dict], contexts: dict[str, str] | None = None) -> str:
    parts = []
    for i, c in enumerate(batch, 1):
        block = f"--- Claim {i} ---\n{c['claim_text']}"
        ctx = (contexts or {}).get(c["id"])
        if ctx:
            block += f"\nSource passage: {ctx[:600]}"
        parts.append(block)
    return "\n\n".join(parts)


def classify_batch(batch: list[dict], system_prompt: str, categories: list[str],
                   contexts: dict[str, str] | None = None) -> dict[str, str] | None:
    """Return {claim_id: category_or_NONE_KEY}, or None if the call failed."""
    out = mc._call_claude(system_prompt, build_batch_prompt(batch, contexts),
                          max_tokens=4096)
    if not isinstance(out, list):
        return None

    valid = set(categories)
    result: dict[str, str] = {}
    for item in out:
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        if not isinstance(n, int) or not (1 <= n <= len(batch)):
            continue
        raw = (item.get("category") or "").strip()
        # An answer outside the topic's categories is recorded as "none" rather
        # than coerced to a real one. Coercion is the bug being audited.
        result[batch[n - 1]["id"]] = raw if raw in valid else NONE_KEY
    return result


def audit_topic(sb, slug: str, runs: int, batch_size: int,
                dry_run: bool, with_context: bool = False) -> dict | None:
    topic = get_topic(slug)
    categories = list(topic["categories"])
    issue_id, claims = load_claims(sb, slug)
    if not claims:
        return None

    batches = [claims[i:i + batch_size] for i in range(0, len(claims), batch_size)]
    calls = len(batches) * runs

    print(f"\n{'=' * 70}")
    print(f"{topic['title']}  ({slug})")
    print(f"{'=' * 70}")
    print(f"  {len(claims)} claims, {len(batches)} batches of up to {batch_size}, "
          f"{runs} run{'s' if runs != 1 else ''}")
    print(f"  API calls: {calls}  ({len(batches)} batches x {runs} runs)")
    print(f"  Last category in this topic's list: {categories[-1]}"
          "   <- where the silent fallback sends anything it cannot place")
    if dry_run:
        return {"slug": slug, "claims": len(claims), "calls": calls, "dry_run": True}

    system_prompt = build_system_prompt(topic)

    contexts = None
    if with_context:
        contexts = load_contexts(sb, [c["id"] for c in claims])
        have = sum(1 for c in claims if contexts.get(c["id"]))
        print(f"  source passages found for {have} of {len(claims)} claims"
              f" ({have / len(claims):.0%})")
        if have == 0:
            print("  [WARN] no source passages at all — this run is identical to "
                  "one without --with-context. Not a context comparison.")

    # Shuffle once, then reuse the same batches for every run: the runs must
    # differ only by the model's own variation, not by how claims were grouped.
    shuffled = list(claims)
    random.Random(SHUFFLE_SEED).shuffle(shuffled)
    batches = [shuffled[i:i + batch_size] for i in range(0, len(shuffled), batch_size)]

    votes: dict[str, list[str]] = defaultdict(list)
    failed_batches = 0
    for run in range(runs):
        print(f"  run {run + 1}/{runs}: ", end="", flush=True)
        for bi, batch in enumerate(batches):
            got = classify_batch(batch, system_prompt, categories, contexts)
            if got is None:
                failed_batches += 1
                print("x", end="", flush=True)
                continue
            for cid, cat in got.items():
                votes[cid].append(cat)
            print(".", end="", flush=True)
            time.sleep(0.3)
        print()

    if failed_batches:
        # Loud, and it changes the verdict rather than quietly shrinking the
        # sample. A claim whose batch failed has fewer votes than the others and
        # must not be reported with the same confidence.
        print(f"  [WARN] {failed_batches} batch call(s) failed; "
              "claims in them were measured fewer times than the rest.")

    stored = {c["id"]: c["category"] for c in claims}
    text = {c["id"]: c["claim_text"] for c in claims}

    per_claim = []
    for cid, cat_votes in votes.items():
        agreed = len(set(cat_votes)) == 1 and len(cat_votes) == runs
        modal, n_modal = Counter(cat_votes).most_common(1)[0]
        per_claim.append({
            "claim_id": cid,
            "stored": stored.get(cid),
            "model": modal,
            "unanimous": agreed,
            "votes": cat_votes,
            "agreement": round(n_modal / len(cat_votes), 3),
            "misplaced": agreed and modal != stored.get(cid),
            "claim_text": text.get(cid, "")[:200],
        })

    unmeasured = [c["id"] for c in claims if c["id"] not in votes]

    by_cat: dict[str, dict] = {}
    for cat in categories:
        mine = [p for p in per_claim if p["stored"] == cat]
        moving = [p for p in mine if p["misplaced"]]
        to_none = [p for p in moving if p["model"] == NONE_KEY]
        by_cat[cat] = {
            "claims_measured": len(mine),
            "stay": len(mine) - len(moving),
            "would_move": len(moving),
            "would_move_to_none": len(to_none),
            "destinations": dict(Counter(p["model"] for p in moving)),
            "share_moving": round(len(moving) / len(mine), 3) if mine else None,
        }

    incoming = Counter(p["model"] for p in per_claim
                       if p["misplaced"] and p["model"] != NONE_KEY)

    return {
        "slug": slug,
        "issue_id": issue_id,
        "title": topic["title"],
        "categories": categories,
        "last_category": categories[-1],
        "claims": len(claims),
        "runs": runs,
        "batch_size": batch_size,
        "with_context": with_context,
        "contexts_found": (sum(1 for c in claims if (contexts or {}).get(c["id"]))
                           if with_context else None),
        "failed_batches": failed_batches,
        "unmeasured_claim_ids": unmeasured,
        "model": mc.LAST_RESOLVED_MODEL or SIGNAL_MODEL,
        "prompt_version": prompt_version(system_prompt),
        "by_category": by_cat,
        "incoming": dict(incoming),
        "claims_detail": per_claim,
    }


def print_topic_report(r: dict) -> None:
    print(f"\n  {'category':<42} {'kept':>5} {'move':>5} {'none':>5}  destinations")
    print(f"  {'-' * 42} {'-' * 5} {'-' * 5} {'-' * 5}  {'-' * 30}")
    for cat, s in r["by_category"].items():
        dests = ", ".join(
            f"{('NONE' if k == NONE_KEY else k)}:{v}"
            for k, v in sorted(s["destinations"].items(), key=lambda kv: -kv[1]))
        flag = ""
        if s["share_moving"] is not None and s["share_moving"] >= 0.5:
            flag = "  <- MOSTLY WRONG"
        elif s["share_moving"] is not None and s["share_moving"] >= 0.25:
            flag = "  <- check"
        mark = " *" if cat == r["last_category"] else "  "
        print(f"  {cat[:42]:<42}{mark[1]}{s['stay']:>4} {s['would_move']:>5} "
              f"{s['would_move_to_none']:>5}  {dests}{flag}")
    print(f"  (* = last category, where the silent fallback sends claims)")

    det = r["claims_detail"]
    unan = sum(1 for x in det if x["unanimous"])
    if det:
        print(f"\n  {unan} of {len(det)} claims got the same answer in all "
              f"{r['runs']} runs ({unan / len(det):.0%}). Only those can be "
              "reported as misplaced.")

    total_moving = sum(s["would_move"] for s in r["by_category"].values())
    total_none = sum(s["would_move_to_none"] for s in r["by_category"].values())
    measured = sum(s["claims_measured"] for s in r["by_category"].values())
    if measured:
        print(f"\n  {total_moving} of {measured} claims ({total_moving / measured:.0%}) "
              f"are placed somewhere the model unanimously disagrees with.")
        print(f"  {total_none} of those bear on no category in this topic at all.")
    if r["unmeasured_claim_ids"]:
        print(f"  {len(r['unmeasured_claim_ids'])} claim(s) got no verdict "
              "(batch failures) and are excluded from every figure above.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issue-slug", help="Audit one topic.")
    ap.add_argument("--all-topics", action="store_true",
                    help="Audit every quality-approved topic — the same set "
                         "stability_sweep measures. Mutually exclusive with "
                         "--issue-slug.")
    ap.add_argument("--include-unapproved", action="store_true",
                    help="With --all-topics, also audit topics that have not "
                         "passed quality review.")
    ap.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                    help=f"Independent passes per batch (default {DEFAULT_RUNS}). "
                         "A claim counts as misplaced only if every run agrees.")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH,
                    help=f"Claims per API call (default {DEFAULT_BATCH}).")
    ap.add_argument("--with-context", action="store_true",
                    help="Show the model the source passage each claim was "
                         "extracted from, alongside the claim. Run the audit "
                         "both ways to separate a wrong category from a claim "
                         "that does not carry its own context. Write the two "
                         "runs to different --report paths.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report the API cost and exit. No calls, no writes.")
    ap.add_argument("--report", default=str(REPORT_PATH),
                    help="Where to write the JSON report.")
    args = ap.parse_args()

    if bool(args.issue_slug) == bool(args.all_topics):
        ap.error("give exactly one of --issue-slug or --all-topics")
    if args.runs < 1:
        ap.error("--runs must be at least 1")

    warn_if_unpinned()
    print("READ-ONLY — no claim is moved and no row is written.")

    sb = mc._get_supabase()

    if args.all_topics:
        if args.include_unapproved:
            slugs = list_slugs()
            print(f"Topics: {len(slugs)} (every topic, approved or not)")
        else:
            slugs = approved_slugs(sb)
            print(f"Topics: {len(slugs)} (quality-approved only; "
                  "--include-unapproved widens this)")
        if not slugs:
            sys.exit("No topics matched. Nothing to audit.")
    else:
        slugs = [args.issue_slug]

    results, total_calls = [], 0
    for slug in slugs:
        r = audit_topic(sb, slug, args.runs, args.batch_size, args.dry_run,
                        with_context=args.with_context)
        if r is None:
            continue
        if args.dry_run:
            total_calls += r["calls"]
            continue
        print_topic_report(r)
        results.append(r)

    if args.dry_run:
        print(f"\nTotal API calls needed: {total_calls}  "
              f"({len(slugs)} topic{'s' if len(slugs) != 1 else ''} x "
              f"batches x {args.runs} runs)")
        return

    if not results:
        print("\nNothing audited.")
        return

    print(f"\n{'=' * 70}")
    print("CATEGORY AUDIT")
    print(f"{'=' * 70}")
    worst = []
    for r in results:
        for cat, s in r["by_category"].items():
            if s["share_moving"] is not None and s["share_moving"] >= 0.25:
                worst.append((s["share_moving"], r["slug"], cat, s))
    if worst:
        print("Categories the model would substantially rebuild:")
        for share, slug, cat, s in sorted(worst, reverse=True):
            last = " (LAST — fallback target)" if cat == \
                next(x["last_category"] for x in results if x["slug"] == slug) else ""
            print(f"  {share:>5.0%}  {slug} / {cat}{last}"
                  f"   {s['would_move']} of {s['claims_measured']}, "
                  f"{s['would_move_to_none']} belong nowhere")
    else:
        print("No category has 25% or more of its claims placed elsewhere.")

    fallback_share = []
    for r in results:
        s = r["by_category"].get(r["last_category"])
        if s and s["share_moving"] is not None:
            fallback_share.append((r["slug"], r["last_category"], s["share_moving"]))
    if fallback_share:
        print("\nThe silent-fallback target in each topic:")
        for slug, cat, share in sorted(fallback_share, key=lambda x: -x[2]):
            print(f"  {share:>5.0%} misplaced   {slug} / {cat}")
        avg_last = sum(x[2] for x in fallback_share) / len(fallback_share)
        others = [s["share_moving"] for r in results
                  for c, s in r["by_category"].items()
                  if c != r["last_category"] and s["share_moving"] is not None]
        avg_other = sum(others) / len(others) if others else 0.0
        print(f"\n  last categories average {avg_last:.0%} misplaced; "
              f"every other category averages {avg_other:.0%}.")
        print("  A large gap is the fallback firing. A small one means the "
              "miscategorisation is ordinary extractor error, which is a "
              "different and smaller fix.")

    out = Path(args.report)
    if args.with_context and out == REPORT_PATH:
        # Otherwise the context run silently overwrites the run it is meant to
        # be compared against, and the comparison becomes impossible to make.
        out = out.with_name(out.stem + "_with_context" + out.suffix)
        print(f"\n  --with-context: writing to {out.name} so the plain run survives.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"topics": results}, indent=2) + "\n")
    print(f"\nFull report: {out}")
    print("Nothing was written to the database.")


if __name__ == "__main__":
    main()
