import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SITE_URL = import.meta.env.VITE_SITE_URL || "https://civicscale.ai";

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const YEARS = Array.from({ length: 5 }, (_, i) => 2025 + i);

const INDUSTRIES = [
  "Agriculture / Forestry / Fishing", "Construction",
  "Finance / Real Estate / Insurance", "Manufacturing",
  "Other Services", "Professional Services",
  "Retail Trade", "Transportation / Utilities", "Wholesale Trade",
];
const EMPLOYEE_RANGES = ["<100", "100-250", "250-500", "500-1000", "1000+"];
const EMPLOYEE_LABELS = {
  "<100": "<100 employees",
  "100-250": "100–250 employees",
  "250-500": "250–500 employees",
  "500-1000": "500–1,000 employees",
  "1000+": "1,000+ employees",
};
const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
  "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
  "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
];
const CARRIER_SUGGESTIONS = ["Cigna", "Aetna", "UnitedHealth", "BCBS", "Humana", "Self-insured/TPA", "Other"];

function ordinalSuffix(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

const ACTIVITY_DOT = {
  subscriber: { color: "#22c55e", label: "Active subscriber" },
  uploaded: { color: "#3b82f6", label: "Uploaded files" },
  viewed: { color: "#f59e0b", label: "Viewed report" },
  benchmark_only: { color: "#94a3b8", label: "Benchmark only" },
};

function BrokerDashboardInner() {
  const navigate = useNavigate();
  const { token, user, company, logout: authLogout } = useAuth();
  const broker = {
    email: user?.email || "",
    firm_name: company?.name || "",
    contact_name: user?.full_name || "",
    logo_url: company?.logo_url || null,
  };
  const authHeaders = { Authorization: `Bearer ${token}` };
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientSummary, setClientSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [clientActivity, setClientActivity] = useState(null);

  // Add client panel state
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [addForm, setAddForm] = useState({
    company_name: "", employee_count_range: "<100", industry: "Manufacturing",
    state: "NY", carrier: "", employer_email: "", estimated_pepm: "", estimated_annual_spend: "",
    renewal_month: "", renewal_year: "",
  });
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");
  const [onboardResult, setOnboardResult] = useState(null);

  // Bulk add state
  const [showBulkPanel, setShowBulkPanel] = useState(false);
  const EMPTY_ROW = () => ({ company_name: "", employee_count_range: "", industry: "", state: "", carrier: "", estimated_pepm: "", renewal_month: "", renewal_year: "" });
  const [bulkRows, setBulkRows] = useState(() => Array.from({ length: 5 }, EMPTY_ROW));
  const [bulkErrors, setBulkErrors] = useState({});
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState(0);
  const [bulkTotal, setBulkTotal] = useState(0);
  const [bulkResults, setBulkResults] = useState(null);

  // Portfolio state
  const [portfolio, setPortfolio] = useState(null);
  const [sortColumn, setSortColumn] = useState("annual_gap");
  const [sortDir, setSortDir] = useState("desc");

  // Profile state
  const [showProfile, setShowProfile] = useState(false);
  const [logoUploading, setLogoUploading] = useState(false);
  const logoInputRef = useRef(null);

  // Tab state
  const [activeTab, setActiveTab] = useState("book"); // "book", "renewals", or "prospects"
  const [renewalData, setRenewalData] = useState(null);
  const [renewalLoading, setRenewalLoading] = useState(false);

  // Plan state
  const [planInfo, setPlanInfo] = useState(null);
  const [upgradeBannerDismissed, setUpgradeBannerDismissed] = useState(false);
  const [upgradeToast, setUpgradeToast] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState("Welcome to Broker Pro! Your account has been upgraded.");

  // Prospect state
  const [prospectForm, setProspectForm] = useState({ company_name: "", employee_count_range: "<100", industry: "Manufacturing", state: "NY", carrier: "" });
  const [prospectLoading, setProspectLoading] = useState(false);
  const [prospectResult, setProspectResult] = useState(null);
  const [prospectError, setProspectError] = useState("");
  const [recentProspects, setRecentProspects] = useState([]);
  const [prospectsLoaded, setProspectsLoaded] = useState(false);

  // Share / notify state
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [notifySent, setNotifySent] = useState(false);
  const [upgradeSent, setUpgradeSent] = useState(false);
  const [brokerNotesOpen, setBrokerNotesOpen] = useState(false);

  // Invite employer modal state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteResult, setInviteResult] = useState(null);

  // Upload state — broker uploads claims/scorecard on behalf of client
  const [claimsFile, setClaimsFile] = useState(null);
  const [claimsZip, setClaimsZip] = useState("");
  const [claimsUploading, setClaimsUploading] = useState(false);
  const [claimsUploadResult, setClaimsUploadResult] = useState(null);
  const [claimsUploadError, setClaimsUploadError] = useState("");
  const [scorecardFile, setScorecardFile] = useState(null);
  const [scorecardUploading, setScorecardUploading] = useState(false);
  const [scorecardUploadResult, setScorecardUploadResult] = useState(null);
  const [scorecardUploadError, setScorecardUploadError] = useState("");

  // Handle ?upgraded=true — poll until plan shows "pro"
  useEffect(() => {
    if (!token) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("upgraded") === "true") {
      window.history.replaceState({}, "", "/broker/dashboard");
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch(`${API}/api/broker/plan`, { headers: authHeaders });
          const data = await res.json();
          if (data.plan === "pro" || data.plan === "pro_cancelling") {
            setPlanInfo(data);
            setUpgradeMessage("Welcome to Broker Pro! Your account has been upgraded.");
            setUpgradeToast(true);
            setTimeout(() => setUpgradeToast(false), 5000);
            clearInterval(poll);
          } else if (attempts >= 10) {
            setUpgradeMessage("Upgrade processing \u2014 your plan will update shortly. Refresh in a moment if it hasn\u2019t changed.");
            setUpgradeToast(true);
            setTimeout(() => setUpgradeToast(false), 8000);
            clearInterval(poll);
          }
        } catch {
          clearInterval(poll);
        }
      }, 2000);
    }
  }, [token]);

  // Fetch clients + portfolio + plan
  const fetchClients = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [clientsRes, portfolioRes, planRes] = await Promise.all([
        fetch(`${API}/api/broker/clients`, { headers: authHeaders }),
        fetch(`${API}/api/broker/portfolio`, { headers: authHeaders }),
        fetch(`${API}/api/broker/plan`, { headers: authHeaders }),
      ]);
      if (clientsRes.ok) {
        const data = await clientsRes.json();
        setClients(data.clients || []);
      }
      if (portfolioRes.ok) {
        setPortfolio(await portfolioRes.json());
      }
      if (planRes.ok) {
        setPlanInfo(await planRes.json());
      }
    } catch (err) { console.error("Failed to fetch clients:", err); }
    setLoading(false);
  }, [token]);

  useEffect(() => { fetchClients(); }, [fetchClients]);

  // Auto-select client from ?client= query param (e.g. from renewal prep report)
  useEffect(() => {
    if (!clients.length) return;
    const params = new URLSearchParams(window.location.search);
    const clientParam = params.get("client");
    if (clientParam && !selectedClient) {
      const match = clients.find((c) => c.employer_email === clientParam);
      if (match) {
        handleSelectClient(match);
        window.history.replaceState({}, "", "/broker/dashboard");
      }
    }
  }, [clients]);

  // Fetch renewal pipeline
  const fetchRenewals = useCallback(async () => {
    if (!token) return;
    setRenewalLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/renewal-pipeline`, { headers: authHeaders });
      if (res.ok) setRenewalData(await res.json());
    } catch (err) { console.error("Failed to fetch renewals:", err); }
    setRenewalLoading(false);
  }, [token]);

  useEffect(() => { if (activeTab === "renewals") fetchRenewals(); }, [activeTab, fetchRenewals]);

  const fetchProspects = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/broker/prospects`, { headers: authHeaders });
      if (res.ok) { const data = await res.json(); setRecentProspects(data.prospects || []); }
    } catch (err) { console.error("Failed to fetch prospects:", err); }
    setProspectsLoaded(true);
  }, [token]);

  useEffect(() => { if (activeTab === "prospects" && !prospectsLoaded) fetchProspects(); }, [activeTab, prospectsLoaded, fetchProspects]);

  const handleProspectSubmit = async (e) => {
    e.preventDefault();
    if (!prospectForm.company_name.trim()) return;
    setProspectLoading(true);
    setProspectError("");
    setProspectResult(null);
    try {
      const res = await fetch(`${API}/api/broker/prospect-benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify(prospectForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to run prospect benchmark.");
      setProspectResult(data);
      fetchProspects();
    } catch (err) { setProspectError(err.message); }
    setProspectLoading(false);
  };

  const addProspectAsClient = (prospect) => {
    setAddForm({
      company_name: prospect.company_name || "",
      employee_count_range: prospect.employee_count_range || "<100",
      industry: prospect.industry || "Manufacturing",
      state: prospect.state || "NY",
      carrier: prospect.carrier || "",
      employer_email: "", estimated_pepm: "", estimated_annual_spend: "", renewal_month: "", renewal_year: "",
    });
    setShowAddPanel(true);
    setAddError("");
    setOnboardResult(null);
    setActiveTab("book");
  };

  // Fetch client summary
  const fetchSummary = useCallback(async (employerEmail) => {
    if (!token) return;
    setSummaryLoading(true);
    setClientSummary(null);
    setClientActivity(null);
    try {
      const [summaryRes, activityRes] = await Promise.all([
        fetch(`${API}/api/broker/clients/${encodeURIComponent(employerEmail)}/summary`, { headers: authHeaders }),
        fetch(`${API}/api/broker/clients/${encodeURIComponent(employerEmail)}/activity`, { headers: authHeaders }),
      ]);
      if (summaryRes.ok) setClientSummary(await summaryRes.json());
      if (activityRes.ok) setClientActivity(await activityRes.json());
    } catch (err) { console.error("Failed to fetch summary:", err); }
    setSummaryLoading(false);
  }, [token]);

  const handleSelectClient = (client) => {
    setSelectedClient(client);
    setOnboardResult(null);
    setNotifySent(false);
    setShareCopied(false);
    setUpgradeSent(false);
    setClaimsFile(null); setClaimsUploadResult(null); setClaimsUploadError("");
    setScorecardFile(null); setScorecardUploadResult(null); setScorecardUploadError("");
    fetchSummary(client.employer_email);
  };

  // Onboard new client
  const handleOnboard = async (e) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError("");
    setOnboardResult(null);

    try {
      const renewalDate = addForm.renewal_month && addForm.renewal_year
        ? `${addForm.renewal_year}-${addForm.renewal_month}-01`
        : null;
      const body = {
        company_name: addForm.company_name,
        employee_count_range: addForm.employee_count_range,
        industry: addForm.industry,
        state: addForm.state,
        carrier: addForm.carrier,
        employer_email: addForm.employer_email || null,
        estimated_pepm: addForm.estimated_pepm ? parseFloat(addForm.estimated_pepm) : null,
        estimated_annual_spend: addForm.estimated_annual_spend ? parseFloat(addForm.estimated_annual_spend) : null,
        renewal_month: renewalDate,
      };

      const res = await fetch(`${API}/api/broker/clients/onboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.detail === "CLIENT_LIMIT_REACHED") {
          setAddError("CLIENT_LIMIT_REACHED");
        } else {
          throw new Error(data.detail || "Failed to onboard client.");
        }
        setAddLoading(false);
        return;
      }

      setOnboardResult(data);
      fetchClients();
    } catch (err) { setAddError(err.message); }
    setAddLoading(false);
  };

  // Upgrade to Pro
  const handleUpgrade = async () => {
    try {
      const res = await fetch(`${API}/api/broker/subscribe`, { method: "POST", headers: authHeaders });
      const data = await res.json();
      if (data.checkout_url) window.location.href = data.checkout_url;
      if (data.already_subscribed) { setPlanInfo(prev => ({ ...prev, plan: "pro", at_limit: false, client_limit: null })); }
    } catch (err) { console.error("Upgrade failed:", err); }
  };

  // Share link
  const handleCopyShareLink = async (shareToken) => {
    const url = `${SITE_URL}/employer/shared-report/${shareToken}`;
    try {
      await navigator.clipboard.writeText(url);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 3000);
    } catch { /* fallback */ }
  };

  // Notify employer
  const handleNotify = async (employerEmail) => {
    if (!token) return;
    setShareLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/clients/${encodeURIComponent(employerEmail)}/notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.sent) setNotifySent(true);
    } catch (err) { console.error("Notify failed:", err); }
    setShareLoading(false);
  };

  // Suggest upgrade
  const handleSuggestUpgrade = async (employerEmail) => {
    if (!token) return;
    setShareLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/clients/${encodeURIComponent(employerEmail)}/notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ message_type: "upgrade" }),
      });
      const data = await res.json();
      if (data.sent) setUpgradeSent(true);
    } catch (err) { console.error("Upgrade suggest failed:", err); }
    setShareLoading(false);
  };

  // Remove client
  const handleRemoveClient = async (employerEmail) => {
    if (!confirm("Remove this employer from your client list?")) return;
    try {
      const res = await fetch(
        `${API}/api/broker/clients/${encodeURIComponent(employerEmail)}`,
        { method: "DELETE", headers: authHeaders }
      );
      if (res.ok) {
        setClients((prev) => prev.filter((c) => c.employer_email !== employerEmail));
        if (selectedClient?.employer_email === employerEmail) {
          setSelectedClient(null);
          setClientSummary(null);
        }
      }
    } catch (err) { console.error("Failed to remove client:", err); }
  };

  const handleLogout = async () => {
    await authLogout();
    navigate("/broker/login");
  };

  // Bulk add handlers
  const updateBulkRow = (idx, field, value) => {
    setBulkRows(prev => prev.map((r, i) => i === idx ? { ...r, [field]: value } : r));
    if (bulkErrors[`${idx}-${field}`]) {
      setBulkErrors(prev => { const n = { ...prev }; delete n[`${idx}-${field}`]; return n; });
    }
  };

  const handleBulkPaste = (e, rowIdx, colIdx) => {
    const text = e.clipboardData.getData("text/plain");
    if (!text.includes("\t") && !text.includes("\n")) return;
    e.preventDefault();
    const colFields = ["company_name", "employee_count_range", "industry", "state", "carrier", "estimated_pepm", "renewal_month"];
    const pastedRows = text.trim().split(/\r?\n/).map(line => line.split("\t"));
    setBulkRows(prev => {
      const updated = [...prev];
      for (let ri = 0; ri < pastedRows.length; ri++) {
        const targetRow = rowIdx + ri;
        if (targetRow >= 50) break;
        while (updated.length <= targetRow) updated.push(EMPTY_ROW());
        for (let ci = 0; ci < pastedRows[ri].length; ci++) {
          const targetCol = colIdx + ci;
          if (targetCol < colFields.length) {
            updated[targetRow] = { ...updated[targetRow], [colFields[targetCol]]: pastedRows[ri][ci].trim() };
          }
        }
      }
      return updated;
    });
  };

  const handleBulkSubmit = async () => {
    // Validate required fields
    const errors = {};
    const validRows = [];
    bulkRows.forEach((row, i) => {
      const hasAny = row.company_name || row.industry || row.state || row.employee_count_range;
      if (!hasAny) return;
      let hasError = false;
      if (!row.company_name.trim()) { errors[`${i}-company_name`] = true; hasError = true; }
      if (!row.employee_count_range.trim()) { errors[`${i}-employee_count_range`] = true; hasError = true; }
      if (!row.industry.trim()) { errors[`${i}-industry`] = true; hasError = true; }
      if (!row.state.trim()) { errors[`${i}-state`] = true; hasError = true; }
      if (!hasError) validRows.push(row);
    });
    setBulkErrors(errors);
    if (Object.keys(errors).length > 0) return;
    if (validRows.length === 0) return;

    setBulkRunning(true);
    setBulkTotal(validRows.length);
    setBulkProgress(0);
    setBulkResults(null);

    try {
      const clients = validRows.map(r => ({
        company_name: r.company_name.trim(),
        employee_count_range: r.employee_count_range,
        industry: r.industry,
        state: r.state,
        carrier: r.carrier || null,
        estimated_pepm: r.estimated_pepm ? parseFloat(r.estimated_pepm) : null,
        renewal_month: r.renewal_month && r.renewal_year ? `${r.renewal_year}-${r.renewal_month}` : null,
      }));
      const res = await fetch(`${API}/api/broker/clients/bulk-onboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ clients }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Bulk onboard failed");
      setBulkProgress(validRows.length);
      setBulkResults(data.results);
      fetchClients();
    } catch (err) {
      setBulkResults([{ company_name: "Error", success: false, error: err.message }]);
    }
    setBulkRunning(false);
  };

  const bulkHasRequired = bulkRows.some(r => r.company_name && r.employee_count_range && r.industry && r.state);

  // Logo upload
  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !broker) return;
    setLogoUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API}/api/broker/profile/logo`, { method: "POST", headers: authHeaders, body: formData });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      // Logo uploaded successfully — will reflect on next page load
    } catch (err) { console.error("Logo upload failed:", err); }
    setLogoUploading(false);
  };

  // Sorting helpers
  const handleSort = (col) => {
    if (sortColumn === col) { setSortDir(d => d === "asc" ? "desc" : "asc"); }
    else { setSortColumn(col); setSortDir("desc"); }
  };
  const sortArrow = (col) => sortColumn === col ? (sortDir === "asc" ? " \u25B2" : " \u25BC") : "";

  const portfolioClients = (portfolio?.clients || []).slice().sort((a, b) => {
    let av = a[sortColumn], bv = b[sortColumn];
    if (av == null) av = sortDir === "asc" ? Infinity : -Infinity;
    if (bv == null) bv = sortDir === "asc" ? Infinity : -Infinity;
    if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortDir === "asc" ? av - bv : bv - av;
  });

  const isRenewing90 = (rm) => {
    if (!rm) return false;
    try {
      const d = new Date(rm);
      const now = new Date();
      const in90 = new Date(now.getTime() + 90 * 24 * 3600 * 1000);
      return d >= now && d <= in90;
    } catch { return false; }
  };

  const renewingClients = portfolioClients.filter(c => isRenewing90(c.renewal_month));

  const fmt = (n) => n != null ? n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : "—";

  // --- Broker claims upload handler ---
  const handleClaimsUpload = async () => {
    if (!claimsFile || !claimsZip || !selectedClient?.employer_email) return;
    setClaimsUploading(true);
    setClaimsUploadError("");
    setClaimsUploadResult(null);
    try {
      const fd = new FormData();
      fd.append("file", claimsFile);
      fd.append("zip_code", claimsZip.trim());
      const res = await fetch(
        `${API}/api/broker/clients/${encodeURIComponent(selectedClient.employer_email)}/claims-upload`,
        { method: "POST", headers: authHeaders, body: fd }
      );
      const data = await res.json();
      if (!res.ok) { setClaimsUploadError(data.detail || "Upload failed"); return; }
      setClaimsUploadResult(data);
      setClaimsFile(null);
      // Refresh client summary to show new upload
      try {
        const sr = await fetch(`${API}/api/broker/clients/${encodeURIComponent(selectedClient.employer_email)}/summary`, { headers: authHeaders });
        if (sr.ok) setClientSummary(await sr.json());
      } catch {}
    } catch (err) {
      setClaimsUploadError("Upload failed. Please try again.");
    } finally {
      setClaimsUploading(false);
    }
  };

  // --- Broker scorecard upload handler ---
  const handleScorecardUpload = async () => {
    if (!scorecardFile || !selectedClient?.employer_email) return;
    setScorecardUploading(true);
    setScorecardUploadError("");
    setScorecardUploadResult(null);
    try {
      const fd = new FormData();
      fd.append("file", scorecardFile);
      const res = await fetch(
        `${API}/api/broker/clients/${encodeURIComponent(selectedClient.employer_email)}/scorecard-upload`,
        { method: "POST", headers: authHeaders, body: fd }
      );
      const data = await res.json();
      if (!res.ok) { setScorecardUploadError(data.detail || "Upload failed"); return; }
      setScorecardUploadResult(data);
      setScorecardFile(null);
      // Refresh client summary
      try {
        const sr = await fetch(`${API}/api/broker/clients/${encodeURIComponent(selectedClient.employer_email)}/summary`, { headers: authHeaders });
        if (sr.ok) setClientSummary(await sr.json());
      } catch {}
    } catch (err) {
      setScorecardUploadError("Upload failed. Please try again.");
    } finally {
      setScorecardUploading(false);
    }
  };

  if (!token || !user) return null;

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden", minHeight: "100vh", background: "#f8fafc" }}>
      {/* NAV */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.96)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em", color: "#f1f5f9" }}>CivicScale</span>
        </a>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ fontSize: 14, color: "#94a3b8" }}>{broker.firm_name}</span>
          <button onClick={() => navigate("/broker/account")} title="Account Settings" style={{ background: "none", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "6px 10px", fontSize: 16, color: "#94a3b8", cursor: "pointer", lineHeight: 1 }}>
            &#9881;
          </button>
          <button onClick={handleLogout} style={{ background: "none", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "6px 14px", fontSize: 13, color: "#94a3b8", cursor: "pointer" }}>
            Sign Out
          </button>
        </div>
      </header>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "88px 24px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>Broker Dashboard</h1>
            <p style={{ color: "#64748b", fontSize: 15, marginTop: 4 }}>
              {broker.contact_name ? `${broker.contact_name} · ` : ""}{broker.firm_name}
              <Link to="/broker/caa-guide" style={{ color: "#0D7377", fontSize: 13, marginLeft: 12, textDecoration: "none" }}>Claims Data Guide</Link>
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => { setShowInviteModal(true); setInviteEmail(""); setInviteResult(null); }}
              style={{ background: "#fff", color: "#1B3A5C", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 16px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
            >
              Invite Client
            </button>
            <button
              onClick={() => { setShowBulkPanel(true); setBulkErrors({}); setBulkResults(null); setBulkRunning(false); setBulkRows(Array.from({ length: 5 }, EMPTY_ROW)); setTimeout(() => { document.getElementById("bulk-add-panel")?.scrollIntoView({ behavior: "smooth", block: "start" }); }, 50); }}
              style={{ background: "#fff", color: "#0D7377", border: "1px solid #0D7377", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
            >
              Bulk Add Clients
            </button>
            <button
              onClick={() => { setShowAddPanel(true); setAddError(""); setOnboardResult(null); setAddForm({ company_name: "", employee_count_range: "<100", industry: "Manufacturing", state: "NY", carrier: "", employer_email: "", estimated_pepm: "", estimated_annual_spend: "", renewal_month: "", renewal_year: "" }); setTimeout(() => { document.getElementById("add-client-panel")?.scrollIntoView({ behavior: "smooth", block: "start" }); }, 50); }}
              style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
            >
              + Add Client
            </button>
          </div>
        </div>

        {/* Upgrade Toast */}
        {upgradeToast && (
          <div style={{ position: "fixed", top: 20, right: 24, zIndex: 1000, background: "#0D7377", color: "#fff", borderRadius: 10, padding: "14px 24px", fontSize: 14, fontWeight: 600, boxShadow: "0 4px 20px rgba(0,0,0,0.15)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 18 }}>&#10003;</span> {upgradeMessage}
          </div>
        )}

        {/* Plan Status Bar */}
        {planInfo && (
          <div style={{ marginBottom: 16 }}>
            {planInfo.plan === "pro" ? (
              <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: "10px 20px", display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#0D7377", fontWeight: 600 }}>
                <span style={{ fontSize: 16 }}>&#10003;</span> Pro Plan &mdash; Unlimited clients
              </div>
            ) : planInfo.plan === "pro_cancelling" ? (
              <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: "10px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 13, color: "#92400e", fontWeight: 600 }}>
                <span>Pro Plan &mdash; Cancelling {planInfo.subscription_period_end ? `(access until ${new Date(planInfo.subscription_period_end).toLocaleDateString("en-US", { month: "short", day: "numeric" })})` : ""}</span>
                <button onClick={async () => { try { const res = await fetch(`${API}/api/broker/reactivate-subscription`, { method: "POST", headers: authHeaders }); const data = await res.json(); if (data.status === "reactivated") setPlanInfo(prev => ({ ...prev, plan: "pro", subscription_period_end: null })); } catch {} }} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "5px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                  Reactivate Pro
                </button>
              </div>
            ) : (
              <div style={{ background: planInfo.client_count >= 10 ? "#fef2f2" : planInfo.client_count >= 8 ? "#fffbeb" : "#f8fafc", border: `1px solid ${planInfo.client_count >= 10 ? "#fecaca" : planInfo.client_count >= 8 ? "#fde68a" : "#e2e8f0"}`, borderRadius: 10, padding: "10px 20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: planInfo.client_count >= 10 ? "#991b1b" : "#475569" }}>
                    Starter Plan &mdash; {planInfo.client_count} of {planInfo.client_limit} clients used
                    {planInfo.client_count >= 10 && " · Limit reached"}
                  </span>
                  <button onClick={handleUpgrade} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "5px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                    Upgrade to Pro &rarr;
                  </button>
                </div>
                <div style={{ height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.min((planInfo.client_count / planInfo.client_limit) * 100, 100)}%`, background: planInfo.client_count >= 10 ? "#ef4444" : planInfo.client_count >= 8 ? "#f59e0b" : "#0D7377", borderRadius: 3, transition: "width 0.3s" }} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Upgrade Banner */}
        {planInfo && planInfo.at_limit && !upgradeBannerDismissed && (
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: "14px 20px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
            <div style={{ fontSize: 13, color: "#92400e", lineHeight: 1.6 }}>
              You've reached the 10-client limit on the Starter plan. Upgrade to Pro for $99/mo &mdash; unlimited clients, renewal prep reports, and Level 2 insights.
            </div>
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
              <button onClick={handleUpgrade} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
                Upgrade to Pro &rarr;
              </button>
              <button onClick={() => setUpgradeBannerDismissed(true)} style={{ background: "none", border: "none", color: "#92400e", fontSize: 16, cursor: "pointer", padding: "4px 8px" }}>
                &times;
              </button>
            </div>
          </div>
        )}

        {/* Tab Switcher */}
        <div style={{ display: "flex", gap: 0, marginBottom: 24, borderBottom: "2px solid #e2e8f0" }}>
          {[
            { key: "book", label: "Book of Business" },
            { key: "renewals", label: "Renewals" },
            { key: "prospects", label: "Prospects" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: "none", border: "none", borderBottom: activeTab === tab.key ? "2px solid #0D7377" : "2px solid transparent",
                padding: "10px 20px", fontSize: 14, fontWeight: activeTab === tab.key ? 600 : 400,
                color: activeTab === tab.key ? "#0D7377" : "#64748b", cursor: "pointer", marginBottom: -2,
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Profile Panel */}
        {showProfile && (
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: 0 }}>Profile</h3>
              <button onClick={() => setShowProfile(false)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 6, padding: "4px 12px", fontSize: 13, color: "#64748b", cursor: "pointer" }}>Close</button>
            </div>
            <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
              <div style={{ position: "relative" }}>
                {broker.logo_url ? (
                  <img src={broker.logo_url} alt="Logo" style={{ width: 64, height: 64, borderRadius: 12, objectFit: "contain", border: "1px solid #e2e8f0" }} />
                ) : (
                  <div style={{ width: 64, height: 64, borderRadius: 12, background: "#f0fdfa", border: "1px solid #99f6e4", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 700, color: "#0D7377" }}>
                    {(broker.firm_name || "B")[0].toUpperCase()}
                  </div>
                )}
                <input ref={logoInputRef} type="file" accept="image/*" onChange={handleLogoUpload} style={{ display: "none" }} />
                <button onClick={() => logoInputRef.current?.click()} disabled={logoUploading} style={{ position: "absolute", bottom: -4, right: -4, width: 24, height: 24, borderRadius: "50%", background: "#0D7377", color: "#fff", border: "2px solid #fff", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {logoUploading ? "..." : "+"}
                </button>
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#1B3A5C" }}>{broker.contact_name || "—"}</p>
                <p style={{ margin: "2px 0 0", fontSize: 14, color: "#64748b" }}>{broker.firm_name}</p>
                <p style={{ margin: "2px 0 0", fontSize: 13, color: "#94a3b8" }}>{broker.email}</p>
              </div>
            </div>
            <p style={{ margin: "12px 0 0", fontSize: 12, color: "#94a3b8" }}>
              Upload your firm logo to brand shared reports sent to clients.
            </p>
          </div>
        )}

        {/* ==================== RENEWALS TAB ==================== */}
        {activeTab === "renewals" && (
          <div>
            {renewalLoading ? (
              <div style={{ textAlign: "center", padding: 48 }}>
                <div style={{ width: 36, height: 36, border: "3px solid #e2e8f0", borderTopColor: "#0D7377", borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px" }} />
                <p style={{ color: "#64748b", fontSize: 14 }}>Loading renewal pipeline...</p>
                <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            ) : renewalData && (renewalData.renewing_soon.length + renewalData.renewing_upcoming.length + renewalData.renewing_later.length + renewalData.no_renewal_date.length === 0) ? (
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 48, textAlign: "center" }}>
                <p style={{ fontSize: 16, color: "#475569", margin: "0 0 8px" }}>No clients yet</p>
                <p style={{ fontSize: 13, color: "#94a3b8" }}>Add clients to your book of business to track their renewal pipeline.</p>
              </div>
            ) : renewalData && (renewalData.renewing_soon.length + renewalData.renewing_upcoming.length + renewalData.renewing_later.length === 0) ? (
              <div>
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 32, textAlign: "center", marginBottom: 24 }}>
                  <p style={{ fontSize: 16, color: "#475569", margin: "0 0 8px" }}>Add renewal dates to your clients to track your pipeline.</p>
                  <p style={{ fontSize: 13, color: "#94a3b8" }}>Edit any client in your book of business to add their renewal month.</p>
                </div>
                <RenewalNoDateSection clients={renewalData.no_renewal_date} onSelectClient={(emp) => { setActiveTab("book"); const match = clients.find(cl => cl.employer_email === emp); if (match) handleSelectClient(match); }} />
              </div>
            ) : renewalData ? (
              <div>
                {/* Three-column pipeline */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 24 }}>
                  <RenewalColumn
                    title="Renewing in 90 days"
                    subtitle="Urgent"
                    clients={renewalData.renewing_soon}
                    borderColor="#f59e0b"
                    titleColor="#92400e"
                    bgColor="#fffbeb"
                    brokerEmail={broker.email}
                    onSelectClient={(emp) => { setActiveTab("book"); const match = clients.find(cl => cl.employer_email === emp); if (match) handleSelectClient(match); }}
                  />
                  <RenewalColumn
                    title="91\u2013180 days"
                    subtitle="Upcoming"
                    clients={renewalData.renewing_upcoming}
                    borderColor="#3b82f6"
                    titleColor="#1d4ed8"
                    bgColor="#eff6ff"
                    brokerEmail={broker.email}
                    onSelectClient={(emp) => { setActiveTab("book"); const match = clients.find(cl => cl.employer_email === emp); if (match) handleSelectClient(match); }}
                  />
                  <RenewalColumn
                    title="Beyond 180 days"
                    subtitle="Future"
                    clients={renewalData.renewing_later}
                    borderColor="#94a3b8"
                    titleColor="#64748b"
                    bgColor="#f8fafc"
                    muted
                    brokerEmail={broker.email}
                    onSelectClient={(emp) => { setActiveTab("book"); const match = clients.find(cl => cl.employer_email === emp); if (match) handleSelectClient(match); }}
                  />
                </div>

                {/* No renewal date section */}
                {renewalData.no_renewal_date.length > 0 && (
                  <RenewalNoDateSection clients={renewalData.no_renewal_date} onSelectClient={(emp) => { setActiveTab("book"); const match = clients.find(cl => cl.employer_email === emp); if (match) handleSelectClient(match); }} />
                )}
              </div>
            ) : null}
          </div>
        )}

        {/* ==================== PROSPECTS TAB ==================== */}
        {activeTab === "prospects" && (
          <div>
            {/* Prospect form */}
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Run a Prospect Assessment</h3>
              <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px", lineHeight: 1.6 }}>
                Generate a preliminary benchmark for a potential client using only publicly available information. Use this as a conversation starter in your first meeting.
              </p>
              <form onSubmit={handleProspectSubmit}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>Company Name *</label>
                    <input value={prospectForm.company_name} onChange={e => setProspectForm({ ...prospectForm, company_name: e.target.value })} placeholder="Acme Corp" required style={{ width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, marginTop: 4, boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>Employees *</label>
                    <select value={prospectForm.employee_count_range} onChange={e => setProspectForm({ ...prospectForm, employee_count_range: e.target.value })} style={{ width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, marginTop: 4, boxSizing: "border-box" }}>
                      {EMPLOYEE_RANGES.map(r => <option key={r} value={r}>{EMPLOYEE_LABELS[r]}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>Industry *</label>
                    <select value={prospectForm.industry} onChange={e => setProspectForm({ ...prospectForm, industry: e.target.value })} style={{ width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, marginTop: 4, boxSizing: "border-box" }}>
                      {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                    </select>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
                  <div>
                    <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>State *</label>
                    <select value={prospectForm.state} onChange={e => setProspectForm({ ...prospectForm, state: e.target.value })} style={{ width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, marginTop: 4, boxSizing: "border-box" }}>
                      {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>Current Carrier (optional)</label>
                    <input value={prospectForm.carrier} onChange={e => setProspectForm({ ...prospectForm, carrier: e.target.value })} placeholder="e.g. Cigna, BCBS" style={{ width: "100%", padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, marginTop: 4, boxSizing: "border-box" }} />
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end" }}>
                    <button type="submit" disabled={prospectLoading || !prospectForm.company_name.trim()} style={{ width: "100%", background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "9px 16px", fontSize: 14, fontWeight: 600, cursor: prospectLoading ? "wait" : "pointer", opacity: prospectLoading ? 0.6 : 1 }}>
                      {prospectLoading ? "Running..." : "Run Prospect Assessment \u2192"}
                    </button>
                  </div>
                </div>
                {prospectError && <p style={{ color: "#EF4444", fontSize: 13, margin: "0 0 8px" }}>{prospectError}</p>}
              </form>
            </div>

            {/* Prospect results */}
            {prospectResult && (
              <div id="prospect-result" style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, marginBottom: 24 }}>
                <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>
                  {prospectResult.company_name} &mdash; Preliminary Assessment
                </h3>
                <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px" }}>{prospectResult.segment}</p>

                {/* Disclaimer */}
                <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: "12px 16px", marginBottom: 20 }}>
                  <p style={{ margin: 0, fontSize: 13, color: "#92400e", lineHeight: 1.6 }}>{prospectResult.disclaimer}</p>
                </div>

                {/* Typical range */}
                <p style={{ fontSize: 13, color: "#64748b", fontWeight: 500, margin: "0 0 10px" }}>Typical cost range for {prospectResult.segment}</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 20 }}>
                  <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "16px 12px", textAlign: "center" }}>
                    <p style={{ fontSize: 11, color: "#166534", margin: "0 0 4px", fontWeight: 500 }}>25th Percentile</p>
                    <p style={{ fontSize: 24, fontWeight: 700, color: "#166534", margin: 0 }}>${Math.round(prospectResult.typical_range.p25)}</p>
                    <p style={{ fontSize: 11, color: "#64748b", margin: "4px 0 0" }}>PEPM</p>
                  </div>
                  <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "16px 12px", textAlign: "center" }}>
                    <p style={{ fontSize: 11, color: "#1d4ed8", margin: "0 0 4px", fontWeight: 500 }}>Median</p>
                    <p style={{ fontSize: 24, fontWeight: 700, color: "#1d4ed8", margin: 0 }}>${Math.round(prospectResult.typical_range.p50)}</p>
                    <p style={{ fontSize: 11, color: "#64748b", margin: "4px 0 0" }}>PEPM</p>
                  </div>
                  <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10, padding: "16px 12px", textAlign: "center" }}>
                    <p style={{ fontSize: 11, color: "#991b1b", margin: "0 0 4px", fontWeight: 500 }}>75th Percentile</p>
                    <p style={{ fontSize: 24, fontWeight: 700, color: "#991b1b", margin: 0 }}>${Math.round(prospectResult.typical_range.p75)}</p>
                    <p style={{ fontSize: 11, color: "#64748b", margin: "4px 0 0" }}>PEPM</p>
                  </div>
                </div>

                {/* Talking points */}
                <p style={{ fontSize: 13, color: "#64748b", fontWeight: 500, margin: "0 0 10px" }}>Talking Points</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
                  {prospectResult.talking_points.map((tp, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                      <div style={{ width: 20, height: 20, borderRadius: "50%", background: "#f0fdfa", border: "1px solid #99f6e4", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#0D7377", flexShrink: 0 }}>{i + 1}</div>
                      <p style={{ margin: 0, fontSize: 14, color: "#475569", lineHeight: 1.7 }}>{tp}</p>
                    </div>
                  ))}
                </div>

                {/* Action buttons */}
                <div style={{ display: "flex", gap: 12 }}>
                  <button onClick={() => addProspectAsClient(prospectResult)} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
                    Add as Client &rarr;
                  </button>
                  <button onClick={() => { const el = document.getElementById("prospect-result"); if (el) { el.style.padding = "32px"; window.print(); el.style.padding = "24px"; }}} style={{ background: "#fff", color: "#0D7377", border: "1px solid #0D7377", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
                    Download One-Pager &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* Recent prospect assessments */}
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0" }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: "#1B3A5C", margin: 0 }}>Recent Prospect Assessments</h3>
              </div>
              {recentProspects.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: "#94a3b8", fontSize: 14 }}>
                  No prospect assessments yet. Use the form above to assess a potential client before your first meeting.
                </div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#f8fafc" }}>
                      <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, color: "#64748b", fontWeight: 500 }}>Company</th>
                      <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, color: "#64748b", fontWeight: 500 }}>Segment</th>
                      <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 12, color: "#64748b", fontWeight: 500 }}>Date</th>
                      <th style={{ padding: "10px 16px", textAlign: "right", fontSize: 12, color: "#64748b", fontWeight: 500 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentProspects.map((p) => (
                      <tr key={p.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "10px 16px", fontSize: 14, fontWeight: 500, color: "#1B3A5C" }}>{p.company_name}</td>
                        <td style={{ padding: "10px 16px", fontSize: 13, color: "#64748b" }}>{p.result_json?.segment || `${p.industry} \u00B7 ${p.state}`}</td>
                        <td style={{ padding: "10px 16px", fontSize: 13, color: "#64748b" }}>{new Date(p.created_at).toLocaleDateString()}</td>
                        <td style={{ padding: "10px 16px", textAlign: "right" }}>
                          <button onClick={() => setProspectResult(p.result_json)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "#475569", cursor: "pointer", marginRight: 6 }}>View</button>
                          <button onClick={() => addProspectAsClient(p)} style={{ background: "none", border: "1px solid #0D7377", borderRadius: 6, padding: "4px 10px", fontSize: 12, color: "#0D7377", fontWeight: 500, cursor: "pointer" }}>Add as Client</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* ==================== BOOK OF BUSINESS TAB ==================== */}
        {activeTab === "book" && <>

        {/* Portfolio Summary */}
        {portfolio && portfolio.summary && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, textAlign: "center" }}>
              <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 6px", fontWeight: 500 }}>Total Clients</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>{portfolio.summary.total_clients}</p>
            </div>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, textAlign: "center" }}>
              <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 6px", fontWeight: 500 }}>Total Identified Excess</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: portfolio.summary.total_annual_excess > 0 ? "#EF4444" : "#1B3A5C", margin: 0 }}>
                {portfolio.summary.total_annual_excess >= 1000000
                  ? `$${(portfolio.summary.total_annual_excess / 1000000).toFixed(1)}M`
                  : fmt(portfolio.summary.total_annual_excess)}{" "}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#94a3b8" }}>across book</span>
              </p>
            </div>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, textAlign: "center" }}>
              <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 6px", fontWeight: 500 }}>Renewals in 90 Days</p>
              <p style={{ fontSize: 28, fontWeight: 700, color: portfolio.summary.clients_renewing_90_days > 0 ? "#f59e0b" : "#1B3A5C", margin: 0 }}>
                {portfolio.summary.clients_renewing_90_days}{" "}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#94a3b8" }}>clients</span>
              </p>
            </div>
          </div>
        )}

        {/* Book of Business Table */}
        {portfolio && portfolioClients.length > 0 && (
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, marginBottom: 24, overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0", fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>
              Book of Business
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                    <th style={{ ...thStyle, cursor: "pointer" }} onClick={() => handleSort("company_name")}>Company{sortArrow("company_name")}</th>
                    <th style={{ ...thStyle, cursor: "pointer" }} onClick={() => handleSort("employee_count_range")}>Size{sortArrow("employee_count_range")}</th>
                    <th style={{ ...thStyle, textAlign: "right", cursor: "pointer" }} onClick={() => handleSort("pepm")}>PEPM{sortArrow("pepm")}</th>
                    <th style={{ ...thStyle, textAlign: "center", cursor: "pointer" }} onClick={() => handleSort("percentile")}>Percentile{sortArrow("percentile")}</th>
                    <th style={{ ...thStyle, textAlign: "right", cursor: "pointer" }} onClick={() => handleSort("annual_gap")}>Annual Gap{sortArrow("annual_gap")}</th>
                    <th style={{ ...thStyle, cursor: "pointer" }} onClick={() => handleSort("renewal_month")}>Renewal{sortArrow("renewal_month")}</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Status</th>
                    <th style={thStyle}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioClients.map((c) => {
                    const dot = ACTIVITY_DOT[c.activity_status] || ACTIVITY_DOT.benchmark_only;
                    const renewing = isRenewing90(c.renewal_month);
                    const pctColor = c.percentile == null ? "#64748b" : c.percentile > 75 ? "#EF4444" : c.percentile > 50 ? "#f59e0b" : "#22c55e";
                    const pctBg = c.percentile == null ? "#f1f5f9" : c.percentile > 75 ? "#fef2f2" : c.percentile > 50 ? "#fffbeb" : "#f0fdf4";
                    return (
                      <tr key={c.employer_email} style={{ borderBottom: "1px solid #f1f5f9", borderLeft: renewing ? "3px solid #f59e0b" : "3px solid transparent" }}>
                        <td style={tdStyle}>
                          <p style={{ margin: 0, fontWeight: 600, color: "#1B3A5C" }}>{c.company_name}</p>
                          {c.industry && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 8, background: "#f1f5f9", color: "#64748b" }}>{c.industry}</span>}
                        </td>
                        <td style={tdStyle}>{c.employee_count_range || "—"}</td>
                        <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600 }}>{c.pepm != null ? fmt(c.pepm) : "—"}</td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          {c.percentile != null ? (
                            <span style={{ display: "inline-block", padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600, background: pctBg, color: pctColor }}>
                              {Math.round(c.percentile)}{ordinalSuffix(Math.round(c.percentile))}
                            </span>
                          ) : "—"}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: c.annual_gap > 0 ? "#EF4444" : "#475569" }}>
                          {c.annual_gap != null ? (c.annual_gap > 0 ? "+" : "") + fmt(c.annual_gap) : "—"}
                        </td>
                        <td style={tdStyle}>
                          {c.renewal_month ? new Date(c.renewal_month).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : "Unknown"}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          <div style={{ width: 10, height: 10, borderRadius: "50%", background: dot.color, margin: "0 auto" }} title={dot.label} />
                        </td>
                        <td style={tdStyle}>
                          <div style={{ display: "flex", gap: 4 }}>
                            {c.share_token && (
                              <button onClick={() => handleCopyShareLink(c.share_token)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#0D7377", cursor: "pointer" }}>Share</button>
                            )}
                            {c.employer_email && !c.employer_email.includes("@broker-onboarded") && c.share_token && (
                              <button onClick={() => handleNotify(c.employer_email)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#1d4ed8", cursor: "pointer" }}>Notify</button>
                            )}
                            <Link to={`/broker/renewal-prep/${encodeURIComponent(c.company_name.toLowerCase().replace(/\s+/g, "-"))}`} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#92400e", cursor: "pointer", textDecoration: "none", display: "inline-block" }}>Report</Link>
                            <button onClick={() => {
                              const match = clients.find(cl => cl.employer_email === c.employer_email);
                              if (match) handleSelectClient(match);
                            }} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#475569", cursor: "pointer" }}>Detail</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Renewal Pipeline */}
        {renewingClients.length > 0 && (
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: 20, marginBottom: 24 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#92400e", margin: "0 0 12px" }}>
              Upcoming Renewals ({renewingClients.length})
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {renewingClients.map((c) => (
                <div key={c.employer_email} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff", border: "1px solid #fde68a", borderRadius: 8, padding: "10px 16px" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: 14, color: "#1B3A5C" }}>{c.company_name}</p>
                    <p style={{ margin: "2px 0 0", fontSize: 12, color: "#92400e" }}>
                      Renews {new Date(c.renewal_month).toLocaleDateString("en-US", { month: "long", year: "numeric" })}
                      {c.annual_gap > 0 && ` · ${fmt(c.annual_gap)} annual gap`}
                    </p>
                  </div>
                  <Link to={`/broker/renewal-prep/${encodeURIComponent(c.company_name.toLowerCase().replace(/\s+/g, "-"))}`} style={{ background: "#92400e", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap", textDecoration: "none", display: "inline-block" }}>
                    Prepare Renewal Report &rarr;
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bulk Add Panel */}
        {showBulkPanel && (
          <div id="bulk-add-panel" style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 28, marginBottom: 24 }}>
            {bulkResults ? (
              /* Results summary */
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Bulk Import Complete</h3>
                <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
                  <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "16px 24px", flex: 1, textAlign: "center" }}>
                    <p style={{ fontSize: 28, fontWeight: 700, color: "#22c55e", margin: 0 }}>{bulkResults.filter(r => r.success).length}</p>
                    <p style={{ fontSize: 13, color: "#475569", margin: "4px 0 0" }}>clients added successfully</p>
                  </div>
                  {bulkResults.some(r => !r.success) && (
                    <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: "16px 24px", flex: 1, textAlign: "center" }}>
                      <p style={{ fontSize: 28, fontWeight: 700, color: "#d97706", margin: 0 }}>{bulkResults.filter(r => !r.success).length}</p>
                      <p style={{ fontSize: 13, color: "#475569", margin: "4px 0 0" }}>rows had errors</p>
                    </div>
                  )}
                </div>
                {/* Per-row results */}
                <div style={{ marginBottom: 20, maxHeight: 300, overflowY: "auto" }}>
                  {bulkResults.map((r, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderBottom: "1px solid #f1f5f9" }}>
                      <span style={{ fontSize: 16 }}>{r.success ? "\u2713" : "\u2717"}</span>
                      <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#1B3A5C" }}>{r.company_name}</span>
                      {r.success ? (
                        <span style={{ fontSize: 12, color: "#22c55e" }}>Benchmarked</span>
                      ) : (
                        <span style={{ fontSize: 12, color: "#d97706" }}>{r.error}</span>
                      )}
                    </div>
                  ))}
                </div>
                <button onClick={() => { setShowBulkPanel(false); setBulkResults(null); }} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
                  View Your Book of Business &rarr;
                </button>
              </div>
            ) : (
              /* Entry grid */
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                  <div>
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Add Multiple Clients</h3>
                    <p style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>Enter your client data below. Tip: you can copy a range from Excel and paste it directly into the grid.</p>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <button onClick={() => setShowBulkPanel(false)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 6, padding: "6px 14px", fontSize: 13, color: "#64748b", cursor: "pointer", textDecoration: "none" }}>
                      &larr; Back to Dashboard
                    </button>
                    <button onClick={handleBulkSubmit} disabled={bulkRunning || !bulkHasRequired} style={{ background: bulkHasRequired && !bulkRunning ? "#1B3A5C" : "#94a3b8", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: bulkHasRequired && !bulkRunning ? "pointer" : "default", opacity: bulkRunning ? 0.6 : 1 }}>
                      {bulkRunning ? `Running benchmarks... ${bulkProgress}/${bulkTotal}` : "Run Benchmarks \u2192"}
                    </button>
                  </div>
                </div>

                {bulkRunning && (
                  <div style={{ marginBottom: 16 }}>
                    <p style={{ fontSize: 14, fontWeight: 600, color: "#1B3A5C", margin: "0 0 8px" }}>Running benchmarks for {bulkTotal} clients...</p>
                    <div style={{ background: "#e2e8f0", borderRadius: 8, height: 8, overflow: "hidden", marginBottom: 8 }}>
                      <div style={{ background: "#0D7377", height: "100%", width: `${bulkTotal ? (bulkProgress / bulkTotal) * 100 : 0}%`, transition: "width 0.3s", borderRadius: 8 }} />
                    </div>
                    <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>{bulkProgress}/{bulkTotal} complete</p>
                  </div>
                )}

                <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 12px", fontStyle: "italic" }}>
                  Your client data is used only to run the benchmarks you request. We never contact your clients directly.
                </p>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 900 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                        <th style={thStyle}>Company Name <span style={{ color: "#EF4444" }}>*</span></th>
                        <th style={thStyle}>Employees <span style={{ color: "#EF4444" }}>*</span></th>
                        <th style={thStyle}>Industry <span style={{ color: "#EF4444" }}>*</span></th>
                        <th style={thStyle}>State <span style={{ color: "#EF4444" }}>*</span></th>
                        <th style={thStyle}>Carrier</th>
                        <th style={thStyle}>Est. PEPM</th>
                        <th style={thStyle}>Renewal</th>
                        <th style={{ ...thStyle, width: 36 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {bulkRows.map((row, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: 4 }}>
                            <input value={row.company_name} onChange={e => updateBulkRow(i, "company_name", e.target.value)} onPaste={e => handleBulkPaste(e, i, 0)} placeholder="Acme Corp" style={{ ...inputStyle, borderColor: bulkErrors[`${i}-company_name`] ? "#EF4444" : "#e2e8f0" }} />
                          </td>
                          <td style={{ padding: 4 }}>
                            <select value={row.employee_count_range} onChange={e => updateBulkRow(i, "employee_count_range", e.target.value)} onPaste={e => handleBulkPaste(e, i, 1)} style={{ ...inputStyle, borderColor: bulkErrors[`${i}-employee_count_range`] ? "#EF4444" : "#e2e8f0" }}>
                              <option value="">Select</option>
                              {EMPLOYEE_RANGES.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                          </td>
                          <td style={{ padding: 4 }}>
                            <select value={row.industry} onChange={e => updateBulkRow(i, "industry", e.target.value)} onPaste={e => handleBulkPaste(e, i, 2)} style={{ ...inputStyle, borderColor: bulkErrors[`${i}-industry`] ? "#EF4444" : "#e2e8f0" }}>
                              <option value="">Select</option>
                              {INDUSTRIES.map(ind => <option key={ind} value={ind}>{ind}</option>)}
                            </select>
                          </td>
                          <td style={{ padding: 4 }}>
                            <select value={row.state} onChange={e => updateBulkRow(i, "state", e.target.value)} onPaste={e => handleBulkPaste(e, i, 3)} style={{ ...inputStyle, borderColor: bulkErrors[`${i}-state`] ? "#EF4444" : "#e2e8f0" }}>
                              <option value="">Select</option>
                              {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </td>
                          <td style={{ padding: 4 }}>
                            <input value={row.carrier} onChange={e => updateBulkRow(i, "carrier", e.target.value)} onPaste={e => handleBulkPaste(e, i, 4)} placeholder="Optional" style={inputStyle} />
                          </td>
                          <td style={{ padding: 4 }}>
                            <input type="number" value={row.estimated_pepm} onChange={e => updateBulkRow(i, "estimated_pepm", e.target.value)} onPaste={e => handleBulkPaste(e, i, 5)} placeholder="$" style={{ ...inputStyle, width: 80 }} />
                          </td>
                          <td style={{ padding: 4 }}>
                            <div style={{ display: "flex", gap: 4 }}>
                              <select value={row.renewal_month} onChange={e => updateBulkRow(i, "renewal_month", e.target.value)} style={{ ...inputStyle, flex: 1, minWidth: 60 }}>
                                <option value="">Mo</option>
                                {MONTHS.map((m, mi) => <option key={m} value={String(mi + 1).padStart(2, "0")}>{m.slice(0, 3)}</option>)}
                              </select>
                              <select value={row.renewal_year} onChange={e => updateBulkRow(i, "renewal_year", e.target.value)} style={{ ...inputStyle, flex: 1, minWidth: 60 }}>
                                <option value="">Yr</option>
                                {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                              </select>
                            </div>
                          </td>
                          <td style={{ padding: 4, textAlign: "center" }}>
                            {bulkRows.length > 1 && (
                              <button onClick={() => setBulkRows(prev => prev.filter((_, j) => j !== i))} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 18, cursor: "pointer", padding: "0 4px", lineHeight: 1 }} title="Remove row">&times;</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {bulkRows.length < 50 && (
                  <button onClick={() => setBulkRows(prev => [...prev, EMPTY_ROW()])} style={{ background: "none", border: "1px dashed #e2e8f0", borderRadius: 8, padding: "8px 16px", fontSize: 13, color: "#64748b", cursor: "pointer", marginTop: 8, width: "100%" }}>
                    + Add Row
                  </button>
                )}
                {Object.keys(bulkErrors).length > 0 && (
                  <p style={{ color: "#991b1b", fontSize: 13, marginTop: 12 }}>Please fill in all required fields (highlighted in red) before submitting.</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Add Client Panel */}
        {showAddPanel && (
          <div id="add-client-panel" style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 28, marginBottom: 24 }}>
            {!onboardResult ? (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                  <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: 0 }}>Add New Client</h3>
                  <button onClick={() => setShowAddPanel(false)} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 6, padding: "4px 12px", fontSize: 13, color: "#64748b", cursor: "pointer" }}>Cancel</button>
                </div>
                <form onSubmit={handleOnboard}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                    <FormField label="Company name" required>
                      <input type="text" required value={addForm.company_name} onChange={(e) => setAddForm({ ...addForm, company_name: e.target.value })} placeholder="Acme Corp" style={inputStyle} />
                    </FormField>
                    <FormField label="Employee count">
                      <select value={addForm.employee_count_range} onChange={(e) => setAddForm({ ...addForm, employee_count_range: e.target.value })} style={inputStyle}>
                        {EMPLOYEE_RANGES.map((r) => <option key={r} value={r}>{EMPLOYEE_LABELS[r]}</option>)}
                      </select>
                    </FormField>
                    <FormField label="Industry">
                      <select value={addForm.industry} onChange={(e) => setAddForm({ ...addForm, industry: e.target.value })} style={inputStyle}>
                        {INDUSTRIES.map((i) => <option key={i} value={i}>{i}</option>)}
                      </select>
                    </FormField>
                    <FormField label="State">
                      <select value={addForm.state} onChange={(e) => setAddForm({ ...addForm, state: e.target.value })} style={inputStyle}>
                        {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </FormField>
                    <FormField label="Current carrier/TPA">
                      <input type="text" value={addForm.carrier} onChange={(e) => setAddForm({ ...addForm, carrier: e.target.value })} placeholder="e.g. Cigna, BCBS, Self-insured" list="carrier-suggestions" style={inputStyle} />
                      <datalist id="carrier-suggestions">
                        {CARRIER_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
                      </datalist>
                    </FormField>
                    <FormField label="Employer email (optional)">
                      <input type="email" value={addForm.employer_email} onChange={(e) => setAddForm({ ...addForm, employer_email: e.target.value })} placeholder="hr@employer.com" style={inputStyle} />
                    </FormField>
                    <FormField label="Renewal month (optional)">
                      <div style={{ display: "flex", gap: 8 }}>
                        <select value={addForm.renewal_month} onChange={(e) => setAddForm({ ...addForm, renewal_month: e.target.value })} style={{ ...inputStyle, flex: 1 }}>
                          <option value="">Month</option>
                          {MONTHS.map((m, i) => <option key={m} value={String(i + 1).padStart(2, "0")}>{m}</option>)}
                        </select>
                        <select value={addForm.renewal_year} onChange={(e) => setAddForm({ ...addForm, renewal_year: e.target.value })} style={{ ...inputStyle, flex: 1 }}>
                          <option value="">Year</option>
                          {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
                        </select>
                      </div>
                    </FormField>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                    <FormField label="Estimated monthly PEPM (optional)" hint="Improves benchmark accuracy">
                      <input type="number" step="0.01" min="0" value={addForm.estimated_pepm} onChange={(e) => setAddForm({ ...addForm, estimated_pepm: e.target.value })} placeholder="e.g. 620" style={inputStyle} />
                    </FormField>
                    <FormField label="Estimated annual spend (optional)" hint="Or use this instead of PEPM">
                      <input type="number" step="1" min="0" value={addForm.estimated_annual_spend} onChange={(e) => setAddForm({ ...addForm, estimated_annual_spend: e.target.value })} placeholder="e.g. 2400000" style={inputStyle} />
                    </FormField>
                  </div>
                  {addError && addError === "CLIENT_LIMIT_REACHED" ? (
                    <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "12px 16px", marginBottom: 12 }}>
                      <p style={{ color: "#991b1b", fontSize: 13, margin: "0 0 8px", fontWeight: 500 }}>You've reached the 10-client limit. Upgrade to Pro to add more clients.</p>
                      <button onClick={handleUpgrade} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>Upgrade to Pro &mdash; $99/mo &rarr;</button>
                    </div>
                  ) : addError ? (
                    <p style={{ color: "#991b1b", fontSize: 13, marginBottom: 12 }}>{addError}</p>
                  ) : null}
                  <button type="submit" disabled={addLoading || !addForm.company_name} style={{ background: "#1B3A5C", color: "#fff", border: "none", borderRadius: 8, padding: "12px 28px", fontSize: 14, fontWeight: 600, cursor: "pointer", opacity: addLoading ? 0.6 : 1 }}>
                    {addLoading ? "Running benchmark..." : "Add Client & Run Benchmark"}
                  </button>
                </form>
              </>
            ) : (
              /* Onboard Success */
              <OnboardSuccess
                result={onboardResult}
                brokerEmail={broker.email}
                onCopyLink={handleCopyShareLink}
                onNotify={handleNotify}
                shareCopied={shareCopied}
                notifySent={notifySent}
                shareLoading={shareLoading}
                onDone={() => { setShowAddPanel(false); setOnboardResult(null); }}
                fmt={fmt}
              />
            )}
          </div>
        )}

        {/* Main Layout: Client List + Detail Panel */}
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          {/* Client List */}
          <div style={{ width: 400, flexShrink: 0 }}>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0", fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>
                Employer Clients ({clients.length})
              </div>

              {loading ? (
                <div style={{ padding: 32, textAlign: "center", color: "#94a3b8" }}>Loading clients...</div>
              ) : clients.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: "#94a3b8", fontSize: 14 }}>
                  No clients yet. Click "Add Client" to get started.
                </div>
              ) : (
                clients.map((client) => {
                  const isSelected = selectedClient?.employer_email === client.employer_email;
                  const dot = ACTIVITY_DOT[client.activity_status] || ACTIVITY_DOT.benchmark_only;
                  return (
                    <div
                      key={client.employer_email}
                      onClick={() => handleSelectClient(client)}
                      style={{
                        padding: "14px 20px", borderBottom: "1px solid #f1f5f9",
                        cursor: "pointer", transition: "background 0.15s",
                        background: isSelected ? "#f0fdfa" : "#fff",
                        borderLeft: isSelected ? "3px solid #0D7377" : "3px solid transparent",
                      }}
                      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "#f8fafc"; }}
                      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "#fff"; }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <div style={{ width: 10, height: 10, borderRadius: "50%", background: dot.color, flexShrink: 0 }} title={dot.label} />
                          <div>
                            <p style={{ margin: 0, fontWeight: 600, fontSize: 14, color: "#1B3A5C" }}>
                              {client.company_name}
                            </p>
                            <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
                              {client.employer_email.includes("@broker-onboarded") ? "No email on file" : client.employer_email}
                            </p>
                          </div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <span style={{
                            display: "inline-block", padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                            background: client.subscription_status === "active" ? "#dcfce7" : client.has_benchmark ? "#eff6ff" : "#f1f5f9",
                            color: client.subscription_status === "active" ? "#166534" : client.has_benchmark ? "#1d4ed8" : "#64748b",
                          }}>
                            {client.subscription_status === "active" ? client.tier : client.has_benchmark ? "benchmarked" : "free"}
                          </span>
                          {client.claims_uploads > 0 && (
                            <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94a3b8" }}>
                              {client.claims_uploads} upload{client.claims_uploads !== 1 ? "s" : ""}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Activity Legend */}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 12, padding: "0 4px" }}>
              {Object.entries(ACTIVITY_DOT).map(([key, { color, label }]) => (
                <div key={key} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#94a3b8" }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
                  {label}
                </div>
              ))}
            </div>
          </div>

          {/* Detail Panel */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {!selectedClient ? (
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 48, textAlign: "center", color: "#94a3b8" }}>
                <p style={{ fontSize: 16, margin: "0 0 8px" }}>Select a client to view details</p>
                <p style={{ fontSize: 13 }}>Click on an employer from the list to see their benchmark, claims, and activity.</p>
              </div>
            ) : summaryLoading ? (
              <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 48, textAlign: "center" }}>
                <div style={{ width: 36, height: 36, border: "3px solid #e2e8f0", borderTopColor: "#0D7377", borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px" }} />
                <p style={{ color: "#64748b", fontSize: 14 }}>Loading summary...</p>
                <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            ) : clientSummary ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {/* Client Header */}
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <h2 style={{ fontSize: 22, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>{clientSummary.company_name}</h2>
                    <p style={{ fontSize: 13, color: "#94a3b8", marginTop: 4 }}>{clientSummary.employer_email}</p>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    {selectedClient.share_token && (
                      <>
                        <button onClick={() => handleCopyShareLink(selectedClient.share_token)} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                          {shareCopied ? "Copied!" : "Copy Share Link"}
                        </button>
                        {selectedClient.employer_email && !selectedClient.employer_email.includes("@broker-onboarded") && (
                          <button onClick={() => handleNotify(selectedClient.employer_email)} disabled={shareLoading || notifySent} style={{ background: notifySent ? "#dcfce7" : "#f0f9ff", color: notifySent ? "#166534" : "#1d4ed8", border: "1px solid " + (notifySent ? "#bbf7d0" : "#bfdbfe"), borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: notifySent ? "default" : "pointer" }}>
                            {notifySent ? "Email Sent" : shareLoading ? "Sending..." : "Email Report"}
                          </button>
                        )}
                      </>
                    )}
                    <span style={{ padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 600, background: clientSummary.subscription.status === "active" ? "#dcfce7" : "#f1f5f9", color: clientSummary.subscription.status === "active" ? "#166534" : "#64748b" }}>
                      {clientSummary.subscription.tier} · {clientSummary.subscription.status}
                    </span>
                    {clientSummary.subscription.status !== "active" && selectedClient.employer_email && !selectedClient.employer_email.includes("@broker-onboarded") && (
                      <button onClick={() => handleSuggestUpgrade(selectedClient.employer_email)} disabled={shareLoading || upgradeSent} style={{ background: upgradeSent ? "#dcfce7" : "#fef3c7", color: upgradeSent ? "#166534" : "#92400e", border: "1px solid " + (upgradeSent ? "#bbf7d0" : "#fde68a"), borderRadius: 6, padding: "6px 14px", fontSize: 12, fontWeight: 600, cursor: upgradeSent ? "default" : "pointer" }}>
                        {upgradeSent ? "Upgrade email sent" : shareLoading ? "Sending..." : "Suggest Upgrade"}
                      </button>
                    )}
                    <button onClick={() => handleRemoveClient(clientSummary.employer_email)} style={{ background: "none", border: "1px solid #fecaca", borderRadius: 6, padding: "4px 10px", fontSize: 11, color: "#991b1b", cursor: "pointer" }}>
                      Remove
                    </button>
                  </div>
                </div>

                {/* Broker Notes — How to present this to your client */}
                <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 12, overflow: "hidden" }}>
                  <button
                    onClick={() => setBrokerNotesOpen(!brokerNotesOpen)}
                    style={{ width: "100%", background: "none", border: "none", padding: "16px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#3b82f6", letterSpacing: "0.08em", textTransform: "uppercase" }}>BROKER NOTES</span>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>How to present this to your client</span>
                    </div>
                    <span style={{ fontSize: 16, color: "#64748b", transform: brokerNotesOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>{"\u25BE"}</span>
                  </button>
                  {brokerNotesOpen && (
                    <div style={{ padding: "0 24px 20px" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <div style={{ display: "flex", gap: 10 }}>
                          <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#1d4ed8", flexShrink: 0 }}>1</span>
                          <p style={{ margin: 0, fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                            <strong>Lead with opportunity, not blame.</strong> Frame the benchmark as a tool to find savings at renewal — not evidence that the employer chose a bad plan. "This shows where you have the most leverage" is better than "you're overpaying."
                          </p>
                        </div>
                        <div style={{ display: "flex", gap: 10 }}>
                          <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#1d4ed8", flexShrink: 0 }}>2</span>
                          <p style={{ margin: 0, fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                            <strong>Normalize the percentile.</strong> Most employers land between the 40th and 70th percentile. Being above median is extremely common — especially in high-cost states or industries with older workforces.
                          </p>
                        </div>
                        <div style={{ display: "flex", gap: 10 }}>
                          <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#1d4ed8", flexShrink: 0 }}>3</span>
                          <p style={{ margin: 0, fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                            <strong>Point to the cost drivers, not the total.</strong> The top cost drivers section is designed to shift the conversation from "how much" to "where" — focus on the specific categories (specialist rates, imaging, pharmacy) where you can negotiate or restructure.
                          </p>
                        </div>
                        <div style={{ display: "flex", gap: 10 }}>
                          <span style={{ width: 22, height: 22, borderRadius: "50%", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#1d4ed8", flexShrink: 0 }}>4</span>
                          <p style={{ margin: 0, fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
                            <strong>Suggest the next step immediately.</strong> Recommend uploading one month of claims data or running the plan scorecard — this turns the conversation from a static report into an action plan that positions you as the guide.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Claims Summary Cards */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                  {[
                    { label: "Total Uploads", value: clientSummary.claims_summary.total_uploads },
                    { label: "Total Claims", value: clientSummary.claims_summary.total_claims.toLocaleString() },
                    { label: "Total Paid", value: fmt(clientSummary.claims_summary.total_paid) },
                    { label: "Excess > 2x", value: fmt(clientSummary.claims_summary.total_excess_2x), color: clientSummary.claims_summary.total_excess_2x > 0 ? "#EF4444" : "#1B3A5C" },
                  ].map((card) => (
                    <div key={card.label} style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, textAlign: "center" }}>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px", fontWeight: 500 }}>{card.label}</p>
                      <p style={{ fontSize: 22, fontWeight: 700, margin: 0, color: card.color || "#1B3A5C" }}>{card.value}</p>
                    </div>
                  ))}
                </div>

                {/* Level 2 Insights */}
                {clientSummary.claims_summary.level2 && clientSummary.claims_summary.level2.has_level2 && (
                  <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 12, padding: "16px 20px" }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "#0D7377", margin: "0 0 8px" }}>LEVEL 2 INSIGHTS</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: "#475569" }}>
                      {clientSummary.claims_summary.level2.provider_variation.total_variation_opportunity > 0 && (
                        <p style={{ margin: 0 }}>Provider variation: <strong style={{ color: "#0D7377" }}>{fmt(clientSummary.claims_summary.level2.provider_variation.total_variation_opportunity)}</strong> opportunity</p>
                      )}
                      {clientSummary.claims_summary.level2.site_of_care.total_site_opportunity > 0 && (
                        <p style={{ margin: 0 }}>Site of care: <strong style={{ color: "#0D7377" }}>{fmt(clientSummary.claims_summary.level2.site_of_care.total_site_opportunity)}</strong> opportunity</p>
                      )}
                      <p style={{ margin: 0 }}>Network: <strong style={{ color: clientSummary.claims_summary.level2.network_leakage.flag === "HIGH" ? "#EF4444" : clientSummary.claims_summary.level2.network_leakage.flag === "MODERATE" ? "#f59e0b" : "#22c55e" }}>{clientSummary.claims_summary.level2.network_leakage.flag}</strong> out-of-network</p>
                    </div>
                  </div>
                )}

                {/* ── Claims Upload Section ── */}
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Upload Claims Data</h3>
                  <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 16px" }}>Upload 835 EDI, CSV, Excel, or ZIP of 835 files for this client.</p>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>Claims file *</label>
                      <input
                        type="file"
                        accept=".835,.edi,.csv,.xlsx,.xls,.zip,.txt"
                        onChange={(e) => { setClaimsFile(e.target.files?.[0] || null); setClaimsUploadResult(null); setClaimsUploadError(""); }}
                        style={{ fontSize: 13, color: "#475569" }}
                      />
                    </div>
                    <div style={{ width: 120 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>ZIP code *</label>
                      <input
                        type="text"
                        maxLength={5}
                        value={claimsZip}
                        onChange={(e) => setClaimsZip(e.target.value.replace(/\D/g, "").slice(0, 5))}
                        placeholder="10001"
                        style={{ width: "100%", padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, boxSizing: "border-box" }}
                      />
                    </div>
                    <button
                      onClick={handleClaimsUpload}
                      disabled={claimsUploading || !claimsFile || claimsZip.length !== 5}
                      style={{
                        padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: claimsUploading || !claimsFile || claimsZip.length !== 5 ? "#cbd5e1" : "#0D7377",
                        color: "#fff", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap",
                      }}
                    >
                      {claimsUploading ? "Analyzing..." : "Upload & Analyze"}
                    </button>
                  </div>
                  {claimsUploadError && (
                    <div style={{ marginTop: 12, padding: 10, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8 }}>
                      <p style={{ color: "#991b1b", fontSize: 12, margin: 0 }}>{claimsUploadError}</p>
                    </div>
                  )}
                  {claimsUploadResult && (
                    <div style={{ marginTop: 12, padding: 12, background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "#0D7377", margin: "0 0 6px" }}>Claims analysis complete</p>
                      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, color: "#475569" }}>
                        <span><strong>{claimsUploadResult.summary.total_claims}</strong> claims</span>
                        <span>Total paid: <strong>{fmt(claimsUploadResult.summary.total_paid)}</strong></span>
                        <span>Excess &gt;2x: <strong style={{ color: claimsUploadResult.summary.total_excess_2x > 0 ? "#EF4444" : "#475569" }}>{fmt(claimsUploadResult.summary.total_excess_2x)}</strong></span>
                      </div>
                      {claimsUploadResult.narrative && (
                        <p style={{ fontSize: 12, color: "#475569", margin: "8px 0 0", lineHeight: 1.5 }}>{claimsUploadResult.narrative}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* ── Scorecard Upload Section ── */}
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Upload Plan Scorecard (SBC)</h3>
                  <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 16px" }}>Upload a Summary of Benefits and Coverage PDF to grade this client's plan.</p>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>SBC PDF *</label>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => { setScorecardFile(e.target.files?.[0] || null); setScorecardUploadResult(null); setScorecardUploadError(""); }}
                        style={{ fontSize: 13, color: "#475569" }}
                      />
                    </div>
                    <button
                      onClick={handleScorecardUpload}
                      disabled={scorecardUploading || !scorecardFile}
                      style={{
                        padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: scorecardUploading || !scorecardFile ? "#cbd5e1" : "#0D7377",
                        color: "#fff", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap",
                      }}
                    >
                      {scorecardUploading ? "Grading..." : "Upload & Grade Plan"}
                    </button>
                  </div>
                  {scorecardUploadError && (
                    <div style={{ marginTop: 12, padding: 10, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8 }}>
                      <p style={{ color: "#991b1b", fontSize: 12, margin: 0 }}>{scorecardUploadError}</p>
                    </div>
                  )}
                  {scorecardUploadResult && (
                    <div style={{ marginTop: 12, padding: 12, background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "#0D7377", margin: "0 0 6px" }}>
                        Plan grade: <span style={{ fontSize: 18 }}>{scorecardUploadResult.grade}</span>
                        <span style={{ fontWeight: 400, color: "#475569", marginLeft: 8 }}>({scorecardUploadResult.score}/100)</span>
                      </p>
                      <p style={{ fontSize: 12, color: "#475569", margin: 0 }}>
                        {scorecardUploadResult.plan_name} ({scorecardUploadResult.network_type})
                        {scorecardUploadResult.savings_estimate_per_ee && (
                          <span> &mdash; est. savings: <strong>{fmt(scorecardUploadResult.savings_estimate_per_ee)}</strong>/employee/year</span>
                        )}
                      </p>
                      {scorecardUploadResult.interpretation && (
                        <p style={{ fontSize: 12, color: "#475569", margin: "6px 0 0", lineHeight: 1.5 }}>{scorecardUploadResult.interpretation}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Gated Features — show lock icons for non-subscribers */}
                {clientSummary.subscription.status !== "active" && (
                  <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Available with Subscription</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      {[
                        { label: "Unlimited Claims Analysis", desc: "Compare every claim against Medicare benchmarks" },
                        { label: "RBP Calculator", desc: "Model reference-based pricing savings" },
                        { label: "Contract Parser", desc: "Extract and benchmark carrier rates" },
                        { label: "Trend Monitoring", desc: "Monthly PEPM tracking with AI alerts" },
                      ].map((feat) => (
                        <div key={feat.label} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 12, background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
                          <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>&#128274;</span>
                          <div>
                            <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#475569" }}>{feat.label}</p>
                            <p style={{ margin: "2px 0 0", fontSize: 11, color: "#94a3b8" }}>{feat.desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <p style={{ margin: "14px 0 0", fontSize: 12, color: "#94a3b8" }}>
                      Free tier: benchmark + scorecard + 1 claims check per quarter.
                      {selectedClient.employer_email && !selectedClient.employer_email.includes("@broker-onboarded") && (
                        <button onClick={() => handleSuggestUpgrade(selectedClient.employer_email)} disabled={shareLoading || upgradeSent} style={{ background: "none", border: "none", color: "#0D7377", fontWeight: 600, cursor: "pointer", fontSize: 12, marginLeft: 4 }}>
                          {upgradeSent ? "Upgrade email sent" : "Suggest upgrade to client"}
                        </button>
                      )}
                    </p>
                  </div>
                )}

                {/* ── Claims Upload Section ── */}
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Upload Claims Data</h3>
                  <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 16px" }}>Upload 835 EDI, CSV, Excel, or ZIP of 835 files for this client.</p>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>Claims file *</label>
                      <input
                        type="file"
                        accept=".835,.edi,.csv,.xlsx,.xls,.zip,.txt"
                        onChange={(e) => { setClaimsFile(e.target.files?.[0] || null); setClaimsUploadResult(null); setClaimsUploadError(""); }}
                        style={{ fontSize: 13, color: "#475569" }}
                      />
                    </div>
                    <div style={{ width: 120 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>ZIP code *</label>
                      <input
                        type="text"
                        maxLength={5}
                        value={claimsZip}
                        onChange={(e) => setClaimsZip(e.target.value.replace(/\D/g, "").slice(0, 5))}
                        placeholder="10001"
                        style={{ width: "100%", padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, boxSizing: "border-box" }}
                      />
                    </div>
                    <button
                      onClick={handleClaimsUpload}
                      disabled={claimsUploading || !claimsFile || claimsZip.length !== 5}
                      style={{
                        padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: claimsUploading || !claimsFile || claimsZip.length !== 5 ? "#cbd5e1" : "#0D7377",
                        color: "#fff", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap",
                      }}
                    >
                      {claimsUploading ? "Analyzing..." : "Upload & Analyze"}
                    </button>
                  </div>
                  {claimsUploadError && (
                    <div style={{ marginTop: 12, padding: 10, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8 }}>
                      <p style={{ color: "#991b1b", fontSize: 12, margin: 0 }}>{claimsUploadError}</p>
                    </div>
                  )}
                  {claimsUploadResult && (
                    <div style={{ marginTop: 12, padding: 12, background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "#0D7377", margin: "0 0 6px" }}>Claims analysis complete</p>
                      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, color: "#475569" }}>
                        <span><strong>{claimsUploadResult.summary.total_claims}</strong> claims</span>
                        <span>Total paid: <strong>{fmt(claimsUploadResult.summary.total_paid)}</strong></span>
                        <span>Excess &gt;2x: <strong style={{ color: claimsUploadResult.summary.total_excess_2x > 0 ? "#EF4444" : "#475569" }}>{fmt(claimsUploadResult.summary.total_excess_2x)}</strong></span>
                      </div>
                      {claimsUploadResult.narrative && (
                        <p style={{ fontSize: 12, color: "#475569", margin: "8px 0 0", lineHeight: 1.5 }}>{claimsUploadResult.narrative}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* ── Scorecard Upload Section ── */}
                <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Upload Plan Scorecard (SBC)</h3>
                  <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 16px" }}>Upload a Summary of Benefits and Coverage PDF to grade this client's plan.</p>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>SBC PDF *</label>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => { setScorecardFile(e.target.files?.[0] || null); setScorecardUploadResult(null); setScorecardUploadError(""); }}
                        style={{ fontSize: 13, color: "#475569" }}
                      />
                    </div>
                    <button
                      onClick={handleScorecardUpload}
                      disabled={scorecardUploading || !scorecardFile}
                      style={{
                        padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
                        background: scorecardUploading || !scorecardFile ? "#cbd5e1" : "#0D7377",
                        color: "#fff", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap",
                      }}
                    >
                      {scorecardUploading ? "Grading..." : "Upload & Grade"}
                    </button>
                  </div>
                  {scorecardUploadError && (
                    <div style={{ marginTop: 12, padding: 10, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8 }}>
                      <p style={{ color: "#991b1b", fontSize: 12, margin: 0 }}>{scorecardUploadError}</p>
                    </div>
                  )}
                  {scorecardUploadResult && (
                    <div style={{ marginTop: 12, padding: 12, background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 8 }}>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "#0D7377", margin: "0 0 6px" }}>
                        Plan grade: <span style={{ fontSize: 18 }}>{scorecardUploadResult.grade}</span>
                        <span style={{ fontWeight: 400, color: "#475569", marginLeft: 8 }}>({scorecardUploadResult.score}/100)</span>
                      </p>
                      <p style={{ fontSize: 12, color: "#475569", margin: 0 }}>
                        {scorecardUploadResult.plan_name} ({scorecardUploadResult.network_type})
                        {scorecardUploadResult.savings_estimate_per_ee && (
                          <span> &mdash; est. savings: <strong>{fmt(scorecardUploadResult.savings_estimate_per_ee)}</strong>/employee/year</span>
                        )}
                      </p>
                      {scorecardUploadResult.interpretation && (
                        <p style={{ fontSize: 12, color: "#475569", margin: "6px 0 0", lineHeight: 1.5 }}>{scorecardUploadResult.interpretation}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Activity Timeline */}
                {clientActivity && clientActivity.events && clientActivity.events.length > 0 && (
                  <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Activity Timeline</h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                      {clientActivity.events.slice(0, 10).map((ev, i) => (
                        <div key={i} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: i < clientActivity.events.length - 1 ? "1px solid #f1f5f9" : "none" }}>
                          <div style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 5, flexShrink: 0, background: ev.type === "subscribed" ? "#22c55e" : ev.type === "claims_uploaded" ? "#3b82f6" : ev.type === "report_viewed" ? "#f59e0b" : "#94a3b8" }} />
                          <div style={{ flex: 1 }}>
                            <p style={{ margin: 0, fontSize: 13, color: "#475569" }}>{ev.label}</p>
                            <p style={{ margin: "2px 0 0", fontSize: 11, color: "#94a3b8" }}>
                              {new Date(ev.timestamp).toLocaleDateString()} at {new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upload Timeline */}
                {clientSummary.upload_timeline && clientSummary.upload_timeline.length > 0 && (
                  <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Claims Upload History</h3>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                          <th style={thStyle}>Date</th>
                          <th style={thStyle}>File</th>
                          <th style={{ ...thStyle, textAlign: "right" }}>Claims</th>
                          <th style={{ ...thStyle, textAlign: "right" }}>Total Paid</th>
                          <th style={{ ...thStyle, textAlign: "right" }}>Excess &gt; 2x</th>
                          <th style={thStyle}>Top CPT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {clientSummary.upload_timeline.map((u) => (
                          <tr key={u.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={tdStyle}>{new Date(u.created_at).toLocaleDateString()}</td>
                            <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.filename || "—"}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>{(u.total_claims || 0).toLocaleString()}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(u.total_paid)}</td>
                            <td style={{ ...tdStyle, textAlign: "right", color: u.total_excess_2x > 0 ? "#EF4444" : "#475569", fontWeight: u.total_excess_2x > 0 ? 600 : 400 }}>{fmt(u.total_excess_2x)}</td>
                            <td style={tdStyle}>{u.top_flagged_cpt || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Trends Summary */}
                {clientSummary.trends && (
                  <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>PEPM Trend Summary</h3>
                    {clientSummary.trends_computed_at && (
                      <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 16px" }}>
                        Computed {new Date(clientSummary.trends_computed_at).toLocaleDateString()}
                      </p>
                    )}
                    {clientSummary.trends.months && clientSummary.trends.months.length > 0 && (
                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                        {clientSummary.trends.months.slice(-6).map((m) => (
                          <div key={m.month} style={{ padding: "12px 16px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0", minWidth: 100, textAlign: "center" }}>
                            <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 4px" }}>{m.month}</p>
                            <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>${(m.pepm || 0).toFixed(0)}</p>
                            <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>PEPM</p>
                          </div>
                        ))}
                      </div>
                    )}
                    {clientSummary.trends.narrative && (
                      <div style={{ marginTop: 16, padding: 16, background: "#f0fdfa", borderRadius: 8, border: "1px solid #99f6e4", fontSize: 13, color: "#1B3A5C", lineHeight: 1.6 }}>
                        {clientSummary.trends.narrative}
                      </div>
                    )}
                  </div>
                )}

                {/* Subscription Info */}
                {clientSummary.subscription.employee_count && (
                  <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, display: "flex", gap: 32 }}>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Employee Count</p>
                      <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>{clientSummary.subscription.employee_count.toLocaleString()}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Subscription Tier</p>
                      <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>{clientSummary.subscription.tier}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Status</p>
                      <p style={{ fontSize: 18, fontWeight: 700, margin: 0, color: clientSummary.subscription.status === "active" ? "#0D7377" : "#64748b" }}>{clientSummary.subscription.status}</p>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>

        </>}
      </div>

      {/* Invite Employer Modal */}
      {showInviteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", borderRadius: 16, padding: 32, maxWidth: 440, width: "90%", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: "0 0 12px" }}>Invite an Employer Client</h3>
            <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.6, margin: "0 0 20px" }}>
              Send a Parity Employer invitation to your client. They'll receive an email with a link to start a 30-day free trial.
            </p>

            {inviteResult ? (
              <div style={{ textAlign: "center" }}>
                {inviteResult.invited ? (
                  <div style={{ padding: 16, background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 8, marginBottom: 16 }}>
                    <p style={{ color: "#0D7377", fontWeight: 600, fontSize: 14, margin: 0 }}>
                      Invitation sent to {inviteResult.email}
                    </p>
                  </div>
                ) : (
                  <div style={{ padding: 16, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, marginBottom: 16 }}>
                    <p style={{ color: "#92400e", fontSize: 14, margin: 0 }}>
                      {inviteResult.reason || "This employer has already been invited."}
                    </p>
                  </div>
                )}
                <button
                  onClick={() => setShowInviteModal(false)}
                  style={{ background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
                >
                  Close
                </button>
              </div>
            ) : (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#475569", marginBottom: 4 }}>Employer contact email</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !inviteLoading && inviteEmail.includes("@") && (async () => {
                      setInviteLoading(true);
                      try {
                        const res = await fetch(`${API}/api/broker/invite-employer`, {
                          method: "POST", headers: { "Content-Type": "application/json", ...authHeaders },
                          body: JSON.stringify({ email: inviteEmail.trim() }),
                        });
                        setInviteResult(await res.json());
                      } catch { setInviteResult({ invited: false, reason: "Failed to send invitation." }); }
                      setInviteLoading(false);
                    })()}
                    placeholder="employer@company.com"
                    style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, fontFamily: "inherit", boxSizing: "border-box" }}
                  />
                </div>
                <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                  <button
                    onClick={() => setShowInviteModal(false)}
                    style={{ background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      if (!inviteEmail.includes("@")) return;
                      setInviteLoading(true);
                      try {
                        const res = await fetch(`${API}/api/broker/invite-employer`, {
                          method: "POST", headers: { "Content-Type": "application/json", ...authHeaders },
                          body: JSON.stringify({ email: inviteEmail.trim() }),
                        });
                        setInviteResult(await res.json());
                      } catch { setInviteResult({ invited: false, reason: "Failed to send invitation." }); }
                      setInviteLoading(false);
                    }}
                    disabled={inviteLoading || !inviteEmail.includes("@")}
                    style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: inviteLoading ? "default" : "pointer", opacity: inviteLoading ? 0.7 : 1 }}
                  >
                    {inviteLoading ? "Sending..." : "Send Invitation"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BrokerDashboard() {
  return (
    <AuthGate product="broker" onNeedsCompany={() => { window.location.href = "/broker/signup"; }}>
      <BrokerDashboardInner />
    </AuthGate>
  );
}


// ---------------------------------------------------------------------------
// RenewalColumn — one column of the renewal pipeline
// ---------------------------------------------------------------------------

function RenewalColumn({ title, subtitle, clients: columnClients, borderColor, titleColor, bgColor, muted, brokerEmail }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "14px 16px", borderBottom: `3px solid ${borderColor}`, background: bgColor }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: titleColor }}>{title}</div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>{subtitle} &middot; {columnClients.length} client{columnClients.length !== 1 ? "s" : ""}</div>
      </div>
      {columnClients.length === 0 ? (
        <div style={{ padding: 24, textAlign: "center", color: "#94a3b8", fontSize: 13 }}>No clients</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {columnClients.map((c) => (
            <div key={c.employer_email} style={{ padding: "14px 16px", borderBottom: "1px solid #f1f5f9", opacity: muted ? 0.7 : 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <div>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>{c.company_name}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: "#64748b" }}>
                    {c.renewal_month ? new Date(c.renewal_month).toLocaleDateString("en-US", { month: "long", year: "numeric" }) : ""}
                    {c.employee_count_range ? ` \u00B7 ${c.employee_count_range}` : ""}
                  </p>
                </div>
                {c.days_until_renewal != null && (
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 10, background: c.days_until_renewal <= 30 ? "#fef2f2" : c.days_until_renewal <= 90 ? "#fffbeb" : "#f1f5f9", color: c.days_until_renewal <= 30 ? "#991b1b" : c.days_until_renewal <= 90 ? "#92400e" : "#64748b", whiteSpace: "nowrap" }}>
                    {c.days_until_renewal <= 0 ? "Past due" : `${c.days_until_renewal}d`}
                  </span>
                )}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px", fontSize: 12 }}>
                <ChecklistItem label="Benchmark run" done={c.checklist.benchmark_run} />
                <ChecklistItem label="Claims check" done={c.checklist.claims_check} />
                <ChecklistItem label="Scorecard graded" done={c.checklist.scorecard_graded} />
                <Link to={`/broker/renewal-prep/${encodeURIComponent(c.company_name.toLowerCase().replace(/\s+/g, "-"))}`} style={{ display: "flex", alignItems: "center", gap: 6, color: "#0D7377", fontWeight: 600, textDecoration: "none", fontSize: 12 }}>
                  Prepare Renewal Report &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// RenewalNoDateSection — clients without renewal dates
// ---------------------------------------------------------------------------

function RenewalNoDateSection({ clients: noDateClients, onSelectClient }) {
  if (noDateClients.length === 0) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "14px 16px", borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#64748b" }}>No renewal date set ({noDateClients.length})</div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Edit these clients to add a renewal month</div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: 16 }}>
        {noDateClients.map((c) => (
          <button
            key={c.employer_email}
            onClick={() => onSelectClient(c.employer_email)}
            style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "8px 14px", fontSize: 13, color: "#475569", cursor: "pointer" }}
          >
            {c.company_name}
          </button>
        ))}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// ChecklistItem — single checklist row
// ---------------------------------------------------------------------------

function ChecklistItem({ label, done, comingSoon }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 13, color: done ? "#22c55e" : "#cbd5e1" }}>{done ? "\u2713" : "\u25CB"}</span>
      <span style={{ color: comingSoon ? "#cbd5e1" : done ? "#475569" : "#94a3b8", fontStyle: comingSoon ? "italic" : "normal" }}>
        {label}{comingSoon && " (coming soon)"}
      </span>
    </div>
  );
}


// ---------------------------------------------------------------------------
// OnboardSuccess — shown after successful client onboard + benchmark
// ---------------------------------------------------------------------------

function OnboardSuccess({ result, brokerEmail, onCopyLink, onNotify, shareCopied, notifySent, shareLoading, onDone, fmt }) {
  const bench = result.benchmark_result || {};
  const res = bench.result || {};
  const dist = bench.distribution || {};
  const benchmarks = bench.benchmarks || {};

  const percentile = res.percentile || 50;
  const pepm = bench.input?.pepm_input || 0;
  const gapMonthly = res.dollar_gap_monthly || 0;
  const gapAnnual = res.dollar_gap_annual || 0;

  const hasEmail = result.employer_email && !result.employer_email.includes("@broker-onboarded");

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: 0 }}>
          Benchmark Complete — {result.company_name}
        </h3>
        <button onClick={onDone} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
          Done
        </button>
      </div>

      {/* Percentile Gauge */}
      <div style={{ display: "flex", gap: 20, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 260, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px" }}>PEPM Percentile</p>
          <p style={{ fontSize: 42, fontWeight: 700, color: percentile > 60 ? "#EF4444" : percentile > 40 ? "#f59e0b" : "#22c55e", margin: 0 }}>
            {Math.round(percentile)}{ordinalSuffix(Math.round(percentile))}
          </p>
          <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>{res.interpretation}</p>
        </div>
        <div style={{ flex: 1, minWidth: 260, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, padding: 24, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px" }}>Monthly Gap vs Median</p>
          <p style={{ fontSize: 42, fontWeight: 700, color: gapMonthly > 0 ? "#EF4444" : "#22c55e", margin: 0 }}>
            {gapMonthly > 0 ? "+" : ""}{fmt(gapMonthly)}
          </p>
          <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
            {fmt(pepm)} PEPM vs {fmt(benchmarks.adjusted_median_pepm)} median
          </p>
        </div>
      </div>

      {gapAnnual > 0 && (
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 10, padding: "16px 20px", marginBottom: 20, textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "#991b1b", margin: 0 }}>
            Estimated annual excess: <strong>{fmt(gapAnnual)}</strong> per employee above median.
          </p>
        </div>
      )}

      {/* Share Actions */}
      <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 12, padding: 20 }}>
        <p style={{ fontSize: 14, fontWeight: 600, color: "#0D7377", margin: "0 0 12px" }}>Share with your client</p>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
          <input
            readOnly
            value={result.share_url}
            style={{ flex: 1, minWidth: 200, padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, color: "#475569", background: "#fff" }}
            onFocus={(e) => e.target.select()}
          />
          <button onClick={() => onCopyLink(result.share_token)} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
            {shareCopied ? "Copied!" : "Copy Link"}
          </button>
        </div>
        {hasEmail && (
          <button onClick={() => onNotify(result.employer_email)} disabled={shareLoading || notifySent} style={{ background: notifySent ? "#dcfce7" : "#fff", color: notifySent ? "#166534" : "#1B3A5C", border: "1px solid " + (notifySent ? "#bbf7d0" : "#e2e8f0"), borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: notifySent ? "default" : "pointer" }}>
            {notifySent ? "Email sent to client" : shareLoading ? "Sending..." : `Email report to ${result.employer_email}`}
          </button>
        )}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// FormField helper
// ---------------------------------------------------------------------------

function FormField({ label, hint, required, children }) {
  return (
    <div>
      <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "#475569", marginBottom: 4 }}>
        {label}{required && <span style={{ color: "#EF4444" }}> *</span>}
      </label>
      {children}
      {hint && <p style={{ fontSize: 11, color: "#94a3b8", margin: "4px 0 0" }}>{hint}</p>}
    </div>
  );
}


const inputStyle = {
  width: "100%", padding: "8px 12px", borderRadius: 8,
  border: "1px solid #e2e8f0", fontSize: 14, outline: "none", boxSizing: "border-box",
  background: "#fff", color: "#1e293b",
};

const thStyle = { textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: 600 };
const tdStyle = { padding: "10px 12px", color: "#475569" };
