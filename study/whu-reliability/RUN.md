# Running WHU on one study question

From the question to "ready for operator acceptance", under "The frozen WHU process" (protocol rev 27) and the advisor's rulings of 20 October 2026 (below). Written for the practice run, `issues/WHU-P02-ultra-processed-foods/` (slug `ultra-processed-foods`). For a study question, replace the slug and the case directory; **every study issue directory is named `WHU-P…` or `WHU-S…`**, because the exclude entries (ruling 3) are keyed to those names.

**Ready for operator acceptance** means `publish.py check <slug>` prints `Ready.`: no row is a STOP, and the four excluded steps (outside review, adjudication verification, operator acceptance, publication) each read `SKIPPED — excluded from the frozen process for the study (protocol rev 27)`. A study answer is never published: `publish`, `update` and `announce` refuse it.

All commands run from the repository root with `backend/venv/bin/python3` (written `py` below). Never `--no-verify`, `--waive` or `WHU_SPEND_OVERRIDE`. Caps: the issue's $50 (`caps.json` `study_per_issue`) and the $25 day cap. If an answer can't finish within $50, that is a result: record it and stop; the limit is not raised.

## Do not read (the drafting session)

- `study/whu-reliability/`, except this file (`RUN.md`);
- `study/whu-reliability/archive/` (the earlier T02 run on this question);
- `~/Downloads/Citation Pilot 2026-10-16/` (the pilot: answer key, the three tools' answers, the T0x exports);
- any judge output (`study/whu-reliability/runs/`, any `replies*` directory, any M1/M2 score);
- the T02 sentences in `docs/whatholdsup-conclusion-judge.md` (its calibration sections).

The library still holds T02's nine documents. Research starts from the question, not from the library's list.

## The study log

`issues/WHU-P02-ultra-processed-foods/study_log.md`, kept by the drafting session (ruling 4). One row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|

Start and end are read from the clock (`date -u +%Y-%m-%dT%H:%M:%SZ`), not estimated. Metered spend is the ledger's figure for the issue after the stage minus before (`py backend/scripts/spend_ledger.py --issue ultra-processed-foods`). Operator minutes are Fred's, as he reports them; 0 for a stage he took no part in. Drafting is not metered, so its cost is its elapsed time.

## The sequence

| # | Stage | Command | Who | Paid | Writes |
|---|---|---|---|---|---|
| 1 | Premise: belief and kill condition, written before any source is opened | `py backend/scripts/whatholdsup/premise.py init ultra-processed-foods`, then fill `premise.json`; `premise.py status ultra-processed-foods` | Claude Code | no | `premise.json` |
| 2 | Research and source store | write `sources.json`; `py backend/scripts/whatholdsup/acquire_sources.py ultra-processed-foods`; `py backend/scripts/whatholdsup/source_store.py ultra-processed-foods status` | Claude Code | no | `sources.json`, the library |
| 2a | **OPERATOR — sources the scripts can't fetch.** `acquire_sources.py` prints a search list. Fred fetches each in a browser and adds it: `py backend/scripts/whatholdsup/source_store.py ultra-processed-foods add <Sxxx> <file> --url <url> --via "<how, by whom>"`. Licence-barred sources are not fetched by machine (rule 33). | Fred | no | one study-log row per fetch |
| 3 | Draft and bind, checks B1–B24 | write `draft/ultra-processed-foods.html`; `py backend/scripts/whatholdsup/bindings.py ultra-processed-foods scan`, bind every row, `bindings.py ultra-processed-foods check`, `bindings.py ultra-processed-foods status`; `py backend/scripts/whatholdsup/lint_claims.py issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --slug ultra-processed-foods` | Claude Code | no | `bindings.json` (not committed); signer values name Claude Code and its session |
| 3b | **The first full draft.** Commit the page and the committable records | `git add issues/WHU-P02-ultra-processed-foods && git commit` (the exclude entries keep out what must not go) | Claude Code | no | this commit is the "first full draft" of steps 9 and 9a |
| 4 | Machine gate, narrow | `py backend/scripts/signal/factcheck_draft.py issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --dry-run` (the plan), then without `--dry-run` and with `--report issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html.gate.json`. At most three runs (ruling 2). | script | **yes**, about $4.63 measured (T01) | the `.gate.json` report and its `.runs.json` |
| 5 | Gate findings, ruled | `py backend/scripts/whatholdsup/findings.py ultra-processed-foods --report <the .gate.json> --scan`, then `py backend/scripts/whatholdsup/ruling.py gate ultra-processed-foods` | ruling model | **yes**, one call per finding | `gate-findings.json`; `rulings/rulings.jsonl` |
| 5a | Apply accepted gate rulings | each `accepted` row carries `ruling_text`: the drafting session replaces the sentence with it word for word (ruling 1), then re-runs step 3's checks | Claude Code, then the applied-text check | no | the applied-text check's log |
| 6 | Conclusion judge | `py backend/scripts/whatholdsup/conclusion_judge.py ultra-processed-foods`, then `py backend/scripts/whatholdsup/ruling.py conclusions ultra-processed-foods` | script, then ruling model | **yes**, about $0.54 projected | `conclusion-review.json`; `rulings/rulings.jsonl` |
| 6a | Apply accepted conclusion rulings | the new text is in each decision's `why` after "New text:"; applied word for word (ruling 1), step 3's checks re-run | Claude Code, then the applied-text check | no | the applied-text check's log |
| 7 | Audit stage | `py backend/scripts/whatholdsup/audit_stage.py run ultra-processed-foods --cap 50` | script (reader, ruling model, second reader) | **yes**, about $31 projected | `audit/<UTC stamp>/`: `manifest.json`, `verdicts.jsonl`, `rulings.jsonl`, `cuts.jsonl`, `second_reads.jsonl` |
| 7a | **OPERATOR — sentences that need a person.** A sentence resting only on a source no model may read is `HUMAN_READ_REQUIRED`; a card or description wording that is not a body sentence is `left_for_person` in `cuts.jsonl`. Fred reads each and records a line in the run's `human_reads.jsonl`: `{"sha": ..., "verdict": "holds", "by": "Fred Ugast", "at": "<UTC>"}`, or says it does not hold. Any left unread are cut from the answer, and the cut is logged. | Fred | no | `human_reads.jsonl`; a study-log row |
| 7b | Apply the audit's corrections | each sentence `must_leave_page`: the ruled wording replaces it word for word, or it is cut; step 3's checks re-run | the audit stage applies body wording; Claude Code applies what it lists; then the applied-text check | no | `audit/<run>/` |
| 7c | Re-audit | step 7 again, until the preflight's `audit complete` row is ok (a second-reader finding accepted in one run is read in the next) | script | **yes** | a new `audit/<UTC stamp>/` |
| 8 | Commit | `git add issues/WHU-P02-ultra-processed-foods && git commit` | Claude Code | no | |
| 9 | Changecheck | `py backend/scripts/whatholdsup/changecheck.py ultra-processed-foods --page issues/WHU-P02-ultra-processed-foods/draft/ultra-processed-foods.html --before <step 3b's commit>` | script | **yes**, about $0.03–0.08 | `change-reviews.json` |
| 9a | Changecheck coverage (ruling 5) | the coverage check: every body sentence changed since step 3b's commit must be among those changecheck read; any it missed are reported | script | no | its report, in the study log |
| 10 | Preflight | `py backend/scripts/whatholdsup/publish.py check ultra-processed-foods` | script | no | its output, in the study log |
| 11 | Archive the private files (ruling 3) | see "The private archive" below | Claude Code | no | `private_manifest.txt` (committed) |

Steps 5–9a repeat in order whenever a later step changes the page. A STOP at step 10 sends the run back to the stage that owns the row.

## The private archive

The repository is public. Audit and ruling logs, and every file that quotes source passages, are never committed (ruling 3). `.gitignore` excludes, for every `issues/WHU-P*` and `issues/WHU-S*` directory: `audit/`, `rulings/`, `export/`, `bindings.json` (spans and envelopes), `gate-findings.json`, `quotations.json`, `conclusion-review.json`, `change-reviews.json`, and the gate reports `draft/*.gate.json*`. Committed: `issue.json`, `premise.json`, `sources.json`, the draft page (WHU's own prose; changecheck reads it from a commit), `study_log.md` and `private_manifest.txt`.

After the run (and after any day that ends mid-run), copy every excluded file to the private archive and commit only their sha256:

```
I=issues/WHU-P02-ultra-processed-foods
D=~/Projects/whu-study-private/WHU-P02-ultra-processed-foods/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$D"
git ls-files --others --ignored --exclude-standard "$I" | while read f; do mkdir -p "$D/$(dirname "$f")"; cp -p "$f" "$D/$f"; done
(cd "$D" && find . -type f | sort | xargs shasum -a 256) > "$I/private_manifest.txt"
git add "$I/private_manifest.txt" && git commit -m "WHU-P02: private archive manifest"
```

## A day-cap stop

The $25 day cap is below the audit's projected $31, so step 7 is expected to stop once. A stopped run's manifest has `"status": "failed"` and `"stopped_by": "day cap"` (or `"issue cap"`, which ends the answer: see Caps above).

- After 00:00 UTC, resume it in its own directory: `py backend/scripts/whatholdsup/audit_stage.py run ultra-processed-foods --resume issues/WHU-P02-ultra-processed-foods/audit/<UTC stamp> --cap 50`. It reads no finished sentence again, and it refuses if the page, bindings, held texts, prompts, model or seed changed since the stop.
- A gate or ruling call stopped by the day cap is run again the next day.
- Each stop and resume is a study-log row.

## Where everything is logged

- **Spend:** `backend/data/spend/ledger.jsonl`, issue `ultra-processed-foods`.
- **Rulings:** gate and conclusion rulings in `rulings/rulings.jsonl`; audit and second-reader rulings in each `audit/<run>/rulings.jsonl`. Every ruling has its time, `"by": "ruling model claude-opus-5-5"`, the model, the prompt's sha256 and its inputs. Prompts: `audit_prompts/rule.md` (audit, second reader, conclusions) and `audit_prompts/rule_cite.md` (gate). Not committed; archived privately.
- **Stages:** `study_log.md`.
- **Held documents** stay in the library and are never committed.

## Rulings (advisor, 2026-10-20)

1. **Applied ruling text.** Accepted ruling text is applied word for word by the drafting session. A script then checks that each applied sentence on the page equals the ruling's text exactly, and logs it. *That script is not yet built; it is needed before step 5a first runs.*
2. **Gate run limits: no override.** A sentence still failing after the third gate run is cut, the cut is logged, and the answer continues. `--past-cap` and `--past-issue-cap` are never used.
3. **Logs and source quotations are never committed** (the repository is public). The exclude entries are in `.gitignore` (above). After a run the logs are copied to `~/Projects/whu-study-private/<issue>/`, and only a manifest of their sha256 is committed.
4. **`study_log.md`:** one row per stage — stage, start and end (UTC, from the clock), metered spend (from the ledger), operator minutes, outcome. Kept by the drafting session.
5. **Changecheck coverage.** After the final changecheck, a script confirms that changecheck read every body sentence changed since the first full draft (step 3b), and reports any it missed. *That script is not yet built; it is needed before step 9a first runs.*
6. **Conclusion judge on Q2.** It was calibrated partly on T02's sentences, so on Q2 it is not out of sample. This applies to the practice run only.
7. **The paid gate's web search** is part of WHU's process and stays.
