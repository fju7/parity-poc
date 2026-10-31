# Check 3d: the 12 scope-note sentences, failure by failure ($0)

Advisor ruling 2026-10-31. Round-1 M1 items whose sentence or context carries WHU scope-note wording (check 3c's
list). No score is changed by this table. Judged by AI models; no human has checked the judgements; the class
column is this session's reading of each sentence against the judges' stated reasons.

Classes for a failure: **(a)** the note misstates or overstates what its cited source says (a real WHU error shown
to readers); **(b)** the cited source is the wrong one; **(c)** the sentence makes no claim about a source (a
judgement, a scope statement): a claim-definition issue. Uncited items carry the label UNCITED for both judges and
count as failures in M1.

| Item | Q | Sentence (as drawn) | Citation | Claude | OpenAI | Judge's reason for the failure | Class |
|---|---|---|---|---|---|---|---|
| M1-fbad03db81 | Q1-03 | Outside this question: "These and other improvements have also increased the estimate of global surface temperature change by approximately 0.1°C …" (IPCC AR6 WGI SPM); a footnote on measuring global surface temperature, which the question names only as the driver [1]. | [1] IPCC AR6 WGI SPM | Supported | **Absent** | OpenAI: footnote 10 supports the quotation and its description, "but the supplied document does not establish what the unspecified question names as its driver or excludes from its scope." | (c) |
| M1-df067c5f4a | Q1-03 | Outside this question: "Panel (a) For hot extremes, the evidence is mostly drawn from …" (IPCC AR6 WGI SPM); a figure caption on observed hot extremes, outside the components the question names [1]. | [1] IPCC AR6 WGI SPM | Supported | **Absent** | OpenAI: the caption is there, "but does not identify the question's named components or establish that this material falls outside its scope." | (c) |
| M1-426cada9b2 | Q1-01 | Judged not material to this question: "recommended only in specific contexts or conditions …" (WHO guideline); Judged not material [2]. | [2] WHO guideline | Supported | Supported | no failure | n/a |
| M1-5a0a9fb12d | Q1-03 | Outside this question: "C.2.6 Cities intensify human-induced warming locally …" (IPCC AR6 WGI SPM); a finding on urban heat and heatwaves, outside the components the question names [1]. | [1] IPCC AR6 WGI SPM | reply said Supported, **unparseable**; counted **Absent** (OpenAI's label, by the refusal-fill rule) | **Absent** | OpenAI: C.2.6 supports the quoted finding, "but the supplied text does not establish that it falls outside the components named in the unspecified question." Claude's reply: "quotes … C.2.6 verbatim … and correctly describes it" (not counted; see Arithmetic). | (c) |
| M1-5b2799906b | Q1-02 | Judged not material to this question: "Authors: Hannah Kuper, Ashrita Saran, and Howard White …" (Rapid Evidence Assessment …); Judged not material [2]. | [2] REA full report | Supported | Supported | no failure | n/a |
| M1-7f780fc97b | Q1-03 | Outside this question: "Across most regions, observed and simulated patterns are consistent." (IPCC AR6 WGI SPM); a figure caption on regional temperature change, which the question names only as the driver [1]. | [1] IPCC AR6 WGI SPM | Supported | **Absent** | OpenAI: Figure SPM.5 has the quotation, "but the document does not establish that this is outside the question." | (c) |
| M1-43cf27c16c | Q1-03 | Judged not material to this question: "Mountain and polar glaciers are committed to continue melting …" (IPCC AR6 WGI SPM); already stated [1]. | [1] IPCC AR6 WGI SPM | Supported | Supported | no failure | n/a |
| M1-465ab812be | Q1-01 | We did not read the 18 included studies themselves, and we did not search for studies published after November 2022. | none | UNCITED | UNCITED | uncited (counted as a failure, not judged) | (c) |
| M1-bbeb3b2720 | Q1-02 | We did not obtain a 2020 correction to the evidence and gap map, because its publisher's terms do not allow our tools to read it. | none | UNCITED | UNCITED | uncited | (c) |
| M1-07cdf12d9c | Q1-04 | Judged not material to this question: "This pre-final-publication version of the AR6 WGIII SPM approved text is subject to error correction …" (IPCC AR6 WGIII SPM); figure caption and the draft-version footer joined to C.3.6 by the PDF text layer, not a finding. | none (source named in parentheses, no [n]) | UNCITED | UNCITED | uncited | (c) |
| M1-19544dcfc0 | Q1-04 | Outside this question: "For example, measures for the mitigation of agricultural CH4 and N2O emissions with emerging technologies show promising results." (IPCC AR6 WGIII SPM); about cutting agricultural methane and nitrous oxide emissions, not about removing carbon dioxide. | none (source named in parentheses, no [n]) | UNCITED | UNCITED | uncited | (c) |
| M1-42cf916f68 | Q1-04 | Judged not material to this question: "SPM 2 3 4 5 … Chapter source Sections 6.4.2, 6.7.7 Carbon sequestration in agriculture …" (IPCC AR6 WGIII SPM); table text (a list of options and chapter sources), not a finding. | none (source named in parentheses, no [n]) | UNCITED | UNCITED | uncited | (c) |

## Arithmetic: each item's contribution as the code computes it

`validity_analysis.scores(m1, "M1_failure", combined)` gives each item the mean of A.score over the two judges'
counted labels (`analyse.per_judge_labels`, after the refusal rule), failure 1, pass 0.

| Item | Counted labels (Claude, OpenAI) | Contribution |
|---|---|---|
| M1-07cdf12d9c | UNCITED, UNCITED | 1.0 |
| M1-19544dcfc0 | UNCITED, UNCITED | 1.0 |
| M1-42cf916f68 | UNCITED, UNCITED | 1.0 |
| M1-465ab812be | UNCITED, UNCITED | 1.0 |
| M1-bbeb3b2720 | UNCITED, UNCITED | 1.0 |
| M1-5a0a9fb12d | **Absent, Absent** | **1.0** |
| M1-7f780fc97b | Supported, Absent | 0.5 |
| M1-df067c5f4a | Supported, Absent | 0.5 |
| M1-fbad03db81 | Supported, Absent | 0.5 |
| M1-426cada9b2 | Supported, Supported | 0.0 |
| M1-43cf27c16c | Supported, Supported | 0.0 |
| M1-5b2799906b | Supported, Supported | 0.0 |
| **Total** | | **7.5** (of WHU's 9.5 on 79 countable) |

**Cause of the 7.5 vs 7.0 gap: M1-5a0a9fb12d counts 1.0, not 0.5.** Claude's reply to it said "Supported", but its
span carried a raw tab character ("C.2.6\tCities …"), which strict JSON parsing rejects ("Invalid control character";
the record's form_problems: "text around the JSON", "not JSON"). The reply was therefore unusable, its label null, and
`analyse.per_judge_labels` applies the refusal rule to an unusable reply as to a refusal: the item "takes the other
judge's label", so Claude's slot counts OpenAI's Absent. **The wrong statement was this report's first version**: it
showed Claude's column as "no label", said "OpenAI's Absent counts 1.0" because Claude gave no label (in fact the code
fills Claude's slot with OpenAI's label), and said "Claude passed all four" (Claude's reply passed this one, but it was
not counted). The advisor's 4 x 0.5 assumed one failing judge of two on every judged item, which the code does not do
for this item.

This is the only round-1 M1 reply with text but no parsed label. Parsed leniently (raw control characters allowed),
it reads Supported; the item would then count 0.5, WHU's M1 failures 9.0 of 79 (11.4%) instead of 9.5 (12.0%). **No
score is changed**: the as-scored rule stands; this is reported as a parser defect (strict JSON on a reply whose
quoted span carries a tab), not corrected.

## Counts

- 12 items: 7 cited and judged, 5 uncited.
- **No failure on 3** (both judges Supported).
- **Failures on 9 items, 7.5 failure points** in the as-scored two-judge count: 3 judged items at 0.5 (OpenAI Absent,
  Claude Supported), M1-5a0a9fb12d at 1.0 (OpenAI Absent, Claude's unparseable reply filled with OpenAI's label), and
  5 uncited at 1.0. See Arithmetic above.
- **(a) 0. (b) 0. (c) 9.**
  - On the 4 judged failures, every OpenAI reason accepts the quotation and its description and fails the sentence
    on the scope judgement ("does not establish that it falls outside the question"), which no source can support.
    Claude passed three of the four, reading the scope wording as WHU's own framing; its reply on the fourth
    (M1-5a0a9fb12d) also said Supported but was unparseable and counted as Absent.
  - The 5 uncited items are WHU's method statements (2) and Q1-04 scope notes that name their source in parentheses
    with no [n] marker (3). None claims anything about a source's content.

Observation, not a class: Q1-04's scope notes name the source in parentheses without a citation marker, where Q1-01
to Q1-03's carry one. That inconsistency is why three Q1-04 notes were drawn as uncited. It is a presentation
point, not an (a) or (b) error; the advisor put it on the post-round fixes list (below).

Post-round WHU fixes list (advisor ruling 2026-10-31, recorded in `quarterly/round1_deviations.md`): "Q1-04 scope
notes name their source in brackets but carry no [n] citation marker (Q1-01 to Q1-03 do): a rendering inconsistency
shown to readers." No class (a) or (b) item.
