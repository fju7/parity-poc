// Parity Health — readable HTML "packet" export.
//
// buildHistoryPacketHTML(records) turns the on-device history records (bills and
// denials, as stored in localBillStore) into ONE self-contained, printable HTML
// document string. Openable in any browser and printable to PDF, so a person can
// forward it to an attorney. Every dynamic value is HTML-escaped.
//
// Field names used here are the REAL stored names (verified against
// localBillStore.saveBill/normalizeBill and App.saveDenialLocally):
//   - bill:   provider.name, serviceDate, summary.totalBilled (fallback
//             totals.total_billed), summary.flaggedItemCount/totalItemCount,
//             createdAt, line_items[{ cpt_code, revenue_code, description,
//             billed_amount }]  (normalized array — guaranteed field names)
//   - denial: record_type, provider_name, payer_name, claim_number, cpt_codes[],
//             date_of_service, billed_amount, denial_reason_plain,
//             denial_category, deadline_days_standard, appeal_deadline_hint,
//             appeal_drafted, letterText, analysis.weakness, createdAt

export function escapeHtml(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function fmtMoney(v) {
  if (v == null || v === "" || Number.isNaN(Number(v))) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(v));
}

function fmtDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Build a key-facts table from [label, value] pairs, omitting rows whose value
// is null/empty. Returns "" if nothing to show. Values are escaped here.
function factsTable(rows) {
  const body = rows
    .filter(([, v]) => v != null && v !== "")
    .map(
      ([label, v]) =>
        `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(v)}</td></tr>`
    )
    .join("");
  if (!body) return "";
  return `<table class="facts">${body}</table>`;
}

function denialSection(r) {
  const a = r.analysis || {};
  const cpts = Array.isArray(r.cpt_codes)
    ? r.cpt_codes.filter(Boolean).join(", ")
    : "";

  let deadline = null;
  if (typeof r.deadline_days_standard === "number") {
    deadline = `within ${r.deadline_days_standard} days`;
  } else if (r.appeal_deadline_hint) {
    deadline = r.appeal_deadline_hint;
  }

  const facts = factsTable([
    ["Provider", r.provider_name],
    ["Payer", r.payer_name],
    ["Claim #", r.claim_number],
    ["Procedure code(s)", cpts],
    ["Service date", r.date_of_service],
    ["Billed amount", fmtMoney(r.billed_amount)],
    ["Appeal deadline", deadline],
    ["Analyzed", fmtDate(r.createdAt)],
  ]);

  const reason = r.denial_reason_plain || r.denial_category || "—";

  let html = `<section class="record">`;
  html += `<h2>Insurance Denial &mdash; ${escapeHtml(
    r.payer_name || "Unknown payer"
  )}</h2>`;
  html += facts;
  html += `<h3>Why the claim was denied</h3><p>${escapeHtml(reason)}</p>`;
  if (a && a.weakness) {
    html += `<h3>Weakness in their reasoning</h3><p>${escapeHtml(
      a.weakness
    )}</p>`;
  }
  if (typeof r.letterText === "string" && r.letterText.trim() !== "") {
    html += `<h3>Drafted appeal letter</h3><div class="letter">${escapeHtml(
      r.letterText
    )}</div>`;
  } else {
    html += `<p><em>No appeal letter has been drafted for this denial yet.</em></p>`;
  }
  html += `</section>`;
  return html;
}

function billSection(r) {
  const provider = r.provider || {};
  const summary = r.summary || {};
  const totals = r.totals || {};
  const providerName = provider.name || "Unknown provider";
  const totalBilled = fmtMoney(
    summary.totalBilled != null ? summary.totalBilled : totals.total_billed
  );

  const facts = factsTable([
    ["Provider", provider.name],
    ["Service date", r.serviceDate],
    ["Total billed", totalBilled],
    ["Analyzed", fmtDate(r.createdAt)],
  ]);

  const items = Array.isArray(r.line_items) ? r.line_items : [];
  let itemsHtml;
  if (items.length === 0) {
    itemsHtml = `<p><em>No line items recorded.</em></p>`;
  } else {
    const rows = items
      .map((li) => {
        const code = li.cpt_code || li.revenue_code || "";
        const desc = li.description || "";
        const amt = fmtMoney(li.billed_amount) || "";
        return `<tr><td>${escapeHtml(code)}</td><td>${escapeHtml(
          desc
        )}</td><td class="num">${escapeHtml(amt)}</td></tr>`;
      })
      .join("");
    itemsHtml = `<table class="items"><thead><tr><th>Code</th><th>Description</th><th class="num">Amount</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  let flaggedLine = "";
  if (
    typeof summary.flaggedItemCount === "number" &&
    typeof summary.totalItemCount === "number"
  ) {
    flaggedLine = `<p>Flagged: ${escapeHtml(summary.flaggedItemCount)} of ${escapeHtml(
      summary.totalItemCount
    )} items</p>`;
  }

  let html = `<section class="record">`;
  html += `<h2>Medical Bill &mdash; ${escapeHtml(providerName)}</h2>`;
  html += facts;
  html += `<h3>Line items</h3>`;
  html += itemsHtml;
  html += flaggedLine;
  html += `</section>`;
  return html;
}

const STYLE = `
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1a1a1a; line-height: 1.5; max-width: 800px; margin: 0 auto; padding: 32px 20px; }
h1 { font-size: 24px; color: #1B3A5C; margin: 0 0 4px; }
h2 { font-size: 18px; color: #1B3A5C; margin: 0 0 12px; border-bottom: 2px solid #0D7377; padding-bottom: 6px; }
h3 { font-size: 13px; color: #444; margin: 18px 0 6px; text-transform: uppercase; letter-spacing: 0.03em; }
p { margin: 6px 0; }
.meta { color: #555; font-size: 13px; margin: 0 0 2px; }
.privacy { color: #777; font-size: 12px; font-style: italic; margin: 0 0 24px; }
.record { margin: 0 0 36px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 14px; }
table.facts th { text-align: left; width: 200px; color: #555; font-weight: 600; vertical-align: top; }
table.facts th, table.facts td { border: 1px solid #ddd; padding: 6px 10px; }
table.items th, table.items td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
table.items th { background: #f5f5f5; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.letter { white-space: pre-wrap; font-family: Georgia, "Times New Roman", serif; border: 1px solid #ccc; padding: 16px; background: #fafafa; border-radius: 4px; margin: 8px 0; }
@media print {
  body { padding: 0; }
  .record { page-break-inside: avoid; }
  h2 { page-break-after: avoid; }
}
`;

export function buildHistoryPacketHTML(records) {
  const list = Array.isArray(records) ? records : [];
  const sections = list
    .map((r) =>
      r && r.record_type === "denial" ? denialSection(r) : billSection(r)
    )
    .join("\n");

  const exportDate = new Date().toLocaleDateString();
  const count = list.length;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Parity Health &mdash; Records Export</title>
<style>${STYLE}</style>
</head>
<body>
<h1>Parity Health &mdash; Records Export</h1>
<p class="meta">Exported ${escapeHtml(exportDate)} &middot; ${escapeHtml(count)} record${
    count === 1 ? "" : "s"
  }</p>
<p class="privacy">This document contains personal health information. You control where it goes.</p>
${count === 0 ? "<p><em>No records to export.</em></p>" : sections}
</body>
</html>`;
}
