import { useState, useCallback, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "./lib/supabase.js";
import { saveBill, getBillById, clearAll } from "./lib/localBillStore.js";
import SignInView from "./components/SignInView.jsx";
import ConsentView from "./components/ConsentView.jsx";
import OnboardingView from "./components/OnboardingView.jsx";
import UploadView from "./components/UploadView.jsx";
import ProcessingView from "./components/ProcessingView.jsx";
import ReportView from "./components/ReportView.jsx";
import ErrorView from "./components/ErrorView.jsx";
import ItemizedBillRequestView from "./components/ItemizedBillRequestView.jsx";
import BillHistoryView from "./components/BillHistoryView.jsx";
import AppHeader from "./components/AppHeader.jsx";
import Toast from "./components/Toast.jsx";
import extractBillData from "./modules/extractBillData.js";
import scoreAnomalies from "./modules/scoreAnomalies.js";
import runCodingIntelligence from "./modules/codingIntelligence.js";

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
    { code: "99215", codeType: "CPT", description: "Office visit, established patient, level 5 (complex)", billedAmount: 525.0 },
  ],
};

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

// Map URL pathname (relative to /parity-health) to view name
function viewFromPath(pathname) {
  const rel = pathname.replace(/^\/parity-health\/?/, "").replace(/\/$/, "");
  if (rel === "history") return "history";
  if (rel === "account") return "account";
  return "onboarding"; // default — auth flow will override
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  // Auth state
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // "consent" | "onboarding" | "upload" | "processing" | "report" | "error" | "itemized-request" | "history"
  const [view, setView] = useState(() => viewFromPath(location.pathname));
  const [processingStep, setProcessingStep] = useState(0);
  const [report, setReport] = useState(null);
  const [provider, setProvider] = useState(null);
  const [serviceDate, setServiceDate] = useState("");
  const [error, setError] = useState({ title: "", message: "" });
  const [eobData, setEobData] = useState(null);
  const [toast, setToast] = useState({ message: "", visible: false });
  const [hasCompletedConsent, setHasCompletedConsent] = useState(false);
  const [consentData, setConsentData] = useState({ consentAnalytics: true, consentEmployer: false });
  const [onboardingData, setOnboardingData] = useState({
    firstName: "",
    lastName: "",
    dateOfBirth: "",
    streetAddress: "",
    city: "",
    state: "",
    zipCode: "",
    email: "",
    phone: "",
  });

  // ----- Auth: session bootstrap + listener -----
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      if (s) fetchProfile(s.user.id, s.user.email);
      setAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      if (s) fetchProfile(s.user.id, s.user.email);
    });

    return () => subscription.unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----- Fetch profile from Supabase and pre-fill onboarding -----
  const fetchProfile = async (userId, email) => {
    try {
      const { data } = await supabase
        .from("profiles")
        .select("first_name, last_name, date_of_birth, street_address, city, state, zip_code, phone, consent_agreed_at, consent_analytics, consent_employer")
        .eq("id", userId)
        .single();

      if (data) {
        setOnboardingData((prev) => ({
          ...prev,
          firstName: data.first_name || "",
          lastName: data.last_name || "",
          dateOfBirth: data.date_of_birth || "",
          streetAddress: data.street_address || "",
          city: data.city || "",
          state: data.state || "",
          zipCode: data.zip_code || "",
          phone: data.phone || "",
          email: email || "",
        }));

        // Track consent state
        if (data.consent_agreed_at) {
          setHasCompletedConsent(true);
          setConsentData({
            consentAnalytics: data.consent_analytics ?? true,
            consentEmployer: data.consent_employer ?? false,
          });
          // Skip to upload if profile is filled in — respect URL if it's a deep link
          if (data.first_name && data.last_name) {
            const urlView = viewFromPath(location.pathname);
            if (urlView === "history" || urlView === "account") {
              setView(urlView);
            } else {
              setView("upload");
            }
          }
        } else {
          setHasCompletedConsent(false);
          setView("consent");
        }
      } else {
        setOnboardingData((prev) => ({ ...prev, email: email || "" }));
        setHasCompletedConsent(false);
        setView("consent");
      }
    } catch {
      // Profile doesn't exist yet — show consent flow
      setOnboardingData((prev) => ({ ...prev, email: email || "" }));
      setHasCompletedConsent(false);
      setView("consent");
    }
  };

  // ----- Sign out -----
  const handleSignOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    navigate("/parity-health/");
    setView("onboarding");
    setReport(null);
    setProvider(null);
    setServiceDate("");
    setProcessingStep(0);
    setError({ title: "", message: "" });
    setEobData(null);
    setOnboardingData({
      firstName: "",
      lastName: "",
      dateOfBirth: "",
      streetAddress: "",
      city: "",
      state: "",
      zipCode: "",
      email: "",
      phone: "",
    });
  }, [navigate]);

  const handleReset = useCallback(() => {
    navigate("/parity-health/");
    setView("upload");
    setReport(null);
    setProvider(null);
    setServiceDate("");
    setProcessingStep(0);
    setError({ title: "", message: "" });
    setEobData(null);
  }, [navigate]);

  // ----- Navigation -----
  const handleNavigate = useCallback((target) => {
    if (target === "upload") {
      navigate("/parity-health/");
    } else if (target === "history") {
      navigate("/parity-health/history");
    } else if (target === "account") {
      navigate("/parity-health/account");
    }
    setView(target);
  }, [navigate]);

  // ----- Delete account -----
  const handleDeleteAccount = useCallback(async () => {
    try {
      // Clear local bill data
      await clearAll();

      // Delete profile from Supabase
      if (session?.user) {
        await supabase.from("profiles").delete().eq("id", session.user.id);
      }

      // Sign out
      await supabase.auth.signOut();
      setSession(null);
      navigate("/parity-health/");
      setView("onboarding");
      setReport(null);
      setProvider(null);
      setServiceDate("");
      setProcessingStep(0);
      setError({ title: "", message: "" });
      setEobData(null);
      setHasCompletedConsent(false);
      setConsentData({ consentAnalytics: true, consentEmployer: false });
      setOnboardingData({
        firstName: "",
        lastName: "",
        dateOfBirth: "",
        streetAddress: "",
        city: "",
        state: "",
        zipCode: "",
        email: "",
        phone: "",
      });
    } catch (err) {
      console.error("Failed to delete account:", err);
    }
  }, [session, navigate]);

  // ----- View saved bill from history (IndexedDB) -----
  const handleViewSavedBill = useCallback(async (billId) => {
    try {
      const bill = await getBillById(billId);
      if (!bill) return;

      setReport({
        lineItems: bill.lineItems || [],
        summary: bill.summary || {},
        partialWarning: bill.partialWarning || null,
        codingAlerts: bill.codingAlerts || [],
        codingSummary: bill.codingSummary || null,
      });
      setProvider(bill.provider || { name: "Unknown Provider" });
      setServiceDate(bill.serviceDate || "");
      setView("report");
    } catch (err) {
      console.error("Failed to load saved bill:", err);
    }
  }, []);

  // ----- Auto-save bill to IndexedDB (local only) -----
  const saveBillLocally = useCallback(
    async (scored, billProvider, billServiceDate) => {
      try {
        await saveBill({
          provider: billProvider || { name: "Unknown Provider" },
          serviceDate: billServiceDate || null,
          summary: scored.summary,
          lineItems: scored.lineItems,
          partialWarning: scored.partialWarning || null,
          codingAlerts: scored.codingAlerts || [],
          codingSummary: scored.codingSummary || null,
        });

        setToast({ message: "Saved", visible: true });
        setTimeout(() => setToast((prev) => ({ ...prev, visible: false })), 2000);
      } catch {
        // Non-blocking — don't disrupt the report display
      }
    },
    []
  );

  // ----- Consent submission -----
  const handleConsentSubmit = useCallback(
    async ({ consentAnalytics: analytics, consentEmployer: employer }) => {
      setConsentData({ consentAnalytics: analytics, consentEmployer: employer });
      setHasCompletedConsent(true);

      if (session?.user) {
        try {
          await supabase.from("profiles").upsert({
            id: session.user.id,
            email: session.user.email,
            consent_analytics: analytics,
            consent_employer: employer,
            consent_agreed_at: new Date().toISOString(),
          });
        } catch {
          // Non-blocking
        }
      }

      setView("onboarding");
    },
    [session]
  );

  const handleOnboardingSubmit = useCallback(
    async (data) => {
      setOnboardingData(data);

      // Upsert profile to Supabase
      if (session?.user) {
        try {
          await supabase.from("profiles").upsert({
            id: session.user.id,
            email: session.user.email,
            first_name: data.firstName,
            last_name: data.lastName,
            date_of_birth: data.dateOfBirth,
            street_address: data.streetAddress,
            city: data.city,
            state: data.state,
            zip_code: data.zipCode,
            phone: data.phone,
          });
        } catch {
          // Non-blocking — continue even if profile save fails
        }
      }

      navigate("/parity-health/");
      setView("upload");
    },
    [session, navigate]
  );

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

      // Step 4: Run coding intelligence checks
      setProcessingStep(3);
      const { codingAlerts, codingSummary } = runCodingIntelligence(
        billData,
        benchmarkResponse.codingAlerts || []
      );
      scored.codingAlerts = codingAlerts;
      scored.codingSummary = codingSummary;

      // Small delay so the user sees the final step
      await delay(400);

      setReport(scored);
      setProvider(billData.provider);
      setServiceDate(billData.serviceDate);
      setView("report");

      // Auto-save to IndexedDB (non-blocking)
      saveBillLocally(scored, billData.provider, billData.serviceDate);
    },
    [saveBillLocally]
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

  // ----- Auth loading state -----
  if (authLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center font-[Arial,sans-serif]">
        <p className="text-gray-400 text-sm">Loading...</p>
      </div>
    );
  }

  // ----- Not signed in -----
  if (!session) {
    return <SignInView />;
  }

  // ----- Determine which view content to render -----
  let viewContent;

  if (view === "processing") {
    viewContent = <ProcessingView currentStep={processingStep} />;
  } else if (view === "error") {
    viewContent = (
      <ErrorView
        title={error.title}
        message={error.message}
        onReset={handleReset}
      />
    );
  } else if (view === "itemized-request") {
    viewContent = (
      <ItemizedBillRequestView
        eobData={eobData}
        onboardingData={onboardingData}
        onReset={handleReset}
      />
    );
  } else if (view === "report" && report) {
    viewContent = (
      <ReportView
        report={report}
        provider={provider}
        serviceDate={serviceDate}
        onReset={handleReset}
      />
    );
  } else if (view === "consent") {
    viewContent = <ConsentView onSubmit={handleConsentSubmit} />;
  } else if (view === "history") {
    viewContent = (
      <BillHistoryView
        onViewBill={handleViewSavedBill}
        onNavigate={handleNavigate}
      />
    );
  } else if (view === "account") {
    viewContent = (
      <OnboardingView
        onSubmit={handleOnboardingSubmit}
        initialData={onboardingData}
        isAccountView
        consentData={consentData}
        onDeleteAccount={handleDeleteAccount}
        session={session}
      />
    );
  } else if (view === "onboarding") {
    viewContent = (
      <OnboardingView
        onSubmit={handleOnboardingSubmit}
        initialData={onboardingData}
      />
    );
  } else {
    viewContent = (
      <UploadView
        onFileSelect={handleFileSelect}
        onSampleBill={handleSampleBill}
      />
    );
  }

  const showHeader = view !== "consent" && view !== "onboarding";

  return (
    <>
      {showHeader && (
        <AppHeader
          onNavigate={handleNavigate}
          currentView={view}
          session={session}
          onSignOut={handleSignOut}
        />
      )}
      {viewContent}
      <Toast message={toast.message} visible={toast.visible} />
    </>
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
