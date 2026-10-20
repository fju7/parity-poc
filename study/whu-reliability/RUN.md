# Running WHU on one study question

From the question to "ready for operator acceptance", under "The frozen WHU process" (protocol rev 27). Written 20 October 2026 for the practice run, `issues/WHU-P02-ultra-processed-foods/` (slug `ultra-processed-foods`). For a study question, replace the slug and the case directory.

**Ready for operator acceptance** means `publish.py check <slug>` prints `Ready.`: no row is a STOP, and the four excluded steps (outside review, adjudication verification, operator acceptance, publication) each read `SKIPPED — excluded from the frozen process for the study (protocol rev 27)`. A study answer is never published: `publish`, `update` and `announce` refuse it.

All commands run from the repository root with `backend/venv/bin/python3` (written `py` below). Never `--no-verify`, `--waive` or `WHU_SPEND_OVERRIDE`. Caps: the issue's $50 (`caps.json` `study_per_issue`) and the $25 day cap. If an answer can't finish within $50, that is a result: record it and stop; the limit is not raised.

## Before the first command

- **Out of reach.** The drafting session must not open `study/whu-reliability/archive/` (the earlier T02 run on this question), the pilot archive `~/Downloads/Citation Pilot 2026-10-16/` (it holds the answer key, the three tools' answers and the T0x exports), or `study/whu-reliability/runs/`. The library still holds T02's nine documents. Research starts from the question, not from the library's list.
- **The clock.** Every stage below gets one line in `issues/WHU-P02-ultra-processed-foods/study_log.md`: stage, start and end time (UTC), who ran it (Claude Code session id, or "operator"), and the ledger spend it added (`py backend/scripts/spend_ledger.py --issue ultra-processed-foods` before and after). Drafting is not metered, so its cost is reported as elapsed time.

## The sequence

| # | Stage | Command | Who | Paid | Log |
|---|---|---|---|---|---|
| 1 | Premise: belief and kill condition, written before any source is opened | `py backend/scripts/whatholdsup/premise.py init ultra-processed-foods`, then fill `premise.json`; `premise.py status ultra-processed-foods` | Claude Code | no | `premise.json` |
| 2 | Research and source store | write `sources.json`; `py backend/scripts/whatholdsup/acquire_sources.py ultra-processed-foods`; `py backend/scripts/whatholdsup/source_store.py ultra-processed-foods status` | Claude Code | no | `sources.json`, the library |
| 2a | **OPERATOR — sources the scripts can't fetch.** `acquire_sources.py` prints a search list. Fred fetches each in a browser and adds it: `py backend/scripts/whatholdsup/source_store.py ultra-processed-foods add <Sxxx> <file> --url <url> --via "<how, by whom>"`. Licence-barred sources are not fetched by machine (rule 33). | Fred | no | `study_log.md`, one line per fetch with its time |
| 3 | Draft and bind, checks B1–B24 | write `draft/ultra-processed-foods.html`; `py backend/scripts/whatholdsup/bindings.py ultra-processed-foods scan`, bind every row, `bindings.py ultra-processed-foods check`, `bindings.py ultra-processed-foods status`; `py backend/scripts/whatholdsup/lint_claims.py issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --slug ultra-processed-foods` | Claude Code | no | `bindings.json`; signer values name Claude Code and its session (`test_whatholdsup_signers.py`) |
| 3b | Commit the draft and records | `git add issues/WHU-P02-ultra-processed-foods && git commit` | Claude Code | no | the commit hash is the `--before` of step 9 |
| 4 | Machine gate, narrow | `py backend/scripts/signal/factcheck_draft.py issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --dry-run` (the plan), then without `--dry-run` and `--report issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html.gate.json` | script | **yes**, about $4.63 measured (T01) | the `.gate.json` report and its `.runs.json` |
| 5 | Gate findings, ruled | `py backend/scripts/whatholdsup/findings.py ultra-processed-foods --report <the .gate.json> --scan`, then `py backend/scripts/whatholdsup/ruling.py gate ultra-processed-foods` | ruling model | **yes**, one call per finding | `gate-findings.json`; `rulings/rulings.jsonl` |
| 5a | Apply accepted gate rulings | each `accepted` row carries `ruling_text`: replace the sentence with it word for word, re-run step 3's checks | Claude Code | no | `study_log.md`, one line per sentence |
| 6 | Conclusion judge | `py backend/scripts/whatholdsup/conclusion_judge.py ultra-processed-foods`, then `py backend/scripts/whatholdsup/ruling.py conclusions ultra-processed-foods` | script, then ruling model | **yes**, about $0.54 projected | `conclusion-review.json`; `rulings/rulings.jsonl` |
| 6a | Apply accepted conclusion rulings | the new text is in each decision's `why` after "New text:"; apply word for word, re-run step 3's checks | Claude Code | no | `study_log.md` |
| 7 | Audit stage | `py backend/scripts/whatholdsup/audit_stage.py run ultra-processed-foods --cap 50` | script (reader, ruling model, second reader) | **yes**, about $31 projected | `audit/<UTC stamp>/`: `manifest.json`, `verdicts.jsonl`, `rulings.jsonl`, `cuts.jsonl`, `second_reads.jsonl` |
| 7a | **OPERATOR — sentences that need a person.** A sentence resting only on a source no model may read is `HUMAN_READ_REQUIRED`; a card or description wording that is not a body sentence is `left_for_person` in `cuts.jsonl`. Fred reads each and records a line in the run's `human_reads.jsonl`: `{"sha": ..., "verdict": "holds", "by": "Fred Ugast", "at": "<UTC>"}`, or says it does not hold. Any left unread are cut from the answer, and the cut is logged. | Fred | no | `human_reads.jsonl`, `study_log.md` |
| 7b | Apply the audit's corrections | each sentence `must_leave_page`: the ruled wording replaces it, or it is cut; re-run step 3's checks | the audit stage applies body wording; Claude Code applies what it lists | no | `audit/<run>/` |
| 7c | Re-audit | step 7 again, until the preflight's `audit complete` row is ok (a second-reader finding accepted in one run is read in the next) | script | **yes** | a new `audit/<UTC stamp>/` |
| 8 | Commit | `git add issues/WHU-P02-ultra-processed-foods && git commit` | Claude Code | no | |
| 9 | Changecheck | `py backend/scripts/whatholdsup/changecheck.py ultra-processed-foods --page issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --before <step 3b's commit>` | script | **yes**, about $0.03–0.08 | `change-reviews.json` |
| 10 | Preflight | `py backend/scripts/whatholdsup/publish.py check ultra-processed-foods` | script | no | its output, saved to `study_log.md` |

Steps 5–9 repeat in order whenever a later step changes the page. A STOP at step 10 sends the run back to the stage that owns the row.

## A day-cap stop

The $25 day cap is below the audit's projected $31, so step 7 is expected to stop once. A stopped run's manifest has `"status": "failed"` and `"stopped_by": "day cap"` (or `"issue cap"`, which ends the answer: see Caps above).

- After 00:00 UTC, resume it in its own directory: `py backend/scripts/whatholdsup/audit_stage.py run ultra-processed-foods --resume issues/WHU-P02-ultra-processed-foods/audit/<UTC stamp> --cap 50`. It reads no finished sentence again, and it refuses if the page, bindings, held texts, prompts, model or seed changed since the stop.
- A gate or ruling call stopped by the day cap is simply run again the next day.
- Log the stop and the resume in `study_log.md`.

## Where everything is logged

- **Spend:** `backend/data/spend/ledger.jsonl`, issue `ultra-processed-foods`.
- **Rulings:** gate and conclusion rulings in `issues/WHU-P02-ultra-processed-foods/rulings/rulings.jsonl`; audit and second-reader rulings in each `audit/<run>/rulings.jsonl`. Every ruling has its time, `"by": "ruling model claude-opus-5-5"`, the model, the prompt's sha256 and its inputs. Prompts: `audit_prompts/rule.md` (audit, second reader, conclusions) and `audit_prompts/rule_cite.md` (gate).
- **Manual steps:** `issues/WHU-P02-ultra-processed-foods/study_log.md`.
- **Records:** everything in the case directory. Held documents stay in the library and are never committed.

## Needs a ruling before the run

1. **Who applies an accepted ruling's text (5a, 6a, 7b).** As written, Claude Code applies it word for word and logs it. That is drafting work, unmetered, done by the session that drafted the page.
2. **The gate's run limit.** `factcheck_draft.py` allows 2 runs per cycle (`RUNS_PER_CYCLE`) and 3 per issue (`RUNS_PER_ISSUE`); `--past-cap` and `--past-issue-cap` lift them with a recorded reason. If corrections need more gate runs than that, is it a stop (a result) or a recorded override?
3. **Whether the audit and ruling logs are committed.** They now carry each ruling's inputs, including quoted source passages of up to about 1,300 characters each. The study README says nothing that could reach a judge, and no source snapshot, is committed. As written, `audit/` and `rulings/` stay uncommitted, like `runs/`. They need adding to `.git/info/exclude` or `.gitignore`, which isn't done yet.
4. **`study_log.md` format and who keeps it.** As written, Claude Code keeps it, with operator steps entered when Fred reports them.
5. **Changecheck reads only the page body (GAP-009).** It won't read a corrected sentence in a change history. A study answer has none, so this should not bite, but it is unproven.
6. **Conclusion judge on Q2.** It isn't out of sample (README, T02 note). The protocol says this matters for the practice run only.
7. **The gate's sources.** `factcheck_draft.py` searches the web, so the gate can read sources the draft never held. That is WHU's process, but it means the gate is not limited to the library.
