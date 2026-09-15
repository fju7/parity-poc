# Current-state reconstruction and control audit

## 1. Evidence and limits

This is a repository-grounded reconstruction, not a claim that every historical manual action is discoverable. It inspected the two pinned baselines named in the review index, current issue artifacts, publication code, hooks, workflows, tests, and the reliability-research incident corpus. Provider-side request logs, Vercel project settings, live database contents, local ignored source bytes, secret values, and every operator terminal action were not available. Where execution cannot be established, this report says so.

The current checkout contains roughly 60 WHU script modules and more than 600 files in the broad WHU-named/test/document/issue set. `publish.py` is about 4,800 lines and dynamically loads the shared Signal gate, the shared spend ledger, and more than two dozen WHU sibling modules. The system has grown by incident accretion: source comments repeatedly identify a historical failure and the control added for it.

## 2. Actual execution boundary

```text
research question / operator decision
  -> issue files + premise/design documents
  -> web/registry/search acquisition
       -> acquire_sources/find_access/source_store/source_ledger
       -> local content-addressed bytes + sources.json/access-routes.json
  -> drafting (human/model; not one orchestrated, receipt-complete service)
  -> mutable HTML/Markdown draft
  -> bindings/autobind/modelbind/spancheck + issue ledgers
  -> shared Signal factcheck_draft (dynamic path import)
       -> signal_model provider alias/settings
       -> Anthropic SDK + optional web search
       -> spend_ledger and pricing table
       -> prompt literals + fixtures + draft_decisions
  -> WHU deterministic/semantic controls loaded dynamically by publish.py
  -> outside-review packet/bundle -> human review -> Markdown adjudication
  -> publish preflight -> Git push -> Vercel watched branch
  -> live-byte polling/reconciliation -> published.json
  -> email parity/preflight -> Resend broadcast -> sent.json/snapshots
  -> generated homepage/issues/library/correction artifacts
  -> later sweeps/watch/corrections -> mutable derivatives and repeat gating
```

### Consequential dependencies outside WHU-named paths

| Dependency | Why it is in the boundary | Identity currently needed |
|---|---|---|
| `backend/scripts/signal/factcheck_draft.py` | Main model fact-check gate, imported by path | file hash, imported dependencies, prompt literals |
| `backend/scripts/signal/signal_model.py` | Model alias/config | file hash, provider-resolved model |
| `backend/scripts/spend_ledger.py` | Budget and cost enforcement | code hash, pricing table, ledger state |
| `backend/verify/*` and shared policies | Assertion extraction/policy used by related outputs | package tree hash, policy version |
| `backend/tests/fixtures/*` | Decisions, known errors, benchmark/golden behavior | fixture hashes and provenance |
| Git index, working tree, history, hooks | Inputs, historical lookup, precommit/prepush enforcement | commit/tree/blob hashes, dirty state, installed hook hash |
| GitHub Actions | CI and path triggers | workflow hashes and event/required-check config |
| Vercel | Build/deploy and live bytes | project/config/build/deployment IDs, public hash |
| Anthropic/web-search provider | Model and retrieval execution | provider request ID, resolved model, settings, response |
| Registries/live web | Fresh external facts and source acquisition | URL/query, timestamp, response hash/status |
| Resend | Subscriber email delivery | payload hash, audience, provider message/broadcast ID |
| Local environment | Secrets, timezone, dependencies, ignored sources | redacted config digest, lock/image/runtime identity |

## 3. Current lifecycle and state inventory

There is no single state machine. The following states exist across file presence, fields, prose, hashes, and conventions.

| Object or concern | Current representations | Principal ambiguity |
|---|---|---|
| Research issue | directory, HTML, `issue.json`, premise/design, register row | no authoritative versioned aggregate |
| Source | URL rows, source IDs, local bytes, access routes, ledger prose | discovered/fetched/opened/read/supplied/support are not one transition system |
| Evidence | source span, locator, quotation, figure, registry fact | exact evaluator-visible payload is often not recorded |
| Claim/proposition | prose sentence, extracted gate claim, binding row, finding text | identity across transformations is heuristic |
| Evaluation | gate JSON, run archive, findings, decisions | exact input/version/population and execution error are inconsistent |
| Review | sent HTML, Markdown review, reviews ledger, adjudication | review authority can outlive reviewed bytes |
| Correction | page text, `corrections.md`, errata, changes/deletions/findings files | no atomic propagation to every derivative |
| Publication | mutable site file + `published.json` action rows | sign-off, Git state, build, deploy, observation are separate facts |
| Email | HTML/text, gate files, sent snapshots, send record | page/email authority and delivery state can diverge |
| Control | module/function returning row tuples | execution, partial/error/stale/liveness semantics are not uniform |

### Conflations observed or structurally permitted

- Source availability can stand in for source supply; source supply can stand in for consideration.
- A span being present can be read socially as a claim being supported.
- A gate report can be about extracted/paraphrased claims rather than the consequential sentence.
- A reviewed predecessor can lend authority to a modified page.
- Missing or caught exceptions often become warning rows rather than a typed `ERROR`.
- “Warn” can mean stale, incomplete, exhausted budget, accepted blocking findings, failed check execution, or advisory concern.
- Repository sign-off, deployment success, and observed reader bytes are distinct but are reconstructed through action rows and live probes.
- Aggregates do not universally carry attempted/eligible/evaluated/excluded/error/reported populations.

## 4. Execution identity required versus present

The minimum identity for a consequential run is:

```text
repository commit + tree + dirty/blob identities
entry point + argv + caller
resolved dynamic module absolute paths + content hashes
runtime/dependency image or lock hash
prompt/template/policy/fixture hashes
source/evidence object versions and evaluator-visible payload hashes
provider + requested model + resolved model + settings
redacted environment/config digest
execution ID + attempt/retry lineage
build ID + deployment ID + public-byte hash
```

The current system records subsets in different outputs. It does not create one immutable execution manifest that proves closure over these dependencies. A commit SHA therefore cannot by itself identify “the WHU that ran.”

## 5. Historical failure to architecture matrix

| Failure family | Immediate manifestation | Architectural enabler | Expected catcher / why it failed | Professional prevention | Scope |
|---|---|---|---|---|---|
| Wrong-version review | reviewer saw predecessor or transformed object | no immutable object/version authority | review record not bound to all published bytes/claims | content-addressed versions and authorization foreign key | architectural |
| Stale derived page/index/email | upstream changed, derivative did not | no complete dependency graph/transaction | path-specific checks or manual regeneration | invalidation graph plus release manifest | architectural |
| Control failed but appeared acceptable | exception/missing run became warning/default | three-value result and catch-all adapters | display showed a row, not execution semantics | typed execution/evaluation state; ERROR non-pass | architectural |
| Missing execution evidence | model call/result could not be reconstructed | no mandatory receipt boundary | logs/spend output partial or overwritten | append-only call receipt before authority | architectural |
| Unknown cost became zero | missing price coerced | numeric field doubled as epistemic state | spend ledger accepted numeric default | nullable amount + `UNKNOWN_PRICE`; hard refusal/override | conventional, fixed locally but class persists |
| Dropped items/denominator drift | 8/9 evaluated but clean result | population not a first-class object | aggregate saw survivors | population manifests and reconciliation invariant | architectural |
| Source acquired but not read/supplied | URL/source row existed | access states not connected to evaluator payload | later controls inferred from store metadata | separate acquisition, parsing, supply, consideration attestations | architectural |
| Span true, proposition false | binding found matching text | prose-first binding; span is wrong primitive for semantics | span checks correctly answered narrow question | proposition-first structure + explicit semantic relation judgment | target design + irreducible judgment |
| Correction introduced error | editing bypassed original research path | correction is mutation, not a versioned research transaction | partial checks focused on changed text | correction as new version with full impact closure | architectural |
| Dynamic dependency skipped by CI | shared Signal changed, WHU tests not selected | filename/path trigger model | hook/workflow looked for WHU names | declared dependency graph + impact test | conventional |
| Deployment mismatch | repo record differed from live bytes | Git push treated as publication proxy | post-hoc live checks and action vocabulary drift | immutable release and deployment records, reconciliation | architectural |
| Correlated reviewers | repeated model roles share inputs/model | “multiple” confused with independence | same representation and ancestry | sealed judgments, ancestry disclosure, disagreement | semantic/control design |
| Open-world overclaim | local support became “no counterevidence” | no knowable global denominator | syntax/search heuristics cannot prove absence | registered search process + residual uncertainty | irreducible open-world boundary |

## 6. Control inventory and disposition

This inventory groups controls by contract; treating every preflight row as an independent control would exaggerate independence. Dispositions are for migration, not instructions to delete current safeguards before replacement.

| Control/group | Exact useful claim | Kind / authority | Current main failure mode | Disposition |
|---|---|---|---|---|
| Source store/content hash | named bytes are held and hashable | deterministic/blocking | local/ignored availability; “held” may imply read | KEEP, move into core |
| Source ledger/access states | declared access state exists | mechanical record | human-read claim not execution-proven | FIX |
| Spancheck/bindings | normalized span occurs in named held bytes | deterministic/blocking | presence mistaken for entailment; parser blind spots | KEEP, rename narrowly |
| Quotations | quoted string matches source | deterministic/blocking | context/attribution not established | KEEP |
| Figure provenance/B13 | figure appears in held corpus | deterministic/blocking | corpus/parser coverage and wrong subject | SIMPLIFY/MERGE |
| Furniture/self-consistency | generated page elements agree locally | deterministic/blocking | many format-specific rules | MERGE into artifact validation |
| Registry figures/facts/settle/sweep | selected structured fields agree with queried snapshot | mixed/blocking | live dependency, age, field coverage | MERGE with source adapter + receipt |
| Errata lookup | registered errata query ran/result recorded | mixed | search completeness and liveness | FIX |
| Page-to-ledger reconciliation | links/bindings/source list reconcile | deterministic/blocking | multiple ledgers remain canonical | KEEP during migration; retire after canonical DB |
| Sources shown | reader-visible list includes bound sources | deterministic/blocking | says nothing about adequacy | KEEP |
| Coverage report | reports what checks examined | deterministic/informational | denominator may itself be incomplete | FIX with population objects |
| Canary/parser reachability | selected held formats are readable | deterministic/blocking | sample canary does not prove all payloads | KEEP, expand contract tests |
| Unjudged/changecheck | changed text lacks current evaluation | mixed/blocking | sentence matching; short text can drop | REPLACE with version invalidation |
| Corrections/deletions/findings checks | correction/removal has recorded basis | mixed/blocking | fragmented records and semantic scope | REPLACE with correction transaction |
| Negatives/counterexample | adversarial search found/failed to find contradictions | semantic/model/blocking or warning | cannot establish global absence; provider correlation | SHADOW; never completeness authority |
| Source advocate/inherited claims | source perspective/scope challenged | semantic/model | same-model/common-representation risk | SHADOW, measure incremental yield |
| Premise/rubric/epistemic | structured editorial judgments exist | semantic | stored judgment may look mechanical | KEEP as explicit judgment, not gate fact |
| Shared Signal fact-check roles | model returned findings on submitted draft | semantic/blocking after adjudication | paraphrase, truncation, common-mode, poor receipt closure | SHADOW as triage; remove direct authority |
| Gate acceptance/waiver | named human accepts residual findings | governance/blocking override | acceptance can obscure error or stale scope | FIX: scoped, expiring, version-bound waiver |
| Outside review packet | named reviewer received a packet | human/semantic | packet may not equal released object; burden | KEEP, make primary, bind exact versions |
| Review/adjudication Markdown | decisions and rationales are preserved | human/governance | free-form parsing and ambiguous applicability | FIX into structured decision + narrative |
| Benchmark/recall fixtures | known cases replay | test | source bytes absent; overfit; gold errors | FIX; hermetic + held-out partitions |
| Precommit hook | WHU-named changes run tests locally | deterministic/advisory | installation/bypass/path miss/shared deps | REMOVE as authority; retain convenience |
| Prepush guard | changed published pages are checked | deterministic/local block | bypassable, deploy branch assumptions, path closure | REPLACE with required CI release check |
| Publish preflight | aggregates numerous rows | mixed/blocking | monolith, catch-and-warn, overloaded state | REBUILD, do not port wholesale |
| Live-byte comparison | public bytes match expected bytes | deterministic/blocking/reconcile | cache/outage and no build identity | KEEP with deployment receipt |
| Email parity/send gate | email figures/content relate to page and send recorded | deterministic/mixed | lossy parity rules; external delivery gap | FIX under release manifest |
| Index/date/issues generators | derived views align with issue state | deterministic | manual regeneration/stale derivatives | REPLACE with pure builds from manifest |
| Spend ledger/cap | priced calls are recorded/capped | deterministic | wrappers incomplete; price/provider drift | FIX at one mandatory gateway |
| Watch/sweeps/reachability | selected external facts/URLs rechecked | monitoring | absence of run and partial failure visibility | KEEP as scheduled jobs with receipts |
| Dashboard/board | projects file state for operator | presentation | projection can become alternate authority | REBUILD as read-only event projection |

### Controls to delete or demote in the target

Delete duplicated figure/string checks after equivalence measurement; replace free-form file parsers with canonical records; remove local hooks from the assurance case; remove any semantic “verified” badge produced solely by models; remove warning-as-success behavior; remove automatically generated assurance prose that says more than a typed contract; demote broad counterexample/search controls to evidence-producing shadow work until incremental value and false assurance are measured.

## 7. Professional-standard gap analysis

| Area | Current WHU | Professional target | Gap |
|---|---|---|---|
| Architecture | script/file mesh centered on monolithic publisher | small services/modules around canonical event/state core | CRITICAL |
| Data model | HTML/JSON/Markdown jointly encode truth and workflow | immutable normalized objects + projections | CRITICAL |
| State management | ad hoc booleans/strings/absence/warnings | typed state machines, legal transitions | CRITICAL |
| Provenance | substantial local records, incomplete closure | end-to-end version/evidence/execution lineage | HIGH |
| Observability | comments, files, partial spend/run logs | mandatory receipts and correlated traces | CRITICAL |
| Testing | many incident regressions; non-hermetic benchmark; few system properties | pyramid, properties, fault injection, hermetic replay | HIGH |
| CI/CD | sparse workflows and name/path triggers; local hooks | dependency-impact CI, required release/deploy checks | CRITICAL |
| Model lifecycle | aliases/prompts embedded across scripts | one gateway, registry, eval and rollout policy | HIGH |
| Prompt/config lifecycle | code literals and fixtures, uneven hashes | versioned artifacts in execution manifests | HIGH |
| Failure handling | exceptions sometimes warning; overloaded `warn` | ERROR/PARTIAL/STALE/WAIVED explicit and non-pass | CRITICAL |
| Deployment | Git/Vercel/live state reconciled through records/probes | signed build/release/deployment manifest | CRITICAL |
| Corrections | edits plus several side ledgers/checks | first-class correction transaction and invalidation | CRITICAL |
| Human review | valuable but packet/version linkage incomplete | exact-object workbench and structured decisions | HIGH |
| Documentation | rich incident commentary, distributed authority | generated system spec + ADRs + runbooks | MEDIUM |
| Security/privacy | secrets mostly env-based; receipt policy absent | classified data, retention, redaction, access audit | HIGH |
| Reproducibility | partial hashes and snapshots | reproducible inputs/config; nondeterminism declared | HIGH |

## 8. Why local repair is no longer the safest option

The current implementation contains good code and hard-won knowledge. That does not make its orchestration salvageable at lower risk. To add canonical identity, transactional state, uniform errors, dependency invalidation, population accounting, and release manifests in place would require changing nearly every control adapter and the 4,800-line publication authority simultaneously. Its behavioral compatibility surface is undocumented and partly encoded in historical files. A clean core can ingest those artifacts as evidence without inheriting their control flow. That gives the team a comparator, a rollback path, and a way to decline migration of controls that fail to show incremental value.
