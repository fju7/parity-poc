# WHU quarterly round 1: drafting briefs

Four briefs for `round1_protocol.md` (frozen at `5f4a928`), §3 (What Holds Up, with fixes 1-3, run by the post-study
runbook) and §4 (blinding), one per WHU run, for Fred to paste into a FRESH Claude Code session each. Modelled on
`rerun_briefs.md`. A drafting session does not read this file; the pasted text is all it gets.

**Before any is pasted:** the advisor checks these briefs (Fred's instruction, 2026-10-28). The answer keys are frozen
first (`keys_manifest_round1.txt`), and no WHU session ever sees a key.

**One session at a time is recommended.** The $25 day cap covers every ledger line, and the study's WHU runs cost about
$12 to $30 each, so a run may stop at the day cap and pick up after 00:00 UTC. Two sessions at once would share the
same $25. The round cap is $250 across the four WHU ledger issues and `whu-quarterly-r1-judging`.

| Run | Case directory | Slug and ledger issue |
|---|---|---|
| WHU-Q1-01 | `issues/WHU-Q1-01-whu-quarterly-r1-01/` | `whu-quarterly-r1-01` |
| WHU-Q1-02 | `issues/WHU-Q1-02-whu-quarterly-r1-02/` | `whu-quarterly-r1-02` |
| WHU-Q1-03 | `issues/WHU-Q1-03-whu-quarterly-r1-03/` | `whu-quarterly-r1-03` |
| WHU-Q1-04 | `issues/WHU-Q1-04-whu-quarterly-r1-04/` | `whu-quarterly-r1-04` |

## Brief: WHU-Q1-01 (whu-quarterly-r1-01)

```text
You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, question WHU-Q1-01. You run this one issue end to end, from the premise to `publish.py check whu-quarterly-r1-01` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-Q1-01-whu-quarterly-r1-01/
- Slug and ledger issue: whu-quarterly-r1-01
- Page: issues/WHU-Q1-01-whu-quarterly-r1-01/draft/whu-quarterly-r1-01.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-Q1-01-whu-quarterly-r1-01/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a quarterly-round question, outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including the three other round-1 questions (issues/WHU-Q1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap (caps.json default_per_day): $25 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself.
- Round cap: $250 across ledger issues whu-quarterly-r1-01, whu-quarterly-r1-02, whu-quarterly-r1-03, whu-quarterly-r1-04 and whu-quarterly-r1-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue <each of the five>`.
  2. If the stage's printed estimate would take that sum past $250, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($250 minus the five-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-Q1-01-whu-quarterly-r1-01/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-quarterly-r1-01`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-quarterly-r1-01`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-quarterly-r1-01`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-quarterly-r1-01 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-quarterly-r1-01`, then `sweep_sources.py resolve whu-quarterly-r1-01 --write`, then `sweep_registry.py registry whu-quarterly-r1-01` if a trial registry record is held.
   - 2c. Run `canary.py whu-quarterly-r1-01`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-quarterly-r1-01 scan`, bind every row, then run `bindings.py whu-quarterly-r1-01 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-quarterly-r1-01`.
   - If the page quotes a passage, run `quotations.py whu-quarterly-r1-01 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-quarterly-r1-01` and bind what it proposes, then `sources_shown.py whu-quarterly-r1-01`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-quarterly-r1-01`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-quarterly-r1-01 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-quarterly-r1-01 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-quarterly-r1-01 --page <page>`, then `ruling.py advocate whu-quarterly-r1-01`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-quarterly-r1-01`, then the GAP-016 check: `applied_check.py whu-quarterly-r1-01 --dangling`, and `ruling.py dangling whu-quarterly-r1-01` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-quarterly-r1-01` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-quarterly-r1-01 --report <page>.gate.json --scan`, then `ruling.py gate whu-quarterly-r1-01`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-quarterly-r1-01`, then `ruling.py conclusions whu-quarterly-r1-01`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-quarterly-r1-01 --cap <cap>`, then `consistency.py audit whu-quarterly-r1-01 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-quarterly-r1-01 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-quarterly-r1-01` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-quarterly-r1-01 --first <3b commit>`.
10. Run `publish.py check whu-quarterly-r1-01` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-Q1-01-whu-quarterly-r1-01/ to a NEW folder, ~/Projects/whu-study-private/WHU-Q1-01-whu-quarterly-r1-01/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-Q1-01-whu-quarterly-r1-01/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-quarterly-r1-01 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-Q1-01-whu-quarterly-r1-01/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-Q1-01 (quarterly round 1): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-quarterly-r1-01 and on all five round-1 ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## Brief: WHU-Q1-02 (whu-quarterly-r1-02)

```text
You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, question WHU-Q1-02. You run this one issue end to end, from the premise to `publish.py check whu-quarterly-r1-02` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-Q1-02-whu-quarterly-r1-02/
- Slug and ledger issue: whu-quarterly-r1-02
- Page: issues/WHU-Q1-02-whu-quarterly-r1-02/draft/whu-quarterly-r1-02.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-Q1-02-whu-quarterly-r1-02/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a quarterly-round question, outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including the three other round-1 questions (issues/WHU-Q1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap (caps.json default_per_day): $25 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself.
- Round cap: $250 across ledger issues whu-quarterly-r1-01, whu-quarterly-r1-02, whu-quarterly-r1-03, whu-quarterly-r1-04 and whu-quarterly-r1-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue <each of the five>`.
  2. If the stage's printed estimate would take that sum past $250, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($250 minus the five-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-Q1-02-whu-quarterly-r1-02/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-quarterly-r1-02`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-quarterly-r1-02`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-quarterly-r1-02`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-quarterly-r1-02 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-quarterly-r1-02`, then `sweep_sources.py resolve whu-quarterly-r1-02 --write`, then `sweep_registry.py registry whu-quarterly-r1-02` if a trial registry record is held.
   - 2c. Run `canary.py whu-quarterly-r1-02`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-quarterly-r1-02 scan`, bind every row, then run `bindings.py whu-quarterly-r1-02 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-quarterly-r1-02`.
   - If the page quotes a passage, run `quotations.py whu-quarterly-r1-02 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-quarterly-r1-02` and bind what it proposes, then `sources_shown.py whu-quarterly-r1-02`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-quarterly-r1-02`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-quarterly-r1-02 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-quarterly-r1-02 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-quarterly-r1-02 --page <page>`, then `ruling.py advocate whu-quarterly-r1-02`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-quarterly-r1-02`, then the GAP-016 check: `applied_check.py whu-quarterly-r1-02 --dangling`, and `ruling.py dangling whu-quarterly-r1-02` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-quarterly-r1-02` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-quarterly-r1-02 --report <page>.gate.json --scan`, then `ruling.py gate whu-quarterly-r1-02`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-quarterly-r1-02`, then `ruling.py conclusions whu-quarterly-r1-02`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-quarterly-r1-02 --cap <cap>`, then `consistency.py audit whu-quarterly-r1-02 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-quarterly-r1-02 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-quarterly-r1-02` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-quarterly-r1-02 --first <3b commit>`.
10. Run `publish.py check whu-quarterly-r1-02` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-Q1-02-whu-quarterly-r1-02/ to a NEW folder, ~/Projects/whu-study-private/WHU-Q1-02-whu-quarterly-r1-02/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-Q1-02-whu-quarterly-r1-02/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-quarterly-r1-02 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-Q1-02-whu-quarterly-r1-02/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-Q1-02 (quarterly round 1): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-quarterly-r1-02 and on all five round-1 ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## Brief: WHU-Q1-03 (whu-quarterly-r1-03)

```text
You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, question WHU-Q1-03. You run this one issue end to end, from the premise to `publish.py check whu-quarterly-r1-03` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-Q1-03-whu-quarterly-r1-03/
- Slug and ledger issue: whu-quarterly-r1-03
- Page: issues/WHU-Q1-03-whu-quarterly-r1-03/draft/whu-quarterly-r1-03.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-Q1-03-whu-quarterly-r1-03/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a quarterly-round question, outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including the three other round-1 questions (issues/WHU-Q1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap (caps.json default_per_day): $25 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself.
- Round cap: $250 across ledger issues whu-quarterly-r1-01, whu-quarterly-r1-02, whu-quarterly-r1-03, whu-quarterly-r1-04 and whu-quarterly-r1-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue <each of the five>`.
  2. If the stage's printed estimate would take that sum past $250, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($250 minus the five-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-Q1-03-whu-quarterly-r1-03/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-quarterly-r1-03`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-quarterly-r1-03`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-quarterly-r1-03`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-quarterly-r1-03 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-quarterly-r1-03`, then `sweep_sources.py resolve whu-quarterly-r1-03 --write`, then `sweep_registry.py registry whu-quarterly-r1-03` if a trial registry record is held.
   - 2c. Run `canary.py whu-quarterly-r1-03`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-quarterly-r1-03 scan`, bind every row, then run `bindings.py whu-quarterly-r1-03 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-quarterly-r1-03`.
   - If the page quotes a passage, run `quotations.py whu-quarterly-r1-03 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-quarterly-r1-03` and bind what it proposes, then `sources_shown.py whu-quarterly-r1-03`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-quarterly-r1-03`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-quarterly-r1-03 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-quarterly-r1-03 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-quarterly-r1-03 --page <page>`, then `ruling.py advocate whu-quarterly-r1-03`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-quarterly-r1-03`, then the GAP-016 check: `applied_check.py whu-quarterly-r1-03 --dangling`, and `ruling.py dangling whu-quarterly-r1-03` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-quarterly-r1-03` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-quarterly-r1-03 --report <page>.gate.json --scan`, then `ruling.py gate whu-quarterly-r1-03`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-quarterly-r1-03`, then `ruling.py conclusions whu-quarterly-r1-03`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-quarterly-r1-03 --cap <cap>`, then `consistency.py audit whu-quarterly-r1-03 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-quarterly-r1-03 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-quarterly-r1-03` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-quarterly-r1-03 --first <3b commit>`.
10. Run `publish.py check whu-quarterly-r1-03` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-Q1-03-whu-quarterly-r1-03/ to a NEW folder, ~/Projects/whu-study-private/WHU-Q1-03-whu-quarterly-r1-03/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-Q1-03-whu-quarterly-r1-03/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-quarterly-r1-03 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-Q1-03-whu-quarterly-r1-03/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-Q1-03 (quarterly round 1): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-quarterly-r1-03 and on all five round-1 ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## Brief: WHU-Q1-04 (whu-quarterly-r1-04)

```text
You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, question WHU-Q1-04. You run this one issue end to end, from the premise to `publish.py check whu-quarterly-r1-04` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-Q1-04-whu-quarterly-r1-04/
- Slug and ledger issue: whu-quarterly-r1-04
- Page: issues/WHU-Q1-04-whu-quarterly-r1-04/draft/whu-quarterly-r1-04.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-Q1-04-whu-quarterly-r1-04/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a quarterly-round question, outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including the three other round-1 questions (issues/WHU-Q1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap (caps.json default_per_day): $25 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself.
- Round cap: $250 across ledger issues whu-quarterly-r1-01, whu-quarterly-r1-02, whu-quarterly-r1-03, whu-quarterly-r1-04 and whu-quarterly-r1-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue <each of the five>`.
  2. If the stage's printed estimate would take that sum past $250, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($250 minus the five-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-Q1-04-whu-quarterly-r1-04/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-quarterly-r1-04`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-quarterly-r1-04`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-quarterly-r1-04`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-quarterly-r1-04 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-quarterly-r1-04`, then `sweep_sources.py resolve whu-quarterly-r1-04 --write`, then `sweep_registry.py registry whu-quarterly-r1-04` if a trial registry record is held.
   - 2c. Run `canary.py whu-quarterly-r1-04`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-quarterly-r1-04 scan`, bind every row, then run `bindings.py whu-quarterly-r1-04 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-quarterly-r1-04`.
   - If the page quotes a passage, run `quotations.py whu-quarterly-r1-04 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-quarterly-r1-04` and bind what it proposes, then `sources_shown.py whu-quarterly-r1-04`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-quarterly-r1-04`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-quarterly-r1-04 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-quarterly-r1-04 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-quarterly-r1-04 --page <page>`, then `ruling.py advocate whu-quarterly-r1-04`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-quarterly-r1-04`, then the GAP-016 check: `applied_check.py whu-quarterly-r1-04 --dangling`, and `ruling.py dangling whu-quarterly-r1-04` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-quarterly-r1-04` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-quarterly-r1-04 --report <page>.gate.json --scan`, then `ruling.py gate whu-quarterly-r1-04`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-quarterly-r1-04`, then `ruling.py conclusions whu-quarterly-r1-04`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-quarterly-r1-04 --cap <cap>`, then `consistency.py audit whu-quarterly-r1-04 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-quarterly-r1-04 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-quarterly-r1-04` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-quarterly-r1-04 --first <3b commit>`.
10. Run `publish.py check whu-quarterly-r1-04` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-Q1-04-whu-quarterly-r1-04/ to a NEW folder, ~/Projects/whu-study-private/WHU-Q1-04-whu-quarterly-r1-04/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-Q1-04-whu-quarterly-r1-04/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-quarterly-r1-04 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-Q1-04-whu-quarterly-r1-04/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-Q1-04 (quarterly round 1): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-quarterly-r1-04 and on all five round-1 ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```
