# WHU-002 — the 30 August corrections

Nobody reviewed this page on 30 August. These are our own findings, made while
clearing the preflight so that a correction already written a day earlier could
reach the live site. Two of them are the page's own controls finally being
listened to rather than deferred, and both found real errors that had been live
for two days.

Labels CORR-01..CORR-05 are cited by `changes.json`.

---

## CORR-01 — no randomised trial had compared them, except the two that had

**The finding.** This page said in four places that no randomised trial had
compared any of these three drugs against another, and that nobody had run a
head-to-head trial. Two exist, both ribociclib against palbociclib:

- **Shaaban MHA, Elbaiomy MA, Eltantawy A, Abdel-Fattah A-HE, Shamaa SSA.**
  *Comparing ribociclib versus palbociclib as a second line treatment in
  combination with fulvestrant in metastatic breast cancer: a randomized clinical
  trial.* Asian Pac J Cancer Prev 2024;25(9):3039–3049,
  doi 10.31557/APJCP.2024.25.9.3039. Randomised, open-label, phase III. Clinical
  benefit rate at six months 58.6% in both arms; median progression-free survival
  12.69 against 13.67 months. Their conclusion, verbatim: "Both Ribociclib and
  palbociclib have similar CBR, PFS and toxicity profile."
- **HARMONIA**, NCT05207709. Phase III, randomised, parallel, open label, same
  pair, HER2-enriched subtype. Opened 28 March 2022. **Terminated**, 61 patients
  enrolled, completion recorded 26 March 2026. No results publication found.

**Why it happened.** The page took NCCN's sentence — "the CDK4/6 inhibitors have
not been directly compared in clinical trials" — verified that the guideline says
it, and printed it unscoped as a claim about the world. The guideline's sentence
is about first-line aromatase-inhibitor combinations and is accurate in that
scope. Neither trial is in that setting. Verifying that a source says X is not
verifying X, and this is the second time this issue has made that exact error;
`inherited.json` was created after the first time and IC-001 has been sitting in
it flagged as `quoted` ever since.

**Disposition** — ACCEPT, in full.

**Change.** All four sentences rewritten. The claim that survives is narrower and
is now what the page says: no randomised trial has compared **abemaciclib**
against either of the other two, in any setting, which is the comparison the
category difference actually turns on. Both trials are reported in the
comparative-evidence section with their figures and their limits, both are in the
source list, and the footer carries the correction.

**Sources considered** — S017 (new, abstract and article record only), S018 (new,
registry record), S001.

---

## CORR-02 — the test direction was in the registry the whole time

**The finding.** This page said, across seven sentences, that it could not
establish whether MONALEESA-2's final overall-survival p-value was one-sided or
two-sided, and named a paywalled statistical section as the reason. The trial's
own results posting on ClinicalTrials.gov (NCT01958021) states it: overall
survival "was compared using a log-rank test at **one-sided cumulative 2.5% level
of significance**", with HR 0.765 (95% CI 0.628–0.932), p = 0.004. PALOMA-2's
posting (NCT01740427) annotates each of its log-rank analyses "1-sided p-value
from the stratified log-rank test", which confirms from a second, independent
route what the page had only from an ASCO 2019 abstract.

**Why it happened.** Two earlier versions were wrong in opposite directions — one
asserted two-sided without a source, the next said the direction could not be
determined. Both searched journals. A journal is a list of what got published; a
registry is a list of what was started and what was reported. This page had been
searching only the first. The preflight check that asks what registry was
searched before a sentence says something cannot be known had been reporting
these seven sentences for two days.

**Disposition** — ACCEPT.

**Change.** The page now states the direction and level, sourced to the registry,
and says plainly that it was wrong twice. What it still does not print is the
critical value at the final look if alpha had been spent at an interim, because
the posting does not give that. S019, S020 and S021 added; S004 and S005 now
declare `characterisation_supported_by: S019`, because the claim about
MONALEESA-2's test is sourced to the registry and not to the papers, which remain
unread.

**Sources considered** — S019, S020, S021 (all new), S004, S005.

---

## CORR-03 — wrong about the corrigendum in both directions

**The finding.** The page first said the MONARCH 3 corrigendum (Ann Oncol
2025;36:1556) sat behind a paywall, then corrected itself to say it was open
access and the block was a limit of our tooling. Europe PMC's record for it
(PMID 41093689) marks it not open access and offers a single route, the
publisher's DOI, labelled "Subscription required". The first version was right.

**Disposition** — ACCEPT.

**Change.** Both the source note and the footer now say what Europe PMC's record
says, and record that the page has been wrong about this in both directions. The
corrigendum is still unread and still disclosed as unread.

---

## CORR-04 — the email claimed an absence the page did not

**The finding.** The announcement email said "None comes from a news report, and
none from a guideline's summary of a trial" — a sourcing claim with no matching
sentence on the page. This is the check written after the 29 August send, which
went out saying every figure came from a trial publication or a drug label while
quoting two observational studies.

**Disposition** — ACCEPT.

**Change.** The unmatched sentence is gone, and the page and both email formats
now carry one identical sourcing sentence. Subscribers hold the older email; the
correction will be carried at the top of the next one.

---

## CORR-05 — a name that was fixed a day ago and never reached a reader

**The finding.** The live page named the wrong first author of the 2018
*npj Breast Cancer* power paper. The correct name, Marie-Laure Tanguy, was
verified against the author list on 29 August and written into the repository the
same day. It did not go live, because publishing it meant re-opening this issue's
checks and we had decided not to spend on that.

**Disposition** — ACCEPT. The decision to defer was reasonable on cost and wrong
on substance: an acknowledged divergence is a note to ourselves, and a reader
looking up the citation had a wrong name in front of them for a day.

**Change.** Live with this correction. Recorded in the footer as its own item
rather than folded into the others.
