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

**What we could verify.** Not that. We searched for the letter five ways —
Europe PMC's REST API (rate-limited on every attempt), its web search, PubMed
by phrase, and two targeted web searches. PubMed does not index reference
lists, so a citation inside one would not surface there in any case. **We could
not confirm the counterexample, and we are not recording it as confirmed.**

**Why the clause goes anyway.** It should not have needed a counterexample. It
is a universal negative over the whole of the literature resting on one search
on one day, which is the shape Appendix C of our own packet listed as the most
exposed claim on the page — and it was doing real work in the paragraph:
discounting the standing of a source whose argument the paragraph then relies
on. We cannot defend it, so it goes. Deleting a claim needs no source; that is
why this is the smallest available fix and the reviewer chose it too.

The sentence now reads "Morning Glory Sciences — a specialist outlet, and we
give its argument on its merits —". The argument is unchanged and its two
premises are still quoted from S009 and S010.

**Open, and it decides which kind of record this is.** If the IJMS letter
exists, a false sentence stood on a live page and this belongs in
`corrections.md` as a correction. If it does not, this is a claim we withdrew
because we could not stand behind it, and belongs in the change log as a
change. We have written it as the second and will move it if the URL arrives.
**Ask the reviewer for the link.**

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
