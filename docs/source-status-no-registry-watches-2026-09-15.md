# Sources whose status no registry watches — a Phase 5 gap

*Widened 2026-09-15 (evening): first written as "legal and regulatory sources
have no status registry"; the same day showed the gap is not specific to
legal documents. Three instances now, listed first.*

## Three instances, one gap

1. **A court quashed part of a determination a cited source rests on.**
   *Walker-Smith v GMC* [2012] EWHC 503 (Admin) quashed the GMC panel's
   findings against one of the three doctors; the Lancet's retraction notice
   rests on that panel's judgment; no registry connects the two.
2. **Legal sources have no status registry at all.** `verify/status.py`
   records a judgment, a determination, an agency filing as `no_registry`;
   the binding re-check can see the text change, never its authority.
3. **A journal's own correction the registry does not surface.** The BMJ
   published a competing-interests correction (bmj.d1678, 15 March 2011) to
   Godlee's editorial (bmj.c7452); Crossref reports c7452 `unchanged` — no
   update-to, no relation, no updating work — and the weekly status re-check
   would have said the same for as long as the page stood. This is the
   paper-status registry, the one the design trusts, missing a published
   correction to a paper we cite.

The gap, stated once: **the system's belief that a source's status is
"unchanged" is only as good as the registry that answers, and for some
sources no registry answers, while for others the registry that answers is
incomplete.** Both look identical on the record. The design's remedy — a
recorded human re-check interval — is therefore not a legal-sources feature;
it is a property every source needs, with the interval set by how much of
its status the machine can actually see.

## The legal case, as first written

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

0. **The re-check interval belongs to every source, not to legal ones.** A
   paper with a Crossref record gets a long interval (the registry watches
   most of its status); a legal document with no registry gets a short one;
   the interval and the last human check are on the record and on the page.
   Instance 3 says the long interval is not infinite: Crossref missed d1678.
1. **A recorded human re-check interval on every legal source**, stored on
   the source (`metadata.status_registry = none`, `metadata.recheck_interval`,
   `metadata.last_human_check`, `checked_by`), surfaced by the weekly job as a
   due-date, and marked on the page as "status last confirmed by a person on
   <date>" — the honest equivalent of the registry line a paper gets. Overdue
   is a marker, like a retraction.
2. **A hand-curated events table for source status**, under the same
   candidate-table discipline as `events.json` (primary URL verified by fetch,
   `reviewed_by`): `{source, event: quashed | reversed | superseded |
   appealed | withdrawn | corrected | retracted, date, by, url}`. CHRONOLOGY
   and STATUS_AT_PUBLISH already know how to consume events; they need a
   source for the ones no registry emits — the legal ones, and the
   corrections a registry missed. Migration 092 (authored) puts the first
   such correction on the editorial's row as `metadata.corrected_by`; the
   gate should read it as a status event, so the editorial carries the
   "corrected" marker exactly as a Crossref update-to would.
3. **Derivative reliance.** A source that rests on a legal determination (the
   notice on the GMC) inherits the determination's re-check, or the page says
   the dependence is unwatched. This is the harder half and may be out of
   scope for Phase 5; it should be named.
4. Migration 090 seeds the first row by hand: Walker-Smith v GMC carries
   `status_registry: none … human re-check interval required (Phase 5)` in
   its metadata.

Until then: any legal source on a published page is a source whose status the
system cannot learn changed, and the operator read should say so on each.

## The requirement that makes a curated status marker safe (not built)

A status marker sourced from hand-curated metadata (`corrected_by` on
Godlee's editorial, migration 092) must be **visibly distinguishable** from
one a registry supplied. A "corrected" badge a reader cannot tell apart from a
Crossref update-to is provenance collapse — the same shape as a model summary
stored as `content_text`: two things of different standing wearing one label.
Tonight the scope statement carries the correction in words and nothing is
built. When the marker is built it says where it came from ("recorded by the
publisher's registry" / "recorded by hand from the correction itself, sha …"),
in the badge, not in a tooltip.

## The twin gap: the citing-source anchor (write-up only, not built)

The same class of document — court judgments, regulatory determinations,
agency filings — has no registry to answer for its **identity** either.
`OPERATOR_SUPPLIED` refuses them at the door for that reason (the GMC
determination of 28 January 2010 and the 2002 Autism General Order were both
refused on 2026-09-15: nothing can say what the file for that identifier IS).
That is correct today and it leaves the GMC determination permanently outside
the corpus while a retraction notice that rests on it is inside.

The path such a document may one day take, and the only one: **both** of

1. **An independently resolved source that cites it**, with issuer, date and
   parties matching the file's own header. The Lancet notice (resolved through
   Crossref, admitted on its title) cites "the UK General Medical Council's
   Fitness to Practise Panel on Jan 28, 2010"; the hand-fetched determination's
   header reads "FITNESS TO PRACTISE PANEL HEARING 28 JANUARY 2010" and names
   Wakefield, Walker-Smith and Murch. The citing source stands in for the
   registry: it says what the document should be, the file has to match, and
   HEADING runs against that description exactly as it runs against a
   registry title. A citation that gives only a name and a year is not enough;
   issuer, date and parties, all three.
2. **A named human in `reviewed_by`**, who has read the file against the
   citation and signed the row — the `events.json` discipline, applied to a
   document rather than a date.

Both, never either. A citing source without a reviewer admits whatever file
happens to carry the right header; a reviewer without a citing source is the
operator asserting identity, which is the conclusion the design forbids the
operator to supply.

This is the twin of the no-status-registry gap above and belongs in the same
design: the class of document that no registry can vouch for at entry is the
class no registry can watch afterwards. A document admitted by anchor needs
the human re-check interval from the moment it enters.
