# Verification addendum — after the rebased directive was applied

Source of truth for everything below: `carlino-et-al-2026-three-year-update-…pdf`
(S007), read in full from the PDF, and `review_packet.py`, both on the machine.

---

## 1. C2(a) — you were right, and I was wrong. Confirmed against Table 1.

The three-year paper reports, in a single table row:

> **RFS: HR 0.510 · 80% CI 0.351 to 0.743 · 95% CI 0.288 to 0.906**

The 80% interval belongs to the **three-year HR 0.510**, exactly as you said. It
does not belong to the 2023 HR 0.561.

I also searched the paper for any 80% interval attaching to the 2023 readout.
There is none. The only nearby values — HR 0.564 (80% CI 0.334–0.953) and HR
0.571 (80% CI 0.329–0.993) — are the TMB-high and TMB-low **subgroup** hazard
ratios from the three-year analysis, and have nothing to do with the 2023
primary readout. My proposed caption would have put a number on a result it was
never computed for, sourced to a document that does not contain that pairing.

That is the second error I have made in this chain, and both are the same error:
taking a figure computed in one context and setting it down in another. It is
the error this article exists to describe. Refusing it was correct, and your
substitute — explaining the 80/95 distinction without the attribution — is the
right fix.

---

## 2. N2 now has its missing number, and it points the other way

The Sept 4 page says:

> "The three-year paper reports a hazard ratio of 0.425 on nine deaths, with an
> **80% interval** of 0.179 to 1.004; the five-year analysis reports 0.471 on
> fourteen, with a **95% interval** of 0.165 to 1.345. Both are wide enough to
> hold a large benefit and a small harm at once."

The paper prints **both** intervals for that hazard ratio, in the same row:

> **OS: HR 0.425 · 80% CI 0.179 to 1.004 · 95% CI 0.114 to 1.584**
> (events 3.7% [4/107] v 10.0% [5/50])

So the like-for-like comparison is available and is not the one on the page:

| | three-year | five-year |
|---|---|---|
| HR | 0.425 | 0.471 |
| 95% CI | **0.114 – 1.584** | 0.165 – 1.345 |
| deaths | 9 | 14 |

At 95% the three-year interval is the **wider** of the two — which is what you
would expect on nine deaths versus fourteen, and the opposite of the impression
the 80%-versus-95% presentation gives. Using the narrower instrument for the
sparser analysis makes the weaker evidence look tidier than the stronger.

**Suggested replacement**, using only figures in a document already held:

> "The three-year paper reports a hazard ratio of 0.425 on nine deaths, 95% CI
> 0.114 to 1.584; the five-year analysis reports 0.471 on fourteen, 95% CI 0.165
> to 1.345. The earlier interval is the wider of the two, which is what nine
> deaths buys you against fourteen. Both are wide enough to hold a large benefit
> and a small harm at once."

If the 80% interval is kept anywhere, it should be labelled as the trial's own
standard — one-sided alpha 0.10 — rather than set beside a 95% interval unmarked.

---

## 3. C4(a) can now be sourced to the trial's own paper, not only to Spruance

The three-year paper's methods state:

> "…estimated using a **Cox proportional hazards model** with treatment group as
> a covariate, stratified by disease stage"

So the assumption is named in the trial's own publication. The proportional
hazards note no longer needs to lean on a 2004 methods paper for authority — it
can say the trial's analysis assumes a constant ratio because the paper says so.

That matters more than it did on Monday, because this page now carries three
estimates that move with follow-up: OS 0.425 → 0.471, DMFS 0.384 → 0.411
(62% → 59%), RFS 0.510 → 0.510. Two of the three drift toward the null as
follow-up lengthens. That is either noise or non-proportionality, and the piece
currently offers the reader no way to tell which.

---

## 4. S012 — the generator is exonerated, so the gap is in the store

`review_packet.py` builds Appendix B like this:

```python
for s in store.sources("melanoma"):
    a = s.get("access") or {}
    st = (a.get("state") if isinstance(a, dict) else a) or "not_opened"
    ...
    B_rows.append("| %s | %s | %s |%s" % (s["id"], st, ...))
```

It iterates whatever `store.sources()` returns and prints `s["id"]` verbatim. No
filter, no renumbering, no skip condition. **The packet generator cannot create
an id gap.** So S011 → S013 reflects the source store itself: S012 was either
retired from the store or never written to it.

That narrows the open question by half. It is now a question for
`source_store` / the store's backing data, not for the packet builder. Worth
resolving, because Appendix B is the denominator for every "in the coverage we
hold" claim on the page, and a silently retired document is exactly the shape of
thing that denominator should not lose quietly.

You were right not to invent an answer.

---

## 5. Accepted without reservation

- **A2.** Your correction is better than my instruction. I told you to fix an
  enumeration; you found that the checks test span presence, figure provenance
  against held documents, and reader-facing representation of binding sources —
  and never classify a document as news versus primary. Describing what the
  checks actually do, rather than repairing the list, is the right call, and it
  is the same lesson as the 2 September correction: the check was precise and
  the prose around it was not.
- **D6.** S003 and S008 distinct, S023 already `full_text_held` — my instruction
  to change it was stale.
- **Publication date.** Leaving it at 4 September until the revision actually
  publishes is correct.

---

## 6. Independent verification of the revision

I read `melanoma.revised.html` (70,152 bytes) directly. Results:

**All six Block A errors are gone.** Zero hits for "the register says so",
"drifted out from 0.288", "45.2% on the combination versus 44%" as a paired
contrast, "costs nothing, and it does", and "in whichever direction the numbers
point".

**The EORTC 18071 insertion is verbatim accurate** against the NEJM abstract:
"65.4% versus 54.4% at five years, HR 0.72 (95.1% CI 0.58–0.88), p=0.001",
prespecified secondary endpoint, 10 mg/kg, five immune-related deaths. Every
figure matches PMID 27717298. Sources entry carries DOI, PMID and PMCID.

**Applied and correct:** A3, A4, A5, A6 (wording matches the recomputation),
C1, C2, C3, C4(a), C4(b), D1, D3 (including the DMFS-is-investigator-assessed
note I flagged), D4, D5. Both scores unchanged at 3.94 and 1.0.

**Two improvements you made that I did not ask for, and that are right:**

- Line 90 now reads "the interval crossed 1.0, so **on a two-sided 5% criterion**
  'no effect' could not be ruled out." That names the standard being applied
  instead of leaving it implicit — it is the fix C2 was reaching for and did not
  articulate.
- Line 108 now qualifies the doubling relation: "For a symmetric test, **and when
  the one-sided test points the way the effect actually went**, the two-sided
  p-value is about double the one-sided one." That condition was missing from the
  Sept 4 text and from my directive. It is genuinely necessary and I did not
  catch it.

**One directive item was not applied and was not reported: D2.**

Reproducibility 4, Consensus 4 and Recency 5 still carry no reasoning anywhere
on the page. The scoring paragraph still explains only rigor and data support.
Those three dimensions contribute 0.80 + 0.60 + 0.50 = **1.90 of the 3.15
numerator behind the 3.94** — 60% of that score — and 0.45 of its 0.80
denominator. More than half of "is the effect real" rests on judgements a reader
is invited to disagree with and given nothing to disagree with.

This is not a challenge to the omission; skipping it may have been deliberate.
It is only that the exception report listed three exceptions and this was a
fourth. If the reason was that the three scores are hard to justify, that is
itself the finding.

**One style nit, take it or leave it.** The A3 replacement reads "…the interval
read 0.294–0.887 — both bounds came in — the upper from 0.906 to 0.887, the
lower from 0.288 to 0.294 — so the interval narrowed only slightly. So the
interval stopped including 1.0 at year three…" Three em-dashes in a row, then two
consecutive sentences opening with "So". Suggest: "…read 0.294–0.887. Both bounds
came in, the upper from 0.906 to 0.887 and the lower from 0.288 to 0.294, so the
interval narrowed only slightly. The crossing was resolved at year three, not
year five…"

**One live upgrade.** Section 2 above supersedes the C2(b) text you applied. The
page now says "at 95% it would be wider still" — true, and the actual figure is
in the paper you hold: **95% CI 0.114 to 1.584**, printed in the same table row
as the 80% interval. With both at 95%, the three-year interval (0.114–1.584) is
wider than the five-year one (0.165–1.345), which is what nine deaths buys you
against fourteen. Replacing the hedge with the number is a strict improvement and
needs no new source.

---

## 7. Correction to section 6 — D2 *was* applied, and I misread my own evidence

Issued 2026-09-08, after the implementation stopped on it rather than applying
the item I raised.

**What section 6 says is wrong.** "One directive item was not applied and was not
reported: D2 … Reproducibility 4, Consensus 4 and Recency 5 still carry no
reasoning anywhere on the page. The scoring paragraph still explains only rigor
and data support." All three sentences were on the page when I wrote that. They
were added by the same 9 September pass I was verifying, and the change report I
had in front of me records them under **Score rationale — Added**, verbatim.

**How I got it wrong.** I grepped the scoring paragraph and read it through
`cut -c1-400`. The paragraph is 1,013 characters of plain text, 1,152 as an HTML
element, and the three sentences begin at plain character 484. [figure corrected 2026-09-09; this originally read 2,116, which was never measured — see RV-08] I saw a paragraph that ended after data support and
recorded an absence. What I had actually observed was the right-hand edge of my
own terminal.

That is the third error I have made in this chain and it is the same error as the
other two — RV-01, where I queried the `analyses` field and not the one that
decided the question, and RV-02, where I took an interval from one context and
set it down in another. All three are a partial view of a document treated as a
fact about the document. It is standing rule 2, it is the error this issue exists
to describe, and I have now committed it three times for three out of three of my
errors in this round while checking a page whose subject is that error.

**What was actually missing, and still was.** Appendix A carried no inference
record for any of the three. It covered the two composites, rigor and source
quality and stopped there. So the reasoning was on the page and its provenance
was not, which is a real half of OR-018 and the half worth acting on. Three
records have now been added: reproducibility on S001 and S004, consensus on the
eight coverage sources in Appendix B that report the Phase 3 announcement, and
recency on the datelines of S001 and S002.

**What must not happen.** The three sentences I drafted for the operator's
resolution should not replace the ones on the page. Mine were worse on two of the
three. My recency sentence ends "Nothing newer exists on this programme," which is
an unscoped universal negative I should not have written; the page's sentence
asserts what the evidence is instead of what it is not. My consensus sentence
buys a scoped negative and an Appendix C entry to maintain where the page's
sentence — "the held sources agree on the directional Phase 3 result" — is
already scoped to the coverage we hold and says the same thing positively. The
prose stands. Only the records were added.
