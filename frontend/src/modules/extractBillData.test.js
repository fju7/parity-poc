/**
 * Unit tests for extractBillData — runs against a synthetic PDF
 * built in-memory with a minimal PDF structure.
 */

import { describe, it, expect } from "vitest";
import extractBillData from "./extractBillData.js";

/**
 * Build a minimal valid PDF file as a Uint8Array.
 * This creates a single-page PDF with the given text lines.
 */
function buildTestPdf(textLines) {
  // We'll use a very minimal PDF 1.4 structure with raw text operators
  const contentLines = textLines
    .map((line, i) => {
      const y = 700 - i * 20;
      return `BT /F1 10 Tf 72 ${y} Td (${escapePdfString(line)}) Tj ET`;
    })
    .join("\n");

  const objects = [];
  let objNum = 1;

  // Object 1: Catalog
  const catalogNum = objNum++;
  objects.push(
    `${catalogNum} 0 obj\n<< /Type /Catalog /Pages ${catalogNum + 1} 0 R >>\nendobj`
  );

  // Object 2: Pages
  const pagesNum = objNum++;
  objects.push(
    `${pagesNum} 0 obj\n<< /Type /Pages /Kids [${pagesNum + 1} 0 R] /Count 1 >>\nendobj`
  );

  // Object 3: Page
  const pageNum = objNum++;
  const contentsNum = objNum;
  const fontNum = objNum + 1;
  objects.push(
    `${pageNum} 0 obj\n<< /Type /Page /Parent ${pagesNum} 0 R /MediaBox [0 0 612 792] /Contents ${contentsNum} 0 R /Resources << /Font << /F1 ${fontNum} 0 R >> >> >>\nendobj`
  );

  // Object 4: Content stream
  objNum++;
  const streamBytes = new TextEncoder().encode(contentLines);
  objects.push(
    `${contentsNum} 0 obj\n<< /Length ${streamBytes.length} >>\nstream\n${contentLines}\nendstream\nendobj`
  );

  // Object 5: Font
  objNum++;
  objects.push(
    `${fontNum} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj`
  );

  // Build the full PDF
  const header = "%PDF-1.4\n";
  const body = objects.join("\n") + "\n";

  // Cross-reference table (simplified)
  const xrefEntries = [];
  let offset = header.length;
  for (const obj of objects) {
    xrefEntries.push(
      `${String(offset).padStart(10, "0")} 00000 n `
    );
    offset += obj.length + 1; // +1 for newline
  }

  const xrefOffset = header.length + body.length;
  const xref = [
    "xref",
    `0 ${objects.length + 1}`,
    "0000000000 65535 f ",
    ...xrefEntries,
    "",
  ].join("\n");

  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root ${catalogNum} 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  const fullPdf = header + body + xref + trailer;
  return new TextEncoder().encode(fullPdf);
}

function escapePdfString(str) {
  return str.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function makeFile(uint8Array, name = "test.pdf") {
  return new File([uint8Array], name, { type: "application/pdf" });
}

describe("extractBillData", () => {
  it("extracts CPT codes and dollar amounts from a synthetic bill", async () => {
    const pdf = buildTestPdf([
      "General Hospital Medical Center",
      "123 Main Street",
      "Tampa, FL 33601-1234",
      "NPI: 1234567890",
      "",
      "Date of Service: 01/15/2026",
      "Patient: Jane Doe",
      "",
      "Code   Description              Amount",
      "99213  Office visit level 3     $250.00",
      "99214  Office visit level 4     $375.00",
      "85025  CBC with differential     $45.50",
      "71046  Chest X-ray 2 views      $320.00",
      "",
      "Total                          $990.50",
    ]);

    const file = makeFile(pdf);
    const result = await extractBillData(file);

    // Provider
    expect(result.provider.name).toContain("Hospital Medical Center");
    expect(result.provider.zip).toBe("33601");
    expect(result.provider.npi).toBe("1234567890");

    // Service date
    expect(result.serviceDate).toBe("01/15/2026");

    // Line items — should find at least some CPT codes
    expect(result.lineItems.length).toBeGreaterThanOrEqual(2);

    const codes = result.lineItems.map((li) => li.code);
    expect(codes).toContain("99213");
    expect(codes).toContain("99214");

    // All items should be CPT type
    for (const item of result.lineItems) {
      expect(item.codeType).toBe("CPT");
      expect(item.billedAmount).toBeGreaterThan(0);
    }

    // Check specific amounts
    const item99213 = result.lineItems.find((li) => li.code === "99213");
    expect(item99213.billedAmount).toBe(250.0);

    // New fields should be present
    expect(result).toHaveProperty("patientName");
    expect(result).toHaveProperty("accountNumber");
    expect(result.patientName).toBe("Jane Doe");
  });

  it("returns empty lineItems for a non-bill PDF", async () => {
    const pdf = buildTestPdf([
      "Meeting Notes",
      "February 2026",
      "Discussed project timeline and deliverables.",
      "Action items assigned to team members.",
    ]);

    const file = makeFile(pdf);
    const result = await extractBillData(file);

    expect(result.lineItems.length).toBe(0);
    expect(result.patientName).toBe("");
    expect(result.accountNumber).toBe("");
  });

  it("extracts patient name and account number from an EOB-like document", async () => {
    const pdf = buildTestPdf([
      "EXPLANATION OF BENEFITS",
      "Aetna Health Insurance",
      "PO Box 14079, Lexington, KY 40512",
      "",
      "Patient: John Smith",
      "Member ID: AET123456789",
      "Account Number: ACC-98765",
      "Claim Reference: CLM2026-4421",
      "",
      "Date of Service: 03/10/2026",
      "Provider: Suncoast Medical Center",
      "",
      "Services Summary:",
      "Office Visit                     $350.00",
      "Lab Work                         $120.00",
      "Total Billed                     $470.00",
      "Plan Paid                        $280.00",
      "Your Responsibility              $190.00",
    ]);

    const file = makeFile(pdf);
    const result = await extractBillData(file);

    expect(result.patientName).toBe("John Smith");
    expect(result.accountNumber).toBe("ACC-98765");
  });

  it("returns empty strings when patient name and account number are not found", async () => {
    const pdf = buildTestPdf([
      "Some Hospital",
      "123 Main St, Tampa FL 33601",
      "Statement Date: 01/20/2026",
      "Amount Due: $500.00",
    ]);

    const file = makeFile(pdf);
    const result = await extractBillData(file);

    expect(result.patientName).toBe("");
    expect(result.accountNumber).toBe("");
  });
});
