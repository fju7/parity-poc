"""
Parity Signal: Per-topic configuration.

Centralizes issue metadata, categories, prompt context, snapshot path, and
manifest path for every Signal topic. All pipeline scripts import this module
instead of hardcoding GLP-1-specific values.

Topic configs resolve in three layers, most specific first:

  1. the hardcoded TOPICS dict below (hand-written prompt_detail),
  2. ``backend/data/signal/dynamic_topics.json`` (legacy local file),
  3. the ``signal_issues`` table.

Layer 3 is what makes the pipeline runnable from any machine. Before it
existed, a topic registered at runtime lived ONLY in the gitignored JSON file
on whichever laptop registered it, so every other machine raised "Unknown topic
slug" for topics that were live on the site. That is the same failure mode
migration 072 fixed for pipeline snapshots.

Usage:
    from topic_config import get_topic, get_manifest_path, get_snapshot_path

    topic = get_topic("glp1-drugs")
    categories = topic["categories"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DYNAMIC_TOPICS_PATH = BACKEND_ROOT / "data" / "signal" / "dynamic_topics.json"

# ---------------------------------------------------------------------------
# Topic definitions
# ---------------------------------------------------------------------------

TOPICS: dict[str, dict] = {
    "glp1-drugs": {
        "slug": "glp1-drugs",
        "title": "GLP-1 Receptor Agonist Drugs",
        "description": (
            "Evidence assessment of GLP-1 receptor agonist medications "
            "(semaglutide/Ozempic/Wegovy, tirzepatide/Mounjaro/Zepbound) "
            "for obesity, diabetes, and cardiovascular outcomes."
        ),
        "categories": [
            "efficacy",
            "safety",
            "cardiovascular",
            "pricing",
            "regulatory",
            "emerging",
        ],
        "prompt_subject": "GLP-1 receptor agonist drugs",
        "prompt_detail": (
            "GLP-1 receptor agonist medications including semaglutide "
            "(Ozempic, Wegovy, Rybelsus), tirzepatide (Mounjaro, Zepbound), "
            "and related drugs used for type 2 diabetes, obesity, and "
            "cardiovascular risk reduction. Topics include clinical efficacy, "
            "safety profiles, cardiovascular outcomes, pricing and access, "
            "regulatory status, and emerging formulations."
        ),
        "manifest_filename": "glp1_sources.json",
    },
    "breast-cancer-therapies": {
        "slug": "breast-cancer-therapies",
        "title": "Breast Cancer Therapies",
        "description": (
            "Evidence assessment of current and emerging breast cancer "
            "therapies including CDK4/6 inhibitors, antibody-drug conjugates, "
            "immunotherapy, and targeted agents across subtypes."
        ),
        "categories": [
            "treatment_efficacy",
            "survival_outcomes",
            "side_effects",
            "treatment_selection",
            "emerging_therapies",
            "guidelines",
        ],
        "prompt_subject": "breast cancer therapies",
        "prompt_detail": (
            "Breast cancer treatment approaches including CDK4/6 inhibitors "
            "(palbociclib, ribociclib, abemaciclib), antibody-drug conjugates "
            "(trastuzumab deruxtecan/Enhertu, sacituzumab govitecan/Trodelvy), "
            "immunotherapy (pembrolizumab/Keytruda), PI3K/AKT pathway "
            "inhibitors (capivasertib, alpelisib), endocrine therapy, and "
            "emerging targeted agents. Covers HR+/HER2-, HER2+, and "
            "triple-negative breast cancer subtypes."
        ),
        "manifest_filename": "breast-cancer-therapies_sources.json",
    },
    "social-media-teen-mental-health": {
        "slug": "social-media-teen-mental-health",
        "title": "Social Media & Teen Mental Health",
        "description": (
            "Evidence assessment of the relationship between social media use "
            "and adolescent mental health, including depression, anxiety, "
            "mechanisms of harm, platform design, interventions, and policy."
        ),
        "categories": [
            "depression_anxiety",
            "mechanisms",
            "platform_design",
            "interventions",
            "policy_regulation",
            "methodology",
        ],
        "prompt_subject": "social media and teen mental health",
        "prompt_detail": (
            "The relationship between social media use and adolescent mental "
            "health outcomes. Topics include associations with depression and "
            "anxiety, causal mechanisms (social comparison, cyberbullying, "
            "sleep disruption, displacement), platform design features that "
            "affect well-being, digital literacy and screen time "
            "interventions, policy and regulatory responses (KOSA, EU DSA, "
            "UK Online Safety Act, state legislation), and methodological "
            "quality of the research base."
        ),
        "manifest_filename": "social-media-teen-mental-health_sources.json",
    },
}


# ---------------------------------------------------------------------------
# Load dynamically registered topics from disk
# ---------------------------------------------------------------------------

def _load_dynamic_topics():
    """Load topics registered at runtime from the dynamic topics JSON file."""
    if DYNAMIC_TOPICS_PATH.exists():
        try:
            with open(DYNAMIC_TOPICS_PATH) as f:
                dynamic = json.load(f)
            for slug, topic in dynamic.items():
                if slug not in TOPICS:
                    TOPICS[slug] = topic
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[topic_config] Warning: failed to load dynamic topics: {exc}")


_load_dynamic_topics()


# ---------------------------------------------------------------------------
# Database-backed topic lookup
# ---------------------------------------------------------------------------
#
# signal_issues already holds slug/title/description for every topic, and
# signal_consensus holds one row per category. That is everything
# register_topic() derives a config from — it sets prompt_subject from the
# title, prompt_detail from the description, and manifest_filename from the
# slug — so a config rebuilt from the database is IDENTICAL to the one
# register_topic wrote to disk. Reading it back from Postgres loses nothing.
#
# Every function here degrades to None rather than raising. topic_config is
# imported by scripts and tests that may have no Supabase credentials, and an
# import-time credential requirement would break them all.

_DB_TOPIC_CACHE: dict[str, dict] = {}
_DB_MISSING: set[str] = set()


def _build_topic(
    slug: str,
    title: str,
    description: str,
    categories: list[str],
    manifest_filename: str | None = None,
) -> dict:
    """The single definition of a topic config dict.

    Both register_topic() and the database loader build configs through here so
    the two paths cannot drift apart.
    """
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "categories": categories,
        "prompt_subject": title.lower(),
        "prompt_detail": description,
        "manifest_filename": manifest_filename or f"{slug}_sources.json",
    }


def _get_supabase():
    """Return the Supabase client, or None if it is unavailable."""
    try:
        if str(BACKEND_ROOT) not in sys.path:
            sys.path.insert(0, str(BACKEND_ROOT))
        from supabase_client import supabase
        return supabase
    except Exception:
        return None


def _categories_from_db(sb, issue_id: str) -> list[str]:
    """Category list for an issue.

    Prefers signal_consensus, which holds exactly one row per category. Falls
    back to distinct signal_claims.category for a topic that has been scored
    but not yet consensus-mapped.

    The claims fallback pages explicitly. PostgREST caps a response at 1000
    rows, and an unpaged select on a large topic would silently drop
    categories — the same class of bug as P0.1 and the A1 citation map.
    """
    try:
        res = (
            sb.table("signal_consensus")
            .select("category")
            .eq("issue_id", issue_id)
            .execute()
        )
        cats = sorted({r["category"] for r in (res.data or []) if r.get("category")})
        if cats:
            return cats
    except Exception:
        pass

    cats: set[str] = set()
    step = 1000
    offset = 0
    while True:
        try:
            res = (
                sb.table("signal_claims")
                .select("category")
                .eq("issue_id", issue_id)
                .range(offset, offset + step - 1)
                .execute()
            )
        except Exception:
            break
        rows = res.data or []
        cats.update(r["category"] for r in rows if r.get("category"))
        if len(rows) < step:
            break
        offset += step
    return sorted(cats)


def _topic_from_db(slug: str) -> dict | None:
    """Rebuild a topic config from signal_issues, or None if not found."""
    if slug in _DB_TOPIC_CACHE:
        return _DB_TOPIC_CACHE[slug]
    if slug in _DB_MISSING:
        return None

    sb = _get_supabase()
    if sb is None:
        return None

    try:
        res = (
            sb.table("signal_issues")
            .select("id, slug, title, description")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        print(f"[topic_config] Warning: database lookup for '{slug}' failed: {exc}")
        return None

    if not rows:
        _DB_MISSING.add(slug)
        return None

    row = rows[0]
    topic = _build_topic(
        row["slug"],
        row.get("title") or slug,
        row.get("description") or "",
        _categories_from_db(sb, row["id"]),
    )
    _DB_TOPIC_CACHE[slug] = topic
    return topic


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_topic(slug: str) -> dict:
    """Return the topic config dict for the given slug, or raise KeyError.

    Resolves through the three layers described in the module docstring:
    hardcoded TOPICS, the dynamic JSON file (already merged into TOPICS at
    import), then signal_issues. KeyError means the slug is in none of them.
    """
    if slug in TOPICS:
        return TOPICS[slug]

    topic = _topic_from_db(slug)
    if topic is not None:
        return topic

    valid = ", ".join(list_slugs())
    raise KeyError(f"Unknown topic slug '{slug}'. Valid slugs: {valid}")


def get_manifest_path(slug: str) -> Path:
    """Return the absolute path to a topic's source manifest JSON file."""
    topic = get_topic(slug)
    return PROJECT_ROOT / "data" / "signal" / "sources" / topic["manifest_filename"]


def get_snapshot_path(slug: str) -> Path:
    """Return the absolute path to a topic's pipeline snapshot JSON file."""
    get_topic(slug)  # validate slug
    return BACKEND_ROOT / "data" / "signal" / f"pipeline_snapshot_{slug}.json"


def register_topic(
    slug: str,
    title: str,
    description: str,
    categories: list[str],
    manifest_filename: str | None = None,
) -> dict:
    """Register a new topic at runtime.

    The durable record of a topic is its signal_issues row, which
    collect_sources.ensure_issue() creates. This function still writes
    ``dynamic_topics.json`` because registration happens BEFORE that row
    exists, and subprocesses started in that window reimport this module and
    would otherwise not see the topic.

    Once the issue row exists, get_topic() can rebuild this config from the
    database on any machine, so the file is a short-lived convenience rather
    than the source of truth. A failed write is therefore logged, not raised.
    """
    topic = _build_topic(slug, title, description, categories, manifest_filename)
    TOPICS[slug] = topic

    dynamic: dict = {}
    if DYNAMIC_TOPICS_PATH.exists():
        try:
            with open(DYNAMIC_TOPICS_PATH) as f:
                dynamic = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    dynamic[slug] = topic
    try:
        DYNAMIC_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DYNAMIC_TOPICS_PATH, "w") as f:
            json.dump(dynamic, f, indent=2)
    except OSError as exc:
        print(f"[topic_config] Warning: could not persist dynamic topic '{slug}': {exc}")

    return topic


def list_slugs(include_database: bool = True) -> list[str]:
    """Return all valid topic slugs.

    Merges the hardcoded and dynamic-file topics with every slug in
    signal_issues. Pass include_database=False for an offline-only list.
    """
    slugs = set(TOPICS)
    slugs.update(_DB_TOPIC_CACHE)

    if include_database:
        sb = _get_supabase()
        if sb is not None:
            try:
                res = sb.table("signal_issues").select("slug").execute()
                slugs.update(r["slug"] for r in (res.data or []) if r.get("slug"))
            except Exception as exc:
                print(f"[topic_config] Warning: could not list topics from database: {exc}")

    return sorted(slugs)
