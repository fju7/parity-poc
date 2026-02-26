import { useState, useCallback, useEffect, useRef } from "react";
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
import ManualEntryView from "./components/ManualEntryView.jsx";
import AIParseModal from "./components/AIParseModal.jsx";
import AppHeader from "./components/AppHeader.jsx";
import Toast from "./components/Toast.jsx";
import extractBillData from "./modules/extractBillData.js";
import { detectEOB } from "./modules/eobExtractor.js";
import { lookupNPPES } from "./modules/nppesLookup.js";
import scoreAnomalies from "./modules/scoreAnomalies.js";
import runCodingIntelligence from "./modules/codingIntelligence.js";
import EOBDetectedView from "./components/EOBDetectedView.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 60000;
const COLD_START_THRESHOLD_MS = 8000;
const KEEPALIVE_INTERVAL_MS = 4 * 60 * 1000; // 4 minutes

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
  if (rel === "manual-entry") return "manual-entry";
  return "onboarding"; // default — auth flow will override
}

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  // Auth state
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Views: "consent" | "onboarding" | "upload" | "processing" | "report" | "error" | "itemized-request" | "history" | "manual-entry"
  const [view, setView] = useState(() => viewFromPath(location.pathname));
  const [processingStep, setProcessingStep] = useState(0);
  const [report, setReport] = useState(null);
  const [provider, setProvider] = useState(null);
  const [serviceDate, setServiceDate] = useState("");
  const [error, setError] = useState({ title: "", message: "" });
  const [eobData, setEobData] = useState(null);
  const [eobExtracted, setEobExtracted] = useState(null);
  const [eobParseError, setEobParseError] = useState(false);
  const [eobOverloaded, setEobOverloaded] = useState(false);
  const [eobPages, setEobPages] = useState(null);
  const [nppesResult, setNppesResult] = useState(null);
  const [nppesLoading, setNppesLoading] = useState(false);
  const [itemizedReason, setItemizedReason] = useState(null);
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

  // AI parsing state
  const [showAIModal, setShowAIModal] = useState(false);
  const [pendingBillData, setPendingBillData] = useState(null);
  const pendingFileRef = useRef(null);
  const [parsingMethod, setParsingMethod] = useState("standard");

  // Cold-start "waking up" indicator
  const [slowServer, setSlowServer] = useState(false);

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

  // ----- Backend keepalive: ping every 4 min while tab is visible -----
  const keepaliveRef = useRef(null);

  useEffect(() => {
    function startKeepalive() {
      stopKeepalive();
      keepaliveRef.current = setInterval(() => {
        fetch(`${API_BASE}/`).catch(() => {});
      }, KEEPALIVE_INTERVAL_MS);
    }

    function stopKeepalive() {
      if (keepaliveRef.current) {
        clearInterval(keepaliveRef.current);
        keepaliveRef.current = null;
      }
    }

    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        startKeepalive();
      } else {
        stopKeepalive();
      }
    }

    // Start immediately if tab is visible and user is signed in
    if (session && document.visibilityState === "visible") {
      startKeepalive();
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      stopKeepalive();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [session]);

  // ----- Fetch profile from Supabase and pre-fill onboarding -----
  const fetchProfile = async (userId, email) => {
    try {
      const { data } = await supabase
        .from("profiles")
        .select("first_name, last_name, date_of_birth, street_address, city, state, zip_code, phone, consent_agreed_at, consent_analytics, consent_employer, employer_code")
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
          employerCode: data.employer_code || "",
          employerCompany: "",
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
            if (urlView === "history" || urlView === "account" || urlView === "manual-entry") {
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
    setEobExtracted(null);
    setEobParseError(false);
    setEobOverloaded(false);
    setEobPages(null);
    setNppesResult(null);
    setNppesLoading(false);
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
    setEobExtracted(null);
    setEobParseError(false);
    setEobOverloaded(false);
    setEobPages(null);
    setNppesResult(null);
    setNppesLoading(false);
    setItemizedReason(null);
    setShowAIModal(false);
    setPendingBillData(null);
    pendingFileRef.current = null;
    setParsingMethod("standard");
  }, [navigate]);

  // ----- Navigation -----
  const handleNavigate = useCallback((target) => {
    if (target === "upload") {
      navigate("/parity-health/");
    } else if (target === "history") {
      navigate("/parity-health/history");
    } else if (target === "account") {
      navigate("/parity-health/account");
    } else if (target === "manual-entry") {
      navigate("/parity-health/manual-entry");
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
      setEobExtracted(null);
      setEobParseError(false);
      setNppesResult(null);
      setNppesLoading(false);
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
        parsingMethod: bill.parsingMethod || "standard",
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
    async (scored, billProvider, billServiceDate, method) => {
      try {
        await saveBill({
          provider: billProvider || { name: "Unknown Provider" },
          serviceDate: billServiceDate || null,
          summary: scored.summary,
          lineItems: scored.lineItems,
          partialWarning: scored.partialWarning || null,
          codingAlerts: scored.codingAlerts || [],
          codingSummary: scored.codingSummary || null,
          parsingMethod: method || "standard",
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
    async ({ consentAnalytics: analytics, consentEmployer: employer, employerCode: code }) => {
      setConsentData({ consentAnalytics: analytics, consentEmployer: employer });
      setHasCompletedConsent(true);

      if (code) {
        setOnboardingData((prev) => ({ ...prev, employerCode: code }));
      }

      if (session?.user) {
        try {
          const upsertData = {
            id: session.user.id,
            email: session.user.email,
            consent_analytics: analytics,
            consent_employer: employer,
            consent_agreed_at: new Date().toISOString(),
          };
          if (code) upsertData.employer_code = code;
          await supabase.from("profiles").upsert(upsertData);
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
    async (billData, method = "standard") => {
      // Guard: if no line items, route to itemized bill request
      if (!billData.lineItems || billData.lineItems.length === 0) {
        setEobData(billData);
        setItemizedReason("no_codes");
        setView("itemized-request");
        return;
      }

      // Step 2: Look up benchmark rates
      setProcessingStep(1);
      setSlowServer(false);

      // Show "waking up" message if the request takes longer than 8s
      const slowTimer = setTimeout(() => setSlowServer(true), COLD_START_THRESHOLD_MS);

      let benchmarkResponse;
      try {
        benchmarkResponse = await fetchBenchmark(
          billData.provider.zip,
          billData.lineItems,
          billData.serviceDate
        );
      } catch (err) {
        clearTimeout(slowTimer);
        setSlowServer(false);
        setError({
          title: "Rate Lookup Unavailable",
          message:
            "Rate lookup is temporarily unavailable. Please try again in a moment.",
        });
        setView("error");
        return;
      }
      clearTimeout(slowTimer);
      setSlowServer(false);

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
      scored.parsingMethod = method;

      // Small delay so the user sees the final step
      await delay(400);

      setReport(scored);
      setProvider(billData.provider);
      setServiceDate(billData.serviceDate);
      setView("report");

      // Auto-save to IndexedDB (non-blocking)
      saveBillLocally(scored, billData.provider, billData.serviceDate, method);

      // Fire-and-forget employer contribution (non-blocking)
      if (consentData.consentEmployer && onboardingData.employerCode) {
        contributeToEmployer(scored, billData, session.user.id, onboardingData.employerCode);
      }
    },
    [saveBillLocally, consentData, onboardingData, session]
  );

  // ----- Standard PDF parsing flow -----
  const handleFileSelect = useCallback(
    async (file) => {
      setView("processing");
      setProcessingStep(0);
      pendingFileRef.current = file;

      try {
        // Step 1: Extract bill data from PDF
        const billData = await extractBillData(file);

        // EOB detection — before AI modal or pipeline
        if (billData.rawText && detectEOB(billData.rawText)) {
          setEobData(billData);
          setProcessingStep(0); // "Reading your document..."
          setSlowServer(false);
          setEobParseError(false);

          // Use text-based AI extraction (fast/cheap) with image fallback for scanned PDFs
          const slowTimer = setTimeout(() => setSlowServer(true), COLD_START_THRESHOLD_MS);
          try {
            let response;
            if (billData.rawText && billData.rawText.trim().length >= 100) {
              // Text-based extraction — no image rendering needed
              response = await fetchWithTimeout(
                `${API_BASE}/api/parse-eob-text`,
                { text: billData.rawText }
              );
            } else {
              // Fallback: scanned/image-only PDF — render to images
              const pages = await renderPDFToBase64(file);
              setEobPages(pages);
              response = await fetchWithTimeout(
                `${API_BASE}/api/parse-eob`,
                { pages }
              );
            }
            clearTimeout(slowTimer);
            setSlowServer(false);
            if (response.error === "overloaded") {
              setEobExtracted({});
              setEobOverloaded(true);
            } else {
              setEobExtracted(response);
            }
          } catch (err) {
            clearTimeout(slowTimer);
            setSlowServer(false);
            console.warn("EOB AI extraction failed:", err.message);
            setEobExtracted({});
            setEobParseError(true);
          }
          setView("eob-detected");
          return;
        }

        // Check for empty extraction — show itemized bill request flow
        if (!billData.lineItems || billData.lineItems.length === 0) {
          setPendingBillData(billData);
          setShowAIModal(true);
          setView("upload");
          return;
        }

        // If fewer than 2 items found, offer AI parsing
        if (billData.lineItems.length < 2) {
          setPendingBillData(billData);
          setShowAIModal(true);
          setView("upload");
          return;
        }

        setParsingMethod("standard");
        await runPipeline(billData, "standard");
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

  // ----- "Having trouble?" link from upload screen -----
  const handleHavingTrouble = useCallback(() => {
    setPendingBillData(null);
    setShowAIModal(true);
  }, []);

  // ----- AI parsing flow -----
  const handleAIParse = useCallback(async () => {
    setShowAIModal(false);
    const file = pendingFileRef.current;

    if (!file) {
      // No file available — go to manual entry
      navigate("/parity-health/manual-entry");
      setView("manual-entry");
      return;
    }

    setView("processing");
    setProcessingStep(0);

    try {
      // Render PDF pages to base64 images
      const pages = await renderPDFToBase64(file);

      setProcessingStep(1);

      // Call AI parsing endpoint
      const response = await fetch(`${API_BASE}/api/parse-with-ai`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pages }),
      });

      if (!response.ok) {
        throw new Error(`AI parse error: ${response.status}`);
      }

      const aiResult = await response.json();

      // Convert AI result to the billData format the pipeline expects
      const billData = {
        provider: {
          name: aiResult.provider_name || "Unknown Provider",
          zip: "00000", // AI parse doesn't get ZIP from images
          npi: null,
        },
        serviceDate: aiResult.service_date || "",
        parsingMethod: "ai",
        insuranceName: aiResult.insurance_name || null,
        lineItems: (aiResult.line_items || [])
          .filter((li) => li.cpt_code || li.revenue_code)
          .map((li) => ({
            code: li.cpt_code || li.revenue_code || "",
            codeType: li.cpt_code ? "CPT" : "REVENUE",
            description: li.description || "Unknown procedure",
            billedAmount: li.billed_amount || 0,
            quantity: li.quantity || 1,
            modifier: li.modifier || null,
          })),
      };

      if (billData.lineItems.length === 0) {
        // AI parsed successfully but found no codes — route to itemized request
        setEobData(billData);
        setItemizedReason("no_codes");
        setView("itemized-request");
        return;
      }

      setParsingMethod("ai");
      await runPipeline(billData, "ai");
    } catch (err) {
      console.error("AI parsing error:", err);
      setError({
        title: "AI Reading Error",
        message:
          "AI reading encountered an error. Please try a clearer image or enter manually.",
      });
      setView("error");
    }
  }, [navigate, runPipeline]);

  // ----- AI modal: skip and use standard results -----
  const handleAISkip = useCallback(async () => {
    setShowAIModal(false);
    if (pendingBillData && pendingBillData.lineItems?.length > 0) {
      setView("processing");
      setProcessingStep(0);
      await delay(300);
      setParsingMethod("standard");
      await runPipeline(pendingBillData, "standard");
    } else {
      // No items at all — show itemized request
      setEobData(pendingBillData);
      setItemizedReason("no_codes");
      setView("itemized-request");
    }
  }, [pendingBillData, runPipeline]);

  // ----- Manual entry flow -----
  const handleManualEntry = useCallback(() => {
    setShowAIModal(false);
    navigate("/parity-health/manual-entry");
    setView("manual-entry");
  }, [navigate]);

  const handleManualSubmit = useCallback(
    async (billData) => {
      setView("processing");
      setProcessingStep(0);
      await delay(300);

      try {
        setParsingMethod("manual");
        await runPipeline(billData, "manual");
      } catch (err) {
        console.error("Manual entry pipeline error:", err);
        setError({
          title: "Processing Error",
          message: "An error occurred while analyzing the bill.",
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
      await runPipeline(SAMPLE_BILL, "standard");
    } catch (err) {
      console.error("Sample bill error:", err);
      setError({
        title: "Processing Error",
        message: "An error occurred while processing the sample bill.",
      });
      setView("error");
    }
  }, [runPipeline]);

  // ----- EOB: retry parse when overloaded -----
  const handleRetryEobParse = useCallback(async () => {
    setEobOverloaded(false);
    setEobParseError(false);
    setProcessingStep(0);
    setSlowServer(false);
    setView("processing");

    const slowTimer = setTimeout(() => setSlowServer(true), COLD_START_THRESHOLD_MS);
    try {
      let response;
      const rawText = eobData?.rawText;
      if (rawText && rawText.trim().length >= 100) {
        response = await fetchWithTimeout(
          `${API_BASE}/api/parse-eob-text`,
          { text: rawText }
        );
      } else if (eobPages) {
        response = await fetchWithTimeout(
          `${API_BASE}/api/parse-eob`,
          { pages: eobPages }
        );
      } else {
        throw new Error("No EOB data available for retry");
      }
      clearTimeout(slowTimer);
      setSlowServer(false);
      if (response.error === "overloaded") {
        setEobExtracted({});
        setEobOverloaded(true);
      } else {
        setEobExtracted(response);
        setEobOverloaded(false);
      }
    } catch (err) {
      clearTimeout(slowTimer);
      setSlowServer(false);
      console.warn("EOB AI retry failed:", err.message);
      setEobExtracted({});
      setEobParseError(true);
    }
    setView("eob-detected");
  }, [eobData, eobPages]);

  // ----- EOB: request itemized bill (triggers NPPES lookup) -----
  const handleRequestItemizedFromEOB = useCallback(async () => {
    setItemizedReason("eob_detected");
    setNppesLoading(true);
    setNppesResult(null);
    setView("itemized-request");

    // Look up provider contact info via NPPES (AI fields use snake_case)
    const providerName = eobExtracted?.provider_name || eobData?.provider?.name || "";
    console.log("[EOB→NPPES] Provider name for lookup:", providerName);
    if (providerName) {
      try {
        const result = await lookupNPPES(providerName);
        console.log("[EOB→NPPES] Result:", result);
        setNppesResult(result);
      } catch (err) {
        console.warn("[EOB→NPPES] Lookup error:", err);
        setNppesResult(null);
      }
    }
    setNppesLoading(false);
  }, [eobExtracted, eobData]);

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
    viewContent = <ProcessingView currentStep={processingStep} slowServer={slowServer} />;
  } else if (view === "error") {
    viewContent = (
      <ErrorView
        title={error.title}
        message={error.message}
        onReset={handleReset}
      />
    );
  } else if (view === "eob-detected") {
    viewContent = (
      <EOBDetectedView
        eobExtracted={eobExtracted}
        eobParseError={eobParseError}
        eobOverloaded={eobOverloaded}
        onRequestItemized={handleRequestItemizedFromEOB}
        onRetryParse={handleRetryEobParse}
        onUploadItemized={handleReset}
      />
    );
  } else if (view === "itemized-request") {
    viewContent = (
      <ItemizedBillRequestView
        eobData={eobData}
        eobExtracted={eobExtracted}
        nppesResult={nppesResult}
        nppesLoading={nppesLoading}
        onboardingData={onboardingData}
        onReset={handleReset}
        reason={itemizedReason}
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
  } else if (view === "manual-entry") {
    viewContent = (
      <ManualEntryView
        onSubmit={handleManualSubmit}
        onCancel={handleReset}
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
        onManualEntry={handleManualEntry}
        onHavingTrouble={handleHavingTrouble}
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
      {showAIModal && (
        <AIParseModal
          onUseAI={handleAIParse}
          onManualEntry={handleManualEntry}
          onSkip={handleAISkip}
          itemCount={pendingBillData?.lineItems?.length || 0}
        />
      )}
      <Toast message={toast.message} visible={toast.visible} />
    </>
  );
}

// ---------------------------------------------------------------------------
// PDF to base64 image rendering (for AI parsing)
// ---------------------------------------------------------------------------

async function renderPDFToBase64(file) {
  const pdfjsLib = await import("pdfjs-dist");

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const pages = [];

  // Render each page at 2x scale for better OCR quality
  const scale = 2.0;

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const viewport = page.getViewport({ scale });

    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext("2d");

    await page.render({ canvasContext: ctx, viewport }).promise;

    // Convert to base64 JPEG (much smaller than PNG, better for API limits)
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    // Strip the data:image/jpeg;base64, prefix
    const base64 = dataUrl.split(",")[1];
    pages.push(base64);
  }

  return pages;
}

// ---------------------------------------------------------------------------
// API call with timeout + retry
// ---------------------------------------------------------------------------

async function fetchBenchmark(zipCode, lineItems, serviceDate) {
  const body = {
    zipCode: zipCode || "00000",
    lineItems: lineItems.map((i) => ({
      code: i.code,
      codeType: i.codeType,
      billedAmount: i.billedAmount,
    })),
  };
  if (serviceDate) {
    body.serviceDate = serviceDate;
  }

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
      // Parse 503 overloaded responses so the caller can handle them
      if (response.status === 503) {
        try {
          const body = await response.json();
          if (body.error === "overloaded") return body;
        } catch { /* fall through to throw */ }
      }
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

// ---------------------------------------------------------------------------
// Fire-and-forget: contribute de-identified billing data to employer dashboard
// ---------------------------------------------------------------------------

async function contributeToEmployer(scored, billData, userId, employerCode) {
  try {
    const lineItems = (scored.lineItems || []).map((item) => ({
      code: item.code || "",
      description: item.description || "",
      billedAmount: item.billedAmount || 0,
      benchmarkRate: item.benchmarkRate || null,
      anomalyScore: item.anomalyScore || null,
      flagged: item.flagged || false,
      flagReason: item.flagReason || null,
      codingFlags: item.codingFlags || null,
    }));

    await fetch(`${API_BASE}/api/employer/contribute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        employer_code: employerCode,
        provider_name: billData.provider?.name || null,
        line_items: lineItems,
      }),
    });
  } catch {
    // Non-blocking — silently ignore contribution failures
  }
}
