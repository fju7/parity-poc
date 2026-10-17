# Calibration review of published text — 17 October 2026

Read-only review of every B19 (hedge preserved) and B21 (holdings) warning that
the calibration checks on branch `whu-calibration-rules` (at `fc06d36`) raise on
the three published issues. Produced by running `bindings.run_checks` with its
save redirected to memory; no draft, bindings or sources file was changed
(sha256 of all 28 issue files identical before and after).

The checks raise no B20 or B21 STOP on any published issue, and their span-check
flags are identical to main's.

Verdicts are a reader's judgement (Claude, this session), not a judges' panel.
REAL means the sentence states more certainty than its cited span allows.

## B19 — hedge preserved (WARN)

| # | issue | row | sentence | evidence hedge | verdict | why |
|---|---|---|---|---|---|---|
| 1 | melanoma | 2c267ff8 | In this story At five years of follow-up, KEYNOTE-942 reported a recurrence-free survival hazard ratio of 0.510 . | trend (S004) | FALSE ALARM | "favorable trend" qualifies overall survival; the sentence reports the RFS hazard ratio, which the span states flatly |
| 2 | melanoma | aa13a72c | If someone quotes "49%" at you, ask which trial. | trend (S004) | FALSE ALARM | advice to the reader; makes no claim about the hedged endpoint |
| 3 | melanoma | b7ec0d96 | Recurrence-free 5-year · HR 0.510 | trend (S004) | FALSE ALARM | a figure label; "trend" is about OS. (The span also calls the five-year analyses "descriptive", a word not on the hedge list.) |
| 4 | melanoma | 2560dcc0 | Distant metastasis-free 5-year · HR 0.411 | trend (S004) | FALSE ALARM | same as 3, for DMFS |
| 5 | melanoma | 075bae72 | They do not share a statistical standing: the Phase 2b's later analyses are, in its own words, descriptive only, against a one-sided alpha of 0.10, while the Phase 3 crossed a prespecified interim threshold. | hypothesis (S007) | FALSE ALARM | "hypothesis" is in "not intended for formal hypothesis testing"; the sentence quotes the caveat itself ("descriptive only") |
| 6 | melanoma | 44195c42 | And most simply, there is nothing to put beside them: the Phase 3 has released no effect size, so quoting 0.51 next to "met its endpoints" is not a comparison but a substitution … | trend (S004) | FALSE ALARM | about the Phase 3's missing numbers; claims nothing about OS |
| 7 | melanoma | cd0fcd83 | In the earlier Phase 2b at five years, patients on the combination were recurring or dying at about half the rate (HR 0.510, 0.294–0.887) and reaching distant metastasis or dying at about two-fifths the rate (HR 0.411, 0.200–0.843). | trend (S004) | FALSE ALARM | RFS and DMFS with their intervals; "trend" is about OS, which the sentence does not mention |
| 8 | melanoma | 27e83c19 | And the one endpoint that would tell you whether anyone lives longer rests, at five years, on an analysis the companies label only "n=14" . | trend (S002), exploratory (S004) | FALSE ALARM | the sentence is itself a statement of weakness ("rests … on … only n=14"); it overstates nothing |
| 9 | melanoma | b37cd07c | The three-year paper reports a hazard ratio of 0.425 on nine deaths, 95% CI 0.114 to 1.584; the five-year analysis reports 0.471 on fourteen, 95% CI 0.165 to 1.345. | preliminary, trend (S007) | FALSE ALARM | reports the OS estimates with intervals that cross 1 and the death counts; no direction is claimed |
| 10 | cdk46 | e1c8b5c5 | PALOMA-2 is also the trial whose investigators recorded a large and disproportionate imbalance in missing survival data between its arms … which they said limits interpretation. | limited (S010) | FALSE ALARM | keeps the hedge as "limits interpretation"; only "limited" is on the list |
| 11 | cdk46 | 0ed90b2c | 2.7 months of median difference, a hazard ratio of 0.96, an interval running through the no-effect line, and a sensitivity analysis that moved the estimate to 0.92 without changing the conclusion. | limited (S010) | FALSE ALARM | the sentence states the null result and its uncertainty ("an interval running through the no-effect line") |
| 12 | cdk46 | 6e9acad8 | Restored 1 September from the full text — the clinical benefit rate at six months of 58.6% in both arms … and the authors' conclusion that both Ribociclib and palbociclib have similar CBR, PFS and toxicity profile . | likely (S017) | FALSE ALARM | "likely" is in "2.85 more likely to survive", an odds statement about menopausal status, not the sentence's claim |
| 13 | cdk46 | a1a8f104 | MONALEESA-2's test was one-sided, and the paper says so itself. | hypothesis (S005) | FALSE ALARM | "null hypothesis" is a statistical term, not a hedge |

**REAL 0, FALSE ALARM 13.** Two causes cover all 13: a hedge in the span that
qualifies a different endpoint or clause than the one the sentence states (1–4,
6, 7, 9, 12), and a hedge word used as a technical term or kept in another form
(5, 8, 10, 11, 13). Both are limits of a word-level rule, recorded for the next
revision of B19's lists; neither is a fault in the published text.

## B21 — holdings sentences (WARN)

| issue | row | sentence | warnings | view |
|---|---|---|---|---|
| cdk46 | 4962b9d1 | We could not obtain PALMARES-2 itself. | holdings sentence not declared to the store (the text names S011, S021); store check not evaluated (names 2 sources; not decidable) | metadata gap, not a text problem. The row has no bucket and predates `rests_on_store`. "PALMARES-2 itself" is the study, S011 (fragment_only); declared as S011, the store check PASSES. |
| deskilling | 70c1e16d | We have not opened Sparrow, Liu and Wegner's 2011 Science paper, which is paywalled. | holdings sentence not declared to the store (the text names S010); store check not evaluated (document_class not set on this source) | metadata gap, not a text problem. S010 is blocked, which satisfies "have not opened"; with `rests_on_store: ["S010"]` and a document_class it would PASS. |
