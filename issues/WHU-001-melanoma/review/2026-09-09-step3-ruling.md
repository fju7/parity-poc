# Step 3 — ruling on the eight blocked rows

None blocks publication. Every one is a record that has not caught up with the
page, plus one email that still describes a page we corrected. The page itself
is sound: rules 1 and 2 ok, 130 figures all in held documents, dateline correct.

---

## First — 1d was a bad instruction and you were right to override it

The grep was mine and it was badly built: it searched raw HTML for a string that
spans a tag boundary, so it could only ever return 0. Worse, I wired a **stop**
to it. Followed literally, my own instruction would have halted the close-out on
a false alarm.

You checked the thing the test was asking about rather than the test, and found
the scoring paragraph byte-identical to the base at 1152 characters. That is the
second time today you have overridden one of my instructions correctly — the
first was preserving the page's own markup rather than substituting the entry
file's degraded copy.

**Process amendment**, beside failure 14:

```
A stop condition is only as good as the test under it. Before wiring a halt to a
check, establish what its false negative looks like — a fragile test with a stop
attached converts a measurement error into a halted pipeline, and the person who
wrote the test is the least likely to notice its blind spot. Where an instruction
says stop, it means stop on the condition the instruction is about, not on the
literal output of the probe suggested for detecting it.
```

---

## Gate A — email-parity

The email is a co-published artifact that `publish.py` keeps in sync. Its
obligation is **not to contradict the page**. Absence is not contradiction;
staleness is.

**A1 — 0.179, 1.004 in the email, not on the page. FIX THE EMAIL.**
This is OR-019 shipping to subscribers after being corrected on the page. The
email still carries the mixed-width comparison — an 80% interval set beside a
95% one — which is the exact thing the finding exists to remove. Replace the
email's sentence to match the page: the three-year hazard ratio of 0.425 on nine
deaths at 95% CI 0.114 to 1.584, the five-year 0.471 on fourteen at 0.165 to
1.345, and the earlier interval being the wider of the two.

**A2 — the unmatched sourcing claim. FIX THE EMAIL.**
Pre-existing on the base, but it is the sentence the page corrected under OR-002
for overstating what the checks do. Leaving it in the email means the
overstatement still reaches readers after the page stopped making it. Bring it
into line with the page's current wording.

**A3 — 0.179 and 1.004 removed with no record of why. FIX THE RECORD.**
The removal is correct; a `deletions.py` entry saying why is what is missing.
The reason is on the page already: both intervals belong to the same hazard
ratio in the same table row of S007, and the 95% pair is the like-for-like
comparison.

**The absences are acceptable and need no action.** The email says nothing about
the scorecard split or the outlet count. An email that carried the *old* single
composite would be a defect; one that carries no verdict and points at the page
is not. Do not manufacture email content to fill a gap the gate does not test.

**Patch, do not rebuild.** Two sentences and a deletions entry, not a rewrite.

---

## Gate B — correction-history

All five are the record catching up. Do them in this order:

**B1 — 3.40 needs a declared exclusion**, exactly as 3.35 and 3.4 have. It is the
page's own arithmetic, now quoted inside the corrected entry that explains the
August weight set. Same treatment, same reason.

**B2 — S029 errata entry.** EORTC 18071 entered the store during remediation
item 2 and was never checked. Check it, then record it.

**B3 — corrections.md 9 September entry.** The footer log has one; this file does
not. That is the gap, not a missing correction.

**B4 — run changecheck.** Mechanical.

**B5 — Spruance, Eggermont, Greenland into verified_attributions. VERIFY FIRST.**
This one is not mechanical and I want it said plainly: the file is called
*verified*_attributions. Adding three names to it because a gate wants them
present, without opening the sources, would be the precise failure this entire
cycle has been about — and it would be worse than the six reviewer errors,
because it would write an unverified claim into the artifact whose name asserts
verification.

Open each: Spruance et al., PMID 15273082 / PMCID PMC478551. Eggermont et al.,
N Engl J Med 2016;375(19):1845–1855, PMID 27717298. Greenland et al., the
statistics paper already held as S022. Confirm the names as the page spells them
against the documents, then record.

If any name on the page does not match its source, that is a finding and it
outranks the gate.

---

## Then

Re-run every gate. Record the email patch, the deletions entry and the five
record fixes in the change set — they are this round's changes and rule 14
applies to them like anything else.

Then step 4, the verification, as written.

---

## CC block

```
STEP 3 — apply the ruling. Then re-run all gates, then proceed to step 4.

EMAIL — patch, do not rebuild. Two sentences only.
  1. Replace the survival-interval sentence to match the page: 0.425 on nine
     deaths, 95% CI 0.114 to 1.584; 0.471 on fourteen, 95% CI 0.165 to 1.345;
     the earlier interval is the wider of the two. This removes 0.179 and 1.004,
     which is what row 1 is blocking on.
  2. Bring the sourcing sentence into line with the page's current wording — the
     one the page corrected for overstating what the pre-publication checks do.
  Leave the scorecard and outlet-count absences alone. An email that carries no
  verdict and points at the page is not a defect; only a stale verdict would be.

RECORD
  3. deletions.py entry for 0.179 and 1.004: removed because both belong to the
     same hazard ratio in the same S007 table row as the 95% pair, and the
     like-for-like comparison is the one the page now makes.
  4. Declared exclusion for 3.40, same treatment as 3.35 and 3.4 — it is the
     page's own arithmetic, quoted inside the entry that explains the August
     weight set.
  5. Errata checked entry for S029.
  6. corrections.md entry for 9 September.
  7. Run changecheck.
  8. verified_attributions: Spruance, Eggermont, Greenland. OPEN EACH SOURCE
     FIRST — PMID 15273082 / PMC478551, PMID 27717298, and S022 respectively —
     and confirm the names as the page spells them against the documents before
     recording. Do not add a name to a file called verified_attributions on the
     strength of a gate wanting it present. If any name on the page does not
     match its source, stop: that is a finding and it outranks the gate.

  Record all of the above in the change set. Rule 14 applies to this round's
  changes like any other.

PROCESS
  9. Add to docs/whatholdsup-process.md beside failure 14 the stop-condition
     amendment quoted in 2026-09-09-step3-ruling.md — a stop wired to a fragile
     test converts a measurement error into a halted pipeline.

Then re-run every gate and report. If all green, proceed to step 4 without
waiting: produce the verification record as specified, then stop for the
operator's acceptance and confirm-review.
```
