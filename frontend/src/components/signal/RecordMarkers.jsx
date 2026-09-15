/**
 * What the frozen publication record and the re-checks say, on the page.
 *
 * Phase 3 design §4. Nothing here removes a claim or re-scores anything; a
 * marker adds a sentence that carries both dates. The wording is the
 * approved draft, verbatim. `retracted` is visually distinct from every other
 * marker -- "we could not confirm this" and "the source was withdrawn" are
 * different in kind.
 */

const fmt = (iso) =>
  iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";

const NOTE = "rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 leading-snug mt-2";
const ACCESS = "rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-xs text-gray-700 leading-snug mt-2";
const INFO = "rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-700 leading-snug mt-2";
const RETRACTED = "rounded-lg border-2 border-red-600 bg-red-50 px-3 py-2 text-xs text-red-900 leading-snug mt-2";

/** The registry's retraction date for a source, from the status events frozen at publication. */
const retractionDate = (st) => {
  const ev = (st?.events || []).find((e) => e.type === "retraction" && e.date);
  if (!ev) return null;
  const [y, m, d] = String(ev.date).split("-").map(Number);
  return fmt(new Date(y, (m || 1) - 1, d || 1).toISOString());
};

/** "Wakefield et al., The Lancet, 1998" from what the registry told us. */
const cite = (src) => {
  const au = src?.first_author ? `${src.first_author} et al.` : null;
  const yr = src?.published?.[0] || null;
  return [au, src?.container, yr].filter(Boolean).join(", ");
};

/** The line under the topic title. */
export function TopicLine({ publication, recheck }) {
  if (!publication) return null;
  const s = publication.summary || {};
  const idOnly = (s.claims?.by_support || {}).IDENTITY_ONLY || 0;
  const shown = (publication.supported_claim_ids || []).length;
  // Two facts, stated separately, so the header never contradicts a marker
  // below it: what was already known at publication (a source retracted
  // before we published) and what the re-checks have found since.
  const retractedAtPublication = new Set(
    Object.entries(publication.status || {}).filter(([, st]) => st?.verdict === "retracted").map(([sid]) => sid)
  ).size;
  const newlyFlagged = new Set((recheck?.flags || []).filter((f) => f.scope === "source" && (f.outcome !== "unreachable" || f.reader_marker)).map((f) => f.source_id)).size;
  return (
    <p className="text-xs text-gray-500 mt-1">
      Sources checked and frozen on {fmt(publication.published_at)}
      {" · "}{retractedAtPublication} source{retractedAtPublication === 1 ? "" : "s"} retracted before publication
      {" · "}{newlyFlagged} source{newlyFlagged === 1 ? "" : "s"} newly flagged since {fmt(publication.published_at)}
      {recheck?.run_at ? <> (last re-check {fmt(recheck.run_at)})</> : null}
      {" · "}{idOnly} of {shown} claims source-confirmed only (wording not machine-checked)
      {" — see markers below. "}
      <a href="/methodology" className="text-[#0D7377] hover:underline">What this means →</a>
    </p>
  );
}

/** Markers for one claim: its support level at publication, then any re-check flag. */
export function ClaimMarkers({ claimId, publication, recheck }) {
  if (!publication) return null;
  const support = publication.support?.[claimId];
  const flags = (recheck?.flags || []).filter((f) => f.scope === "claim" && f.claim_id === claimId);
  const pub = fmt(publication.published_at);
  // Subject links to a source retracted before publication: information, not doubt.
  // (A SUPPORT link to such a source is refused at publish and never reaches here.)
  const subjectOfRetracted = (publication.links?.[claimId] || []).filter(
    (l) => l.role === "subject" && publication.status?.[l.source_id]?.verdict === "retracted"
  );
  return (
    <>
      {subjectOfRetracted.map((l, i) => {
        const src = publication.sourceMeta?.[l.source_id] || {};
        const when = retractionDate(publication.status?.[l.source_id]);
        return (
          <div key={"subj" + i} className={INFO}>
            <span className="font-semibold">About a retracted paper. </span>
            The study this claim describes{cite(src) ? <> — {cite(src)} —</> : null} was retracted by the journal
            {when ? ` on ${when}` : ""} (Crossref). The claim reports what that paper did or said; its retraction is
            part of the record, not a doubt about this claim.
          </div>
        );
      })}
      {support === "IDENTITY_ONLY" && (
        <div className={NOTE}>
          <span className="font-semibold">Source confirmed; wording not machine-checked. </span>
          We verified that the cited document is the one named and fetched its text. This claim carries no figure
          or quotation we could match against it, so its wording rests on the extraction, not on a check.
        </div>
      )}
      {flags.map((f, i) => {
        const when = fmt(f.observed_at);
        if (f.outcome === "binding_lost") {
          const figs = (f.figures || []).join(", ");
          return (
            <div key={i} className={NOTE}>
              Re-checked {when}: we could no longer match the figure this claim was published on
              {figs ? ` (${figs})` : ""} in the cited source. The claim is shown as it was published. That may
              mean the source changed, or that our reading of it did — either way, treat the figure as
              unconfirmed until we have re-read the source ourselves.
            </div>
          );
        }
        if (f.outcome === "status_changed" && f.verdict === "retracted") {
          return (
            <div key={i} className={RETRACTED}>
              <span className="font-bold uppercase tracking-wide">Retracted source. </span>
              This claim rests on a paper the journal retracted after we published on {pub} (Crossref, observed {when}).
              The claim is shown as published and marked; it should not be relied on until we have reviewed the retraction.
            </div>
          );
        }
        if (f.outcome === "status_changed") {
          return (
            <div key={i} className={NOTE}>
              <span className="font-semibold capitalize">{f.verdict.replace(/_/g, " ")}. </span>
              A source this claim rests on changed status ({f.verdict.replace(/_/g, " ")}), observed {when}; it was
              checked on {pub}. We have not yet reviewed what changed.
            </div>
          );
        }
        return null;
      })}
    </>
  );
}

/** Markers for one source entry: status at publication, then re-check outcomes. */
export function SourceMarkers({ sourceId, publication, recheck }) {
  if (!publication) return null;
  const st = publication.status?.[sourceId];
  const flags = (recheck?.flags || []).filter((f) => f.scope === "source" && f.source_id === sourceId);
  const pub = fmt(publication.published_at);
  const out = [];
  if (st?.verdict === "retracted") {
    // Already retracted at publication. Only claims ABOUT it can be on the page
    // (support links were refused at publish), so this is information, not warning.
    const when = retractionDate(st);
    out.push(
      <div key="ret" className={INFO}>
        <span className="font-semibold">Retracted paper. </span>
        Crossref records a retraction of this source{when ? ` dated ${when}` : ""}. It was already retracted when this
        page was published on {pub}. It is listed because a claim on this page describes it; nothing on this page
        rests on it as evidence.
      </div>
    );
  } else if (st?.verdict === "superseded") {
    out.push(
      <div key="sup" className={NOTE}>
        <span className="font-semibold">Superseded. </span>A newer version of this source exists in the registry. The
        version cited here is the one checked on {pub}.
      </div>
    );
  } else if (st?.verdict === "corrected") {
    out.push(
      <div key="cor" className={NOTE}>
        <span className="font-semibold">Corrected. </span>The publisher has issued a correction to this source. The
        figures on this page were checked on {pub}; we have not yet reviewed what the correction changed.
      </div>
    );
  }
  for (const f of flags) {
    const when = fmt(f.observed_at);
    if (f.outcome === "unreachable" && f.reader_marker) {
      out.push(
        <div key={"u" + when} className={ACCESS}>
          <span className="font-semibold">Could not re-check. </span>We were unable to retrieve this source on {when}
          (and on the previous check). This says nothing about the claim — it says we could not confirm it again.
          Last confirmed {pub}.
        </div>
      );
    } else if (f.outcome === "status_changed" && f.verdict === "retracted") {
      const ev = (f.events || []).find((e) => e.type === "retraction" && e.date);
      out.push(
        <div key={"r" + when} className={RETRACTED}>
          <span className="font-bold uppercase tracking-wide">Retracted. </span>Crossref records a retraction of this
          source{ev?.date ? ` dated ${ev.date}` : ""}, observed {when}. Claims on this page rested on it when published
          on {pub}. We have not removed them; we have marked them.
        </div>
      );
    } else if (f.outcome === "status_changed") {
      out.push(
        <div key={"s" + when} className={NOTE}>
          <span className="font-semibold capitalize">{f.verdict.replace(/_/g, " ")}. </span>Observed {when}; this
          source was checked on {pub}. We have not yet reviewed what changed.
        </div>
      );
    } else if (f.outcome === "binding_lost") {
      out.push(
        <div key={"b" + when} className={NOTE}>
          Re-checked {when}: we could no longer match this source's title to the registry's record as we did on {pub}.
          Treat attributions to it as unconfirmed until we have re-read it ourselves.
        </div>
      );
    }
  }
  return out.length ? <>{out}</> : null;
}
