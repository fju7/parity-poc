# melanoma — source advocate, 2026-09-01

One section per item. Each must be closed before this issue can
publish. An open item blocks; an item closed "no merit", with the
reason on the record, does not.

For an OBJECTION, from a source a machine could read:

    MERIT:  yes | partly | no   — and why, citing what you read
    EFFECT: changes | narrows | none
    DID:    what actually changed, or nothing and why

For a QUESTION, from a source only a person is permitted to read:

    ANSWERED BY: a person's name. Not "the team", not a role.
    ON:          the date they opened the document
    ANSWER:      what it says, quoted
    LOCATOR:     section, table or page
    EFFECT:      changes | narrows | none
    DID:         what changed

The second form exists because of NCCN v6.2026: one document, readable
by no automated check here, holding the fact that decided the piece.
Everything else on the page could be machine-checked, so the pipeline
behaved as though the page had been checked. Where only a person can
read the source, the person is the check.


---

## S001 — Merck & Moderna — Phase 3 INTerpath-001 met RFS and DMFS endpoints
*Advocate: the authors of Merck & Moderna — Phase 3 INTerpath-001 met RFS and DMFS endpoints*  
*Ledger state: full_text_held*  

### S001-01 — SERIOUS / NARROWS

**We say.** The Phase 3 announcement reports no numerical Phase 3 results.

**They object.** The press release does not merely omit numbers silently — it affirmatively characterises the magnitude of the results in language that goes beyond 'met its endpoint', and the page does not quote or engage with that language.

**Their document says.** "First and only combination regimen to demonstrate statistically significant and clinically meaningful improvements in RFS and DMFS compared to KEYTRUDA alone" — Merck press release, headline bullet / opening summary block.
  — *Headline bullet points / opening summary, Merck press release, 19 August 2026*

**Why it matters.** The page's framing is that the announcement says only 'met its endpoint' — the floor of what could be said. But the announcement also says the improvements were 'statistically significant and clinically meaningful', which is a second-order characterisation of magnitude, not merely a binary pass/fail. The page's conclusion that the announcement provides no information beyond the floor is therefore too broad; the announcement does provide a qualitative magnitude claim, even if it withholds the hazard ratio.

MERIT:  no — The objection is that the page 'does not quote or engage with' the release's 'statistically significant and clinically meaningful'. The page quotes that exact phrase, inside the sentence this objection is about: 'Of the study it is actually announcing it says only that the endpoints were met, "statistically significant and clinically meaningful".' It is recorded as Q-05 in quotations.json, matched verbatim against S001.
EFFECT: none
DID:    Nothing. The premise is false against the page as it stands.


### S001-02 — SERIOUS / NARROWS

**We say.** This is why the absence of a hazard ratio in the Phase 3 announcement matters: "met its endpoint" is the floor of what could be said, not a summary of what was found.

**They object.** The press release does not stop at 'met its endpoint'; it adds 'statistically significant and clinically meaningful improvements', which the page treats as absent when constructing its argument about the floor.

**Their document says.** "statistically significant and clinically meaningful improvements in RFS and DMFS compared to KEYTRUDA alone" — Merck press release, headline bullet and body.
  — *Headline bullet points and body paragraph, Merck press release, 19 August 2026*

**Why it matters.** The page's argument is built on the premise that 'met its endpoint' is the entirety of what the announcement conveys about results. That premise is factually incomplete: the announcement also characterises the improvements as both statistically significant and clinically meaningful. The page's conclusion — that the announcement tells us nothing beyond the binary floor — does not survive as written; it survives only in the narrower form that the announcement withholds the numerical hazard ratio.

MERIT:  no — Same phrase, same sentence, same quotation record. The page's argument is not that the release says nothing beyond the binary; it is that the release gives no NUMBER, which the very next sentence enumerates: 'No hazard ratio, no interval, no p-value, no percentage.'
EFFECT: none
DID:    Nothing.


### S001-03 — MINOR / NONE

**We say.** We had called the announcement one that

**They object.** This sentence is incomplete as supplied, so no specific factual claim can be checked; however, to the extent it characterises the announcement as one that withholds all qualitative description of benefit, the press release's own language ('statistically significant and clinically meaningful') is the fact the page must engage with before that characterisation can stand.

**Their document says.** "statistically significant and clinically meaningful improvements in RFS and DMFS" — Merck press release, headline bullet.
  — *Headline bullet points, Merck press release, 19 August 2026*

**Why it matters.** Because the sentence is truncated, the severity is limited; but if the missing completion characterises the announcement as purely binary or uninformative about magnitude, the press release's qualitative magnitude language is the answer the page must address.

MERIT:  no — The sentence the advocate was given — 'We had called the announcement one that' — is a fragment, and it is a fragment of the CHANGE LOG. Two defects met here: the extractor was ending sentences at source-file line breaks, so hand-wrapped paragraphs shredded; and the advocate was reading the change log as though it were the article. Both fixed. There is no live claim to answer.
EFFECT: none
DID:    source_ledger.plain marks block boundaries with a sentinel instead of a newline, and the advocate reads source_ledger.body_only.


---

## S002 — Merck & Moderna — five-year KEYNOTE-942 data, ASCO 2026
*Advocate: the authors of Merck & Moderna — five-year KEYNOTE-942 data, ASCO 2026*  
*Ledger state: abstract_held*  

### S002-04 — SERIOUS / NARROWS

**We say.** it called the trial's two endpoints co-primary when one is primary and one key secondary

**They object.** Our document is unambiguous on this point and the page's characterisation of the summary's error is correct, but the error is the summary's, not ours — our press release and the JCO paper both state exactly what the page says they should: one primary endpoint (RFS) and one key secondary endpoint (DMFS).

**Their document says.** "The primary endpoint is RFS… Intismeran autogene in combination with KEYTRUDA also continued to demonstrate a meaningful improvement in distant metastasis-free survival (DMFS), a key secondary endpoint" — and the JCO abstract: "Primary endpoint was RFS; secondary endpoints included DMFS and safety."
  — *Merck/Moderna ASCO 2026 press release, 'About KEYNOTE-942' section; JCO abstract (ASCO 2026, 44:16_suppl:9500), Methods*

**Why it matters.** The page correctly identifies the summary's error, but should note that the error is confined to the summary and is directly contradicted by the body of our document — the body cannot be faulted for the summary's misstatement, and any conclusion that our document itself conflates the endpoints is wrong.

MERIT:  no — The advocate agrees with the page ('the page's characterisation of the summary's error is correct') and objects only that the error belongs to a summary rather than to the body. The page says exactly that. The sentence is also a change-log entry, recording a correction already made.
EFFECT: none
DID:    Nothing.


### S002-05 — SERIOUS / NARROWS

**We say.** it said the Phase 3 was blinded against 'exactly' a bias its own investigator-assessed endpoint still carries

**They object.** Our document does not claim the Phase 3 eliminates investigator-assessment bias from KEYNOTE-942; it describes INTerpath-001 as 'double-blind, placebo- and active-comparator-controlled' — a design feature of the Phase 3, not a retroactive correction of the Phase 2b — and KEYNOTE-942's RFS is explicitly described throughout as investigator-assessed.

**Their document says.** "INTerpath-001 is a randomized, double-blind, placebo- and active-comparator-controlled global Phase 3 trial" (Merck INTerpath-001 press release, 19 Aug 2026); KEYNOTE-942 primary analysis slide deck (ASCO 2023): "The primary end point of this study was the investigator's assessment of RFS."
  — *Merck INTerpath-001 press release, 'About INTerpath-001' section; KEYNOTE-942 primary analysis slide deck (ASCO 2023), Methods*

**Why it matters.** If the page concludes that our document overclaims blinding as a solution to investigator-assessment bias in KEYNOTE-942 itself, that conclusion is not supported: our document never applies the Phase 3 blinding retroactively to the Phase 2b endpoint; the two trials are described separately and the Phase 2b's open-label, investigator-assessed design is stated plainly.

MERIT:  no — Also a change-log entry, and the advocate's own reading of it agrees with ours: the release describes the Phase 3 as double-blind and does not apply that retroactively to the Phase 2b endpoint, which is what our correction says we had wrongly implied.
EFFECT: none
DID:    Nothing.


### S002-06 — SERIOUS / CHANGES

**We say.** it credited the five-year data with clearing the no-effect line when the body says year three

**They object.** Our document does not claim the five-year data is the first analysis to clear the no-effect line; the RFS confidence interval already excluded 1.0 at the three-year update (HR 0.510; 95% CI 0.288–0.906) and again at five years (HR 0.510; 95% CI 0.294–0.887), and the five-year press release describes the result as 'sustained improvement,' not a new crossing.

**Their document says.** Three-year: "HR, 0.510; 95% CI, 0.288-0.906; 2-sided nominal P value, .019" (JCO Oncology Advances, three-year update). Five-year: "reducing the risk of recurrence or death… HR=0.510; [95% CI, 0.294–0.887]" described as 'continued to prolong' and 'sustained improvement' (Merck ASCO 2026 press release, headline and body).
  — *Merck ASCO 2026 press release, headline bullet and 'About KEYNOTE-942' section; JCO Oncology Advances three-year update (NCT03897881), Results*

**Why it matters.** If the page's summary credits the five-year data with the first exclusion of the null, that is factually wrong: the upper bound of the CI fell below 1.0 at the three-year analysis. Our document's body explicitly frames the five-year result as a continuation, not a new threshold crossing. A conclusion built on 'the five-year data finally cleared the no-effect line' does not survive.

MERIT:  no — settled from this repository's own history, not from a source.
        The correction entry says: "We had skipped the three-year readout, which
        is where the recurrence interval actually cleared the no-effect line."
        The page before that correction (54b9c88 and 378a976, 26 and 27 August)
        read: "By five years it had tightened to 0.294-0.887 and cleared the
        line." So the page DID credit the five-year data, and the entry
        describes the error it fixed accurately. S007 confirms the three-year
        95% CI was 0.288-0.906, which is where it actually happened.
EFFECT: none
DID:    Nothing. The entry stands as written. Note that the live sentences no
        longer say "cleared the line" at all — S007-17 replaced that with "the
        interval no longer crossed it", because the three-year analysis was
        descriptive. The change log keeps the old wording, which is what a
        record of a correction is for.


### S002-07 — MINOR / NONE

**We say.** it twice described a study that has released no effect size as having published nothing

**They object.** Our document (the KEYNOTE-942 five-year press release and simultaneous JCO paper) is not the study described as having 'published nothing' — the page appears to be referring to INTerpath-001, whose topline readout (19 August 2026) explicitly states that effect-size data have not yet been disclosed and will be presented at a future medical meeting, which is precisely what our document says.

**Their document says.** "The Companies plan to present data at an upcoming international medical meeting" (Merck INTerpath-001 topline press release, 19 Aug 2026); "Magnitude of benefit has not been disclosed" (KOL Pulse INTerpath-001 profile). Our ASCO 2026 press release does not claim INTerpath-001 has published an effect size.
  — *Merck INTerpath-001 topline press release, 19 August 2026, 'About INTerpath-001' section; Merck ASCO 2026 KEYNOTE-942 press release, 1 June 2026*

**Why it matters.** The page's characterisation that the summary wrongly says INTerpath-001 'published nothing' when in fact it released a topline result (positive RFS and DMFS, no magnitude) is a framing dispute: a topline with no effect size is not a publication of results in the conventional sense, and our document does not misrepresent this. The conclusion stands but the framing is imprecise.

MERIT:  no — A change-log entry. The advocate's point — that a topline with no effect size is not 'publishing nothing' — is the correction we already made and printed.
EFFECT: none
DID:    Nothing.


### S002-08 — MINOR / NONE

**We say.** the exploratory OS figure HR 0.471 (0.165–1.345) reported as 'n=14'

**They object.** Our document reports the OS HR as 0.471 (95% CI 0.165–1.345) and the total death count as 14 across both arms combined, and explicitly labels OS as an exploratory endpoint to which no alpha was assigned — the page's use of 'n=14' as a descriptor of the OS analysis is accurate but potentially misleading if read as the denominator of the HR calculation rather than the total event count across 157 randomised patients.

**Their document says.** "Intismeran autogene in combination with KEYTRUDA demonstrated an encouraging trend toward overall survival in an exploratory analysis compared to KEYTRUDA alone (HR=0.471; [95% CI, 0.165–1.345])" (Merck ASCO 2026 press release, headline bullet); "Overall survival is immature — only 14 deaths total" (intismeranautogene.ai editorial visualization, citing the JCO paper); JCO abstract: "Exploratory endpoints included OS. No alpha was assigned to this analysis."
  — *Merck ASCO 2026 press release, headline bullet; JCO abstract (ASCO 2026, 44:16_suppl:9500), Methods; ecancer.org report citing JCO: 'Seven patients in each treatment group died during follow-up'*

**Why it matters.** The figures are correct. The objection is that 'n=14' needs the clarifying context our document provides — that this is 14 total deaths across both arms (7 per arm per ecancer), in a trial of 157 patients, with OS explicitly underpowered and exploratory. Omitting that context does not change the page's conclusion but does change the reader's sense of how immature the OS data are.

MERIT:  no — the editor asked whether the paper states the split explicitly.
        It does: S004, "Overall, 7 of 107 patients (6.5%) in the intismeran plus
        pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab arm died".
        So the label stays. It is the companies' own — S002 prints "n=14"
        literally — and quoting what they published is the point of the section.
EFFECT: none
DID:    Kept the label and made the attribution exact: the release supplies
        "n=14" and does not say fourteen of what; the paper's own sentence,
        quoted on the page as Q-13, supplies the split. Also corrected a gloss
        of my own that said "fourteen deaths in 157 patients" without the
        per-arm breakdown the paper gives.


---

## S003 — KEYNOTE-942: a randomised, phase 2b study — The Lancet, 2024
*Advocate: the investigators and statisticians who published KEYNOTE-942: a randomised, phase 2b study — The Lancet, 2024*  
*Ledger state: abstract_held*  

### S003-09 — SERIOUS / NARROWS

**We say.** When the same data were published in The Lancet, they came with two-sided p = 0.053, although the prespecified analysis was one-sided.

**They object.** The Lancet paper itself reports both the two-sided p = 0.053 and the prespecified one-sided framework in the same document — the paper does not suppress or contradict the one-sided design; the page omits that the paper explicitly states the one-sided p = 0.0266 met the prespecified threshold, making the two-sided figure a supplementary presentation, not a substitution.

**Their document says.** "Recurrence-free survival was longer with combination versus monotherapy (hazard ratio [HR] for recurrence or death, 0·561 [95% CI 0·309–1·017]; two-sided p=0·053)" — and the ASCO abstract of the same primary data states: "HR = 0.561; 95% CI: (0.309, 1.017); 1-sided p-value of 0.0266" confirming the one-sided threshold was met at the prespecified primary analysis.
  — *Results section / Abstract, The Lancet 403(10427):632–644, 2024; corroborated by JCO LBA9503 (ASCO 2023) reporting the same primary data with one-sided p = 0.0266*

**Why it matters.** The page implies the Lancet publication reframed a one-sided result as two-sided, suggesting a post-hoc statistical shift. In fact, the Lancet paper reports both; the one-sided primary endpoint was met (p = 0.0266 vs. prespecified alpha of 0.10 one-sided), and the two-sided p = 0.053 is a conventional supplementary presentation. The conclusion that the result is borderline or that the publication obscured the one-sided design does not survive: the paper discloses both, and the primary endpoint was formally met.

MERIT:  yes — and the evidence was in the library, not in the paper the
        objection pointed at. The advocate cited a prespecified one-sided alpha
        of 0.10. It is not in S003, which we hold only as an abstract. It IS in
        two documents we hold in full: S007 — "The trial was designed with
        approximately 80% power to detect a hazard ratio (HR) of 0.5 with a
        one-sided a of 0.10 after 40 RFS events" — and S008, independently:
        "1-sided alpha of 0.1 per protocol". Two sources, agreeing.
EFFECT: changes
DID:    The paragraph now states the trial's own threshold and what follows from
        it: 0.0266 was inside a prespecified one-sided 0.10 by a wide margin,
        and 0.053 is a near miss only against a 0.05 line this trial never used.
        The section's point is unchanged and better founded — the two p-values
        are the same result — but it no longer leaves a reader to supply 0.05 as
        the threshold. Recorded as Q-11 and Q-12.

        The objection also says The Lancet reports both framings, so our
        sentence implies a shift the paper did not make. That half is NOT closed:
        S003 is abstract_held and the abstract carries neither "one-sided" nor
        "0.0266". The page no longer implies a post-hoc shift, because it now
        names the prespecified design, so nothing turns on it — but if the full
        text is ever held, check whether the paper states the one-sided analysis
        alongside the two-sided p, and say so if it does.


### S003-10 — SERIOUS / CHANGES

**We say.** Source quality scores 3 rather than 5 for the same reason: the claim currently rests on a corporate press release, which the rubric ranks as industry analysis, not the peer-reviewed publication it will eventually become.

**They object.** The Lancet paper (PMID 38246194) was published on January 18, 2024 — it is already a peer-reviewed publication, not a forthcoming one; the source metadata in the same document being assessed explicitly identifies it as 'The peer-reviewed publication,' so scoring it as a press release is factually wrong.

**Their document says.** The Lancet, 2024 Feb 17; 403(10427):632–644. doi: 10.1016/S0140-6736(23)02268-7. Published online January 18, 2024. PMID 38246194. The source metadata in the submitted JSON reads: 'type: primary' and 'used_for: The peer-reviewed publication.'
  — *Source metadata field 'used_for' and 'type' in the submitted JSON; publication date confirmed at PubMed PMID 38246194 and The Lancet DOI 10.1016/S0140-6736(23)02268-7*

**Why it matters.** The entire rationale for the score-3 downgrade is that the claim rests on a press release rather than the peer-reviewed paper. The peer-reviewed paper exists and is the source being assessed. A score of 3 assigned on this basis is wrong on its face and the scoring conclusion does not survive.

MERIT:  no — The advocate has conflated two trials. The score being defended is for the PHASE 3 claim — 'improves recurrence-free survival ... in resected stage IIB-IV melanoma', the Phase 3 population — which rests on a company release and nothing else. The Lancet 2024 paper is the Phase 2b, stage IIIB-IV, a different trial in a different population. A peer-reviewed paper about another study does not raise the source quality of this claim.
EFFECT: none
DID:    Nothing.


### S003-11 — SERIOUS / CHANGES

**We say.** The peer-reviewed publication of the three-year readout.

**They object.** The Lancet 2024 paper is the primary analysis (median follow-up ~23 months), not the three-year readout; the three-year readout was published separately in JCO Oncology Advances (Carlino et al., 2026), and conflating the two misidentifies what the Lancet paper actually reports.

**Their document says.** "From July 18, 2019, to Sept 30, 2021, 157 patients were assigned … median follow-up was 23 months and 24 months, respectively." The three-year update is: Carlino MS et al., JCO Oncol Adv 3:e2500008, 2026 (cited in the 5-year JCO paper as a distinct publication).
  — *Results section, The Lancet 403(10427):632–644, 2024 (median follow-up 23 months); three-year publication identified at JCO Oncol Adv 3:e2500008, 2026*

**Why it matters.** Any assessment that treats the Lancet 2024 paper as the three-year readout will misread its follow-up duration, event counts, and HR. The Lancet paper reports 44 events at ~23 months median follow-up; the three-year readout reports 47 events and HR 0.510. Conclusions drawn about what the Lancet paper 'shows' at three years are conclusions about a different document.

MERIT:  no — 'The peer-reviewed publication of the three-year readout' is the ledger's used_for for S007, the JCO Oncology Advances paper. S003's used_for reads 'The peer-reviewed publication. Source of HR 0.561 (0.309-1.017)...' and makes no three-year claim. The advocate was shown both source blocks and attributed one description to the other.
EFFECT: none
DID:    Nothing.


### S003-12 — MINOR / NONE

**We say.** KEYNOTE-942: a randomised, phase 2b study — The Lancet, 2024

**They object.** This citation line is accurate as a title and journal attribution and we raise no objection to it as a standalone identifier; however, in the context of the surrounding sentences that misdescribe this paper as a press release and as the three-year readout, the accurate citation label creates a false impression that the errors in those surrounding sentences have been checked against the actual paper.

**Their document says.** "Individualised neoantigen therapy mRNA-4157 (V940) plus pembrolizumab versus pembrolizumab monotherapy in resected melanoma (KEYNOTE-942): a randomised, phase 2b study." The Lancet, 403(10427), 632–644. doi: 10.1016/S0140-6736(23)02268-7.
  — *Title and bibliographic line, The Lancet 403(10427):632–644, 2024*

**Why it matters.** The citation itself is correct. The objection is contextual: the accurate label does not immunise the surrounding characterisations (press release; three-year readout) from correction.

MERIT:  no — The advocate raises no objection to the citation itself and defers to S003-10 and S003-13, both of which rest on the same conflation.
EFFECT: none
DID:    Nothing.


### S003-13 — SERIOUS / CHANGES

**We say.** The peer-reviewed publication.

**They object.** This descriptor is accurate — the Lancet 2024 paper is the peer-reviewed publication — but it directly contradicts the sentence two lines above it in the same source block, which states the claim 'currently rests on a corporate press release … not the peer-reviewed publication it will eventually become'; the internal contradiction means one of the two characterisations must be wrong, and the press-release characterisation is the error.

**Their document says.** Source metadata 'used_for' field: 'The peer-reviewed publication. Source of HR 0.561 (0.309–1.017) with two-sided p = 0.053, the stage IIIB–IV enrolment, the 107/50 arm sizes, the open-label design, and grade 3+ treatment-related events at 25% versus 18%.' Published PMID 38246194, January 18, 2024.
  — *Source metadata block, 'used_for' field; The Lancet DOI 10.1016/S0140-6736(23)02268-7*

**Why it matters.** The page's own source block confirms this is the peer-reviewed publication, which directly invalidates the score-3 downgrade applied on the grounds that it is a press release. The internal contradiction is not a matter of interpretation — the same document calls it both a press release (for scoring) and a peer-reviewed publication (in the metadata). The scoring conclusion does not survive.

MERIT:  no — Same conflation as S003-10. There is no contradiction: S003 is the peer-reviewed publication OF THE PHASE 2b, and the score-3 is for the PHASE 3 claim, which has no peer-reviewed publication at all. Two sentences about two different trials.
EFFECT: none
DID:    Nothing.


---

## S004 — Five-year results — Journal of Clinical Oncology, 1 June 2026
*Advocate: the investigators and statisticians who published Five-year results — Journal of Clinical Oncology, 1 June 2026*  
*Ledger state: full_text_held*  

---

## S006 — The ASCO Post — INTerpath-001 meets primary and key secondary endpoints
*Advocate: the authors of The ASCO Post — INTerpath-001 meets primary and key secondary endpoints*  
*Ledger state: full_text_held*  

### S006-14 — MINOR / NONE

**We say.** The outlets we reached attributed those figures correctly to KEYNOTE-942 — among them The ASCO Post, Dermatology Times, OncLive and FierceBiotech — and several said plainly that no Phase 3 efficacy numbers had been released.

**They object.** The ASCO Post article does attribute the efficacy figures (HR=0.51 for RFS, HR=0.411 for DMFS) explicitly to KEYNOTE-942/mRNA-4157-P201, and it does not publish any Phase 3 efficacy numbers — so the characterisation of our article is accurate on both counts and we do not object to it.

**Their document says.** "The phase III readout builds on previously reported phase IIb results for intismeran in combination with pembrolizumab from the KEYNOTE-942/mRNA-4157-P201 trial, including the 5-year follow-up data presented at the 2026 ASCO Annual Meeting, in which the combination demonstrated a 49% reduction in the risk of recurrence or death (hazard ratio [HR] = 0.51, 95% confidence interval [CI] = 0.294–0.887) and a 59% reduction in the risk of distant metastasis or death (HR = 0.411, 95% CI = 0.200–0.843) compared to pembrolizumab alone."
  — *Paragraph 2 of the ASCO Post article (INTerpath-001 meets primary and key secondary endpoints, August 2026)*

**Why it matters.** The page's characterisation of our article is accurate; we confirm it rather than contest it. No correction is warranted.

MERIT:  no — The advocate confirms the page's characterisation and states plainly that no correction is warranted.
EFFECT: none
DID:    Nothing.


### S006-15 — MINOR / NONE

**We say.** The ASCO Post — INTerpath-001 meets primary and key secondary endpoints

**They object.** The article's headline is accurately reproduced, but the page should note that the article explicitly states the trial met its primary endpoint of recurrence-free survival (RFS) AND a key secondary endpoint of distant metastasis-free survival (DMFS) — two distinct endpoints — which is a more precise characterisation than the headline alone conveys.

**Their document says.** "The trial met its primary endpoint of recurrence-free survival (RFS) and a key secondary endpoint of distant metastasis-free survival (DMFS)."
  — *Opening section / topline summary, ASCO Post article (INTerpath-001 meets primary and key secondary endpoints, August 2026)*

**Why it matters.** The headline citation is accurate; the omission of the specific endpoint names (RFS and DMFS) is a minor imprecision that does not change any conclusion the page draws.

MERIT:  partly — The advocate is right that the source line gives the headline without the endpoint names, and right that nothing turns on it: the page names both endpoints, RFS and DMFS, in its own prose several times.
EFFECT: none
DID:    Nothing. Recorded rather than acted on, because the information the objection asks for is already on the page in its own voice.


### S006-16 — SERIOUS / NARROWS

**We say.** of a different curve; 35.4 is in nothing we hold; and The ASCO Post's

**They object.** The claim that '35.4 is in nothing we hold' is confirmed by our article: The ASCO Post article publishes no Phase 3 efficacy figures whatsoever — no hazard ratios, no percentage improvements, no median survival numbers from INTerpath-001 itself — so the figure 35.4 is indeed absent from our document; however, the page must not imply our article was a source candidate for that figure, because our article explicitly frames all quantitative efficacy data as Phase 2b KEYNOTE-942 results, not Phase 3 INTerpath-001 results.

**Their document says.** "The phase III readout builds on previously reported phase IIb results for intismeran in combination with pembrolizumab from the KEYNOTE-942/mRNA-4157-P201 trial... in which the combination demonstrated a 49% reduction in the risk of recurrence or death (hazard ratio [HR] = 0.51...) and a 59% reduction in the risk of distant metastasis or death (HR = 0.411...)"
  — *Paragraph 2, ASCO Post article (INTerpath-001 meets primary and key secondary endpoints, August 2026)*

**Why it matters.** If the page is tracing the origin of '35.4' and listing The ASCO Post as a document it examined, it must make clear that our article contains only Phase 2b figures attributed to KEYNOTE-942, and that the absence of 35.4 from our article is therefore expected and uninformative about where that figure originated. Treating our article as a failed source for a Phase 3 number misrepresents what our article was ever positioned to contain.

MERIT:  no — The advocate confirms the finding it was asked about — its article publishes no Phase 3 efficacy figures — which is exactly what the page says. Its caution, that the absence of 35.4 from a document that publishes no Phase 3 figures is uninformative about where 35.4 came from, is correct and is the reason the correction entry says the figure is in NOTHING we hold rather than blaming this outlet.
EFFECT: none
DID:    Nothing.


---

## S007 — Three-Year Update of a Randomized Phase IIb Study of Intismeran Autogene Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma — JCO Oncology Advances, 2026
*Advocate: the investigators and statisticians who published Three-Year Update of a Randomized Phase IIb Study of Intismeran Autogene Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma — JCO Oncology Advances, 2026*  
*Ledger state: full_text_held*  

### S007-17 — SERIOUS / NARROWS

**We say.** It had already cleared the line by the three-year readout at ASCO 2024, since published in full: HR 0.510, 95% CI 0.288–0.906.

**They object.** The three-year update was a planned supportive analysis in which RFS and DMFS were explicitly not formally tested; the p-values are described as nominal and descriptive, so the phrase 'cleared the line' — implying a pre-specified formal hypothesis test was passed — mischaracterises the statistical status of this readout.

**Their document says.** "RFS and DMFS were not formally tested; nominal 2-sided p-values are descriptive." (ASCO 2024 abstract LBA9512, which is the same analysis published in full as OA-25-00008); the JCO Oncology Advances paper describes this as "a planned supportive analysis" triggered when the last randomised patient had ≥2 years of follow-up.
  — *Methods / Statistical Analysis section, JCO Oncology Advances 2026, DOI 10.1200/OA-25-00008; confirmed in ASCO 2024 abstract LBA9512*

**Why it matters.** If the page's argument depends on the three-year readout having 'cleared' a formal efficacy boundary, that argument is wrong: the three-year analysis was pre-specified as supportive and descriptive, not a formal test. The HR and CI are real, but they do not constitute a crossed efficacy line in the regulatory or statistical sense.

MERIT:  yes — Upheld, from the paper itself. S007 states: 'These subsequent analyses are not intended for formal hypothesis testing (ie, are descriptive only).' 'Cleared the line' implies a threshold crossed in a test that was run; no test was run.
EFFECT: narrows
DID:    The sentence now reads that the interval no longer crossed 1.0 at three years, and says the paper calls its analyses descriptive only and not intended for formal hypothesis testing — 'an interval that stopped including 1.0 rather than a threshold anyone crossed'. The summary bullet is narrowed the same way.


### S007-18 — SERIOUS / NARROWS

**We say.** HR 0.510, 95% CI 0.288–0.906

**They object.** These figures are the RFS hazard ratio from the three-year update, but the page does not state — and the omission matters — that the accompanying p-value (nominal 0.019) is explicitly labelled descriptive and that RFS was not formally tested at this timepoint, which affects how the strength of this evidence should be characterised.

**Their document says.** "RFS benefit in the combo vs pembro arm was maintained with 49% risk reduction in recurrence and/or death (HR [95% CI], 0.510 [0.288–0.906]; 2-sided nominal p-value 0.019)." The word 'nominal' is integral to the reported result.
  — *Results section, ASCO 2024 abstract LBA9512 (same data as OA-25-00008); Methods/Statistical Analysis, OA-25-00008*

**Why it matters.** Quoting the HR and CI without the 'nominal/descriptive' qualifier attached to the p-value creates the impression of a formally significant result; the paper's own framing is more cautious and that caution is material to any conclusion drawn about evidentiary weight.

MERIT:  yes — Same finding as S007-17, and it adds one the advocate did not: S007 reports this hazard ratio with an 80% confidence interval (0.351-0.743) in its text, giving the 95% interval (0.288-0.906) in the results table. The page had quoted the 95% interval without saying which the paper leads with.
EFFECT: narrows
DID:    The source note now states both intervals, says which one the page quotes and why, and carries the paper's 'descriptive only' sentence as a quotation.


### S007-19 — MINOR / NONE

**We say.** Three-Year Update of a Randomized Phase IIb Study of Intismeran Autogene Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma — JCO Oncology Advances, 2026

**They object.** The page truncates the paper's full title, omitting the parenthetical drug synonyms '(mRNA-4157, V940)' that are part of the published title and are necessary for readers to locate or identify the paper unambiguously in literature searches.

**Their document says.** Full published title: "Three-Year Update of a Randomized Phase IIb Study of the Individualized Neoantigen Therapy Intismeran Autogene (mRNA-4157, V940) Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma."
  — *Title, JCO Oncology Advances 2026, DOI 10.1200/OA-25-00008*

**Why it matters.** A truncated title is a bibliographic inaccuracy; it does not change the page's substantive conclusions but could impede readers trying to retrieve the source.

MERIT:  yes — Upheld. The published title is 'Three-Year Update of a Randomized Phase IIb Study of the Individualized Neoantigen Therapy Intismeran Autogene (mRNA-4157, V940) Plus Pembrolizumab Versus Pembrolizumab in Resected Melanoma'. We had dropped 'the Individualized Neoantigen Therapy' and the drug synonyms, which are how a reader finds it.
EFFECT: none
DID:    Restored the full published title on the page and in the ledger, read off the held document.


### S007-20 — SERIOUS / CHANGES

**We say.** We had skipped the three-year readout, which is where the

**They object.** This sentence is an incomplete fragment — it ends mid-clause — so it is impossible to evaluate what claim is being made about our paper or to determine whether the omitted content misrepresents it; the truncation itself is an error that must be corrected before the sentence can be assessed.

**They looked and found nothing.** The sentence is cut off before its predicate is complete. I searched the full text of OA-25-00008 and the ASCO 2024 abstract LBA9512 for any passage that would complete the implied claim (e.g., about a threshold being crossed, a subgroup result, or a DMFS finding), but without the rest of the sentence I cannot identify which specific finding the page intended to reference or whether our document answers it.

**Why it matters.** An incomplete sentence that purports to characterise our paper cannot be verified or rebutted; it must be completed and resubmitted. As written, it makes an unverifiable assertion about what the three-year readout contains, and any conclusion built on it is unsupported.

MERIT:  no — The advocate is right that it was handed a fragment ending mid-clause and could not evaluate it, and right that the truncation is itself an error. It was ours: the sentence extractor was breaking at source-file line breaks. There is no claim here to answer.
EFFECT: none
DID:    Extractor fixed; see S001-03.


---

## S008 — Weber JS, Khattak MA, Carlino MS, et al. Individualized neoantigen therapy mRNA-4157 (V940) plus pembrolizumab in resected melanoma: 3-year update from the mRNA-4157-P201 (KEYNOTE-942) trial. ASCO 2024, abstract LBA9512
*Advocate: the authors of Weber JS, Khattak MA, Carlino MS, et al. Individualized neoantigen therapy mRNA-4157 (V940) plus pembrolizumab in resected melanoma: 3-year update from the mRNA-4157-P201 (KEYNOTE-942) trial. ASCO 2024, abstract LBA9512*  
*Ledger state: full_text_held*  

### S008-21 — SERIOUS / NARROWS

**We say.** The peer-reviewed publication of the three-year readout.

**They object.** LBA9512 is a conference abstract published in a JCO supplement, not a full peer-reviewed article; the actual full peer-reviewed publication of the three-year data is a separate paper (Carlino MS et al., JCO Oncology Advances 3:e2500008, 2026), which the page does not cite or acknowledge.

**Their document says.** J Clin Oncol 42, 2024 (suppl 17; abstr LBA9512) [cited as abstract, not full article, in the 5-year update reference list]; separately: 'Carlino MS, Khattak A, Meniawy T, et al: Three-year update of a randomized phase IIb study of the individualized neoantigen therapy intismeran autogene (mRNA-4157, V940) plus pembrolizumab versus pembrolizumab in resected melanoma. JCO Oncol Adv 3:e2500008, 2026'
  — *Reference list of Weber et al. ASCO 2024 LBA9512 (as cited in the 5-year update, JCO 2026); JCO Oncology Advances 3:e2500008, 2026*

**Why it matters.** The page presents LBA9512 as the peer-reviewed publication of the three-year readout, lending it a weight it does not carry as a conference abstract. The actual full peer-reviewed three-year publication (Carlino et al., JCO Oncology Advances, 2026) is omitted entirely, meaning the page's characterisation of the evidentiary status of the three-year data is materially incomplete.

MERIT:  yes — Upheld in substance. The page's source note called the ASCO 2024 material the publication of the three-year readout while the actual peer-reviewed paper — Carlino et al., JCO Oncology Advances 2026 — is S007 and sat in the same source list.
EFFECT: changes
DID:    The note is rewritten. It now describes S007 as the peer-reviewed publication, held in full and read on 1 September, and no longer routes the three-year figures through the conference presentation.


### S008-22 — SERIOUS / NARROWS

**We say.** The three-year figures quoted above are taken from the ASCO 2024 presentation of the same analysis; the journal site blocks automated access, so we have verified the citation but not read the full text ourselves.

**They object.** The source document (LBA9512) is an ASCO abstract published in JCO supplement with a public DOI and indexed abstract text; the page's claim that it could not access the content because 'the journal site blocks automated access' mischaracterises the accessibility of the abstract, whose key results (HR 0.510, 95% CI 0.288–0.906) are in the publicly indexed abstract and in the Merck/Moderna press release of 3 June 2024.

**Their document says.** 'The benefit of RFS in the combination ... a 49% risk reduction in recurrence and/or death (hazard ratio [HR], 95% CI, 0.510 [0.288-0.906]; 2-sided nominal P value, .019)' — abstract content publicly indexed at DOI 10.1200/JCO.2024.42.17_suppl.LBA9512
  — *Results section, LBA9512 abstract, J Clin Oncol 42:17_suppl, 2024*

**Why it matters.** The page's disclaimer that it 'verified the citation but not read the full text' implies epistemic uncertainty about the figures it quotes; in fact the abstract text is publicly accessible and the figures are confirmed, so the disclaimer overstates the limitation and may cause readers to discount the reliability of the cited numbers.

MERIT:  yes — Upheld, and worse than the advocate knew. The note said 'the journal site blocks automated access, so we have verified the citation but not read the full text ourselves' while the ledger recorded S007 as full_text_held. The page claimed it could not read a document we hold.
EFFECT: changes
DID:    Note rewritten from the held bytes. Separately: inaccessibility_claims, the check built to catch exactly this, missed it — neither 'blocks automated access' nor 'not read the full text' was in its list of phrasings. Broadened, with the failure recorded in the source.


### S008-23 — SERIOUS / NARROWS

**We say.** The three-year figures quoted above are taken from the ASCO 2024 presentation of the same analysis; the journal site blocks automated access, so we have verified the citation but not read the full text ourselves.

**They object.** The page does not mention that a full peer-reviewed journal article of the three-year data (Carlino et al., JCO Oncology Advances 3:e2500008, 2026) exists and is separately accessible, which would have resolved any access limitation the page describes.

**Their document says.** Carlino MS, Khattak A, Meniawy T, et al: Three-year update of a randomized phase IIb study of the individualized neoantigen therapy intismeran autogene (mRNA-4157, V940) plus pembrolizumab versus pembrolizumab in resected melanoma. JCO Oncol Adv 3:e2500008, 2026
  — *Reference list of the 5-year update (Weber/Carlino et al., JCO 2026, DOI 10.1200/JCO-26-00835); JCO Oncology Advances 3:e2500008, 2026*

**Why it matters.** The page's stated inability to read the full text of the three-year data is rendered moot by the existence of a full open-access peer-reviewed publication of the same data; omitting this source means the page's epistemic caveat is unfounded and its characterisation of the evidence base is incomplete.

MERIT:  yes — Upheld and already answered by the same edit: the full peer-reviewed three-year paper is S007, we hold it, and the page now says so.
EFFECT: changes
DID:    Covered by S008-21 and S008-22.


### S008-24 — MINOR / NONE

**We say.** It had already cleared the line by the three-year readout at ASCO 2024, since published in full: HR 0.510, 95% CI 0.288–0.906.

**They object.** The phrase 'since published in full' is ambiguous as to which publication it refers: if it refers to LBA9512, that is a conference abstract (JCO supplement), not a full article; the full peer-reviewed publication of the three-year data is Carlino et al., JCO Oncology Advances 3:e2500008, 2026, which the page does not cite.

**Their document says.** Carlino MS, Khattak A, Meniawy T, et al: Three-year update of a randomized phase IIb study of the individualized neoantigen therapy intismeran autogene (mRNA-4157, V940) plus pembrolizumab versus pembrolizumab in resected melanoma. JCO Oncol Adv 3:e2500008, 2026
  — *Reference list of the 5-year update (JCO 2026, DOI 10.1200/JCO-26-00835)*

**Why it matters.** The HR figure itself is correct; the objection is to the implied publication status. The conclusion that the CI cleared the no-effect line is accurate, but the page should distinguish the conference abstract from the full peer-reviewed article and cite the latter.

MERIT:  yes — Upheld. 'Since published in full' was ambiguous between the conference abstract and the journal article.
EFFECT: none
DID:    The phrase now sits beside a note naming the journal publication explicitly.


### S008-25 — MINOR / NONE

**We say.** We had skipped the three-year readout, which is where the

**They object.** The page acknowledges skipping the three-year readout but does not acknowledge that the three-year data have since been published as a full peer-reviewed article (Carlino et al., JCO Oncology Advances 3:e2500008, 2026), meaning the omission it confesses to is more consequential than it states: a full journal article, not merely a conference abstract, was missed.

**Their document says.** Carlino MS, Khattak A, Meniawy T, et al: Three-year update of a randomized phase IIb study of the individualized neoantigen therapy intismeran autogene (mRNA-4157, V940) plus pembrolizumab versus pembrolizumab in resected melanoma. JCO Oncol Adv 3:e2500008, 2026
  — *Reference list of the 5-year update (JCO 2026, DOI 10.1200/JCO-26-00835)*

**Why it matters.** The self-correction is welcome, but its scope is understated: the page implies it missed only a conference presentation, when in fact it also missed a full peer-reviewed journal article of the same data. This affects how readers assess the thoroughness of the page's literature review.

MERIT:  no — A change-log entry — our record of having skipped the three-year readout — read as a live claim. The advocate's point that the data have since been published in full is true and the page now says so in the source list.
EFFECT: none
DID:    Nothing beyond the S008-21 edit.


---

## S009 — Morning Glory Sciences — INTerpath-001
*Advocate: the authors of Morning Glory Sciences — INTerpath-001*  
*Ledger state: full_text_held*  

### S009-26 — SERIOUS / NARROWS

**We say.** absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit.

**They object.** The page attributes this argument to Morning Glory Sciences as if it were a contested or one-sided claim, but our document immediately follows that statement with an additional, independent caution — 'Most stage IIB and IIC patients never recur after surgery alone' — which deepens the same concern and is omitted from the page's framing of the dispute.

**Their document says.** "Absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit. A significant result across a denominator of 1,137 patients is not the same thing as an established rationale for treating a stage IIB patient. The stage expansion deserves equal caution. Most stage IIB and IIC patients never recur after surgery alone."
  — *Morning Glory Sciences — INTerpath-001, section on design change / stage expansion (paragraphs beginning 'A design change also bears directly on interpretation')*

**Why it matters.** The page frames the absolute-benefit argument as a bare assertion by Morning Glory Sciences that Pharmacy Times rebuts. Our document does not rest on a single sentence: it supplies a second, independent empirical claim ('Most stage IIB and IIC patients never recur after surgery alone') that reinforces the same concern. Omitting that second sentence makes our position look weaker than it is and makes the Pharmacy Times rebuttal look more decisive than it is. The page's conclusion — that 'neither reading reached the general coverage' — survives, but the characterisation of our reading as a single-sentence hazard-ratio argument is too narrow.

MERIT:  yes — and my note calling this section a digression was wrong, which
        the editor said plainly and I withdraw. Identifying a real disagreement
        between outlets, on a question that decides how to read the result, is
        the work. The test is whether it bears on the subject, and it does: the
        Phase 3 widened the population, and whether the benefit reaches the
        patients it newly includes is the whole question of what the numbers,
        when they come, will support.
EFFECT: changes
DID:    Carried the half of Morning Glory's argument the page had left out, as
        Q-14, and reorganised the section around it. The disagreement is still
        set out; what follows it is now what the source actually says about
        whether the disagreement can be settled.


### S009-27 — SERIOUS / NARROWS

**We say.** Which of them is right determines how much of the Phase 3 benefit reaches the patients it newly includes, and neither reading reached the general coverage.

**They object.** Our document does not merely assert a position on absolute risk — it explicitly flags that the Phase 3 hazard ratios have not been disclosed, making any resolution of the dispute between the two readings currently impossible from the trial data, a material fact the page omits.

**Their document says.** "Because the Phase 3 hazard ratios have not been disclosed, those 157-patient figures cannot be placed alongside the 1,137-patient result. They belong to the Phase 2b population, not to this one."
  — *Morning Glory Sciences — INTerpath-001, section preceding the stage-expansion discussion ('A design change also bears directly on interpretation')*

**Why it matters.** The page poses the question 'which of them is right' as if it is answerable from existing data and simply ignored by general coverage. Our document establishes that the Phase 3 event rates and hazard ratios are undisclosed, so the question cannot yet be resolved empirically. This changes the nature of the dispute: it is not Morning Glory Sciences vs. Pharmacy Times on a factual question with a knowable answer — it is two priors about stage IIB/IIC risk applied to a data gap. The page's framing implies a resolvable factual disagreement; our document shows it is currently unresolvable.

MERIT:  yes, and it changes what the section is about. The advocate was right
        that we posed "which of them is right" as though it were answerable and
        merely ignored. It is not answerable, and the reason is checkable rather
        than rhetorical, so the page now shows the checking:

          - no hazard ratio, interval or p-value for this trial is in either
            company release, in any coverage we hold, or in the registry;
          - ClinicalTrials.gov NCT05933577 carries hasResults = false, has never
            had results submitted, and gives an estimated primary completion of
            26 October 2029 — which is why the August announcement is a
            prespecified interim look and says so. Entered as S013 and held.

        The editor also asked whether placing the 157-patient figures beside the
        1,137-patient result would mislead. It would, and the page now says how,
        from held documents: different populations (IIIB-IV against IIB-IV),
        different design (open-label against double-blind with the outcomes
        assessor masked), different statistical standing (the Phase 2b's later
        analyses "descriptive only" against a one-sided alpha of 0.10; the
        Phase 3 a prespecified interim threshold) — and no Phase 3 effect size
        to compare to at all, so quoting 0.51 beside "met its endpoints" is a
        substitution rather than a comparison.
EFFECT: changes
DID:    Rewrote the section. Added S013 (the registry record) and Q-14.


### S009-28 — MINOR / NONE

**We say.** Morning Glory Sciences: the Phase 2b population was stage IIIB–IV, the Phase 3 adds node-negative disease

**They object.** Our document's point about the stage expansion is not merely descriptive — it is embedded in a broader argument that the Phase 2b hazard ratios (the only ones disclosed) belong to a different population and therefore cannot be used to infer the absolute benefit for the newly added stage IIB/IIC patients; the page strips that inferential warning from the factual observation.

**Their document says.** "The Phase 2b population was stage IIIB–IV; the Phase 3 adds stage IIB and IIC — node-negative disease. Absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit."
  — *Morning Glory Sciences — INTerpath-001, stage-expansion section*

**Why it matters.** The page's summary is factually accurate as far as it goes; the omission of the inferential context (that Phase 2b HRs cannot be applied to the Phase 3 IIB/IIC subgroup) does not change the page's conclusion but does misrepresent the logical structure of our argument, making it look like a simple epidemiological claim rather than a warning about cross-population inference.

MERIT:  no — The advocate agrees the summary is factually accurate and objects to what it leaves out. That is the same point as S009-26 and S009-27 and is carried there.
EFFECT: none
DID:    Nothing.


---

## S010 — Pharmacy Times — Phase 3 trial marks first success for personalized mRNA cancer therapy in resected melanoma
*Advocate: —*  
*Ledger state: blocked*  

> nobody can open this source, so no advocate runs on it. The ledger blocks new characterisation of it instead — which is the correct control, because an advocate here would be guessing.


---

## S011 — MLQ News — Moderna and Merck's personalized melanoma therapy meets two Phase 3 endpoints
*Advocate: the authors of MLQ News — Moderna and Merck's personalized melanoma therapy meets two Phase 3 endpoints*  
*Ledger state: full_text_held*  
