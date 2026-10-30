You are drafting an answer key: the main conclusions of one expert review, stated exactly as the review states them. The key will be used to judge other people's answers to the research question below, so it must say what the review concludes, no more and no less.

THE RESEARCH QUESTION:
<<<QUESTION
{question}
QUESTION>>>

WHAT THE REVIEW IS: {review}

THE REVIEW'S TEXT (the only material you may use):
{documents}

Instructions.
1. Use ONLY the review's text above. Do not use anything you know from elsewhere, including your memory of this review.
2. Give up to five main conclusions that bear on the research question: the findings the review itself presents as its conclusions (for a systematic review, its abstract's conclusions and graded main results; for an IPCC statement, the statement and the findings it rests on). Fewer than five is fine. Do not add conclusions the review does not draw.
3. For each conclusion give:
   - "statement": the conclusion in plain words, one or two sentences;
   - "direction": which way the finding goes (for example: benefit, harm, no difference, increase, decrease, uncertain);
   - "size": the size the review reports, with its numbers and units, or "not stated";
   - "certainty": the review's own certainty or confidence terms, word for word (e.g. "low-certainty evidence", "high confidence", "very likely"), or "not stated";
   - "scope": who and what the conclusion covers, and anything the review says it does not cover;
   - "quotes": one to three passages copied character for character from the review's text above, each with "role" (what it supports: statement, size, certainty or scope) and "section" (the nearest heading above it).
4. Every quotation must appear in the text above exactly as you copy it; a quotation that is not found is a failed key. Keep each under 400 characters.
5. Where the review hedges, keep the hedge. Where it grades certainty, keep the grade. Do not strengthen or weaken anything.

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"conclusions": [{"n": 1, "statement": "...", "direction": "...", "size": "...", "certainty": "...", "scope": "...", "quotes": [{"text": "...", "role": "...", "section": "..."}]}]}
