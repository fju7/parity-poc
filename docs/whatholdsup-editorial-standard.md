# What Holds Up — editorial standard

**Standard version 1.1** — 2026-08-28. Four questions, eleven rules, and a stopping rule.

Bump the minor version when a rule is refined, the major version when a rule is
added or removed, and record the version in the issue's `issue.json` and in
every review. A review means "reviewed against the standard as it stood that
day". An old review must not silently acquire today's standard, and a rule
added after issue one was published is not a finding against issue one.

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

## What stops publication, and what does not

Every finding gets a class, and the test is one question: **if a reader found
this after publication, would we have to print a correction?**

| Class | Blocks | What it is |
|---|---|---|
| FACT | yes | A figure, date, name, endpoint or attribution a source contradicts |
| CONTRADICTION | yes | The piece disagreeing with itself |
| THIRD_PARTY | yes | A claim about someone else's conduct, offered without evidence |
| CALIBRATION | **no** | Phrasing, ordering, emphasis, degree |

CALIBRATION findings are recorded and the piece publishes. This is not a lowered
bar; it is the recognition that the previous bar could not be cleared. Across
six checks of issue one, factual errors went 3, 3, 1, 0, 0, 0 — and the total
number of findings did not fall, because what kept arriving was wording. There
is always a better available phrasing, so a gate that blocks on phrasing never
opens, and the piece sat unpublished for three runs with nothing wrong in it.

The risk this creates is obvious: CALIBRATION becomes the label that lets a real
error through. That is why `factcheck_recall.py` now checks the labelling and
not only the detection — every error seeded into the fixture is one that would
require a correction, so any of them labelled CALIBRATION is a failure the test
reports louder than a miss. A miss is silence. A mislabel is a false all-clear.

---

## Standing rules

These come from real errors. Each was made, caught, and is recorded in
`backend/tests/fixtures/factcheck_known_errors.json`.

### 0. Write nothing we have not read, and mark every inference

Two rules, and they come before the other eleven because they are about the
draft rather than about the analysis.

**Nothing enters a draft unless it rests on a document we hold and have read.**
Not remembered, not inferred from an abstract, not carried over from an earlier
sentence of our own. The binding row is written when the sentence is written,
not recovered afterwards by a check.

**Every inference is declared as one, and shows its work** — which held
documents it stands on, and the step from those to the claim, written out in a
sentence a reader could disagree with.

Both are enforced: `bindings.py` refuses to pass an issue whose new sentences
have no span, no declared kind, or an inference with no premises. Their tests
are `backend/tests/test_whatholdsup_rules.py`, and those tests exist to make the
rules **fail**, because a check that has only ever passed has not been tested.

#### Why these are first

Issue one's second page gate returned eleven real defects. Two were of the kind
our string checks look for — a span that was not in the document it cited. Nine
were not: a figure with no citation, an inference presented as a report, a
subheading contradicting the paragraph beneath it, a claim about what other
outlets said that no held article supported. Not one of those can be caught by
asking "is this string in that document", because the sentence was written
before anyone opened a document. Tested against that corpus, these two rules
would have prevented ten of the eleven.

The gates are not where mistakes should be found. They are the second net.

#### And why they are in code

Both rules were **already in this repository** when the gate found those
defects. `bucket` — the field that declares whether a sentence is a report or
an inference — had existed since the binding row was designed, and was null on
all eighty-five sentences of issue one. "Empirical sentences bound" had been a
WARN for weeks. The deletion rule, the rule that a correction is written from
the source record, and `undefined_states` were the same: each written down,
each gating nothing, and each followed by the error it described.

A rule that does not block is a rule that will be broken by whoever is tired.

#### No exemption for what was already written

The rules apply to every empirical sentence on every page of all three issues.
Nothing is grandfathered.

The first implementation did grandfather. The reasoning was that blocking 318
sentences would stop three issues and teach the operator to waive the check —
which is the reasoning behind every waiver anyone has ever granted, and the
editor rejected it in one line: given the state of the drafting, every sentence
in all three articles is to be revalidated or rewritten.

The exemption had already proved him right before he said it. Drawn the obvious
way — "everything unbound today" — it excused a sentence written that same
afternoon, one of two the gate had never examined. Redrawn from git it still
excused sixty-four sentences whose only claim to exemption was that nobody had
checked them yet. A rule whose scope is *not the things we already did* is not
a rule.

So the backlog is the honest number, printed on every run:

| issue | sentences | bound | to revalidate |
|---|---|---|---|
| melanoma | 85 | 17 | 68 |
| deskilling | 112 | 3 | 109 |
| cdk46 | 168 | 27 | 141 |

Zero of the 365 declare whether they are a report or an inference. Nothing
publishes until its own column reads zero. A sentence leaves that column by
being bound to the words it rests on, by being declared an inference and shown,
or by coming off the page — and the third is a legitimate outcome, not a
failure.

---

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

### 11. Before criticising the coverage, find the best of it

Sample deliberately for the outlet that got it right, and name it. A claim that
"reporting missed X" has to survive somebody having said X.

If careful coverage exists, the piece's claim is **not** "they missed this". It
is: *here is the layer beneath what even the careful reporting gives you.* That
is a stronger footing and an honest one, and it is usually the more interesting
piece.

This rule exists because issue one failed it. Its framing rested on a reader
meeting "49%" and reasonably taking it for a phase 3 figure. A Dispatch reader
would not have: that piece attributed the 49% and 59% to the phase 2 trial
explicitly, preserved the composite endpoints — "recurrence or death", not
"recurrence" — and stated that the phase 3 numbers had not been released.
BioPharma Dive and Dermatology Times were also explicit. We had not looked.

The analysis survived. The framing did not deserve to. And note which way the
comparison ran: the Dispatch preserved a composite endpoint in a
general-interest newsletter where our own email used the shorthand. We do not
get to hold others to a standard we are still learning to meet.

`factcheck_draft.py --survey "<topic>"` runs this search before a draft exists,
which is the cheap moment to discover the coverage is better than assumed.
Afterwards the framing is already built and the pull is to defend it.

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

- Rule 0 passes: `bindings.py <slug> preflight` shows both writing rules OK,
  with no sentence left to revalidate. This is checked FIRST. Running the roles
  over a draft whose sentences rest on nothing spends money to rediscover that
  they rest on nothing.
- `factcheck_draft.py` exits 0 — six roles, including COVERAGE.
- `--survey` was run BEFORE drafting, not after.
- The four questions are answerable from the piece.
- Every rule above has been read against the draft, not recalled from memory.
