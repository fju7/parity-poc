Readers have raised several findings about one sentence of a draft, with the source text it rests on. You decide them together: whatever you decide becomes the one text of that sentence, and no finding is ruled again. You see only the sentence, the findings and the quoted source text; decide on those alone, without outside knowledge.

THE SENTENCE:
<<<SENTENCE
{sentence}
SENTENCE>>>

THE FINDINGS (each with the quotations it rests on, by number):
<<<FINDINGS
{findings}
FINDINGS>>>

THE QUOTED SOURCE TEXT (each quotation shown with the text around it in its document):
<<<SOURCE
{quoted_source_text}
SOURCE>>>

Decide each finding: it is right, or it is wrong because the source text supports the sentence as written on that point. Then decide one of:
- accept: at least one finding is right, and one reader's proposed text settles every finding that is right and says only what the source text supports; give that text, word for word.
- amend: at least one finding is right, and no proposed text settles every finding that is right while saying only what the source text supports; give one text that does. If nothing the sentence says can be supported, give the shortest text that can, or "" to cut the sentence.
- reject: every finding is wrong: the source text supports the sentence as written. Say what in the source text supports it.

Your text is the sentence's only replacement. It must settle every finding you decide is right, and must not undo what the sentence already says correctly.

Reply with ONE JSON object and nothing else, no code fence:
{"ruling": "<accept, amend or reject>", "text": "<the text to publish: the chosen proposed text for accept, your text for amend, null for reject>", "reason": "<brief: for each finding by number, right or wrong, citing the source text>"}
