# Adversarial review of the target architecture

## Method and result

The proposed target was attacked as if it were already the next source of false assurance. An attack “survives” when the design needs a mitigation, limitation, or staged proof; “contained” means a stated invariant directly blocks or exposes it. No attack is evidence of efficacy by itself.

The strongest objection is that a much simpler system—immutable source folders, a competent editor, two independent reviewers, and a static-site release checklist—could be safer than a new data platform. This objection is partly right. The target was therefore reduced to a modular monolith, relational database, blob store, outbox, adapters, and release manifest. The semantic control stack remains optional/shadow. The clean core is justified only by the failures that a checklist cannot reliably solve: exact version authority, population accounting, execution receipts, dependency invalidation, atomic correction propagation, and build/deployment reconciliation.

## 60 attacks

| # | Attack | What could go wrong | Required containment / verdict |
|---:|---|---|---|
| 1 | Unnecessary complexity | New core adds more failure surface than files | stage components; architecture budget; compare to simple baseline. Survives as program risk. |
| 2 | Overengineered provenance | Team logs everything and reviews nothing | minimum receipt fields; measure reconstruction use; tier payload retention. Contained by scope, not eliminated. |
| 3 | False assurance from lineage | Perfect ancestry is mistaken for truth | separate mechanical and semantic schemas/UI; prohibit “verified.” Contained contractually. |
| 4 | State explosion | Operators cannot distinguish dozens of states | keep orthogonal execution/coverage/verdict axes; user views summarize without coercion. Needs UX test. |
| 5 | Semantics disguised as types | `SUPPORTS` looks deterministic | evaluator/task/confidence/rationale mandatory; type is a judgment record. Contained if UI complies. |
| 6 | Excessive storage | payload/source retention becomes unaffordable | content dedup, tiering, retention, byte budgets. Survives; measure. |
| 7 | Performance | dependency traversal and hashing delay work | transactional direct edges, indexed closure for release only; benchmark. Low risk at WHU scale. |
| 8 | Privacy | receipts persist personal/private source text | classification, encryption, RBAC, redaction receipts, deletion tombstones. High residual risk. |
| 9 | Provider nondeterminism | same manifest cannot reproduce response | preserve exact output; call replay a comparison, not reproduction. Limitation explicit. |
| 10 | Stale dependency | edge exists but downstream state is not invalidated | same-transaction invalidation/outbox and property tests. Contained for known edges. |
| 11 | Incomplete dependency graph | unknown consumer stays current | expected-consumer manifest + runtime observed edges + incomplete-closure non-pass. Residual risk remains. |
| 12 | Partial database write | object saved but invalidation missing | one DB transaction; outbox for external effects. Contained. |
| 13 | Blob/DB split write | DB references missing blob | stage/upload hash, verify, then commit reference; orphan sweeper. Contained with tests. |
| 14 | Split brain | old and new cores both authorize release | one release authority per environment; shadow cannot sign. Cutover flag itself audited. |
| 15 | Retry after timeout | provider charged/responded but client retries | attempt IDs and `OUTCOME_UNKNOWN`; reconcile before retry where possible. Residual provider limitation. |
| 16 | Concurrency | two edits derive from same parent | optimistic version check; both children preserved, merge is explicit. Contained. |
| 17 | Idempotency collision | same key used for different payload | bind key to payload hash; mismatch hard error. Contained. |
| 18 | Duplicate email | retry sends twice | immutable payload + provider/idempotency key + uncertain send state. Residual if provider lacks support. |
| 19 | Schema migration | migration changes meaning of old verdicts | expand/contract; schema version; no in-place semantic reinterpretation. Contained by policy/testing. |
| 20 | Old-data migration | missing lineage is inferred and treated as fact | `LEGACY_PARTIAL/AMBIGUOUS`; field-level provenance; no completeness claim. Contained. |
| 21 | Correction propagation | a derivative outside graph is missed | consumer registry, observed deploy/email edges, reconciliation. Residual unknown-consumer risk. |
| 22 | Deployment mismatch | provider reports success but serves wrong bytes | public-byte observation tied to deployment; mismatch non-pass. Contained after observable endpoint. |
| 23 | CDN/cache divergence | different readers see different bytes | multi-probe sampling and cache headers; cannot prove every reader. Report scope. |
| 24 | Missing source | release depends on unavailable bytes | required source blob/rights state blocks; optional source explicit. Contained. |
| 25 | Missing receipt | result exists without execution evidence | authority FK requires receipt; import as partial only. Contained. |
| 26 | Model outage | mandatory semantic job blocks indefinitely | queue/backoff, human alternative, explicit unavailable state; never pass. Availability tradeoff survives. |
| 27 | Reviewer disagreement | workflow forces consensus and erases minority | preserve sealed judgments and disagreement; authorization policy names resolver. Contained. |
| 28 | Unavailable human | publication stalls | risk-tier queues, substitute qualified reviewer, explicit deferral/waiver; measure delay. Not eliminated. |
| 29 | Unknown model cost | amount becomes zero in totals | price state separate; aggregate counts unknown; default refusal. Contained. |
| 30 | CI trigger failure | shared change misses relevant tests | dependency graph + observed runtime edges + periodic full suite. Residual edge risk. |
| 31 | Prompt change | semantic behavior changes without code change | prompt as versioned dependency; offline eval + shadow. Contained procedurally. |
| 32 | Model change/alias drift | provider resolves alias differently | requested and resolved model in receipt; unapproved resolution blocks authority. Provider may not disclose fully. |
| 33 | Dynamic import | code loaded by path escapes impact analysis | resolved absolute path/hash in manifest; undeclared runtime edge fails CI/release. Contained when executed. |
| 34 | Failed build | partial artifacts reach deploy | atomic build produces manifest only on complete success. Contained. |
| 35 | Failed deployment | record says released but live is old | separate BUILT/DEPLOYING/DEPLOYED/OBSERVED states. Contained. |
| 36 | Rollback | old release restores stale evidence silently | rollback is new deployment of old manifest; UI states evidence cutoff; later corrections remain obligations. Needs policy. |
| 37 | Control heartbeat failure | absence is interpreted as no findings | expected-control manifest; absent receipt is missing/error. Contained. |
| 38 | Control output missing | execution complete but blob absent | receipt completion requires output hash or explicit no-output contract. Contained. |
| 39 | Invalidated review | UI still highlights old approval | current projection excludes invalidated authorization but history visible. Contained. |
| 40 | Open-world incompleteness | search process badge reads as exhaustive | ban COMPLETE outside closed corpus; residual-risk language. Human overinterpretation remains. |
| 41 | Source licensing | immutable storage violates rights | rights classification, restricted storage/pointers, deletion tombstone; legal review needed. High residual. |
| 42 | Malicious source | prompt injection redirects model/tools | treat sources as data; isolate instructions; tool/egress allowlists; adversarial tests. Residual model risk. |
| 43 | Parser exploit | hostile PDF/HTML compromises worker | sandbox parsers, limits, malware scanning, no credentials. Contained operationally. |
| 44 | Context truncation | receipt proves payload but omitted tail matters | tokenizer-aware size accounting, truncation state, population of excluded segments, non-pass where required. Contained if contracts define required context. |
| 45 | Representation loss | parsed text drops tables/footnotes | originals retained, transform diagnostics, format corpus, semantic reviewer sees loss flags. Residual adapter risk. |
| 46 | Correlated model reviewers | multiple roles share blind spot | ancestry/evidence-path logging; sealed heterogeneous review; do not count roles as independence. Measurement required. |
| 47 | Deterministic proxy overclaim | hash/schema check becomes “supported” | separate result schema and label lint; user-facing claim contract. Contained technically, cultural risk remains. |
| 48 | Test oracle failure | tests encode wrong expected behavior | versioned adjudication, challenge path, negative controls, independent review. Residual unavoidable. |
| 49 | Golden-set error | wrong labels block good changes | uncertainty/disagreement; never sole release gate until validated; re-adjudication. Contained by authority limits. |
| 50 | Historical overfitting | system catches only known incidents | structural mutations, held-out cases, prospective measurement. Measurement required. |
| 51 | Excessive human burden | reviewers face every minor edit | validated warrant-preserving transforms, risk tiers, sampled audit; track minutes. Survives until measured. |
| 52 | Recursive controls | a control requires controls on its own prose/results | control outputs are structured data; only release-facing prose gets ordinary review; no infinite assurance chain. Contained by stopping rule. |
| 53 | Provider execution unreproducible | request receipt cannot prove server internals | terminology limited to submitted SDK payload/provider response; do not claim wire/server execution. Explicit limitation. |
| 54 | Search adapter drops result blocks | verdict persists without acquired evidence | population reconciliation and representation requirements; missing evidence makes partial. Contained. |
| 55 | Wrong consequential unit | proposition granularity is selected to make checks pass | preserve original sentence/context; human can split/merge with recorded rationale; no perfect mechanical solution. Residual semantic risk. |
| 56 | Cosmetic edits trigger rereview storm | byte versions invalidate harmless changes | artifact/proposition separation; enumerated lossless transforms; audit exceptions. Contained after validation. |
| 57 | “Materiality” model becomes oracle | classifier silently authorizes edits | classifier only routes; uncertain/positive requires human; sample false negatives. Contained by no sole authority. |
| 58 | Emergency waiver becomes loophole | deadlines normalize bypass | exact scope, signer, reason, expiry, visible release flag, rate alert, retrospective review. Governance risk remains. |
| 59 | Metrics are gamed | team optimizes receipt rate, not reliability | pair process metrics with escaped defects, false assurance, burden, and audits; no single KPI. Residual organizational risk. |
| 60 | Simpler architecture is safer | human/editor/static site avoids platform bugs | keep target minimal; require each stage to beat simple comparator; abandon components without net value. This attack materially changed the target. |

## Decision after attack

The target survives only as a **minimal clean core with staged authority**. It does not justify a comprehensive provenance platform or automated semantic verification system. The following constraints are conditions of approval:

1. No microservice/event-stream/graph-database expansion without demonstrated scale need.
2. Model and search controls remain shadow until prospective incremental value is measured.
3. The simple comparator—competent final review plus immutable release checklist—must be evaluated at equal cost.
4. Unknown dependency closure, missing receipts, and partial populations are explicit non-pass states.
5. Privacy/licensing review precedes full payload retention.
6. Cutover requires two issues and a correction cycle, not a feature-completeness assertion.

With those constraints, clean-core migration remains safer than further incident-driven growth inside the incumbent.
