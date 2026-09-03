# melanoma — adjudication of the outside review, 2026-09-03

Review packet: `2026-09-03-review-packet.md`
Prompt version: the 3 September revision (two questions; Appendices A, B, C)
The review itself is never edited after the fact, including by us. This file
sits beside it and is where our decisions go.

Nine findings. **Eight accepted, one referred to the editor.** No rejections.
That is the first review of this publication with no rejection in it, and the
reason is worth recording: the packet sent the reviewer at the reasoning and
the universal negatives rather than at the figures, and every figure had
already been verified against held bytes. They spent their attention where we
could not check ourselves, which is what the prompt now asks for.

---

## OR-1 — "The framing was never explained to readers." — ACCEPT, deleted

The reviewer cites public commentary explaining the one-sided framework. We did
not need their sources: **S019, KOL Pulse, which is in our own library**, says
"formal hypothesis testing of RFS, overall one-sided alpha=0.10, performed at
primary analysis". A document we hold, and had read, and had bound other
sentences to, falsifies the claim.

This is the most uncomfortable finding in the set. Rule 11 is our own rule —
before criticising the coverage, find the best of it — and the coverage that
beats us was on our own shelf. Deterministic checks cannot catch this: nothing
in the binding layer asks whether a *universal negative about other people's
work* is contradicted by a document in the library. That is now recorded as a
gap rather than fixed, because the fix is a new check and this is not the
moment to write one.

## OR-2 — composite endpoints, three passages — ACCEPT, all three

Rule 3. Three explanatory passages dropped death from an endpoint that is
recurrence-or-death or distant-metastasis-or-death. The sentence about the
Phase 2b was internally inconsistent in the same breath — it preserved
"recurring or dying" and then wrote "reaching distant metastasis". Corrected to
"recurring or dying", "spreads to distant organs or the patient dies", and
"reaching distant metastasis or dying".

## OR-3 — the normal practice is not named as normal — ACCEPT

Rule 6, and the page nowhere discharged it. Added after the companies' own
statement that the data will be presented at a meeting: announcing topline
results ahead of a conference presentation is routine, and this piece is not an
accusation that anything improper happened.

Bound as a judgement rather than asserted: its premises are the release's own
sentence and two outlets reporting the same expected sequence, and its step
says plainly that nothing in any document we hold treats the order as
irregular. "Routine" is a claim about industry practice and we hold no document
that states it in general terms; the step says exactly how far our evidence
goes.

## OR-4 — one composite verdict for direction and magnitude — REFERRED TO THE EDITOR

Not accepted and not rejected. See "The one for the editor" below.

## OR-5 — J10, the p-value gloss — ACCEPT

The strongest finding in the set, and the one Appendix A was built to produce.
Our step read "if the drug were useless, you would see a result this good about
5% of the time by luck". Our own bound premise says the P value is computed "if
every model assumption were correct, INCLUDING the test hypothesis". We
conditioned on the test hypothesis alone and dropped the rest of the model —
which is the exact misinterpretation the cited paper exists to correct. We
mis-stated the source we had verified, in the direction the source warns about.

Rewritten to carry the whole condition, and the step now says what went wrong.

## OR-6 — J07, "no effect could not be ruled out" — ACCEPT

Unqualified, it implies the trial failed a test it never set itself: the
prespecified analysis was one-sided at alpha 0.10 and produced p = 0.0266. Now
reads "on a two-sided 5% criterion", and the step explains why the criterion is
named. This is our Rule 7 applied to a sentence that did not obviously look
like a p-value sentence.

## OR-7 — "n=14 — the whole survival analysis" — ACCEPT

Fourteen is a count of deaths; n is a sample size everywhere else on the page
and everywhere else in trial reporting. The body already gets this right and
says so explicitly, which makes the summary strip worse rather than better — a
reader who reads only the strip is misled by the page's own shorthand. Strip
now reads "14 deaths".

## OR-8 — "and none to a news report" — ACCEPT

Contradicted by our own correction history further down the same page, which
records the five-year rates being credited to The ASCO Post. Clause deleted.

The reviewer's better repair — moving those rates onto the ASCO abstract — is
**not done and cannot be yet**: see the acquisition note below.

## OR-9 — "A week on" — ACCEPT

Event 19 August, page updated 3 September. Replaced with "No numbers have been
released since", which does not go stale.

---

## The one for the editor — OR-4

> The proposition scored is directional: does the treatment improve RFS? The
> page itself says a large blinded Phase 3 crossed its prereg threshold, while
> what remains unknown is how large the improvement is. Penalising the absence
> of magnitude through "Data support 1" and rolling it into one "Moderate"
> verdict combines exactly the two questions Rule 8 says one verdict cannot
> express.

We think the reviewer has identified something real and that the decision is
not ours. The page anticipates the objection — "a scoring system worth having
has to be able to say both at once" — and answers it by publishing the six
dimensions beside the composite. The reviewer's reply is that the composite is
presented as a verdict, and a verdict is precisely what Rule 8 forbids here.

Four ways out, for the editor:

1. **Drop the composite for this claim.** The reviewer's fix. Cheapest, and
   costs the piece its headline number.
2. **Drop composites generally.** Consistent, and a large product change.
3. **Score direction and magnitude separately** — two numbers, always. Answers
   the rule head-on and is the most work.
4. **Reject**, on the ground that six published dimensions beside the composite
   already separate the questions for any reader who looks.

Nothing is changed on the page until this is decided. The composite currently
reads 3.35, Moderate.

---

## Acquisition — what the reviewer could reach and we cannot

The reviewer reports S014 (ASCO abstract 9500) and S017 (OncLive) are readable
from the open web, and reports what S014 contains: the five-year RFS and OS
landmark rates, and "No alpha was assigned to this analysis".

**Both still return HTTP 403** — to `acquire_sources.py` and to the sanctioned
fetcher, retried 3 September. So we do not hold them, and nothing on the page
may rest on them. The reviewer's account of what S014 says is prose about a
document, which is the one thing this publication has learned not to write
from.

They stay on the human search list. If the operator saves either file, the
store takes it directly:

    python3 backend/scripts/whatholdsup/source_store.py melanoma \
      add S014 <path> --url <url> --via "saved from a browser"

S014 would earn its place twice over: it moves the five-year landmark rates off
a news report and onto the primary document, which is OR-8's real repair, and
"No alpha was assigned to this analysis" is direct support for the descriptive-
only point the piece currently makes from the three-year paper.
