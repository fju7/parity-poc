import { useState, useCallback } from "react";
import OnboardingView from "./components/OnboardingView.jsx";
import UploadView from "./components/UploadView.jsx";
import ProcessingView from "./components/ProcessingView.jsx";
import ReportView from "./components/ReportView.jsx";
import ErrorView from "./components/ErrorView.jsx";
import ItemizedBillRequestView from "./components/ItemizedBillRequestView.jsx";
import extractBillData from "./modules/extractBillData.js";
import scoreAnomalies from "./modules/scoreAnomalies.js";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 10000;

// ---------------------------------------------------------------------------
// Sample bill data (for investor demo — no PDF needed)
// ---------------------------------------------------------------------------

const SAMPLE_BILL = {
  provider: { name: "Clearwater Medical Center", zip: "33701", npi: null },
  serviceDate: "01/15/2026",
  lineItems: [
    { code: "99214", codeType: "CPT", description: "Office visit, established patient, level 4", billedAmount: 425.0 },
    { code: "71046", codeType: "CPT", description: "Chest X-ray, 2 views", billedAmount: 380.0 },
    { code: "85025", codeType: "CPT", description: "Complete blood count with differential", billedAmount: 145.0 },
    { code: "80053", codeType: "CPT", description: "Comprehensive metabolic panel", billedAmount: 220.0 },
    { code: "99213", codeType: "CPT", description: "Office visit, established patient, level 3", billedAmount: 285.0 },
    { code: "36415", codeType: "CPT", description: "Venipuncture for blood draw", billedAmount: 75.0 },
    { code: "93000", codeType: "CPT", description: "Electrocardiogram (ECG), 12-lead", billedAmount: 310.0 },
    { code: "99214", codeType: "CPT", description: "Office visit, established patient, level 4 (follow-up)", billedAmount: 425.0 },
  ],
};

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  // "onboarding" | "upload" | "processing" | "report" | "error" | "itemized-request"
  const [view, setView] = useState("onboarding");
  const [processingStep, setProcessingStep] = useState(0);
  const [report, setReport] = useState(null);
  const [provider, setProvider] = useState(null);
  const [serviceDate, setServiceDate] = useState("");
  const [error, setError] = useState({ title: "", message: "" });
  const [eobData, setEobData] = useState(null);
  const [onboardingData, setOnboardingData] = useState({
    patientName: "",
    dateOfBirth: "",
    providerName: "",
    serviceDate: "",
  });

  const handleReset = useCallback(() => {
    setView("onboarding");
    setReport(null);
    setProvider(null);
    setServiceDate("");
    setProcessingStep(0);
    setError({ title: "", message: "" });
    setEobData(null);
    setOnboardingData({
      patientName: "",
      dateOfBirth: "",
      providerName: "",
      serviceDate: "",
    });
  }, []);

  const handleOnboardingSubmit = useCallback((data) => {
    setOnboardingData(data);
    setView("upload");
  }, []);

  const runPipeline = useCallback(
    async (billData) => {
      // Step 2: Look up benchmark rates
      setProcessingStep(1);

      let benchmarkResponse;
      try {
        benchmarkResponse = await fetchBenchmark(
          billData.provider.zip,
          billData.lineItems
        );
      } catch (err) {
        setError({
          title: "Rate Lookup Unavailable",
          message:
            "Rate lookup is temporarily unavailable. Please try again in a moment.",
        });
        setView("error");
        return;
      }

      // Check if all benchmarks are null
      const foundCount = benchmarkResponse.lineItems.filter(
        (i) => i.benchmarkRate !== null
      ).length;
      const nullCount = benchmarkResponse.lineItems.length - foundCount;

      // Step 3: Score anomalies
      setProcessingStep(2);
      const scored = scoreAnomalies(
        billData.lineItems,
        benchmarkResponse.lineItems
      );

      // Add a partial-benchmark warning to the report if needed
      if (foundCount === 0) {
        scored.partialWarning = `None of the ${nullCount} procedure codes could be benchmarked against current CMS data.`;
      } else if (nullCount > 0) {
        scored.partialWarning = `${nullCount} of ${benchmarkResponse.lineItems.length} procedure codes could not be benchmarked against current CMS data.`;
      }

      // Small delay so the user sees the final step
      await delay(400);

      setReport(scored);
      setProvider(billData.provider);
      setServiceDate(billData.serviceDate);
      setView("report");
    },
    []
  );

  const handleFileSelect = useCallback(
    async (file) => {
      setView("processing");
      setProcessingStep(0);

      try {
        // Step 1: Extract bill data from PDF
        const billData = await extractBillData(file);

        // Check for empty extraction — show itemized bill request flow
        if (!billData.lineItems || billData.lineItems.length === 0) {
          setEobData(billData);
          setView("itemized-request");
          return;
        }

        await runPipeline(billData);
      } catch (err) {
        console.error("Pipeline error:", err);
        setError({
          title: "Processing Error",
          message:
            "An error occurred while processing your document. Please make sure it is a valid PDF and try again.",
        });
        setView("error");
      }
    },
    [runPipeline]
  );

  const handleSampleBill = useCallback(async () => {
    setView("processing");
    setProcessingStep(0);

    // Small delay to show the first step
    await delay(600);

    try {
      await runPipeline(SAMPLE_BILL);
    } catch (err) {
      console.error("Sample bill error:", err);
      setError({
        title: "Processing Error",
        message: "An error occurred while processing the sample bill.",
      });
      setView("error");
    }
  }, [runPipeline]);

  if (view === "processing") {
    return <ProcessingView currentStep={processingStep} />;
  }

  if (view === "error") {
    return (
      <ErrorView
        title={error.title}
        message={error.message}
        onReset={handleReset}
      />
    );
  }

  if (view === "itemized-request") {
    return (
      <ItemizedBillRequestView eobData={eobData} onboardingData={onboardingData} onReset={handleReset} />
    );
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

  if (view === "onboarding") {
    return <OnboardingView onSubmit={handleOnboardingSubmit} />;
  }

  return (
    <UploadView
      onFileSelect={handleFileSelect}
      onSampleBill={handleSampleBill}
    />
  );
}

// ---------------------------------------------------------------------------
// API call with timeout + retry
// ---------------------------------------------------------------------------

async function fetchBenchmark(zipCode, lineItems) {
  const body = {
    zipCode: zipCode || "00000",
    lineItems: lineItems.map((i) => ({
      code: i.code,
      codeType: i.codeType,
      billedAmount: i.billedAmount,
    })),
  };

  // First attempt
  try {
    return await fetchWithTimeout(`${API_BASE}/api/benchmark`, body);
  } catch (err) {
    // Retry once on timeout/network error
    console.warn("Benchmark API first attempt failed, retrying:", err.message);
    return await fetchWithTimeout(`${API_BASE}/api/benchmark`, body);
  }
}

async function fetchWithTimeout(url, body) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
