"""
Parity Signal: Per-topic configuration.

Centralizes issue metadata, categories, prompt context, snapshot path, and
manifest path for every Signal topic. All pipeline scripts import this module
instead of hardcoding GLP-1-specific values.

Usage:
    from topic_config import get_topic, get_manifest_path, get_snapshot_path

    topic = get_topic("glp1-drugs")
    categories = topic["categories"]
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

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
# Helper functions
# ---------------------------------------------------------------------------

def get_topic(slug: str) -> dict:
    """Return the topic config dict for the given slug, or raise KeyError."""
    if slug not in TOPICS:
        valid = ", ".join(sorted(TOPICS.keys()))
        raise KeyError(f"Unknown topic slug '{slug}'. Valid slugs: {valid}")
    return TOPICS[slug]


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

    Used by the automated pipeline to add dynamically created topics
    without hardcoding them in TOPICS.
    """
    TOPICS[slug] = {
        "slug": slug,
        "title": title,
        "description": description,
        "categories": categories,
        "prompt_subject": title.lower(),
        "prompt_detail": description,
        "manifest_filename": manifest_filename or f"{slug}_sources.json",
    }
    return TOPICS[slug]


def list_slugs() -> list[str]:
    """Return all valid topic slugs."""
    return sorted(TOPICS.keys())
