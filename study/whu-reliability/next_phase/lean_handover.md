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
