# What Holds Up — standing rules for the orchestrator trial and after

Compiled 2026-11-27 from the advisor's rulings (deviations.md, patches.jsonl, up to P169) and this session's briefs.
Each rule names where it was ruled. These rules are applied without asking; work stops and is reported only for
the three cases in §9.

## 1. Fail-safe: when in doubt, take it out

- A sentence, line or source that cannot be shown to rest on what was received is removed or never written; the
  page says what could not be established (lean fail-safe, lean_failsafe.py; "We could not verify where this
  belief is published.", P142).
- A check that cannot see fails; it never reports success while blind (CLAUDE.md, golden-set rule 1). Unmeasured is
  a failure; a registry non-answer is "not checkable", never clean (P091, SAP-Signal-3).
- A partial step never leaves a page: a step stopped mid-way is rolled back to its start (P149).
- A unit stated on the page is never declared on the readers' list; a unit whose statement was removed becomes a
  "not stated" line (P153, P155, P159).

## 2. Every bound is derived, never fixed

- A pre-step or per-call bound = max(the step's dry-run estimate, the highest same-config measured figure) x 2
  (MARGIN). Never a mean, never a pooled figure, never a constant (P141 sweep; P164 for the belief call).
- Same config = the same model and the same kind of run (orchestrated or not); the reply-limits table is recorded,
  not matched (P141).
- A step's limit = (calls it may make) x its per-call bound (P164). A limit below the step's own per-call
  reservation is an error (the $0.50 belief limit, P164).

## 3. Per-call reservation

- A multi-call stage reserves only its NEXT call's bound, checked against what is left before every paid call
  (spend_ledger._reserve_next). A call that does not fit is a cap stop, recorded with the calls made and left, the
  page restored (P149).
- The needed cap for a run = the most, over the run, of likely spend so far + the next call's bound; caps are set to
  it rounded up to the next $0.50, never above the line's remainder or $10.00 (P151, P168).

## 4. Fix the class, not the instance

- Every defect a run finds is fixed for its whole class, with a test on the run's own records.
- Before the next paid run, a $0 check of the same class runs across ALL recorded case folders (the text-assembly
  sweep, P163, is the model: text_sweep.py over every orchestrated case, plus constructed hard cases).
- Replays of pages generated under earlier rules run under those rules, by a stated fixture, with their expectations
  unchanged; each new rule has its own tests (P158).

## 5. Never loosen a check to make a run pass

- No threshold, budget or check is lowered, widened or skipped to get a page through (KEY_WORDS_SHARE unchanged,
  P142; the declaration budget unchanged, P157, P160; the $10 provenance limit unchanged, P112).
- A run that would only spend toward a known, certain stop is not started (P140 ruling 6; the $0.50 belief limit,
  2026-11-27).
- If a run does not reach Ready under a brief that says so, no further paid call is made in that trial (P157 ruling 5).

## 6. One checked script per edit-and-commit

- Each edit-and-commit runs as one `set -e -o pipefail` script; each edit asserts it landed before git is touched;
  the staged set equals the commit's own paths; `git diff --cached` is read against the message (CLAUDE.md,
  2026-11-05).
- Real exit codes only: a test or check whose exit code is hidden counts as not run (CLAUDE.md, 2026-10-30).
- Each fix gets a patch-ledger entry and a deviations row; every commit is pushed to main and the push is checked
  for objects transferred.
- A file holding several fixes is committed fix by fix (the earlier fix's hunks alone first), never as a mixed commit.

## 7. Pre-run check before any paid call

- Before a paid run: orch/prerun_check.py (the full suite, every rehearsal test in its own process, the replay gate
  over the recorded runs), every exit code 0, under 15 minutes wall (P138). A paid run refuses without a passing
  replay-gate record for the current code (P134).
- The room rule before each run: the day's ledger + likely <= the day's room, and the line's remainder >= the run cap.
- A resume never crosses a change to the harness files (code_hash.HARNESS and the orchestrator's import closure):
  a run checkpointed before such a change starts fresh (P146, P157).

## 8. Standing constraints

- Never `--no-verify`, `--waive` or `WHU_SPEND_OVERRIDE`.
- Nothing in Fred's name: no attestation, signature or verdict written for him; an approval he gave is recorded as
  the advisor's relay (P108, P148, P166; CLAUDE.md, signers rule).
- No git writes over the device bridge; held documents and publisher text go to ~/Projects/whu-study-private/
  only, never the repository (audit run folders are not committed).
- Never print keys; never send the user's email or personal details to an outside service.
- No Google call without the paid-tier preflight.

## 9. When to stop and report

Work proceeds under these rules without asking. It stops and reports ONLY for:

- (a) a change to what counts as a reliable page: a check's meaning or threshold, or a new kind of page content;
- (b) an irreversible step;
- (c) spend beyond the development budget.

Every new defect found by a paid run becomes a $0 check across all recorded case folders before the next paid run.
Reports come at milestones only: Ready reached, a fork under this section, or the budget under $8. Each report says
what happened, the numbers and the commits; no progress notes.
