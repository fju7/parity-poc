# A second reading of every NOT_MATERIAL declaration: cost assessment (advisor's ruling 2 on the P187 fork)

This is an assessment only. Nothing has been built. The decision is the advisor's.

## The proposal

The declarations budget of min(10, 20% of page sentences) would be replaced by two things:

- every NOT_MATERIAL declaration gets an independent second reading by the Google judge (gemini-4-argon), as the
  overstatement check's second read does;
- the hard limit of 20% of page sentences stays.

On disagreement, the finding is stated on the page, or the conclusion sentence it affects is withdrawn. The
scope-element exemptions are unchanged.

## What 01b-01e would have sent to a second reader

All figures are from the committed records. The NOT_MATERIAL judgements come from coverage.json plus omissions.json,
and 01e includes the one that was ruled NOT_MATERIAL and then stopped over the budget.

| Run | NOT_MATERIAL judgements to read | Counted declarations (today's rule) | Page sentences | Today's limit | 20% limit |
|---|---|---|---|---|---|
| 01b | 22 (coverage 21, omissions 1) | 14 | 201 | 10 | 40 |
| 01c | 11 (coverage 11) | 11 | 190 | 10 | 38 |
| 01d | 24 (coverage 17, omissions 7) | 21 | 188 | 10 | 37 |
| 01e | 18 (coverage 10, omissions 8) | 15 | 184 | 10 | 36 |
| **Total** | **75** | | | | |

Under the 20% limit alone, all four runs are within it. Each would then stand or fall on what the second reader
says.

## Cost per second reading

The second reader has to see what the omission ruling sees: the question, the scope with its out-of-scope entries,
the finding with 600 characters of its document around it, the page sentences around its anchor, and what the page
already says from that source. Anything less is not an independent reading of the same judgement.

That payload is measured: 56 logged omission-ruling calls average 3,858 input tokens (maximum 4,974). Replies are
short; the overstatement check's average is 44 tokens (maximum 63), so about 60 tokens is assumed here.

gemini-4-argon prices are from spend_ledger.PRICES. Until 2026-11-30 they are $2 per million tokens in and $10 per
million out. From 2026-12-01 they are $4 and $20.

| | Now | From 2026-12-01 |
|---|---|---|
| Mean call (3,858 in, 60 out) | $0.0083 | $0.0166 |
| Largest measured payload (4,974 in, 63 out) | $0.0106 | $0.0212 |
| Per-call bound (highest measured x 2, standing rule 2) | $0.021 | $0.042 |

### Per run, second readings only

| Run | Mean, now | Mean, from Dec 1 | Worst (largest payload, Dec 1 prices) |
|---|---|---|---|
| 01b | $0.18 | $0.37 | $0.47 |
| 01c | $0.09 | $0.18 | $0.23 |
| 01d | $0.20 | $0.40 | $0.51 |
| 01e | $0.15 | $0.30 | $0.38 |

A malformed reply is re-asked once and a second bad reply counts as disagreement, the fail-safe as in the
overstatement check, so the worst case is twice the column above. That is at most $1.02 a run, for 01d.

### The disagreement path

There is no measured disagreement rate. Both routes are costed instead:

- **Withdraw the affected conclusion sentence.** Code removes it through the lean fail-safe, at $0.
- **State the finding.** This needs one written sentence, an ADD call at the omission ruling's measured cost: mean
  $0.0277, highest $0.0414.
  - It is limited by the additions budget, min(8, 15% of body sentences), which is 8 on these pages.
  - At most 8 x $0.0414 = $0.33 a run, and the rest are withdrawn.
  - A coverage-step declaration has no anchor sentence. If stating it finds no place (P171's rule), nothing can be
    withdrawn in its place, and the page is Not Ready.

**Total added per run:** about $0.15 to $0.40 when the readers agree. At most about $1.35 (01d: $1.02 + $0.33) at
Dec 1 prices when everything disagrees.

**A measurement before any build:** re-reading the 75 recorded judgements with the Google judge would cost about
$0.62 now ($1.25 from Dec 1). It would give a measured disagreement rate on 01b-01e.

## What it takes to build

About 500-700 lines:

- **The step:** a `second_read` step after omissions and before audit, `orch/second_read.py`, modelled on
  `orch/overstatement.py`. It reads every NOT_MATERIAL declaration from coverage.json and omissions.json, one call
  each.
- **The record:** `rulings/second_read.jsonl`, one row per declaration with inputs and hashes.
- **The disagreement path:** an ADD-writing call (a new prompt, "state this finding in one sentence", checked by
  the same span and placement rules), or a fail-safe withdrawal.
- **The page's rules:** coverage_check stops counting the min(10, ...) cap and enforces the 20% limit. A new preflight
  row, "not-material declarations second-read", STOPs on any declaration without an agreeing second read.
- **The run's tables:** reply_limits, stage_cap and steps.py entries; orch/writes.py classification; a rehearsal-plan
  stub for the new call.
- **Tests:** about 8.

The harness changes, so as after any such change, a checkpointed run cannot resume.

## Risks

1. **Replay coverage.** The replay gate's recorded runs (02z-02zd) hold no second-read replies. Their replays need
   synthetic agreeing replies, or they become "unreplayable: new input" from the new step on.
2. **A different reader from a different company.** That is the point. But its disagreement rate on Cochrane-style
   "not material" calls is unmeasured, and a high rate would turn the budget stop into many withdrawals. Q1-01 could
   then reach Ready thinner, or still stop Not Ready on unplaceable coverage units.
3. **A threshold change.** Replacing the min(10, ...) cap with 20% plus a second reading changes what counts as a
   reliable page (standing rule 9(a)). It is the advisor's decision.

## Recommendation

Measure before building: the $0.62 re-read of the 75 recorded judgements. If the readers agree on most of them, the
build is worth its cost. If they disagree on most, the stop becomes withdrawals, and the page that results needs a
look before the rule changes.
