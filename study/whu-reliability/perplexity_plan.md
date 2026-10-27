# WHU reliability study: Perplexity add-on plan (exploratory)

Approved by Fred 2026-10-27, after all study results were seen. Frozen by the commit that adds this file, before any Perplexity run. Its sha256 is recorded in `deviations.md`.

## Status

- **Exploratory.** This is a comparison of WHU with one more tool, Perplexity Deep Research. It is outside H1 and H2, and it changes no study result, rule or figure already reported.
- **Questions:** WHU-S01 to WHU-S04 only.
- **Budget:** one new ledger issue, `whu-reliability-judging-perplexity`, with `--cap 32.82`. That is $375 less the $342.18 already spent (the ledger sums to $342.19: WHU $99.07, judging $243.12). The $375 study total check still applies. Every model call in this add-on, the takeaway comparison included, is billed to this issue and bounded by this cap. The judging day cap (`caps.json` "study_judging_per_day", every `whu-reliability-judging*` issue) applies as before. The cost is estimated before any call. If the estimate exceeds the cap, the work STOPs and is reported.

## Runs

- **Tool:** Perplexity (perplexity.ai) in Fred's Chrome, on Fred's account, in Deep Research mode (or "Research", whichever the app names it). The mode and any model the app shows are recorded.
- **Settings:** before the first run, the states of memory, personalisation, the AI profile, connected apps and files (e.g. Gmail, Drive) and any selected Space are recorded. Memory, personalisation and connected-file sources are switched off for the runs. Nothing else is changed. Every setting's before and after state is recorded so Fred can restore it.
- **Prompt:** each question's RUN_TOOLS.md question box, pasted exactly, protocol sentence included. One new thread per question, with no follow-ups.
- **Clarifying questions:** if Perplexity asks one instead of starting, the reply is exactly "Please proceed with your best interpretation." (Fred's brief for this add-on), and the exchange is recorded. This differs from RUN_TOOLS.md's "Please answer the question as asked."
- **Once only.** Each question is answered once. A rerun is allowed only after a technical failure, which is logged with evidence first (protocol, fairness rule 2).
- **Capture:** each answer is saved by Perplexity's own export, Markdown if offered, otherwise PDF, into ~/Downloads. It is moved byte for byte to `~/Projects/whu-study-private/answers/WHU-S0N/perplexity.raw.<ext>`. `perplexity.md` is built around it by `tools/build_capture.py`, as the other captures were, with nothing retyped. Both files are hashed. Each run is recorded in `answers/run_record_perplexity.md`: time, mode and model shown, settings, clarifying exchange, export route, sizes and sha256. Only the sha256 manifest is committed.

## Scoring

Everything is done as for WHU-S01 to WHU-S04, with the same code, prompts, models and rules. Nothing already scored is changed. Perplexity has its own private run directories (`~/Projects/whu-study-private/scoring/perplexity/`), so the study's existing items, samples, replies and manifests are not touched.

- **Adapter.** A Perplexity adapter in `blinding/adapt.py` takes the report out of the capture and maps each citation marker to its own entry in the answer's numbered source list, as `adapt.claude_sources` does for Claude's Markdown export. A marker the list lacks, or an entry with no URL, stops the run. It is tested against the four answers by script: every marker resolves, and the counts are reported.
- **Blinding.** blind.py runs unchanged. Perplexity's names are added to the blinding phrase list (`blind_phrases.json`): "Perplexity" (with or without "AI") and its share-link host. The list's sha256 is re-pinned in blind.py and the change is logged in deviations.md. Before any Perplexity item is sampled, the 32 existing blinded answers (S01-S08) are re-blinded from their adapted sources and must match `blinded_manifest.txt` byte for byte. If they do not, the work STOPs.
- **M1 sampling.** This uses the Stage 1 rule: 20 claim-like sentences per answer (`identifiability.claim_like`), or all of them if there are fewer. The draw is `random.Random("<SEED>/<question>/Perplexity/M1")`, where SEED is the freeze commit `5d83e9b…` read as a hexadecimal integer. A drawn sentence with no marker is UNCITED. Item ids are `opaque("M1", "<question>/Perplexity/<idx>")`.
- **M2 items.** Every conclusion of each frozen key is judged against Perplexity's answer: 5, 5, 1 and 2 conclusions, 13 items in all.
- **Snapshots.** One snapshot per distinct cited address, with the "#:~:text" fragment dropped. If an address already has a row in the study's snapshot manifest, that row and its snapshot are reused, so the same evidence serves every system. Each new address goes through `snapshot.py`, then routes (a) to (c) of `retrieve_sources.py`. Route (d) is used for sources marked free to read but blocking automation, fetched in Fred's Chrome by Claude Code, under the same ruling as the extension: no sign-ins, no account creation, no payment, and no way past a paywall or bot wall. Each file passes `ingest_operator.py`'s size and sha256 check, and its extent is decided by the same rule as a script fetch.
- **Judging.** `judge_m1.py` (M1 v3) and `judge_m2.py` (M2 v2) run unchanged: Claude Opus 5.5 and gpt-6-astra, with the same delivery, refusal rule and abstract-only rule. Each judge has a seeded 20% second read (seed: the freeze commit; pool: the Perplexity items judged), written to that run's own `consistency_sample.json`. Both run on `whu-reliability-judging-perplexity` with `--cap 32.82`.

## Analysis (exploratory)

Perplexity's M1 and M2 rates are computed by `analyse.py`'s rules as `analyse_eight.py` applies them on S01-S04: the EVERY abstract-only correction, and Uncited counted as an M1 failure. The views reported, each with its n, are:

- two-judge combined;
- each judge alone;
- agreed only;
- M1 on cited items only;
- reachability (scripted, with Fred's-Chrome fetches, still unreachable);
- the uncited share.

**WHU minus Perplexity** on S01-S04 uses the difference, the ratio and 95% intervals from the same bootstrap: whole questions resampled (4 with replacement), 10,000 resamples, `random.Random(int(freeze commit, 16))`. WHU's rows are the existing S01-S04 rows, unchanged. The M2 label counts are given per judge (Claude judge / OpenAI judge). All of this is labelled exploratory, judged by AI models only, and outside H1 and H2.

## Takeaway comparison (spec (d), exploratory)

This uses spec (d)'s two prompts, verbatim from `machine_only_plan.md`, as run by `takeaway.py`, with the same models and the same quote check.

- **Extraction:** run on Perplexity's four blinded answers by both judges. WHU's S01-S04 extractions already exist from the spec (d) run with the same prompt and judges, and are reused, not re-run.
- **Comparison:** run on WHU against Perplexity for each of S01-S04, by both judges. The A/B order is seeded by `random.Random("<SEED>/takeaway/<question>/WHU-Perplexity")` and recorded.
- **Reporting:** disagreements between the judges are reported, not resolved.

## Limitations

- Perplexity answered on 2026-10-27, 5 days after the other tools' S01-S04 runs (2026-10-22), not within the protocol's 48-hour window. Fred's brief described this as about 10 days; the 5-day figure is the measured one.
- The plan was approved after every study result had been seen.
- Fred's Perplexity account and its settings are used as found, apart from the switches above.
- Judged by AI models only, with no human review.
- The blinding identifiability check is not run for Perplexity. At the study's freeze it was a measured limitation, not a gate.
