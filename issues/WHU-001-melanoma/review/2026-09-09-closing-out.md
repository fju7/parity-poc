# Closing out — what I can and cannot do

Three things left. I can help with one of them and must not do the other two.

---

## 0. First: RV-06 is missing, and it blocks the signature

CC added RV-05. My sixth error happened after that and has no entry. Signing an
adjudication that omits the most recent reviewer error makes the signature
attest to something untrue, so this goes in first.

**RV-06 — reviewer error, rejected**

> **Raised.** Ruling 1 of 8 September: the reviewer ruled that the page's
> "out by 0.05" self-accusation was false because 3.35 rounds to 3.4, and
> instructed that the correction be withdrawn.
>
> **Disposition** — REJECT
>
> **Reason.** The August page's own printed arithmetic came to 3.4000 exactly.
> It used a different weight set — reproducibility and recency at .15 each,
> where the rubric gives .20 and .10. Both sets sum to 1.00; the entire 0.05 is
> that one swap, corrected in commit 87b8d9d on 3 September alongside the
> rubric's publication. No rounding was ever involved. The page's original
> account was wrong and so was the reviewer's replacement for it.
>
> The reviewer did attach a caveat — "check what the 26 August page printed
> before finalising" — but attached it to the display convention, which was not
> the failure mode. A caveat covers the axis its author happened to imagine. It
> is not a check, and it reads as diligence to everyone including the person who
> wrote it. The five errors before this one were caught by opening the artifact;
> this one was not caught by naming an uncertainty about it.
>
> The implementation resolved it by reading the commit history, which is the
> artifact neither account had opened.

**Two amendments this earns**, both small, both in the process document:

- Beside failure 14: *A caveat is not a check. Naming an uncertainty protects
  against the failure you imagined and does nothing about the one you did not.
  Where a ruling turns on a historical artifact, open the artifact.*
- In §13, beside the naming conventions: *A duplicate of a superseded document
  is a trap. A duplicate of a document you are about to edit is a backup. Do not
  delete the second kind before the edit is verified.* My remediation order told
  CC to delete the `_1` duplicates as traps; one of them was the only surviving
  copy of `2026-09-04-update-entry.html` after a bad index-based edit, and had
  the hygiene item run before the edit rather than after, the file would have
  been unrecoverable.

---

## 1. The second signature — yours, and here is what would make it real

I drafted the adjudication. Standing rule 13 exists because a reviewer writing
up the disposition of their own findings grades them generously without
noticing. I have now made six errors in this cycle and written the entries
assessing all six. I am the wrong signatory twice over and signing it myself
would empty the rule of content on its first application.

What the signature attests to, so it is an act rather than a formality:

1. **Every ACCEPT actually landed on the page.** V1–V6 cover this mechanically;
   the signature is a person confirming the mechanical result was read.
2. **Each disposition matches what was actually decided**, not what reads well
   afterwards.
3. **Nothing was quietly dropped.** OR-018 changed disposition twice — NOT ACTED
   ON, then PARTIALLY ACTED ON, then closed. OR-007 is half-rejected. Those two
   are where a reader should look first.
4. **The RV entries are honest.** Read RV-01 through RV-06 hardest. They are the
   entries where I assessed my own errors, and a reviewer writing up their own
   mistakes will describe them as narrower than they were. If any of the six
   reads as tidier than what actually happened, that is the finding, and it is
   worth more than the entry it corrects.

If you sign without reading, the file records that two people looked when one
did — which is the same class of thing as a log paragraph dated before the
event it describes.

---

## 2. The confirm-review — also yours

An operator action, and it should follow the signature rather than accompany it.
It records that the outside review happened and was adjudicated. That statement
is only true once the adjudication is complete, which means after RV-06.

---

## 3. Email-parity and correction-history preflight — I have not opened these

I do not know what either check tests. Advising on them from their names would
be the seventh instance of the error this cycle has been about, so the first
step is a report, not a fix.

Two things worth flagging in advance, because both are live and either could
make these checks fire honestly:

- **Correction-history** plausibly tests rule 10 — that the log accounts for the
  page's stated update history. The log now runs 27 Aug, 28 Aug, 2 Sep, 4 Sep,
  9 Sep with the header at 9 September. If it checks that every dated heading
  has a corresponding change record, the change-set schema should satisfy it; if
  it checks something about entry ordering or the relationship between the
  header and the newest entry, that was rebuilt today and should pass.
- **Email-parity** compares the email summary against the page. `publish.py`
  already does this and the review prompt mentions it. The page has changed
  substantially across this round; the email almost certainly has not. If the
  email still carries the old scorecard, the "out by 0.05" line, the four-outlet
  count, or anything from the pre-9-September survival bullet, parity will fail
  correctly and the email needs rebuilding — which is work nobody has scoped.

Neither is a rubber stamp. Get the report first.

---

## CC block

```
TASK: Report on the two remaining preflight gates. Report only — change nothing.

For each of the email-parity and correction-history preflight items:

1. Name the check: the file and function that implements it, and what it
   actually tests — in the terms the code uses, not the terms the gate name
   suggests.
2. Its current state on page 321396fb2e01ca08: pass, fail, or blocked, with the
   exact output.
3. If it fails, the specific items failing, and for each whether the failure is
   in the page, in the email, or in the check's own keying (like the stale
   3.35 exclusion was).
4. Whether anything in this round's work is the cause — the log surgery, the
   change-set schema, the rebound sentences, the new source, or the date move.

Then, for email-parity specifically: report what the email summary currently
says about the scorecard, the outlet count, the survival intervals and the
correction history, and whether any of it still describes the pre-9-September
page.

Do not fix anything. Do not rebuild the email. Two of the six errors this cycle
came from acting on a description of an artifact rather than the artifact, so I
want the artifact before I advise.

Also, before either signature: add RV-06 to the adjudication (text supplied in
2026-09-09-closing-out.md), and the two process-document amendments it earns —
the caveat-is-not-a-check line beside failure 14, and the duplicate/backup
distinction in §13.
```
