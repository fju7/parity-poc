# WHU quarterly round 1: deviations log

Kept from the freeze (commit `5f4a928b757d7f47c1ba8ed47600ced4a7a69f12`, `round1_protocol.md`), as its §10
requires: every departure from the protocol, with its date, what changed, why, and whether it was decided
before or after any result was seen. One row per entry, newest last. Dates are UTC.

| Date | What | Why | Decided before or after any result was seen |
|---|---|---|---|
| 2026-10-28 | Ruling (advisor), recorded verbatim in substance: WHU-Q1-02 (Campbell cl2.70016, PMID 39917627) passes eligibility criterion 2: the study protocol's criterion accepts "an explicit statement of strength" (`docs/whu-reliability-protocol.md`, line 58), which the abstract gives ("large but based on a low number of studies"; "low confidence in study findings"). The draw stands. | The closer reading (draw record `draws/campbell-5f4a928….json`) flagged criterion 2: no GRADE, a per-study confidence rating rather than a grade on the conclusion. | Before any answer key, system run or judging. |
| 2026-10-28 | Ruling (advisor): WHU-Q1-03 (IPCC AR6-SYR-B.1.3) passes criterion 2: the IPCC unit is the numbered statement as a whole (protocol line 241, "Frame and draw rulings"), and the statement carries "high confidence" and "virtually certain". The draw stands. | The closer reading flagged that the statement's first sentence carries no calibrated term. | Before any answer key, system run or judging. |
| 2026-10-28 | Ruling (advisor): the IPCC statements read for the draw from the extension draw's fetch cache (2026-10-24, the four AR6 SPM pages, `frames.Fetcher`), because ipcc.ch now answers the script with HTTP 403, are accepted as recorded (protocol §1; draw record `draws/ipcc-5f4a928….json`). All 400 eligible statements hash to the frame's `statement_sha256`. No bot wall was worked around. | ipcc.ch refused the script's fetch on 2026-10-28. | Before any answer key, system run or judging. |
