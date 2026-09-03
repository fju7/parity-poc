# melanoma — counterexample hunt, 2026-09-03

One section per universal negative on the page. A claim is not cleared
by a SURVIVED verdict alone: somebody has to read what was searched and
say whether that search would have found the thing.

    VERDICT: broken | narrowed | survived   — yours, not the role's
    BASIS:   what you read to decide, with a locator
    DID:     what changed on the page, or nothing and why


---

### CE-01 — role says BROKEN (HIGH confidence)

**We say.** CheckMate 238's arms are nivolumab and ipilimumab, so there is no placebo arm to report against.

**What breaks it.** CheckMate 238 used matched double-dummy placebo: each active arm received the other drug's matched placebo, so both arms contained a placebo component and placebo data exist within the trial.

**Citation.** Adjuvant Nivolumab versus Ipilimumab in Resected Stage III/IV Melanoma: 5-Year Efficacy and Biomarker Results from CheckMate 238, Clinical Cancer Research 2023; https://aacrjournals.org/clincancerres/article/29/17/3352/728540/

**Their words.** “nivolumab 3 mg/kg every 2 weeks or i.v. ipilimumab 10 mg/kg every 3 weeks for four doses and then every 12 weeks, each with corresponding matched placebo”

**We inherited this.** The original says: The claim appears to be a lay inference from the trial's active-controlled design label ('active-controlled' in EJC/ScienceDirect publications), which is accurate as far as it goes — the primary comparison is active vs. active — but the double-dummy placebo component is consistently documented in every primary publication and is not the same as having no placebo at all.

**Does it change the conclusion.** This breaks the sentence directly. The claim is used to explain why no placebo-referenced OS figure can be reported from CheckMate 238. That explanation is wrong: a matched placebo was administered in both arms, and placebo-arm data exist within the trial structure. The conclusion that there is 'nothing to report against' is therefore unsupported. This does not necessarily change the piece's broader conclusion about OS maturity, but it invalidates the stated reason for the absence of a placebo comparator.

**Searched.** ClinicalTrials.gov NCT02388906 (CheckMate 238 registry record); PubMed/PMC for 'CheckMate 238 placebo double-blind'; Lancet Oncology 4-year results (PMID 32961119); Clinical Cancer Research 5-year results (PMID 37378689); European Journal of Cancer AJCC-8 reassessment (ScienceDirect S0959804922003926); HRA NHS summary; OncLive long-term data report. Query terms used: 'CheckMate 238 trial design arms nivolumab ipilimumab placebo', 'CheckMate 238 double dummy matched placebo'.

VERDICT: survived — the sentence is right, and the page now says why
BASIS:   S021, the CheckMate 238 registry record we hold in full. Its two arm groups are 'Ipilimumab and Placebo matching Nivolumab' and 'Nivolumab and Placebo matching Ipilimumab', BOTH typed EXPERIMENTAL, masking QUADRUPLE. That is a double-dummy for blinding: every patient received an active drug plus the other drug's matching placebo. It is not a placebo ARM, and no nivolumab-versus-placebo comparison can be computed from it. The role read the word 'Placebo' in the arm labels and concluded placebo data exist.
DID:     The page now says what the record says, because a high-confidence reader got this wrong and a reader of ours could too: it quotes both arm labels and adds that the placebos are the dummies that keep it blinded, one for each drug, and every patient received an active treatment.


---

### CE-02 — role says BROKEN (HIGH confidence)

**We say.** In this programme, overall survival has been reported only as an exploratory analysis in the smaller trial, on an "n=14" — fourteen deaths among 157 patients, seven in each arm.

**What breaks it.** Multiple factual errors compound in this sentence. (1) IMMUNED enrolled 167 patients (56 + 59 + 52 across three arms), not 157. (2) OS was a pre-specified secondary endpoint in IMMUNED, not merely an exploratory analysis. (3) OS was reported across all three arms, not just as a two-arm comparison with 14 deaths split seven each: the final Lancet 2022 paper showed nivolumab+ipilimumab produced a statistically significant OS benefit over placebo, while nivolumab alone did not — a differentiated result incompatible with a symmetric 7/7 death split. (4) CheckMate 76K (NCT04099251) also has OS as a formal pre-specified endpoint with 277 deaths required for the final OS analysis, meaning OS in this programme is not confined to an exploratory analysis in one small trial.

**Citation.** IMMUNED final results: Livingstone et al., The Lancet, Vol 400, Issue 10358, 1–7 October 2022. https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(22)01654-3/abstract; CheckMate 76K SAP: https://cdn.clinicaltrials.gov/large-docs/51/NCT04099251/Prot_SAP_000.pdf

**Their words.** “Overall survival was significantly improved for patients receiving nivolumab plus ipilimumab compared with placebo.”

**We inherited this.** The original says: Possibly inherited from a summary of the IMMUNED 2020 interim Lancet paper (Zimmer et al., Lancet 2020; 395:1558–68), which reported only RFS and did not include OS. The 2022 final paper added OS. If the author read only the 2020 interim paper, the OS characterisation would be absent — but the patient count and endpoint classification errors are not explained by that source alone.

**Does it change the conclusion.** Every specific number in this sentence is wrong or misleading: the patient count (157 vs 167), the endpoint classification (exploratory vs pre-specified secondary), the death count framing (symmetric 7/7 vs a differentiated OS result), and the scope claim (OS reported 'only' in one small trial, when CheckMate 76K has a formal OS endpoint). This breaks the sentence entirely. It may or may not change the piece's conclusion depending on what that conclusion is, but it materially misrepresents the evidence base.

**Searched.** PubMed/PMC for 'IMMUNED trial overall survival melanoma nivolumab ipilimumab placebo 157 patients'; The Lancet abstract for IMMUNED final results (PIIS0140-6736(22)01654-3); ASCO Post summary of IMMUNED final results; Annals of Oncology abstract 784O (ESMO 2022 OS results); ScienceDirect IMMUNED final paper; ClinicalTrials.gov NCT04099251 SAP document for CheckMate 76K OS endpoint specification. Query terms: 'IMMUNED trial 167 patients enrolled overall survival deaths seven OR 14 deaths OR OS events nivolumab placebo'; 'IMMUNED trial final results overall survival deaths placebo arm Lancet 2022'.

VERDICT: survived — the attack went to the wrong trial, at HIGH confidence
BASIS:   The sentence says 'in this programme', which is intismeran: KEYNOTE-942 and INTerpath-001. The role went to IMMUNED and CheckMate 76K — nivolumab and ipilimumab trials, different drugs, different sponsors, not on this page. Every figure it calls an error is verified in S004, which we hold: 'Among 157 randomly assigned patients (intismeran plus pembrolizumab, n 5 107; pembrolizumab, n 5 50)' and '7 of 107 patients (6.5%) ... and 7 of 50 (14.0%) ... died'. 107 + 50 = 157 and 7 + 7 = 14.
DID:     Nothing. The sentence is correct as written and was re-verified against the held bytes tonight.


---

### CE-03 — role says NARROWED (LOW confidence)

**We say.** And one thing almost nobody mentioned Two specialist outlets touched it, and they disagree.

**What breaks it.** No direct counterexample found — this is a coverage claim, not a factual claim about trial data, and cannot be falsified by registry or literature search alone. However, the claim is unverifiable as written: 'almost nobody' and 'two specialist outlets' are not defined, and the search found at least the Pharmacy Times article and the Morning Glory Sciences reference cited in the next claim, consistent with the 'two outlets' assertion. The claim survives on its own terms but cannot be confirmed or denied without knowing the full universe of coverage the author surveyed.

**Citation.** 

**Does it change the conclusion.** This sentence is a framing claim, not a data claim. It cannot be broken by a registry search. Its validity depends entirely on the completeness of the coverage survey the author conducted, which is not disclosed. It is unfalsifiable as written and therefore should carry an epistemic caveat, not a factual assertion.

**Searched.** Web search for 'Morning Glory Sciences melanoma nivolumab adjuvant stage IIB IIC publication'; 'Pharmacy Times nivolumab melanoma stage IIB IIC recurrence risk stage III'; general news search for CheckMate 76K coverage. No registry search is applicable to a media-coverage claim. Databases checked for specialist oncology outlet coverage: OncLive, ASCO Post, MedPage Today, Cancer Network, Dermatology Times, Pharmacy Times.

VERDICT: narrowed — the role is right that it was unbounded
BASIS:   It is a claim about our own survey, not about the world, and no search can settle it. The role said so and declined to break it, which is the correct verdict.
DID:     The heading and sentence are bounded to what we read: 'And one thing almost nothing we read mentioned' / 'Of the coverage we hold, two specialist outlets touched it'.


---

### CE-04 — role says NARROWED (MEDIUM confidence)

**We say.** Morning Glory Sciences — an outlet we can find no other publication citing, so we give the argument on its merits rather than on its authority — the Phase 2b population was stage IIIB–IV, the Phase 3 adds node-negative disease, and "absolute recurrence risk in that group is lower, so the same hazard ratio delivers a smaller absolute benefit." Pharmacy Times makes the opposite case about the same patients: resected stage IIB or IIC melanoma "can face risks of recurrence and melanoma-specific mortality similar to those observed in stage III disease." Neither reading reached the general coverage.

**What breaks it.** The Pharmacy Times characterisation is confirmed and accurately sourced: the CheckMate 76K Nature Medicine paper itself states that 'patients with resected stage IIB/C melanoma have high recurrence risk, similar to those with resected stage IIIA/B disease,' and the Pharmacy Times article on the FDA approval quotes trial investigators to the same effect. The Morning Glory Sciences outlet cannot be found in any indexed database, consistent with the author's own caveat. However, the logical argument attributed to Morning Glory Sciences is independently verifiable: the Phase 2b IMMUNED trial enrolled stage IV NED patients, not stage IIB/C, so the population comparison the author draws (Phase 2b = IIIB–IV; Phase 3 = adds node-negative) conflates two different trials (IMMUNED and CheckMate 76K) rather than two phases of the same programme. If 'Phase 2b' refers to IMMUNED and 'Phase 3' to CheckMate 76K, these are separate programmes with different sponsors, not sequential phases of one programme. This is a potential logical error in the Morning Glory Sciences argument as characterised, not a counterexample to the Pharmacy Times claim.

**Citation.** Pharmacy Times FDA approval article: https://www.pharmacytimes.com/view/fda-approves-nivolumab-for-completely-resected-stage-iib-or-stage-iic-melanoma-in-adult-pediatric-patients; CheckMate 76K primary results: Kirkwood et al., Nature Medicine, October 2023, https://www.nature.com/articles/s41591-023-02583-2

**Their words.** “patients with resected stage IIB/C melanoma have high recurrence risk, similar to those with resected stage IIIA/B disease”

**We inherited this.** The original says: The Pharmacy Times claim traces directly to the CheckMate 76K Nature Medicine primary publication (Kirkwood et al. 2023) and to the FDA approval press materials. The Morning Glory Sciences claim cannot be traced to any indexed source.

**Does it change the conclusion.** The Pharmacy Times characterisation is accurate and well-sourced. The Morning Glory Sciences argument, as characterised, may rest on a category error (treating IMMUNED and CheckMate 76K as sequential phases of one programme). Neither finding changes the piece's conclusion about the two outlets disagreeing, but the Morning Glory Sciences argument may be weaker than presented if the programme-phase framing is incorrect.

**Searched.** Web search for 'Morning Glory Sciences melanoma nivolumab adjuvant stage IIB IIC publication'; 'Pharmacy Times nivolumab melanoma stage IIB IIC recurrence risk stage III'; PubMed for Morning Glory Sciences as author affiliation or journal; Google Scholar for Morning Glory Sciences oncology. No results for Morning Glory Sciences in any indexed database. Pharmacy Times article confirmed at pharmacytimes.com. CheckMate 76K Nature Medicine paper confirmed. WHO ICTRP, EudraCT/CTIS, ISRCTN, and ClinicalTrials.gov were not searched for this claim as it is a media/argument claim, not a trial-existence claim.

VERDICT: survived — the same wrong trial
BASIS:   The role's objection is that the Morning Glory argument 'conflates IMMUNED and CheckMate 76K'. Neither trial is on this page. The Phase 2b is KEYNOTE-942 and the Phase 3 is INTerpath-001, sequential phases of one intismeran programme, and S004 and S001 give their stage ranges: 'resected stage IIIB to IV' and 'Completely Resected Stage IIB-IV'. The role did confirm the Pharmacy Times quotation, which is the half of the sentence that could have been wrong.
DID:     Nothing on this claim. The bounding change is recorded under CE-03.


---

### CE-05 — role says NARROWED (MEDIUM confidence)

**We say.** Every number above traces to one of these, and none to a news report — a check that runs before this page can publish refuses it otherwise.

**What breaks it.** No external counterexample is possible: this is an internal editorial process claim about the author's own sourcing discipline, not a falsifiable empirical claim about the world. It cannot be broken by registry search. However, the analysis of Claim 2 above shows that at least one number in the piece — the patient count of 157 — does not accurately trace to the primary source (IMMUNED enrolled 167), which means either the sourcing check failed or the number was not drawn from a primary source. That is a functional counterexample to the spirit of this claim, even if not to its literal wording.

**Citation.** IMMUNED trial registration and primary publication: Zimmer et al., Lancet 2020; 395:1558–68 (167 patients enrolled: 56 + 59 + 52); Livingstone et al., Lancet 2022; 400(10358) (final results confirming same enrolment).

**Their words.** “Patients were randomly assigned (1:1:1) to either nivolumab plus ipilimumab... nivolumab monotherapy... or matching placebo”

**We inherited this.** The original says: This claim is the author's own, not inherited from a guideline or review.

**Does it change the conclusion.** If the '157 patients' figure in Claim 2 is wrong, then at least one number in the piece does not accurately trace to a primary source, which directly contradicts this editorial-process assurance. This matters for the piece's credibility claim, not for its clinical conclusions.

**Searched.** ClinicalTrials.gov NCT02892305 (IMMUNED registry record); PubMed for IMMUNED enrolment figures; Lancet 2020 and 2022 IMMUNED papers for patient counts; WHO ICTRP for IMMUNED registration; EudraCT for IMMUNED (trial conducted in Germany, registered under EU CTR). Queries: 'IMMUNED trial 167 patients enrolled overall survival deaths'; 'IMMUNED nivolumab ipilimumab placebo stage IV melanoma enrolment'. ClinicalTrials.gov, EudraCT/CTIS, ISRCTN, WHO ICTRP, FDA Drugs@FDA, and EMA EPAR were considered; the enrolment figure is confirmed in the published Lancet papers rather than requiring separate registry retrieval.

VERDICT: survived — the attack was built on its own earlier error
BASIS:   The role's whole case is that '157' does not trace to a primary source because IMMUNED enrolled 167. IMMUNED is not on this page. S004 prints 157 for KEYNOTE-942 and the binder confirms the span. This is a finding manufactured from a finding, which is the failure mode B15 exists to make visible in ourselves and is worth recording when a role does it to us.
DID:     Nothing.

