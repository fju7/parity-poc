# cdk46 — adjudication of the outside review, 2026-08-29

Reviewed content: `2026-08-29-sent.html`, sha256 `033297d0d90d1fb6`
Standard: version 1.1

The review itself is in `2026-08-29-review.md` and is never edited after the fact,
including by us. This file sits beside it and is where our decisions go.

Three findings, one unsourced suspicion. All four accepted. Every source the reviewer
cited was opened and read here before any change was made — that rule exists because the
worst error in this issue came from acting on an unverified claim about somebody else's
document, and it came from our own gate.

---

## OR-001

**Finding**

> "No randomised trial has tested one of these drugs against another. Three research
> programmes have compared them anyway, and reported across four papers."
>
> BREACH: Question 2 / unsupported factual claim. More than three comparative programmes
> exist; a 2023 reconstructed-patient-data comparison and a 2023 real-world cohort were
> both missed.

**Disposition** — ACCEPT

**Reason**

Verified. The 2023 *Cancers* study (PMC10527344) rebuilt patient-level survival curves
from PALOMA-2, MONALEESA-2 and MONARCH 3 by graphical reconstruction — 1,827 patients —
and estimated every pairwise difference directly. Read here in full before acting.

The finding is not merely a miscount. A publication whose subject is what other people's
evidence does and does not establish stated the size of a literature it had not surveyed.
"Three research programmes have compared them anyway, and reported across four papers" is
a claim of completeness, made in a sentence whose only function was to sound thorough.

The reviewer's own framing is the important part: the missed studies *support* our
conclusion. We were not shading the evidence in our favour. We were asserting a fact
about the world we had not checked — which is the same failure as OR-001 of the internal
pre-review and as the three charges against NCCN withdrawn earlier in this issue, and it
is the failure this publication exists to find in others.

**Change**

Body, replacing the count:

> "Several research programmes have compared them indirectly or observationally. This page
> examines four of them. It does not claim to have the whole literature — an outside
> reviewer found two more that we had missed, one of which is now the fourth below."

And the study itself is now on the page and in the sources, with all its figures. It
brings one number that cuts against this piece's conclusion and it is printed rather than
omitted: on progression-free survival its one-stage model puts abemaciclib against
ribociclib at 0.722 (0.520–1.002), **p = 0.051** — the closest anything has come to
separating those two. It does not separate them, and the paper's own two-stage model on
the same data gives 0.921 (0.597–1.420, p = 0.710). Both are on the page.

The reviewer's smaller fix was to drop the number and leave the three studies as the ones
examined. We went further and added the study, because it is good evidence on the exact
question and because the borderline PFS figure is the strongest counter-evidence in the
piece.

**Sources considered** — new S011 (*Cancers* 2023, PMC10527344), S016 (P-VERIFY),
S012 (PALMARES-2), S015 (network meta-analysis)

---

## OR-002

**Finding**

> "…on an endpoint none of these trials was powered for."
>
> BREACH: Question 2 / factual error. PALOMA-2 was explicitly powered for overall
> survival. MONARCH 3 was not. The claim flattens a real design difference.

**Disposition** — ACCEPT

**Reason**

Verified verbatim from the PALOMA-2 publication: "The final OS analysis was planned to be
performed after at least 390 events, providing an 80% power to detect a hazard ratio [HR]
≤0.74, using a stratified log-rank test with a one-sided significance level of 0.025."

This is the most valuable of the three findings, because the error was costing the piece
an argument rather than merely stating something false. Palbociclib's null result comes
from an analysis built to detect an effect of that size. Abemaciclib's near-miss comes
from a gated secondary endpoint. Those are not the same kind of negative result, and the
page had erased the difference in order to make a tidier sentence.

**Change**

The clause is deleted from the Not-established list, and a paragraph added where the
grade is introduced:

> "PALOMA-2 powered for it: its final survival analysis was planned after at least 390
> events, with 80% power to detect a hazard ratio of 0.74 or better at a one-sided 0.025.
> MONARCH 3 did not: survival there was a gated secondary endpoint, its final analysis
> planned at about 315 events with alpha split between the whole population and a
> visceral-disease subgroup. So palbociclib's null result comes from an analysis built to
> find an effect of that size, and abemaciclib's near-miss comes from one that was not."

**One departure from the reviewer's evidence, and it is a limit on us, not on them.** The
reviewer quotes MONARCH 3 as saying "No power assumptions were made for the secondary
endpoint of OS." That sentence is not on our page, because Annals of Oncology returns 403
to us and we could not open it. What is on the page is what we could open and read: the
gated-secondary design, the ~315-event plan and the split alpha, from CancerNetwork's
report of the same analysis. The reviewer's quote is stronger and should replace ours the
moment somebody with journal access can confirm it.

**Sources considered** — S010 (PALOMA-2 final OS, PMC10950136), S003 (MONARCH 3 final OS),
CancerNetwork report of MONARCH 3

---

## OR-003

**Finding**

> "The threshold is the conventional one and the guideline applied it correctly."
>
> BREACH: factual error / internal contradiction. The page says several paragraphs
> earlier that MONARCH 3 was judged against .034.

**Disposition** — ACCEPT

**Reason**

Correct, and the contradiction is entirely ours. The sentence survived four separate
rewrites of the surrounding paragraph, including one made specifically to introduce the
.034 figure. It is a good demonstration of what a gate run cannot do: this required
holding two paragraphs in mind at once, and every automated pass read them separately.

**Change**

> "abemaciclib's did not (P = .0664, against its own boundary of .034). The guideline
> applied each trial's result correctly."

**Sources considered** — S003 (MONARCH 3 final OS), SABCS 2023 GS01-12

---

## OR-S01 — suspicion, not a finding

**Raised**

> "Every study that has compared the two it grades apart finds nothing between them…" —
> an exhaustive claim from a piece that has just been shown to have missed studies. The
> reviewer could not source a counterexample and did not report it as a finding.

**Disposition** — ACCEPT

**Reason**

They were right not to report it and right to raise it. We could not source a
counterexample either, and the closest thing to one — the reconstructed-data PFS figure
at p = 0.051 — is now on the page. But the reviewer's reasoning is the point: an
exhaustive claim from a publication that had just demonstrated an incomplete survey is
not a claim it has earned.

**Change** — standfirst:

> "Every comparison this page could find of the two it grades apart finds nothing between
> them."

**Sources considered** — all four comparison sources

---

## The post-review gate run

One gate run followed the adjudication above, under the new two-run cap (cycle 2, run 1).
$2.83, one serious finding, zero serious inference findings. Five items were acted on and
are recorded here so that the changes they caused can be traced to something a reader can
open.

---

## GATE-01

**Finding** — "A corrigendum to this paper exists — Ann Oncol 2025;36:1556 — and we have
not been able to read it: it is behind the publisher's wall." The corrigendum is published
open access under a Creative Commons licence; the claim of a paywall is false. A second,
MINOR finding noted that the same passage disclaimed having read it and then asserted "we
have no reason to think any of them is affected" — a conclusion reachable only by reading
it.

**Disposition** — ACCEPT

**Reason** — Both correct. The first is a claim about a publisher's access policy that we
made without checking, which is the class this issue has committed repeatedly. The second
is a straightforward contradiction inside one sentence.

We still could not open it. Every route tried here — Annals, ScienceDirect, the DOI
redirect, Elsevier's linking hub, Europe PMC, PubMed — returned a block. That is a limit
of this environment, not of the licence, and the page now says exactly that.

**Not accepted in full**: the gate reports that the corrigendum corrects a Figure 4 event
count (placebo arm 162 → 132) and does not touch the HR, CI or p-value. That is very
probably right and it is not on the page, because it is a claim about a document we have
not opened — the rule adopted today, applied to the run that told us about it.

**Change** — the paywall claim removed, the contradiction removed, replaced with what is
true: it is open access, we could not retrieve it, our figures match the original article
and the SABCS presentation, and whether the corrigendum touches them requires reading it.
Plus an open invitation to anyone who can.

---

## GATE-02

**Finding** — The 97% interval-overlap figure is presented as a measure of how similar the
two effects are, when overlap is also a function of interval width, which is a function of
power — the same caution the page applies to p-values and not to its own derived statistic.

**Disposition** — ACCEPT

**Reason** — The page had just written that where an interval ends "is set by how many
patients were enrolled, how many events occurred and how variable they were", and then
computed a percentage from those bounds without carrying the caveat across. Holding
ourselves to a standard in one paragraph and not the next is the fault this piece exists
to name in others.

**Change** — a sentence before the arithmetic: the overlap is also a function of how wide
abemaciclib's interval is, itself a consequence of what that trial was powered to detect,
and not only of how close the point estimates are.

---

## GATE-03

**Finding** — Three separate NOT_FOUND verdicts read the parenthetical "(0.637, 1.015)" as
ribociclib's confidence bounds. They are abemaciclib's.

**Disposition** — ACCEPT

**Reason** — The arithmetic was never wrong, but one ambiguous parenthetical produced three
findings, which means a reader working from that sentence alone would make the same
mistake. A number with no owner named is a number waiting to be misattributed.

**Change** — "Using abemaciclib's unrounded lower bound of 0.637 in place of the rounded
0.64…", and an explicit parenthetical: "0.637 and 1.015 are abemaciclib's bounds
throughout; ribociclib's are 0.63 and 0.93."

---

## GATE-04

**Finding** — "No number on this page comes from a news report, and none from a
guideline's summary of a trial" implies news reports and guideline summaries are sources
from which wrong numbers come, without citing an instance.

**Disposition** — ACCEPT

**Reason** — The role's own note says this does not reach the level of the recorded
UNSUPPORTED error, and it is right: it names nobody. But it is a negative claim about
others doing the work of a positive claim about us, and this issue has already withdrawn
four charges against third parties.

**Change** — rewritten as what it always should have been, a statement of our own sourcing:
every figure traces to a trial publication, a drug label or a comparative study, cited by
name; and where a correction to a source is known to us it is noted in that entry.

---

## GATE-05

**Finding** — "Its Table 1 lists MONARCH 3 at HR 0.804 (0.637–1.015) with 97.2 months of
follow-up" — the HR, CI and SABCS citation verify, but that 97.2 months is MONARCH 3's own
follow-up rather than the range maximum across all seven trials could not be confirmed
from the table.

**Disposition** — ACCEPT

**Reason** — Neither could we. Our source for that attribution was a fetcher's summary of
the paper, not a quotation from the table. Under the rule adopted today it does not belong
on the page. This is the second time in two days that the same sentence about the same
paper has had to be corrected, in opposite directions, on unverified attribution.

**Change** — the follow-up attribution removed. What remains is quoted: the HR, the CI, the
"year of updated data 2023", the SABCS 2023 reference, and separately the pooled 73.3-month
median across a 48.7–97.2 range, which the paper states in its own text.

---

## PREFLIGHT-01

**Raised by** — `publish.py check`, not by a reviewer.

> STOP  page dateline  says nothing, and today is 29 August 2026 — a reader reads
> that as when it was written

**Disposition** — ACCEPT

**Reason**

The masthead still said "DRAFT — not published". The preflight refuses to let a page go
out whose own date does not match the day it goes out, on the reasoning written into the
check itself: an assessment published on the 28th whose masthead says the 26th is the
error this publication exists to point at, printed on itself.

**Change** — masthead: "Published 29 August 2026 · guideline version 6.2026".

The version is on the masthead deliberately. The piece is about a specific version of a
document that is revised several times a year, and a reader arriving in six months should
be able to see at a glance which one it read without hunting for it in the sources.

---

## Outstanding after this adjudication

Carried from the internal pre-review, both still open, neither blocking:

1. **Read the MONARCH 3 corrigendum** (Ann Oncol 2025;36:1556, PMID 41093689). Requires
   journal access. The page discloses that it is unread.
2. **MONALEESA-2's final OS significance boundary**, from the NEJM supplementary appendix.
   The page says we do not know it.

Added by this adjudication:

3. **Confirm MONARCH 3's "No power assumptions were made for the secondary endpoint of
   OS"** from the Annals full text, and replace our weaker secondary-sourced phrasing with
   it. Requires journal access.
4. **The second study the reviewer found** — the 2023 real-world cohort (PMC10217927) — is
   cited in this adjudication but is not yet on the page. It agrees with the other four
   and adding it is not urgent; it is recorded here so that its absence is a decision
   rather than an oversight.

---

## What this review demonstrated

Fourteen gate runs on the assessment did not find any of these three. That is not a
failure of the gate so much as a description of what it is: each role reads the page
alone, and none of them audits another's output or holds two distant paragraphs together.

The costliest error in this issue — the claim that the network meta-analysis used stale
MONARCH 3 data — was *generated* by the gate's recency role and repeated across three
runs. No number of further runs could have caught it. Both it and OR-003 were caught by
readers, one internal and one outside.

That is the argument for keeping this step, and for the gating changes agreed on the same
day: a hard cap of two runs before review and one after, and a standing rule that no gate
claim about a third party's document may be published until that document has been opened.
