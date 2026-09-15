# Signal methodology page — every process claim beside the code that performs it

Rewritten 2026-09-15 (verification plan Phase 4, scoped to `MethodologyView.jsx`
only; the footer and the other marketing claims are not in this pass).
Rendered at `signal.civicscale.ai/methodology`.

## What the old page said that was not true, or not the method

| old claim | status |
|---|---|
| Weights: reproducibility 15%, consensus 15%, recency 15%, rigor 10% | **wrong** — `score_claims.py DEFAULT_WEIGHTS` is 0.20 / 0.15 / 0.10 / 0.10. Now rendered from a constant that `frontend/src/__tests__/methodology.test.js` compares to the Python file. |
| "Source Quality: evaluates the credibility and tier of the underlying source", with a 1–5 scale | **rewritten** — the score is a model's reading of the source's title, type label and date; the type label was itself model-written at discovery (`00_discover_sources.py`); nothing binds it to the fetched document. The page now says exactly that. Not bound to the document because the frozen corpus cannot be re-scored and a registry-derived tier would be a new pipeline, not a page edit. |
| Per-dimension five-level scales | **removed** — the rubric lives in `SCORE_SYSTEM_PROMPT`; reproducing it as if it were an instrument overstated it. One-line descriptions with the 5 and 1 anchors remain, matching the prompt. |
| "an AI model assesses the overall consensus status for each category" | **kept, qualified** — now states the written decision order, that the reading is not reproducible run to run, and that topic one was read once (`signal_consensus.runs` is NULL on all six mmr rows). |
| Nothing about what decides whether a claim is shown | **added** — the gates section. |
| "Source data is updated periodically" | **replaced** with the actual cadence and its consequence (marks, never un-publishes). |

## Every process claim on the new page → the code

| claim on the page | code that performs it |
|---|---|
| Each source's identifier is looked up in the registry that issues it (Crossref, Europe PMC, ClinicalTrials.gov) and the document retrieved | `backend/verify/literature.py` (`identify`, `resolve`, `fetch`), `backend/verify/generic.py` for URLs, run by `backend/verify/publish.py` |
| A source that resolves to nothing / to a different paper / cannot be retrieved is withheld; the record notes it with the reason | `verify/publish.py` (`survives`, `withheld_reason` on each source of the record); mmr record: 29 of 35 survived, 6 withheld for `fetch` |
| A claim's number must be in the fetched text of a cited source | `verify/bind.py bind_figure`; `verify/publish.py` support level `FIGURE_BOUND` / `UNSUPPORTED` |
| A quotation must be verbatim | `verify/bind.py bind_span`; `SPAN_BOUND` |
| A source cannot support a claim about an event after its date | `verify/chronology.py bind_chronology`; applied in `verify/publish.py` |
| Claims that fail are withheld from the page | `frontend/src/SignalApp.jsx` filters claims to `topic_publications.supported_claim_ids` |
| Claims with no figure and no quotation are shown, marked "Source identified; not checked against it"; the header counts them as claims that could not be matched against their sources (wording changed 2026-09-15 evening after the operator's read: "source confirmed" implied a check that did not happen) | `verify/publish.py` `IDENTITY_ONLY`; `RecordMarkers.jsx` (`support === "IDENTITY_ONLY"`, `TopicLine`) |
| Retraction / correction / expression of concern checked at publication | `verify/status.py check`, called from `verify/publish.py` |
| …and every week; monthly re-fetch and re-bind | `backend/scripts/recheck_topic.py --kind status` / `--kind bindings`; `.github/workflows/verify-gates.yml` (cron `0 12 * * 1` weekly, `0 11 1-7 * 1` monthly) |
| A change marks the page, never un-publishes it | `recheck_topic.py` docstring ("never edits the record, never flips status"); `RecordMarkers.jsx TopicLine` renders re-check flags |
| The record is frozen and displayed; markers come from it | `verify/publish.py store_publication` → `topic_publications`; `SignalApp.jsx` reads it; `RecordMarkers.jsx` |
| Plain summaries, consensus text, narrative and glossary are checked against the claims and sources they were given before storage; a summary that adds a number or an authority is not shown | `backend/scripts/signal/prose_gate.py`, wired in `score_claims.store_summaries`, `map_consensus.map_category`, `generate_summary.generate_narrative` / `generate_glossary`; rules in `backend/verify/policy.py` (`_PROSE` tiers) |
| A model assigns six integer scores 1–5 | `score_claims.py SCORE_SYSTEM_PROMPT`, `score_batch` |
| Composite is a weighted average computed in code | `score_claims.py` composite calculation ("deterministic Python, not Claude") with `DEFAULT_WEIGHTS` |
| Category thresholds Strong ≥ 4.0 / Moderate ≥ 3.0 / Mixed ≥ 2.0 / Weak | `score_claims.py EVIDENCE_CATEGORIES` |
| Scores rank and label; they never decide whether a claim is shown | showing is `supported_claim_ids` (above); scores are `signal_claim_composites` |
| Source quality is scored from title, type label and date; the label was model-written at discovery | `score_claims._build_batch_prompt` (title, source_type, publication_date); `00_discover_sources.py` writes `source_type` |
| Consensus: one status per category from a written decision order (debated / uncertain / consensus) | `map_consensus.py` consensus prompt (the ordered procedure, Session A7c) |
| The reading is not reproducible run to run | `map_consensus.py` R-01 note; `scripts/signal/golden_set.py` drift record (CLAUDE.md, Session ENG) |
| Can be run several times, modal status + agreement stored; topic one read once | `map_consensus.py --runs` (default 1), `reconcile()`; `signal_consensus.runs/agreement` (migration 074) — NULL on all six mmr rows |
| Debate arguments shown with the claims the model attributed | `signal_consensus.for_claim_ids/against_claim_ids` (migration 071); `IssueDashboard.jsx DebateItem / SideEvidence` |
| Checks do not establish that the right sources were chosen or that findings were fairly weighted | design doc §5a; "Not in scope" of the verification plan |

## Deliberately not on the page

`verify/policy.py`'s surface table, the string-literal lint, `db_posture()`, the
posture CI job: internal controls, not method. The reader is told what is
checked and what is scored, not how the repository enforces it.
