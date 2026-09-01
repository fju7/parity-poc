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
