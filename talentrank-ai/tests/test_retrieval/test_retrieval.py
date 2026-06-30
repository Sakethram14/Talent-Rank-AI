"""
Tests for the retrieval layer: DenseRetriever, LexicalRetriever, HybridRetriever.

Uses small synthetic datasets (5-10 candidates) with known properties so
that retrieval behaviour can be asserted deterministically.
"""

from __future__ import annotations

import pickle
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.config.settings import reset_settings
from src.retrieval.dense import DenseRetriever
from src.retrieval.hybrid import HybridRetriever, _reciprocal_rank_fusion, _min_max_normalise
from src.retrieval.lexical import LexicalRetriever, _tokenize


# ── fixtures ─────────────────────────────────────────────────────────


CANDIDATE_IDS = [
    "CAND_0000001",
    "CAND_0000002",
    "CAND_0000003",
    "CAND_0000004",
    "CAND_0000005",
    "CAND_0000006",
    "CAND_0000007",
    "CAND_0000008",
]


def _make_synthetic_candidates() -> list[dict]:
    """
    8 candidates with distinct professional profiles.

    Candidates 1-3 are strong AI/ML matches.
    Candidates 4-5 are partial matches (software eng but not ML).
    Candidates 6-8 are non-relevant (marketing, HR, civil eng).
    """
    return [
        {
            "candidate_id": "CAND_0000001",
            "profile": {
                "headline": "Senior Machine Learning Engineer",
                "summary": "Building production ML systems with FAISS and sentence-transformers. Expert in Python and vector databases.",
                "current_title": "ML Engineer",
                "current_company": "AI Corp",
                "years_of_experience": 7,
            },
            "skills": [
                {"name": "Python", "proficiency": "expert", "duration_months": 84},
                {"name": "Machine Learning", "proficiency": "expert", "duration_months": 72},
                {"name": "FAISS", "proficiency": "advanced", "duration_months": 36},
                {"name": "sentence-transformers", "proficiency": "advanced", "duration_months": 30},
            ],
            "career_history": [
                {"title": "ML Engineer", "company": "AI Corp", "duration_months": 48, "description": "Designed embeddings-based retrieval systems using sentence-transformers and FAISS for production search."},
            ],
            "education": [{"degree": "M.Tech", "field_of_study": "Computer Science", "institution": "IIT Delhi"}],
        },
        {
            "candidate_id": "CAND_0000002",
            "profile": {
                "headline": "AI Research Engineer — NLP and Deep Learning",
                "summary": "Experienced in LLM fine-tuning, ranking systems, and evaluation frameworks. Published researcher.",
                "current_title": "AI Engineer",
                "current_company": "TechStartup",
                "years_of_experience": 6,
            },
            "skills": [
                {"name": "Python", "proficiency": "expert", "duration_months": 72},
                {"name": "Deep Learning", "proficiency": "expert", "duration_months": 60},
                {"name": "NLP", "proficiency": "advanced", "duration_months": 48},
                {"name": "LLM", "proficiency": "advanced", "duration_months": 24},
            ],
            "career_history": [
                {"title": "AI Engineer", "company": "TechStartup", "duration_months": 36, "description": "Built ranking and recommendation systems with evaluation using NDCG and MRR metrics."},
            ],
            "education": [{"degree": "M.Sc", "field_of_study": "Artificial Intelligence", "institution": "IIIT Hyderabad"}],
        },
        {
            "candidate_id": "CAND_0000003",
            "profile": {
                "headline": "Data Scientist — Computer Vision and ML Ops",
                "summary": "End-to-end ML pipeline development. Experience with Pinecone and Elasticsearch for search systems.",
                "current_title": "Senior Data Scientist",
                "current_company": "BigTech",
                "years_of_experience": 8,
            },
            "skills": [
                {"name": "Python", "proficiency": "expert", "duration_months": 96},
                {"name": "Computer Vision", "proficiency": "expert", "duration_months": 60},
                {"name": "MLOps", "proficiency": "advanced", "duration_months": 36},
                {"name": "Elasticsearch", "proficiency": "advanced", "duration_months": 30},
            ],
            "career_history": [
                {"title": "Data Scientist", "company": "BigTech", "duration_months": 60, "description": "Deployed vector search infrastructure using Pinecone and Elasticsearch with hybrid retrieval."},
            ],
            "education": [{"degree": "B.Tech", "field_of_study": "Computer Engineering", "institution": "NIT Trichy"}],
        },
        {
            "candidate_id": "CAND_0000004",
            "profile": {
                "headline": "Full Stack Software Engineer",
                "summary": "Building web applications with React and Node.js. Some experience with Python scripting.",
                "current_title": "Software Engineer",
                "current_company": "WebDev Inc",
                "years_of_experience": 5,
            },
            "skills": [
                {"name": "JavaScript", "proficiency": "expert", "duration_months": 60},
                {"name": "React", "proficiency": "advanced", "duration_months": 48},
                {"name": "Python", "proficiency": "intermediate", "duration_months": 24},
            ],
            "career_history": [
                {"title": "Software Engineer", "company": "WebDev Inc", "duration_months": 36, "description": "Frontend and backend development of customer-facing web applications."},
            ],
            "education": [{"degree": "B.Tech", "field_of_study": "Information Technology", "institution": "VIT Vellore"}],
        },
        {
            "candidate_id": "CAND_0000005",
            "profile": {
                "headline": "Backend Developer — Java and Microservices",
                "summary": "Specialising in distributed systems and cloud infrastructure. AWS certified.",
                "current_title": "Senior Backend Developer",
                "current_company": "CloudServ",
                "years_of_experience": 9,
            },
            "skills": [
                {"name": "Java", "proficiency": "expert", "duration_months": 108},
                {"name": "Microservices", "proficiency": "expert", "duration_months": 72},
                {"name": "AWS", "proficiency": "advanced", "duration_months": 48},
            ],
            "career_history": [
                {"title": "Backend Developer", "company": "CloudServ", "duration_months": 48, "description": "Designed and maintained microservices architecture serving millions of requests."},
            ],
            "education": [{"degree": "B.E", "field_of_study": "Computer Science", "institution": "BITS Pilani"}],
        },
        {
            "candidate_id": "CAND_0000006",
            "profile": {
                "headline": "Marketing Manager",
                "summary": "Digital marketing strategy and brand management. SEO and SEM expert.",
                "current_title": "Marketing Manager",
                "current_company": "BrandCo",
                "years_of_experience": 10,
            },
            "skills": [
                {"name": "SEO", "proficiency": "expert", "duration_months": 120},
                {"name": "Google Ads", "proficiency": "advanced", "duration_months": 72},
            ],
            "career_history": [
                {"title": "Marketing Manager", "company": "BrandCo", "duration_months": 60, "description": "Led digital marketing campaigns and managed brand strategy."},
            ],
            "education": [{"degree": "MBA", "field_of_study": "Marketing", "institution": "XLRI"}],
        },
        {
            "candidate_id": "CAND_0000007",
            "profile": {
                "headline": "HR Business Partner",
                "summary": "Talent acquisition and employee engagement specialist.",
                "current_title": "HR Manager",
                "current_company": "PeopleCo",
                "years_of_experience": 12,
            },
            "skills": [
                {"name": "Talent Acquisition", "proficiency": "expert", "duration_months": 144},
                {"name": "Employee Relations", "proficiency": "advanced", "duration_months": 96},
            ],
            "career_history": [
                {"title": "HR Manager", "company": "PeopleCo", "duration_months": 72, "description": "Managed hiring pipeline and employee retention programs."},
            ],
            "education": [{"degree": "MBA", "field_of_study": "Human Resources", "institution": "TISS Mumbai"}],
        },
        {
            "candidate_id": "CAND_0000008",
            "profile": {
                "headline": "Civil Engineer — Structural Design",
                "summary": "Specialising in structural analysis and construction project management.",
                "current_title": "Civil Engineer",
                "current_company": "BuildIt",
                "years_of_experience": 6,
            },
            "skills": [
                {"name": "AutoCAD", "proficiency": "expert", "duration_months": 72},
                {"name": "Structural Analysis", "proficiency": "advanced", "duration_months": 60},
            ],
            "career_history": [
                {"title": "Civil Engineer", "company": "BuildIt", "duration_months": 36, "description": "Structural design and analysis for commercial building projects."},
            ],
            "education": [{"degree": "B.Tech", "field_of_study": "Civil Engineering", "institution": "IIT Roorkee"}],
        },
    ]


def _make_synthetic_embeddings(n: int = 8, dim: int = 384, seed: int = 42) -> np.ndarray:
    """
    Create synthetic embedding matrix with controlled similarity structure.

    Candidates 0-2 are close to each other (AI/ML cluster),
    Candidates 3-4 are in a mid-range cluster (software eng),
    Candidates 5-7 are far from the AI/ML cluster.

    The JD query vector will be aligned with the AI/ML cluster.
    """
    rng = np.random.RandomState(seed)

    # Base direction for AI/ML (our JD direction)
    ai_ml_direction = rng.randn(dim).astype(np.float32)
    ai_ml_direction /= np.linalg.norm(ai_ml_direction)

    # Software eng direction (partially overlapping with AI/ML)
    sw_direction = 0.3 * ai_ml_direction + 0.7 * rng.randn(dim).astype(np.float32)
    sw_direction /= np.linalg.norm(sw_direction)

    # Non-tech direction (orthogonal-ish to AI/ML)
    non_tech_direction = rng.randn(dim).astype(np.float32)
    non_tech_direction -= non_tech_direction.dot(ai_ml_direction) * ai_ml_direction
    non_tech_direction /= np.linalg.norm(non_tech_direction)

    embeddings = np.zeros((n, dim), dtype=np.float32)

    # AI/ML candidates (close to ai_ml_direction + small noise)
    for i in range(3):
        noise = rng.randn(dim).astype(np.float32) * 0.1
        vec = ai_ml_direction + noise
        embeddings[i] = vec / np.linalg.norm(vec)

    # Software eng (between AI/ML and non-tech)
    for i in range(3, 5):
        noise = rng.randn(dim).astype(np.float32) * 0.15
        vec = sw_direction + noise
        embeddings[i] = vec / np.linalg.norm(vec)

    # Non-tech (far from AI/ML)
    for i in range(5, n):
        noise = rng.randn(dim).astype(np.float32) * 0.1
        vec = non_tech_direction + noise
        embeddings[i] = vec / np.linalg.norm(vec)

    return embeddings, ai_ml_direction.reshape(1, -1)


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset the settings singleton between tests."""
    reset_settings()
    yield
    reset_settings()


# ═════════════════════════════════════════════════════════════════════
#  DenseRetriever tests
# ═════════════════════════════════════════════════════════════════════


class TestDenseRetriever:
    """Tests for the FAISS-backed dense retriever."""

    def test_build_and_query_basic(self):
        """Top-3 results should be the AI/ML candidates."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results = dr.query(jd_vec, top_k=3)
        assert len(results) == 3

        top_ids = {cid for cid, _ in results}
        assert top_ids == {"CAND_0000001", "CAND_0000002", "CAND_0000003"}

    def test_scores_are_descending(self):
        """Scores must be in non-increasing order."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results = dr.query(jd_vec, top_k=8)
        scores = [s for _, s in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Score at rank {i} ({scores[i]:.4f}) < score at rank {i+1} ({scores[i+1]:.4f})"
            )

    def test_non_tech_candidates_rank_low(self):
        """Marketing/HR/Civil candidates should be in the bottom half."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results = dr.query(jd_vec, top_k=8)
        rank_map = {cid: rank for rank, (cid, _) in enumerate(results)}
        # Non-tech candidates should be ranked >= 3 (after the 3 AI/ML candidates)
        for cid in ["CAND_0000006", "CAND_0000007", "CAND_0000008"]:
            assert rank_map[cid] >= 3, f"{cid} ranked too high: {rank_map[cid]}"

    def test_query_returns_candidate_id_and_float_score(self):
        """Each result must be a (str, float) tuple."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results = dr.query(jd_vec, top_k=2)
        for cid, score in results:
            assert isinstance(cid, str)
            assert isinstance(score, float)

    def test_top_k_limits_results(self):
        """Requesting top_k=2 should return exactly 2 results."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results = dr.query(jd_vec, top_k=2)
        assert len(results) == 2

    def test_save_and_load_index(self, tmp_path: Path):
        """Index should be serialisable and produce identical results."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results_before = dr.query(jd_vec, top_k=5)

        index_path = tmp_path / "test.faiss"
        dr.save_index(index_path)

        # Create a new retriever and load the saved index
        dr2 = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr2.load_index(index_path)

        results_after = dr2.query(jd_vec, top_k=5)

        assert len(results_before) == len(results_after)
        for (cid1, s1), (cid2, s2) in zip(results_before, results_after):
            assert cid1 == cid2
            assert abs(s1 - s2) < 1e-6

    def test_query_before_build_raises(self):
        """Querying without building should raise RuntimeError."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)

        with pytest.raises(RuntimeError, match="not available"):
            dr.query(jd_vec, top_k=3)

    def test_mismatched_rows_raises(self):
        """Matrix rows ≠ candidate_ids length should raise ValueError."""
        embeddings, _ = _make_synthetic_embeddings()
        with pytest.raises(ValueError, match="candidate_ids length"):
            DenseRetriever(embeddings, CANDIDATE_IDS[:3])

    def test_query_1d_embedding(self):
        """A 1-D query vector should work the same as a 2-D row vector."""
        embeddings, jd_vec = _make_synthetic_embeddings()
        dr = DenseRetriever(embeddings, CANDIDATE_IDS)
        dr.build_index()

        results_2d = dr.query(jd_vec, top_k=5)  # shape (1, dim)
        results_1d = dr.query(jd_vec.ravel(), top_k=5)  # shape (dim,)

        for (c1, s1), (c2, s2) in zip(results_2d, results_1d):
            assert c1 == c2
            assert abs(s1 - s2) < 1e-6


# ═════════════════════════════════════════════════════════════════════
#  LexicalRetriever tests
# ═════════════════════════════════════════════════════════════════════


class TestLexicalRetriever:
    """Tests for the BM25-backed lexical retriever."""

    def test_build_and_query_basic(self):
        """AI/ML query terms should surface AI/ML candidates."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results = lr.query("machine learning Python FAISS embeddings", top_k=3)
        assert len(results) > 0

        top_ids = {cid for cid, _ in results}
        # Candidate 1 has all those keywords
        assert "CAND_0000001" in top_ids

    def test_non_relevant_query_surfaces_correct_candidates(self):
        """Marketing-related query should surface the marketing candidate."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results = lr.query("marketing SEO brand management", top_k=3)
        top_ids = {cid for cid, _ in results}
        assert "CAND_0000006" in top_ids

    def test_scores_are_non_negative(self):
        """BM25 scores should all be ≥ 0."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results = lr.query("Python engineer", top_k=8)
        for _, score in results:
            assert score >= 0.0

    def test_scores_are_descending(self):
        """Results must be sorted by score descending."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results = lr.query("machine learning engineer", top_k=5)
        scores = [s for _, s in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_empty_query_returns_empty(self):
        """Querying with empty string should return no results (all scores 0)."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results = lr.query("", top_k=5)
        assert len(results) == 0

    def test_query_before_build_raises(self):
        """Querying without building should raise RuntimeError."""
        lr = LexicalRetriever()
        with pytest.raises(RuntimeError, match="not available"):
            lr.query("test", top_k=3)

    def test_save_and_load(self, tmp_path: Path):
        """Index should be serialisable and produce identical results."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        results_before = lr.query("Python machine learning", top_k=5)

        index_path = tmp_path / "bm25.pkl"
        lr.save(index_path)

        lr2 = LexicalRetriever()
        lr2.load(index_path)

        results_after = lr2.query("Python machine learning", top_k=5)

        assert len(results_before) == len(results_after)
        for (c1, s1), (c2, s2) in zip(results_before, results_after):
            assert c1 == c2
            assert abs(s1 - s2) < 1e-6

    def test_mismatched_lengths_raises(self):
        """candidates ≠ candidate_ids should raise ValueError."""
        candidates = _make_synthetic_candidates()
        lr = LexicalRetriever()
        with pytest.raises(ValueError, match="candidate_ids"):
            lr.build_index(candidates, CANDIDATE_IDS[:3])


# ═════════════════════════════════════════════════════════════════════
#  Tokenizer tests
# ═════════════════════════════════════════════════════════════════════


class TestTokenizer:
    """Tests for the internal tokeniser used by LexicalRetriever."""

    def test_basic_tokenization(self):
        tokens = _tokenize("Machine Learning Engineer")
        assert tokens == ["machine", "learning", "engineer"]

    def test_special_chars_preserved(self):
        """C++ and C# should survive tokenisation."""
        tokens = _tokenize("C++ developer with C# experience")
        assert "c++" in tokens
        assert "c#" in tokens

    def test_short_tokens_dropped(self):
        """Single character tokens should be dropped."""
        tokens = _tokenize("I am a ML engineer")
        assert "i" not in tokens
        assert "ml" in tokens

    def test_empty_string(self):
        assert _tokenize("") == []


# ═════════════════════════════════════════════════════════════════════
#  HybridRetriever tests
# ═════════════════════════════════════════════════════════════════════


class TestHybridRetriever:
    """Tests for the hybrid (dense + lexical) fusion retriever."""

    def _build_retrievers(self):
        """Set up both retrievers on synthetic data."""
        candidates = _make_synthetic_candidates()
        ids = [c["candidate_id"] for c in candidates]
        embeddings, jd_vec = _make_synthetic_embeddings(n=len(ids))

        dr = DenseRetriever(embeddings, ids)
        dr.build_index()

        lr = LexicalRetriever()
        lr.build_index(candidates, ids)

        return dr, lr, jd_vec

    def test_rrf_fusion_returns_results(self):
        """RRF fusion should return a non-empty result set."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(
            jd_vec,
            "Senior AI Engineer machine learning Python FAISS",
            top_k=5,
            method="rrf",
        )
        assert len(results) > 0
        assert len(results) <= 5

    def test_weighted_fusion_returns_results(self):
        """Weighted fusion should return a non-empty result set."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(
            jd_vec,
            "Senior AI Engineer machine learning Python FAISS",
            top_k=5,
            method="weighted",
        )
        assert len(results) > 0
        assert len(results) <= 5

    def test_rrf_scores_descending(self):
        """RRF results should be sorted by score descending."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(jd_vec, "machine learning engineer", top_k=8, method="rrf")
        scores = [s for _, s in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_ai_ml_candidates_rank_high_rrf(self):
        """AI/ML candidates should dominate top-3 in RRF fusion."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(
            jd_vec,
            "Senior AI Engineer machine learning Python embeddings FAISS retrieval",
            top_k=8,
            method="rrf",
        )
        top3_ids = {cid for cid, _ in results[:3]}
        ai_ml_ids = {"CAND_0000001", "CAND_0000002", "CAND_0000003"}
        # At least 2 of 3 AI/ML candidates should be in top 3
        assert len(top3_ids & ai_ml_ids) >= 2, (
            f"Expected ≥ 2 AI/ML candidates in top-3, got {top3_ids & ai_ml_ids}"
        )

    def test_ai_ml_candidates_rank_high_weighted(self):
        """AI/ML candidates should dominate top-3 in weighted fusion."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(
            jd_vec,
            "Senior AI Engineer machine learning Python embeddings FAISS retrieval",
            top_k=8,
            method="weighted",
        )
        top3_ids = {cid for cid, _ in results[:3]}
        ai_ml_ids = {"CAND_0000001", "CAND_0000002", "CAND_0000003"}
        assert len(top3_ids & ai_ml_ids) >= 2

    def test_invalid_method_raises(self):
        """Unknown fusion method should raise ValueError."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        with pytest.raises(ValueError, match="Unknown fusion method"):
            hr.query(jd_vec, "test", top_k=5, method="invalid")

    def test_result_format(self):
        """Each result should be a (str, float) tuple."""
        dr, lr, jd_vec = self._build_retrievers()
        hr = HybridRetriever(dr, lr)

        results = hr.query(jd_vec, "machine learning", top_k=5, method="rrf")
        for cid, score in results:
            assert isinstance(cid, str)
            assert isinstance(score, float)


# ═════════════════════════════════════════════════════════════════════
#  RRF / normalisation unit tests
# ═════════════════════════════════════════════════════════════════════


class TestRRFAndNormalisation:
    """Unit tests for the fusion helper functions."""

    def test_rrf_single_list(self):
        """RRF of a single list should assign 1/(k+rank) scores."""
        ranked = [("A", 10.0), ("B", 8.0), ("C", 5.0)]
        fused = dict(_reciprocal_rank_fusion([ranked], k=60))

        assert abs(fused["A"] - 1 / 61) < 1e-8
        assert abs(fused["B"] - 1 / 62) < 1e-8
        assert abs(fused["C"] - 1 / 63) < 1e-8

    def test_rrf_two_lists_accumulates(self):
        """RRF should accumulate scores across lists."""
        list1 = [("A", 10.0), ("B", 8.0)]
        list2 = [("B", 5.0), ("A", 3.0)]
        fused = dict(_reciprocal_rank_fusion([list1, list2], k=60))

        # A: 1/61 (rank 1 in list1) + 1/62 (rank 2 in list2)
        expected_a = 1 / 61 + 1 / 62
        # B: 1/62 (rank 2 in list1) + 1/61 (rank 1 in list2)
        expected_b = 1 / 62 + 1 / 61

        assert abs(fused["A"] - expected_a) < 1e-8
        assert abs(fused["B"] - expected_b) < 1e-8
        # A and B should have the same score since both are rank 1+2
        assert abs(fused["A"] - fused["B"]) < 1e-8

    def test_rrf_candidate_in_only_one_list(self):
        """Candidates appearing in only one list should get partial RRF score."""
        list1 = [("A", 10.0), ("B", 8.0)]
        list2 = [("C", 5.0)]
        fused = dict(_reciprocal_rank_fusion([list1, list2], k=60))

        assert "C" in fused
        assert abs(fused["C"] - 1 / 61) < 1e-8
        assert fused["A"] == 1 / 61  # Only in list1

    def test_min_max_normalise_basic(self):
        """Min-max should scale to [0, 1]."""
        results = [("A", 10.0), ("B", 5.0), ("C", 0.0)]
        normed = dict(_min_max_normalise(results))

        assert abs(normed["A"] - 1.0) < 1e-8
        assert abs(normed["B"] - 0.5) < 1e-8
        assert abs(normed["C"] - 0.0) < 1e-8

    def test_min_max_normalise_equal_scores(self):
        """All equal scores should normalise to 1.0."""
        results = [("A", 5.0), ("B", 5.0), ("C", 5.0)]
        normed = dict(_min_max_normalise(results))

        for _, score in normed.items():
            assert abs(score - 1.0) < 1e-8

    def test_min_max_normalise_empty(self):
        """Empty input should return empty output."""
        assert _min_max_normalise([]) == []
