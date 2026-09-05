# Briefing for an independent architecture review

Prepared 4 September 2026, by the system under review.
Published version: an artifact in the operator's Claude gallery.

---

## Part 1 — what we are asking you to evaluate

The operator states the requirement in three parts. A viable product must:

1. Fully research and capture the available data and reports bearing on a question.
2. Draft a report that accurately summarises and analyses that data.
3. Review the report AND its summary email to verify facts and evaluate
   inferences in both.

His concern is that the architecture is not good enough to ensure the outcome.
The question is not whether the current system can be patched. It is whether
this is the right SHAPE of system for the problem, and if not, what shape is.

We are not asking you to review the melanoma article. We are asking you to
review the machine that produced it, using that article's complete failure
record as evidence.

## Part 2 — the system as built

  46 modules · 20,424 lines of check code · 89 preflight rows · 182 tests
  3 issues published · $76.40 total model spend

Pipeline, in order:

  Acquisition       sources fetched, stored by content hash, ledger records
                    access state (full_text_held / abstract_held / blocked /
                    not_opened).                                        free
  Drafting          a model writes the assessment from held documents.  model
  Binding           every empirical sentence gets a row naming source,
                    locator and the exact supporting span; typed
                    deterministic / context / judgement / figure. A
                    judgement must show premises and a written step.    free
  Deterministic     ~89 rows: spans in the bytes, figures in some held
                    document, quotations verbatim, counts consistent,
                    registry facts, erratum lookups.                    free
  Fact-check gate   model pipeline, adversarial roles. Capped 3/issue,
                    1/email.                                     ~$4.45/run
  Outside review    independent reader gets a self-contained bundle:
                    prompt, piece, and appendices for every inference,
                    every source's access state, every universal
                    negative.                                          human
  Publish/announce  preflight must pass; email checked against the page.free

Two rules the system is built around:

  Rule 1  No factual sentence enters a draft unless it rests on a document we
          hold and have read.
  Rule 2  Every inference is declared as one and shows its premises and step.

And R1, the constitutional constraint: the binding layer may assert only the
presence or absence of a span. It may never assert that a sentence is true.

## Part 3 — what it has produced

  Issue              Gate runs  Reviews  Spend    Status
  WHU-001 melanoma       8         2     $36.20   published; corrected twice after
  WHU-002 cdk46          3         2     $29.57   published; 17 adjudicated errors
  WHU-003 deskilling     2         1     $10.63   published

Intended budget is 3 gate runs plus 1 on the email. Melanoma used 8. The
overrun is a finding: "correct the page, which creates text nobody has read,
which re-blocks the gate" is a structural property of the design.

## Part 4 — the error record

Issue two, 17 adjudicated errors, classified by what would have caught them
(run backend/scripts/whatholdsup/error_taxonomy.py):

  REGISTRY    7  (41%)   a structured field in a trial record
  LEDGER      3  (18%)   our own repository contradicting itself
  QUOTATION   1  ( 6%)   a string in or not in a document we hold
  ARITHMETIC  1  ( 6%)   a relation between numbers already on the page
  READING     5  (29%)   somebody must open a document and understand a claim

  Mechanically settleable  12 of 17 (71%) — of those, a check exists for 6
  Needs a person            5 of 17 (29%)

THE NUMBER THAT SHOULD WORRY YOU: 6 of 17 (35%) were introduced by an earlier
correction. One, CORR-13, was a correction that DELETED A TRUE STATEMENT — the
page said a trial randomised in "29 blocks of four", a fact-check finding could
not verify it, and the sentence was withdrawn by someone who had not opened the
paper. The paper says it, in its Methods.

The same rate held on issue one: 3 of its errors came in with corrections,
including a false accusation against ourselves — a printed score of 3.4 said to
be "out by 0.05 against its own working" of 3.35. 3.35 rounds to 3.4.

Issue one, by who found it (~38 items; classification is ours, and a judgement):

  Deterministic checks   ~30%   spans absent from bytes; figures in no held
                                document; a universal negative contradicted by
                                our own library; broken arithmetic under a mark
  Model fact-check gate  ~25%   self-contradiction; claims wider than evidence.
                                Half its findings on the last run were REACH
                                FAILURES — it could not open a paywalled
                                document we hold in full
  Outside review         ~25%   inference failures; scope; hedges; the piece
                                arguing with itself
  The operator, reading  ~10%   word choice importing a frame the source avoids;
                                a sentence denying the wrong proposition
  Found incidentally     ~10%   six defects in the check layer itself, two of
                                them inside a check within an hour of writing it

## Part 5 — where the errors that reached readers came from

The architecture answers one question extremely well: IS THIS STRING IN THAT
DOCUMENT? It is asked ~90 ways, free, on every publish. It is a good layer.

The errors that survived 8 gate runs, 2 outside reviews and 90 checks:

  "side effects attributed to THE VACCINE" — 59.6%, 59.6%, 51.0%
      span correct and quoted verbatim. The release attributes those rates to
      the COMBINATION of two drugs. We assigned them to one. Subject wrong.

  "Fourteen deaths, seven in each arm — NOT FOURTEEN PATIENTS"
      span correct, quoted in the same sentence. Fourteen patients did die.
      The sentence denies the WRONG PROPOSITION.

  "an outlet we can find NO OTHER PUBLICATION CITING"
      no span could exist. A universal negative over the whole literature. A
      2026 letter in the Irish Journal of Medical Science cites it.

  "SEVERAL OUTLETS called it a landmark"
      the word is in four held documents. It is the principal investigator's
      word, quoted from the company release. Wrong VOICE.

  "a check that runs before this page can publish REFUSES IT OTHERWISE"
      no such check existed. A claim about OUR OWN PROCESS — and 13 of 22
      sources were missing from the list it described.

  "the printed figure was OUT BY 0.05 against its own working"
      both numbers on the page. 3.35 rounds to 3.4. A false ARITHMETIC
      SELF-ACCUSATION, written in a correction.

NOT ONE OF THESE IS A SPAN ERROR. In every case the quotation was accurate and
the source correctly named. What was wrong was the proposition built around the
quotation: its subject, scope, voice, negation, or its claim about the pipeline.

The verification layer has near-total coverage of the error class that is NOT
failing and close to zero coverage of the class that is.

Three structural reasons:

1. PROSE IS WRITTEN FIRST AND BOUND AFTERWARDS. A sentence is composed, then a
   supporting span is found. That order lets a true span be attached to a false
   proposition, and the check confirms the span. Every error above entered this
   way.

2. WHOLE REGIONS WERE INVISIBLE. The change log — where we tell readers what we
   got wrong — sits in <footer>, and the binder strips <footer> before reading.
   154 sentences, a fifth of the prose, no controls at all until 4 September.
   Separately, quantities spelled as words are invisible to every figure check,
   which matches digits: 41 such sentences on the current page, none bound.

3. CORRECTIONS ARE THE LEAST-CHECKED TEXT AND THE LARGEST ERROR SOURCE. 35% of
   recorded errors arrived in a correction.

## Part 6 — the incumbent's assessment

Written by the system under review. Discount accordingly; check it against the
repository.

The architecture as built will not reliably deliver requirement 2 or 3, and
more checks of the current kind will not change that.

THERE IS NO MEASUREMENT. Every check was written after a specific incident and
is validated against that incident. That is good regression practice and it is
not an evaluation. Nobody knows the false-negative rate against errors not yet
made, because there is no held-out corpus and no scoring. The system's growth
is therefore unfalsifiable: 90 checks and 20,000 lines feel like rigour, and
the only evidence about whether they work is that errors keep arriving from
regions nobody modelled.

THE COMPLEXITY IS NOW A HAZARD. This week, changing one display state silently
disabled a guard two files away that existed to stop an unreviewed email being
sent — and the email went out with its gate check auto-waived. A check written
to catch reach failures was itself pointed at the wrong document twice within
an hour. 25 preflight warnings are permanently amber.

WORTH KEEPING: the binding layer and its span discipline; the source ledger
with explicit access states, which makes "we could not read this" a first-class
fact; the recorded error corpus; and the outside-review packet, the
highest-yield instrument in the system.

WHERE QUALITY ACTUALLY COMES FROM: an outside reader with the right prompt
returned nine real findings for an afternoon's work. The operator, reading the
published page, found two more in an hour. The last four gate runs cost ~$18
and found less.

## Part 7 — five candidate redesigns

A. INVERT THE ORDER: STRUCTURE FIRST, PROSE GENERATED FROM IT   [large]
   Require every claim as a structured record — {subject, predicate, value,
   unit, population, source, locator, span} — extracted before any sentence
   exists. Generate prose from the records, then check the prose back against
   the structure: does the sentence's subject match the record's subject?
   Addresses: every error in Part 5. Costs: rewrite of drafting; prose may read
   worse. Risk: subject-matching may itself need a model.

B. NARROW THE PRODUCT TO THE STRUCTURED LAYER                  [medium]
   Publish the claim table, sources with access states, what is established and
   what is not, the intervals, the change log. Cut the explanatory prose, where
   every error in Part 5 lives.
   Costs: much less good as journalism. Worth asking: is the readable article
   the value, or the verified substrate?

C. MEASURE BEFORE BUILDING ANYTHING ELSE                       [cheap, first]
   Freeze the check layer. Build a held-out corpus from the ~55 recorded errors
   plus injected mutations. Score every check. Publish detection rate per check
   and delete the ones that catch nothing.
   Why first: without it, every other option is a guess.

D. MAKE THE HUMAN LOOP PRIMARY, NOT LAST                       [medium]
   Two independent readers with structured prompts BEFORE publication. Move the
   model gate to a cheap pre-filter that prepares questions for them.
   Evidence: the yield ordering in Part 6.

E. CORRECTIONS MAY ONLY REMOVE, NEVER ADD                      [small, now]
   A correction may withdraw, narrow, or quote. It may not introduce a new
   factual assertion without the full drafting path. Written from the source
   record, never from the finding.
   Addresses 35% of all recorded errors. Caveat: CORR-13 shows removal has its
   own failure mode, so removal also requires reading the source.

## Part 8 — what we want your answer on

Q1  Is span verification the wrong primitive? Everything is built on "this
    string is in that document". The errors are all "this sentence misdescribes
    what that string means". Is there a primitive closer to the failure mode,
    and does it exist outside a model?
Q2  Can a machine check a sentence's subject against its source's subject? If
    not, the ceiling is set and requirement 2 needs a person by design.
Q3  Is 90 checks past diminishing returns, or past NEGATIVE returns? We have
    direct evidence of checks disabling each other.
Q4  How should a publication verify claims about itself? Several errors were
    false statements about our own process and library — the easiest class to
    check, and nothing was checking them.
Q5  Is the correction path fixable, or is the answer to publish less often?
Q6  Does a viable version exist at this scale at all — one editor, an AI
    pipeline, ~$25 an issue? If requirement 2 needs a subject-matter editor per
    issue, we would rather know now.

## Part 9 — how to inspect it

  backend/scripts/whatholdsup/error_taxonomy.py
      Run it. Prints the 17-error classification and the 35% figure.
  issues/WHU-001-melanoma/corrections.md
      Every error on issue one, reader-facing, in date order.
  docs/whatholdsup-claim-bindings-spec.md
      The binding layer and R1 — the constitutional part of the design.
  backend/scripts/whatholdsup/bindings.py
      The binder. Line ~152: FURNITURE strips <footer>, which is how the change
      log went unchecked.
  backend/scripts/whatholdsup/publish.py
      The preflight. ~89 rows; UNWAIVABLE_ON_SEND is the guard that failed.
  issues/WHU-001-melanoma/review/2026-09-04-for-reviewer.html
      The outside-review packet.
  docs/whatholdsup-open-gaps.md
      Known gaps, including GAP-006.
  backend/data/spend/ledger.jsonl
      Every priced model call, by issue.

Each check module's docstring records the incident that caused it to be
written. That is the fastest way to understand why the system has this shape —
and read end to end, the clearest evidence for the argument in Part 5.
