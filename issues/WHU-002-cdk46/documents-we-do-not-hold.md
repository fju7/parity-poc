# WHU-002 — documents we do not hold

Ten journal papers and two conference abstracts return 403, 502 or a cookie
wall to a plain fetch. Until each is in the library, the ledger permits only
the figures a retrieval literally returned, attributed to that retrieval, and
NO characterisation of the document.

For each: open it with whatever access you have, save the PDF, then

    cd /Users/fredugast/Projects/parity-poc-repo/backend
    ../backend/venv/bin/python3 scripts/whatholdsup/source_store.py cdk46 \
      add <SID> <path-to-pdf> --url <url> --via "how you got it"

It refuses anything whose text does not identify it as that document, so a
wrong or walled file cannot go in by accident.

## S002 — MONARCH 3 — abemaciclib as initial therapy. J Clin Oncol, 2017

    state  fragment_only
    url    https://ascopubs.org/doi/10.1200/JCO.2017.75.6155
    we use it for: Primary progression-free survival: median not reached vs 14.7 months, HR 0.54 (95% CI 0.41–0.72), P = .000021.

## S003 — MONARCH 3 — final overall survival. Ann Oncol, 2024

    state  fragment_only
    url    https://www.annalsofoncology.org/article/S0923-7534(24)00139-X/fulltext
    we use it for: 66.8 vs 53.7 months, HR 0.804 (95% CI 0.637–1.015), two-sided P = .0664, at 8.1 years median follow-up. Not statistically significant. The trial maintained a cumulative two-sided type I error of 0.05 by the Lan-DeMets method with an O’Brien

## S004 — MONALEESA-2 — updated results. Ann Oncol, 2018

    state  blocked
    url    https://pubmed.ncbi.nlm.nih.gov/29718092/
    we use it for: Progression-free survival 25.3 vs 16.0 months, HR 0.568 (95% CI 0.457–0.704).

## S005 — MONALEESA-2 — overall survival with ribociclib plus letrozole. N Engl J Med, 2022

    state  blocked
    url    https://www.nejm.org/doi/full/10.1056/NEJMoa2114663
    we use it for: 63.9 vs 51.4 months, HR 0.76 (95% CI 0.63–0.93), two-sided P = 0.008, at 80 months median follow-up. The only overall-survival result among the three first-line postmenopausal aromatase-inhibitor trials that reached significance.

## S006 — MONALEESA-7 — ribociclib plus endocrine therapy in premenopausal women. Lancet Oncol, 2018

    state  blocked
    url    https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045(18)30292-4/abstract
    we use it for: Progression-free survival 23.8 vs 13.0 months, HR 0.55, P < .0001.

## S007 — MONALEESA-7 — overall survival. N Engl J Med, 2019

    state  fragment_only
    url    https://www.nejm.org/doi/full/10.1056/NEJMoa1903765
    we use it for: The protocol-specified interim analysis: median not reached vs 40.9 months, HR 0.71 (95% CI 0.54–0.95), one-sided P = .00973 against a prespecified stopping boundary of P = .01018, at 34.6 months median follow-up. The direction of the test

## S008 — MONALEESA-7 — updated overall survival. Clin Cancer Res, 2022;28:851

    state  fragment_only
    url    https://aacrjournals.org/clincancerres/article/28/5/851/681697/Updated-Overall-Survival-of-Ribociclib-plus
    we use it for: The exploratory extended follow-up at 53.5 months: 58.7 vs 48.0 months, HR 0.76 (95% CI 0.61–0.96). The authors describe it as exploratory in those words. It is not the figure this page leads with for MONALEESA-7 and it is not on the interv

## S009 — PALOMA-2 — palbociclib and letrozole. N Engl J Med, 2016

    state  fragment_only
    url    https://www.nejm.org/doi/full/10.1056/NEJMoa1607303
    we use it for: Primary progression-free survival: 24.8 vs 14.5 months, HR 0.58 (95% CI 0.46–0.72), two-sided P < .001. These are the figures the paper prints, and they are what the table shows. The unrounded 0.576 (0.463–0.718) appears in the 2019 extende

## S010 — PALOMA-2 — final overall survival. J Clin Oncol, 2024

    state  fragment_only
    url    https://pmc.ncbi.nlm.nih.gov/articles/PMC10950136/
    we use it for: 53.9 vs 51.2 months, HR 0.956 (95% CI 0.777–1.177), one-sided P = .34, at 90.1 months median follow-up. Source also of the missing-data imbalance (unknown survival status 13.3% vs 21.2%) and of the investigators’ recovered-data sensitivity

## S011 — PALMARES-2 — real-world comparison of first-line palbociclib, ribociclib and abemaciclib. Ann Oncol, April 2025

    state  fragment_only
    url    https://www.annalsofoncology.org/article/S0923-7534(25)00134-6/fulltext
    we use it for: 1,982 patients, eighteen Italian centres, inverse-probability weighting. Progression-free survival: abemaciclib vs palbociclib aHR 0.76 (0.63–0.92), p = 0.004; ribociclib vs palbociclib 0.83 (0.73–0.95), p = 0.007; abemaciclib vs ribociclib

## S016 — P-VERIFY — comparative overall survival of CDK4/6 inhibitors plus an aromatase inhibitor, US real-world setting, 2025

    state  blocked
    url    https://pubmed.ncbi.nlm.nih.gov/39754979/
    we use it for: The Palbociclib Verifying Evidence of Real-world Impact study. 9,146 patients from the Flatiron Health record database — 6,831 on palbociclib, 1,279 on ribociclib, 1,036 on abemaciclib — with stabilised inverse-probability weighting. Overal

## S023 — MONALEESA-7 — overall survival, ASCO 2019 late-breaking abstract LBA1008. J Clin Oncol 37, no. 18_suppl.

    state  fragment_only
    url    https://ascopubs.org/doi/abs/10.1200/JCO.2019.37.18_suppl.LBA1008
    we use it for: One sentence, quoted on the page: “statistical comparison was made by 1-sided stratified log-rank test”. This entry exists because that quotation was on the page with NO SOURCE ENTRY AT ALL — it was found by the quotation check on 31 August, which asks of every quoted passage which source it came fr…
