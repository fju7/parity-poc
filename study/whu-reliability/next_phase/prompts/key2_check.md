You are checking a draft answer key against the expert review it was drafted from. You did not draft it. Your job is to find every place where the key does not say what the review says.

THE RESEARCH QUESTION:
<<<QUESTION
{question}
QUESTION>>>

WHAT THE REVIEW IS: {review}

THE REVIEW'S TEXT (the only material you may use):
{documents}

THE DRAFT KEY:
<<<KEY
{key}
KEY>>>

Instructions.
1. Use ONLY the review's text above. Do not use anything you know from elsewhere.
2. For each conclusion in the draft, check its statement, direction, size, certainty and scope against the review, and check that each quotation appears in the text word for word and supports what its role says.
3. Give each conclusion one verdict: "keep" (correct as drafted), "correct" (wrong in some field; give the corrected conclusion in full, with quotations copied from the text), or "drop" (not a conclusion the review draws, or not on the research question).
4. If the review draws a main conclusion on the research question that the draft leaves out, and the draft has fewer than five, add it, in the same form, with verdict "add".
5. Give a one-sentence reason for every verdict other than "keep".

Reply with ONE JSON object and nothing else, no code fence, in exactly this form:
{"checks": [{"n": 1, "verdict": "keep|correct|drop|add", "reason": "...", "conclusion": {"n": 1, "statement": "...", "direction": "...", "size": "...", "certainty": "...", "scope": "...", "quotes": [{"text": "...", "role": "...", "section": "..."}]}}]}
("conclusion" is required for "correct" and "add", and omitted otherwise.)
