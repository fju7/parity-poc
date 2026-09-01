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

**R2. Every empirical sentence answers all three questions in section 3. A bucket
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

**An unclassified empirical sentence is a defect** and blocks publication, exactly
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

**B1 Unbound empirical sentence.** A sentence carrying a figure, trial name,
registry id or quotation with no binding row. → the *Cancers* 2023 study.

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

    bind          every empirical sentence gets a row, or blocks
    deterministic B1–B11; free; produces blocks and repairs, never verdicts on truth
    rewrite       unbindable claims are narrowed toward bindable ones
    gate          priced, and ONLY over sentences whose span is present and
                  whose characterisation is in question
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
