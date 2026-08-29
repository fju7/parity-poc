# cdk46 — counterexample hunt, 2026-08-29-TEST

One section per universal negative on the page. A claim is not cleared
by a SURVIVED verdict alone: somebody has to read what was searched and
say whether that search would have found the thing.

    VERDICT: broken | narrowed | survived   — yours, not the role's
    BASIS:   what you read to decide, with a locator
    DID:     what changed on the page, or nothing and why


---

### CE-01 — role says BROKEN (HIGH confidence)

**We say.** No randomised trial has tested one of these drugs against another.

**What breaks it.** A published randomised Phase III open-label trial (Mansoura University, Egypt, 2022–2023) directly compared ribociclib versus palbociclib plus fulvestrant as second-line treatment in ER+/HER2− metastatic breast cancer, with 58 patients per arm.

**Citation.** Ahmed Shaaban MH et al. 'Comparing Ribociclib versus Palbociclib as a Second Line Treatment in Combination with Fulvestrant in Metastatic Breast Cancer: A Randomized Clinical Trial.' Asian Pacific Journal of Cancer Prevention, 25(9):3039–3049, 2024. DOI: 10.31557/APJCP.2024.25.9.3039. PMC11700305.

**Their words.** “This is an interventional concurrent randomised phase III open label clinical trial.”

**We inherited this.** The original says: The claim appears to be inherited from guideline and review language that is typically scoped to 'no large head-to-head RCT in the first-line setting' (e.g., PALMARES-2, Annals of Oncology 2025: 'no large head-to-head comparisons of the three CDK4/6is have been conducted so far') — a narrower claim that drops the qualifiers 'large' and 'first-line' when adopted into the piece.

**Does it change the conclusion.** This breaks the sentence directly and completely. The piece's broader conclusion — that no head-to-head RCT evidence exists to separate the drugs — may still hold in the specific first-line setting, but the unqualified universal sentence is false. A counterexample that is second-line, single-centre, and small still defeats an unqualified 'no randomised trial has ever.' The piece's conclusion may survive with a scope qualifier; the sentence as written does not.

**Searched.** ClinicalTrials.gov (queries: 'abemaciclib ribociclib palbociclib head-to-head randomised'; 'CDK4/6 inhibitor head-to-head randomized'; 'abemaciclib vs ribociclib randomized'; 'palbociclib vs ribociclib randomized'; 'ribociclib palbociclib randomized phase III'; 'abemaciclib versus palbociclib randomized NCT'); PubMed/PMC (same drug-name queries plus 'head-to-head', 'versus', 'comparative', 'randomized', 'randomised'); ASCO abstract database (HARMONIA TiP abstract JCO 2023); ESMO/Annals of Oncology (HARMONIA TiP 2022); EudraCT number 2021-002027-38 confirmed via NCT05207709 secondary ID; WHO ICTRP (via ClinicalTrials.gov international registry linkage); APJCP journal (Mansoura trial); Dana-Farber clinical trials listing (HARMONIA); Springer/Breast Cancer Research and Treatment (indirect comparison meta-analyses); Scientific Reports (network meta-analysis); real-world registry studies (OPAL, PALMARES-2, P-VERIFY, TriNetX) reviewed to confirm they are observational, not randomised.

VERDICT: 
BASIS:   
DID:     


---

### CE-02 — role says BROKEN (HIGH confidence)

**We say.** No randomised trial has compared any of the three against another.

**What breaks it.** Two randomised trials have compared palbociclib directly against ribociclib: (1) the published Mansoura/APJCP Phase III RCT (2024), and (2) the HARMONIA trial (NCT05207709, EudraCT 2021-002027-38), an international multicenter Phase III RCT randomising patients 1:1 to ribociclib+ET vs. palbociclib+ET, currently active and not recruiting.

**Citation.** (1) Ahmed Shaaban MH et al. APJCP 25(9):3039–3049, 2024. DOI: 10.31557/APJCP.2024.25.9.3039. (2) HARMONIA SOLTI-2101/AFT-58, NCT05207709, EudraCT 2021-002027-38; TiP abstract: JCO 41(16_suppl):TPS1125, 2023; Annals of Oncology 33(S7):272TiP, 2022.

**Their words.** “HARMONIA is an international, multicenter, randomized, open-label and phase III study.”

**We inherited this.** The original says: Inherited from review and guideline language scoped to 'no head-to-head RCT data comparing CDK4/6i' in the first-line or all-comers metastatic setting (e.g., P-VERIFY/PMC12424423: 'To date, there have been no head-to-head RCT data comparing CDK4/6i'). The Mansoura trial is second-line and single-centre; HARMONIA is restricted to the HER2-enriched intrinsic subtype — both scope qualifiers were dropped when the claim was generalised.

**Does it change the conclusion.** This breaks the sentence completely. Two separate randomised trials — one completed and published, one active Phase III — have compared palbociclib against ribociclib. No randomised trial has yet compared abemaciclib directly against either of the other two, so the claim survives for that specific pair. The piece's conclusion may be partially salvageable if rewritten to specify the abemaciclib comparisons, but the sentence as written is false.

**Searched.** ClinicalTrials.gov (queries: 'ribociclib palbociclib randomized'; 'abemaciclib ribociclib randomized'; 'abemaciclib palbociclib randomized'; 'CDK4/6 inhibitor head-to-head'; 'HARMONIA trial'; NCT05207709 direct lookup); PubMed/PMC (drug-name pairs + 'randomized clinical trial', 'head-to-head', 'versus'); ASCO abstracts 2022–2025; ESMO/Annals of Oncology abstracts 2022–2025; EudraCT 2021-002027-38 (confirmed via NCT secondary ID field); ISRCTN (no additional hits found); WHO ICTRP (via ClinicalTrials.gov linkage); APJCP journal full text; Dana-Farber trial listing; real-world studies (OPAL, PALMARES-2, TriNetX, P-VERIFY) confirmed as observational.

VERDICT: 
BASIS:   
DID:     


---

### CE-03 — role says BROKEN (HIGH confidence)

**We say.** No randomised trial has tested it, and none of the four comparative studies examined here separates them.

**What breaks it.** The 'no randomised trial has tested it' component is broken by the Mansoura/APJCP Phase III RCT (ribociclib vs. palbociclib, 2024) and the HARMONIA Phase III RCT (NCT05207709, ribociclib vs. palbociclib, active). The second clause ('none of the four comparative studies separates them') cannot be evaluated without knowing which four studies the piece cites, but the first clause — a universal negative — is independently broken.

**Citation.** (1) Ahmed Shaaban MH et al. APJCP 25(9):3039–3049, 2024. DOI: 10.31557/APJCP.2024.25.9.3039. (2) NCT05207709 / HARMONIA, ClinicalTrials.gov, status: Active Not Recruiting.

**Their words.** “This is an interventional concurrent randomised phase III open label clinical trial.”

**We inherited this.** The original says: Same lineage as Claims 1 and 2: generalised from scoped guideline/review language about the absence of large, first-line, all-comers head-to-head RCTs.

**Does it change the conclusion.** The first clause of the sentence is a universal negative and is broken. The second clause about the four comparative studies may be accurate as written (those four studies may genuinely not separate the drugs), but the conjunction means the whole sentence is false if either clause is false. The piece's conclusion about the four studies is unaffected by the counterexample, but the framing sentence that introduces it is wrong.

**Searched.** Same searches as Claims 1 and 2. Additionally searched for 'four comparative studies CDK4/6 inhibitor' and 'abemaciclib ribociclib palbociclib comparative study' to attempt to identify the specific four studies referenced, without success (the piece's identity is unknown). The randomised-trial component of the claim is broken regardless.

VERDICT: 
BASIS:   
DID:     


---

### CE-04 — role says NARROWED (HIGH confidence)

**We say.** The evidence's answer is that nothing has been shown to separate them: no randomised trial has compared them, and none of the four comparative studies on this page can tell abemaciclib and ribociclib apart.

**What breaks it.** The claim 'no randomised trial has compared them' is broken for the palbociclib–ribociclib pair (Mansoura/APJCP 2024 RCT; HARMONIA Phase III NCT05207709). However, for the specific pair named in the sentence — abemaciclib and ribociclib — no completed or ongoing randomised head-to-head trial was found. A 2025 matching-adjusted indirect comparison (MAIC) of monarchE vs. NATALEE explicitly states: 'No trials have directly compared efficacy and safety of adjuvant ribociclib and abemaciclib.' The abemaciclib-vs.-ribociclib universal negative therefore survives, but the broader framing ('no randomised trial has compared them' referring to the CDK4/6 class) is false.

**Citation.** For the survival of the abemaciclib–ribociclib specific claim: PMC12465954 (MAIC, 2025): 'No trials have directly compared efficacy and safety of adjuvant ribociclib and abemaciclib.' For the break of the broader class claim: NCT05207709 (HARMONIA) and APJCP 2024 DOI: 10.31557/APJCP.2024.25.9.3039.

**Their words.** “No trials have directly compared efficacy and safety of adjuvant ribociclib and abemaciclib.”

**We inherited this.** The original says: The 'no randomised trial' framing is inherited from class-level review language (e.g., PALMARES-2 Annals of Oncology 2025: 'no large head-to-head comparisons of the three CDK4/6is have been conducted so far'; P-VERIFY PMC12424423: 'no head-to-head RCT data comparing CDK4/6i'). The original sources use qualifiers ('large,' 'in this setting') that were dropped. The abemaciclib–ribociclib specific claim is accurate; the class-level claim is not.

**Does it change the conclusion.** The sentence names abemaciclib and ribociclib specifically in its second clause, and that specific comparison has not been randomised — so the second clause survives. But the first clause ('no randomised trial has compared them') uses 'them' to refer to the CDK4/6 class broadly, and that is broken by the palbociclib–ribociclib trials. The piece's conclusion about abemaciclib vs. ribociclib indistinguishability may be correct, but the sentence's framing — that the absence of any head-to-head RCT is the reason — is inaccurate for the class as a whole. The piece needs to specify 'no randomised trial has compared abemaciclib against ribociclib' rather than making a class-wide claim.

**Searched.** ClinicalTrials.gov (queries: 'abemaciclib ribociclib randomized'; 'abemaciclib versus ribociclib'; 'Verzenio Kisqali randomized'; 'CDK4/6 inhibitor head-to-head abemaciclib'; NCT searches by drug name combination); PubMed/PMC ('abemaciclib ribociclib head-to-head randomized', 'abemaciclib ribociclib versus randomised trial'); ASCO abstracts 2020–2025; ESMO abstracts 2020–2025; EudraCT/CTIS (via EudraCT number cross-reference from ClinicalTrials.gov); ISRCTN (no abemaciclib–ribociclib head-to-head found); WHO ICTRP (via ClinicalTrials.gov international linkage); FDA Drugs@FDA (abemaciclib and ribociclib NDA/sNDA review documents — no head-to-head RCT referenced); EMA EPAR for abemaciclib (Verzenios) and ribociclib (Kisqali) — no head-to-head RCT referenced; PMC12465954 MAIC (2025) explicitly confirms no direct trial exists for adjuvant abemaciclib vs. ribociclib.

VERDICT: 
BASIS:   
DID:     

