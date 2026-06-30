"""
Text processing utilities for TalentRank AI.

Handles text cleaning, title normalization, and candidate text
construction for embedding generation.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from src.utils.logging import get_logger

logger = get_logger("utils.text")

# ──────────────────────────────────────────────────────────────────────
# Title normalization mappings
# ──────────────────────────────────────────────────────────────────────

# Map common title variations to canonical forms for consistent matching
TITLE_NORMALIZATIONS: dict[str, str] = {
    "swe": "Software Engineer",
    "sde": "Software Development Engineer",
    "sr.": "Senior",
    "jr.": "Junior",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "vp": "Vice President",
    "svp": "Senior Vice President",
    "avp": "Assistant Vice President",
    "cto": "Chief Technology Officer",
    "ceo": "Chief Executive Officer",
    "coo": "Chief Operating Officer",
    "devops": "DevOps",
}

# Titles that strongly indicate AI/ML engineering roles
AI_ML_TITLE_KEYWORDS: set[str] = {
    "machine learning", "ml engineer", "ai engineer", "data scientist",
    "nlp engineer", "deep learning", "research engineer", "applied scientist",
    "ml ops", "mlops", "computer vision", "cv engineer",
}

# Titles that are strong negative signals for this JD
NON_RELEVANT_TITLES: set[str] = {
    "marketing manager", "sales executive", "hr manager", "accountant",
    "graphic designer", "content writer", "customer support",
    "operations manager", "civil engineer", "mechanical engineer",
}

# ──────────────────────────────────────────────────────────────────────
# Text cleaning
# ──────────────────────────────────────────────────────────────────────


def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text for embedding or matching.

    - Strips whitespace
    - Normalizes unicode
    - Collapses multiple spaces
    - Lowercases
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_title(title: Optional[str]) -> str:
    """
    Normalize a job title for consistent comparison.

    Expands abbreviations and lowercases for matching.
    """
    if not title:
        return ""
    title = clean_text(title).lower()
    for abbrev, full in TITLE_NORMALIZATIONS.items():
        # Word-boundary replacement to avoid partial matches
        title = re.sub(rf"\b{re.escape(abbrev)}\b", full.lower(), title)
    return title


def is_ai_ml_title(title: str) -> bool:
    """Check if a title indicates an AI/ML engineering role."""
    normalized = normalize_title(title)
    return any(kw in normalized for kw in AI_ML_TITLE_KEYWORDS)


def is_non_relevant_title(title: str) -> bool:
    """Check if a title is clearly non-relevant for the Senior AI Engineer JD."""
    normalized = normalize_title(title)
    return any(kw in normalized for kw in NON_RELEVANT_TITLES)


# ──────────────────────────────────────────────────────────────────────
# Candidate text construction (for embedding generation)
# ──────────────────────────────────────────────────────────────────────


def build_candidate_text(candidate: dict[str, Any]) -> str:
    """
    Construct a unified text representation of a candidate for embedding.

    Combines headline, summary, career history descriptions, and skills
    into a single coherent passage that captures the candidate's
    professional identity.

    Args:
        candidate: Full candidate record from the JSONL dataset.

    Returns:
        A single text string suitable for embedding generation.
    """
    parts: list[str] = []

    profile = candidate.get("profile", {})

    # Headline and summary carry the strongest semantic signal
    headline = clean_text(profile.get("headline", ""))
    if headline:
        parts.append(headline)

    summary = clean_text(profile.get("summary", ""))
    if summary:
        parts.append(summary)

    # Current role context
    current_title = profile.get("current_title", "")
    current_company = profile.get("current_company", "")
    yoe = profile.get("years_of_experience", 0)
    if current_title:
        parts.append(
            f"Currently working as {current_title} at {current_company} "
            f"with {yoe} years of experience."
        )

    # Career history (recent roles weighted more by position in text)
    career = candidate.get("career_history", [])
    for i, role in enumerate(career[:5]):  # Cap at 5 most recent
        role_title = role.get("title", "")
        role_company = role.get("company", "")
        role_desc = clean_text(role.get("description", ""))
        duration = role.get("duration_months", 0)
        if role_desc:
            parts.append(
                f"{role_title} at {role_company} ({duration} months): {role_desc}"
            )

    # Skills with proficiency context
    skills = candidate.get("skills", [])
    if skills:
        skill_strs = []
        for s in skills:
            name = s.get("name", "")
            prof = s.get("proficiency", "")
            dur = s.get("duration_months", 0)
            if name:
                skill_strs.append(f"{name} ({prof}, {dur}mo)")
        if skill_strs:
            parts.append("Skills: " + ", ".join(skill_strs))

    # Education
    education = candidate.get("education", [])
    for edu in education:
        degree = edu.get("degree", "")
        field = edu.get("field_of_study", "")
        institution = edu.get("institution", "")
        if degree and field:
            parts.append(f"Education: {degree} in {field} from {institution}")

    return " ".join(parts)


def build_jd_query_text() -> str:
    """
    Construct the query text representing the job description.

    This is the text we embed and compare candidates against.
    Derived directly from the official job_description.docx.
    """
    return (
        "Senior AI Engineer with 5-9 years experience building production "
        "ML systems. Must have hands-on experience with embeddings-based "
        "retrieval systems such as sentence-transformers, OpenAI embeddings, "
        "BGE, or E5 deployed to real users. Production experience with "
        "vector databases or hybrid search infrastructure including "
        "Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, "
        "or FAISS. Strong Python coding skills. Experience designing "
        "evaluation frameworks for ranking systems using NDCG, MRR, MAP, "
        "and A/B testing. Preference for candidates who have shipped "
        "end-to-end ranking, search, or recommendation systems at product "
        "companies. Located in or willing to relocate to Pune or Noida, India. "
        "Experience with LLM fine-tuning, learning-to-rank models, HR-tech, "
        "and open-source contributions are valued. Scrappy product-engineering "
        "mindset over pure research orientation. Sub-30 day notice period preferred."
    )
