const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  PageBreak, convertInchesToTwip,
} = require('docx');
const fs = require('fs');

const INK = '1A1A1A', SOFT = '4A4A4A', RULE = 'C8CCD2', ACCENT = '1F4E79', SHADE = 'EEF1F5';

// ---------------------------------------------------------------------------
// PROVISION SHEETS -- populated from candidates.json + retrieved text.
// Regenerate: python3 build_provisions.py && node build_attorney_doc.js
// ---------------------------------------------------------------------------
// The twelve rows from backend/data/verify/candidates.json with the retrieved
// provision text, VERBATIM, written by scripts/legal_review/build_provisions.py.
const PROVISIONS = require('./provisions.json');
// ---------------------------------------------------------------------------

const P = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, line: 280 },
  alignment: opts.align,
  children: [new TextRun({
    text, size: opts.size ?? 21, color: opts.color ?? INK,
    bold: opts.bold, italics: opts.italics, font: opts.font ?? 'Calibri',
  })],
});

const Rich = (runs, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 140, line: 280 },
  children: runs.map(r => new TextRun({
    text: r.t, size: r.size ?? 21, color: r.color ?? INK,
    bold: r.b, italics: r.i, font: r.font ?? 'Calibri',
  })),
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 340, after: 160 },
  children: [new TextRun({ text, size: 28, bold: true, color: INK, font: 'Calibri' })],
});

const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 260, after: 120 },
  children: [new TextRun({ text, size: 23, bold: true, color: ACCENT, font: 'Calibri' })],
});

const Label = (text) => new Paragraph({
  spacing: { before: 160, after: 60 },
  children: [new TextRun({
    text: text.toUpperCase(), size: 16, bold: true, color: ACCENT,
    font: 'Calibri', characterSpacing: 24,
  })],
});

const Bullet = (text) => new Paragraph({
  bullet: { level: 0 },
  spacing: { after: 90, line: 280 },
  children: [new TextRun({ text, size: 21, color: INK, font: 'Calibri' })],
});

const RuleLine = (before = 200, after = 200) => new Paragraph({
  spacing: { before, after },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 1 } },
  children: [new TextRun({ text: '', size: 2 })],
});

const NO_BORDER = {
  top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
};

const THIN = {
  top: { style: BorderStyle.SINGLE, size: 4, color: RULE },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
  left: { style: BorderStyle.SINGLE, size: 4, color: RULE },
  right: { style: BorderStyle.SINGLE, size: 4, color: RULE },
};

const TOTAL = 9360; // 6.5" content width in DXA

// Two-column key/value table used on the provision sheets
function factTable(rows) {
  return new Table({
    columnWidths: [2300, 7060],
    width: { size: TOTAL, type: WidthType.DXA },
    borders: THIN,
    rows: rows.map(([k, v]) => new TableRow({
      children: [
        new TableCell({
          width: { size: 2300, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: SHADE, color: 'auto' },
          margins: { top: 90, bottom: 90, left: 110, right: 110 },
          children: [new Paragraph({
            spacing: { after: 0, line: 260 },
            children: [new TextRun({ text: k, size: 18, bold: true, color: SOFT, font: 'Calibri' })],
          })],
        }),
        new TableCell({
          width: { size: 7060, type: WidthType.DXA },
          margins: { top: 90, bottom: 90, left: 110, right: 110 },
          children: [new Paragraph({
            spacing: { after: 0, line: 260 },
            children: [new TextRun({ text: v, size: 20, color: INK, font: 'Calibri' })],
          })],
        }),
      ],
    })),
  });
}

// A response block: prompt + checkbox line + ruled writing space
function responseBlock(question, choices, lines = 3) {
  const kids = [
    new Paragraph({
      spacing: { before: 150, after: 70, line: 280 },
      children: [new TextRun({ text: question, size: 20, bold: true, color: INK, font: 'Calibri' })],
    }),
  ];
  if (choices) {
    kids.push(new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({
        text: choices.map(c => '☐  ' + c).join('        '),
        size: 20, color: INK, font: 'Calibri',
      })],
    }));
  }
  for (let i = 0; i < lines; i++) {
    kids.push(new Paragraph({
      spacing: { before: 200, after: 0, line: 240 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 2 } },
      children: [new TextRun({ text: ' ', size: 20, color: 'FFFFFF' })],
    }));
  }
  return kids;
}

function generalQuestion(n, title, body, lines = 5) {
  return [
    new Paragraph({
      spacing: { before: 300, after: 80 },
      children: [
        new TextRun({ text: `Q${n}.  `, size: 22, bold: true, color: ACCENT, font: 'Calibri' }),
        new TextRun({ text: title, size: 22, bold: true, color: INK, font: 'Calibri' }),
      ],
    }),
    P(body, { color: SOFT, after: 60 }),
    ...Array.from({ length: lines }, () => new Paragraph({
      spacing: { before: 150, after: 0 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 1 } },
      children: [new TextRun({ text: '', size: 2 })],
    })),
  ];
}

// ---------------------------------------------------------------------------
const body = [];

// Masthead
body.push(new Paragraph({
  spacing: { after: 40 },
  children: [new TextRun({
    text: 'CIVICSCALE  ·  REQUEST FOR LEGAL REVIEW',
    size: 17, bold: true, color: ACCENT, font: 'Calibri', characterSpacing: 30,
  })],
}));
body.push(new Paragraph({
  spacing: { after: 120 },
  children: [new TextRun({
    text: 'Statutory citations in provider claim-denial appeal letters',
    size: 34, bold: true, color: INK, font: 'Calibri',
  })],
}));
body.push(new Paragraph({
  spacing: { after: 220 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: INK, space: 4 } },
  children: [new TextRun({ text: '', size: 2 })],
}));

body.push(factTable([
  ['From', 'Fred Ugast, U.S. Photovoltaics, Inc. (CivicScale) — fred.ugast@uspv.co'],
  ['Subject', 'Review of twelve legal provisions proposed for citation in appeal letters'],
  ['Jurisdiction', 'Ohio'],
  ['Estimated effort', 'One to two hours. Twelve short sheets plus six general questions.'],
  ['Status', 'Pre-launch. No letter containing these citations has been sent to any payer.'],
]));

// ---- What we are asking
body.push(H1('What we are asking you to do'));
body.push(P(
  'CivicScale is building software that drafts appeal letters for medical practices whose ' +
  'insurance claims have been denied. Each letter argues the practice’s case and, where useful, ' +
  'cites the legal provision that supports it.'
));
body.push(P(
  'We have built an automated check that verifies three things about every citation before a letter ' +
  'can use it: that the provision exists, that its actual text contains whatever we quote from it, ' +
  'and that it applies to the type of payer being written to. Nothing reaches a letter unless all ' +
  'three hold.'
));
body.push(Rich([
  { t: 'What our check cannot do is tell us whether a provision is the ', },
  { t: 'right', i: true },
  { t: ' one to cite for a given denial reason. That is a legal judgement, and it is the only thing ' +
       'standing between the current state — letters that cite no law at all — and letters that cite ' +
       'law we can stand behind.' },
]));
body.push(P(
  'Below are twelve provisions we have selected as candidates, one sheet each. For each, we ask you ' +
  'to tell us whether it does what we think it does and whether citing it is sound. Six broader ' +
  'questions follow.'
));

body.push(H2('What we are not asking'));
body.push(Bullet('We are not asking you to draft or review letter language beyond the single sentence shown on each sheet.'));
body.push(Bullet('We are not asking for an opinion on the software, the business, or anything outside these twelve provisions and the six questions.'));
body.push(Bullet('We are not asking you to research provisions we have not listed — though if an obvious better one comes to mind, we very much want to know.'));
body.push(Bullet('This is a request for review, not an engagement letter. Please scope and quote as you see fit.'));

body.push(H2('Why this matters more than it might appear'));
body.push(P(
  'An earlier version of this software generated its legal citations without checking them. Of ' +
  'nineteen provisions it cited across ten test letters, twelve did not say what the letter claimed. ' +
  'One example: the letters repeatedly cited Ohio Adm. Code 3901-1-54 as a health-claims payment ' +
  'standard. Its actual subject is unfair property and casualty claims settlement practices.'
));
body.push(P(
  'Those letters went to no one — they were generated in testing and the defect was found before ' +
  'launch. The automated check described above was built in response, and the software currently ' +
  'cites no statute whatsoever. We would rather cite nothing than cite wrongly, and we will keep ' +
  'citing nothing until someone qualified has signed off on what we cite.'
));

// ---- How to respond
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('How to respond'));
body.push(P(
  'Mark up this document however suits you — tick boxes, write in the ruled space, use tracked ' +
  'changes or comments, or reply separately referencing the sheet numbers. Short answers are fine. ' +
  'Where a provision is wrong for our purpose, the most useful thing you can tell us is what would ' +
  'be right instead, or that nothing would be.'
));
body.push(P(
  'Each provision sheet asks four questions. The first two are the ones that gate the software: a ' +
  'provision only becomes usable if both are affirmative.',
  { color: SOFT }
));

body.push(RuleLine(220, 160));
body.push(Label('The four questions on each sheet'));
body.push(Bullet('1.  Does this provision impose the obligation we describe?'));
body.push(Bullet('2.  Is it appropriate to cite for this denial reason and this payer type?'));
body.push(Bullet('3.  If not — is there a better provision, or none?'));
body.push(Bullet('4.  Any wording you would require or forbid when it is cited?'));
body.push(RuleLine(160, 240));

// ---- General questions
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('Six general questions'));
body.push(P(
  'These matter more to us than any single provision, because each one shapes how the software ' +
  'behaves across every letter it will ever write.',
  { color: SOFT }
));

body.push(...generalQuestion(1,
  'Should a first-level appeal to a commercial payer cite statute at all?',
  'We genuinely do not know. We have heard both that statutory citation signals seriousness and ' +
  'gets claims reworked, and that it antagonises claims staff who have no authority to act on it ' +
  'and slows things down. If citation belongs only at second level or external review, we would ' +
  'rather build that in than discover it.'
));

body.push(...generalQuestion(2,
  'Does Medicare authority carry any weight with a commercial payer?',
  'Our check currently refuses to let a letter cite Medicare-derived authority — the CMS claims ' +
  'processing manuals, the National Correct Coding Initiative — when the payer is a commercial ' +
  'insurer, on the reasoning that those bind Medicare contractors and not Anthem. But we understand ' +
  'many commercial payers adopt NCCI edits contractually in their provider agreements. If that makes ' +
  'our refusal too strict, we would loosen it — but only on advice, and we would want to know how to ' +
  'frame such a citation so it is accurate about what it is.'
));

body.push(...generalQuestion(3,
  'Are we missing the provisions that actually work?',
  'Our twelve were assembled by reading the Ohio Revised Code and the CMS manuals directly. Someone ' +
  'who does this work will know which provisions practices actually cite to effect, and which are ' +
  'technically apposite but practically inert. Please tell us what we should be citing that is not ' +
  'on the list.'
));

body.push(...generalQuestion(4,
  'Does a software-generated letter citing law create any exposure for the practice sending it?',
  'The letter goes out over the practice’s name and signature. We want to understand whether ' +
  'anything about that arrangement — the citation of legal provisions in a document prepared by ' +
  'software, sent by a non-lawyer to an insurer in pursuit of payment — creates risk for the ' +
  'practice, for us, or for both. Unauthorised practice of law, misrepresentation, or anything ' +
  'else we have not thought of.'
));

body.push(...generalQuestion(5,
  'How strongly should the letter assert?',
  'There is a difference between “Ohio law requires payment within thirty days” and “we understand ' +
  'Ohio law to require payment within thirty days.” We can write either, uniformly, across every ' +
  'letter. Which is right, and does it change by provision or by payer type?'
));

body.push(...generalQuestion(6,
  'Does this structure transfer to other states?',
  'We are starting with Ohio. Our intention is that each additional state is a separate set of ' +
  'provisions reviewed the same way, and that until a state has been reviewed its letters cite ' +
  'nothing. Is that the right shape, or do the differences between states run deeper than a ' +
  'per-state citation list can capture?'
));

// ---- Provision sheets
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('The twelve provisions'));
body.push(P(
  'One sheet each. Each sheet gives the denial reason, the payer type, the provision, its retrieved ' +
  'text, and the exact sentence a letter would build from it — then asks the four questions.'
));
body.push(P(
  'Denial reason codes are the standard CARC codes used on remittance advice; the plain meaning is ' +
  'given on each sheet.',
  { color: SOFT, size: 19 }
));

PROVISIONS.forEach((pv, idx) => {
  body.push(new Paragraph({ children: [new PageBreak()] }));

  body.push(new Paragraph({
    spacing: { after: 40 },
    children: [new TextRun({
      text: `SHEET ${idx + 1} OF ${PROVISIONS.length}  ·  ${pv.id}`,
      size: 16, bold: true, color: ACCENT, font: 'Calibri', characterSpacing: 26,
    })],
  }));
  body.push(new Paragraph({
    spacing: { after: 160 },
    children: [new TextRun({ text: pv.citation, size: 30, bold: true, color: INK, font: 'Calibri' })],
  }));

  body.push(factTable([
    ['Denial reason', `${pv.denialCode} — ${pv.denialMeaning}`],
    ['Payer type', pv.payerType],
    ['Official heading', pv.heading],
    ['Retrieved from', pv.source],
  ]));

  body.push(Label('Retrieved text'));
  body.push(new Paragraph({
    spacing: { after: 150, line: 280 },
    indent: { left: 240 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 10 } },
    children: [new TextRun({ text: pv.excerpt, size: 20, color: INK, font: 'Calibri' })],
  }));

  body.push(Label('The sentence a letter would write'));
  body.push(new Paragraph({
    spacing: { after: 150, line: 280 },
    indent: { left: 240 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: RULE, space: 10 } },
    children: [new TextRun({ text: pv.assertion, size: 20, color: INK, italics: true, font: 'Calibri' })],
  }));

  body.push(Label('Why we selected it'));
  body.push(P(pv.rationale, { size: 20, color: SOFT }));
  body.push(P(pv.ourNote, { size: 19, color: SOFT, italics: true, after: 60 }));

  body.push(RuleLine(200, 40));

  body.push(...responseBlock('1.  Does this provision impose the obligation we describe?',
    ['Yes', 'No', 'Partly'], 2));
  body.push(...responseBlock('2.  Is it appropriate to cite for this denial reason and this payer type?',
    ['Yes', 'No', 'With caveats'], 2));
  body.push(...responseBlock('3.  If not — what should we cite instead, or should we cite nothing?',
    null, 3));
  body.push(...responseBlock('4.  Wording you would require or forbid:',
    null, 3));
});

// ---- Close
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('Anything else'));
body.push(P(
  'If something about this approach strikes you as wrong in a way none of the questions above ' +
  'reaches, that is the most valuable thing you could tell us. We would rather hear it now than ' +
  'after the first letter goes out.'
));
body.push(...Array.from({ length: 8 }, () => new Paragraph({
  spacing: { before: 170, after: 0 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 1 } },
  children: [new TextRun({ text: '', size: 2 })],
})));

body.push(RuleLine(340, 120));
body.push(P(
  'Reviewer name and date: ______________________________________________________',
  { size: 20, color: SOFT }
));

const doc = new Document({
  styles: { default: { document: { run: { font: 'Calibri', size: 21, color: INK } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: {
          top: convertInchesToTwip(1), bottom: convertInchesToTwip(1),
          left: convertInchesToTwip(1), right: convertInchesToTwip(1),
        },
      },
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = process.argv[2] || 'CivicScale-Legal-Review-Request.docx';
  fs.writeFileSync(out, buf);
  console.log('written', out, buf.length, 'bytes');
});
