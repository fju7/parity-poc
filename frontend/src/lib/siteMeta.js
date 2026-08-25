/**
 * Per-product page metadata — the single source of truth.
 *
 * Consumed twice:
 *   1. At build time by scripts/generate-host-html.mjs, which stamps these
 *      values into a static HTML file per host. This is the copy that crawlers
 *      and link-preview bots (Slack, LinkedIn, X, iMessage) actually read,
 *      because they never execute our JavaScript.
 *   2. At runtime by main.jsx, so client-side navigation keeps the tab title
 *      and meta tags in sync.
 *
 * Both must agree, which is why they import the same object. Before this file
 * existed the map lived only in main.jsx and ran after hydration, so every
 * shared link previewed with index.html's hardcoded fallback — Parity Health's
 * bill-analysis copy, on all six products.
 *
 * Adding a new host (including moving a product to its own apex domain) means
 * adding an entry here and a matching rewrite in vercel.json.
 */

export const DEFAULT_KEY = "main";

/** Product key -> metadata. `url` is the canonical origin for that product. */
export const SITE_META = {
  main: {
    title: "CivicScale — Institutional Benchmark Infrastructure",
    description:
      "Benchmark infrastructure for healthcare pricing and evidence. Independent analysis built on public CMS data and peer-reviewed research.",
    url: "https://civicscale.ai",
  },
  health: {
    title: "Parity Health — Understand Your Medical Bill",
    description:
      "Upload your medical bill, EOB, or denial letter. See what you should actually owe — powered by CMS benchmark data.",
    url: "https://health.civicscale.ai",
  },
  employer: {
    title: "Parity Employer — Independent Claims Analytics",
    description:
      "Benchmark your health plan against CMS data. Identify overpayments before renewal. No TPA required.",
    url: "https://employer.civicscale.ai",
  },
  broker: {
    title: "Parity Broker — Independent Benchmarking for Benefits Brokers",
    description:
      "Give every client independent benchmark data. Generate CAA-compliant data request letters. Free for up to 10 clients.",
    url: "https://broker.civicscale.ai",
  },
  provider: {
    title: "Parity Provider — Contract Integrity and Denial Intelligence",
    description:
      "Audit your remittance files against contracted rates. Identify underpayments and denial patterns automatically.",
    url: "https://provider.civicscale.ai",
  },
  billing: {
    title: "Parity Billing — RCM Analytics Across Your Practice Portfolio",
    description:
      "Batch 835 ingestion, payer benchmarking, and cross-practice escalation tracking for billing companies.",
    url: "https://billing.civicscale.ai",
  },
  signal: {
    title: "Parity Signal — What the Evidence Actually Says",
    description:
      "Every claim on a contested topic, scored across six dimensions of credibility, with the sources shown and the disagreements named.",
    url: "https://signal.civicscale.ai",
  },
};

/** Hosts that should serve each product. Staging hosts are marked noindex. */
export const HOST_MAP = {
  "civicscale.ai": { key: "main", index: true },
  "www.civicscale.ai": { key: "main", index: true },
  "health.civicscale.ai": { key: "health", index: true },
  "employer.civicscale.ai": { key: "employer", index: true },
  "broker.civicscale.ai": { key: "broker", index: true },
  "provider.civicscale.ai": { key: "provider", index: true },
  "billing.civicscale.ai": { key: "billing", index: true },
  "signal.civicscale.ai": { key: "signal", index: true },
  "staging-health.civicscale.ai": { key: "health", index: false },
  "staging-employer.civicscale.ai": { key: "employer", index: false },
  "staging-broker.civicscale.ai": { key: "broker", index: false },
  "staging-provider.civicscale.ai": { key: "provider", index: false },
  "staging-billing.civicscale.ai": { key: "billing", index: false },
  "staging-signal.civicscale.ai": { key: "signal", index: false },
};

/** Resolve a hostname to its product key and indexing policy. */
export function resolveHost(hostname) {
  return HOST_MAP[hostname] || { key: DEFAULT_KEY, index: false };
}

/** Metadata for a hostname, never undefined. */
export function metaForHost(hostname) {
  const { key, index } = resolveHost(hostname);
  return { key, index, ...(SITE_META[key] || SITE_META[DEFAULT_KEY]) };
}
