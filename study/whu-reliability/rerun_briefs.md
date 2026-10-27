# WHU post-study re-run: drafting briefs

Two briefs for `rerun_plan.md`, for Fred to paste into two FRESH Claude Code sessions after 00:00 UTC. Paste each one whole, one per session. The sessions share the $25 day cap, so expect day-cap stops: the audit alone was projected at about $31 per issue in the study. A drafting session does not read this file; the pasted text is all it gets.

## Brief: WHU-S01r (whu-rerun-s01)

```text
You are a FRESH drafting session: the post-study re-run WHU-S01r of WHU-S01, under WHU fixes 1-3. You run this one issue end to end, from the premise to `publish.py check whu-rerun-s01` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-S01r-whu-rerun-s01/
- Slug and ledger issue: whu-rerun-s01
- Page: issues/WHU-S01r-whu-rerun-s01/draft/whu-rerun-s01.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md. It mentions S01 and S07 only as unit counts and STOP rows; that is known and accepted.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-S01r-whu-rerun-s01/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a post-study re-run, outside the study.

DO NOT READ (blinding; these are rules, not suggestions)
- issues/WHU-S01-tb-dna-testing/, all of it, and its git history (no git log, show or diff on it).
- Any answer key (any key.json), any judge output or score, any M1 or M2 figure.
- ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: RUN.md, the plans (rerun_plan.md and its predictions), rerun_briefs.md, frames, answers and results.
- docs/whu-omissions-investigation-2026-10.md.
- docs/whu-fix2-omission-rulings-design.md, and §2 of docs/whu-fix3-evidence-standard.md.
- backend/data/whatholdsup/library/issues/tb-dna-testing.json and every backend/data/whatholdsup/library/_reachability_tb-dna-testing* file.
- Any other issue's case folder.
- Tests or fixtures that name S01 or S07. Running the suite through the pre-commit hook is allowed.

The library still holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap: $25 (default_per_day). It is shared with the other re-run session.
- Re-run total: $60 across ledger issues whu-rerun-s01, whu-rerun-s07 and whu-rerun-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue whu-rerun-s01`, `--issue whu-rerun-s07` and `--issue whu-rerun-judging`.
  2. If the stage's printed estimate would take that sum past $60, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($60 minus the three-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-S01r-whu-rerun-s01/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-rerun-s01`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-rerun-s01`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-rerun-s01`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-rerun-s01 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below.
   - 2b. Run `errata.py whu-rerun-s01`, then `sweep_sources.py resolve whu-rerun-s01 --write`, then `sweep_registry.py registry whu-rerun-s01` if a trial registry record is held.
   - 2c. Run `canary.py whu-rerun-s01`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-rerun-s01 scan`, bind every row, then run `bindings.py whu-rerun-s01 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-rerun-s01`.
   - If the page quotes a passage, run `quotations.py whu-rerun-s01 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-rerun-s01` and bind what it proposes, then `sources_shown.py whu-rerun-s01`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-rerun-s01`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-rerun-s01 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-rerun-s01 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-rerun-s01 --page <page>`, then `ruling.py advocate whu-rerun-s01`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-rerun-s01`, then the GAP-016 check: `applied_check.py whu-rerun-s01 --dangling`, and `ruling.py dangling whu-rerun-s01` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-rerun-s01` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-rerun-s01 --report <page>.gate.json --scan`, then `ruling.py gate whu-rerun-s01`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-rerun-s01`, then `ruling.py conclusions whu-rerun-s01`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-rerun-s01 --cap <cap>`, then `consistency.py audit whu-rerun-s01 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-rerun-s01 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-rerun-s01` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-rerun-s01 --first <3b commit>`.
10. Run `publish.py check whu-rerun-s01` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The new rows are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-S01r-whu-rerun-s01/ to a NEW folder, ~/Projects/whu-study-private/WHU-S01r-whu-rerun-s01/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-S01r-whu-rerun-s01/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-rerun-s01 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-S01r-whu-rerun-s01/, with plain commits: `git add <those paths>` and `git commit -m "WHU-S01r (post-study re-run): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why;
- the study log;
- spend on whu-rerun-s01 and on all three re-run ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

## Brief: WHU-S07r (whu-rerun-s07)

```text
You are a FRESH drafting session: the post-study re-run WHU-S07r of WHU-S07, under WHU fixes 1-3. You run this one issue end to end, from the premise to `publish.py check whu-rerun-s07` printing `Ready.`. The work is paid and metered.

Repo: /Users/fredugast/Projects/parity-poc-repo, on main only. Never create a branch or a worktree.
- Case directory: issues/WHU-S07r-whu-rerun-s07/
- Slug and ledger issue: whu-rerun-s07
- Page: issues/WHU-S07r-whu-rerun-s07/draft/whu-rerun-s07.html
- `py` means backend/venv/bin/python3. Every command runs from the repository root.
- Read the clock with `date -u +%Y-%m-%dT%H:%M:%SZ`. Never estimate the time.

READ FIRST
- CLAUDE.md. It mentions S01 and S07 only as unit counts and STOP rows; that is known and accepted.
- docs/whatholdsup-process.md: §0-§5 and §4.5 (the post-study runbook).
- docs/whu-fix3-evidence-standard.md §3 ONLY (the rule).
- issues/WHU-S07r-whu-rerun-s07/issue.json. Its "study": true is only so the tools run and publish refuses it. It is a post-study re-run, outside the study.

DO NOT READ (blinding; these are rules, not suggestions)
- issues/WHU-S07-urban-form-transport-emissions/, all of it, and its git history (no git log, show or diff on it).
- Any answer key (any key.json), any judge output or score, any M1 or M2 figure.
- ~/Projects/whu-study-private/. The only exception is step 11: you create your own new subfolder and write into it, and read nothing else there.
- study/whu-reliability/, all of it: RUN.md, the plans (rerun_plan.md and its predictions), rerun_briefs.md, frames, answers and results.
- docs/whu-omissions-investigation-2026-10.md.
- docs/whu-fix2-omission-rulings-design.md, and §2 of docs/whu-fix3-evidence-standard.md.
- backend/data/whatholdsup/library/issues/urban-form-transport-emissions.json and every backend/data/whatholdsup/library/_reachability_urban-form-transport-emissions* file.
- Any other issue's case folder.
- Tests or fixtures that name S01 or S07. Running the suite through the pre-commit hook is allowed.

The library still holds documents from earlier runs. Research starts from the question, never from the library's list. If you open one of the paths above by accident, stop and tell Fred which one.

CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Issue cap: $50 (caps.json study_per_issue).
- Day cap: $25 (default_per_day). It is shared with the other re-run session.
- Re-run total: $60 across ledger issues whu-rerun-s01, whu-rerun-s07 and whu-rerun-judging. Code does not enforce it, so you do:
  1. Before every paid stage, sum `py backend/scripts/spend_ledger.py --issue whu-rerun-s01`, `--issue whu-rerun-s07` and `--issue whu-rerun-judging`.
  2. If the stage's printed estimate would take that sum past $60, do not start the stage. Stop and report.
  3. Where a stage takes --cap, pass the smaller of ($50 minus this issue's spend) and ($60 minus the three-issue sum).
- A stage that prints NOT STARTED for the day cap: record it in the study log, stop, and resume after the next 00:00 UTC with the stage's own resume command.
- If the answer cannot reach `Ready.` within the caps, that is a result. Record it and stop. No cap is raised.

THE SEQUENCE
The post-study runbook is §4.5 plus fix 3. The frozen RUN.md does NOT govern this run. Keep issues/WHU-S07r-whu-rerun-s07/study_log.md with one row per stage:

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |

1. Premise, written BEFORE any source is opened.
   - Run `py backend/scripts/whatholdsup/premise.py init whu-rerun-s07`.
   - Fill the belief and the kill condition.
   - Fill `scope` {covers, out[{what, why}], by, written_at}.
   - Fill `evidence_standard` {weighs: measured and/or assessed, measured, assessed, when_they_differ: "state both", by, written_at}.
   - Run `premise.py status whu-rerun-s07`.
2. Sources.
   - Write sources.json, then run `py backend/scripts/whatholdsup/acquire_sources.py whu-rerun-s07`. For an IPCC AR6 WGII or WGIII chapter, it adds that report's SPM.
   - Run `source_store.py whu-rerun-s07 status`.
   - 2a. A source the scripts cannot fetch needs a person: see OPERATOR STEPS below.
   - 2b. Run `errata.py whu-rerun-s07`, then `sweep_sources.py resolve whu-rerun-s07 --write`, then `sweep_registry.py registry whu-rerun-s07` if a trial registry record is held.
   - 2c. Run `canary.py whu-rerun-s07`, again after any source is added, and again before step 10.
3. Draft and bind.
   - Write the page.
   - Run `bindings.py whu-rerun-s07 scan`, bind every row, then run `bindings.py whu-rerun-s07 check` and `status`.
   - Run `lint_claims.py <page> --slug whu-rerun-s07`.
   - If the page quotes a passage, run `quotations.py whu-rerun-s07 --page <page> --init`, fill each quotation, and re-run without --init until nothing is BLOCKED.
   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.
   - 3a. Write the visible source list. Run `bibbind.py whu-rerun-s07` and bind what it proposes, then `sources_shown.py whu-rerun-s07`.
   - 3c. Coverage (§4.5): run `coverage_check.py whu-rerun-s07`. Every headline unit must be used, added, or declared, with `declare <key> out_of_scope|not_material --why ... --by ...`. Render the readers' list ("Findings in our sources we judged outside this question") with `coverage_check.py whu-rerun-s07 render`.
   - 3d. Fix 3, paid at about $0.02 per candidate. Run `ruling.py judgements whu-rerun-s07 --cap <cap>`. State each relevant judgement on the page with its certainty or confidence terms, bound inside it, or declare it on the readers' list.
   - 3b. Commit the first full draft (see COMMITS). This commit is the "first full draft" for the protected-sentences row and for changecheck.
4. Gate, at most three runs in all, counting 7d.
   - Run `py backend/scripts/signal/factcheck_draft.py <page> --dry-run`.
   - Then run it again without --dry-run, with `--report <page>.gate.json`.
   - 4b. Run `source_advocate.py run whu-rerun-s07 --page <page>`, then `ruling.py advocate whu-rerun-s07`, which rules MISSTATES objections.
   - 4c. Apply the accepted rulings word for word. Re-run the step-3 checks, then `applied_check.py whu-rerun-s07`, then the GAP-016 check: `applied_check.py whu-rerun-s07 --dangling`, and `ruling.py dangling whu-rerun-s07` if it lists anything. Repeat until clean.
   - 4d. Run `ruling.py omissions whu-rerun-s07` (LEAVES_OUT objections).
   - 4e. Insert each ADD word for word directly after the sentence it names, and bind it with "origin": "omission_add". Then run applied_check and --dangling as in 4c. Any declarations go on the readers' list.
5. Run `findings.py whu-rerun-s07 --report <page>.gate.json --scan`, then `ruling.py gate whu-rerun-s07`.
   - 5a. Apply as in 4c.
6. Run `conclusion_judge.py whu-rerun-s07`, then `ruling.py conclusions whu-rerun-s07`.
   - 6a. Apply as in 4c.
7. Audit: `audit_stage.py run whu-rerun-s07 --cap <cap>`, then `consistency.py audit whu-rerun-s07 <stamp>`.
   - 7a. Sentences that need a person go to Fred (OPERATOR STEPS). A sentence left unread is cut, and the cut is logged.
   - 7b. Apply every accepted wording or cut from the audit's logs word for word, then run the step-3 checks, applied_check and --dangling.
   - 7c. Re-audit until the preflight's "audit complete" row is ok.
   - 7d. Run the final narrow gate with `--changed-since <page>.gate.json` (dry run first), then step 5 on its findings.
8. Commit.
9. Run `changecheck.py whu-rerun-s07 --page <page> --before <3b commit>`. If it reports findings, run `ruling.py changecheck whu-rerun-s07` and apply as in 4c.
   - 9a. Run `changecheck_coverage.py whu-rerun-s07 --first <3b commit>`.
10. Run `publish.py check whu-rerun-s07` until it prints `Ready.`. A STOP sends you back to the stage that owns the row. The new rows are:
    - "protected sentences kept";
    - "omission objections ruled";
    - "headline conclusions accounted for";
    - "declared findings shown to readers";
    - "assessment judgements stated";
    - the premise rows "scope declared" and "evidence standard declared".

    Never run publish, update or announce. They refuse this issue anyway.
11. Private archive. Copy every git-ignored file under issues/WHU-S07r-whu-rerun-s07/ to a NEW folder, ~/Projects/whu-study-private/WHU-S07r-whu-rerun-s07/<UTC stamp>/, with paths kept. Write their sha256 list to issues/WHU-S07r-whu-rerun-s07/private_manifest.txt and commit it. Do the same at the end of any day that stops mid-run.

Steps 5 to 9a repeat in order whenever a later step changes the page. Ruling text is applied word for word, never paraphrased. Signer fields follow CLAUDE.md "RULE — Who may be named in a WHU signed field". You write your own agent name, never Fred's.

OPERATOR STEPS
When a person is needed (a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence, a sign-off, anything for a person), STOP and give Fred numbered steps:
- exactly what to open, from where, and what to do;
- downloads go to ~/Downloads ONLY, and his advisor places them;
- the exact command that takes each file in, for example `source_store.py whu-rerun-s07 add <Sxxx> <file> --url <url> --via "<how, by whom>"`.

Then wait. Never sign in, create an account, pay, or get past a paywall or bot wall.

COMMITS (Fred's instruction: commit and push)
- Commit only paths under issues/WHU-S07r-whu-rerun-s07/, with plain commits: `git add <those paths>` and `git commit -m "WHU-S07r (post-study re-run): <what>"`.
- The .gitignore keeps out audit/, rulings/, bindings.json, quotations.json and gate reports. Never force-add them.
- Do not commit the ledger, the library, CLAUDE.md or any other path, even if you find it modified.
- Never use --no-verify or --amend. If the pre-commit hook fails, stop and report its output.
- After each commit, run `git push origin main` and confirm the output shows `<old>..<new>  main -> main`. "Everything up-to-date" with no such line is a failed push.
- If the push is rejected, stop and report. Never force-push.

REPORT, at the end or at any stop:
- where you stopped and why;
- the study log;
- spend on whu-rerun-s07 and on all three re-run ledger issues;
- each preflight row;
- ADD sentences and declarations against their budgets;
- judgement candidates, relevant and stated;
- items sent to a person;
- every commit hash, and the "main -> main" line of each push.
```

