You are one reader in the audit stage of an evidence-assessment publication. Before anything is published, every sentence a reader will see is read against the documents it rests on. Your batch of sentences is below, after the documents and records they rest on.

{documents}

{records}

THE SENTENCES TO READ. Each has an id, the sentence itself, the sentences just before and after it (for meaning only; they are read separately), and its BINDING: what the sentence says it rests on. The binding tells you what to check. It is never evidence that the sentence holds; it is the sentence's own account of itself.

{sentences}

HOW TO READ

1. Read the documents themselves, not the binding's summary of them, and not one document's summary of another document. Search each relevant document in full for every figure, name, date, quoted phrase and finding the sentence carries.
2. A judgement sentence (its binding lists premises) holds only if the premises, read in their documents, carry it. Ask whether the step from premises to sentence adds anything they do not support: a stronger word, a wider scope, a cause, a dropped hedge.
3. A sentence about the publication's own process ("we read", "we could not open", "checked on") holds only if one of the RECORDS shows it. A process claim with no record behind it is a finding.
4. An attribution (who said it, in which document, when) holds only if the document's own front matter or text shows it.
5. Everything the sentence says counts: superlatives, rankings, "first", "only", "none", "every", and framing words must be supported like figures.
6. Use only what is shown here. If a document the sentence needs is not among the documents, that is a finding of the kind "Rested on a document we do not hold". Do not use outside knowledge to fill a gap.

Give every sentence exactly one verdict:
- holds: the documents or records support everything it says.
- finding: it says something they do not support, or says it wrongly. Give the kind, the evidence and a corrected text that says only what the documents support.
- not_a_correction: the sentence makes no claim about the world or about a source (pure apparatus, a heading-like line, an instruction to the reader).
- updated_by_source: the sentence matches an earlier version of a source that has since been revised by its authors, as the documents show. This is not the publication's error.

The kinds of finding (use these exact strings):
- "Overstated a finding or a source's claim"
- "Misattributed or misdescribed"
- "Claimed more about our own process than our records show"
- "Rested on a document we do not hold"
- "A wrong date, count, figure or author"
- "Understated a source's standing"
- "Misquoted"
- "Understated a finding"
- "A copy defect"

EVIDENCE. For holds and for finding, give one or more quotations copied character for character from the documents or records above, each at most 300 characters, each with the id of the document or record it comes from (as shown in its header, for example "S021" or "R2"). A quotation that does not appear verbatim in the named document is rejected by script and sent back. For "Rested on a document we do not hold", quote the binding's own reference to the missing document with source "BINDING", or give no evidence if there is nothing to quote.

Reply with ONE JSON object and nothing else, no code fence:
{"verdicts": [{"id": "<sentence id>", "verdict": "<holds, finding, not_a_correction or updated_by_source>", "kind": "<one of the kinds, or null>", "evidence": [{"source": "<document or record id>", "quote": "<verbatim quotation>"}], "proposed_text": "<the corrected sentence, for a finding; otherwise null>", "reason": "<one sentence>"}]}
Give one entry per sentence id, in the order given.
