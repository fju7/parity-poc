# WHU clean-core implementation plan

**Status:** implementation authorized; foundation only  
**Branch:** `feat/whu-core-foundation`  
**Production authority:** unchanged

## First increment

This increment implements the smallest dependency-free foundation:

- canonical serialization and content identities;
- closed execution, coverage, and pricing states;
- immutable execution/attempt receipt types;
- mechanical authority eligibility that refuses error, partial, invalidated, and unknown-price states;
- a service-role-only, append-only PostgreSQL migration for shadow receipts;
- unit and invariant tests.

It does not apply the migration, route production calls through the core, authorize publication, create semantic verdict types, or backfill historical records.

## Acceptance criteria

1. Canonical identity is stable under dictionary ordering and refuses lossy/non-JSON values.
2. Terminal execution states cannot transition to completion.
3. Completed attempts require a response hash; errors require an error code.
4. Attempt ordinals are contiguous, so a dropped retry cannot be hidden.
5. Unknown cost is represented by `NULL`, never numeric zero, and blocks authority eligibility.
6. Non-evaluated, partial, and invalidated coverage block authority eligibility.
7. Idempotency identity changes when consequential payload/code/config/prompt/policy/fixture identity changes.
8. Database tables are append-only and inaccessible to anonymous/authenticated client roles.

## Review gate before integration

Before applying migration 093 or modifying a model call site:

- review privacy and retention for stored payload references;
- decide which blob store and encryption boundary will hold full payloads;
- test the migration in staging, including RLS posture and append-only triggers;
- implement a transactional repository/outbox and failure-injection tests;
- select one non-publication call path for shadow dual-write;
- define a rollback that disables dual-write without weakening existing execution.

## Following increments

1. Receipt repository, encrypted payload store, and transactional outbox.
2. One Signal/WHU model call in shadow dual-write, with provider timeout and retry injection.
3. Immutable source/representation and population manifests.
4. Dependency edges and invalidation in shadow.
5. Release manifest and deployment reconciliation.

Each increment requires its own review and measured shadow criteria. Publication authority remains with the incumbent until the architecture review's cutover Definition of Done is met.
