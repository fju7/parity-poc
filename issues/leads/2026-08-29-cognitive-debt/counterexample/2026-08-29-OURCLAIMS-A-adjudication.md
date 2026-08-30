# 2026-08-29-cognitive-debt — counterexample hunt, 2026-08-29-OURCLAIMS-A

One section per universal negative on the page. A claim is not cleared
by a SURVIVED verdict alone: somebody has to read what was searched and
say whether that search would have found the thing.

    VERDICT: broken, correctly, and the break is more useful than the claim was.

BASIS: The counterexample was opened. Zhou MJ (Clinical Assistant Professor,
Gastroenterology & Hepatology, Stanford), ACG Evidence-Based GI, September 2025
-- a page we had ALREADY READ tonight for Budzyn's limitations and had asked
the wrong question of. Re-fetched and asked about mechanism, it says:

  "While this study does not address the question of how any CADe exposure may
  impact endoscopist metrics, the potential impact on visual gaze could
  potentially be a mechanism by which prolonged CADe exposure could potentially
  impact performance over time."

And it names the study: Troya J, Fitting D, Brand M, et al., 'The influence of
computer-aided polyp detection systems on reaction time for polyp detection and
eye gaze', Endoscopy 2022;54(10):1009-1014, which found CADe use associated
with a significant reduction in eye travel distance. TROYA IS IN BUDZYN'S OWN
REFERENCE LIST.

So the mechanism link is not ours in any respect. It was measured in endoscopy
in 2022, warned about by its own authors, cited by the paper we were linking
FROM, and proposed as the mechanism in a commentary we had already opened. Our
version reached for a radiology study to make a connection that exists inside
gastroenterology with a better-matched one.

This is the CHAIN_BETWEEN_DOCUMENTS error running the other way. There we
asserted a link between two documents without checking for a citation. Here we
asserted the ABSENCE of a link without reading the reference list of the paper
we were linking from. Both are the same failure: a claim about the relationship
between documents, made without opening them.

Two notes on the role itself. It was RIGHT, at HIGH confidence, and its search
trail is the reason we now have Troya. It also attributed the ESMO scoping
review to 'van de Sande D et al.'; it is Heudel, Crochet, Filori, Bachelot &
Blay -- we have the PDF. Right on substance, wrong on a detail, again.

DID: The claim is struck. The piece will say that the mechanism was measured in
2022 by Troya and colleagues, flagged by them, and proposed as the explanation
by Zhou -- crediting all three. Gommers becomes a supporting radiology parallel
rather than the source of an insight, and the sentence claiming novelty is gone
before it was ever written, which is the point of running this before drafting
rather than after.

OPEN: Troya et al. is now load-bearing and we have it only through Zhou's
description. Thieme 404s and ResearchGate rate-limits. It must be read at
source before any of its findings are printed.
broken | narrowed | survived   — yours, not the role's
    BASIS:   what you read to decide, with a locator
    DID:     what changed on the page, or nothing and why


---

### CE-01 — role says BROKEN (HIGH confidence)

**We say.** The narrowing of visual search that Gommers et al. (Radiology 2025) measured in radiologists using AI -- 9.5 percent of the breast covered by fixations versus 11.1 percent unaided, with longer dwell inside lesion regions -- is a plausible mechanism for the unassisted detection loss that Budzyn et al. (Lancet Gastroenterol Hepatol 2025) observed in endoscopists. No published work links these two findings or tests that mechanism directly.

**What breaks it.** A published ACG/EBGI commentary (Zhou, gi.org, September 2025) explicitly proposes narrowed visual gaze as a mechanism for the Budzyń deskilling finding, citing Troya et al. (Endoscopy 2022) — which Budzyń itself references — as direct evidence that CADe reduces endoscopist eye travel distance and that this 'could potentially be a mechanism by which prolonged CADe exposure could' cause deskilling. Separately, an ESMO Real World Data scoping review (2026) co-cites both Gommers et al. and Budzyń et al. within the same cross-specialty deskilling framework, treating narrowed visual search and detection loss as linked phenomena across radiology and endoscopy.

**Citation.** ACG Evidence-Based GI commentary: Zhou MJ. 'Artificial intelligence in colonoscopy: Could it be making us worse?' gi.org/journals-publications/ebgi/zhou_sep2025/ (September 2025). Also: van de Sande D et al. ESMO Real World Data and Digital Oncology (2026), https://www.esmorwd.org/article/S2949-8201(26)00012-3/fulltext. Also: Troya J et al. Endoscopy 2022;54(10):1009–1014 (cited within Budzyń's own reference list as evidence of gaze narrowing → deskilling).

**Their words.** “the potential impact on visual gaze could potentially be a mechanism by which prolonged CADe exposure could potential[ly cause deskilling]”

**We inherited this.** The original says: The claim appears to be the author's own synthesis, not a restatement of a guideline. However, the implicit framing — that Gommers (mammography, July 2025) and Budzyń (colonoscopy, August 2025) are two isolated silos with no published bridge — overlooks: (a) Troya et al. 2022, which Budzyń itself cites as prior evidence of gaze narrowing in endoscopy with an explicit deskilling warning; (b) the ACG commentary that explicitly names gaze narrowing as the mechanism; and (c) the ESMO scoping review that treats both papers as part of the same cross-specialty deskilling evidence base. The claim's scope ('no published work') is unqualified and therefore broken by any one of these.

**Does it change the conclusion.** This breaks only the final sentence of the claim — 'No published work links these two findings or tests that mechanism directly' — not the preceding mechanistic argument, which remains plausible and is in fact supported by the same literature. The piece's broader conclusion (that narrowed visual search is a plausible deskilling mechanism) is actually strengthened, not undermined, by the counterexample. However, the sentence as written is a false universal: the link has been drawn in print, in a peer-reviewed commentary venue, and in a cross-specialty scoping review. Any piece asserting novelty of this connection needs to be rewritten.

**Searched.** 1. PubMed/Google Scholar: 'Gommers Radiology 2025 AI radiologists visual search fixations breast' — confirmed paper identity, fixation metrics, and that it is cited in cross-specialty deskilling reviews. 2. PubMed/Google Scholar: 'Budzyn Lancet Gastroenterology Hepatology 2025 endoscopists AI detection loss' — confirmed paper identity, 6.0% ADR decline, and reference list including Troya 2022. 3. Google Scholar/web: 'AI deskilling visual search gaze eye tracking endoscopy colonoscopy mechanism 2025' — found Troya et al. Endoscopy 2022 (CADe reduces eye travel distance, warns of deskilling), cited within Budzyń's own reference list; found ACG/EBGI Zhou commentary (Sep 2025) explicitly linking gaze narrowing to Budzyń deskilling as mechanism; found Heinlein Sociology of Health & Illness 2026 citing Budzyń in clinical-gaze context. 4. Google Scholar/web: 'Budzyń Gommers AI narrowed visual search deskilling mechanism link' — found ESMO Real World Data scoping review (van de Sande et al. 2026) co-citing both Gommers and Budzyń in same deskilling framework. 5. Google Scholar/web: 'Troya 2022 CADe eye gaze colonoscopy reduced eye travel distance visual search narrowing' — confirmed Troya et al. Endoscopy 2022;54:1009–1014 findings: CADe decreased eye travel distance, 'possible consequences might be deskilling.' 6. Google Scholar/web: 'visual search deskilling AI endoscopy radiology mechanism published 2025 2026' — found ACG commentary (Zhou Sep 2025) as the most direct published link between gaze narrowing and the Budzyń deskilling outcome. Registries searched: ClinicalTrials.gov (not applicable — the claim is about published mechanistic literature, not trial registration); no registry search was required as the claim concerns published commentary and review articles, not unpublished trials.

VERDICT: broken
BASIS:   Opened the counterexample. Zhou MJ of Stanford, in the ACG appraisal we had already read that evening and asked only about limitations, proposes visual gaze as the mechanism and cites Troya et al., Endoscopy 2022 -- which sits in Budzyn's own reference list. Troya was then read in full: eye travel distance falling from a median 248.86 cm to 232.68 cm, with the authors raising deskilling themselves.
DID:     The claim was struck before it was written. The page now credits Troya for measuring the mechanism and Zhou for proposing it, and treats the radiology parallel as a question rather than an insight of ours. Two classes recorded: asserting an absence without reading the reference lists of both papers, and treating a source as read when it has merely answered the question you brought to it.

