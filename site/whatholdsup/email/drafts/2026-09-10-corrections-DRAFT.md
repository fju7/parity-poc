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
> **Why you are hearing about a 29 August error on 10 September.** We found both
> errors quickly and corrected the pages the same day. We did not tell you for
> twelve days because we had no way to send a correction — no mechanism existed
> for it, and the record of what we had emailed and when did not exist either.
> Both were built this week. This is the first thing they have been used for.
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
> **When we found it.** The same day it went out. Our own record has said since
> 29 August that Jacot is not an author of that paper, and the page was corrected
> that day. What a check found this week was not the wrong name — it was that the
> email carrying it had never been corrected, and that nothing in this system
> connected a correction on a page to a message already in an inbox.
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
> the result. **A reader had no way to see from the email that the two were not
> comparable**,
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

## The passage stage, run on the whole email — 10 September 2026

The email changed materially after its last run: a delay paragraph added, the
"when we found it" paragraph rewritten, an effort claim cut, and two words added
to the comparability sentence. Re-run on the whole body, not part 3 alone.

**Q1 — do any two sentences contradict each other?** No — and one pair was
checked closely, because it was near-contradictory before this revision. *"We
found both errors quickly and corrected the pages the same day"* and *"neither
correction reached your inbox until now"* are consistent only because the
mechanism sentence sits between them; without *"we had no way to send a
correction"* they read as an admission of twelve days' inaction. The paragraph
carries its own resolution, which is what Q4 asks of it.

**Q2 — does any sentence assert a state another sentence or the store
contradicts?** No. Every figure and quotation is verified against held bytes or
against the sent blob, listed in the notes above. The two new factual claims were
checked for this run:

- *"Our own record has said since 29 August that Jacot is not an author"* —
  `attributions.json`, `checked_against: "the paper's own author list, opened
  2026-08-29"`.
- *"the page was corrected that day"* — cdk46's live change log, fetched from
  served bytes, carries the correction naming Marie-Laure Tanguy.

**Q3 — could a careful reader leave believing something false that no sentence
states?** One thing found and **not fixed here, because it is the operator's**:
the closing paragraph sends readers to both change logs to check the
corrections. **cdk46's live log does not contain the word "Jacot."** It says *"The
page named the wrong researcher; the first author of that 2018 npj Breast Cancer
paper is Marie-Laure Tanguy."* A reader who follows the link to verify *"not
Jacot"* will find the correction and not the name they were told to check for.
The email is accurate; the destination is thinner than the email implies.

The delay paragraph was also read for this: *"we had no way to send a
correction"* is true and could be heard as an excuse. It is followed immediately
by *"Both were built this week"*, which converts it into a statement about what
was missing rather than about why it was acceptable.

**Q4 — is a reader asked to hold anything in suspension longer than the passage
supports?** No. Each of the three paragraphs — the delay, and the two
corrections — resolves inside itself. The longest suspension is within the
attribution section, where *"Two things are wrong with that sentence"* opens a
pair that closes four sentences later; the pair is enumerated and closes in
order.

**At whole-email scope:** the ordering puts the attribution first, which is the
error with another person's name on it. That is the right order and it is also
the flattering one — it is the error least attributable to sloppiness. Recorded
rather than changed: the alternative, leading with our own interval mistake,
would bury a named researcher's correction under our own housekeeping.
