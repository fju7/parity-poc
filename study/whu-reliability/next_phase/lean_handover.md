# Lean WHU accuracy test: handover (session LT, 2026-11-05 15:33Z)

The Mac is being restarted for a system update. This note says where the test stands. Details are in `deviations.md`, `lean_test_log.md` and `lean_contamination.md`. The code freeze is **fab2b3e**: no code changes until Q1-04 has finished.

## Done
- **Q1-01** (WHU-L1-01, 314b7af): Ready, but ruled **invalid** by the advisor. Its stated reading limit is contradicted by one sentence resting on S001@144900. Records and $0.99 are kept as they are.
- **Q1-02** (WHU-L1-02): Not Ready (left for a person). It was replaced by **Q1-02r** (WHU-L1-02r, b2b75d5): Ready, $2.22 ledger, about $12.13 drafting. Its contamination scan is valid, and the replay on fab2b3e was identical.
- **Q1-03** (WHU-L1-03, a4b9996): Ready, $9.42 ledger, about $17.84 drafting. Contamination scan valid. Its fail-safe counts and the not-read mismatch are recorded.
- The ruled reading-limit check (no page sentence relies on a section outside the read record) passes for Q1-02r and Q1-03.
- The advisor's rulings after Q1-03 are recorded (736ca07): standing is judged at system level; Q1-04 start; post-test fixes 6 and 7; the fix-4 pattern for Q1-03's second not-read deletion.
- **Q1-04** was started and then stopped after about 1 minute for the restart. $0 was spent; it does not count as an attempt.

## Pending, in order
1. **Q1-04.** Start a fresh drafter with the prompt from `lean_briefs.md` (sha256 `56996bacfdc0…`). The private copy is `~/Projects/whu-study-private/lean/session_lt/prompt_04_final.txt`; the older `prompt_04.txt` is stale, so don't use it. Check the room rule first: today's ledger + $7.18 likely ≤ $50. After it finishes:
   - contamination scan;
   - drafting cost;
   - `lean_failsafe.py report`;
   - audit counts;
   - the not-read mismatch and its cost;
   - the reading-limit check (sentence vs read sections) and the system-level reading-record check below;
   - archive and empty the scratchpad;
   - record and commit.
2. **Reading-record checks for Q1-03 and Q1-02r (advisor ruling 1, $0).** For each section the read record lists, report whether it was received in full by a checking stage (coverage check, advocate/omission rulings, audit), and which stage, with evidence from the logs. A listed section that no checking stage received in full makes that run invalid; it is then re-run after Q1-04 on fab2b3e.
   - The work had just begun. A first finding: the advocate's model call (`source_advocate.brief_for`) receives only source metadata and the page sentences, plus web search, not the held text. The coverage check, omission rulings, audit and judgements stages are still to be traced (ruling.py, audit_stage.py, coverage_check.units_of; logs under `issues/WHU-L1-0x-*/audit/`, `rulings/`, `advocate/`).
   - The drafter-level "seen" scripts are at `~/Projects/whu-study-private/lean/session_lt/readcheck/`.
   - Q1-03's fix-4 item: quote the page's reading-limit text, and check whether it still discloses that figures and tables were not read (as graphics).
3. **Q1-01 re-run** after Q1-04. Fresh drafter on fab2b3e, in WHU-L1-01r / ledger issue whu-lean-q1-01r. The prompt is unchanged except the slug, the folder and a line forbidding the earlier attempt (`lean_briefs.make("01", …, suffix="r")`, RERUN_LINE). Scanner `--rerun 01`; prepare_lean `ALL["WHU-Q1-01"] = "whu-lean-q1-01r"`. Plus any re-runs that ruling 1 requires.
4. **Post-test fixes 1-7**, each with a test (listed in `lean_test_log.md`), after all runs:
   1. The audit dry run makes paid calls.
   2. The redact cross-source gap.
   3. The not-read generator/preflight mismatch.
   4. A not-read record can be removed only when a read record covers it.
   5. The preflight stops on a sentence outside the read sections (exempting title blocks for source-list lines).
   6. The read record is built from what the checking stages received.
   7. Duplicate rulings when the final gate re-files findings.
5. **Judging** with `prepare_lean.py` (ledger issue whu-reliability-judging-lean, line $55), then `analyse_lean.py`, then the final report. Cost per question is shown as pipeline + drafting = total, with drafting's share.

## Ledger
Today (UTC 2026-11-05), all lines: **$40.76**. The room rule is $50. Lean issues so far:
- whu-lean-q1-01: $0.99
- whu-lean-q1-02: $1.83
- whu-lean-q1-02r: $2.22
- whu-lean-q1-03: $9.42
- whu-lean-q1-04: $0

## Next step
Ruling 2 said to start Q1-04 now, so it is next. Re-check the room rule (it resets at 00:00 UTC), then start the fresh Q1-04 drafter. While it runs, do the $0 system-level reading-record checks for Q1-03 and Q1-02r (pending item 2), but commit only after the drafter has finished, to avoid a git clash.

## Update (after the restart, 2026-11-05 ~19:30Z)
- Checks passed (main = origin/main = 488a8d2, no code change since fab2b3e, $40.76 today, prompt hash ok). **Q1-04 drafter restarted 18:58:45Z**, fresh, same prompt; running in the background.
- Pending item 2 is **done ($0)**: see the deviations rows "Ruling 1, system-level reading-record check" and "Q1-03 fix-4 item". Under ruling 1, **neither Q1-02r nor Q1-03 passes**, because lean's checking stages are retrieval-based and are never sent whole sections. Waiting on the advisor: re-run on fab2b3e, or after fix 6? Tool: `~/Projects/whu-study-private/lean/session_lt/readcheck/system_read.py` (run it on Q1-04 once it finishes).
- Not yet committed (wait for the drafter to finish): deviations.md, this note.

## Update (2026-11-05 ~20:30Z): Q1-04 finished
- **Q1-04: NOT Ready, stopped for good at 4d** (an omission was left for a person), $3.50 ledger, about $13.44 drafting, contamination VALID. Post-run steps done: scan, cost, fail-safe report, reading checks, scratchpad archived to `session_lt/scratch_after_q1-04/` and emptied, records written (lean_test_log, lean_contamination, deviations). Day total $44.26.
- **Next, waiting on the advisor:** (1) Q1-02r and Q1-03 fail ruling 1 by design of lean's retrieval-based checking. Re-run them on fab2b3e as ruled, or after fix 6? (2) Q1-01 re-run (pending item 3). (3) Q1-03's fix-4 quote is recorded. Is it disclosure? Then post-test fixes 1-7 and judging.

## Update (2026-11-05 ~21:10Z): second freeze and re-runs
- Advisor rulings after Q1-04 recorded (deviations). Q1-02r, Q1-03 and Q1-04 are invalid. Fixes 1-7 and rules 3a/3b were designed (c4679b0) and built; **freeze f11c6c9**; full suite exit 0.
- Re-runs Q1-01b..Q1-04b (folders WHU-L1-0nb, ledger issues whu-lean-q1-0nb, prompts in lean_briefs.md §WHU-Q1-0nb), one at a time. Runs line remaining $22.04 against likely $20.95.
- After each: contamination scan (`lean_contamination_scan.py <transcript> <paths> --rerun-b NN --scratch <this session's scratchpad> --cleaned <drafter start>`), `lean_reading.py <slug>` (it must pass: reading statement, sentences rest on received text, not-read records), cost, fail-safe report, archive and empty the scratchpad, record and commit.
- Judging afterwards: prepare_lean.py `ALL` must map to the 0nb slugs.
- **Q1-01b finished Not Ready ($1.19) and found three defects in f11c6c9** (deviations, 21:25Z). Q1-02b..04b are NOT started; waiting on the advisor.
- **Third freeze 9db89f2** (corrections after Q1-01b). Reserve $4 moved to the runs line ($44, $24.85 left). Order: Q1-01c (`--rerun-c 01` for the scanner), then Q1-02b, Q1-03b, Q1-04b (`--rerun-b NN`).
- **Q1-01c Ready ($1.53), reading check passes.** Next: Q1-02b. Day ledger $46.97 + $4.54 likely > $50, so it starts after 00:00 UTC (room rule).
- **Q1-02b Not Ready ($2.13): one STOP, a false positive in `omissions.leaks_source_text`** (substring, not whole-word, match; deviations 00:55Z). Contamination valid; reading check passes. Q1-03b NOT started; waiting on the advisor. If fixed: test, re-freeze, $0 re-check of Q1-02b, then Q1-03b, Q1-04b.
- **Fourth freeze c41f80f** (whole-word leak guard). Q1-02b `Ready.` on its unchanged records (only the guard row changed); Q1-01c byte-identical. Next: Q1-03b, then Q1-04b, on c41f80f.
- **Q1-03b `Ready.` ($3.10)** on c41f80f. Contamination valid; reading check passes. Open for the advisor: source form "page", premise rows filled after the source was opened, changecheck finding bound rather than ruled (deviations). Next: Q1-04b on c41f80f (`--rerun-b 04`).
- **Q1-04b Not Ready ($3.40)**, stopped for good at 4d: 4 omissions over the ADD budget (8) sent to a person, a §4.6.1 human step (rule worked as written; no code defect). Contamination valid; reading check passes. All four re-runs done. Waiting on the advisor before judging (prepare_lean.py, analyse_lean.py).
- **Fifth freeze 0fece2a** (over-budget omissions become code's "Not added" line). Q1-01c, Q1-02b, Q1-03b byte-identical on it, all `Ready.`. Q1-04b Not Ready on c41f80f. Q1-04c (new folder, ledger issue whu-lean-q1-04c) runs on 0fece2a. No judging until the advisor rules on the Q1-01c WHO fetch and Q1-03b's three choices.
- **Q1-04c Not Ready ($4.60)** on 0fece2a: one STOP, `lint_claims.unknowability` on the rule-3b "We could not establish whether … has a newer edition." line (code conflict). Rulings A-E recorded. **D run ($0.02): under the brief's path Q1-03b is BLOCKED** (the lean fail-safe removes a required "Judged not material" readers'-list line; 3 STOPs). Q1-03b's on-disk records are in the post-D state; pre-D copy in `session_lt/d_q103b_before/`. Waiting on the advisor (Q1-04c's STOP; Q1-03b after D). **No judging yet.**
- **Sixth freeze 9863fb2.** Ready: Q1-01c, Q1-02b (byte-identical), Q1-03b (Ready again after the binding fix; step 9 re-run the brief's way, $0.04). Not Ready: Q1-04c (lint STOP and missing recency provenance). Next: judging on the Ready pages (prepare_lean.py, analyse_lean.py), reported against lean_test_rule.md.
- **Judging done ($26.08); analysis run.** §10 NOT PASSED (Q1-04 Not Ready). Three scored: bars 1-3 hold; bar 4 fails (M2 Overstates+Contradicts: Claude judge 6.7%, OpenAI 20.0%, vs round-1 WHU 0% / 10.5%). M1 5.08% combined. Results: results/lean/lean_ai_only.json. Next: the final report; the post-test list.
- **Test CLOSED (advisor, 2026-11-06); the report is final** (deviations, lean_test_log "Closed"). Next phase, build only, $0 in model calls: the code-driven orchestrator (design `docs/whu-orchestrator.md`, committed before code), the gemini-4-argon overstatement check, the post-test list, and the offline replay + cost estimate. Then the advisor rules on the seeded-defect and new-questions tests.
