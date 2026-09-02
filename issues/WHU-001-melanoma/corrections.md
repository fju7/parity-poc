# WHU-001 — public correction history

Substantive changes made **after** publication. Draft changes and things caught
in review belong in `review/`, not here — this is the only one of the three
histories a reader sees, and mixing them makes it useless to them.

Each entry: what a reader who saw the earlier version needs to know, and when.
Not how the process failed; that is in the repository.

## 28 August 2026 — the page did not say when it last changed

An earlier version of this assessment was readable on the site before 28 August.
It differed from the version now published in more than forty places above the
footer, and the change log it carried described only an earlier round of edits.
Several of the differences are substantive. A sentence characterising how most
coverage had handled the earlier trial's figures was replaced, after checking outlet
by outlet, with the finding that most specialist outlets attributed them correctly;
that section now leads with what the coverage did rather than with our own earlier
framing of it. There were four corrections to statistical language, including "risk
reduction" for a reduction in hazard and "unblinded" for a trial that was open-label
from the start. A confidence interval was missing from the five-year survival
comparison. And a sentence said the therapy does not extend life where the truthful
statement is that the question is open. What moved, and why, is
set out in full in the change log at the foot of the assessment itself.

The exact figure — forty-one differences above the footer — was established by
diffing the version readers were served against the version published on 28 August.
The count is in the repository; the substance is in the change log.

None of that reached a reader at the time. The page was dated 26 August, the homepage
dated it 27 August, and the change log on it stopped at an earlier round. That is a
quiet edit, and `who-pays-for-this` says we do not make them. The scale of it was
only established because a reader — in this case the operator — asked how anyone
could tell whether the published version was the current one.

What has changed as a result:

- The masthead now reads "Published 26 August 2026 &middot; Updated 28 August 2026",
  and the update date links to the change log.
- The change log carries an entry for 28 August describing every change in reader terms.
- The evidence-currency line moved from 26 to 28 August, the day the adverse-event
  figures were last read off the source.
- Two checks now run before anything publishes: the masthead's update date must be the
  publication date, and if readers can already see a different version of a page, this
  file must carry an entry dated that day. Both stop a publish rather than warn about it.

No figure, hazard ratio, interval or conclusion in the assessment changed on 28 August
in a way that alters what it says about the trial. The adverse-event percentages were
re-read off Merck's five-year release and are unchanged; what changed was the sentence
around them, which had described them as the trial's side effects where the source
attributes them to the vaccine specifically.

## 29 August 2026 — a navigation link, and how we found out we had not recorded it

Issue two published on 28 August and was reachable from its own navigation bar
and nowhere else — not from the homepage, not from this page, not from the
sitemap. On 29 August a link to it was added to the navigation on this page,
along with the other three.

That is a small change and it is recorded here for a reason that is not small.
It was made without being written down, and it stayed unrecorded until the
publish reconciliation refused to pass this issue and named one changed
sentence with no decision behind it. `who-pays-for-this` says we do not make
quiet edits. This was one, for about an hour, made by the person who built the
check that caught it.

Nothing else on this page changed. No figure, interval, source or conclusion
differs from the version published on 28 August.


## 1 September 2026 — three figures that were in no document we hold

Three numbers on this page did not come from any source. They have been
corrected against the paper the page cites, the *Journal of Clinical Oncology*
five-year update of KEYNOTE-942 (Khattak et al., 1 June 2026), whose full text
we have held since 1 September 2026.

**Recurrence-free rates.** The page read: "The absolute figures from the same
trial, at five years: **68.8%** of combination patients were recurrence-free
versus 49.1% on pembrolizumab alone. That is a gap of roughly **20 percentage
points** at the five-year mark."

The paper reports: "The four-year RFS (95% CI) was **72.4%** (62.2 to 80.2)
with intismeran plus pembrolizumab versus **49.1%** (33.3 to 63.0) with
pembrolizumab."

Three things were wrong. 68.8% appears in none of the eight documents this
issue holds. 49.1% was right, but it is the four-year figure, and its pair is
72.4%. And the time point was wrong: the five-year update reports its
recurrence-free rates at four years. The corrected gap is 23 points, at four
years. The page now gives both intervals, which it did not before.

**Survival rates.** The page read: "the same five-year analysis reads 92.2%
alive versus **71.3%** — 95% CI 84.2–96.3 and **35.4**–89.6, as *The ASCO Post*
reported them from the five-year data. A large observed gap."

The paper's Figure 1C gives 92.2% (84.2 to 96.3) and **85.6% (70.5 to 93.3)**,
at 48 months — the figure's legend states its time points as 18, 24, 36 and 48.
71.3 does appear in the paper, once, as the lower bound of the recurrence-free
curve's 80.4% (71.3 to 86.9): a different endpoint on a different panel. 35.4
appears nowhere. And *The ASCO Post*'s report of this trial, whose full text we
hold, contains none of these figures; the attribution was wrong.

The observed gap is therefore under seven points, not twenty-one, and the
sentence that called it large has been rewritten. The direction of the finding
is unchanged: the intervals overlap along most of their length and the data can
neither confirm nor rule the difference out.

Which arm is which had to be established, because that figure's text does not
extract cleanly. The paper states in prose that "7 of 107 patients (6.5%) in
the intismeran plus pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab
arm died", and 100 − 85.6 = 14.4, against 100 − 92.2 = 7.8. The assignment is
the authors' own arithmetic, not ours.

**The January topline.** The page described, dated and quoted a document:
"The companies' five-year topline of **20 January 2026** reported **one-sided
nominal p = 0.0075**." Neither the figure nor the document is in anything we
hold, and no such release appears in this issue's source list. Both mentions
have been removed, along with the paragraph built on the second one. What
survives is what the paper itself says, which we do hold: the five-year
analyses were descriptive, and no p-value was released for the survival
analysis.

### How this happened, and what changed because of it

These were not figures taken from a document and mistyped. They were written
before the document existed. This page was published on 26 August carrying two
of them; the third was added on 27 August; this issue's source ledger was not
created until 28 August, and the paper that settles all three was not held
until 1 September — six days after the sentence that misquotes it went live.

Every check this publication had ran downstream of the writing, and asked
downstream questions: is the page internally consistent, do the links resolve,
are the coverage claims supported. None asked whether a number came from
anywhere, because when these sentences were written there was nowhere for them
to come from.

A check that asks it now exists. It takes every figure on a page and looks for
it in every document the issue holds, and where an issue holds all of its
sources — as this one does — a figure found in none of them stops the publish.
It reports presence and absence and nothing else: a figure found is not a
sentence that is true, and where sources are unheld a figure missing is not a
sentence that is false.

Nothing else on this page changed. The hazard ratios, intervals, event counts
and conclusions are as published.

## 2 September 2026 — what two adversarial checks found

The source advocate (which argues each source's case against our page) and the
counterexample hunt (which tries to break every universal negative) ran on this
issue for the first time. Thirty-six findings, thirty-one closed with a reason
on the record, five of them upheld and acted on.

**"Cleared the line."** We said the recurrence interval cleared the no-effect
line at the three-year readout. The three-year paper says of that analysis:
"These subsequent analyses are not intended for formal hypothesis testing (ie,
are descriptive only)." An interval that stops including 1.0 is not a threshold
crossed in a test, and the page now says which of the two happened. The same
paper leads with an 80% confidence interval (0.351–0.743) and gives the 95%
(0.288–0.906) in its table; the note now says which we quote and why.

**A source we said we could not read.** The note on that paper read: "the
journal site blocks automated access, so we have verified the citation but not
read the full text ourselves." We hold it in full. The note is rewritten from
the document. The check built to catch a page claiming a held source is
unreachable did not fire, because neither phrasing was in its list.

**A truncated title.** We had dropped "the Individualized Neoantigen Therapy"
and "(mRNA-4157, V940)" from the three-year paper's title — the words a reader
uses to find it. Restored.

**"n=14".** A faithful quotation of the companies' own label that reads as
fourteen patients. It is fourteen deaths, seven in each arm, and the page now
says so where the label first appears.

**A claim wider than its evidence.** A sentence opened on adjuvant melanoma
trials before narrowing to PD-1 inhibitors, so a reader could take the broader
class as the claim. It now says what it is not about. The hunt named a trial
that broke the wider pattern; we do not hold that paper, and when we tried to
get it we found it carries a correction nobody has read. The sentence steps
around the claim rather than making it on a finding.

**The threshold the trial actually set.** The section contrasting one-sided
0.0266 with two-sided 0.053 left a reader to supply 0.05 as the line. The trial
prespecified a one-sided alpha of 0.10 — "designed with approximately 80% power
to detect a hazard ratio (HR) of 0.5", against that threshold, in the three-year
paper, and "1-sided alpha of 0.1 per protocol" in the ASCO 2024 presentation. So
0.0266 cleared its own threshold by a wide margin and 0.053 misses a line this
trial never used. The section's point is unchanged and better founded.

Five findings remain open, and they are judgement rather than fact: how much of
one outlet's argument to carry, and whether a question we pose as unanswered is
in fact unanswerable. They are recorded in this issue's adjudication files with
what is known and what is not.

### Later on 2 September — the three questions the checks could not answer

Three findings needed an editor rather than a document, and the answers changed
the piece.

**"n=14" stays, and now says what it counts.** The label is the companies' own
— their release prints it and does not say fourteen of what. The paper does, and
the page now quotes it: "7 of 107 patients (6.5%) in the intismeran plus
pembrolizumab arm and 7 of 50 (14.0%) in the pembrolizumab arm died."

**The disagreement between two outlets is not a digression.** An earlier note of
ours called it one. That was wrong. Whether the benefit reaches the patients the
Phase 3 newly includes is the question of what these numbers, when they come,
will support, which is what this issue is about.

**But the disagreement cannot be settled, and the page now shows the checking.**
No hazard ratio, confidence interval or p-value for this trial appears in either
company release, in any coverage we hold, or in the trial's own registry record:
ClinicalTrials.gov NCT05933577 carries no posted results at all and gives an
estimated primary completion date of 26 October 2029. The August announcement
was a prespecified interim look.

So placing the earlier trial's figures beside this result would mislead, and the
page now says how: the trials do not share a population (stage IIIB–IV against
IIB–IV), a design (open-label against double-blind with the outcomes assessor
masked), or a statistical standing (analyses the earlier paper calls
"descriptive only", against a prespecified interim threshold). And there is
nothing to compare to — the Phase 3 has released no effect size, so quoting 0.51
next to "met its endpoints" is a substitution rather than a comparison. That is
what the headlines did.

## 2 September 2026, later — the correction was wrong, and this is the record

The page gate ran for the first time on the corrected text and reported that two
of the three figures removed on 1 September were real. They were. Both are
restored.

**What we removed, and why that was wrong.** On 1 September a new check (B13)
asked, of every figure on the page, whether it appears in any document this
issue holds. Three did not. Two of those three were the five-year landmark
rates: 68.8% recurrence-free against 49.1%, and 92.2% alive against 71.3% on an
interval of 35.4–89.6.

What this issue held was the full *Journal of Clinical Oncology* paper, and that
paper reports landmark rates only at 18, 24, 36 and 48 months — its own figure
legend says so. The five-year rates were reported from the same analysis in *The
ASCO Post*, which we did not hold. Acquired today, it reads:

> At 5 years, the recurrence-free survival rate was 68.8% (95% confidence
> interval [CI] = 56.3%–78.3%) in the combination arm and 49.1% (95% CI =
> 33.3%–63.0%) in the monotherapy arm.

> There was a trend for improved overall survival as well, an exploratory
> endpoint (HR = 0.47; 95% CI = 0.17–1.35) with 5-year rates of 92.2% (95% CI =
> 84.2%–96.3%) in the combination arm and 71.3% (95% CI = 35.4%–89.6%) in the
> pembrolizumab alone arm.

**What was actually wrong with the original sentences.** Not the figures — the
intervals. 68.8% and 71.3% were printed without them, and 35.4–89.6 is the whole
point of the survival number: on seven deaths in fifty patients it runs from a
third of that arm alive to nine in ten. And the attribution was wrong: they were
credited to a paper that does not print them.

**What was worse than the error.** The correction notice. It said the figures
"came from no document" and that one "exists nowhere", and drew a general lesson
about prose being written before documents existed. The check had been careful —
it reports that a figure is in *nothing we hold*, and prints, in its own output,
that a miss is not a falsehood and that a figure can be absent because the source
is not held. The sentence written around it said something stronger and worse.

Accusing ourselves of inventing figures we had not invented is a more serious
failure than publishing them without intervals. It is recorded here at length
because the check did its job and the writing did not, which is the failure this
publication is least able to see in itself.

**What remains removed.** The "five-year topline of 20 January 2026" reporting a
one-sided nominal p = 0.0075. That document is in nothing we hold and in no
source list on this page, and nothing found since has changed it. It stays out.

**And the four-year figures.** The JCO paper's own sentence — "The four-year RFS
(95% CI) was 72.4% (62.2 to 80.2) with intismeran plus pembrolizumab versus
49.1% (33.3 to 63.0) with pembrolizumab" — is real too, at a different time
point. The page carries the five-year rates, which is what it always meant to
report, and notes the 48-month values where they differ.

## 2 September 2026, later still — what the first page gate found

The gate ran on the corrected text and made thirteen blocking findings. Each is
now closed against a document, recorded in `gate-findings.json`, with the
quotation checked against the bytes.

**Where it was right.** The claim about adjuvant PD-1 inhibitors and overall
survival carried no citation at all; it now rests on two registry records —
KEYNOTE-054, which is pembrolizumab against placebo and lists overall survival
as a secondary endpoint with no result posted, and CheckMate 238, whose
comparator is ipilimumab, so there is no placebo arm to report against. The
Phase 3 widened its population downward only: stage IV was in both trials, and
IIB, IIC and IIIA sit below the earlier trial's floor of IIIB. The list of
outlets named FierceBiotech and OncLive, neither of which we hold; both are
removed and the sentence now names only outlets whose articles are in the
library, quoting three of them. And a change-log entry gave a gap of "four and a
half months" that matches no pair of dates we hold; it is nine months, 16 April
2023 to 18 January 2024.

**Where it was wrong, in the way we keep being wrong.** It reported our account
of MLQ News as contradicted, because no MLQ News article appeared in its search
results. We hold that article. It says, word for word, what the page said it
says. That is the same error as our own correction notice of the day before: a
finding about what a check could reach, stated as a finding about the world.
Roles do it to each other, and a finding reads like evidence because it arrives
in the same shape as evidence.

**So a finding can no longer close itself.** A new check requires every gate
finding to be settled by a quotation from a document we hold, and verifies that
quotation against the bytes. Prose cannot close one. Nor can an absence — there
is no sentence in any paper reading "this figure appears nowhere", so a claim of
that shape can never be recorded as settled, which is the outcome we wanted and
did not get on 1 September.

**And building it found something worse.** The check that guards quotations —
the most damaging error this publication could make — compared the page against
a transcription somebody had typed. It never opened the source. A mistyped
transcription that matched the page passed. It reads the document now, and the
first run turned up two of our own quotations that do not survive it: one where
the page ends a sentence the source continues, and one where a PDF ligature made
a true quotation unmatchable. Both are fixed.

## 2 September 2026 — the second page gate

Nineteen blocking findings, all closed against documents. Four were right and
three of those four were sentences written earlier the same day.

**A subheading that contradicted the paragraph under it.** "The distinction the
coverage collapsed" sat directly above "every outlet whose article we hold
attributed those figures correctly". A subheading is a claim. It now reads "What
correct attribution still leaves open".

**An accusation the page's own check does not sustain.** The piece said "That is
what the headlines did" — of substituting the earlier trial's figures for the
Phase 3's — immediately after establishing that every outlet it holds attributed
correctly. We hold no example of a headline doing it. The sentence now describes
the structural effect without accusing anyone of it.

**An interval we calculated and did not say we had.** "The same data, read
against the one-sided 90% interval, would not cross 1.0" is arithmetic this page
performed. It checks out, and that is not the point: the page's own rule is that
figures we compute are marked as ours. Removed.

**A parenthetical resting on a figure panel nobody has read.** The claim that
the full paper's 48-month arms read 92.2% and 85.6% came from a figure whose
text extracts jumbled. It now says only what the figure legend says.

### Where the gate was wrong, and why it is worth recording

Five findings were claims about documents this issue holds, made without opening
them.

It reported all three of our adverse-event percentages as wrong, giving 60.6%,
56.7% and 49.0%. Those are the three-year figures. The five-year release we hold
prints "fatigue (59.6%), injection site pain (59.6%), and chills (51.0%)" — the
page's three exactly.

It reported the three-year hazard ratio as 0.501 rather than 0.510. The
three-year paper, which we hold in full, says "The updated RFS HR improved to
0.510" and prints 0.510 in its results table. 0.501 appears nowhere in it.

It said MLQ News does not name confidence intervals or event counts. The article
contains two sentences listing what was withheld; the gate found one and we
quote the other, verbatim.

And on Practical Dermatology it contradicted its own previous run: the first
gate said that outlet's enumeration was *fuller* than our paraphrase, this one
says it does not enumerate at all. We hold the article. It carries the sentence
we quote.

None of this makes the gate less useful — it found four real problems in text
that had already passed every deterministic check here. It means a finding is a
claim about a document, and a claim about a document is settled by opening the
document. Every one of the nineteen is now recorded with the source and the
sentence that settled it, and those quotations are checked against the bytes on
every run.
