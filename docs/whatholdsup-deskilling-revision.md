# Deskilling — pending page corrections for the republish

Issue: `issues/WHU-003-deskilling/`; page: `site/whatholdsup/deskilling.html` (live at
whatholdsup.org/deskilling, unchanged since 30 August). Opened 2026-10-18 from binding
batch 1. Nothing here is on the page yet: each correction goes out through `publish.py`
with the republish, with a `corrections.md` entry. Proposed wording is the operator's
unless marked otherwise. Rows are binding-row shas in `bindings.json`.

## Errors found in the published page

Ten confirmed across batches 1 and 2 (read against held text, 18 October 2026):

| | count | rows |
|---|---|---|
| overstates the source | 5 | 32db25e0, 509b18f6, b8844660, bd8b242c, ad3f7c73 |
| misattributes or misdescribes | 3 | 26e94905, 8598e9ca, 34b99db8 |
| misstates how a source was read | 1 | the Wang paragraph (c8d0e2c5, 5bd6e3b7, b8844660 rest on it) — now true once those rows bind to S046 |
| misquotes | 1 | Q-25 |
| understates the source | 0 | |

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

## Bound

Batch 1 (2026-10-18): 849a833e, b61e583d, 9675c628, f2072847, a84075d9, 5850f3bd, 83bed04b,
d49da6c2. Batch 2 (2026-10-18): c8d0e2c5 (S046), 43a5da1b, 7a69a530, e2d620f3, 495cfe6a,
3da7203e, 57c41ddd, 03ea8e0e, f9eb567e, 48a03a9a, b2fff6c7, c2f8c733, 5bd6e3b7 (S046, page text
unchanged). Verdicts signed by Fred Ugast, checked against held text with Claude as advisor.
