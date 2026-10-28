# "Check an AI answer": internal pilot

Status: written 2026-10-28, before any pilot code. Internal only. Exploratory: outside the
reliability study's H1 and H2, and it changes no study record, result or rule. The test, the
sample and the pass bar below are fixed by the commit that adds this file, before any run.
Budget: Fred's approval of 2026-10-28 (option B), `--cap 35` on ledger issue `whu-check-pilot`.

## 1. What it is

A tool that takes an AI research answer with citations and says, for each factual claim in it,
whether the source it cites backs the claim. It is built from the reliability study's own code,
so the pilot can be tested against the study's own labels.

## 2. Input

A pasted AI answer with its citations, in any capture format the study handled
(`study/whu-reliability/blinding/adapt.py`):

| Format | adapt.py | Answers in the study |
|---|---|---|
| inline Markdown links (the report section) | `report_section` | Claude Research S01-S04 |
| ChatGPT page-data markers 【…】 with the capture's citation table | `chatgpt_lenticular` | ChatGPT S01, S02 |
| ChatGPT `[[k]](url)` | `chatgpt_bracketed` | ChatGPT S03, S04 |
| Gemini Markdown export, "Works cited" list | `report_section` + `works_cited` | Gemini S01, S02 |
| Gemini HTML export | `gemini_html` | Gemini S03, S04 |
| Claude "Download as Markdown", numbered "## Sources" | `claude_sources` | Claude S05-S08 |
| Perplexity "Download as Markdown", `[^n]` and "## References" | `perplexity_sources` | Perplexity S01-S04 |

A pasted answer without a capture header is read as if it were the report section (the code
prefixes the "## Report" heading `report_section` looks for). The format is named by the caller
or, if not named, detected from the text by the first rule that applies: an HTML document
(Gemini HTML); 【…】 markers; `[[k]](url)`; `[^n]` markers with a "References" heading; a
"Works cited" heading; a numbered "Sources" heading; otherwise inline links. No wording is
changed; an answer the adapter cannot read stops with the adapter's own error.

## 3. Pipeline (the study's code, reused, not copied)

1. **Adapt** the answer (table above).
2. **Sentences and citations**, as `prepare_scoring.py` did: `blind.from_markdown` numbers the
   links, `blind.blind` and `blind.sentence_rows` split the text into sentences with their
   ~400-character context (the blinding rules run, as they did for the study's judge). A
   claim is a sentence `identifiability.claim_like` accepts (samplable, 8 to 70 words, a number
   or a citation marker). Each claim's citations are its `[n]` markers looked up in the
   answer's reference list (`adapt.fragment_free` on each address).
3. **Limit.** The first 40 claims in the answer's order are checked; the rest are listed as not
   checked. (40 is the preview's limit.)
4. **Open-licence copies only.** For each cited address, the work's licence is read before
   anything is fetched: Europe PMC's `license` field (`find_access.epmc`, by the PMCID, PMID or
   DOI in the address, `find_access.ids_from_url`), else an Unpaywall open-access location whose
   `license` starts `cc` (`find_access.unpaywall`). Accepted licences: any Creative Commons
   licence (`cc0`, `cc by` and its variants). A work with none is not fetched and is not judged.
5. **Snapshot**, for a work with an open licence: `retrieve_sources.retrieve`, routes (a) the
   script, (b) curl, (c) open-access locations, in that order; held only if `snapshot.extent`
   calls the text full text or abstract only. Route (d) (a person's browser) is never used.
6. **Judge**: `judge_m1.py`'s M1 v3 prompt (`prompts/m1_citation_support.md`, its sha256
   checked against `judge_m1.PROMPT_SHA256` before any call), built by `judge_m1.build`, sent by
   `judge_m1.call_claude` (Claude judge, `judge_m1.CLAUDE_MODEL`, only), parsed by
   `judge_m1.parse`, labelled by `judge_m1.final_label`. Long sources by `judge_m1.chunk`, and
   `judge_m1.delivery_problems` as in the study. **First read only**: no second read, no
   consistency sample. A refused call is retried once unchanged, as in the study.
7. **Label** per claim, with the reason:

| Pilot label | When | Reason shown |
|---|---|---|
| BACKED | M1 label Supported | the judge's reason and its quoted span |
| NOT BACKED | Overstates, Understates, Absent, Wrong source, Contradicted | the M1 label, the judge's reason and span |
| NO SOURCE | the sentence has no citation marker (the study's UNCITED) | "no citation" |
| COULDN'T CHECK | any cited work with no open-licence copy, or not retrieved, or Unreachable, NOT_VERIFIABLE_ABSTRACT (Absent on an abstract only), INCOMPLETE_SOURCES (the delivery check), REFUSED, or a reply that does not parse | which source and why |

As in the study, a claim is never judged on part of its sources: if any cited work cannot be
checked, the claim is COULDN'T CHECK. This mapping is the study's own (`analyse.py`
`M1_PASS`/`M1_FAIL`; `scorecard/measures.py` supported / cited_not_supported / uncited).

## 4. Sample

8 study answers, 2 each from Claude Research, ChatGPT deep research, Gemini Deep Research and
Perplexity Deep Research, on WHU-S01 to WHU-S04 only (ChatGPT searched the web there).

Draw: `rng = random.Random("%d/check-pilot" % SEED)`, SEED the freeze commit
`5d83e9b8025312923f3fb8ea2d5de3b47c212362` read as a hexadecimal integer (written in decimal,
as `prepare_scoring.py` writes it). For each system in the order Claude, ChatGPT, Gemini,
Perplexity: `sorted(rng.sample(["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"], 2))`, one generator
for all four draws. The input for each answer is its study capture
(`~/Projects/whu-study-private/answers/<q>/`, `gemini.raw.html` for Gemini S03/S04), read in
the format `prepare_scoring.tool_answer` used; Perplexity's are the re-run captures the study
scored (not the set-aside personalised ones).

## 5. The test (fixed before any run)

**Same sentence.** The pilot's sentences for an answer are compared with the study's
`scoring/blinded/<q>/<system>.sentences.jsonl` (Perplexity: `scoring/perplexity/blinded/`) by
index and text. If they differ, that is reported, and sentences are matched by text only.

**The study's label** for a sentence is its Claude-judge first-read M1 label
(`scoring/m1/replies/claude/<item>.json`, `label`; Perplexity `scoring/perplexity/m1/replies/claude/`),
item to sentence by `key_map.json`; UNCITED for a drawn sentence in `uncited.json`; an item with
no reply because no cited source was held counts as COULDN'T CHECK. It is mapped to the four
labels by §3's table.

**Reported:**
- **Agreement**: of the sentences both the study drew and the pilot checked (within its 40), where
  neither label is COULDN'T CHECK, the share with the same label. Also, with its n: agreement
  counting COULDN'T CHECK as a label; agreement on cited sentences only (NO SOURCE left out); and
  the 4x4 table of study label against pilot label.
- **COULDN'T CHECK share**: of all claims the pilot checked (up to 40 per answer, all 8 answers),
  the share labelled COULDN'T CHECK, with the reasons counted (no open licence; not retrieved;
  abstract only; delivery check; refusal; unparsed).
- **Dollars per answer**: ledger spend on `whu-check-pilot` divided by 8, and per answer.

**Pass bar:** all three must hold.
1. Agreement at least 90% on the claims both labelled (the first agreement figure above).
2. COULDN'T CHECK on 20% of claims or fewer.
3. $5 per answer or less (total spend divided by 8).

Failing any of these is a result, not a reason to retune and re-run. The pilot is run once. A
second run is allowed only after a technical failure, logged with evidence first; nothing about
prompts, rules, limits or the sample changes between runs.

**Known expectations, stated before the run.** The open-licence rule will leave many sources
uncheckable (news pages, guideline pages, IPCC and other reports without a Creative Commons
licence; paywalled articles), so condition 2 may well fail; the study judged any held snapshot.
Agreement is measured only where both read the same source, but the study's snapshot and the
pilot's may be different copies (a different route or version).

## 6. Spend

Before any call: a $0 preparation pass (adapt, sentences, licences, snapshots, and
`count_tokens` on every prompt) prints the worst-case estimate, judge_m1's formula (every input
token at the cache-write price plus `CLAUDE_MAX_OUT` output tokens per call). If the estimate is
over $35, the pilot STOPs before any call. Before each call: `spend_ledger.check_cap`
(caps.json's day cap and the issue cap) and the run's `--cap 35` on `whu-check-pilot`; either
over means STOP. No override is used. Calls are metered through `spend_ledger.metered` on issue
`whu-check-pilot`.

## 7. Out of scope

No public endpoint for the pilot, no storage of anyone else's text, no sign-in. The pilot's
inputs are the study's own captures; its outputs stay in the private folder
(`~/Projects/whu-study-private/check_pilot/`), and only counts are committed.

## 8. Code

`study/whu-reliability/check_pilot/`: `pipeline.py` (steps 1-7, importing the study modules by
path), `run_pilot.py` (the sample, the estimate, the run, the comparison), and offline tests in
`backend/tests/test_whu_check_pilot.py` on one recorded answer with recorded sources and a
recorded judge reply.
