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
