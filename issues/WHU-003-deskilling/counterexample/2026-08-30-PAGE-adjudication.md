# deskilling — counterexample hunt, 2026-08-30-PAGE

One section per universal negative on the page. A claim is not cleared
by a SURVIVED verdict alone: somebody has to read what was searched and
say whether that search would have found the thing.

    VERDICT: broken | narrowed | survived   — yours, not the role's
    BASIS:   what you read to decide, with a locator
    DID:     what changed on the page, or nothing and why


---

### CE-01 — role says LOW (LOW confidence)

**We say.** So, within the twelve studies that review includes: not one study, and not a settled literature either.

**We inherited this.** The original says: Unknown — the referent review is not identified in the claim as submitted.

**Does it change the conclusion.** The claim is syntactically incomplete as presented — it is a sentence fragment ('not one study, and not a settled literature either') that appears to be torn from a larger argument about what a specific review's twelve studies do or do not show. Without knowing which review and which twelve studies are referenced, it is impossible to verify or falsify the universal negative embedded in it. The claim cannot be broken without knowing its referent.

**Searched.** The claim contains no named review, drug, condition, or study set to search against. No registry or database search was possible without a referent. Searched Google Scholar and general web for 'twelve studies review LLM cognitive performance' and 'twelve studies review AI cognitive decline' — no matching review identified. ClinicalTrials.gov, WHO ICTRP, EudraCT/CTIS, ISRCTN, FDA Drugs@FDA, and EMA EPAR were not searched because the claim does not name any intervention, comparator, or condition that would generate a registry query.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-02 — role says LOW (LOW confidence)

**We say.** There is no study on this page that followed anyone for months and found no decay, because the one we were told was that study is not.

**We inherited this.** The original says: Appears to be a meta-commentary on a curated reading list or article page, not a primary source claim.

**Does it change the conclusion.** The claim refers to 'this page' — an unspecified webpage or document — and asserts that no study on it followed participants longitudinally and found no cognitive decay. Without knowing which page is meant, the universal negative cannot be tested. The Kosmyna et al. (arXiv:2506.08872) study did follow participants over four months, but the Stanković comment (arXiv:2601.00856) argues its Session 4 (the only session that could show decay) had only n=18 (six per condition), making the longitudinal claim fragile. Whether that constitutes 'found no decay' or 'found decay' depends on interpretation. The claim as written is untestable without the referent page.

**Searched.** Searched for 'LLM cognitive performance longitudinal study no decay months' and 'AI cognitive decline longitudinal no effect study'. Reviewed Kosmyna et al. arXiv:2506.08872 and Stanković et al. arXiv:2601.00856 abstracts and secondary coverage. No registry search was applicable — the claim does not name an intervention or condition amenable to ClinicalTrials.gov, WHO ICTRP, EudraCT/CTIS, ISRCTN, FDA Drugs@FDA, or EMA EPAR queries.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-03 — role says NARROWED (MEDIUM confidence)

**We say.** Stanković and colleagues' own assessment of that paper, in their comment on it, is that there is no strong evidence that the LLM use negatively affects performance itself.

**What breaks it.** The publicly available abstract of arXiv:2601.00856 does not use the phrase 'no strong evidence that LLM use negatively affects performance itself.' The abstract states that the authors' concerns focus on sample size, reproducibility, EEG methodology, inconsistencies in reporting, and limited transparency — i.e., methodological critique — and that 'some results by Kosmyna et al. (2025) could be interpreted more conservatively.' The claim as written attributes a specific conclusion ('no strong evidence that LLM use negatively affects performance itself') to Stanković et al. that the abstract does not contain verbatim. The full PDF may contain this language, but the abstract — the only portion retrievable — supports only a narrower reading: that the results warrant more conservative interpretation, not that performance effects are absent.

**Citation.** https://arxiv.org/abs/2601.00856

**Their words.** “"some results by Kosmyna et al. (2025) could be interpreted more conservatively"”

**We inherited this.** The original says: The specific phrasing 'no strong evidence that the LLM use negatively affects performance itself' appears to originate in a secondary summary (e.g., the Senwitt deep-dive page at learn.senwitt.com, which paraphrases the Stanković comment) rather than in the Stanković comment's own abstract. The Stanković abstract's actual scope is methodological critique and a call for conservative interpretation.

**Does it change the conclusion.** This matters for the piece's argument: if the Stanković comment actually says only 'interpret more conservatively' rather than 'no strong evidence of performance harm,' then citing it as an endorsement of the stronger negative claim overstates what the comment says. The piece's conclusion may still be directionally correct, but the sentence as written misrepresents the comment's scope.

**Searched.** Searched arXiv.org abstract page for 2601.00856; ResearchGate listing for the same paper; Senwitt deep-dive page (learn.senwitt.com/research/your-brain-on-chatgpt/); PsyPost coverage; PennNeuroKnow coverage. Searched for 'Stanković 2601.00856 full text no strong evidence performance'. Full PDF text was not directly retrievable in search results. ClinicalTrials.gov, WHO ICTRP, EudraCT/CTIS, ISRCTN, FDA Drugs@FDA, and EMA EPAR are not applicable to this claim.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-04 — role says NARROWED (MEDIUM confidence)

**We say.** arXiv 2601.00856 Source of the power calculation of roughly 159 participants, the observation that some reported figures rest on two to four essays per group, the discrepancy between 55 completers and 54 analysed, the definition of a 'significant connection' as a relative measure and the consequence they draw from it, and their assessment that there is no strong evidence that the tool use negatively affects performance itself.

**What breaks it.** arXiv:2601.00856 (Stanković et al., submitted 29 December 2025) is confirmed to exist and to be a comment on Kosmyna et al. (arXiv:2506.08872). Its abstract confirms concerns about sample size, reproducibility, EEG methodology, inconsistencies in reporting, and limited transparency. However, the specific details attributed to it — the power calculation of ~159 participants, the 55/54 discrepancy, the 'two to four essays per group' observation, the definition of 'significant connection' as a relative measure, and the exact phrase 'no strong evidence that the tool use negatively affects performance itself' — cannot be verified from the publicly indexed abstract alone. The paper exists and is directionally consistent with these claims, but the specific numerical and terminological details require the full PDF to confirm or deny.

**Citation.** https://arxiv.org/abs/2601.00856

**Their words.** “"(iv) inconsistencies in the reporting of results; and (v) limited transparency in several aspects of the study's procedures"”

**We inherited this.** The original says: The abstract of arXiv:2601.00856 is the confirmed source for the general methodological critique. The specific numerical details (159, 55 vs. 54, 2–4 essays) are not verifiable from the abstract and may be the piece's own derivations attributed to Stanković et al.

**Does it change the conclusion.** If any of the specific attributed details (e.g., the 159-participant power calculation, the 55/54 discrepancy) are not in arXiv:2601.00856 but are instead the piece's own calculations, the sentence misattributes them. This would be a sourcing error, not a factual error about the underlying study — but it would still break the sentence as written.

**Searched.** Searched arXiv.org abstract for 2601.00856; arxiv.org PDF link (arxiv.org/pdf/2601.00856); ResearchGate listing; ADS abstract (ui.adsabs.harvard.edu). Full PDF content was not returned in search snippets. Searched 'arXiv 2601.00856 power calculation 159 participants' and '55 completers 54 analysed Kosmyna'. No registry search applicable.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-05 — role says BROKEN (HIGH confidence)

**We say.** No conclusive evidence that difficult general knowledge questions cause a 'Google Stroop effect'.

**What breaks it.** This is the verbatim title of a published, peer-reviewed replication study: Hesselmann, G. (2020). 'No conclusive evidence that difficult general knowledge questions cause a "Google Stroop effect". A replication study.' PeerJ 8:e10325. The claim as written is not an original assertion — it is the title of an existing paper. If the piece presents this phrase as its own conclusion or as an unattributed finding, it is reproducing the title of Hesselmann (2020) without attribution. If the piece cites Hesselmann (2020) correctly, the sentence is fine. The 'break' is that the phrase is not the piece's own finding: it already exists as a published paper title.

**Citation.** https://peerj.com/articles/10325/ — Hesselmann, G. (2020). PeerJ 8:e10325. DOI: 10.7717/peerj.10325

**Their words.** “"No conclusive evidence that difficult general knowledge questions cause a 'Google Stroop effect'. A replication study"”

**We inherited this.** The original says: Hesselmann, G. (2020). PeerJ 8:e10325. The original Sparrow, Liu & Wegner (2011) Science paper claimed the effect; Hesselmann (2020) is the registered replication that failed to confirm it.

**Does it change the conclusion.** If the piece presents this as its own conclusion without citing Hesselmann (2020), it is an attribution error. If it cites Hesselmann correctly, the sentence survives. The underlying finding — that the Google Stroop effect did not replicate — is real and published. The break is sourcing, not substance.

**Searched.** Searched PubMed (PMC7651475), PeerJ, Semantic Scholar, and ResearchGate for 'Google Stroop effect difficult general knowledge questions'. Confirmed Hesselmann (2020) as the source. Also searched ClinicalTrials.gov for 'Google Stroop effect' — no registered trials found. WHO ICTRP, EudraCT/CTIS, ISRCTN not applicable to a cognitive psychology paradigm study. FDA Drugs@FDA and EMA EPAR not applicable.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-06 — role says LOW (LOW confidence)

**We say.** Read twice: the first reading asked only about the study's limitations and did not surface the mechanism, which is recorded in the repository as an error of ours.

**We inherited this.** The original says: Self-generated; refers to an internal editorial process.

**Does it change the conclusion.** This is a self-referential procedural claim about the piece's own reading process and an internal repository record. It is not a factual claim about the external world that can be verified or falsified by searching registries, databases, or the literature. No counterexample is possible from external sources.

**Searched.** No external search is possible or meaningful for a claim about the piece's own internal reading log. ClinicalTrials.gov, WHO ICTRP, EudraCT/CTIS, ISRCTN, FDA Drugs@FDA, EMA EPAR, and literature databases are not applicable.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.


---

### CE-07 — role says NARROWED (MEDIUM confidence)

**We say.** Fortune, 26 August 2025 Carries the six-point fall to a business readership, connects it to a Microsoft and Carnegie Mellon survey and to an aviation analogy, and reports none of the study's eleven limitations.

**What breaks it.** A Fortune article dated 26 August 2025 about the MIT brain/ChatGPT study with those specific elements — a six-point fall, a Microsoft/Carnegie Mellon connection, an aviation analogy, and zero of eleven limitations — could not be confirmed. The closest confirmed Fortune coverage is: (a) a Fortune article from February 11, 2025 about the Microsoft/Carnegie Mellon critical-thinking survey (fortune.com/2025/02/11/ai-impact-brain-critical-thinking-microsoft-study/), and (b) a Forbes article dated 26 August 2025 about MIT's GenAI pilot failure rate (forbes.com/sites/jasonsnyder/2025/08/26), which is a different study entirely. An MIT News clip records a Forbes article from July 2, 2025 about the Kosmyna study. No Fortune article dated specifically 26 August 2025 covering the Kosmyna study with those three specific elements was found.

**Citation.** https://fortune.com/2025/02/11/ai-impact-brain-critical-thinking-microsoft-study/ (Microsoft/CMU study, February 2025); https://news.mit.edu/news-clip/forbes-787 (Forbes, July 2, 2025, Kosmyna study); https://www.forbes.com/sites/jasonsnyder/2025/08/26 (Forbes, August 26, 2025, different MIT study)

**Their words.** “"New research from authors at Microsoft and Carnegie Mellon University finds that leaning too much on tools such as ChatGPT is associated with weaker critical thinking"”

**We inherited this.** The original says: The Microsoft/Carnegie Mellon survey is a real February 2025 study (fortune.com/2025/02/11). The Kosmyna MIT study is real (arXiv:2506.08872, June 2025). The claim appears to combine both into a single attributed Fortune article dated 26 August 2025, which may be a conflation.

**Does it change the conclusion.** If the Fortune article dated 26 August 2025 does not exist as described, the sentence is a fabricated citation — the most serious possible error. If it exists but is behind a paywall not indexed by search, the sentence may be correct but unverifiable. Either way, the specific date, outlet, and combination of elements (six-point fall + aviation analogy + Microsoft/CMU + zero limitations) could not be confirmed, which is a material finding for any fact-check.

**Searched.** Searched 'Fortune August 26 2025 MIT ChatGPT cognitive six point aviation'; 'Fortune August 2025 MIT brain cognitive decline Microsoft Carnegie Mellon aviation'; 'Fortune 26 August 2025 LLM cognitive'; MIT News clip archive (news.mit.edu/news-clip/forbes-787); Forbes August 26 2025 results. Also searched ClinicalTrials.gov, WHO ICTRP, EudraCT/CTIS, ISRCTN — not applicable to a media coverage claim. FDA Drugs@FDA and EMA EPAR not applicable.

VERDICT: survived
BASIS:   Seven sentences were extracted; FIVE ARE NOT OUR CLAIMS. One is the verbatim title of Hesselmann's paper, correctly reported BROKEN by the role because the paper exists. Two are source-list notes describing what Fortune and Zhou carry. One is our own process note about reading a source twice. The extractor keys on the shape of a universal negative and cannot tell a claim from a title, which is a known limit and not a defect in the page.
         Of the two claims that ARE ours, the role returned LOW confidence and no counterexample on both: that within the twelve studies the review includes there is not one settled literature, and that no study on this page followed anyone for months and found no decay. Both stand as written, and both are already scoped on the page.
         Two NARROWED verdicts were checked and neither survives. The role said the Stankovic phrase 'no strong evidence that LLM use negatively affects performance' does not appear in the abstract of arXiv 2601.00856 — it was reading the abstract; the PDF contains it verbatim: 'However, there is no strong evidence that the LLM use negatively affects performance itself.' The role also doubted the Fortune citation and offered a different Fortune article from February 2025. The August piece is confirmed: Sasha Rogelberg, 26 August 2025, the colonoscopy study, 28.4% to 22.4%, the Microsoft and Carnegie Mellon study and the Air France 447 example, all present.
DID:     Nothing removed. One thing ADDED, because verifying the Fortune citation turned up a detail worth the reader's attention: its headline is 'Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own'. Twenty per cent is the relative decline and six points is the absolute one, and both are true. The page now says so. It is the clearest small illustration of how a finding changes on the way out of its field without anybody printing anything false.

