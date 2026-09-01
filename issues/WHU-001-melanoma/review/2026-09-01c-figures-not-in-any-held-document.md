# Three figures on the live melanoma page are in no document we hold

Found: 2026-09-01, by three model binders reading sources for spans, then
verified by hand against the held bytes before anything was written here.

Every held document for this issue was searched: S001-S008, all eight held.
The searches are exact-string, after the normaliser that handles The Lancet's
middle dot. What follows is what the documents print, not what a check said.

---

## 1. "68.8% recurrence-free at five years" — page line 99

**The page:** "The **absolute** figures from the same trial, at five years:
**68.8%** of combination patients were recurrence-free versus **49.1%** on
pembrolizumab alone. That is a gap of roughly **20 percentage points** at the
five-year mark."

**S004, the cited five-year paper (Journal of Clinical Oncology, 1 June 2026,
full text held), prints:**

> The four-year RFS (95% CI) was 72.4% (62.2 to 80.2) with intismeran plus
> pembrolizumab versus 49.1% (33.3 to 63.0) with pembrolizumab.

- `68.8` appears in **none of the eight held documents**.
- `49.1%` is the **four-year** figure, and its pair is **72.4%**, not 68.8%.
- The Figure 1A curve labels for the combination arm are 80.4, 78.3, 73.8,
  72.4; for the control arm 62.2, 55.6, 60.0, 49.1. There is no 68.8 on either.
- The true gap at that time point is **23.3 points**, not "roughly 20".
- The time point is **four years**, not five.

Three errors in one sentence: a figure that exists nowhere, a mislabelled time
point, and an arithmetic consequence of the first.

## 2. "92.2% alive versus 71.3%, CI 84.2-96.3 and 35.4-89.6" — page line 160

**The page:** "Reported as survival rates the same five-year analysis reads
**92.2%** alive versus **71.3%** — 95% CI 84.2&ndash;96.3 and 35.4&ndash;89.6,
as *The ASCO Post* reported them from the five-year data."

**S004, Figure 1C, prints:**

> 92.2% (84.2 to 96.3) 85.6% (70.5 to 93.3)

- `92.2% (84.2 to 96.3)` is right.
- The comparator is **85.6% (70.5 to 93.3)**, not 71.3% (35.4-89.6).
- `71.3` is in S004 exactly once, as the lower bound of the RFS curve's
  **80.4% (71.3 to 86.9)** — a different endpoint on a different figure.
- `35.4` and `89.6` appear in **none of the eight held documents**.
- **S006 is The ASCO Post, and its full text is held.** It contains none of
  92.2, 71.3, 85.6, 35.4. The attribution is to a document that does not carry
  the figures attributed to it.

This one also changes the argument that follows it. The paragraph says "A large
observed gap, but one the interval shows the data can neither confirm nor rule
out." The observed gap is **6.6 points** (92.2 vs 85.6), not 20.9.

## 3. "one-sided nominal p = 0.0075 in the 20 January 2026 topline" — lines 160, 177

**The page:** "the one-sided 0.0075 in the January topline" and "The companies'
five-year topline of **20 January 2026** reported **one-sided nominal
p = 0.0075**."

- `0.0075` appears in **none of the eight held documents**.
- No January 2026 topline appears in this issue's source list at all. The
  sources run S001-S008; none is dated January 2026, and no held document
  contains the strings "January", "nominal" or "one-sided" in the two company
  releases (S002, S005) or The ASCO Post (S006).

This is not a wrong figure. It is a **document the page describes, dates and
quotes, which has no entry in the ledger.** The second half of that section
turns on it.

---

## What this says about the checks

None of the three was caught by a check. All three are of the same shape and it
is a shape nothing here tests for:

> **a figure that is in no held document at all.**

B2 answers "is this span in the source this row names" — but only for a
sentence somebody has already bound. B12 compares precision against a cited
source. B9 reconciles anchors against the ledger. Not one of them asks the
question that would have caught all three on the day they were written: *does
this number appear anywhere in anything we hold?*

That check is cheap, it needs no binding, and it runs over every figure on a
page in one pass. It is B13, and it should exist before the next issue.

Its honest verdict on a hit is not "true" and on a miss is not "false" — a
figure can be absent because the source is not held (see the two entries
below, which are exactly that). The verdict is: **this figure is in nothing we
hold, and here is why that is or is not expected.**

---

## Two the binders flagged that are NOT errors

Recorded because the reason they are not errors is the reason the checks exist.

**cdk46, the MONARCH 3 progression-free row: `HR 0.54 (0.41-0.72)`.** The binder
compared it against S003, the *Ann Oncol 2024 final overall-survival* paper,
which restates the updated primary-objective PFS as 28.2 vs 14.8 months,
HR 0.540 (0.418-0.698). The page's row is labelled *primary analysis, JCO 2017*
— a different readout of a different data cut. The binder checked the wrong
document, which is the MEL-01 failure again.

But the row is **not checkable either**: S002, MONARCH 3's 2017 primary paper,
is `fragment_only`. Nobody holds it. Acquiring it is the action; calling the row
wrong is not.

**deskilling, "Residents asked for the AI in 70% of cases".** The binder read
S034, a Rad Insight blog post, which attributes a 70%-request figure to
*Mascagni and colleagues*, a different 2025 chest X-ray study. Our paragraph is
about *Savardi*, read at source. Two documents, not a contradiction.

The finding underneath it is a different one, and it was **already caught**.

Savardi *is* listed on the page, as a Primary source, with its DOI and a note
recording that it was read at source. What it does not have is an entry in
`sources.json` -- and B9 reports exactly that, as a BLOCKED finding:

    https://doi.org/10.1186/s13244-024-01893-4
        no source entry, and no held document prints this identifier

Three more on issue three (the ESMO review, the JAMIA crossover study, and a
Nature Medicine paper) and three on issue two, including the *Cancers* 2023
reconstructed-patient-data comparison whose source note alone carries eleven
figures. Both pages are gated on these; neither can publish while they stand.

This was written up here first as a blind spot in B9, on the strength of one
binder's report, and it is not one. Checking cost two minutes and the claim was
wrong. Recorded because it is the same failure as the two above it: **a finding
about a document, produced without opening the thing that already knew.**

What B13 adds over B9 is not the missing source entry. It is that the figures
of a blocked source are ON THE PAGE while it is blocked -- eleven of them in
that one *Cancers* note -- and until now nothing counted them.

The one claim above that survives checking: "the authors list **eleven**
limitations of their own, and the largest is..." is about S021, Budzyn, which
is `fragment_only`. The 795-to-1,382 doubling is held only as *outside*
criticism (S035, Science Media Centre). Nothing held supports "the authors list
eleven", or that this was the largest of them. That is a live attribution to a
document nobody holds, and no check reports it, because the page cites S021
correctly and B9 only asks whether the ledger knows the link.
