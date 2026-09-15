# Target architecture and engineering standard

## 1. Design rule

The core records **what object existed, what operation ran, what population it covered, what evidence it saw, what judgment it returned, and what authority was granted**. It does not declare semantic truth. Mechanical facts and semantic judgments use separate types, storage fields, UI language, and authorization policies.

Every proposed component must prevent or expose a named failure and emit evidence that it did so. If it cannot demonstrate incremental value over a simpler component, it is removed.

## 2. Architecture

```text
                         +-----------------------+
question + scope ------> | Research Run service  |
                         | immutable event log   |
                         +-----------+-----------+
                                     |
              +----------------------+----------------------+
              v                      v                      v
      +---------------+      +---------------+      +----------------+
      | Source adapters|      | Model gateway |      | Human workbench|
      | fetch/parse     |      | receipts/cost |      | exact versions |
      +-------+-------+      +-------+-------+      +--------+-------+
              |                      |                       |
              +----------------------+-----------------------+
                                     v
                         +-----------------------+
                         | Canonical object store|
                         | blobs + relational DB |
                         | versions/dependencies |
                         +-----------+-----------+
                                     |
                         +-----------v-----------+
                         | Evaluation/control    |
                         | scheduler + state     |
                         +-----------+-----------+
                                     |
                         +-----------v-----------+
                         | Release authority     |
                         | signed manifest       |
                         +------+----------+-----+
                                |          |
                           pure build   deploy adapter
                                |          |
                          pages/email   public bytes
                                +----+-----+
                                     v
                              reconciliation
```

### Minimal components

1. **Canonical store:** PostgreSQL for metadata/events/constraints; content-addressed object storage for source bytes, payloads, outputs, and built artifacts. It is not a graph database; dependency edges are an ordinary table.
2. **Research-run coordinator:** validates legal transitions and schedules work. It is not a distributed workflow engine initially; one transactional worker and an outbox are safer.
3. **Source adapters:** acquire and parse while preserving originals and transform receipts. Each adapter has a narrow contract.
4. **Model gateway:** the only production path to a provider. It stores a receipt before results can create authority, applies budgets, and exposes typed failures.
5. **Control runner:** runs deterministic controls and records semantic evaluations under different result types.
6. **Human workbench:** shows exact proposition, source context, transformations, competing evidence, and prior judgments; captures structured decision plus rationale.
7. **Release authority:** evaluates a declarative policy against exact versions and produces a signed manifest. It never edits content.
8. **Pure builders/deploy adapters:** derive pages, indexes, review packets, and emails from the manifest; deploy and reconcile bytes.

Avoid Kafka, microservices, a graph database, event sourcing frameworks, and a giant ontology until scale demonstrates a need. A modular monolith, one database, one blob store, one job queue/outbox, and explicit provider/deploy adapters are sufficient.

## 3. Canonical object model

The smallest useful model is below. Names such as “claim” are not proof of truth.

| Object | Immutable identity / essential fields | Purpose |
|---|---|---|
| `ResearchRun` | run ID, question/scope version, cutoff, owner, state | execution umbrella and declared boundary |
| `SourceObject` | source ID/version, origin metadata, captured blob hash, acquisition receipt, license/privacy class | distinguish discovery, capture, and bytes |
| `Representation` | parent source/version, parser/transform identity, blob hash, loss/truncation metadata | make transformations explicit |
| `PropositionVersion` | stable proposition ID, version ID, exact text + optional structured facets, parent/reason | consequential semantic unit |
| `EvidenceRelation` | proposition version, source/representation/span/context, relation judgment version | candidate support/contradiction; not truth |
| `PopulationManifest` | population ID, member IDs, attempted/eligible/evaluated/excluded/error/reported counts and reasons | prevent silent denominator changes |
| `ExecutionReceipt` | execution/attempt IDs, operation, caller, exact inputs, code/config/model/prompt identity, payload/response refs, timing/error/usage/cost | reconstruct consequential operations |
| `Evaluation` | subject version, task/contract, evaluator identity, evidence view, population, semantic verdict/confidence/rationale/disagreement | store explicit judgment |
| `ControlExecution` | subject version, invariant ID/version, receipt, typed state, diagnostics | narrow mechanical result |
| `Authorization` | exact subject versions, policy version, authority/actor, decision, expiry/waiver | permit a transition without claiming truth |
| `DependencyEdge` | upstream version, downstream version, edge type, producer identity | invalidation and impact closure |
| `Correction` | trigger, affected versions, replacement/withdrawal versions, adjudication, propagation state | correction as transaction |
| `ReleaseManifest` | complete object/version set, required control/evaluation states, build inputs, signer | one release identity |
| `Artifact` / `Deployment` | build hash, artifact bytes, environment, deployment/provider IDs, observed public hashes | separate built, deployed, and observed |

Do not create separate domain objects for every current JSON file. Import them as legacy evidence or projections. Add a type only when it has an independent lifecycle or invariant.

### Source state

Source state is multidimensional, not one status:

- discovery: `DISCOVERED | NOT_DISCOVERED` (bounded to a recorded search);
- acquisition: `NOT_ATTEMPTED | FETCHED | BLOCKED | ERROR`;
- representation: `UNPARSED | PARSED | PARTIAL | ERROR`;
- supply: exact representation/blob IDs included in a particular request;
- human handling: `NOT_REVIEWED | REVIEWED` with actor/time/version attestation;
- relation: a proposition-specific semantic judgment;
- coverage: a search-process record, never global completeness.

“Considered” should not be a mechanical state unless a person/evaluator explicitly attests to a defined task. Payload inclusion proves supply, not attention.

### Evaluation state

Execution and verdict are separate:

```text
execution_state = PENDING | RUNNING | COMPLETED | ERROR | CANCELLED
coverage_state  = NOT_EVALUATED | PARTIALLY_EVALUATED | EVALUATED | INVALIDATED
verdict         = SUPPORTS | CONTRADICTS | MIXED | INSUFFICIENT | DISAGREEMENT
```

`verdict` is nullable unless execution completed and the declared population was evaluated. Deterministic controls use `PASS | FAIL | NOT_APPLICABLE` only after successful execution. Staleness and waiver are attributes/authorizations, never pass values.

## 4. Execution flow

1. Register question, intended scope, temporal cutoff, authority requirements, and initial search plan as a version.
2. Record every search run, query, adapter, result population, exclusions, and inaccessible sources.
3. Capture source bytes and immutable representations; emit transform receipts and truncation/loss flags.
4. Create propositions before polished prose where practical. Preserve the original consequential sentence when prose-first work occurs.
5. Bind candidate evidence to exact proposition versions. Deterministic checks verify bytes/locators only.
6. Run semantic relation evaluations against original context. Preserve independent judgments and disagreements.
7. Generate draft artifacts from authorized proposition versions and editorial material.
8. Re-extract/align draft sentences to proposition versions. A semantic materiality decision is explicit; uncertainty requires review.
9. Run deterministic controls, model triage, and human review against exact release-candidate versions and population manifests.
10. Release authority evaluates policy and issues an authorization or enumerated blockers. No generic “verified.”
11. Pure build creates all derivatives in one build graph; manifest binds their hashes.
12. Deploy adapter records provider/build/deployment IDs; reconciliation compares public bytes with manifest.
13. Any upstream change inserts invalidations synchronously in the same transaction. Refresh creates new versions; it never clears history.

## 5. Hard invariants

| Invariant | Enforcement | Test | Failure and observability | Recovery |
|---|---|---|---|---|
| ERROR never becomes PASS | DB constraints + result algebra | property test all transitions/aggregations | transaction rejected; alert with IDs | retry creates new attempt; no overwrite |
| UNKNOWN/missing never becomes zero/empty success | schema nullability + typed amount/state | serialization and mutation tests | reject write or emit explicit UNKNOWN | add price/data or scoped override |
| Review binds exact versions | authorization foreign keys to immutable hashes | mutate any subject and assert invalidation | release blocked; stale review visible | re-review or approved nonmaterial transform rule |
| Material change cannot inherit authority | version creation + invalidation transaction | subject/predicate/scope/polarity/time mutations | dependents `INVALIDATED` | adjudicate materiality/re-authorize |
| Every consequential call has receipt | gateway transaction and DB constraint | kill before/after provider; missing-receipt injection | result cannot be authoritative; metric/alert | recover provider ID if possible, else rerun |
| Every aggregate names populations | `PopulationManifest` required FK | dropped/error/empty batch properties | aggregate write rejected | correct manifest/recompute |
| Blocking control proves current input | subject hash and control version required | stale-input test | release blocker names mismatch | rerun current version |
| Release traces to build/deploy/public bytes | manifest/deployment constraints | failed/partial deploy tests | state remains BUILT/DEPLOYING/MISMATCH | redeploy or rollback manifest |
| Upstream change invalidates declared dependents | synchronous edge traversal/outbox | randomized DAG mutation tests | release policy sees stale nodes | rebuild/review/waive exact edge |
| Missing dependency closure is non-pass | release impact query | hidden-edge fixtures and expected-set reconciliation | `INCOMPLETE_CLOSURE`, not PASS | register edge; rerun impact |
| Non-evaluated/partial/error/stale cannot satisfy required policy | policy engine types | truth-table/property tests | blocker with population/reason | complete work or scoped waiver |
| Unknown model cost is not zero | money amount nullable + pricing status | unpriced model fixture | call refused by default/UNKNOWN recorded | price model or explicit capped authorization |
| Mechanical check cannot emit semantic verdict | separate schemas/APIs | type and contract tests | invalid write rejected | create semantic Evaluation |
| Correction propagates atomically as obligations | correction transaction + dependency edges | partial-write/crash tests | correction remains PENDING_PROPAGATION | resume idempotently |
| Retrying does not duplicate authority/spend records | idempotency key per attempt/effect | retry storms | duplicate effect rejected, attempts retained | reconcile uncertain provider outcome |
| Publication population is closed and enumerated | release manifest members | add unmanifested artifact | deploy rejected | rebuild signed manifest |

## 6. Observability and execution evidence

Every consequential operation receives `execution_id`, `attempt_id`, trace ID, caller, operation contract/version, exact input object versions, dependency/code/config hashes, timestamps, and result state. Model receipts additionally record:

- `request_payload_submitted_to_sdk` (encrypted or access-controlled), not “wire bytes”;
- provider, requested model, resolved model/snapshot when returned, settings, tool definitions;
- prompt/template/policy hashes and rendered payload hash;
- exact source/evidence representations included and byte/token truncation facts;
- exact response, provider request ID, finish reason, parsing result;
- error and retry lineage;
- usage and cost with `KNOWN | ESTIMATED | UNKNOWN` pricing state;
- downstream object IDs created from the response.

Metrics: receipt coverage, error/partial/stale populations, invalidation age, release-block reasons, retry/duplicate rate, unknown cost, control yield and overlap, human minutes, disagreement, false block, correction propagation latency, deployment mismatch duration. Logs must never be the only record of authority.

Retention: metadata and hashes retained with the research record; sensitive full payloads encrypted with role-based access and a declared retention window; licensed source bytes stored according to rights; deletion produces a tombstone and renders reproduction partial. Never retain secrets in payloads. Redaction transformations get their own hashes and receipts.

## 7. Deterministic versus semantic boundary

Mechanical facts include hash equality, payload membership, counts, state transitions, timestamps, executed control versions, and public-byte equality. Semantic judgments include paraphrase identity, entailment, source authority, evidence adequacy, search sufficiency, inference quality, and fairness.

A semantic evaluation may authorize publication under a policy, but the UI must say, for example, “Reviewer R17 judged proposition P3v5 supported by evidence E8/E9 under task T2,” not “verified.” Disagreement remains visible. A model result is evidence of a model judgment, not a fact about the world.

## 8. Broad-domain/open-world design

Each research run records databases/source classes, queries, languages, dates, exclusions, inaccessible items, counterevidence terms, snowball/citation traversal, sentinels, and stop rationale. Coverage output is a process statement and residual-risk assessment. The only allowed completeness claims are bounded to a defined, enumerable corpus whose denominator is recorded. Domain authority is a semantic judgment with rationale, not a global source ranking.

## 9. Human review

The workbench presents side by side:

- exact proposition and its parent/version diff;
- original source bytes or lawful view, surrounding section, and locator;
- every representation/transformation and truncation warning;
- candidate support and contradiction;
- model interpretations, sealed until initial human judgment where independence matters;
- search scope, inaccessible sources, and residual uncertainty;
- review/adjudication history and affected derivatives.

Humans decide semantic identity, evidence relation, adequacy for the intended claim, disagreement, exceptions, and publication authorization. They do not attest that scripts ran; receipts do that. Burden is measured in minutes, queue age, rereview rate, disagreement, and corrections found per hour. A reviewer may abstain or mark insufficient evidence. Rubber-stamp “approve all” is not supported.

## 10. Testing architecture

- **Unit:** parsers, hashers, state transitions, policy predicates, pure builders.
- **Schema/state machine:** database constraints and exhaustive transition tables.
- **Property/invariant:** errors never pass; population totals reconcile; any upstream mutation invalidates all reachable dependents; builders are deterministic.
- **Integration:** real DB/blob/outbox; source adapter fixtures; model gateway with recorded SDK fakes; deploy/email adapters in sandbox.
- **Dependency resolution:** static declarations plus runtime receipt comparison; dynamic-import and prompt/config changes must show impact.
- **Model wrapper:** requested/resolved model, retries, truncation, usage/cost unknown, tool payload preservation, malformed responses.
- **Failure injection:** provider timeout after charge, lost response, DB commit failure, outbox duplication, partial blob upload, build failure, deploy mismatch, live probe outage.
- **Mutation:** remove a population member, alter a hash, change subject/quantifier/polarity, omit a control receipt, change a prompt without impact declaration.
- **Historical replay:** every incident becomes a structural fixture; assertions target the class, not only the original string.
- **Semantic regression:** blinded/held-out, gold uncertainty and disagreement recorded; compare against competent final-text review at equal cost.
- **End to end:** one synthetic issue through correction, rollback, and public-byte reconciliation without live provider spend.

Golden tests are used only for deterministic artifacts or adjudicated semantic sets with versioned uncertainty. A failing or unavailable fixture is `ERROR/NOT_EVALUATED`, never skipped into a green headline.

## 11. CI/CD and release

Build an impact graph from package imports, declared runtime dependencies, prompts, policies, fixtures, schemas, migrations, builders, deployment config, and observed execution receipts. CI computes affected tests/artifacts/controls. A changed Signal wrapper, model, prompt, pricing table, shared policy, or dynamic module therefore selects WHU checks even when its path lacks “whatholdsup.”

Required checks: formatting/static analysis; unit/schema/property; integration; migration forward/backward or expand/contract checks; dependency closure; artifact reproducibility; incident replay; security/secret scan; release-policy evaluation. Model evaluations do not run on every commit: prompt/model changes run offline recorded sets and then shadow/canary gates under spend budgets.

Release uses build-once/promote-many. A signed manifest names all inputs and artifacts. Deploy does not mutate the manifest. Public-byte observation creates a deployment observation, not retroactive sign-off. Rollback promotes a previous manifest and creates a new deployment record. Emails require the deployed release ID and immutable payload hash; delivery is a separate provider state.

## 12. Security, privacy, and reproducibility

Use least-privilege service identities, secret manager injection, no secrets in receipts, encryption for payload/source blobs, role-based access, audit logs, and per-source licensing/privacy classification. Threat-model malicious documents, prompt injection, parser exploits, SSRF, oversized payloads, poisoned registries, and data exfiltration through model tools.

Pin libraries and container/runtime images. Record provider model resolution but admit nondeterminism: a run is reproducible as to inputs/config and replayable against stored output; it may not be behaviorally repeatable against a hosted model. A replay creates a new receipt and comparison, never overwrites the old result.

## 13. Definition of Done: professionally credible foundation

WHU meets the target foundation when:

1. 100% of new consequential objects are immutable/versioned and content-addressed where applicable.
2. 100% of required model calls and controls have reconstructable receipts, or publication is blocked with an explicit missing-receipt state.
3. Every aggregate reconciles attempted, eligible, evaluated, excluded, error, and reported populations.
4. Reviews and authorizations name exact subject/evidence/policy versions; mutation tests prove invalidation.
5. One release manifest binds pages, indexes, emails, build, deployment, and observed public bytes.
6. Corrections create versioned transactions and all known derivatives are invalidated and reconciled.
7. CI impact analysis catches shared-module, prompt, policy, fixture, config, and dynamic-dependency changes.
8. Historical incident classes pass structural regression and fault-injection suites.
9. Semantic controls publish measured incremental yield, disagreement, false assurance, human burden, cost, and evaluated population; unmeasured controls have no blocking authority.
10. Open-world outputs state search process and residual uncertainty and never claim global completeness.
11. Security/privacy/retention controls are documented, tested, and audited.
12. Two new issues plus one correction cycle complete under shadow comparison and production release with no unexplained state divergence.
