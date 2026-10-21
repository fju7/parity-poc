# WHU reliability study: working directory

Protocol: "WHU Reliability Study: Protocol" (Claude Docs, `claude.ai/code/artifact/ed0f1c5e-8fe5-48ac-b441-9e8fc54d1078`), draft, not yet frozen.

This directory holds the study's code, prompts and blinding list. Data the study produces goes under `runs/` and is not committed: source snapshots (other people's copyrighted text), judge replies and anything that could reach a judge or a WHU run. Everything is hashed when it is made (protocol, integrity rule 4).

| Path | What |
|---|---|
| `prompts/m1_citation_support.md` | M1 judge prompt (claim + about 400 characters of context + source snapshot → one of seven labels). Version 2 (see below). |
| `prompts/m2_conclusion_calibration.md` | M2 judge prompt (blinded answer + one answer-key conclusion → Matches / Overstates / Understates / Contradicts / Omits). **Drafted, not tested**: there are no M2 items yet. It is tested later on the practice questions' answer keys. |
| `scripts/snapshot.py` | Fetches each cited source once and saves the bytes, the text both judges read, sha256 and readable extent. Free. |
| `scripts/judge_m1.py` | Runs the M1 prompt with both judges on the same snapshot. Meters every call into `backend/data/spend/ledger.jsonl` and stops before any call that could take the round past its cap. |
| `scripts/score_prep.py` | Per-label agreement, confusion tables, form checks and cost per call. Free. |
| `blinding/blind_phrases.json` | The fixed rewrite list: house phrases, tool signatures, and British-to-American spelling. Also the residual "tells" the check counts. |
| `blinding/blind.py` | Converts an answer to one plain format, applies the list, and reports the residual tells. Free. |

## Measures of the WHU process

Recorded on every study issue as the WHU run produces it, alongside the judged measures (M1, M2):

- **Ruling-model consistency (added 2026-10-21).** After each ruling step, a seeded random 20% of that step's rulings (at least one) is re-run with the identical payload and prompt; the second ruling is logged and never applied. Reported per step and per issue: the share of pairs with the same decision and text, and with the same decision alone (unusable second replies counted apart). Code: `backend/scripts/whatholdsup/consistency.py` (called by `ruling.py`; `consistency.py audit` for audit runs; `consistency.py report`). Log: each issue's `rulings/consistency.jsonl`, not committed. See RUN.md.

## Prep round 1 (19 October 2026)

**Pilot location.** The October pilot is not in this repository or in `fju7/ai-research-reliability`. It is a local archive, `~/Downloads/Citation Pilot 2026-10-16/`:
- **Questions:** `README.md`.
- **Answers:** `reports/`.
- **Judge prompts:** `judging/xjudge_prompt_*.txt`.
- **Judge replies:** `judging/judge_result_*.json` (Claude), `judging/xjudge_chatgpt_*` and `judging/xjudge_gemini_*`.
- **Pairs:** `data/sample_40_pairs.json`.

The pilot has **no human-settled labels**. The operator's blind scoring stopped, and the seven disputed pairs went out for volunteer review with no result recorded.

### B. M1 judge prompt: a behaviour check, not an accuracy measurement

By the advisor's ruling of 19 October, the prompt was tested only on pilot items where every pilot judge (Claude, ChatGPT and Gemini) gave the same label. That gives 18 items: 14 Supported, 3 Absent, and 1 Overreach: scope, read as Overstates.

This checks three things:
- the judges return valid JSON;
- they follow the label definitions;
- they agree where the pilot was unanimous.

**It does not measure accuracy.** The reference labels are three AI judges agreeing, not a person, and they are almost all Supported. They do not establish ground truth.

**Judges:**
- `claude-fable-5-1`, max_tokens 1024.
- `gpt-6-astra` through the Responses API, max_output_tokens 6000, default reasoning.
- Each was chosen as the top generally available model on its company's pricing page on 19 October. For gpt-6-astra that is an inference from its listing: first and highest-priced under "Flagship models". The protocol's choice of judge models is still to be ruled.

**Snapshots.** Fetched once, on 19 October. Two of the 18 sources were unreachable, and those items were dropped and counted:
- P23, `jamanetwork.com`: HTTP 403.
- P30, Canada's Food Guide: 604 readable characters, a JavaScript-only page.

That leaves 16 items. Readable extent: 12 full text (7 articles, 5 pages that are their own whole document) and 4 abstract only.

**Results** (prompt v2; one run per judge):

| | Claude judge | ChatGPT judge |
|---|---|---|
| Agrees with the unanimous pilot label | 13/16 (13/14 excluding refusals) | 13/16 |
| Valid JSON in the required form | 14/16 (both failures are refusals) | 16/16 |
| Span quoted verbatim from the snapshot | 14/14 labelled | 16/16 |
| Refusals (`stop_reason: refusal`, no output, input billed) | **2** (P01, P41) | 0 |
| Judge agrees with the other judge | 10/16 | |

Per-label agreement (reference label → what the judge said):

| Reference | n | Claude judge | ChatGPT judge |
|---|---|---|---|
| Supported | 12 | Supported 12 | Supported 9, Overstates 2 (P16, P22), Absent 1 (P29) |
| Absent | 3 | Absent 1, Supported 1 (P34), refusal 1 (P41) | Absent 3 |
| Overstates | 1 | refusal 1 (P01) | Overstates 1 |

**What the disagreements show.** These are protocol questions, not judge errors:
- **P01 and P41: Claude refusals.** Both repeat:
  - P01 refused again on Fable 5.1, and also on `claude-opus-5-5`.
  - The sources are a gut-microbiome feeding trial (P01) and an NCBI Bookshelf chapter on vitamin D metabolism (P41).
  - The protocol needs a rule. Proposed: a refusal is no label, the item goes to people, and the refusal rate is reported per system. The input must not be rephrased to get past it.
- **P16 and P22: framing words beyond the source.**
  - P16's claim says "most explicit"; P22's says "medically necessary". The source supports the rest of each claim but not these words.
  - The ChatGPT judge says Overstates; the Claude judge says Supported.
  - The prompt needs to say whether a framing word or comparison counts as part of the claim.
- **P34: a sentence citing two sources.** The Claude judge checked only the part attributed to this source; the pilot judges said Absent. Either M1 sampling must cut the claim to the part attributed to the cited source, or the prompt must say what to do.
- **P29: abstract only.** The snapshot is the abstract, which says sugar and fiber "change" but not in which direction. The ChatGPT judge says Absent. The pilot judges may have read the full paper.
- **Prompt v1 → v2.** In the first smoke test, the ChatGPT judge labelled P29 Contradicted because the claim says "Gibney (2018)" and the page says 2019. One paragraph was added before the full run: a small error in how a sentence *names* a document does not change the label; a different study is still Wrong source. The v1 replies are kept in `runs/prep1/replies_v1/`.

### C. Cost

**Measured on B's calls** (one run, 16 items). Refusals are included, because their input is billed.

| Per M1 call | Claude judge (Fable 5.1, $10/$50 per MTok) | ChatGPT judge (gpt-6-astra, $10/$50) |
|---|---|---|
| Mean input tokens | 20,267 | 12,716 |
| Mean output tokens | 240 | 145 (includes reasoning) |
| Mean $ (median $) | $0.215 ($0.103) | $0.134 ($0.062) |
| Largest call | $1.22 (P41, 122k tokens, refused) | $0.77 (P41) |

Snapshots average 46,000 characters (median 20,000; largest 268,000). The judges' tokenizers read about 2.5 characters per token (Claude) and 4.0 (OpenAI).

**M2 per call, estimated (not measured):**
- **Input:**
  - prompt about 3,400 characters, plus one key conclusion about 800;
  - plus the blinded answer, mean 2,900 words, about 18,000 characters. Mean pilot lengths: Claude 3,500 words, ChatGPT 2,560, Gemini 3,920, WHU test answers 1,700.
  - That is about 8,900 input tokens for Claude and 5,600 for OpenAI.
- **Output:** assumed about 300 tokens (Claude) and 400 (OpenAI, with reasoning).
- **Per call:** about **$0.10 (Claude)** and **$0.08 (ChatGPT)**.

**Projection for the full study:**
- About 480 items: 4 systems × (80 M1 claims + 40 M2 conclusions) = 320 M1 + 160 M2.
- 2 judges × 2 runs.
- That is 640 M1 calls and 320 M2 calls per judge.

| | Claude judge | ChatGPT judge | Total |
|---|---|---|---|
| M1 at measured mean | $137 | $86 | $223 |
| M1 at measured median | $66 | $40 | $106 |
| M2 estimate | $33 | $24 | $58 |
| **Study, mean basis** | | | **≈ $280** |

**Assumptions and sensitivities:**
- **Snapshot size drives M1.** The pilot's sources are health sources. Six of the eight study questions are not: Campbell reviews, a National Academies report and IPCC. A National Academies report or an IPCC chapter can run to hundreds of pages. If the mean snapshot is twice the pilot's, M1 is about $450 and the study about $500, **above the $300 line where Fred decides before the full run.** The protocol does not yet say whether a snapshot is capped or cut to the relevant part.
- **Caching would cut it by roughly 40%.** Put the DOCUMENT first in the prompt, run both runs of an item back to back, and judge the claims that share a source together. A Fable cache read costs 0.025× input, after a 1.25× write; an OpenAI cached input costs 0.1×. The study would come to about $165 at the mean. This changes the prompt's order, so it must be decided before the prompts are frozen.
- **Refusals cost money and yield nothing.** At the pilot's rate (2 of 16 Claude calls), about 12% of Claude M1 calls are paid for with no label.

### D. Blinding phrase list

**The list.** `blinding/blind_phrases.json` holds:
- 21 rewrite rules (17 for WHU, 4 for tool signatures);
- a 109-word British-to-American spelling map, applied to lowercase words only, so that names like "Science Media Centre" are kept;
- 14 residual detectors.

**What `blind.py` does:**
- **Format.** Strips headings, layout and emphasis, and WHU's page furniture: masthead, corrections notice, change history and source-note annotations.
- **References.** Reduces references to a numbered "citation + URL" list.
- **Text.** Normalises quotation marks and dashes, then applies the rules.

**The rule:** a rule may change wording, never what is claimed. "In our reading" becomes "In this answer", not nothing. M2 scores certainty, so dropping a hedge would make WHU's answers overstate.

**Tested** on WHU's three published issues and the pilot's four WHU test answers. The pilot's 12 tool answers are the baseline, because a tell identifies a system only if its rate differs between systems. Residual tells after blinding, per 1,000 words:

| Tell | WHU published (3) | WHU test answers (4) | Claude (4) | ChatGPT (4) | Gemini (4) |
|---|---|---|---|---|---|
| Inline citation markers `[n]` | 1.11 | **0.00** | 43.25 | 0.00 | 26.49 |
| First-person plural (we/our/us) | **5.03** | **2.19** | 1.04 | 0.58 | 0.45 |
| Coverage analysis (headline, press release, coverage) | **1.11** | **1.72** | 0.42 | 0.00 | 0.00 |
| Addresses "a reader" | **0.95** | **0.31** | 0.00 | 0.00 | 0.00 |
| Closing certainty paragraph ("Certainty about the direction is…") | 0.00 | **0.63** | 0.00 | 0.00 | 0.00 |
| "et al." | 1.32 | 0.94 | 3.90 | 4.38 | 3.37 |
| Corrections language | 0.58 | 0.47 | 0.07 | 0.00 | 0.06 |
| Notes on unread sources | 0.86 | 0.00 | 0.00 | 0.00 | 0.00 |
| "In this answer" (the rewrite of "in our reading") | 0.29 | 0.00 | 0.00 | 0.00 | 0.00 |
| Dated process notes ("read … on 30 August 2026") | 0.29 | 0.00 | 0.00 | 0.00 | 0.00 |
| Watching / "would settle" | 0.21 | 0.00 | 0.00 | 0.00 | 0.00 |
| British spelling | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 |
| Words | 24,278 | 6,394 | 14,358 | 10,270 | 15,707 |

**What still identifies WHU after the list.** A fixed phrase list cannot fix these:

1. **No inline citations.** WHU's body names its sources in prose and carries no reference markers. Claude and Gemini carry 26–43 markers per 1,000 words. Under "plain text with numbered references", WHU's answer is the one without markers, along with ChatGPT's. M1 also needs claim-to-source links. The fix is an export step that adds `[n]` from WHU's bindings, not a phrase rule.
2. **First person.** About 2–5 "we/our" per 1,000 words, against 0.5–1 for the tools, mostly in reasoning sentences ("so we cannot reconcile …"). Rewriting them takes a grammar-aware pass. That is a model paraphrase under fixed instructions, which the protocol's "fixed list applied by script" does not allow as written.
3. **The coverage paragraph.** WHU answers include a paragraph assessing how the news covered the evidence. No tool does this. It is content, not phrasing.
4. **The closing certainty paragraph.** It is reworded, but it is still a separate certainty statement at the end, and only WHU has one.
5. **Talking about "a reader".**
6. **Length.** WHU's test answers average about 1,600 words, against 2,500–3,900 for the tools.
7. **Published pages only:** notes on unread sources, dated process notes, corrections language and the watch section. They do not appear in the test answers; a study answer is a new page with no corrections or watch history.
8. **The rewrite itself.** "In this answer" appears only in WHU text.

So the phrase list removes the vocabulary but not the shape. The protocol's blinding check (a model guessing the system from 20 blinded claims) is what measures whether the shape is enough to identify WHU. At M1 level, claims plus 400 characters of context, items 1, 4 and 6 mostly disappear and items 2, 3 and 5 remain. That check was not run in this round, because it costs money.

### Spend

$5.74 of the $10 cap: 36 calls in `backend/data/spend/ledger.jsonl` under issue `whu-reliability-prep1`.

| Calls | Judge | What |
|---|---|---|
| 16 | Claude (Fable 5.1) | Full run |
| 16 | ChatGPT (gpt-6-astra) | Full run |
| 1 + 1 | Claude, ChatGPT | P29 under prompt v1 |
| 1 | Claude (Fable 5.1) | P01 refusal retry |
| 1 | Claude (Opus 5.5) | P01 refusal diagnostic |

The prices added to `spend_ledger.PRICES` (and the gate's copy, held equal by test) are `claude-fable-5-1` and `claude-opus-5-5`, from the pricing page on 19 October. The OpenAI price is in `judge_m1.py`, with its source and date.

## Prep round 2 (19 October 2026)

Rulings: protocol rev 23, "Rulings from prep round 1", "Blinding rulings" and "Audit stage design approved". Data under `runs/prep2/`, not committed. Spend: **$6.07 of $25**, under ledger issue `whu-reliability-prep2`.

### Part 1. Judge prompts

**OpenAI model.** `GET /v1/models` (19 October) returns 135 ids. The gpt-6 family is `gpt-6-astra` (created 2026-08-27), `gpt-6-sol` and `gpt-6-luna` (2026-09-14), and `gpt-6.1-sol` (2026-09-27). OpenAI's models page (developers.openai.com/api/docs/models) calls GPT-6 Astra "our flagship model for complex reasoning and coding" and "Our most capable model for the most demanding work". GPT-6.1 Sol is "Near-Astra performance … at a lower cost". **Judge: `gpt-6-astra`.**

**Claude judge.** Switched to `claude-opus-5-5`.

**M1 v3** (`prompts/m1_citation_support.md`; v2 kept as `m1_citation_support_v2.md`, with its replies in `runs/prep1/`):
- **Order.** The sources come first, then the claim, then the instructions.
- **Framing.** Superlatives, rankings and "first" are part of the claim; unsupported framing is Overstates.
- **Several sources.** A sentence citing several sources is judged against all of them, and the judge sees every cited snapshot.
- **Naming errors.** A small error in naming a document still doesn't change the label.

**Caching.**
- Claude uses a `cache_control` breakpoint at the end of the documents.
- OpenAI uses automatic prefix caching, with a `prompt_cache_key` naming the documents.

**Runner rules** (`scripts/judge_m1.py`, tests in `backend/tests/test_whu_study_judge_m1.py`):
- **Refusal.** Retried once, unchanged. If refused again, the label is REFUSED and the item is flagged for a person; the other judge's label stands.
- **Abstract only.** An Absent on an abstract-only snapshot is recorded as NOT_VERIFIABLE_ABSTRACT. The snapshot record has an `abstract_only` flag, decided from the stored text by `snapshot.py`.
- **Length.** Snapshots are counted in tokens. Over 150,000 tokens, a source is cut to the sections containing the claim's key terms and the item is marked CHUNKED. **No test item was over 150,000 tokens.** The largest, P41, is 120,853, so chunking is exercised only by the tests.

**Snapshots.**
- Now one per source.
- The prep-1 bytes are reused, so each source was fetched once for the whole prep.
- Four test sentences cite two sources: P03, P06, P31 and P40. P40's second source (hopkinsdiabetesinfo.org) is unreachable and is recorded on the item.

**Results** (16 items, one run per judge):

| | Claude judge (Opus 5.5) | ChatGPT judge (gpt-6-astra) |
|---|---|---|
| Agrees with the unanimous pilot label | 12/16 | 13/16 |
| Refused items (calls) | **2 (4)**: P01 and P41, refused on both attempts | 0 |
| NOT_VERIFIABLE_ABSTRACT | 0 | 2 (P29, P34) |
| Valid JSON / span verbatim, of labelled items | 14/14 / 14/14 | 16/16 / 16/16 |
| Judge agrees with the other judge | 12/16 | |
| Sent to a person | P01, P29, P34, P41 | |

| Pilot label (n) | Claude judge said | ChatGPT judge said |
|---|---|---|
| Supported (12) | Supported 11, Overstates 1 (P16) | Supported 10, Overstates 1 (P16), NOT_VERIFIABLE_ABSTRACT 1 (P29) |
| Absent (3) | Absent 1, Supported 1 (P34), REFUSED 1 (P41) | Absent 2, NOT_VERIFIABLE_ABSTRACT 1 (P34) |
| Overstates (1) | REFUSED 1 (P01) | Overstates 1 |

**Reading the results:**
- **P16.** Both judges now apply the framing rule to "most explicit". The pilot's "Supported" predates that rule.
- **P22.** The two judges now agree on Supported.
- **The refusals were not Fable-specific.** Opus 5.5 refuses P01 (a gut-microbiome feeding trial) and P41 (an NCBI Bookshelf chapter on vitamin D metabolism), as Fable 5.1 did. The ruling expected Opus 5.5 to be free of them.
- **P34.** The Claude judge still passes P34 on the Gibney part alone. The sentence's other source (Atzeni 2022) had no link in the ChatGPT answer, so it could not be given.
- **Checker fix.** The verbatim check now applies Unicode NFKC normalisation. P33's span was verbatim apart from a PDF ligature ("Eﬀects").

**Cost per call, measured:**

| | Claude judge | ChatGPT judge |
|---|---|---|
| Main run, mean (median) | $0.099 ($0.047) | $0.139 ($0.069) |
| Cache hits in the main run | 3 of 18 calls; 27% of input tokens | 0 of 16 calls |
| Cache probe: second pass on P28, P36 and P39 | $0.0146 per call; 90% of input from cache | $0.0153 per call; 100% of the source block from cache |

The main run had few cache hits because every item ran once and few items share a source:
- P06 and P31 cite the same two sources, but in opposite order, so their prefixes differ.
- P29's source block is under OpenAI's 1,024-token caching minimum.

The probe (`replies-cacheprobe1/2`) is what a study run 2 looks like. Its labels are not used.

**Full-study projection with caching** (`scripts/project_cost.py`):
*(Superseded on 20 October 2026: see "Cost projection as ruled" at the end.)*
- Run 1 of each item is priced as measured.
- Run 2 is priced from the same call's tokens, with the source block at the cached rate.
- M2 is estimated: the answer is cached once and read by its other nine calls (5 conclusions × 2 runs).

| | M1 Claude | M1 ChatGPT | M2 Claude | M2 ChatGPT | **Total** |
|---|---|---|---|---|---|
| Pilot-sized sources | $40 | $55 | $6 | $13 | **$114** |
| Sources twice the pilot's size | $73 | $97 | $6 | $13 | **$188** |

**Both are below $300.** Two assumptions:
- **Run 2 must reach each item within the cache's lifetime.** Five minutes is Claude's default, so run each item's two runs back to back.
- **Order matters.** Sentences citing the same sources should give them in the same order.

**M2** (`prompts/m2_conclusion_calibration.md`) now puts the answer first, then the conclusion, then the instructions. It has the same framing wording and a several-places rule. **Not tested.**

### Part 2. Blinding

**WHU export** (`blinding/export_whu.py`):
- **Splitting.** Sentences are split exactly as `bindings.py` splits the page.
- **Markers.** `[n]` comes from each sentence's binding: `source_id`, then `also_rests_on`, then the premises' sources. References are numbered in order of first citation, and markers sit before the closing punctuation.
- **Dropped:** the masthead line, the correction notices, the source notes and the change history.

| | Sentences | Bound | With markers |
|---|---|---|---|
| Deskilling | 288 | 288 | 231 |
| cdk46 | 304 | 158 | 31 |
| Melanoma | 205 | 56 | 51 |

**Gap: cdk46's and melanoma's bindings cover only their empirical sentences.** A study answer built under the every-sentence rule would look like deskilling.

**One plain format for the tools** (`blind.py`):
- **Claude.** Its site-name chips become `[n]`, placed before the full stop.
- **Gemini.** Glued numerals and `[cite: n]` become `[n]`.
- **ChatGPT.** HTML tables and captions left in its exports are stripped.
- **Splitting.** All systems' sentences are split by WHU's splitter, with common abbreviations protected.

**Phrase list changes** (`blind_phrases.json`):
- **Deleted, not replaced:** "in our reading", "in our judgement" and "as we read it" (rules W03a–e). These are the only WHU-only hedges in the three issues: 6, 1 and 1 uses, and 0 in any tool's answer.
- **The "In this answer" rewrite is gone.**
- **"This page" now becomes "this report".** That's a replacement, because the phrase can't be deleted without breaking the sentence. Claude Research calls its own answer "this report". **This is a decision for Fred.**
- **Approximation signs.** "~" and "≈" before a number become "about", for every system (rule N01, added after check 1).

**Not samplable, for every system:** `blind.process_reason()` covers unread-source notes, dated process notes, change history, the watch section and own-method sentences. The WHU export also excludes the watch section whole. Sentences whose values Gemini's export lost are marked too. First person, length and paragraph shape are untouched.

**Identifiability check** (`blinding/identifiability.py`):
- Opus 5.5 guesses the system for 20 blinded claim-like sentences per system, each with the roughly 400 characters before it, as an M1 judge sees it.
- The 80 sentences are shuffled and sent in four batches of 20 (seed 20261019).
- WHU's sentences come from the three published issues; the tools' from the pilot answers.

| | WHU | Claude | ChatGPT | Gemini |
|---|---|---|---|---|
| Check 1: identified | **20/20** | 20/20 | 20/20 | 20/20 |
| Check 2 (after extending the list): identified | **20/20** | 19/20 (1 guessed ChatGPT) | 20/20 | 20/20 |

**Blinding fails: WHU was identified 100% of the time in both runs**, against the 50% threshold. Chance is 25%.

**What the guesser said gave WHU away:**
- **Topic.** WHU's sentences are about AI deskilling, CDK4/6 drugs and melanoma; the tools' are about the pilot's four questions. This is a confound in the check as specified: no phrase list can remove it.
- **Editorial voice and first person.** "We give the number…", "the general rule we have drawn", "in their words", "In fairness to the author".
- **Close checking of other sources.** Auditing a review's references, abstract against body, pre-registration.
- **WHU-only page elements.** Chart descriptions ("Amber bars cross the 95% no-effect line") and the rubric scorecard ("Rigor scores 5").

**What gave the tools away:**
- **Claude:** site-name tags in check 1, which were a converter bug, now fixed. In check 2, dense trial statistics.
- **ChatGPT:** "~" and "≈" notation and no citations at all. Its answers have none.
- **Gemini:** ornate mechanistic prose and its "[cite:]" format.

**Not yet handled:**
- **Converter leftovers.** A few Claude tags and Gemini "cite:" markers remain in check 2's text.
- **Further extensions** (not run, since only one re-run was allowed): marking chart-description and rubric-score sentences as not samplable.

### Part 3. The audit stage

**Built:**
- `backend/scripts/whatholdsup/audit_stage.py`, the driver;
- `audit_prompts/read.md` and `audit_prompts/rule.md`, the prompts, each identified by sha256 on the manifest;
- the preflight row `audit complete` in `publish.py`, BLOCKED when it cannot run.

See `docs/whu-audit-stage-design.md`, "As built".

**Tests:** `backend/tests/test_whatholdsup_audit_stage.py`, 20 passed. They cover:
- a fabricated quote fails the verbatim check;
- preflight blocks an issue with no audit, a sentence with no verdict, a corrected or cut sentence still on the page, a failed run and a dry run;
- a sentence still failing after three rounds is cut and logged;
- what the ruling model was actually sent contains none of the forbidden fields, even with them smuggled into the binding row;
- the spend cap stops a call before it is made.

**Dry run.** The first 20 units of deskilling: 4 card, 2 meta description, 14 page.
- **Command:** `audit_stage.py run deskilling --dry-run --limit 20 --out <scratch> --ledger-issue whu-reliability-prep2`.
- **It wrote nothing to the issue.** The dry run refuses an `--out` inside `issues/`.

| | Calls | Input tokens | Output tokens | $ |
|---|---|---|---|---|
| Reading (3 rounds) | 7 | 168,887 | 9,607 | 0.868 |
| Ruling | 7 | 8,464 | 1,932 | 0.073 |
| Second reader (7 units: 6 judgement rows + 1) | 3 | 140,199 | 3,962 | 0.640 |
| **Total** | 17 | 317,550 | 15,501 | **1.580** |

- **Per sentence: $0.079.**
- **By part:** reading $0.043, ruling $0.004, second reader $0.032.
- **Tokens per sentence:** about 15,900 in and 780 out.
- **Time:** 149 s of model time, 2 min 32 s of wall time.
- **Whole page (495 units):** about $39 at this rate. That is an extrapolation from 20 units, not a measurement.

**What the dry run found** (read-only; nothing was applied):
- **Masthead dateline (u7).** "Evidence last read 18 October 2026" was flagged.
  - Round 1 changed it to 19 October; round 2 to "30 August"; round 3 still found a problem, so it was cut.
  - The rounds disagree because the records hold both dates. The three-round cut worked as designed, but the sentence needs a person.
  - Preflight already warns that the "as of" date trails the newest recorded check.
- **Correction notice (u14).** "On 19 October 2026 we re-read every sentence" → "On 18 and 19 October 2026…", accepted. The records show the reading ran over both days.
- **Card and meta description (u4, u5, u6): a defect in the build.** These sentences found no page sentence to borrow a binding from, so they were read with no documents. They were found "Rested on a document we do not hold", and the ruling model amended them to "" and cut them. A card restates the page and must be read against it. **This needs fixing before the practice run.** **Closed, checked 20 October 2026:** prep round 3 (`24e3538`) reads card and meta sentences against the page body with their own prompt (`audit_prompts/summary.md`), and no card sentence was cut in that round (below); `ff79b9d` applies a card or meta wording only if it is a whole body sentence, word for word, and otherwise leaves it for a person. Tests: `test_card_and_meta_sentences_are_read_against_the_page_body_not_the_sources`, `test_a_card_wording_the_model_composed_is_left_for_a_person_and_never_applied`, `test_a_card_wording_that_is_a_body_sentence_word_for_word_is_applied`. A ruling that amends a card sentence to "" still cuts it, as for a body sentence.
- **Second reader.** Agreed on all 7.

**The card is also out of date on its own.** The homepage card still reads "The evidence usually offered is weak." The page was corrected on 19 October to "In our reading, the evidence usually offered for it is weak." Not fixed here.

## Prep round 3 (19 October 2026)

Rulings: protocol rev 24, "Rulings from prep round 2". **Spend: $11.26 of $20** under ledger issue `whu-reliability-prep3`. Pushed first: `070eded..a7c18d4  HEAD -> main`.

### Audit stage fixes

- **Card and meta-description sentences are read against the page body**, not the sources. They use their own prompt (`audit_prompts/summary.md`), and a finding has the kind "Summary says what the body does not". The round-2 binding borrow is removed.
- **The deskilling dry run was re-run** (20 units, read-only; $1.64):
  - **No card sentence was cut.**
  - **The stale card sentence was flagged:** "The evidence usually offered is weak." becomes the page's "In our reading, the evidence usually offered for it is weak."
  - **The second card sentence and both meta-description sentences were flagged too.** Each drops or widens the body's hedges. All four corrections were accepted, and each corrected text then held.
- **Licence.** `licensed_ids()` reads `licence_forbids_machine_reading` from the issue's `sources.json` (`source_store.LICENCE_KEY`). On cdk46 that is S001 (NCCN). No id is hard-coded.
  - **Never sent:** a licensed source's text is dropped from the held texts before any prompt is built, and its spans are withheld from binding lines.
  - **Bound only to it:** the sentence is HUMAN_READ_REQUIRED. Preflight blocks until a person's read is recorded in `human_reads.jsonl`.
  - **Bound to it and to others:** the sentence is read against the others only, and the verdict records that.
  - **Tests:** a payload test plants the licensed text in both the held texts and the binding span, and asserts it reaches no request. It fails if the withholding is switched off. Audit-stage tests: 24 passed.

### Sampling

Chart descriptions and rubric scores are not samplable, for every system:
- **Structurally in the WHU export:** `p.ci-cap`, figcaptions and anything marked `data-whu`.
- **By text pattern in `blind.py`**, for every system.

Across the three issues this excludes 42 WHU sentences (34 rubric, 8 chart). The patterns matched no sentence in any tool's answer.

### P34 and incomplete sources

**Both judges were sent one snapshot for P34:** Gibney (nutritionconnect.org). The answer's sentence is "**Atzeni et al. (2022)** reports gut microbiome differences with UPF intake; and **Gibney (2018)** critiques UPF definitions."
- **No link.** ChatGPT's answer gives no link and no reference list.
- **No pair.** The pilot's pair extractor cut the bold name "Atzeni et al." and made no pair for it.
- **So:** Atzeni had no snapshot.

**The runner now marks such an item INCOMPLETE_SOURCES.** Each item lists every cited work under `citations`. If any has no URL or an unreachable snapshot, no judge is called and the item goes to a person. P34 (Atzeni) and P40 (`hopkinsdiabetesinfo.org`, HTTP 403) are now INCOMPLETE_SOURCES. `--allow-incomplete` is only for tests of the judges themselves.

### Bias test (replaces the identifiability gate)

16 items, M1 v3, both judges, one run per condition, all four conditions back to back per item. The author line comes after the documents and before the claim. The bias test ran with `--allow-incomplete`, so P34 and P40 were judged on the sources that exist.

| Condition | Claude: labels changed from A1 | ChatGPT: labels changed from A1 |
|---|---|---|
| A2, repeat run | 0 | 1: P22, Overstates → Supported |
| B, "written by What Holds Up" | 1: P34, Supported → NOT_VERIFIABLE_ABSTRACT | 0 |
| C, "written by an AI chatbot" | 0 | 1: P03, Supported → Overstates |

**Rule:** FAIL if B or C changed at least two more labels than A2.
- **Claude: pass.** At most 1 more label changed than in A2.
- **ChatGPT: pass.** No more labels changed than in A2.

**Result: PASS.**

**Refusals:** Claude refused P01 and P41 in every condition; ChatGPT refused nothing.

**Cost:**

| | A1 | A2 | B | C |
|---|---|---|---|---|
| Claude | $1.77 | $0.26 | $0.26 | $0.26 |
| ChatGPT | $2.23 | $0.32 | $2.25 | $2.25 |

**Caching:**
- **Claude:** cache hits on 57 of 72 calls.
- **ChatGPT:** only the identical repeat (A2) hit its cache: 16 of 64 calls. When the text after the documents changed (B, C), it paid full price.
- **Cost consequence for M2:** if that holds generally, OpenAI's M2 calls (one answer, five different conclusions) won't share a cache. Its M2 estimate would rise from about $13 to about $24, putting the study at about $125 at pilot-sized sources and about $199 at twice that. Both are still under $300.

### Practice question

Choose from the pilot's four questions the one with the fewest unreachable cited sources across the three tools' answers. Every cited URL was fetched once on 19 October under `snapshot.py`'s rules; a cited work with no URL counts as unreachable.

| Question | Reachable | Unreachable | No URL | Unreachable + no URL |
|---|---|---|---|---|
| Q1 exercise and depression | 52 | 34 | 4 | 38 |
| **Q2 ultra-processed foods** | 71 | **21** | 4 | **25** |
| Q3 intermittent fasting | 40 | 33 | 1 | 34 |
| Q4 vitamin D over 60 | 41 | 32 | 1 | 33 |

**Choice: Q2, "Do ultra-processed foods harm your health?"** It has the fewest unreachable sources either way: 21 fetched-unreachable, or 25 with no-URL citations included. No tie-break was needed.

**WHU has been run on Q2 once, before the freeze, and that run is set aside.** The pilot's citation test built `issues/WHU-T02-ctp-ultra-processed-foods/` on 16–17 October 2026 (session `11b68ac5…`, model `claude-opus-5-5`, nothing committed): stages 1–3 only (premise, research and source store, drafting and binding), under the checks of the tree at `401a597`, before B19–B24, the narrow gate, the conclusion judge and the audit stage existed. Its 18 judgement sentences were then used on 17 October to calibrate the conclusion judge (126 calls, $0.539; `docs/whatholdsup-conclusion-judge.md`), so the conclusion judge's results on Q2 are not out of sample — for the practice run only, not the study.

**Moved out of reach, 20 October 2026** (protocol rev 27, "Practice run"): the issue directory to `archive/WHU-T02/issue/` and its library map `library/issues/ctp-ultra-processed-foods.json` to `archive/WHU-T02/library/`; the nine `used_by` references to it were removed from `library/index.json` and are kept in `archive/WHU-T02/library/index_used_by_removed.json`. The nine held documents stay in the shared library. Why: the practice run (WHU-P02) is built from the question alone, and a drafting session that could open T02's draft, spans and notes on the same question would carry T02's choices into it. `archive/` is excluded from git (`.git/info/exclude`) and lies outside `issues/`, which no drafting step or the daily source sweep reads.

## Cost projection as ruled (20 October 2026)

Budget ruling, protocol rev 26: four questions instead of eight, with the number of items judged unchanged; the audit's second reader reads every flagged sentence plus a seeded 10% of the sentences that held; each judge reads each item once, plus a seeded 20% read a second time. This supersedes the projections in prep rounds 2 and 3 above. No paid call was made for it. Script: `scripts/project_cost.py runs/prep2` (the "as ruled" rows).

**What the code now does.**
- `judge_m1.py` decides which items will be judged from the manifest, before any call. It draws the 20% from them with `--seed` (default 20261020) and writes `replies<tag>/consistency_sample.json` (seed, share, pool, items). Each sampled item's second read follows its first straight away, so the source block is still cached. A rerun that would draw a different sample stops.
- `audit_stage.py`'s second reader reads every sentence that had a finding, at its final wording, plus `random.Random(seed).sample()` of 10% of those that held on first read. The seed and the sampled units are on the manifest.

**Judging: 480 items.** These are 320 M1 claims and 160 M2 conclusions (16 answers × 10). Each judge reads each item once, plus a 20% second read.
- The first-read cost per item is measured: prep round 2's main run (`runs/prep2/replies`).
- A second read is priced as the cache probe measured it, because it is an identical prompt sent straight after the first.
- On OpenAI, M2's ten conclusions per answer are each priced uncached. Prep round 3 found OpenAI caches only an identical prompt.
- M2 is still an estimate: no M2 call has been made.

| Part | Arithmetic | Pilot-sized sources | Sources 2× pilot |
|---|---|---|---|
| M1 Claude | 320 × ($0.1111 first + 0.2 × $0.0145 second) | $36.47 | 320 × ($0.2095 + 0.2 × $0.0180) = $68.20 |
| M1 ChatGPT | 320 × ($0.1392 + 0.2 × $0.0335) | $46.68 | 320 × ($0.2570 + 0.2 × $0.0450) = $85.11 |
| M2 Claude | 16 × ($0.0495 + 9 × $0.0142) + 32 × $0.0142 | $3.29 | $3.29 |
| M2 ChatGPT | 16 × 10 × $0.0765 + 32 × $0.0256 | $13.06 | $13.06 |
| **Judging** | | **$99.50** | **$169.66** |

**WHU: 4 × $31 = $124.** $31 is the protocol's figure per question. The study total is:
- **pilot-sized sources:** $124 + $99.50 = **$223.50**;
- **sources twice the pilot's size:** $124 + $169.66 = **$293.66**.

Both are under $300; the second is $6.34 under.

**Check on the $31.** The figure is the dry-run estimate of $44.37 with the second reader cut from $15.84 to a tenth of that: 44.37 − 15.84 + 1.58 = $30.11. That treats the dry run's $0.032 per sentence as the cost of second-reading a sentence. It is not: the second reader read 7 of the 20 units for $0.640, which is **$0.091 per sentence read**. Under the ruling, the second reader reads F + 10% × (495 − F) sentences, where F is the number flagged. The deskilling re-read corrected 140 sentences.

| Flagged (F) | Second reads | Second reader | WHU per question | Study, pilot-sized | Study, 2× |
|---|---|---|---|---|---|
| 50 | 94.5 | $8.64 | $37.17 | $248.18 | $318.34 |
| 94 | 134.1 | $12.26 | $40.79 | $262.66 | $332.82 |
| 140 | 175.5 | $16.05 | $44.58 | $277.82 | $347.98 |

The other per-question parts are reading $21.29, ruling $1.98, the paid gate $4.63, the conclusion judge $0.54 and changecheck $0.09.

**The per-sentence rate is uncertain.**
- A reading call's cost is mostly its held documents, so cost follows the number of batches more than the number of sentences.
- The dry run's 7 second reads took 3 calls, about 2 sentences a call. A full run's second-read batches would hold up to 20, so $0.091 is probably an upper bound.
- The practice run is where this is first measured. If its measured cost would put the study over $300, Fred decides before the full run (protocol, "Budget ruling").

## Pre-freeze round (21 October 2026)

### Identifiability check, same topic

Per protocol rev 24 this is reported, not a gate. Spend: **$0.17 of $5**, ledger issue `whu-reliability-prefreeze`, 4 calls (Opus 5.5). Data under `runs/prefreeze/identifiability/`, not committed.

**What went in.** All four answers are to the same question, Q2 ("Do ultra-processed foods harm your health?"), so topic no longer separates WHU from the tools as it did in prep round 2.
- **WHU:** WHU-P02's page, exported by `export_whu.py` (markers from its bindings; 42 sentences, all bound, all with markers, all samplable and claim-like), then `blind.py` (the rewrite and deletion list; process sentences not sampled).
- **Tools:** the pilot's Claude, ChatGPT and Gemini answers to Q2 through `blind.py`. Claim-like samplable sentences: Claude 117, ChatGPT 48, Gemini 102.
- 20 per system (every system had at least 20), seed 20261019, shuffled, four batches of 20, each sentence with the ~400 characters before it.

**`identifiability.py` changes:** a system with fewer than N sentences is sampled whole rather than refused; each system's rate is reported against chance (25%) with a one-sided binomial tail; the clues are kept for every system; the result says "reported, not a gate" instead of the old pass/fail field.

**Confusion table** (rows: true system; columns: the guess):

| | WHU | Claude | ChatGPT | Gemini |
|---|---|---|---|---|
| WHU | **20** | 0 | 0 | 0 |
| Claude | 0 | **20** | 0 | 0 |
| ChatGPT | 0 | 0 | **20** | 0 |
| Gemini | 0 | 0 | 0 | **20** |

**WHU was identified 20 of 20 times (100%), against 25% by chance** (P(20 of 20 by chance) = 9.1 × 10⁻¹³). Every system was. Precision for WHU 20/20. With the topic held constant the result is the same as prep round 2's: what identifies a system is its form, not its subject.

**What the guesser said gave each system away** (its own clue words, summarised):
- **WHU:** a measured, hedged register and editorial moves: naming where sources disagree and quoting both, critiquing causal language and media coverage, close trial caveats, full confidence-interval wording, one or two bracket references per sentence. Phrase-level leftovers: "on its own criteria", "the cohorts here", "on this report" (the rule that turns "this page" into "this report" leaves "on this report"), and British spellings the list does not cover ("yoghurt", "savoury").
- **Claude:** terse bullet and timeline entries, class-and-GRADE notes, paired high-numbered citations, and converter leftovers: "Wikipedia" tags and site-chip fragments ("cacfp +2").
- **ChatGPT:** no bracket citations (author-year or none), approximate values in flattened tables, and leftovers: "≈" glued to a label ("HR≈1.62", "N≈44,000"), which rule N01 does not match because a letter precedes it; "a about 15%" (N01 turning "a ~15%" into "a about"); a Mermaid diagram's text; a garbled table cell.
- **Gemini:** ornate, grandiose mechanistic vocabulary, and converter leftovers: "Lane et al.3" glued numerals in table rows and a surviving "[cite: 5]".

**Not changed** (each needs a ruling): the phrase list (British spellings, "on this report"), and the converter defects named above.

### Consistency report: current and superseded pairs

`consistency.py report` now sorts each pair by the ruling it re-asked: **current** (in `rulings/rulings.jsonl` or an audit run that is not withdrawn), **superseded** (in `rulings/superseded/*-rulings.jsonl` or a withdrawn audit run) or **not found**. The issue's rate counts current pairs only; the others are shown apart. A pair logged with no ruling id is matched by its payload sha256 and first decision and text, and the report counts those. WHU-P02: 6 pairs, all current (all six logged with no id, matched by content): 4 of 6 agree on decision and text (67%), 5 of 6 on decision alone (83%), as in the study log.

**Ids.** `ruling.py` has one writer to the ruling log, `rule()`, and it sets `id` on every record before writing (test added). No `ruling.py` record has been made on any issue since c625411 (2026-10-21 01:21Z): WHU-P02's 21 current rulings were made 00:55–01:05Z, before it, and carry no id; they are the only `ruling.py` records in `issues/`.

## Pre-freeze build (21 October 2026, protocol rev 33)

Rulings: protocol rev 33, "Pre-freeze rulings". Spend under ledger issue `whu-reliability-prefreeze2`, cap $8 for the round. Data under `runs/prefreeze/`, not committed.

### Blinding: conversion defects fixed, for every system alike

`blind.py` and `blind_phrases.json`; tests `backend/tests/test_whu_study_blinding.py` (25, one or more per rule).

**Leftover markup removed:**
- **Site-name chips.** A link is a citation marker when its text is its own URL, or one word (optionally followed by "+2") that the URL's host contains, ignoring case and hyphens. That catches "Wikipedia" (en.wikipedia.org) and "cacfp +2" (cacfp.org), which the old lowercase-only rule missed, and they now become `[n]` inside the full stop, also after a closing quote. A link whose text is prose keeps its text.
- **URLs holding parentheses** ("…/S1550-4131(19)30248-7") no longer leave "30248-7)" in the text.
- **"[cite: n]"** escaped as `\[cite: 5\]` in a markdown table is now read as a marker.
- **Numerals glued to "et al."** ("Lane et al.3") become "Lane et al. [3]" for every system; after a closing quote ('"limited"47') too, in the Gemini pass.
- **"<" before a number** ("<20%") is text. The old tag-stripper read it as the start of a tag and deleted everything up to the next ">", here into ChatGPT's diagram; it now strips only tags that start with a letter or "/". Fenced code blocks (ChatGPT's mermaid diagrams) are dropped as markup.
- **Runs of empty table cells** (" ; ; ; ;", where Gemini's export lost a value) collapse to one separator.

**Approximation signs:** N01a turns "a ~15%" into "a roughly 15%" (never "a about"); N01b turns "HR≈1.62" into "HR about 1.62"; N01 is unchanged for the rest.

**"on this page" is deleted** (W15a at a sentence's start, W15b elsewhere), not rewritten to "on this report". "This page" alone still becomes "this report" (W15).

**Spelling:** the British-to-American list moved out of `blind_phrases.json` into `blinding/spelling_us.json`, 360 words (109 before), sha256 `6a0eec29ed625c9e70770588298a541448253d1faeadf87302debb2e3d3db0ad`, pinned in `blind.py` as `SPELLING_SHA256`; a changed list is refused. Whole words, lowercase forms only, as before.

**Unchanged:** every other rule; first person, sentence length and tone ("on its own criteria" stays, as ruled).

### Identifiability check, re-run (reported, not a gate)

Same material as the last round (WHU-P02's export and the pilot's three Q2 answers), same seed 20261019, 20 claim-like sentences per system, Opus 5.5 guessing. Run 2 after the listed fixes found four further conversion defects in the guesser's clues (the parenthesised URL, the "<" deletion, the glued numeral after a quote, the empty cells); they were fixed and the check was run a third time. Spend: $0.16 and $0.16.

| True system (rows) → guess | WHU | Claude | ChatGPT | Gemini |
|---|---|---|---|---|
| WHU | **20** | 0 | 0 | 0 |
| Claude | 0 | **20** | 0 | 0 |
| ChatGPT | 0 | 0 | **20** | 0 |
| Gemini | 0 | 0 | 0 | **20** |

The same in run 2 and run 3: **every system identified 20 of 20** (chance 25%; P = 9.1 × 10⁻¹³ each). The guesser called its WHU guesses "high" confidence 15 of 20 times last round, 13 in run 2 and 8 in run 3; WHU's 20 sentences were identical in runs 2 and 3, so that fall is at least partly run-to-run variation, not the fixes.

**What the guesser said gave each system away (run 3).** No clue names a converter leftover any more except Gemini's lost-value table rows ("garbled table").
- **WHU:** a plain, measured, hedged register; full confidence-interval wording; naming where sources disagree and quoting both; critiques of media headlines and causal language; "the cohorts here", "on its own criteria" (the system's voice, which stays).
- **Claude:** terse bullets, "Results:" and "How to read this" style, policy timelines, high and paired citation numbers.
- **ChatGPT:** no bracket citations (author-year inline, or none), summary tables with a limitations column, "about"/"roughly" values, "For example", "e.g." lists.
- **Gemini:** ornate, florid mechanistic vocabulary ("engineered hyper-palatability", "intrinsic cellular matrix", "totality of … evidence demonstrates"), title-case evidence tables with class and GRADE columns.

So with conversion defects removed, each system is still told apart by its writing, which the rules forbid rewording. The gate remains the bias test (passed in prep round 3).

### M2 behaviour check: not frozen

**What ran.** `scripts/judge_m2.py` (new; built on judge_m1's API calls, metering and refusal rule) ran the M2 prompt (`prompts/m2_conclusion_calibration.md`, sha256 `aebfffc11d659a5fff6d594218856a90ff4d1ed7ffd979a5dca511661b6bbe78`, unchanged since d3a5b05) with both judges (Opus 5.5, gpt-6-astra), one read each.
- **Answers:** the four blinded answers to Q2 (WHU-P02, Claude, ChatGPT, Gemini), labelled A–D for the judges.
- **Conclusions:** Q2 has no review-based answer key, so the conclusions are the answers' own. There are three per answer: its overall verdict, whether processing itself causes harm (Gemini: that not all foods in the category are equally harmful), and the feeding-trial evidence. Claude Code wrote each in the key's fields, quoting the answer verbatim.
- **Items:** every conclusion judged against every answer, 12 × 4 = 48 items, 96 calls. An answer judged against its own conclusion should come back Matches.
- Data in `runs/prefreeze/m2/`, not committed.

| | Claude judge | ChatGPT judge |
|---|---|---|
| Valid JSON, in the required form | 48/48 | 48/48 |
| Quotation verbatim in the answer | 48/48 | 48/48 |
| Refusals | 0 | 0 |
| Labels: Matches / Overstates / Understates / Contradicts / Omits | 29 / 13 / 6 / 0 / 0 | 18 / 26 / 4 / 0 / 0 |
| Own-answer conclusion labelled Matches | 12/12 | 7/12 |
| Calls with a cache hit | 44/48 | 0/48 |
| Cost per call: mean, median, max | $0.019, $0.016, $0.075 | $0.065, $0.067, $0.092 |
| Cost | $0.91 | $3.10 |

**Agreement between the judges: 35 of 48 (73%).** All 13 disagreements go one way: the ChatGPT judge says Overstates where the Claude judge says Matches (11) or Understates (2).

**What failed: the framing rule is applied two ways.** In 12 of the 13 disagreements, the ChatGPT judge's reason is the prompt's framing paragraph:
- The answer calls a trial "landmark" or "the first", or ranks a body of evidence "the strongest causal evidence", and the conclusion does not support that framing, so it says Overstates. That follows the prompt's wording: "If the review's conclusion does not support such framing, that is Overstates, even when the rest matches."
- The Claude judge sees the same words and reads them in context: relative to the weaker observational evidence, or within the conclusion's own certainty ("confirm", "demonstrates"). It says Matches.
- The ChatGPT judge's five Overstates on own-answer conclusions have the same cause. The conclusion fields carried the answer's verdict but not its "landmark" or "strongest" wording, so those words count against it.
- The thirteenth disagreement (Gemini's subgroup conclusion against ChatGPT's answer) is a real reading difference: Understates against Overstates on an answer that is inconsistent about subgroups.

**Not frozen.** The form is clean, but the two judges split systematically on one paragraph of the prompt. At this rate about a quarter of M2 items would go to people, every one in the same direction. The ambiguity is when a review conclusion "supports" a framing word, especially one the answer attaches to a study rather than to the conclusion ("a landmark trial") or uses comparatively ("the strongest evidence is about overeating"). That needs a ruling, then a re-test, before M2 is frozen.

**Caveats.**
- These conclusions are not review conclusions; they come from the answers themselves.
- A Claude instance wrote them, and only the ChatGPT judge departs from Matches on them.
- The ChatGPT judge got no cache hits even with a `prompt_cache_key` per answer, as in prep round 3. M2 on OpenAI is priced uncached.

### M2 v2: frozen (advisor ruling on the framing paragraph, 21 October 2026)

**The change.** Line 23 of `prompts/m2_conclusion_calibration.md` (the framing paragraph) is replaced word for word by the advisor's ruling: "Judge certainty, not vocabulary", with what counts as Overstates and what does not, including study descriptors, framing caveated in the same passage, and framing no stronger than the review's own certainty language. v1 is kept as `prompts/m2_conclusion_calibration_v1.md` (sha256 `aebfffc1…`); its replies stay in `runs/prefreeze/m2/replies/`.

**Frozen: M2 v2, sha256 `64a5a5b667e697b55e4f42f2473b3b5516c5e9ceec0f0d88a878cdc9eb38bb33`.** It is pinned in `judge_m2.py` (`PROMPT_SHA256`), which refuses a changed prompt; the test is `backend/tests/test_whu_study_judge_m2.py`.

**Re-run.** The same 48 items, both judges, one read each, into `replies_v2/`. Spend $4.10 (Claude judge $0.94, ChatGPT judge $3.16), of the $5 authorised.

| | Claude judge | ChatGPT judge |
|---|---|---|
| Valid JSON | 47/48 (one reply cut off at the 1,024-token output limit) | 48/48 |
| Quotation verbatim | 47/47 | 48/48 |
| Refusals | 0 | 0 |
| Labels: Matches / Overstates / Understates | 30 / 11 / 6 (+1 unparsed) | 30 / 13 / 5 |
| Own-answer conclusion labelled Matches | 12/12 | 12/12 |

**Agreement between the judges: 45 of 48** (35 under v1); the freeze rule needed 42. The three disagreements:
- the cut-off reply (D3 against answer A): its visible label is Matches, the same as the ChatGPT judge's;
- B1 against answer C, Matches against Overstates;
- D2 against answer C, Understates against Overstates, the same split as under v1.

**A1 against answer B** (the answer gives a type 2 diabetes association "GRADE moderate" where the conclusion has very low to low): **Overstates from both judges** (v1: Matches from Claude, Overstates from ChatGPT).

**Did anything move from Overstates to Matches only because of a study descriptor?** Yes, three of the ChatGPT judge's labels: B3, C3 and D3 against answer C. Under v1 each reason named only "first" and "landmark".
- **C3 and D3:** the conclusions are themselves "causally demonstrated" and "confirm", so the v2 exemptions apply twice over.
- **B3 against answer C** is the one to look at: B3's conclusion has moderate certainty, and the answer also says the trials "causally demonstrated" and "uniquely demonstrate" the effect. Both judges now say Matches.
- Another three moved because a ranking was caveated in the same passage ("the strongest causal evidence, but it has limits"): A3 and B3 against answer B, C3 against answer B.
- The other nine had mixed v1 reasons (descriptors together with certainty wording).

**Runner note, not changed:** the Claude judge's output limit (1,024 tokens) cut off one reason in 48. Raising it is a runner change for Fred to rule on.

### Sampling frames (no draw for the study)

Built by `scripts/frames.py` and committed as numbered files in `frames/`, each with its queries (URL, UTC date, HTTP status, sha256 of the reply) and every candidate's result on every test. No drafting session reads them (RUN.md, "Do not read"). Tests: `backend/tests/test_whu_study_frames.py`. All queries were made on 21 October 2026. A rebuild re-logs a cached reply under the rebuild's time.

| Frame | Registry and query | Candidates | Eligible |
|---|---|---|---|
| Cochrane | PubMed E-utilities: `"Cochrane Database Syst Rev"[ta] AND 2024/01/01:2026/09/30[dp]`, then efetch | 1,054 | **718** |
| Campbell | PubMed E-utilities: `"Campbell Syst Rev"[ta] AND 2024/01/01:2026/09/30[dp]` | 200 | **24** |
| IPCC AR6 headline statements | no API; the four official "SPM headline statements" pages on ipcc.ch, one entry per statement | 76 | **64** |
| National Academies, 2024-01 to 2026-09 | no API; the catalogue's listing pages, filtered by year | candidate list only (below) | drawn by the draw procedure |

**How each test is applied** (the text is in each file's `tests`):
- **A review, not something else** (Cochrane, Campbell). Excluded on title, publication type or the abstract's first words:
  - protocols (314 of Cochrane's candidates are protocols: "This is a protocol for a Cochrane Review"; 140 Campbell entries are protocols, evidence and gap maps, title registrations, editorials, corrections or scoping reviews);
  - withdrawn or retracted reviews.
- **Published in the window.** PubMed's electronic publication date (else the issue date); the AR6 report's year (2021–2023).
- **States a certainty grade.**
  - Cochrane and Campbell: the PubMed abstract carries a GRADE certainty or quality term ("low-certainty", "certainty of the evidence", "GRADE", "strength of evidence"). Fails among the reviews: 14 of 740 Cochrane, 36 of 60 Campbell (many Campbell abstracts give no grade).
  - IPCC: the headline statement itself carries calibrated language (a confidence level or a likelihood term). 12 of WGI's 14 headline statements carry none: in WGI the calibrated terms sit in the sub-paragraphs (A.1.1 …), not in the headline sentence, so they fail. That is the rule as written. **This needs a ruling** if WGI should be represented.
- **Public abstract.** PubMed holds an abstract. Among the reviews, every Cochrane review has one and one Campbell review does not; the other records with no abstract were already excluded (editorials, corrections and the like). The IPCC statements are published in full.
- **Not a WHU topic.** The title (IPCC: the statement) matches none of the patterns in `EXCLUDED_TOPICS`: melanoma and mRNA cancer vaccines; CDK4/6 inhibitors; AI use and cognition; exercise and depression; ultra-processed food; intermittent fasting; vitamin D. These exclude 8 Cochrane reviews: "Exercise for depression", "Intermittent fasting for adults with overweight or obesity", and six on vitamin D. Excluding every vitamin D review, not only those on people over 60, is a choice. **It needs confirming.**
- **Not tested here:** "can be put as one plain question". The protocol leaves that to the closer reading after the draw.

**What could not be determined:** the PubMed records are as of the query date (recent Cochrane reviews may not yet be indexed). For the National Academies, nothing is tested on the list: each test runs at the draw, one candidate at a time.

### Draw procedure, for a frame with no full eligible list

Ruled 21 October 2026, after the National Academies site rate-limited a full crawl (HTTP 429 after a few requests, with no Retry-After header). It applies to any frame whose eligible list was not built in full. Code: `frames.py draw-<frame> --seed N`.
1. Take the frame's candidate list, numbered `n` in its fixed order (National Academies: by publication id).
2. Shuffle the numbers with the seed: `random.Random(seed).shuffle(order)`.
3. Test eligibility in that order (the same tests as above; a National Academies report "states a certainty grade" when its OpenBook Summary chapter uses at least three levels of one evidence scale, or two levels of confidence or certainty language).
4. **The first eligible candidate is the draw.**
5. A candidate whose test could not be completed (a page not fetched) is logged as undetermined and passed over, never drawn.
6. Every candidate checked is logged, with each test's result and reason, in `frames/draws/<frame>-seed<N>.json`, with the frame file's sha256. A draw is made once; the script refuses a second draw with the same seed.

**National Academies candidate lists** (the catalogue's "Consensus Study Report" label, from the listing pages alone; 20 s between requests, backing off on 429):

| List | Listing query (year filter) | Listing pages | Catalogue entries | Consensus Study Reports (candidates) | File |
|---|---|---|---|---|---|
| Study, 2024-01 to 2026-09 | `publications/all?publication_date[from]=2024&publication_date[to]=2026` | 52 | 872 | **186** | `frames/nasem.json` |
| Practice, 2017–2023 | `publications/all?publication_date[from]=2017&publication_date[to]=2023` | 143 | 2,342 | **524** | `frames/nasem-practice.json` |

Each file logs every listing query (URL, UTC time, HTTP status, sha256), all made on 21 October 2026, and the count of cards by label. The other cards are proceedings (235; 655), annual reports, special publications, issue papers, rapid expert consultations, and 421 and 1,127 cards with no label. The catalogue gives a year, not a date, so a 2026 report published after 30 September is caught by the draw's date test (Crossref's month). The site returned HTTP 429 four times during the build; each was waited out and the page fetched.

### Practice draw (WHU-P03), 21 October 2026

`frames.py draw-nasem-practice --seed 20261021`, against `frames/nasem-practice.json` (sha256 `a22731cd…`). Log: `frames/draws/nasem-practice-seed20261021.json`.
- 33 of 524 candidates were checked; the 33rd was eligible and is the draw.
- Of the 32 passed over, 29 failed "states a certainty grade" (their Summary chapter has no graded evidence scale, or uses fewer than three levels of one) and 3 were undetermined: no Summary chapter found in the OpenBook contents (one is a Spanish translation). None failed on topic or date.
- The drawn report's Summary uses four levels of one evidence scale and is free to read online.
- **Known gap in this log:** the Summary-chapter reads made during this draw were not written to `queries_logged` (the fetch was made with logging off, a leftover of the full-crawl code). Each candidate's result and reason are logged; the URLs, times and statuses of those reads are not. Fixed after the draw (`kind="openbook"`, with a test); the study draw will log them. The practice draw is not re-run: a draw is made once.

The question, written from the report's subject without naming it, is in `issues/WHU-P03-antimalarial-prophylaxis/issue.json`. The report itself is named only below.

## Private notes (not for a drafting session)

A drafting session does not read this section (RUN.md, "Do not read").

- **WHU-P03's source report:** National Academies of Sciences, Engineering, and Medicine (2020), *Assessment of Long-Term Health Effects of Antimalarial Drugs When Used for Prophylaxis*, doi:10.17226/25688, publication id 25688 (candidate n=258 in `frames/nasem-practice.json`).
