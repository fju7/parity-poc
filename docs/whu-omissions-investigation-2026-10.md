# Why WHU understated or left out key conclusions (reliability study, S01–S08)

Read-only investigation, 27 October 2026, by Claude Code. Nothing was run that calls a model; no code or issue record was changed. This file is the only thing committed.

**What was read.** `CLAUDE.md`; `study/whu-reliability/RUN.md`; `study/whu-reliability/deviations.md`; each issue's `study_log.md`, `issue.json`, `premise.json` and `sources.json`; each issue's `rulings/rulings.jsonl`, `audit/<run>/rulings.jsonl` and `audit/<run>/cuts.jsonl`; the step-3b commit of each page against the final page; the M2 judge replies in `~/Projects/whu-study-private/scoring/m2/replies/` (S01–S04) and `replies_ext/` (S05–S08), with `key_map.json` to find the WHU answers; the ruling prompt `backend/scripts/whatholdsup/audit_prompts/rule_group.md` (sha256 `68a0fd06…`) and the advocate brief in `source_advocate.py`. The scored WHU answers were checked to carry the final pages' text (one distinctive final-page sentence per issue found in each answer file).

**Quotation rule.** WHU page text and ruling text (the replacement wording a ruling put on the page) are quoted. Judges' stated reasons are quoted, as the brief asks. Source documents, answer-key quotations and the other tools' answers are not quoted. Ruling *reasons* and advocate findings, which quote the sources, are paraphrased.

**Note for the reader.** This file states the answer key's conclusions in paraphrase and quotes the M2 judges' reasons. Until now the repository held only counts for M2. It is written here because the brief asked for it.

---

## 1. The items

Thirteen WHU items were labelled Understates or Omits by at least one judge: 12 labels from the Claude judge and 11 from the OpenAI judge, which matches the brief. The source is each judge's reply file, field `label` (all `human_review: false`). S02 and S04 have none.

| # | Item | Key conclusion (paraphrased) | Claude | OpenAI |
|---|---|---|---|---|
| 1 | WHU-S01-C1 | Ultra vs smear: little to no difference in all-cause deaths at 6 and 18 months (high certainty) | Matches | **Understates** |
| 2 | WHU-S01-C2 | A strategy with Ultra probably shortens time to diagnosis (moderate certainty) | **Omits** | **Omits** |
| 3 | WHU-S01-C4 | Ultra slightly increases loss to follow-up (high certainty) | **Understates** | Matches |
| 4 | WHU-S03-C1 | How broadly diverse actors are engaged influences political support and policy outcomes (IPCC WGIII, medium confidence) | **Understates** | **Understates** |
| 5 | WHU-S05-C5 | Undernutrition may raise the risk of TB coming back after treatment (two studies) | **Omits** | **Omits** |
| 6 | WHU-S06-C5 | Conditions that may help arts programmes engage young people, and barriers (very low confidence) | **Omits** | **Omits** |
| 7 | WHU-S07-C2 | Investment in public transport and walking and cycling infrastructure can further support mode shift (IPCC, high confidence) | **Omits** | Matches |
| 8 | WHU-S07-C3 | Teleworking, digitalisation and similar systemic changes may reduce transport demand (IPCC, high confidence) | **Omits** | **Omits** |
| 9 | WHU-S07-C4 | Some of those changes could induce demand and reduce the cut (IPCC, medium confidence) | **Omits** | **Omits** |
| 10 | WHU-S08-C1 | Considering climate risk in settlement and infrastructure planning is critical for resilience and well-being (IPCC WGII SPM C.2.6, high confidence) | **Understates** | **Understates** |
| 11 | WHU-S08-C2 | Basic services, infrastructure, livelihoods, food systems and community-based adaptation improve lives, especially for low-income and marginalised groups (high confidence) | **Understates** | **Understates** |
| 12 | WHU-S08-C3 | Inclusive, integrated, long-term planning, with regulation, monitoring and resources, fosters system transition (high confidence) | **Understates** | **Understates** |
| 13 | WHU-S08-C4 | Effective partnerships across government, civil society and the private sector strengthen vulnerable people's adaptive capacity (medium to high confidence) | **Omits** | **Omits** |

### The judges' stated reasons

- **S01-C1, OpenAI (Understates)** `replies/openai/M2-7c4ebf8e9c.json`: "The answer is inconsistent: it accurately reports the Ultra-specific high-certainty finding, but its overarching and closing framing presents overall mortality effects as inconclusive rather than preserving the review's high-certainty conclusion of little to no difference for Ultra versus smear microscopy in adults."
- **S01-C2, Claude (Omits)** `replies/claude/M2-7ff37c4640.json`: "The answer reports the 2025 review's moderate-certainty finding on time to treatment (GMR 0.35, HR 3.00) but never mentions the separate finding that Xpert Ultra probably shortens time to diagnosis (GMR 0.49)."
- **S01-C2, OpenAI (Omits)** `replies/openai/M2-7ff37c4640.json`: "The answer discusses more confirmed diagnoses and shorter time to treatment, but takes no position on whether Xpert MTB/RIF Ultra shortens time to TB diagnosis, the distinct outcome covered by this conclusion."
- **S01-C4, Claude (Understates)** `replies/claude/M2-5eca8d8272.json`: "The direction and percentages match, but the answer leaves out the review's high-certainty grading and risk ratio and presents the finding as a passing aside, while its closing summary stresses 'probably fewer confirmed patients lost before treatment' (from the original Xpert review), so a reader comes away weighting this harm less than the review does."
- **S03-C1, Claude (Understates)** `replies/claude/M2-d5229417c0.json`: "The review holds with medium confidence that how broadly diverse actors are engaged influences both political support and policy outcomes, whereas the answer narrows this to citizens' assemblies, explicitly excludes businesses, workers, youth and Indigenous groups, and presents the effect on political support as not shown."
- **S03-C1, OpenAI (Understates)** `replies/openai/M2-d5229417c0.json`: "The answer offers a narrower, more tentative conclusion focused on European citizens' assemblies, rather than the review's medium-confidence finding that engagement across diverse actor groups influences political support and policy outcomes, without specifying a uniformly positive direction."
- **S05-C5, Claude (Omits)** `replies_ext/claude/M2-b9d4da744f.json`: "The answer covers only incident TB disease and never mentions TB recurrence after treatment, so it takes no position on the review's finding about recurrent TB."
- **S05-C5, OpenAI (Omits)** `replies_ext/openai/M2-b9d4da744f.json`: "The answer discusses developing TB disease and preventing incident cases, but takes no position on whether undernutrition increases TB recurrence after treatment."
- **S06-C5, Claude (Omits)** `replies_ext/claude/M2-cfa4d89663.json`: "The answer only says the review offers very-low-confidence 'pointers on what helps programs work'. It never states what those facilitators are (accessible, flexible delivery; support from staff, family and community; professional artists; cultural relevance; regularity) or the barriers (lack of advocacy, low funding), so it takes no position on this conclusion."
- **S06-C5, OpenAI (Omits)** `replies_ext/openai/M2-cfa4d89663.json`: "The answer mentions very-low-confidence pointers on program delivery but does not state any of the review's proposed conditions for engagement or barriers to successful delivery."
- **S07-C2, Claude (Omits)** `replies_ext/claude/M2-e67f0f8f54.json`: "The answer mentions transit only as one part of bundled urban-form packages (e.g., 'significant public transit improvements' alongside density and mixed uses). It never states a position on whether investing in public transport or walking and cycling infrastructure supports mode shift, nor gives the 2–10% active-mobility estimate."
- **S07-C3, Claude (Omits)** `replies_ext/claude/M2-6b035ff059.json`: "The answer never addresses teleworking, digitalisation, dematerialisation, supply chain management or smart/shared mobility as ways to reduce transport demand, so it takes no position on this conclusion."
- **S07-C3, OpenAI (Omits)** `replies_ext/openai/M2-6b035ff059.json`: "The answer discusses urban form and transport pricing but takes no position on whether teleworking, digitalisation, dematerialisation, supply chain management, or smart and shared mobility reduce passenger and freight transport demand."
- **S07-C4, Claude (Omits)** `replies_ext/claude/M2-19ae7989e8.json`: "The answer never discusses induced demand or rebound effects that could reduce the emission cuts from these changes; its note that driving rises slightly in areas that lose population is a displacement effect within one study, not a position on induced demand."
- **S07-C4, OpenAI (Omits)** `replies_ext/openai/M2-19ae7989e8.json`: "The answer discusses limits on emissions savings but does not address whether induced demand or rebound effects could reduce those savings."
- **S08-C1, Claude (Understates)** `replies_ext/claude/M2-8d302bfbc8.json`: "The review judges with high confidence that considering climate risk in settlement and infrastructure planning is critical for resilience and well-being, while the answer presents the benefit as 'not proven, not disproven: mostly unmeasured' and gives no comparable high-confidence endorsement of climate-informed planning."
- **S08-C1, OpenAI (Understates)** `replies_ext/openai/M2-8d302bfbc8.json`: "Although it acknowledges some planning benefits, the answer's overall framing makes the contribution to resilience and well-being uncertain, weakening the review's high-confidence judgement that considering climate risks in settlement and infrastructure planning is critical, even without a measured effect size."
- **S08-C2, Claude (Understates)** `replies_ext/claude/M2-5853f0e5e2.json`: "The review states with high confidence that basic services, infrastructure, food systems and community-based adaptation enhance lives and livelihoods, especially of low-income and marginalised groups, whereas the answer calls evidence that adaptation leaves people better off thin, 'some evidence' at most, and 'not proven, not disproven: mostly unmeasured'."
- **S08-C2, OpenAI (Understates)** `replies_ext/openai/M2-5853f0e5e2.json`: "Read as a whole, the answer presents adaptation's benefits to people as largely uncertain or unmeasured, rather than conveying the review's high-confidence finding that the specified services, infrastructure, livelihood and community-based measures improve lives and livelihoods, especially for low-income and marginalised groups."
- **S08-C3, Claude (Understates)** `replies_ext/claude/M2-b4b0d10fa4.json`: "The answer does report, with high confidence, that zoning combined with other planning measures works better, but its overall verdict on climate-informed planning is 'not proven, not disproven: mostly unmeasured', which is weaker than the review's high-confidence finding that inclusive, integrated, long-term planning with regulation, monitoring and resources fosters system transition."
- **S08-C3, OpenAI (Understates)** `replies_ext/openai/M2-b4b0d10fa4.json`: "Despite inconsistently acknowledging high-confidence benefits of combined planning measures, the answer's overall framing presents planning effectiveness as largely unmeasured and narrowly supported, weakening the review's high-confidence conclusion that inclusive, integrated, long-term planning helps urban and rural transitions under the listed enabling conditions."
- **S08-C4, Claude (Omits)** `replies_ext/claude/M2-82a711be3f.json`: "The answer discusses zoning, governance systems, community-based adaptation and flood insurance, but never takes a position on whether partnerships between governments, civil society and the private sector strengthen the adaptive capacity of vulnerable people."
- **S08-C4, OpenAI (Omits)** `replies_ext/openai/M2-82a711be3f.json`: "The answer does not address whether effective cross-scale partnerships among governments, civil society and the private sector strengthen vulnerable people's adaptive capacity through infrastructure and services."

---

## 2. Cause of each item

Codes: (a) evidence not held or not read; (b) in the first draft but removed or weakened by a ruling, audit, cut or conclusion-judge amendment; (c) question or premise narrowed, so the conclusion fell out of scope; (d) a hedging or calibration rule pushed the wording below the source; (e) possible answer-key dispute; (f) other.

Within (f), every case here is the same thing, so it is named once: **(f) drafting omission.** The source was held and read, and the point is in scope, but the step-3 draft left it out (or reported it without its grade). No later stage put it back. Where the source advocate raised the point, the ruling model rejected it (see §4).

"First draft" is the step-3b commit: S01 `9b481d3`, S03 `c8bec0f`, S05 `e884c2d`, S06 `7615c61`, S07 `c57fb04`, S08 `790f830`. "Final" is the page on `main` at `7ed5006`.

### 1. WHU-S01-C1: (b) weakened by advocate rulings

- **Source held?** Yes. S001 (Otieno 2025 Cochrane), `full_text_held`.
- **First draft.** The Ultra sentence was already present: "For the newer Xpert MTB/RIF Ultra test, a 2025 Cochrane review found that the test made little to no difference to deaths from any cause at six months (risk ratio 0.79, 0.61 to 1.01) or at 18 months (adjusted rate ratio 0.77, 0.46 to 1.29)." The closing read: "They do not show that the test by itself reduces deaths among everyone tested, though in people with HIV deaths were probably reduced."
- **What changed it.**
  - Advocate ruling `78ec04f65ce78d78` (`rulings/rulings.jsonl:7`, step 4b, applied at 4c) changed the closing to "They could not confidently rule in or rule out an effect of the test on deaths among everyone tested, though in people with HIV deaths were probably reduced." The ruling adopted the 2021 review's *inconclusive* framing for the original Xpert test. It is now the page's closing statement for all testing, which includes the Ultra result rated high-certainty little-to-no-difference.
  - Advocate ruling `41357058d569c59b` (`:12`) added "The trials have given inconclusive evidence on overall mortality, and the review could not assess outcomes specific to drug-resistant TB."
  - Meanwhile ruling `66446f794dfc5409` (`:2`) *strengthened* the Ultra sentence to "…found high-certainty evidence from one trial that using it instead of smear microscopy made little to no difference…". This creates the inconsistency the OpenAI judge names.
- **Also.** On the standfirst, ruling `113afb6f93eaac5f` (`:1`) rejected an advocate objection (finding 3, SERIOUS) that "have not shown that it saves lives" understates a high-certainty null.
- **Unsure.** Only one judge flagged this (Claude: Matches). The page's sentence 19 states the key conclusion correctly. The weakening is to the synthesis lines only.

### 2. WHU-S01-C2: (f) drafting omission

- **Source held?** Yes. Time to diagnosis is a Summary-of-findings outcome of S001, held in full.
- **First and final drafts.** Neither mentions time to diagnosis. Both report only time to treatment. The first draft said "probably reduces the time to treatment, with an adjusted geometric mean ratio of 0.35 (0.21 to 0.58) in one trial". Ruling `9146db191242e6d4` (`:5`) amended that to the two-trial wording, still about treatment only.
- **Advocate.** An advocate finding on the standfirst (S001-01, ruled in `113afb6f93eaac5f`, `:1`) noted in passing that the review reports time to diagnosis. But it was framed as an objection to "confirmed diagnosis", and it was rejected on that point. No stage asked for the missing outcome to be added.

### 3. WHU-S01-C4: (f) drafting omission (grade and effect measure left out)

- **First and final drafts.** Unchanged in both: "The 2025 review also reported that slightly more people were lost to follow-up in XPEL-TB's Xpert Ultra arm (13.6%) than with smear microscopy (10.1%)." The sentence has no certainty grade and no risk ratio.
- **Closing line.** The closing synthesis (ruling `399fab9c1ea84ab0`, `:9`) keeps "probably fewer confirmed patients lost before treatment". That finding comes from the 2021 review, so the closing weights the older finding over this one.
- **Rulings.** No ruling touched sentence 34.
- **Unsure.** One judge only (OpenAI: Matches).

### 4. WHU-S03-C1: (a) evidence not held or not read — *unsure; (c) is close*

- **Not held.** The key's statement comes from the WGIII Summary for Policymakers. WHU did not hold the SPM.
- **Held but not drawn on.** WHU held Chapter 13 in full (S006, 617,783 characters), and its executive summary has a related, broader statement about the range of actors shaping climate governance. The page draws on two other Chapter 13 sentences only (legitimacy of assemblies; few case studies measuring direct effects). The other held sources (S001–S005) are all citizens'-assembly or deliberation studies.
- **First draft.** It already stated the gap: "The evidence comes from citizens' assemblies in Europe; none of the sources held here studies the involvement of businesses, workers, young people or Indigenous communities as distinct groups." Advocate ruling `rulings.jsonl:20` kept the limit and reworded it: "…none of the sources held here studies businesses, workers, young people or Indigenous communities as distinct groups."
- **No ruling removed this.** The question (`issue.json`) names all those groups, so it was not narrowed. The research stage chose sources that could not answer for them.
- **Related calibration change (not this item).** Audit `20261023T011327Z` ruling 3 removed "with medium evidence and high agreement" from the page's Chapter 13 justice sentence. The advocate ruling (`rulings.jsonl:26`) had kept it. The audit ruled that the tag did not belong to that sentence because of how the paragraph is laid out in the PDF. Two rulings on one IPCC calibration tag disagreed, and the later one stripped it.

### 5. WHU-S05-C5: (c) the question's scope — *unsure; (e) possible*

- **The question.** `issue.json` asks whether undernourished people are "more likely to go on to develop TB disease". That is incident disease. The study wrote the question from the review's stated objective. No WHU stage narrowed it.
- **The drafts.** Recurrence after treatment is a secondary outcome of the review (S001, held in full). It appears in neither draft. No ruling or audit record raises it as an omission. The one ruling whose inputs mention recurrence (`rulings.jsonl:2`) rules on other findings.
- **Classification.** (c), with the narrowing sitting in the question wording rather than in WHU's premise. If the protocol treats the key as covering everything in the review rather than the question, this is closer to (e).

### 6. WHU-S06-C5: (c) the question's scope — *unsure; (e) possible*

- **The question.** It asks whether arts programmes "reduce offending or improve their behaviour and wellbeing", which is outcomes. The key's own scope note says this conclusion is about conditions for engagement and delivery, not about whether the programmes reduce offending.
- **First draft.** No mention of facilitators or barriers.
- **What a ruling added.** Advocate ruling `rulings.jsonl:5` (step 4b, applied at 4c) changed "What the evidence holds is young people's own accounts of feeling better, and a handful of small studies whose numbers could not be pooled." to "What the evidence holds is mostly qualitative: accounts suggesting young people may gain positive emotions, a sense of self, engagement in creative practice and positive relationships, plus pointers on what helps programmes work, all formally rated at very low confidence. Alongside these sit a handful of small studies whose numbers could not be pooled." That gesture has no content, and both judges quote it as the reason it does not count.
- **Classification.** The item is (c) because the page treats delivery conditions as off-question. The ruling made it a visible near-miss.

### 7. WHU-S07-C2: (f) drafting omission; the advocate's objection was rejected

- **Source held and cited.** WHU held the WGIII SPM (S003, full text) and cites SPM C.8.2. The key's C2–C4 are the second to fourth sentences of that same paragraph.
- **First and final drafts.** Both use only C.8.2's first sentence: "The Intergovernmental Panel on Climate Change (IPCC) concludes, with high confidence, that changes in urban form … could reduce transport-related greenhouse gas emissions…". Public transport appears only inside the NRC bundle ("…significant public transit improvements, mixed uses and other supportive demand management measures").
- **Advocate.** Advocate item S003-13 (SERIOUS; adjudication `20261025T001512Z`) objected that the page omits the rest of C.8.2: transit and active-travel investment, teleworking and digitalisation, and induced demand. Its proposed text was empty.
- **Ruling.** Ruling `rulings.jsonl:12` **rejected** it. The reason, paraphrased: the sentence's two stated narrowings are supported, and the adjacent SPM sentences describe other measures, which do not broaden that specific claim. That is a ruling on whether the sentence is accurate. It does not ask whether the page is complete.
- **Unsure.** One judge only (OpenAI: Matches).

### 8. WHU-S07-C3: (f) drafting omission; the advocate's objection was rejected — *(c) close*

- **Same evidence as item 7:** SPM held, `rulings.jsonl:12` rejected the advocate's objection.
- **Why not (c).** The question covers layout "together with measures such as transport pricing", which plausibly takes in demand-side measures such as teleworking. The premise (`premise.json`) frames the belief around density, mixing, transit and road charging. If teleworking is read as outside the question, this is (c).

### 9. WHU-S07-C4: (f) drafting omission; the advocate's objection was rejected

- **Same evidence as item 7.** Induced demand is the qualification on C3 in the same SPM paragraph, and S003-13 raised it.
- **Nearest page text.** The page's closest point is the cost-effectiveness line from advocate ruling `rulings.jsonl:10`: "Set against what is known about the effects of gasoline taxes and congestion prices, densification looks unlikely to be a cost-effective way to cut aggregate driving…". That is not a statement about rebound.

### 10. WHU-S08-C1: (c) premise sets a measured-evaluation standard; the question restatement was narrowed — *unsure; (e) possible*

- **Not held.** The key is WGII SPM C.2.6, which WHU did not hold. It held Chapter 6 (S003) and, by the first draft's own account, read its executive summary and section 6.3.3.1.
- **The premise's standard.** `premise.json` frames the belief as planning being *known* to work. The kill condition (1) asks for "controlled or quasi-experimental evaluations, or systematic reviews of them". The page's verdict, unchanged from the first draft, is "Not proven, not disproven: mostly unmeasured." The key is an IPCC high-confidence *judgement* that considering climate risk is critical. The key's own scope note calls it "a judgement…not a measured effect". The page answers a different question (has the effect been measured?), so the judges read it as understating.
- **The step-6 narrowing.** Conclusion ruling `b6caee39a4c1249d` (`rulings.jsonl:55`, step 6, applied at 6a) changed "The question is whether taking climate change into account when designing and planning towns, rural areas and infrastructure makes them better able to cope and improves people's wellbeing." to "The question is whether implemented adaptation responses to climate change are effective." Audit `20261026T003303Z` u5 narrowed "…evidence about people's wellbeing is thinner still" to "…evidence about effects on people's health is also scarce". See §3.
- **Classification.** The root is the premise's standard (step 1). The rulings made it worse. Under a key that states assessed judgements rather than measured effects, (e) is a fair second reading.

### 11. WHU-S08-C2: (a) evidence not held

- **Not held, and not in the held chapter's summary.** SPM C.2.6 was not held. Its list (basic services, infrastructure, livelihoods, food systems, community-based adaptation, benefit to low-income and marginalised groups) does not appear as such in the parts of Chapter 6 the page drew on.
- **What the page says about people.** It addresses wellbeing only through the LMIC health review (S002). Its line is "Evidence that it leaves people better off, for example in health, remains thin in low- and middle-income countries." Audit `20261025T003105Z` u41 added "in low- and middle-income countries".
- **Unsure.** (c) applies as well. The premise's measured-evidence standard steered the research away from assessment statements of this kind.

### 12. WHU-S08-C3: (c) premise sets a measured-evaluation standard — *unsure; (e) possible*

- **The related finding is on the page.** It is in the held Chapter 6 (section 6.3.3.1 and executive summary).
  - Advocate ruling `57da61b8d98f8a86` (`rulings.jsonl:18`) added "…it also finds, with high confidence, that conventional zoning is more effective when governance systems facilitate land use policies for climate adaptation that preclude negative human-nature interactions and curb spatial inequity."
  - The chain `df7e3ea53dea2904` (`:21`), then audit `20261025T003105Z` u40, then audit `20261026T004500Z` u39 produced "The chapter rates adaptation through zoning and land use as more effective when combined with other planning measures (high confidence), for example with ecosystem-based adaptations for flood management and curbing the urban heat island effect."
- **Why it still reads as understating.** Both judges say the page reports the high-confidence finding but that the verdict "Not proven, not disproven: mostly unmeasured." outweighs it. That verdict came from the first draft and was never ruled on. The cause is the same premise standard as item 10.

### 13. WHU-S08-C4: (a) evidence not held — *unsure; (f) possible*

- **Not held, and held text not drawn on.** SPM C.2.6 was not held. The held Chapter 6 executive summary has a related medium-confidence statement on local governments working in partnership with community, private-sector and national actors. The page never uses it.
- **Records.** No ruling, audit unit or cut touches partnerships.
- **Classification.** If the executive summary counts as read (the first draft said it was), this is a drafting omission (f) rather than (a).

### Summary of the classification

| # | Item | Primary | Uncertain? | Stage that owns it |
|---|---|---|---|---|
| 1 | S01-C1 | (b) | one judge only | 4b/4c advocate rulings `78ec04f6…`, `41357058…` |
| 2 | S01-C2 | (f) | no | step 3 draft |
| 3 | S01-C4 | (f) | one judge only | step 3 draft |
| 4 | S03-C1 | (a) | yes, (c) close | step 2 research |
| 5 | S05-C5 | (c) | yes, (e) | question (`issue.json`) |
| 6 | S06-C5 | (c) | yes, (e) | question; advocate ruling `:5` |
| 7 | S07-C2 | (f) | one judge only | step 3; advocate objection rejected, `rulings.jsonl:12` |
| 8 | S07-C3 | (f) | yes, (c) | step 3; `rulings.jsonl:12` |
| 9 | S07-C4 | (f) | no | step 3; `rulings.jsonl:12` |
| 10 | S08-C1 | (c) | yes, (e) | step 1 premise; step 6 `b6caee39…` |
| 11 | S08-C2 | (a) | yes, (c) | step 2 research |
| 12 | S08-C3 | (c) | yes, (e) | step 1 premise; verdict line in step 3 |
| 13 | S08-C4 | (a) | yes, (f) | step 2 research |

---

## 3. The S08 pattern: rulings that narrowed the question and removed what was not read

The study log recorded this as a process finding at 2026-10-25T00:44:00Z, with an addition at 2026-10-26T00:45:00Z. The full list from the records follows. Items marked † are not in the study log's list.

### A. The page's statement of the question

**A1. Conclusion ruling `b6caee39a4c1249d`** (`rulings/rulings.jsonl:55`; step 6 conclusion judge and `ruling.py conclusions`; applied at 6a).
- Before: "The question is whether taking climate change into account when designing and planning towns, rural areas and infrastructure makes them better able to cope and improves people's wellbeing."
- After: "The question is whether implemented adaptation responses to climate change are effective."
- Mechanism: the conclusion judge treated the restatement as a conclusion and asked whether its bound source (S001, the stocktake) supports it. The finding says the passage is silent about planning towns, rural areas, infrastructure or wellbeing. The ruling rewrote the *question* so that the stocktake would support it.
- Consequence: the next sentence, unchanged, is "It is widely taken for granted that it does." It now refers to the narrowed question (study log, item 4).

**A2. Audit `20261025T003105Z` u1** (step 7; meta description; `left_for_person` in `cuts.jsonl`, not applied).
- Before: "Planning towns and infrastructure with climate change in mind is widely taken to make places cope better and leave people better off."
- Ruled: "It is widely taken for granted that implemented adaptation responses to climate change are effective."
- Applied: no. At 7a, Fred chose a body sentence for the summary instead.

**A3. Audit `20261026T003303Z` u5** (step 7c run 4; applied at 7b). †
- Before: "In our reading, the reviews and assessment we read do not show that it fails; they show that the benefit is mostly assumed rather than measured, that measured results are few and narrow, and that evidence about people's wellbeing is thinner still."
- After: "…and that evidence about effects on people's health is also scarce."
- This narrows the standfirst's "wellbeing" to "health".

**A4. Audit `20261025T003105Z` u41** (step 7; applied at 7b). †
- Before: "Evidence that it leaves people better off, for example in health, remains thin."
- After: "Evidence that it leaves people better off, for example in health, remains thin in low- and middle-income countries."

### B. The page's statements of what WHU did and did not read

**B1. Conclusion ruling `125d538dde6fcc01`** (`rulings/rulings.jsonl:54`; step 6; applied at 6a).
- Before: "We did not search the grey literature, which the stocktake's authors say may hold more evidence of risk reduction, and we did not read the primary studies of heat and green infrastructure that the IPCC chapter cites."
- After: "We did not search the grey literature, which the stocktake's authors say may hold more evidence of risk reduction."
- Mechanism: the stocktake passage says nothing about the IPCC chapter's primary studies, so the clause about WHU's own reading was dropped as unsupported.

**B2. Audit `20261025T003105Z` u46** (step 7; applied at 7b).
- Before: "Of the IPCC chapter, we drew on its executive summary and its section on land use planning, and did not read the rest."
- After: "Of the IPCC chapter, we cite its section on land use planning (6.3.3.1)."
- Reason, paraphrased: nothing in the source records what WHU did or did not read, so the reading claim must go, and the quoted text does not show an executive summary.

**B3. Audit `20261025T003105Z` u47** (step 7; applied at 7b). †
- Before (as left by B1): "We did not search the grey literature, which the stocktake's authors say may hold more evidence of risk reduction."
- After: "The stocktake's authors say the grey literature may hold more evidence of risk reduction."
- Reason, paraphrased: no record shows the publication's search process. This removed the last statement that the grey literature was not searched. The study log does not list it.

**B4. Audit `20261026T003303Z` u45, three rounds, then cut** (`audit/20261026T003303Z/cuts.jsonl`, "still failing after 3 read-and-correct rounds"; step 7c run 4; cut at 7b).
- Round 1 (amend): "Of the IPCC chapter, we cite its section on land use planning (6.3.3.1) and its finding that slow uptake of monitoring and evaluation frameworks constrains climate resilient urban development pathways."
- Round 2 (accept): "…(6.3.3.1) and its observation that there is little evidence on how best to make monitoring and evaluation approaches practical at the local scale."
- Round 3 (accept): "Of the IPCC chapter, we cite its section on land use planning (6.3.3.1), which finds with high confidence that adaptation actions through zoning and land use are more effective when combined with other planning measures."
- Cut. The page lost its last statement of which parts of the chapter were read (study log, item 5).

**B5. Dangling ruling `e7904798c3cc64f8`** (`rulings/rulings.jsonl:57`; GAP-016 check after the u45 cut). The heading "What the IPCC assessed about planning itself" was cut, then restored at the advisor's ruling. The cut rested on the `applied_check.dangling()` cut-sentence defect the study log records at 2026-10-26T00:45:00Z.

**B6. The stocktake's reading-purpose clause.** †
- Advocate ruling `8ae1718065708594` (`rulings.jsonl:5`, step 4b) changed "This stocktake covers adaptation of every kind, not planning alone; we read it for what it says about how outcomes are measured, not as a count of planning studies." to "…explicitly excludes processes of decision-making, adaptation governance and planning; we read it for what it says about how outcomes are measured among implemented responses, not as evidence about planning studies."
- Audit `20261025T004606Z` u14 changed "explicitly excludes" to "focuses on … rather than".
- Audit `20261026T005252Z` u14 (second reader; applied at 7b) then gave "This stocktake focuses on observed and implemented adaptation responses rather than processes of decision-making, adaptation governance and planning." This dropped WHU's statement of how it used the source.

**What is left.** The final page's "What we did not read" section says: "We hold four documents: two systematic reviews, one assessment chapter and one evaluation."; "The stocktake's authors say the grey literature may hold more evidence of risk reduction."; and the manuscript and working-paper note. It no longer says that anything was not read or not searched.

**The mechanism in one line.** The conclusion judge (step 6) and the audit reader (step 7) check every body sentence against its bound source. A sentence about WHU's own question or reading can never be supported by a source. `rule_group.md` then tells the ruling model to "give the shortest text that can [be supported], or "" to cut the sentence". So these sentences are rewritten into source claims or removed. Seven other "we hold / we have not opened" sentences escaped only because the audit raised them as `HUMAN_READ_REQUIRED` and Fred read them (7a). The same kind of sentence gets two different treatments depending on how the reader's quotation came out.

---

## 4. Summary

### Counts by primary cause

| Cause | Items (of 13) | Judge labels (of 23) |
|---|---|---|
| (a) evidence not held or not read | 3: S03-C1, S08-C2, S08-C4 | 6 |
| (b) removed or weakened by a ruling | 1: S01-C1 | 1 |
| (c) question or premise scope | 4: S05-C5, S06-C5, S08-C1, S08-C3 | 8 |
| (d) hedging or calibration rule | 0 | 0 |
| (e) answer-key dispute | 0 as primary (5 marked as a possible second reading) | 0 |
| (f) drafting omission (held, read, in scope; not drafted or not graded) | 5: S01-C2, S01-C4, S07-C2, S07-C3, S07-C4 | 8 |

Seven of the 13 classifications are marked uncertain (table in §2).

**No item traces to B19 or another hedging rule (d).** The calibration checks (B19–B21) guard only one direction, against more certainty than the source allows. None flags a page that is *less* certain than its source. That is why the S01-C4 sentence (no grade) and the S08 verdict line passed every check.

### Which stage is responsible

- **Drafting and research (steps 2–3) own 8 of 13**: all of (a) and (f). Nothing later in the pipeline adds a missing finding.
- **The script that lets these through is `ruling.py` with `audit_prompts/rule_group.md`.**
  - The source advocate is briefed to hunt omissions: "you are here for what the page left out" (`source_advocate.py`). But the ruling prompt decides each finding only as "right, or … wrong because the source text supports the sentence as written".
  - So an omission objection on a correct sentence is always "wrong". S07's `rulings.jsonl:12` (C2–C4) and S03's `rulings.jsonl:2` (a paper's call left out "does not make anything the sentence says inaccurate") are this rule at work.
  - The same prompt's "give the shortest text that can [be supported], or "" to cut" is what removed S08's method statements (§3).
- **The premise (step 1, `premise.json`) and question (`issue.json`) own 4.** In S08 the premise set a measured-evaluation standard. The key states assessed judgements.
- **Advocate rulings at 4b/4c own 1** (S01-C1).

### Fix options (not implemented)

**Cause (f): omissions are never ruled as omissions**
1. Give `ruling.py advocate` a decision for completeness, e.g. `add`. Completeness gets its own test: does the omitted, quoted finding from the same source answer the page's question?
   - Where: `audit_prompts/rule_group.md` (new prompt, new sha256 for the study), `ruling.py advocate`, and the 4c apply step (insert a sentence rather than replace one).
   - Test: replay S07's S003-13 brief, with the sentence and quotation from `rulings.jsonl:12`, against a stubbed model. Assert that the prompt the model receives allows a non-reject outcome for an omission and that `add` text reaches 4c.
   - A unit test on the prompt template should also fail if a finding of the kind "left out" can only be ruled right/wrong on sentence support.
2. **A coverage check against the drawn source's headline findings** before step 3b. For every primary outcome in a held review's Summary of findings or abstract conclusions (and every sentence of the cited SPM paragraph), the page must use it or declare it out of scope with a reason, as B6's `scope_words` do. Example: S07 cites C.8.2 but uses one of its four sentences.
   - Where: a new check in `bindings.py check` (WARN, like B19), reading the sections `sources.json` marks as read.
   - Tests: a fixture with a held Cochrane SoF listing time to diagnosis and a page that reports only time to treatment warns (S01-C2). A page citing SPM C.8.2 that binds only its first sentence warns (S07).
3. **Grade carried with every finding of a held review.** A bound sentence reporting a review's outcome must carry the review's GRADE level (the mirror of B20).
   - Where: `bindings.py`, next to B20.
   - Test: S01 sentence 34 ("slightly more people were lost to follow-up … (13.6%) than … (10.1%)"), whose span carries "high-certainty evidence", warns.

**Cause (a): sources that answer the question were not held, or were held but not used**
4. **When a question's natural primary source is an assessment** (IPCC, Cochrane), require the summary-level document (SPM or abstract) to be held alongside the chapter, or declare it not held in `sources.json`.
   - Where: `acquire_sources.py` and `source_store.py status`.
   - Test: an issue holding an AR6 chapter and no SPM reports "assessment summary not held" (S03, S08).
5. **For every group or arm the question names** (S03: businesses, workers, young people, Indigenous communities), require a held source or a declared gap, and check held long documents for sections on it before declaring the gap.
   - Where: `premise.py status`.
   - Test: S03's `issue.json` question and `sources.json` yield a list of named groups with no bound source; the check passes only once each has a premise note.

**Cause (c): the question or premise sets a narrower standard than the question**
6. **Make the evidence standard explicit and visible.** If `premise.json`'s kill condition demands controlled evaluations, the page must also report the assessment's own confidence judgement in its verdict section, not only the measured-evidence verdict. Example: S08's "Not proven, not disproven: mostly unmeasured." stands beside an IPCC high-confidence statement it never weighs.
   - Where: `premise.py` (a field for "standard of evidence") and `conclusion_judge.py` (judge the verdict line against the strongest held assessment statement as well as its bound span).
   - Test: an S08 fixture whose verdict line contradicts a held high-confidence executive-summary statement is flagged.
7. **Lock the question restatement.** The page sentence that restates the question must equal `issue.json`'s question (normalised), or carry a signed reason. It is excluded from conclusion-judge and audit source-support rulings.
   - Where: `conclusion_judge.py` and `audit_stage.py` (skip, or route to a person), plus a preflight row in `publish.py check`.
   - Test: applying ruling `b6caee39a4c1249d`'s text to the S08 page makes preflight STOP.

**Cause (b): rulings weaken or remove; S08's disclosures**
8. **Classify method and limits sentences** ("we read", "we did not read", "we did not search", "we hold", "the question is") as `kind: disclosure` at binding time. Route them to a person (as `HUMAN_READ_REQUIRED` does), never to a source-support ruling, and never cut them automatically.
   - Where: `bindings.py scan` (classifier), `audit_stage.py`, `conclusion_judge.py`, and `ruling.py` (refuse to rule on a disclosure row).
   - Test: replay S08's audit u46, u47 and u45 and conclusion ruling `125d538dde6fcc01`. Each must end as "left for person", with zero text changes.
9. **No-loss check after every apply step.** Compare the page's set of disclosure sentences and its question sentence with the step-3b commit. Any removed or narrowed one is a STOP until a person signs it.
   - Where: `applied_check.py` (beside `--dangling`), and `changecheck_coverage.py`.
   - Test: S08 at `5e8cb4d` against `790f830` reports B1–B4 and A1.
10. **Rulings that change the certainty of a synthesis line.** A ruling that replaces a high-certainty finding's wording with an "inconclusive" or "could not rule in or out" frame, on a sentence that also summarises a high-certainty result, is flagged for the conclusion judge to compare against every bound span on the page, not only the sentence's own.
    - Where: `ruling.py` (post-check), `conclusion_judge.py`.
    - Test: S01 ruling `78ec04f65ce78d78` applied to a page whose sentence 19 says "high-certainty … little to no difference" is flagged.

**Cause (d): no instance, but the gap is real**
11. **Add an understatement check that mirrors B19:** the span carries "high certainty" or "high confidence", and the sentence carries a hedge or no grade. WARN.
    - Where: `bindings.py check`.
    - Test: the S01-C4 sentence and S08's verdict line, each against a high-confidence premise, warn.

**Cause (e): key scope**
12. For the next study run, record in the key which conclusions are *in scope of the question as worded* (S05-C5 recurrence, S06-C5 delivery conditions). Report M2 for in-scope conclusions separately from all conclusions, decided before judging and logged in `deviations.md`.
    - Test: the M2 scorer prints both counts.

### The three fixes with the most reach

1. **An omission decision in `ruling.py` / `rule_group.md`** (option 1), with the source-coverage check at step 3 (option 2). Between them these cover the 5 (f) items and the S08-C4 near-miss. The advocate already finds these omissions; the ruling prompt is what throws them away.
2. **Disclosure sentences never go to source-support rulings, and none is removed without a signature** (options 8 and 9). This stops the whole S08 pattern (A1, A3, B1–B4, B6) and would have kept S08's question as worded.
3. **The premise's evidence standard is stated, and the page must weigh the strongest assessment judgement it holds** (options 6 and 4). This covers S08-C1 to C3 and S03-C1 together: 5 items, 10 judge labels.
