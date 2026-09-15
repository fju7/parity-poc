# WHU engineering architecture review

**Review date:** 2026-09-15  
**System baseline:** `fju7/parity-poc@c92807897e7377a37bc30e4787e408fd58a747a5`  
**Research baseline:** `fju7/ai-research-reliability@02c8a758155d4b24ef708ca237fbc97dd468cfb5`  
**Scope:** architecture and engineering review only; no production code changed  
**Disposition:** `CLEAN_CORE_REBUILD_RECOMMENDED`

## Executive conclusion

WHU feels like whack-a-mole because its controls are attached to files and incidents rather than to a small, canonical state machine. The repository contains valuable parts, but the system as a whole has no single authoritative representation of a research run, proposition version, evaluation population, authorization, build, or deployment. Instead, meaning is distributed across mutable HTML, JSON ledgers, Markdown adjudications, dynamically imported Python scripts, Git history, hook installation, model output, local source bytes, Vercel state, and human convention. A new check commonly adds another representation, another state vocabulary, and another implicit dependency. It can close the triggering example while leaving the structural class elsewhere—or create a fresh stale derivative.

The immediate problem is not that WHU lacks safeguards. It has many. The problem is that safeguards do not operate under one transaction, one identity model, one failure algebra, or one dependency graph. `publish.py` dynamically loads more than two dozen sibling controls plus the shared Signal fact-checker and spend ledger. Some exceptions become warnings; some warnings may still permit publication; model findings can be accepted; hooks are local and bypassable; deployment is reconciled after Git-mediated publication; and authority is reconstructed from files that were not designed as a database. The current architecture has become difficult to test as a whole and expensive to reason about.

The safest target is a **clean, deliberately small research core** built beside the incumbent, with migration rather than a big-bang cutover. Preserve validated source snapshots, bindings, historical publications, adjudications, incident fixtures, outside-review materials, and narrow deterministic checks. Do not port the current orchestration or its entire control catalogue. New work should flow through immutable objects, append-only events, exact execution receipts, typed non-pass states, explicit population accounting, version-bound review, dependency invalidation, and a signed release manifest. Semantic judgments remain judgments with named evaluator, evidence view, confidence, disagreement, and scope; they never become mechanical facts merely because they are stored.

Incremental repair alone is rejected. The monolithic, dynamically composed publication path and file-based state model make foundational repair invasive enough to be a rewrite conducted inside the most fragile code. A major in-place refactor is possible but has worse rollback and comparison properties. A clean core with adapters permits shadow execution, record-by-record comparison, and issue-by-issue cutover while keeping the incumbent read-only except for export adapters.

## What the review found

- The real execution boundary extends beyond WHU-named paths into `backend/scripts/signal/factcheck_draft.py`, `signal_model.py`, `backend/scripts/spend_ledger.py`, shared verification policy, test fixtures, Git hooks, Git history, GitHub workflows, Vercel, Anthropic, Resend, registries, the live web, and operator environment.
- Execution identity is not one durable object. Repository SHA alone is insufficient because dynamic path loads, working-tree bytes, uncommitted data, environment, provider aliases, prompts, source snapshots, hook installation, and deployed bytes can differ.
- The current data model conflates content and workflow state. HTML is simultaneously authored content, a model input, a publication unit, and a source for derived checks. JSON and Markdown files serve as ledgers, state transitions, waivers, and narrative records without transactional integrity.
- The three-value control vocabulary (`ok`, `BLOCKED`, `warn`) is too coarse for execution semantics. It cannot faithfully represent not attempted, partial, error, stale, invalidated, waived, disagreement, or not applicable. Warnings are especially overloaded.
- The strongest current assets are the explicit source-access distinctions, content-addressed source storage design, exact-span bindings, incident corpus, external review packets, historical adjudications, publication byte hashing, and several narrow deterministic validators. Their claims must be narrowed to what they establish.
- The weakest area is authority propagation: which exact proposition, page, email, review packet, build, and deployed bytes a review/control authorizes, and what invalidates that authority.
- Open-world coverage cannot be made complete. WHU should record search scope and residual uncertainty rather than expose a `COMPLETE` flag.
- The model layer is not the main architectural novelty. Most failures are conventional failures of identity, state, missingness, dependency closure, aggregation, release engineering, and observability.

## Baseline evidence

The audit ran the current WHU suite without changing it:

```text
414 passed, 25 failed, 1 skipped
```

Twenty-four failures came from benchmark spans whose source-store lookup returned `undetermined`, because the required held bytes were unavailable in this checkout. One failure reported that the live melanoma change log did not pass its own correction rule. This result is not treated as “mostly passing”: the evaluated population was 440 tests, with 414 pass, 25 fail, and 1 skip. The missing-source cases are also evidence that tests and historical cases are not hermetic.

## Recommended decision

Build a new `whu_core` beside the existing implementation. It should initially be a ledger and release authority, not a new collection of semantic checkers. First ingest and identify existing objects without claiming completeness. Then dual-write receipts and typed states. Then shadow dependency invalidation and release manifests. Only after the new core can reproduce and explain an existing issue should it become authoritative for new issues. The old publication path remains available for rollback until two complete issues and one correction cycle have passed defined equivalence and incident-replay gates.

Do not add another semantic control before foundational identity, receipt, state, population, and invalidation work is in place.

## Deliverables

1. [Current state and control audit](current-state.md)
2. [Target architecture and engineering standard](target-architecture.md)
3. [Migration roadmap, alternatives, and risk register](migration-and-risk.md)
4. [Adversarial review: 60 attacks](adversarial-review.md)

## Hard implementation gate

This review changes documentation only. No production implementation should begin until the owner reviews the target, agrees to the clean-core migration strategy, selects the first shadow issue, and explicitly authorizes implementation.
