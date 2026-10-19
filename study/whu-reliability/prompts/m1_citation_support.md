You are checking one sentence against one document. The question is narrow: does the document shown below say what the sentence says? You are not asked whether the sentence is true in the world.

Use ONLY the document text shown between the DOCUMENT markers. Do not use anything you know from elsewhere: not your memory of this study, not other papers, not what is generally accepted. If the document does not say it, it does not say it, however likely it is to be true. Do not guess what the full paper would say if you are shown only part of it.

THE SENTENCE (the claim to check):
<<<CLAIM
{claim}
CLAIM>>>

TEXT JUST BEFORE THE SENTENCE, for context only (it is not being checked; use it only to understand what the sentence refers to):
<<<CONTEXT
{context}
CONTEXT>>>

THE DOCUMENT the sentence cites. Readable extent: {extent}. If this says "abstract only", you are seeing the abstract or a summary record, not the whole paper.
<<<DOCUMENT
{document}
DOCUMENT>>>

Give exactly one label:

- Supported: the document says it. Numbers, the population and setting (scope), the strength or certainty, and any causal language all match. Rounding that does not change the meaning is fine. A paraphrase is fine if it claims no more and no less.
- Overstates: the document says something weaker than the sentence. This includes: a larger effect or more certainty than the document reports; a finding in one group stated for a wider group; association stated as cause; a draft, past or provisional status stated as current or final; "no evidence of an effect" stated as "no effect"; a hedge in the document ("may", "suggests", "low certainty") dropped.
- Understates: the document says something stronger than the sentence. The sentence reports a smaller effect, less certainty, a narrower scope, or adds a hedge the document does not have.
- Absent: the document is on the sentence's topic but does not contain what the sentence says. Use this when the specific number, finding or statement cannot be found in the text shown, including when only the abstract is shown and the claim is not in it.
- Wrong source: the document is real and readable but about something else: a different study, population, intervention or question from the one the sentence attributes to it.
- Contradicted: the document says the opposite of the sentence, or reports a figure that conflicts with it.
- Unreachable: the text between the DOCUMENT markers is not the document at all (an error page, a login or cookie wall, navigation only, empty). Do not use this because the document is long, technical or abstract-only.

How the sentence NAMES the document (author spelling, year, journal, page) is not what is being checked. If the document is clearly the one the sentence means, a small error in naming it does not change the label; mention it in the reason. If the sentence attributes the finding to a different study, author group or body than the document, that is Wrong source.

If more than one problem applies, choose the one that most changes what a reader would conclude, in this order: Contradicted, Wrong source, Overstates, Understates, Absent.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"label": "<one of the seven labels, spelled as above>", "span": "<an exact quotation, copied character for character from the DOCUMENT, of at most 300 characters, that your label rests on>", "reason": "<one sentence>"}

For "span": quote the passage that supports the sentence (Supported), shows the gap (Overstates, Understates, Contradicted), or shows what the document is actually about (Wrong source, Absent: the closest passage). For Unreachable, quote the text that shows it is not the document. Never quote the sentence or the context as the span.
