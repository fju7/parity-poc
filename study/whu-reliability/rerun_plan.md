# WHU reliability study: post-study re-run of WHU-S01 and WHU-S07 under fixes 1-3 (exploratory)

Approved by Fred 2026-10-27, after all study results were seen. Fixed by the commit that adds this file, before any re-run starts. Its sha256 is recorded in `deviations.md`. A drafting session does not read this file.

**Amended 2026-10-27, before any re-run (Fred).** Both re-runs are to finish on 2026-10-28 UTC, and judging comes later. Three changes follow:
- the re-run total rises from $60 to $100;
- the WHU day cap is $75 for UTC day 2026-10-28 only;
- the quote check runs after M1 and M2, and only if the budget covers it.

The success rule, the comparison and the $50 per-issue cap are unchanged. The new sha256 is in `deviations.md`.

## Status and purpose

- **Purpose:** a post-study check of WHU fixes 1-3:
  - fix 1, protected sentences;
  - fix 2, omission rulings and the coverage check;
  - fix 3, the evidence standard and held assessment judgements.
- The runbook is `docs/whatholdsup-process.md` §4.5, and `docs/whu-fix3-evidence-standard.md` §3 for fix 3. Commits are listed in CLAUDE.md, "WHU post-study fixes 1-3 — summary".
- **Exploratory.** It is outside H1 and H2. It changes no study record, result, rule or figure already reported.
- **Questions:** WHU-S01 and WHU-S07 only, asked again word for word.

| Re-run | Case directory | Slug and ledger issue | Question |
|---|---|---|---|
| WHU-S01r | `issues/WHU-S01r-whu-rerun-s01/` | `whu-rerun-s01` | WHU-S01's `issue.json` question, verbatim |
| WHU-S07r | `issues/WHU-S07r-whu-rerun-s07/` | `whu-rerun-s07` | WHU-S07's `issue.json` question, verbatim |

**Why the issue.json says "study": true.** Each issue.json carries `"study": true` and `"rerun_of"`. Fred chose this on 2026-10-27 over `"study": false`, because with false the WHU tools refuse to run (`publish.issue_cfg`, `ruling.require_study`). With true:
- the tools run unchanged;
- `publish`, `update` and `announce` refuse the issue;
- the four steps the study excludes are recorded as SKIPPED;
- the cap is caps.json `study_per_issue` ($50).

The `"rerun_of"` field and the note in each issue.json say the run is post-study and outside H1/H2. The study's analysis scripts read fixed question lists, so the re-runs do not enter any study figure.

## Runs

- **Who runs them.** Each issue is run end to end by a fresh Claude Code session. The briefs are in `rerun_briefs.md`, pasted by Fred after 00:00 UTC.
- **Which runbook.** The sessions follow the post-study runbook, not the frozen `RUN.md`. That means the stage sequence written out in the brief (the same tools and order as the study), with the fix 1-3 steps:
  - `premise.json` `scope` and `evidence_standard`, written before any source is opened;
  - step 3c, coverage, and the readers' list;
  - the relevance ruling on held assessment judgements, and their statement or declaration;
  - step 4b's MISSTATES / LEAVES_OUT objection types;
  - step 4d, omission rulings, and step 4e, applying ADDs;
  - the new preflight rows, all fail-closed.
- **The answer** is the issue page as committed once `publish.py check <slug>` prints `Ready.` This is the same rule as the study's WHU answers (`scoring/whu_answers_manifest.txt`). Its sha256 and commit are recorded in a manifest beside the study's.
- **Once only.** Each question is run once. A second run is allowed only after a technical failure, logged with evidence first.
- **No answer counts as a failure.** A run that cannot reach `Ready.` within its caps is a result. It is recorded, not scored, and the success rule below is then reported as not met.

## Blinding

The drafting sessions must not read any of the following:
- the original `issues/WHU-S01-tb-dna-testing/` and `issues/WHU-S07-urban-form-transport-emissions/` folders, or their git history;
- the answer keys (any `key.json`);
- the private folder `~/Projects/whu-study-private/`. They may only write their own archive subfolder there;
- `study/whu-reliability/`, all of it, including this plan, its predictions and `rerun_briefs.md`;
- any judge output or score.

Approved additions (Fred, 2026-10-27):
- `docs/whu-omissions-investigation-2026-10.md`;
- the S01/S07 parts of the fix design docs: all of `docs/whu-fix2-omission-rulings-design.md`, which the §4.5 runbook replaces, and §2 ("Measured on the study issues") of `docs/whu-fix3-evidence-standard.md`;
- the original slugs' library and reachability files:
  - `backend/data/whatholdsup/library/issues/tb-dna-testing.json`;
  - `backend/data/whatholdsup/library/issues/urban-form-transport-emissions.json`;
  - every `backend/data/whatholdsup/library/_reachability_tb-dna-testing*` and `_reachability_urban-form-transport-emissions*` file.

Also excluded: tests and fixtures that name S01 or S07. Running the suite (the pre-commit hook) is allowed.

**Known leaks.** CLAUDE.md, which every session reads, mentions S01 and S07 only as coverage unit counts and STOP rows. The shared library still holds the documents the original runs acquired. Research starts from the question, not from the library's list.

## Comparison

The re-run WHU answers are compared with the original WHU-S01 and WHU-S07 answers on M1 (citation support) and M2 (labels against the frozen keys). Everything is done exactly as in the study:

- **Same code and prompts.** The study's scoring code runs unchanged:
  - `prepare_scoring.py`, `retrieve_sources.py`, `ingest_operator.py`;
  - `judge_m1.py` with M1 v3 and `judge_m2.py` with M2 v2;
  - the same two judges, delivery, refusal rule and abstract-only rule (EVERY);
  - `blind.py` unchanged, on the WHU answer as the study converted WHU pages.
- **Separate run directory.** The re-runs have their own private run directory (`~/Projects/whu-study-private/scoring/rerun/`). The study's items, samples, replies and manifests are not touched.
- **M1 sampling.** The Stage 1 rule: 20 claim-like sentences per answer (`identifiability.claim_like`), or all of them if fewer.
  - The draw is `random.Random("<SEED>/<question>/WHU-rerun/M1")`, where SEED is the freeze commit `5d83e9b8025312923f3fb8ea2d5de3b47c212362` read as a hexadecimal integer, and `<question>` is `WHU-S01` or `WHU-S07`.
  - A drawn sentence with no marker is UNCITED.
  - Item ids are `opaque("M1", "<question>/WHU-rerun/<idx>")`.
- **M2 items.** Every conclusion of the frozen keys for WHU-S01 and WHU-S07 is judged against the re-run answer: 9 items.
- **Snapshots.** One per distinct cited address, reused from the study's snapshot manifest where the address (or its DOI, PMID or PMCID) is already held. Routes (a) to (c) are used, then route (d) under the extension's ruling: no sign-in, account, payment, or way past a paywall or bot wall.
- **Second reads.** Each judge re-reads a seeded 20% of items. The seed is the freeze commit and the pool is the re-run items judged.
- **Quote check.** `quotecheck_m1.py`'s spec (a) is applied to the re-run M1 items with a first read from both judges, with delivery identical to their first read. It runs after M1 and M2 are judged, and only if its estimate fits within what remains of the $100. If it does not fit, it is not run, and that is reported. The success rule does not use it.
- **Original rows.** The original WHU-S01 rows (Stage 1 replies) and WHU-S07 rows (the extension's `_ext` replies) are used unchanged and are not re-judged.

## Success rule (fixed 2026-10-27, before any run)

Labels are each judge's first-read labels, read as `analyse.py` reads them for the per-judge views: a REFUSED label takes the other judge's label. The rule is met only if all three conditions hold:

1. **Understates+Omits falls under both judges.** Count WHU's conclusions labelled Understates or Omits across the 9 key conclusions:
   - under the Claude judge, below the original **5** (S01-C2, S01-C4, S07-C2, S07-C3, S07-C4);
   - under the OpenAI judge, below the original **4** (S01-C1, S01-C2, S07-C3, S07-C4).

   The originals are from `docs/whu-omissions-investigation-2026-10.md` §1.
2. **Overstates+Contradicts does not rise under either judge.** For each judge, the re-run count across the 9 conclusions is at most the original count under that judge. The originals are computed by the analysis from the original replies, by the same code. This session did not read them.
3. **M1 citation failure does not rise by more than 5 points.** WHU's two-judge combined M1 failure rate, pooled over S01 and S07, rises by no more than 5.0 percentage points: re-run ≤ original + 5.0. The rate is computed by `analyse_eight.py`'s rules (EVERY abstract-only correction; Uncited counted as a failure), not quote-checked.

**Gaps and missing answers.** If a conclusion has no countable label from a judge, the gap is reported, and that judge's condition is evaluated on the labelled conclusions. If either re-run has no answer (above), the rule is not met.

**Reported whatever the outcome**, each figure with its n:
- the per-conclusion M2 labels for both judges, by conclusion id only (no key text);
- the two-judge combined M2 score (original 4.5) and the either-judge count (original 6). These do not decide;
- M1: two-judge combined, each judge alone, agreed only, cited items only, quote-checked, uncited share and reachability;
- the WHU process measures:
  - spend per stage;
  - each new preflight row's outcome;
  - ADD sentences and declarations, against their budgets;
  - judgement candidates, relevant ones, and how each was stated or declared;
  - items sent to a person;
  - the ruling-model consistency sample.

## Predictions (written before any run; a drafting session does not read this section)

These are from the investigation's cause codes, not from the keys:
- S01-C2, S01-C4, S07-C2, S07-C3 and S07-C4 are "(f) drafting omission": the source was held and in scope, and the step-3 draft left the point out or dropped its grade. This is the class targeted by fix 2's coverage check (step 3c), by its omission rulings (4d), and by fix 3's judgement rule for the IPCC statements. We expect most of the fall here, mainly on S07.
- S01-C1 (one judge, "(b) weakened by advocate rulings") is not targeted directly. It may remain.
- The risk runs the other way. ADD sentences make pages longer, and could raise Overstates or M1 failures. Conditions 2 and 3 test that.

## Budget

- **$100 in total** across the ledger issues `whu-rerun-s01`, `whu-rerun-s07` and `whu-rerun-judging`. Fred raised it from $60 on 2026-10-27, before any run.
- **Per issue:** each WHU re-run has the $50 cap (caps.json `study_per_issue`, by its `"study": true`). Unchanged.
- **Per day:** caps.json `default_per_day` covers every ledger line, both WHU sessions together.
  - It is **$75 for UTC day 2026-10-28 only** (Fred, 2026-10-27), so both re-runs can finish that day.
  - It goes back to **$25 at 2026-10-29T00:00Z, or once both re-runs finish, whichever is first**. The restore is one committed edit: `default_per_day` back to 25, and the `_default_per_day_raise` note removed. It is done by the session Fred tells to do it. Otherwise the scoring session does it, and records it in `deviations.md`, before it starts any judging.
  - caps.json has no date field. The raise was committed at about 21:25Z on 2026-10-27, when that day's ledger already stood at $153.39, so it allowed nothing more that day.
  - A re-run still going on 2026-10-29 has the $25 day cap.
- **The $100 total is not enforced by code.** Before each paid stage, the drafting session sums the three ledger issues with `spend_ledger.py --issue`, and stops if the stage's printed estimate would take the total past $100. Where a stage takes `--cap`, the session passes the smaller of the issue's remaining $50 and the remaining $100.
- **Judging comes after both re-runs, in this order:**
  1. M1 and M2;
  2. then the quote check, only if its estimate fits what remains.

  All of it bills to `whu-rerun-judging`. Each part is estimated before any call (`prepare_scoring.py`'s projection), with `--cap` set to $100 less the three issues' spend. If the M1 and M2 estimate exceeds what remains, the work STOPs and is reported.
  - The judge runners' day cap counts only `whu-reliability-judging*` ledger issues, so it does not see `whu-rerun-judging`. The scoring session therefore checks the day's judging total by hand against caps.json `study_judging_per_day` ($150) before it starts.

## Limitations

- Only 2 questions and 9 key conclusions are tested, judged by AI models only, with no human review.
- The fixes were designed while looking at these two questions' failures (`docs/whu-omissions-investigation-2026-10.md`). Improvement here is therefore necessary but not sufficient. Fresh questions in the quarterly round are the real test.
- The plan was approved after every study result had been seen.
- The re-runs start about 3 to 6 days after the originals (S01 drafted from 22 October, S07 from 24 October). Any change to WHU's tools since the original runs, other than fixes 1-3, is not isolated from them.
- The library still holds the originals' documents (see Blinding, "Known leaks").
