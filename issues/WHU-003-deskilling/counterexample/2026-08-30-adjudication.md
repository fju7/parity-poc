# deskilling — counterexample hunt, 2026-08-30

One section per universal negative on the page. A claim is not cleared
by a SURVIVED verdict alone: somebody has to read what was searched and
say whether that search would have found the thing.

    VERDICT: broken | narrowed | survived   — yours, not the role's
    BASIS:   what you read to decide, with a locator
    DID:     what changed on the page, or nothing and why


---

### CE-01 — role says SURVIVED (LOW confidence)

**We say.** So, within the twelve studies that review includes: not one study, and not a settled literature either.

**Does it change the conclusion.** Cannot be evaluated without knowing which review and which twelve studies are referenced. The claim is internally self-referential to a document not identified in the input. No counterexample can be found or ruled out without that anchor. The survival verdict here is a verdict of insufficient context, not a clean search result.

**Searched.** No targeted search was possible because the claim names no review, no condition, no drug, and no field. The claim is a fragment that requires its parent document to be testable. Registries searched would depend entirely on the subject matter of the unnamed review. This is an untestable claim as written.

VERDICT: survived
BASIS:   The role could not test it because it read the sentence without its paragraph -- it says so: "the claim names no review". The review is the Heudel scoping review, named three sentences earlier and cited in full in the source list, and the twelve studies are the twelve its own PRISMA diagram reports including (n = 12, read in the publisher's PDF). Within that set the sentence is a count, not a search: this page read every one of the twelve at source. An untestable-as-extracted verdict is not a survival, and it is not a break either.
DID:     Nothing. The sentence is already scoped to a named set in the sentence before it.


---

### CE-02 — role says NARROWED (MEDIUM confidence)

**We say.** Not one piece of coverage we read named the suspension of the Polish screening programme as the reason the volume rose, or the absence of withdrawal-time data, or the eleven limitations as a body.

**What breaks it.** The Science Media Centre expert reaction (published 12 August 2025, the same day as the Budzyń et al. Lancet paper) explicitly names the volume increase — from 795 to 1,382 colonoscopies — as a potential confound for the deskilling finding, and raises workload/fatigue as an alternative explanation. This is a named limitation about volume, though it attributes the rise to AI introduction workload rather than specifically to the suspension of the Polish screening programme.

**Citation.** https://www.sciencemediacentre.org/expert-reaction-to-observational-study-looking-at-detection-rate-of-precancerous-growths-in-colonoscopies-by-health-professionals-who-perform-them-before-and-after-the-routine-introduction-of-ai/

**Their words.** “"the number of colonoscopies performed nearly doubled after the AI tool was introduced, going from 795 to 1382"”

**We inherited this.** The original says: The claim appears to be the authors' own assertion about their own reading of coverage, not inherited from a guideline or review.

**Does it change the conclusion.** The claim is about what 'coverage we read' named — a set the authors define. The SMC piece is expert commentary, not standard press coverage, and it names the volume rise as a confound but does not specifically attribute it to the suspension of the Polish screening programme. The claim about the screening-suspension explanation specifically, and about the eleven limitations as a body, may still hold within the defined coverage set. The sentence is narrowed, not broken: the volume-rise confound was publicly named in expert commentary on publication day, so any coverage set that included the SMC piece would break the claim.

**Searched.** Web search: 'Polish screening programme suspension colonoscopy volume'; 'Budzyń colonoscopy deskilling study volume increase Polish screening suspension limitation'; 'Fortune August 26 2025 AI deskilling colonoscopy article'; Science Media Centre expert reaction page (August 2025); PMC article on COVID-19 and Polish cancer screening coverage (PMC8314399); Lancet Gastroenterology & Hepatology abstract (PIIS2468-1253(25)00133-5). No registry search was applicable (this is a claim about press coverage, not a clinical trial claim).

VERDICT: narrowed
BASIS:   The counterexample is real and I had it in hand: the SMC page, read at source today, carries Osmani saying "the number of colonoscopies performed nearly doubled after the AI tool was introduced, going from 795 to 1382". The page already treats the SMC as its disconfirming instance and names Osmani twice. But the sentence as written sat three paragraphs later and a careful reader -- this role -- came away thinking nobody had named the rise. That is the sentence's fault, not the reader's. The distinction that survives is narrower and sharper than what we had: the rise travelled, the REASON for it did not. Nobody named the screening-programme suspension, the missing withdrawal times, or the eleven limitations as a body.
DID:     Rewritten. It now opens by crediting Osmani and Time with carrying the rise, and makes the claim about why it rose.


---

### CE-03 — role says BROKEN (HIGH confidence)

**We say.** Communications of the ACM took the finding to knowledge workers, observing that similar issues pop up in law, education, journalism, software development, and other fields ; it carries caveats of its own, about governance and about deskilling having good outcomes as well as bad ones, but none of this study's.

**What breaks it.** The CACM article by Greengard (7 November 2025) does carry the Budzyń et al. colonoscopy finding and does note that deskilling can have positive and negative outcomes and raises governance, but the article also explicitly references the Lancet colonoscopy study's own finding (the 28.4%→22.4% ADR drop) as its anchor example — meaning it carries at least the study's headline result. Whether it carries the study's methodological limitations is a separate question, but the claim 'none of this study's' is contradicted by the article reproducing the study's central quantitative finding.

**Citation.** https://cacm.acm.org/news/the-ai-deskilling-paradox/

**Their words.** “"The detection rate for precancerous lesions dropped from 28.4% to 22.4% without AI in the picture."”

**We inherited this.** The original says: Claim 9 in this same batch is a self-correction of this exact claim, acknowledging it was wrong. That self-correction confirms the break.

**Does it change the conclusion.** The piece's conclusion — that coverage omits the study's limitations — may still hold if 'none of this study's' is read narrowly as referring only to methodological caveats (observational design, confounds, etc.) rather than the headline result. But the sentence as written says 'none of this study's' without qualification, and the CACM piece does carry the study's own numerical finding. The sentence is broken on its face; the underlying point about limitations being omitted may survive a more carefully worded version.

**Searched.** Web search: 'Greengard AI Deskilling Paradox Communications ACM 2025'; direct retrieval of cacm.acm.org/news/the-ai-deskilling-paradox/. No registry search applicable.

VERDICT: survived
BASIS:   A misparse, and a fair one. "It carries caveats of its own... but none of this study's" elides the noun: the role read it as "none of this study's FINDINGS", which would indeed be false, since CACM reproduces the 28.4-to-22.4 result. The sentence means none of this study's CAVEATS, which is what the clause it is joined to is about, and which the source note at the foot of the page states in full. But a sentence that a careful reader takes backwards is a defective sentence on a page whose subject is people taking numbers backwards.
DID:     The noun is now on the page: "but none of this study's caveats."


---

### CE-04 — role says SURVIVED (MEDIUM confidence)

**We say.** arXiv 2601.00856 Their closing sentence — that there is no strong evidence the tool use negatively affects performance itself — is a verdict on the paper they audited, not on the field.

**Does it change the conclusion.** The claim is an interpretive characterisation of the scope of a conclusion in arXiv:2601.00856 (Stankovic et al., 'Comment on: Your Brain on ChatGPT'). The paper exists and is confirmed (submitted 29 December 2025, commenting on arXiv:2506.08872, Kosmyna et al.). The interpretive claim — that the closing sentence is scoped to the audited paper, not the field — is a reading of the text that cannot be falsified by a registry or database search. No counterexample was found that would show the closing sentence makes a field-level claim. The claim survives as a matter of textual interpretation, not empirical fact.

**Searched.** Web search: 'arXiv 2601.00856'; arxiv.org/abs/2601.00856 abstract page; ResearchGate listing; ADS abstract (ui.adsabs.harvard.edu). The abstract confirms the paper's scope (concerns about sample size, EEG methodology, reproducibility, reporting inconsistencies, transparency) but the full text closing sentence is behind the PDF and was not retrieved. Confidence is therefore MEDIUM rather than HIGH.

VERDICT: survived
BASIS:   Verified at source rather than accepted. The Stankovic comment's own closing position is a judgement on the Kosmyna paper it audited; its abstract frames the whole document as comments intended to improve "the manuscript's readiness for peer-reviewed publication", which is a statement about one manuscript. The sentence exists precisely to stop that verdict being read as a finding about the field, so a search that cannot break it is the expected result.
DID:     Nothing.


---

### CE-05 — role says SURVIVED (LOW confidence)

**We say.** Source of the power calculation of roughly 159 participants, the observation that some reported figures rest on two to four essays per group, the discrepancy between 55 completers and 54 analysed — on which the paper itself gives a reason the comment does not address, and this page prints the paper's — the definition of a "significant connection" as a relative measure and the consequence they draw from it, and their assessment that there is no strong evidence that the tool use negatively affects performance itself.

**Does it change the conclusion.** This claim is a list of specific methodological points attributed to arXiv:2601.00856 and to 'this page' (the publishing outlet being audited). It is an internal editorial claim about what specific sources do and do not contain. Verifying it requires full-text access to both the comment paper and the outlet's own page — neither of which is fully accessible via web search. No counterexample was found, but the survival verdict reflects inability to access the full texts, not a clean search. The claim is untestable at the level of granularity required without the source documents.

**Searched.** Web search: 'arXiv 2601.00856'; arxiv.org abstract page; ResearchGate and ADS listings for the Stankovic et al. comment. The abstract lists five primary concerns (sample size, reproducibility, EEG methodology, reporting inconsistencies, transparency) but does not enumerate the specific sub-points listed in the claim. Full PDF not retrieved.

VERDICT: survived
BASIS:   This is a source note, not a claim about the world -- it lists which sentences on the page come from arXiv 2601.00856. The lint catches it because it contains "no strong evidence", which is a quotation of the source. Every item in it was checked against the PDF today, including the clause added this afternoon recording that Kosmyna answers the 55/54 question and the comment does not address the answer.
DID:     Nothing. It was already updated today for the 55/54 finding.


---

### CE-06 — role says SURVIVED (HIGH confidence)

**We say.** No conclusive evidence that difficult general knowledge questions cause a "Google Stroop effect".

**We inherited this.** The original says: Hesselmann G. 2020. 'No conclusive evidence that difficult general knowledge questions cause a "Google Stroop effect". A replication study.' PeerJ 8:e10325. https://doi.org/10.7717/peerj.10325. The claim is the paper's own title, not a secondary paraphrase.

**Does it change the conclusion.** This sentence is the verbatim title of a published, peer-reviewed replication study: Hesselmann G. (2020), PeerJ 8:e10325. The claim is not an assertion made by the piece being audited — it IS the title of a source paper. As a title, it accurately represents the paper's conclusion. The paper found no evidence for the Google Stroop effect across four experiments. Two prior replication attempts (2018) also failed. The original 2011 Sparrow et al. Science finding has not been successfully replicated. The claim survives as an accurate summary of the replication literature as of the search date.

**Searched.** Web search: 'Google Stroop effect difficult general knowledge questions study'; PubMed (PMID 33194451); PeerJ (peerj.com/articles/10325); Semantic Scholar; ResearchGate. No registry search applicable (this is a cognitive psychology replication study, not a clinical trial). ClinicalTrials.gov, WHO ICTRP, EudraCT, ISRCTN not searched as irrelevant to this claim type.

VERDICT: survived
BASIS:   This is the verbatim title of a published paper -- Hesselmann, PeerJ 2020, article 10325 -- appearing in the source list. Attacking a title as though it were our assertion is a false positive of the extractor, and the role said so. Worth recording rather than silently dropping: the lint should not be taught to skip titles, because a title we chose to quote is still a claim we are carrying.
DID:     Nothing.


---

### CE-07 — role says SURVIVED (LOW confidence)

**We say.** The first time we asked it only about the study's limitations, and so missed the mechanism paragraph entirely; the repository records that as our error rather than its omission.

**Does it change the conclusion.** This is an internal editorial/process claim about the authors' own interaction with an AI tool and their own repository log. It is not a factual claim about the external world that can be verified or falsified by searching databases, registries, or published literature. No counterexample is possible from external sources. The claim survives by default — it is untestable from outside the authors' workflow.

**Searched.** No external search is possible or meaningful for a claim about an internal editorial process and a private repository log. No registries, databases, or literature sources are relevant.

VERDICT: survived
BASIS:   An internal claim about our own process -- that we asked a source-reading role the wrong question the first time and the repository records it as our error. There is no external counterexample to a statement about our own files, and the role correctly found none. Verified against the repository record rather than left as an assertion.
DID:     Nothing.


---

### CE-08 — role says NARROWED (MEDIUM confidence)

**We say.** Fortune , 26 August 2025 Carries the six-point fall to a business readership, connects it to a Microsoft and Carnegie Mellon survey and to an aviation analogy, and reports none of the study's eleven limitations.

**What breaks it.** The Fortune article of 26 August 2025 (dc.fortune.com/2025/08/26/ai-overreliance-doctor-procedure-study, by Sasha Rogelberg) does exist and does cover the Budzyń et al. finding. However, the claim that it 'connects it to a Microsoft and Carnegie Mellon survey and to an aviation analogy' cannot be confirmed from the retrieved snippet — those elements appear in the CACM Greengard piece, not necessarily in the Fortune piece. The Fortune article's connection to the Microsoft/CMU survey and aviation analogy is unverified; those details may have been misattributed from the CACM article.

**Citation.** https://dc.fortune.com/2025/08/26/ai-overreliance-doctor-procedure-study

**Their words.** “"Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own, study finds"”

**Does it change the conclusion.** The Fortune article exists on the stated date and does carry the deskilling finding. The specific claim that it connects to a Microsoft/CMU survey and an aviation analogy is unverified — those elements are confirmed in the CACM piece (Greengard), not in the Fortune piece from the retrieved text. If those elements are absent from the Fortune piece, the characterisation of its content is partially wrong. The claim about 'none of the study's eleven limitations' cannot be verified or falsified without full-text access to the Fortune article.

**Searched.** Web search: 'Fortune AI deskilling six-point August 2025'; 'Fortune August 26 2025 AI deskilling colonoscopy article'; dc.fortune.com/2025/08/26/ai-overreliance-doctor-procedure-study retrieved. CACM article retrieved separately. No registry search applicable.

VERDICT: survived
BASIS:   The role could not retrieve the Fortune full text and inferred the Microsoft/Carnegie Mellon and aviation elements might have been misattributed from the CACM piece. They were not. The article, opened at the URL the page cites, carries verbatim: "A study from Microsoft and Carnegie Mellon University earlier this year found that among surveyed knowledge workers, AI increased work efficiency, but reduced critical engagement with content, atrophying judgment skills" -- and the aviation analogy is Air France 447, described at length. It reports no limitation of the colonoscopy study; the nearest it comes is noting the researchers "did not anticipate this outcome and therefore did not collect data on why this happened", which is not one of the eleven. The note stands as written. Same failure mode as the SOURCE role's verdict on this article earlier today: it searched for the piece instead of opening the URL beside the claim.
DID:     Nothing on this note. Opening the article again is what produced the Fortune correction now printed in the body -- that its account of the study's design is false.


---

### CE-09 — role says SURVIVED (HIGH confidence)

**We say.** Greengard S, "The AI Deskilling Paradox", Communications of the ACM , 7 November 2025, carries none of this study's limitations but does carry caveats of its own, on governance and on deskilling having good outcomes as well as bad ones; we had described it as carrying none, and that was wrong.

**Does it change the conclusion.** This claim is itself a self-correction of Claim 3 above. It asserts: (a) the CACM piece carries no limitations from the Budzyń et al. study; (b) it does carry its own caveats on governance and on deskilling having good and bad outcomes; (c) the prior description of it as carrying 'none' was wrong. Parts (b) and (c) are confirmed by the retrieved CACM text — the article does note that 'Deskilling can lead to a variety of positive and negative outcomes' and discusses governance. Part (a) — that it carries none of the study's own methodological limitations — is consistent with the retrieved text, which reproduces the headline finding but shows no discussion of the study's observational design, confounds, or other limitations. The self-correction in (c) is accurate. No counterexample to the corrected claim was found.

**Searched.** Web search: 'Greengard AI Deskilling Paradox Communications ACM 2025'; cacm.acm.org/news/the-ai-deskilling-paradox/ retrieved. Confirmed: article discusses governance, positive/negative deskilling outcomes, and carries the headline ADR figures. No methodological limitations of the Budzyń study were found in the retrieved text.

VERDICT: survived
BASIS:   A source note recording a correction we already made -- we had said CACM carried no caveats at all, and it does carry its own, on governance and on deskilling having good as well as bad outcomes. The role found nothing to break because the sentence is already the corrected version. CACM's page returned 403 to a direct read today; the note rests on the earlier reading, and that limit is recorded here rather than left silent.
DID:     Nothing.

