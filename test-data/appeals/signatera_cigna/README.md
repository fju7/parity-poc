# Signatera / Cigna appeal fixture

The locked, **de-identified** regression fixture for the Parity Health appeal
enhancement. Every future phase (PH-3 PubMed/CMS evidence retrieval, PH-4 package
assembler, …) is scored against this same fixture so progress is measured, not eyeballed.

## Source case
A real Cigna / eviCore **prior-authorization** denial of **CPT 0340U** (Signatera
molecular-residual-disease plasma test) as **Experimental / Investigational / Unproven**
under payer guideline **MOL.CU.117**. All PII is replaced with synthetic values
(Jane A. Doe / 123 Main St / MEMBER-TEST-001 / CLAIM-TEST-0340U). Clinical facts, codes,
payer/eviCore names, public submission addresses, and phone/fax numbers are preserved.

## Files
| File | Purpose |
|---|---|
| `denial_source.txt` | De-identified denial text — input to `analyze-denial` |
| `expected_extraction.json` | Golden Phase-1 extraction (the scored target) |
| `baseline_appeal.md` | The pre-PH-1 leaky letter — the documented "before" baseline to beat |
| `assertions.md` | Human-readable, phase-tagged assertions |
| `README.md` | This file |

## Running the eval

**Deterministic suite** (no model call, CI-safe — validators + letter cleanup):
```
cd backend && python3 -m pytest tests/test_signatera_fixture.py -v
```

**Live extraction eval** (calls the deployed API; on-demand, scores model drift):
```
cd backend && python3 -m pytest tests/test_signatera_fixture.py -m eval -v -s
```
The eval prints a per-field pass/fail table and a `matched/total` score, and asserts a
perfect score on the locked structured fields. It is excluded from default runs via
`addopts = -m "not eval"` in `backend/pytest.ini`, so live-model flakiness never breaks CI.

## The scoring rule for every future phase
Add new `@pytest.mark.eval` cases here, scored the same `fields_matched / fields_total`
way, so each phase reports a single reproducible number against this fixture. Keep the
deterministic suite green at all times; the eval score is the phase-over-phase metric.

## PH-1 before → after (what the harness locks in)
| Metric | Before (baseline_appeal.md) | After PH-1 |
|---|---|---|
| Leaked `[ ]` placeholders | 6+ | 0 |
| Payer submission address | blank (`[Cigna/EviCore Mailing Address]`) | filled from the denial |
| Letterhead date | invented (`[Date: June 23, 2026]`) | stamped to today's local date |
| Signature | unnamed (`[Signature]` / `[Advocate…]`) | named ("Submitted on behalf of …") or ACTION-REQUIRED marker |
| `deadline_days_expedited` | mis-set to 30 | 3 (72-hour), panel window kept in `appeal_deadline_hint` |
