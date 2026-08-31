# WHU-002 — the 31 August re-gate, and what it found

The page gate ran on final text at 23:03 and cost **$5.70**, against an estimate
of $2.68. It returned 14 unresolved findings. Four were overturned
deterministically by the registry before anyone read them. Of the ten left,
**four were real and one of them was serious**, and the rest are recorded in
`draft_decisions.json` with the evidence that settles them.

Labels CORR-10..CORR-13 are cited by `changes.json`.

---

## CORR-10 — a wall we could not open, over a paper our own ledger says was read

**The finding.** The gate's most consequential objection. This page said:

> the paper itself is behind a wall we could not open
> We could not open PALMARES-2's declaration of interests. That is a statement
> about our access and not about its investigators, **of whom we know nothing**

and built a fairness argument on it: P-VERIFY's Pfizer funding is disclosed,
PALMARES-2's is not, and the asymmetry is attributed to access rather than to a
choice. The gate says the paper is open access under CC BY-NC-ND.

**We did not settle the licence and did not need to.** Every direct route was
refused on 31 August — annalsofoncology.org 403, ScienceDirect robots-disallowed,
The Breast 403, PMC behind a CAPTCHA, Europe PMC's search endpoint rate-limited
through repeated attempts. What settled it was in the repository:

    S011 access.state = machine_read, by the fact-check gate, 2026-08-29

**The page contradicted its own source ledger, and nothing compared them.**

**The distinction.** "Behind a wall" is a claim about the DOCUMENT. "We could
not open it" is a claim about OUR ATTEMPT. Only the second is ours to make.
This is the same error as a SOURCE role that could not reach a registry
reporting a figure wrong, as a retrieval that received a truncated document
reporting a string absent, and as a check that read an empty directory as an
agent that never ran — all three of which happened today. Here it was in the
page's own voice, in front of a reader, load-bearing.

And "of whom we know nothing" is worse than imprecise: it asserts an absence we
never searched for. Sub-analyses of the same study are published separately and
carry their own declarations. We did not look.

**Disposition** — ACCEPT, in full.

**Change.** Both sentences rewritten to describe our attempt rather than the
document, to say that the ledger records the paper as reached, and to say
plainly that not reading the declaration was a choice and not a wall. The gate's
report of what the sub-analyses disclose is attributed to the gate, not repeated
as our finding, because we have not read them.

**Structural change.** `source_ledger.inaccessibility_claims()`: a sentence
saying a source could not be opened, against a ledger that says it was read, is
now a STOP. It does not decide whether the document is open — it cannot, since
that needs a retrieval and a failed retrieval is the evidence this check exists
to distrust. It reports the tension and makes a person resolve it, by correcting
the page or by downgrading a ledger entry that overstates what was read. It
found two on this page; both are fixed.

---

## CORR-11 — the fourth position on one p-value

**The finding.** The page's table prints MONALEESA-2's final overall survival as
`p = 0.008`, NEJM's figure, and its footnote said **"it is one-sided"**, sourced
to the registry's statement that the test was run at a one-sided cumulative 2.5%
level.

Read from the ClinicalTrials.gov v2 API on 31 August, NCT01958021, Overall
Survival (OS):

    pValue        0.004
    Hazard Ratio  0.765 (95% CI 0.628-0.932)
    description   "...compared using a log-rank test at one-sided cumulative
                   2.5% level of significance."

NEJM prints P = 0.008 with HR 0.76 (0.63-0.93). **0.008 is exactly twice
0.004** — which is what a one-sided and a two-sided presentation of one log-rank
test look like beside each other.

So the design was one-sided and the journal's number is not the one-sided
number. The page had taken the registry's statement about the TEST and attached
it to the JOURNAL's figure. Two documents' facts paired as though they were one.

This is the fourth position this page has held on a single fact: two-sided with
no source; then unknowable; then one-sided with the registry's directionality on
the journal's number; and now this. The first was unsourced, the second was a
search we had not run, the third was a conflation — and the third was introduced
by the correction that fixed the second, and found by the gate run that read it.

**Disposition** — ACCEPT.

**Change.** The footnote now gives both numbers, says which document each comes
from, states the doubling as arithmetic, and says explicitly that we have not
read NEJM's statistical section so the doubling is not offered as the paper's own
account of itself. The page keeps printing 0.008, because that is what a reader
will find, and no longer calls it one-sided.

**Sources considered** — S019 (registry, re-read at the API), S005 (NEJM, still
unread and still disclosed as unread).

---

## CORR-12 — a trial that reported nothing cannot have found no difference

**The finding.** In two places the page said the two randomised head-to-head
trials "found no difference". One of them is HARMONIA, which terminated at 61
patients with no results publication. It found nothing. The page says so
correctly elsewhere — "this page draws none from it beyond the fact that the
trial was run" — and then flattened it in the summary a reader is most likely to
quote.

**Disposition** — ACCEPT.

**Change.** Both sentences now separate them: one reported and found no
difference, the other stopped at 61 patients and never reported.

---

## CORR-13 — our arithmetic wearing the source's clothes

**The finding.** The source note for the Shaaban trial said the randomisation
was "in 29 blocks of four by opaque sealed envelope". No source we can reach
states a number of blocks. 116 divided by four is 29. We did the division and
printed the result as though the paper had said it.

Small, and exactly the class of error that erodes a source note's whole value: a
reader who checks one figure and finds it is not in the paper has no reason to
trust the four beside it.

**Disposition** — ACCEPT.

**Change.** Withdrawn, and the withdrawal is on the page rather than silent.

---

## Declined, with the evidence — see `draft_decisions.json`

- **70.2 months** — the role says the figure is not in the meta-analysis's
  results section and belongs to a preceding ASCO abstract. It is in the results
  section; Europe PMC's full-text XML returns it with its surrounding sentences.
  Four confirming reads across two hosts. The single denial came from a
  retrieval that reported Table 1 absent from what it had received.
- **MONALEESA-7's annotation string** — NOT_FOUND because the role could not
  read the posting. The API returns `pValueComment: "One-sided stratified
  log-rank test"` in under a second.
- **NCCN's HR 0.56 (0.45-0.70)** — a claim about what the GUIDELINE prints,
  checked by the role against the trial publications instead. Fred read the
  guideline on 29 August and confirmed the figure. NCCN's licence forbids any
  automated check reading it, so this finding can only ever be raised and only
  ever be answered this way.
- **PALMARES-2's ASCO 2024 figures** — the role says the page conflates the
  conference presentation with the paper. The page separates them explicitly, in
  the same sentence.

---

## What the run cost, and what the estimate said

    estimated   $2.68
    actual      $5.70      2.1x under

The estimator counts claims whose figure has left the page and adds a fixed
charge for the roles that must read the whole page. It was within 9% on the
previous run and 2.1x under on this one, and the difference is visible in the
cost breakdown: **seventeen separate SOURCE roles ran**, one per source, and
`--since` carried far fewer verdicts than the model assumed.

The single most expensive line:

    source:HARMONIA — ClinicalTrials.gov     $0.87   253,272 tok   9 searches

**$0.87 and nine web searches to establish facts that `registry_facts.py`
confirms from the API for nothing, in under a second, and that the board had
already confirmed before the run started.** The deterministic tier currently
overturns the model's verdict AFTER the spend. registry_figures.py's own
docstring says it "runs BEFORE the SOURCE role, settles what it can, and is both
cheaper and more accurate than the thing it short-circuits" — and it does not.
That is the largest single piece of waste in this pipeline and it is now the
next thing to fix.
