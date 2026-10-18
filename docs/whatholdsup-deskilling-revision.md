# Deskilling — pending page corrections for the republish

Issue: `issues/WHU-003-deskilling/`; page: `site/whatholdsup/deskilling.html` (live at
whatholdsup.org/deskilling, unchanged since 30 August). Opened 2026-10-18 from binding
batch 1. Nothing here is on the page yet: each correction goes out through `publish.py`
with the republish, with a `corrections.md` entry. Proposed wording is the operator's
unless marked otherwise. Rows are binding-row shas in `bindings.json`.

## Errors found in the published page

105 errors in about 350 sentences read closely — 53 overstate a finding or a source's claim; 18 claim more about WHU's own process than the records show; 15 misattribute or misdescribe; 6 wrong date, count, figure or author; 5 understate a source's standing; 3 misquote; 3 rest on a document not held; 2 understate a finding. Of the 48 judgement sentences, 24 were wrong.

Adjusted from the operator's figure (78, of which 54 outside the rule) by steps 1–2 of the batch-4 write: three sentences the batch-4 readers had left as not held or unclear are corrections at the operator's instruction and are now counted (b44e344b, overstates; 645248a3, misquotes; 0f2e96af, rests on a document not held), and the outside-the-rule count is 53, not 54: 48 batch-4 step-2 sentences, those three, and 4173a438 and e14ccbb0 from batch 3. The five step-4 errors and b053b281 are bound rows, inside the rule. No verdict was reversed: 89466d77 and 13eeff53 stay errors (the article page has no causation disclaimer either); d06d9c3d, 7011fffe, 111ae20d, 483ce0da, d956dc78, 93c14a94 and 7419c16a stand.

The "misstates how a source was read" row of the earlier tally (the Wang paragraph) is counted with WHU's own process.

| | count | rows |
|---|---|---|
| overstates a finding or a source's claim | 53 | 32db25e0, 509b18f6, b8844660, bd8b242c, ad3f7c73; batch 3: ed48b451, 41c3df15, 1c761af8, 94b39b65, 8762158c, f8238a88, 94cd79d4, a4267014, 09ba5473; batch 4: 7032a248, 84eaf825, 50770789, 5ddcede1, dd75605f, 523c0e8e, 6350f29e, b34b3805, 3646a7a7, 97c5510d, 89466d77, 13eeff53, 3b702c14, dde90522, 991b00d0, 65dba6ca, b44e344b; judgements: acd4fe6c, fcd870cc, 8d9dda78, b7985c65, 3d054dd8, a0b796f2, dbe8c633, 94285a34, caab5487, e7229fa9, b25cbddc, 6183737f, 2c9f964b, 13a1f595, cb13b0ff, 1ed69ef1, 738c8380, 6b66734b, 4512a421, afd83f74, e99eaaf7, 849ac2af |
| claims more about WHU's own process than the records show | 18 | the Wang paragraph (c8d0e2c5, 5bd6e3b7, b8844660); batch 4: 514fe6d8, f3bac0ab, d0f6be94, e6b318db, 1007d4e3, 3277476a, a3804315, dfbdfe06, 6f8d3f6e, 9c6d0d80, 6349e704, 6da54bce, d77cec11, b3bad0a5, 66fbb27d, 63ba2dc1, e68fe056 |
| misattributes or misdescribes | 15 | 26e94905, 8598e9ca, 34b99db8; batch 3: 73aed151; batch 4: bfc28e7c, b4f1e3b4, 5a602740, 194ddb13, 91730a4c, cb170ac7, 3c3f210c, 042baf28, c4927d74, e7b33c5f; judgements: 4fd2fa15 |
| wrong date, count, figure or author | 6 | batch 4: 20099139, 5f408161, d09a03dc, f7dd45eb, 930417d1, b053b281 |
| misquotes | 3 | Q-25; batch 3: e0713036; batch 4: 645248a3 |
| understates a source's standing | 5 | batch 3: 7a05297b, 4173a438, e14ccbb0; batch 4: 38d82aac, 564c3790 |
| understates a finding | 2 | batch 4: dba5f62d, 14e6751b |
| rests on a document not held | 3 | batch 4: 0eba3348, 0f2e96af; judgements: dbaaa31b |

Of the 10 batch-3 errors in the proposals, the automatic checks caught 1 on the uncorrected text; of the 5 batch-4 step-4 errors, 2. Close reading against the source found the rest.

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

## Batch 4 (2026-10-18): sentences outside the empirical rule, and step-4 rows

Read by five read-only agents against the held texts and our own records, with the main findings re-checked by Claude; written at the operator's instruction. Sentences in group (ii) or (iv) have no bindings.json row, because the empirical rule does not reach them; their 'binding for the corrected text' lists the held spans, each confirmed by script to occur verbatim in the named source.

## 30. bfc28e7c — misdescribed design (overstated absence of randomisation)

**Page now:** Nobody was randomised.

**Evidence:** S021 Methods: "after which colonoscopies were randomly done either with or without AI assistance according to the date of colonoscopy".

**Proposed:** "The before-and-after comparison was not randomised, although after installation the days on which AI was switched on were allocated at random by date."

**Binding for the corrected text:** S021: "after which colonoscopies were randomly done either with or without AI assistance according to the date of colonoscopy".

## 31. 50770789 — dropped hedge

**Page now:** Time pressure did not make that happen more often; it made it worse, with heavier reliance on the system's negative calls and a measurable fall in performance.

**Evidence:** S038__9a6d53b2f3f0.txt: "Conversely, time pressure did not exacerbate automation bias occurrence, but appeared to increase its severity, evidenced by heightened reliance on the system's negative consultations and subsequent performance decline." S038__562405fcc1c5.txt: "While time pressure did not increase the frequency of automation bias occurrence, it appeared to intensify its severity"

**Proposed:** "Time pressure did not make that happen more often, but it appeared to make it worse, with heavier reliance on the system's negative calls and a fall in performance."

**Binding for the corrected text:** S038: "Conversely, time pressure did not exacerbate automation bias occurrence, but appeared to increase its severity, evidenced by heightened reliance on the system's negative consultations and subsequent p"; S038: "While time pressure did not increase the frequency of automation bias occurrence, it appeared to intensify its severity".

## 32. 7032a248 — overstatement (dropped qualification)

**Page now:** And when the AI's errors exceeded an acceptability threshold, they overrode it.

**Evidence:** S047__e8869cc8faa5.txt: "When the AI method introduced errors that exceeded the level of 'acceptability' (above 2 on the global score ...), initially the errors by residents grew with a similar trend (slope ≃ 1). However, when the neural network performed more serious errors (above 3 points), the slope of errors introduced by residents considerably diminished"

**Proposed:** "And when the AI's errors were serious, beyond about three points on the global score, their own errors largely stopped following it; just past the acceptability threshold of two points, they still tracked it."

**Binding for the corrected text:** S047, as quoted in the evidence above.

## 33. 3b702c14 — unsupported quantifier

**Page now:** The Polish endoscopists were still working with the AI most days and being measured on the days they were not.

**Evidence:** S021__4296ea811a43.txt: "after which colonoscopies were randomly done either with or without AI assistance according to the date of colonoscopy" ; "795 before vs. 1382 after AI implementation including 734 with AI-assistance and 648 without AI-assistance"

**Proposed:** "The Polish endoscopists were still working with the AI on the days allocated to it, about half their lists, and being measured on the days they were not."

**Binding for the corrected text:** S021: "after which colonoscopies were randomly done either with or without AI assistance according to the date of colonoscopy"; S021: "795 before vs. 1382 after AI implementation including 734 with AI-assistance and 648 without AI-assistance".

## 34. 3c3f210c — misdescribed design (phase misattributed)

**Page now:** The Norwegian endoscopists had it taken away entirely — all but two of the thirteen, who reported running it throughout.

**Evidence:** S043__3af130dc2d4d.txt: "In the current study, two endoscopists reported having CADe active throughout the entire examination (including intubation of the colon), while the remaining endoscopists activated CADe on withdrawal from the cecum." Design: "three successive phases: 1) before CADe exposure, 2) during CADe use, and 3) after CADe removal" ... "Each endoscopist completed the three consecutive phases in a fixed order"; "we analyzed 5013 colonoscopies performed by 7 inexperienced and 6 experienced endoscopists" who "participated in all three phases"

**Proposed:** "The Norwegian endoscopists had it taken away entirely: all thirteen did a third phase after CADe was removed."

**Binding for the corrected text:** S043: "In the current study, two endoscopists reported having CADe active throughout the entire examination (including intubation of the colon), while the remaining endoscopists activated CADe on withdrawal "; S043: "three successive phases: 1) before CADe exposure, 2) during CADe use, and 3) after CADe removal"; S043: "Each endoscopist completed the three consecutive phases in a fixed order"; S043: "we analyzed 5013 colonoscopies performed by 7 inexperienced and 6 experienced endoscopists".

## 35. 5ddcede1 — misattributed inference / dropped qualifier

**Page now:** It shows no significant effect in any phase — but that includes no benefit while the AI was running, and the authors suggest why: experienced endoscopists may also be less enthusiastic about a software tool intended to improve their performance , and two endoscopists ran it throughout while the rest switched it on only during withdrawal.

**Evidence:** S043__3af130dc2d4d.txt: "The experienced endoscopists may also be less enthusiastic about a software tool intended to improve their performance, leading to an aversion to using it effectively." ... "GI Genius has to be actively turned on by the endoscopist. In the current study, two endoscopists reported having CADe active throughout the entire examination (including intubation of the colon), while the remaining endoscopists activated CADe on withdrawal from the cecum."

**Proposed:** "It shows no significant effect in any phase — but that includes no benefit while the AI was running, and the authors suggest why: experienced endoscopists may also be less enthusiastic about a software tool intended to improve their performance . They also report that two endoscopists had CADe active throughout the entire examination, including intubation, while the rest switched it on only on withdrawal."

**Binding for the corrected text:** S043: "The experienced endoscopists may also be less enthusiastic about a software tool intended to improve their performance, leading to an aversion to using it effectively."; S043: "GI Genius has to be actively turned on by the endoscopist. In the current study, two endoscopists reported having CADe active throughout the entire examination (including intubation of the colon), whi".

## 36. 20099139 — wrong date

**Page now:** The mechanism was measured in 2022, by people who then said what worried them about it.

**Evidence:** S031__4564350bb359.txt: "submitted 19.9.2021 accepted after revision 10.2.2022 published online 14.2.2022"; S031__2402cde39b20.txt: "The study was approved by the local ethical committee (No. 2021033001)."

**Proposed:** "The mechanism was measured in a study published in 2022, by people who then said what worried them about it."

**Binding for the corrected text:** S031: "submitted 19.9.2021 accepted after revision 10.2.2022 published online 14.2.2022"; S031: "The study was approved by the local ethical committee (No. 2021033001).".

## 37. 514fe6d8 — overstatement (self-description)

**Page now:** This page uses their hedges, not firmer ones.

**Evidence:** S031 held text: 'Possible consequences of these findings might be prolonged examination time and deskilling'; 'a potential risk of overreliance and deskilling'. Troya's held text never calls the gaze change a mechanism (no 'mechanism' in S031). The page's own section headline says 'The mechanism was measured in 2022' and 'something has to have changed in how they look'; the sources that link it to the Polish result hedge: S032 (Zhou) 'could potentially be a mechanism', S043 (Pedersen) 'could explain'.

**Proposed:** "On consequences this page uses their hedges, not firmer ones; that the narrowing they measured is the mechanism behind the Polish result is Zhou's and Pedersen and colleagues' proposal, not a finding."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 38. dba5f62d — understatement (omits authors' own caveat)

**Page now:** The same narrowing has been measured in breast imaging, and read there as a gain.

**Evidence:** S028__934e511be728.txt: "The observed reduction in breast coverage with AI support, compared with no AI support, may suggest a more efficient search ... However, reduced coverage could also increase the risk of missing cancers not detected by AI, which underscores the need for AI to be highly accurate and for radiologists to feel accountable for their decisions."

**Proposed:** "The same narrowing has been measured in breast imaging, and read there mainly as a gain, though its authors note it could also raise the risk of missing cancers the AI does not detect."

**Binding for the corrected text:** S028: "The observed reduction in breast coverage with AI support, compared with no AI support, may suggest a more efficient search"; S028: "However, reduced coverage could also increase the risk of missing cancers not detected by AI, which underscores the need for AI to be highly accurate and for radiologists to feel accountable for their".

## 39. 042baf28 — misattribution / understatement

**Page now:** One team measures the narrowing with the tool present and calls it efficiency; another measures the outcome with the tool absent and worries about what was not looked at.

**Evidence:** S028__934e511be728.txt: "However, reduced coverage could also increase the risk of missing cancers not detected by AI"; S031__2402cde39b20.txt: "Videos examined with AI support significantly reduced eye travel distance." ... "This might be efficient but risks missing a polyp that is not captured by the system."

**Proposed:** "One team measures the narrowing with the tool present and calls it a more efficient search, while noting it could let cancers the AI misses go unseen; another measures the outcome with the tool absent and worries about what was not looked at."

**Binding for the corrected text:** S028: "However, reduced coverage could also increase the risk of missing cancers not detected by AI"; S031: "Videos examined with AI support significantly reduced eye travel distance."; S031: "This might be efficient but risks missing a polyp that is not captured by the system.".

## 40. 5f408161 — wrong figure

**Page now:** The same radiologists, the same task, and a forty-point swing.

**Evidence:** S030__69d3852d76cd.txt: "inexperienced (mean, 79.7% ± 11.7 [SD] vs 19.8% ± 14.0; P < .001; r = 0.93), moderately experienced (mean, 81.3% ± 10.1 vs 24.8% ± 11.6; P < .001; r = 0.96), and very experienced (mean, 82.3% ± 4.2 vs 45.5% ± 9.1; P = .003; r = 0.97)"

**Proposed:** "The same radiologists, the same task, and a swing of between 37 and 60 points."

**Binding for the corrected text:** S030: "inexperienced (mean, 79.7% ± 11.7 [SD] vs 19.8% ± 14.0; P < .001; r = 0.93), moderately experienced (mean, 81.3% ± 10.1 vs 24.8% ± 11.6; P < .001; r = 0.96), and very experienced (mean, 82.3% ± 4.2 vs".

## 41. dd75605f — cause misdescribed / hedge dropped

**Page now:** Never-skilling is a trainee who never develops the skill, because the tool was there from the beginning.

**Evidence:** S025__5e52060b995d.txt: "never-skilling refers to the failure to develop foundational competencies during formative training when AI substitutes majority of the cognitive effort required to build independent clinical reasoning." | S025__5e52060b995d.txt: "The risk of never-skilling is not a risk of AI per se, but a risk of using AI in answer-delivery mode during periods when cognitive architecture is still being constructed." | S025__5e52060b995d.txt: "AI, however, is available from the first day of medical school, before any clinical reasoning architecture has formed."

**Proposed:** "Never-skilling is a trainee who fails to develop the skill in the first place, because the AI did the thinking while the skill was being formed."

**Binding for the corrected text:** S025: "never-skilling refers to the failure to develop foundational competencies during formative training when AI substitutes majority of the cognitive effort required to build independent clinical reasonin"; S025: "The risk of never-skilling is not a risk of AI per se, but a risk of using AI in answer-delivery mode during periods when cognitive architecture is still being constructed."; S025: "AI, however, is available from the first day of medical school, before any clinical reasoning architecture has formed.".

## 42. f7dd45eb — wrong count

**Page now:** Fifty-four participants completed its first three sessions; the fourth session, which carries the claim about lasting effects, had eighteen , split across two crossover arms.

**Evidence:** S007__9b84e8dff3e5.txt: "60 adults were recruited to participate in our study, but due to scheduling difficulties, 55 completed the experiment in full (attending a minimum of three sessions, defined later). To ensure data distribution, we are here only reporting data from 54 participants" | S007__9b84e8dff3e5.txt: "We recruited a total of 54 participants for Sessions 1, 2, 3, and 18 participants among them completed session 4." | S007__9b84e8dff3e5.txt: "Session 4 was not a mandatory session, and thus, due to participants' availability and scheduling constraints, only 18 participants were able to attend."

**Proposed:** "Fifty-four participants are reported for its first three sessions (fifty-five completed them); the fourth session, which carries the claim about lasting effects, had eighteen, split across two crossover arms."

**Binding for the corrected text:** S007: "60 adults were recruited to participate in our study, but due to scheduling difficulties, 55 completed the experiment in full (attending a minimum of three sessions, defined later). To ensure data dis"; S007: "We recruited a total of 54 participants for Sessions 1, 2, 3, and 18 participants among them completed session 4."; S007: "Session 4 was not a mandatory session, and thus, due to participants' availability and scheduling constraints, only 18 participants were able to attend.".

## 43. 89466d77 — unsupported claim about the source (causation disclaimer not in source)

**Page now:** It is cross-sectional, and the author does not claim causation.

**Evidence:** S008__e90160a909e9.txt: "These findings suggest that cognitive offloading plays a substantial role in explaining the negative impact of AI usage on critical thinking." | S008__e90160a909e9.txt: "The total effect of AI tool usage on critical thinking was significant (b = -0.42, SE = 0.08, p < 0.001)." | S008__e90160a909e9.txt: "Experimental studies that manipulate the level of AI tool usage and measure resultant changes in critical thinking performance could offer causal evidence of the relationship between these variables."

**Proposed:** "It is cross-sectional, so it cannot show causation — though the paper writes of "the negative impact of AI usage on critical thinking", and itself calls for experiments that "could offer causal evidence"."

**Binding for the corrected text:** S008: "These findings suggest that cognitive offloading plays a substantial role in explaining the negative impact of AI usage on critical thinking."; S008: "The total effect of AI tool usage on critical thinking was significant (b = -0.42, SE = 0.08, p < 0.001)."; S008: "Experimental studies that manipulate the level of AI tool usage and measure resultant changes in critical thinking performance could offer causal evidence of the relationship between these variables.".

## 44. f3bac0ab — misdescribes the process

**Page now:** We expected to find that this evidence had reached the public without its qualifications, and the first thing we looked for was whether that was true.

**Evidence:** premise.json KILL_CONDITION_4_TESTED.the_lesson: 'We proposed a pattern, chose five instances that fit it, and told the operator it was demonstrable. One deliberate search for the disconfirming case found it in the first result.'; the_condition: 'That our five-carrier demonstration was a sample we selected'.

**Proposed:** "We expected to find that this evidence had reached the public without its qualifications, and we first gathered coverage that fitted that expectation; a later, deliberate search for the contrary case tested whether it was true."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 45. 523c0e8e — dropped hedge

**Page now:** A critical appraisal for the American College of Gastroenterology laid out the design problems for gastroenterologists and proposed the gaze mechanism.

**Evidence:** S032: "the authors do cite an interesting study looking at the impact of a CADe system on visual gaze pattern ... the potential impact on visual gaze could potentially be a mechanism by which prolonged CADe exposure could potentially impact performance over time."

**Proposed:** "A critical appraisal for the American College of Gastroenterology laid out the design problems for gastroenterologists and suggested, heavily hedged, that changes in visual gaze could be a mechanism."

**Binding for the corrected text:** S032: "the authors do cite an interesting study looking at the impact of a CADe system on visual gaze pattern"; S032: "the potential impact on visual gaze could potentially be a mechanism by which prolonged CADe exposure could potentially impact performance over time.".

## 46. 6350f29e — overstatement / misdescription

**Page now:** Time carried both on 13 August 2025, quoting Professor Osmani on the rise in procedure volume and the fatigue it could cause, and Professor Tucker on automation bias not being peculiar to AI, and calling the study observational throughout.

**Evidence:** S040: the word 'observational' occurs once: "Researchers across various European institutions conducted an observational study surveying four endoscopy centers in Poland"; headline "Using AI Made Doctors Worse at Spotting Cancer Without Assistance"; "a new study has found that doctors who regularly used AI actually became less skilled within months." Osmani is paraphrased, not quoted: "Venet Osmani ... noted to SMC that the total number of colonoscopies-including both AI-assisted and non-AI-assisted ones-increased over the course of the study. The increased workload, Osmani suggested, could have led to clinician fatigue". Tucker is quoted: "is not unique to AI systems and is a risk with the introduction of any new technology."

**Proposed:** "Time carried both on 13 August 2025, reporting Professor Osmani's point about the rise in procedure volume and the fatigue it could cause, quoting Professor Tucker on automation bias not being peculiar to AI, and calling it an observational study, though its headline said using AI made doctors worse."

**Binding for the corrected text:** S040: "Researchers across various European institutions conducted an observational study surveying four endoscopy centers in Poland"; S040: "Using AI Made Doctors Worse at Spotting Cancer Without Assistance"; S040: "a new study has found that doctors who regularly used AI actually became less skilled within months."; S040: "noted to SMC that the total number of colonoscopies-including both AI-assisted and non-AI-assisted ones-increased over the course of the study. The increased workload, Osmani suggested, could have led".

## 47. 3646a7a7 — unsupported 'none' / scope

**Page now:** What did not travel is why it rose: not one piece of coverage we read named the suspension of the Polish screening programme as the reason, or the absence of withdrawal-time data, or the eleven limitations as a body.

**Evidence:** S032 (ACG appraisal): "Importantly, withdrawal time was not reported in this study, which could potentially significantly impact ADR." S036 register: "WE CANNOT SAY WHETHER STAT CARRIED THE CAVEATS. The free portion does not, and the article continues behind a paywall."

**Proposed:** "What did not travel is why it rose: none of the news coverage we read named the suspension of the Polish screening programme as the reason, the absence of withdrawal-time data or the eleven limitations as a body, and STAT's article continues behind a paywall we could not read; only the American College of Gastroenterology's appraisal noted the missing withdrawal times."

**Binding for the corrected text:** S023, S033, S034, S036, S037, S040, S041, S042, as quoted in the evidence above.

## 48. b4f1e3b4 — misattribution / internal contradiction

**Page now:** The authors' call for randomised crossover trials did travel, but only inside the specialty: Professor Tucker made it at the Science Media Centre on the day of publication, and the American College of Gastroenterology's appraisal asked for prospective before-and-after trials.

**Evidence:** S035__fc4cec431558.txt: "Prof Allan Tucker, Professor of Artificial Intelligence in the Department of Computer Science, Brunel University of London: ... the authors make it clear that randomised crossover trials are needed to make more robust claims." ; S032__153788ef3f41.txt: "Prospective trials comparing colonoscopy quality before vs after AI exposure are needed to validate these findings." ; S021__4296ea811a43.txt: "robust prospective studies such as randomized crossover trials"

**Proposed:** "The authors' call for randomised crossover trials did travel, but not far: Professor Allan Tucker, a computer scientist at Brunel, relayed it at the Science Media Centre on the day of publication, and the American College of Gastroenterology's appraisal asked for prospective trials comparing colonoscopy quality before and after AI exposure."

**Binding for the corrected text:** S035: "Prof Allan Tucker, Professor of Artificial Intelligence in the Department of Computer Science, Brunel University of London:"; S035: "the authors make it clear that randomised crossover trials are needed to make more robust claims."; S032: "Prospective trials comparing colonoscopy quality before vs after AI exposure are needed to validate these findings."; S021: "robust prospective studies such as randomized crossover trials".

## 49. e7b33c5f — misdescribes location

**Page now:** The sentence under it was not.

**Evidence:** S023: the text directly under the headline is "New research indicates endoscopists introduced to AI tools performed procedures less effectively when those tools were no longer available." The 28.4%/22.4% sentence is several paragraphs further down: "A study published in the Lancet Gastroenterology & Hepatology journal this month found that in 1,443 patients ..."

**Proposed:** "A sentence further down was not."

**Binding for the corrected text:** S023: "New research indicates endoscopists introduced to AI tools performed procedures less effectively when those tools were no longer available.".

## 50. d0f6be94 — misattributes how the error was caught

**Page now:** We caught it by opening the article again rather than trusting our note of it.

**Evidence:** draft/2026-08-30-gate-adjudication.md section 1: 'Found by the ADVOCATE role, confirmed by opening the article.'; git 20efafd: 'The confirming run's advocate pass found the one thing six runs, four passes and an outside reviewer had walked past'. (counterexample/2026-08-30-adjudication.md line 153 says 'Opening the article again is what produced the Fortune correction', which supports the page's version.)

**Proposed:** "A fact-check run flagged it, and we confirmed it by opening the article again rather than trusting our note of it."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 51. 97c5510d — overstatement (repeats error recorded in revision doc §4)

**Page now:** A radiologist writing for trainees paired the colonoscopy result with the mammography experiment — the closest thing to this page in general-audience writing — and reported the limitations of neither.

**Evidence:** S034: "Budzyń and colleagues published a multicentre observational study in Lancet Gastroenterology & Hepatology showing that endoscopists ..."; audience: "Trainees (should) adapt", "The resident inherits the responsibility" - a radiology audience, not general readers.

**Proposed:** "A radiologist writing for trainees paired the colonoscopy result with the mammography experiment — the closest thing to this page that we found — and, beyond calling the colonoscopy study observational, reported none of the limitations of either."

**Binding for the corrected text:** S034: "The resident inherits the responsibility".

## 52. 5a602740 — misattributed wording (the review's body does not say retrospective)

**Page now:** It is a retrospective observational study; the review's body says so.

**Evidence:** S029__caec391d5633.txt: "A multicenter observational study conducted in Poland and published in The Lancet Gastroenterology & Hepatology in 2025" ; abstract: "In a multicenter randomized trial in colonoscopy"

**Proposed:** "It is a retrospective observational study; the review's own body calls it observational."

**Binding for the corrected text:** S029: "In a multicenter randomized trial in colonoscopy".

## 53. e6b318db — overstatement

**Page now:** We read the review's full text at source on 29 August 2026, and noticed only because we had read both underlying papers that evening.

**Evidence:** sources.json at publication (git 7c95f92) S028.access: on 2026-08-29, sections 'design, participants, both AUC figures, both eye-tracking figures, the conclusion', not_read 'the full paper'; S030.access: on 2026-08-29, 'the RSNA publisher page: ...', not_read 'the full paper'. S029.access.note: 'read end to end by claude on 2026-08-29' (a PDF supplied by fred after esmorwd.org 403'd).

**Proposed:** "We read the review's full text at source on 29 August 2026, and noticed only because we had read the main results of both underlying papers that evening."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 54. 194ddb13 — misattribution ("independently")

**Page now:** The colonoscopy authors asked for it, and Professor Tucker asked for it independently on the day of publication.

**Evidence:** S035__fc4cec431558.txt: "It is also worth noting that some major changes to the endoscopy department were undertaken in the middle of the study, and the authors make it clear that randomised crossover trials are needed to make more robust claims."

**Proposed:** "The colonoscopy authors asked for it, and Professor Tucker repeated their call at the Science Media Centre on the day of publication."

**Binding for the corrected text:** S035: "It is also worth noting that some major changes to the endoscopy department were undertaken in the middle of the study, and the authors make it clear that randomised crossover trials are needed to mak".

## 55. 38d82aac — misdescribed status / wrong count

**Page now:** Three of the studies this page relies on are preprints or working papers, and we have said so each time.

**Evidence:** S001__72e1d3c7e1e9.txt: "Published as a conference paper at COLM 2026" | S007__9b84e8dff3e5.txt: "Preprint, under review" | S017__9db353a1dcf7.txt: "v20260111" (no venue) | S019__d811e9038b17.txt: "arXiv:2601.00856 (cs) [Submitted on 29 Dec 2025]"

**Proposed:** "Two of the studies this page relies on are a preprint and a working paper, as is the comment on one of them, and we have said so each time; a third, by Liu and colleagues, has been published as a COLM 2026 conference paper."

**Binding for the corrected text:** S001: "Published as a conference paper at COLM 2026".

## 56. 14e6751b — understatement

**Page now:** One meta-analysis in this literature has already been retracted after nine and a half months of public criticism, and a scoping review in it mis-cites a paper.

**Evidence:** S005__4a3a8265fbfd.txt: "Preprint Version 1: 2 July 2025" and "Wang & Fan (2025) was retracted by the Editor on 22 April 2026, citing discrepancies in the meta-analysis" | S029__caec391d5633.txt: "In a multicenter randomized trial in colonoscopy, the adenoma detection rate (ADR) dropped significantly from 28.4% to 22.4%"

**Proposed:** "One meta-analysis in this literature has already been retracted after nine and a half months of public criticism, and the scoping review that gathers this literature for doctors misdescribes the colonoscopy study and misattributes figures in its key-studies table."

**Binding for the corrected text:** S005: "Preprint Version 1: 2 July 2025"; S005: "Wang & Fan (2025) was retracted by the Editor on 22 April 2026, citing discrepancies in the meta-analysis"; S029: "In a multicenter randomized trial in colonoscopy, the adenoma detection rate (ADR) dropped significantly from 28.4% to 22.4%".

## 57. 1007d4e3 — overstatement

**Page now:** We check the sources on this page against their journals' notices, and record when we last did.

**Evidence:** errata.json: a single pass, checked_on 2026-09-03; most sources 'UNCHECKABLE' ('no DOI, PMID, PMCID or PII can be parsed'), including S001, S007, S008, S009, S025, S038; S019, S026 and S032 'UNCHECKED' (lookup failed, 'HTTP 404 from Crossref'); S046, S047 and S048 not in errata.json at all. The lookup is of Europe PMC/Crossref bibliographic records, not journals' notices. watch.json checks[0] (30 Aug): not_checked 'W4 — NO retraction sweep run'. sweeps.json status runs cover about 13 sources.

**Proposed:** "We check the sources on this page that carry a DOI or PubMed identifier for corrections and retractions in Europe PMC and Crossref, and record when we last did; most of the others cannot be looked up this way, and the lookup failed for three."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 58. 3277476a — promise beyond the modest promise

**Page now:** If a general-audience account carries this evidence with its limitations attached, we will say so and link to it.

**Evidence:** review/2026-09-12-modest-promise-ruling.md: 'the page promises nothing' and 'What Holds Up makes only the modest promise ... and no other'; watch.json the_promise: 'no promise to the reader'. watch.json W7 records the intent ('we say so'); W7 was last checked on 2026-08-30 (watch.json checks[0]).

**Proposed:** "Whether a general-audience account carries this evidence with its limitations attached is one of the questions we watch; we last looked on 30 August 2026."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 59. a3804315 — overstatement

**Page now:** The full watch list, with the searches that would answer each question, is kept in the repository that produces this page, alongside a record of every check — including the ones that found nothing.

**Evidence:** git c4bc473: 'So of four paid runs today, ONE produced an artifact ... $23.78 of the $34.67 spent today produced no machine-readable record'; git 08e0101: 'the outside review was never recorded'. watch.json holds the queries for each question (supported), and its checks array has three entries, all 2026-08-30; later sweeps are in sweeps.json.runs.

**Proposed:** "The full watch list, with the searches that would answer each question, is kept in the repository that produces this page, alongside a record of the checks we have run — including the ones that found nothing — although three fact-check runs on 30 August left no report."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 60. dfbdfe06 — overstatement

**Page now:** Every figure above comes from the study that produced it, read directly.

**Evidence:** P = 0.0089 is not in S021's held text (the Warwick accepted manuscript gives 'p=0.009' and 'p = 0.009'), nor in S048 (SSRN preprint); it occurs only in S027 (Nature Reviews highlight, abstract_held preview): '(-6% absolute difference, P = 0.0089)'. The 70% cytology figure is Public Health England's estimate as quoted by the Royal College of Pathologists (S039: 'estimated to be approximately 70%, according to Public Health England').

**Proposed:** "Every study figure above comes from the study that produced it, read directly, except P = 0.0089, which is the Nature Reviews highlight's (the accepted manuscript we read gives p = 0.009), and the 70% cytology estimate, which is Public Health England's as the Royal College of Pathologists reports it."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 61. 6f8d3f6e — overstatement

**Page now:** Where we could not read something, we say so rather than passing on somebody else's account of it.

**Evidence:** sources.json S044.access: state blocked, sections 'the Europe PMC core record: title, authors, journal, publication date, DOI, PMID', not_read 'the editorial text'. The page characterises it ('the specialty is working this frame over its own evidence') and never says it was not read; it is not among the three items the next sentence lists. P = 0.0089 is passed on from S027 (a secondary highlight) without saying so (see line 194).

**Proposed:** "Where we could not read something, we say so rather than passing on somebody else's account of it — with two exceptions now corrected: the Gastroenterology editorial, which we know only by its title and authors, and the P value of 0.0089, which comes from a research highlight."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 62. 9c6d0d80 — overstatement

**Page now:** What we watch is narrower than what could change — we can see a registry record move and a paper cite another paper, and we cannot see most of what happens in a field — and nothing obliges anyone to look before you arrive.

**Evidence:** sweeps.json: registry = {} (empty); every 'registry' run for this issue (2026-09-14, 09-21, 09-28, 10-05, 10-12) records 'sources_queried': 0. Citation sweeps do run (sweeps.json.citations for 14 sources).

**Proposed:** "What we watch is narrower than what could change — we can see a paper cite another paper, though no registry record is yet captured for this page, and we cannot see most of what happens in a field — and nothing obliges anyone to look before you arrive."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 63. 6349e704 — misdescribes (location) and overstates

**Page now:** The watch list below is real and it runs; it is our instrument, not a promise to you.

**Evidence:** In the HEAD page the watch list (h2 id="watch", 'What would settle it, and what we are watching') comes before this paragraph, not below it. review/2026-09-12-modest-promise-ruling.md: 'a watch that runs on its own, on time, every time, against every question. No such watch exists here'. watch.json records question checks only on 2026-08-30; the weekly sweeps (sweeps.json.runs to 2026-10-12) are what runs, and the 7 September run was skipped (git 46b6897).

**Proposed:** "The watch list above is real, and its citation and correction sweeps run weekly; it is our instrument, not a promise to you."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 64. 6da54bce — overstatement

**Page now:** Where we read a study through somebody else’s account of it rather than at source, this says so.

**Evidence:** The Budzyń entry gives 'P = 0.0089' and says 'Read in the accepted manuscript'; S021's held accepted manuscript gives 'p=0.009'; 0.0089 occurs only in S027 (Nature Reviews highlight preview). The source list does not say the figure came through the highlight.

**Proposed:** "Where we read a study through somebody else's account of it rather than at source, this says so, with one exception corrected below: P = 0.0089 comes from the Nature Reviews research highlight, not from the accepted manuscript, which gives p = 0.009."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 65. d77cec11 — unsupported claim about access; figure not in the copy read

**Page now:** Read in the accepted manuscript held by the University of Warwick repository; the publisher’s own site refused every request.

**Evidence:** sources.json S021.access.sections: 'the accepted manuscript, Warwick WRAP repository copy' (supported). No record shows the publisher refusing requests for the article: S021 note 2026-10-18 and access-routes.json S021: 'Unpaywall closed, no free copy; paywalled. Not fetched.' The 403s recorded are for the correction notice (S021.THE_CORRECTION.read: 'the publisher (403 on /fulltext and /abstract)'). The entry's P = 0.0089 is not in the accepted manuscript ('p=0.009').

**Proposed:** "Read in the accepted manuscript held by the University of Warwick repository, which gives the P value as 0.009; the published version is paywalled and we have not read it."

**Binding for the corrected text:** S021, as quoted in the evidence above.

## 66. 91730a4c — misdescribed scope of correction

**Page now:** But one of the two findings that was affected is the exposure variable itself, AI introduction, in the adjusted model.

**Evidence:** S045__cef89cd565d3.txt: "A covariate (indication for colonoscopy) had been mistakenly omitted from the multivariable analysis presented in supplementary table 6 in the appendix of this Article ... the only affected findings are for the variables \"After AI introduction (using AI in colonoscopy)\" and \"Age >60 years\"." ; S021__4296ea811a43.txt: Supplementary Table 6 rows "After AI implementation (without using AI in colonoscopy) 145/648 (22.4%) 0.70 (0.54, 0.89) 0.68 (0.53. 0.88)" and "After AI implementation (using AI in colonoscopy) 186/734 (25.3%)"

**Proposed:** "But one of the two findings that was affected is the AI-assisted category, colonoscopies performed with AI after its introduction, in the supplementary adjusted model covering all 2,177 colonoscopies."

**Binding for the corrected text:** S045: "A covariate (indication for colonoscopy) had been mistakenly omitted from the multivariable analysis presented in supplementary table 6 in the appendix of this Article".

## 67. 84eaf825 — overstatement carried from previous sentence

**Page now:** The journal says interpretation is unchanged and we have no basis to disagree; we note it because a correction to the adjusted estimate for the thing a study is about is worth a reader knowing, whichever way it went.

**Evidence:** S045__cef89cd565d3.txt: "These changes do not affect the interpretation of the data." ; "the only affected findings are for the variables \"After AI introduction (using AI in colonoscopy)\" and \"Age >60 years\""

**Proposed:** "The journal says interpretation is unchanged and we have no basis to disagree; we note it because a correction to a study's adjusted model is worth a reader knowing, whichever way it went."

**Binding for the corrected text:** S045: "These changes do not affect the interpretation of the data.".

## 68. cb170ac7 — misattributed location

**Page now:** The paper’s title calls it a scoping review; its methods section describes a narrative review .

**Evidence:** S029__caec391d5633.txt: abstract "Materials and methods: We conducted a narrative review of empirical studies" ; main text "MATERIALS AND METHODS This scoping review was conducted in accordance with the Preferred Reporting Items for Systematic Reviews and Meta-Analyses extension for Scoping Reviews (PRISMA-ScR) guidelines."

**Proposed:** "The paper’s title calls it a scoping review, and so does its methods section; the methods paragraph of its abstract describes a narrative review ."

**Binding for the corrected text:** S029: "Materials and methods: We conducted a narrative review of empirical studies"; S029: "MATERIALS AND METHODS This scoping review was conducted in accordance with the Preferred Reporting Items for Systematic Reviews and Meta-Analyses extension for Scoping Reviews (PRISMA-ScR) guidelines.".

## 69. b3bad0a5 — overstatement and understatement

**Page now:** This page relies on the review for that count and for nothing else; each paper named above was read at source.

**Evidence:** The same entry says the review is the 'Source of the count ... and of the authors' own characterisation of the evidence as scarce, limited and fragmented', so the page relies on it for more than the count. Papers named above that were not read: Rebolj et al. (sources.json not_reached: 'Wiley (403), PubMed (captcha), PMC (captcha)'); Weinberg and Bretthauer (S044 blocked, 'NOT READ IN FULL'); the 2018 replication project (no ledger row; described via S009).

**Proposed:** "This page relies on the review for that count and for its authors' characterisation of the evidence; the studies named above were read at source, except Rebolj and colleagues, which we could not reach, and the Weinberg and Bretthauer editorial, which we know only by its record."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 70. 66fbb27d — misstates how the source was read

**Page now:** Read at the publisher.

**Evidence:** sources.json S046.access.note: 'Downloaded by Fred Ugast in his own browser from PubMed Central (PMC10531198) ... OUP's PDF ... as deposited in PMC'; second rendition 'PubMed Central's HTML', 2026-10-18; S046 'Had no ledger row until 2026-10-18'.

**Proposed:** "Read in the published version, as deposited in PubMed Central."

**Binding for the corrected text:** S046, as quoted in the evidence above.

## 71. d09a03dc — wrong author

**Page now:** Primary Royal College of Pathologists.

**Evidence:** S039__7bec9861abbd.txt: "Published: 16 October 2025 Author: Dr Duaa Saeed-Chesterman Read time: 9 Mins In this article, Dr Duaa Saeed-Chesterman explains the development of the NHS Cervical Screening Programme" ... "Meet the author Dr Duaa Saeed-Chesterman Consultant Histopathologist"

**Proposed:** "Primary Saeed-Chesterman D (Royal College of Pathologists)."

**Binding for the corrected text:** S039: "Published: 16 October 2025 Author: Dr Duaa Saeed-Chesterman Read time: 9 Mins In this article, Dr Duaa Saeed-Chesterman explains the development of the NHS Cervical Screening Programme"; S039: "Meet the author Dr Duaa Saeed-Chesterman Consultant Histopathologist".

## 72. c4927d74 — detail not in source

**Page now:** Also the source of the authors' own reconciliation with the Polish study, of their limitations — PDR-5 rather than ADR, the three-and-a-half-year time effect, the case-mix shift, possible underpowering, one device — and of the endoscopist-level split.

**Evidence:** S043__3af130dc2d4d.txt: "it is challenging to draw such a conclusion ... given that there is always a time effect in which endoscopists may naturally upskill or deskill over time. Mean inclusion time from the first colonoscopy among the inexperienced group was 6.8 months in phase 1, 17.7 months in phase 2, and 23.8 months in phase 3." Limitations: "The most important is the use of PDR-5 ... rather than the gold standard ADR"; "the risk of underpowering"; "differences in the case-mix"; "we used only one type of AI device"

**Proposed:** "Also the source of the authors' own reconciliation with the Polish study, of their limitations — PDR-5 rather than ADR, the time effect, the case-mix shift, possible underpowering, one device — and of the endoscopist-level split."

**Binding for the corrected text:** S043: "it is challenging to draw such a conclusion"; S043: "given that there is always a time effect in which endoscopists may naturally upskill or deskill over time. Mean inclusion time from the first colonoscopy among the inexperienced group was 6.8 months i"; S043: "The most important is the use of PDR-5"; S043: "rather than the gold standard ADR".

## 73. 63ba2dc1 — overstatement

**Page now:** Everything this page says about that work is a description of what the replications set out to reproduce, taken from the replication papers themselves.

**Evidence:** sources.json S010.access.sections: 'the citation only, as Hesselmann reports it'. Hesselmann (S009) is the only replication paper in the ledger; the 2018 replication project is described from Hesselmann's text and was removed as a source (git 0ee52b8: 'Camerer removed from the page rather than left unverified').

**Proposed:** "Everything this page says about that work is a description of what the replications set out to reproduce, taken from Hesselmann's replication paper."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 74. 13eeff53 — unsupported claim about the source (causation disclaimer not in source)

**Page now:** The author does not claim causation.

**Evidence:** S008__e90160a909e9.txt: "These findings suggest that cognitive offloading plays a substantial role in explaining the negative impact of AI usage on critical thinking." | S008__e90160a909e9.txt: "this study sought to explore the impact of AI tool usage on critical thinking skills" | S008__e90160a909e9.txt: "Experimental studies that manipulate the level of AI tool usage ... could offer causal evidence of the relationship between these variables."

**Proposed:** "The design cannot show causation, and the author calls for experiments that "could offer causal evidence", but the paper writes of "the negative impact of AI usage on critical thinking"."

**Binding for the corrected text:** S008: "These findings suggest that cognitive offloading plays a substantial role in explaining the negative impact of AI usage on critical thinking."; S008: "this study sought to explore the impact of AI tool usage on critical thinking skills"; S008: "Experimental studies that manipulate the level of AI tool usage"; S008: "could offer causal evidence of the relationship between these variables.".

## 75. 564c3790 — misdescribed status (published called preprint)

**Page now:** Preprint Liu, Christian, Dumbalska, Bakker & Dubey.

**Evidence:** S001__72e1d3c7e1e9.txt: "Published as a conference paper at COLM 2026 AI Assistance Reduces Persistence and Hurts Independent Performance Grace Liu Carnegie Mellon University Brian Christian University of Oxford Tsvetomira Dumbalska University of Oxford ... Michiel A. Bakker ... Rachit Dubey"

**Proposed:** "Conference paper Liu, Christian, Dumbalska, Bakker & Dubey."

**Binding for the corrected text:** S001: "Published as a conference paper at COLM 2026 AI Assistance Reduces Persistence and Hurts Independent Performance Grace Liu Carnegie Mellon University Brian Christian University of Oxford Tsvetomira Du".

## 76. e68fe056 — overstatement

**Page now:** No pre-registration statement appears in any version.

**Evidence:** sources.json S001.verified_against_v4.PREREGISTRATION: 'NO STATEMENT ANYWHERE, in v2 or v4'; access.sections: 'arXiv HTML v2 and then v4'; versions v1 (6 Apr) and v3 (4 Aug) were not read; the held copy is v4 only.

**Proposed:** "No pre-registration statement appears in version 2 or version 4, the two we read."

**Binding for the corrected text:** our own records, as quoted in the evidence above (a process claim; no source span).

## 77. b34b3805 — overstatement / misdescription

**Page now:** Carries Professor Osmani’s volume-and-fatigue caveat by name, quotes Professor Tucker on automation bias not being peculiar to AI, and calls the study observational throughout.

**Evidence:** S040: 'observational' occurs once ("conducted an observational study"); headline "Using AI Made Doctors Worse at Spotting Cancer Without Assistance"; "doctors who regularly used AI actually became less skilled within months." Osmani: "The increased workload, Osmani suggested, could have led to clinician fatigue and poorer detection rates." Tucker: "is not unique to AI systems and is a risk with the introduction of any new technology."

**Proposed:** "Carries Professor Osmani’s volume-and-fatigue caveat by name, quotes Professor Tucker on automation bias not being peculiar to AI, and calls it an observational study, though its headline says using AI made doctors worse."

**Binding for the corrected text:** S040: "conducted an observational study"; S040: "Using AI Made Doctors Worse at Spotting Cancer Without Assistance"; S040: "doctors who regularly used AI actually became less skilled within months."; S040: "The increased workload, Osmani suggested, could have led to clinician fatigue and poorer detection rates.".

## 78. 645248a3 — misquotes

**Page now:** Their December 2024 preprint had said reduced , and a negative impact on endoscopist performance ; the version that came through peer review says may reduce , and behaviour .

**Evidence:** S021 (the accepted manuscript we hold): "Continuous exposure to AI may reduce ADR of standard colonoscopy, suggesting a negative impact on endoscopist behavior." The page's quoted 'behaviour' is not the held text's spelling.

**Proposed:** "Their December 2024 preprint had said reduced , and a negative impact on endoscopist performance ; the version that came through peer review says may reduce , and behavior ."

**Binding for the corrected text:** S021: "Continuous exposure to AI may reduce ADR of standard colonoscopy, suggesting a negative impact on endoscopist behavior.".

## 79. 0f2e96af — rests on a document not held

**Page now:** And it has already been applied to this exact literature, by someone with standing to do it.

**Evidence:** S044 is blocked; sources.json holds only its Europe PMC / Crossref record (title, authors, journal, date). 'Applied to this exact literature' and 'by someone with standing' describe the editorial's contents, which we have not read.

**Proposed:** "And the frame has already been named in this literature, in the title of an editorial by Weinberg and Bretthauer, which we have not been able to read."

**Binding for the corrected text:** S044, as quoted in the evidence above.

## 80. b44e344b — overstates (unsupported superlative)

**Page now:** Editorial Retraction Note, Humanities and Social Sciences Communications , 22 April 2026 The retraction of the most-cited meta-analysis finding that ChatGPT improves learning.

**Evidence:** 'Most-cited' is in no held document and no recorded citation count. S004 itself is not held; S005's held front matter gives the date: 'Wang & Fan (2025) was retracted by the Editor on 22 April 2026'.

**Proposed:** "Editorial Retraction Note, Humanities and Social Sciences Communications , 22 April 2026 The retraction of the meta-analysis finding that ChatGPT improves learning."

**Binding for the corrected text:** S004, as quoted in the evidence above.

## 81. dde90522 — overstates (a question reported as an argument)

**Page now:** Professor Venet Osmani of Queen Mary University of London named the volume problem exactly — the number of colonoscopies performed nearly doubled after the AI tool was introduced, going from 795 to 1382 — and argued that three months is too short a window for genuine skill loss in experienced clinicians.

**Evidence:** S035, Osmani: "Finally, the study suggests a drop in skill over just three months. This is a very short period, especially for a clinician with over 27 years of experience. It raises the question of whether a true loss of skill could happen so quickly". He raises a question; the page has him argue it. B19 catches this on the uncorrected text.

**Proposed:** "Professor Venet Osmani of Queen Mary University of London named the volume problem exactly — the number of colonoscopies performed nearly doubled after the AI tool was introduced, going from 795 to 1382 — and questioned whether a true loss of skill could happen in three months, a very short period for a clinician with over 27 years of experience."

**Binding for the corrected text:** deterministic. Span, S035 (SMC expert reaction, Prof Venet Osmani): "For example, the number of colonoscopies performed nearly doubled after the AI tool was introduced, going from 795 to 1382." also_rests_on S035: "Osmani, Professor of Clinical AI and Machine Learning, Queen Mary University of London, said: "There are several reasons to be cautious about concluding that AI" also_rests_on S035: "Finally, the study suggests a drop in skill over just three months. This is a very short period, especially for a clinician with over 27 years of experience. It" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 82. 991b00d0 — hedge strengthened ('could' becomes 'would')

**Page now:** They also point at Troya and colleagues — the eye-tracking study in the section above — as the mechanism that would explain the Polish result.

**Evidence:** S043: "A study by Troya et al. showed decreased eye travel distance when using CADe , which could explain why such deskilling happened in the study by Budzyn et al." B19 catches this on the uncorrected text.

**Proposed:** "They also point at Troya and colleagues — the eye-tracking study in the section above — as a mechanism that could explain the Polish result."

**Binding for the corrected text:** context. Span, S043 (Discussion): "A study by Troya et al. showed decreased eye travel distance when using CADe , which could explain why such deskilling happened in the study by Budzyn et al." Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 83. 930417d1 — misreads the flow diagram

**Page now:** ESMO Real World Data and Digital Oncology 2026;12:100693 Source of the count of included work — twelve studies from 373 records screened — and of the authors’ own characterisation of the evidence as scarce, limited and fragmented.

**Evidence:** S029 Figure 1: "Total records identified n = 373 Total records screened n = 65". 373 is records identified, not screened.

**Proposed:** "ESMO Real World Data and Digital Oncology 2026;12:100693 Source of the count of included work — twelve studies from 373 records identified — and of the authors’ own characterisation of the evidence as scarce, limited and fragmented."

**Binding for the corrected text:** deterministic. Span, S029 (Figure 1; Abstract; Limitations): "Total records identified n = 373 Total records screened n = 65 Full-text articles assessed for eligibility n = 65 Studies included in qualitative synthesis (scoping review) n = 12" also_rests_on S029: "Evidence of clinical deskilling, though scarce, is consistent across specialties." also_rests_on S029: "most of the available evidence on deskilling remains fragmented across specialties, with heterogeneous study designs and variable methodological rigor." also_rests_on S029: "Overall, the number of highquality empirical studies remains limited" Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 84. 65dba6ca — scope widened; an unsupported ranking

**Page now:** Separately, four learning scientists audited the studies behind the next-most-cited synthesis and found that of 19 comparisons, four met three basic criteria : a well-defined treatment, an adequately described control, and a valid learning measure.

**Evidence:** S006: "we audited a subset of primary experiments included in Deng et al.'s meta-analysis"; "only four comparisons (21%) satisfied all three criteria". 'Next-most-cited' rests on no held document or recorded count.

**Proposed:** "Separately, four learning scientists audited a subset of the studies behind another synthesis and found that of 19 comparisons, four met three basic criteria : a well-defined treatment, an adequately described control, and a valid learning measure."

**Binding for the corrected text:** deterministic. Span, S006 (Abstract; Table 1): "A summary of results for 19 comparisons is reported (see Table 1). Notably, only four comparisons (21%) satisfied all three criteria" also_rests_on S006: "To provide some initial evidence, we audited a subset of primary experiments included in Deng et al.'s meta-­analysis, demonstrating that only a small minority " also_rests_on S006: "Paper identifies three non-­negotiables: well-­defined treatment and control, and valid learning measures." Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 85. 0eba3348 — rests on a document not held (now attributed to the College's report)

**Page now:** The two counts differ and we cannot say why: the College's report and the review's source disagree about the starting number, and NHS Digital's own annual report says 48 consolidated to 8 without mentioning any earlier closures.

**Evidence:** S039: "The effect on the workforce was further exacerbated by the centralisation and consolidation of NHSCSP labs, reducing 48 accredited labs to 8 centralised labs as of 2019." S029 Table 1: "laboratories reduced from 45 UK) to 8" (citing Rebolj et al. 2022, not reachable). NHS Digital's annual report is not in the source list and not held.

**Proposed:** "The two counts differ and we cannot say why: the College's report gives 48 accredited labs reduced to 8 centralised labs as of 2019, while the review's source, which we could not read, starts from 45."

**Binding for the corrected text:** context. Span, S039 (RCPath report, workforce paragraph): "The effect on the workforce was further exacerbated by the centralisation and consolidation of NHSCSP labs, reducing 48 accredited labs to 8 centralised labs as of 2019." Checks in memory on the corrected text (rule 1, B2, B5, B6, B12, B19 incl. significance, B20, B22, B23): clean.

## 86. b053b281 — the volume the held proof prints

**Page now:** The proof we hold prints “Volume 11 ■ Issue C” in its running footer, above “Available online xxx”; the publisher’s registered metadata for the version of record gives volume 12 and no issue, which is what we cite.

**Evidence:** the S029 PDF in the library (sha caec391d…, held 2026-09-15 from the publisher's whole-issue bundle) prints "Volume 12 ■ Issue C ■ 2026" in its footer and "Available online 19 March 2026". The 'Volume 11 … xxx' wording describes the proof read on 29–30 August, which is not the file we hold. The S029 ledger note is corrected to match, with a dated note.

**Proposed:** "The copy we hold prints “Volume 12 ■ Issue C ■ 2026” in its running footer, and the publisher’s registered metadata for the version of record gives volume 12, which is what we cite."

**Binding for the corrected text:** S029: "Volume 12 ■ Issue C ■ 2026" (running footer, held text).

## 87. Batch-4 sentences checked and standing

- `d956dc78` On 5 June 2026, two days after the Norwegian trial appeared, Gastroenterology published an editorial by Weinbe — Stands. Europe PMC, checked 2026-10-18: PMID 42250888, electronicPublicationDate 2026-06-05; S043's own metadata gives its epub as 3 June 2026, two days earlier. Title and authors match Crossref (10.1053/j.gastro.2026.05.026).
- `d06d9c3d` It has been a preprint since June 2025. — Stands. arXiv API, checked 2026-10-18: 2506.08872 latest version v2 (published 2025-06-10, updated 2025-12-31), no journal reference or DOI; Crossref has no published version. Note: we hold v1; v2 has not been read.
- `93c14a94` The correction notice states that the scientific conclusions are unaffected, and nothing on this page turns on — Stands. Now held as S049, the notice reads: 'Table 4 was a duplicate of Table 3 in the publication. The corrected version of Table 4 appears below. The author states that the scientific conclusions are unaffected.' (The statement is the author's, carried by the notice.)
- `111ae20d` That is a working paper, not a reviewed one. — Stands. Crossref, checked 2026-10-18: only SSRN (10.2139/ssrn.6097646) and PsyArXiv/OSF (10.31234/osf.io/yk25n_v1) posted versions; no journal article.
- `7011fffe` Submitted June 2025 and still a preprint. — Stands, on the same check as d06d9c3d (submitted 10 June 2025; no published version as of 18 October 2026).
- `7419c16a` Source of the date and of the editor’s stated ground. — Stands. S004 itself is not held, but S005's held front matter gives the same date and ground: 'Wang & Fan (2025) was retracted by the Editor on 22 April 2026, citing discrepancies in the meta-analysis'.
- `483ce0da` A working paper, not peer reviewed. — Stands, on the same check as 111ae20d.
- `17e6f095` (In fairness to the author… a published correction of 10 September 2025…) — now fully supported: the recruitment is in S008, and the correction is S049 ('Table 4 was a duplicate of Table 3'). Bindable; not yet bound.
- `89466d77`, `13eeff53` — do NOT stand: the MDPI article page (held 2026-10-18 as S008's second rendition) contains no causation disclaimer either; corrected above.

## Judgements (2026-10-18): the 48 group-(iii) sentences

Each judgement sentence was given premises cut from held text by two read-only agents, every span re-verified by script as an exact substring of its held text, and a written-out step; Claude Code read each against its premises, reviewed by Claude (advisor), and the operator ruled. 24 stand and are bound as judgements (listed under Bound). 24 are corrections, below. The proposed wording is Claude Code's unless the operator gave it (afd83f74, e99eaaf7, 849ac2af).

## 88. acd4fe6c — overstates (judgement)

**Page now:** Nobody's skill decayed; there was simply far less of the work on which the skill is built.

**Evidence:** 'Nobody's skill decayed' is a universal negative no source establishes; S039 says the change is 'potentially reducing diagnostic expertise' and calls skill retention a challenge, and S029 cites 'erosion of morphological expertise'.

**Proposed:** "Nobody measured an individual's skill decaying; there was simply far less of the work on which the skill is built — which, the College warns, may itself reduce diagnostic expertise."

**Binding for the corrected text:** judgement. Premises: S039: "The major shift into primary HPV testing has resulted in a massive reduction in cytology workload, estimated to be approximately 70%, according to Public Health England."; S039: "The effect on the workforce was further exacerbated by the centralisation and consolidation of NHSCSP labs, reducing 48 accredited labs to 8 centralised labs as of 2019."; S039: "resulting in less exposure to abnormal cases and a shift towards lower-grade lesions, potentially reducing diagnostic expertise in the diagnosis of higher-grade lesions. The retention of skills, continued training and maintenance of diagnostic accuracy in the face of decreasing disease prevalence remains a challenge in both cytology and histopathology."; S029: "cytology workloads declined by 80%-85%, raising concerns about the erosion of morphological expertise and the reduction of training opportunities for junior pathologists.". Step: S039 and S029 describe a fall in cytology workload and laboratories, and both warn this may erode expertise; no held source measured individual skill in either direction, so the far-less-work clause holds but the universal 'nobody's skill decayed' does not. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 89. fcd870cc — overstates (judgement)

**Page now:** This one is — specifically on the question of what happens after the tool is withdrawn, since it found a real gain while the tool was running — with the limits its own authors put on it.

**Evidence:** 'It found a real gain while the tool was running' drops the restriction: the gain was significant only among the seven inexperienced endoscopists; overall and among the experienced there was none, so the after-withdrawal null is not informative in the same way for them.

**Proposed:** "This one is — specifically on the question of what happens after the tool is withdrawn, since among its inexperienced endoscopists it found a real gain while the tool was running — with the limits its own authors put on it."

**Binding for the corrected text:** judgement. Premises: S043: "CADe temporarily increased PDR-5 among inexperienced endoscopists from phase 1 to 2 (31.9% [216/678] to 39.5% [257/651]; odds ratio [OR] 1.43, 95%CI 1.11-1.84). There was no significant change between phases 1 and 3 (31.9% [216/678] to 36.3% [173/476]; OR 1.03, 95%CI 0.79-1.34). There was no significant CADe effect on PDR-5 among experienced endoscopists between phases."; S043: "2 (CADe) All 548/1739 (31.5) 1.09 (0.94-1.26) - Inexperienced 257/651 (39.5) 1.37 (1.09-1.72) 1 1.43 (1.11-1.84) 1 Experienced 291/1088 (26.7) 0.92 (0.76-1.12)"; S043: "In non-CADe-assisted colonoscopy, no upskilling or deskilling was observed following a period of CADe exposure.". Step: S043 reports a null after withdrawal, but its gain during CADe was among inexperienced endoscopists only (OR 1.43); overall the phase-2 rise was 29.7% to 31.5% (OR 1.09, 0.94-1.26) and the experienced showed none; so the null after withdrawal is informative chiefly for the inexperienced. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 90. 8d9dda78 — overstates (judgement)

**Page now:** If AI exposure changes what an endoscopist can do unassisted, something has to have changed in how they look.

**Evidence:** 'Something has to have changed in how they look' asserts a necessary mechanism; S021 itself proposes motivation, focus and responsibility, and withdrawal time and case mix were also uncontrolled, and S043 says only that gaze 'could explain' the result.

**Proposed:** "If AI exposure changes what an endoscopist can do unassisted, one plausible place for the change is in how they look."

**Binding for the corrected text:** judgement. Premises: S043: "A study by Troya et al. showed decreased eye travel distance when using CADe , which could explain why such deskilling happened in the study by Budzyn et al."; S031: "Effort, as expressed by eye travel distance, decreased, and gaze remained more focused, presumably waiting for a bounding box to appear. This might be efficient but risks missing a polyp that is not captured by the system."; S021: "We assume that continuous exposure to decision support systems like AI may lead to the natural human tendency to over-rely on their recommendations, leading to clinicians becoming less motivated, less focused, and less responsible when making cognitive decisions without AI assistance.". Step: S043 and S031 propose gaze change as one possible mechanism, while S021 proposes reduced motivation, focus and responsibility; so a change in looking is a plausible mechanism, not a necessary one. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'could' (S043), 'appear' (S031), 'might' (S031), 'may' (S021); the sentence carries no hedge) — a WARN, not a block.

## 91. b7985c65 — overstates (judgement)

**Page now:** Nobody has tested whether those are the same thing, and this page does not claim they are.

**Evidence:** 'Nobody has tested' is a universal negative no held source establishes; the most the evidence supports is that neither paper tests it and we found no study that does. (Also, S028 itself warns reduced coverage could increase missed cancers, so the preceding contrast slightly understates Gommers' caution.)

**Proposed:** "We have found no study that tests whether those are the same thing, and this page does not claim they are."

**Binding for the corrected text:** judgement. Premises: S028: "Radiologists improved their breast cancer detection accuracy when reading mammography with AI support, spending more fixation time on suspicious areas and less on the rest of the breast, indicating a more efficient search."; S028: "However, reduced coverage could also increase the risk of missing cancers not detected by AI"; S031: "Effort, as expressed by eye travel distance, decreased, and gaze remained more focused, presumably waiting for a bounding box to appear. This might be efficient but risks missing a polyp that is not captured by the system.". Step: S028 reads narrowed search as efficiency and S031 reads narrowed gaze as a risk; neither tests whether the two narrowings are the same phenomenon; we found no study that does, but that absence is ours, not established. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'could' (S028), 'appear' (S031), 'might' (S031); the sentence carries no hedge) — a WARN, not a block.

## 92. 3d054dd8 — overstates (judgement)

**Page now:** It is a study about what happens inside a single reading, and it is the clearest measurement in this entire field of the thing people actually describe when they say AI has changed how they work: you take what it gives you.

**Evidence:** 'The clearest measurement in this entire field' is an unsupported superlative; S046 (45.5% of errors under AI attributable to automation bias), S038 (7% of correct judgements overturned) and S017 (79.8% following wrong advice) measure the same thing, and no ranking is given.

**Proposed:** "It is a study about what happens inside a single reading, and it measures directly the thing people actually describe when they say AI has changed how they work: you take what it gives you."

**Binding for the corrected text:** judgement. Premises: S030: "The percentage of correctly rated mammograms by inexperienced (mean, 79.7% ± 11.7 [SD] vs 19.8% ± 14.0; P < .001; r = 0.93), moderately experienced (mean, 81.3% ± 10.1 vs 24.8% ± 11.6; P < .001; r = 0.96), and very experienced (mean, 82.3% ± 4.2 vs 45.5% ± 9.1; P = .003; r = 0.97) radiologists was significantly impacted by the correctness of"; S030: "The results show that inexperienced, moderately experienced, and very experienced radiologists reading mammograms are prone to automation bias when being supported by an AI-based system.". Step: S030 measures, within single readings, how accuracy falls when the AI suggestion is wrong (to 19.8%, 24.8% and 45.5%) and concludes readers at all levels are prone to automation bias; so it directly measures taking what the AI gives you. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 93. dbaaa31b — rests on a document not held (S044) (judgement)

**Page now:** What this page does that it does not is carry the distinction out of the specialty to a reader deciding something about their own work — and that, rather than the frame, is the part we can claim.

**Evidence:** The comparison ('what this page does that it does not') concerns the content and audience of S044, which is not among the held texts, so no passage can support what that editorial does or does not do.

**Proposed:** "What this page tries to add to an editorial written for the specialty is to carry the distinction out of it to a reader deciding something about their own work — and that, rather than the frame, is the part we can claim."

**Binding for the corrected text:** judgement. Premises: S025: "AI integration in medical training may introduce three distinct risks to competency development: deskilling, mis-skilling, and never-skilling.". Step: S025 supplies the three-way distinction; the claim that the Weinberg and Bretthauer editorial does not carry it to general readers rests on S044, which is not held, and on its venue (Gastroenterology). Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'may' (S025); the sentence carries no hedge) — a WARN, not a block.

## 94. a0b796f2 — overstates (judgement)

**Page now:** The evidence a general reader has been offered is much weaker than the evidence they have not.

**Evidence:** The strength comparison is supported, but 'the evidence they have not [been offered]' is too strong: Fortune (S023) carried the Polish result to a general readership; what did not reach them is that evidence with its qualifications, which is how the page's own opening puts it.

**Proposed:** "The evidence a general reader is usually offered is much weaker than the evidence that has mostly not reached them with its qualifications intact."

**Binding for the corrected text:** judgement. Premises: S019: "indicates that approximately N = 159 participants would be required for adequate power."; S007: "We recruited a total of 54 participants for Sessions 1, 2, 3, and 18 participants among them completed session 4."; S009: "the sequential Bayes Factor (BF) analysis yielded a final BF 01 of 5.07 in favor of the null over the alternative hypothesis, after the data from N = 89 participants were taken into account"; S008: "The correlation between AI tool use and critical thinking was found to be strongly negative (r = -0.68), suggesting that greater reliance on AI tools is associated with a decline in critical thinking skills."; S021: "ADR of standard colonoscopy significantly decreased from 28.4% (226/795) before to 22.4% (145/648) after the exposure to AI, corresponding to a 6% absolute reduction (95% confidence interval: -10.5% to -1.6%)."; S030: "The percentage of correctly rated mammograms by inexperienced (mean, 79.7% ± 11.7 [SD] vs 19.8% ± 14.0; P < .001; r = 0.93), moderately experienced (mean, 81.3% ± 10.1 vs 24.8% ± 11.6; P < .001; r = 0.96), and very experienced (mean, 82.3% ± 4.2 vs 45.5% ± 9.1; P = .003; r = 0.97) radiologists was significantly impacted by the correctness of"; S023: "endoscopists introduced to an AI-assistance system went from detecting potential polyps at a rate of 28.4% with the technology to 22.4% after they no longer had access to the AI tools they were introduced to-a 20% drop in detection rates.". Step: The widely circulated studies are underpowered (S019 on S007), a failed replication (S009) or cross-sectional (S008), while the medical evidence includes measured falls (S021) and controlled reader studies (S030); but S023 shows the Polish result did reach a general (business) readership, albeit misdescribed and without its limitations. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'hypothesis' (S009); the sentence carries no hedge) — a WARN, not a block.

## 95. dbe8c633 — overstates (a claim about what public belief rests on, stated as fact) (judgement)

**Page now:** The belief that AI is degrading thinking does not usually travel on any of the above.

**Evidence:** This is an empirical claim about what public belief travels on, and no held passage measures it; the held coverage that does exist (Fortune, CACM) cites the Polish study and a Microsoft/Carnegie Mellon survey, which cuts partly against it.

**Proposed:** "In our reading, the belief that AI is degrading thinking does not usually rest on any of the above."

**Binding for the corrected text:** judgement. Premises: S023: "A study from Microsoft and Carnegie Mellon University earlier this year found that among surveyed knowledge workers, AI increased work efficiency, but reduced critical enga"; S033: "In a 2025 survey conducted by Microsoft Research and Hank Lee , a Carnegie Mellon Ph.D. student, knowledge workers reported that generative AI made tasks seem cognitively easier.". Step: No held source surveys which studies the general belief rests on; the two held general-audience pieces (S023, S033) lean on the Polish study itself and on a Microsoft/Carnegie Mellon survey, neither of which is the 'three studies' that follow. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 96. 94285a34 — overstates (judgement)

**Page now:** It travels on three studies, and all three are weaker than their reputations.

**Evidence:** 'It travels on three studies' asserts which studies carry the belief without any source on that, and held coverage cites the Microsoft/Carnegie Mellon survey instead; 'weaker than their reputations' needs their reputations documented, which only the page's own descriptions supply.

**Proposed:** "Three studies often cited for it are each weaker than they are usually taken to be."

**Binding for the corrected text:** judgement. Premises: S007: "We recruited a total of 54 participants for Sessions 1, 2, 3, and 18 participants among them completed session 4."; S019: "indicates that approximately N = 159 participants would be required for adequate power."; S019: "Thus, a group with fewer significant connections should not necessarily be interpreted as exhibiting weaker overall neural activity."; S009: "the sequential Bayes Factor (BF) analysis yielded a final BF 01 of 5.07 in favor of the null over the alternative hypothesis, after the data from N = 89 participants were taken into account"; S008: "The correlation between AI tool use and critical thinking was found to be strongly negative (r = -0.68), suggesting that greater reliance on AI tools is associated with a decline in critical thinking skills."; S008: "Experimental studies that manipulate the level of AI tool usage and measure resultant changes in critical thinking performance could offer causal evidence of the relationship between these variables."; S023: "A study from Microsoft and Carnegie Mellon University earlier this year found that among surveyed knowledge workers, AI increased work efficiency, but reduced critical enga". Step: S019 shows S007 is underpowered (54, then 18; ~159 needed) and its connectivity measure relative; S009 finds no Google effect (BF 5.07 for the null); S008 is a survey correlation whose author says experiments are needed for causal evidence; so each is weaker than a causal reading, but no source establishes that belief 'travels on' exactly these three, and S023/S033 cite a different study. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'hypothesis' (S009), 'could' (S008); the sentence carries no hedge) — a WARN, not a block.

## 97. caab5487 — overstates (judgement)

**Page now:** That uniformity is what common-method variance looks like.

**Evidence:** 'Is what common-method variance looks like' reads as a diagnosis; uniform correlations are consistent with common-method variance but equally with a real relationship, and no held source tests for it.

**Proposed:** "That uniformity is what common-method variance would produce, though it does not prove it is present."

**Binding for the corrected text:** judgement. Premises: S008: "Cognitive Offloading ↔ Critical Thinking +0.72 -0.68 -0.75 Strong positive correlation Strong negative correlation Strong negative correlation"; S008: "we conducted surveys and in-depth interviews with 666 participants across diverse age groups and educational backgrounds"; S008: "Experimental studies that manipulate the level of AI tool usage and measure resultant changes in critical thinking performance could offer causal evidence of the relationship between these variables.". Step: S008 measures all three constructs in one survey and reports uniformly strong correlations (+0.72, -0.68, -0.75); uniform strong correlations among same-source self-reports are what shared method variance would produce, but S008 does not test for it and genuine association would also produce them. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'could' (S008); the sentence carries no hedge) — a WARN, not a block.

## 98. e7229fa9 — overstates (judgement)

**Page now:** The strongest evidence that AI use degrades a real skill, in real work, comes from an endoscopy suite — measured not after the tool was taken away but on the days it was not used, during a period when it was in use on the others.

**Evidence:** 'The strongest evidence' is an unscoped superlative across all evidence; the premises establish only that it is the strongest such evidence among the studies this page read, and the prospective Pedersen trial on the same question found no decay.

**Proposed:** "The strongest evidence we found that AI use degrades a real skill, in real work, comes from an endoscopy suite — measured not after the tool was taken away but on the days it was not used, during a period when it was in use on the others."

**Binding for the corrected text:** judgement. Premises: S021: "ADR of standard colonoscopy significantly decreased from 28.4% (226/795) before to 22.4% (145/648) after the exposure to AI, corresponding to a 6% absolute reduction (95% confidence interval: -10.5% to -1.6%)."; S021: "These centers implemented AI tools for polyp detection at the end of 2021, after which colonoscopies were randomly conducted with or without AI assistance according to the date of examination."; S021: "We conducted a retrospective observational study at four endoscopy centers in Poland."; S043: "We evaluated the effect of exposure to CADe "after" CADe was removed, whereas Budzyn et al. investigated how endoscopists perform non-CADe-assisted colonoscopy "while" they were exposed to CADe in the other colonoscopies they performed during the same time period.". Step: Among the studies this page reviewed, the Polish study is the only one showing a fall in a clinical skill in routine practice, and its non-AI colonoscopies were done on non-AI days while AI was in use on other days, as Pedersen et al. point out; the superlative is therefore a ranking within this page's evidence. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 99. b25cbddc — overstates (judgement)

**Page now:** The ones that would make a reader hold the number loosely did not.

**Evidence:** An unscoped universal negative about all coverage; the premises (and the page itself, 'not one piece of coverage we read') support it only for the coverage this page read, and absence cannot be shown from held passages.

**Proposed:** "The ones that would make a reader hold the number loosely did not, in the coverage we read."

**Binding for the corrected text:** judgement. Premises: S021: "This was primarily due to the temporary suspension of the colonoscopy-based colorectal cancer screening programme in Poland on 1 January 2022 (lasting until December 2022)."; S021: "Seventh, the lack of data of endoscope withdrawal time and sample size calculation due to the retrospective observational design are also noticeable limitations."; S040: "noted to SMC that the total number of colonoscopies-including both AI-assisted and non-AI-assisted ones-increased over the course of the study. The increased workload, Osmani suggested, could have led to clinician fatigue and poorer detection rates."; S023: "endoscopists introduced to an AI-assistance system went from detecting potential polyps at a rate of 28.4% with the technology to 22.4% after they no longer had access to the AI tools they were introduced to-a 20% drop in detection rates.". Step: The caveats that explain the fall in detail (the screening-programme suspension as the cause of the volume rise, the missing withdrawal-time data) are in the paper, while the coverage read reported at most that volume rose, and Fortune reported the figures without limitations. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'could' (S040); the sentence carries no hedge) — a WARN, not a block.

## 100. 6183737f — overstates (judgement)

**Page now:** What did not travel is the specific.

**Evidence:** Time carried a specific caveat (the rise in procedure volume and its possible effect through fatigue), as the page's own next sentence concedes; the unqualified 'the specific' did not travel is broader than the premises allow.

**Proposed:** "What mostly did not travel is the specific."

**Binding for the corrected text:** judgement. Premises: S021: "This was primarily due to the temporary suspension of the colonoscopy-based colorectal cancer screening programme in Poland on 1 January 2022 (lasting until December 2022)."; S021: "Seventh, the lack of data of endoscope withdrawal time and sample size calculation due to the retrospective observational design are also noticeable limitations."; S040: "noted to SMC that the total number of colonoscopies-including both AI-assisted and non-AI-assisted ones-increased over the course of the study. The increased workload, Osmani suggested, could have led to clinician fatigue and poorer detection rates.". Step: The paper's specific limitations (the screening-programme suspension as the reason for the volume rise, the missing withdrawal-time data) are absent from the coverage held, although Time did carry the volume rise itself. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'could' (S040); the sentence carries no hedge) — a WARN, not a block.

## 101. 2c9f964b — overstates (judgement)

**Page now:** And the further the finding got from the specialty, the less arrived with it.

**Evidence:** 'The further ..., the less' asserts a graded, monotonic relationship across all coverage; the premises show only a contrast between a few specialist and a few general outlets, and Time, a general outlet, carried both caveats.

**Proposed:** "And the pieces we read that were furthest from the specialty, in business and computing outlets, carried the least of it."

**Binding for the corrected text:** judgement. Premises: S023: "endoscopists introduced to an AI-assistance system went from detecting potential polyps at a rate of 28.4% with the technology to 22.4% after they no longer had access to the AI tools they were introduced to-a 20% drop in detection rates."; S023: "Doctors who used AI assistance in procedures became 20% worse at spotting abnormalities on their own, study finds, raising concern about overreliance"; S023: "A study from Microsoft and Carnegie Mellon University earlier this year found that among surveyed knowledge workers, AI increased work efficiency, but reduced critical engagement with content, atrophying judgment skills."; S033: "The detection rate for precancerous lesions dropped from 28.4% to 22.4% without AI in the picture. Similar issues pop up in law, education, journalism, software development, and other fields."; S041: "The authors acknowledged some limitations of the study, including its observational nature, noting that factors other than the implementation of AI use may have influenced the findings."; S042: ""However, the study design, population limits, operator factors, and short-term focus restrict broad applicability, and the deskilling concern remains hypothetical rather than proven," he noted.". Step: Specialist outlets (ASCO Post, Healthgrades with a named gastroenterologist) carried caveats, while the business and computing outlets (Fortune, Communications of the ACM) reported the figures with none of the study's limitations, so the pieces furthest from the specialty carried the least. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'may' (S041); the sentence carries no hedge) — a WARN, not a block.

## 102. 13a1f595 — overstates (judgement)

**Page now:** That is the same design error this page is about, in a magazine read by more people than the journal — and a draft of this section said nothing false had been printed here.

**Evidence:** No held passage supports the readership comparison ('read by more people than the journal'), and the draft history is an internal record, not a source; the design-error part is fully supported.

**Proposed:** "That is the same design error this page is about, in a general business magazine — and a draft of this section said nothing false had been printed here."

**Binding for the corrected text:** judgement. Premises: S023: "endoscopists introduced to an AI-assistance system went from detecting potential polyps at a rate of 28.4% with the technology to 22.4% after they no longer had access to the AI tools they were introduced to-a 20% drop in detection rates."; S021: "ADR of standard colonoscopy significantly decreased from 28.4% (226/795) before to 22.4% (145/648) after the exposure to AI, corresponding to a 6% absolute reduction (95% confidence interval: -10.5% to -1.6%)."; S021: "These centers implemented AI tools for polyp detection at the end of 2021, after which colonoscopies were randomly conducted with or without AI assistance according to the date of examination."; S043: "We evaluated the effect of exposure to CADe "after" CADe was removed, whereas Budzyn et al. investigated how endoscopists perform non-CADe-assisted colonoscopy "while" they were exposed to CADe in the other colonoscopies they performed during the same time period.". Step: Fortune said the 28.4% was 'with the technology' and the 22.4% 'after they no longer had access', whereas the paper's 28.4% is pre-AI and the 22.4% was measured on non-AI days while AI was in use on other days, so Fortune repeats the 'after removal' misreading the page is about. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 103. cb13b0ff — overstates (judgement)

**Page now:** None of this makes the review's substance wrong, and we are relying on it.

**Evidence:** The listed errors (wrong design label, misattributed reference 16, a Savardi summary that does not match the paper, a Table 1 misattribution) are themselves errors of substance; the premises support only that the parts this page relies on — the count and the overall characterisation — are not undermined.

**Proposed:** "None of this undermines the parts of the review we rely on — its count of included studies and its description of the evidence as scarce and fragmented."

**Binding for the corrected text:** judgement. Premises: S029: "Studies included in qualitative synthesis (scoping review) n = 12"; S029: "Evidence of clinical deskilling, though scarce, is consistent across specialties."; S029: "most of the available evidence on deskilling remains fragmented across specialties, with heterogeneous study designs and variable methodological rigor."; S029: "In a multicenter randomized trial in colonoscopy, the adenoma detection rate (ADR) dropped significantly from 28.4% to 22.4% when endoscopists reverted to non-AI procedures after repeated AI use, while ADR remained stable with AI assistance (25.3%)."; S029: "16. Gommers JJJ, Verboom SD, Duvivier KM, et al. Influence of AI decision support on radiologists' performance and visual search in screening mammography. Radiology. 2025;316(1):e243688.". Step: The review's errors are in how it describes individual studies (design label, reference attribution), while the count of included studies and its characterisation of the evidence as scarce and fragmented, which is what this page uses, are unaffected. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 104. 1ed69ef1 — overstates (judgement)

**Page now:** It makes the point that carrying a finding accurately across a boundary is difficult enough that the careful people fail at it too.

**Evidence:** One review's errors show that careful specialists can fail; 'difficult enough that the careful people fail at it too' generalises from one case, and calling the authors 'careful' is not established by a review with several misattributions.

**Proposed:** "It shows that carrying a finding accurately across a boundary is difficult enough that a specialist review, whose own body gets the design right, can still fail at it."

**Binding for the corrected text:** judgement. Premises: S029: "In a multicenter randomized trial in colonoscopy, the adenoma detection rate (ADR) dropped significantly from 28.4% to 22.4% when endoscopists reverted to non-AI procedures after repeated AI use, while ADR remained stable with AI assistance (25.3%)."; S029: "The strongest empirical signal of clinical deskilling was observed in colonoscopy. A multicenter observational study conducted in Poland". Step: A specialist review whose body correctly calls the study observational still misdescribes it in its abstract, which shows that even expert authors can lose a finding's design when summarising it. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 105. 738c8380 — overstates (judgement)

**Page now:** It settles the confounding that the volume doubling introduced, and it is the single study that would move this from an association to a causal finding.

**Evidence:** 'Settles' and 'the single study that would move this from an association to a causal finding' are stronger than the premises allow: one trial would address confounding by period but not settle it, and Pedersen et al.'s prospective before-during-after design is another route to a causal test.

**Proposed:** "It would address the confounding that the volume doubling introduced, and it is the design that would most directly test whether the association is causal."

**Binding for the corrected text:** judgement. Premises: S021: "we observed an almost two-fold increase in the number of procedures in the post-AI phase compared to the pre-AI phase (795 before vs. 1382 after AI implementation including 734 with AI-assistance and 648 without AI-assistance), even though both phases covered approximately three months."; S021: "This was primarily due to the temporary suspension of the colonoscopy-based colorectal cancer screening programme in Poland on 1 January 2022 (lasting until December 2022)."; S021: "We conducted a retrospective observational study at four endoscopy centers in Poland."; S021: "We emphasize the urgent need for robust prospective studies such as randomized crossover trials to assess its generalizability and call for more behavioral research to understand the currently under-investigated mechanisms of how AI affects physician capability."; S043: "We evaluated the effect of exposure to CADe "after" CADe was removed, whereas Budzyn et al. investigated how endoscopists perform non-CADe-assisted colonoscopy "while" they were exposed to CADe in the other colonoscopies they performed during the same time period.". Step: A randomised crossover allocation of endoscopists would balance period effects such as the volume increase from the screening suspension across arms, so it would address that confounding and test whether the observed association is causal. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 106. 4fd2fa15 — misdescribes the Norwegian trial's span (judgement)

**Page now:** Neither reaches the horizon people actually ask about, which is years.

**Evidence:** Pedersen et al. ran from November 2021 to June 2025 and the inexperienced group's mean inclusion reached 23.8 months by phase 3, so the trial's sequence does span about two years; what neither reaches is years of AI exposure before unassisted measurement. 'The horizon people actually ask about' is also unsourced.

**Proposed:** "Neither follows endoscopists through years of AI use before measuring them without it."

**Binding for the corrected text:** judgement. Premises: S043: "Mean inclusion times from the first colonoscopy among the inexperienced vs. experienced groups were 6.8 vs. 2.2 months in phase 1, 17.7 vs. 7.6 months in phase 2, and 23.8 vs. 11.8 months in phase 3, respectively."; S043: "We performed a prospective, multicenter, registry-based, pragmatic clinical trial from November 2021 to June 2025"; S021: "we observed an almost two-fold increase in the number of procedures in the post-AI phase compared to the pre-AI phase (795 before vs. 1382 after AI implementation including 734 with AI-assistance and 648 without AI-assistance), even though both phases covered approximately three months.". Step: The Polish comparison covers about three months either side and the Norwegian trial's phases cover roughly a year of CADe exposure and about six months after removal for the inexperienced group, so neither follows endoscopists through several years of use. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 107. 6b66734b — overstates (judgement)

**Page now:** Eye tracking during real colonoscopy, linked to what was actually found, would move the mechanism from plausible to shown.

**Evidence:** Eye tracking linked to findings in live procedures would still be observational; it would make the mechanism more than plausible but would not by itself 'show' it causally.

**Proposed:** "Eye tracking during real colonoscopy, linked to what was actually found, would test the mechanism directly rather than in video clips."

**Binding for the corrected text:** judgement. Premises: S031: "Participants with variable levels of colonoscopy experience viewed video sequences (n = 29) while eye movement was tracked."; S031: "21 participants performed 1218 experiments."; S031: "It increased misinterpretation of normal mucosa and decreased the eye travel distance. Possible consequences of these findings might be prolonged examination time and deskilling."; S032: "the potential impact on visual gaze could potentially be a mechanism by which prolonged CADe exposure could potentially impact performance over time.". Step: The gaze evidence (Troya et al., 21 participants viewing video sequences) and the ACG appraisal propose gaze narrowing as a possible mechanism; measuring gaze in live procedures and linking it to detections would test that mechanism directly. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): B19 evidence hedge dropped (the evidence says 'might' (S031), 'could' (S032); the sentence carries no hedge) — a WARN, not a block.

## 108. 4512a421 — overstates (judgement)

**Page now:** It does not say whether any clinician, department or reader should use these tools, and nothing here bears on whether AI-assisted colonoscopy is good for patients — the randomised evidence that AI raises detection during the procedure is not in dispute and is not what this page examined.

**Evidence:** 'Not in dispute' is a universal claim no held passage establishes; the premises show a meta-analysis of randomised trials reporting a rise, which this page does not dispute.

**Proposed:** "It does not say whether any clinician, department or reader should use these tools, and nothing here bears on whether AI-assisted colonoscopy is good for patients — the randomised evidence that AI raises detection during the procedure is not something this page disputes and is not what it examined."

**Binding for the corrected text:** judgement. Premises: S021: "a meta-analysis of 20 randomized trials showed an absolute 8.1 % increase in ADR with the use of AI during colonoscopy."; S043: "We evaluated the effect of exposure to CADe "after" CADe was removed, whereas Budzyn et al. investigated how endoscopists perform non-CADe-assisted colonoscopy "while" they were exposed to CADe in the other colonoscopies they performed during the same time period.". Step: The Polish authors cite a meta-analysis of 20 randomised trials showing an 8.1% absolute ADR increase with AI, and this page's question is unassisted performance, so the in-procedure benefit is outside its scope. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 109. afd83f74 — overstates (judgement)

**Page now:** The studies being quoted in general coverage are not the strong ones, in either direction.

**Evidence:** Held coverage shows only the alarm-side studies (MIT, Microsoft/Carnegie Mellon) being quoted; no held passage shows general coverage quoting the reassuring meta-analyses, so 'in either direction' is not established for coverage, and 'being quoted' is unscoped. The operator's correction also drops the second clause: the premises it needed (S005, the retraction) bear on a synthesis, not on what the coverage quoted.

**Proposed:** "The studies quoted in the general coverage we read are not the strong ones."

**Binding for the corrected text:** judgement. Premises: S040: "An earlier study by the Massachusetts Institute of Technology found that ChatGPT eroded critical thinking skills ."; S023: "A study from Microsoft and Carnegie Mellon University earlier this year found that among surveyed knowledge workers, AI increased work efficiency, but reduced critical engagement with content, atrophying judgment skills."; S007: "We recruited a total of 54 participants for Sessions 1, 2, 3, and 18 participants among them completed session 4."; S007: "Preprint, under review"; S019: "indicates that approximately N = 159 participants would be required for adequate power."; S008: "They were recruited through a combination of convenience and purposive sampling to ensure a diverse representation across age groups, educational backgrounds, and professional fields. The sample was promoted online in the UK on different social media platforms". Step: The studies the general coverage we read attached the colonoscopy result to (an MIT ChatGPT study in Time, a Microsoft and Carnegie Mellon survey in Fortune) are a small preprint under review (S007: 54 participants, 18 in session 4; S019: about 159 needed) and a self-selected self-report survey (S008), so neither is among the strong ones. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## 110. e99eaaf7 — overstates (a claim about readers, stated as fact) (judgement)

**Page now:** Both of those are true, and neither is what a reader takes from a review date on a page.

**Evidence:** No held passage concerns how readers interpret review dates; 'what a reader takes from a review date' is an empirical claim about readers stated as fact.

**Proposed:** "Both of those are true, and in our judgement neither is what a reader takes from a review date on a page."

**Binding for the corrected text:** WHU's own records, as a process claim: the operator's ruling of 12 September 2026 (`issues/WHU-003-deskilling/review/2026-09-12-modest-promise-ruling.md`, adjudicated as REVIEW-DATE-001 in `review/2026-09-12-review-date-adjudication.md`): “A "Last reviewed" date on a page is a currency claim — it tells a reader somebody looked recently and found nothing”; and `corrections.md`, 12 September 2026 entry: "Neither of those is what a reader takes from a review date on a page. A review date implies the page is kept current, and we cannot stand behind that." The corrected wording marks the sentence as our judgement; no held document bears on it. Not yet bound in bindings.json: no binding mechanism reads a record outside the source store (as a judgement with no premises it blocks rule 2).

## 111. 849ac2af — overstates (an unscoped superlative) (judgement)

**Page now:** The clearest evidence about what happens when the machine is wrong comes from a reading room.

**Evidence:** 'The clearest evidence' is unscoped. The premises rank the reader studies this page read (S030 against S046 and S038); they establish nothing about evidence the page did not read.

**Proposed:** "Among the studies we read, the clearest evidence about what happens when the machine is wrong comes from a reading room."

**Binding for the corrected text:** judgement. Premises: S030: "The percentage of correctly rated mammograms by inexperienced (mean, 79.7% ± 11.7 [SD] vs 19.8% ± 14.0; P < .001; r = 0.93)"; S030: "very experienced (mean, 82.3% ± 4.2 vs 45.5% ± 9.1; P = .003; r = 0.97) radiologists was significantly impacted by the correctness of the AI prediction of BI-RADS category."; S046: "However, the clinicians' errors in the AI-assisted round were associated with automation bias, accounting for 45.5% of the total mistakes."; S038: "it also resulted in a 7% automation bias rate, where initially correct evaluations were overturned by erroneous AI advice.". Step: Dratsch et al.'s reader study, in which the same radiologists' accuracy fell from about 80% to 19.8–45.5% when the AI suggestion was wrong, is the most direct measurement of the effect of erroneous AI among the studies reviewed (Wang et al. and Rosbach et al. measure smaller or differently defined effects), so the clearest evidence comes from a radiology reading room. Checks in memory on the corrected text (rule 1, rule 2, B2, B5, B6, B12, B19 incl. significance, B20, B21, B22, B23): clean.

## Bound

Batch 1 (2026-10-18): 849a833e, b61e583d, 9675c628, f2072847, a84075d9, 5850f3bd, 83bed04b,
d49da6c2. Batch 2 (2026-10-18): c8d0e2c5 (S046), 43a5da1b, 7a69a530, e2d620f3, 495cfe6a,
3da7203e, 57c41ddd, 03ea8e0e, f9eb567e, 48a03a9a, b2fff6c7, c2f8c733, 5bd6e3b7 (S046, page text
unchanged). Verdicts signed by Fred Ugast, checked against held text with Claude as advisor. Batch 3 (2026-10-18): 11147b19 (B6 disposition on "only"), f83a6cfe, ae6de87f, d250f28b, 875ef76c, 695c1c4e, 7332d1e1, b9b79e7b, fa3d6649, 0f7a7387, ff258fcb, 286c807d, 8367d5ea, ea7550a9, 8e62c8a7 and 36c83e6f (each also resting on S043's "from November 2021 to June 2025 … at three Norwegian outpatient clinics"), 086f4a02 (S046's PMC HTML rendition, which prints ±). Not bound, corrections above: a4267014, 09ba5473 and the batch-3 errors. Batch 4 (2026-10-18): ca9628d8, 27aa49d9, d9fc5473, 502fa7d2, 0172a591, cfb23438 (citation only), 156950e7, e3505b85, f75193b0, 02c52e9f, 286e6f09, 74c83102, a6e4f110, 6e60f428, 5ba6a1cf, 2da5831f, b3980490, 6e298fd2 (Table 1 linearisation doubt in why_bound), 9e43899c, 97fc07bf, 8c183fe5 (issue 6 from Crossref; 'Issue date : June 2026' held), 30a6ffe0 and b27ab3c7 (53, 436 and 41 declared as our arithmetic).

Judgements (2026-10-18), bound as judgement rows with premises and step, verdicts signed by Fred Ugast (premises read against held text by Claude Code, reviewed by Claude as advisor): faec9851, 8d3197bb, d03dd93f, af54c425, d742d3ee, 70a74bf8, 1d4c39aa, ca66d6ea, 5c684127, 98040c6f, 82f7999b, 1cfeb55b, 89556149, 9fec3c76, 4332610d, 46230167, 6b15012a, 3944e40f, 4cea8f5d, d190d0b3, 1b44f672, 22bfc8c8, 2f2fe514, c999cd40. B19 hedge dispositions recorded on 10 (c999cd40, 8d3197bb, d03dd93f, 5c684127, 1cfeb55b, 9fec3c76, 46230167, 6b15012a, 3944e40f, 4cea8f5d). B19 left as WARN on 3, because the disposition's form would be false: faec9851 (it does restate S021's hedged claim, with its own 'plausibly', which B19's sentence list does not read as a hedge); af54c425 and d742d3ee ('limited' is S029's finding, not a hedge on it, and both sentences restate it). Not bound, corrections above: the 24 judgement errors.
