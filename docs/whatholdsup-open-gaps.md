# Open gaps — checks we know we need and have not written

A gap recorded here is not a gap that is being worked on. It is one we found,
decided not to fix in the moment because fixing a control while adjudicating is
how this project's errors have been made, and did not want to lose.

Each entry names the error that revealed it, so that a later reader can judge
whether the gap is still real.

---

## GAP-001 — nothing checks a universal negative against our own library

**Raised by** the outside review of 2026-09-03, finding OR-1.
**Fix when** issue one is published. Before issue two's revalidation, because
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
checked. The registry pair is the clearest: the row's premises already carry
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
