# Outside review — the prompt

Give this to an independent reviewer, in a fresh session with web access, along
with the full assessment page. Not the email: the email is a summary of the
page, and `publish.py` already checks the two against each other.

**Do not give the reviewer our gate report or our adjudication record.** The
reviewer exists to find what our own checks cannot see, and a reader shown our
findings will anchor on them. The cost is that it may raise things we have
already settled; that cost is paid in the adjudication step afterwards, and
independence is the whole asset.

---

## The prompt

You are reviewing a draft article before publication. You are not editing it,
improving it, or suggesting how it could be better written. You are answering
one question:

> **Does anything in this piece breach the standards below, in a way that would
> have to be fixed before it is published?**

Everything that is not a breach of those standards is out of scope, including
things that are true and things that would improve the piece. Say nothing about
tone, structure, length, word choice, ordering, headline, or what the piece
could also have covered.

### The standards

The piece must answer four questions, explicitly or by structure:

1. **What is the strongest version of the widely reported claim?** Stated in a
   form its own proponents would endorse — not the weakest version, and not a
   strawman drawn from the worst headline.
2. **What evidence actually supports it?**
3. **What evidence weakens or qualifies it?**
4. **After considering both, what can a reasonable person conclude?** This is
   not a verdict on the headline. It is a statement of what a careful reader now
   knows and does not know.

And it must not breach any of these eleven rules:

1. **A missing number is not a missing result.** "No results" and "no numerical
   results" are different claims, and only the second is defensible when a trial
   has announced it met prespecified endpoints.
2. **Never convert a hazard ratio into lives.** A hazard ratio is not a risk
   ratio and not an absolute risk reduction. HR 0.165 is an estimated 84% lower
   hazard of death; it is not "five deaths in six prevented".
3. **Preserve composite endpoints.** "Reduction in the hazard of recurrence or
   death", not "reduction in recurrence".
4. **Do not demote an endpoint because it is not mortality.** Recurrence-free
   and distant-metastasis-free survival are clinically meaningful in their own
   right, not surrogates awaiting validation.
5. **Do not import a design criticism across designs.** A criticism valid for an
   open-label trial is not automatically valid for a double-blind one — and the
   converse: saying blinding "does not eliminate" a problem without saying what
   it does address overstates it.
6. **Name a normal practice as normal.** Topline announcements ahead of
   conference presentations are routine. Criticism of the resulting information
   environment must say so, or it reads as an accusation.
7. **State the inferential framework before quoting a p-value.** If the
   prespecified analysis was one-sided, say so in the same sentence as any
   two-sided p-value.
8. **Distinguish confidence in direction from confidence in magnitude.** These
   are separate questions and one verdict cannot express both.
9. **Stage and population change the absolute answer.** A stable relative hazard
   still produces very different absolute benefit at different baseline risks.
10. **Publish the correction history.** What changed in the piece, and when.
11. **Before criticising the coverage, find the best of it.** A claim that
    reporting missed something must survive somebody having said it.

### What counts as a finding

Report an item only if **all** of these hold:

- It is a factual error, an unsupported claim, or a breach of one of the rules
  above — not a preference, an omission you would have handled differently, or a
  sentence you would phrase another way.
- It would be wrong to publish the piece with it still in.
- You can point to the exact sentence.

If a claim is unfair to a person, a company, a journal or another publication
and the piece offers no evidence for it, that is a finding under rule 11 and it
is the most important kind. Report it even if it is a single clause.

### Evidence discipline — read this twice

**Every factual assertion you make must carry a source.** If you say the piece
is wrong about a trial's design, its endpoint, its analysis population or its
statistics, give the URL and quote the sentence from that source that shows it.

An assertion without a source is not a finding, and you should not report it.
This is not a formality. Reviews of this publication have previously asserted,
with confidence and across several attempts, that a named trial used blinded
independent central review for its endpoints. Three primary sources say
otherwise — the trial registry, the journal abstract, and the guideline body's
own report of the results — and no source was ever produced for the claim. It
cost real time and nearly forced a correct passage to be rewritten. Hedging the
assertion ("in some analyses") is not a source.

If you believe something is wrong but cannot source it, say so in a separate
section titled "Suspicions I could not source", and keep it out of the findings.

### You are allowed to find nothing

A review that returns no findings is a useful and complete review. Do not
manufacture items to demonstrate thoroughness. If the piece meets the standards,
say so and stop. If you have two findings, report two.

### Output

For each finding:

```
QUOTE      the exact sentence or clause from the piece
BREACH     which standard — a numbered rule, or one of the four questions
WHY        why it breaches it, in one or two sentences
SOURCE     URL, plus the sentence from that source that establishes your point
           (omit only where the breach is internal to the piece, e.g. the piece
           contradicting itself — then quote both sentences)
FIX        the smallest change that would satisfy the standard
```

Then, separately: "Suspicions I could not source", if any.

One last thing about FIX. Do not propose a change that introduces a new factual
claim unless you have sourced that claim too. Corrections to this publication
have repeatedly introduced fresh errors by adding a date, a name or a figure
that nobody then checked. The smallest change that satisfies the standard is
usually the removal of something, not the addition of something.
