import { useState } from "react";
import UploadView from "./components/UploadView.jsx";
import ProcessingView from "./components/ProcessingView.jsx";
import ReportView from "./components/ReportView.jsx";

// Mock data for UI development — will be replaced by real pipeline in Task 7
const MOCK_REPORT = {
  lineItems: [
    { code: "99214", codeType: "CPT", description: "Office visit, level 4", billedAmount: 375.0, benchmarkRate: 135.02, benchmarkSource: "CMS_PFS_2026", localityCode: "99", anomalyScore: 2.78, flagged: true, flagReason: "Billed at 2.8x the Medicare benchmark rate", estimatedDiscrepancy: 239.98 },
    { code: "71046", codeType: "CPT", description: "Chest X-ray, 2 views", billedAmount: 320.0, benchmarkRate: 34.12, benchmarkSource: "CMS_PFS_2026", localityCode: "99", anomalyScore: 9.38, flagged: true, flagReason: "Billed at 9.4x the Medicare benchmark rate", estimatedDiscrepancy: 285.88 },
    { code: "85025", codeType: "CPT", description: "CBC with differential", billedAmount: 45.5, benchmarkRate: null, benchmarkSource: "NOT_FOUND", localityCode: "99", anomalyScore: null, flagged: false, flagReason: "", estimatedDiscrepancy: 0 },
    { code: "99213", codeType: "CPT", description: "Office visit, level 3", billedAmount: 250.0, benchmarkRate: 94.56, benchmarkSource: "CMS_PFS_2026", localityCode: "99", anomalyScore: 2.64, flagged: true, flagReason: "Billed at 2.6x the Medicare benchmark rate", estimatedDiscrepancy: 155.44 },
    { code: "36415", codeType: "CPT", description: "Venipuncture", billedAmount: 35.0, benchmarkRate: 12.45, benchmarkSource: "CMS_PFS_2026", localityCode: "99", anomalyScore: 2.81, flagged: true, flagReason: "Billed at 2.8x the Medicare benchmark rate", estimatedDiscrepancy: 22.55 },
    { code: "80053", codeType: "CPT", description: "Comprehensive metabolic panel", billedAmount: 120.0, benchmarkRate: null, benchmarkSource: "NOT_FOUND", localityCode: "99", anomalyScore: null, flagged: false, flagReason: "", estimatedDiscrepancy: 0 },
  ],
  summary: {
    totalBilled: 1145.5,
    totalBenchmark: 276.15,
    totalPotentialDiscrepancy: 703.85,
    flaggedItemCount: 4,
    totalItemCount: 6,
  },
};

const MOCK_PROVIDER = {
  name: "Tampa General Hospital",
  zip: "33601",
  npi: "1234567890",
};

export default function App() {
  // "upload" | "processing" | "report"
  const [view, setView] = useState("upload");
  const [processingStep, setProcessingStep] = useState(0);
  const [report, setReport] = useState(null);
  const [provider, setProvider] = useState(null);
  const [serviceDate, setServiceDate] = useState("");

  const handleFileSelect = (file) => {
    // Task 7 will replace this with real extraction pipeline
    setView("processing");
    setProcessingStep(0);

    // Simulate processing steps
    setTimeout(() => setProcessingStep(1), 1000);
    setTimeout(() => setProcessingStep(2), 2000);
    setTimeout(() => {
      setReport(MOCK_REPORT);
      setProvider(MOCK_PROVIDER);
      setServiceDate("01/15/2026");
      setView("report");
    }, 3000);
  };

  const handleSampleBill = () => {
    handleFileSelect(null);
  };

  const handleReset = () => {
    setView("upload");
    setReport(null);
    setProvider(null);
    setServiceDate("");
    setProcessingStep(0);
  };

  if (view === "processing") {
    return <ProcessingView currentStep={processingStep} />;
  }

  if (view === "report" && report) {
    return (
      <ReportView
        report={report}
        provider={provider}
        serviceDate={serviceDate}
        onReset={handleReset}
      />
    );
  }

  return (
    <UploadView
      onFileSelect={handleFileSelect}
      onSampleBill={handleSampleBill}
    />
  );
}
