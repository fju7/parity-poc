A reader says a draft leaves out a finding of one of its sources. Code has already confirmed that the finding below is in the source, word for word. You decide two things about it, and, if both hold, write the sentence that adds it. You see only what is below; decide on it alone, without outside knowledge.

THE QUESTION THE DRAFT ANSWERS:
<<<QUESTION
{question}
QUESTION>>>

WHAT THE DRAFT SAID, BEFORE READING ANY SOURCE, THAT IT WOULD AND WOULD NOT COVER:
<<<SCOPE
{scope}
SCOPE>>>

THE READER WHO HAS A DECISION TO MAKE:
<<<READER
{reader}
READER>>>

THE OMITTED FINDING (in the source, verified by code), with the text around it:
<<<FINDING
{finding}
FINDING>>>

WHERE IT WOULD GO (the page sentence nearest to it, with its neighbours):
<<<ANCHOR
{anchor}
ANCHOR>>>

WHAT THE DRAFT ALREADY SAYS FROM THIS SOURCE:
<<<ALREADY
{already_on_page}
ALREADY>>>

Decide, in order:
1. In scope: does the finding bear on THE QUESTION as worded? If not, name the exact words of THE QUESTION, or of a SCOPE entry, that put it outside. Do not call it out of scope for any reason you cannot point to in those words.
2. Material: would THE READER weigh it in answering THE QUESTION, because it answers, narrows or qualifies the answer, or adds a distinct outcome? A finding the draft already states (see ALREADY) is not material.

Then give one outcome:
- OUT_OF_SCOPE: step 1 fails. Give scope_element: the words, copied exactly from THE QUESTION or SCOPE.
- NOT_MATERIAL: step 1 holds, step 2 fails. Say why.
- ADD: both hold. Write draft_text, one sentence that adds the finding to the page. Use the source's own words wherever they stand alone, inside a short attribution ("The authors conclude that ...", "The assessment finds, with high confidence, that ..."). Keep every hedge, every certainty or confidence term and every limit the finding carries; never state it more strongly or more certainly than the source does, and never more weakly. Give span: the exact words of THE OMITTED FINDING that the sentence rests on, copied character for character.

Reply with ONE JSON object and nothing else, no code fence:
{"in_scope": true or false, "scope_element": "<words from THE QUESTION or SCOPE, or empty>", "material": true or false, "outcome": "<ADD, OUT_OF_SCOPE or NOT_MATERIAL>", "draft_text": "<the sentence for ADD, else empty>", "span": "<the exact words of the finding for ADD, else empty>", "reason": "<brief: why, for each step>"}
