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
