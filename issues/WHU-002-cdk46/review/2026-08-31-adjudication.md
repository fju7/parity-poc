# WHU-002 — the 31 August corrections

Nobody reviewed this page on 31 August either. These are findings from two of
the page's own checks — the re-gate of 30 August and the quotation check written
on 31 August — plus one thing the quotation check turned up that nothing else
had looked at. All three are anchored: each rests on a source that was opened
and read on the day the change was made, not on a memory of it.

Labels CORR-06..CORR-08 are cited by `changes.json`.

---

## CORR-06 — a registry number that belonged to a different trial

**The finding.** The MONALEESA-7 source note (S007) cited the ASCO 2019 abstract
for the direction of the overall-survival test, and said the journal paper was
behind a wall we could not open. When CORR-02 added registry confirmations on
30 August it attached NCT01740427 to this sentence. That is PALOMA-2's registry
number. MONALEESA-7 is NCT02278120.

Reported by the re-gate of 30 August as a THIRD_PARTY finding; it is one of two
findings in that run that were real, out of nine that were checkable.

**What the right registry says**, read from the ClinicalTrials.gov v2 API on
31 August, `resultsSection.outcomeMeasuresModule`, Overall Survival (OS):

- p = 0.00973, `pValueComment` verbatim: **"One-sided stratified log-rank test"**
- statistical method: Log Rank; Cox proportional hazard 0.712, 95% CI 0.535–0.948

So the substance the sentence asserted was right and the citation behind it was
wrong — the worst combination, because nothing downstream of the sentence looks
wrong and the reader who follows the link lands on another trial.

**Disposition** — ACCEPT.

**Change.** The note now cites NCT02278120, quotes the registry's own annotation,
and gives the posted p-value. **S022 added** for that record: the correction
would otherwise have been a citation with no source entry behind it, which is
the failure mode `source_ledger` exists to catch.

A second sentence in the same note said the 0.712 hazard ratio "appears in
conference reporting and not in the publication this page cites". That was
written before the registry was read. 0.712 is the Cox hazard ratio in the
registry posting the sentence now cites, one line above. Corrected to say so,
with the interval.

**Sources considered** — S022 (new), S007.

---

## CORR-07 — a row label read as a quotation

**The finding.** The page carried, inside quotation marks, the phrase
`"year of updated data 2023"`, attributed to Table 1 of the network
meta-analysis. No such string is in the paper. "Year of updated data" is a row
label; the row reads `2022 2022 2022 2023 2021 2021 2020` across columns that
run PALOMA-2, MONALEESA-2, MONALEESA-7, MONARCH 3, PALOMA-3, MONALEESA-3,
MONARCH 2 — so the 2023 that belongs to MONARCH 3 is the fourth cell after the
label, not the word next to it. Read from the Europe PMC full text of
PMC10850180 on 31 August and recorded as Q-16.

Found by the quotation check (`quotations.py`), written on 31 August, on its
first run over this page. This is the class of error the check was written for:
a quotation that is not a misreading of the source's meaning — the meaning is
right, MONARCH 3's updated data is from 2023 — but is not a thing the source
says in those words.

**Disposition** — ACCEPT.

**Change.** The sentence now names the row and states what it gives, instead of
quoting a string that does not exist: *its "Year of updated data" row gives 2023
for that trial*. The row label is quoted because the row label is verbatim.

**Sources considered** — S015.

---

## CORR-08 — the source gives two different median follow-ups

**The finding.** The page prints the network meta-analysis's median follow-up as
73.3 months in two places. Its abstract gives 73.3; its results section gives
70.2. Both give the same range, 48.7–97.2 months. Raised by the re-gate of
30 August; it is the second of that run's two real findings.

**What the paper says**, read 31 August:

- abstract: "Median follow-up was 73.3 months (range: 48.7–97.2 months)."
- results: "The median follow-up was 70.2 months (range: 48.7–97.2 months)."

**How that was established, because it nearly was not.** The re-gate raised 70.2
as a model finding. A model finding is not a figure. Four retrievals were run
before this went on the page:

1. nature.com article — returned both sentences verbatim.
2. nature.com article, asked whether the literal string "70.2" occurs — returned
   **"This string does not appear in the document."** The same answer said Table 1
   was "not fully displayed in the provided content", i.e. it had received a
   truncated conversion and was reporting absence from a document it did not
   fully have.
3. nature.com article, asked which sections it had received — listed Results
   present, quoted its opening words, and returned the sentence verbatim again.
4. Europe PMC full-text XML for PMC10850180, a different host and a different
   representation — returned both sentences verbatim and stated each string
   occurs exactly once.

Three confirmations across two hosts; the one denial came from a retrieval that
demonstrably did not hold the whole document. **An absence reported by a
retrieval that got a truncated document is not evidence of absence** — the same
shape as the SOURCE role returning WRONG_VALUE when retrieval failed, which is
the incident this whole apparatus was built after. Had the second read been the
only check, the honest conclusion would have been that the re-gate invented 70.2
and the sentence would have come off the page.

nature.com's Table 1 URL is disallowed by robots and PMC's HTML is behind a
CAPTCHA, so neither was used; the table was read through Europe PMC.

We have not established which is correct and we are not in a position to. The
range is identical in both, so this is not two different datasets; it is one
dataset with two summary statistics printed for it, and only the paper's authors
know which is the typo.

**Disposition** — ACCEPT, as a disclosure rather than a correction.

**Change.** The page keeps the abstract's figure, because that is the figure a
reader who opens the paper meets first and the one the page has always used, and
now says in the same breath that the results section gives 70.2 and that the
discrepancy is the source's own. Printing one figure from a source that prints
two, silently, is the thing this page exists not to do.

The alternative — dropping the figure — was considered and rejected: the pooled
follow-up is what makes the meta-analysis's null result readable, and a reader
cannot weigh "no significant difference" without knowing over how long.

**Sources considered** — S015.

---

## CORR-09 — the corrections above, told to a reader

**The finding.** CORR-06, CORR-07 and CORR-08 were all recorded in the
repository and none of them was on the page. All three were live. Fetched from
whatholdsup.org/cdk46 on 31 August:

    NCT01740427                  LIVE   <- MONALEESA-7's note, wrong trial
    year of updated data 2023    LIVE   <- a string that is not in the paper
    73.3                         LIVE   } printed alone, no mention of the
    70.2                         absent }  70.2 the same source also gives

This page carries a publication history and a dated correction record, and it
had corrections it was not putting in them. A correction record that holds
everything an outside reader found and nothing our own checks found is not a
correction record, it is a record of being caught.

**Disposition** — ACCEPT.

**Change.** A "Corrected 31 August 2026, by our own checks" paragraph in the
updates section, naming all three, saying which check found each, and saying
that none was found by a reader and all three had been live for a day. Also
written into `corrections.md`. The quotation of our own withdrawn wording is
recorded as Q-17, `kind: rhetorical` — asking the matcher to confirm a string we
are on the record as having invented would be incoherent.

**What this cost.** The paragraph adds sentences the gate has never read, so it
raises the cost of the run that clears this page. That is the correct order:
the page says what is true and the gate is paid to check it, not the other way
round. On 30 August this issue got that order backwards — a correct author name
sat unpublished for a day because publishing it meant paying for a gate run —
and it is written into the correction above as the error it was.

**Sources considered** — the live page itself.
