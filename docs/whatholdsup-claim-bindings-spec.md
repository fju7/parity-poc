# Claim bindings — a specification

Status: proposed, 1 September 2026. Written after the first day on which every
document behind an issue was read against the page it supports.

Reviewed and agreed by the operator, 1 September 2026, with four amendments
incorporated here: three questions rather than three buckets; context handled by
mechanism rather than by classification; tables and figures separated; and the
errata check promoted to the first thing built.

---

## 0. Two governing rules

Everything below is subordinate to these. They are first because both were
learned the hard way on the day this was written.

**R1. The binding layer may assert only the presence or absence of a span. It may
never assert that a sentence is true.**

On 1 September two checks asserted more than their premises supported and both
nearly forced edits to correct sentences. `substance()`, built to tell a paper
from a page about a paper, was run over drug labels and registry postings and
called them landing pages — a 221,525-character results posting among them.
`inaccessibility_claims`, built to catch a page claiming it could not open a
source the ledger said was read, was run against `abstract_held` and blocked the
publish over three true sentences. Both answered confidently outside the domain
they were built for, and an answer given out of turn looks exactly like an answer
given in turn.

So this layer reports what it can observe and hands the resolution to a person. A
block is a question. A verdict about truth is not this layer's to give.

**R2. Every sentence answers all three questions in section 3. A bucket
selects WHO SIGNS each answer; it never excuses a sentence from being asked.**

---

## 1. What is wrong now

Every control this project owns is about a DOCUMENT. Is it held. What kind is it.
Was it read. Does the ledger overstate what was read. Not one control is about a
SENTENCE.

Nothing anywhere records: *this sentence rests on this source, at this locator,
supported by these exact words.*

Four consequences follow, and they are the four things that keep going wrong.

**Verification cannot be complete.** Nothing enumerates what must be checked, so
what gets checked is what somebody thought of.

**It cannot be deterministic.** There is no span to match against, so the question
"is this supported" has to be put to a model, which returns prose about the
source. Corrections then get written from that prose. Twice this week a correction
written from a finding rather than from a source was itself wrong, once deleting a
true statement.

**It cannot be cheap**, so it is rationed, so it is partial.

**It cannot carry forward.** Every gate run re-judges everything, and nothing
re-checks a correction. 35% of the errors recorded in the taxonomy were introduced
by earlier corrections. Nothing in the system could have caught that class at all.

And because each control was written AFTER an incident, in the shape of that
incident, each catches its own ghost and nothing adjacent. `substance()` was
written after a landing page was stored as full text; within hours it called four
ClinicalTrials.gov results postings and three drug labels "pages about documents".
`inaccessibility_claims` was written after PALMARES-2; the next day it blocked a
publish over three sentences that were true. A check derived from an incident
inherits the incident's scope and nothing else.

## 2. The object

    Binding
      claim_id            stable id
      sentence            the exact published sentence
      sentence_sha        fingerprint, so a change is detectable
      source_id           the source it rests on
      document_sha        the exact bytes, from the library
      locator_type        prose | table | field | figure | none
      locator             section heading, table id, JSON path, figure number
      span                the exact characters in the document that support it
      envelope            span plus its surrounding context and section heading
      scope_words         quantifiers and hedges in the sentence, each mapped
                          to a token in the span, or flagged unmapped
      verdicts            locatable / faithful / warranted, each with who and when
      bucket              observed, not chosen — see section 4
      rests_on_store      for a sentence about OUR holdings only: the source ids
                          whose store record it describes — see §4a, B21
      grade_departure     a person's written reason for stating more confidence
                          than any grade the evidence states — see §4a, B20

A sentence carrying a figure, a trial name, a registry id, a proper noun or a
quotation and having NO binding row is a defect that blocks publication. That one
rule would have caught the *Cancers* 2023 study, which sat on the published page
with eight figures, its own entry in the visible source list, and no entry in the
ledger — invisible to every control we have.

## 3. Three questions, not three buckets

The operator proposed classifying each sentence as deterministic,
context-dependent/table-based, or judgement, and applying the process that fits
its bucket. The instinct is right: **the verification method must be selected by
the claim's type, and the type must be declared, so that an unclassified sentence
is a defect.** That is the move that turns "we check what occurs to us" into a
process.

But one bucket per sentence routes the sentence to one test and thereby EXCUSES it
from the others, and that is the exact shape of every failure recorded this week —
a check applied where its premise holds, and nothing asking the other question.

Two examples from today. "Grade 3 diarrhoea in 8%" is a deterministic claim: a
number, in a label, verbatim. It is also wrong, because the label says "8% to
20%", and that is a context failure sitting inside a deterministic span. In the
other direction, "HARMONIA establishes nothing either way" reads as a judgement
call; what was missing was a deterministic field, `whyStopped`, that nobody had
bound.

So: every sentence answers all three questions, and every answer is recorded.

**Locatable.** Is there a span in bytes we hold that says this? Deterministic,
free, no model.

**Faithful.** Read with what surrounds it, does the span mean what our sentence
says? Needs a reader — but a cheap and bounded one, because the span is already
found and the reader is handed the envelope rather than sent to search.

**Warranted.** Does our sentence's claim — its scope, its quantifiers, its
adverbs, its verbs of establishment — follow from what is faithful? Judgement.

The bucket is then not a routing decision. It is an OBSERVATION about where the
hard part of a given sentence lies, and it determines WHO must sign each verdict,
never which verdicts are required.

    bucket            locatable      faithful           warranted
    deterministic     machine        machine (B5, B6)   machine, then spot-checked
    context/table     machine        reader, given the  reader
                                     envelope
    judgement         machine        reader             named judge — see §7
    figure-based      NOT POSSIBLE   human attestation  named judge

Two rules make the classification load-bearing rather than decorative.

**An unclassified sentence is a defect** and blocks publication, exactly
as an unbound one does. The bucket is declared when the sentence is written, by
whoever writes it, and it is a claim about the sentence that can itself be wrong —
which is why the machine still runs B1–B11 over every row regardless of bucket.

**A bucket may be corrected downward but never upward without a signature.** If the
deterministic checks find a sentence is not what its bucket says — an unmapped
scope word in a "deterministic" sentence, a truncated span — the sentence is
demoted to the bucket its evidence supports and the stricter process applies.
Promoting a sentence to a cheaper bucket requires the judge for the bucket it is
leaving.

## 4. The deterministic layer

Each check below is stated with the error from this issue it would have caught.
None of them costs money and none of them calls a model.

**B1 Unbound sentence.** A page sentence with no binding row, or with a row that
is bound to nothing. → the *Cancers* 2023 study.

*Every sentence gets a row (2026-10-18).* B1 used to apply only to an "empirical"
sentence — one carrying a figure, trial name, registry id or quotation — and that
filter contradicted the writing rule the editor adopted on 2026-09-02, which the
editorial standard states as: "A sentence leaves that column by being bound to the
words it rests on, by being declared an inference and shown, or by coming off the
page", and preflight prints as "every sentence in the article is either bound to the
words it rests on, declared as an inference and shown, or off the page". Read by
hand, the 282 sentences the filter left without a row on the deskilling page held 53
errors, and no word list recovered them (the best reached 81% of a hand sort). So
`bindings.scan` now gives every page sentence a row except the ones the MARKUP says
are not prose: headings (h1–h4) and a source-list role label standing alone. A bold
lead at the start of a paragraph is NOT a heading: the page uses that markup for
emphatic claims as well, and markup cannot tell the two apart. The old triggers still name
a row's reason when they fire. Two word lists tag rows — `trigger: source_claim` (the
sentence describes a document in words) and `trigger: process_claim` (it says what we
read, opened, hold, checked or found) — and the process tag routes the row to B21's
store check (§4, B21). Tags route; they never decide whether a sentence gets a row.

**B2 Span present in cited document.** `span in document_bytes`. → HR 0.956
(0.777–1.177) attributed to *J Clin Oncol* 2024; the strings occur nowhere in the
paper. They occur in NCT01740427, which we also hold.

**B3 Span found in a different held document.** When B2 fails, search every other
held document before reporting absence. If found, report the correct source
rather than a failure. → the same error, repaired instead of merely flagged, and
the third instance this week of a registry number printed under a journal's name.

**B4 Locator servable.** If `locator_type == table`, the held bytes must contain
tables; if `field`, the path must resolve; if `prose`, the section must exist. →
the network meta-analysis, whose stored HTML contains zero `<table>` elements
while the page quotes its Table 1 for a row label and a hazard ratio. The ledger
says `full_text_held`. A document can be the whole paper by every test we run and
still be missing the part the sentence depends on.

**B5 Span completeness.** A span that begins or ends mid-sentence, or that stops
immediately before a conjunction or range marker — "and", "or", "to", an en dash
between numbers — is a defect. **This is the important one.** A large share of what
looks like context failure is truncation, and truncation is mechanically
detectable.
→ "grade 3 in 8%", where the span stops before "to 20%".
→ the ribociclib monitoring schedule, where the span stops before "at the
  beginning of each subsequent 4 cycles", halving the monitoring it describes.
*Sentence end (2026-10-18).* A span that ends at a sentence-final full stop,
question or exclamation mark (a closing quotation mark or bracket allowed), where
the document goes on with a new sentence (a capital, a digit or an opening
quotation mark), is complete. The conjunction test is case-insensitive and had
read the next sentence's "To" as the preposition (deskilling 2a091110, Troya's
"…not captured by the system. To further analyze…"). A span cut mid-sentence still
flags.

**B6 Scope words traceable.** Every quantifier and hedge in the sentence — every,
all, none, only, never, restricted, established, confirmed, always — must map to a
token in the span, or be flagged unmapped.
→ "labels every log-rank p-value on the study 1-sided": 15 log-rank analyses in
  the posting, 3 annotated, 12 not.
→ "restricted to the HER2-enriched intrinsic subtype", against an inclusion
  criterion reading "HER2-E **or** Basal-like".
→ "What PALOMA-2 established", against authors who wrote that the follow-up
  imbalance "limited interpretation".

**B7 Universal claims enumerate.** A claim quantified over a set must carry the
count and the enumeration, not one instance. This already exists in
`registry_settle._annotation()` and was simply never run against the sentence
that needed it.

**B8 Closer source available.** If a span supporting the claim exists in a
document CLOSER to the claim than the one cited — the publication itself rather
than a conference abstract about it — report it. → MONALEESA-7's one-sidedness,
sourced to an ASCO abstract and a registry while the NEJM paper we now hold says
*"The one-sided stratified log-rank P value was 0.00973."*

**B9 Page-to-ledger reconciliation.** Every source entry rendered on the page must
have a row in `sources.json`, and every source in `sources.json` must be reachable
on the page. → the *Cancers* study again, from the other direction.

**B10 Errata and comments.** Every source's bibliographic record must be checked
for `EIN` (erratum in) and `CIN` (comment in), and each result acquired or
recorded as unheld. Free, mechanical, requires no judgement. → the MONARCH 3
corrigendum of December 2025, and the MONALEESA-2 correction of August 2019. Both
were found today by a person reading metadata. Neither was found by any control
this project has built, and there had been nine months and seven years
respectively in which to find them.

**B11 Re-binding on re-acquisition.** When a document is re-acquired and its hash
differs, every span bound to the old bytes is re-tested against the new. Content
addressing already keeps both versions, so this is a diff, not an argument. This
is the changelog mechanism the library was built for and it has never been wired.

## 4a. Calibration — B19, B20, B21 (added October 2026)

A three-judge read of all 80 judgement sentences in the four WHU test issues
(T01–T04) found that every confirmed reasoning error leaned one way: toward
more certainty than the cited source allows. B6 asks whether a hedge in the
SENTENCE maps to the span; nothing asked the converse. These are numbered
after B18 rather than filed under B6, because `negatives.py` reads every B6
flag as its own quantifier worklist. All three run in `bindings.py check`, over
every on-page row — judgements included, which the span checks skip.

**B19 Hedge preserved. WARN.** The evidence is a judgement's premises, or a
bound sentence's span plus `also_rests_on`. If the evidence carries a hedge
(may, might, could, possibly, probably, likely, suggest(s), suggestive,
appear(s/ed), cautious(ly), preliminary, tentative, uncertain(ty), exploratory,
hypothesis(-generating), limited, low certainty, very low, low quality, not
statistically significant, trend, perhaps, would tend to, arguably, plausibly,
plausible — the last two added 18 October 2026) and the
sentence carries none (the same list plus modest, unclear, not a finding,
cannot, does not show, too few, low, weak), it is reported with the word found.
A negation — "does not support", "no evidence" — removes the hedge only when
the sentence carries no other hedge word; it never cancels one the sentence
keeps ("limited evidence, graded as no evidence" keeps "limited"). The
capitalised "May" is not a hedge where a date makes it the month: followed by
a year, a day number or "of", or preceded by a day number. → T01 s85, "The
evidence does not support choosing … on the basis of age or sex", against
"should be interpreted cautiously".

*Disposition (added 18 October 2026).* A hedge word may be disposed of, by a
person, on the row: `hedge_dispositions`, a list of `{word, why, by, on}`, the
same discipline as B6's `scope_words` and B20's `grade_departure`. When a hedge
B19 finds has a matching entry (word compared case- and space-insensitively),
that word is reported as INFO, verdict "evidence hedge disposed", with the
signer, date and reason in the finding; any other hedge on the row stays WARN.
An entry with a blank `why` or `by` is not a signature and is ignored. The flag
is never dropped: the record still says the evidence used the word. → deskilling
5850f3bd, S005's "they appear in about 36% of the included studies", where
"appear" means "occur" and states a count.

**B20 Confidence ceiling. STOP on a breach, WARN on no grade.** A sentence
beginning "Confidence in", "Confidence that" or "Confidence … is" states a
level on the ladder very low < low < moderate < moderate-to-good = reasonably
high < high. Its evidence's grades are very low / low / moderate / high within
six words of certainty, quality, confidence, GRADE or CINeMA. A level above the
highest stated grade blocks unless the row carries `grade_departure`, a
non-empty reason written by a person. No grade in any premise also blocks —
"confidence stated without a cited grade" — unless the stated level is low or
very low, which claim nothing a missing grade could undercut. `grade_departure`
lifts the ceiling block only: a missing grade is cured by citing the grade. →
T04 s60, "high" against the USPSTF's "moderate certainty".

The ceiling reads the PREMISE SPANS, not the documents. A grade the source
states somewhere the binding did not cite is invisible to it: T03 s53 and T01
s82 rest on reviews that grade their evidence low, but no premise span says so.
Both block as stating a level with no cited grade.

**B21 Holdings sentences rest on the store.** A sentence whose subject is our
own holdings or actions — begins "We hold", "We have not opened / read /
checked / obtained", "We did not obtain", "Our search", or ends ", which we have
not opened" — is true or false according to `sources.json`, not according to
any document. Such a row declares `rests_on_store` (the ids whose store record
it describes), carries no `source_id`, `also_rests_on` or `premises`, and takes
bucket `deterministic`: the machine answers all three questions against the
store. `bindings.py check` runs `epistemic.check_sentence` on every one, passing the
row's `rests_on_store` as the subject — the text is not asked which source it
means — and records a FAIL or NOT EVALUATED in `check_flags`. A row without the
field resolves from the text exactly as before. A sentence saying we hold the
abstract ONLY ("abstract only", "only the abstract", "the abstract … not the
full text / paper") passes on abstract_held and fails on every other state,
full_text_held included. "Have not opened", "did not obtain" and "could not obtain"
pass on not_opened, blocked or fragment_only and fail on full_text_held or
human_read. On abstract_held they WARN, "we hold its abstract — say so": true of
the paper, silent about what we hold. epistemic counts that WARN as evaluated.

**Process claims (2026-10-18).** A row the scan tags `trigger: process_claim` is a
holdings sentence too (`bindings.is_holdings(sentence, trigger)`; one detector, not
two). Its subject is the source-list entry it sits in (`store_subject_markup`, read
from the entry's link) if it sits in one, else whatever its text names. With
neither, it is NOT EVALUATED (WARN), never "not in sources" — "We check the sources
on this page" is about no one document. The comparisons the store can make
mechanically: "read in full / read at source / read directly / read in the … / we
read / we opened" need full_text_held or human_read; "could not open / could not
read / has not been able to read or open" need a not-held state; and "read at the
publisher" is a claim about the ROUTE, checked against the library: it passes when a
held rendition comes from a host that is not a repository or the ledger's sections
name the publisher's page, and fails when every held rendition is a repository copy
(PubMed Central, Europe PMC, arXiv, SSRN, OSF, an institutional repository).

**A declared judgement is not routed by its tag (2026-10-18).** The process_claim tag
is a word match set before anyone reads the sentence. A row whose bucket is
declared `judgement` — premises in held documents and a step — is not routed to B21
because of the tag; the subject phrasing (`HOLDINGS`, "we hold …") still routes it.
A process_claim row not declared a judgement is routed as above. (Deskilling
d03dd93f: tagged by "we missed", a judgement over S029, S047 and S043.)

**A declared framing row is settled (2026-10-18).** A row with bucket `context` and a
signed `framing` note {why, by} — a heading, signpost or transition that makes no
claim — is not "rests on nothing yet" in rule 1. It is reported on its own ok row,
"rule 1 — sentences declared framing", and never counted as bound or verified. A
note with a blank why or by, or on a row not declared context, is not a declaration.

**B24 — a sentence resting on WHU's own committed records (2026-10-18).** A claim
about what WHU did or decided ("read at the publisher", "a draft of this section
said …", the review-date ruling) has its evidence in the repository, not the
library, and `rests_on_store` cannot name a ruling. Such a row carries
`rests_on_record`: a list of `{path, quote, sha}`. `path` is repo-relative and
must be under `docs/` or the issue's own case directory (its `review/`,
`corrections.md`, `sources.json`, `watch.json`, `sweeps.json`, `errata.json` …);
anything else — the page under `site/`, another issue, an absolute path — is
BAD, "record path is not a WHU record". `quote` must occur, under spancheck's
normalisation, in the file **as committed at HEAD** (read through git; the
working tree is not a record). `sha` is the file's git blob sha when the binding
was made (`bindings.record_entry` writes it). A quote no longer in the committed
file, or a file not committed, is BAD, "record quote not in the committed file",
and rule 1 counts the row as bound on something that is not there. A file whose
blob has changed with the quote still in it is a WARN, "record changed since
binding", reported per row and on rule 1's own row "records changed since
binding"; the binding still counts. A verified record binding settles rule 1 —
reported on its own ok row, "sentences resting on WHU's committed records", and
never counted as a span of a document — and B21 does not ask the store about a
record-bound row that declares no store subject; a row that cites a document as
support is still refused, and a row with a store subject is still checked
against it.

*Markup and commit messages (2026-10-18).* HTML tags — an element name and its
attributes, never a bare "<" as in "p<0.001" — are removed from both the file and
the quote before matching, so a quote of a corrections.md sentence matches with or
without its `<q>` markup. A record entry may instead be `{commit, quote}`: the
quote must be in that commit's message (`git show -s --format=%B`), and the commit
must be in main's history; a quote not in the message, or a commit that is not an
ancestor of main, is BAD. No sha: a commit is immutable. `bindings.commit_entry`
writes it.

**A document mentioned and not held gets an entry.** A holdings sentence whose
`rests_on_store` names an id with no entry, or that declares nothing, cites
nothing, and whose text names no registered source, STOPs: "document not in
sources.json — add an entry (unread) for it". If the text does name a
registered source, it is undeclared, not unregistered, and WARNs with that id.
The entry is made with `source_ledger.py <slug> add <id> --title … --type …
--by <name>`, which writes the ledger's existing `not_opened` state — no new
state — and sets `document_class`. The ledger audit's "source ledger complete"
row reports every not_opened entry; that is intended.

**document_class at creation.** `epistemic.document_class_of()` sets it when
`source_ledger.add_unread()` creates an entry: `record_about` by the same three
discriminators `is_record_about()` reads (an explicit record form, type
`reference`, bibliographic sections); `document` where an explicit form or the
form `source_store.TYPES` gives the type settles it; otherwise `unclassified`,
written explicitly, which B21 reports as a WARN ("source unclassified") rather
than a silent NOT EVALUATED. It agrees with all 32 classes set by hand across
the seven issues. Existing entries are not back-filled; acquire_sources.py,
which updates existing entries, does not set it. epistemic also reads "have not
opened" and "did not obtain" as UNREAD, and "our search" as HOLD over the
declared sources (whether what the search fetched is held; not whether the
search was adequate). STOP: a holdings sentence that cites a
document as support; the store disagreeing. WARN: an undeclared holdings
sentence; a store check that returns NOT EVALUATED or reads no claim; a row
declaring `rests_on_store` whose sentence is not a holdings sentence. Rule 1 is
satisfied by the store and reported on its own row, never counted as a span.

**Why one new field, `rests_on_store`.** Nothing existing fit. A bucket names
who signs; it cannot name a record. `source_id`, `also_rests_on` and
`premises` are support, which is exactly what such a sentence must not carry.
`locator_type: none` says there is no locator, not that the store is the
answer. `bind_field` binds to a held document's field, and the store is not a
held document. The field also carries the subject: `epistemic.declared_sources`
reads the source ids off the row to know which record to ask.

**What the store check cannot yet do** (measured on copies of the test issues'
bindings, October 2026, with `rests_on_store` added). No source in the four
issues sets `document_class`, so every declared subject is NOT EVALUATED — by
design: an unclassified source is never assumed to be a document. Three of the
15 holdings sentences are about documents with no entry in `sources.json` (a
meta-analysis or study cited inside another source, a guideline's errata) and
STOP until one is added. A sentence whose text names two registered sources
and whose row declares neither ("We could not obtain PALMARES-2 itself": S011
and S021) stays NOT EVALUATED until rests_on_store says which. A sentence mixing a holdings clause with a cited claim (T04
s51) must be split: it cannot both rest on the store and cite a document. No page renders a per-sentence citation marker from the
bindings today, so a holdings sentence carries none by construction.

## 4b. Figures and wording — separators, rounding, B22, B23 (added 17 October 2026)

These make the free layer able to settle what the paid gate used to be paid for.
Code: `figure_text.py` (separators and rounding), `bindings.py` (rule 1, B22,
B23), `spancheck.py` (B12), `b13.py`. Tests:
`backend/tests/test_whatholdsup_figure_checks.py`.

**Thousands separators.** Rule 1, B12 and B13 read a grouped integer written
with a comma, a space, a no-break space or a thin space as one figure, both in
the sentence and in the held text. Before this, rule 1 and B13 read only the
comma, and B12 only matched a comma literally. Six figures in the test issues
(T01 14,170; T02 9,888,373 and 100,000; T04 21,315, 60,000 and 53,537) were in
their own spans, printed "14 170", and were reported as resting on nothing.
The reading is narrow: a lead group of one to three digits, then groups of
exactly three, with no digit, decimal point or separator-and-digit on either
side, so "in 2019 100 patients" is not joined.

**Rule 1 on judgements.** A judgement's figures must be in one of its premise
spans. A figure found only elsewhere in the held text does not satisfy it. An
undetermined premise covers its figures on the binder's word and is reported on
its own row. (This was already how rule 1 behaved; it is now pinned by tests.)

**Rounding.** A sentence figure that is a span figure with **at most one decimal
place dropped, correctly rounded** (half away from zero) passes rule 1. The pass
is not silent: an ok row, "rule 1 — figures shown rounded from their span",
carries an INFO note naming both values. Examples: −0.946 shown as −0.95, and
−0.43 shown as −0.4, pass. −0.946 shown as −0.9 (two places dropped) or as −0.94
(a truncation) fails as a figure in no span. An integer is never read as a
rounding. This is B12's precision rule, the one function `figure_text.rounds_to`
used by both, so the two cannot drift.

**B22 Wording claim. STOP.** This catches a sentence that says it gives a
source's own words.

- **Triggers:** "own wording", "own words", "in its words", "in their words"
  (and "in its own words").
- **"verbatim" and "word for word" trigger only** when the next thing after them,
  whitespace aside, is a colon or an opening quotation mark. "Addresses this
  question almost word for word" describes a likeness and gives no words to
  check, so it does not flag.
- **What is checked:** the claimed words are the clause after the phrase (after
  "is that", "is:" or a comma), up to the closing quotation mark if it opens with
  one, or else to the end of the clause.
- **When it passes:** if the whole clause, or any comma-delimited prefix of it of
  at least **two** words, is verbatim in a span the row is bound to or in the held
  text of a source it cites. Matching uses spancheck's normalisation. The
  two-word floor exists because melanoma's "in its own words, descriptive only ,
  against …" claims two words, and they are in S007. A single word is never
  enough.
- **Comparison form (2026-10-18):** quotations.py's. Curly against straight and
  single against double quotation marks fold silently. A match that needs the
  accent fold ("Budzyń" on the page, "Budzyn" in the held XML) passes with an INFO
  note, "wording claim matched ignoring accents", naming the words.
- **A sentence with a `<q>` (2026-10-18):** only the words inside the `<q>`
  elements that fall within the sentence on the page are claimed, and every one
  must be in the source; an unquoted lead-in ("In their words, trainees who rely
  on AI during the early formative years <q>may fail …</q>") is paraphrase and is
  not checked. A `<q>` running past the sentence's end is cut there. A sentence
  that cannot be found on the page is read as before.
- **When it fails:** STOP, naming the clause and the closest held sentence.
- **Source not held, or a defective text layer:** "wording claim undetermined",
  WARN, never STOP.
- **Reported speech** ("states that", "writes that", "describes this as") claims
  only the sense and is not this check's.
- **What it was built for:** T01 s80, the paid gate's one real error in Phase B.

**B23 Omitted interval. INFO.** A bound span gives a point estimate with a
confidence interval, and the sentence states that estimate (or a correct
rounding of it) with no interval, no interval word and neither bound. Most of
Phase B's real minor findings (I2, I3, I7, I9, I10) were this. A named interval
("95% CI") counts. An unnamed bracket counts only for a decimal estimate lying
between its bounds, so "aged 65 (60–70)" is not read as one.

**INFO** is a severity, never a preflight state: `publish.show()` turns any state
other than ok / BLOCKED / warn into a STOP. An INFO note rides in an ok row's
detail. The calibration row is ok when it carries only INFO notes.

Validation (read-only, saves captured in memory):

- **T01 s80:** STOPs under B22.
- **Published issues:** no new STOP on melanoma, cdk46 or deskilling. Two B22
  warns, cdk46 `78e56e24` and deskilling `34dbcad2`, are undetermined because the
  cited source is not held.
- **INFO notes:** B23 gave 24 across the test issues and 8 across the published
  ones; rule 1 gave 3 rounding notes.

## 4c. The narrowed paid gate (17 October 2026)

`factcheck_draft.py` now runs NARROW by default:

- **source** over only the figures and quotations the free checks cannot decide.
  `whatholdsup/narrow_gate.py` selects them, and the call is given those claims
  and nothing of the draft. A claim is selected when its evidence is a span
  `b2_present` marks UNDETERMINED: the source is fragment_only, blocked or
  not_opened, its held text has a defective layer, or the span is in no held text
  we could search. A quotation is selected when it is recorded in
  `quotations.json` against a source we do not hold. There is at most one call
  per such source, and no call at all if the set is empty.
- **recency**, unchanged, one call: whether a readout has been superseded is a
  question about the world after the documents we hold.

Not selected, because something free already answers it:

- a figure in a held span (rule 1, B12, B13, rounding);
- a figure in no span, or a span not in its document (rule 1 BLOCKS);
- an unbound sentence (rule 1's backlog row);
- a quotation whose source is held (quotations.py reads it against the bytes);
- a quotation with no recorded source (quotations.py BLOCKS);
- an attested `figure` row, and any source whose licence forbids machine
  reading. These are listed under `excluded`.

**The report** records `mode` (narrow or full), `roles_run`, `roles_not_run`, and
`narrow.source_checked` (the claim ids sent), with each claim's
`undetermined_because`. Roles that did not run print as NOT RUN, never as "0
findings". The report keeps the same sha binding, sentence fingerprints and
`passed` flag. So preflight's page-gate row (current report bound to the page
sha) and findings.py (B15) read it as before. Caps and run limits are unchanged:
a narrow run is a run.

**`--full`** restores the old gate unchanged: extract, source over every
extracted claim, recency, advocate (selective reporting, framing, unsupported
characterisation), inference (whether conclusions are warranted), and coverage
(best outside coverage, contradictions of the premise). Use it when the narrow
gate's blind spots matter.

**`--dry-run`** prints the selected claims, the calls that would be made and the
estimated cost ($0.75 a call, the figure the cap is checked with). It makes no
call, writes no report and counts no cycle. On T01 it selects nothing: one call,
recency, $0.75, against Phase B's $4.63. melanoma, cdk46 and deskilling also
select nothing.

**What the narrow gate gives up**, accepted on 17 October 2026:

- **Provenance of verbatim words.** Phase B S7/S8: WebMD relaying CNN. The words
  are verbatim in held text; the defect is who said them first. No string check
  sees that, and in narrow mode no role reads for it.
- **The whole-document readers.** Advocate, inference and coverage found Phase B's
  real calibration and selection points (A6–A8, I4, I8). B19–B21 and the
  conclusion judge cover part of that ground, not all of it.
- **Figures nobody bound.** A figure in an unbound sentence is not sent. On
  deskilling, B13 reports 29 figures in no held document while 19 sources are
  unheld, and the narrow gate selects none of them, because their sentences carry
  no binding naming a source. Binding them is the fix; `--full` is the stopgap.

Deskilling records ahead of page from 52f2205: S033/S034/S045 quoted but not linked on the committed page; clears at republish.

## 5. Context

The operator is right that a span quoted accurately but out of context is where a
lot of errors sit. Three mechanisms, in decreasing order of how much they buy.

**Never store a bare span.** Store the envelope: the span, its section heading, and
enough characters either side to make its sentence and its neighbours legible.
Whoever checks faithfulness sees "Grade 3 diarrhea occurred in 8% to 20% of
patients", not "8%". Most context errors stop being judgement calls the moment the
context is in front of the reader.

**B5 and B6 above are context checks that happen to be deterministic.** Truncation
and unmapped scope words are the two commonest ways a true span becomes a false
sentence, and both are decidable by string operations. This is what shrinks the
judgement bucket from "most sentences" to something a person can actually work
through.

The size of what these two buy is the whole argument for building them. Of the
fourteen errors found on 1 September by reading every document behind issue two,
**eight were decidable by string operations** — span absent, span in a different
document, span truncated, scope word unmapped, locator unservable, source
unreconciled. Three more were errata, found in bibliographic fields. Three were
genuine judgement. Context, handled by mechanism, stops being the large murky
bucket it appears to be.

**What remains is genuine and needs a reader**: a span that is complete, whose
scope words all map, and which still misleads because of what the document says
elsewhere. P-VERIFY's "in the absence of head-to-head RCTs" is exactly this — the
phrase is in the paper, and it modifies other authors' analyses, not the study's
own rationale. No string test finds that. A reader handed the envelope does.

## 6. Tables and figures

**Tables are recoverable and must be recovered.** A table claim is only bindable if
the table's cells exist as text beside the document. So: on acquisition, extract
tables to a derived artefact stored under the document's hash; where a publisher
serves table bodies separately, fetch what the stub points at. A claim whose
locator is a table, against a document with no extracted tables, is a **B4 block**
— which is what the network meta-analysis should have produced instead of passing
as full text.

**Figures are not bindable and must be labelled.** A claim that rests on reading a
plotted curve cannot be bound to characters, and pretending otherwise is how a
confident-looking system produces a confident wrong answer. Such a claim requires
a **human attestation**: a named person, a date, the question they were asked and
the answer they gave. This is the NCCN pattern generalised — where a machine
cannot read, a person answers a recorded question — and the page should say, in
the source entry, that the claim rests on a figure read by a person.

The honest consequence: figure-based claims are more expensive than any other
kind, and the right response to that is usually to find the number in the text or
the registry instead, and only fall back to the figure when it exists nowhere else.

## 7. Judgement

The operator asks that we identify each judgement call and decide what can judge
it. Two things to add before the routing question.

**Narrow before you route.** Most of today's judgement errors dissolve under
rewriting rather than adjudication. "What PALOMA-2 established" becomes "PALOMA-2
did not demonstrate a survival benefit" — which is bindable, because the paper
says *"OS was not significantly improved"*. "Restricted to the HER2-enriched
subtype" becomes "the randomised comparison was in the HER2-enriched subtype" —
bindable. "It opens by describing its own purpose as..." becomes a claim about
what the paper says rather than where it says it — bindable. **A judgement claim
that can be replaced by a bindable one should be**, and the pipeline should try
that rewrite before spending a judge on it.

What survives is a much smaller set: claims of emphasis, of sufficiency, of what a
body of evidence adds up to. Those are the sentences this publication exists to
write, and they should be the ones a human reader spends attention on.

**Who judges what.**

| kind of judgement | judge |
|---|---|
| does the span support the sentence | the priced gate, given the envelope |
| does the source support the characterisation | the adversarial source role |
| is the framing fair, is something missing | the outside reviewer |
| anything a licence reserves to a person | the operator, by recorded question and answer |

The outside reviewer's record is the argument for the last two rows. They found
the Table 1 error, the two head-to-head trials the page said did not exist, and
the *Cancers* study. Every one of those is a selection or framing failure, and not
one of them is the kind of thing a span check can see.

## 8. The pipeline

    bind          every sentence gets a row (headings and labels by markup excepted), or blocks
    deterministic B1–B23; free; produces blocks and repairs, never verdicts on truth
    rewrite       unbindable claims are narrowed toward bindable ones
    gate          priced, and by default ONLY over figures and quotations the
                  deterministic layer marks UNDETERMINED, plus recency (4c);
                  --full runs the whole-document roles as well
    correct       edit the sentence AND its binding; a correction that removes a
                  claim must remove a row whose span was ABSENT
    re-gate       only the rows whose sentence_sha or span changed
    review        the outside reviewer receives the binding table
    final edit    the operator

Two things this buys that we do not have.

**"Checked once" becomes affordable.** A row whose sentence and span are unchanged
does not need re-judging. That is what makes the second gate cheap enough to be
mandatory, and the second gate is the only thing that would have caught the
corrections that introduced errors.

**The correction step becomes constrained.** A correction that deletes a claim
must point at a row whose span was absent. On 31 August a correction withdrew the
Shaaban paper's own "29 blocks with block size of four" as our arithmetic. Under
this rule that deletion is refused, because the span is in the paper.

## 9. What this does not solve

Stated plainly, because a control that is trusted beyond its premise is the
failure this whole document is about.

- **A source that is itself wrong.** B10 is a partial answer and only a partial one.
- **Selection.** Nothing here notices a counterexample we never looked for, or a
  study we did not find. That is the counterexample hunt and the outside reviewer.
- **Figures**, per section 6, which is why they carry a person's name.
- **The bindings rotting**, if B11 is not wired.
- **Emphasis and proportion** — how much weight a true sentence carries in a
  paragraph. No mechanism proposed here touches it.

And the mechanism itself will be wrong, which is what R1 is for. Build it knowing
that, and build it so that being wrong shows up as a block a person resolves
rather than a verdict that stands.

## 10. Build order

Ordered by evidence produced per hour spent, not by architectural tidiness.

**1. B10, errata and comments — first, alone, and immediately.** It is the smallest
thing in this document: read the `EIN` and `CIN` fields of every source's
bibliographic record and acquire or record what they name. It requires no binding
store, no schema and no judgement. It found two corrections on the day it was done
by hand — a December 2025 corrigendum to MONARCH 3's final survival paper, and an
August 2019 correction to MONALEESA-2's updated results — after nine months and
seven years respectively in which nothing here noticed. Run it across all three
issues before anything else is built.

**2. The binding store, and B1.** Bind issue two's empirical sentences. Publish the
count of unbound ones as a number we look at. That number is the honest measure of
how much of the page rests on nothing the system can name, and it should appear in
preflight from the first day.

**3. B2, B3, B5, B6.** Span present; span found elsewhere; span truncated; scope
word unmapped. These four are most of the mechanical yield and none needs a model.

**4. B9 reconciliation**, which is a few lines and catches a whole source hiding in
plain sight on the published page.

**5. B4 and table extraction on acquisition.** Larger, because it changes what
acquisition stores; do it once the store exists to hold the derived tables.

**6. B8 and B11** — closer source available, and re-binding on re-acquisition. B11
is what makes the library a changelog instead of an archive.

**7. The envelope-fed faithfulness gate**, replacing the current page gate's
go-and-find-out role with a here-are-the-bytes role. Last, because it is the only
step that costs money, and everything above it shrinks what it has to read.

Steps 1 and 2 are worth doing before issue two publishes. The rest is not, and
saying so is part of the spec: a control built in a hurry to unblock a publication
is how five of the checks discussed in section 1 came to exist.
