# melanoma — adjudication of the outside review, 2026-08-28

Reviewed content: `2026-08-28-sent.html`, sha256 `bd101cd121688ead`
Standard: version 1.1
Page after adjudication: sha256 `b491276bd331`

The review itself is in `2026-08-28-review.md` and is never edited after the fact,
including by us. This file sits beside it and is where our decisions go.

One block per finding. Every REJECT also goes into `draft_decisions.json` with
a `what_would_change_it`, so a rejection is a judgment on the record rather
than a thing we chose not to do.

---

## OR-001

**Finding**

> "When the same data were published in The Lancet, they came with two-sided p = 0.053."
>
> BREACH — Rule 7: state the inferential framework before quoting a p-value. The piece
> correctly explains in the surrounding sentences that the trial used a prespecified
> one-sided framework, but the rule is explicit: when giving the two-sided p-value, that
> fact must be stated in the same sentence.

**Disposition** — ACCEPT

**Reason** — The rule says what it says, and the reviewer is right that the surrounding
explanation does not discharge it. A reader who skims the bolded figures sees 0.0266 and
0.053 without the framework attached to either. The fix costs nine words and changes no
argument. Accepted in the reviewer's own wording.

**Change**

> "When the same data were published in *The Lancet*, they came with **two-sided
> p = 0.053**, although the prespecified analysis was one-sided."

**Sources considered** — the ASCO 2024 KEYNOTE-942 design presentation supplied by the
reviewer (1-sided alpha of 0.1 per protocol); S007 (JCO five-year update).

---

## OR-002 — raised by the reviewer, explicitly not counted as a finding

**Finding**

> "The only route to it is a clinical trial." The reviewer verified that intismeran remains
> investigational and that trials are ongoing, but found no authoritative documentation
> establishing that expanded-access or compassionate-use routes are categorically
> unavailable. Recorded as a suspicion, not a finding.

**Disposition** — ACCEPT anyway

**Reason** — The reviewer was right to leave it out under the brief we set, which asks only
what breaches the standard. We are taking it anyway on a different ground: this sentence
sits in the section addressed to a patient deciding what to do next, and it is the one
place in the piece where a categorical claim we cannot source could close off a real
option for a reader. The claims around it — investigational, unapproved, not prescribable —
are supported and unchanged. Cost of the fix is two sentences; cost of being wrong falls
on a patient.

**Change**

> "In practice that means a clinical trial." (was: "The only route to it is a clinical trial.")
>
> "Ask your oncologist whether anything is enrolling near you, whether your stage and
> surgical status fit, and whether any expanded-access route exists."

**Sources considered** — S004 (Phase 3 announcement, describes intismeran as
investigational); no source found either way on expanded access, which is the point.

---

# Also changed in this pass — our own findings, not the reviewer's

These came out of the 13:56 gate report's claim-level verdicts, which had not been read
until after the snapshot went to the reviewer. They are recorded here because they change
the reviewed sha and the record must explain why it moved.

## GATE-c34 / c35 — ACCEPT

The draft said Practical Dermatology, Pharmacy Times and MLQ News "each listed what was
missing — hazard ratios, absolute event rates, p-values." SOURCE read them: only MLQ News
enumerated those metrics; Practical Dermatology said the companies had not disclosed
Phase 3 efficacy estimates; Pharmacy Times used a looser framing; Medical Daily could not
be verified. This is an overstatement of the same kind the piece retracts two paragraphs
later, which makes it worse than it looks.

**Change** — the sentence now attributes to each outlet only what it verifiably said, and
drops Pharmacy Times and Medical Daily from the claim entirely.

## GATE-c44 — ACCEPT

A source note dated The ASCO Post's confirmation to "21 August 2026 ... two days after the
announcement." The article exists but carries no such dateline and does not contain that
statement. The note was also orphaned — it followed no link. Removed.

## GATE-c28 / c29 — ACCEPT

Publication datelines "Morning Glory Sciences, on 20 August" and "Pharmacy Times, on
19 August" could not be confirmed from the articles themselves; only a relative timestamp
was retrievable for Pharmacy Times. Specificity inflation — a date added for precision
that is itself unverified. Dates removed from the body and from the source register; the
attributions and the quoted arguments stand.

---

# Rejected — instrument defects, not draft errors

Recorded here and in `factcheck_known_errors.json`. None produced a change.

## GATE-c22 — REJECT (`WRONG_READOUT_COMPARISON`, 4th occurrence)

SOURCE called the adverse-event rates wrong — fatigue 59.6%, injection-site pain 59.6%,
chills 51.0% — against the ASCO 2023 slide deck and the June 2023 press release, giving
60.6 / 55.8 / 50.0. Those are the 2023 primary-analysis figures. The draft's are the
five-year cut. The recorded defect names these exact numbers: *"adverse events
59.6/59.6/51.0 called wrong against the 2023 primary analysis, then against the three-year
update."* The prompt fix made after the third occurrence did not hold.

**what_would_change_it** — a five-year readout of KEYNOTE-942 giving different rates.

## GATE — four THIRD_PARTY objections — REJECT (`SOURCE_FALSE_NEGATIVE`, 5th–8th occurrence)

SOURCE reported Morning Glory Sciences, MLQ News, Medical Daily and the Spanish Science
Media Centre as unfindable. The same run's COVERAGE role cites all four, three with working
URLs that are in the draft. Morning Glory and MLQ return HTTP 403 to an automated fetch,
which is bot-blocking, not absence.

**what_would_change_it** — a fetch of those URLs from a normal browser returning nothing,
or the outlets' own pages failing to contain the quoted material.

