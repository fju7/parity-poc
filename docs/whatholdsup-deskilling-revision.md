# Deskilling — pending page corrections for the republish

Issue: `issues/WHU-003-deskilling/`; page: `site/whatholdsup/deskilling.html` (live at
whatholdsup.org/deskilling, unchanged since 30 August). Opened 2026-10-18 from binding
batch 1. Nothing here is on the page yet: each correction goes out through `publish.py`
with the republish, with a `corrections.md` entry. Proposed wording is the operator's
unless marked otherwise. Rows are binding-row shas in `bindings.json`.

## Errors found in the published page

Six confirmed in batch 1 (19 rows read against held text):

| | count | rows |
|---|---|---|
| overstates the source | 4 | 32db25e0, 509b18f6, b8844660, ad3f7c73 |
| misstates how the source was read | 1 | the Wang paragraph (c8d0e2c5, 5bd6e3b7, b8844660 rest on it) |
| misattributes | 1 | 26e94905 |
| understates the source | 0 | |

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

## 4. ad3f7c73 — Decker and the Nature Reviews highlight (wording pending)

**Page now, with the two sentences it depends on (verbatim, in order):**

> Fortune , 26 August 2025 Carries the six-point fall to a business readership, connects it to a Microsoft and Carnegie Mellon survey and to an aviation analogy, and reports none of the study’s eleven limitations.
> Cited here as an instance, not for any figure.
> The same is true of the research highlight in Nature Reviews Gastroenterology & Hepatology of 5 September 2025 and of Decker J, “When AI Reads the Easy Cases”, Rad Insights, 15 May 2026 — which pairs the colonoscopy and mammography results and is the closest published thing to this page.

**Problem:** "The same is true of" carries the Fortune sentence's claim — that the piece
"reports none of the study's eleven limitations" — over to Decker and to the Nature
Reviews highlight. Decker (S034, full_text_held) names the design: "Budzyń and colleagues
published a multicentre observational study…", the limitation the page credits The ASCO
Post with reporting ("its observational nature"). The Nature Reviews highlight (S027) is
fragment_only, so nothing held supports its half of the sentence.

**Proposed:** to be decided after the S027 fetch attempt.

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

**Proposed:** resolution pending a Wang fetch attempt — either Wang is acquired, entered
in the ledger and these rows bound to it, or the paragraph stops claiming a reading at
source and the rows are attributed to the review.

## 6. S005 not linked in the source list

S005 (Ingebrigtsen & Lukic audit, PsyArXiv, osf.io/wgu56) is not linked in the page's
source list; a84075d9 and 5850f3bd rest on it. Republish must add the link. (The audit is
named only inside the note of the *Retraction Note* entry, whose link is nature.com.)

Binding those two rows raised a new preflight block, "every document the piece rests on is
in the list a reader sees" (S005). It is accepted on the same basis as the S033/S034/S045
block of 52f2205: the records are ahead of the page, and it clears at republish.

## 7. Unbound until a source is held

Not page errors: the held document that "matched" each is a coincidence of digits, so
they stay unbound.

| row | page sentence | needs |
|---|---|---|
| 43a5da1b | The more specific problem is that AI use, cognitive offloading and critical thinking were all three measured by self-report in the same instrument, and the three correlations among them are uniformly strong — −0.68, +0.72 and −0.75. | S008 (Gerlich), fragment_only |
| 34b99db8 | Societies 2025;15(1):6 Source of the 666 valid responses of 669, the recruitment through social media in the United Kingdom, the cross-sectional design, and the three correlations of −0.68, +0.72 and −0.75. | S008 |
| bd8b242c | Access to it raised their confidence by 11.7 percentage points while about half its answers were faulty — and their confidence did not fall as they met more wrong answers. | S017 (Shaw & Nave), fragment_only |
| 8598e9ca | arXiv 2601.00856 Their closing sentence — that there is no strong evidence the tool use negatively affects performance itself — is a verdict on the paper they audited, not on the field. | S019's PDF (only the arXiv abstract page is held) |

## Bound in batch 1

Confirmed 2026-10-18 (verdicts signed by Fred Ugast, checked against held text with
Claude as advisor): 849a833e, b61e583d, 9675c628, f2072847, a84075d9, 5850f3bd, 83bed04b,
d49da6c2. Full proposals, spans and checks: the batch-1 review of 18 October.
