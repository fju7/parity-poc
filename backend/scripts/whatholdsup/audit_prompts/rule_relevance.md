A draft answers the question below. One of its sources contains the expert judgement below. You decide only whether that judgement bears on the question. You see only what is below; decide on it alone, without outside knowledge.

THE QUESTION:
<<<QUESTION
{question}
QUESTION>>>

WHAT THE DRAFT SAID, BEFORE READING ANY SOURCE, THAT IT WOULD AND WOULD NOT COVER:
<<<SCOPE
{scope}
SCOPE>>>

THE JUDGEMENT (from the source, verified by code):
<<<JUDGEMENT
{judgement}
JUDGEMENT>>>

The judgement is relevant if a reader of the answer would need it to weigh the answer to THE QUESTION: it is about the same intervention, exposure or outcome, or directly about whether the evidence shows it. It is not relevant if it is about something THE QUESTION does not ask.

If relevant, copy into question_words the exact words of THE QUESTION (or of the SCOPE's "Covers" or an out-of-scope entry) that the judgement bears on: at least two consecutive words, copied character for character. Use " … " between separate runs of words, in the order they appear.

Reply with ONE JSON object and nothing else, no code fence:
{"relevant": true or false, "question_words": "<the copied words, or empty>", "reason": "<one sentence>"}
