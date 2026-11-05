# Lean four-question test: drafting prompts

Made by `lean_briefs.py` from `quarterly/round1_briefs.md` (sha256 f1eaf131e58aff702c552d04fe239c6105351d27b7057c13f58f23d75e4ac5b4), advisor's ruling 2 of 2026-11-05. Each prompt below is given verbatim to one fresh subagent; its model and the time it started are in `lean_test_log.md`. A drafting subagent never reads this file.

## WHU-Q1-01 (whu-lean-q1-01)

Changes from round 1's brief:

- 1 x 'You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, questio' -> 'You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("'
- 7 x 'issues/WHU-Q1-01-whu-quarterly-r1-01/' -> 'issues/WHU-L1-01-whu-lean-q1-01/'
- 1 x 'It is a quarterly-round question, outside the reliability study.' -> "It is a lean-test question (round 1's question, asked again of lean WHU), outsid"
- 1 x "- Any other issue's case folder, including the three other round-1 questions (is" -> "- Any other issue's case folder, including all four round-1 questions (issues/WH"
- 1 x 'If you open one of the paths above by accident, stop and tell Fred which one.' -> 'If you open one of the paths above by accident, stop and report which one.'
- 1 x 'WHU-Q1-01 (quarterly round 1): <what>' -> 'WHU-L1-01 (lean test): <what>'
- 1 x '~/Projects/whu-study-private/WHU-Q1-01-whu-quarterly-r1-01/' -> '~/Projects/whu-study-private/WHU-L1-01-whu-lean-q1-01/'
- 1 x '- spend on whu-quarterly-r1-01 and on all five round-1 ledger issues;' -> '- spend on whu-lean-q1-01 and on all four lean-test ledger issues (whu-lean-q1-0'
- 1 x '   - Write the protected sentences (§4.5, fix 1) plainly: the question restateme' -> '   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and past'
- CAPS block -> lean caps ($10 run cap, $60 day cap, $50 room rule)
- 37 x slug whu-quarterly-r1-01 -> whu-lean-q1-01
- LEAN SWITCH block inserted before THE SEQUENCE

Prompt sha256: `e416e0d8fc4cd22225b4c92ccf73d4171f6790f98fba6828cdf85ba88fa2b0a7`

```text
You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("lean + machine scope notes"), question WHU-Q1-01. You run this one issue end to end, from the premise to `publish.py check whu-lean-q1-01` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-L1-01-whu-lean-q1-01/
- Slug and ledger issue: whu-lean-q1-01
- Page: issues/WHU-L1-01-whu-lean-q1-01/draft/whu-lean-q1-01.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-L1-01-whu-lean-q1-01/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a lean-test question (round 1's question, asked again of lean WHU), outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including all four round-1 questions (issues/WHU-Q1-*, this question's round-1 folder too) and the other lean-test questions (issues/WHU-L1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and report which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Run cap: $10 for this issue (lean test, validity_plan.md §10). Where a stage takes --cap, pass ($10 minus this issue's spend: `py backend/scripts/spend_ledger.py --issue whu-lean-q1-01`). Hitting it is a result, not a reason to raise it.
- Day cap (caps.json default_per_day): $60 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself. Before every paid stage, check that today's ledger total plus the stage's printed estimate is at most $50; if not, do not start it: record it and stop.
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

LEAN SWITCH (lean four-question test, "lean + machine scope notes"; added to round 1's brief)
- Every command runs with WHU_LEAN=1 in its environment: write `WHU_LEAN=1 py ...` for every `py` command. A command run without it is not this run.
- Read docs/whatholdsup-process.md §4.6 and §4.6.1 as well as §4.5. Where they differ from §4.5, §4.6 and §4.6.1 govern.
- Protected sentences are GENERATED, never written by hand: the question restatement and what we held, read and did not read come from issue.json and sources.json (`access.state`, `access.sections`, `access.not_read`); what we searched and did not search comes from a top-level `"search": {"searched": [...], "not_searched": [...]}` in sources.json. Fill those records, then paste the output of `WHU_LEAN=1 py backend/scripts/whatholdsup/lean_sentences.py whu-lean-q1-01 render`. The readers' list is pasted from `WHU_LEAN=1 py backend/scripts/whatholdsup/coverage_check.py whu-lean-q1-01 render`. A protected sentence written by hand is cut by the audit and stops the preflight.
- No person takes part in this run. Wherever this brief says a person, Fred or OPERATOR STEPS is needed, you STOP instead: record in study_log.md exactly which step needed a person and why, and end with the REPORT. Never write human_reads.jsonl, person_decisions.md, protected_signoffs.json or any signed field naming a person.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-L1-01-whu-lean-q1-01/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-lean-q1-01`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-lean-q1-01`.
2. Sources.
   - PUBLISHER TERMS (study rule after WHU-S05): never fetch, hold, quote from or pass to a model any copy from Elsevier (sciencedirect.com, thelancet.com, cell.com), Wiley (onlinelibrary.wiley.com, cochranelibrary.com), SAGE (journals.sagepub.com) or NCCN, UNLESS Europe PMC lists that article under a CC licence. Use the Europe PMC/PMC CC copy or an institutional repository copy instead. If neither exists, record the source as not held, with the reason "publisher terms". If acquire_sources.py has already fetched such a copy, do not use it: stop and tell Fred, naming the source.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-lean-q1-01`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-lean-q1-01 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-lean-q1-01`, then `sweep_sources.py resolve whu-lean-q1-01 --write`, then `sweep_registry.py registry whu-lean-q1-01` if a trial registry record is held.
   - 2c. Run `canary.py whu-lean-q1-01`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-lean-q1-01 scan`, bind every row, then run `bindings.py whu-lean-q1-01 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-lean-q1-01`.
   - If the page quotes a passage, run `quotations.py whu-lean-q1-01 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and paste `lean_sentences.py whu-lean-q1-01 render`.
   - 3a. Write the visible source list. Run `bibbind.py whu-lean-q1-01` and bind what it proposes, then `sources_shown.py whu-lean-q1-01`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-lean-q1-01`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-lean-q1-01 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-lean-q1-01 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-lean-q1-01 --page <page>`, then `ruling.py advocate whu-lean-q1-01`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-lean-q1-01`, then the GAP-016 check: `applied_check.py whu-lean-q1-01 --dangling`, and `ruling.py dangling whu-lean-q1-01` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-lean-q1-01` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-lean-q1-01 --report <page>.gate.json --scan`, then `ruling.py gate whu-lean-q1-01`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-lean-q1-01`, then `ruling.py conclusions whu-lean-q1-01`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-lean-q1-01 --cap <cap>`, then `consistency.py audit whu-lean-q1-01 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-lean-q1-01 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-lean-q1-01` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-lean-q1-01 --first <3b commit>`.
10. Run `publish.py check whu-lean-q1-01` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-L1-01-whu-lean-q1-01/ to a NEW folder, ~/Projects/whu-study-private/WHU-L1-01-whu-lean-q1-01/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-L1-01-whu-lean-q1-01/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-lean-q1-01 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-L1-01-whu-lean-q1-01/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-L1-01 (lean test): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-lean-q1-01 and on all four lean-test ledger issues (whu-lean-q1-01 to -04);
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## WHU-Q1-02 (whu-lean-q1-02)

Changes from round 1's brief:

- 1 x 'You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, questio' -> 'You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("'
- 7 x 'issues/WHU-Q1-02-whu-quarterly-r1-02/' -> 'issues/WHU-L1-02-whu-lean-q1-02/'
- 1 x 'It is a quarterly-round question, outside the reliability study.' -> "It is a lean-test question (round 1's question, asked again of lean WHU), outsid"
- 1 x "- Any other issue's case folder, including the three other round-1 questions (is" -> "- Any other issue's case folder, including all four round-1 questions (issues/WH"
- 1 x 'If you open one of the paths above by accident, stop and tell Fred which one.' -> 'If you open one of the paths above by accident, stop and report which one.'
- 1 x 'WHU-Q1-02 (quarterly round 1): <what>' -> 'WHU-L1-02 (lean test): <what>'
- 1 x '~/Projects/whu-study-private/WHU-Q1-02-whu-quarterly-r1-02/' -> '~/Projects/whu-study-private/WHU-L1-02-whu-lean-q1-02/'
- 1 x '- spend on whu-quarterly-r1-02 and on all five round-1 ledger issues;' -> '- spend on whu-lean-q1-02 and on all four lean-test ledger issues (whu-lean-q1-0'
- 1 x '   - Write the protected sentences (§4.5, fix 1) plainly: the question restateme' -> '   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and past'
- CAPS block -> lean caps ($10 run cap, $60 day cap, $50 room rule)
- 37 x slug whu-quarterly-r1-02 -> whu-lean-q1-02
- LEAN SWITCH block inserted before THE SEQUENCE
- DO NOT READ: one line added (advisor ruling 2026-11-05, after Q1-01): '- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.'

Prompt sha256: `c5b4c4dfc22abe32ade7f774dff429705286426a02041fff31656bc8b62828a0`

```text
You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("lean + machine scope notes"), question WHU-Q1-02. You run this one issue end to end, from the premise to `publish.py check whu-lean-q1-02` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-L1-02-whu-lean-q1-02/
- Slug and ledger issue: whu-lean-q1-02
- Page: issues/WHU-L1-02-whu-lean-q1-02/draft/whu-lean-q1-02.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-L1-02-whu-lean-q1-02/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a lean-test question (round 1's question, asked again of lean WHU), outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including all four round-1 questions (issues/WHU-Q1-*, this question's round-1 folder too) and the other lean-test questions (issues/WHU-L1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.
- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and report which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Run cap: $10 for this issue (lean test, validity_plan.md §10). Where a stage takes --cap, pass ($10 minus this issue's spend: `py backend/scripts/spend_ledger.py --issue whu-lean-q1-02`). Hitting it is a result, not a reason to raise it.
- Day cap (caps.json default_per_day): $60 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself. Before every paid stage, check that today's ledger total plus the stage's printed estimate is at most $50; if not, do not start it: record it and stop.
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

LEAN SWITCH (lean four-question test, "lean + machine scope notes"; added to round 1's brief)
- Every command runs with WHU_LEAN=1 in its environment: write `WHU_LEAN=1 py ...` for every `py` command. A command run without it is not this run.
- Read docs/whatholdsup-process.md §4.6 and §4.6.1 as well as §4.5. Where they differ from §4.5, §4.6 and §4.6.1 govern.
- Protected sentences are GENERATED, never written by hand: the question restatement and what we held, read and did not read come from issue.json and sources.json (`access.state`, `access.sections`, `access.not_read`); what we searched and did not search comes from a top-level `"search": {"searched": [...], "not_searched": [...]}` in sources.json. Fill those records, then paste the output of `WHU_LEAN=1 py backend/scripts/whatholdsup/lean_sentences.py whu-lean-q1-02 render`. The readers' list is pasted from `WHU_LEAN=1 py backend/scripts/whatholdsup/coverage_check.py whu-lean-q1-02 render`. A protected sentence written by hand is cut by the audit and stops the preflight.
- No person takes part in this run. Wherever this brief says a person, Fred or OPERATOR STEPS is needed, you STOP instead: record in study_log.md exactly which step needed a person and why, and end with the REPORT. Never write human_reads.jsonl, person_decisions.md, protected_signoffs.json or any signed field naming a person.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-L1-02-whu-lean-q1-02/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-lean-q1-02`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-lean-q1-02`.
2. Sources.
   - PUBLISHER TERMS (study rule after WHU-S05): never fetch, hold, quote from or pass to a model any copy from Elsevier (sciencedirect.com, thelancet.com, cell.com), Wiley (onlinelibrary.wiley.com, cochranelibrary.com), SAGE (journals.sagepub.com) or NCCN, UNLESS Europe PMC lists that article under a CC licence. Use the Europe PMC/PMC CC copy or an institutional repository copy instead. If neither exists, record the source as not held, with the reason "publisher terms". If acquire_sources.py has already fetched such a copy, do not use it: stop and tell Fred, naming the source.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-lean-q1-02`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-lean-q1-02 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-lean-q1-02`, then `sweep_sources.py resolve whu-lean-q1-02 --write`, then `sweep_registry.py registry whu-lean-q1-02` if a trial registry record is held.
   - 2c. Run `canary.py whu-lean-q1-02`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-lean-q1-02 scan`, bind every row, then run `bindings.py whu-lean-q1-02 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-lean-q1-02`.
   - If the page quotes a passage, run `quotations.py whu-lean-q1-02 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and paste `lean_sentences.py whu-lean-q1-02 render`.
   - 3a. Write the visible source list. Run `bibbind.py whu-lean-q1-02` and bind what it proposes, then `sources_shown.py whu-lean-q1-02`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-lean-q1-02`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-lean-q1-02 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-lean-q1-02 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-lean-q1-02 --page <page>`, then `ruling.py advocate whu-lean-q1-02`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-lean-q1-02`, then the GAP-016 check: `applied_check.py whu-lean-q1-02 --dangling`, and `ruling.py dangling whu-lean-q1-02` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-lean-q1-02` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-lean-q1-02 --report <page>.gate.json --scan`, then `ruling.py gate whu-lean-q1-02`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-lean-q1-02`, then `ruling.py conclusions whu-lean-q1-02`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-lean-q1-02 --cap <cap>`, then `consistency.py audit whu-lean-q1-02 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-lean-q1-02 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-lean-q1-02` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-lean-q1-02 --first <3b commit>`.
10. Run `publish.py check whu-lean-q1-02` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-L1-02-whu-lean-q1-02/ to a NEW folder, ~/Projects/whu-study-private/WHU-L1-02-whu-lean-q1-02/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-L1-02-whu-lean-q1-02/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-lean-q1-02 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-L1-02-whu-lean-q1-02/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-L1-02 (lean test): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-lean-q1-02 and on all four lean-test ledger issues (whu-lean-q1-01 to -04);
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## WHU-Q1-03 (whu-lean-q1-03)

Changes from round 1's brief:

- 1 x 'You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, questio' -> 'You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("'
- 7 x 'issues/WHU-Q1-03-whu-quarterly-r1-03/' -> 'issues/WHU-L1-03-whu-lean-q1-03/'
- 1 x 'It is a quarterly-round question, outside the reliability study.' -> "It is a lean-test question (round 1's question, asked again of lean WHU), outsid"
- 1 x "- Any other issue's case folder, including the three other round-1 questions (is" -> "- Any other issue's case folder, including all four round-1 questions (issues/WH"
- 1 x 'If you open one of the paths above by accident, stop and tell Fred which one.' -> 'If you open one of the paths above by accident, stop and report which one.'
- 1 x 'WHU-Q1-03 (quarterly round 1): <what>' -> 'WHU-L1-03 (lean test): <what>'
- 1 x '~/Projects/whu-study-private/WHU-Q1-03-whu-quarterly-r1-03/' -> '~/Projects/whu-study-private/WHU-L1-03-whu-lean-q1-03/'
- 1 x '- spend on whu-quarterly-r1-03 and on all five round-1 ledger issues;' -> '- spend on whu-lean-q1-03 and on all four lean-test ledger issues (whu-lean-q1-0'
- 1 x '   - Write the protected sentences (§4.5, fix 1) plainly: the question restateme' -> '   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and past'
- CAPS block -> lean caps ($10 run cap, $60 day cap, $50 room rule)
- 37 x slug whu-quarterly-r1-03 -> whu-lean-q1-03
- LEAN SWITCH block inserted before THE SEQUENCE
- DO NOT READ: one line added (advisor ruling 2026-11-05, after Q1-01): '- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.'

Prompt sha256: `90fb10dec459dd545612ffc21a6a0c3c218bac54717404dba3b485eda65f801f`

```text
You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("lean + machine scope notes"), question WHU-Q1-03. You run this one issue end to end, from the premise to `publish.py check whu-lean-q1-03` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-L1-03-whu-lean-q1-03/
- Slug and ledger issue: whu-lean-q1-03
- Page: issues/WHU-L1-03-whu-lean-q1-03/draft/whu-lean-q1-03.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-L1-03-whu-lean-q1-03/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a lean-test question (round 1's question, asked again of lean WHU), outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including all four round-1 questions (issues/WHU-Q1-*, this question's round-1 folder too) and the other lean-test questions (issues/WHU-L1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.
- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and report which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Run cap: $10 for this issue (lean test, validity_plan.md §10). Where a stage takes --cap, pass ($10 minus this issue's spend: `py backend/scripts/spend_ledger.py --issue whu-lean-q1-03`). Hitting it is a result, not a reason to raise it.
- Day cap (caps.json default_per_day): $60 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself. Before every paid stage, check that today's ledger total plus the stage's printed estimate is at most $50; if not, do not start it: record it and stop.
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

LEAN SWITCH (lean four-question test, "lean + machine scope notes"; added to round 1's brief)
- Every command runs with WHU_LEAN=1 in its environment: write `WHU_LEAN=1 py ...` for every `py` command. A command run without it is not this run.
- Read docs/whatholdsup-process.md §4.6 and §4.6.1 as well as §4.5. Where they differ from §4.5, §4.6 and §4.6.1 govern.
- Protected sentences are GENERATED, never written by hand: the question restatement and what we held, read and did not read come from issue.json and sources.json (`access.state`, `access.sections`, `access.not_read`); what we searched and did not search comes from a top-level `"search": {"searched": [...], "not_searched": [...]}` in sources.json. Fill those records, then paste the output of `WHU_LEAN=1 py backend/scripts/whatholdsup/lean_sentences.py whu-lean-q1-03 render`. The readers' list is pasted from `WHU_LEAN=1 py backend/scripts/whatholdsup/coverage_check.py whu-lean-q1-03 render`. A protected sentence written by hand is cut by the audit and stops the preflight.
- No person takes part in this run. Wherever this brief says a person, Fred or OPERATOR STEPS is needed, you STOP instead: record in study_log.md exactly which step needed a person and why, and end with the REPORT. Never write human_reads.jsonl, person_decisions.md, protected_signoffs.json or any signed field naming a person.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-L1-03-whu-lean-q1-03/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-lean-q1-03`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-lean-q1-03`.
2. Sources.
   - PUBLISHER TERMS (study rule after WHU-S05): never fetch, hold, quote from or pass to a model any copy from Elsevier (sciencedirect.com, thelancet.com, cell.com), Wiley (onlinelibrary.wiley.com, cochranelibrary.com), SAGE (journals.sagepub.com) or NCCN, UNLESS Europe PMC lists that article under a CC licence. Use the Europe PMC/PMC CC copy or an institutional repository copy instead. If neither exists, record the source as not held, with the reason "publisher terms". If acquire_sources.py has already fetched such a copy, do not use it: stop and tell Fred, naming the source.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-lean-q1-03`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-lean-q1-03 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-lean-q1-03`, then `sweep_sources.py resolve whu-lean-q1-03 --write`, then `sweep_registry.py registry whu-lean-q1-03` if a trial registry record is held.
   - 2c. Run `canary.py whu-lean-q1-03`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-lean-q1-03 scan`, bind every row, then run `bindings.py whu-lean-q1-03 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-lean-q1-03`.
   - If the page quotes a passage, run `quotations.py whu-lean-q1-03 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and paste `lean_sentences.py whu-lean-q1-03 render`.
   - 3a. Write the visible source list. Run `bibbind.py whu-lean-q1-03` and bind what it proposes, then `sources_shown.py whu-lean-q1-03`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-lean-q1-03`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-lean-q1-03 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-lean-q1-03 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-lean-q1-03 --page <page>`, then `ruling.py advocate whu-lean-q1-03`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-lean-q1-03`, then the GAP-016 check: `applied_check.py whu-lean-q1-03 --dangling`, and `ruling.py dangling whu-lean-q1-03` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-lean-q1-03` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-lean-q1-03 --report <page>.gate.json --scan`, then `ruling.py gate whu-lean-q1-03`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-lean-q1-03`, then `ruling.py conclusions whu-lean-q1-03`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-lean-q1-03 --cap <cap>`, then `consistency.py audit whu-lean-q1-03 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-lean-q1-03 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-lean-q1-03` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-lean-q1-03 --first <3b commit>`.
10. Run `publish.py check whu-lean-q1-03` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-L1-03-whu-lean-q1-03/ to a NEW folder, ~/Projects/whu-study-private/WHU-L1-03-whu-lean-q1-03/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-L1-03-whu-lean-q1-03/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-lean-q1-03 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-L1-03-whu-lean-q1-03/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-L1-03 (lean test): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-lean-q1-03 and on all four lean-test ledger issues (whu-lean-q1-01 to -04);
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## WHU-Q1-04 (whu-lean-q1-04)

Changes from round 1's brief:

- 1 x 'You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, questio' -> 'You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("'
- 7 x 'issues/WHU-Q1-04-whu-quarterly-r1-04/' -> 'issues/WHU-L1-04-whu-lean-q1-04/'
- 1 x 'It is a quarterly-round question, outside the reliability study.' -> "It is a lean-test question (round 1's question, asked again of lean WHU), outsid"
- 1 x "- Any other issue's case folder, including the three other round-1 questions (is" -> "- Any other issue's case folder, including all four round-1 questions (issues/WH"
- 1 x 'If you open one of the paths above by accident, stop and tell Fred which one.' -> 'If you open one of the paths above by accident, stop and report which one.'
- 1 x 'WHU-Q1-04 (quarterly round 1): <what>' -> 'WHU-L1-04 (lean test): <what>'
- 1 x '~/Projects/whu-study-private/WHU-Q1-04-whu-quarterly-r1-04/' -> '~/Projects/whu-study-private/WHU-L1-04-whu-lean-q1-04/'
- 1 x '- spend on whu-quarterly-r1-04 and on all five round-1 ledger issues;' -> '- spend on whu-lean-q1-04 and on all four lean-test ledger issues (whu-lean-q1-0'
- 1 x '   - Write the protected sentences (§4.5, fix 1) plainly: the question restateme' -> '   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and past'
- CAPS block -> lean caps ($10 run cap, $60 day cap, $50 room rule)
- 37 x slug whu-quarterly-r1-04 -> whu-lean-q1-04
- LEAN SWITCH block inserted before THE SEQUENCE
- DO NOT READ: one line added (advisor ruling 2026-11-05, after Q1-01): '- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.'

Prompt sha256: `56996bacfdc0932825b772a28f55b7faa6eec621f0b6b061eab2fbd057f68f5b`

```text
You are a FRESH drafting session: What Holds Up (WHU) lean four-question test ("lean + machine scope notes"), question WHU-Q1-04. You run this one issue end to end, from the premise to `publish.py check whu-lean-q1-04` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-L1-04-whu-lean-q1-04/
- Slug and ledger issue: whu-lean-q1-04
- Page: issues/WHU-L1-04-whu-lean-q1-04/draft/whu-lean-q1-04.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-L1-04-whu-lean-q1-04/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a lean-test question (round 1's question, asked again of lean WHU), outside the reliability study.

DO NOT READ (blinding; these are rules, not suggestions)
- Any answer key (any key.json), and anything under ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: the round-1 protocol, its draw records and deviations log, these briefs, the capture instructions, RUN.md, frames, answers and results.
- Any judge output or score, and any answer to this question from another system (Claude Research, ChatGPT, Gemini, Perplexity).
- Any other issue's case folder, including all four round-1 questions (issues/WHU-Q1-*, this question's round-1 folder too) and the other lean-test questions (issues/WHU-L1-*), and their git history.
- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.
- Do not open, search, list or grep inside any issues/ folder other than your own; for format examples use the process doc and backend/scripts only.

The library holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and report which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Run cap: $10 for this issue (lean test, validity_plan.md §10). Where a stage takes --cap, pass ($10 minus this issue's spend: `py backend/scripts/spend_ledger.py --issue whu-lean-q1-04`). Hitting it is a result, not a reason to raise it.
- Day cap (caps.json default_per_day): $60 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself. Before every paid stage, check that today's ledger total plus the stage's printed estimate is at most $50; if not, do not start it: record it and stop.
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

LEAN SWITCH (lean four-question test, "lean + machine scope notes"; added to round 1's brief)
- Every command runs with WHU_LEAN=1 in its environment: write `WHU_LEAN=1 py ...` for every `py` command. A command run without it is not this run.
- Read docs/whatholdsup-process.md §4.6 and §4.6.1 as well as §4.5. Where they differ from §4.5, §4.6 and §4.6.1 govern.
- Protected sentences are GENERATED, never written by hand: the question restatement and what we held, read and did not read come from issue.json and sources.json (`access.state`, `access.sections`, `access.not_read`); what we searched and did not search comes from a top-level `"search": {"searched": [...], "not_searched": [...]}` in sources.json. Fill those records, then paste the output of `WHU_LEAN=1 py backend/scripts/whatholdsup/lean_sentences.py whu-lean-q1-04 render`. The readers' list is pasted from `WHU_LEAN=1 py backend/scripts/whatholdsup/coverage_check.py whu-lean-q1-04 render`. A protected sentence written by hand is cut by the audit and stops the preflight.
- No person takes part in this run. Wherever this brief says a person, Fred or OPERATOR STEPS is needed, you STOP instead: record in study_log.md exactly which step needed a person and why, and end with the REPORT. Never write human_reads.jsonl, person_decisions.md, protected_signoffs.json or any signed field naming a person.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-L1-04-whu-lean-q1-04/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-lean-q1-04`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-lean-q1-04`.
2. Sources.
   - PUBLISHER TERMS (study rule after WHU-S05): never fetch, hold, quote from or pass to a model any copy from Elsevier (sciencedirect.com, thelancet.com, cell.com), Wiley (onlinelibrary.wiley.com, cochranelibrary.com), SAGE (journals.sagepub.com) or NCCN, UNLESS Europe PMC lists that article under a CC licence. Use the Europe PMC/PMC CC copy or an institutional repository copy instead. If neither exists, record the source as not held, with the reason "publisher terms". If acquire_sources.py has already fetched such a copy, do not use it: stop and tell Fred, naming the source.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-lean-q1-04`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-lean-q1-04 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below. (ipcc.ch's HTML pages may answer scripts with HTTP 403; its PDF downloads have answered. A 403 is never worked around.)
   - 2b. Run `errata.py whu-lean-q1-04`, then `sweep_sources.py resolve whu-lean-q1-04 --write`, then `sweep_registry.py registry whu-lean-q1-04` if a trial registry record is held.
   - 2c. Run `canary.py whu-lean-q1-04`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-lean-q1-04 scan`, bind every row, then run `bindings.py whu-lean-q1-04 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-lean-q1-04`.
   - If the page quotes a passage, run `quotations.py whu-lean-q1-04 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and paste `lean_sentences.py whu-lean-q1-04 render`.
   - 3a. Write the visible source list. Run `bibbind.py whu-lean-q1-04` and bind what it proposes, then `sources_shown.py whu-lean-q1-04`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-lean-q1-04`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-lean-q1-04 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-lean-q1-04 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-lean-q1-04 --page <page>`, then `ruling.py advocate whu-lean-q1-04`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-lean-q1-04`, then the GAP-016 check: `applied_check.py whu-lean-q1-04 --dangling`, and `ruling.py dangling whu-lean-q1-04` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-lean-q1-04` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-lean-q1-04 --report <page>.gate.json --scan`, then `ruling.py gate whu-lean-q1-04`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-lean-q1-04`, then `ruling.py conclusions whu-lean-q1-04`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-lean-q1-04 --cap <cap>`, then `consistency.py audit whu-lean-q1-04 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-lean-q1-04 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-lean-q1-04` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-lean-q1-04 --first <3b commit>`.
10. Run `publish.py check whu-lean-q1-04` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The rows added after the study are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-L1-04-whu-lean-q1-04/ to a NEW folder, ~/Projects/whu-study-private/WHU-L1-04-whu-lean-q1-04/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-L1-04-whu-lean-q1-04/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-lean-q1-04 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-L1-04-whu-lean-q1-04/, with plain commits: `git add <those paths>`, check `git diff --cached --name-only` shows only them, then `git commit -m "WHU-L1-04 (lean test): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why, and say plainly whether this run is FINISHED (Ready., or stopped for good);
- the study log;
- spend on whu-lean-q1-04 and on all four lean-test ledger issues (whu-lean-q1-01 to -04);
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```
