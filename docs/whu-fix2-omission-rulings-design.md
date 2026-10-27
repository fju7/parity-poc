# WHU fix 2: omission rulings and a step-3 coverage check (design only)

Status: **design for review, 27 October 2026. No code is changed by this document.**
Post-study: the reliability study (S01–S08) is complete, and nothing here alters a study record.

Background: `docs/whu-omissions-investigation-2026-10.md`. Five of the 13 Understates/Omits items were drafting omissions of findings that were held, read and in scope (S01-C2, S01-C4, S07-C2, S07-C3, S07-C4). On S07 the source advocate raised exactly the omission, as SERIOUS, and the ruling model rejected it (`issues/WHU-S07-…/rulings/rulings.jsonl:12`, advocate item S003-13). Its reason was that the sentence the objection was anchored to was itself accurate.

Fix 1 (`68d0324`, `94ed5e3`) stopped rulings from destroying scope and reading statements. Fix 2 is the converse: it gives an omitted finding a way *onto* the page.

---

## 0. What the current code does, and why omissions are lost

**The advocate is told to hunt omissions** (`backend/scripts/whatholdsup/source_advocate.py`, `ADVOCATE_SYSTEM`, lines 115–169):

> "Your job is RETRIEVAL, not taste. … The strongest objection is almost never "that is unfair" — it is "you did not read section 4, which answers you.""
>
> "The omission was the fact in the source that answered the question the page had posed. That is what you are hunting for."
>
> "3. … Other checks handle figures; you are here for what the page left out."

**But its output schema has no place for an omission as such.** Every objection is one shape:

```
"claim_quoted":  "the exact sentence or phrase from the page you object to",
"objection":     "your objection, in one sentence",
"source_says":   "what your document actually says, QUOTED, with a locator …",
"locator":       …, "could_not_find": …,
"severity":      "SERIOUS" | "MINOR",
"changes_conclusion": "CHANGES" | "NARROWS" | "NONE",
"why":           "why this matters to what the page concludes"
```

So an omission has to be pinned to a page sentence (`claim_quoted`) and expressed as an objection *to that sentence*. The schema has no field that says "this is something left out". The only way to tell an omission from a misstatement today is the wording of `objection`. A rough keyword count ("omits", "leaves out", "does not mention", "missing", …) over every advocate brief in S01–S08 finds 145 of 311 objections (47%) phrased as omissions. That is a heuristic, not a classification.

**The ruling prompt can only rule on the sentence** (`audit_prompts/rule_group.md`, frozen for the study at sha256 `68a0fd06…`; `rule.md` is the same in substance):

> "Decide each finding: it is right, or it is wrong because the source text supports the sentence as written on that point."
>
> "- reject: every finding is wrong: the source text supports the sentence as written."
>
> "- amend: … If nothing the sentence says can be supported, give the shortest text that can, or "" to cut the sentence."

**Consequence.** An omission objection on an accurate anchor sentence is always "wrong" under this test, and the item closes as `MERIT: no`. The adjudication template (`write_template`) has MERIT / EFFECT / DID, and its EFFECT words (`changes | narrows | sharpens | corrects | none`) have nothing for "add". The process has no step that inserts a sentence. Every apply step (4c, 5a, 6a, 7b) replaces or cuts one existing sentence word for word.

**Quotation checking today.**
- `check_quotations` tests `source_says` against the held text with `audit_stage.quoted_in`, which checks presence only: no offset is recorded.
- A failure is re-asked once (`_requote`); a second failure carries `QUOTE_NOTE`.
- The advocate call runs with `search=True`, so a quotation can come from the web rather than the held document. That is why a code check, not the model, must decide where a quotation sits.
- `audit_stage.locate(q, hay)` already returns `(start, end)` offsets of the held text by the same comparison. Fix 2 uses it.

**The premise has no scope field.** `premise.json` holds `belief`, `what_the_sources_show`, `direction`, `reader_with_a_decision`, `kill_condition`, `kill_condition_tested`. The question itself is in `issue.json`. Nothing records, before the sources are read, what the answer will *not* cover.

**The step-3 checks are all about sentences already on the page.**
- B1–B24 run per binding row (`bindings.py`); B2/B3/B5/B6 run over real bytes (`spancheck.py`).
- `modelbind.py` lets a model *propose* a span for an existing sentence and has `spancheck` decide whether it exists: "the model searches, the machine decides".
- No check starts from a source and asks which of its conclusions the page uses.

---

## 1. Objection types

**Change.** Add a required `type` to the advocate's objection schema:

```
"type": "MISSTATES" | "LEAVES_OUT",
```

- **MISSTATES.** As today: `claim_quoted` is the page sentence objected to, and `source_says` is what contradicts or qualifies it. It goes to the existing advocate ruling (`rule_group.md`), unchanged.
- **LEAVES_OUT.** `claim_quoted` is renamed in meaning to *the page sentence nearest to where the finding belongs* (its anchor, used only for placement). `source_says` becomes mandatory and must quote **the omitted finding itself**, not the sentence the page already uses. An empty `source_says` is not an omission objection: the code records it as UNRUN and asks again once, as `_requote` does.
- **Prompt.** Rule 3 is rewritten: "If the page leaves out a finding of your document that answers its question, say LEAVES_OUT and quote that finding; do not quote the passage the page already uses."
- **Adjudication template.** It shows `type`. An omission item closes with the new outcome words (§2), not MERIT/EFFECT.
- **Older briefs** (no `type`): `omission_kind()` flags the keyword pattern above as *suspected* LEAVES_OUT. The flag only routes the item for a re-ask; it decides nothing. A suspected omission whose `source_says` is text the page already binds is re-asked once for the omitted finding (paid, about $0.05). That is exactly S07's S003-13, whose quotation was C.8.2's first sentence, already on the page.
- **The prompt's location.** `ADVOCATE_SYSTEM` lives in `source_advocate.py`, which is not on `frozen.py`'s list. The ruling prompts that are frozen (`rule.md`, `rule_group.md`, `rule_cite.md`, `rule_group_cite.md`, `read.md`, `summary.md`) are not touched. The omission ruling gets its own new prompt file.

---

## 2. The omission ruling

New mode `ruling.py omissions` (step 4d, after 4c). One call per LEAVES_OUT objection, not grouped by anchor sentence: an ADD inserts, it does not replace, so two omissions near one sentence are two decisions. Objections quoting the same held passage (same source, overlapping offsets) are merged first, so one finding is ruled once.

### Inputs (the payload; nothing else reaches the model, as for every ruling)
- the question, from `issue.json`;
- the premise's `scope` (new, §2.4) and `reader_with_a_decision`;
- the omitted finding: the verified quotation and its held context (±`QUOTE_AROUND` characters, `audit_stage.in_context`);
- the anchor sentence and its two neighbours, from the page;
- the page's existing sentences bound to the same source, so the model can see what is already used.

The source id, the signer fields and the advocate's own prose are *not* sent, as the existing allow-list tests require.

### The three tests, in order

1. **In the held source (code; no call).**
   - `audit_stage.locate(source_says, held_text)` must return `(start, end)` in the held text of the objection's source (`ruling.held_texts`, reading order).
   - A licence-barred source (`audit_stage.licensed_ids`) is never sent; its omission goes to a person.
   - Not found means **NOT_IN_SOURCE**, decided by code. The model is never called, and the record says which text was looked for and where.
   - Found means the offsets and the sha256 of the held text are recorded. Every later step quotes from the offsets, never from the advocate's words.
2. **Within scope (model, constrained by code).**
   - The model answers `in_scope: true|false` and, if false, must name the element of `issue.json`'s question, or the `scope.out` entry, that excludes it.
   - Code checks that the named element appears in the question or in `premise.json` `scope.out`. An OUT_OF_SCOPE that names neither is refused and goes to a person, so OUT_OF_SCOPE cannot become the new "reject".
3. **Material (model).** `material: true|false`, against two questions:
   - Does the finding answer, narrow or qualify the page's answer to the question?
   - Would `reader_with_a_decision` weigh it?
   - A SERIOUS objection with `changes_conclusion` CHANGES that the model calls NOT_MATERIAL goes to a person rather than being decided by the model.

### Outcomes

| Outcome | Decided by | What happens |
|---|---|---|
| **NOT_IN_SOURCE** | code (test 1) | Item closed; nothing on the page. Record: source, sha256 of the text sought, "not in the held text". |
| **OUT_OF_SCOPE** | model, checked by code (test 2) | Item closed; recorded (§2.4). No sentence added. |
| **NOT_MATERIAL** | model (test 3), or a person for SERIOUS/CHANGES | Item closed with the reason. |
| **ADD** | model proposes, code checks (below) | The drafting session inserts the sentence word for word after the anchor. It is bound, checked and audited like any new sentence. |

### Drafting an ADD sentence
- The model returns `draft_text` and `span`. `span` must be a substring of the verified quotation; code checks it with `locate`, as `modelbind` does.
- **Source wording is preferred.** The form is an attribution frame around the source's own clause ("The IPCC concludes, with high confidence, that …"). Paraphrase is allowed only where the source's sentence will not stand alone, and then the span still binds it.
- **Placement.** The ADD goes immediately after the anchor sentence. If the anchor is a protected sentence (fix 1) or sits in the limits section, it goes after the last unprotected sentence of the same section.

### Binding and checks on an ADD
- The row is created with `origin: "omission_add"` and `ruling: <id>`, bound to the span.
- B2 (span present), B5 and B6 (scope words) run as for any row.
- **No stronger than the source.** B19 (hedge preserved) is a **STOP**, not a WARN, on `omission_add` rows. B20 (confidence ceiling) applies as usual. A new **B25 (grade carried)** STOPs if the span carries a certainty or confidence term (GRADE, IPCC calibrated language) that the sentence drops. B25 also WARNs if the sentence states a *higher* level than the span (no weaker, no stronger).
- **Then:**
  - `applied_check.py` checks the inserted text equals `draft_text` exactly. That needs an "insert" record kind next to replace and cut.
  - The GAP-016 dangling check runs.
  - Changecheck reads it as a changed sentence since 3b, and 9a coverage requires that.
  - The conclusion judge reads it if it is a judgement row.
  - The audit reads it like any page sentence; the audit's existing kind "Understated a finding" applies in both directions.

### 2.4 Where scope is declared, and where OUT_OF_SCOPE is recorded
- **`premise.json` gains `scope`**, written at step 1 *before any source is opened* (the same discipline as `belief`), so scope cannot be fitted to the findings afterwards:
  `{"covers": "<what the answer will address>", "out": [{"what": "...", "why": "..."}], "by": "<agent or person>"}`.
  `premise.py status` warns when `scope` is missing on a new issue.
- **`issues/<case>/omissions.json`** (committed) records every omission ruling:
  - fields: source id, held-text sha256, `start`/`end` offsets, sha256 of the quoted text, outcome, reason in WHU's own words, ruling id;
  - **no source text.** Ruling 3 forbids committing source quotations; the quoted text lives in `rulings/omissions.jsonl`, which is ignored and archived privately.
- **The adjudication item** closes as `OMISSION: out_of_scope — <element>; DID: nothing added`.
- **Optionally** the page's limits section carries one WHU sentence naming what is out of scope ("This answer does not cover …"). That sentence is protected under fix 1, via a new phrasing or the row marker, so later rulings cannot remove it.

---

## 3. The step-3 coverage check

New script `coverage_check.py` (step 3c, after 3a, before the 3b commit). It starts from the sources and asks which of their headline conclusions the page accounts for.

### Which sources
A **relied-on source** is one named in `premise.json` `what_the_sources_show.sources`, or one that at least three on-page binding rows rest on (`audit_stage.sources_of`). Sources held as abstract only are included, judged on their abstract.

### Identifying headline conclusions (code first)
Extraction works on the held text in reading order (`spancheck._text`, which the other checks use), with section boundaries from the document's own structure:

| Document | Headline units |
|---|---|
| JATS/PMC XML (Cochrane, most journals) | every sentence of the abstract's conclusion section (`<sec>` titled "Authors' conclusions", "Conclusions", "Interpretation", "Implications"), and abstract results sentences that carry a certainty or confidence term (GRADE words) |
| Campbell / other systematic reviews (PDF text) | the same, by heading text in the reading-order text |
| IPCC SPM | each numbered statement (`A.1`, `C.8.2`, …): its headline sentence and every sub-sentence that carries a calibrated term ("high confidence", "medium evidence, high agreement", …) |
| IPCC chapter | each Executive Summary paragraph's first sentence and every sentence with a calibrated term |
| Other (reports, primary studies) | the abstract's conclusion sentence(s) if a heading is found; otherwise **no automatic units** |

- Where no structure is found, the row WARNs ("no headline section found") and a model may *propose* units. The machine accepts only units it can `locate` in the held text, as `modelbind` does.
- Every unit is stored as `{source, start, end, text_sha256, section}`, with offsets verified by `locate` on the held text. No source text is committed: `coverage.json` holds offsets and hashes; the text is regenerated from the held document when needed.
- **Validity note.** The study's private answer-key tools also extract conclusions with offsets. WHU's extractor must be written from the documents' own structure, as above, and must not reuse or consult those tools or the keys. Otherwise a future evaluation would be measuring WHU against a definition WHU was built to match.

### Accounting
Each unit must end in one of these states:
- **used** (code): some on-page binding row's span `locate`s inside or overlapping the unit's offsets.
- **declared out of scope**: `{reason, element of the question or scope.out, by}`. The same code check applies as for OUT_OF_SCOPE rulings: the element must exist in the question or scope.
- **declared not material**: `{reason, by}`.
- **added**: a sentence is drafted and bound. It is then a *used* unit and goes through the step-3 checks like any other.

`bindings.py check` reports the counts. Under fix 1's rules, a declaration naming a person needs a signature. An agent may declare, and its declarations are counted and shown in the preflight row "headline conclusions accounted for": STOP on any unit with no state, otherwise ok with the counts.

### What this would and would not have caught in the study
Judged from where the missed conclusions sit (their locations are in the private details file):
- **Likely caught** (S01-C2, S01-C4, S06-C5, S07-C2–C4): those findings are headline units of a held, relied-on source, and the drafter would have had to use them or declare them. S06-C5 would most likely be declared out of scope, but declared on the record.
- **Not caught** (S03-C1, S08-C1–C4, S05-C5): the source that states them was not held (S03, S08), or the finding is not in a headline section (S05-C5). That is fix option 4 of the investigation (hold the assessment summary), a separate change.

---

## 4. Interaction with fix 1, the conclusion judge and the audit

- **Fix 1.**
  - Omission rulings only insert; they never rewrite or cut, so they cannot touch a protected sentence.
  - An ADD anchored on a protected sentence is placed after it, never merged into it.
  - The optional out-of-scope limits sentence is itself protected.
  - `split_protected` stays in front of every other ruling mode, and the omissions mode needs no exception.
  - An ADD sentence states a finding, so `STATES_FINDING` keeps it unprotected and audited.
- **Conclusion judge.**
  - ADD rows that are judgements are judged on their current text.
  - The judge's UNDERSTATES label already exists; with B25 in place, an ADD that drops the source's grade is stopped at step 3 before the judge sees it.
  - The judge never decides an omission, because it reads only bound sentences.
- **Audit.**
  - ADD sentences are page units like any other.
  - An audit ruling may amend or cut an ADD. That is allowed: an ADD is a source claim and must survive the audit.
  - A cut ADD returns its coverage unit to "no state", so the coverage row STOPs and a person sees that a headline conclusion has left the page again.
- **Changecheck and 9a.** ADD sentences are changed since 3b, so changecheck must read them.

---

## 5. Cost per issue, and the risks of a longer or overstated page

**Cost estimate** (from the study's own records):
- **Advocate rulings:** S08 spent $0.56 on 29 rulings, about $0.02 each. The keyword count suggests about 18 omission-shaped objections per issue (145 across 8 issues). Omission rulings carry more input (question, scope, context), so about $0.03 each, or roughly **$0.55 per issue**, plus the 20% consistency sample (about $0.11).
- **Re-asks** for pre-fix-2 briefs: a few per issue at about $0.05, under **$0.30**.
- **Coverage check:** code only, **$0**. The optional model proposal for unstructured sources is about $0.05 per source.
- **Downstream:** each ADD is one more audit unit (about $0.052 per unit per run on S08). Five ADDs over three audit runs is about **$0.80**. The narrow gate's source role is about $0.10–0.30 per source call if an ADD carries a figure. The conclusion judge is under $0.01 per sentence.
- **Total:** about **$1.5–2.5 per issue**, against roughly $30 spent per study issue and the $50 cap. `stage_cap.py` gains an `omissions` stage with units = merged LEAVES_OUT objections.

**Page bloat.**
- *Risk:* 145 omission-shaped objections in 8 issues; if even a third became ADDs, a page gains six sentences.
- *Mitigations:*
  - materiality is a separate test with a stated reason;
  - duplicates are merged by source offsets;
  - an **ADD budget**: at most 8 ADD sentences, or 15% of body sentences, whichever is smaller. Beyond it, ADDs are grouped into one section ("What else the sources conclude"), and anything over the budget goes to a person, never dropped silently;
  - the coverage check's "used" state counts an existing sentence that already carries the finding, so nothing is added twice.

**Overstatement.**
- *Risk:* an ADD written in the model's words drops a hedge or raises a grade, which is the error class B19 was built for.
- *Mitigations:*
  - source wording preferred;
  - span-bound;
  - B19 as STOP and B25 (grade carried, both directions) on `omission_add` rows;
  - then the conclusion judge and the audit, as for any sentence.

**Process risk.**
- *Risk:* OUT_OF_SCOPE and NOT_MATERIAL become the new place where omissions die.
- *Mitigations:*
  - OUT_OF_SCOPE must name a question or `scope.out` element (code-checked);
  - SERIOUS/CHANGES omissions go to a person when ruled NOT_MATERIAL;
  - every decision is in the committed `omissions.json`, with counts in the preflight;
  - the consistency sample covers the new mode.

---

## 6. Tests

Real source text may not be committed (ruling 3). So each real-text replay reads its inputs at test time from the private archive (`~/Projects/whu-study-private/<issue>/…`) or the library, and is **skipped with a reason when they are absent**, as in CI. Each has a synthetic twin in the repository with the same structure. Every fake model answers only from the prompt it receives; the code under test chooses what reaches it.

1. **S07 replay (expect ADD).**
   - Input: advocate item S003-13 (adjudication `20261025T001512Z`, ruled by `rulings.jsonl:12`).
   - The old brief has no `type`. `omission_kind()` flags it, and its `source_says` is already bound on the page, so it is re-asked. The fake advocate answers with C.8.2's second sentence, taken at runtime from the held S003 text.
   - Code: `locate` finds it (offsets recorded), the scope element "measures such as transport pricing … better connected" is present in the question, and the fake ruling model returns `ADD` with a span inside the quotation.
   - Asserts:
     - code verified the span;
     - B2 and B19 ran on the draft row for real;
     - B19/B25 STOP when the fake's draft drops "high confidence" (a second variant);
     - `omissions.json` holds offsets and hashes and **no source text**.
2. **Genuinely out of scope (expect OUT_OF_SCOPE).**
   - Input: S03 advocate item S002-14 (adjudication `20261023T005608Z`), which the ruling at `rulings.jsonl:2` covered. The objection is that the page leaves out the paper's recommendation on strengthening how assemblies are followed up: a prescription, while the question asks whether involvement affects backing and results.
   - The fake returns `in_scope: false`, naming the question's "affect whether the policies win political backing and get results".
   - Asserts:
     - the code check accepts the named element;
     - the item closes as out of scope;
     - nothing is added to the page.
   - A twin case, where the fake names an element that is in neither the question nor `scope.out`, must be refused by code and go to a person.
3. **Synthetic NOT_IN_SOURCE (decided by code).** An objection whose `source_says` is not in the held text. Asserts:
   - the outcome is NOT_IN_SOURCE;
   - the fake model was **never called**;
   - the record names the text sought and the source.
4. **Real filters, not a cooperative fake.**
   - With `locate` stubbed to always succeed, test 3 must fail.
   - With the scope-element check removed, test 2's twin must fail.
   - With the B19 STOP on `omission_add` rows reverted to WARN, the over-strong variant of test 1 must fail. This is the same mutation check used for fix 1.
5. **Coverage.**
   - A synthetic JATS abstract with an "Authors' conclusions" section, and a synthetic SPM-style numbered statement with four calibrated sub-sentences.
   - Asserts:
     - the units are extracted with verified offsets;
     - one is used by a page row, so the others must be declared and the preflight STOPs until they are;
     - an out-of-scope declaration naming no question element is refused;
     - a cut ADD returns its unit to "no state".
6. **Fix 1 still holds.** An ADD anchored on a protected sentence is inserted after it, and the protected sentence is byte-identical.
7. **Budget.** A ninth ADD on a page already at the budget goes to a person, not onto the page.

---

## 7. Files that would change, in order (one change at a time, each with its tests and a full-suite run)

1. **`backend/scripts/whatholdsup/source_advocate.py`.** The `type` field and rule 3 rewritten in `ADVOCATE_SYSTEM`; `write_template` shows the type and the omission closing words; `omission_kind()` and the one-time re-ask for older briefs. Tests: schema, template, re-ask.
2. **`backend/scripts/whatholdsup/premise.py`.** The `scope` field, its template and a status warning. Tests: missing scope warns; scope written after a source is opened is flagged, using the same timestamp discipline as `belief`.
3. **`backend/scripts/whatholdsup/omissions.py`** (new). Test 1 (locate and offsets), the merge by offsets, the code check on scope elements, and `omissions.json` and `rulings/omissions.jsonl` I/O. Tests 3 and 4.
4. **`backend/scripts/whatholdsup/audit_prompts/rule_omission.md`** (new, not frozen) **and `ruling.py`.** The `omissions` mode: payload allow-list, outcomes, routing to a person, `pending()` units, consistency sample. The advocate mode keeps only MISSTATES. Tests 1, 2, 6 and 7.
5. **`backend/scripts/whatholdsup/bindings.py` and `spancheck.py`.** `origin: omission_add` rows, B19 as STOP on them, B25 grade carried. Tests: the over-strong and over-weak drafts.
6. **`backend/scripts/whatholdsup/applied_check.py`.** An "insert" record kind; the dangling check sees insertions. Tests.
7. **`backend/scripts/whatholdsup/coverage_check.py`** (new) **and `bindings.py check`** reporting. Test 5.
8. **`backend/scripts/whatholdsup/stage_cap.py`.** An `omissions` stage estimate.
9. **`backend/scripts/whatholdsup/publish.py`.** Preflight rows "omission objections ruled" and "headline conclusions accounted for", both fail-closed.
10. **`study/whu-reliability/RUN.md` is not edited** (it is a frozen study file). The new steps 3c, 4d and 4e go in `docs/whatholdsup-process.md` and the WHU runbook for post-study issues. CLAUDE.md gets an entry with each step.

Each step is its own commit, tagged post-study, with tests that apply the real filters, and is reviewed before the next.
