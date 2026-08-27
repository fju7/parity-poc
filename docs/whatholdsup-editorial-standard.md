# What Holds Up — editorial standard

What this publication does is not fact-checking. Almost everything in the
coverage we examine is literally true. Nor is it contrarianism: the claim we
examine is often right.

What it does is **decompose confidence** — show a reader what we know strongly,
what we only suspect, what cannot yet be quantified, and what further evidence
would change the answer.

That is the product. Everything below serves it.

---

## The four questions

Every issue must answer these, explicitly or by structure:

1. **What is the strongest version of the widely reported claim?**
   Not the weakest, not a strawman drawn from the worst headline. If we cannot
   state the claim in a form its own proponents would endorse, we are not ready
   to examine it.
2. **What evidence actually supports it?**
3. **What evidence weakens or qualifies it?**
4. **After considering both, what can a reasonable person conclude?**

Question 4 is not a verdict on the headline. It is a statement of what a
careful reader now knows and does not know.

---

## The occupational hazard

> Once your job is finding what conventional coverage missed, you have an
> incentive to make the missing qualification sound more devastating than it
> actually is.

This is the specific way this publication will fail if it fails. It is the
mirror image of the bias we exist to catch in others, and it is harder to see
in ourselves because each individual sentence is defensible.

The test: **would this sentence survive being read aloud by someone who
believes the underlying result?** Not "is it true" — every sentence we publish
must be true — but "is the impression it leaves proportionate to the evidence."

---

## Standing rules

These come from real errors. Each was made, caught, and is recorded in
`backend/tests/fixtures/factcheck_known_errors.json`.

### 1. A missing number is not a missing result

"No results" and "no numerical efficacy results" are different claims and only
one of them is defensible when a trial has announced that it met prespecified
endpoints. Write the second.

The same applies to "published nothing", "the quantitative content is nil", and
every construction that converts *we have not been shown the magnitude* into
*we have not been shown anything*. Our argument is about magnitude. Say that.

A large blinded randomised trial clearing prespecified endpoints against an
active comparator is consequential evidence. **"We do not yet know how large
the benefit was" is a completely different statement from "we do not know
whether it worked",** and a piece that blurs them has taken a side.

### 2. Never convert a hazard ratio into lives

A hazard ratio is not a risk ratio and is not an absolute risk reduction. HR
0.165 is an estimated 84% lower hazard of death. It is **not** "five deaths in
six prevented", and any sentence that converts a ratio into a count of people
is wrong unless the absolute rates are given and the arithmetic is shown.

State a confidence interval as what it is:

> The interval is extraordinarily wide: compatible with anything from a very
> large reduction in the hazard of death to roughly a 35% increase.

If we explain a distinction to readers in one paragraph, we may not violate it
in the next. A reader who understood our explanation would catch us, and that
is the worst way to lose one.

### 3. Preserve composite endpoints

"49% reduction in the hazard of recurrence or death", not "49% reduction in
recurrence". "59% reduction in the hazard of distant metastasis or death", not
"59% reduction in metastasis". The shorthand is what the coverage we criticise
does. Precision here is the thing we are for.

### 4. Do not demote an endpoint because it is not mortality

Recurrence-free and distant-metastasis-free survival are clinically meaningful
outcomes in their own right, not surrogates awaiting validation. FDA has
approved adjuvant melanoma therapies on RFS. For a patient whose high-risk
melanoma has been resected, not developing metastatic disease is the outcome,
not a stand-in for one.

"The endpoint people actually care about" is a value judgment dressed as a
methodological one. The accurate framing is that RFS and OS answer **different
questions**, and a trial that answered the first has not failed to answer the
second — it has not been asked to.

### 5. Do not import a design criticism across designs

A criticism that is valid for an open-label trial is not automatically valid
for a double-blind one. Blinding is the mechanism that answers differential
assessment; saying it "does not eliminate the problem" without saying what
residual mechanism remains is an assertion, not an analysis.

An independent review committee **relocates** clinical judgment to blinded
central assessors. It does not remove it. Where an endpoint is
investigator-assessed, say so neutrally and say what the design does about it.

### 6. Name a normal practice as normal

Topline announcements ahead of conference presentations are standard. Where we
criticise the information environment that results, we must say that the
practice is routine, so the criticism lands where it belongs — on the certainty
with which third parties report numbers that do not come from the trial being
announced — and not as an insinuation about the sponsor's conduct.

Any claim about anyone's *conduct* — "failed to", "quietly", "buried", "nobody
reported" — requires instances. This applies to companies, regulators and other
publications equally.

### 7. State the inferential framework before quoting a p-value

If the prespecified primary analysis was one-sided, say so in the same sentence
as the two-sided p-value. Otherwise a reader may reasonably infer that the
sponsor chose the test after seeing the data, which is an accusation we have
not made and cannot support.

Likewise, "if the interval includes 1.0 then 'this treatment does nothing' is
among the possibilities" is a good lay explanation and too absolute where a
prespecified one-sided test governed the inference. Say instead that the result
would not meet the conventional two-sided 5% standard.

### 8. Distinguish confidence in direction from confidence in magnitude

These are separate questions and a single verdict cannot express both:

- **Direction** — does the intervention do anything, and which way?
- **Magnitude** — how much, in relative and absolute terms, and for whom?

A positive topline from a large blinded trial can warrant high confidence in
direction and near-zero confidence in magnitude at the same time. A rubric, a
score or a headline that collapses the two will misrepresent one of them.

Where the two diverge, say so in those words. It is usually the most useful
sentence in the piece.

### 9. Stage and population change the absolute answer

A relative hazard broadly stable across populations still produces very
different absolute benefit at different baseline risks. Where a later trial
extends to a lower-risk population than the one that produced the quoted
figures, that is material and belongs prominently, not in a caveat.

### 10. Publish the correction history

What changed in the piece, and when. Not how our process failed — that belongs
in the repository — but what a reader who saw an earlier version needs to know.
This is the behaviour we ask readers to value, so we demonstrate it.

---

## Before an inquiry starts

An inquiry begins from **a claim that could turn out to be false**, not a
subject someone finds interesting. "Does the vaccine add benefit over
pembrolizumab alone" is an inquiry. "Cancer vaccines" is a reading list.

Measured on our own corpus: topics built around one falsifiable question leave
2% of their evidence bearing on nothing askable. Topics built around a subject
heading leave 18% to 26%. The difference is not editorial taste, it is whether
the piece has something to be wrong about.

---

## Before an issue publishes

- `factcheck_draft.py` exits 0.
- The four questions are answerable from the piece.
- Every rule above has been read against the draft, not recalled from memory.
