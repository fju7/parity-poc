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
