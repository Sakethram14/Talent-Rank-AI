"""
Centralized configuration for TalentRank AI.

All paths, thresholds, model names, and tunable parameters are defined here.
No module should contain hardcoded paths or magic numbers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


def _project_root() -> Path:
    """Walk up from this file to find the project root (contains src/)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "src").is_dir() and (current / "configs").is_dir():
            return current
        current = current.parent
    # Fallback: two levels up from config/settings.py
    return Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class PathConfig:
    """All filesystem paths used by the project."""

    project_root: Path = field(default_factory=_project_root)

    @property
    def data_raw(self) -> Path:
        return self.project_root / "data" / "raw"

    @property
    def data_processed(self) -> Path:
        return self.project_root / "data" / "processed"

    @property
    def artifacts_root(self) -> Path:
        return self.project_root / "artifacts"

    @property
    def artifacts_embeddings(self) -> Path:
        return self.project_root / "artifacts" / "embeddings"

    @property
    def artifacts_features(self) -> Path:
        return self.project_root / "artifacts" / "features"

    @property
    def artifacts_indices(self) -> Path:
        return self.project_root / "artifacts" / "indices"

    @property
    def configs_dir(self) -> Path:
        return self.project_root / "configs"

    @property
    def candidates_jsonl(self) -> Path:
        return self.data_raw / "candidates.jsonl"

    @property
    def sample_candidates_json(self) -> Path:
        return self.data_raw / "sample_candidates.json"

    @property
    def feature_store_path(self) -> Path:
        return self.artifacts_features / "feature_store.parquet"

    @property
    def embeddings_matrix_path(self) -> Path:
        return self.artifacts_embeddings / "candidate_embeddings.npy"

    @property
    def jd_embedding_path(self) -> Path:
        return self.artifacts_embeddings / "jd_embedding.npy"

    @property
    def faiss_index_path(self) -> Path:
        return self.artifacts_indices / "candidate.faiss"

    @property
    def bm25_index_path(self) -> Path:
        return self.artifacts_indices / "bm25_index.pkl"

    def ensure_dirs(self) -> None:
        """Create all necessary directories."""
        for d in [
            self.data_raw,
            self.data_processed,
            self.artifacts_embeddings,
            self.artifacts_features,
            self.artifacts_indices,
        ]:
            d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class DataConfig:
    """Data processing parameters."""

    total_candidates: int = 100_000
    candidate_id_pattern: str = r"^CAND_\d{7}$"
    max_career_entries: int = 10
    max_education_entries: int = 5
    max_skills: int = 100  # Generous upper bound
    batch_size: int = 5_000  # For streaming JSONL processing
    valid_company_sizes: tuple = (
        "1-10", "11-50", "51-200", "201-500",
        "501-1000", "1001-5000", "5001-10000", "10001+",
    )
    valid_proficiency_levels: tuple = (
        "beginner", "intermediate", "advanced", "expert",
    )
    valid_work_modes: tuple = ("remote", "hybrid", "onsite", "flexible")
    valid_language_levels: tuple = (
        "basic", "conversational", "professional", "native",
    )
    valid_education_tiers: tuple = (
        "tier_1", "tier_2", "tier_3", "tier_4", "unknown",
    )


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding generation parameters."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    max_seq_length: int = 256
    batch_size: int = 256
    normalize: bool = True
    use_int8_quantization: bool = False  # Enable for production memory savings
    device: str = "cpu"  # Hackathon constraint: CPU only


@dataclass(frozen=True)
class RetrievalConfig:
    """Retrieval pipeline parameters."""

    # Dense retrieval
    dense_top_k: int = 500
    # Lexical retrieval (BM25)
    bm25_top_k: int = 500
    # Hybrid fusion
    hybrid_top_k: int = 300  # Candidates passed to final ranking
    dense_weight: float = 0.6
    bm25_weight: float = 0.4


@dataclass(frozen=True)
class HoneypotConfig:
    """Honeypot detection thresholds."""

    # Maximum ratio of claimed experience to plausible experience
    max_experience_inflation_ratio: float = 1.5
    # Expert skills with 0 duration
    max_expert_zero_duration_skills: int = 2
    # Minimum skill duration for expert claim (months)
    min_expert_duration_months: int = 6
    # Maximum percentage of honeypots allowed in top 100
    max_honeypot_rate: float = 0.10


@dataclass(frozen=True)
class BehaviorConfig:
    """Behavioral signal thresholds."""

    # Minimum acceptable recruiter response rate
    min_response_rate: float = 0.05
    # Maximum days since last active to be considered "available"
    max_inactive_days: int = 180
    # Minimum profile completeness (0-100)
    min_profile_completeness: float = 30.0
    # GitHub activity: -1 means no GitHub linked
    github_not_linked_value: float = -1.0
    # Offer acceptance: -1 means no prior offers
    no_offer_history_value: float = -1.0


@dataclass(frozen=True)
class RankingConfig:
    """Ranking engine parameters."""

    top_k_output: int = 100
    # Score component weights
    semantic_weight: float = 0.35
    structured_weight: float = 0.35
    behavioral_weight: float = 0.20
    recency_weight: float = 0.10
    # Experience preferences (from JD: 5-9 years)
    ideal_experience_min: float = 5.0
    ideal_experience_max: float = 9.0
    experience_tolerance: float = 3.0  # Years outside ideal range before heavy penalty


@dataclass(frozen=True)
class ComputeConstraints:
    """Hackathon compute limits — hard constraints."""

    max_runtime_seconds: int = 300  # 5 minutes
    max_memory_gb: int = 16
    gpu_allowed: bool = False
    network_allowed: bool = False
    max_disk_gb: int = 5


@dataclass
class Settings:
    """Master settings object aggregating all configuration."""

    paths: PathConfig = field(default_factory=PathConfig)
    data: DataConfig = field(default_factory=DataConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    honeypot: HoneypotConfig = field(default_factory=HoneypotConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    compute: ComputeConstraints = field(default_factory=ComputeConstraints)

    def __post_init__(self) -> None:
        self.paths.ensure_dirs()


# Singleton pattern
_settings: Optional[Settings] = None


def get_settings(project_root: Optional[Path] = None) -> Settings:
    """Get or create the singleton Settings instance."""
    global _settings
    if _settings is None:
        if project_root:
            paths = PathConfig(project_root=project_root)
        else:
            paths = PathConfig()
        _settings = Settings(paths=paths)
    return _settings


def reset_settings() -> None:
    """Reset the singleton (for testing)."""
    global _settings
    _settings = None
