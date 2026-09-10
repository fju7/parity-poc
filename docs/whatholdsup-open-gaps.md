# Open gaps — checks we know we need and have not written

A gap recorded here is not a gap that is being worked on. It is one we found,
decided not to fix in the moment because fixing a control while adjudicating is
how this project's errors have been made, and did not want to lose.

Each entry names the error that revealed it, so that a later reader can judge
whether the gap is still real.

---

## GAP-001 — nothing checks a universal negative against our own library

**Raised by** the outside review of 2026-09-03, finding OR-1.
**Fix when** — CHANGED 2026-09-03, BEFORE ISSUE ONE PUBLISHES. See the
decision at the foot of this entry. Before issue two's revalidation, because
that piece is built almost entirely on claims about what a guideline does and
does not say.

Issue one said "The framing was never explained to readers." S019, KOL Pulse,
sitting in our own library and already bound to other sentences on the same
page, says: *"formal hypothesis testing of RFS, overall one-sided alpha=0.10,
performed at primary analysis"*. A document we held, had read, and had bound
other claims to, falsified the sentence. Four passes of our own checks walked
past it, and an outside reader found it in one.

**Why nothing caught it.** Every check we own asks whether a span the page
cites is present in the document it cites. None asks the opposite question: is
there a document in the library that CONTRADICTS a sentence the page asserts?
That question only has teeth for one class of sentence — the universal negative,
"nobody said X", "no trial reported Y", "the framing was never explained" —
because those are the only claims a single held document can falsify outright.

Rule 11 of the editorial standard is precisely this rule for coverage, and it
is written down and enforced by nobody. The pattern is the one recorded five
times in three days: the rule existed, gated nothing, and was followed by the
error it described.

**Shape of the fix.** Detect the universal-negative sentences — never, none, no
outlet, nobody, every, all — and for each, search every held document for the
thing it says does not exist, using the same normaliser the span checks use.
Report candidates for a person to read; do not auto-fail. The check cannot know
whether a hit really contradicts the sentence, and a check that asserted it did
would be making exactly the kind of claim R1 forbids.

**What would show the gap is closed.** A test that plants "no outlet reported a
hazard ratio" on a page whose library contains an outlet reporting a hazard
ratio, and asserts the check surfaces it.

**Do not** let this become an allow/blocklist of negation words built from the
sentences we happen to have met. Four such lists in this repository have been
wrong. The trigger is a grammatical shape, and the output is a question for a
human, not a verdict.

**Six live B6 flags on issue one are this gap, 3 September.** Running
`bindings.py melanoma check` after the last round of bindings — it had not been
run, so `status` was reporting the previous day's flags — left six flags that
no span can settle, because each sentence's claim is an absence over documents
rather than a presence in one:

    "the release ... gives no figure for either"          bounded: S001
    "The only survival figure in the programme"           unbounded: the library
    "no hazard ratio ... appears in either company        unbounded: the library
     release, in any of the ... coverage we hold"
    "NCT05933577 still carries no posted results"         bounded: S013
    "A one-sided test asks only 'is it better?'"          definitional, not an absence
    "each registry record marks that result NOT_POSTED"   enumerated: S020 and S026

The two bounded ones and the enumerated one are checkable today and are not
checked.

### What was closed on 3 September, and what the editor left open

Working through the flags one at a time closed four of the six by teaching
checks to read evidence they could not read before, and NONE of them by
signature:

  * **a negation can be a value.** A row bound BY LOCATOR whose field is false,
    null, 0, empty or a declared negative state has its negation carried by
    that value. The registry record contains no "no results", no "not posted",
    no "none" anywhere in it — the negation is a JSON boolean. Narrowed after
    implementation showed the wider version would clear a corpus claim on the
    strength of one field.
  * **a quantifier over named things is a count.** "each" is mapped when the
    sentence names trials the ledger resolves and the row rests on a span from
    every one of them. Cite one record of two and it flags.
  * **B14, a bounded figure negative.** One source, held in full: does it carry
    a hazard ratio, interval or p-value in a sentence about its OWN subject
    rather than another trial? This is the tractable corner of this gap, and
    building it exposed that KEYNOTE-942 — the most-cited trial on the page —
    was in no source's also_called, so nothing could resolve its name.

**The two the editor declined to sign, 2026-09-03.**

    "The ONLY survival figure in the programme ..."
    "... appears in ANY of the specialist or general coverage we hold ... ALL"

Both range over the whole programme — two trials, five releases, the papers,
four registry records. No search of one document settles either, and B14
correctly declines to try. The editor was offered a signed disposition with a
falsifier and chose not to take it:

> "Leave it for GAP-001."

**So this gap now blocks publication of issue one.** That is the consequence of
the decision and it is written here rather than discovered later: the
span-check row stays BLOCKED, and the only thing that clears it is the
library-wide search this entry describes. The signature was the cheaper route
and it was refused on purpose. The registry pair is the clearest: the row's premises already carry
`"reportingStatus":"NOT_POSTED"` from BOTH records, so "each" is satisfied by
evidence the row names and B6 cannot see it, because B6 looks for a WORD and
the force is carried by there being one span per record. A quantifier over
named things is mapped when the row rests on every thing the sentence names —
and that check can fail, which is the point.


---

## GAP-002 — there are two decisions files and only one of them is read

**Raised by** trying to re-gate issue one on 2026-09-03.
**Fix when** issue one is published, with GAP-001.

Eleven adjudications written on 3 September were recorded, correct, and
invisible. The board read none of them and the gate would have re-reported
every finding as new — a $4.61 run to rediscover judgements already made.

Two causes, both worth fixing:

**The path.** `factcheck_draft.DECISIONS` defaults to
`backend/tests/fixtures/draft_decisions.json`, which is where the board reads
from and where 239 production adjudications actually live. The issue folders
also contain `draft_decisions.json`, which is what a person naturally writes to
and what the queued gate jobs pass with `--decisions`. So a decision written in
the obvious place is read by the gate run and not by the board, and a decision
written in the fixtures place is read by the board and not by a gate run that
passes `--decisions`. Production adjudication records should not live under
`tests/fixtures` in either case.

**The key.** A decision matches on `(ROLE_OF[kind], normalised quote)` and then
on severity, where the role is `ADVOCATE`, `INFERENCE` or `SOURCE` and the
severity for a SOURCE finding is its CLASS — `NOT_FOUND`, `WRONG_VALUE`,
`WRONG_SOURCE` — not the display word. Ten decisions were written with roles
taken from the report's section headings and no severity at all, and matched
nothing.

`publish.py` already carries a comment about this exact failure: thirty-one
SOURCE decisions went silently unmatched because the key was the display word
rather than the class. The lesson did not transfer, because the recorder is a
person writing JSON by hand and nothing checks what they wrote against what the
matcher expects.

**Found in the wild, 3 September.** Seven decisions written on 28 August carry
an EMPTY severity. `classify()` keys on (role, quote), finds them, compares
severity, and reports STALE — which blocks. Worse, `load_decisions` keeps the
LAST entry for a key, so a malformed row written after a good one silently
overrides it: two email findings had been correctly adjudicated on 27 August
and re-adjudicated badly on 28 August, and the bad row won. The email gate had
read STOP ever since for no reason anyone could see.

Four were repaired by copying the severity from an identical decision elsewhere
in the file — evidence, not assumption. Three could not be, and are left
malformed rather than guessed:

    2026-08-28  melanoma.html  "The outlets The ASCO Post, Dermatology Times, OncLive, FierceBiotech…"
    2026-08-28  melanoma.html  "Dermatology Times, Pharmacy Times and Medical Daily stated plainly…"
    2026-08-28  melanoma.html  "Pharmacy Times published its coverage of the Phase 3 trial result on 19 August…"

All three quote text no longer on the page, so they block nothing today. They
are listed here because a repair nobody records is a repair nobody can check.

**Shape of the fix.** One path, not under `tests/`. A writer function that takes
a finding and a disposition and derives role, severity and quote from the
finding itself, so the key cannot be typed wrong. And a preflight row reporting
orphaned decisions — entries matching no finding — which is the signal that
would have shown this in seconds. `publish.py status` already computes an
orphan count; it is not on the board.

**A third cause, found while fixing the first two.** Finding ids are reused
across runs. Run 013's `o1` was an objection about the ASCO 2024 interval; run
014's `o1` is a contradiction about blinding. A script that deduplicated new
decisions on `(finding_id, date)` therefore dropped two of them silently, on a
day when both runs happened. The id is a position in one report, not a name for
a finding, and nothing in the file says so. The writer should key on the quote
and refuse to record a decision whose quote is not in the report it claims to
be adjudicating.

**What would show the gap is closed.** A test that writes a decision through
the writer for each of the three roles and asserts `gate_state` reports each
as ADJUDICATED rather than NEW; and one that writes two decisions carrying the
same finding id from different runs and asserts both survive.


---

## GAP-003 — the change log is checked by nothing

**Raised by** applying the 3 September gate's o5 finding.
**Fix when** issue one is published, with GAP-001 and GAP-002.

`body_only()` strips the change log before the binder and the quotation check
see the page. That was right when it was written — five modules had been
reporting the change log's own sentences as unbound claims, and "the change log
is not the article" is a real distinction.

But the change log is where corrections are explained, and explaining a
correction means quoting the document that forced it. Today's o5 fix put two
verbatim quotations into it — the January 2026 release's <q>one-sided nominal
p=0.0075</q> and the ASCO abstract's <q>No alpha was assigned to this
analysis</q> — and nothing checked either. Both were verified by hand against
held bytes; the quotation count stayed at 18 and neither appeared in it.

So the page's most self-critical section, the one a sceptical reader turns to
first, is the one section where a misquotation would pass silently.

**Shape of the fix.** The change log should be excluded from BINDING — its
sentences are about us, not about the world — and included in the QUOTATION
check, which asks only whether quoted words are really in the document they are
attributed to. That question is just as meaningful there as in the body. Two
different exclusions are being served by one function.

**What would show the gap is closed.** A test that plants a misquotation in a
change-log entry and asserts the quotation check reports it.


---

## GAP-004 — the meta description is prose that ships and nothing reads it

**Raised by** fixing the `<title>` leak on 2026-09-03.
**Fix when** issue one is published.

`page_sentences` now strips `<head>`, because `<title>` was arriving as page
prose with no full stop and gluing itself to the first thing after it. That is
right: a title is a label, not a sentence somebody wrote as a claim.

The meta description is not a label. Issue one's reads:

    Merck and Moderna announced a Phase 3 melanoma success and released no
    Phase 3 numbers. What was actually published, and what it will and will
    not support.

"released no Phase 3 numbers" is a universal negative about two companies. It
is the first thing a search result, a link preview, or a social card shows a
reader — for many readers it is the ONLY sentence of ours they will ever see —
and it is now, by our own fix, outside every check on this page. Before the fix
it was outside them too, because it lives in an attribute and tag-stripping
drops attribute values.

**Shape of the fix.** Extract `<meta name="description">` and the `og:` and
`twitter:` description content, and put those sentences through the binder like
any others. They are claims we publish. The count of sentences on the page goes
up by one or two and that is the honest number.

**What would show the gap is closed.** A test that plants an unsupported figure
in a page's meta description and asserts rule 1 blocks.


---

## GAP-005 — a figure is compared as a bare number, so an unrelated number clears it

**Raised by** probing the `restates` mark on 2026-09-03.
**Fix when** issue one is published.

Every figure check in this layer compares numbers with the units and the
quantity thrown away. Two consequences, both seen on the live page today:

**A claim cleared by a coincidence.** The stat strip's "14 deaths" is satisfied
by S004's `7 of 50 (14.0%)`. Fourteen deaths and fourteen per cent are not the
same statement, and `_as_numbers` cannot tell them apart. The strip is
therefore not marked `restates`, because the mark would pass for a reason that
is not a reason.

**A claim flagged by a coincidence.** B12 reported that we had added a decimal
to `0.053`, having found `0.05` in Greenland et al. — the conventional
threshold, in a statistics reference, with no relation to our p-value. That
particular flag has gone, because B12 now asks every source the row names and
one of them (the Lancet, in the row's own premises) prints `two-sided p=0.053`
verbatim. The underlying defect did not go: B12 still decides that two numbers
are the same quantity because their digits round to each other.

**Shape of the fix.** Carry the token around the figure — the unit, the
per-cent sign, the word it modifies — and require it to match before treating
two numbers as the same quantity. Where the surrounding token cannot be
recovered, say so and flag, rather than matching on digits alone.

**What would show the gap is closed.** A test asserting that "14 deaths" is NOT
satisfied by a span reading "7 of 50 (14.0%)", and that it IS satisfied by one
reading "14 patients died".

### Closed for the furniture marks, 2026-09-03

`modelbind.measurements()` now returns (value, dimension) rather than a bare
number, and `furniture.check_restates` compares quantities. The dimension is
read from NOTATION and never from a vocabulary of nouns: a per-cent sign, a
unit of time, a dose unit, or a following word (which makes the number a count
OF something). The word itself is not compared — "deaths" against "patients
died" would need a stemmer and would be wrong by Thursday.

The match rule is deliberately weaker than "the units agree": a bare number the
notation did not qualify matches anything, because flagging every unqualified
number would flag most of a page and teach the operator to scroll past the
check. It is exactly strong enough for the failure that produced it.

Four tests carry it, including the two named above.

**Still open: B12.** It continues to decide that two numbers are the same
quantity because their digits round to each other. The specific false flag that
raised this gap is gone for a different reason — B12 now asks every source the
row names, and one of them prints `two-sided p=0.053` verbatim — so nothing on
a live page is currently wrong because of it. The defect is still there.

**Still open: the stat strip.** With the fix in place, marking issue one's stat
strip `restates` BLOCKS, which is the correct answer and was not available
before: its "14 deaths" is the page adding S004's seven and seven. That is a
`computed` figure, not a restated one, and it needs either the working shown or
a different card.

## GAP-006 — a quantity written as a word is invisible to every check

**Found:** 4 September 2026, by a reader question about "not fourteen patients",
which was false and which nothing had examined.

`bindings.FIGURE` and `BARE_INT` match digits. `is_empirical` therefore never
classifies a sentence whose only quantities are spelled out, so no binding row
is created, so rule 1, rule 2, B2, B6 and b13 have nothing to look at. The
sentence is not checked and passed; it is never seen.

**Measured on the melanoma page:** 41 sentences state their only quantities in
words. None is bound. Among them:

- "It is that wide because it rests on fourteen deaths, seven in each arm"
- "on seven deaths in fifty patients it runs from a third of them alive to nine
  in ten"
- "the treated group's rate of death would be about a sixth of the control
  group's; at the other it would be about a third higher"

Each is a checkable quantitative claim.

**Why it is not fixed by adding the words to the pattern.** Most of the 41 are
prose that should not be bound — "a wide one means it did not", "a comparison of
how fast something is happening in two groups". A pattern that pulls all 41 into
the binder demands a source for those, and a check that demands the impossible
is one people route around. The bare-integer work has the shape of the right
fix: `counts_as_claim` asks whether the integer is doing quantitative work
(excluding phase names, dates, years) rather than whether it is an integer. The
same question has to be asked of number words.

**What closing it looks like:** number words are recognised as quantities when
they are doing quantitative work, the melanoma page's real cases are bound, and
the prose cases are not swept in.

## GAP-007 — the live site is behind the repository after a correction

**Found:** 5 September 2026, by the independent architecture reviewer, who saw
two corrected errors still on whatholdsup.org.

Corrections are committed and then wait for a person to run the publish script.
On 4 September two proposition-level errors were corrected in the repository
and the site was not republished, so both remained in front of readers while
the record said they were fixed. `publish.py check` reports "live page DIFFERS
from the repo — the site is behind" as a WARN, and a warn among twenty-five
other warns is not a control.

The reviewer's framing is the right one: a correction should be a first-class
release with its own state, not an edit that waits for someone to remember.

**What closing it looks like:** an uncorrected live page blocks, loudly, with
the sentences named — or corrections publish themselves once their own checks
pass.

---

## A staleness test evaluated against the same narrowed view that created the staleness

Found 2026-09-09 in `b13.py`. The class: a check asks "is this record still
live?" and answers it against its own filtered view of the page rather than
against the page. Anything the filter removed is then reported as dead.

The instance. `b13.figures_on_page()` drops sentences matching `AB.OURS` — the
page saying it did a sum itself — and `bindings.page_sentences()` strips the
change log. A declared figure-exclusion for `3.40`, which lives only in a
change-log sentence about the page's own arithmetic, could therefore never be
marked `used` here, and the staleness test compared its `in_sentence` against
that same doubly-narrowed list. It reported the entry as an exclusion that had
outlived its sentence. `corrections_check.py` reads the change log with no
`OURS` filter and genuinely needs the entry: deleting it as dead would have
re-blocked that module on a figure that is the page's own arithmetic.

This is the second instance in the same function. The comment above the code
records the first — an exclusion skipped because the figure also turned up in
some held document, so the rule was never reached and was reported as dead. The
fix then was to stop inferring staleness from `used` alone. The fix now is to
compare against the whole page, normalised on both sides, because
`ledger.plain()` leaves a double space wherever it stripped a tag while the
sentence forms the rules were keyed from have one.

**What makes the repair trustworthy is the regression test, not the green row.**
Verified after the change: the two live entries register live, a fabricated
`in_sentence` that is not on the page registers stale, and the retired 3.35
wording — a genuinely dead entry — still registers stale.

**Where it will recur:** anywhere two checks share a source file and differ on
scope. The scope difference is invisible from inside either one. `b13` and
`corrections_check` share `figure-exclusions.json`; `sources_shown` and the
bindings share `bindings.json` and differ on whether the reader-facing list
counts, which is the same shape and was mis-described three times before anyone
read the code.

---

## Structural: the "Why this is worth a whole article" box carries too much before its turn

Recorded 2026-09-09, for the next revision. **Not a factual defect and not to be
edited now** — restructuring dense prose at the last moment, in a passage already
misread twice, is how a further error gets in.

Two independent automated readings misread the same box on two consecutive
`changecheck` runs. The first collapsed the two subjects of "A post logged by KOL
Pulse identified the figure … ; KOL Pulse's own text names the trial throughout"
and reported a contradiction between them. The second read the enumeration under
the kicker as implying the outlets were at fault, against the page's own "The
problem is not misattribution".

Both readings are wrong and both dispositions stand. But two misreadings by
independent readers is a signal about the prose rather than only about the
checkers. The box asks a reader to hold, in order: an enumeration of five
outlets; a correction about which author omitted a trial name; three block
quotations; a parenthetical about a source we lost and regained and one we still
do not hold; and only then the turn — that the attribution was correct and the
problem is subtler. The resolution arrives after everything it resolves.

**What closing it looks like:** the turn stated near the top, so a reader knows
what the enumeration is evidence *for* before reading it.

---

## An artefact of measurement mistaken for a fact about the page

Four instances in one cycle, 2026-09-08/09, and they run in **both** directions —
a live thing reported as a defect, and a defect reported as a pass. That symmetry
is why this is a class and not four bugs.

| # | the measurement | what it reported | what was true |
|---|---|---|---|
| 1 | `b13` staleness tested against its own filtered sentence list | a live figure-exclusion had outlived its sentence | the sentence was in the change log, which that list strips |
| 2 | `grep -c "Consensus scores 4 because"` on raw HTML | the prose had been removed during a records-only pass | `</strong>` sits between the two halves; the string never existed in raw HTML |
| 3 | a fixed 2,400-char raw-HTML window, tag-stripped | "the paragraph runs to 2,116 characters" | the paragraph is 1,013; 2,116 was the window |
| 4 | `_norm(quote) in _norm(draft)` in the adjudication check | a live gate decision quoted a sentence that was gone | stripping `<q>` leaves a space before the comma; the sentence is verbatim on the page |

Also, in the other direction and in the same days: `cmp -s` reporting a **missing**
file as a **diverged** one, and a correction published saying a clause had been
removed when it had not — measurement of the wrong artefact, again.

**What they share.** In each case something was measured that was *adjacent* to
the object of the claim — a filtered view, a raw serialisation, an arbitrary
window, a normalised string — and the result was reported as a fact about the
object. It is failure 14 pointed at our own tooling instead of at a source, and
it is why "the check says so" is not by itself evidence.

**What closing it looks like:** before a check's output is acted on, its false
negative and its false positive are both stated. A check that has never been made
to fail on purpose has not been tested, only run. The b13 repair is the model —
the regression test that proves a genuinely dead entry is still caught is the
part that matters, not the green row.

---

## The documents that tell us we are wrong are the ones we are least likely to hold

Errata, correction notices, letters to editors, comments. They are short,
low-value to indexers, frequently paywalled, and almost never deposited to the
open archives that carry the papers they correct. They are also the only class of
document that can falsify a figure already published.

Two live instances, both in this issue:

- **S029** — the NEJM paper behind the ipilimumab counterexample was formally
  corrected in 2018. The notice is subscription-only at NEJM (403 to a script),
  absent from PubMed Central and Europe PMC (`isOpenAccess N`, `inEPMC N`), and
  carries no abstract at PubMed or Crossref. We hold its bibliographic record as
  S030 and cannot read the notice. `corrections not yet read` blocks on it.
- **S028** — the letter whose reference list falsified a claim on this page.
  Its own text is unheld and paywalled.

The near-miss worth recording: S028 turned out to be **partly** reachable after
all. The publisher deposited its reference list to Crossref, so the one fact the
correction turns on is machine-readable from the DOI, even though the letter is
not. That was found on 2026-09-09 by looking up an identifier that had been in
the source record since 4 September and had never been queried.

**What closing it looks like:** when a source is acquired, its `Erratum in`,
`Comment in` and `Correction of` fields are read at the same time, and the
identifiers already in the record are actually queried rather than stored. Both
S028's DOI and S029's erratum were sitting in our own files, unqueried, while the
page made claims that turned on them.


---

## Access-state vocabulary does not describe structured publisher metadata

The store has six access states — `full_text_held`, `human_read`,
`abstract_held`, `fragment_only`, `blocked`, `not_opened` — and every one of them
describes how much of a document's **prose** we have. None describes the thing
S028 actually is: a publisher's Crossref deposit, carrying the full bibliographic
record, a twelve-item reference list and an author ORCID, with the article's own
text unread and paywalled.

`abstract_held` is what S028 carries and it is wrong in both directions at once.
It **understates** what we hold — we have the complete reference list, which is
the only part the claim turns on, and it is machine-readable and reproducible by
anyone with the DOI. It **overstates** what we read — we have not read the
abstract either.

S028 is the first claim on this site resting on structured metadata rather than
on prose, and it will not be the last: reference lists, `Erratum in` fields,
ORCID, `Comment in`, registry field paths. The bindings store already has
`locator_type: field` for the registry case, so half the vocabulary exists on the
binding side and none of it on the source side.

**Not decided here, deliberately.** Adding a state mid-cycle, to make one source
look right, is how a taxonomy acquires a category that fits exactly one thing.
The question is what a state should describe — the artefact, the retrieval, or
what it licenses us to say — and that is a decision to take with the whole
vocabulary in view.

---

## The KOL Pulse box — REQUIRED for the next revision

Escalated 2026-09-09 from an optional structural note. **Three automated
misreadings, three consecutive `changecheck` runs, two different readers, three
different sentences.** The third was not caused by editing the box at all: an
unrelated sentence in it got shorter, the segmenter regrouped, and a previously
disposed finding came back under a new `finding_key`.

Every claim in the box is correct and every disposition stands. That is now
beside the point. At three independent misreadings, "the claims are correct" is
not a sufficient answer — the passage is defeating readers, and a page whose
subject is prose that misleads without being false does not get to have one.

The box asks a reader to hold, in order: an enumeration of five outlets; a
correction about which author omitted a trial name; three block quotations; a
parenthetical about a source lost and regained and one still not held; and only
then the turn — that the attribution was correct and the problem is subtler. The
resolution arrives after everything it resolves.

**What closing it looks like:** state the turn near the top, so a reader knows
what the enumeration is evidence *for* before reading it.

---

## Gate budget: an operator decision, not an overrun

Recorded so the next issue starts from a known position rather than rediscovering
this.

Eight gate runs against a budgeted three. **$36.34 spent of a $40 per-issue cap**
(measured 2026-09-09; it was $36.29 earlier the same day and moved because of
this cycle's own `changecheck` runs). The budget's own note says an issue through
a first run, an outside review, two re-gates and a counterexample hunt "should
land near $25", and that hitting $40 "means something is wrong with the process,
not with the budget."

**The operator ruled against overriding the budget.** That ruling is the reason
43 empirical sentences on the published page have never been examined by any
role, and it is a defensible trade — but it is a decision with a cost, and the
cost is these 43 specific sentences. `unjudged.py` degrades to WARN rather than
BAD once the budget is spent, on the reasoning that a STOP with no available
remedy trains the operator to waive. So this will never block; it will only ever
warn. That is why it is written down here.

The 43, as of page sha 2727429064d69721:

   1. Why this is worth a whole article Five outlets whose articles we hold named KEYNOTE-942 when attributing the 49% figure — The
   2. A single hazard ratio summarising five years assumes the ratio held steady across those five years.
   3. There is one patient-level reading a hazard ratio does support.
   4. Take one treated and one untreated patient at random: at a hazard ratio of 0.510 there is about a 66% chance the treated one
   5. The hazard ratio tells you who is likely to win.
   6. These are 95% intervals, the convention readers meet elsewhere.
   7. The trial registered a one-sided alpha of 0.10; its later three-year paper reports both 80% and 95% intervals for the updated
   8. Amber bars cross the 95% no-effect line; green ones clear it.
   9. Both bounds came in, the upper from 0.906 to 0.887 and the lower from 0.288 to 0.294, so the interval narrowed slightly.
   10. This trial's own threshold is on the record: the three-year paper says the trial was designed with approximately 80% power to
   11. In EORTC 18071, adjuvant ipilimumab versus placebo in resected stage III melanoma reported overall survival as a prespecified
   12. One caveat the figures on this page raise themselves: intismeran is an intramuscular injection that caused injection-site pai
   13. Morning Glory Sciences — we give its argument on its merits rather than on its authority — the Phase 2b population was stage
   14. In the Lancet report, immune-mediated adverse events were similar — 36% in the combination arm and 36% in the monotherapy arm
   15. At five years the company release puts immune-related events at 45.2% versus 44%, over a longer window than the Lancet’s.
   16. The three-year paper reports a hazard ratio of 0.425 on nine deaths, 95% CI 0.114 to 1.584; the five-year analysis reports 0.
   17. Dermatology Times — Personalized mRNA-Based Melanoma Vaccine Meets Primary Endpoints Practical Dermatology — Intismeran Plus
   18. Primary INTerpath-001 — ClinicalTrials.gov, NCT05933577 Registry record.
   19. Primary KEYNOTE-054 — ClinicalTrials.gov, NCT02362594 Registry record.
   20. Primary KEYNOTE-716 — ClinicalTrials.gov, NCT03553836 Registry record.
   21. Primary CheckMate 238 — ClinicalTrials.gov, NCT02388906 Registry record.
   22. Primary Spruance, Reid, Grace & Samore — Hazard Ratio in Clinical Trials Antimicrob Agents Chemother 2004;48(8):2787–2792.
   23. Primary Survival Analysis — StatPearls, NCBI Bookshelf Source for the direction a hazard ratio moves in: risk rises as the va
   24. Source for what a hazard ratio of 1 means, and for the caution that a hazard ratio is not a proportion of patients benefited.
   25. The word interim appears nowhere in the NCT05933577 record, and that record has not been updated since 24 September 2025 — el
   26. The lower moved from 0.288 to 0.294, which is inward on any reading — closer to 1.0, closer to the point estimate, closer to
   27. We set 45.2% against 44% for any-grade immune-related events, then 25% against 18% for grade 3 or worse, in a single sentence
   28. The Lancet reports both on the same patients at the same cut — immune-mediated events 36% in each arm, grade 3 or worse treat
   29. In EORTC 18071, adjuvant ipilimumab against placebo in resected stage III melanoma reported overall survival as a prespecifie
   30. We wrote that an assessor who does not know the arm cannot favour it, and printed, a few hundred words later, that the therap
   31. The reviewer also proposed attaching the three-year paper's 80% interval, 0.351–0.743, to the 2023 readout.
   32. It belongs to the three-year hazard ratio of 0.510, and no 80% interval for the 2023 result exists in any document we hold.
   33. The hazard-ratio explainer now names the assumption underneath a single hazard ratio — that the ratio held steady across the
   34. The confidence-interval chart now says that its amber and green split is a convention rather than a verdict, and that this tr
   35. And the three-year survival interval is now given at 95%, 0.114–1.584, so that it can be read against the five-year 0.165–1.3
   36. What differed was the working itself: reproducibility and recency were shown at 15% each where the rubric gives them 20% and
   37. We had credited KOL Pulse with giving the 49% figure as a phase 2 result without naming the trial; the outlet names KEYNOTE-9
   38. The published page scored this assessment 3.4 , beside a working that gave reproducibility and recency 15% each.
   39. The rubric gives them 20% and 10% .
   40. On 2 September we said a “five-year topline of 20 January 2026” reporting a one-sided nominal p = 0.0075 would stay out until
   41. Our p-value gloss said that if the drug were useless you would see a result this good about 5% of the time, which quietly dro
   42. And one hazard ratio did circulate under the Phase 3’s name.
   43. A melanoma oncologist posted, in a roundup we hold, Exciting announcement today from Phase3 INTerpath001 followed by RFS HR=0

Most are the 8 and 9 September additions: the hazard-ratio explainer, the chart
caption, the EORTC counterexample, the blinding caveat, the scorecard reasoning
and the change-log entries. They are bound and span-checked — rule 1 and rule 2
pass on all 131 — but bound is not the same as read by a role looking for what
the binding cannot see.

---

## Dates: the record stamps are zone-unlabelled, and nothing enforces a policy

**Recorded 2026-09-09, deliberately not fixed.** Three reader-facing date sites
were repaired the same day (`index_dates`, `corrections_intake.business_days_since`,
the masthead in `publish.py`), each with a regression test. Roughly thirty others
were left exactly as they are.

They are the record stamps: `date.today().isoformat()` in `bindings.py` (260,
312, 651, 761), `source_store.py` (571, 618, 622, 626, 631, 682),
`source_ledger.py:735`, `errata.py:392`, `deletions.py:209`, `findings.py:208`,
`premise.py:323`, `modelbind.py:254`, `counterexample.py:403`,
`source_advocate.py:435`, `sweep_sources.py` (252, 325), `scan_leads.py:219`,
`review_bundle.py:186`, `review_packet.py:328`, `watch.py` (246, 314, 340), and
`time.strftime("%Y-%m-%d")` in `find_access.py:215`.

Each writes a bare `YYYY-MM-DD` with no zone, from whichever machine ran the
command. This repository's commits carry four different offsets — `-05:00`,
`-04:00`, `Z` and `-06:00` — so "the day this was checked" means a different
thing depending on where somebody was sitting.

**Why not today.** Thirty edits at the end of a close-out is how the next error
enters. The same reasoning deferred the KOL Pulse box and the weight binding.

**The eventual fix is not thirty edits.** It is one helper that every stamp calls,
so the policy lives in one place and can be tested once — the shape the three
repaired sites now have, where `index_dates.EDITORIAL_TZ` is the single
definition and the other two import it rather than restating it. Next cycle,
with a test.

**The residue in the meantime.** `watch.days_since_check()` now reads *today* in
the editorial zone but subtracts a stored `"on"` that is still one of these
unlabelled stamps. That is better than two live clocks and it is not correct; it
is listed here so the improvement is not mistaken for a repair.

---

## `corrections.md` has no generator, and a machine-derived date is grepped against it

The public correction history is written by hand. Its dates are editorial-local
by convention and enforced by nothing — no code produces them, no check reads
them for consistency with the record.

`publish.py:1483` then does `logged = today in corrections_text(slug)`, grepping
a *derived* pretty date against that hand-typed prose to decide whether a change
has been recorded for readers. Until 2026-09-09 the derived side came off the
local clock, so the two agreed only while every machine sat in New York; it now
reads `EDITORIAL_TZ`, which removes the zone half of the problem and leaves the
other half standing.

**A hand-maintained representation checked by a machine-derived one is the shape
of this entire day.** The index had it, the family instance count had it, and
this has it. The check passes when a human happens to have typed the same string
the machine happens to derive.

---

## `record-live` writes `action: "republish"` for something that is not a republication

The record uses one word for two events. `publish` and `update` are things that
happened to the argument. `republish` is what `record-live` writes when a person
has read a diff and signed it as **not** touching the argument — every row
carrying it in `published.json` is a live-sha reconciliation, distinguishable
only by the `basis`/`diff`/`supersedes` keys the publication rows do not have.

This is `b13`'s two-notions-of-"used" one layer down: two meanings under one
name, with the distinction living in a reader rather than in the data.

**The dependency runs both ways and both directions can break silently.**

| consumer | reads `"republish"` as | if the vocabulary is fixed at source |
|---|---|---|
| `index_dates.PUBLICATION_ACTIONS` | *a reconciliation* — excluded from reader-facing dates | **breaks silently.** A new action name falls through to neither tuple, and a nav-link reconciliation starts printing "updated" on the homepage |
| `guard_published.py:129` | *a sign-off exists* | breaks: a new name must be added to `wanted` or the pre-push guard stops recognising a signed page |
| `publish.py:1833`, `:1955` | *the last signed-off sha* | breaks: `record-live` and `update` would stop finding the row they supersede |

`index_dates` is currently the **only** consumer that needs the two meanings kept
apart, and it is the only one that would fail without saying so. Whoever splits
the vocabulary must change it in the same commit.

**Not fixed now, on purpose.** Renaming an action rewrites the meaning of rows
already written, and `published.json` is the record a publication decision rests
on. It is a schema change with a migration, not a tidy-up at the end of a cycle.

---

## `store.case_dir()` raises `SystemExit` from library code

**Recorded 2026-09-09, deliberately not changed.**

`source_store.case_dir(slug)` ends with `raise SystemExit("no case directory for %r" % slug)`.
That is a library function making a terminate-the-process decision that belongs
to its caller. It is why a correct-looking guard in
`bindings._declared_exclusions()` caught nothing: the author wrote
`except Exception`, which is the right instinct and the wrong clause, because
`SystemExit` derives from `BaseException`.

The guard is fixed — `except (Exception, SystemExit)`, naming what is actually
thrown rather than reaching for bare `BaseException`, which would also swallow
`KeyboardInterrupt` and make a hung run uninterruptible through that path.

**The defect underneath is untouched.** `case_dir()` is called from many places;
changing what it raises is a change to every one of them, and each caller would
need to be read rather than assumed. The correct shape is a
`NoCaseDirectory(Exception)` raised by the library and a `SystemExit` chosen by
the command-line entry points, which are the only layer entitled to end the
process.

**Why it matters beyond the one call site.** Any future caller that guards this
function with the obvious `except Exception` gets the same silent nothing. The
next person will write the same clause, for the same good reason.

---

## Failures that reach a reader are the ones that do not announce themselves

Three instances, all found 2026-09-09, which is what makes it a class rather
than a coincidence:

1. **The `action: "republish"` consumers.** Five things read that value. Four
   fail loudly if the vocabulary is fixed at source — a name they do not
   recognise stops a guard or a lookup and somebody sees it immediately. The
   fifth, `index_dates.PUBLICATION_ACTIONS`, falls through to neither tuple and
   starts printing "updated" on the homepage for a nav-link reconciliation.
   **The one that fails silently is the only reader-facing one.**
2. **The dateline gate** returned green over the half of the masthead it never
   read, for twelve days, while a false publication date sat on the live page.
3. **The guard that caught nothing** left 22 tests red with no signal that
   anything had changed, because a guard that swallows everything and a guard
   that catches nothing look identical from outside.

The common shape: **the louder a failure is, the further it is from a reader.**
Loud failures stop the person who caused them. Silent ones travel. When choosing
what to harden next, prefer the quiet path over the frequent one.

---

## `or True` in a test, caught by its own author

The first version of `test_a_bare_date_survives` in
`backend/tests/test_whatholdsup_dates.py` read:

```python
assert C._editorial_day("2026-09-01") == date(2026, 8, 31) or True
```

Which passes whatever `_editorial_day` returns. It is the same object as a stop
wired to a probe that cannot fire, one layer up: a construct whose triggering
condition was never produced, sitting in the file whose whole purpose is to
produce triggering conditions.

It was caught and removed before it was committed, by the person who wrote it,
while checking why it passed. **It is recorded because it was caught rather than
in spite of it** — the failure mode is not "somebody wrote a bad assertion", it
is "an assertion that cannot fail is invisible in a passing run", and the only
reason this one is visible is that its author looked at a green line and asked
why it was green. It also had a second life: the assertion was hiding a real
defect, that a bare `--on 2026-09-01` was being read as midnight UTC and shifted
back a day. Fixing the test found the bug the test was written to cover.

---

## Bindings cannot tell a sentence from its quotation

**Confirmed 2026-09-09. Recorded, deliberately not fixed — next cycle.**

`bindings.fingerprint(sent)` is a hash of the sentence text, and it is the key a
binding is stored under. **Two identical sentences have one key.** A change-log
entry that quotes a body sentence verbatim is therefore *bound by construction*:
the binder cannot distinguish the log copy from the body copy, and neither can
anything downstream of it.

`corrections_check.py:197` carries the figure-level form — a figure appearing in
a change-log sentence is exempted from the `b13` "is this figure in a document we
hold" check **if the same figure appears anywhere in the body**.

### Nothing is wrong today, and that is not reassuring

The two overlapping sentences on the melanoma page were investigated on
2026-09-09 and the log genuinely quotes the body: body copies `0daab2e`
(3 September), log copies `853200c` (9 September), six days apart. The
declarations and their evidence are in
`issues/WHU-001-melanoma/log-quotations.json`.

**The defect is that the mechanism cannot check what was just checked by hand.**
It cannot tell a legitimate quotation from an illegitimate one, because it cannot
tell a quotation from the thing quoted.

### The failure mode, stated so nobody has to re-derive why it matters

> **A change-log entry that quotes a sentence later REMOVED from the body stays
> bound to a span that no longer supports anything on the page — and reads as
> verified.** The binding survives because the key is the text, and the text is
> still there. Only its subject has gone.

The same shape covers a log entry that quotes an **external claim we do not
endorse** — "an outlet reported X" — where X acquires the body's binding and the
apparatus reports the page as having a source for a claim it exists to dispute.

**A second, independent manifestation, 10 September 2026.** The epistemic check reported
that a correction announcing the removal of an ASCO Post quotation was false,
because the phrase *"key secondary endpoint"* is on the page. It is — **four
times, in our own prose.** The quotation is gone. The check matched a string
without its attribution, which is the same defect as bindings keying on
`fingerprint(sentence)`: **the apparatus cannot tell a sentence from its
quotation.** Two independent manifestations, arrived at by different routes, is
what makes the case for fixing the root rather than patching either symptom.

The staleness arm of the B18 exemption is the interim control: if a declared
overlap stops matching, the test fires and names this hazard. It catches the
melanoma case. It does not catch the general one.

### Why not now

Making bindings region-aware — keying on `(region, fingerprint)` or refusing to
bind inside `<footer id="updates">` at all — is a change to the core of the
apparatus, and every existing binding's key changes with it. That is a migration
of `bindings.json` on three issues, not a close-out edit. The same reasoning has
deferred the weight binding, the thirty record stamps and the KOL Pulse box.

---

## A score is printed without the arithmetic that produced it

**Design recorded 10 September 2026. Nothing built, and the deferral is deliberate.**

The melanoma page prints `3.94` for *is the effect real*. `the-rubric.html`
prints the six weights that produce it. **Nothing connects them.** The score was
computed under whatever the weights were on the day it was computed, and the
page records the result without recording the inputs.

### The mechanism is live today

RV-06 is not a historical error, it is a standing one. Edit the percentages in
`the-rubric.html` and the published `3.94` silently becomes a number the rubric
no longer produces. **Every check still passes** — `furniture.py`'s `computed`
mark re-derives the score from the scores printed beside it and the weights
printed beside *those*, so it verifies the page against itself and would go on
passing after the rubric moved underneath it. The figure-exclusion for `3.94`
names that mark as its falsifier, so the exclusion would keep standing too.

This already happened once in the small: commit `87b8d9d` of 3 September
corrected a working from 3.40 to 3.35 because two of the six weights had been
shown at 15% where the rubric gives 20% and 10%. It was found by a person
reading two documents side by side.

### The design

**(a) Record the weight set in the issue's record at publish time.** A score
should carry the arithmetic that produced it: the six weights, the six component
scores, and the rubric version they came from, written into the issue record
when the page publishes. Not read from `the-rubric.html` at check time — read
from it *once*, at publish, and frozen. The same discipline as
`rules_rendered`: what was in force when the thing went out.

**(b) Two checks, and they are not the same check.**

| check | asks | fails when |
|---|---|---|
| internal consistency | does the printed score equal the recorded weights applied to the recorded component scores? | the page's own arithmetic is wrong |
| rubric drift | do the recorded weights equal the rubric's **current** weights? | the rubric moved after publication |

The second is not an error and must not be reported as one. **It is a fact the
reader is owed:** *this score was computed under a rubric we have since
changed.* Collapsing the two would either suppress a real arithmetic error or
raise a false alarm every time the rubric is legitimately revised — and the
second failure mode trains people to ignore the first.

### Why deferred, and to where

To **the start of the next issue**, not to "later". Building it now means
building it against one scorecard on one page and testing it against nothing:
the only way to know the drift check works is to have a second weight set to
drift from, and the next issue is where that appears. Building an untested
detector for a failure that has already occurred once is how failure 16 gets a
fourth instance.

---

## Subscribers hold a superseded version of both emails

**Recorded 10 September 2026.** The pre-push guard prints this as a WARN on every push. A
warning that scrolls past on a push is not a record, and both of these have been
true for a week or more.

### Issue two — `email/issue2-cdk46.html`

Sent **2026-08-29T14:33:42Z**, sha `f4fa716462ff6cd7` (commit `5b2775e`). On disk
now: sha `8d90545235a4319c`. **Nine sentences differ.** The one that matters:

> **As sent:** "…including that the width of abemaciclib's interval is itself a
> consequence of what that trial was powered to detect — a point **Jacot** and
> colleagues made formally in *npj Breast Cancer* in 2018…"

Two errors in one clause. The first author of that paper is **Marie-Laure
Tanguy**, not Jacot. And the point attributed to them is ours: their paper
computes each trial's statistical *power* to reach significance on survival and
concludes that significance appearing in some trials and not others "might be
more attributable to chance than to a truly different drug efficacy". It says
nothing about the width of a confidence interval.

The other eight: hazard ratios named as such rather than "figures"; the scope of
the eight-readout claim bounded ("not about every analysis ever run on these
datasets"); and the sourcing sentence replaced, because "none comes from a news
report" was not true of the whole table.

### Issue one — `email/issue1-melanoma.html`

Sent **2026-09-04T16:27:37Z**, sha `5ef7890a0d09a895` (commit `1862820`). On disk
now: sha `74d5a094da86e4a7`. **Seven sentences differ.** The one that matters:

> **As sent:** "…reports 0.425 on nine deaths, with an **80% interval** of 0.179
> to 1.004…"

An 80% interval printed beside 95% intervals elsewhere in the same email. A
reader comparing them reads a narrower uncertainty than the data supports. The
page now prints **95% CI 0.114 to 1.584** — the wider of the two, which is what
nine deaths actually support.

The rest are sourcing-sentence corrections: "every figure" narrowed to "every
numerical trial result", with the acknowledgement that claims about what an
outlet reported trace to the coverage itself, and a plainer statement of what
the pre-publication checks do and do not test.

### Standing

**Nothing has been sent.** A correction note is drafted for the top of the next
outgoing email — cdk46's attribution first, because it has a third party's name
on it, then the melanoma interval. The sourcing-sentence changes go to the
record only; they correct an overstatement about our own process and need no
announcement.

---

## A signal that exists and goes unread

**10 September 2026.** The pre-push guard has printed, on every push since 31 August:

```
WARN  cdk46: site/whatholdsup/cdk46.html has been live at an unrecorded version
      published 2026-08-31T16:58:05  content 4e4bb50b371fcd3a
      live now                       content 112e7a397d01481e
```

**Ten days, unread.** The same drift was then found a second time, from the
other end — by comparing masthead datelines against the publication record — and
reported as a discovery.

Two things follow, and the second is the entry.

**It is corroboration.** Two routes, different mechanisms, same finding: a guard
hashing files against the record, and a check reading prose dates against the
record. Neither knew about the other. That is the strongest form the evidence
could take, and it should be recorded as such rather than as an embarrassment.

**It is a third variant of the silent-failure class, and the worst one.** The
other two are a signal that never fires and a signal that fires with the wrong
message. This is **a signal that fires correctly, in the right place, and is not
read** — and it is worse than no signal, because the guard's existence is
counted as coverage. Nobody was going to build a second check for a thing the
first check was already reporting. A warning printed into a push's output, in a
paragraph with two other warnings, on a step whose success is signalled by the
push completing, is a signal designed to be scrolled past.

The fix is not a louder warning. It is that **a standing condition belongs in a
standing record**, where its age is visible, and the WARN's job is to point at
it. That is what the entry above this one does for the emails.

---

## Nothing checks whether `corrections.md`'s own claims are still true

**10 September 2026. The correction log has now been wrong twice, in two different ways.**

| when | what it asserted | what was true |
|---|---|---|
| 1 September 2026 | a correction had been published; the deletion note explaining it was printed | the change had never been made, and the note explaining it was false |
| 31 August–10 September 2026 | the MONARCH 3 corrigendum *"remains unread and is still disclosed as unread"*, and *"the first version was right"* — that it sits behind a paywall | it was held in full on 1 September, one day later, and it is open access under CC BY-NC-ND |

The second is the more instructive because **the sentence was true when it was
written.** It became false the next day and nothing noticed for nine. A dated
record is allowed to age; what is missing is anything that reports when it has.

### The gap, exactly

`corrections_check` tests corrections **against the page**: does the log say what
the page shows. Nothing tests a correction's assertions **against the source
store**. So a correction can assert an access state, a read state, or the
contents of a document, and no check ever compares that assertion with what
`sources.json` and the held bytes actually say — even though both are in this
repository and both are machine-readable.

That is the same shape as the homepage before `index_dates.py`: a reader-facing
document with no control pointed at it, going stale while every other control
stayed green.

### The design, recorded, built nothing

Any `corrections.md` entry asserting an access state must agree with
`source_store`. The store already holds, per source, `access.state`, the date it
was held, the sha of the bytes and the route; a correction that says "unread",
"paywalled", "open access" or "held in full" is making a claim about exactly
those fields. The check is a comparison, not a judgement.

**Deferred for the same reason as the weight drift**: there is one instance to
test against, and one instance is enough to write a check that passes and not
enough to know it fires. It goes on the next issue's list, where a second
correction asserting a second access state gives it something to disagree with.

**The narrower point, worth keeping separate from the design.** The failure here
is not that the log was wrong. It is that **a dated record has no expiry and no
freshness signal**, so "true when written" and "true now" are indistinguishable
to every reader including its author. Any check built for this should report the
*age of the assertion* alongside the disagreement, because the nine days are the
finding, not the mismatch.

---

## An unverifiable count of one's own errors is a flattering claim in damaging clothes

**10 September 2026, from the OR-C ruling on cdk46.**

The page says *"This is the fifth position this page has taken on one fact."*
That reads as damaging and it is not, quite. **It asks for credit for candour and
cannot be audited** — a reader has no way to check whether the number is five,
or four, or seven, and the only direction the error can run is the one that makes
us look more scrupulous than the record supports.

Run through the direction column, it leans toward us. **Self-criticism is a
flattering form**, and a self-criticism carrying an unverifiable number is the
flattering part wearing the damaging part's clothes.

**The corroboration is that this has already happened twice, today.** Two counts
maintained in prose have been found wrong: the failure-family instance tally,
which ran ahead of the RV series because it lived across four documents with no
register, and "four commits", which under-described the cdk46 drift and was
carried into a directive without being re-measured. Neither was maintained
dishonestly. Both were wrong.

**Resolved on the page rather than removed**, because the enumeration turned out
to be there already: the sentence names all five positions and the next sentence
says why each was wrong. What it lacked was dates. Each now carries the day it
was on the page — 28, 29, 30, 31 August and 1 September — derived from
`git log -S` over the page's own history rather than from anybody's memory, and
pointing at the change log so the count can be checked instead of believed.

**The rule this leaves.** A count of our own failures is a claim like any other
and carries the same obligation: it is stated with the evidence that lets a
reader falsify it, or it is not stated as a number. *"This page has repeatedly
changed its position on this fact; the log records each change"* asserts nothing
a reader cannot check.

---

## The epistemic-state check: it passes its test set and fails the corpus, 4/4

**Built 10 September 2026. NOT wired into `check`, and the reason is the finding.**

`backend/scripts/whatholdsup/epistemic.py`, with `test_whatholdsup_epistemic.py`
written first. Against the five-instance test set it does exactly what was
asked — three fire, two do not, including the S029 erratum disclosure, which is
the hard one because S030 *is* held in full and what is held is the PubMed
record, not the notice.

**Run across all three issues it produced four findings and every one is a false
positive.** Zero true findings.

| # | issue | what it said | why it is wrong |
|---|---|---|---|
| 1 | cdk46 | S021 asserted UNREAD, store says `full_text_held` | the sentence is about the PALMARES-2 **paper**; S021 is the PALMARES-2 **ClinicalTrials.gov record**. Holding the registry record is not holding the paper |
| 2 | cdk46 | S002 asserted READ, store says `fragment_only` | the sentence is about the **corrigendum**; S002 is the 2017 trial paper, matched because the sentence mentions "MONARCH 3" |
| 3 | melanoma | S002 asserted READ, store says `abstract_held` | *"the five-year release we hold"* is true — the release **is** held, as an abstract. My rule treated `abstract_held` as not-held for every read-predicate |
| 4 | melanoma | a correction says a quotation was removed; the phrase is on the page | the phrase *"key secondary endpoint"* is on the page four times, in **our own prose**. The **ASCO Post quotation** of it is gone. The check matched a string without its attribution |

### What this actually establishes

**Three of the four are one problem: resolution.** The check tells READ from
UNREAD reliably — that half is a vocabulary match and it works. It cannot
reliably tell **which document a sentence predicates about**, as opposed to
which documents it mentions. A sentence naming three sources and asserting
something about one of them is the normal case in this publication's prose, and
the check has no way to find the subject.

### And the test set was too easy in the one dimension that matters

This is the part worth keeping. All five fixtures had an **unambiguous subject**.
I satisfied failure 16 — made it fire, made it not fire — on a set that never
exercised the mechanism that turned out to be load-bearing. **"Make the construct
fire once" is necessary and it is not sufficient: a test set drawn from known
incidents tests the part of the problem the incidents made visible, and the part
they did not make visible is exactly the part nobody has looked at.**

The corpus run is what found this, and it cost one command. **Run a new check
against the whole corpus before wiring it in, always** — the test set says
whether it works on what you already understood.

### Two store-level facts it surfaced, which are worth more than the check

**The record-vs-document distinction is carried in three different ways.** S030
declares `form: record`. S021 carries it only in prose — its title says
"ClinicalTrials.gov record" and no field says so. S025 carries `type:
corrigendum`. A check cannot ask the store *"is this a document or a record
about one?"* and get a reliable answer, because the store answers it in a field,
in a title, or not at all, depending on who wrote the entry.

**And an alias gap made a source invisible.** S025 had no `also_called` at all,
so no sentence could resolve to it — the very source at the centre of two of the
three incidents. Aliases were added. But this means **coverage silently depends
on how well each source entry was filled in**, and a source with no aliases is
not checked rather than checked and passed. That is a silent failure of exactly
the class recorded above it.

### What happens next

Not wired in. It stays runnable by hand (`python3 epistemic.py`) and the test set
stands as a regression fixture for the three incidents. The subject-resolution
problem is the next issue's work, and the honest statement of it is: **this is
not a vocabulary problem, it is a reference-resolution problem, and I do not
currently have a test that distinguishes a working resolver from a broken one
beyond the five hand-built cases.** By failure 16 that means it is not ready,
and by the rule above it means the next step is more corpus, not more fixtures.

---

## Two piles, not one: waiting on effort, waiting on an idea

**Adopted 10 September 2026.** Every entry in this document was deferred, and they were not
deferred for the same reason. Sorting them into one pile makes the second kind
invisible.

> **A defect deferred for cost waits on effort. A defect deferred for want of a
> test waits on an idea.**

The difference is operational, not philosophical. The first pile is scheduling:
pick it up when there is time, and it will be there. The second is not — no
amount of time moves it, because the missing thing is a way to tell a working
implementation from a broken one, and by failure 16 a protective construct whose
triggering condition cannot be specified is not a protection.

**When this pile is next re-read**, every entry gets one of the two labels, and
the re-read is the moment to apply failure 18 as well: a defect deferred whole is
often three defects, and one of them is usually cheap. The two exercises belong
together — decompose first, then sort the parts.

Current examples of the second kind, stated so they are not mistaken for
scheduling: automated contradiction detection, and automated assessment of
whether a passage leaves a false impression. Neither is expensive. Neither has a
test.

---

## The epistemic check, retargeted: 1 of 89 sentences evaluated

**10 September 2026, superseding the entry above it.** The check's job changed from
adjudication to triage, and the number that matters changed with it.

| issue | epistemic sentences | PASS | FAIL | NOT EVALUATED | coverage |
|---|---|---|---|---|---|
| cdk46 | 20 | 0 | 0 | 20 | **0%** |
| deskilling | 17 | 0 | 0 | 17 | **0%** |
| melanoma | 52 | 0 | 1 | 51 | **2%** |

**1 of 89, and the one FAIL is the known false positive** cross-referenced to the
fingerprint hazard above. Nothing on any page has been established as either
sound or stale.

**Three outcomes, never two.** A check that cannot determine a sentence's subject
reports NOT EVALUATED and never PASS. Silence about what was not examined is the
difference between a coverage number and a false assurance — and the first
version of this file produced exactly that false assurance, four false positives
read as "the corpus is clean".

**What the coverage is gated on**, in order of how much each would move it:

1. **`document_class`** is set on 4 sources of 99. A source without it is NOT
   EVALUATED rather than assumed to be a document, which is correct and is why
   deskilling reads 0% with 41 of 44 sources aliased.
2. **Aliases**: 81 of 99 sources carry them; 18 cannot be named at all.
3. **Bindings**: 7 of 228 cdk46 rows carry a locator naming a source, so
   binding-based subject resolution almost never fires and the string half
   usually decides alone — which is what it was doing when it got three of four
   wrong.

None of those is a defect in the check. **They are the store's own coverage, made
visible by something that finally asked.** The 88 NOT EVALUATED sentences are the
passage-reading stage's worklist (§5.5), which is what the check is now for.

---

## "7 of 228" was a statement about locators, and the answer underneath it

**10 September 2026. Answered as a schema fact, because the summary I gave was misleading.**

### What a binding row records

Of cdk46's 228 rows, 169 are currently on the page. Non-empty counts on those 169:

| field | on-page rows | what it is |
|---|---|---|
| `sentence`, `sentence_sha`, `why_empirical`, `verdicts` | 169 | every row |
| `source_id` | **34** | **the source, as a resolvable id** |
| `document_sha` | 27 | the content hash of the held document |
| `span` | 27 | the bytes the sentence rests on |
| `why_bound` | 22 | prose |
| `locator` | **7** | prose naming where in the document |
| `bucket` | 7 | deterministic / context / judgement / figure |

**The source IS recoverable by a dedicated field.** `source_id` is that field.
`quotations.py` reads it directly (`r.get("source_id")`), and `spancheck.py` is a
pure function over (sentence, span, document bytes) with the caller supplying the
document. So the span checks identify documents exactly the way the epistemic
check should.

**"7 of 228" described `locator` only** and I reported it as if it characterised
the row. That is the third time in two days I have reported a narrow field's
count as a fact about the whole — after 163/132 and "the five are unenumerated",
both from reading a truncated line instead of the object. Same family, third
instance, and this one reached a directive.

### The answer underneath, which is not benign and is not hidden

`bindings.rule_rows("cdk46")` today:

```
rule 1 — written from a document we hold      BLOCKED  135 of 169 rest on nothing
rule 2 — every sentence declares its kind     BLOCKED  162 undeclared
sentences still to revalidate                 warn     162 of 169
```

So the claim *"every sentence is bound to a verifiable span or declared as a
judgement"* is **not** mechanically untraceable — it is mechanically **refuted**,
loudly, by the repository's own gate, and that is why this issue cannot publish.

**It is a backlog, not a regression**, and the row says so: rule 1 was *"adopted
2026-09-02 with no exemption for what was already written"*, five days after
cdk46 published. The 162 are the sentences the rule reaches back over. Nothing is
concealed; the gate has been printing it since 2 September.

### Why binding resolution still cannot help the epistemic check

Not the schema. **The sentences making epistemic claims are among the unbound
162.** Of the 14 epistemic sentences on the cdk46 page: 9 are inside the binder's
scope, 5 are in the change log, which the binder correctly strips — and of the
9 in scope, **1** is recorded in `bindings.json`.

The two systems are not disjoint by design; they are disjoint because the sentences
that say what we know about a source are mostly in source notes and are mostly
part of the revalidation backlog.

---

## The cdk46 metadata backfill: it moved coverage from 0% to 5%, and that is the finding

**10 September 2026.** cdk46's 26 sources now all declare `document_class`, and 23 of 26
carry aliases (up from 11). The backfill was self-testing by design: coverage
should move off 0%, and if it barely moved, **the metadata was not the binding
constraint.**

It barely moved. **1 of 20**, up from 0 of 20.

So the constraint is subject resolution, and the metadata work — which was the
obvious thing to do and would have felt like progress — bought one sentence. Had
this been run across all 99 sources first, as the tidier instinct wanted, the
same conclusion would have cost four times as much and arrived no sooner.

**Policy, recorded as a decision rather than an omission:** melanoma's and
deskilling's sources are filled **when those issues are next opened**, not now.
The judgement *"is this a document or a record about one"* goes wrong in bulk
when it is made to clear a number.

**And one classification was corrected rather than kept.** S021 (the PALMARES-2
registry record) was marked `record_about` on 9 September to suppress a false
positive. That was reasoning from the symptom: it **is** the registry entry, and
claims about the registry entry rest on it. It is now `document`, the false
positive is back, and it is recorded as what it always was — a subject-resolution
defect, in which a sentence about the *paper* resolves to the *registry record*
because both are called PALMARES-2.

---

## cdk46 was published before rule 1 existed and was never migrated to it

**10 September 2026. The precise statement, because the loose one will otherwise be the one
remembered.**

Rule 1 was **adopted 2 September 2026 with no exemption for what was already
written.** cdk46 published **28–31 August**. Melanoma, written under the rule,
passes rules 1 and 2 on **all 131** of its sentences. So this is **a backlog in
one issue, not a defect in the apparatus** — and the apparatus has been reporting
it correctly, in the gate, since the day the rule was adopted.

**Eight days unread.** Same class as the pre-push guard's cdk46 warning and the
four-day lock: a signal that fired correctly, in the right place, and was not
read. Third instance of that class; it is now four with this one.

### The record's-reach principle does NOT transfer here, and the difference matters

This morning it was established that **a record has a start date, and events
before it are outside its reach** — which is why no 26 August row was backfilled
into `published.json`.

**That argument does not apply to a standard, and reaching for it here would be
motivated.** A record documents the past; **a standard describes a live
artifact.** cdk46 is on the web right now, and a reader today reads it under
whatever this publication claims today. When the rule was adopted has no bearing
on whether a page currently meets it.

Written down because the two cases look alike — both are "the rule is newer than
the thing" — and only one of them is an argument.

---

## The 135 is not the number. Measured, it is three numbers.

**10 September 2026, before proposing any plan, because an estimate of size is not a
measurement of size.**

`page_sentences("cdk46")` returns **487** body sentences. `rule_rows` computes
its verdict over the **169** that have a binding row. **317 have no row at all.**

Triaged — heuristically, and the method is stated below because the
EMPIRICAL/JUDGEMENT boundary is a judgement call:

| class | all 487 | with a binding row | **with no row at all** |
|---|---|---|---|
| EMPIRICAL — carries a figure, quotation, named trial, registry id | 308 | 168 | **140** |
| JUDGEMENT — interpretive, no figure | 125 | 0 | **125** |
| FURNITURE — headings, transitions, asserts nothing | 54 | 2 | **52** |

**The hypothesis that most of the 135 are undeclared judgements is wrong.**
Judgements have no rows at all, so they are not among the 135. The 135 are bound
rows whose binding rests on nothing — a subset of the 168 rowed empirical
sentences.

So the work is three piles, not one:

1. **135** — rowed, empirical, resting on nothing. Rule 1 reports these.
2. **140** — empirical, **no row at all.** Rule 1 does not see these.
3. **125** — judgements needing premises and a step. Rule 2's concern; also unrowed.

### And a scope claim that the body does not perform

`bindings.rule_rows()` opens: *"The two rules, as blocking rows. **Every sentence
on the page, no exemptions.**"* Its body reads
`{k: v for k, v in rows.items() if v.get("on_page")}` — the rows in
`bindings.json`. `scan()` creates a row only where an anchor is detectable
(`if not must: continue`), so **a sentence with no figure, quotation or named
source never enters, and is never examined by either rule.**

That is **failure 15 in the file that defines rule 1**: a check that examines part
of what its name describes, reporting the unexamined part as nothing at all
rather than as passing — which is better than a false pass and is still not what
the docstring says.

**Method, stated so the numbers can be discounted appropriately.** The triage is
a regex heuristic over the sentence text: a figure, quotation marker, named trial
or registry identifier makes it EMPIRICAL; six words or fewer with no digit makes
it FURNITURE; the rest are JUDGEMENT. It is not an adjudication and the
EMPIRICAL/JUDGEMENT line in particular will be wrong in individual cases. It is
offered as **the composition of the problem**, which is what was asked for, and
not as a work list.

---

## Where the binding claim is made, verbatim — and it is scoped

**10 September 2026. Answered from the bytes, not paraphrased.**

**No unscoped, site-wide claim about sentence binding exists.** Every site-wide
claim is about **figures**:

| where | exact wording | scope |
|---|---|---|
| `index.html` | *"Every figure is verified against a company release, a regulatory filing or a peer-reviewed paper."* | site-wide, **figures** |
| `what-this-is.html` | *"One verifies every figure against its primary source."* | site-wide, **figures**, describing the pre-publication checks |
| `cdk46.html` | *"Every figure is the trial publication's own and every cell names the analysis it comes from."* / *"Every figure above traces to a named source."* | this issue, **figures** |
| `email/issue1-melanoma.html` | *"Every sentence in the assessment names the words in that document which support it."* | **the melanoma assessment** |
| `melanoma.html` | *"Publishing the corrections above meant binding every sentence on this page to the words it rests on."* | **this page**, past tense |

**The sentence-level claim is made twice and both times about melanoma**, which
passes on all 131. **It is never made about cdk46 and never made site-wide.**

And cdk46's figure claim is supported by a green gate row: *"no sentence carrying
a figure rests only on coverage — every number on the page reaches a release, a
paper or a registry record."*

**So there is no live false claim, and this is not urgent in the way it might
have been.** The site's claim stands. What follows from the ruling is that
**cdk46 needs its own disclosure** once the composition above is settled — scoped
so it is true, because *"135 of this issue's sentences rest on nothing"* would be
inaccurate in the harsh direction when 140 more were never examined and 125 are
judgements.

---

## "All 131 sentences" meant all 131 of the 131 that had rows

**10 September 2026. Reported, not concluded from.**

| issue | body sentences (`page_sentences`) | examined by rules 1 and 2 | **not examined** |
|---|---|---|---|
| melanoma | **343** | **131** | **212** |
| cdk46 | 487 | 169 | 317 |
| deskilling | 426 | 112 | 314 |

**131 is the rowed population, not the page-sentence count.** Melanoma's rule 1
row reads, verbatim:

> `rule 1 — written from a document we hold   ok   all 131 sentence(s) name the
> words they rest on, and every figure they carry is in one of those spans`

and the function producing it opened with *"Every sentence on the page, no
exemptions."* Melanoma published on 9 September on the strength of that pair.

Those are the numbers. **What follows from them is the operator's, and this entry
does not take it** — the last several times a conclusion was drawn from a summary
rather than from the object, it was wrong, and this is a summary.

### What was fixed today regardless

**The scope claim.** `rule_rows`' docstring now says what the function examines,
carries the three counts above, and names the defect: failure 15, in the file
that defines rule 1, and simultaneously the unread-signature failure — a control
described in words that nothing performs.

**The third outcome.** `bindings.not_examined(slug)` is the difference between
the page and the rowed population, and `rule_rows` now emits a row for it:

> `sentences neither rule examined   warn   212 of 343 body sentence(s) … The
> rows above are computed over the other 131. Not examined is not passed.`

**WARN and not BLOCKED, deliberately.** An unexamined sentence is not a failing
sentence, and reporting it as one would push somebody to delete prose to clear a
number — which is failure 20 waiting to happen in the other direction.

**And the row cannot vanish.** Its first version called `page_sentences()`, which
raises for a slug with no page, and that took the rules suite from 89 passing to
61. Now a failure to count reports *"could not be counted … Unknown, not zero"*
— because omitting the row on error would reintroduce exactly the absence the row
exists to remove. Third time this week a new call has broken on the synthetic
test slug; the pattern is that a function reaching for the real page is added to
a module the tests exercise without one.

**Appendix D** carries the examined/not-examined pair beside the epistemic
coverage, in the packet rather than on the page.

### Why the number is large, and why that is not the same as bad

A binding row is created only where `scan()` detects an anchor — a figure, a
quotation, a named trial, a registry identifier, a DOI. That is a **reasonable
way to find sentences worth binding** and a **bad way to define the population of
a rule that claims to cover the page.** The two uses were never separated, and
the docstring described the second while the code did the first.

---

## Rule 13 rested on a list nothing produced. It is derived now.

**10 September 2026. `backend/scripts/whatholdsup/open_list.py`.**

Rule 13 makes an acceptance require two things the operator can genuinely
supply: **knowing what remains open**, and choosing to publish anyway. **Nothing
in this apparatus produced or checked the first.** It was assembled by hand, from
memory, by whoever wrote the acceptance block.

### What the difference is, measured

On 9 September the hand-written list said **one thing**: the S029 erratum. Run
against the same page today, the derived list returns **seven checks not
returning ok**, plus coverage and the waive:

| what the derived list carries | on the 9 September list? |
|---|---|
| S029 erratum, BLOCKED, not read | **yes** — the only item |
| 212 of 343 body sentences not examined by rules 1 or 2 | no |
| 2 correction lookups failed — S007, S030 — *"NOT known to be clean"* | no |
| 15 sources with no resolvable identifier, so no automatic check is possible | no |
| 10 held documents never round-tripped by the canary | no |
| 5 documents checked only against a length floor, *"a weaker thing"* | no |
| 2 of 131 sentences resting on a human attestation no check may read | no |
| 1 of 52 epistemic sentences evaluated | no |

**Six of the eight were invisible to the person signing.** Not concealed —
several were printing in gate output at the time — but nobody was assembling
them, because assembling them was somebody's memory and memory is what the whole
week has been about.

**The first of rule 13's two requirements was not supplied — not by the operator,
to him.** That is a fact about the list, not about the decision.

### The generalisation, which is why this is an entry and not a task

Every failure this week has been a hand-maintained representation drifting from
the thing it represents: the index dates, the family instance count, the
correction log's access state, the four-commit figure, the locator count, and
"all 131 sentences". **The open list is one of those, and it is the one a
publication decision rests on.**

### Why it does not rank, which is the governing reason

**It does not decide which items are fatal, and that is the design rather than an
omission.** Rule 13's two requirements are knowing what is open and choosing to
publish anyway. **A list that pre-decides which items are fatal supplies the
first and quietly removes the second** — the operator is left agreeing with a
verdict rather than making a decision, which is precisely the objection that
produced the current rule 13 when he refused to sign a block that made his
signature ceremonial.

### Information available is not information delivered

Six of the eight items were invisible to the signer on 9 September. **Not
concealed** — several were printing in gate output at the time. Nobody was
assembling them. Rule 13 needs the second thing, and until today nothing supplied
it.

### The two sentences whose support is a person's word

The list names them rather than summarising them, because *"2 of 131 rest on a
human attestation"* is an assurance and the sentences are a fact:

1. *"Data support scores 1 — the rubric's anchor for 1 is purely qualitative
   assertion with no numeric support, which is what a statement that two
   endpoints were met, with no figure for either, is."* — attested by Claude
   (Opus 5), against this publication's own rubric, read 3 September 2026.
2. *"Readers saw 3.4, which was the correct total of the working printed beneath
   it — but that working weighted two of the six dimensions differently from the
   rubric, which puts the same six scores at 3.35."* — attested against the
   repository's git history and the live page, read 3 September 2026, re-verified
   8 September against commit 2c71b8e.

**Naming which two is better than any assurance about them.** A reader of the
acceptance can go and disagree with a sentence; they cannot disagree with a
count.

### What it deliberately does not do

It does not decide whether any item should block. Collapsing *"here is what is
open"* into *"here is what stops you"* would take rule 13's **second**
requirement away from the operator as well, and the point of the rule is that
both are his.

### And the acceptance mechanism has now found two defects in itself

Twice exercised, twice a defect surfaced: the first time the operator refused to
sign a block that made his signature ceremonial, which produced the current rule
13; the second time the rule's own first requirement turned out to be
unsatisfiable. **That is the mechanism working**, and it is recorded that way
rather than as two embarrassments — a control that has never objected to anything
has not been tested.

---

## A third kind of figure, with no category: measurements of our own apparatus

**Named 10 September 2026. Nothing built — a category is not added mid-round.**

The binding scheme has two kinds of figure. A figure is **taken from a source**,
and a span in a held document supports it. Or it is **worked out by the page**,
and `furniture.py`'s `computed` mark re-derives it from the numbers printed
beside it.

**131, 343 and 212 are neither.** They are measurements of this repository's own
machinery — how many sentences the binder can see, how many have a row, how many
neither rule examined. There is no held document because **there is nothing to
hold**: the fact did not exist until a function was run, and the function is in
this repository.

### What happened to them, which is the finding

They were **declared as exclusions.** `figure-exclusions.json` says of itself
that an exclusion means *"this figure is not taken from a source"*, never *"do
not check this figure"* — and that is exactly right for the page's own
arithmetic, which the `computed` mark still verifies. It is not right for these.
Nothing verifies them. The declaration is the only thing standing behind them.

**This is what happens to a thing with no category: it is suppressed rather than
classified.** The exclusion file was the nearest available hole and they went
into it, and the record now says "not from a source" where the true statement is
"derived by us, from us, at a moment in time, by a named function".

### The class is already larger than three, and growing

- the rules coverage pair — **131 examined, 212 not**
- the corpus figure — **412 of 1,256 across three issues**
- the epistemic coverage — **1 of 52**
- the alias and `document_class` counts — **23 of 26**, **26 of 26**
- anything Appendix D reports about where the machinery has not looked

**Every one of these is a self-measurement, and self-measurements are exactly
what this publication has spent the week getting wrong.** The 2,116-character
paragraph was one. "All 131 sentences" was one. "7 of 228" was one. They are the
figures with no external document to check them against, which is precisely why
they need a category with a falsifier attached rather than an exemption.

### What the category would need, when it is built

A figure of this kind should carry **the function that produces it** and be
**re-derived at check time**, not declared once. That is `computed`'s discipline
pointed at the apparatus instead of at the page — the mark that says *"here is
the working, re-do it"*, where the working is a call rather than a multiplication.

The interim exclusion for 131/343/212 already carries a falsifier of that shape:
*if `rule_rows` stops reporting 131, or `not_examined` stops returning 212, or
`page_sentences` stops returning 343, the sentence must be re-derived.* **It is
the right test written in the wrong place** — prose in a file nothing executes,
where it should be a call in a file that runs every gate.

---

## changecheck cannot read the change log, which is where corrections are

**10 September 2026. Found while running it, as directed, on the melanoma republication.**

`changecheck` reads `ledger.body_only(html)`. That strips
`<footer id="updates">` — the reader-facing change log. On the melanoma
republication:

| | changed sentences |
|---|---|
| `publish.changes_since` (whole page) | **8** |
| `changecheck` scope (`body_only`) | **1** |

The seven it did not see are **the entire correction** — the sentence claiming
every sentence on the page was bound, and its replacement. `changecheck`
reported *"1 changed sentence(s) reviewed against the page, nothing found"*, and
the `changed sentences reviewed` row went green.

**The row is true and the impression is false**, which is failure 15 again: the
check examined what it examines and said so, and the sentence it produced reads
as though the page's changes had been read.

**And the class of text it cannot reach is the worst possible one.** The change
log is where this publication records having been wrong. It is the region where
new prose is most likely to be written under time pressure, by the person who
made the error, describing their own mistake — and it is invisible to the only
check that reads new text for meaning. `corrections_check` (B18) reads the log
for figures and false-disagreement claims; nothing reads it for sense.

**Not fixed today.** Widening `changecheck`'s scope changes what every future run
costs and what it reports, and doing that inside a publish sequence is how the
next defect enters. It is the first thing on the next issue's list, and the fix
is one call — `body_only` to whole-page — plus a re-baseline of what "nothing
found" has historically meant.

---

## The venv fallback that silently substituted a different interpreter

**10 September 2026.** Every command this session ran as
`V=.venv/bin/python3; [ -x "$V" ] || V=python3`. **There is no `.venv` in this
repository.** The project venv is `backend/venv`. So the fallback fired on every
single invocation and everything ran on the system interpreter.

It went unnoticed because it did not matter — the whatholdsup modules are
stdlib-only — until `changecheck` needed `anthropic`, which is installed in
`backend/venv` and not system-wide, and the run died on `ModuleNotFoundError`.

**The shape:** a fallback that substitutes a different thing and reports nothing.
It is the same object as a guard that catches nothing and a row that vanishes on
error — *the working case and the degraded case are indistinguishable from
outside*. A fallback that cannot say it fired is a silent substitution, and the
right form is either to fail loudly or to print which interpreter it chose.

---

## The passage stage's first application, and what it found

**10 September 2026. Run on the corrected melanoma change-log entry, before publishing.**

It was applied to **the passage it was designed for**: text no sentence-scoped
check can read — `changecheck` strips the change log — written under time
pressure, by the party that made the error, about their own mistake. That is the
worst-case input for every other control in this repository, and it is where a
publication records having been wrong.

**Q1 — do any two sentences contradict each other?** No. The plain-language gloss
("a figure, a quotation or a named source") and the exact list ("a figure, a
quotation, a named trial, a registry identifier") differ in wording and agree in
substance. "Not examined is not the same as unsupported" and "we did not know
which it was, and we said that we did" are consistent: the first is about the 212,
the second about our claim.

**Q2 — does any sentence assert a state the store contradicts? YES. This is why
the publish stopped.**

The passage says *"binding the sentences on this page that carry a figure, a
quotation or a named source **to the words they rest on** — 131 of this page's
343 sentences."*

The store says **95**. `bindings.preflight_rows` reports: *"95 of 131 empirical
sentence(s) are bound to a span; 36 rest on nothing this system can name."* Of
the 36, 34 are judgements — which satisfy rule 1 through their premises rather
than a span, legitimately — and **2 are `figure`-bucket sentences that are not
judgements and have no span at all.**

So the correction, whose entire subject is that we overstated our binding
coverage, **overstates our binding coverage.** By a smaller factor and in the
same direction.

**Q3 — could a careful reader leave believing something false that no sentence
states?** Yes, and it is the same fact from the reader's side: told "we said
*every* and it was 131", a reader takes 131 as the solid number. It has a further
split the passage does not mention.
*At whole-page scope*: the corrected entry now carries the page's only coverage
caveat, while the source notes and the homepage make unqualified "every figure"
claims. Those are figure claims and the figure check is green, so no false
impression is created — but the corrected entry is doing more work than it says.

**Q4 — is a reader asked to hold anything in suspension longer than the passage
supports?** Borderline, and worth recording rather than acting on. The paragraph
runs 1,814 characters and now contains a correction about coverage followed by
five unrelated findings. The correction was inserted into a paragraph written for
another purpose. That is the KOL Pulse shape at lower severity; it is a structural
note for the next revision, not a blocker.

### What this establishes about the stage

**A detector would have passed this passage.** Every figure in it is correct
against something: 131 is `rule_rows`' count, 343 is `page_sentences`', 212 is
`not_examined()`'s. `corrections_check` passes. `changecheck` cannot see it.
Rule 1 says ok.

**What fails is the join between a true number and the words around it** — "131
sentences bound to the words they rest on" versus "131 sentences that satisfy
rule 1, of which 95 carry a span". No sentence-scoped check compares those,
because the defect is not in a sentence; it is between a sentence and a fact
about the apparatus that produced it.

### Consequences, unresolved and going back to the operator

1. **The passage needs a further correction**, and it is the third statement this
   entry will have made about its own coverage. That needs a ruling, not an edit.
2. **`empirical sentences bound` calls 34 judgements "resting on nothing this
   system can name"** while rule 1 correctly counts their premises. Two rows,
   one file, opposite characterisations of the same 34 sentences. Which is right
   depends on what "bound" is claimed to mean, and the page inherited the loose
   reading.
3. **The 2 `figure`-bucket sentences with no span** are neither judgements nor
   bound. They need looking at on their own.

---

## Why changecheck's scope is not being widened today

**10 September 2026.** It stays on the next issue's list, unwidened, and the reason is
worth stating so it does not read as an omission.

Changing a check's scope means re-baselining what every past "nothing found"
meant. Doing that **at the moment of publish, inside the sequence that check
guards**, is the failure-16 shape: a protective construct altered while it is
load-bearing, with no opportunity to establish that the new version fires and the
old one's history still means something.

And what would be held hostage to it is **the repair of a claim currently false on
the live page**. A widened check that has never been made to fire is not worth a
day of a false claim standing.

---

## What the venv fallback means for this session's numbers

**10 September 2026. Stated plainly rather than left as a footnote.**

Every command in this session — including every run of the test suite — used
`V=.venv/bin/python3; [ -x "$V" ] || V=python3`. **There is no `.venv` in this
repository.** The project venv is `backend/venv`. The fallback fired on every
single invocation and announced nothing.

**So "89 tests passing" is a result from an environment that was substituted
without notice.** It happens to be fine — the whatholdsup modules are
stdlib-only, and re-running the suite on `backend/venv` gives the same 89. But
that was **verified after the fact, not before**, and for the length of this
session a number that looked settled was produced by a path nobody had checked.

Filed with the guard that caught nothing and the row that vanished on error:
**the working case and the degraded case are indistinguishable from outside.**

### Fixed

`jsonio.announce_interpreter()` prints to stderr when the running interpreter is
not the project venv, and `publish.py` now records `sys.executable` in every row
it stores, so a stored result carries the environment that produced it.

**The first version of that function was wrong, and wrong in the family it was
written to catch.** It compared `Path(sys.executable).resolve()` against the
venv's `bin/python3` — but a venv's `python3` is a **symlink to the base
interpreter**, so resolving both makes them equal and the check returned "this is
the project venv" for every interpreter on the machine. It was written to catch a
silent substitution and, for an hour, silently passed one. It compares
`sys.prefix` now, which is what actually differs between environments, and it was
made to fire on the system interpreter and stay quiet on the venv before being
trusted.

---

## There is no hole in rule 1. There is a third route, and I did not report it.

**10 September 2026. Correcting my own finding of an hour earlier.**

I reported that two `figure`-bucket sentences *"are neither judgements nor bound
and have no span at all"*, and left the implication that rule 1 passes sentences
satisfying neither route. **That implication was wrong. Rule 1 has three routes,
not two, and the third is deliberate, documented, costed and separately
reported.**

### The mechanism, from the code

```python
attested = [k for k, v in on_page.items()
            if (v.get("bucket") or "") == "figure"
            and (v.get("attested_by") or "").strip()
            and (v.get("attested_in") or "").strip()
            and (v.get("locator") or "").strip()]
unbound  = [k for k, v in on_page.items()
            if not covering(v) and k not in set(attested)]
```

A row passes rule 1 by **one of three** routes:

| route | test | melanoma |
|---|---|---|
| **BOUND** | its own `span` (or an `also_rests_on` span) is present in a held document | **95** |
| **DECLARED** | `bucket == "judgement"`, and its `premises` carry spans | **34** |
| **ATTESTED** | `bucket == "figure"`, with a named person, the record of their reading, and a locator | **2** |
| | **unbound — fails rule 1** | **0** |

Measured: `covering()` is empty for exactly 2 rows, both attested. **`unbound` is
0.** Nothing passes by satisfying nothing.

### Why the third route exists, in the file's own words

> *"NCCN's licence forbids putting the guideline through any automated tool, so no
> check has read it or ever may… A rule 1 that demanded a span from those
> sentences would make the attested route useless and push us toward pasting
> licence-bound text into a file to satisfy a check — the worst outcome
> available."*

And it is **not** merged into the verified counts:

> *"The count is reported SEPARATELY below and never added to the verified ones,
> because 'a human says this is in a document nothing may read' and 'this string
> is in these bytes' are different claims and merging them is the oldest error in
> this repository."*

That separate row is the one already in the acceptance block: *"2 of 131 rest on
a document no check may read."* **It was in front of me, in the open list I
generated, while I wrote that they were unaccounted for.**

The two are named in the acceptance block: the rubric's data-support anchor,
attested against `score_claims.py`; and the 3.4/3.35 working, attested against git
history and the deployed page.

### What I got wrong, and how

I derived "neither judgements nor bound" from **bucket and span alone** and did
not read the pass logic. The categories I had were the two I already knew about,
and a thing that fits neither reads as unaccounted for rather than as a third
category. **That is the same move as the third kind of figure recorded above** —
where a self-measurement with no category was suppressed into an exclusion file
rather than classified.

**The corrected finding is smaller and different.** The passage's *"131 sentences
bound to the words they rest on"* is still wrong, because 95 are bound. But the
other 36 are not unaccounted for: 34 are declared and 2 are attested. **The defect
is a word doing three jobs, not a hole.**

---

## Every comparison that normalises before comparing — the survey

**10 September 2026. Reported; nothing fixed beyond `announce_interpreter`, as ruled.**

The question asked of each site: **does the property being tested survive the
normalisation?**

### Orthogonal — normalisation removes something the question does not depend on

The large majority. `spancheck._norm` normalises whitespace, dash characters and
**decimal separators** — it exists because *The Lancet* prints `0·561` with a
middle dot, and three figures were reported absent from a document that held them
all day. Every span-presence check runs `_norm(span).lower() in _norm(doc).lower()`.
The question is *"is this text in this document"*; typography is not the
difference being sought. Same for `b13`, `deletions`, `negatives`, `quotations`,
`changecheck`, `reconcile:160`, `modelbind`, `findings`, `canary`.

### Same-axis — the normalisation can erase the thing being tested

| site | what it normalises | the risk |
|---|---|---|
| `jsonio.announce_interpreter` **(FIXED)** | `Path.resolve()` on interpreter paths | **realised.** A venv `python3` is a symlink to the base interpreter, so resolving both made every interpreter look like the project venv |
| `reconcile.py:107` | `u.rstrip("/").lower()` on **page URLs** | URL **paths are case-sensitive**. Two distinct links differing only in case would be treated as the same known URL, and one would be silently accepted as accounted-for |
| `sweep_sources.py:222` | `slug.lower() in d.name.lower()` — **substring** | a slug that is a prefix or substring of another issue's directory name resolves to the wrong issue. Harmless with three issues named `cdk46`, `melanoma`, `deskilling`; a future `melanoma-2` would match `melanoma`'s directory first |
| `source_store.py:889/903` | `k.lower() in _searchable(data).lower()` | identity of a held document by substring match; two identifiers differing only in case merge |

### The opposite failure, in the same week

`b13`'s staleness arm normalises **too little**. `_norm` collapses whitespace runs
but does not remove a space before a full stop, so `"343 sentences."` and
`"343 sentences ."` differ after normalisation — and a hand-written figure
exclusion was reported as stale against the page it correctly described.

**Normalising too little reports a false difference. Normalising along the
question's own axis reports a false sameness.** The second is worse: a false
difference is a red check somebody investigates; a false sameness is a green one
nobody does.

**None of the three unrealised risks is fixed today**, per the ruling. They are
listed so the next person changing any comparison in this apparatus has the
question in front of them: *does the property I am testing survive this
normalisation?*

---

## The passage stage, second run on the same passage: Q3 again, on the denominator

**10 September 2026. The rewrite fixed the numerator and left the denominator undeclared.**

**Q1 — contradiction? Clean.** 95 + 34 + 2 = 131; 131 + 212 = 343. The
*"no exemptions"* quotation is past tense and the phrase is still findable in
`bindings.py`, in the corrected docstring's own history note.

**Q2 — asserted state against the store? Clean, all six figures verified
individually:**

| the page says | the store says |
|---|---|
| 343 sentences | `page_sentences` → **343** |
| examined 131 | `rule_rows` population → **131** |
| 95 point at a span | rows with a span → **95** |
| 34 judgements on premises | → **34** |
| 2 attested | → **2** |
| 212 not examined | `not_examined()` → **212** |

**Q3 — false impression no sentence states? NOT CLEAN.**

> *"This page has 343 sentences."*

**The page does not have 343 sentences.** 343 is `page_sentences` — the body
*after* the head, the navigation and the change log are stripped. The change log
alone carries **267** more. The whole document is **656**.

Nothing in the passage says what 343 excludes, and a reader who counted would get
a different number. **The reader is standing in the change log while reading it** —
the one region the denominator leaves out.

**And the direction is the familiar one.** 131 of 343 is **38%**. Counting the
change log the same way gives 131 of 610, or **21%**. The undeclared denominator
makes our coverage look nearly twice as good.

**This is the third time the same paragraph has understated the same thing** —
*"every sentence"*, then *"131 of 343 bound"*, now an unstated denominator — and
each correction fixed the error one level down while leaving a new one at the
level below. That is §12g's regress, and §12g's own test catches it: **the
sentence still contains a single number where the truth has a shape.** 343 is a
scope decision presented as a count.

**Q4 — suspension? Borderline, as before.** 1,966 characters; the correction now
runs six sentences before the paragraph's original content resumes. Structural
note for the next revision, agreed, not a blocker.

**Stopped. Not fixed, not proceeded.** The fix is not obvious — whether the change
log should count toward binding coverage at all is a real question, and answering
it inside a publish sequence is how the fourth version of this sentence gets
written.
