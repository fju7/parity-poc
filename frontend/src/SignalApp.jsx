import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate, useParams, useNavigate, useLocation } from "react-router-dom";
import { supabase } from "./lib/supabase";
import SignalHeader from "./components/signal/SignalHeader";
import SignalFooter from "./components/signal/SignalFooter";
import SignalLanding from "./components/signal/SignalLanding";
import IssueDashboard from "./components/signal/IssueDashboard";
import MethodologyView from "./components/signal/MethodologyView";
import SignalLogin from "./components/signal/SignalLogin";
import PricingView from "./components/signal/PricingView";
import AccountView from "./components/signal/AccountView";
import AdminRequestsDashboard from "./components/signal/AdminRequestsDashboard";
import AdminAnalytics from "./components/signal/AdminAnalytics";
import AdminReviewDashboard from "./components/signal/AdminReviewDashboard";

import { API_BASE } from "./lib/apiBase";
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function DashboardRoute({ session, userTier, tierData }) {
  const { slug } = useParams();
  return <LazyDashboard slug={slug} session={session} userTier={userTier} tierData={tierData} />;
}

function LazyDashboard({ slug, session, userTier, tierData }) {
  const [state, setState] = useState({
    issue: null,
    summary: null,
    claims: null,
    consensus: null,
    sources: null,
    dimensionScores: null,
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
      publication={state.publication}
      recheck={state.recheck}
      dimensionScores={state.dimensionScores}
      loading={state.loading}
      error={state.error}
      notPublished={state.notPublished}
      slug={slug}
      session={session}
      userTier={userTier}
      tierData={tierData}
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
      // No row. Under migration 078's RLS that means "not published" whether
      // the slug is a draft or was never a topic; the page says so, and it
      // is not an error.
      return {
        issue: null,
        summary: null,
        claims: null,
        consensus: null,
        sources: null,
        dimensionScores: null,
        loading: false,
        error: null,
        notPublished: true,
      };
    }

    const issueId = issue.id;

    // 2. Parallel fetch everything else
    const [summaryRes, claimsRes, consensusRes, sourcesRes] =
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
      ]);

    // The frozen publication record (Phase 3): status = 'published' opened
    // the door; the record says what stands inside it. No record, nothing
    // shown -- the page reads as not yet published.
    const { data: pubRows } = await supabase
      .from("topic_publications")
      .select("publish_id, published_at, gate_version, record, supported_claim_ids, surviving_source_ids")
      .eq("slug", slug)
      .order("published_at", { ascending: false })
      .limit(1);
    const pubRow = pubRows?.[0];
    if (!pubRow) {
      return { issue: null, summary: null, claims: null, consensus: null, sources: null,
               dimensionScores: null, loading: false, error: null, notPublished: true };
    }
    const supportedIds = new Set(pubRow.supported_claim_ids || []);
    const survivingIds = new Set(pubRow.surviving_source_ids || []);
    const publication = {
      publish_id: pubRow.publish_id,
      published_at: pubRow.published_at,
      gate_version: pubRow.gate_version,
      summary: pubRow.record?.summary,
      // WORKS, not rows. Each source row is one retrieval of a publication;
      // three rows of the 2004 IOM report are one work. Counts shown anywhere
      // are by work (operator's ruling, 2026-09-16: a pill that said
      // "3 sources" for one report asserted corroboration nothing had
      // examined). works_of_claim comes from the record; older records (no
      // `works`) fall back to counting supporting rows.
      works: pubRow.record?.works || null,
      work_count: Object.fromEntries((pubRow.record?.claims || []).filter((c) => c.work_count != null).map((c) => [c.claim_id, c.work_count])),
      // the operator's ratified scope statement, frozen with this record (publish.scope_statement)
      scope_statement: pubRow.record?.scope_statement?.text || null,
      supported_claim_ids: pubRow.supported_claim_ids || [],
      surviving_source_ids: pubRow.surviving_source_ids || [],
      support: Object.fromEntries((pubRow.record?.claims || []).map((c) => [c.claim_id, c.support])),
      status: Object.fromEntries((pubRow.record?.sources || []).filter((x) => x.status).map((x) => [x.source_id, x.status])),
      // per claim: the surviving links and the role each source plays (subject | support), as recorded
      links: Object.fromEntries((pubRow.record?.claims || []).map((c) => [
        c.claim_id,
        (c.per_source || []).filter((p) => p.level && p.level !== "UNSUPPORTED").map((p) => ({ source_id: p.source_id, role: p.role, rule: p.role_rule })),
      ])),
      sourceMeta: Object.fromEntries((pubRow.record?.sources || []).map((x) => [x.source_id, {
        first_author: x.resolution?.first_author, published: x.resolution?.published, container: x.resolution?.container,
      }])),
    };
    const { data: recheckRows } = await supabase
      .from("topic_rechecks")
      .select("run_id, run_at, kind, flags, exit_ok")
      .eq("slug", slug)
      .order("run_at", { ascending: false })
      .limit(2);
    // The latest run of each kind; flags from both are shown.
    const latestByKind = {};
    for (const r of recheckRows || []) if (!latestByKind[r.kind]) latestByKind[r.kind] = r;
    const recheck = Object.keys(latestByKind).length
      ? { run_at: (recheckRows || [])[0].run_at, flags: Object.values(latestByKind).flatMap((r) => r.flags || []) }
      : null;

    const rawClaims = (claimsRes.data || []).filter((c) => supportedIds.has(c.id));
    const rawClaimIds = rawClaims.map((c) => c.id);

    // Citation counts per claim.
    //
    // This used to select every row in signal_claim_sources with no filter at
    // all. PostgREST caps returned rows (Supabase default 1000), so once the
    // corpus grew past that the map was built from a truncated page and most
    // claims silently reported 0 citations. Scoping to this topic's claims
    // keeps the query well under the cap — same class of bug as the landing
    // page counts, fixed the same way.
    const sourceCountMap = new Map();
    if (rawClaimIds.length > 0) {
      const { data: claimSourceRows } = await supabase
        .from("signal_claim_sources")
        .select("claim_id")
        .in("claim_id", rawClaimIds);

      for (const row of claimSourceRows || []) {
        sourceCountMap.set(row.claim_id, (sourceCountMap.get(row.claim_id) || 0) + 1);
      }
    }

    // Attach source counts to claims: distinct WORKS among the claim's
    // supporting links when the record carries them; the raw link count only
    // for a record that predates the work/document split.
    const claims = rawClaims.map((claim) => ({
      ...claim,
      _sourceCount: publication.work_count[claim.id] != null ? publication.work_count[claim.id] : (sourceCountMap.get(claim.id) || 0),
    }));

    // 3. Fetch dimension scores for all claims (for Analytical Paths weight adjustment)
    const claimIds = claims.map((c) => c.id);
    let dimensionScores = new Map();
    if (claimIds.length > 0) {
      const { data: dimScoresData } = await supabase
        .from("signal_claim_scores")
        .select("claim_id, dimension, score")
        .in("claim_id", claimIds);

      if (dimScoresData) {
        for (const row of dimScoresData) {
          if (!dimensionScores.has(row.claim_id)) {
            dimensionScores.set(row.claim_id, {});
          }
          dimensionScores.get(row.claim_id)[row.dimension] = row.score;
        }
      }
    }

    return {
      issue,
      summary: summaryRes.data || null,
      claims,
      consensus: consensusRes.data || [],
      sources: (sourcesRes.data || []).filter((x) => survivingIds.has(x.id)),
      publication,
      recheck,
      dimensionScores,
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
      dimensionScores: null,
      loading: false,
      error: err.message || "Failed to load data",
    };
  }
}

export default function SignalApp() {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [userTier, setUserTier] = useState("free");
  const [tierData, setTierData] = useState(null);

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
      .then((data) => {
        setUserTier(data.tier || "free");
        setTierData(data);
      })
      .catch(() => {
        setUserTier("free");
        setTierData(null);
      });
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
    <div className="min-h-screen bg-[#0a1628] flex flex-col font-[Arial,sans-serif]">
      <ScrollToTop />
      <SignalHeader session={session} onSignOut={handleSignOut} />
      <main className="flex-1">
        <Routes>
          <Route
            index
            element={
              <SignalLanding
                session={session}
                userTier={userTier}
                tierData={tierData}
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
            path="signup"
            element={<SignalLogin signup />}
          />
          <Route
            path="pricing"
            element={<PricingView session={session} userTier={userTier} />}
          />
          <Route
            path="account"
            element={<AccountView session={session} />}
          />
          <Route path="admin" element={<Navigate to="/admin/requests" replace />} />
          <Route
            path="admin/requests"
            element={<AdminRequestsDashboard session={session} />}
          />
          <Route
            path="admin/analytics"
            element={<AdminAnalytics session={session} />}
          />
          <Route
            path="admin/review"
            element={<AdminReviewDashboard session={session} />}
          />
          <Route
            path=":slug"
            element={<DashboardRoute session={session} userTier={userTier} tierData={tierData} />}
          />
        </Routes>
      </main>
      <SignalFooter />
    </div>
  );
}
