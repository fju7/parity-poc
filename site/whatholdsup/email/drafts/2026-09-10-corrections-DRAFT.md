# DRAFT — the first correction email. NOT SENT.

**Assembled 10 September 2026. Nothing has been sent.**

**Scope is deliberate, not derived.** `sent.json` records four historical sends,
all with `covers: unknown`, so `update_email.outstanding()` returns **24**
corrections no send is known to have carried. Sending 24 would be an archive, not
a correction. This first send names exactly two, and derivation begins after it
from a real floor.

`covers:` when this is sent —

- cdk46 — *1 September 2026 — an observation we put under someone else's name, and a true conclusion with a false reason*
- melanoma — *9 September 2026 — an outside review, and a self-accusation that overstated what we did*

---

## Subject

> Two corrections to issues you have already read

## Body

> We got two things wrong in emails we sent you. Both are corrected on the pages;
> neither correction reached your inbox until now.
>
> ---
>
> ### We put a finding under the wrong researcher's name
>
> **What changed.** The email for issue two, *The Category Difference*, sent on
> 29 August, credited a point about confidence-interval width to "Jacot and
> colleagues" in *npj Breast Cancer*, 2018.
>
> **Why.** Two things are wrong with that sentence. The first author of that
> paper is **Marie-Laure Tanguy** — not Jacot, who is not an author on it in any
> position. And the point we handed them is ours: Tanguy and colleagues did not
> write about the width of a confidence interval. They computed how much
> statistical **power** each of these trials had to reach significance on overall
> survival at all. Their paper says: *"PALOMA-2 and MONALEESA trials have an
> almost similar power despite different allocation ratios, while MONARCH-3 has a
> more limited power."* All four trials came out under 70% power unless the gain
> in median survival exceeded twelve months. Their conclusion: if a significant
> survival improvement appears in some of these trials and not others, the
> difference *"might be more attributable to chance than to a truly different
> drug efficacy."*
>
> We found it when a gate run read the email against the page, and the operator
> obtained the full text after every automated route from here was refused.
>
> **What you should now believe that differs.** The argument in that issue stands
> and it is *ours to defend*, not a finding we can attach to someone else's
> paper. If you took the interval-width point as established by Tanguy and
> colleagues, it is not — it is our observation, and you should weigh it as one.
> What their paper establishes is that these trials were mostly too small to
> detect a survival difference at all: none of the four reaches 70% power unless
> the gain in median survival exceeds twelve months. Whether that helps or hurts
> the argument in that issue is yours to judge.
>
> The paper: Tanguy M-L, Cabel L, Berger F, Pierga J-Y, Savignoni A, Bidard F-C.
> *Cdk4/6 inhibitors and overall survival: power of first-line trials in
> metastatic breast cancer.* npj Breast Cancer 2018;4:14.
> DOI 10.1038/s41523-018-0068-4. PMID 29951582.
>
> ---
>
> ### We printed two different kinds of interval side by side
>
> **What changed.** The email for issue one, *The Melanoma Result*, sent on
> 4 September, gave an earlier analysis as "0.425 on nine deaths, with an **80%
> interval** of 0.179 to 1.004". A few lines above, it gave the later analysis
> as "the hazard ratio is 0.471 and the interval runs from 0.165 to 1.345" —
> with no width stated at all. That one was a 95% interval.
>
> **Why.** Both intervals for that hazard ratio sit in the same row of the same
> table in the same paper: *"HR — 0.425 · 80% CI 0.179 to 1.004 · 95% CI 0.114 to
> 1.584"*. We printed the narrower of the two, labelled it, and set it beside an
> interval we did not label. An 80% interval is narrower than a 95% interval
> computed from the same data; that is what the numbers mean, not a property of
> the result. **A reader had no way to see that the two were not comparable**,
> because only one of them carried a width.
>
> **What you should now believe that differs.** That result is **less certain
> than the email made it look**, not more. The 95% interval is **0.114 to
> 1.584** — wider than the five-year figure's interval, not tighter, and it
> includes 1. On nine deaths, that analysis does not establish a survival
> benefit, and if you came away thinking it pointed to one more firmly than the
> later data, that was our error and not the paper's.
>
> ---
>
> Both pages carry these corrections in their own change logs, with the dates
> they were made. If you would rather read the corrections than take our summary
> of them: whatholdsup.org/melanoma and whatholdsup.org/cdk46, at the bottom of
> each page.

---

## Notes for whoever sends this

- **Spell both names.** "Jacot" and "Marie-Laure Tanguy" both appear on purpose.
  A correction naming only the right name leaves a reader who remembers the wrong
  one unable to tell it is the same sentence.
- **Do not soften "not Jacot, who is not an author on it in any position."** The
  sentence is short because the correction is simple, and a subordinate clause is
  where this kind of thing goes to hide.
- **Do not explain how the wrong name got in.** We do not know. A guess inside a
  correction notice is a new unsourced claim in the worst possible place.
- **PART 3 GOES THROUGH THE PASSAGE STAGE BEFORE ANY SEND.** Hand-written prose
  about our own error, under time pressure, by the party that made it, is the
  exact class §5.5 exists for — and it is the one part of this email no
  derivation touches. The four questions, on both "what you should now believe"
  paragraphs, recorded like any other run. Done 10 September 2026; see below.
- **The two "what you should now believe" paragraphs are the correction.**
  Everything above each is what changed and why. If length has to come out, it
  comes out of the first two parts.
- **Both claims are verified against held bytes**, not against a summary: the
  Tanguy span at plain character 44,065 of source S024, sha `e49e76bb…`; the
  interval pair in the melanoma page's own source note and in the 9 September
  correction entry.
- **On sending, record it** in `backend/data/whatholdsup/sent.json` with
  `covers:` naming exactly the two headings above. Derivation begins from that
  row; until it exists, `outstanding()` still returns 24.


---

## The passage stage, run on part 3 — 10 September 2026

Part 3 is the one part of this email no derivation touches, and it is
hand-written prose about our own error by the party that made it. §5.5's four
questions, run on both *"what you should now believe"* paragraphs.

**Q1 — do any two sentences here contradict each other?** No. The two paragraphs
concern different issues and different errors; neither makes a claim the other
denies.

**Q2 — does any sentence assert a state another sentence or the store
contradicts?** No, and each claim is checked against held bytes rather than
against a summary:

- *"MONARCH-3 has a more limited power"* — verbatim in S024, sha `e49e76bb…`.
- *"none of the four reaches 70% power unless the gain in median survival exceeds
  twelve months"* — the paper's own statement, same document.
- *"might be more attributable to chance than to a truly different drug
  efficacy"* — verbatim, same document.
- *"95% CI 0.114 to 1.584"* — on the melanoma page and in its 9 September
  correction entry.
- *"an 80% interval of 0.179 to 1.004"* — in the email as sent, `5ef7890a…`,
  recovered from git by matching the recorded sha.

**Q3 — could a careful reader leave believing something false that no sentence
states?** This is where the wording changed. The first draft said *"What their
paper does establish is stronger for the piece"* — which tells a reader how to
feel about our own correction, inside the correction. A reader could come away
believing the error made the argument **better**, which no evidence supports and
which is the flattering direction. It now states what Tanguy and colleagues
established and ends *"Whether that helps or hurts the argument in that issue is
yours to judge."*

One thing checked and left: the interval paragraph says the result *"does not
establish a survival benefit"*. A reader might take that as *establishes no
benefit*. The next clause — the interval *"includes 1"* — is what distinguishes
them, and it stays unsoftened.

**Q4 — is a reader asked to hold anything in suspension longer than the passage
supports?** No. Each paragraph resolves inside itself: what we said, what is
true, what to believe now. Neither asks a reader to carry a premise across the
other.
