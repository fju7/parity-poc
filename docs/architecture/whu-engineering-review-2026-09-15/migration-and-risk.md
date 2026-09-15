# Migration strategy, alternatives, and risk register

## 1. Repair versus refactor versus rebuild

| Option | Strength | Fatal concern | Recommendation |
|---|---|---|---|
| Incremental repair | lowest immediate disruption; preserves every behavior | foundational changes touch most adapters; no clean comparator; continues accidental state model | Reject as destination; allow only containment fixes |
| Major in-place refactor | can reuse code and data | rollback is difficult; old/new authority coexist inside same monolith; test oracle is current behavior | Reject as primary path |
| Clean rebuild | clear architecture and state model | migration, feature parity temptation, dual-system burden | Use for core, not big-bang product rewrite |
| Hybrid clean core + adapters | preserves evidence/history and selected validators; supports shadowing/cutover | temporary duplication and reconciliation work | **Recommended** |

The selected disposition is `CLEAN_CORE_REBUILD_RECOMMENDED`. “Clean” applies to the core identity/state/release authority. It does not mean discard validated assets or rewrite the site all at once.

## 2. What to preserve

Preserve immutably: original source bytes where lawful, source metadata/access records, published/sent artifact snapshots, bindings and quoted spans, gate reports, reviews/adjudications, correction history, incident and benchmark cases, publication/deployment observations, spend history, and narrow validators that pass contract tests. Preserve provenance about uncertainty during import.

Do not automatically port: the `publish.py` orchestration, free-form file parsing as authority, three-state row vocabulary, locally installed hooks as controls, duplicated figure/string controls, model verdicts labeled verification, or current path-based CI selection.

## 3. Staged roadmap

### Stage 0 — Freeze the assurance claim

**Objective:** stop architectural expansion while retaining production service.  
**Affected:** process/docs only.  
**Invariants:** no new control claims without contract, owner, population, liveness, and test; failures are reported with denominators.  
**Retire:** none.  
**Compatibility:** incumbent stays authoritative.  
**Tests:** baseline suite and inventory snapshots.  
**Shadow:** none.  
**Success:** control catalogue frozen; all new exceptions documented.  
**Rollback:** not applicable. **Risk:** low.

### Stage 1 — Execution identity and receipts

**Objective:** make consequential model/control executions reconstructable.  
**Affected:** new model gateway adapter, receipt DB/blob schema; incumbent call sites dual-write through compatibility wrappers.  
**Invariants:** receipt required before result gains authority; unknown cost nonzero/explicit.  
**Retire:** direct provider calls only after coverage.  
**Backfill:** import historical metadata as `LEGACY_PARTIAL`, never fabricate payloads.  
**Tests:** timeouts, retries, missing price, sensitive redaction, provider ID absence.  
**Shadow:** compare call outputs/spend; no gating.  
**Success:** ≥99.5% new consequential calls have complete required receipts for 30 days; no secret incident.  
**Rollback:** bypass payload retention but retain mandatory minimal receipt and explicit partial state. **Risk:** medium.

### Stage 2 — Canonical versions and populations

**Objective:** establish immutable proposition/source/representation/population identities.  
**Affected:** importer, object store, version APIs, workbench read views.  
**Invariants:** no in-place mutation; every evaluation names subject and population.  
**Retire:** none; files are imported as legacy projections.  
**Backfill:** content-hash existing artifacts; ambiguous identities remain unresolved.  
**Tests:** duplicate/hash collision handling, short/truncated sentences, 8-of-9 populations.  
**Shadow:** reconcile new IDs with current page/binding/gate objects.  
**Success:** 100% of shadow issue release-candidate claims and sources addressed by exact version; unexplained population delta zero.  
**Rollback:** stop import, preserve append-only records. **Risk:** high.

### Stage 3 — Typed state and dependency invalidation

**Objective:** eliminate error/pass laundering and stale inheritance.  
**Affected:** state engine, dependency edges, compatibility projection to current rows.  
**Invariants:** ERROR/PARTIAL/STALE non-pass; upstream change invalidates reachable downstream objects.  
**Retire:** no new uses of `ok/warn/BLOCKED` in core.  
**Backfill:** map legacy states with explicit confidence and `LEGACY_AMBIGUOUS`.  
**Tests:** exhaustive state algebra, randomized DAGs, partial transaction/outbox.  
**Shadow:** report divergences without blocking.  
**Success:** historical stale-state incidents detected; false invalidation burden below agreed threshold.  
**Rollback:** disable auto-blocking, never erase stale markers. **Risk:** high.

### Stage 4 — Release manifest and deployment reconciliation

**Objective:** bind publication, derivatives, build, deploy, email, and public bytes.  
**Affected:** pure builders, manifest signer, Vercel/Resend adapters.  
**Invariants:** build once; every artifact is in manifest; deploy and observe are separate.  
**Retire:** direct Git-push-as-publication authority, after shadow.  
**Backfill:** historical releases marked partial with known bytes/actions.  
**Tests:** failed build/deploy, split brain, cache mismatch, rollback, duplicate email.  
**Shadow:** build current issue both ways; byte/semantic diff.  
**Success:** two releases with zero unexplained artifact difference and public reconciliation.  
**Rollback:** promote prior manifest; incumbent remains available. **Risk:** high.

### Stage 5 — Correction transactions and human workbench

**Objective:** make corrections first-class and review exact objects.  
**Affected:** correction workflow, review UI, authorization.  
**Invariants:** correction creates versions; all dependents invalidated; review names exact versions.  
**Retire:** free-form adjudication parsing as authority; Markdown retained as narrative/export.  
**Backfill:** link only high-confidence historical corrections; leave unresolved edges visible.  
**Tests:** correction adds/removes/changes scope; unavailable reviewer; disagreement; partial propagation.  
**Shadow:** one full correction cycle in both systems.  
**Success:** all known consumers reconciled; reviewer can trace originals and transformations; measured burden acceptable.  
**Rollback:** export structured decision to incumbent artifacts; do not discard versions. **Risk:** medium-high.

### Stage 6 — Control simplification and semantic shadow trials

**Objective:** retain the smallest measured control set.  
**Affected:** control runner, benchmarks, model triage, review process.  
**Invariants:** every control declares exact contract/population and cannot exceed authority scope.  
**Retire:** duplicates/no-yield controls after ablation; model gate loses direct “verified” authority.  
**Tests:** held-out semantic sets, false assurance, mutation, common-mode analysis.  
**Shadow:** claim-support, independent-first review, counterevidence lane separately.  
**Success:** incremental consequential catches per hour/dollar over competent final review; bounded false blocks and burden.  
**Rollback:** demote/disable individual control; core state unaffected. **Risk:** medium.

### Stage 7 — New-issue cutover and old-engine retirement

**Objective:** make clean core authoritative for new issues.  
**Affected:** all new research runs; old issues remain readable legacy imports until touched.  
**Invariants:** Definition of Done in target report.  
**Retire:** incumbent orchestration after two issues and one correction cycle, incident replay, disaster recovery exercise, and owner approval.  
**Compatibility:** legacy pages remain deployable from last signed manifest.  
**Tests:** full synthetic and real shadow E2E.  
**Success:** no unexplained state divergence, complete receipts/populations/manifests, acceptable latency/burden.  
**Rollback:** promote last incumbent release manifest and pause new runs. **Risk:** high but bounded.

## 4. Risk register

| Risk | Likelihood / impact | Detection | Mitigation / owner action |
|---|---|---|---|
| New core becomes a giant ontology | M/H | schema growth, low field use | architecture budget; require lifecycle/invariant for each type |
| Dependency graph incomplete | H/H | reconciliation misses, incident replay | expected-consumer manifests, runtime observed edges, fail incomplete |
| Dual systems disagree | H/M | scheduled reconciliation | new core shadow only until divergence adjudicated |
| Migration fabricates certainty | M/H | imported records look complete | `LEGACY_PARTIAL/AMBIGUOUS`, field-level provenance |
| Receipts expose private/licensed data | M/H | privacy audit/DLP | encryption, RBAC, minimization, retention, lawful source policy |
| Storage/cost grows sharply | M/M | per-run byte/cost metrics | tier payloads; deduplicate blobs; retain hashes/metadata |
| Provider nondeterminism defeats replay | H/M | replay deltas | define reproducibility as input/config/output preservation, not identical rerun |
| Model gateway outage blocks all calls | M/H | SLO/alerts | explicit queue, retry policy, alternate provider only by new config/version |
| Retry double-spends or duplicates effects | M/H | idempotency reconciliation | attempt IDs, idempotency keys, uncertain-outcome state |
| Human review becomes bottleneck | H/H | queue age/minutes | prioritize consequential claims; abstention; measured sampling; staffing |
| Humans automate-bias to model output | M/H | order/disagreement metrics | sealed initial judgment; show originals first |
| Semantic diff misses material change | M/H | blinded audit | never sole authority; conservative review on uncertainty |
| False invalidations make system unusable | M/M | invalidations per edit/time | typed edge classes, pure cosmetic transforms, scoped overrides |
| Waivers become normal path | M/H | waiver rate/age | owner, reason, exact scope, expiry, review; release dashboards |
| Old data cannot be linked | H/M | unresolved import report | accept unresolved history; do not block new core on perfect backfill |
| Build/deploy split brain | M/H | manifest/public hash monitor | build once, immutable release, rollback drill |
| Email sends twice | L/H | provider/idempotency receipt | immutable payload and send idempotency key; separate prepared/sent/delivered |
| Source parser loses context | H/H | transform loss flags/canaries | originals alongside representations; adapter contract corpus |
| Malicious source prompt-injects model | M/H | adversarial fixtures | isolate source data from instructions; tool allowlists; egress controls |
| Open-world process still overclaims | H/H | language policy audit | no COMPLETE; bounded scope/residual-risk templates and human review |
| Controls share common-mode failures | H/M | ancestry/overlap metrics | structural diversity; sealed judgments; ablation |
| Gold set is wrong | M/H | disagreement/re-adjudication | versioned labels, multiple adjudicators, uncertainty, challenge process |
| CI impact graph misses dynamic edge | M/H | runtime receipt undeclared-edge check | declared + observed dependencies; full periodic suite |
| Database migration corrupts authority | L/H | checksum/constraint audit | expand-contract, backups, shadow readers, rollback rehearsal |
| Event/outbox partial write | L/H | invariant reconciliation | same-transaction outbox, idempotent consumers |
| Operator bypasses gate under pressure | M/H | immutable waiver/identity audit | no hidden bypass; scoped signed emergency path; retrospective review |
| Clean rebuild never ships | M/H | milestone aging | narrow stages; first deliver receipts/manifests, not feature parity |

## 5. Success measures

Foundation measures are not “number of controls.” Track:

- receipt completeness and reconstruction success;
- stale/invalidated dependents and time to resolution;
- population reconciliation errors;
- state coercion violations;
- deployment/public mismatch duration;
- correction propagation completion;
- consequential defects caught before publication, by layer;
- induced errors and false assurance attributable to controls;
- model spend with unknown-cost population;
- human minutes, wait time, disagreement, override rate;
- semantic control incremental yield over simple final-output review;
- security/privacy incidents and retained bytes.

## 6. Immediate next decision

Authorize only Stage 0 and a design spike for Stage 1 after reviewing this report. Do not authorize the entire rebuild as one project. The first implementation proposal should contain the receipt schema, threat model, compatibility wrapper, failure-injection plan, and rollback criteria; it should not change publication authority.
