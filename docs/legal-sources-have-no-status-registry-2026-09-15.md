# Legal and regulatory sources have no status registry — a Phase 5 gap

Written 2026-09-15 for the verification plan's Phase 5. Not built. The worked
example is a document Fred fetched by hand the same day.

## The gap

The publish gate freezes each source with a **status**: for a paper, Crossref
and Europe PMC say whether it has since been retracted, corrected, or the
subject of an expression of concern (`verify/status.py`), and the weekly
re-check (`recheck_topic.py --kind status`) marks the page when that changes.
That is the mechanism behind "a change marks the page; it never silently
un-publishes it".

Nothing plays that role for a legal or regulatory document. A court judgment,
a tribunal determination, a regulator's decision, a coverage policy: no
registry surfaces that it was appealed, quashed, reversed, superseded or
withdrawn. `verify/status.py` records these as `no_registry` — "watched by the
binding re-check only" — and the binding re-check can only tell us whether the
text at the URL still says what it said. It cannot learn that a higher court
said the text no longer stands.

The verification plan describes the law registry as "free, stable,
machine-retrievable". Free and machine-retrievable hold. **Stable is false for
any determination subject to appeal.** The text is stable; its authority is
not.

## The worked example

The GMC's Fitness to Practise Panel determination of 28 January 2010 found
against Wakefield, Walker-Smith and Murch on, among other things, ethics
approval and the treatment of child subjects. The Lancet's retraction notice
of 6 February 2010 rests on it explicitly ("Following the judgment of the UK
General Medical Council's Fitness to Practise Panel on Jan 28, 2010 …
investigations were 'approved' by the local ethics committee have been proven
to be false"). Two years later, *Walker-Smith v General Medical Council*
[2012] EWHC 503 (Admin), Mitting J, 7 March 2012, quashed the panel's findings
and sanction against Walker-Smith.

On the record as frozen today (`0e25a32`):

- the notice's status is `retraction_notice` (Crossref knows it retracts
  Wakefield 1998) — correct, and permanent;
- the notice's own reliance on the GMC determination has **no status at all**.
  If the corpus had cited the GMC determination directly it would be
  `no_registry`, and the 2012 judgment would never reach the page by any
  machine route.

Two mmr claims attribute findings to the GMC in terms that cover the co-authors
rather than Wakefield alone (721f53f7 "the Wakefield et al. research involved …
ethical violations in the treatment of child subjects (including invasive
procedures without ethical approval)"; 08ba751e "the Wakefield et al. study was
found to have involved … ethical violations in subject recruitment"). The
first now renders, identity-only, on the retraction notice. The machine has
no way to know that part of what it rests on was quashed.

## What Phase 5 needs

1. **A recorded human re-check interval on every legal source**, stored on
   the source (`metadata.status_registry = none`, `metadata.recheck_interval`,
   `metadata.last_human_check`, `checked_by`), surfaced by the weekly job as a
   due-date, and marked on the page as "status last confirmed by a person on
   <date>" — the honest equivalent of the registry line a paper gets. Overdue
   is a marker, like a retraction.
2. **A hand-curated events table for legal status**, under the same
   candidate-table discipline as `events.json` (primary URL verified by fetch,
   `reviewed_by`): `{source, event: quashed | reversed | superseded |
   appealed | withdrawn, date, by, url}`. CHRONOLOGY and STATUS_AT_PUBLISH
   already know how to consume events; they need a source for legal ones.
3. **Derivative reliance.** A source that rests on a legal determination (the
   notice on the GMC) inherits the determination's re-check, or the page says
   the dependence is unwatched. This is the harder half and may be out of
   scope for Phase 5; it should be named.
4. Migration 090 seeds the first row by hand: Walker-Smith v GMC carries
   `status_registry: none … human re-check interval required (Phase 5)` in
   its metadata.

Until then: any legal source on a published page is a source whose status the
system cannot learn changed, and the operator read should say so on each.
