import { useState, useEffect, useCallback } from "react";
import { Routes, Route, useParams, useNavigate, useLocation } from "react-router-dom";
import { supabase } from "./lib/supabase";
import SignalHeader from "./components/signal/SignalHeader";
import SignalFooter from "./components/signal/SignalFooter";
import SignalLanding from "./components/signal/SignalLanding";
import IssueDashboard from "./components/signal/IssueDashboard";
import MethodologyView from "./components/signal/MethodologyView";
import SignalLogin from "./components/signal/SignalLogin";
import PricingView from "./components/signal/PricingView";
import AccountView from "./components/signal/AccountView";

function DashboardRoute({ session, userTier }) {
  const { slug } = useParams();
  return <LazyDashboard slug={slug} session={session} userTier={userTier} />;
}

function LazyDashboard({ slug, session, userTier }) {
  const [state, setState] = useState({
    issue: null,
    summary: null,
    claims: null,
    consensus: null,
    sources: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    loadIssueData(slug).then(setState);
  }, [slug]);

  return (
    <IssueDashboard
      issue={state.issue}
      summary={state.summary}
      claims={state.claims}
      consensus={state.consensus}
      sources={state.sources}
      loading={state.loading}
      error={state.error}
      session={session}
      userTier={userTier}
    />
  );
}

async function loadIssueData(slug) {
  try {
    // 1. Fetch issue by slug
    const { data: issue, error: issueErr } = await supabase
      .from("signal_issues")
      .select("*")
      .eq("slug", slug)
      .single();

    if (issueErr || !issue) {
      return {
        issue: null,
        summary: null,
        claims: null,
        consensus: null,
        sources: null,
        loading: false,
        error: issueErr?.message || "Topic not found",
      };
    }

    const issueId = issue.id;

    // 2. Parallel fetch everything else
    const [summaryRes, claimsRes, consensusRes, sourcesRes, claimSourceCountsRes] =
      await Promise.all([
        supabase
          .from("signal_summaries")
          .select("*")
          .eq("issue_id", issueId)
          .order("version", { ascending: false })
          .limit(1)
          .single(),
        supabase
          .from("signal_claims")
          .select("*, signal_claim_composites(*)")
          .eq("issue_id", issueId),
        supabase
          .from("signal_consensus")
          .select("*")
          .eq("issue_id", issueId),
        supabase
          .from("signal_sources")
          .select("id, title, url, source_type, publication_date")
          .eq("issue_id", issueId),
        // Get source counts per claim
        supabase
          .from("signal_claim_sources")
          .select("claim_id"),
      ]);

    // Build source count map
    const sourceCountMap = new Map();
    if (claimSourceCountsRes.data) {
      for (const row of claimSourceCountsRes.data) {
        sourceCountMap.set(
          row.claim_id,
          (sourceCountMap.get(row.claim_id) || 0) + 1
        );
      }
    }

    // Attach source counts to claims
    const claims = (claimsRes.data || []).map((claim) => ({
      ...claim,
      _sourceCount: sourceCountMap.get(claim.id) || 0,
    }));

    return {
      issue,
      summary: summaryRes.data || null,
      claims,
      consensus: consensusRes.data || [],
      sources: sourcesRes.data || [],
      loading: false,
      error: null,
    };
  } catch (err) {
    return {
      issue: null,
      summary: null,
      claims: null,
      consensus: null,
      sources: null,
      loading: false,
      error: err.message || "Failed to load data",
    };
  }
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function SignalApp() {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [userTier, setUserTier] = useState("free");

  // Auth: session bootstrap + listener
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Reusable tier fetcher
  const fetchTier = useCallback(() => {
    if (!session?.access_token) {
      setUserTier("free");
      return;
    }
    fetch(`${API_BASE}/api/signal/stripe/tier`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
      .then((res) => (res.ok ? res.json() : { tier: "free" }))
      .then((data) => setUserTier(data.tier || "free"))
      .catch(() => setUserTier("free"));
  }, [session]);

  // Fetch user tier when session changes
  useEffect(() => {
    fetchTier();
  }, [fetchTier]);

  // Re-fetch tier after returning from Stripe Checkout
  const location = useLocation();
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("checkout_success") === "1") {
      // Small delay to let Stripe webhook process
      const timer = setTimeout(() => fetchTier(), 1500);
      // Clean up the query param from the URL
      params.delete("checkout_success");
      const cleanPath = params.toString()
        ? `${location.pathname}?${params.toString()}`
        : location.pathname;
      navigate(cleanPath, { replace: true });
      return () => clearTimeout(timer);
    }
  }, [location.search, fetchTier, navigate, location.pathname]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    setSession(null);
    navigate("/signal/login");
  }

  return (
    <div className="min-h-screen bg-white flex flex-col font-[Arial,sans-serif]">
      <SignalHeader session={session} onSignOut={handleSignOut} />
      <main className="flex-1">
        <Routes>
          <Route
            index
            element={
              <SignalLanding
                session={session}
                userTier={userTier}
              />
            }
          />
          <Route
            path="methodology"
            element={<MethodologyView />}
          />
          <Route
            path="login"
            element={<SignalLogin />}
          />
          <Route
            path="pricing"
            element={<PricingView session={session} userTier={userTier} />}
          />
          <Route
            path="account"
            element={<AccountView session={session} />}
          />
          <Route
            path=":slug"
            element={<DashboardRoute session={session} userTier={userTier} />}
          />
        </Routes>
      </main>
      <SignalFooter />
    </div>
  );
}
