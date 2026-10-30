# WHU next phase: validity plan (FROZEN)

Drafted 2026-10-30 by Claude Code (session VP, the scoring side) from the approved plan
(`~/Projects/whu-study-private/next_phase/next_phase_plan.md`, "WHU next phase: validity checks and a leaner
WHU", 29 Oct 2026). Draft 2 folds in the advisor's rulings of 2026-10-30 on draft 1 (marked "Ruling"). Approved
for freezing by the advisor on 2026-10-30 after a second review (open items 1-3 answered: the Google cache-write
rate is unused, the note kept; the check-10 wrapper accepted on the terms in §8; the line on pilot v4 added to §9).
**No check ran before the freeze.** It is frozen by the commit that adds this version, together with the files it names as frozen with it (§8, §4, §6, §9); that commit's full
40-character hash, read as a hexadecimal integer, is **SEED** for every draw below (the round-1 seed rule,
`quarterly/round1_protocol.md` §1). "R1SEED" means round 1's seed, `5f4a928b757d7f47c1ba8ed47600ced4a7a69f12`
read the same way.

Everything here is outside the study's H1/H2 and changes no study or round-1 record, result or rule. All
figures are labelled "judged by AI models" except check 5's human labels. Nothing is published, deployed or
announced.

## 0. Common rules

- **Data.** Round 1's private scoring run, `~/Projects/whu-study-private/scoring/quarterly/round1/`
  (`m1/items.json`, `m1/key_map.json`, `m1/uncited.json`, `m1/replies/{claude,openai}/` first reads,
  `m1/replies_repeat/`, `m1/sources/`, `m2/`, `blinded/<q>/<system>.sentences.jsonl`), and its committed
  results, `quarterly/round1_scoring/round1_ai_only.json` (§6A/§6B as pre-stated) and
  `posthoc_whu_sentence_kinds_round1.json`. Study records only where named (check 4). Superseded reply
  folders (`replies_superseded_*`) are never used.
- **Comparisons a check can overturn ("the seven").** Of round 1's §6A comparisons (WHU against each tool,
  two-judge combined, all four questions), the ones whose 95% interval excludes zero under **both** existing
  judges alone: M1 failure vs Claude Research (-0.50), ChatGPT (-0.88), Gemini (-0.70), Perplexity (-0.30);
  M2 Overstates vs ChatGPT (-0.26) and Gemini (-0.58); M2 Understates+Omits vs ChatGPT (-0.42). Every other
  comparison already has an interval including zero under at least one judge and is reported, not tested.
  Every check reports its figures with and without WHU-Q1-02 (round 1's rule).
- **Analysis code.** `quarterly/analyse_round1.py`'s rules (analyse.py via analyse_eight.py: EVERY
  abstract-only rule, UNCITED counted as a failure by code, a combined view counting each judge's label,
  bootstrap over whole questions, 10,000 resamples). A new judge enters as one more label source; nothing in
  those rules changes.
- **Spend.** Each paid item has its own ledger issue and `--cap`, prints its estimate before any call and
  STOPs if the estimate is over its cap. No `WHU_SPEND_OVERRIDE`, no `--waive`, no `--no-verify`. Phase total:
  $350 including step 1 (Fred's approval), tracked by summing the phase's ledger issues
  (`spend_ledger.py --issue`) before each paid item.
- **Day caps (Ruling 3).** caps.json `default_per_day` is raised from $25 to $60 for this phase (committed
  `e454d9f`, with the note "Raised from 25 to 60 by Fred on 2026-10-30 for the WHU validity phase
  (validity_plan.md); back to 25 when the phase ends or at 2026-11-30T23:59Z, whichever is first; the $350
  phase cap is unchanged."). Judging items use ledger issues with the existing judging prefix
  (`whu-reliability-judging-validity-c1`, `-validity-c4m2`, `-validity-c10`, `whu-reliability-judging-lean`), so
  `study_judging_per_day` ($150) applies to them as well. Both day caps are checked before every judging stage:
  the new runners call `spend_ledger.check_day_cap` and the judging-day check themselves; for stages run
  through `judge_m1.py` / `judge_m2.py` (which check only the judging day cap), `check_day_cap` is called by
  the stage's wrapper before it starts, and the runners are not changed. While the raise stands,
  `backend/tests/test_whu_study_judging_cap.py` fails (it asserts 25), as during the 29 October raise; the test
  is not changed.
- **Prices** (US $ per million tokens), from `backend/scripts/spend_ledger.py` PRICES (and the gate's copy,
  held equal by test): `claude-opus-5-5` in 4.00, out 20.00, cache write 5.00, cache read 0.20;
  `claude-sonnet-5-5` 2.00 / 10.00 / 2.50 / 0.10; `claude-haiku-5-5` 0.10 / 0.50 / 0.125 / 0.01 (prompts over
  100,000 tokens: 0.50 / 2.50 / 0.625 / 0.05). **`gemini-4-argon` (Ruling 1, committed `a9593f8`):** input
  2.00, output 10.00 (thinking counts as output), cache read 0.10, through 2026-11-30; from 2026-12-01 input
  4.00, output 20.00, cache read 0.20 (`spend_ledger.rates()` picks the row by the call's UTC date; test
  `backend/tests/test_whu_validity_prices.py`). The row's cache-write rate is set to the input rate: the ruling
  gives none, so that is an inference, and no runner here sets an explicit cache. `gpt-6-astra` is not in the
  ledger's table: input 10.00, cached input 1.00, output 50.00, from `judge_m1.OPENAI_PRICE` (standard tier,
  checked 2026-10-19).
- **Separation.** Keys, judge replies, planted-defect records and every result here stay with the scoring
  side. None is shown to a lean-WHU drafting session, and no key text or planted location goes into a
  committed file (hashes only).

## 1. Check 1: a third judge from Google

**Key and model (Ruling 1): in place.** `GEMINI_API_KEY` is in `backend/.env` (checked by name; the value is
never printed or logged). `google-genai` 2.34.0 is installed in `backend/venv` (via `python -m pip`: the venv's
`pip3` shim points at the repo's old path). The id was confirmed by a free `models.list` call on 2026-10-30:
`models/gemini-4-argon` is listed. Google's flagship, not a preview. Priced as §0.

- **Data:** every round-1 M1 item judged by both existing judges (217; the 10 delivery-check items and 3
  with no held source stay excluded, as in round 1), and every M2 item (91: WHU 19, Claude 19, ChatGPT 19,
  Gemini 15, Perplexity 19). ChatGPT's 78 M1 items are UNCITED by code and need no judge.
- **Procedure:** a new runner, `study/whu-reliability/next_phase/judge_google.py`, imports `judge_m1` and
  `judge_m2` unchanged and uses their prompt builders, the same delivered text (the same chunks Claude was
  sent, so the third judge reads exactly what the other two read), their parsers and their refusal rule.
  Prompts: M1 v3 (`prompts/m1_citation_support.md`, sha256 04efb531…), M2 v2
  (`prompts/m2_conclusion_calibration.md`, sha256 64a5a5b6…), verified by hash before the first call. First
  reads only (no repeat). Items in a random order across systems and questions
  (`random.Random("%d/check1" % SEED)`). Default sampling settings; the model string each reply returns is
  recorded, and a reply under any other model id stops the run. Cost per call from usage metadata (prompt,
  cached and candidate-plus-thinking token counts) at `spend_ledger.rates("gemini-4-argon", n, at=call time)`,
  written to the ledger. Replies to `~/Projects/whu-study-private/scoring/quarterly/round1/{m1,m2}/replies/google/`.
- **Analysis:** §6A recomputed with Google alone, three judges combined, and (check 2) OpenAI+Google.
- **Conclusion changes if**, for any of the seven: Google's WHU-minus-tool difference lies outside the range
  of the Claude-judge and OpenAI-judge differences by more than 5 percentage points in the direction that
  narrows WHU's lead, **or** Google's 95% interval includes zero (or reverses). A gap outside the range that
  widens WHU's lead is reported, not a change. **Flag:** Google judging Gemini's answers is a self-preference
  risk of its own; the two Gemini comparisons are reported with that label.
- **Cost:** about 13.5M Claude-token-equivalents of documents across M1 (`cost_projection.json`); at the
  ruled price, ~$27 input plus ~$5 output for M1 (2,000 output tokens per item assumed, thinking included),
  ~$3 for M2: **~$35, up to ~$50** if Google's tokenizer or thinking runs higher. **Cap $55**, ledger issue
  `whu-reliability-judging-validity-c1`.

## 2. Check 2: the non-Anthropic-judge view ($0 after check 1)

- **Data:** check 1's replies and round 1's OpenAI first reads.
- **Procedure:** §6A recomputed with the Claude judge's labels removed: OpenAI alone (already in
  `round1_ai_only.json`), Google alone, and OpenAI+Google combined (each label counted). Self-preference read:
  the Claude judge's WHU rate minus the non-Anthropic combined WHU rate, against the same difference for
  Claude Research and for the three non-Claude tools.
- **Conclusion changes if**, for any of the seven, the OpenAI+Google combined 95% interval includes zero, or
  the combined WHU lead is less than half the two-judge (Claude+OpenAI) lead. **Self-preference flag** if the
  Claude judge favours WHU or Claude Research by more than 5 points beyond what it does for the non-Claude tools
  (difference in differences). For reference, round 1 as scored: WHU M1 failure 8.9% (Claude judge) against
  15.2% (OpenAI judge).
- **Cap:** $0. If check 1 has not run, check 2 reports OpenAI alone and says so.

## 3. Check 3: identifiability

- **Data:** round 1's blinded M1 sentences as the judges saw them (`blinded/<q>/<system>.sentences.jsonl`,
  sentence plus the ~400 characters before it), and the 19 blinded answers M2 judges saw.
- **Procedure:** `blinding/identifiability.py` (the study's code), with two changes, both in the runner, not
  the module's rules: chance is 1/5 (five systems; the module's `binom_tail` default is 1/4), and the guesser
  is each judge model in turn (`claude-opus-5-5`, `gpt-6-astra`, `gemini-4-argon`). **Sample:** for each system,
  20 of its round-1 M1 sentences (`random.Random("%d/check3/%s" % (SEED, system))`; all if fewer), 100
  sentences, shuffled together, in batches of 20; plus each of the 19 whole answers, one per call. Reported: the
  confusion table per guesser, each system's identification rate against 20% with a one-sided binomial tail,
  and the clues named.
- **Conclusion changes if** WHU is identified in at least 9 of 20 sentences by a guesser (one-sided tail
  p ≤ 0.01 against 0.20) **and** WHU's M1 failure rate (that judge's own labels) differs between WHU items it
  identified and items it did not by 15 points or more. With 20 WHU items the second half is descriptive; a
  "yes" sends the item to the advisor, not to an automatic verdict.
- **Cost:** ~100 short sentences and 19 answers per guesser, three guessers; **~$2-4. Cap $5**, issue
  `whu-validity-c3-ident` (not a judging issue: the $60 day cap applies).

## 4. Check 4: second answer keys by a non-Anthropic model

- **Scope (Ruling 2):** the four round-1 questions (WHU-Q1-01 to -04) and two study questions, **WHU-S01
  (Cochrane) and WHU-S02 (Campbell)**. S03 and S04 (IPCC; key sources ~0.9M and ~3.0M tokens) move to round 2's
  budget.
- **Model (Ruling 1):** `gemini-4-argon`, a third company, so neither existing judge scores against its own
  company's key. Drafter and checker are separate calls with no shared history, as protocol §2's separate
  instances.
- **Data:** the same full texts the first keys used, `~/Projects/whu-study-private/keys/quarterly/round1/<q>/source/`
  and `~/Projects/whu-study-private/keys/WHU-S0{1,2}/source/`, each file verified against its `sources.sha256`
  before use. Where a source is held both as XML and as text (`fulltext.xml` and `fulltext.txt`), the text file
  is used; PDFs are given as their `.txt`. A question's text over 900,000 tokens is given in the order its
  `sources.sha256` lists the files and cut at 900,000, the cut logged.
- **Prompts (Ruling 6), frozen with the plan:** `next_phase/prompts/key2_draft.md` (sha256 0f866872…) and
  `next_phase/prompts/key2_check.md` (sha256 55c0fbca…). They carry protocol §2's key unchanged in content:
  up to five main conclusions on the question, each with direction, size, certainty in the review's own words,
  scope, and one to three quotations copied character for character with their section. The checker returns
  keep / correct / drop / add for each conclusion, with a reason. The output fields are `key.json`'s
  (`statement`, `direction`, `size`, `certainty`, `scope`, `quotes[]`), so `judge_m2.py` reads a second key
  unchanged. Inputs: the question as committed for round 1 (or the study), a one-line description of the
  review (its citation), and the texts.
- **Procedure:** draft, then check; every quotation found word for word in the held text by code (a quote not
  found is a failed conclusion, dropped and logged); the checker's corrections applied by code; the drafter and
  checker see no first key, answer, judge reply or result. Second keys frozen (sha256 in
  `next_phase/keys2_manifest.txt`; text private, `~/Projects/whu-study-private/keys2/`) before any rescoring.
  **Rescoring:** every answer to those six questions against every second-key conclusion, M2 v2, all three
  judges, first reads, `judge_m2.py`'s code (Google through `judge_google.py`). **Where the keys differ:** a
  second-key conclusion is "matched" to a first-key conclusion when their quoted passages overlap by at least
  half of the shorter quote's characters (offsets in the same held text, by code); rates are reported on all
  second-key conclusions and on unmatched ones.
- **Conclusion changes if**, under the second key: WHU's M2 Overstates+Contradicts or Understates+Omits rate
  rises by 10 points or more (round 1, or S01-S02 against the study's own figures); or any of the three M2
  comparisons among the seven has a 95% interval that now includes zero; or any WHU-vs-tool M2 point difference
  reverses sign by more than 5 points.
- **Cost:** the texts as given are ~1.43M tokens (text files only: Q1-01 0.18M, Q1-02 0.05M, Q1-03 0.18M,
  Q1-04 1.02M cut to 0.90M, S01 0.03M, S02 0.08M; characters / 2.674), each read twice (draft, check): ~$6-8
  at the ruled price; rescoring ~140 answer-conclusion items with three judges ~$20.
  **~$30. Cap $40**: issues `whu-validity-c4-keys` (drafting, cap $12) and
  `whu-reliability-judging-validity-c4m2` (rescoring, cap $28).

## 5. Check 5: the human probability sample ($0; Fred's time)

**Frame.** M1: the 216 round-1 items both judges labelled (ChatGPT's are all UNCITED by code and leave the
frame). M2: all 91 items. **Strata:** system × judge agreement (same label from both judges, or not), from
`round1_ai_only.json`'s pairs:

| Measure | System | Agree (N) | Disagree (N) | Drawn: agree | Drawn: disagree |
|---|---|---|---|---|---|
| M1 | WHU | 68 | 5 | 8 | all 5 |
| M1 | Claude Research | 34 | 10 | 8 | all 10 |
| M1 | Gemini | 37 | 13 | 8 | all 13 |
| M1 | Perplexity | 42 | 7 | 8 | all 7 |
| M2 | WHU | 16 | 3 | 1 | all 3 |
| M2 | Claude Research | 15 | 4 | 1 | all 4 |
| M2 | ChatGPT | 17 | 2 | 1 | all 2 |
| M2 | Gemini | 13 | 2 | 1 | all 2 |
| M2 | Perplexity | 17 | 2 | 1 | all 2 |

67 M1 items and 18 M2 items. Draw: `random.Random("%d/check5/%s/%s/%s" % (SEED, measure, system, stratum))`,
simple random sampling without replacement within each agree stratum; disagree strata are a census. The strata
use the two existing judges, fixed before check 1 runs.

**Power, briefly.** Disagree strata are censused, so they carry no sampling error. The agree strata hold the
judges' shared errors, which is the threat. The smallest lead among the seven is M1 against Perplexity (30
points); erasing it would need the judges to share a wrong pass on roughly a quarter of WHU's agreed items (or a
matching wrong fail on Perplexity's). With 8 items drawn, the chance of seeing none of a 25% shared error is
0.75^8 = 10%, so such an error shows up with about 90% probability. Smaller shared errors may go unseen. Their
size is carried into the corrected interval, not assumed away. M2's agree strata (1 item each) are too thin to
correct M2 with any precision. M2 is reported as diagnostic, its intervals as they come out.

**Weights.** Item weight = N_stratum / n_labelled in the stratum (n counts only items labelled with a verdict,
so an early stop leaves a valid stratified sample; see the form).

**Blinding.** Items are rebuilt from what the judges saw: the blinded sentence and its context (blind.py's
output: system names, citation styles and page layout removed; markers normalised to [n]) and the cited
source's held snapshot as plain text, with a find box. For M2, the blinded answer and the key conclusion (Fred
is not a key-blind party; he is not a drafting session). No system name, judge label, judge quote or stratum is
shown. Order: one shuffle of all 85 items (`random.Random("%d/check5/order" % SEED)`), interleaved so every
prefix holds strata in proportion.

**The form** (a local page, never published; answers written to
`~/Projects/whu-study-private/validity/check5/fred.jsonl`): one item per screen. M1: "Does the cited source
support this sentence?" Supported / Not supported (then one of: not stated, overstates, contradicts, wrong
source) / Can't tell. M2: "Compared with the key conclusion, the answer…" Matches / Overstates / Understates /
Omits / Contradicts / Can't tell. Optional box: "I think I know which system wrote this" (Fred's own
identifiability, reported). Save, then next; back allowed; stop anytime. **Time:** M1 about 1.5-2 minutes an
item (100-135 min), M2 about 4-5 (70-90 min): **about 3 to 3.5 hours**, which can be split across sessions.

**Correction method.** For judge j, system s and stratum h, from the labelled items (human label = truth,
"Can't tell" excluded and counted): sensitivity Se = P(judge fails | human fails), specificity
Sp = P(judge passes | human passes), each with Jeffreys (add one half) smoothing for empty cells; combined over
the system's strata with the weights. Corrected judged-failure rate θ = (π_obs + Sp − 1) / (Se + Sp − 1),
clipped to [0, 1], where π_obs is the judge's failure share on that system's judged items. The system's
corrected M1 rate = (UNCITED + θ × judged) / countable (UNCITED is code and carries no judge error). If
Se + Sp − 1 < 0.5 the correction is unidentifiable and the direct stratified human estimate Σ_h (N_h/N) ȳ_h is
used, flagged. The direct estimate is reported beside the corrected one throughout. Two-judge corrected = the
mean of the two judges' corrected rates; the same correction is reported for the Google judge once check 1 has
run. **Uncertainty:** bootstrap, 10,000 resamples (`random.Random("%d/check5/boot" % SEED)`): resample the four
questions with replacement, then within each drawn question resample the labelled items within each stratum;
recompute Se, Sp, θ and every WHU-minus-tool difference; percentile 95% intervals.

**Conclusion changes if**, for any of the seven, the corrected difference's 95% interval includes zero, or the
corrected WHU lead is less than half its AI-only lead.

**Who labels (Ruling 5).** **Fred labels alone for now.** His labels are the analysis and are reported as his,
with the statement that Fred built WHU beside every figure. **Volunteers wait** for a version of the form
limited to items whose cited sources are under a Creative Commons licence, since held snapshots may not be
shown to anyone else (pilot doc §10.3 (e)). If that version runs, its labels go through the same code, are
reported separately with their agreement with Fred's on shared items, and are never pooled with his.

## 6. Check 6: the claim definition for future rounds ($0)

**Definition (Ruling 6: code written, frozen with the plan, `next_phase/claims.py`; tests
`backend/tests/test_whu_validity_claims.py`).** A *claim* is a sentence of the answer's body that is claim-like
(`identifiability.claim_like`: a number or a citation marker, 8-70 words) and that code does not place in one
of four kinds, decided the same way for every system:
- **process:** the system's own statement of what it searched, held, read or could not read, or how it worked.
  For WHU, a binding row marked protected "reading". For any system, a first-person or self-referring subject
  ("I", "we", "my", "our", "this answer/report/response/review/summary/search") in the first four words with a
  process verb from a fixed list. A sentence that also states a finding stays a claim ("We found no trial…"),
  using the words of `bindings.STATES_FINDING`;
- **question:** the question restated (the words of `bindings.QUESTION_RESTATEMENT`, plus "your question"; WHU:
  protected "question");
- **out_of_scope:** a line declaring findings outside the answer's scope (the leads of
  `bindings.DECLARATION_LEAD`: WHU's readers' list; WHU: protected "scope"), or a line under a heading
  naming further reading, related topics, excluded or out-of-scope material (the last heading in the ~400
  characters before it);
- **furniture:** a heading, figure or table caption, or reference-list entry.

The patterns are copied into `claims.py` rather than imported, so the definition cannot move when WHU's code
does; a test checks the copies against `bindings.py` while they are meant to agree.

- **Procedure:** future rounds draw M1's 20 sentences exactly as now (old definition, for continuity), and
  classify each by `claims.kind`; both rates are reported, the new definition's on the drawn sentences it keeps.
  Round 1 gets the same classification as a labelled sensitivity; its pre-stated results stand. Round 1's
  existing post-hoc figure (WHU 12.0% as scored, 3.0% excluding readers'-list and process sentences) is the
  reference. Not run yet.
- **Conclusion changes if** any of the seven changes direction, or its interval crosses zero, between the two
  definitions.
- **Cap:** $0.

## 7. Check 9: reachability, both ways ($0)

- **Data:** `round1_ai_only.json` "reachability" and `m1/sources/manifest.json` (route per source: script,
  operator fetch, unreachable, abstract only).
- **Procedure:** every system's M1 under three counts: (a) unreachable and undelivered (INCOMPLETE_SOURCES)
  items counted as failures; (b) those items excluded; (c) script-reachable only (items needing an operator fetch
  also excluded). Table per system: cited items, by script, by operator fetch, unreachable, abstract-only,
  undelivered. As scored, WHU has 75 of 75 reachable by script; the tools 63-87% by script, 93-98% after
  operator fetches.
- **Conclusion changes if** any of the seven changes direction, its interval crosses zero, or the lead halves
  under any of (a)-(c).
- **Cap:** $0.

## 8. Check 10: prompt wording

- **Data:** a seeded 20% of round-1 judged items: M1 44 of 217 and M2 19 of 91, drawn within system
  (`random.Random("%d/check10/%s/%s" % (SEED, measure, system))`).
- **Prompts (Ruling 6), frozen with the plan:** `next_phase/prompts/m1_citation_support_alt.md` (sha256
  589f8dd8…) and `next_phase/prompts/m2_conclusion_calibration_alt.md` (sha256 1f74129b…). They keep the same
  placeholders in the same order (so the runners' cache split at `{documents}` / `{answer}` is unchanged), the
  same seven and five labels, the same tie-break order, the same rules in substance and the same output format
  (the parsers are unchanged). The label definitions are listed in reverse order. Checked by code: outside the
  label names, the conclusion block's field names and the output-format paragraph, the longest word run shared
  with the frozen prompt is 5 words (M1) and 6 words (M2: a quoted example, "the review says 'causally
  demonstrated', 'proved'").
- **Procedure:** both existing judges, first reads, the same delivered text, through `judge_m1.py` /
  `judge_m2.py` with the prompt path and its sha256 swapped by the stage's wrapper (the runners' frozen-prompt
  check is satisfied for the alternative's own hash). The wrapper verifies the alternative prompt's sha256 against
  this section before every stage, never modifies the frozen prompts, and logs the swap (paths, both hashes, time)
  in the run record. Issue order shuffled.
- **Analysis:** label flip rate per judge (pass/fail and exact label). Per system and measure, the shift
  (alternative minus original failure rate on the subsample) is added to the full-sample rate, and the seven are
  recomputed.
- **Conclusion changes if** any of the seven changes sign under the shifted rates; a flip rate over 15% for
  either judge is flagged as instability even without a change in direction.
- **Cost:** round 1's two-judge cost per M1 item was ~$0.50 ($132.12 / 263 calls per judge), with no cache
  benefit on a new prompt; ~$22 M1 + ~$2 M2. **Cap $30**, issue `whu-reliability-judging-validity-c10`.

## 9. The seeded-defect test (draft stage; the code checks and the first audit only)

**Scope (Ruling 2).** Seeded defects are run through the code checks and the first audit only. **The gate
(fact-check), the advocate and the omission rulings are not tested, and the report says so** in its first
paragraph: "lean catches no fewer" is shown for the code checks and the first audit, not for the gate or the
advocate.

**Case root (Ruling 4), from the scripts: the pipeline does not run from a case root outside `issues/`.**
`source_store.case_dir(slug)` globs `ROOT/issues/WHU-*-<slug>` (`source_store.CASES = ROOT / "issues"`), and
every stage used here finds its case through it (audit_stage, coverage_check, lean_coverage, sources_shown,
lean_sentences, bindings); `publish.case_dir` finds the case by the `slug` in `ROOT/issues/*/issue.json`. No
argument or environment variable points elsewhere. `audit_stage.py` writes into the case's `audit/`, except
`--dry-run --out DIR` (outside `issues/`), which also requires `--limit N` and so cannot audit a whole page.
**Therefore:** the copies run as cases `issues/WHU-SD-NN-<slug>/` (`"study": true`, so publish, update and
announce refuse them), and **a `.gitignore` entry `issues/WHU-SD-*/` is committed with the freeze**: today only
`audit/`, `rulings/` and `export/` are ignored for study cases, so a copy's page, `issue.json` and bindings
would otherwise show as untracked in the shared index (round 1's shared-index slip, deviations 2026-10-29). The
copies use the shared source library as the originals do (no document is added or changed). After the last
seeded run each copy is archived to `~/Projects/whu-study-private/validity/seeded/<copy>/` and deleted from
`issues/`, **before any lean drafting session starts**.

**Copies.** The four round-1 WHU pages as scored (each question's commit in
`quarterly/whu_answers_manifest_round1.txt`; WHU-Q1-02 at `bd18e5e`), with their bindings, coverage and source
list. Five copies per question, one planted error each, one of each type per question: 20 copies, 4 per type.

**Planting** (by the scoring session, by code where possible; each target drawn with
`random.Random("%d/seeded/%s/%s" % (SEED, question, type))` from the eligible sentences):
- *wrong figure:* one number in a bound sentence changed (×1.5, rounded to the page's precision); its binding
  unchanged.
- *overstated certainty:* one certainty or hedge term raised one step (e.g. low → moderate certainty; may →
  does; likely → very likely; medium → high confidence).
- *misattributed source:* the sentence's citation and binding moved to another held source on the same page
  that does not state it, on that source's passage with the highest BM25 overlap (so spancheck still passes); a
  named source in the text changed to match.
- *dropped key conclusion:* one sentence that alone carries a "used" headline unit in `coverage.json` deleted,
  with its binding row.
- *invented citation:* a citation to a work not in the source store (a plausible title and a DOI that resolves
  to nothing) added to an existing sentence, with a reference-list entry.

**Record, before any run:** `planted.json` (private,
`~/Projects/whu-study-private/validity/seeded/planted.json`) with, per copy: question, type, the page's unit id
and character offsets, binding row id, the original and planted sentences' sha256, the changed token, and (for
a dropped conclusion) the headline unit id. Its sha256 is committed before the first run.

**Systems:** full WHU (current main with the switch off), lean WHU (`WHU_LEAN=1`, Sonnet 5.5 default tiers),
lean WHU Haiku variant (`variant_models("haiku-5-5")`). Each copy is run through, with no person in the loop:
the code checks of step 3 (spancheck, bibbind, sources_shown, coverage_check / lean_coverage, and lean_sentences
for lean), **the first full audit** (`audit_stage.py run`), then `publish.py check` for its code rows.

**"Caught", exactly.** A planted error is caught by a system if, in that copy's records, either: (1) a code
check STOPs or WARNs naming the planted unit, its binding row, or (dropped conclusion) the dropped headline unit;
or (2) the audit's **final** verdict on the planted unit is not "holds" (a finding, amend, cut,
must_leave_page or FAILED_READ). For lean, final means the deciding model's verdict after escalation (a Sonnet
or Haiku flag that Opus settles as "holds" is *not* caught). Protected sentences sent to a person
(HUMAN_READ_REQUIRED) are not caught, because no machine found anything. The audit cannot see a deleted
sentence, so a dropped conclusion can be caught only under (1). **Strict variant** (reported beside it): the
finding's text names the changed token (the number, certainty term, source label or citation), by string match.
**False alarms:** non-"holds" final verdicts on unplanted units, per system, against that page's round-1 audit.
If lean's false-alarm rate exceeds full's by more than half, the catch comparison is reported as not
interpretable (a system that flags everything catches everything). Check pilot v4 gave false NOT BACKED verdicts
when retrieval missed the supporting passage (§12); the false-alarm guard and the strict variant are where this
shows for lean WHU.

**Bar (added to the lean pass bar):** lean (Sonnet) catches no fewer planted errors than full, overall and for
each of the five types. The Haiku variant is reported against the same bar and decides nothing. With 4 per type,
ties are likely and are a pass.

**Cost** (first-audit figures from `lean_replay_round1.json`; per copy Q1-01 / -02 / -03 / -04): full $0.93 /
2.00 / 5.23 / 2.86; Sonnet $0.56 / 0.89 / 2.88 / 1.66 (pessimistic); Haiku $0.39 / 0.63 / 2.04 / 1.11. Five
copies each: full ~$55, Sonnet ~$30, Haiku ~$21: **~$106. Cap $110** (full $57, Sonnet $32, Haiku $21), issues
`whu-validity-sd-full`, `-sd-sonnet`, `-sd-haiku`. Each copy is also under caps.json `study_per_issue` ($50).

## 10. The lean-WHU four-question test

As the approved plan's Part B, unchanged: lean WHU (`WHU_LEAN=1`, Sonnet 5.5 default) answers WHU-Q1-01 to -04 in
**fresh sessions** that see no round-1 page, key, score, judge reply, planted-defect record, seeded copy or
validity result (round 1's briefs, `quarterly/round1_briefs.md`, with the lean switch; the shared library still
holds round 1's documents: a known leak, recorded). Issues `whu-lean-q1-01` to `-04` (`"study": true`,
`"round": "lean"`), code frozen at one commit for all four. Judged: WHU only, against the frozen round-1 keys, the
same code, both judges (Claude and OpenAI, as round 1); M1 20 sentences per answer drawn by
`random.Random("%d/%s/WHU-lean/M1" % (R1SEED, q))`, M2 every key conclusion, second reads on a seeded 20% as in
round 1; issue `whu-reliability-judging-lean`.

**Pass bar, unchanged; all must hold:**
1. Cost: median under $5 per answer, none over $10 (ledger). Each run's `--cap` is $10, so a run that hits it
   fails this bar for that answer.
2. Fred's time: under 10 minutes per answer (operator minutes in each study log).
3. M1 failure, two judges combined, at most 3 points above round-1 WHU under both definitions: ≤ 15.0% as scored
   (round 1: 12.03%); ≤ 6.0% excluding process and declaration sentences (round 1: 2.99%).
4. M2 Understates+Omits and Overstates+Contradicts no higher than round-1 WHU under either judge (round 1:
   Claude judge 0% and 0%; OpenAI judge 5.3% and 10.5%; 19 conclusions, so one failure under the Claude judge
   fails this bar).
5. (Added by the approved plan.) The seeded-defect bar of §9, for the code checks and first audit.

Failing any one is a result. **Cost:** runs ≤ $40 (four × $10 caps); judging ~$30-45 (WHU's share of round 1's
judging). **Cap $85** ($40 runs, $45 judging).

## 11. Order

1. Step 1: check pilot v4: **done** (§12).
2. Advisor's second review of this draft; Fred's approval; the freeze commit (SEED), carrying this file, the
   four prompts in `next_phase/prompts/`, `next_phase/claims.py` and its test, and the `.gitignore` entry for
   `issues/WHU-SD-*/`.
3. Checks on existing answers: $0 first (9, 6), then paid (1 → 2, 3, 4, 10). Fred's labelling (check 5) can start
   at the freeze; its analysis comes after the paid checks.
4. **Report the checks, then STOP for the advisor.** If any check changes the conclusion, that is the finding,
   reported first, and the evaluation is fixed before money goes on WHU (the approved plan's rule). The
   seeded-defect and lean test do not start without a ruling.
5. Seeded defects (§9).
6. Lean four-question test (§10).

## 12. Budget

**Step 1 result (check pilot v4, doc §11.1-§11.2, `check_pilot/pilot_v4_counts.json`):** $3.03 spent (worst case
$7.92). It fails one bar of five: agreement 83.3% (bar 90%; v3 97.9%), because BM25 retrieval missed the
supporting passage (7 of 8 disagreements are study BACKED → v4 NOT BACKED). It passes COULDN'T CHECK 18.0% (v3
21.7%), $0.38 per answer (v3 $4.67), time and passages. It cleared 13 of v3's 15 delivery-check claims.

| Item | Ledger issue(s) | Estimate | Cap |
|---|---|---|---|
| Step 1: check pilot v4 | whu-check-pilot-v4 | **spent $3.03** | $10 |
| Check 1: Google judge | whu-reliability-judging-validity-c1 | ~$35-50 | $55 |
| Checks 2, 6, 9 | none | $0 | $0 |
| Check 3: identifiability | whu-validity-c3-ident | ~$2-4 | $5 |
| Check 4: second keys (Q1-01..04, S01, S02) | whu-validity-c4-keys; whu-reliability-judging-validity-c4m2 | ~$30 | $40 ($12 + $28) |
| Check 5: human sample | none | $0; Fred ~3-3.5 h | $0 |
| Check 10: prompt wording | whu-reliability-judging-validity-c10 | ~$24 | $30 |
| Seeded defects (code checks + first audit) | whu-validity-sd-{full,sonnet,haiku} | ~$106 | $110 |
| Lean test: runs | whu-lean-q1-01 … -04 | ≤ $40 | $40 |
| Lean test: judging | whu-reliability-judging-lean | ~$30-45 | $45 |
| **Total** | | **~$270-310** | **$335** |
| Reserve (Ruling 2) | | | $15 |

**Ruling after the freeze (advisor, 2026-10-30, before any check-3 call):** check 3's cap is raised from $5 to $6,
the extra $1 taken from the $15 reserve (reserve now $14; caps total $336). Reason: check 3's printed estimate was
$5.21 likely (100 sentences ~$0.85; 19 whole answers ~$4.35), over its $5 cap, so nothing had run. The whole of check
3 (sentences and whole answers) runs under the new cap.

Step 1's unspent $6.97 stays inside its line (caps are not moved between items without a ruling). Spending at
up to $60 a day (§0) takes about six spending days.

## 13. Open items for the advisor

1. The Google row's cache-write rate is set to the input rate, an inference (§0). No runner here caches
   explicitly, so it should not be used.
2. Check 10's wrapper swaps the prompt path and expected hash for the judge runners (§8). Is that acceptable,
   or should the alternatives get their own runner like `judge_google.py`?
3. Check pilot v4's result (§12) bears on lean WHU's audit, which uses the same retrieval; there the bound
   passage is always sent as well. The seeded-defect false-alarm guard (§9) is where it would show. No change is
   proposed.
