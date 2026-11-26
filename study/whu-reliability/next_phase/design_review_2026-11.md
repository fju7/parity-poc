# Orchestrator trial 1 — design review after the stopping rule (2026-11-26)

Asked for by the advisor's ruling after attempt 26 (attempt 3 of 3, not Ready). Everything here was done at $0, from the
committed records and the code at 6bbfd2b. Nothing is fixed here. No paid call is made until this review is ruled on.
The trial line has about $9.13 left, untouched.

**Sources used, and the provenance of every count below**

- **LEDGER**: `backend/data/spend/ledger.jsonl` at 6bbfd2b, filtered to rows whose `issue` starts `whu-lean-orch-t1-`.
  That is 1,321 rows of 12,767. Its total, $40.8676, equals the trial line's spend: $39.0208 before attempt 26 plus
  $1.8468 for attempt 26.
- **RUN**: `issues/WHU-OT1-<f>-whu-lean-orch-t1-q1-<f>/orchestrator/run_paid.json` for each folder f. That is 29
  folders. 02d has no run_paid.json: it was lost to the SystemExit that deviations.md line 129 records.
- **PROPOSALS**: each folder's `proposals.json`.
- **DEV**: `study/whu-reliability/next_phase/deviations.md`, cited by line number.
- **CODE**: file:line at 6bbfd2b under `backend/scripts/whatholdsup/` (abbreviated W/) and
  `backend/scripts/signal/factcheck_draft.py` (FC).

**Attempt numbers and folders (DEV 123-245)**

- Attempts 1-23 are folders 02 and 02b-02w, one each.
- Attempt 24 is 02x (an outage, resumed), then 02y, 02z and 02za (fresh runs). It ended as "cap spent", which made it
  attempt 1 of 3 toward the stopping rule.
- Attempt 25 is 02zb (a $0 stop, not counted) and then 02zc (attempt 2 of 3).
- Attempt 26 is 02zd (attempt 3 of 3).

All 30 folders ask the same question (Q1-02).

## 1. Single points of failure

Two facts govern every step:

- **Any exception ends the run Not Ready.** `orchestrator.run` catches every exception from a step and records
  "Not Ready: …" (W/orchestrator.py:1707-1712). `run_cmds` stops on any stage exit code not listed in `EXITS`
  (W/orchestrator.py:146-149, W/orch/steps.py:150-156).
- **A truncated reply surfaces differently by caller:**
  - `audit_stage.Caller` raises ReplyCutOff (W/audit_stage.py:1024, 1056-1059);
  - `factcheck_draft.call` returns None (FC 969-993);
  - `model_steps.ask_json` re-asks only a *malformed* reply (W/orch/model_steps.py:60-77); a ReplyCutOff passes
    straight through it.

**How "measured" was read.** Measured = LEDGER `output` tokens, grouped by `step` and `role`. The p95 is the
nearest-rank value.

- Caller rows are all tagged role "audit" (spend_ledger records the script, not the call site). So where one step
  makes calls with two different limits, the rows cannot be split, and the table says so.
- Extended thinking: no call site passes a `thinking` parameter. Whether Opus or Sonnet 5.5 think by default, and
  whether that counts against max_tokens, is not established from the repo. The Google gateway adds thinking to
  output (W/orch/google.py:150-157).

| Step (call site) | Model | Output limit | Measured n / max / p95 | Truncated reply | Invalid reply | If it finally fails |
|---|---|---|---|---|---|---|
| premise (model_steps:114) | opus-5-5 | 4000 (steps.py:42) | 28 / 1941 / 1823 | ReplyCutOff, no re-ask | 1 re-ask, then Unusable | run ends |
| discover (orchestrator:616) | sonnet-4-6 + search | 4000 (steps.py:43) | 28 / 2291 / 2208 | None → RunStop "discover: no reply" (orchestrator:607) | 1 re-ask | run ends |
| draft (orchestrator:886) | opus-5-5 | 30000 (steps.py:44) | 21 / 4389 / 4292 | ReplyCutOff, no re-ask | 1 re-ask | run ends |
| coverage (model_steps:291) | sonnet-5-5 | **600** (steps.py:45) | 310 / **566** / 429 | ReplyCutOff, not caught | Unusable → unit kept in scope | run ends on truncation |
| judgements: relevance rulings (ruling.py) + sentence (model_steps:361) | sonnet-5-5, escalates to opus-5-5 | 4000 (ruling.py:106) / **500** (steps.py:46) | 413 / 622 / 404 (both call sites pooled) | rulings: 1 retry at the same limit; sentence: ReplyCutOff | rulings: escalate; sentence: 1 re-ask, Unusable not caught | run ends |
| belief (premise_reading:246, 260) | sonnet-4-6 + search | **1500 hard-coded** | 5 / **2051** / 2051 | None → RunStop "belief: no reply" (orchestrator:1503) | round 1: 1 re-ask, then Unusable (not caught); round 2: Unusable → None | run ends |
| premise_reading (premise_reading:355) | opus-5-5 | **1500 hard-coded** | 4 / 1500 (cut) / -; before attempt 26: 1135, 1225, 1119 | ReplyCutOff, no re-ask | 1 re-ask | **run ended (attempt 26)** |
| gate / final gate (FC roles extract, recency, inference, coverage) | sonnet-4-6 + search | 64000 (FC 114, read_budget 1573) | recency 17 / 3434 / 3323 | None, no re-ask → exit 2 | strict: 1 re-ask | run ends |
| advocate briefs (source_advocate, FC) | sonnet-5-5 | 64000 | 18 / 8691 / 8289 (all advocate:Sxxx) | None → brief failed → non-zero exit | 1 re-ask | run ends |
| advocate requote / omission re-ask (FC) | sonnet-5-5 / sonnet-4-6 | 64000 | 64 / 596 / 455 | None → treated as {} | 1 re-ask | carries on |
| ruling.py advocate / findings / conclusions / changecheck / dangling / corrections | opus-5-5 | 4000 (ruling.py:106) | advocate 22 / 747 / 670; changecheck 2 / 250 | 1 retry at the same limit (ATTEMPTS = 2, ruling.py:109), then exit 4 → command run once more | RulingError → exit 1 | run ends |
| ruling.py omissions | opus-5-5 | 4000 | 55 / 967 / 906 | as above | RulingError → sent to a person | item to a person |
| conclusion_judge (conclusion_judge:352) | sonnet-4-6 | 600 | no rows tagged for this step | None → UNPARSEABLE, counted as flagged | 1 re-ask | flagged; what follows downstream is not established |
| changecheck review (FC) | sonnet-4-6 | 64000 | 5 / 451 / 451 | None → an UNRUN finding, exit 0 | 1 re-ask | to ruling.py changecheck; outcome not established |
| audit (audit_stage; reader + rule) | sonnet-5-5 reader, opus-5-5 rule/escalation | reader 12000 (audit_stage:105), **rule 1500** (:106) | 125 / 5813 / 4247 (reader and rule pooled) | ReplyCutOff → AuditFailure → exit 2 | 1 re-ask (parse_reply) | run ends |
| consistency audit (consistency.py) | opus-5-5 | audit kind 1500, ruling kinds 4000 | not separable from the audit rows | audit kind: ReplyCutOff not caught → run ends; ruling kinds: recorded, no stop | recorded "not usable" | audit kind: run ends |
| overstatement (orch/google.py) | gemini-4-argon | 2800 (google.py:44), includes thinking | 194 / 63 / 56 | **never detected**: `finish` is recorded but MAX_TOKENS is not checked | 1 re-ask at the same limit | verdict "yes" → sentence removed (fail-safe) |

**Steps whose limit is under 2× the measured max**

- **coverage:** 600 against 566, which is 1.06×.
- **premise_reading:** 1500 against 1225 before attempt 26, which is 1.22×. Attempt 26's reply then reached the limit.
- **belief:** 1500 against 2051, which is 0.73×. The recorded 2051 came from a reply that was *not* cut off (02zd
  round 2). Why a web-search call can report more output than max_tokens is not established; the ledger's output
  count may sum the search loop's turns.
- **discover:** 4000 against 2291, which is 1.75×.
- **Not settled from the ledger:** judgement_sentence (500) and the audit rule calls (1500). Their rows are pooled
  with calls whose limits are 4000 and 12000. The pooled maxima, 622 and 5813, exceed both small limits, so neither
  limit can be shown to be safe.

Premise is 2.06×, just over the line. Premise already failed once at its old 1500 limit (attempt 1, DEV 122).

**Steps where a truncated reply ends the run with no re-ask.** Every step except the ruling.py modes:

- premise, discover, draft, coverage, judgement_sentence;
- belief (both rounds), premise_reading;
- every audit call (reader and rule);
- every factcheck_draft role (gate, final gate, advocate briefs, changecheck);
- the consistency audit's audit kind.

ruling.py re-asks once at the *same* limit. Nowhere is a truncated reply re-asked with a higher limit. On the Google
call, truncation is not detected at all.

**Proposed policy (one rule, every call site)**

1. **One table.** Every model call reads its output limit from one table, keyed by call site, with no limit written
   in at the call site. That table is `steps.REPLY_LIMITS`, extended to cover every row above; the two hard-coded
   1500s, RULE_MAX_OUT, ruling.MAX_OUT and conclusion_judge's 600 move into it.
2. **Distinct ledger roles.** Every call records its call site as the ledger `role`, so lengths are measurable per
   call site, never pooled.
3. **Limits set from measurements.** limit = max(floor, 2 × measured max) over all orchestrated runs, rounded up to
   100. A $0 test recomputes this from LEDGER and fails when any limit falls below 2× its measured max. The test runs
   with the suite, so every paid run that produces a new longest reply is caught before the next run.
4. **Truncation handled the same way everywhere.** A truncated reply is detected everywhere (Anthropic stop_reason
   `max_tokens`; Google finish_reason MAX_TOKENS) and re-asked once with the limit doubled. The re-ask is bounded by
   the step's call cap and the provider's maximum, is checked against the per-call and run caps first, and is
   recorded in the run record next to `malformed_replies`.
5. **A second truncation takes the step's own fail-safe.** That fail-safe is what the step already does with an
   unusable reply: coverage keeps the unit in scope, overstatement removes the sentence, the others stop the run.

This one rule would have carried attempts 1 (premise, 1500) and 26 (premise_reading, 1500) past the stop for at most
one extra call each. Attempt 26's run cap had $8.15 left.

## 2. Rehearsal gap

**Why the offline rehearsals reach Ready**

- **The replies are synthetic.** They are built to each prompt's schema, short, and always `stop_reason = end_turn`
  (W/orch/rehearsal.py:229; W/orch/rehearsal_replies.py:1-4: "a rehearsal proves the plumbing, not the page"). A stub
  can never be cut off, never be long, and never say something a check refuses on its substance.
- **The sources are not the run's.** Every rehearsal is built on base slug `whu-lean-orch-t1-q1-02w` (the scratchpad
  `reh.sh` used for every rehearsal since attempt 24). Its HTTP is replayed from a 4.4 MB record-then-replay cache
  (~/Projects/whu-study-private/rehearsal_http). It never sees the next run's proposals, documents or registry answers.
- **The costs are synthetic,** so no stop that depends on a cap or a measured estimate can appear.
- **The checks that judge substance are fed stubs built to pass them.** Belief outlets "verified", rulings placed,
  quotations matched.

What the rehearsals do prove: plumbing, fault and shape handling. Each of the four rehearsal plans in item 6 of
the P125-P127 verification did what it should.

**Each real stop since attempt 24, and whether a rehearsal could have caught it**

| Run | Stop (RUN result, DEV row) | Could the existing rehearsal catch it? | Would a replay rehearsal? |
|---|---|---|---|
| 02x | registry unavailable at discover (outage) | It exercises the stop (the europepmc_search_down plan); an outage cannot be prevented | n/a |
| 02y | source-list standing check: entry [6] has three years (Crossref organisational tenure in the author string; DEV 211) | No: needs that source's real Crossref record | Only after 02y, as a regression test on its record |
| 02z | ruling could not be placed: "not found on the page" (DEV 216) | No: stub rulings quote the page exactly | Yes for 02z's own rulings, replayed against later code; not before 02z |
| 02za | cap spent before the audit (DEV 223-226) | No: costs are synthetic | Yes: replaying real token counts gives real spend and would have shown the audit estimate exceeding the cap |
| 02zb | $0 stop: run cap above $10 (DEV 229) | No: the rehearsal copies issue.json from the base, not the real folder | A $0 `orchestrator.py run --dry` on the real folder would; replay is not needed |
| 02zc | preflight STOP rows (DEV 234): recency line for an unheld source; U+2010 vs ASCII hyphen; a readers'-list line on unreceived text; belief 0 of 3 outlets | No: the base's documents and stub outlets never produce these | The hyphen defect: possibly, from 02za's held S001, which prints U+2010 (not established that 02za quoted it). The recency line: yes from 02zc on. Belief: no (needs live pages). |
| 02zd | premise_reading cut off at 1500 | No: stubs are never cut off | No: the earlier replies were 1119-1225 tokens. Only the limit policy in §1 would have caught it. |

**Proposed replay rehearsal (built at $0, runs at $0)**

1. **Record from now on.** Every paid call's raw reply text, stop_reason and usage go privately to
   `~/Projects/whu-study-private/replies/<slug>/` (it holds publisher text, so never the repo), keyed by step, role
   and the sha256 of the prompt. Today only parsed forms are kept: proposals.json, page.json, coverage.json,
   judgements.json, rulings/*.jsonl, audit verdicts.jsonl and premise_checks.jsonl, plus the ledger's token counts.
2. **Replay 02z, 02za, 02zc and 02zd from what exists.**
   - The held documents come from `~/Projects/whu-study-private/checkpoints/<slug>/*/library` and
     `run_provenance/<slug>` (present for all four).
   - A reply-replay stub returns each recorded parsed reply, re-serialised, together with that call's LEDGER output
     count.
   - **When the recorded count is at or over the current limit, the stub returns `stop_reason = max_tokens`.** That
     ties the replay to item 1's limit policy.
   - Registry answers were not recorded for paid runs, so confirm would re-query (free registries, $0) or be recorded
     from now on.
   - Prompts that changed since the run (code changed) fall back to the synthetic generator. Each such fallback is
     reported by name.
3. **Gate.** Before any paid attempt, the replay of every recorded run must reach the same or a later step than the
   run did, with no new STOP rows.
4. **Cost to build.**
   - $0 in model calls.
   - The work: a reply-store writer in audit_stage.Caller, factcheck_draft.call and orch/google.py; a replay stub
     beside rehearsal_replies.py; a library-root switch; and tests.
   - My estimate is 500-700 lines including tests, one working session. That is an estimate, not a measurement.

Honest limit: a replay finds regressions on inputs already seen. 02zd's cut-off was a new input, which only §1's
measured-limit rule catches. Discovery returns a different source set each run (§3), so a replay can never stand in
for the next real run.

## 3. Source access, 02z-02zd

Counts come from RUN `sources` and PROPOSALS. "Confirmed" means a registry record agreed and the source entered
sources.json. Each refusal is classed by hand from its recorded reason.

| Run | Proposed | Confirmed | Held (full text) | Wall | No permitted copy | Erratum / correction | Not the document | Form rule | Other | Held / confirmed | Held / proposed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 02z | 8 | 6 | 1 | 1 (S002 T&F 403) | 0 | 2 (S003 notice does not name it; S004 notice not held) | 0 | 2 (S005, S006 assessment summary) | 0 | 17% | 13% |
| 02za | 8 | 7 | 3 | 1 | 0 | 2 | 1 (S005 unesdoc, 2,475 bytes, 0 title words) | 0 | 0 | 43% | 38% |
| 02zc | 8 | 7 | 1 | 1 | 0 | 2 | 2 (S006 landing page; S007 unesdoc 2,475 bytes) | 1 (S005) | 0 | 14% | 13% |
| 02zd | 8 | 4 | 1 | 1 | 0 | 1 | 0 | 1 (S004 REA) | 0 | 25% | 13% |
| **Total** | **32** | **24** | **6** | **4** | **0** | **7** | **3** | **4** | **0** | **25%** | **19%** |

- **No permitted copy is 0 as a primary cause.** Every wall row also records "open copy via OpenAlex: no permitted
  open copy listed".
- **S001, the 2025 Campbell review, is the only source held in every run.** 02za also held the UNESCO Guide and the
  review's own protocol.
- **The same three sources fail in every run they appear in:**
  - the T&F review is walled, 4 of 4 runs;
  - the evidence-and-gap map's erratum is not held, 4 of 4;
  - the Asia-Pacific review's erratum notice does not name it, 3 of 3.

**Discovery stability.** The 32 proposals cluster into 14 distinct works. Titles were matched by word-set Jaccard
≥ 0.6, with two corrections made by reading them: "Inclusion and education (GEM Report 2020)" was merged with the
GEM 2020 report, and the 02za review *protocol* was kept apart from the review.

- In all 4 runs: 3 works (the review, the T&F review, the gap map).
- In 3 runs: 4 works (Asia-Pacific teacher review, the REA, "Inclusive Education and Children with Disabilities",
  GEM 2020).
- In 2 runs: 1 work (UNESCO policy guidelines).
- In 1 run: 6 works.

| Pairwise overlap of proposed works (Jaccard) | Score |
|---|---|
| 02z–02za | 0.60 |
| 02z–02zc | 0.60 |
| 02z–02zd | 0.60 |
| 02za–02zc | 0.45 |
| 02za–02zd | 0.33 |
| 02zc–02zd | 0.33 |
| **mean** | **0.49** |

Same question, same prompt, same model: about half of each run's proposed set changes between runs. Confirmation
varies more than proposal does: 02zd confirmed 4 of 8, the others 6-7 of 8.

## 4. Early stop on thin sources

**Proposal**

- **The minimum.** Held-source minimum = **2 distinct works held as full text**, counted from `holdings.py`'s record
  (blocked and not-held sources excluded), with at least one of them a review or synthesis.
- **Where it is checked.** A $0 code check straight after `acquire`, before `draft`, the first model call after
  acquire.
- **The outcome.** Below the minimum, the run ends with the honest outcome "Insufficient sources: N of M confirmed
  sources held (minimum 2); not drafted". The run record gets each refusal's reason class as in §3. This is a named
  terminal outcome, not "Not Ready", and it does not count as a defect toward any stopping rule.
- **Why 2.** With one held work, every sentence rests on one document. "What holds up" across sources cannot be
  stated, and the preflight's source rows can only fail or pass trivially. The number 2 is a judgement for the
  advisor; the table below also shows 3.

**What each past run would have cost had it stopped there.** Spend through acquire comes from RUN's step `usd`
summed through `acquire`; the run total comes from LEDGER. "Held" is RUN `sources.held` where present, otherwise the
acquire step's recorded outcome. For 02e-02l the acquire outcome predates the holdings record and may count sources
later blocked by corrections.

| Run | Held | Spent through acquire | Actual total | Saved at min 2 |
|---|---|---|---|---|
| 02e | 1 | $0.5282 | $0.9068 | $0.3785 |
| 02f | 1 | $0.3654 | $1.0088 | $0.6433 |
| 02g | 1 | $0.5334 | $1.4187 | $0.8853 |
| 02h | 1 | $0.5232 | $1.8109 | $1.2876 |
| 02i | 1 | $0.5058 | $0.7061 | $0.2003 |
| 02k | 1 | $0.4930 | $0.6374 | $0.1444 |
| 02l | 1 | $0.4959 | $1.3671 | $0.8711 |
| 02r | 1 | $0.4965 | $2.4800 | $1.9835 |
| 02s | 1 | $0.5291 | $2.3479 | $1.8188 |
| 02u | 1 | $0.5003 | $2.3378 | $1.8375 |
| 02w | 1 | $0.5223 | $2.2803 | $1.7580 |
| 02z | 1 | $0.4961 | $3.1040 | $2.6079 |
| 02zc | 1 | $0.3596 | $2.3937 | $2.0341 |
| 02zd | 1 | $0.6492 | $1.8468 | $1.1976 |
| **14 runs** | | | | **$17.6480** |

- **Not stopped at 2:** 02n, 02o and 02v (2 held); 02p, 02q and 02za (3 held); 02m (4); 02t (5); 02y (2).
  02m, 02p and 02t ended at acquire on outages anyway.
- **At a minimum of 3,** 02n, 02o, 02v and 02y would also have stopped, for $22.2868 saved in all.
- **Not in the table:** 02, 02b, 02j, 02x and 02zb ended before acquire. 02c's held count is not recorded. 02d has
  no run record.

Of the $40.8676, **$17.65 (43%) was spent after acquire on runs that held one source.** Every run since 02z on this
question has held one source except 02za.

## 5. Step ordering: refusals that run before a route that might rescue the source

The rule used to judge the order: refuse first when the refusal is about the WORK (wrong work, retracted, licence
bars machine reading). Rescue first when the refusal is about one RETRIEVAL (this copy is a landing page, a summary,
a wall, a fragment).

**What happened to 02zd's S004** (traced in code)

- `acquire_sources.py --landing-pdfs --open-copies` ran (W/orch/steps.py:88) and fetched the gov.uk page
  (71,842 bytes).
- `held_check` (W/source_store.py:894) passed `identifies()` (12 of 12 title words), then `classify()` took the
  assessment-summary form branch (:538), because discover had typed S004 `assessment_summary`.
- `substance_assessment_summary` passed the 2,000-character floor. It returned "undetermined" at :420 because
  `ASSESSMENT_PARENT` (:392: summary for policymakers / technical summary / … / assessment report) matched nothing
  in the first 3,000 characters.
- `acquire_sources.py:409` keeps a page for the landing route only when `kind == "landing"`, so the route at :414
  never ran.
- The open copy step found no DOI recorded (W/open_copy.py:173).

| # | Refusal (file:line) | Rescue it pre-empts (file:line) | Gate on the rescue | Is the refusal about the work or the retrieval? | Correct order |
|---|---|---|---|---|---|
| 1 | assessment-summary form "undetermined" / "stub" (source_store:417-420); page form "shell" (:542-544) | landing-page route (acquire_sources:414) | `kind == "landing"` only (:409); only `substance()` returns it (:500, :511) | retrieval | **rescue first**: any identified-but-not-the-document HTML page should be offered to the landing route. Caveat: the route re-runs the same `held_check` on the PDF (landing_route:361). ASSESSMENT_PARENT does not match "Rapid Evidence Assessment", so the REA's PDF could fail the same rule unless its opening names one of the listed parents. The root problem is the REA being typed as an assessment summary at all. |
| 2 | an abstract counts as held (HELD_STATES includes abstract_held, source_store:851), so the fetch loop breaks (acquire_sources:407) | landing route (:414) and open copies (:427), both gated on `data is None` | the abstract sets `data` | retrieval | **rescue first**: an abstract should not end the search for full text. The orchestrator then marks it `could_not_hold` (orchestrator:779-782), so the rescue is lost silently. |
| 3 | open copy needs a recorded DOI (open_copy:173) | OpenAlex open copies | DOI present | neither (an input gap) | order right; for agency pages with no DOI this route is a no-op, and the landing route must carry them |
| 4 | open copy drops every copy on the source's own host (open_copy:91) | a PDF on the same host as a landing page | host differs | retrieval when the host refused only one page; host-level for a 403 wall | **narrow it**: exclude the host only after a wall, not after a landing/summary refusal |
| 5 | one transient failure (timeout / 5xx / 429) earlier in the loop (acquire_sources:378) | both rescues (:414, :427 require `not unavailable`) | `not unavailable` | neither: the run stops "registry unavailable" anyway (orchestrator:788) | defensible as built |
| 6 | only the first landing page is kept (:409 `landing is None`) | a later, better landing page | first only | retrieval | minor; try each landing page in turn |
| 7 | identity failure (source_store:901, kind None) | landing route | kind | work | refusal first is correct |
| 8 | Europe PMC "not served" / 4xx / outage | NCBI PMC fallback (acquire_sources:361-397) | EPMC fullTextXML URL, orchestrated | retrieval | already rescue first; correct |
| 9 | walls, robots, TDM (open_copy:116-140, :203, :209; landing_route:321-360) | n/a (end that candidate only; the source's own 403 still falls through to both rescues, :372-379) | | permission | correct |
| 10 | submittedVersion (open_copy:88) | n/a (that candidate only) | | policy on the version | correct as ruled |
| 11 | licence decision after the fetch (landing_route:366-369) | n/a | | permission | correct |
| 12 | robots.txt for an added SPM (acquire_sources:342-350) | none | | permission | correct |
| 13 | licence forbids machine reading (acquire_sources:331) | none | | work | correct |
| 14 | retracted / expression of concern (orchestrator:747-752) | none | | work | correct |
| 15 | correction notice not held or not naming the source (orchestrator:761-771) blocks a source whose own full text WAS held | the notice search runs first (orch/corrections.py:265: Europe PMC, PubMed, NCBI PMC) | | **a retrieval of a different document**, treated as about the work | a policy question for the advisor. This rule alone removed 7 of 24 confirmed sources in §3. |

Provenance of this table: a read-only code inventory (a delegated agent's read of the acquire path), with rows 1-2
spot-checked against the source at 6bbfd2b (source_store.py:390-421 and :851, acquire_sources.py:403-430). Rows 3-15
rest on that read and were not independently re-verified line by line. The same applies to §1's table (spot-checked:
orchestrator.py:1707-1712, ruling.py:109, orch/google.py:147-158, orchestrator.py:1500-1505).

## 6. Cost so far (attempts 1-26)

All figures come from LEDGER, by issue. The total is $40.8676 over 30 folders and 1,321 calls.

| Attempt | Folder(s) | $ | Stop cause |
|---|---|---|---|
| 1 | 02 | 0.0314 | single reply: premise cut off at 1500 |
| 2 | 02b | 0.0344 | single reply: field 'measured' over 400 characters |
| 3 | 02c | 0.5240 | plumbing: acquire exit 1 (an unstored source) treated as a stop |
| 4 | 02d | 0.6539 | plumbing: coverage declaration needed an `element` the schema never asked for |
| 5 | 02e | 0.9068 | plumbing: git commit failed in the run |
| 6 | 02f | 1.0088 | plumbing: the gate's normal exit 1 treated as a stop |
| 7 | 02g | 1.4187 | plumbing: undeclared model refused by orch_guard |
| 8 | 02h | 1.8109 | plumbing: record changed outside its owning step |
| 9 | 02i | 0.7061 | single reply: two JSON objects |
| 10 | 02j | 0.4921 | plumbing: AttributeError ('dict'.strip) |
| 11 | 02k | 0.6374 | plumbing: FileNotFoundError |
| 12 | 02l | 1.3671 | single reply: web-search narration made the recency reply malformed |
| 13 | 02m | 0.4967 | outage: Europe PMC |
| 14 | 02n | 1.4835 | single reply: prose before the fenced JSON (recency) |
| 15 | 02o | 2.4668 | defect: a ruling could not be placed on the page |
| 16 | 02p | 0.4875 | outage: Europe PMC |
| 17 | 02q | 2.5328 | single reply: audit reply "Extra data" |
| 18 | 02r | 2.4800 | plumbing: consistency audit ran on a round with no rulings |
| 19 | 02s | 2.3479 | plumbing: orch/google.py shadowed the google package |
| 20 | 02t | 0.4826 | outage: Europe PMC |
| 21 | 02u | 2.3378 | defect: references still dangling after the ruling |
| 22 | 02v | 2.0505 | outage: gemini-4-argon 503 |
| 23 | 02w | 2.2803 | plumbing: the harness check compared HEAD (plus six STOP rows) |
| 24 | 02x, 02y, 02z, 02za | 0.9728 + 0.6360 + 3.1040 + 2.8764 = 7.5893 | outage (02x), defect (02y source-list years), defect (02z ruling placement), budget (02za cap spent) |
| 25 | 02zb, 02zc | 0.0000 + 2.3937 | plumbing (02zb, cap config, not counted), defect (02zc preflight STOP rows) |
| 26 | 02zd | 1.8468 | single reply: premise_reading cut off at 1500 |

**By stop cause** (each folder counted once, by its own stop)

| Cause | Folders | $ | Share |
|---|---|---|---|
| plumbing | 12 (02c-02h, 02j, 02k, 02r, 02s, 02w, 02zb) | 14.5607 | 36% |
| defect | 5 (02o, 02u, 02y, 02z, 02zc) | 10.9384 | 27% |
| single-reply failure | 7 (02, 02b, 02i, 02l, 02n, 02q, 02zd) | 8.0020 | 20% |
| outage (an added class: external, neither plumbing nor defect) | 5 (02m, 02p, 02t, 02v, 02x) | 4.4902 | 11% |
| budget | 1 (02za) | 2.8764 | 7% |
| thin sources | 0 (no run stops on it today) | 0 | 0% |
| **total** | **30** | **40.8676** | |

- **Thin sources overlaps the classes above.** 14 of these runs held one source (§4), and $17.65 was spent after
  acquire on them. Under §4's rule they would have ended "insufficient sources" before their recorded stop.
- **Stop-cause classes are a judgement.** The class is read from each RUN result and its DEV row; it is not a
  recorded field.

## For the ruling (not decided here)

1. Adopt §1's limit policy: one table, limits at least 2× the measured max, one re-ask on truncation with the limit
   doubled, Google truncation detected.
2. Build §2's reply store now, and the replay rehearsal as a gate before paid attempts.
3. Adopt §4's held-source minimum: 2 or 3, checked after acquire, ending "insufficient sources".
4. §5 rows 1, 2 and 4: let the landing route and open copies run before a retrieval-level refusal. Settle whether a
   correction notice that cannot be held should block a held source (row 15).
5. Settle whether this question (Q1-02) can meet any held-source minimum at all. Across 02z-02zd it held 1, 3, 1 and
   1 works; the walled T&F review and the two erratum rules account for 11 of the 18 refusals.
