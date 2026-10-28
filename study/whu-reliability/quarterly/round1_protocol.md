# WHU quarterly round 1: protocol

Drafted 2026-10-28 by Claude Code (session L); reviewed by the advisor, whose §13 rulings of
2026-10-28 are written into §12 and §13 below, and approved by Fred (option B). **Frozen by the
commit that adds this file**; that commit's full hash is the seed (§1). The duplicate-test patterns
and the draw script are frozen with it: `quarterly/round1_duplicates.json` and
`quarterly/round1_draw.py`.

## 0. What this round is, and what it copies

Round 1 asks four fresh questions of WHU and four AI research tools, and scores the answers as the
reliability study did. It is the test the post-study re-run plan names: "Fresh questions in the
quarterly round are the real test" of WHU fixes 1-3 (`rerun_plan.md`, Limitations).

Every rule is copied from the study protocol (`docs/whu-reliability-protocol.md`, with its dated
rulings) and from the study's records (`deviations.md`, `machine_only_plan.md`, `rerun_plan.md`,
`perplexity_plan.md`, `RUN_TOOLS.md`) unless it is listed in §12, "Changes from the study, with
reasons". Where this file and the study protocol differ and §12 does not list the difference, the
study protocol wins and the difference is a drafting error to be logged.

Outside the study's H1 and H2: round 1 changes no study record, result, rule or figure.

## 1. Questions: four, fresh

**Strata, as in the study:** Cochrane systematic reviews (1 question, health), Campbell Systematic
Reviews (1, social policy), IPCC AR6 numbered Summary for Policymakers statements carrying IPCC
calibrated language (2, from different AR6 reports).

**Sampling frames:** the study's frame files, unchanged: `frames/cochrane.json` (sha256
2122300f…), `frames/campbell.json` (9f375451…), `frames/ipcc.json` (93d99e21…). Their windows,
tests and topic exclusions are the study's (protocol, "Question selection", eligibility 1-5;
"Frame and draw rulings"; "National Academies frame dropped").

**Eligible** if the entry passes the study's eligibility criteria 1-5 and the draw-time duplicate
test (`frames.py draw_study`), and:

- **Open licence (Cochrane and Campbell), deviations 2026-10-24, Option 2:** "(i) Europe PMC lists
  the review with an open licence (CC BY, CC BY-NC or CC BY-NC-ND) in its license field, AND (ii)
  Europe PMC's fullTextXML service returns the full text. Check (ii) by HTTP status and content
  type only; do not read or save the text. (iii) The entry must also pass eligibility criteria 1-5
  as before." Europe PMC's search is
  `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:<pmid> AND SRC:MED&resultType=core&format=json`.
  An entry that fails is passed over and logged with its reason, as in the S05 re-draw.
- **IPCC:** IPCC entries stay under the study's rule, read under the IPCC's copyright terms
  (https://www.ipcc.ch/copyright/); Option 2 is not applied to them (ruling §13.1).
- **Not used before:** the entry is none of these, each excluded with the reason logged:
  - Cochrane: CD016194 (WHU-S01), CD015890.pub2 (WHU-S05), and CD005632.pub4 (drawn for WHU-S05
    and rejected on closer reading);
  - Campbell: 10.1002/cl2.1376 (WHU-S02), 10.1002/cl2.1377 (WHU-S06);
  - IPCC AR6: AR6-WGIII-E.3.3 (WHU-S03), AR6-WGII-D.3.2 (WHU-S04), AR6-WGIII-C.8.2 (WHU-S07),
    AR6-WGII-C.2.6 (WHU-S08);
  - the pilots' and practice runs': the pilot's four questions (T01 exercise and depression, T02
    ultra-processed foods, T03 intermittent fasting, T04 vitamin D in older adults) and WHU-P02,
    already in the frames' duplicate test; WHU-P03 (National Academies, withdrawn) and WHU-P04
    (IPCC AR5) are outside these frames;
  - the post-study re-runs (WHU-S01r, WHU-S07r) and the Perplexity add-on asked the study's own
    questions, so they add no entry.
- **Topic duplicates of the study's questions** (§12, change 2): the draw-time duplicate test also
  covers the eight study questions WHU-S01 to WHU-S08, by the same kind of pattern the test already
  applies to WHU's published and tested questions (`frames.WHU_QUESTIONS`). The patterns are in
  `quarterly/round1_duplicates.json`, committed with the freeze, before the seed exists.

**Order of the draw-time tests** for each candidate, in the shuffle (`quarterly/round1_draw.py`,
which imports the study's `frames.py` unchanged and follows `frames.draw_study`'s procedure): (a)
for IPCC, the statement as fetched must hash to the frame's `statement_sha256`; (b) not an entry
used before (the list above); (c) the duplicate test (`frames.WHU_QUESTIONS` plus the round-1
patterns); (d) for IPCC's second question, not from the same AR6 report as the first; (e) for
Cochrane and Campbell, Option 2. The first candidate passing all is the draw; every candidate
checked is logged with its result and reason. The closer reading (eligibility 1-5 on the abstract
or statement) follows, as in the study's draw records, and a failure takes the next in the
shuffle.

**Drawing** (protocol, "Freeze rulings", the seed rule): SEED = the full 40-character hash of the
commit that freezes this protocol, read as a hexadecimal integer. Each frame's eligible list is
shuffled with `random.Random(SEED)`; the first entry that passes is the draw; the second IPCC
question is the next entry that passes from a different AR6 report than the first. If an entry
fails on closer reading, the next in the shuffle is taken and the reason logged. Every candidate
checked is logged (`quarterly/round1_draw.py`, following `frames.draw_study`; written to
`quarterly/draws/<frame>-<commit>.json`). **IPCC statements** are read offline from the fetch cache of the
extension draw (2026-10-24, `frames.Fetcher`), because ipcc.ch now answers the script with HTTP 403; each
statement must still hash to the frame's `statement_sha256` (test (a)), and no bot wall is worked around.

**Question ids:** WHU-Q1-01 (Cochrane), WHU-Q1-02 (Campbell), WHU-Q1-03 and WHU-Q1-04 (IPCC, in
draw order). **Wording:** written from the review's stated objective in plain words, without naming
the review; all four committed before any system runs.

## 2. Answer keys

As in the study (protocol, "Answer keys"; Stage 1 ruling): up to five main conclusions per key,
each with direction, size, certainty in the review's own terms, scope limits and the review's own
words quoted with location; drafted by a Claude instance from the full text, checked against the
review by a second, separate instance; a disputed conclusion is corrected or dropped and the change
logged; frozen (sha256 in a keys manifest) before any system runs. The key-dispute procedure applies
unchanged. Full text: Europe PMC's fullTextXML for Cochrane and Campbell (the Option 2 copy); the
SPM and, where the statement rests on it, the chapter on ipcc.ch for IPCC.

## 3. Systems

Every system gets the question text, followed by: "Please research this and give me a well-sourced
answer with citations." Each tool is run once per question, within 48 hours of the others for that
question, with the date, time, model or version shown and the full export recorded and hashed at
capture (`RUN_TOOLS.md`, `perplexity_plan.md`).

| System | Configuration |
| --- | --- |
| What Holds Up, with fixes 1-3 | The code at HEAD of `main` at the freeze commit: fixes 1-3 (CLAUDE.md, "WHU post-study fixes 1-3 — summary") and the mechanical tool fixes made during the post-study re-runs (deviations 2026-10-28). Frozen at that commit for the whole round (protocol, fairness rule 1). Run by the post-study runbook (`docs/whatholdsup-process.md` §4.5, with `docs/whu-fix3-evidence-standard.md` §3), as the re-runs were: `premise.json` scope and evidence standard before any source is opened, coverage and the readers' list, relevance rulings on held assessment judgements, the omission rulings and ADDs, and every new preflight row fail-closed. The answer is the issue page as committed once `publish.py check <slug>` prints `Ready.`; its sha256 and commit go in an answers manifest. |
| Claude Research (claude.ai) | Research mode, incognito chat, plan accepted unchanged, no follow-ups (`RUN_TOOLS.md`). |
| ChatGPT deep research | Paid plan, memory and custom instructions off, normal chat, plan accepted unchanged, no follow-ups (`RUN_TOOLS.md`). **Launched through the `$deep-research` app link, as for WHU-S01 to WHU-S04, not the composer chip** (ruling §13.3). **Record whether it searched the web:** the report header's search and citation counts ("Research completed in Nm · N citations · N searches") and whether the export holds any URL. If the header shows 0 searches, that is recorded, the run is not repeated, and its figures are labelled "no web search performed". |
| Gemini Deep Research | Default model on the account used, plan accepted unchanged, no follow-ups. |
| Perplexity Deep Research | Fred's account, Deep Research mode; memory, personalisation (including "Your occupation") and connected-file sources off, every setting's before and after state recorded (`perplexity_plan.md`; deviations 2026-10-27, the personalisation capture fault). |

**WHU issues** carry `"study": true` in issue.json, as the re-runs did (`rerun_plan.md`, "Why the
issue.json says study: true"), so the tools run unchanged, `publish`, `update` and `announce`
refuse the issue, the four excluded steps (outside review, second-session verification, operator
acceptance, publication) are recorded as SKIPPED, and the cap is caps.json `study_per_issue`. Each
issue also carries `"round": "Q1"` and a note that it is a quarterly-round question.

**Once only.** Each system answers each question once; a re-run only after a technical failure (a
crash, a timeout, an empty export), logged with evidence first. A ChatGPT run with no web search is
not a technical failure (ruling §13.3). A WHU run that cannot reach `Ready.` within its caps
is a result, recorded and not scored.

## 4. Blinding

As in the study (protocol, "Blinding" and its rulings; `blinding/blind.py` and its frozen phrase
list and spelling map, unchanged), plus three separations:

- **Key drafters and checkers see no tool or WHU answer** for that round, before or after their key
  is frozen, and no judge reply.
- **WHU drafting sessions see no answer key,** and none of: the private folder
  `~/Projects/whu-study-private/` (other than writing their own archive subfolder), `study/whu-reliability/`
  (including this protocol and the round's draw records' closer readings), any judge output or
  score, or another system's answer. As in the re-runs, running the test suite (the pre-commit hook)
  is allowed; tests and fixtures that name a round-1 question may not be read.
- **The advisor does not read any key,** before or after its freeze.

Judges are never told which system wrote an item; items reach them in random order across systems
and questions.

## 5. Measures

**M1 (citation support)** and **M2 (conclusion calibration)** exactly as in the study:

- the same code, unchanged: `prepare_scoring.py` (verify, blind, sample, snapshot, cost),
  `retrieve_sources.py`, `ingest_operator.py`, `judge_m1.py` (M1 v3, sha256 04efb531…),
  `judge_m2.py` (M2 v2, sha256 64a5a5b6…), `analyse.py` / `analyse_eight.py` rules;
- the same two judges (Claude Opus 5.5 `claude-opus-5-5`; OpenAI `gpt-6-astra`), the same delivery,
  refusal rule, abstract-only rule (EVERY), long-source rule and INCOMPLETE_SOURCES rule;
- **M1 sampling:** 20 claim-like sentences per answer (`identifiability.claim_like`), or all if
  fewer, drawn by `random.Random("<SEED>/<question>/<system>/M1")`, SEED this protocol's freeze
  commit; a drawn sentence with no marker is UNCITED; item ids `opaque("M1", ...)` with this SEED;
- **M2:** every conclusion of the frozen key, for every answer;
- **second reads:** each judge re-reads a seeded 20% of items (the freeze commit's seed);
- **snapshots:** one per distinct cited address, retrieved by routes (a) to (c), then route (d)
  in Fred's Chrome by Claude Code for sources free to read but blocking automation, under the
  extension's ruling (deviations 2026-10-27): no sign-in, account, payment, or way past a paywall or
  bot wall; reachability rule unchanged for every system, WHU included;
- run directory: private, `~/Projects/whu-study-private/scoring/quarterly/round1/`; the study's
  items, samples, replies and manifests are not touched.

**Quote check: not run.** Fred's budget approval (option B, 2026-10-28) is "quarterly round 1 with
a round cap of $250, no quote check".

Reported for every system, as in the study: M1 two-judge combined, each judge alone, agreed only,
cited only, uncited share, reachability (flag above 20% unreachable or abstract-only); M2
two-judge combined, each judge, the direction of every failure; refusal rates; cost and elapsed
time (M4); WHU's process measures as in the re-runs (spend per stage, each new preflight row's
outcome, ADDs and declarations against their budgets, judgement candidates and how each was stated
or declared, items sent to a person, the ruling-model consistency sample).

## 6. Pre-stated comparisons

All judged by AI models only; reported with every n; nothing here is H1 or H2.

**A. WHU against each tool, on the four round-1 questions.** For each tool T in Claude Research,
ChatGPT deep research, Gemini Deep Research, Perplexity Deep Research:

1. M1 failure rate (cited-not-supported + uncited, over countable items), WHU against T;
2. M2 Overstates rate (key conclusions labelled Overstates), WHU against T;
3. M2 Understates+Omits rate (labelled Understates or Omits), WHU against T.

Each as the difference and the ratio of rates, two-judge combined (each judge's label counted, as
`analyse.py` combines them), with the study's bootstrap: whole questions resampled, 10,000
resamples, seeded by the freeze commit's hash. Each judge's view is reported alongside. No
threshold: the study's half-rate rule is reported for each comparison but decides nothing.

**B. WHU in round 1 against WHU in the study: the test of fixes 1-3 on fresh questions.** WHU's
round-1 rates on the four new questions against WHU's study rates on WHU-S01 to WHU-S08
(`results/eight_ai_only.json`, unchanged), by the same code. Two independent sets of questions, so
the bootstrap resamples questions within each set separately; the difference's 95% interval is
reported.

Fixes 1-3 are reported as **having held on fresh questions** only if all three conditions hold
(the re-run plan's success rule, applied to rates because the question sets differ). The rule is
reported with its intervals and labelled "descriptive; 4 questions" (ruling §13.4):

1. WHU's M2 Understates+Omits rate in round 1 is below its study rate, under both judges;
2. WHU's M2 Overstates+Contradicts rate in round 1 is not above its study rate, under either judge;
3. WHU's two-judge combined M1 failure rate in round 1 is no more than 5.0 percentage points above
   its study rate (EVERY abstract-only correction; Uncited counted as a failure; not quote-checked).

If WHU has no answer on a round-1 question, the rule is reported as not met. Gaps (a conclusion
with no countable label from a judge) are reported, and that judge's condition is evaluated on the
labelled conclusions.

## 7. Spend

- **Per WHU issue:** $50 (caps.json `study_per_issue`), never raised for a run: an answer that
  cannot finish within it is a result.
- **Per day:** caps.json `default_per_day` ($25) covers every ledger line; runs pick up the next
  day. The judging runners' own day cap (`study_judging_per_day`, $150) counts only
  `whu-reliability-judging*` issues, so round 1's judging issue is checked against it by hand
  before each judging stage.
- **Round cap: $250**, Fred's approval (option B, 2026-10-28), across the ledger issues of the four
  WHU runs and `whu-quarterly-r1-judging`. Not enforced by code: before each paid stage the session
  sums those issues with `spend_ledger.py --issue` and STOPs if the stage's printed estimate would
  take the round past $250. Where a stage takes `--cap`, it is passed the smaller of the issue's
  remaining $50 and the round's remainder.
- **Judging** is estimated before any call by `prepare_scoring.py`'s projection; if the estimate
  exceeds what remains of the $250, the work STOPs and is reported.
- No override of any cap (no `WHU_SPEND_OVERRIDE`), no `--waive`, no `--no-verify`.

## 8. Order

Fixed, each step committed before the next (protocol, fairness rule 5): this protocol frozen; the
questions drawn and committed; the answer keys drafted, checked and frozen; the five systems run;
blinding and sampling; snapshots; the cost projection; judging (M1, M2); analysis. Git timestamps
are the record.

## 9. Fairness and integrity

The study's rules 1-5 apply unchanged: WHU frozen at one commit (a fix found during the round waits
for the round's end); no reruns but for a logged technical failure; no coaching (the operator does
only what the runbook prescribes, each manual step logged with its time); everything saved and
hashed as produced, never edited; the order fixed.

## 10. Reporting and deviations

Results are reported whatever they show, primary comparisons (§6) first, labelled "judged by AI
models only; not checked by people". A deviations log for round 1
(`study/whu-reliability/quarterly/round1_deviations.md`) is kept from the freeze, one row per
departure: date, what changed, why, and whether decided before or after any result was seen.
Nothing is published, announced or deployed by this round's sessions.

## 11. Limitations, stated before any run

- Four questions, AI judges only, no human review: wide intervals; the comparisons are descriptive.
- Comparison B compares different questions; a difference may reflect the questions, not the fixes.
- The tools may have changed since October 2026; each is run as it behaves on the run date.
- Fixes 1-3 were designed on the study's failures; round 1 is their first out-of-sample test.

## 12. Changes from the study, with reasons

1. **Open-licence eligibility for Cochrane and Campbell (Option 2).** The study applied it only to
   the WHU-S05 re-draw; here it applies to every Cochrane and Campbell candidate from the start.
   Reason: deviations 2026-10-24 (no key can lawfully be drafted from a review whose full text is
   not openly available under the Wiley terms), and the brief for this round.
2. **The duplicate test also covers the study's eight questions.** Reason: "fresh questions"; the
   study logged S05/S01 and S08/S04 closeness as limitations, and round 1 should not repeat that.
3. **Every review and AR6 section the study or the pilots used is excluded** (§1). Reason: fresh
   questions.
4. **WHU is the post-study WHU** (fixes 1-3 and the re-run tool fixes, at the freeze commit), run by
   the post-study runbook. Reason: round 1 tests those fixes.
5. **Perplexity Deep Research is a full fifth system** on all four questions (the study added it
   afterwards, on S01-S04 only). Reason: the brief for this round.
6. **Machine-only from the start.** No Stage 2 human review; the machine-only plan's spec (b)
   cross-company view is reported as secondary, as in the study. Reason: the study's ruling of
   2026-10-24 (no budget), carried forward.
7. **No quote check.** Reason: Fred's budget approval (option B).
8. **No H1/H2 and no extension rule.** The round has pre-stated comparisons (§6), not hypotheses.
   Reason: it is a monitoring round, not a re-run of the study.
9. **Budget:** $250 round cap and a $50 per-issue cap per WHU run; no study-total check; the $25
   day cap unchanged (ruling §13.5). Reason: Fred's approval.
10. **ChatGPT launched through the `$deep-research` app link**, as for WHU-S01 to WHU-S04, not the
    composer chip; 0 searches recorded, not re-run, figures labelled "no web search performed".
    Reason: ruling §13.3 (in the study, S05-S08 ran with 0 searches, cause not established).

## 13. Advisor rulings on the draft's open questions (2026-10-28, before the freeze)

1. **IPCC and the open-licence rule:** IPCC stays under the study's rule (IPCC copyright terms).
   Option 2 applies to Cochrane and Campbell only.
2. **Frames:** unchanged; the study's frame files are used as committed.
3. **ChatGPT:** launch deep research via the `$deep-research` app link, as for WHU-S01 to WHU-S04,
   not the composer chip. If the report header still shows 0 searches, record it, do not re-run,
   and label its figures "no web search performed".
4. **§6B:** the rule is kept, reported with its intervals and labelled "descriptive; 4 questions".
5. **Spend:** the day cap stays $25.
