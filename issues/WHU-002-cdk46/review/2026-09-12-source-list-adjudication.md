# WHU-002 — changes made after publication, 12 September 2026

Not a review. As with melanoma's `2026-08-29-nav-adjudication.md`, this file
exists because the publish reconciliation requires every change to a published
page to cite a decision that resolves to something a person can open and read.

## SRC-LIST-001 — two documents the page rests on, shown to the reader

**What changed.** The Shaaban entry in the reader-facing source list now says it
is the only randomised head-to-head trial on the page that reported a result
(HARMONIA terminated at 61), and that the full text we hold is the operator's
PDF, supplied 1 September after automated routes were refused. Tanguy et al.
(npj Breast Cancer 2018) gains an entry, tagged Methods, quoting the paper's
concluding sentence (Q-22, matched verbatim against the held text).

**Why.** The preflight row `every document the piece rests on is in the list a
reader sees` named S017 (seven sentences, including a median PFS figure) and
S024 (two). S017 was in fact listed under its publisher DOI while the ledger
holds it at its PMC address — one document, two identifiers — so the ledger
now carries the DOI and the check matches a listed link by any identifier the
ledger holds, as reconcile.py already does; no duplicate entry was added. S024
was genuinely absent.

**Also in this round, not reader-facing.** S027–S029 (ESMO Open 2025, Cancers
2023, Breast Cancer Res Treat 2019) added to the ledger and acquired in full
through acquire_sources.py, each verified by content; errata looked up, clean.
Rule 1's seven loose figures examined one by one: 0.96, 2.7 and 0.921
(0.755–1.124) rebound to spans that state them; the rest are recorded as
findings in the session report, not cleared.

**Who decided.** The operator's block of 12 September 2026 (CDK46 — the Class 1
work), applied by Claude Code; the determination that the list additions are a
correction was made against the live page.

**Effect on this assessment.** None on any figure. Two entries in the source
list are new or fuller.

**Recorded for readers** in `corrections.md`, 12 September 2026.
