# WHU-002 — post-publication review and adjudication

Received 29 August 2026, after the assessment published on 28 August and after
the announcement email had been sent. The reviewer read the live page against
the standards. Four findings. All four accepted. Labels PUB-01..PUB-04 are the
reviewer's; PUB-S01 is ours, found while fixing the others.

---

## PUB-01 — the page treats an evidence category as a ranking of drugs

**The finding.** NCCN maintains two distinct systems. Categories of Evidence and
Consensus (1, 2A, 2B, 3) record the strength of evidence and the degree of panel
consensus that an intervention is *appropriate*. Categories of Preference
(Preferred, Other Recommended, Useful in Certain Circumstances) rank regimens
against one another on efficacy, safety and evidence together. The page treats
the first as though it were the second.

**Adjudication: accepted, and it is the most serious error either issue has
carried.**

The operator supplied the guideline's own language, verbatim, from version
6.2026: all three aromatase-inhibitor-plus-CDK4/6-inhibitor combinations are
listed as preferred first-line options, for postmenopausal patients and for
premenopausal patients on ovarian ablation or suppression; ribociclib is a
category 1 recommendation because of the overall survival benefit; abemaciclib
and palbociclib are category 2A. The preference designation does not differ
across the three. Only the category of evidence does.

This is not a wrong figure. Every figure on the page was verified and none
changed. It is a **selective omission** — the fact in the source document most
likely to change a reader's answer to the question the page posed, left out of a
page built to criticise how that document reads. It belongs to the error class
already recorded in the fixture as claims about a third party's document made
from a partial reading of it, and it is the sixth instance across two issues.

The irony is worth recording rather than smoothing over. The thesis of the piece
is that an evidence label gets read as a ranking of drugs when it is not one. We
made exactly that error, about exactly that label, in the piece about the error —
after eighteen automated fact-check runs and two reviews, none of which asked
whether the guideline had a second system.

**What changed.** Standfirst, the section "What the guideline says" (two new
paragraphs, one stating the two systems and one naming our own error), the
section "What a reader is owed", the three social-preview descriptions, one
phrase in "Where the intervals fall", one in the comparative-studies section,
and a public correction entry. The argument survives and narrows: not that a
guideline ranks three drugs on thin evidence, but that a grade printed in a
column beside two others is read as a ranking whether or not it was meant as
one — which the page can now evidence from its own conduct.

**What could not be done.** The announcement email carried the same omission and
has been sent. It cannot be recalled. The correction runs at the top of issue
three's email.

---

## PUB-02 — MONALEESA-2's p-value is described as two-sided without a source

**The finding.** The page states in five places that MONALEESA-2's final
overall-survival p of 0.008 is two-sided. The reviewer contends the analysis was
one-sided, against an adjusted boundary.

**Adjudication: accepted as to our error; the reviewer's replacement is not
adopted.**

We cannot source "two-sided". It was asserted, not read. That is the same class
of error as PUB-01 in miniature — a characterisation of somebody else's document
made without opening it — and the standing rule is that such a claim does not go
on the page.

The rule cuts both ways. We could not open the NEJM paper's statistical section
either: every route returned a paywall or a challenge page. So the reviewer's
one-sided reading is recorded on the page as a contention and is **not printed as
fact**, for the same reason our two-sided reading was removed. The number now
stands as the publication prints it, with nothing added to it, and the open
question is stated as open in the footer's list of things we have not read.

**What changed.** "Two-sided" removed from all five occurrences; the footnote
now states what we do and do not know and attributes the competing reading; the
source entry carries the same qualification; the footer's unread list names it.

---

## PUB-03 — two claims are broader than the evidence behind them

**The finding.** "No study that compares them by other means finds a difference"
is a universal claim resting on a survey the page itself says is incomplete. And
"all three indirect comparisons" says three where the page examines four.

**Adjudication: both accepted.**

The first is the recurrence of the class an outside reviewer caught before
publication (OR-S01) — an exhaustive claim from a partial survey — in a sentence
the earlier fix did not reach. The second is a count left stale when the fourth
study was added during review; the section heading above it said "three times, by
three methods" while the paragraph beneath said four.

**What changed.** The universal claim now names the four studies it is a claim
about and says explicitly that four studies are not the literature; it also now
carries the p = 0.051 figure that comes closest to contradicting it. Counts
reconciled in three places: the section subhead, the worked box label, and the
"not established" list.

---

## PUB-04 — the footer described a published page as an unpublished draft

**Adjudication: accepted. Fixed 29 August, before this file was written.**

The footer said "Draft — not published" beneath a masthead reading Published, on
a live page, for the first hours after publication.

---

## PUB-S01 — issue two was unreachable from anywhere a reader starts

Not the reviewer's finding. Found while fixing PUB-01.

The assessment was live at /cdk46 and linked from its own navigation bar and
nowhere else. The homepage did not list it. The navigation on the homepage, the
policy pages and issue one did not link it. It was absent from the sitemap. The
publish path had recorded a successful deployment of a page no reader could find.

**What changed.** Navigation on all four other pages, a card on the homepage
above issue one, and a sitemap entry. This is a gap in the publish checks, not a
one-off: nothing in the pipeline asserts that a newly published issue is
reachable from the site root.

---

# Stale gate findings, dispositioned 29 August 2026

The last gate run judged draft `3d7c7f85`. The corrections above changed the
page to `f78c768a`, which voids the run — a verdict unbound from the sha it
judged is meaningless. Rather than spend another run, each open finding is
dispositioned here against the current text. Whoever accepts the gate is
asserting these, and the assertion is checkable by anyone who opens the page.

## Assessment — cdk46.html

**c2 — NOT_FOUND. "The NCCN guideline assigns ribociclib ... category 1."**
Not found because the gate could not open the source: NCCN v6.2026 is behind a
login wall, and its licence forbids putting the document through an AI tool at
all, so no automated check on this issue is permitted to read it. The claim is
confirmed by the operator, who read the guideline directly and supplied its
language verbatim on 28 and 29 August. Recorded in the source ledger as S001,
`human_read`, with the sections read named. **Accepted: the finding is an
absence of machine access, not a contradiction.**

**c31, c32, c33 — NOT_FOUND. The 97% interval-overlap claims.**
Correctly found, and the first version of this disposition was wrong about what
was done with them. It said all three sentences were removed before publication.
They were not. The claim is still on the page, in "Where the intervals fall",
and this file asserted otherwise because it was written from memory of the
editing rather than from the page — the same fault, at one remove, as the ones
it is dispositioning.

What the gate found was real: the bounds 0.637–1.015 are abemaciclib's, from
MONARCH 3, and an earlier draft used them as ribociclib's. What the page now
does is show the arithmetic in full and name whose bounds are whose — "ribociclib's
interval runs 0.63 to 0.93, a width of 0.30; the part of it inside abemaciclib's
runs 0.64 to 0.93, a width of 0.29. 0.29 ÷ 0.30 = 96.7%" — followed by the
explicit line "(0.637 and 1.015 are *abemaciclib's* bounds throughout;
ribociclib's are 0.63 and 0.93.)" The page also states that the figure is ours
rather than a published one, and that the overlap is partly a function of how
wide abemaciclib's interval is.

**Accepted: the misattribution the gate found is gone, the claim it appeared in
is not, and the page now carries the derivation and the attribution the gate was
right to ask for.** The 97% figure is a calculation of ours on published bounds,
labelled as such.

## Email — issue2-cdk46.html

**o1 — FACT. "One interval stopped at 0.93. The other stopped at 1.02."**
The published bound is 1.015. 1.02 is that number correctly rounded to two
decimal places, which is the precision the sentence uses throughout for both
intervals. This is the rounding class already recorded in the fixture as
`RECALL_BRIEF_OVERFIRED_A_NEW_CLASS`, which fired on seven consecutive runs
before being recognised as an over-fire. **Accepted as an over-fire**, with the
note that the page — as distinct from the email — now prints 0.637–1.015
unrounded in the source entry, so a reader who wants the exact bound has it.

**c16 — WRONG_VALUE. "With fulvestrant ... both ribociclib and abemaciclib are
graded category 1."** Same access problem as c2, and confirmed the same way: the
operator supplied the guideline's own sentence, which states that ribociclib and
abemaciclib with fulvestrant are listed as category 1 options because those
combinations showed an overall survival benefit in MONALEESA-3 and MONARCH 2.
**Accepted.**

**c35 — WRONG_SOURCE, unlocatable.** The quote is the extractor's paraphrase
rather than a sentence from the draft, so it cannot be matched against the text
and its absence proves nothing either way. **Accepted as unlocatable**, and
recorded as an instance of the extractor paraphrasing where it should quote.

---

## GATE-06 — the email gate run of 29 August

One run, $4.60, on the rewritten email. Six findings adjudicated in
`backend/tests/fixtures/draft_decisions.json`. Two changed the page and the
email; one is rejected with reasons; three are recorded without change.

**Upheld, after seven dismissals.** The role objected that MONARCH 3's published
upper bound is 1.015 and the piece prints 1.02. That is correct rounding, which
is why it was dismissed as an over-fire seven consecutive times and recorded in
the fixture as `RECALL_BRIEF_OVERFIRED_A_NEW_CLASS`. The dismissals were wrong.
The sentence presents the number as the precise place the interval stopped, in
the one piece whose argument is about exactly that, and the rounding runs in
opposite directions on the two figures — 0.804 down, 1.015 up — which widens the
apparent gap the way that suits us. Fixed at the hinge in both the page and the
email. Recorded as a new class, `DISMISSAL_HARDENED_INTO_A_HABIT`, with a
standing rule: a finding dismissed three times on the same reasoning gets read
again by someone who did not write the earlier dismissals.

**Upheld, and the most useful thing in the run.** The COVERAGE role found Jacot
et al., *npj Breast Cancer* 2018, which makes this page's power argument
formally and six years earlier. We had presented it as our own analysis. Now
cited by name, with the fact that we came to it late stated on the page.

**Rejected, with reasons.** The role objected that our claim about missed
coverage is unsupportable, citing OncLive and Pharmacy Times as outlets that did
carry the two-system distinction. The objection answers a claim we do not make:
the sentence is about this page's omission, not about the coverage. It is
nonetheless useful, and it bears on the premise gate — if the distinction was
carried in clinical coverage, the case that this was a widely-missed fact is
weaker than the piece implies, and issue two's `premise.json` already records
that no public claim was ever identified. Worth noting that the role contradicted
itself inside a single run: its closing section states that no coverage explains
the two-system distinction, while its own evidence names two outlets that do.
Neither half is adopted. Both are claims about documents nobody here has opened.

**Recorded without change.** The PALMARES-2 interval objection is already
disposed of on the page, which names both the conference figure (0.91,
0.70–1.19) and the published one, and says which it uses — the role reached the
abstract and not the paywalled paper, exactly the case the disclosure was
written for. The CivicScale funding claim is unverifiable externally because it
is a statement by the publisher about the publisher, of the same kind as the
pre-publication access disclosure beside it.

**On the two runs.** The gate ran twice on nearly identical text and returned
materially different severities: run one put three SERIOUS findings in
INFERENCE and none in ADVOCATE; run two put zero in INFERENCE and two in
ADVOCATE, on the same underlying fact. Same file, same model, same day. That
instability is the argument for the deterministic checks, which returned
identical output both times because they contain no model.
