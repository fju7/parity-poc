"""Shared helpers, constants, and Pydantic models for employer sub-routers."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from supabase import create_client

# ---------------------------------------------------------------------------
# Benchmark data (loaded once at import time via load_employer_benchmarks())
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_benchmark_data: dict | None = None


def load_employer_benchmarks():
    """Load benchmark_compiled.json into memory. Called once at app startup."""
    global _benchmark_data
    path = DATA_DIR / "employer_benchmarks" / "benchmark_compiled.json"
    if not path.exists():
        print(f"WARNING: Employer benchmark file not found at {path}")
        _benchmark_data = {}
        return
    with open(path, "r") as f:
        _benchmark_data = json.load(f)
    print(f"Loaded employer benchmark data ({len(_benchmark_data.get('by_industry', {}))} industries)")


def get_benchmarks() -> dict:
    """Return the loaded benchmark data dict."""
    if _benchmark_data is None:
        load_employer_benchmarks()
    return _benchmark_data


# ---------------------------------------------------------------------------
# Supabase client (lazy singleton — separate from provider's)
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_claude():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="AI analysis is not configured on this server.",
            )
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="AI dependencies are not installed.",
            )
    return _anthropic_client


def _call_claude(system_prompt: str, user_content, max_tokens: int = 4096) -> dict | None:
    """Call Claude API with retry on 529, return parsed JSON."""
    client = _get_claude()
    backoff_delays = [2, 5, 10]
    response = None

    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[Employer AI] Claude overloaded (529), retry {attempt + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[Employer AI] API error: {exc}")
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[Employer AI] Invalid JSON: {raw_text[:500]}")
        return None


# ---------------------------------------------------------------------------
# Stripe config
# ---------------------------------------------------------------------------

STRIPE_PRICE_EMPLOYER_MONTHLY = os.environ.get("STRIPE_PRICE_EMPLOYER_MONTHLY", "")
STRIPE_PRICE_EMPLOYER_ANNUAL = os.environ.get("STRIPE_PRICE_EMPLOYER_ANNUAL", "")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BenchmarkRequest(BaseModel):
    industry: str
    company_size: str  # "10-49", "50-199", "200-999", "1000+"
    state: str
    pepm_input: float  # employer PEPM in dollars
    email: Optional[str] = None


class ClaimsCheckRequest(BaseModel):
    email: Optional[str] = None
    zip_code: str
    column_mapping: Optional[dict] = None  # AI-assisted or user-provided


class ScorecardRequest(BaseModel):
    email: Optional[str] = None
    plan_name: Optional[str] = None
    network_type: Optional[str] = None  # PPO, HMO, HDHP, etc.


class EmployerCheckoutRequest(BaseModel):
    email: str
    company_name: Optional[str] = None
    employee_count: Optional[int] = None
    tier: str = "standard"  # standard, premium
    billing_period: str = "monthly"  # monthly, annual
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SubscriptionStatusRequest(BaseModel):
    email: str
