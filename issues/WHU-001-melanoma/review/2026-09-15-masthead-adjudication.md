# melanoma — the masthead changes that live only in the publication record

Drafted 15 September 2026 by Advisor Claude, for the operator to accept or send
back. This document decides nothing new. It records where two existing
decisions already live, so that labels resolve against them.

Between the version an outside reviewer read on 4 September (sha `a788f00a…`)
and the page as it stands, the masthead changed three times. The third — the
dateline moving to 13 September — is recorded in `changes.json`. The first two
are not, and both are recorded in `published.json` instead. Neither is a missing
decision; both are on the far side of a record boundary the reconciler does not
cross.

## MASTHEAD-001 — the dateline set to 10 September for publication

**What changed.** The masthead dateline moved from *Updated 4 September 2026* to
*Updated 10 September 2026*. The navigation was unchanged: the enumerated issue
links were still present on both sides.

**When it reached readers.** The page went from the reviewed `a788f00a…` to
`76703fe9…`, recorded in `backend/data/whatholdsup/published.json` as a
**publish** row for this issue at 2026-09-10T17:54:52+00:00, sha `76703fe9…`.

**Who decided it, and how.** The operator, by publishing. `publish.py dateline`
sets the last-updated slot as part of the publication it belongs to; the
decision is the publication, and the publication row is its record. No separate
editorial judgement was made about the date, and none should be recorded as
though it had been.

## NAV-002 — the enumerated issue links replaced by a single Issues link

**What changed.** On 10 September 2026 the navigation on every page of the site
lost its enumerated issue links and gained one link to the generated index at
`/issues`. On this page the change was, verbatim from the record:

```
-  <a href="/melanoma" aria-current="page">Issue one</a>
-  <a href="/cdk46">Issue two</a>
-  <a href="/deskilling">Issue three</a>
+  <a href="/issues" aria-current="page">Issues</a>
```

**When it reached readers.** In commit `eead63c9dec835012d11d3af18b49d11e6e5fe74`,
committed 2026-09-10T18:19:50Z, which changed seven pages. The page went from
sha256 `76703fe9…` to `97d53bc3…`.

**Who decided it, and how.** The operator. `backend/data/whatholdsup/published.json`
carries a republish row for this issue at 2026-09-10T18:18:45+00:00, sha
`97d53bc3…`, superseding `76703fe9…`, whose basis reads: *"NOT a preflight. A
person read the diff below and signed it as not touching the argument. 4 changed
line(s)."* The row carries the four lines above as its `diff`, and this note:
*"Nav only: the enumerated issue links replaced with a single Issues link,
pointing at the new generated index at /issues. No sentence of the assessment
changed."* Deskilling carries the identical row at the same instant.

**Why it happened**, as the contemporaneous record states it — not as anyone's
recollection, which was not available when this was written. The commit message
of `eead63c` says: *"The issues index is built and generated, not written… Nav:
the enumerated issue links are gone from all seven pages, replaced by a single
Issues link. Melanoma and deskilling are published, so both carry a record-live
for the nav change; cdk46's nav change is deliberately NOT in this commit"* —
because the pre-push guard refused that push, cdk46 carrying adjudicated edits
with no publication record for them. That is why cdk46 kept the enumerated nav
while every other page changed, and why this change appears on two issues and
not three.

**What this document is for.** Both decisions above are complete. One is a
publication; the other is a diff a person read and signed. Each is on the record
with its date, its bytes and its reasoning. But both live in `published.json`,
and `reconcile()` reads only `changes.json`. The result is that the reconciler
reports this masthead as text that left the page with nothing recording it —
which is false. This document exists so that `changes.json` entries have labels
that resolve, and for no other purpose.

**What the reconciler will say afterwards, and why it is not quite right.** With
these entries in place the diff row is matched on its new text alone and
attributed to ERRATUM-001, the label on the third transition. That is the
closest thing the machinery can say: one diff row spans three changes, and only
one of them can be named. The board reports such a match as "matched on the new
text alone", which is honest about the weakness, and the three transitions are
each recorded separately here and in `changes.json` for anyone who looks.

**What this document does not decide.** It does not settle whether `reconcile()`
should read record-live rows directly. It should not be taken as establishing
that a record-live sign-off needs an adjudication in future; the opposite is
more likely right, and the question is filed as D1d in
`docs/whatholdsup-open-gaps.md`.

---

**What the operator is accepting.** That the two masthead changes described
above are the ones already on the publication record — the dateline set by the
publication of 10 September, and the navigation change he read and signed the
same day via the record-live row quoted here — and that recording them in
`changes.json` under these labels restates those decisions rather than creating
new ones. Nothing about the page's argument, figures or sources is in question.

Accepted by Fred Ugast, operator, 15 September 2026, stated in session. This
publication takes the operator's stated acceptance as his signature; no
manuscript signature is produced, and this line records the acceptance rather
than leaving a blank that could be read as its absence.
