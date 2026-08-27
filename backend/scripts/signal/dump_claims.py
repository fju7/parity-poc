"""
Print the claims behind a category, so a human can read the evidence.

WHY THIS EXISTS
---------------
The stability sweep tells you a published label disagrees with what the model
produces today. It does not tell you which one is right. GLP-1 pricing had been
published as "debated" for five months; the sweep said "consensus"; only
reading all 44 claims settled it — they are prices, spending figures and
coverage rules with no opposing position, and the sweep was right.

Three of the seven drifts found on 2026-08-27 rest on 6, 7 and 11 claims. A
label assigned over six claims deserves to be read before it is published,
in either direction.

Read-only. No model calls, no writes.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/dump_claims.py --drifted        # every drifted category
    python scripts/signal/dump_claims.py --slug glp1-drugs --category pricing
    python scripts/signal/dump_claims.py --drifted --max 12   # cap per category
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc

SWEEP = Path(__file__).resolve().parents[2] / "data" / "signal" / "stability_sweep.json"
PAGE = 1000  # PostgREST caps a request at 1000 rows; page explicitly.


def load_claims(sb, slug: str) -> tuple[str, dict[str, list[dict]]]:
    """Claims for one issue, grouped by category, paged past the row cap."""
    resp = sb.table("signal_issues").select("id").eq("slug", slug).execute()
    if not resp.data:
        print(f"[ERROR] No issue with slug '{slug}'.")
        return "", {}
    issue_id = resp.data[0]["id"]

    rows, offset = [], 0
    while True:
        page = (sb.table("signal_claims")
                  .select("id, claim_text, category, specificity")
                  .eq("issue_id", issue_id)
                  .range(offset, offset + PAGE - 1).execute()).data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE

    # Composites live in signal_claim_composites and are fetched by claim_id in
    # chunks of 50, the same shape map_consensus uses. A .in_() list longer than
    # that risks a URL-length failure, which is why it is chunked and not paged.
    ids = [r["id"] for r in rows]
    comps: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        got = (sb.table("signal_claim_composites")
                 .select("claim_id, composite_score, evidence_category")
                 .in_("claim_id", ids[i:i + 50]).execute()).data or []
        for c in got:
            comps[c["claim_id"]] = c

    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        c = comps.get(r["id"])
        r["composite_score"] = float(c["composite_score"]) if c and c.get("composite_score") is not None else None
        r["evidence_category"] = c.get("evidence_category") if c else None
        by_cat.setdefault(r.get("category") or "(none)", []).append(r)
    return issue_id, by_cat


def show(slug: str, category: str, claims: list[dict], published: str | None,
         current: str | None, limit: int | None) -> None:
    print("\n" + "=" * 78)
    head = f"{slug} / {category}"
    if published and current:
        head += f"    published={published}  ->  now={current}"
    print(head)
    print("=" * 78)
    if not claims:
        print("  (no claims found for this category)")
        return
    scored = [c for c in claims if c.get("composite_score") is not None]
    print(f"{len(claims)} claims, {len(scored)} scored"
          + (f" — showing the {limit} highest-scoring" if limit and len(claims) > limit else ""))
    print()
    claims = sorted(claims, key=lambda c: (c.get("composite_score") is None,
                                           -(c.get("composite_score") or 0)))
    for i, c in enumerate(claims[:limit] if limit else claims, 1):
        sc = c.get("composite_score")
        sc = f"{sc:.2f}" if isinstance(sc, (int, float)) else " -- "
        ev = c.get("evidence_category") or ""
        body = textwrap.fill(c.get("claim_text", "").strip(), width=70,
                             initial_indent="", subsequent_indent="          ")
        print(f"  {i:>2}. [{sc}] {body}")
        if ev:
            print(f"          ({ev})")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Print the claims behind a category. Read-only.")
    ap.add_argument("--slug")
    ap.add_argument("--category")
    ap.add_argument("--drifted", action="store_true",
                    help="Every category in the latest stability sweep where published != current.")
    ap.add_argument("--max", type=int, default=None, help="Cap claims shown per category.")
    args = ap.parse_args()

    if not args.drifted and not (args.slug and args.category):
        ap.error("use --drifted, or both --slug and --category")

    targets: list[tuple[str, str, str | None, str | None]] = []
    if args.drifted:
        if not SWEEP.exists():
            sys.exit(f"[ERROR] No sweep at {SWEEP}. Run stability_sweep.py first.")
        data = json.loads(SWEEP.read_text())
        for r in data.get("results", []):
            if not r.get("agrees"):
                targets.append((r["slug"], r["category"], r.get("published"), r.get("current")))
        if not targets:
            print("No drifted categories in the latest sweep.")
            return
        print(f"{len(targets)} drifted categor{'y' if len(targets)==1 else 'ies'} in {SWEEP.name}")
    else:
        targets.append((args.slug, args.category, None, None))

    sb = mc._get_supabase()
    cache: dict[str, dict[str, list[dict]]] = {}
    for slug, category, published, current in targets:
        if slug not in cache:
            _, cache[slug] = load_claims(sb, slug)
        show(slug, category, cache[slug].get(category, []), published, current, args.max)

    print("=" * 78)
    print("Read-only. Nothing was written.")


if __name__ == "__main__":
    main()
