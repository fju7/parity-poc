# What Holds Up — choosing an issue

The editorial standard says how to write one. This says what to write about,
and what to decline.

---

## The subject of an inquiry is a claim, not a topic

Not "CDK4/6 inhibitors". Not "cancer vaccines". A sentence someone could be
wrong about:

> The three approved CDK4/6 inhibitors are broadly interchangeable.
> The vaccine adds benefit over pembrolizumab alone.

If it cannot be false, it is a reading list.

Measured on our own corpus: topics built around one falsifiable question leave
2% of their evidence bearing on nothing askable. Topics built around a subject
heading leave 18–26%. This is not a matter of taste.

## The five tests

An issue must pass all five.

**1. Somebody acts on it.**
A person takes a drug, chooses between two, changes a habit, forms a view that
moves a vote or a purchase. The test is whether anyone would do anything
differently for having read us. If not, it is trivia, however interesting.

The best issues come from a real question someone actually asked. Issue two
exists because a reader wanted to know how the drug his wife was taking
compared with the alternatives, and could not find out. That is the shape.

**2. The claim is in wide circulation and is plausible.**
We are not in the debunking business. A claim that is obviously false is
somebody else's easier job, and writing it makes us the publication that
catches out fools rather than the one that clarifies hard things. The claim
should be one a careful person could hold — ideally one we half-hold ourselves
at the outset.

**3. Public evidence exists to say something definite about confidence.**
Not necessarily about magnitude — "direction established, size unknown" is a
publishable answer and often the most useful one. But there must be enough to
distinguish what is known from what is assumed. If the honest answer is "nobody
knows" with nothing to add about why or what would settle it, there is no
piece.

**4. It is not already available in one careful article.**
Rule 11. Run `factcheck_draft.py --survey` before committing. If somebody has
written it well, either the piece changes shape or it does not run. Finding
that out costs one call.

**5. We can source it properly.**
The evidence that settles a claim is not the same as the evidence about its
subject: head-to-head trials, network meta-analyses, real-world comparisons,
negative results, and the methodological critiques of the studies everyone
cites. If those exist and we cannot reach them, we cannot do the piece.

## Disqualifiers

- **It would function as individual advice.** We say what the evidence shows
  and how confidently. We do not tell a reader what to take, sell or do. Where
  a piece touches a live personal decision — and the good ones do — it must
  leave the decision with the reader and their clinician.
- **The answer needs expertise we cannot hand over.** If a reader cannot follow
  the reasoning after we have explained it, we are asking for trust, which is
  the thing we exist to make unnecessary.
- **Our own evidence base is thin and cannot be repaired within scope.** Better
  to decline than to publish confidence we do not have. See the standing note
  of 2026-08-27: a corpus will support a proposition the wider literature
  refutes, if it lacks the studies that do the refuting.

## Two genres, and knowing which one you are writing

**A — the number does not come from where you think.**
Pegged to a news event. A claim enters circulation, gets repeated with borrowed
figures, and the provenance blurs. Issue one. Time-sensitive, and the value
decays as better coverage catches up.

**B — the comparison everyone makes is not supported.**
Not pegged to anything. A standing belief that looks settled and is not, or
looks contested and is not. Issue two. Evergreen, harder to research, and
better suited to a subscription: it is worth reading a year later.

A cadence built only on A is a race against wire services. A publication of
mostly B, with A when something breaks, is a different and more defensible
product.

## The order of work

1. **Claim.** State it so it could be false. Write it down before searching.
2. **Survey.** `--survey` first. Who has covered this well, and what would we
   add? This can end the inquiry, and that is a success.
3. **Source to the claim.** Deliberately seek what could refute it: head-to-head
   evidence, comparative syntheses, negative trials, methodological critiques.
   Signal's corpus is a place to find a claim, not to settle one.
4. **Decompose confidence.** Direction and magnitude separately. What is
   established, what is contested, what is unquantified, what would settle it.
5. **Draft**, then the six-role gate, then read against every rule in the
   editorial standard rather than recalling them.

## The recurring question a reader should be able to answer afterwards

Not "was the headline right". Rather: *how much of this is known, how do we
know it, and what would change the answer.*
