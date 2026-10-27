# WHU fix 3: the premise states its evidence standard (design addendum)

Status: **design for review, 27 October 2026. No code changed.** Post-study: no study record is altered.

Background: `docs/whu-omissions-investigation-2026-10.md`, cause (c). On S08, `premise.json`'s kill condition asked for "controlled or quasi-experimental evaluations", and the page's verdict ("Not proven, not disproven: mostly unmeasured.") answered that question. The page never weighed the assessment's high-confidence judgements, so the judges read it as understating. S03-C1 has the same shape: the page's evidence is citizens'-assembly studies, and the assessment's judgement on actor engagement is absent.

---

## 1. What the code does today

- **`premise.py`.**
  - `TEMPLATE` has `belief`, `what_the_sources_show`, `direction`, `reader_with_a_decision`, `kill_condition`, `kill_condition_tested`, and (fix 2) `scope`.
  - Nothing records what *kind* of evidence the answer will weigh.
  - `scope_rows` checks only that `scope` was written before the first source was held, to the day.
- **Drafting rules (`bindings.py`).**
  - B19, B20 and B25 compare a sentence with the spans it is bound to. They cannot see a judgement the page never binds.
  - Fix 2's coverage check (`coverage_check.py`) sees only the assessment statements and Executive Summary paragraphs the page *binds*. This is its recorded known limit.
- **Conclusion judge (`conclusion_judge.py`).**
  - `judged_rows` sends each on-page judgement row with its own premises, and the judge "sees only the passages the writer actually read".
  - Its UNDERSTATES label exists, but it cannot compare a verdict with a judgement that is in no premise. The S08 study log records this: "the conclusion judge reads only the bound abstract span".

So no stage can see a held assessment judgement the page leaves out.

---

## 2. Measured on the study issues (read-only, 27 October)

Assessment judgement groups in held documents, detected by structure (`coverage_check.groups_of`):

| Issue | Held assessment | Groups | With calibrated language | Bound by the page |
|---|---|---|---|---|
| S08 | Ch. 6 (S003) | 9 Executive Summary paragraphs | 9 | 2 |
| S03 | Ch. 13 (S006) | 19 Executive Summary paragraphs | 19 | 1 |
| S07 | WGIII SPM (S003) | 103 numbered statements | 103 | 1 |

Two facts follow.

1. **A rule limited to what the page binds would miss S03.** The S03 paragraph about the broad group of actors who shape climate governance is ¶7 of Chapter 13's Executive Summary. It carries calibrated language, and the page does not bind it. Fix 3 must therefore consider every held assessment judgement *on the question*, so it needs a relevance filter.
2. **The replays can be flagged only through what WHU held.**
   - The answer key's statements for S08-C1, C2 and C3 and for S03-C1 are in the IPCC SPMs, which WHU never held. The held chapters appear in the key only as scope or direction passages (locations: private details file).
   - So a rule that reads held documents can flag the **pages** of S08 (C1 and C3, through Chapter 6 Executive Summary paragraphs on the same subject) and of S03 (C1, through Chapter 13 ¶7).
   - It **cannot flag S08-C2**, whose only location is the unheld SPM C.2.6.
   - Holding the assessment summary is the investigation's fix option 4, a separate change.

---

## 3. The design

### 3.1 `premise.json` `evidence_standard` (step 1, before any source is opened)

```
"evidence_standard": {
  "weighs": ["measured", "assessed"],      // at least one
  "measured": "<which outcomes and designs count: trials, cohorts, evaluations ...>",
  "assessed": "<which expert assessments count: systematic-review conclusions, IPCC confidence-rated statements, guideline recommendations ...>",
  "when_they_differ": "state both",        // fixed; the page states both and drops neither
  "by": "...", "written_at": "<UTC>"
}
```

- `premise.py status` gets a row "evidence standard declared":
  - WARN if missing, or written after the first source was held (the same day-level test as `scope`);
  - STOP if `weighs` omits "assessed" while a held source is an assessment (see 3.2), unless `scope.out` names assessments with a reason.

### 3.2 Which held judgements count (code, then a constrained relevance ruling)

- **Candidates (code).** In every held source:
  - each assessment Executive Summary paragraph and each numbered SPM statement carrying calibrated language (`coverage_check.groups_of`, structure-detected);
  - each sentence of a review abstract's conclusions section;
  - each graded abstract-results sentence.
  - Each is located in the held text and stored by offsets; no source text is committed.
- **On the question.** This is the open decision. Options:
  - **R1 (recommended).** A ruling-model call per candidate: on the question yes/no. A "yes" must quote the words of the issue.json question it bears on, and code checks those words exist in the question, as `omissions.scope_element_ok` does.
    - Cost at the study's figures (about $0.02–0.03 a call): S08 9 calls, S03 19, S07 about 105 (about $3).
    - Within the $50 cap. Deterministic where code can be.
  - **R2.** Lexical overlap with the question's content words. Free, but fuzzy: it under-matches paraphrase, and over-matches common words like "emissions" across an SPM.
  - **R3.** Only what the page binds. Free and exact, but **misses S03** (2, fact 1). Rejected.

### 3.3 The rule (a preflight row, "assessment judgements stated")

For every on-question candidate judgement (3.2), the page must do one of three things:

- **state it with its certainty:** an on-page row is bound inside it, and the sentence carries its certainty or confidence term (B25's term families);
- **declare it out of scope** on the readers' list (fix 2's mechanism, `coverage_check.py declare`, counted against the declarations budget);
- **declare it not material**, with a reason. A SERIOUS case goes to a person, as in fix 2.

**When it applies.** The rule applies whenever `evidence_standard.weighs` includes "measured" and an on-question held judgement exists. This avoids classifying the page's verdict sentence by model. "The page states a measured-evidence verdict" is approximated by the premise declaring that it weighs measured outcomes.

*Alternative, for the advisor:* a binding-row field `verdict_basis: measured|assessed|both` on the answer sentence(s), set by the drafter, with the rule firing only on `measured`.

### 3.4 Interaction with what exists

- **Fix 2.**
  - The candidates extend the coverage units to unbound assessment sections (their known limit), but only those ruled on the question.
  - The readers' list and its budget are shared.
  - ADD sentences already carry grades (B25).
- **Fix 1.** Declarations are protected (`scope` kind). Nothing here rewrites a sentence.
- **The conclusion judge.** Unchanged: it still reads bound premises only. This rule is the stage that sees what the page does not bind.

---

## 4. Replays and tests (when built)

- **S08.** On-question Chapter 6 Executive Summary paragraphs unbound by the page are flagged, and the row STOPs. This covers C1 and C3's subject matter. **C2 is not flaggable** (2).
- **S03.** Chapter 13 Executive Summary ¶7 is flagged as on the question, and the row STOPs.
- **Synthetic twins in the repo** (the held texts are private):
  - a candidate stated with its certainty passes;
  - the same one stated without its term STOPs;
  - one declared out of scope must be on the readers' list;
  - an R1 "yes" that quotes no question words is refused by code.
- **Broken-check tests:**
  - remove the relevance code check;
  - remove the certainty-term test;
  - make the candidate set bound-only. That must fail the S03 replay.

---

## 5. Decisions needed before building

1. The relevance filter: R1 (recommended), R2 or R3.
2. Whether the rule fires on the premise's `weighs` (3.3) or on a drafter-set `verdict_basis` field.
3. Acceptance that S08-C2 is out of reach without holding the SPM (investigation fix option 4).
