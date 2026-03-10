/**
 * CPT code plain-English label lookup.
 * Shared across Parity Health ReportView and Employer ClaimsCheck.
 */

const CPT_DESCRIPTIONS = {
  "27447": "Total Knee Replacement",
  "29881": "Knee Arthroscopy",
  "73721": "MRI, Joint of Lower Extremity",
  "75574": "CT Heart Artery w/Contrast",
  "20610": "Joint Injection, Large",
  "22551": "Cervical Spine Fusion",
  "70553": "MRI Brain w/Contrast",
  "99213": "Office Visit, Established (Low)",
  "99214": "Office Visit, Established (Moderate)",
  "99215": "Office Visit, Established (High)",
  "85025": "Complete Blood Count",
  "80053": "Comprehensive Metabolic Panel",
  "36415": "Blood Draw",
  "99204": "Office Visit, New (Moderate)",
  "99205": "Office Visit, New (High)",
  "93000": "Electrocardiogram",
  "99232": "Hospital Visit, Subsequent",
  "99283": "Emergency Dept Visit, Moderate",
  "99284": "Emergency Dept Visit, High",
  "99285": "Emergency Dept Visit, Critical",
  "99281": "Emergency Dept Visit, Minimal",
  "99282": "Emergency Dept Visit, Low",
  "99203": "Office Visit, New (Low)",
  "99212": "Office Visit, Established (Minimal)",
  "99211": "Office Visit, Established (Nurse)",
  "99223": "Hospital Admit, High Complexity",
  "99222": "Hospital Admit, Moderate Complexity",
  "99221": "Hospital Admit, Low Complexity",
  "99231": "Hospital Visit, Subsequent (Low)",
  "99233": "Hospital Visit, Subsequent (High)",
  "99238": "Hospital Discharge Day",
  "99239": "Hospital Discharge Day (>30 min)",
  "99291": "Critical Care, First Hour",
  "99292": "Critical Care, Each Addl 30 min",
  "71046": "Chest X-Ray, 2 Views",
  "71045": "Chest X-Ray, 1 View",
  "70551": "MRI Brain w/o Contrast",
  "70553": "MRI Brain w/o & w/Contrast",
  "73721": "MRI Lower Extremity Joint",
  "73221": "MRI Upper Extremity Joint",
  "74177": "CT Abdomen & Pelvis w/Contrast",
  "74176": "CT Abdomen & Pelvis w/o Contrast",
  "76856": "Pelvic Ultrasound",
  "76700": "Abdominal Ultrasound, Complete",
  "93306": "Echocardiogram, Complete",
  "93005": "Electrocardiogram, Tracing Only",
  "10060": "Incision & Drainage, Abscess",
  "10120": "Foreign Body Removal, Simple",
  "12001": "Wound Repair, Simple (2.5 cm)",
  "12002": "Wound Repair, Simple (2.6-7.5 cm)",
  "20600": "Joint Injection, Small",
  "20605": "Joint Injection, Intermediate",
  "43239": "Upper GI Endoscopy w/Biopsy",
  "45380": "Colonoscopy w/Biopsy",
  "45378": "Colonoscopy, Diagnostic",
  "90834": "Psychotherapy, 45 min",
  "90837": "Psychotherapy, 60 min",
  "90847": "Family Psychotherapy",
  "97110": "Therapeutic Exercise",
  "97140": "Manual Therapy",
  "97530": "Therapeutic Activities",
  "96372": "Therapeutic Injection",
  "96374": "IV Push, Single Drug",
  "96375": "IV Push, Each Addl Drug",
  "81001": "Urinalysis, Automated",
  "84443": "Thyroid Stimulating Hormone (TSH)",
  "83036": "Hemoglobin A1C",
  "80048": "Basic Metabolic Panel",
  "85610": "Prothrombin Time (PT)",
  "86900": "Blood Typing, ABO",
  "86901": "Blood Typing, Rh(D)",
};

export const cptLabel = (code) => {
  const desc = CPT_DESCRIPTIONS[String(code)];
  return desc ? `CPT ${code} — ${desc}` : `CPT ${code}`;
};

/**
 * Returns just the plain-English description, or null if not found.
 */
export const cptDescription = (code) => {
  return CPT_DESCRIPTIONS[String(code)] || null;
};

export default cptLabel;
