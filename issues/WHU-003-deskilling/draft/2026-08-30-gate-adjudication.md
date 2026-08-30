# Page gate, run 1 of 2 — adjudication

Draft: `issues/WHU-003-deskilling/draft/deskilling.html`
Gate sha judged: `637d53be8f9fd4af456b3d073fac825a38c0737952ba5bac406675c4af9ffb2b`
Run: 2026-08-30T14:23Z · 98 claims · 69 VERIFIED, 22 NOT_FOUND, 7 WRONG_VALUE · 9 objections · 5 inferences
Cost: $10.89, 27 API calls, 134 web searches. Cap: `RUNS_PER_CYCLE = 2`. **This is run 1. One run remains.**

Scope, as set by the operator: *"What I want to make sure of is that there are no factual errors and that
inferences are validated. What we found before is that there is an endless loop when we start getting into
the way things are expressed and words used that can be interpreted differently by different people. Our
touchstone is accuracy and fairness but there is a limit to what we can reasonably accomplish."*

Everything below was adjudicated in a single pass and every edit made at once, because that is what the cap
is for.

---

## 1. Findings acted on — the page changed

| # | Finding | What was wrong | What the page says now |
|---|---|---|---|
| 1 | **Ke author count** (c97) | Page: "Ke and sixteen colleagues" and "Seventeen authors". The list is sixteen names. `attributions.json` had transcribed all sixteen correctly and then written "seventeen in total" underneath them. | "Ke and fifteen colleagues"; "Sixteen authors in all". Recounted against PubMed PMID 42174254, the Nature Medicine page and three institutional repositories. |
| 2 | **Cytology figures** (c28, extended) | Page: "cut cytology workload by 80% to 85% and reduced the number of laboratories from 45 to 8." Both numbers came from the scoping review's summary of a 2022 paper we never opened — under a sentence promising every study in that list was read at source. The RCPath report, citing Public Health England, says ~70% and 48 laboratories. The gate caught the first error; checking it caught the second, which the gate did not. | "about 70%" and "48 to 8", quoted from the RCPath report (new source S039), with the review's differing figures and our failure to reach its citation stated in the same sentence. |
| 3 | **Pathology bullet** (no gate finding; found while checking c28's neighbour) | Same defect: 28 pathologists and 7% were taken from the review, not from a paper. There was no source entry for it at all. | Attributed to Rosbach, Ganz, Ammeling, Riener & Aubreville (arXiv 2411.00998), read at source (new source S038), with the time-pressure finding stated correctly: time pressure raised the *severity* of automation bias, not its frequency. |
| 4 | **"It has been replicated"** (objection 7) | Three experiments in one preprint by one team is internal replication. The word implies an independent group. | "it held in all three experiments — which is internal replication by one team in one preprint, not confirmation by anybody else." |
| 5 | **Eye travel** (inference 1) | The page contrasted the *overall* 6.5% with the novice 3% using "smaller still", which implies the overall figure is the experienced one. It is not, and the experienced figure was never stated in the body. | All three now stated: overall ~6.5%, experienced 247.89→227.09 cm (~8%), novice 255.66→247.89 cm (~3%). |
| 6 | **The travel thesis** (coverage c95, plus our own check of Time) | **The most serious finding of the run.** The page said *"none of it crossed the boundary."* False. *Time* (13 Aug 2025) carried Osmani's volume-and-fatigue caveat by name, Tucker on automation bias, and called the study observational throughout. The *ASCO Post* quoted the authors on "its observational nature" and on "factors other than the implementation of AI". *Healthgrades* called it "a retrospective observational study" and carried an expert saying the concern "remains hypothetical rather than proven". *Communications of the ACM*, which we said carried no limitations, carries several of its own. | Rewritten as two paragraphs: the general caution travelled; the *specific* did not — not one outlet named the Polish screening suspension, the missing withdrawal times, the eleven limitations as a body, or the authors' call for randomised crossover trials. Three new coverage sources (S040–S042), all read at source. The section standfirst and the footer's "claim we made and withdrew" both updated. |
| 7 | **Fortune's analogy** (objection 2) | Body said "an automation analogy"; our own source note said "an aviation analogy". | "an aviation analogy", matching the note. |
| 8 | **Heudel radiology miscitation** (objection 5) | A serious accusation against named authors, asserted with no quotation. | The review's sentence is now quoted, its reference number named, the mismatch stated in particulars, and the date we read the full text given. Evidence from source ledger S029, which holds the sentence verbatim from the PDF. |
| 9 | **Dratsch spread** (inference 4) | "wrong more often than they were right" from a mean of 45.5% with SD 9.1 — the spread crosses the halfway line. | All three SDs now printed, and the sentence says "on average" and names the spread. |
| 10 | **Confidence interval** (inference 3) | −10.5 to −1.6 given without saying both bounds are below zero. | "both ends below zero" added; a lay reader can now see the interval excludes no-effect. |
| 11 | **Troya timing** (objection 3) | "three years before the deskilling result" — ambiguous between publication and the events. | "three years before the deskilling study was published". |
| 12 | **Stanković sequencing** (objection 4) | The sentence limiting the quote to one paper came after the quote. | Moved before it. |
| 13 | **Heudel's quote subject** (inference 5, redirected) | The review's phrase is about the *evidence* of clinical deskilling. The page attached it to clinical deskilling itself. The quotation was verbatim; its subject was not. | "the evidence of clinical deskilling is 'though scarce, consistent across specialties'". |

## 2. Findings checked and rejected — the page did not change

Recorded in `backend/tests/fixtures/draft_decisions.json` (31 entries) so that run 2 reports them as decided
rather than new.

- **Osmani and "three months"** (c17). The SMC page says it, verbatim, in the source the page cites. The gate read secondary reports of his comments instead of the page.
- **The volume figures, 795 → 1,382** (objections 8 and 9, both SERIOUS). The paper's own limitation 8 gives 1,382 as the *total* post-AI colonoscopies (734 with AI, 648 without) against 795 before. The gate had it as the non-AI subset. **Acting on this would have inserted an arithmetic error and published a correction of a named academic who had it right.**
- **Dratsch, "50 mammograms of which 49 were analysed"** (objection 1 SERIOUS, inference 2 SERIOUS). The Methods state one mammogram was excluded because the sides of the lesions had been switched in the original report. The gate reasoned from the abstract, found no exclusion, and read silence as contradiction. **Acting on this would have deleted a correct fact we had gone to the Methods to get.**
- **Savardi's 32 residents** (c30). The gate read our framing backwards. The page attributes the 32 to the review and prints the true figure of eight in the same paragraph.
- **Liu, 1,060 analysed** (c81). 307 + 585 + 168 = 1,060. The gate reconstructed a third group size from degrees of freedom.
- **Liu, the three effect sizes** (c82). Experiment 3 has both d = −0.42 (solve rate) and d = +0.42 (skip rate). The gate found the second and concluded we had conflated them.
- **Rad Insights, 15 May 2026, Decker J** (c96). Checked at the page: byline "Josh Decker, MD", date line "May 15, 2026", update stamp "July 31, 2026". Both elements the gate called wrong are right; it read the update stamp as the date.
- **The quotation marks on "a multicenter randomized trial"** (objection 6). Already inside `<q>` tags in the body. The gate reads stripped prose, in which `<q>` leaves no mark.
- **"though scarce, consistent across specialties"** (inference 5). Not a transcription error — the review's own words, recorded verbatim in S029 from the PDF. The awkwardness was real and had a different cause, fixed at item 13 above.
- **Eighteen NOT_FOUND findings on paywalled text, figures and supplementary tables** (c12, c13, c14, c18–c21, c41, c45, c94, c73–c78, c80, c91). NOT_FOUND for *access*, not for content. Each was read in the document — the Warwick accepted manuscript, the operator's PDFs of the scoping review and the Norwegian audit, the open-access Troya paper — and each reading is recorded in `sources.json` with sections read and sections not read. The rule that an unread source is not a source that agrees with us cuts both ways: a document the gate cannot open is not evidence against what the document says.
- **Ingebrigtsen & Lukic, first posted 2 July 2025** (c72, c92). Read by the operator in the v1 PDF; S005 records "Submitted 26 June 2025; preprint v1 2 July 2025; v2 23 April 2026". OSF serves only v2 to a machine.

## 3. Left open — needs the operator, or needs time

1. **A possible correction on the colonoscopy study.** *Lancet Gastroenterol Hepatol* 2025 Nov;10(11):e12. Europe PMC returned its homepage; we could not confirm the notice exists or what it touches. Added to watch question **W4** as the most consequential open item on the list — the page's central number comes from that paper.
2. ~~**The scoping review's pathology citation.**~~ **CLOSED 2026-08-30, same day.** The operator re-supplied the review PDF and it was read end to end. The answer is *both*: the review's **body** cites reference 17 — arXiv 2411.00998, the right paper — while its **Table 1** attributes the same 28 pathologists and the same 7% to reference 35, Bellahsen-Harrar et al., *PLOS ONE* 2025;20(8):e0323270, which has eight pathologists, no time-pressure condition and no such figure. Reference 17 itself carries the right arXiv identifier under the wrong first initial, wrong co-authors and a wrong title. Our 2026-08-29 note had transcribed the table correctly and was silent about the body — it had not crossed two rows, as was suspected before the PDF was reopened. The citation mismatch is recorded in the Rosbach source note, with the review's body credited for getting it right; the body paragraph gained one sentence, on a *different* finding the re-read turned up — the review's abstract puts the same pathology experiment at "over 30% of participants" where its body puts it at 7% of judgments. Different denominators, both possibly true, and the larger number is the one in the abstract. Watch question **W8** closed.
3. ~~**Shaw & Nave, "11.7 percentage points"** (c86).~~ **CLOSED 2026-08-30, same day.** The operator read the sentence in the PDF: *"Despite approximately half of System 3 answers being faulty, access to AI increased confidence by 11.7 percentage points (AI-Assisted: M = 77.0%, SE = 1.30%, 95% CI [74.4, 79.6]; Brain-Only: M = 65.3%, SE = 2.21%, 95% CI [61.0, 69.6]; t(202.91) = 4.57, p = 8.55 x 10-6; Hedges' g = 0.54, 95% CI [0.32, 0.77])."* Two means on a 0-100 scale, 77.0 and 65.3, differing by 11.7 exactly, and the paper uses the words "percentage points" itself. **The page is right as printed and nothing changed.** Recorded in `draft_decisions.json` and in source ledger S017. Fourth time on this issue that the deciding document had to be opened by a human, and the fourth time the machine's uncertainty was about access rather than about the fact.
4. **Medscape, 25 August 2025.** The gate's coverage pass reported it carried both framings and the finding that adenomas per colonoscopy did not change significantly — a point worth having. The article returns 402. Left off the page, and recorded in `sources.json` under `not_reached`: an unread source is not a source that agrees with us, and that holds when it would have helped the new claim as readily as when it would have hurt the old one.

## 3b. The process failure this turn exposed

The operator asked why he was being sent back to a PDF he had already supplied. He was right to ask, and the
answer is worse than the first reply I gave him.

**First failure.** S017 recorded that the Shaw & Nave PDF had been read, by whom, on what date, and which page
ranges — but not the sentence carrying the figure. A summary of a document is not the document. When the gate
questioned one number, the ledger could not answer.

**Second failure.** I then told him there was nothing on disk to reopen. The search behind that claim looked in
the working directory and in the three mounted folders and did not look in the session's own upload directory,
where every PDF he had ever attached was still sitting — the scoping review, Shaw & Nave, the Norwegian audit,
Troya. *Not finding something is a statement about where you looked*, and it was reported to him as a statement
about the world. That is the same error class as telling him the issue-two email was unsent because a button
said so.

**The fix, adopted this turn:** `THE_EXTRACT_RULE` in `sources.json`. Any source this page takes a figure or a
quotation from must carry those sentences verbatim in the ledger. Not a page range. The sentences. S029 now
holds nineteen verbatim extracts from the scoping review, including every PRISMA number, both miscited
references, and the table rows. S017 holds the four sentences behind every figure the page prints from it. Both
are marked compliant.

## 4. What this run cost and what it bought

$10.89 bought three real factual errors (the Ke count, the cytology figures, the Dratsch spread), one false
claim about the world corrected (the travel thesis), one unsourced bullet traced to its paper, and four
calibration fixes. It also produced **five SERIOUS findings that were wrong**, two of which would have put a
new error on the page and one of which would have published a correction of a named academic who was right.

That is the argument for the adjudication step, and for the cap. The gate is a source of candidates, not
verdicts — the same rule the counterexample hunter runs under. Every finding above that changed the page was
opened at a primary document first.

## 5. Verification after the edits

- `lint_claims.py` — all STOP checks pass; 8 universal-claim warnings, each previously walked. One new STOP appeared during editing ("Rebolj and colleagues" named on the page without an author-list check) and was cleared by removing the name rather than by asserting a byline nobody had opened.
- One assumption caught in the act: the new Rosbach attribution was first recorded with the first name **Elena**. The arXiv author list says **Emely**. Corrected before it reached anything, and the false start left in `attributions.json` on purpose.
- Run 2 of 2 remains, to confirm.
