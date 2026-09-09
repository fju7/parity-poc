# Close-out — the last four items, in order

Dependency order matters. RV-06 and the preflight gates can both surface page
changes; a verification run before them verifies a page that then moves. So:

1. RV-06 and the amendments (small, independent)
2. Preflight gate report — report only, because a fix may change the page
3. Whatever the gates surface, decided
4. Verification (the agent — a non-author)
5. Acceptance (Fred)
6. Confirm-review (Fred)

Steps 1–4 are the block below. Steps 5 and 6 are yours and cannot be delegated:
5 attests that 4 happened and was done by someone who did not write the work.

---

## The verification artifact

Rule 13's verification half needs one addition I did not write into the patch:
**the verification is recorded, with what was read.** Per entry — the
disposition, the artifact opened to confirm it, and the verdict. Not a summary
line.

Without that, "verified" is an assertion with exactly the same standing as the
assertions it checks, and the acceptance signature would attest to a claim
nobody can audit. This cycle produced six reviewer errors, every one of them a
conclusion stated without the artifact behind it named. The fix that worked was
naming the artifact. Apply it to the check as well as to the work.

Add to the rule 13 patch, at the end of the *Verification* paragraph:

```
The verification is recorded as it is performed: for each entry, the disposition
checked, the artifact opened to check it, and the verdict. A verification that
records only its conclusion is an assertion of the same kind as the ones it is
checking, and the acceptance signature would then attest to something unaudited.
```

---

## CC block

```
TASK: Close out the melanoma issue. Four steps, in order. Stop and report
between step 2 and step 3.

Base: the live page. Record its SHA at the start and again at the end; if it
changed between them, say what changed it.

--- STEP 1 — complete the record ---

1a. Add RV-06 to the adjudication. Text is in 2026-09-09-closing-out.md,
    section 0. It records that the reviewer's ruling 1 of 8 September was
    rejected: the August page used a different weight set (reproducibility and
    recency at .15 where the rubric gives .20 and .10), its printed arithmetic
    came to 3.4000 exactly, and no rounding was ever involved. Corrected in
    commit 87b8d9d.

1b. Apply the rule 13 amendment in 2026-09-09-rule13-amendment.md — a
    find-and-replace against the REPO copy of docs/whatholdsup-process.md, which
    is ahead of any copy in ~/Downloads. Verify the FIND text matches before
    replacing; stop and report if it does not. Include the recorded-verification
    sentence quoted above, appended to the Verification paragraph.

1c. Two further process amendments, if not already applied:
    - beside failure 14: "A caveat is not a check. Naming an uncertainty
      protects against the failure you imagined and does nothing about the one
      you did not. Where a ruling turns on a historical artifact, open the
      artifact."
    - in §13: "A duplicate of a superseded document is a trap. A duplicate of a
      document you are about to edit is a backup. Do not delete the second kind
      before the edit is verified."
    - beside failure 14, a third: "A check whose own history is a correction
      should be read before its name is trusted. sources_shown was
      mis-described by three separate readers; its earlier version read bindings
      only and was wrong in exactly the way that omission predicts."

1d. Settle one open discrepancy:
      grep -c "Consensus scores 4 because" site/whatholdsup/melanoma.html
    If 1, the sentence exists and the last report's claim that it does not is
    wrong — note it and move on. If 0, prose changed during a pass that was
    declared records-only; that is a finding, report it and stop.

--- STEP 2 — the two preflight gates. REPORT ONLY. Change nothing. ---

For email-parity and correction-history, each:
  - the file and function implementing it, and what it actually tests, in the
    terms the code uses rather than the terms the gate name suggests
  - its state on the current page: pass, fail or blocked, with exact output
  - for any failure: the specific items, and whether the fault is in the page,
    in the email, or in the check's own keying
  - whether this round caused it — the log surgery, the change-set schema, the
    rebound sentences, the new source, or the date move

For email-parity specifically, report what the email summary currently says
about the scorecard, the outlet count, the survival intervals and the correction
history, and whether any of it still describes a pre-9-September page.

Then STOP and report. Do not fix, do not rebuild the email.

--- STEP 3 — after the report is ruled on ---

Apply whatever is decided. Re-run all gates.

--- STEP 4 — verification, under rule 13 as amended ---

You did not write the adjudication, so you supply the verification half. Produce
a verification record — a file, not a chat summary — covering every OR and RV
entry. Per entry:

  entry id | disposition | the artifact you opened to check it | verdict

Verdict is CONFIRMED or DISCREPANCY. For a discrepancy, say what the entry
claims and what the artifact shows.

Four things the verification is for:
  1. every ACCEPT actually landed on the page
  2. each disposition matches what was decided, not what reads well afterwards
  3. nothing was quietly dropped — OR-018 changed disposition twice and OR-007
     is half-rejected; look there first
  4. the RV entries are honest

On 4: read RV-01 through RV-06 hardest. They are where the reviewer assessed
their own errors, and a reviewer writing up their own mistakes describes them as
narrower than they were. An RV entry that reads tidier than what happened is
itself a finding and is worth more than the entry it corrects. You have made and
self-corrected two errors about sources_shown in this repo today; that is the
behaviour that qualifies you for this, not against it — but it is also the
reason the record must show what you read rather than only what you concluded.

Then stop. The acceptance signature and the confirm-review are the operator's
and you do not supply either.
```

---

## What Fred does, after step 4 returns

**Acceptance.** Read the verification record — not the adjudication. You are
attesting that a non-author verified it and that you accept the result. If the
record shows any DISCREPANCY, that comes back before acceptance.

**Confirm-review.** After acceptance, not with it. It records that the outside
review happened and was adjudicated, and that is only true once the adjudication
is complete and verified.

Then publish, if the gates are green.
