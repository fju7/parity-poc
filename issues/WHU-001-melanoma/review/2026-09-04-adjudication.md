# melanoma — adjudication of the outside review, 2026-09-04

Reviewed: `2026-09-04-for-reviewer.html` — the single-file bundle: prompt, page,
Appendices A–D. Page sha256 `a788f00ab152…`, snapshotted as
`2026-09-04-sent.html`.
The review itself is in `2026-09-04-review.md` and is never edited after the
fact, including by us. This file is where our decisions go.

**Nine findings. Nine accepted. No rejections.** Two are accepted on grounds
different from the ones the reviewer gave, and both differences are set out
below rather than smoothed over. One is accepted and enlarged: what the
reviewer found as a single missing source was thirteen, and the sentence
describing the control over it described a control that did not exist.

## A note on the sources in this review

The reviewer's SOURCE fields reached us without their URLs. The quoted
sentences survived; the links did not. That is our transcription loss, not
their omission, and it matters in one place — OR-1 — where the finding turns on
a document we could not then locate. Everywhere else the claim was checkable
against the page or against a document already in our library, and every one of
those checked out.

---

## OR-0904-1 — "an outlet we can find no other publication citing" — ACCEPT, deleted, on different grounds

**Finding.** A 2026 letter in the Irish Journal of Medical Science cites Morning
Glory Sciences, so the negative is false.

**CONFIRMED, later the same day.** The operator supplied the PubMed id and we
read the publisher's own page. Riaz L, Komal W, Qureshi R, Khan M, *FDA Approval
of daratumumab and hyaluronidase-fihj plus VRd for the frontline treatment of
newly diagnosed multiple myeloma*, Irish Journal of Medical Science, 2026, DOI
10.1007/s11845-026-04315-0, PMID 41920444. A Letter to the Editor. Its reference
12 reads:

> Morning Glory Sciences. Oncology drug approval news flash: Daratumumab and
> hyaluronidase-fihj plus bortezomib, lenalidomide, and dexamethasone approved
> for newly diagnosed multiple myeloma in transplant-ineligible adults
> [Internet]. Morning Glory Sciences (2026) Jan 28

**So the sentence was false, on a live page, and this is a correction rather
than a withdrawal.** It is recorded in `corrections.md` under 4 September. The
document is held as **S028** so that the correction rests on a document and not
on a report of one.

**What we could not do, and it matters.** We searched five ways before the id
arrived — Europe PMC's REST API (rate-limited on every attempt through our fetch
proxy), its web search, PubMed by phrase, and two web searches — and found
nothing. PubMed does not index reference lists, so a citation living in one was
never going to surface there. **We had no way to run the search our own sentence
claimed to have run.** A sentence whose truth depends on a search we cannot
perform should not have been written, and that is the finding underneath the
finding.

**Why the clause would have gone regardless.** It is a universal negative over
the whole of the literature resting on one search on one day, and it was doing
real work in the paragraph: discounting the standing of a source whose argument
the paragraph then relies on. The counterexample settles it; the shape of the
claim was already indefensible.

The sentence now reads "Morning Glory Sciences — a specialist outlet, and we
give its argument on its merits —". The argument is unchanged and its two
premises are still quoted from S009 and S010.

**What this says about B15.** On 3 September we recorded exactly this gap — that
nothing asks whether a universal negative about other people's work is
contradicted by a document — and built B15 to close it. B15 searches OUR OWN
LIBRARY. This counterexample was never in our library and could not have been.
The check we built to catch this class of error is, by construction, unable to
catch the instance that arrived the next day. That is not an argument against
B15; it is the boundary of what a library search can do, and the reason a claim
about the whole literature cannot be defended by one.

**J28** carried the same negative as an inference premise. The premise is
removed and the step rewritten.

## OR-0904-2 — J01, "0 Phase 3 efficacy numbers released" — ACCEPT

The most uncomfortable finding in the set, because **we had already found it
ourselves and shipped it anyway.** J01's recorded step says, in capitals:

> THE CARD DOES NOT SAY THAT. It says '0 Phase 3 efficacy numbers released',
> which a reader takes as a claim about the world rather than about our shelf,
> and the caption has no room for the scope this binding names. Recorded so the
> mismatch is visible to the editor rather than invisible.

It was visible. It went out anyway, and the packet handed the reviewer our own
note admitting it. Recording a defect is not fixing it, and a binding that
documents a mismatch is not a scope.

The card now reads **"0 Phase 3 efficacy numbers in the announcement"**, which
is what S001 supports: the release states both endpoints were met and gives no
hazard ratio, interval, p-value or percentage for either. The step is rewritten
to match, and the row is `judgement` — it is a count over one document, which
is a step, not a figure read off a page.

We did not take the reviewer's suggested "found in our sources": it scopes the
claim to our searching when the stronger and simpler thing is true, that the
announcement contains none.

## OR-0904-3 — J09, "any interval" — ACCEPT

1.0 is the no-difference value for a **ratio**. For a difference between two
rates it is 0. The section explains confidence intervals generally, so "any
interval" is wrong, and J09's own step says "1.0 is the no-difference value for
a ratio" — the step was right and the sentence was broader than it.

Now: "The single most useful question to ask of a hazard-ratio interval: does it
cross 1.0? Because for a hazard ratio, 1.0 means no difference at all. (The
no-difference value depends on the measure: it is 1.0 for a ratio, and 0 for a
difference between two rates.)"

The reviewer's cited source for the ratio/difference distinction is not in S025
— we searched it and the language is not there. The narrowing needs no new
source: it removes reach rather than adding a claim. The added parenthesis rests
on S025, which is already the premise for what a hazard ratio is.

## OR-0904-4 — the p-value definition — ACCEPT

The strongest finding in the set, and it is settled by a document already on our
shelf. **S022**, Greenland et al., which the page cites and which we have read:

> The P value is then the probability that the chosen test statistic would have
> been at least as large as its observed value **if every model assumption were
> correct**, including the test hypothesis.

Our definition card conditioned on the treatment doing nothing and nothing else,
and then said "A small p-value means the result would be a surprising fluke",
which attributes a small p to chance specifically — one of the misinterpretations
that paper exists to list. The callout directly beneath it already said the
assumptions "are part of the claim, not a footnote to it". The page contradicted
itself across two adjacent boxes.

Rewritten to S022's own framing, which is compatibility with the whole model:

> How compatible the data are with a model in which the treatment did nothing —
> and in which every other assumption behind the analysis holds. By convention,
> below 0.05 is called statistically significant: an arbitrary line, but a
> widely used one.

This is a replacement rather than the deletion the reviewer proposed, because a
glossary term with no definition is worse. The replacement introduces no claim
S022 does not make in those words.

## OR-0904-5 — the stage-risk sentence — ACCEPT, on the internal ground only

The reviewer gives two reasons. We can check one of them and not the other.

**Checkable, and decisive.** The paragraph above says "Which of them is right
cannot be settled from anything published." The sentence then settles it, in
Morning Glory's favour, and demotes Pharmacy Times to a "counter". A piece
cannot say a question is unsettled and then answer it two paragraphs later. That
is enough on its own.

**Not checkable here.** The stage-specific cohorts showing IIB≈IIIA and IIC≈IIIB
arrived without citations. We have not verified them and are not recording them.
They would strengthen the finding; they are not needed for it, and the fix is
the same either way — deletion.

The sentence is gone. The one after it — "Whether the effect holds up across
that wider range is a real open question" — already said what the evidence
carries.

## OR-0904-6 — "this page holds no document about one" — ACCEPT

A flat contradiction inside one paragraph. The sentence before it says
CheckMate 238's arms are nivolumab and ipilimumab; Appendix B lists S021, that
trial's registry record; ipilimumab is a CTLA-4 antibody. We hold a document
about one.

We confirmed the pharmacology independently — StatPearls NBK557795,
"Ipilimumab is a CTLA-4 monoclonal antibody" — though the fix needs no source,
because it is a deletion. The clause is gone. The paragraph still makes its
point: a CTLA-4 inhibitor is a different drug against a different target, so the
PD-1 claim does not extend to the class.

Worth noting where this sat: Appendix C listed this exact sentence as item 6,
"a claim about our own library, checkable against Appendix B". It was checkable,
and it was checked, and it failed. The appendix worked.

## OR-0904-7 — two composite endpoints — ACCEPT, both

Rule 3, in the last two places the composite had been left short. "a rate of
recurrence" → "a rate of recurrence or death". "reduces recurrence and distant
metastasis" → "reduces recurrence or death, and distant metastasis or death".

Three passages were corrected for this on 3 September. Two more survived. The
rule has now produced findings in three consecutive reviews, which says the
drafting process is not applying it, not that the reviewers keep finding new
instances.

## OR-0904-8 — the source list — ACCEPT, and it is larger than reported

The reviewer found that the five-year landmark rates trace to the ASCO abstract
and that the abstract was not in the list a reader sees. Checking it properly:
**thirteen of the twenty-two documents this piece rests on were missing** — all
three other trial registries, all three statistical references, the ASCO
abstract, and five of the coverage articles the piece quotes about what the
coverage said.

Worse is the sentence that introduced the list:

> Every number above traces to one of these, and none to a news report — **a
> check that runs before this page can publish refuses it otherwise.**

No such check existed. B9 runs the other way: it takes every link on the page
and asks whether the ledger accounts for it. Nothing took the sources the
bindings name and asked whether the reader can see them. We advertised a control
we did not have, in the sentence asking readers to trust the list. That is worse
than having no control, because a reader who checks our sources is entitled to
assume the check we describe ran.

Three things done:

1. All thirteen added to the displayed list, with what each supports.
2. The sentence rewritten to describe the check that now exists, and the claim
   about news reports corrected: two hazard ratios do reach the page from a news
   roundup — the ones inside the quoted announcement-day post — because a figure
   circulating under the wrong trial's name is the subject of that paragraph.
   The same sentence in the footer's Checking note, and in the email, is
   corrected to match.
3. **B17 built** — `sources_shown.py`. Two directions: a document an on-page
   sentence rests on that the reader cannot see BLOCKS; a listed document
   nothing rests on WARNs. It runs on the URL, because a link is what a reader
   actually has.

B17 found one more thing on its first run: S026's ledger URL was the
ClinicalTrials.gov **API** address, the only registry record in the issue not
carrying its human `/study/` URL. A reader following it would have got JSON.
Normalised, with the old address recorded in the access note.

## OR-0904-9 — the correction history — ACCEPT

The header said Updated 4 September; the change log's last heading said 2
September; paragraphs beneath that heading described things done on 3 September.
The diagnosis is that `corrections.md` and the page's own change log had
diverged — corrections.md carried full entries for 3 and 4 September and the
page carried neither.

A 4 September entry has been added covering the two missing days and this
review: what changed on 3 September, what changed on 4 September before the
review, what the review changed, and the source-list failure above. It opens by
saying the gap existed, because the gap is one of the findings.

---

## A note on these labels

They are `OR-0904-n`, not `OR-n`. The 3 September adjudication used `OR-1`
through `OR-9` and so did the first draft of this one, which put eighteen
decisions into nine labels: a change citing `OR-4` would have resolved to
either yesterday's composite-verdict decision or today's p-value definition,
and the reconciliation check would have passed either way. A label that
resolves to two different decisions is not a label. Dated from here on.

## Two things the reviewer looked for and did not find

Both are recorded because a negative result from an independent search is
evidence we cannot generate ourselves.

- **Appendix C item 4, "in its own voice".** The reviewer tested whether the
  qualification is a hedge that makes the sentence unfalsifiable, and concluded
  it survives: KOL Pulse reproduces the oncologist's post carrying the Phase 2b
  hazard ratios, while its own editorial text says the Phase 3 numbers are not
  disclosed and warns that the circulating ratios are Phase 2b figures. The
  distinction between what an outlet says and what it quotes is real. Kept.

- **Appendix C items 8 and 9**, the two negatives scoped to the world rather
  than to our library. The reviewer found no published INTerpath-001 hazard
  ratio, interval or absolute rate, and no stage-specific Phase 3 subgroup
  result, as of 4 September 2026. This does not make either sentence safe. It is
  the best evidence available that they are currently true.

## What this review says about the process

Four of the nine findings were things the page said about itself: a card whose
scope its own binding contradicted, a clause its own paragraph disproved, a
definition its own callout corrected, a source list its own introduction
misdescribed. None needed an outside document. All four were reachable by
reading the page against itself, and none of our checks reads the page against
itself.

That is the gap worth naming. Our machinery checks sentences against documents.
It has no test for a page that argues with itself, and this is the second review
in a row where self-contradiction was the largest category.

---

# The gate's own open findings, decided the same day

The 3 September page gate left thirteen findings open against text still on the
page. They were not part of the outside review and are decided here because the
review made several of them cheap to settle: documents acquired for one finding
turn out to answer another.

**One of them found the Morning Glory sentence a day before the reviewer did.**
Finding o4, THIRD_PARTY: *"This is a negative characterisation of a named
outlet's credibility. The draft's search may simply have been incomplete, or the
outlet may be new or niche."* That is the same defect the outside reviewer
reported as their first finding, and our own machinery raised it on 3 September.
It sat unactioned for a day, and the sentence went to a reviewer inside the
packet. The check worked; the disposition did not happen. That is now the second
distinct way this sentence was catchable before it was caught.

## GATE-0904-o7 — "Several outlets called it a landmark" — ACCEPT

The gate is right and the error is in the second sentence of the piece. No held
outlet uses the word in its own voice. What the documents show is that S001, the
companies' release, carries *"Today's results represent a landmark moment for
adjuvant melanoma treatment"*, and S016 attributes it to Long, the study's
principal investigator; S006, S016 and S017 reproduce it as a quotation.

So the word is the investigator's, carried by the coverage — which is the exact
distinction this piece spends a section drawing, and the standfirst was on the
wrong side of it. Rewritten to attribute the phrase where it belongs. Recorded
as quotation Q-29.

## GATE-0904-o1 / o2 — 3.4 against a working of 3.35 — ACCEPT, both

**3.35 rounds to 3.4.** The printed number was right. We had recorded it as a
discrepancy, said the figure was *"out by 0.05"* for eight days, and
"corrected" it — accusing ourselves of an arithmetic error we had not made, in
the correction history, where a reader goes to check whether we can be trusted
about our own mistakes.

Three passages carried it and all three are rewritten. What was actually wrong
with the composite is that it averaged direction-confidence and size-confidence
into one number, which is a defect in the number's shape, not its arithmetic,
and that is what the change log now says.

This is the second time a correction notice on this page has been worse than the
thing it corrected. Both times the shape was identical: a check reported
precisely, and the sentence written around it overstated. The 2 September entry
records the first instance in those words, and we did it again eight days later.

## GATE-0904-i5 — the five-year rates' attribution — ACCEPT

The body said the rates come from "the report of the analysis rather than from
the paper", which was vague and, after 3 September, wrong: they rest on S014,
the ASCO 2026 abstract. Now named.

## GATE-0904-o3 — "Coverage has been merging them" — RESOLVED, already gone

The offending subheading was replaced on 4 September before the review. What the
gate still matched is the residue of its quote — "Different sizes, different
patients, different rigour" — which is a factual comparison of two trials and
makes no claim about what coverage did.

## Seven reach failures — REJECT, all seven

Each has its own heading below so that a change can cite one decision rather than a group: a label that resolves to seven decisions is the defect this file already records about OR-n.

Seven findings that the gate could not verify because it could not reach the
document. Each is answered by bytes we hold:

### GATE-0904-c23

"the ASCO 2024 deck states 1-sided alpha of 0.1 per protocol": that
  deck is **S008**, we hold it, and the string is in it verbatim. The page now
  names it as a document we hold rather than as "the deck".
### GATE-0904-c27

HR 0.425, 80% CI 0.179 to 1.004, nine deaths: S007 prints
  `0.425 [80% CI, 0.179 to 1.004]` and the arm counts 4/107 and 5/50, which is
  nine.
### GATE-0904-c28

RFS 80% CI 0.351–0.743: S007 prints `0.510 [80% CI, 0.351 to 0.743]`.
### GATE-0904-c33

NOT_POSTED with posting dates November 2026 and October 2033: both
  are field values in S020 and S026, and two sentences are bound to them.
### GATE-0904-c43

the announcement-day post's HRs are Phase 2b figures: the gate's own
  text confirms the figures; the finding is about characterisation, and the page
  says only what S019 says.
### GATE-0904-c45

"shared with regulatory authorities": S001 contains that clause
  verbatim, twice.
### GATE-0904-c47

"not intended for formal hypothesis testing (ie, are descriptive
  only)": verbatim in S007.

An absence observed by something that could not reach the document is not an
absence. Seven of the thirteen were that.

**What would change it:** any of these strings failing `spancheck.b2_present`
against the source named, or the held bytes proving not to be the document.

## GATE-0904-c31 — "no alpha was assigned" — ACCEPT IN PART

The gate says the abstract's *"No alpha was assigned to this analysis"* attaches
to the exploratory OS analysis, not to the five-year recurrence result the page
uses it for. Reading S014, the sentence sits at the end of the methods' endpoint
list — primary RFS, secondary DMFS and safety, exploratory OS — and "this
analysis" most naturally means the five-year analysis being reported.

We think our reading is right and we are not certain, so the page now says where
the sentence sits: "in its methods, at the end of the list of endpoints". The
reader can see what it attaches to and disagree with us. Disclosure rather than
a silent resolution, because the ambiguity is real and is the gate's.

**What would change it:** the full presentation or protocol showing alpha
assigned to the five-year RFS analysis, which would make the companies' word
"nominal" wrong rather than exact.
