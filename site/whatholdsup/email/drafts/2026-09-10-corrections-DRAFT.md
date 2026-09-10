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
> What their paper does establish is stronger for the piece and different in
> kind: these trials were mostly too small to detect a survival difference, so
> the presence or absence of significance across them is weak evidence about the
> drugs.
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
> interval** of 0.179 to 1.004" — in a message whose other intervals were 95%.
>
> **Why.** Both intervals for that hazard ratio sit in the same table row of the
> same paper. We printed the narrower one beside 95% figures without saying so.
> An 80% interval is narrower than a 95% interval computed from the same data;
> that is what the numbers mean, not a property of the result.
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
