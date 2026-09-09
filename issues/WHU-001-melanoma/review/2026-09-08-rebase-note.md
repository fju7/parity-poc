# Rebase note — outside review, Sept 3 packet → Sept 4 bundle

The editor was right to stop. My 8 September directive was built against
`2026-09-03-review-packet.md`, SHA `09f91562bb645ec1`, 26 inference records. The
live base is `2026-09-04-for-reviewer.html`, SHA `a788f00ab1521235`, **37**
inference records plus a new Appendix D. Fred handed me the packet that was one
day stale; I had no way to know a newer bundle existed, and I did not check for
one before writing edit instructions. That is my error, and it is the same class
of error the packet is built to catch: I asserted something about the state of
the world from the state of my own library.

The J-numbering has been renumbered wholesale — old J01 (outlet attribution) is
now J03; new J01 is the stat-strip zero. **Every J-reference in the 8 September
review is invalid.** The rebased directive references sentences by text.

---

## What I got wrong

**Universal negative #1. I confirmed a false claim.**

My review said: "**Verified true as stated.** … the measure appears in the posted
results with the `analyses` array absent … Your reading of the registry is exactly
right."

It is not. I queried the `analyses` field and nothing else. The actual fields:

| trial | reportingStatus | anticipatedPostingDate |
|---|---|---|
| KEYNOTE-054 (NCT02362594), OS, all participants | `NOT_POSTED` | **2026-11** |
| KEYNOTE-054, OS, PD-L1-positive | `NOT_POSTED` | 2026-11 |
| KEYNOTE-716 (NCT03553836), OS | `NOT_POSTED` | **2033-10** |

The Sept 3 packet said the trials "posted an overall-survival result that carries
no statistical analysis at all — no hazard ratio, no confidence interval, no
p-value," and I signed it off. The Sept 4 bundle had already corrected it to
"has posted an overall-survival result at all… That is an absence of a finding,
not a null one," with the two posting dates. **Sept 4 is right, the Sept 3 packet
was wrong, and I confirmed the wrong one.**

This matters for substance, not just accuracy. "Posted a result with the analysis
missing" reads as withholding. "Not posted, anticipated November 2026" reads as a
schedule. The Sept 4 wording is the honest one, and my finding F8's suggested fix
("neither has posted a statistical analysis of overall survival at all") would
have re-introduced the older, wrong framing. The editor stopping prevented a
regression.

---

## What was already fixed before my review was written

These blocks are dead. Do not apply them.

| block | status in Sept 4 base |
|---|---|
| **B2** three-trial sentence | Already rewritten as two placebo-controlled trials, CheckMate 238 handled separately with its arm labels quoted. My fix would have been a downgrade. |
| **B4** restore OncLive | Already restored and named; the correction notice records it was obtained 3 September. Manifest already updated. |
| **D5** "A week on" | Gone — now "No numbers have been released since." |
| **F2's example** | The five-year rates no longer rest on The ASCO Post. The ASCO abstract was obtained by hand on 3 September and they now rest on it. My specific counterexample is dead — but see N3 below, the sentence is still false by another route. |
| **D1** partially | Stat strip item 3 is now "14 deaths" rather than "n=14". Items 3 and 4 still carry no trial label, so the finding survives in reduced form. |

---

## What survives, verified against `a788f00ab1521235`

Fourteen of the twenty-two. All confirmed present in the Sept 4 text, most
verbatim. Three of them — "the register says so", "the lower bound had drifted
out", and the adverse-event contrast — **have no inference record among the 37**.
That is a pattern worth naming on its own: the sentences carrying the errors I
found are the sentences Appendix A does not cover.

Detail is in the rebased directive.

---

## New findings that only exist against the Sept 4 base

**N1. KEYNOTE-054's overall survival is due in November 2026.** Two months away.
For a piece whose central open question is "does this extend life," the date on
which the field's nearest comparable trial reports its survival endpoint is the
most decision-relevant fact available, and it is sitting in a registry record the
piece already cites. Add it.

**N2. The new survival bullet compares an 80% interval to a 95% interval as
though they were the same instrument.** The Sept 4 text adds: "The three-year
paper reports a hazard ratio of 0.425 on nine deaths, with an 80% interval of
0.179 to 1.004; the five-year analysis reports 0.471 on fourteen, with a 95%
interval of 0.165 to 1.345. Both are wide enough to hold a large benefit and a
small harm at once."

An 80% interval that contains 1.0 is a far weaker signal than a 95% interval that
does, because the 80% interval is the narrower instrument. The 95% interval around
0.425 would be materially wider than the 0.179–1.004 printed. Saying "both are
wide enough" flattens that. This is the same interval-mixing problem as my C2,
now inside a single sentence.

**N3. "None to a news report" is still false, by a new route.** Two places now
assert it, one of them citing a machine guarantee:

- Sources: "Every number above traces to one of these, and none to a news report
  — **a check that runs before this page can publish refuses it otherwise.**"
- Checking: "Every figure above traces to **a company release, a peer-reviewed
  paper or a trial registry record**, and none to a news report."

The five-year rates now rest on the **ASCO 2026 meeting abstract**. A conference
abstract is not a company release, not a trial registry record, and not a
peer-reviewed paper — meeting abstracts are selected, not peer-reviewed, which is
the entire reason the piece elsewhere scores source quality 3 for resting on
pre-publication material. The enumeration has three slots and the document fits
none of them.

The publish-gate clause makes this worse rather than better: a check is being
offered to the reader as a guarantee of a sentence that is not true. Either the
check's definition of "news report" is narrower than the sentence's, or the check
is passing something it should refuse. Both are worth knowing before publication,
and this is the second time on this page that a check's precise output has been
reported in prose that overstates it — which the 2 September correction already
identified as the failure mode worth keeping in view.

**N4. Appendix C asks whether the CheckMate 238 exclusion is "honest and not
convenient."** It is honest — and incomplete. The exclusion is argued on the
grounds that every patient received an active treatment, which is correct. What
is not said is that the active comparator, ipilimumab, is the one adjuvant
therapy in this disease with a demonstrated overall-survival benefit against
placebo (EORTC 18071, HR 0.72, p=0.001 — my F9). Nivolumab failing to separate
from it on survival is therefore a *harder* test than placebo, not an
uninformative one. The exclusion is defensible; the reason given is the weaker
half of the true reason.

---

## The one thing I would ask you to change about the process

The Sept 4 bundle's own header says the last reviewer read a file whose SHA
begins `bd101cd121688ead`, and that 208 prose changes had gone in since. That
warning exists because this has happened before. It happened again to me because
the packet I was handed was a day old and carried no pointer to a successor.

A one-line freshness check at the top of the reviewer prompt — *this bundle is
current as of BUILD DATE; if a newer `for-reviewer.html` exists in the output
directory, review that instead* — would have caught it, as would a reviewer
whose first action is to list the directory rather than read the attachment. I
should have done the second. I did not.
