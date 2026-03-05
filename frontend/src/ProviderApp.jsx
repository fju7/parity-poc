import { useState, useEffect, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import * as XLSX from "xlsx";
import { supabase } from "./lib/supabase.js";
import { LogoIcon } from "./components/CivicScaleHomepage.jsx";
import ProviderAuditPage from "./components/ProviderAuditPage.jsx";
import ProviderAuditReport from "./components/ProviderAuditReport.jsx";
import "./components/CivicScaleHomepage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SPECIALTIES = [
  "Internal Medicine",
  "Family Medicine",
  "Cardiology",
  "Orthopedics",
  "Dermatology",
  "Radiology",
  "Pathology/Lab",
  "Other",
];

export default function ProviderApp() {
  const location = useLocation();

  // "landing" | "sent" | "onboarding" | "dashboard"
  const [view, setView] = useState(null);
  const [showAuditReport, setShowAuditReport] = useState(false);
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [authError, setAuthError] = useState("");
  const [activeTab, setActiveTab] = useState("home");

  // Onboarding form state
  const [formData, setFormData] = useState({
    practice_name: "",
    specialty: "",
    npi: "",
    zip_code: "",
  });
  const [formError, setFormError] = useState("");
  const [formSaving, setFormSaving] = useState(false);

  // ── Contract Integrity state ──
  const [contractStep, setContractStep] = useState("upload-rates");
  const [contractError, setContractError] = useState("");
  const [parsedRates, setParsedRates] = useState(null); // { payers, rows }
  const [savingRates, setSavingRates] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState("");
  const [savedContractRates, setSavedContractRates] = useState({}); // {cpt: rate}
  const [savedPayerName, setSavedPayerName] = useState("");
  const [parsedRemittance, setParsedRemittance] = useState(null);
  const [parsedRemittances, setParsedRemittances] = useState([]); // multi-file results
  const [uploadProgress, setUploadProgress] = useState(null); // { total, done, errors[] }
  const [ratesMethod, setRatesMethod] = useState(null); // null | "excel" | "pdf" | "medicare-pct" | "paste" | "photo"
  const [extractingRates, setExtractingRates] = useState(false);
  const [savedPayers, setSavedPayers] = useState([]); // [{name, rates: {cpt: rate}, codeCount}]
  const [filePayerMap, setFilePayerMap] = useState({}); // {filename: assignedPayerName}
  const [analysisResults, setAnalysisResults] = useState([]); // [{payer_name, result, denial_intel}]
  const [selectedPayerIdx, setSelectedPayerIdx] = useState(0);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sortField, setSortField] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  // ── Coding Analysis state ──
  const [codingLines, setCodingLines] = useState([
    { cpt_code: "", units: 1, billed_amount: 0 },
  ]);
  const [codingSpecialty, setCodingSpecialty] = useState("");
  const [codingDateStart, setCodingDateStart] = useState("");
  const [codingDateEnd, setCodingDateEnd] = useState("");
  const [codingResult, setCodingResult] = useState(null);
  const [codingLoading, setCodingLoading] = useState(false);
  const [codingError, setCodingError] = useState("");

  // ── Denial Intelligence state ──
  const [denialIntel, setDenialIntel] = useState(null);
  const [denialLoading, setDenialLoading] = useState(false);

  // ── Dashboard home state ──
  const [recentAnalyses, setRecentAnalyses] = useState(null);
  const [loadingRecent, setLoadingRecent] = useState(false);

  // ── Historical report viewer state ──
  const [historicalReport, setHistoricalReport] = useState(null); // full analysis record
  const [historicalLoading, setHistoricalLoading] = useState(false);

  // Auth bootstrap
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setView("landing");
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setSession(null);
        setProfile(null);
        setView("landing");
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function loadProfile(userId) {
    const { data, error } = await supabase
      .from("provider_profiles")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) {
      console.error("[ProviderApp] Error loading profile:", error);
      setView("onboarding");
      return;
    }

    if (data) {
      setProfile(data);
      setView("dashboard");
    } else {
      setView("onboarding");
    }
  }

  // Magic link send
  const handleSendLink = useCallback(async (e) => {
    e.preventDefault();
    setSending(true);
    setAuthError("");

    const origin = window.location.hostname === "localhost"
      ? window.location.origin
      : "https://civicscale.ai";

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: origin + "/provider" },
    });

    setSending(false);
    if (error) {
      setAuthError(error.message);
    } else {
      setView("sent");
    }
  }, [email]);

  // Onboarding submit
  const handleOnboardingSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!formData.practice_name.trim()) {
      setFormError("Practice name is required.");
      return;
    }
    setFormSaving(true);
    setFormError("");

    const { data, error } = await supabase
      .from("provider_profiles")
      .insert({
        user_id: session.user.id,
        practice_name: formData.practice_name.trim(),
        specialty: formData.specialty || null,
        npi: formData.npi.trim() || null,
        zip_code: formData.zip_code.trim() || null,
      })
      .select()
      .single();

    setFormSaving(false);
    if (error) {
      setFormError(error.message);
    } else {
      setProfile(data);
      setView("dashboard");
    }
  }, [session, formData]);

  // Sign out
  const handleSignOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
    setView("landing");
  }, []);

  // ── Contract Integrity handlers ──

  function resetContract() {
    setContractStep("upload-rates");
    setContractError("");
    setSaveSuccess("");
    setParsedRates(null);
    setSavedContractRates({});
    setSavedPayerName("");
    setParsedRemittance(null);
    setAnalysisResult(null);
    setDenialIntel(null);
    setDenialLoading(false);
    setSortField(null);
    setSortDir("asc");
    setRatesMethod(null);
    setExtractingRates(false);
    setSavedPayers([]);
    setFilePayerMap({});
    setAnalysisResults([]);
    setSelectedPayerIdx(0);
  }

  async function handleDownloadTemplate() {
    try {
      const resp = await fetch(`${API_BASE}/api/provider/contract-template`);
      if (!resp.ok) throw new Error("Failed to download template");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "contract_rates_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setContractError("Could not download template. Is the backend running?");
    }
  }

  function handleRatesFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setContractError("");

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(new Uint8Array(evt.target.result), { type: "array" });
        // Find "Contract Rates" sheet or use first sheet
        const sheetName = wb.SheetNames.find(n => n.toLowerCase().includes("contract")) || wb.SheetNames[0];
        const ws = wb.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });

        if (data.length < 5) {
          setContractError("Template appears empty. Please fill in CPT codes and rates starting at row 5.");
          return;
        }

        // Row 4 (index 3) = payer headers starting at column D (index 3)
        const headerRow = data[3] || [];
        const payers = [];
        for (let i = 3; i < headerRow.length; i++) {
          const name = String(headerRow[i] || "").trim();
          if (name) payers.push({ index: i, name });
        }

        if (payers.length === 0) {
          setContractError("No payer names found in row 4 (columns D onward). Check the template format.");
          return;
        }

        // Rows 5+ (index 4+): Col A = CPT, Col B = description, Cols D+ = rates
        const rows = [];
        for (let r = 4; r < data.length; r++) {
          const row = data[r];
          const cpt = String(row[0] || "").trim();
          if (!cpt) continue;
          const desc = String(row[1] || "").trim();
          const rates = {};
          for (const p of payers) {
            const val = parseFloat(row[p.index]);
            if (!isNaN(val) && val > 0) rates[p.name] = val;
          }
          if (Object.keys(rates).length > 0) {
            rows.push({ cpt, description: desc, rates });
          }
        }

        if (rows.length === 0) {
          setContractError("No valid CPT codes with rates found. Check that rates are in columns D onward.");
          return;
        }

        setParsedRates({ payers: payers.map(p => p.name), rows });
        setContractStep("preview-rates");
      } catch (err) {
        setContractError("Could not parse Excel file: " + err.message);
      }
    };
    reader.readAsArrayBuffer(file);
  }

  // Convert extraction API response to parsedRates format
  function applyExtractedRates(data) {
    const payerName = data.payer_name || "Payer";
    const rows = (data.rates || []).map(r => ({
      cpt: r.cpt,
      description: r.description || "",
      rates: { [payerName]: r.rate },
    }));
    if (rows.length === 0) {
      setContractError("No CPT codes with rates were found. Please try a different input method.");
      return;
    }
    setParsedRates({ payers: [payerName], rows });
    setContractStep("preview-rates");
  }

  async function handleRatesPdfUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtractingRates(true);
    setContractError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const resp = await fetch(`${API_BASE}/api/provider/extract-fee-schedule-pdf`, {
        method: "POST",
        body,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to extract rates from PDF");
      }
      applyExtractedRates(await resp.json());
    } catch (err) {
      setContractError("PDF extraction failed: " + err.message);
    }
    setExtractingRates(false);
  }

  async function handleRatesImageUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtractingRates(true);
    setContractError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const resp = await fetch(`${API_BASE}/api/provider/extract-fee-schedule-image`, {
        method: "POST",
        body,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to extract rates from image");
      }
      applyExtractedRates(await resp.json());
    } catch (err) {
      setContractError("Image extraction failed: " + err.message);
    }
    setExtractingRates(false);
  }

  async function handleRatesTextExtract(text) {
    setExtractingRates(true);
    setContractError("");
    try {
      const resp = await fetch(`${API_BASE}/api/provider/extract-fee-schedule-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to extract rates from text");
      }
      applyExtractedRates(await resp.json());
    } catch (err) {
      setContractError("Text extraction failed: " + err.message);
    }
    setExtractingRates(false);
  }

  async function handleMedicarePercentage(payerName, percentage, zipCode, effectiveDate) {
    setExtractingRates(true);
    setContractError("");
    try {
      const resp = await fetch(`${API_BASE}/api/provider/calculate-medicare-percentage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payer_name: payerName,
          percentage,
          zip_code: zipCode,
          effective_date: effectiveDate || "",
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to calculate rates");
      }
      const data = await resp.json();
      applyExtractedRates(data);
    } catch (err) {
      setContractError("Rate calculation failed: " + err.message);
    }
    setExtractingRates(false);
  }

  async function handleSaveRates() {
    if (!parsedRates || !session) return;
    setSavingRates(true);
    setContractError("");
    setSaveSuccess("");

    const firstPayer = parsedRates.payers[0];
    const ratesPayload = parsedRates.rows.map(r => ({
      cpt: r.cpt,
      description: r.description,
      rates: r.rates,
    }));

    try {
      const resp = await fetch(`${API_BASE}/api/provider/save-rates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          payer_name: firstPayer,
          rates: ratesPayload,
        }),
      });
      if (!resp.ok) throw new Error("Failed to save rates");
    } catch (err) {
      // Non-fatal — rates still usable in-session
      console.warn("Save to server failed:", err.message);
    }

    // Build payer entries for ALL payers in the file
    const newPayers = [];
    for (const payerName of parsedRates.payers) {
      const flatRates = {};
      let codeCount = 0;
      for (const row of parsedRates.rows) {
        if (row.rates[payerName]) {
          flatRates[row.cpt] = row.rates[payerName];
          codeCount++;
        }
      }
      if (codeCount > 0) {
        newPayers.push({ name: payerName, rates: flatRates, codeCount });
      }
    }
    setSavedPayers(prev => [...prev, ...newPayers]);

    // Backward compat: also set first payer as active
    if (newPayers.length > 0) {
      setSavedContractRates(newPayers[0].rates);
      setSavedPayerName(newPayers[0].name);
    }

    const payerLabel = newPayers.length === 1 ? newPayers[0].name : `${newPayers.length} payers`;
    setSaveSuccess(`Saved ${payerLabel} — ${parsedRates.rows.length} CPT codes. Add another payer or proceed to Step 2.`);
    setSavingRates(false);

    // Reset parsedRates so user can add another payer
    setParsedRates(null);
    setRatesMethod(null);
  }

  function handleRemovePayer(idx) {
    setSavedPayers(prev => prev.filter((_, i) => i !== idx));
  }

  async function handle835Upload(e) {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setContractError("");
    setContractStep("parsing-835");

    const files = Array.from(fileList);
    setUploadProgress({ total: files.length, done: 0, errors: [] });

    const body = new FormData();
    for (const f of files) {
      body.append("files", f);
    }

    try {
      const resp = await fetch(`${API_BASE}/api/provider/parse-835-batch`, {
        method: "POST",
        body,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to parse 835 files");
      }
      const data = await resp.json();
      setUploadProgress({ total: data.total_files, done: data.successful, errors: data.errors });

      if (data.results.length === 0) {
        throw new Error(
          data.errors.length > 0
            ? `All files failed: ${data.errors.map(e => `${e.filename}: ${e.error}`).join("; ")}`
            : "No valid 835 files found"
        );
      }

      setParsedRemittances(data.results);

      // Auto-map each 835 file to a saved payer by name matching
      if (savedPayers.length > 0) {
        const map = {};
        for (const r of data.results) {
          const detected = (r.payer_name || "").toLowerCase();
          const match = savedPayers.find(p =>
            detected === p.name.toLowerCase() ||
            detected.includes(p.name.toLowerCase()) ||
            p.name.toLowerCase().includes(detected)
          );
          if (match) map[r.filename] = match.name;
        }
        setFilePayerMap(map);
      }

      // Merge all results into a combined parsedRemittance for backward compat
      const merged = {
        payer_name: data.results[0].payer_name,
        payee_name: data.results[0].payee_name,
        production_date: data.results[0].production_date,
        total_billed: data.results.reduce((s, r) => s + (r.total_billed || 0), 0),
        total_paid: data.results.reduce((s, r) => s + (r.total_paid || 0), 0),
        claim_count: data.results.reduce((s, r) => s + (r.claim_count || 0), 0),
        claims: data.results.flatMap(r => r.claims || []),
        line_items: data.results.flatMap(r => r.line_items || []),
        _file_count: data.results.length,
        _payers: [...new Set(data.results.map(r => r.payer_name).filter(Boolean))],
      };
      setParsedRemittance(merged);
      setContractStep("preview-835");
    } catch (err) {
      setContractError(err.message);
      setContractStep("upload-835");
    }
  }

  async function handleRunAnalysis() {
    if (!parsedRemittance || !session) return;
    setContractStep("analyzing");
    setContractError("");
    setDenialIntel(null);
    setAnalysisResults([]);

    function buildLines(items) {
      return items.map(item => ({
        cpt_code: item.cpt_code,
        code_type: item.code_type || "CPT",
        billed_amount: item.billed_amount || 0,
        paid_amount: item.paid_amount || 0,
        units: item.units || 1,
        adjustments: (item.adjustments || []).map(a => a.code || "").join(", "),
        claim_id: item.claim_id || "",
      }));
    }

    async function analyzeOnePayer(payerName, rates, lineItems) {
      const resp = await fetch(`${API_BASE}/api/provider/analyze-contract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          payer_name: payerName,
          zip_code: profile?.zip_code || "",
          contract_rates: rates,
          remittance_lines: buildLines(lineItems),
        }),
      });
      if (!resp.ok) throw new Error(`Analysis failed for ${payerName}`);
      const result = await resp.json();

      // Fetch denial intelligence
      let denial = null;
      const denied = (result.line_items || []).filter(l => l.flag === "DENIED");
      if (denied.length > 0) {
        try {
          const dResp = await fetch(`${API_BASE}/api/provider/analyze-denials`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              payer_name: payerName,
              denied_lines: denied.map(l => ({
                cpt_code: l.cpt_code,
                billed_amount: l.billed_amount,
                adjustment_codes: l.adjustments || "",
                claim_id: l.claim_id || "",
              })),
            }),
          });
          if (dResp.ok) denial = await dResp.json();
        } catch { /* non-fatal */ }
      }
      return { payer_name: payerName, result, denial_intel: denial };
    }

    try {
      if (savedPayers.length > 0) {
        // Multi-payer: group 835 files by assigned payer and analyze each
        const allResults = [];
        for (const payer of savedPayers) {
          // Find 835 files assigned to this payer
          const payerFiles = parsedRemittances.filter(r => {
            const assigned = filePayerMap[r.filename];
            return assigned ? assigned === payer.name : (r.payer_name || "") === payer.name;
          });
          if (payerFiles.length === 0) continue;
          const lines = payerFiles.flatMap(f => f.line_items || []);
          if (lines.length === 0) continue;
          allResults.push(await analyzeOnePayer(payer.name, payer.rates, lines));
        }

        if (allResults.length === 0) {
          throw new Error("No 835 files matched any saved payer. Check payer assignments in Step 2.");
        }

        setAnalysisResults(allResults);
        setSelectedPayerIdx(0);
        setAnalysisResult(allResults[0].result);
        setDenialIntel(allResults[0].denial_intel);
        setDenialLoading(false);
        setContractStep("report");
      } else {
        // Single payer fallback
        const result = await analyzeOnePayer(
          savedPayerName || parsedRemittance.payer_name || "",
          savedContractRates,
          parsedRemittance.line_items,
        );
        setAnalysisResults([result]);
        setSelectedPayerIdx(0);
        setAnalysisResult(result.result);
        setDenialIntel(result.denial_intel);
        setDenialLoading(false);
        setContractStep("report");
      }
    } catch (err) {
      setContractError("Analysis failed: " + err.message);
      setContractStep("preview-835");
    }
  }

  function selectPayerResult(idx) {
    if (!analysisResults[idx]) return;
    setSelectedPayerIdx(idx);
    setAnalysisResult(analysisResults[idx].result);
    setDenialIntel(analysisResults[idx].denial_intel);
  }

  async function fetchDenialIntel(analysisData, payerName) {
    const deniedLines = (analysisData.line_items || []).filter(l => l.flag === "DENIED");
    if (deniedLines.length === 0) return;

    setDenialLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/provider/analyze-denials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payer_name: payerName,
          denied_lines: deniedLines.map(l => ({
            cpt_code: l.cpt_code,
            billed_amount: l.billed_amount,
            adjustment_codes: l.adjustments || "",
            claim_id: l.claim_id || "",
          })),
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setDenialIntel(data);
      }
    } catch (err) {
      console.warn("Denial intelligence failed:", err.message);
    }
    setDenialLoading(false);
  }

  function handleSort(field) {
    if (sortField === field) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  function getSortedLines() {
    if (!analysisResult?.line_items) return [];
    const lines = [...analysisResult.line_items];
    if (!sortField) return lines;

    const flagOrder = { UNDERPAID: 0, DENIED: 1, BILLED_BELOW: 2, OVERPAID: 3, NO_CONTRACT: 4, CORRECT: 5 };
    lines.sort((a, b) => {
      let va, vb;
      if (sortField === "flag") {
        va = flagOrder[a.flag] ?? 5;
        vb = flagOrder[b.flag] ?? 5;
      } else {
        va = a[sortField] ?? 0;
        vb = b[sortField] ?? 0;
      }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return lines;
  }

  // ── Coding Analysis handlers ──

  function addCodingLine() {
    setCodingLines(prev => [...prev, { cpt_code: "", units: 1, billed_amount: 0 }]);
  }

  function removeCodingLine(idx) {
    setCodingLines(prev => prev.filter((_, i) => i !== idx));
  }

  function updateCodingLine(idx, field, value) {
    setCodingLines(prev => prev.map((line, i) =>
      i === idx ? { ...line, [field]: value } : line
    ));
  }

  function resetCoding() {
    setCodingLines([{ cpt_code: "", units: 1, billed_amount: 0 }]);
    setCodingResult(null);
    setCodingError("");
    setCodingDateStart("");
    setCodingDateEnd("");
  }

  async function handleRunCodingAnalysis() {
    const validLines = codingLines.filter(l => l.cpt_code.trim());
    if (validLines.length === 0) {
      setCodingError("Add at least one CPT code.");
      return;
    }
    setCodingLoading(true);
    setCodingError("");
    setCodingResult(null);

    try {
      const resp = await fetch(`${API_BASE}/api/provider/analyze-coding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          specialty: codingSpecialty || profile?.specialty || "",
          date_range: codingDateStart && codingDateEnd ? `${codingDateStart} to ${codingDateEnd}` : "",
          lines: validLines.map(l => ({
            cpt_code: l.cpt_code.trim(),
            units: parseInt(l.units) || 1,
            billed_amount: parseFloat(l.billed_amount) || 0,
          })),
        }),
      });
      if (!resp.ok) throw new Error("Coding analysis failed");
      const data = await resp.json();
      setCodingResult(data);
    } catch (err) {
      setCodingError("Analysis failed: " + err.message);
    }
    setCodingLoading(false);
  }

  // ── Dashboard home: load recent analyses ──

  async function loadRecentAnalyses() {
    if (!session) return;
    setLoadingRecent(true);
    try {
      const { data, error } = await supabase
        .from("provider_analyses")
        .select("id, payer_name, production_date, total_billed, total_paid, underpayment, adherence_rate")
        .eq("user_id", session.user.id)
        .order("production_date", { ascending: false })
        .limit(5);
      if (!error) setRecentAnalyses(data || []);
    } catch {
      // Non-fatal
    }
    setLoadingRecent(false);
  }

  useEffect(() => {
    if (view === "dashboard" && activeTab === "home" && !historicalReport) {
      loadRecentAnalyses();
    }
  }, [view, activeTab, historicalReport]);

  async function loadHistoricalReport(analysisId) {
    setHistoricalLoading(true);
    try {
      const { data, error } = await supabase
        .from("provider_analyses")
        .select("*")
        .eq("id", analysisId)
        .single();
      if (!error && data) {
        setHistoricalReport(data);
      }
    } catch {
      // Non-fatal
    }
    setHistoricalLoading(false);
  }

  function getHistoricalSortedLines() {
    if (!historicalReport?.result_json?.line_items) return [];
    const lines = [...historicalReport.result_json.line_items];
    if (!sortField) return lines;
    const flagOrder = { UNDERPAID: 0, DENIED: 1, BILLED_BELOW: 2, OVERPAID: 3, NO_CONTRACT: 4, CORRECT: 5 };
    lines.sort((a, b) => {
      let va, vb;
      if (sortField === "flag") {
        va = flagOrder[a.flag] ?? 5;
        vb = flagOrder[b.flag] ?? 5;
      } else {
        va = a[sortField] ?? 0;
        vb = b[sortField] ?? 0;
      }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return lines;
  }

  // ── Shared nav ──
  const nav = (
    <nav className="cs-nav">
      <Link className="cs-nav-logo" to="/">
        <LogoIcon />
        <span className="cs-nav-wordmark">CivicScale</span>
      </Link>
      <div className="cs-nav-links">
        <Link to="/provider">For Providers</Link>
      </div>
    </nav>
  );

  // Route: /provider/audit → dedicated audit landing page + wizard
  if (location.pathname.includes("/provider/audit")) {
    return <ProviderAuditPage session={session} profile={profile} />;
  }

  // Audit report view (triggered from dashboard)
  if (showAuditReport && analysisResults.length > 0) {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ paddingTop: 80 }}>
          <ProviderAuditReport
            analysisResults={analysisResults}
            practiceInfo={profile}
            onClose={() => setShowAuditReport(false)}
          />
        </div>
      </div>
    );
  }

  // Don't render until auth check completes
  if (view === null) {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--cs-slate)" }}>Loading...</p>
        </div>
      </div>
    );
  }

  // ── LANDING VIEW ──
  if (view === "landing" || view === "sent") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Parity Provider
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 15 }}>
                Audit your payer contracts. Find what they owe you.
              </p>
            </div>

            {view === "sent" ? (
              <div style={{
                padding: 24, borderRadius: 12, border: "1px solid var(--cs-teal)",
                background: "var(--cs-teal-pale)", textAlign: "center"
              }}>
                <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginBottom: 4 }}>
                  Check your email
                </p>
                <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
                  We sent a login link to <strong>{email}</strong>. Click it to sign in.
                </p>
                <button
                  onClick={() => setView("landing")}
                  style={{
                    marginTop: 16, background: "none", border: "none",
                    color: "var(--cs-teal)", cursor: "pointer", fontSize: 14,
                    textDecoration: "underline",
                  }}
                >
                  Use a different email
                </button>
              </div>
            ) : (
              <form onSubmit={handleSendLink}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{
                    display: "block", fontSize: 14, fontWeight: 500,
                    color: "var(--cs-navy)", marginBottom: 6,
                  }}>
                    Email address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="doctor@yourpractice.com"
                    style={{
                      width: "100%", padding: "10px 12px", borderRadius: 8,
                      border: "1px solid var(--cs-border)", fontSize: 15,
                      outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>

                {authError && (
                  <div style={{
                    padding: 12, borderRadius: 8, background: "#fef2f2",
                    border: "1px solid #fecaca", marginBottom: 16,
                  }}>
                    <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{authError}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={sending}
                  className="cs-btn-primary"
                  style={{
                    width: "100%", justifyContent: "center",
                    opacity: sending ? 0.6 : 1,
                  }}
                >
                  {sending ? "Sending..." : "Send Login Link"}
                </button>

                <p style={{ textAlign: "center", fontSize: 13, color: "var(--cs-slate)", marginTop: 16 }}>
                  We'll send you a secure login link — no password needed.
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── ONBOARDING VIEW ──
  if (view === "onboarding") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 460, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 32 }}>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Set up your practice
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 14 }}>
                Tell us about your practice so we can tailor the analysis.
              </p>
            </div>

            <form onSubmit={handleOnboardingSubmit}>
              {/* Practice Name */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Practice name *</label>
                <input
                  type="text"
                  required
                  value={formData.practice_name}
                  onChange={(e) => setFormData(d => ({ ...d, practice_name: e.target.value }))}
                  placeholder="e.g. Sunshine Internal Medicine"
                  style={inputStyle}
                />
              </div>

              {/* Specialty */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Specialty</label>
                <select
                  value={formData.specialty}
                  onChange={(e) => setFormData(d => ({ ...d, specialty: e.target.value }))}
                  style={{ ...inputStyle, appearance: "auto" }}
                >
                  <option value="">Select a specialty</option>
                  {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* NPI */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>NPI number</label>
                <input
                  type="text"
                  value={formData.npi}
                  onChange={(e) => setFormData(d => ({ ...d, npi: e.target.value }))}
                  placeholder="Optional — 10-digit NPI"
                  maxLength={10}
                  style={inputStyle}
                />
              </div>

              {/* ZIP Code */}
              <div style={{ marginBottom: 24 }}>
                <label style={labelStyle}>Practice ZIP code</label>
                <input
                  type="text"
                  value={formData.zip_code}
                  onChange={(e) => setFormData(d => ({ ...d, zip_code: e.target.value }))}
                  placeholder="e.g. 33701"
                  maxLength={5}
                  style={inputStyle}
                />
              </div>

              {formError && (
                <div style={{
                  padding: 12, borderRadius: 8, background: "#fef2f2",
                  border: "1px solid #fecaca", marginBottom: 16,
                }}>
                  <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{formError}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={formSaving}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: formSaving ? 0.6 : 1,
                }}
              >
                {formSaving ? "Saving..." : "Continue to Dashboard"}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // ── DASHBOARD VIEW ──
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* Dashboard nav with practice info */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cs-navy)" }}>
              {profile?.practice_name}
            </div>
            {profile?.specialty && (
              <span style={{
                fontSize: 11, fontWeight: 500, color: "var(--cs-teal)",
                background: "var(--cs-teal-pale)", padding: "2px 8px",
                borderRadius: 4, display: "inline-block", marginTop: 2,
              }}>
                {profile.specialty}
              </span>
            )}
          </div>
          <button
            onClick={handleSignOut}
            style={{
              background: "none", border: "1px solid var(--cs-border)",
              borderRadius: 8, padding: "6px 14px", fontSize: 13,
              color: "var(--cs-slate)", cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </div>
      </nav>

      <div style={{ paddingTop: 88, maxWidth: 960, margin: "0 auto", padding: "88px 24px 60px" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
            Parity Provider
          </h1>
          <p style={{ color: "var(--cs-slate)", marginTop: 4, fontSize: 14 }}>
            Contract integrity and coding intelligence for your practice.
          </p>
        </div>

        {/* Tab buttons */}
        <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
          {["home", "contract", "coding"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "10px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
                cursor: "pointer", border: "1px solid",
                ...(activeTab === tab
                  ? { background: "var(--cs-navy)", color: "#fff", borderColor: "var(--cs-navy)" }
                  : { background: "#fff", color: "var(--cs-slate)", borderColor: "var(--cs-border)" }
                ),
              }}
            >
              {tab === "home" ? "Dashboard" : tab === "contract" ? "Contract Integrity" : "Coding Analysis"}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "home" ? (
          historicalReport ? (
            <HistoricalReportView
              record={historicalReport}
              sortField={sortField}
              sortDir={sortDir}
              onSort={handleSort}
              getSortedLines={getHistoricalSortedLines}
              onBack={() => { setHistoricalReport(null); setSortField(null); setSortDir("asc"); }}
            />
          ) : historicalLoading ? (
            <div style={{ textAlign: "center", padding: 48 }}>
              <Spinner />
              <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16 }}>Loading report...</p>
            </div>
          ) : (
            <DashboardHome
              recentAnalyses={recentAnalyses}
              loading={loadingRecent}
              onGoToContract={() => setActiveTab("contract")}
              onGoToCoding={() => setActiveTab("coding")}
              onViewAnalysis={(id) => loadHistoricalReport(id)}
            />
          )
        ) : activeTab === "contract" ? (
          <div>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 0, marginBottom: 24, lineHeight: 1.6 }}>
              Upload your 835 remittance file and contracted rates. We compare every paid amount against what your payer agreed to pay — by code, by claim, by payer.
            </p>
            <ContractIntegrityTab
            step={contractStep}
            error={contractError}
            parsedRates={parsedRates}
            savingRates={savingRates}
            saveSuccess={saveSuccess}
            parsedRemittance={parsedRemittance}
            parsedRemittances={parsedRemittances}
            uploadProgress={uploadProgress}
            analysisResult={analysisResult}
            denialIntel={denialIntel}
            denialLoading={denialLoading}
            sortField={sortField}
            sortDir={sortDir}
            ratesMethod={ratesMethod}
            extractingRates={extractingRates}
            zipCode={profile?.zip_code || ""}
            savedPayers={savedPayers}
            filePayerMap={filePayerMap}
            analysisResults={analysisResults}
            selectedPayerIdx={selectedPayerIdx}
            onDownloadTemplate={handleDownloadTemplate}
            onRatesFileUpload={handleRatesFileUpload}
            onSaveRates={handleSaveRates}
            on835Upload={handle835Upload}
            onRunAnalysis={handleRunAnalysis}
            onSort={handleSort}
            getSortedLines={getSortedLines}
            onReset={resetContract}
            onSetRatesMethod={setRatesMethod}
            onRatesPdfUpload={handleRatesPdfUpload}
            onRatesImageUpload={handleRatesImageUpload}
            onRatesTextExtract={handleRatesTextExtract}
            onMedicarePercentage={handleMedicarePercentage}
            onRemovePayer={handleRemovePayer}
            onFilePayerAssign={(filename, payer) => setFilePayerMap(prev => ({ ...prev, [filename]: payer }))}
            onSelectPayerResult={selectPayerResult}
            onGenerateReport={() => setShowAuditReport(true)}
          />
          </div>
        ) : (
          <div>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 0, marginBottom: 24, lineHeight: 1.6 }}>
              Enter your billing patterns. We identify undercoding risk and compliance issues — independent of payer, because correct coding is correct coding regardless of who is paying.
            </p>
            <CodingAnalysisTab
            lines={codingLines}
            specialty={codingSpecialty}
            dateStart={codingDateStart}
            dateEnd={codingDateEnd}
            result={codingResult}
            loading={codingLoading}
            error={codingError}
            profileSpecialty={profile?.specialty || ""}
            onAddLine={addCodingLine}
            onRemoveLine={removeCodingLine}
            onUpdateLine={updateCodingLine}
            onSetSpecialty={setCodingSpecialty}
            onSetDateStart={setCodingDateStart}
            onSetDateEnd={setCodingDateEnd}
            onRun={handleRunCodingAnalysis}
            onReset={resetCoding}
            onGoToContract={() => setActiveTab("contract")}
          />
          </div>
        )}
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          .cs-nav, button, .no-print { display: none !important; }
          body { font-size: 11px; color: #000; }
          div[style] { max-width: 100% !important; padding: 0 !important; }
        }
      `}</style>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Contract Integrity Tab Component
// ═══════════════════════════════════════════════════════════════════

function ContractIntegrityTab({
  step, error, parsedRates, savingRates, saveSuccess, parsedRemittance, parsedRemittances, uploadProgress, analysisResult,
  denialIntel, denialLoading,
  sortField, sortDir,
  ratesMethod, extractingRates, zipCode,
  savedPayers, filePayerMap, analysisResults, selectedPayerIdx,
  onDownloadTemplate, onRatesFileUpload, onSaveRates, on835Upload,
  onRunAnalysis, onSort, getSortedLines, onReset,
  onSetRatesMethod, onRatesPdfUpload, onRatesImageUpload, onRatesTextExtract, onMedicarePercentage,
  onRemovePayer, onFilePayerAssign, onSelectPayerResult,
  onGenerateReport,
}) {
  // ── Loading / analyzing overlays ──
  if (step === "parsing-835") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 48, textAlign: "center", background: "#fff" }}>
        <Spinner />
        <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
          Parsing remittance files...
        </p>
        <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
          Reading claims and payment data from 835 files.
        </p>
      </div>
    );
  }

  if (step === "analyzing") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 48, textAlign: "center", background: "#fff" }}>
        <Spinner />
        <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
          Comparing remittance against your contracted rates...
        </p>
        <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
          Checking each line item for underpayments, denials, and rate discrepancies.
        </p>
      </div>
    );
  }

  // ── Report view (replaces everything) ──
  if (step === "report" && analysisResult) {
    const s = analysisResult.summary || {};
    const sc = analysisResult.scorecard || {};
    const sortedLines = getSortedLines();
    const adherenceColor = s.adherence_rate >= 97 ? "#059669" : s.adherence_rate >= 90 ? "#d97706" : "#dc2626";
    const multiPayer = analysisResults.length > 1;

    return (
      <div>
        {/* Payer tabs (multi-payer only) */}
        {multiPayer && (
          <div style={{ display: "flex", gap: 0, marginBottom: 24, borderBottom: "2px solid var(--cs-border)", flexWrap: "wrap" }}>
            <button
              onClick={() => onSelectPayerResult(selectedPayerIdx)}
              style={{ display: "none" }}
            />
            {analysisResults.map((r, i) => (
              <button
                key={i}
                onClick={() => onSelectPayerResult(i)}
                style={{
                  padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                  border: "none", borderBottom: i === selectedPayerIdx ? "2px solid var(--cs-teal)" : "2px solid transparent",
                  background: "transparent",
                  color: i === selectedPayerIdx ? "var(--cs-teal)" : "var(--cs-slate)",
                  marginBottom: -2,
                }}
              >
                {r.payer_name}
              </button>
            ))}
          </div>
        )}

        {/* Cross-payer summary (multi-payer only) */}
        {multiPayer && (
          <div style={{
            background: "var(--cs-navy)", borderRadius: 12, padding: 24,
            marginBottom: 24, color: "#fff",
          }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Cross-Payer Summary</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {analysisResults.map((r, i) => {
                const rs = r.result?.summary || {};
                return (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 14 }}>
                    <span>{r.payer_name}</span>
                    <span>
                      {rs.total_underpayment > 0 ? (
                        <span style={{ color: "#fca5a5" }}>
                          Underpaid ${rs.total_underpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })} across {rs.underpaid_count} line{rs.underpaid_count !== 1 ? "s" : ""}
                        </span>
                      ) : (
                        <span style={{ color: "#86efac" }}>Within contract on all lines</span>
                      )}
                      {rs.denied_count > 0 && (
                        <span style={{ color: "#fcd34d", marginLeft: 12 }}>
                          {rs.denied_count} denied
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
            <div style={{ borderTop: "1px solid rgba(255,255,255,0.2)", marginTop: 12, paddingTop: 12, fontSize: 15, fontWeight: 600 }}>
              Total: ${analysisResults.reduce((s, r) => s + (r.result?.summary?.total_underpayment || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2 })} underpayment
            </div>
          </div>
        )}

        {/* Per-payer heading */}
        {multiPayer && (
          <h4 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 16 }}>
            {analysisResults[selectedPayerIdx]?.payer_name} — Detail
          </h4>
        )}

        {/* Summary Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 }}>
          <SummaryCard label="Total Contracted" value={`$${(s.total_contracted || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
          <SummaryCard label="Total Paid" value={`$${(s.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
          <SummaryCard label="Underpayment" value={`$${(s.total_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} color={s.total_underpayment > 0 ? "#dc2626" : undefined} />
          <SummaryCard label="Adherence Rate" value={`${s.adherence_rate || 0}%`} color={adherenceColor} />
        </div>

        {/* Underpayment callout */}
        {s.total_underpayment > 0 && (
          <div style={{
            background: "var(--cs-navy)", borderRadius: 12, padding: 24,
            marginBottom: 24, color: "#fff",
          }}>
            <div style={{ fontSize: 14, opacity: 0.8, marginBottom: 4 }}>Total Potential Underpayment</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>
              ${s.total_underpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: 13, marginTop: 8, opacity: 0.7 }}>
              {s.underpaid_count} underpaid line{s.underpaid_count !== 1 ? "s" : ""} + {s.denied_count} denied
              {" "}out of {s.line_count} total
            </div>
          </div>
        )}

        {/* Billed-Below-Contract callout (Capability 3) */}
        {s.billed_below_count > 0 && (
          <div style={{
            background: "#fff7ed", borderRadius: 12, padding: 20,
            marginBottom: 24, border: "1px solid #fb923c",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 18 }}>&#9888;</span>
              <span style={{ fontSize: 15, fontWeight: 600, color: "#9a3412" }}>
                Chargemaster Below Contract
              </span>
            </div>
            <p style={{ fontSize: 14, color: "#9a3412", margin: 0, lineHeight: 1.5 }}>
              {s.billed_below_count} line{s.billed_below_count !== 1 ? "s" : ""} billed below your contracted rate.
              Total chargemaster gap: <strong>${(s.total_chargemaster_gap || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>.
              Your payer will only pay up to the billed amount — update your chargemaster to capture the full contracted rate.
            </p>
          </div>
        )}

        {/* Flag breakdown */}
        <div style={{
          display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap",
        }}>
          <FlagBadge label="Correct" count={s.correct_count} color="#059669" bg="#ecfdf5" />
          <FlagBadge label="Underpaid" count={s.underpaid_count} color="#dc2626" bg="#fef2f2" />
          <FlagBadge label="Denied" count={s.denied_count} color="#d97706" bg="#fffbeb" />
          {s.billed_below_count > 0 && (
            <FlagBadge label="Below Contract" count={s.billed_below_count} color="#ea580c" bg="#fff7ed" />
          )}
          <FlagBadge label="Overpaid" count={s.overpaid_count} color="#2563eb" bg="#eff6ff" />
          <FlagBadge label="No Contract" count={s.no_contract_count} color="#6b7280" bg="#f3f4f6" />
        </div>

        {/* Practice Performance Scorecard (Capability 4) */}
        {(sc.clean_claim_rate != null) && (
          <div style={{ marginBottom: 24 }}>
            <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
              Practice Performance
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
              <KpiTile
                label="Clean Claim Rate"
                value={`${sc.clean_claim_rate}%`}
                benchmark="95%"
                color={sc.clean_claim_rate >= 95 ? "#059669" : sc.clean_claim_rate >= 85 ? "#d97706" : "#dc2626"}
              />
              <KpiTile
                label="Denial Rate"
                value={`${sc.denial_rate}%`}
                benchmark="<5%"
                color={sc.denial_rate <= 5 ? "#059669" : sc.denial_rate <= 10 ? "#d97706" : "#dc2626"}
              />
              <KpiTile
                label="Payer Adherence"
                value={`${sc.payer_adherence_rate}%`}
                benchmark="97%"
                color={sc.payer_adherence_rate >= 97 ? "#059669" : sc.payer_adherence_rate >= 90 ? "#d97706" : "#dc2626"}
              />
              <KpiTile
                label="Preventable Denials"
                value={`${sc.preventable_denial_rate}%`}
                benchmark="<30%"
                color={sc.preventable_denial_rate <= 30 ? "#059669" : sc.preventable_denial_rate <= 50 ? "#d97706" : "#dc2626"}
              />
            </div>
            {sc.narrative && (
              <div style={{
                padding: 16, borderRadius: 8, background: "#f0f9ff",
                border: "1px solid #bae6fd", fontSize: 14, color: "var(--cs-navy)",
                lineHeight: 1.6,
              }}>
                {sc.narrative}
              </div>
            )}
            {s.line_count < 50 && (
              <p style={{
                fontSize: 12, color: "var(--cs-slate)", marginTop: 12, marginBottom: 0,
                fontStyle: "italic",
              }}>
                Note: This analysis is based on {s.line_count} line items.
                Metrics are more meaningful with a full month of remittance data (typically 200+ line items).
              </p>
            )}
          </div>
        )}

        {/* Top Underpaid Codes */}
        {analysisResult.top_underpaid?.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
              Top Underpaid Codes
            </h4>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>CPT Code</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Total Underpayment</th>
                  </tr>
                </thead>
                <tbody>
                  {analysisResult.top_underpaid.map((item, i) => (
                    <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                      <td style={tdStyle}>{item.cpt_code}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#dc2626", fontWeight: 600 }}>
                        ${item.total_underpayment.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Denial Intelligence (Capability 1) */}
        {denialLoading && (
          <div style={{
            border: "1px solid var(--cs-border)", borderRadius: 12,
            padding: 24, marginBottom: 24, textAlign: "center", background: "#fff",
          }}>
            <Spinner />
            <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 12, fontSize: 14 }}>
              Analyzing denial patterns...
            </p>
          </div>
        )}
        {denialIntel && !denialIntel.error && (denialIntel.denial_types?.length > 0 || denialIntel.pattern_summary) && (
          <DenialIntelligenceSection intel={denialIntel} />
        )}

        {/* Full Line Items */}
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
            All Line Items ({sortedLines.length})
          </h4>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <SortTh field="cpt_code" label="CPT" current={sortField} dir={sortDir} onSort={onSort} />
                  <SortTh field="billed_amount" label="Billed" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="paid_amount" label="Paid" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="expected_payment" label="Expected" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="variance" label="Variance" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="flag" label="Flag" current={sortField} dir={sortDir} onSort={onSort} />
                  <th style={{ ...thStyle, textAlign: "right" }}>Medicare</th>
                </tr>
              </thead>
              <tbody>
                {sortedLines.map((item, i) => {
                  const rowBg = flagRowColor(item.flag, i);
                  return (
                    <tr key={i} style={{ background: rowBg }}>
                      <td style={tdStyle}>{item.cpt_code}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.billed_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.paid_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>
                        {item.expected_payment != null ? `$${item.expected_payment.toFixed(2)}` : "—"}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: varianceColor(item.variance) }}>
                        {item.variance != null ? `${item.variance >= 0 ? "+" : ""}$${item.variance.toFixed(2)}` : "—"}
                      </td>
                      <td style={tdStyle}>
                        <FlagPill flag={item.flag} />
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontSize: 12, color: "var(--cs-slate)" }}>
                        {item.medicare_rate ? `$${item.medicare_rate.toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{
          padding: 16, borderRadius: 8, background: "var(--cs-mist)",
          fontSize: 12, color: "var(--cs-slate)", marginBottom: 24,
          lineHeight: 1.6,
        }}>
          <strong>Disclaimer:</strong> This analysis compares payer remittance data against your self-reported contracted rates
          and publicly available CMS Medicare benchmarks. It is not legal or financial advice. Verify all findings with your
          payer contracts and consult a billing specialist before taking action.
        </div>

        {/* Action buttons */}
        <div className="no-print" style={{ display: "flex", gap: 12 }}>
          {onGenerateReport && (
            <button onClick={onGenerateReport} style={btnPrimary}>
              Generate Report
            </button>
          )}
          <button onClick={() => window.print()} style={btnOutline}>
            Print
          </button>
          <button onClick={onReset} style={btnOutline}>
            Start Over
          </button>
        </div>
      </div>
    );
  }

  // ── Default: show both steps always ──
  const ratesReady = !!parsedRates;
  const { payers = [], rows = [] } = parsedRates || {};
  const remittanceReady = !!parsedRemittance;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* ── STEP 1: Contract Rates ── */}
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 1: Contract Rates
        </h3>

        {/* Saved payers list */}
        {savedPayers.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {savedPayers.map((p, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 14px", borderRadius: 8,
                  background: "var(--cs-teal-pale)", border: "1px solid var(--cs-teal)",
                }}>
                  <span style={{ fontSize: 14, color: "var(--cs-navy)" }}>
                    <strong>{p.name}</strong> — {p.codeCount} CPT codes
                  </span>
                  <button
                    onClick={() => onRemovePayer(i)}
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      fontSize: 13, color: "var(--cs-slate)", padding: "2px 8px",
                    }}
                    title="Remove payer"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
            {saveSuccess && (
              <p style={{ fontSize: 13, color: "#059669", marginTop: 8, marginBottom: 0 }}>{saveSuccess}</p>
            )}
          </div>
        )}

        {ratesReady ? (
          <>
            <div style={{
              padding: 12, borderRadius: 8, background: "var(--cs-teal-pale)",
              border: "1px solid var(--cs-teal)", marginBottom: 20, fontSize: 14,
            }}>
              Found <strong>{rows.length}</strong> CPT codes across <strong>{payers.length}</strong> payer{payers.length !== 1 ? "s" : ""}: {payers.join(", ")}
            </div>

            <div style={{ overflowX: "auto", marginBottom: 20 }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>CPT</th>
                    <th style={thStyle}>Description</th>
                    {payers.map(p => <th key={p} style={{ ...thStyle, textAlign: "right" }}>{p}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 20).map((row, i) => (
                    <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                      <td style={tdStyle}>{row.cpt}</td>
                      <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.description}</td>
                      {payers.map(p => (
                        <td key={p} style={{ ...tdStyle, textAlign: "right" }}>
                          {row.rates[p] ? `$${row.rates[p].toFixed(2)}` : <span style={{ color: "#ccc" }}>—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length > 20 && (
                <p style={{ fontSize: 13, color: "var(--cs-slate)", marginTop: 8 }}>
                  Showing 20 of {rows.length} rows
                </p>
              )}
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <button onClick={onSaveRates} disabled={savingRates} style={{ ...btnPrimary, opacity: savingRates ? 0.6 : 1 }}>
                {savingRates ? "Saving..." : "Save Contract Rates"}
              </button>
              <label style={{ ...btnOutline, display: "inline-flex", alignItems: "center", cursor: "pointer" }}>
                Upload Different File
                <input type="file" accept=".xlsx,.xls" onChange={onRatesFileUpload} style={{ display: "none" }} />
              </label>
            </div>
            {saveSuccess && (
              <div style={{
                marginTop: 12, padding: 12, borderRadius: 8,
                background: "#ecfdf5", border: "1px solid #6ee7b7",
                fontSize: 14, color: "#065f46",
              }}>
                {saveSuccess}
              </div>
            )}
          </>
        ) : (
          <>
            {extractingRates ? (
              <div style={{ textAlign: "center", padding: 32 }}>
                <Spinner />
                <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
                  Extracting fee schedule rates...
                </p>
                <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
                  This may take a moment for large documents.
                </p>
              </div>
            ) : !ratesMethod ? (
              <>
                <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 20 }}>
                  Choose how you&rsquo;d like to enter your contract rates:
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                  {[
                    { key: "excel", title: "Excel/CSV Upload", desc: "Upload filled template with CPT codes and rates" },
                    { key: "pdf", title: "PDF Contract", desc: "AI extracts rates from your payer contract PDF" },
                    { key: "medicare-pct", title: "Percentage of Medicare", desc: "Enter payer's % of Medicare PFS rates (e.g., 115%)" },
                    { key: "paste", title: "Paste Text", desc: "Copy and paste rate table from email or portal" },
                    { key: "photo", title: "Photo / Screenshot", desc: "Upload an image of your fee schedule" },
                  ].map(m => (
                    <button
                      key={m.key}
                      onClick={() => onSetRatesMethod(m.key)}
                      style={{
                        display: "flex", alignItems: "center", padding: "14px 16px",
                        border: "1px solid var(--cs-border)", borderRadius: 8,
                        background: "#fff", cursor: "pointer", textAlign: "left",
                        transition: "border-color 0.15s",
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--cs-teal)"}
                      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--cs-border)"}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 14 }}>{m.title}</div>
                        <div style={{ fontSize: 12, color: "var(--cs-slate)", marginTop: 2 }}>{m.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
                <HelpSectionFeeSchedule />
              </>
            ) : ratesMethod === "excel" ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                  <button onClick={() => onSetRatesMethod(null)} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
                  <span style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 15 }}>Excel/CSV Upload</span>
                </div>
                <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
                  <button onClick={onDownloadTemplate} style={btnOutline}>
                    <DownloadIcon /> Download Template
                  </button>
                </div>
                <DropZone accept=".xlsx,.xls" onChange={onRatesFileUpload}>
                  Upload your completed contract rates spreadsheet (.xlsx)
                </DropZone>
                <div style={{ marginTop: 20, padding: 16, borderRadius: 8, background: "var(--cs-mist)", fontSize: 13, color: "var(--cs-slate)" }}>
                  <strong style={{ color: "var(--cs-navy)" }}>Template format:</strong> Row 4 contains payer names (columns D onward).
                  Rows 5+ contain CPT codes (column A), descriptions (column B), and contracted rates under each payer column.
                </div>
              </>
            ) : ratesMethod === "pdf" ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                  <button onClick={() => onSetRatesMethod(null)} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
                  <span style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 15 }}>Extract from PDF Contract</span>
                </div>
                <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 16 }}>
                  Upload your payer contract PDF. AI will identify and extract fee schedule tables with CPT codes and rates.
                </p>
                <DropZone accept=".pdf,application/pdf" onChange={onRatesPdfUpload}>
                  Upload payer contract PDF
                </DropZone>
              </>
            ) : ratesMethod === "medicare-pct" ? (
              <MedicarePercentageForm
                onBack={() => onSetRatesMethod(null)}
                onSubmit={onMedicarePercentage}
                defaultZip={zipCode}
              />
            ) : ratesMethod === "paste" ? (
              <PasteTextForm
                onBack={() => onSetRatesMethod(null)}
                onSubmit={onRatesTextExtract}
              />
            ) : ratesMethod === "photo" ? (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                  <button onClick={() => onSetRatesMethod(null)} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
                  <span style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 15 }}>Photo / Screenshot</span>
                </div>
                <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 16 }}>
                  Upload a photo of a printed fee schedule or a screenshot from your PM system.
                </p>
                <DropZone accept="image/*" onChange={onRatesImageUpload}>
                  Upload fee schedule image (JPG, PNG, etc.)
                </DropZone>
              </>
            ) : null}
          </>
        )}

        {error && !extractingRates && <ErrorBanner message={error} />}
      </div>

      {/* ── STEP 2: 835 Remittance ── */}
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 2: Upload 835 Remittance File
        </h3>

        {remittanceReady ? (
          <>
            {/* Remittance preview */}
            <div style={{
              padding: 12, borderRadius: 8, background: "var(--cs-teal-pale)",
              border: "1px solid var(--cs-teal)", marginBottom: 20, fontSize: 14,
            }}>
              {parsedRemittance._file_count > 1 && (
                <div style={{ marginBottom: 6, fontWeight: 600, color: "var(--cs-navy)" }}>
                  {parsedRemittance._file_count} files parsed
                  {parsedRemittance._payers?.length > 1 && <> from {parsedRemittance._payers.length} payers: {parsedRemittance._payers.join(", ")}</>}
                </div>
              )}
              Found <strong>{parsedRemittance.claim_count}</strong> claims,{" "}
              <strong>{(parsedRemittance.line_items || []).length}</strong> line items,{" "}
              <strong>${(parsedRemittance.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong> total paid
              {parsedRemittance._file_count <= 1 && parsedRemittance.payer_name && <> — from <strong>{parsedRemittance.payer_name}</strong></>}
              {parsedRemittance._file_count <= 1 && parsedRemittance.production_date && <> ({parsedRemittance.production_date})</>}
            </div>

            {/* Per-file breakdown with payer assignment */}
            {parsedRemittances.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                {savedPayers.length > 0 ? (
                  <>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 8 }}>
                      Payer assignment per file:
                    </p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {parsedRemittances.map((r, i) => {
                        const assigned = filePayerMap[r.filename];
                        const matched = assigned || "";
                        return (
                          <div key={i} style={{
                            fontSize: 13, padding: "8px 12px", borderRadius: 6,
                            background: matched ? "var(--cs-teal-pale)" : "#fef2f2",
                            border: matched ? "1px solid var(--cs-teal)" : "1px solid #fecaca",
                            display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12,
                            flexWrap: "wrap",
                          }}>
                            <span style={{ color: "var(--cs-navy)", fontWeight: 500 }}>
                              {r.filename}
                              <span style={{ color: "var(--cs-slate)", fontWeight: 400, marginLeft: 8 }}>
                                {r.claim_count} claims &middot; ${(r.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                              </span>
                            </span>
                            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ fontSize: 12, color: "var(--cs-slate)" }}>
                                Detected: {r.payer_name || "unknown"}
                              </span>
                              <select
                                value={matched}
                                onChange={e => onFilePayerAssign(r.filename, e.target.value)}
                                style={{
                                  padding: "4px 8px", borderRadius: 6, fontSize: 12,
                                  border: "1px solid var(--cs-border)", background: "#fff",
                                }}
                              >
                                <option value="">— Select payer —</option>
                                {savedPayers.map(p => (
                                  <option key={p.name} value={p.name}>{p.name}</option>
                                ))}
                              </select>
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : parsedRemittances.length > 1 ? (
                  <details>
                    <summary style={{ cursor: "pointer", fontSize: 13, color: "var(--cs-teal)", fontWeight: 600, marginBottom: 8 }}>
                      View per-file breakdown
                    </summary>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                      {parsedRemittances.map((r, i) => (
                        <div key={i} style={{ fontSize: 13, padding: 8, borderRadius: 6, background: "var(--cs-mist)", display: "flex", justifyContent: "space-between" }}>
                          <span style={{ color: "var(--cs-navy)", fontWeight: 500 }}>{r.filename}</span>
                          <span style={{ color: "var(--cs-slate)" }}>
                            {r.payer_name} &middot; {r.claim_count} claims &middot; ${(r.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                ) : null}
              </div>
            )}

            <div style={{ overflowX: "auto", marginBottom: 20 }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>CPT</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Billed</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Units</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Paid</th>
                    <th style={thStyle}>Adj Codes</th>
                  </tr>
                </thead>
                <tbody>
                  {(parsedRemittance.line_items || []).slice(0, 10).map((item, i) => (
                    <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                      <td style={tdStyle}>{item.cpt_code}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.billed_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>{item.units || 1}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.paid_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, fontSize: 12, color: "var(--cs-slate)" }}>
                        {(item.adjustments || []).map(a => a.code).filter(Boolean).join(", ") || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(parsedRemittance.line_items || []).length > 10 && (
                <p style={{ fontSize: 13, color: "var(--cs-slate)", marginTop: 8 }}>
                  Showing 10 of {(parsedRemittance.line_items || []).length} line items
                </p>
              )}
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <button
                onClick={onRunAnalysis}
                disabled={!ratesReady && savedPayers.length === 0}
                style={{ ...btnPrimary, opacity: (ratesReady || savedPayers.length > 0) ? 1 : 0.5 }}
              >
                Run Analysis{savedPayers.length > 1 ? ` (${savedPayers.length} payers)` : ""}
              </button>
              <label style={{ ...btnOutline, display: "inline-flex", alignItems: "center", cursor: "pointer" }}>
                Upload Different Files
                <input type="file" accept=".txt,.835,.edi,.zip,text/plain,application/zip" multiple onChange={on835Upload} style={{ display: "none" }} />
              </label>
              {!ratesReady && savedPayers.length === 0 && (
                <span style={{ fontSize: 13, color: "var(--cs-slate)" }}>Upload contract rates first to run analysis</span>
              )}
            </div>
          </>
        ) : (
          <>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 24 }}>
              Upload one or more Electronic Remittance Advice (ERA/835) files. You can select multiple files at once or upload a .zip archive.
            </p>

            <DropZone accept=".txt,.835,.edi,.zip,text/plain,application/zip" onChange={on835Upload} multiple>
              Accepted formats: .835, .edi, .txt, .zip &mdash; select multiple files or drop a zip
            </DropZone>

            {uploadProgress && uploadProgress.errors.length > 0 && (
              <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "#fef2f2", border: "1px solid #fecaca", fontSize: 13 }}>
                <strong style={{ color: "#991b1b" }}>{uploadProgress.errors.length} file{uploadProgress.errors.length !== 1 ? "s" : ""} failed:</strong>
                <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                  {uploadProgress.errors.map((e, i) => (
                    <li key={i} style={{ color: "#991b1b" }}>{e.filename}: {e.error}</li>
                  ))}
                </ul>
              </div>
            )}

            <HelpSection835 />
          </>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Start over */}
      {(ratesReady || remittanceReady || savedPayers.length > 0) && (
        <div>
          <button onClick={onReset} style={btnOutline}>Start Over</button>
        </div>
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Dashboard Home Component
// ═══════════════════════════════════════════════════════════════════

function DashboardHome({ recentAnalyses, loading, onGoToContract, onGoToCoding, onViewAnalysis }) {
  const hasAnalyses = recentAnalyses && recentAnalyses.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Quick Actions */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        <button
          onClick={onGoToContract}
          style={{
            border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24,
            background: "#fff", cursor: "pointer", textAlign: "left",
            transition: "border-color 0.15s",
          }}
          onMouseOver={e => e.currentTarget.style.borderColor = "var(--cs-teal)"}
          onMouseOut={e => e.currentTarget.style.borderColor = "var(--cs-border)"}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
              background: "var(--cs-teal-pale)",
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)" }}>Contract Integrity</div>
              <div style={{ fontSize: 13, color: "var(--cs-slate)" }}>Audit payer remittances</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: "var(--cs-slate)", margin: 0, lineHeight: 1.5 }}>
            Compare your remittances against contracted rates. Find what your payer owes you.
          </p>
        </button>

        <button
          onClick={onGoToCoding}
          style={{
            border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24,
            background: "#fff", cursor: "pointer", textAlign: "left",
            transition: "border-color 0.15s",
          }}
          onMouseOver={e => e.currentTarget.style.borderColor = "var(--cs-teal)"}
          onMouseOut={e => e.currentTarget.style.borderColor = "var(--cs-border)"}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
              background: "#eff6ff",
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)" }}>Coding Analysis</div>
              <div style={{ fontSize: 13, color: "var(--cs-slate)" }}>Check coding patterns</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: "var(--cs-slate)", margin: 0, lineHeight: 1.5 }}>
            Analyze your E&M coding patterns. Find undercoding risk and compliance issues.
          </p>
        </button>
      </div>

      {/* Recent Analyses */}
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24, background: "#fff" }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 16px" }}>
          Recent Analyses
        </h3>

        {loading ? (
          <div style={{ textAlign: "center", padding: 24 }}>
            <Spinner />
            <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 12 }}>Loading...</p>
          </div>
        ) : hasAnalyses ? (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Payer</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Total Billed</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Total Paid</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Underpayment</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Adherence</th>
                </tr>
              </thead>
              <tbody>
                {recentAnalyses.map((a, i) => (
                  <tr
                    key={a.id}
                    onClick={() => onViewAnalysis(a.id)}
                    style={{
                      cursor: "pointer",
                      ...(i % 2 === 0 ? {} : { background: "var(--cs-mist)" }),
                    }}
                    onMouseOver={e => e.currentTarget.style.background = "var(--cs-teal-pale)"}
                    onMouseOut={e => e.currentTarget.style.background = i % 2 === 0 ? "" : "var(--cs-mist)"}
                  >
                    <td style={tdStyle}>
                      {a.production_date ? new Date(a.production_date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                    </td>
                    <td style={tdStyle}>{a.payer_name || "—"}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      ${(a.total_billed || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      ${(a.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: a.underpayment > 0 ? "#dc2626" : "inherit", fontWeight: a.underpayment > 0 ? 600 : 400 }}>
                      ${(a.underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{
                      ...tdStyle, textAlign: "right", fontWeight: 600,
                      color: a.adherence_rate >= 97 ? "#059669" : a.adherence_rate >= 90 ? "#d97706" : "#dc2626",
                    }}>
                      {a.adherence_rate}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            padding: 32, textAlign: "center", background: "var(--cs-mist)",
            borderRadius: 8,
          }}>
            <div style={{ marginBottom: 12 }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
              No analyses yet
            </h4>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, margin: "0 0 16px", maxWidth: 400, marginLeft: "auto", marginRight: "auto" }}>
              Start by uploading your contract rates and an 835 remittance file to run your first contract integrity analysis.
            </p>
            <button onClick={onGoToContract} style={btnPrimary}>
              Get Started
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Historical Report Viewer
// ═══════════════════════════════════════════════════════════════════

function HistoricalReportView({ record, sortField, sortDir, onSort, getSortedLines, onBack }) {
  const rj = record.result_json || {};
  const s = rj.summary || {};
  const sc = rj.scorecard || {};
  const di = rj.denial_intelligence || {};
  const sortedLines = getSortedLines();
  const adherenceColor = s.adherence_rate >= 97 ? "#059669" : s.adherence_rate >= 90 ? "#d97706" : "#dc2626";

  // Format header date: "December 2025"
  const headerDate = record.production_date
    ? new Date(record.production_date + "T00:00:00").toLocaleDateString("en-US", { month: "long", year: "numeric" })
    : "";

  return (
    <div>
      {/* Back button + header */}
      <div className="no-print" style={{ marginBottom: 24 }}>
        <button
          onClick={onBack}
          style={{
            background: "none", border: "none", padding: 0,
            color: "var(--cs-teal)", fontSize: 14, fontWeight: 600,
            cursor: "pointer", marginBottom: 12, display: "block",
          }}
        >
          &larr; Back to Dashboard
        </button>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
          {record.payer_name || "Analysis"}{headerDate ? ` — ${headerDate}` : ""}
        </h2>
      </div>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 }}>
        <SummaryCard label="Total Contracted" value={`$${(s.total_contracted || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
        <SummaryCard label="Total Paid" value={`$${(s.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
        <SummaryCard label="Underpayment" value={`$${(s.total_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} color={s.total_underpayment > 0 ? "#dc2626" : undefined} />
        <SummaryCard label="Adherence Rate" value={`${s.adherence_rate || 0}%`} color={adherenceColor} />
      </div>

      {/* Underpayment callout */}
      {s.total_underpayment > 0 && (
        <div style={{
          background: "var(--cs-navy)", borderRadius: 12, padding: 24,
          marginBottom: 24, color: "#fff",
        }}>
          <div style={{ fontSize: 14, opacity: 0.8, marginBottom: 4 }}>Total Potential Underpayment</div>
          <div style={{ fontSize: 32, fontWeight: 700 }}>
            ${s.total_underpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: 13, marginTop: 8, opacity: 0.7 }}>
            {s.underpaid_count} underpaid line{s.underpaid_count !== 1 ? "s" : ""} + {s.denied_count} denied
            {" "}out of {s.line_count} total
          </div>
        </div>
      )}

      {/* Billed-Below-Contract callout */}
      {s.billed_below_count > 0 && (
        <div style={{
          background: "#fff7ed", borderRadius: 12, padding: 20,
          marginBottom: 24, border: "1px solid #fb923c",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 18 }}>&#9888;</span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "#9a3412" }}>
              Chargemaster Below Contract
            </span>
          </div>
          <p style={{ fontSize: 14, color: "#9a3412", margin: 0, lineHeight: 1.5 }}>
            {s.billed_below_count} line{s.billed_below_count !== 1 ? "s" : ""} billed below your contracted rate.
            Total chargemaster gap: <strong>${(s.total_chargemaster_gap || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>.
          </p>
        </div>
      )}

      {/* Flag breakdown */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <FlagBadge label="Correct" count={s.correct_count} color="#059669" bg="#ecfdf5" />
        <FlagBadge label="Underpaid" count={s.underpaid_count} color="#dc2626" bg="#fef2f2" />
        <FlagBadge label="Denied" count={s.denied_count} color="#d97706" bg="#fffbeb" />
        {s.billed_below_count > 0 && (
          <FlagBadge label="Below Contract" count={s.billed_below_count} color="#ea580c" bg="#fff7ed" />
        )}
        <FlagBadge label="Overpaid" count={s.overpaid_count} color="#2563eb" bg="#eff6ff" />
        <FlagBadge label="No Contract" count={s.no_contract_count} color="#6b7280" bg="#f3f4f6" />
      </div>

      {/* Practice Performance Scorecard */}
      {(sc.clean_claim_rate != null) && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
            Practice Performance
          </h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
            <KpiTile label="Clean Claim Rate" value={`${sc.clean_claim_rate}%`} benchmark="95%" color={sc.clean_claim_rate >= 95 ? "#059669" : sc.clean_claim_rate >= 85 ? "#d97706" : "#dc2626"} />
            <KpiTile label="Denial Rate" value={`${sc.denial_rate}%`} benchmark="<5%" color={sc.denial_rate <= 5 ? "#059669" : sc.denial_rate <= 10 ? "#d97706" : "#dc2626"} />
            <KpiTile label="Payer Adherence" value={`${sc.payer_adherence_rate}%`} benchmark="97%" color={sc.payer_adherence_rate >= 97 ? "#059669" : sc.payer_adherence_rate >= 90 ? "#d97706" : "#dc2626"} />
            <KpiTile label="Preventable Denials" value={`${sc.preventable_denial_rate}%`} benchmark="<30%" color={sc.preventable_denial_rate <= 30 ? "#059669" : sc.preventable_denial_rate <= 50 ? "#d97706" : "#dc2626"} />
          </div>
          {sc.narrative && (
            <div style={{
              padding: 16, borderRadius: 8, background: "#f0f9ff",
              border: "1px solid #bae6fd", fontSize: 14, color: "var(--cs-navy)",
              lineHeight: 1.6,
            }}>
              {sc.narrative}
            </div>
          )}
          {s.line_count < 50 && (
            <p style={{ fontSize: 12, color: "var(--cs-slate)", marginTop: 12, marginBottom: 0, fontStyle: "italic" }}>
              Note: This analysis is based on {s.line_count} line items.
              Metrics are more meaningful with a full month of remittance data (typically 200+ line items).
            </p>
          )}
        </div>
      )}

      {/* Top Underpaid Codes */}
      {(rj.top_underpaid || []).length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
            Top Underpaid Codes
          </h4>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>CPT Code</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Total Underpayment</th>
                </tr>
              </thead>
              <tbody>
                {rj.top_underpaid.map((item, i) => (
                  <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                    <td style={tdStyle}>{item.cpt_code}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#dc2626", fontWeight: 600 }}>
                      ${item.total_underpayment.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Denial Intelligence (from stored data) */}
      {di.denial_types?.length > 0 && (
        <DenialIntelligenceSection intel={di} />
      )}

      {/* Full Line Items (only if stored in result_json) */}
      {sortedLines.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
            All Line Items ({sortedLines.length})
          </h4>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <SortTh field="cpt_code" label="CPT" current={sortField} dir={sortDir} onSort={onSort} />
                  <SortTh field="billed_amount" label="Billed" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="paid_amount" label="Paid" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="expected_payment" label="Expected" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="variance" label="Variance" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="flag" label="Flag" current={sortField} dir={sortDir} onSort={onSort} />
                  <th style={{ ...thStyle, textAlign: "right" }}>Medicare</th>
                </tr>
              </thead>
              <tbody>
                {sortedLines.map((item, i) => {
                  const rowBg = flagRowColor(item.flag, i);
                  return (
                    <tr key={i} style={{ background: rowBg }}>
                      <td style={tdStyle}>{item.cpt_code}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.billed_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.paid_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>
                        {item.expected_payment != null ? `$${item.expected_payment.toFixed(2)}` : "—"}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: varianceColor(item.variance) }}>
                        {item.variance != null ? `${item.variance >= 0 ? "+" : ""}$${item.variance.toFixed(2)}` : "—"}
                      </td>
                      <td style={tdStyle}>
                        <FlagPill flag={item.flag} />
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontSize: 12, color: "var(--cs-slate)" }}>
                        {item.medicare_rate ? `$${item.medicare_rate.toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div style={{
        padding: 16, borderRadius: 8, background: "var(--cs-mist)",
        fontSize: 12, color: "var(--cs-slate)", marginBottom: 24, lineHeight: 1.6,
      }}>
        <strong>Disclaimer:</strong> This analysis compares payer remittance data against your self-reported contracted rates
        and publicly available CMS Medicare benchmarks. It is not legal or financial advice. Verify all findings with your
        payer contracts and consult a billing specialist before taking action.
      </div>

      {/* Action buttons */}
      <div className="no-print" style={{ display: "flex", gap: 12 }}>
        <button onClick={() => window.print()} style={btnPrimary}>Download Report</button>
        <button onClick={onBack} style={btnOutline}>Back to Dashboard</button>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Coding Analysis Tab Component
// ═══════════════════════════════════════════════════════════════════

function CodingAnalysisTab({
  lines, specialty, dateStart, dateEnd, result, loading, error, profileSpecialty,
  onAddLine, onRemoveLine, onUpdateLine, onSetSpecialty, onSetDateStart, onSetDateEnd, onRun, onReset,
  onGoToContract,
}) {

  if (loading) {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 48, textAlign: "center", background: "#fff" }}>
        <Spinner />
        <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
          Analyzing coding patterns...
        </p>
        <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
          Checking E&M distributions and coding patterns.
        </p>
      </div>
    );
  }

  // ── Report view ──
  if (result) {
    const em = result.em_distribution || {};
    const bench = result.em_benchmark || {};
    const emCodes = ["99211", "99212", "99213", "99214", "99215"];
    const maxPct = Math.max(...emCodes.map(c => Math.max(em[c] || 0, bench[c] || 0)), 1);

    return (
      <div>
        {/* E&M Distribution */}
        {result.em_total > 0 && (
          <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24, background: "#fff", marginBottom: 24 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 4px" }}>
              E&M Visit Distribution
            </h3>
            <p style={{ color: "var(--cs-slate)", fontSize: 13, margin: "0 0 20px" }}>
              Your established patient E&M mix ({result.em_total} visits) vs. specialty benchmark
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {emCodes.map(code => {
                const yours = em[code] || 0;
                const theirs = bench[code] || 0;
                return (
                  <div key={code} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 50, fontSize: 13, fontWeight: 600, color: "var(--cs-navy)", textAlign: "right" }}>{code}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                        <div style={{
                          height: 14, borderRadius: 3,
                          background: "var(--cs-teal)",
                          width: `${(yours / maxPct) * 100}%`,
                          minWidth: yours > 0 ? 4 : 0,
                          transition: "width 0.3s",
                        }} />
                        <span style={{ fontSize: 12, color: "var(--cs-navy)", fontWeight: 600, whiteSpace: "nowrap" }}>{yours}%</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{
                          height: 8, borderRadius: 2,
                          background: "var(--cs-border)",
                          width: `${(theirs / maxPct) * 100}%`,
                          minWidth: theirs > 0 ? 4 : 0,
                        }} />
                        <span style={{ fontSize: 11, color: "var(--cs-slate)", whiteSpace: "nowrap" }}>{theirs}%</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ display: "flex", gap: 16, marginTop: 16, fontSize: 12, color: "var(--cs-slate)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 12, borderRadius: 2, background: "var(--cs-teal)" }} />
                Your practice
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 12, height: 8, borderRadius: 2, background: "var(--cs-border)" }} />
                Specialty benchmark
              </div>
            </div>

            {/* E&M Alerts */}
            {(result.em_alerts || []).map((alert, i) => (
              <div key={i} style={{
                marginTop: 16, padding: 14, borderRadius: 8,
                background: alert.severity === "warning" ? "#fffbeb" : "#eff6ff",
                border: `1px solid ${alert.severity === "warning" ? "#fbbf24" : "#93c5fd"}`,
                fontSize: 13, color: "var(--cs-navy)", lineHeight: 1.5,
              }}>
                <strong>{alert.type === "UNDERCODING" ? "Potential Undercoding" : "Coding Pattern Note"}:</strong>{" "}
                {alert.message}
              </div>
            ))}
          </div>
        )}

        {/* Revenue Gap Estimator (Capability 2) */}
        {result.revenue_gap && (
          <div style={{
            border: "1px solid var(--cs-border)", borderRadius: 12,
            padding: 24, background: "#fff", marginBottom: 24,
          }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 4px" }}>
              Revenue Gap Estimate
            </h3>
            <p style={{ color: "var(--cs-slate)", fontSize: 13, margin: "0 0 20px" }}>
              Based on {result.revenue_gap.weeks_of_data} weeks of data
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              <div style={{
                padding: 20, borderRadius: 10,
                background: "#fffbeb", border: "1px solid #fbbf24",
              }}>
                <div style={{ fontSize: 13, color: "#92400e", marginBottom: 4 }}>Period Gap</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: "#92400e" }}>
                  ${(result.revenue_gap.total_gap_period || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div style={{
                padding: 20, borderRadius: 10,
                background: "#fef2f2", border: "1px solid #fca5a5",
              }}>
                <div style={{ fontSize: 13, color: "#991b1b", marginBottom: 4 }}>Annualized Gap</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: "#dc2626" }}>
                  ${(result.revenue_gap.annualized_gap || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {result.revenue_gap.narrative && (
              <div style={{
                padding: 16, borderRadius: 8, background: "#f0f9ff",
                border: "1px solid #bae6fd", fontSize: 14, color: "var(--cs-navy)",
                lineHeight: 1.6, marginBottom: 20,
              }}>
                {result.revenue_gap.narrative}
              </div>
            )}

            {result.revenue_gap.gap_lines?.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Code</th>
                      <th style={{ ...thStyle, textAlign: "right" }}>Your %</th>
                      <th style={{ ...thStyle, textAlign: "right" }}>Benchmark %</th>
                      <th style={{ ...thStyle, textAlign: "right" }}>Visit Gap</th>
                      <th style={{ ...thStyle, textAlign: "right" }}>Revenue Gap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.revenue_gap.gap_lines.map((gl, i) => (
                      <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                        <td style={tdStyle}>{gl.code}</td>
                        <td style={{ ...tdStyle, textAlign: "right" }}>{gl.current_pct}%</td>
                        <td style={{ ...tdStyle, textAlign: "right" }}>{gl.benchmark_pct}%</td>
                        <td style={{ ...tdStyle, textAlign: "right" }}>{gl.visit_gap}</td>
                        <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: "#dc2626" }}>
                          ${gl.revenue_gap.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Bridge callout to Contract Integrity */}
        <div style={{
          border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24,
          background: "var(--cs-mist)", marginBottom: 24,
        }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
            Want rate-level analysis?
          </h4>
          <p style={{ fontSize: 13, color: "var(--cs-slate)", lineHeight: 1.6, margin: "0 0 16px" }}>
            Coding analysis identifies whether you are billing at the right complexity level — that question
            is the same regardless of payer. Whether your payer is actually honoring your contracted rates
            is a separate question. Upload your 835 remittance file in the Contract Integrity tab for a
            payer-specific rate comparison against your contracted rates.
          </p>
          <button onClick={onGoToContract} style={{
            background: "none", border: "none", padding: 0,
            color: "var(--cs-teal)", fontSize: 14, fontWeight: 600,
            cursor: "pointer",
          }}>
            Go to Contract Integrity &rarr;
          </button>
        </div>

        {/* Disclaimer */}
        <div style={{
          padding: 16, borderRadius: 8, background: "var(--cs-mist)",
          fontSize: 12, color: "var(--cs-slate)", marginBottom: 24, lineHeight: 1.6,
        }}>
          <strong>Disclaimer:</strong> This coding analysis uses CMS benchmark distributions for specialty comparison.
          It is not legal or compliance advice. Individual chart documentation determines the appropriate code level.
          Consult a certified coder or compliance officer before making changes.
        </div>

        {/* Actions */}
        <div className="no-print" style={{ display: "flex", gap: 12 }}>
          <button onClick={() => window.print()} style={btnPrimary}>Download Report</button>
          <button onClick={onReset} style={btnOutline}>Start Over</button>
        </div>
      </div>
    );
  }

  // ── Input form ──
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Settings row */}
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24, background: "#fff" }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 16px" }}>
          Analysis Settings
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
          <div>
            <label style={labelStyle}>Specialty</label>
            <select
              value={specialty || profileSpecialty}
              onChange={e => onSetSpecialty(e.target.value)}
              style={{ ...inputStyle, appearance: "auto" }}
            >
              <option value="">Select specialty</option>
              {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Period Start</label>
            <input
              type="date"
              value={dateStart}
              onChange={e => onSetDateStart(e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Period End</label>
            <input
              type="date"
              value={dateEnd}
              onChange={e => onSetDateEnd(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>
      </div>

      {/* Billing lines */}
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 24, background: "#fff" }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 4px" }}>
          Billing Lines
        </h3>
        <p style={{ color: "var(--cs-slate)", fontSize: 13, margin: "0 0 16px" }}>
          Enter CPT codes from recent claims. Include units and billed amounts for benchmark comparison.
        </p>

        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT Code</th>
                <th style={{ ...thStyle, textAlign: "center", width: 80 }}>Units</th>
                <th style={{ ...thStyle, textAlign: "right", width: 120 }}>Billed ($)</th>
                <th style={{ ...thStyle, width: 50 }}></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, i) => (
                <tr key={i}>
                  <td style={tdStyle}>
                    <input
                      type="text"
                      value={line.cpt_code}
                      onChange={e => onUpdateLine(i, "cpt_code", e.target.value)}
                      placeholder="e.g. 99213"
                      maxLength={5}
                      style={{ ...inputStyle, padding: "6px 10px", fontSize: 13 }}
                    />
                  </td>
                  <td style={tdStyle}>
                    <input
                      type="number"
                      value={line.units}
                      onChange={e => onUpdateLine(i, "units", e.target.value)}
                      min={1}
                      style={{ ...inputStyle, padding: "6px 10px", fontSize: 13, textAlign: "center" }}
                    />
                  </td>
                  <td style={tdStyle}>
                    <input
                      type="number"
                      value={line.billed_amount}
                      onChange={e => onUpdateLine(i, "billed_amount", e.target.value)}
                      step="0.01"
                      style={{ ...inputStyle, padding: "6px 10px", fontSize: 13, textAlign: "right" }}
                    />
                  </td>
                  <td style={tdStyle}>
                    {lines.length > 1 && (
                      <button
                        onClick={() => onRemoveLine(i)}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "#dc2626", fontSize: 16, padding: "4px 8px",
                        }}
                        title="Remove line"
                      >
                        &times;
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button
          onClick={onAddLine}
          style={{
            marginTop: 12, background: "none", border: "1px dashed var(--cs-border)",
            borderRadius: 8, padding: "8px 16px", fontSize: 13, color: "var(--cs-teal)",
            cursor: "pointer", fontWeight: 500,
          }}
        >
          + Add Line
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      <div>
        <button onClick={onRun} style={btnPrimary}>
          Run Coding Analysis
        </button>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Small reusable components
// ═══════════════════════════════════════════════════════════════════

function StepIndicator({ current }) {
  const steps = ["Contract Rates", "Remittance", "Analysis"];
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
      {steps.map((label, i) => {
        const num = i + 1;
        const active = num <= current;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              width: 24, height: 24, borderRadius: "50%", fontSize: 12, fontWeight: 700,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: active ? "var(--cs-navy)" : "var(--cs-border)",
              color: active ? "#fff" : "var(--cs-slate)",
            }}>
              {num}
            </div>
            <span style={{ fontSize: 13, color: active ? "var(--cs-navy)" : "var(--cs-slate)", fontWeight: active ? 600 : 400 }}>
              {label}
            </span>
            {i < steps.length - 1 && <div style={{ width: 20, height: 1, background: "var(--cs-border)" }} />}
          </div>
        );
      })}
    </div>
  );
}

function SummaryCard({ label, value, color }) {
  return (
    <div style={{
      border: "1px solid var(--cs-border)", borderRadius: 10,
      padding: 20, background: "#fff",
    }}>
      <div style={{ fontSize: 13, color: "var(--cs-slate)", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || "var(--cs-navy)" }}>{value}</div>
    </div>
  );
}

function FlagBadge({ label, count, color, bg }) {
  return (
    <div style={{
      padding: "6px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
      background: bg, color, display: "inline-flex", gap: 6, alignItems: "center",
    }}>
      <span>{count}</span>
      <span style={{ fontWeight: 400 }}>{label}</span>
    </div>
  );
}

function FlagPill({ flag }) {
  const colors = {
    UNDERPAID: { bg: "#fef2f2", color: "#dc2626" },
    DENIED: { bg: "#fffbeb", color: "#d97706" },
    BILLED_BELOW: { bg: "#fff7ed", color: "#ea580c" },
    CORRECT: { bg: "#ecfdf5", color: "#059669" },
    OVERPAID: { bg: "#eff6ff", color: "#2563eb" },
    NO_CONTRACT: { bg: "#f3f4f6", color: "#6b7280" },
  };
  const c = colors[flag] || colors.NO_CONTRACT;
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
      background: c.bg, color: c.color,
    }}>
      {flag}
    </span>
  );
}

function SortTh({ field, label, current, dir, onSort, align = "left" }) {
  const active = current === field;
  return (
    <th
      onClick={() => onSort(field)}
      style={{
        ...thStyle,
        textAlign: align,
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      {label} {active ? (dir === "asc" ? "\u25B2" : "\u25BC") : ""}
    </th>
  );
}

function HelpSection835() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 20 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: "none", border: "none", cursor: "pointer", padding: 0,
          fontSize: 13, color: "var(--cs-teal)", fontWeight: 600,
        }}
      >
        {open ? "▾" : "▸"} Need help finding your 835 files?
      </button>
      {open && (
        <div style={{ marginTop: 12, padding: 16, borderRadius: 8, background: "var(--cs-mist)", fontSize: 13, color: "var(--cs-slate)", lineHeight: 1.6 }}>
          <p style={{ margin: "0 0 12px", fontWeight: 600, color: "var(--cs-navy)" }}>Where to find 835 files:</p>
          <p style={{ margin: "0 0 10px" }}>
            <strong>From your clearinghouse:</strong> Log into Availity, Office Ally, Change Healthcare, or your clearinghouse portal.
            Look for &quot;ERA Downloads&quot; or &quot;835 Downloads.&quot; Download files for the month you want audited.
          </p>
          <p style={{ margin: "0 0 10px" }}>
            <strong>From your PM system:</strong> Some systems (Athena, Kareo, eClinicalWorks) can export raw 835 files.
            Check your reports or billing section.
          </p>
          <p style={{ margin: 0 }}>
            <strong>From your billing company:</strong> If you outsource billing, ask your billing company to export
            the raw 835 remittance files for the month you want audited.
          </p>
        </div>
      )}
    </div>
  );
}

function MedicarePercentageForm({ onBack, onSubmit, defaultZip }) {
  const [payer, setPayer] = useState("");
  const [pct, setPct] = useState("115");
  const [zip, setZip] = useState(defaultZip || "");
  const [effectiveDate, setEffectiveDate] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!payer.trim() || !pct || isNaN(parseFloat(pct)) || !zip.trim() || zip.trim().length < 5) return;
    onSubmit(payer.trim(), parseFloat(pct), zip.trim(), effectiveDate);
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <button onClick={onBack} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
        <span style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 15 }}>Percentage of Medicare</span>
      </div>
      <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 16 }}>
        Many contracts pay a percentage of the Medicare Physician Fee Schedule.
        Enter your payer&rsquo;s percentage and we&rsquo;ll calculate rates for all CPT codes in your area.
      </p>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 400 }}>
        <div>
          <label style={labelStyle}>Payer Name</label>
          <input value={payer} onChange={e => setPayer(e.target.value)} placeholder="e.g., Aetna" style={inputStyle} required />
        </div>
        <div>
          <label style={labelStyle}>Percentage of Medicare (%)</label>
          <input type="number" value={pct} onChange={e => setPct(e.target.value)} placeholder="115" min="1" max="500" step="0.1" style={inputStyle} required />
          <p style={{ fontSize: 12, color: "var(--cs-slate)", marginTop: 4, marginBottom: 0 }}>
            e.g., 115 means the payer pays 115% of Medicare rates
          </p>
        </div>
        <div>
          <label style={labelStyle}>Practice ZIP Code</label>
          <input value={zip} onChange={e => setZip(e.target.value)} placeholder="33701" maxLength={5} style={inputStyle} required />
          <p style={{ fontSize: 12, color: "var(--cs-slate)", marginTop: 4, marginBottom: 0 }}>
            Used to look up geographic Medicare rates for your area
          </p>
        </div>
        <div>
          <label style={labelStyle}>Effective Date (optional)</label>
          <input type="date" value={effectiveDate} onChange={e => setEffectiveDate(e.target.value)} style={inputStyle} />
        </div>
        <button type="submit" style={btnPrimary}>Calculate Rates</button>
      </form>
    </div>
  );
}

function PasteTextForm({ onBack, onSubmit }) {
  const [text, setText] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    onSubmit(text.trim());
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <button onClick={onBack} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
        <span style={{ fontWeight: 600, color: "var(--cs-navy)", fontSize: 15 }}>Paste Text</span>
      </div>
      <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 16 }}>
        Paste fee schedule text from your payer portal, email, or any document. AI will extract CPT codes and rates.
      </p>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={"Paste fee schedule text here...\n\nExample:\n99213  Office Visit, Est. Patient, Level 3  $95.00\n99214  Office Visit, Est. Patient, Level 4  $135.00"}
          rows={10}
          style={{
            ...inputStyle, resize: "vertical", fontFamily: "monospace", fontSize: 13,
            minHeight: 150,
          }}
          required
        />
        <button type="submit" style={btnPrimary}>Extract Rates</button>
      </form>
    </div>
  );
}

function HelpSectionFeeSchedule() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 4 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          background: "none", border: "none", cursor: "pointer", padding: 0,
          fontSize: 13, color: "var(--cs-teal)", fontWeight: 600,
        }}
      >
        {open ? "\u25BE" : "\u25B8"} Where to find your fee schedules
      </button>
      {open && (
        <div style={{ marginTop: 12, padding: 16, borderRadius: 8, background: "var(--cs-mist)", fontSize: 13, color: "var(--cs-slate)", lineHeight: 1.6 }}>
          <p style={{ margin: "0 0 10px" }}>
            <strong>Check your contract:</strong> Your payer contract should include a fee schedule or state a percentage of Medicare.
            Look for an exhibit or attachment labeled &quot;Fee Schedule&quot; or &quot;Reimbursement Rates.&quot;
          </p>
          <p style={{ margin: "0 0 10px" }}>
            <strong>Payer portal:</strong> Many payers (Aetna, UHC, BCBS, Cigna) publish fee schedules in their provider portals.
            Look under &quot;Contracts&quot; or &quot;Fee Schedules.&quot;
          </p>
          <p style={{ margin: "0 0 10px" }}>
            <strong>Percentage of Medicare:</strong> If your contract says something like &quot;115% of Medicare PFS,&quot;
            use the Percentage of Medicare option &mdash; no file needed.
          </p>
          <p style={{ margin: 0 }}>
            <strong>Ask your billing company:</strong> If you outsource billing, your billing company should have copies
            of your payer fee schedules or know the contracted percentages.
          </p>
        </div>
      )}
    </div>
  );
}

function ErrorBanner({ message }) {
  return (
    <div style={{
      padding: 12, borderRadius: 8, background: "#fef2f2",
      border: "1px solid #fecaca", marginTop: 16,
    }}>
      <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{message}</p>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{
      width: 40, height: 40, border: "3px solid var(--cs-border)",
      borderTopColor: "var(--cs-teal)", borderRadius: "50%",
      margin: "0 auto", animation: "spin 0.8s linear infinite",
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function DropZone({ accept, onChange, children, multiple = false }) {
  const [dragging, setDragging] = useState(false);

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    const dropped = e.dataTransfer?.files;
    if (dropped?.length) {
      onChange({ target: { files: multiple ? dropped : [dropped[0]] } });
    }
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        border: dragging ? "2px solid var(--cs-teal)" : "2px dashed var(--cs-border)",
        borderRadius: 10,
        padding: 32,
        textAlign: "center",
        background: dragging ? "var(--cs-teal-pale)" : "var(--cs-mist)",
        transition: "border-color 0.15s, background 0.15s",
      }}
    >
      <UploadIcon />
      <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 12, marginBottom: 12 }}>
        {children}
      </p>
      <label style={{
        display: "inline-block", padding: "8px 20px", borderRadius: 8,
        background: "var(--cs-navy)", color: "#fff", fontSize: 14, fontWeight: 600,
        cursor: "pointer",
      }}>
        {multiple ? "Choose Files" : "Choose File"}
        <input type="file" accept={accept} multiple={multiple} onChange={onChange} style={{ display: "none" }} />
      </label>
      {dragging && (
        <p style={{ color: "var(--cs-teal)", fontSize: 13, fontWeight: 600, marginTop: 8, marginBottom: 0 }}>
          Drop {multiple ? "files" : "file"} here
        </p>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}

function KpiTile({ label, value, benchmark, color }) {
  return (
    <div style={{
      border: "1px solid var(--cs-border)", borderRadius: 10,
      padding: 16, background: "#fff",
    }}>
      <div style={{ fontSize: 12, color: "var(--cs-slate)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || "var(--cs-navy)" }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--cs-slate)", marginTop: 4 }}>
        Benchmark: {benchmark}
      </div>
    </div>
  );
}

function DenialIntelligenceSection({ intel }) {
  const [expandedType, setExpandedType] = useState(null);

  return (
    <div style={{ marginBottom: 24 }}>
      <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
        Denial Intelligence
      </h4>

      {/* Pattern summary */}
      {intel.pattern_summary && (
        <div style={{
          padding: 16, borderRadius: 8, background: "#fffbeb",
          border: "1px solid #fbbf24", fontSize: 14, color: "#92400e",
          lineHeight: 1.6, marginBottom: 16,
        }}>
          {intel.pattern_summary}
        </div>
      )}

      {/* Recoverable value */}
      {intel.total_recoverable_value > 0 && (
        <div style={{
          padding: 16, borderRadius: 8, background: "#ecfdf5",
          border: "1px solid #6ee7b7", marginBottom: 16,
        }}>
          <div style={{ fontSize: 13, color: "#065f46", marginBottom: 4 }}>Estimated Recoverable Value</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#059669" }}>
            ${intel.total_recoverable_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </div>
        </div>
      )}

      {/* Denial type cards */}
      {(intel.denial_types || []).map((dt, i) => {
        const isExpanded = expandedType === i;
        const worthColor = dt.appeal_worthiness === "high" ? "#059669"
          : dt.appeal_worthiness === "medium" ? "#d97706" : "#6b7280";

        return (
          <div key={i} style={{
            border: "1px solid var(--cs-border)", borderRadius: 10,
            marginBottom: 12, overflow: "hidden", background: "#fff",
          }}>
            <div
              onClick={() => setExpandedType(isExpanded ? null : i)}
              style={{
                padding: 16, cursor: "pointer",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: "var(--cs-navy)" }}>
                    {dt.adjustment_code}
                  </span>
                  <span style={{
                    padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                    background: dt.is_actionable ? "#ecfdf5" : "#f3f4f6",
                    color: dt.is_actionable ? "#059669" : "#6b7280",
                  }}>
                    {dt.is_actionable ? "Actionable" : "Non-actionable"}
                  </span>
                  <span style={{
                    padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                    color: worthColor,
                  }}>
                    Appeal: {dt.appeal_worthiness}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "var(--cs-slate)" }}>
                  {dt.plain_language}
                </div>
              </div>
              <div style={{ textAlign: "right", whiteSpace: "nowrap", marginLeft: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cs-navy)" }}>
                  {dt.count} line{dt.count !== 1 ? "s" : ""} &middot; ${(dt.total_value || 0).toFixed(2)}
                </div>
                <div style={{ fontSize: 12, color: "var(--cs-teal)" }}>
                  {isExpanded ? "Hide details" : "Show details"}
                </div>
              </div>
            </div>

            {isExpanded && (
              <div style={{ padding: "0 16px 16px", borderTop: "1px solid var(--cs-border)" }}>
                {dt.recommended_action && (
                  <div style={{ padding: "12px 0", fontSize: 13, color: "var(--cs-navy)", lineHeight: 1.5 }}>
                    <strong>Recommended action:</strong> {dt.recommended_action}
                  </div>
                )}
                {dt.appeal_letter_template && (
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 8, marginTop: 8 }}>
                      Appeal Letter Template
                    </div>
                    <div style={{
                      padding: 16, borderRadius: 8, background: "var(--cs-mist)",
                      fontSize: 13, color: "var(--cs-navy)", whiteSpace: "pre-wrap",
                      lineHeight: 1.6, fontFamily: "monospace",
                    }}>
                      {dt.appeal_letter_template}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6, verticalAlign: "middle" }}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Style helpers
// ═══════════════════════════════════════════════════════════════════

function flagRowColor(flag, index) {
  const even = index % 2 === 0;
  switch (flag) {
    case "UNDERPAID": return even ? "#fef2f2" : "#fee2e2";
    case "DENIED": return even ? "#fffbeb" : "#fef3c7";
    case "BILLED_BELOW": return even ? "#fff7ed" : "#ffedd5";
    case "CORRECT": return even ? "#ecfdf5" : "#d1fae5";
    case "OVERPAID": return even ? "#eff6ff" : "#dbeafe";
    case "NO_CONTRACT": return even ? "#f9fafb" : "#f3f4f6";
    default: return even ? "#fff" : "var(--cs-mist)";
  }
}

function varianceColor(v) {
  if (v == null) return "var(--cs-slate)";
  if (v < -0.5) return "#dc2626";
  if (v > 0.5) return "#2563eb";
  return "#059669";
}

const tableStyle = {
  width: "100%", borderCollapse: "collapse", fontSize: 13,
};

const thStyle = {
  padding: "8px 10px", textAlign: "left", fontSize: 12, fontWeight: 600,
  color: "var(--cs-slate)", borderBottom: "2px solid var(--cs-border)",
  whiteSpace: "nowrap",
};

const tdStyle = {
  padding: "7px 10px", borderBottom: "1px solid var(--cs-border)",
};

const btnPrimary = {
  padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600,
  cursor: "pointer", border: "none",
  background: "var(--cs-navy)", color: "#fff",
};

const btnOutline = {
  padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600,
  cursor: "pointer", border: "1px solid var(--cs-border)",
  background: "#fff", color: "var(--cs-slate)",
};

// ── Shared styles ──
const labelStyle = {
  display: "block", fontSize: 14, fontWeight: 500,
  color: "var(--cs-navy)", marginBottom: 6,
};

const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1px solid var(--cs-border)", fontSize: 15,
  outline: "none", boxSizing: "border-box",
};
