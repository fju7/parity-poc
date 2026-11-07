# WHU orchestrator: design (written and committed before its code)

Session LT, 2026-11-06. Advisor's ruling after the lean four-question test closed (study/whu-reliability/next_phase/
deviations.md, row "the lean four-question test is CLOSED as reported"). **Build only: $0 in model calls** until the
advisor rules on a paid run. Four items:

1. a code-driven orchestrator that replaces the drafting agent;
2. a cross-company overstatement check in WHU's own sentence gate (gemini-4-argon);
3. the whole post-test list folded in;
4. an offline replay on the three scored lean pages' stored records, and a likely and worst per-question cost with no
   drafting agent.

Everything here is lean WHU (`WHU_LEAN=1`); the orchestrator sets the switch itself and refuses to run without it.

---------------------------------------------------------------------------------------------------------------------

## 1. Why: what the drafting agent did

In the lean test a drafting agent ran each issue from a brief (`lean_briefs.md`). On several runs it departed from
the brief to clear a check (advisor's process finding E, deviations row "rulings on the four open items (A-E)"):

| E | Departure | Where |
|---|---|---|
| 1 | deleted a "not read" record | Q1-01 (812c50a), Q1-03 (before 8762d4c) |
| 2 | bound a finding instead of having it ruled | Q1-03b step 9 (03098d8) |
| 3 | applied a redaction by hand | Q1-02r 4d/4e (f41a303) |
| 4 | ran a stage twice in parallel | Q1-04 3d (82f1432) |
| 5 | switched to another edition of a source | Q1-04 (a049fb9) |
| 6 | chose a source form that skipped a check | Q1-03b (196affa "record", 2e1b243 "page"), Q1-04c (S003 "page", 2bd2b56) |
| 7 | edited a source-list line by hand after the draft, with no log | Q1-02b (found by the offline replay; added by the advisor's ruling of 2026-11-07) |
| 8 | put the audit's first-read proposed wording on the page, which no accepted ruling chose | Q1-03b, two sentences (replay; ruling 2026-11-07) |
| 9 | removed a sentence with no record | Q1-03b, after an omission ADD (replay; ruling 2026-11-07) |

Also recorded, and in scope: premise rows filled after a source was opened (C); a hand-set browser user agent (A);
a guessed clock reading corrected later (Q1-04c). Rules that live only in an agent's instructions were broken
whenever breaking them cleared a check. **The design rule: every rule is enforced by code at the step that owns it.
Nothing depends on a model choosing to follow an instruction.**

## 2. The orchestrator

`backend/scripts/whatholdsup/orchestrator.py` (CLI) and `backend/scripts/whatholdsup/orch/` (the step table, the
guard, the chain, the applier, the model steps). One command runs one issue end to end:

    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py run <slug> --mode paid|trial
    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py replay <slug>
    WHU_LEAN=1 py backend/scripts/whatholdsup/orchestrator.py status <slug>

There is no other way to advance an orchestrated issue: no step can be run alone, skipped, re-ordered or repeated
outside the table's own repeat rule.

### 2.1 The step table

`orch/steps.py` holds `STEPS`, a tuple fixed in code. Each `Step` declares:

- `name` and `kind` (`code` or `model`);
- `owns`: the record paths (relative to the case folder, glob patterns allowed) only this step may create or change;
- `models`: the model ids it may call (empty for a code step) and the ledger `role`s those calls carry;
- `max_calls` and `cap_usd`: hard limits enforced by the guard (2.3);
- `run(ctx)`: the code. A model step builds its prompt from declared inputs only, receives a reply through the
  gateway, validates it against a schema, and writes records itself. **A model never writes a file, never runs a
  command, never chooses which step comes next.**

The order (each row a step; "existing" means an existing stage module, called in-process or as a child with fixed
arguments the step builds; nothing is typed by an agent):

| # | step | kind | what it does | owns |
|---|---|---|---|---|
| 0 | `provenance` | code | harness-state manifest (2.6); refuses a dirty tree under backend/scripts or docs | `orchestrator/manifest.json` |
| 1 | `premise` | model | belief, kill condition, scope, evidence standard from issue.json's question only; written through `premise.py`; **all four rows are written here, before any source exists** (C) | `premise.json` |
| 2 | `discover` | model (web search) | proposes sources as {title, first author, year, container, type}; code resolves each through a registry (Crossref, Europe PMC); an unresolved proposal is recorded, never guessed into an identifier; publisher terms enforced by code (domain list, Europe PMC CC check) | `sources.json` (once; frozen after this step) |
| 3 | `acquire` | code | `acquire_sources`, `source_store status`, `errata`, `sweep_sources resolve --write`, `sweep_registry`, `canary` | `sources.json` (`access`, fetch fields only), held texts |
| 4 | `draft` | model | writes the page as JSON sentences, each naming the passage ids (from `passage_index`) it rests on; code renders the HTML, pastes `lean_sentences render` and `coverage_check render` | `draft/<slug>.html` |
| 5 | `bind` | code | `bindings scan`; each sentence bound to the exact passage span it named (code locates it; a sentence whose passage does not hold it is unbound and leaves); `bibbind` proposals accepted by code; `sources_shown`; `lint_claims`; quotations located by code | `bindings.json`, `quotations.json`, `attributions.json` |
| 6 | `coverage` | model | for each coverage unit not used, a fixed-schema decision {used, out_of_scope, not_material} with a ≤200-char reason; code writes `declare` with `--by` = the model id | `coverage.json` |
| 7 | `judgements` | existing + model | `ruling.py judgements`; each relevant judgement is stated (a model step returns one sentence per judgement and its anchor) or declared; code inserts and binds | `judgements.json`, page |
| 8 | `commit_3b` | code | commits the first full draft (the changecheck baseline) | git |
| 9 | `gate` | existing | `factcheck_draft --dry-run`, then the real gate with `--report`; at most three gate runs per issue, counted by code | `draft/<slug>.html.gate.json*` |
| 10 | `advocate` | existing | `source_advocate run`, `ruling.py advocate`; apply (2.4); `applied_check`, `--dangling`, `ruling.py dangling` | `advocate/`, `rulings/` |
| 11 | `omissions` | existing | `ruling.py omissions`; ADDs inserted by code after the named sentence, bound `omission_add`; Not added lines by code (rules 3a and the over-budget line); redaction only by `omissions.record` | `omissions.json`, page |
| 12 | `findings` | existing | `findings --scan`, `ruling.py gate`; rule 3b by `lean_editions` (never a new edition); apply | `gate-findings.json`, `rulings/` |
| 13 | `conclusions` | existing | `conclusion_judge`, `ruling.py conclusions`; apply | `conclusion-review.json` |
| 14 | `audit` | existing | `audit_stage run --cap`, `consistency audit`; amends and cuts applied by code; re-audit until "audit complete" or 3 rounds | `audit/` |
| 15 | `overstatement` | model (Google) | §3 | `rulings/overstatement.jsonl`, page |
| 16 | `final_gate` | existing | narrow gate `--changed-since`, then step 12's code on its findings | gate report runs |
| 17 | `commit_8` | code | commit | git |
| 18 | `changecheck` | existing | `changecheck --before <3b>`, `ruling.py changecheck`; apply; `changecheck_coverage --first <3b>` | `change-reviews.json` |
| 19 | `preflight` | code | `publish.py check`; prints `Ready.` or the STOP rows. **A STOP is the run's result.** Steps 12-18 repeat, in order, when a step after 11 changed the page, at most twice in all (code counter); then the result stands | — |
| 20 | `archive` | code | private archive + `private_manifest.txt`; commit | `private_manifest.txt` |

(Row 6's decisions go through `coverage_check.declare` exactly as now, into `coverage.json`.)

Steps the brief gave to a person ("OPERATOR STEPS", a source a script cannot fetch, a HUMAN_READ_REQUIRED sentence,
a sign-off) end the run Not Ready with the reason recorded (as the lean test did). The orchestrator never writes
`human_reads.jsonl`, `person_decisions.md`, `protected_signoffs.json` or a signed field naming a person: no step owns
them, so the chain (2.5) stops any write to them.

### 2.2 Applying rulings: code, word for word (`orch/apply.py`)

The drafter applied rulings by hand, and that is where E2 and E3 happened. The applier takes the ruling logs the
stages already write (`rulings/rulings.jsonl`, audit cuts and amends, omission ADDs, fail-safe removals) and edits
the page itself: a replacement swaps the ruled-on sentence for the ruling's text; a cut or a fail-safe removal
deletes the sentence; an ADD is inserted directly after its named sentence. Then `applied_check` and `--dangling`
run, and a mismatch is a STOP, never an edit by anyone else. Bindings for changed sentences are recomputed by step
5's code. **No step may create a binding row for a sentence a finding names unless a ruling for that finding
exists** (E2).

### 2.3 The guard: models only inside defined steps (`spend_ledger.orch_guard`)

Every paid model call in WHU already passes one of three places before money is spent: `spend_ledger`'s metered
client (`_MeteredMessages.create`: the audit and every stage built on it), `factcheck_draft.call` (the gate, the
advocate, rulings), and, new, the Google gateway of §3. Each calls `spend_ledger.orch_guard(model, script, role)`
before the call. The guard:

- **on an orchestrated issue** (issue.json `"orchestrated": true`), refuses any call unless the environment carries
  the token the running orchestrator wrote to the issue's lock file, and the current step (`WHU_ORCH_STEP`) declares
  that model and role. So a stage run by hand on an orchestrated issue cannot spend (no ad-hoc commands);
- in `trial` and `replay` modes (`WHU_ORCH_MODE`), refuses every paid call (post-test item 2);
- counts calls and spend per step against `max_calls` and `cap_usd`;
- off an orchestrated issue, does nothing: every stage runs exactly as before.

A test walks the AST of `backend/scripts/whatholdsup/` and `backend/scripts/signal/factcheck_draft.py` and fails if
any `messages.create`, `messages.stream` or `generate_content` call site is not dominated by `orch_guard` in the same
function, or by the metered client.

### 2.4 One step at a time

The orchestrator holds an exclusive `fcntl` lock on `backend/data/whatholdsup/orchestrator.lock` for the whole run,
and runs steps strictly in sequence in one process; a child stage is waited for before the next starts. A second
orchestrator on any issue is refused while the lock is held, and the guard refuses a call from a process whose token
is not the lock's (E4).

### 2.5 Record ownership: the chain (`orch/chain.py`)

Before and after each step the orchestrator hashes every file in the case folder (and the issue's library record).
After the step, any created, changed or deleted path not in the step's `owns` is a **STOP: "record changed outside
the step that owns it"**, and the run ends. The hashes are appended to `orchestrator/chain.jsonl`. `publish.py check`
gains a row for orchestrated issues, **"records match the orchestrator's chain"**: every record's current hash must
equal the last hash the chain wrote for it. So a record edited between runs, or after the run, stops the page.

Consequences, by construction:

- `sources.json`'s source list (ids, URLs, types, editions) is owned by `discover` alone and is frozen after it: no
  later step can add a source, switch an edition or rebind to one (E5). A newer edition is settled by rule 3b's code.
- the read record (`access.sections`, `access.not_read`) is written by code from what the checking stages received
  (fix 6), owned by `acquire` (not_read) and `preflight`'s builder; no model step owns it (E1).
- `omissions.json` is written only by `omissions.record` inside step 11, which redacts across every held source
  (fix 2); no step can hand-redact (E3).
- a source's **form is derived by code** from its type (`source_store.form_of`, `TYPES`); `discover`'s schema has no
  `form` field and the type comes from the closed `TYPES` list, so a form that skips a check cannot be chosen (E6).
  The new **"assessment summary"** form (§4, item 5) gives an assessment report's summary its own test instead of
  "page".

### 2.6 Harness-state provenance (post-test item 3)

`orchestrator/manifest.json`, written by step 0 and re-checked by step 19: the freeze commit; sha256 of CLAUDE.md,
`docs/whatholdsup-process.md`, this file, every `.py` under `backend/scripts/whatholdsup/` and `factcheck_draft.py`;
the model id of every step (`lean.STAGE_MODELS` plus the orchestrator's own); each external tool's settings (the
fetch user agent, web-search max uses, passage retrieval k and threshold, caps); the clock read from the system at
start (never estimated). A changed hash at step 19 is a STOP.

### 2.7 What E becomes (each with a test)

| E | Impossible because | Test (`tests/test_whu_orchestrator.py`) |
|---|---|---|
| 1 delete a not-read record | the read record is code-built; a write to it from a step that does not own it stops the chain; the preflight row "records match the chain" | `test_e1_not_read_edit_outside_owner_stops` |
| 2 bind a finding | the applier and binder refuse a binding for a finding with no ruling; only `findings`/`changecheck` rule | `test_e2_binding_without_ruling_refused` |
| 3 hand redaction | `omissions.json` owned by step 11 only; redaction only in `omissions.record` | `test_e3_omissions_edit_outside_step_stops` |
| 4 parallel stage | one process, one lock; the guard refuses a foreign token | `test_e4_second_orchestrator_refused`, `test_e4_guard_refuses_foreign_token` |
| 5 switch edition | source list frozen after `discover`; chain stops any later change | `test_e5_source_list_frozen_after_discover` |
| 6 form choice | no `form` in the schema; form derived from type | `test_e6_form_derived_not_chosen` |
| A user agent | one constant, generic, no browser string | `test_fetch_user_agent_is_generic` |
| C premise order | `premise` runs before `discover`; premise.json frozen after | `test_premise_before_sources_and_frozen` |
| ad hoc commands | guard on orchestrated issues | `test_guard_refuses_call_outside_orchestrator` |

## 3. The overstatement check (item 2): `orch/overstatement.py`

**What it asks.** For each page sentence bound to a passage (a `bindings.json` row with a held span; protected
sentences are bound to no passage and are not sent), one call to **gemini-4-argon** with **only** the sentence and
its passage (the exact bound span, widened to whole sentences, at most 2,400 characters). No question, no page, no
source title, no other sentence. The prompt (fixed in code, its sha256 recorded with every reply):

    You compare one sentence with the passage it cites. Answer whether the SENTENCE overstates the PASSAGE:
    states more than the passage says, generalises beyond what the passage covers, or states something more
    certainly than the passage does. Reply with JSON only:
    {"overstates": "yes" or "no", "how": "more" | "generalises" | "more_certain" | "none", "why": "<at most 30 words>"}

    PASSAGE:
    <passage>

    SENTENCE:
    <sentence>

**What a reply does.** `"yes"` makes the sentence leave the page under the lean fail-safe
(`lean_failsafe.record("overstatement", ...)`, outcome "removed: unresolved finding"); the applier deletes it. On a
required line (a readers'-list line, `is_required_line`) the outcome is the fail-safe's STOP: the line stays and the
page is Not Ready. A "yes" is **recorded, never dismissed**: no step rules on it, rewrites the sentence or re-asks.
A reply that is not valid JSON, or a refusal, is asked once more; a second bad reply is **treated as "yes"**
(a finding code cannot verify, as the fail-safe treats relevance). A transport error (no reply) stops the run Not
Ready for that reason; it is not a verdict. A sentence with several bound passages is sent once per passage; "yes"
on any passage removes it.

**Records.** `rulings/overstatement.jsonl`: sentence fingerprint, passage source id, offsets and sha256, prompt sha,
model and `model_version` from the reply, the reply text, verdict, usd. A sentence-and-passage pair already checked
with the same inputs is not sent again (as fix 7).

**Preflight row "overstatement check complete"** (lean only): every bound sentence on the page has a verdict for its
current text and passage; a sentence with a "yes" still on the page, or a missing verdict, is a STOP.

**Paid-tier preflight first.** The Google gateway (`orch/google.py`) is the only way to get a Google client. It runs
`judge_google`'s preflight first (one tiny generate call with no study content; a Free Tier refusal or any error is a
STOP) and never calls `count_tokens` (estimates are local: 3.0 characters a token). Every call passes `orch_guard`,
is metered into the ledger (`spend_ledger.rates("gemini-4-argon")`), and its reply model must start with
`gemini-4-argon`.

**Cost.** Per sentence-passage pair: input ≈ (sentence + passage + prompt) / 3.0 tokens (≈ 1,000), output at most
`MAX_OUT` = 1,024 tokens including thinking. The estimate is printed before the step and checked against its cap.

## 4. The post-test list, folded in (item 3)

| item | where | test |
|---|---|---|
| fixes 1-7, rules 3a/3b, the fail-safe items (§4.6.1) | built in freezes 2-6; the orchestrator runs them in their steps, and the preflight rows already enforce them | existing: `tests/test_whu_lean_post_test_fixes.py` (re-run in the suite) |
| 1 patch ledger (arXiv:2611.04338 §5) | `study/whu-reliability/next_phase/patch_ledger.py`: `patches.jsonl`, one entry per deviations row from this phase on, with fixed fields {trigger, timing relative to data, components affected, data exposure, decision-rule change yes/no, non-impact check}; a non-impact check is a committed script with its expected output sha256; `patch_ledger.py verify` re-runs every check; a defect in a check is logged as a patch. Rows before this phase are listed as legacy (fields not back-filled) | `test_patch_ledger.py` |
| 2 trial runs make no paid call | `--mode trial`: the guard refuses every paid call; outputs go to a scratch copy that is deleted at the end, never into `issues/` | `test_trial_mode_makes_no_paid_call`, `test_trial_outputs_discarded` |
| 3 harness-state provenance | §2.6 | `test_manifest_records_hashes_models_tools` |
| 4 code-driven orchestrator | §2 | §2.7 |
| 5a honest fetch user agent | `acquire_sources.UA` = `"WHU-fetch/1.0 (automated research client)"`, no browser string, no email; every hand fetch path uses it | `test_fetch_user_agent_is_generic` |
| 5b "assessment summary" form | `source_store.FORMS` gains `"assessment summary"` (type `assessment_summary`: a summary or headline statements of an assessment report); test: at least 2,000 characters held, and the text names its parent report (an "Summary for Policymakers"/"Technical Summary"/"Headline Statements" or the report title in the first 3,000 characters); errata checked as for an article | `test_assessment_summary_form` |
| 6 recency sweep provenance | `factcheck_draft.call` captures, from the response itself, every web-search query (`server_tool_use`) and every result domain (`web_search_tool_result`); `sweep_recency` writes them as `searched` and `queries` on every study and on the sweep; `lean_editions.searched_of` reads them. Code-captured, not model-claimed | `test_recency_records_registries_and_queries` |
| 7 `lint_claims.unknowability` grammar | the pattern covers any subject + could not / cannot / were unable to / failed to + establish / determine / verify / confirm, and passives (cannot / could not / can't be + participle; "it is not possible to …"); rule 3b's code-written line now carries its registries (fix 1) and is exempt only when it names them | `test_unknowability_every_form` |

Briefs are retired: the premise-row order and the user-agent rule are code (§2.1, item 5a).

## 5. Offline replay and cost (item 4)

**Replay** (`orchestrator.py replay <slug>`, $0) on whu-lean-q1-01c, -02b and -03b. It copies the case folder to a
scratch directory (never writing `issues/`), sets `WHU_ORCH_MODE=replay` (the guard refuses every paid call), and runs
the code steps on the stored records. The agent-written records (premise, sources list, page, declarations) are
taken as the inputs they were; they cannot be replayed, because no orchestrator step produced them, and the report
says so. What is compared, stored against reproduced, by sha256 of normalised output:

- `publish.py check` (every row and the verdict);
- `lean_sentences render` and `coverage_check render`;
- `bindings check` and `status`;
- `lean_failsafe report`;
- `applied_check` and `--dangling`;
- the applier: re-applying every ruling in the logs to the 3b page reproduces the committed page's sentence set
  (where a ruling log fully determines it).

Expected: identical. A difference is reported as it is, not fixed in the replay. Results:
`study/whu-reliability/next_phase/results/orchestrator/replay.json` (counts and hashes only).

**Cost with no drafting agent** (`orch/estimate.py`): per question, likely and worst =
pipeline (the run's ledger stages, minus calls only a drafter made: repeated dry runs, duplicate stages) +
the new model steps (premise, discover, draft, coverage decisions, judgement sentences: tokens measured from the
stored records, priced at `spend_ledger.rates` for each step's model) + the overstatement check (bound
sentence-passage pairs on the stored page × §3's per-call figure). Likely uses measured output sizes; worst uses
each step's `max_tokens` and cap. Results: `results/orchestrator/cost_estimate.json`.

## 6. What is not in this build

- No paid call of any kind, including the Google preflight; the gateway is built and tested against a stub client.
- No new question is run, and the lean-test records are not changed.
- The seeded-defect test and a new-questions test wait for the advisor's ruling.

## 7. Changes made while building (recorded after §1-6 were committed)

- **Registry resolution is Europe PMC only**, through WHU's own lookup (`orch/resolve.py` on
  `find_access.epmc`/`titles_agree`). The design named Crossref too, via the shared `verify` package; WHU's modules
  may not import it (`tests/verify/test_units.py`, design doc §8 of that package). Crossref is listed under "not
  searched".
- **Trial and replay run in a scratch copy of the repository** (`orch/sandbox.py`): `backend/scripts`, the case
  folders, the issue's library documents, the study folder and the homepage, a read-only local git clone (the
  preflight reads earlier page versions), and an `.env` with no key in it. Every module finds the repository from
  its own path, so nothing reaches the real records or ledger. Outputs are discarded when the copy is deleted.
- **A Caller needs no key in trial or replay mode** (`audit_stage.Caller`): it refuses every call, so a stage whose
  rulings are all carried (fix 7) finishes at $0 and one that needs a new call is refused, both by construction.
- **Worst cost is the issue's run cap.** Every paid call checks `run_cap_usd` (`spend_ledger.cap_for`); the
  orchestrator refuses an issue without one, at most $10. The step caps sum higher ($28.30) and are per-step limits.
- **A changed sentence's binding, by rule.** A ruling's replacement rests on the passages of the sentence it
  replaced; an omission ADD on its finding's span; a coverage "state" sentence on its unit's span. Nothing else may
  be (re)bound after the draft (E2).
- **The source's form is frozen after `acquire`** with the other frozen fields (E6).
- **The audit step re-audits** until a round changes nothing, at most three rounds, then runs the consistency
  audit; the applier runs `ruling.py dangling` once when an applied ruling left a reference pointing at nothing.
- **Paid mode is refused** unless `WHU_ORCH_PAID_RULED` names the advisor's ruling (this build is $0).

- **E7-E9 (added 2026-11-07, before any paid call).** `orch/accounting.py`, run by `run_step` after every step that owns the page, once the code-written blocks are re-rendered from their generators: every prose sentence is a provenance key written by the code that placed it, or the text of an applied record (`orchestrator/applied.jsonl`); every code-written line is one its generator writes now (the source list from `sources.json`, frozen after `acquire`, so a hand-edited source line is never explained, E7); a first read's `proposed_text` is never applied, only an accepted ruling's `text` (E8); a sentence that leaves the page is an applied record's old sentence, or a code-written line its generator no longer writes (E9). A problem stops the run. Tests: `test_e7_a_hand_edited_source_line_stops`, `test_e8_a_first_read_proposal_is_never_applied_and_a_hand_placed_one_stops`, `test_e9_a_removal_with_no_record_stops_and_a_recorded_one_passes`, `test_e7_e9_run_after_every_page_owning_step`.
- **Sandbox, fresh issue (2026-11-07).** A fresh issue has no library record until `acquire` writes one; the scratch copy no longer requires it (found by the $0 trial-mode pass on WHU-OT1-02, which then stopped at the premise's first model call, refused, as designed).
- **Reply limits, failed-step records, step labels (2026-11-07, after trial 1's first attempt).** The never-run steps' reply limits sit in one table, `orch/steps.py` REPLY_LIMITS, each at least 1.5x the largest matching output in the stored lean records (basis in `study/whu-reliability/next_phase/results/orchestrator/reply_limits.json`); the draft's 30,000 needs an explicit request timeout. A failed step is recorded (reason, cost, commands, replies, a cut-off reply included) before the run stops; every ledger row written in a step names it.
- **Rulings after trial 1's attempt 3 (2026-11-07, recorded before code).** (a) A source that cannot be held is recorded as "not held" and does not stop the run; nothing on the page draws on it, and the page's code-written limits block carries "We found <title> but could not hold it, so nothing on this page draws on it."; orchestrated runs keep no human search list; the run stops Not Ready only if no source is held. (b) `discover`'s type field allows "none of these"; such a source is treated as (a) with "We found <title> but it is not of a type we can check, so nothing on this page draws on it." (an evidence-and-gap-map type is on the post-test list). (c) PMC-hosted articles (pmc.ncbi.nlm.nih.gov, a PMCID) are confirmed as articles through Europe PMC; the agency-site rule excludes PMC. (d) study_log's per-step cost is the sum of the ledger rows labelled with that step.
- **Corrections and retractions (ruling 2026-11-07, recorded before code).** At `acquire`, every source's bibliographic record is read for a retraction (Europe PMC pubType / commentCorrection, Crossref update metadata); a retracted source is treated as not held, with "We found <title> but it has been retracted, so nothing on this page draws on it." A correction to a source not held needs no action (the errata check passes it). A correction to a held source is fetched at `acquire` as a linked record on that source (not a new source); a code step after the bound sentences exist, and again in the repeat group, removes under the fail-safe ("removed: affected by correction <notice id>") every page sentence whose bound passage shares a figure or a run of 5+ consecutive content words with the notice, unless the sentence re-binds against the notice's corrected text; a notice that cannot be held makes the source not held ("…has a published correction we could not hold, so nothing on this page draws on it.").
