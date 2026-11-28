# Next phase: the planted-errors (seeded-defect) test — recorded, not started

Recorded 2026-11-28 on the advisor's ruling 8 on WHU-OT1-04i (P222). Nothing here is built or run. No paid call is
made for this test until the advisor approves its design.

## What is decided

- **The test.** The planted-errors (seeded-defect) test: known defects planted in copies of cases (issues/WHU-SD-*,
  git-ignored), run through the pipeline, and counted as caught or missed.
- **Its money.** Its own line, "seeded-defect test", $89, ledger issues starting `whu-validity-sd-`
  (backend/data/spend/caps.json; `spend_ledger.check_line_cap` enforces it; `WHU_SPEND_OVERRIDE` does not lift it).
  The orchestrator trial line ($95, $2.89 left) is not used for it.
- **Order.** Design first, then an estimate. Both go to the advisor. No paid call before the advisor approves the
  design.
- **The standing rules it must meet** (standing_rules.md; deviations.md 2026-11-23):
  - frozen grading: the planted defects, the expected catches and the grading rule are committed and hashed before
    any run, and are not changed after a result is seen;
  - hard-to-judge cases: the planted set includes defects a reader could reasonably miss, not only easy ones, and the
    subset written in different styles to test judge leniency by writing style (deviations.md, 2026-11-23).

## Items for the test to measure (added as they are found)

1. **Output tokens not returned on Claude calls** (P219; advisor's ruling 6 on P222: no change now). On the
   judgement-sentence call site, 59–78% of billed output tokens in the three longest replies (04h 766, 04g 752,
   04e 748 tokens) were in no returned text block; across all recorded judgement-sentence replies, output ran 4.1× the
   visible text at the median and up to 11×; other Claude call sites 1.3–3×; the Google judge 0.98×. The likely
   cause is reasoning billed as output that the client never sees; the raw blocks are not stored, so it is not
   confirmed. The test should measure, per call site, whether these calls catch planted defects at a different rate
   with reasoning on and off, and what each costs. Nothing is changed until it has.
