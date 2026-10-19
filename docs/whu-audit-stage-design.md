# WHU audit stage — design (not built)

*Approved 19 October 2026 (protocol rev 23, "Audit stage design approved") with two additions, both now in the text below: a sentence still failing after three read-and-correct rounds is cut and the cut logged, and the meta description and card text are read in the same pass as the body. Built in prep round 2 as `backend/scripts/whatholdsup/audit_stage.py`, with its prompts in `backend/scripts/whatholdsup/audit_prompts/`; see "As built" at the end for where the build departs from this design. It turns the deskilling audit of 18–19 October 2026 into a stage that runs the same way on every draft, so that it can be frozen as part of the WHU process the reliability study tests.*

## Why this stage exists

The deskilling page had been through every automatic check WHU has, and it was then read sentence by sentence against its sources and WHU's own records. The reading found 140 sentences to correct out of about 435 (`docs/whatholdsup-deskilling-revision.md`; corrections.md, entry of 19 October 2026).

- **The automatic checks** (bindings rules, the narrow gate, changecheck) caught almost none of those 140.
- **The one-shot conclusion judge** caught 15 of the 24 judgement errors. It also raised 12 false alarms among 24 sound sentences.

Reading every sentence is what found the errors. A reading that depends on someone deciding to do it is not part of a process that can be frozen and tested. This stage makes it part of the process.

## Inputs

The stage reads only what is committed, and records the sha256 of each input on the run's manifest.

| Input | What it is | Where |
|---|---|---|
| The draft | The page as it would be published, header to footer | `site/whatholdsup/<slug>.html` or the issue's `draft/`; sha256 of the bytes |
| Bindings | One row per sentence: span, premises, records it rests on, declared framing, hedge and scope dispositions | `issues/<case>/bindings.json` |
| Held sources | The text of every source the page cites, as held, each with its document sha and readable extent | the source store (`source_store.py`), `sources.json` |
| WHU's records | What process sentences are checked against: corrections, sweeps, premise, review files, commits | the issue directory and `git log` |

## Unit of work: every sentence row

The unit is **every sentence a reader sees**. That means each bindings row, including:
- the header and footer rows (`25c1100`);
- the standfirst;
- the meta description;
- each source-list note;
- each change-history entry.

It is not limited to the sentences the empirical rule selects. The deskilling reading found 53 of its errors in sentences that rule does not reach. Sentences are identified by their binding-row sha, so a verdict belongs to the exact wording it was given on.

Sentences are read in **batches of about 15 to 25, grouped by the source they rest on**. That is how the deskilling batches were cut: one agent holding one source's text reads every sentence that cites it. Sentences with no source go to a batch of their own: judgements read against their premises, and process sentences read against WHU's records.

## What the reading agent reads per sentence

Each sentence is read with:

1. **The sentence, its paragraph, and the sentence before and after.** Joining sentences are where this publication fails (process doc §12h).
2. **Its binding:** span, premises, `rests_on_record`, framing and dispositions. These are *what to check*, never evidence that it holds. The binding is the claim's own account of itself.
3. **The held source text itself**, opened at the span and searched in full for every figure, name, date and quoted phrase the sentence carries. The rule from the deskilling batches: read the source, not the binding's summary of it, and not a review's summary of a study the review cites.
4. **For a judgement sentence:** each premise's span, read in its source. The question is whether the step from premises to sentence adds anything the premises do not carry.
5. **For a process sentence** ("we read", "we could not open", "checked on"): the named WHU record, at the commit that made it. A process claim with no record behind it is a finding.
6. **For an attribution** (who said it, in which document, when): the source's identity, meaning its title page and front matter, as held.

The agent has read access to the case directory and the source store, and nothing else. In particular it has no web access. A source that is not held is a finding ("rested on a document we do not hold"), never a reason to go and find something.

## Verdicts and finding kinds

Every sentence gets one verdict:

- **holds**, with the verbatim span(s) it rests on;
- **finding**, of one kind below, with evidence and a proposed corrected text;
- **not a correction**: apparatus, under the process doc §9 classification rule;
- **updated by the source**: the source itself changed (a revised paper, a new version). This is recorded, but it is not WHU's error. Liu v6 was this case.

The finding kinds are the deskilling error kinds, unchanged. Counts on the corrections page are of 19 October 2026:

| Kind | Deskilling count |
|---|---|
| Overstated a finding or a source's claim | 72 |
| Misattributed or misdescribed | 24 |
| Claimed more about our own process than our records show | 20 |
| Rested on a document we do not hold | 7 |
| A wrong date, count, figure or author | 6 |
| Understated a source's standing | 5 |
| Misquoted | 3 |
| Understated a finding | 2 |
| A copy defect | 1 |

## How findings are recorded

The stage keeps one directory per run, `issues/<case>/audit/<run-id>/`. It holds:

- `manifest.json`: input shas, prompt shas, model ids, the batches, start and end times.
- `findings.jsonl`: one row per sentence. Each row carries:
  - the row sha and the sentence;
  - the verdict and the kind;
  - evidence as `{source_id, document_sha, quote}`;
  - the proposed text;
  - the agent id and batch;
  - the tokens used and the time.
- `rulings.jsonl`: one row per finding: the ruling (accept, reject or amend), the amended text, a one-sentence reason, who ruled and when.

Before anything is ruled, a script checks that every quoted evidence span occurs verbatim in the named document. The deskilling batches did this by hand. A finding whose evidence is not verbatim goes back to its agent; it is not passed to the advisor.

## How each finding is settled

The advisor rules on every finding. This was ruled on 19 October: the advisor's rulings are part of WHU's process, and each one is logged with its time, like the operator's manual steps.

- The advisor sees only:
  - the finding row;
  - the sentence in its paragraph;
  - the quoted evidence and enough of the source around each quote to read it in place.
- **"Accept"** means the corrected text goes into the draft. The changed sentence then gets a new row sha and is read again, in a short re-read pass, until it holds.
- **"Reject"** needs a reason that cites the source. The sentence keeps its holds verdict with the advisor's span.
- **A sample of "holds" verdicts is read again by a second, independent agent.** The sample is 10% of rows, plus every judgement row. This estimates how often the audit itself misses something. The deskilling run had this shape: batch readers, then the main session re-checking. That is the only check on the stage's own miss rate before Stage 2 (protocol open item "Ground truth for the audit itself").

## What blocks publication

A new preflight row, `audit complete`, is a **STOP** (fail closed, no `--waive`) unless all of the following hold:

1. Every sentence on the page, at the page's current sha, has a verdict whose row sha matches its current wording. A sentence edited after its verdict has no verdict.
2. Every finding has a ruling.
3. Every accepted finding is applied, and its new wording has a holds verdict.
4. The second-reader sample is complete, and every disagreement in it is ruled.
5. The run's manifest input shas match the committed bindings and source store, so nothing was read against a different version.

## Cost and time per sentence

**What the deskilling records allow:**
- **Wall-clock time.** Git timestamps show the reading took about 9 hours 10 minutes for about 435 sentences: batch 1 committed at 12:02 on 18 October, and "every sentence now read" at 21:11. That is about 1.3 minutes of elapsed time per sentence. The figure includes binding work, the operator's turnarounds and five batches run one after another.
- **Corrections and verification** (republish steps 1 to 2f) took about 3.5 more hours on 19 October, from 08:57 to 12:25.

**What they do not allow is cost per sentence.** The reading ran in Claude Code, on a subscription, through read-only subagents. Its tokens are not in the spend ledger. The only metered deskilling spend on 18 October is the conclusion judge: $0.17, 48 Sonnet calls.

The stage therefore records its own tokens and time per sentence and per batch, in `findings.jsonl`, from its first run. The practice-question run is where cost per sentence is first measured. Until then, any figure is an estimate. As one: about 20,000 input tokens per sentence at Opus 5.5 rates gives roughly $0.08 to $0.12 a sentence, or $35 to $50 for a 435-sentence page. That is not a measurement.

## Running unattended

The stage has to run without Fred in the loop. Under the study's integrity rules his manual steps count against WHU.

- **A driver script** (to be built) cuts the batches, starts one headless Claude Code agent per batch with the fixed reading prompt, and collects `findings.jsonl`. It then runs the verbatim check, calls the advisor once per finding with the fixed ruling prompt, applies accepted text, and re-reads changed sentences. It writes the manifest throughout.
- **Prompts are files, frozen with the protocol.** The reading prompt and the ruling prompt are each identified by sha256 on the manifest.
- **It stops itself.** It halts on a spend cap (the spend ledger, per issue and per day), on an agent failure (logged; the batch is re-run once, then the stage stops), and on any input sha changing mid-run.
- **Fred starts the run and reads its summary.** Anything he does in between is a logged manual step with a time.

## Isolation in the study: what the advisor and the agents must not see

The advisor's rulings are part of WHU's process, so the advisor must see only what WHU's process would show it on any ordinary issue. It must never see:

- **The answer key** for the question, or any part of it: its conclusions, direction, size, certainty grades or scope notes. Nor the fact that a key exists.
- **The identity of the review the question was drawn from, as such.** WHU may find and cite that review on its own; finding it is what M3 (coverage) measures. The advisor must not be told it is the target.
- **Any other system's answer** to any study question: Claude Research, ChatGPT deep research, Gemini Deep Research.
- **Any judge verdict, blinded material, human label or interim result**, for this question or any other.
- **The study's question list, draw seed or protocol working files**, beyond what WHU's own process documents say.

**How this is enforced:**
- The study's private material (keys, other systems' answers, judge outputs) lives outside the WHU repository's case directories, in a location the driver never mounts.
- The advisor is called only by the driver, with a prompt built from the finding row and the held source text. The manifest records the sha256 of every advisor input, so it can be shown afterwards that nothing else was passed.
- The advisor instance used for rulings is not the instance that drafted or checked any answer key (ruled 19 October, "Answer-key checking in Stage 1").

## Before freezing

1. Build the driver and the two prompts.
2. Run the stage on one practice question (protocol open item "WHU outside health").
3. Measure tokens, time and the second-reader disagreement rate per sentence.
4. Then freeze the stage with the protocol.

Any change after the freeze waits until the study ends (integrity rule 1).


## As built (prep round 2, 19 October 2026)

`backend/scripts/whatholdsup/audit_stage.py` is the driver. `audit_prompts/read.md` and `audit_prompts/rule.md` are the reading prompt and the ruling prompt, each identified by sha256 on every run's manifest. Tests: `backend/tests/test_whatholdsup_audit_stage.py`.

**The two additions.**
- **Cuts.** A sentence still failing at its third read is cut. Its text must leave the page, and `cuts.jsonl` records every round's finding and ruling. A ruling that amends a sentence to "" cuts it too.
- **Card and meta description.** `units()` reads the homepage card's prose and the meta description in the same pass as the page and the change history. A card or meta sentence with no binding row of its own is read against the binding of the page sentence it restates (word overlap of at least 0.45), and the unit records which one.

**Where the build departs from the design above.**
- **The reading runs through the API, not headless Claude Code agents.** That puts every token in the spend ledger, so a cap is a cap and cost per sentence is measured, not estimated. A held text over 120,000 characters is cut to windows around the batch's spans and key terms.
- **The ruling model replaces the advisor during the study.** This is the protocol's ruling of 19 October ("Advisor rulings during WHU's run"). `ruling_payload()` is an allow-list of five fields: the sentence, the kind, the reader's reason, the proposed text, and the quoted source text, each quotation shown in its document. Not even a source id travels. The test inspects what the fake model was actually sent, with forbidden fields smuggled into the binding row.
- **The second reader's accepted findings are not re-read in the same run.** Their old wording is marked "must leave the page", and the next run reads the corrected text.
- **Any failure stops the run** and the manifest says "failed": a reply that does not parse, a quotation still not verbatim after one re-read, a refusal, a reply cut off at its token ceiling, the spend cap or the day cap.

**The preflight row.** `audit complete` is a STOP unless all of the following hold:
- the latest run under `issues/<case>/audit/` is complete;
- it was not a `--dry-run` (which reads a limited number of units);
- every sentence a reader will see, at its current wording, is settled in it;
- no wording the audit corrected or cut is still on the page.

**Issues published before adoption.** An issue first published before 19 October 2026 (`ADOPTED`) is SKIPPED by name, as the conclusion judge does for the issues that predate it. Deskilling, cdk46 and melanoma are SKIPPED. Whether they should be audited under the stage is a decision left open.
