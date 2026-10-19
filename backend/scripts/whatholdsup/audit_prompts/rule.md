A reader has raised a finding about one sentence of a draft, with the source text it rests on. You decide whether the finding is right. You see only the sentence, the finding and the quoted source text; decide on those alone, without outside knowledge.

THE SENTENCE:
<<<SENTENCE
{sentence}
SENTENCE>>>

THE FINDING:
<<<FINDING
Kind: {kind}
Reader's reason: {reason}
Reader's proposed text: {proposed_text}
FINDING>>>

THE QUOTED SOURCE TEXT (each quotation shown with the text around it in its document):
<<<SOURCE
{quoted_source_text}
SOURCE>>>

Decide one of:
- accept: the finding is right and the proposed text says only what the source text supports.
- amend: the finding is right but the proposed text is not; give a corrected text that says only what the source text supports. If nothing the sentence says can be supported, give the shortest text that can, or "" to cut the sentence.
- reject: the finding is wrong: the source text supports the sentence as written. Say what in the source text supports it.

Reply with ONE JSON object and nothing else, no code fence:
{"ruling": "<accept, amend or reject>", "text": "<the text to publish: the proposed text for accept, your text for amend, null for reject>", "reason": "<one sentence, citing the source text>"}
