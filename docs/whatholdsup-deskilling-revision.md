# Deskilling — pending page corrections for the republish

Issue: `issues/WHU-003-deskilling/`; page: `site/whatholdsup/deskilling.html` (live at
whatholdsup.org/deskilling, unchanged since 30 August). Opened 2026-10-18 from binding
batch 1. Nothing here is on the page yet: each correction goes out through `publish.py`
with the republish, with a `corrections.md` entry. Proposed wording is the operator's
unless marked otherwise. Rows are binding-row shas in `bindings.json`.

## Errors found in the published page

22 errors in about 71 sentences read closely — 12 overstate a finding, 4 misattribute or misdescribe, 2 misquote, 1 misstates how a source was read, 3 understate a source's standing (published work called "accepted" or "a preprint"); 0 understate a finding.

| | count | rows |
|---|---|---|
| overstates a finding | 12 | 32db25e0, 509b18f6, b8844660, bd8b242c, ad3f7c73; batch 3: ed48b451, 41c3df15, 1c761af8, 94b39b65, 8762158c, f8238a88, 94cd79d4 |
| misattributes or misdescribes | 4 | 26e94905, 8598e9ca, 34b99db8; batch 3: 73aed151 |
| misquotes | 2 | Q-25; batch 3: e0713036 |
| misstates how a source was read | 1 | the Wang paragraph (c8d0e2c5, 5bd6e3b7, b8844660 rest on it) — now true once those rows bind to S046 |
| understates a source's standing | 3 | batch 3: 7a05297b, 4173a438, e14ccbb0 |
| understates a finding | 0 | |

Of the 10 batch-3 errors, the automatic checks caught 1 on the uncorrected text; close reading against the source found the rest.

Not in the count above (operator's call): a4267014 and 09ba5473, §27 and §28 — "without warning" is S001's description of Experiment 1 only, found by the batch-3 write's conditional check.

Not counted as errors: Q-17 (a title marked as a quotation; formatting) and 43.8 (in S031's
Table 2 as 43.79, correctly rounded; no change).

## 1. 32db25e0 — "adjusted", and a dropped hedge

**Page now:** After the AI was removed it was 36.3% (173 of 476) against the 31.9% baseline — an adjusted odds ratio of 1.03 , on 0.79 to 1.34, which is no change.

**Problem:** S043's table gives 1.03 (0.79–1.34) for phase 3 in the *univariable* column;
the multivariable cell for phase 3 is "–". The adjusted odds ratio S043 reports (1.43) is
for phase 2. And S043 says "no significant change", not "no change".

**Source (S043, full_text_held):** abstract — "There was no significant change between
phases 1 and 3 (31.9% [216/678] to 36.3% [173/476]; OR 1.03, 95%CI 0.79-1.34)."; table,
phases 1 and 3 — "Inexperienced 173/476 (36.3) 1.03 (0.79-1.34) -" (univariable, then
multivariable).

**Proposed:** "After the AI was removed it was 36.3% (173 of 476) against the 31.9%
baseline — an unadjusted odds ratio of 1.03, on 0.79 to 1.34, not a statistically
significant change."

## 2. 509b18f6 — "indistinguishable"

**Page now:** The system detected polyps faster than people did — a median 1.16 seconds against 2.97 — but the people using it were no faster than the people working without it (2.90 seconds, indistinguishable from 2.97).

**Problem:** stronger than the source. S031's abstract says the reaction time with CADe
"was similar to that without CADe"; its Results say it "was not statistically different
from that without CADe support".

**Proposed:** replace "indistinguishable from 2.97" with "not statistically different
from 2.97".

## 3. 26e94905 — "retrospective" attributed to the review

**Page now:** Its abstract describes the colonoscopy study as “a multicenter randomized trial”; the study is retrospective and observational, as the review’s own body says.

**Problem:** S029's body says the study is "observational" ("A multicenter observational
study conducted in Poland and published in The Lancet"); "retrospective" does not occur
anywhere in S029. The word is the study's own: S021 (Budzyń et al., the same Lancet
Gastroenterol Hepatol paper, author's accepted manuscript), Methods: "We conducted a
retrospective observational study at four endoscopy centers in Poland."

**Proposed:** replace "the study is retrospective and observational, as the review's own
body says" with "the study is observational, as the review's own body says, and
retrospective, as the study itself states". **Binding:** when this row is bound, add S021
(that Methods sentence) as `also_rests_on`.

## 4. ad3f7c73 — Decker and the Nature Reviews highlight

**Page now, with the two sentences it depends on (verbatim, in order):**

> Fortune , 26 August 2025 Carries the six-point fall to a business readership, connects it to a Microsoft and Carnegie Mellon survey and to an aviation analogy, and reports none of the study’s eleven limitations.
> Cited here as an instance, not for any figure.
> The same is true of the research highlight in Nature Reviews Gastroenterology & Hepatology of 5 September 2025 and of Decker J, “When AI Reads the Easy Cases”, Rad Insights, 15 May 2026 — which pairs the colonoscopy and mammography results and is the closest published thing to this page.

**Problem:** "The same is true of" carries the Fortune sentence's claim — that the piece
"reports none of the study's eleven limitations" — over to Decker and to the Nature
Reviews highlight. Decker (S034, full_text_held) names the design: "Budzyń and colleagues
published a multicentre observational study…", the limitation the page credits The ASCO
Post with reporting ("its observational nature"). The Nature Reviews highlight (S027) is
now held only as Nature's subscription preview (abstract_held), which itself calls the study
"A new multicentre, observational study" and "this retrospective study".

**Evidence:** S027 preview: "A new multicentre, observational study has examined whether
continuous exposure to artificial intelligence (AI) …"; "In this retrospective study at four
endoscopy centres in Poland taking part in the ACCEPT trial …"; the preview stops at "This is
a preview of subscription content". S034 (full text): "Budzyń and colleagues published a
multicentre observational study in Lancet Gastroenterology & Hepatology …"; searched and
absent from S034: retrospective; the screening programme's suspension or the 795-to-1,382
rise; withdrawal time; blinding of the study ("blind" occurs only as "AI-blind reading
slots"); the exclusion of the first 100 procedures; confounding; "limitation". The Fortune
sentence before it stands: S023 mentions none of the eleven limitations (§12).

**Proposed (replacing ad3f7c73):**

> The research highlight in Nature Reviews Gastroenterology & Hepatology of 5 September 2025 calls it a multicentre, observational, retrospective study; we hold only the publisher's preview, which says nothing more about its limitations. Decker J, “When AI Reads the Easy Cases”, Rad Insights, 15 May 2026, calls it a multicentre observational study but mentions none of these others: the near-doubling of procedures after the screening programme was suspended, the missing withdrawal times, the absence of blinding, or the exclusion of the first 100 procedures. It pairs the colonoscopy and mammography results and is the closest published thing to this page.

**Binding for the corrected text:** judgement; premises S027 (the two preview sentences),
S034 (the Budzyń sentence; the Dratsch mammography sentence); step: both name the design;
S034's full text names none of the listed limitations (bounded term search above); S027 is
a preview, so nothing is said about what the rest of it omits.

## 5. c8d0e2c5, 5bd6e3b7, b8844660 — Wang et al., "read here at source"

**Page now:** the paragraph introducing them says "Among them, and each read here at
source rather than through the review's summary of it:", then:

- c8d0e2c5: AI assistance raised overall diagnostic accuracy from 87.2% to 96.4%.
- 5bd6e3b7: It also accounted for the errors that remained: 45.5% of the errors made under AI assistance were attributable to automation bias , across all levels of experience.
- b8844660: When the authors tested selectively withholding AI outputs that were likely to mislead, automation bias fell by 41.7%.

**Problem:** Wang DY et al., J Am Med Inform Assoc 2023;30(10):1684-1692 (S029's reference
22) is not held and has no row in `sources.json`. The only held text carrying these
figures is S029's summary of it — the route the page says it did not take. And b8844660
says the authors "tested" withholding outputs, where S029 says they "proposed an 'AI
suppression' strategy … reducing automation bias by 41.7%"; whether 41.7% was measured or
simulated needs Wang itself.

**Resolved 18 October 2026:** Wang is held (S046, the published version, via PMC).
c8d0e2c5 and 5bd6e3b7 are bound to S046 with their page text unchanged — Wang defines "A
misleading event (automation bias) … as the clinician's original correct diagnosis being
misled by a wrong AI diagnosis", and the 45.5% is 132/290 of those, so "attributable to"
stands; "The automation bias was found to affect clinicians of all levels of expertise".
With those bindings the paragraph's "read here at source" is true for Wang.

**b8844660 still needs the page change.** Wang: "We simulated a third-round clinician-AI
interaction test with this AI suppression strategy … It was assumed that the clinicians'
diagnoses would switch to their AI-unassisted diagnoses"; "If we had retracted the AI
diagnosis of these 16 MRIs … the misleading events were estimated to be decreased by
41.7%"; limitation (3): "The third-round clinician-AI interaction test was a simulation and
the reading session was not repeated."

**Proposed (b8844660):** "When the authors simulated selectively withholding AI outputs that
were likely to mislead, recalculating their own data on the assumption that clinicians
would fall back on their unassisted diagnoses, automation bias was estimated to fall by
41.7%."

**Binding for the corrected text:** S046, the 41.7% Results sentence; also_rests_on the
Methods simulation passage.

## 6. S005 not linked in the source list

S005 (Ingebrigtsen & Lukic audit, PsyArXiv, osf.io/wgu56) is not linked in the page's
source list; a84075d9 and 5850f3bd rest on it. Republish must add the link. (The audit is
named only inside the note of the *Retraction Note* entry, whose link is nature.com.)

Binding those two rows raised a new preflight block, "every document the piece rests on is
in the list a reader sees" (S005). It is accepted on the same basis as the S033/S034/S045
block of 52f2205: the records are ahead of the page, and it clears at republish.

## 7. bd8b242c — a significance qualifier dropped

**Page now:** Access to it raised their confidence by 11.7 percentage points while about half its answers were faulty — and their confidence did not fall as they met more wrong answers.

**Problem:** S017 (Shaw & Nave, SSRN working paper, held): "Within the AI-Assisted condition,
confidence did not significantly decline as the number of faulty trials increased (β = -1.14,
SE = 0.89, t = -1.28, 95% CI [-2.88, 0.61], p = 0.202)." The page drops "significantly".
The rest is supported: "Despite approximately half of System 3 answers being faulty, access to
AI increased confidence by 11.7 percentage points". B19's new check catches this ("significance
qualifier dropped").

**Proposed:** "Access to it raised their confidence by 11.7 percentage points while about
half its answers were faulty — and their confidence did not fall significantly as they met
more wrong answers."

**Binding for the corrected text:** S017, the Confidence sentence (11.7, half faulty);
also_rests_on the β/p = 0.202 sentence.

## 8. 8598e9ca — not their closing sentence

**Page now:** arXiv 2601.00856 Their closing sentence — that there is no strong evidence the tool use negatively affects performance itself — is a verdict on the paper they audited, not on the field.

**Problem:** S019 (the comment's PDF, held): the sentence "However, there is no strong evidence
that the LLM use negatively affects performance itself." sits at character 14,281 of 17,886,
inside the paragraph beginning "Finally, the results presented in the commented paper …", with
more argument after it. The comment closes: "Ultimately, the field stands to gain significantly
from further exploration of the cognitive impact of AI tools, but careful attention to these
methodological challenges is essential to ensure more reliable and meaningful conclusions."
Also S019 says "the LLM use", the page "the tool use".

**Proposed:** "arXiv 2601.00856 Their sentence that there is no strong evidence the LLM use
negatively affects performance itself is a verdict on the paper they audited, not on the
field." (2601.00856 is declared citation furniture.)

**Binding for the corrected text:** S019 PDF, that sentence.

## 9. 34b99db8 — "the cross-sectional design" is not Gerlich's description

**Page now:** Societies 2025;15(1):6 Source of the 666 valid responses of 669, the recruitment through social media in the United Kingdom, the cross-sectional design, and the three correlations of −0.68, +0.72 and −0.75.

**Problem:** S008 (Gerlich, published, held) calls its design "a mixed-method design": "A
structured questionnaire consisting of 23 questions" and "Semi-structured interviews were
conducted with a subset of 50 participants" (Results: "50 semi-structured interviews"). Its
abstract says "surveys and in-depth interviews with 666 participants"; the Methods and Results
agree on 50 and are the ones to cite. 666 of 669, the UK, social media and the three
correlations are all in S008.

**Proposed:** "Societies 2025;15(1):6 Source of the 666 valid responses of 669, the recruitment
through social media in the United Kingdom, the mixed-method design — a single 23-question
questionnaire and 50 semi-structured interviews — and the three correlations of −0.68, +0.72
and −0.75."

**Binding for the corrected text:** S008: 3.2 Participants (669/666, UK, social media); 3.3 the
questionnaire; 3.4 the 50 interviews; Table 6 (correlations).

## 10. Q-25 — a spliced quotation

**Page now:** it says it reports 54 <q>to ensure data distribution (as participants were
assigned in three groups)</q>

**Problem:** S007: "To ensure data distribution, we are here only reporting data from 54
participants (as participants were assigned in three groups, see details below)." The
quotation silently omits ", we are here only reporting data from 54 participants" and ", see
details below". The meaning is not changed (the page states the 54 outside the quotation
marks), but a quotation with silent omissions is not verbatim.

**Proposed:** it says it reports 54 participants <q>to ensure data distribution</q>, because
<q>participants were assigned in three groups</q>

**Record for the corrected text:** two quotation records against S007, each fragment verbatim.

## 11. Q-17 — a title, not a quotation

**Page now:** Gastroenterology published an editorial by Weinberg and Bretthauer titled
<q>Upskilling, Deskilling, or Never Skilling: Who Benefits From Artificial Intelligence in
Colonoscopy?</q>

**Evidence:** Crossref (DOI 10.1053/j.gastro.2026.05.026): title "Upskilling, Deskilling, or
Never Skilling: Who Benefits From Artificial Intelligence in Colonoscopy?"; authors David S.
Weinberg, Michael Bretthauer; Gastroenterology; issued June 2026 — identical. S044 itself is
blocked.

**Proposed:** titled <cite>Upskilling, Deskilling, or Never Skilling: Who Benefits From Artificial
Intelligence in Colonoscopy?</cite> — a title, which the quotation check does not read; bound to
S044's Crossref record.

## 12. Fortune (S023) — "reports none of the study's eleven limitations" stands

Term search and a read of S023's whole passage on the study against S021's eleven
limitations (first … tenth, finally): none appears. Its one caveat — "To be sure, Romańczyk and
his team did measure why endoscopists behaved this way because they did not anticipate this
outcome and therefore did not collect data on why this happened" — is about the mechanism, not
one of the eleven (and reads as a typo for "did not measure"). No change.

## 13. 43.8 (fa3d6649, 0f7a7387) — in S031's Table 2, no change

S031's Table 2 ("Percentage of time an examiner inspected false-positive bounding boxes relative
to duration of the bounding box on screen"), row "All", column "All": "43.79 (40.71-54.89)". The
page's 43.8 is that figure correctly rounded one place; rule 1 passes it with an INFO note.
"least of all for the briefest ones": the Mild row (24.76) is the lowest. Table 2 is in the held
Europe PMC XML as well as in Thieme's PDF, now held as S031's second rendition (version of
record). No page change; bindings to propose: fa3d6649 → S031 Table 2 + "Participants inspected
the bounding boxes for < 50 % of the time …"; 0f7a7387 → the same plus Results (21 participants,
10 novice and 11 experienced, 1218 experiments; the 3-week washout; reaction times; 4 to 6 false
identifications, P = 0.001) and Table 1 (eye travel).

## 14. Unbound until a source is held

None left from batch 1: 43a5da1b (S008) is bound; 34b99db8, bd8b242c and 8598e9ca have their
sources held and corrections above.

## 15. 94cd79d4 — "the largest", and "primarily" dropped

**Page now:** The authors list eleven limitations of their own, and the largest is not subtle: the total number of procedures in the second period nearly doubled, from 795 to 1,382 — while the non-AI procedures actually measured fell from 795 to 648 — because Poland suspended its colonoscopy-based screening programme on 1 January 2022 and the centres used the freed capacity to draw patients off the waiting list.

**Evidence:** S021 numbers its eleven limitations (First … Tenth, Finally) and ranks none of them; "the largest" was our ranking stated as fact. And the eighth limitation says the volume rise "was primarily due to the temporary suspension of the colonoscopy-based colorectal cancer screening programme in Poland on 1 January 2022"; the page said "because".

**Proposed:** "The authors list eleven limitations of their own, and the one we think matters most is not subtle: the total number of procedures in the second period nearly doubled, from 795 to 1,382 — while the non-AI procedures actually measured fell from 795 to 648 — primarily because Poland suspended its colonoscopy-based screening programme on 1 January 2022 and the centres used the freed capacity to take more patients from the waiting list."

**Binding for the corrected text:** judgement. premise S021: "The present study has several limitations." premise S021: "Eighth, we observed an almost two-fold increase in the number of procedures in the post-AI phase compared to …" premise S021: "Finally, the number of examinations performed by some endoscopists was relatively low" premise S021: "Before AI implementation N=795 After AI implementation N=648 Difference (95% CI); p-value ADR n (%) 226 …" Step: The limitations paragraph runs First to Tenth and then Finally: eleven. The eighth reports 795 procedures before and 1382 after (734 with AI, 648 without), 'primarily due to' the suspension of the screening programme on 1 January 2022, which let centres take more patients from the waiting list. The ranking is ours: S021 numbers its limitations and does not rank them; 'the one we think matters most' says so on the page. Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 16. ed48b451 — "adjusted" again, in the source list

**Page now:** Source of the three phases — before CADe, during CADe, after CADe removal — the thirteen endoscopists (seven inexperienced, six experienced) and 5,013 colonoscopies, the primary endpoint of detection of at least one polyp of 5 mm or more, the rise among inexperienced endoscopists from 31.9% (216/678) to 39.5% (257/651) at an odds ratio of 1.43 on 1.11–1.84, the 36.3% (173/476) after removal at an adjusted odds ratio of 1.03 on 0.79–1.34, the absence of any significant effect among the experienced, and the quoted conclusion.

**Evidence:** Same error as §1 (32db25e0). S043 abstract: "There was no significant change between phases 1 and 3 (31.9% [216/678] to 36.3% [173/476]; OR 1.03, 95%CI 0.79-1.34)." Its table gives "Inexperienced 173/476 (36.3) 1.03 (0.79-1.34) -": the univariable column, with "-" for multivariable.

**Proposed:** "Source of the three phases — before CADe, during CADe, after CADe removal — the thirteen endoscopists (seven inexperienced, six experienced) and 5,013 colonoscopies, the primary endpoint of detection of at least one polyp of 5 mm or more, the rise among inexperienced endoscopists from 31.9% (216/678) to 39.5% (257/651) at an odds ratio of 1.43 on 1.11–1.84, the 36.3% (173/476) after removal at an odds ratio of 1.03 on 0.79–1.34, the absence of any significant effect among the experienced, and the quoted conclusion."

**Binding for the corrected text:** deterministic. Span, S043 (Abstract, Methods/Results/Conclusions): "endoscopists from phase 1 to 2 (31.9% [216/678] to 39.5% [257/651]; odds ratio [OR] 1.43, 95%CI 1.11-1.84). There was no significant change between phases 1 …" also_rests_on S043: "13 endoscopists (7 inexperienced, 6 experienced) performed 5013 colonoscopies; median patient age was 59 …" also_rests_on S043: "The primary end point was change in the proportion of colonoscopies with detection of at least one polyp ≥5 …" also_rests_on S043: "3 (after CADe) All 457/1521 (30.0) 0.95 (0.82-1.11) - Inexperienced 173/476 (36.3) 1.03 (0.79-1.34) -" also_rests_on S043: "Conclusions PDR-5 of inexperienced endoscopists increased when CADe was used." Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 17. 73aed151 — "AI-generated" suggestions from a purported AI

**Page now:** Dratsch and colleagues showed 27 radiologists a set of mammograms alongside AI-generated BI-RADS category suggestions.

**Evidence:** S030 Materials and Methods: "27 radiologists read 50 mammograms and provided their Breast Imaging Reporting and Data System (BI-RADS) assessment assisted by a purported AI system." The suggestions were the researchers', set correct or incorrect by design; no AI generated them.

**Proposed:** "Dratsch and colleagues had 27 radiologists read a set of mammograms alongside BI-RADS category suggestions from a purported AI system."

**Binding for the corrected text:** context. Span, S030 (Abstract, Materials and Methods): "In this prospective experiment, 27 radiologists read 50 mammograms and provided their Breast Imaging Reporting and Data System (BI-RADS) assessment assisted by …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 18. 41c3df15 — "the figure most often quoted"

**Page now:** Gerlich's 2025 study is the source of the figure most often quoted, a correlation of −0.68 between AI use and critical thinking.

**Evidence:** No held document ranks how often figures are quoted. The figure itself is right: S008, "The correlation between AI tool use and critical thinking was found to be strongly negative (r = -0.68)".

**Proposed:** "Gerlich's 2025 study reports a correlation of −0.68 between AI tool use and critical thinking."

**Binding for the corrected text:** deterministic. Span, S008 (Results, correlations): "The correlation between AI tool use and critical thinking was found to be strongly negative (r = -0.68), suggesting that greater reliance on AI tools is …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 19. 1c761af8 — "gave up sooner"

**Page now:** Unassisted solve rates fell, at effect sizes of −0.42, −0.19 and −0.42, and people gave up sooner.

**Evidence:** S001 measures a skip rate (how often a test problem was skipped), not timing; its words are "give up more frequently" and "more likely to give up". The skip-rate difference was significant in Experiment 1 ("P = 0.031") and Experiment 3 ("P = 0.008") but not Experiment 2: "t(583) = 1.18, P = 0.239; Cohen's d = 0.10, 95% CI [-0.07, 0.26]), but the result was not significant." The three solve-rate effect sizes (−0.42, −0.19, −0.42) are right.

**Proposed:** "Unassisted solve rates fell, at effect sizes of −0.42, −0.19 and −0.42, and people gave up more often — significantly in the first and third experiments, not in the second."

**Binding for the corrected text:** deterministic. Span, S001 (Experiments 1-3, Results): "had a lower solve rate (mean 0.57, s.d. 0.41) than participants in the control condition (mean 0.73, s.d. 0.34; t(305) = -3.64, P < 0.001; Cohen's d = -0.42, …" also_rests_on S001: "had a lower solve rate (mean 0.71, s.d. 0.36) than participants in the control condition (mean 0.77, s.d. …" also_rests_on S001: "had a lower solve rate (mean 0.76, s.d. 0.34) than participants in the control condition (mean 0.89, s.d. …" also_rests_on S001: "the AI condition had a higher skip rate (mean 0.20, s.d. 0.36) than participants in the control condition …" also_rests_on S001: "exhibited a higher skip rate (mean 0.10, s.d. 0.26) than participants in the control condition (mean 0.07, …" also_rests_on S001: "also had a higher skip rate (mean 0.08, s.d. 0.21) than participants in the control condition (mean 0.01, …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 20. 94b39b65 — 79.8% given to all three experiments

**Page now:** Separately, three pre-registered experiments with 1,372 participants across 9,593 trials randomised whether an AI assistant's answer was right or wrong: participants consulted it on more than half of trials and, having consulted it, followed it on 79.8% of the trials where it was wrong .

**Evidence:** The abstract covers the pool: "Across three preregistered experiments … (N = 1,372; 9,593 trials) … Participants chose to consult an AI assistant on a majority of trials (>50%)." The 79.8% is printed only in Study 1's results: "Conditional on using System 3, participants followed AI's advice on 92.7% of AI-Accurate trials … and 79.8% of AI-Faulty trials". No pooled faulty-trial follow rate was found.

**Proposed:** "Separately, three pre-registered experiments with 1,372 participants across 9,593 trials randomised whether an AI assistant's answer was right or wrong: participants consulted it on more than half of trials and, in the first experiment, having consulted it, followed it on 79.8% of the trials where it was wrong."

**Binding for the corrected text:** deterministic. Span, S017 (Abstract; Study 1, Chat Use & AI Adoption): "Across three preregistered experiments using an adapted Cognitive Reflection Test (N = 1,372; 9,593 trials), we randomized AI accuracy via hidden seed prompts. …" also_rests_on S017: "Conditional on using System 3, participants followed AI's advice on 92.7% of AI-Accurate trials (SE = 1.2%, …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 21. 8762158c — "did not decline", and Study 1 figures given to the three

**Page now:** Wharton School Research Paper, February 2026 Source of the three pre-registered experiments, 1,372 participants and 9,593 trials, the 79.8% of chat-engaged trials on which participants followed faulty advice, and the confidence rise of 11.7 percentage points that did not decline as faulty trials accumulated.

**Evidence:** S017 Study 1: "Within the AI-Assisted condition, confidence did not significantly decline as the number of faulty trials increased (β = -1.14, SE = 0.89, t = -1.28, 95% CI [-2.88, 0.61], p = 0.202)." The 79.8% and the 11.7-point rise are Study 1's (as 94b39b65). The B19 significance check catches the first error on the uncorrected text.

**Proposed:** "Wharton School Research Paper, February 2026 Source of the three pre-registered experiments, 1,372 participants and 9,593 trials, and, from the first experiment, the 79.8% of chat-engaged trials on which participants followed faulty advice and the confidence rise of 11.7 percentage points that did not significantly decline as faulty trials accumulated."

**Binding for the corrected text:** deterministic. Span, S017 (Abstract; Study 1): "Across three preregistered experiments using an adapted Cognitive Reflection Test (N = 1,372; 9,593 trials), we randomized AI accuracy via hidden seed prompts. …" also_rests_on S017: "Conditional on using System 3, participants followed AI's advice on 92.7% of AI-Accurate trials (SE = 1.2%, …" also_rests_on S017: "Despite approximately half of System 3 answers being faulty, access to AI increased confidence by 11.7 …" also_rests_on S017: "Within the AI-Assisted condition, confidence did not significantly decline as the number of faulty trials …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 22. e0713036 — a quotation with an article the source does not have

**Page now:** Healthgrades , 19 August 2025 Calls it “a retrospective observational study” and carries an outside expert’s judgement that “the study design, population limits, operator factors, and short-term focus restrict broad applicability, and the deskilling concern remains hypothetical rather than proven”.

**Evidence:** Healthgrades (S042): "This retrospective observational study was conducted across four Polish endoscopy centers …". The page's quotation marks enclose "a retrospective observational study". The second quotation is verbatim; the outside expert is Prateek Sharma, chair of ASGE's AI Institute for Gastroenterology, not an author of the study.

**Proposed:** "Healthgrades , 19 August 2025 Calls it a “retrospective observational study” and carries an outside expert’s judgement that “the study design, population limits, operator factors, and short-term focus restrict broad applicability, and the deskilling concern remains hypothetical rather than proven”."

**Binding for the corrected text:** deterministic. Span, S042 (Healthgrades article body): "However, the study design, population limits, operator factors, and short-term focus restrict broad applicability, and the deskilling concern remains …" also_rests_on S042: "This retrospective observational study was conducted across four Polish endoscopy centers participating in …" also_rests_on S042: "Updated on August 19, 2025" also_rests_on S042: "Commenting on the study, Prateek Sharma , MD, MASGE, the chair of the American Society for Gastrointestinal …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 23. f8238a88 — "exploratory" dropped; "recruited"

**Page now:** Hesselmann's 2020 replication analysed 89 participants of 117 recruited and did not find the effect: the data were about five times more likely under the null than under the alternative, and about sixteen times more likely when tested against the original's specific predicted pattern.

**Evidence:** S009: "When the specific data pattern reported in the original study was considered as alternative model in an exploratory analysis, our data were 16 times more likely under the null model (BF 0+ = 16.43)." The page presents it beside the preregistered BF01 of 5.07 as a second result of the same standing. And "A total of 117 participants were tested.", not recruited.

**Proposed:** "Hesselmann's 2020 replication analysed 89 participants of 117 tested and did not find the effect: the data were about five times more likely under the null than under the alternative, and, in an exploratory analysis, about sixteen times more likely when tested against the original's specific predicted pattern."

**Binding for the corrected text:** deterministic. Span, S009 (Methods, Sample; Results): "Accordingly, the sequential Bayes Factor (BF) analysis yielded a final BF 01 of 5.07 in favor of the null over the alternative hypothesis, after the data from …" also_rests_on S009: "A total of 117 participants were tested." also_rests_on S009: "When the specific data pattern reported in the original study was considered as alternative model in an …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 24. 7a05297b — "accepted at the Journal of …": published, and not that name

**Page now:** Extended and peer reviewed as Rosbach E, Ammeling J, Ganz J, Bertram CA, Conrad T, Riener A, Aubreville M, “Stuck on Suggestions”, accepted at the Journal of Machine Learning for Biomedical Imaging , 2026 (arXiv:2603.11821) Source of the 28 trained pathology experts, the 7% automation-bias rate — initially correct evaluations overturned by erroneous AI advice — and the finding that time pressure did not raise the frequency of automation bias but appeared to increase its severity, through heavier reliance on the system’s negative consultations and a subsequent fall in performance.

**Evidence:** The held MELBA article (arXiv 2603.11821v3) header: "Machine Learning for Biomedical Imaging … Volume 2026, Received: 2025-07-15, Published 2026-03-13". It was published five months before the page was drafted, in a journal whose name has no "Journal of". The findings are unchanged.

**Proposed:** "Extended and peer reviewed as Rosbach E, Ammeling J, Ganz J, Bertram CA, Conrad T, Riener A, Aubreville M, “Stuck on Suggestions”, Machine Learning for Biomedical Imaging, published 13 March 2026 (arXiv:2603.11821) Source of the 28 trained pathology experts, the 7% automation-bias rate — initially correct evaluations overturned by erroneous AI advice — and the finding that time pressure did not raise the frequency of automation bias but appeared to increase its severity, through heavier reliance on the system’s negative consultations and a subsequent fall in performance."

**Binding for the corrected text:** deterministic. Span, S038 (MELBA article header and abstract; arXiv v1 abstract): "However, it also introduced a 7% automation bias rate, quantified as the number of accepted negative consultations, where a previously correct independent …" also_rests_on S038: "Machine Learning for Biomedical Imaging Stuck on Suggestions: Automation Bias, the Anchoring Effect, and the …" also_rests_on S038: "Volume 2026, Received: 2025-07-15, Published 2026-03-13" also_rests_on S038: "Through a web-based experiment involving 28 trained pathology experts, who estimated tumor cell percentages …" also_rests_on S038: "it also resulted in a 7% automation bias rate, where initially correct evaluations were overturned by …" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 25. 4173a438 — "one preprint"; "held in all three"

**Page now:** That is causal, and it held in all three experiments — which is internal replication by one team in one preprint, not confirmation by anybody else.

**Evidence:** S001, the version the page says it checked (arXiv 2604.04721v4), carries "Published as a conference paper at COLM 2026" on every page. "It held in all three experiments" is true of the solve rates (d = −0.42, −0.19, −0.42, each significant) and not of giving up (Experiment 2: "the result was not significant").

**Proposed:** "That is causal, and the fall in solve rates held in all three experiments — which is internal replication by one team in one paper, not confirmation by anybody else."

**Binding for the corrected text:** S001: the header line "Published as a conference paper at COLM 2026"; the three solve-rate sentences (Cohen's d = -0.42, -0.19, -0.42), as for 1c761af8. No bindings.json row: the tooling does not classify the sentence as empirical (no figure, no named source), so it has none to bind.

## 26. e14ccbb0 — "a preprint"; "about fifteen minutes long"

**Page now:** It is also about fifteen minutes long, and it is a preprint with no pre-registration statement.

**Evidence:** S001: "Published as a conference paper at COLM 2026". The fifteen minutes is Experiment 2's: "our study took approximately 15 minutes to complete" (Experiment 3: "approximately 13 minutes"). No pre-registration statement occurs in the held text, which agrees with the page.

**Proposed:** "Its second experiment took about fifteen minutes, and the paper, published at COLM 2026, carries no pre-registration statement."

**Binding for the corrected text:** S001: "(our study took approximately 15 minutes to complete)" (Experiment 2, 3.1 Method); the header line "Published as a conference paper at COLM 2026". No bindings.json row, as 4173a438.

## 27. a4267014 — "without warning" holds for Experiment 1 only

**Page now:** Three randomised experiments — 1,222 people randomised, 1,060 analysed — had participants work through practice problems with or without AI, then removed the AI without warning and gave them three more.

**Evidence:** S001 Experiment 1: "the AI assistant was then removed without warning, and participants were asked to solve 3 additional fraction problems." Experiment 2: "The AI assistant was then removed, and participants were asked to solve 3 additional fraction problems." Experiment 3: "The AI assistant was then removed, and participants were asked to solve 3 additional reading comprehension problems." (Experiment 2's motivation speaks of "the AI sidebar being present and then suddenly removed" in Experiment 1, and its control arm saw an equivalent sidebar removed.) The page states it of all three.

**Proposed:** "Three randomised experiments — 1,222 people randomised, 1,060 analysed — had participants work through practice problems with or without AI, then removed the AI and gave them three more."

**Binding for the corrected text:** judgement. premise S001: "We conduct a series of randomized experiments across 1, 222 participants, spanning mathematical reasoning …" premise S001: "This led to the exclusion of 47 participants, leaving a final sample of 307 participants (N = 185 in the AI …" premise S001: "This led to the exclusion of 82 participants, leaving a final sample of 585 participants (N = 308 in the AI …" premise S001: "This led to the exclusion of 33 participants, leaving a final sample of 168 participants (N = 85 in the AI …" premise S001: "the AI assistant was then removed without warning, and participants were asked to solve 3 additional fraction …" premise S001: "The AI assistant was then removed, and participants were asked to solve 3 additional reading comprehension …" Step: S001 reports 1,222 participants across the three experiments and final analysed samples of 307, 585 and 168; 307 + 585 + 168 = 1,060 (our sum, declared in figure-exclusions). Each experiment removed the AI after the learning problems and set 3 test problems; only Experiment 1 says the removal was 'without warning'. Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean, with rule 1's comma-and-space INFO on 1, 222.

## 28. 09ba5473 — "withdrawn without warning" in the source list

**Page now:** arXiv 2604.04721 Source of the three randomised experiments, 1,222 randomised and 1,060 analysed, the effect sizes of −0.42, −0.19 and −0.42 on unassisted solve rates, and the design in which the AI is withdrawn without warning before three test problems.

**Evidence:** As a4267014: only Experiment 1 says "without warning".

**Proposed:** "arXiv 2604.04721 Source of the three randomised experiments, 1,222 randomised and 1,060 analysed, the effect sizes of −0.42, −0.19 and −0.42 on unassisted solve rates, and the design in which the AI is withdrawn before three test problems."

**Binding for the corrected text:** judgement. premise S001: "arXiv:2604.04721v4 [cs.AI] 5 Aug 2026" premise S001: "We conduct a series of randomized experiments across 1, 222 participants, spanning mathematical reasoning …" premise S001: "This led to the exclusion of 47 participants, leaving a final sample of 307 participants (N = 185 in the AI …" premise S001: "This led to the exclusion of 82 participants, leaving a final sample of 585 participants (N = 308 in the AI …" premise S001: "This led to the exclusion of 33 participants, leaving a final sample of 168 participants (N = 85 in the AI …" premise S001: "had a lower solve rate (mean 0.57, s.d. 0.41) than participants in the control condition (mean 0.73, s.d. …" premise S001: "had a lower solve rate (mean 0.71, s.d. 0.36) than participants in the control condition (mean 0.77, s.d. …" premise S001: "had a lower solve rate (mean 0.76, s.d. 0.34) than participants in the control condition (mean 0.89, s.d. …" premise S001: "the AI assistant was then removed without warning, and participants were asked to solve 3 additional fraction …" Step: As a4267014 for the counts and design (1,060 = 307 + 585 + 168, our sum); the three solve-rate effect sizes are Cohen's d = -0.42, -0.19 and -0.42 as printed in the three Results sections. Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean, with rule 1's comma-and-space INFO on 1, 222.

## 29. 59861255 — "2025 (arXiv:2411.00998)" stands

**Page now:** 2025 (arXiv:2411.00998).

**Evidence:** the held v1 is dated "arXiv:2411.00998v1 [cs.HC] 1 Nov 2024", but the paper was published in 2025: Crossref (free works API, 2026-10-18) holds doi 10.1007/978-3-658-47422-5_27, a book chapter in *Bildverarbeitung für die Medizin 2025* (Informatik aktuell), Springer Fachmedien Wiesbaden, pp. 129–134, issued 2025, same title, same five authors. Recorded on S038 in sources.json as a citation-only rendition (the chapter text is not held). No page change.

**Proposed binding (not written):** context, resting on S038's Crossref record for the year and venue. A source-store binding rather than a span, since the chapter is not held; to be confirmed by the operator.

## Bound

Batch 1 (2026-10-18): 849a833e, b61e583d, 9675c628, f2072847, a84075d9, 5850f3bd, 83bed04b,
d49da6c2. Batch 2 (2026-10-18): c8d0e2c5 (S046), 43a5da1b, 7a69a530, e2d620f3, 495cfe6a,
3da7203e, 57c41ddd, 03ea8e0e, f9eb567e, 48a03a9a, b2fff6c7, c2f8c733, 5bd6e3b7 (S046, page text
unchanged). Verdicts signed by Fred Ugast, checked against held text with Claude as advisor. Batch 3 (2026-10-18): 11147b19 (B6 disposition on "only"), f83a6cfe, ae6de87f, d250f28b, 875ef76c, 695c1c4e, 7332d1e1, b9b79e7b, fa3d6649, 0f7a7387, ff258fcb, 286c807d, 8367d5ea, ea7550a9, 8e62c8a7 and 36c83e6f (each also resting on S043's "from November 2021 to June 2025 … at three Norwegian outpatient clinics"), 086f4a02 (S046's PMC HTML rendition, which prints ±). Not bound, corrections above: a4267014, 09ba5473 and the batch-3 errors.
