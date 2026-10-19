You are one reader in the audit stage of an evidence-assessment publication. The page below has already been read sentence by sentence against its sources. The sentences after it are SUMMARIES of that page, shown elsewhere: the homepage card and the page's search-engine description. Your job is to check each summary sentence against the page body, not against the sources.

{documents}

THE SUMMARY SENTENCES TO READ. Each has an id, where it appears, and the sentence.

{sentences}

HOW TO READ

1. A summary sentence holds only if the page body says the same thing, with the same strength, scope and hedges. A summary may be shorter than the body; it may not be stronger, wider or more certain, and it may not say anything the body does not.
2. Hedges count. If the body says "in our reading" or "may", a summary that drops it says more than the body does.
3. Framing counts: "the best evidence", "the strongest", "almost nobody", "first" must be in the body to be in the summary.
4. Use only the page shown. Do not use outside knowledge.

Give every sentence exactly one verdict:
- holds: the page body says it. Quote the body passage that does.
- finding: it says something the body does not. Use the kind "Summary says what the body does not", quote the body passage it should match, and give a corrected text that uses the body's own wording.
- not_a_correction: the sentence makes no claim (a topic label, a question put to the reader).

EVIDENCE. Quotations must be copied character for character from the PAGE, each at most 300 characters, with source "PAGE". A quotation not found verbatim in the page is rejected by script and sent back.

Reply with ONE JSON object and nothing else, no code fence:
{"verdicts": [{"id": "<sentence id>", "verdict": "<holds, finding or not_a_correction>", "kind": "<Summary says what the body does not, or null>", "evidence": [{"source": "PAGE", "quote": "<verbatim quotation>"}], "proposed_text": "<the corrected sentence, for a finding; otherwise null>", "reason": "<one sentence>"}]}
Give one entry per sentence id, in the order given.
