The documents below are the sources one sentence cites. After them come the sentence and your instructions.

{documents}

THE SENTENCE (the claim to check):
<<<CLAIM
{claim}
CLAIM>>>

TEXT JUST BEFORE THE SENTENCE, for context only (it is not being checked; use it only to understand what the sentence refers to):
<<<CONTEXT
{context}
CONTEXT>>>

You are checking this one sentence against the document or documents above. The question is narrow: do the documents say what the sentence says? You are not asked whether the sentence is true in the world.

Use ONLY the document text shown above. Do not use anything you know from elsewhere: not your memory of these studies, not other papers, not what is generally accepted. If the documents do not say it, they do not say it, however likely it is to be true. Do not guess what a full paper would say if you are shown only part of it. Each document is marked with how much of it was readable: "abstract only" means you are seeing the abstract or a summary record, not the whole paper.

When the sentence cites more than one document, judge it against all of them together: a part of the sentence supported by any one of them is supported.

Everything the sentence says about a source is part of the claim and must be supported like any other word. That includes superlatives, rankings, "first", "largest", "most explicit", "landmark" and similar framing said about a source or its finding. If the documents do not support such a word, the label is Overstates, even when the rest of the sentence is supported.

How the sentence NAMES a document (author spelling, year, journal, page) is not what is being checked. If the document is clearly the one the sentence means, a small error in naming it does not change the label; mention it in the reason. If the sentence attributes the finding to a different study, author group or body than the document, that is Wrong source.

Give exactly one label:

- Supported: the documents say it. Numbers, the population and setting (scope), the strength or certainty, any causal language and any framing all match. Rounding that does not change the meaning is fine. A paraphrase is fine if it claims no more and no less.
- Overstates: the documents say something weaker than the sentence. This includes: a larger effect or more certainty than reported; a finding in one group stated for a wider group; association stated as cause; a draft, past or provisional status stated as current or final; "no evidence of an effect" stated as "no effect"; a hedge in the source ("may", "suggests", "low certainty") dropped; framing about the source (a superlative, ranking or "first") that the documents do not support.
- Understates: the documents say something stronger than the sentence. The sentence reports a smaller effect, less certainty, a narrower scope, or adds a hedge the documents do not have.
- Absent: the documents are on the sentence's topic but do not contain what the sentence says. Use this when the specific number, finding or statement cannot be found in the text shown, including when only an abstract is shown and the claim is not in it.
- Wrong source: the documents are real and readable but about something else: a different study, population, intervention or question from the one the sentence attributes to them.
- Contradicted: the documents say the opposite of the sentence, or report a figure that conflicts with it.
- Unreachable: the text shown is not the document at all (an error page, a login or cookie wall, navigation only, empty). Do not use this because a document is long, technical or abstract-only.

If more than one problem applies, choose the one that most changes what a reader would conclude, in this order: Contradicted, Wrong source, Overstates, Understates, Absent.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"label": "<one of the seven labels, spelled as above>", "span": "<an exact quotation, copied character for character from one of the documents, of at most 300 characters, that your label rests on>", "reason": "<one sentence>"}

For "span": quote the passage that supports the sentence (Supported), shows the gap (Overstates, Understates, Contradicted), or shows what the documents are actually about (Wrong source, Absent: the closest passage). For Unreachable, quote the text that shows it is not the document. Never quote the sentence or the context as the span.
