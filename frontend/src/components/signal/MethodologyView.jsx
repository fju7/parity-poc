import { Link } from "react-router-dom";

// Every process claim on this page names the code that performs it, in the
// `where` fields below and in docs/signal-methodology-claims-2026-09-15.md.
// A sentence with no code behind it does not belong here. Rewritten
// 2026-09-15 (Phase 4 of the verification plan, methodology page only): the
// previous page described a scoring rubric as if it were the method, carried
// weights that did not match score_claims.py, and did not mention the gates
// that decide what is shown at all.

import { WEIGHTS, CATEGORY_THRESHOLDS } from "../../lib/signalScoring";

const GATES = [
  {
    name: "Every source is resolved and fetched",
    where: "backend/verify/literature.py, verify/generic.py, verify/publish.py",
    text:
      "Before a topic is published, each source's identifier (DOI, PubMed ID, trial number, or URL) is looked up in the registry that issues it — Crossref, Europe PMC, ClinicalTrials.gov — and the document itself is retrieved. A source whose identifier resolves to nothing, or to a different paper, or whose text cannot be retrieved, is withheld from the page, and the publication record notes it with the reason.",
  },
  {
    name: "Every figure in a claim is found in its source",
    where: "backend/verify/bind.py (FIGURE, SPAN, HEADING, CHRONOLOGY), verify/publish.py",
    text:
      "A claim that states a number must have that number present in the fetched text of a source it cites; a claim that quotes must quote verbatim; and a source cannot support a claim about something that happened after it was published. Claims that fail are withheld from the page. Claims whose sources resolved but which state no figure and quote no phrase are shown and marked \"Source identified; not checked against it\": the cited document is the one named and its text is held, but nothing in the claim could be matched against that text, so the page has not checked that the document says what the claim says. The topic header counts these as claims that could not be matched against their sources.",
  },
  {
    name: "Retractions and corrections are checked",
    where: "backend/verify/status.py; backend/scripts/recheck_topic.py; .github/workflows/verify-gates.yml",
    text:
      "At publication, and every week afterwards, each source's registry record is checked for a retraction, correction or expression of concern. Monthly, every source is fetched again and every binding re-run. A change marks the page; it never silently un-publishes it.",
  },
  {
    name: "The record is frozen and shown",
    where: "backend/verify/publish.py (the publication record); frontend/src/components/signal/RecordMarkers.jsx",
    text:
      "What each claim rested on at the moment of publication — which source, which binding, what the registry said — is written to a record that is stored and displayed. The markers on the topic page (\"withheld\", \"Source identified; not checked against it\", \"retracted before publication\") come from that record, not from a model.",
  },
  {
    name: "The prose is checked against the claims",
    where: "backend/scripts/signal/prose_gate.py; backend/verify/policy.py",
    text:
      "The plain-language summary under each claim, the consensus text for each category, the overall narrative and the glossary are written by a model. Before any of it is stored, its figures and the bodies it names are checked against the claims and sources it was given. A summary that adds a number or an authority the claims do not contain is not shown; the claim is shown without it.",
  },
];

const DIMENSIONS = [
  {
    name: "Source quality",
    key: "source_quality",
    description:
      "How authoritative the model judges the claim's sources to be, on a 1–5 scale (5: regulatory label or major peer-reviewed trial; 1: opinion or unreviewed preprint). This is scored from the source's title, type label and publication date. The type label was itself written by a model when the source was gathered; it is not derived from the fetched document. Treat this dimension as the model's reading, not a verified property of the source.",
  },
  {
    name: "Data support",
    key: "data_support",
    description:
      "Whether the claim rests on quantitative results (5: specific statistics with intervals; 1: a purely qualitative assertion).",
  },
  {
    name: "Reproducibility",
    key: "reproducibility",
    description:
      "Whether the finding has been confirmed by independent sources (5: multiple independent trials; 1: preliminary or contested).",
  },
  {
    name: "Consensus",
    key: "consensus",
    description:
      "What proportion of the credible sources in the topic agree with the claim (5: universal; 1: a minority position).",
  },
  {
    name: "Recency",
    key: "recency",
    description:
      "How recent the evidence is, from the publication date (5: within the last year; 1: more than six years old).",
  },
  {
    name: "Rigor",
    key: "rigor",
    description:
      "Methodological quality as the model reads it (5: large pre-registered trial; 1: anecdotal or flawed).",
  },
];

function pct(w) {
  return `${Math.round(w * 100)}%`;
}

export default function MethodologyView() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 font-[Arial,sans-serif]">
      <Link
        to="/signal"
        className="text-sm text-[#0D7377] hover:underline mb-4 inline-flex items-center gap-1 min-h-[44px]"
      >
        &larr; Back to Signal
      </Link>

      <h1 className="text-2xl font-bold text-white mb-2">How a topic is built</h1>
      <p className="text-gray-300 text-sm leading-relaxed mb-8">
        Two different things happen to every claim on Parity Signal, and they
        should not be confused. Some things are <strong className="text-white">checked</strong> — by
        code, against a registry and a fetched document, and a claim that fails is
        not shown. Other things are <strong className="text-white">scored</strong> — by a
        language model, on a 1–5 scale, and the score is a reading, not a
        verification. This page says which is which.
      </p>

      {/* Gates */}
      <h2 className="text-lg font-bold text-white mb-1">What is checked</h2>
      <p className="text-sm text-gray-400 leading-relaxed mb-4">
        No model takes part in any of these. Each is a comparison of strings
        against a document the system retrieved.
      </p>
      <div className="space-y-4 mb-10">
        {GATES.map((g) => (
          <div key={g.name} className="border border-white/[0.1] rounded-xl p-4">
            <h3 className="font-bold text-[#f1f5f9] text-sm mb-1">{g.name}</h3>
            <p className="text-sm text-gray-300 leading-relaxed">{g.text}</p>
          </div>
        ))}
      </div>

      {/* Scores */}
      <h2 className="text-lg font-bold text-white mb-1">What is scored</h2>
      <p className="text-sm text-gray-400 leading-relaxed mb-4">
        A language model reads each claim with its sources and assigns six
        integer scores from 1 to 5. The composite is computed in code as a
        weighted average and mapped to a category. The scores decide how a
        claim is <em>ranked and labelled</em>; they never decide whether it is
        shown — that is the checks above.
      </p>
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 mb-6">
        <h3 className="text-sm font-bold text-[#1B3A5C] mb-2">Composite</h3>
        <div className="bg-white rounded-lg p-3 font-mono text-xs text-[#1B3A5C] leading-loose border border-gray-100 overflow-x-auto">
          <div className="min-w-0">
            composite =<br />
            {Object.entries(WEIGHTS).map(([k, w], i) => (
              <span key={k}>
                &nbsp;&nbsp;{i === 0 ? "" : "+ "}({k} × {w.toFixed(2)})<br />
              </span>
            ))}
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          {CATEGORY_THRESHOLDS.map(([name, t], i) => (
            <span key={name}>
              {i > 0 ? " · " : ""}
              <strong>{name}</strong> ≥ {t.toFixed(1)}
            </span>
          ))}
        </p>
      </div>
      <div className="space-y-4 mb-10">
        {DIMENSIONS.map((dim) => (
          <div key={dim.key} className="border border-white/[0.1] rounded-xl p-4">
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-[#f1f5f9] text-sm">{dim.name}</h3>
              <span className="text-xs font-semibold text-[#0D7377] bg-[#0D7377]/10 px-2 py-0.5 rounded-full">
                Weight: {pct(WEIGHTS[dim.key])}
              </span>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">{dim.description}</p>
          </div>
        ))}
      </div>

      {/* Consensus mapping */}
      <h2 className="text-lg font-bold text-white mb-1">How a category's consensus is read</h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">
        Claims are grouped by category. For each category a model reads all of
        the category's claims and assigns one status, using a written decision
        order: conflicting credible evidence is <em>debated</em>; thin evidence
        is <em>uncertain</em>; undisputed evidence is <em>consensus</em>. This
        reading is not reproducible run to run, and the same claims have been
        read differently on different days. The pipeline can therefore run the
        reading several times and store the status the runs agree on with the
        agreement rate; the first published topic was read once, and its record
        says so. A model reading of consensus is a reading, not a count.
      </p>
      <div className="space-y-2 mb-10">
        {[
          { status: "Consensus", dot: "bg-emerald-400", desc: "The category's claims do not dispute one another." },
          { status: "Debated", dot: "bg-amber-400", desc: "Credible claims conflict. The arguments on each side are shown, with the claims they rest on where the model attributed them." },
          { status: "Uncertain", dot: "bg-gray-400", desc: "Too little evidence to read a direction." },
        ].map((s) => (
          <div key={s.status} className="flex items-start gap-2.5 py-2">
            <span className={`w-2.5 h-2.5 rounded-full ${s.dot} shrink-0 mt-1`} />
            <div>
              <span className="text-sm font-bold text-[#f1f5f9]">{s.status}</span>
              <p className="text-sm text-gray-300">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* What this is not */}
      <h2 className="text-lg font-bold text-white mb-1">What this does not do</h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-10">
        The checks establish that a source exists, that it was retrieved, and
        that it contains what a claim says it contains. They do not establish
        that the right sources were chosen, that contested findings were fairly
        weighted, or that a claim is true. A score is a model's judgement about
        the evidence as presented to it. Nothing here is a clinical
        recommendation.
      </p>

      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500 leading-relaxed">
        <strong className="text-gray-700">Disclaimer:</strong> Parity Signal
        summarises published research. Scores are generated by language models
        and reflect the evidence as read, not clinical recommendations. Always
        consult healthcare professionals for medical decisions. Sources are
        re-checked on a schedule; a page marks changes rather than hiding them.
      </div>
    </div>
  );
}
