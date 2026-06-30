"""
FastAPI Dependencies for TalentRank AI.

Manages loading the heavy ML singletons (embeddings, retrievers, feature store)
once at application startup and injecting them into route handlers.
"""
from typing import Any
from fastapi import Request
from src.features.store import FeatureStore
from src.retrieval.dense import DenseRetriever
from src.retrieval.lexical import LexicalRetriever
from src.retrieval.hybrid import HybridRetriever
from src.embeddings.generator import EmbeddingGenerator
from src.ranking.ranker import CandidateRanker
from src.explanations.evidence import EvidenceCollector

def get_feature_store(request: Request) -> FeatureStore:
    return request.app.state.ml_models["feature_store"]

def get_dense_retriever(request: Request) -> DenseRetriever:
    return request.app.state.ml_models["dense_retriever"]

def get_lexical_retriever(request: Request) -> LexicalRetriever:
    return request.app.state.ml_models["lexical_retriever"]

def get_hybrid_retriever(request: Request) -> HybridRetriever:
    return request.app.state.ml_models["hybrid_retriever"]

def get_embedding_generator(request: Request) -> EmbeddingGenerator:
    return request.app.state.ml_models["embedding_generator"]

def get_ranker(request: Request) -> CandidateRanker:
    return request.app.state.ml_models["ranker"]

def get_evidence_collector(request: Request) -> EvidenceCollector:
    return request.app.state.ml_models["evidence_collector"]

def get_candidate_repository(request: Request) -> Any:
    return request.app.state.ml_models["candidate_repository"]

def get_enrichment_layer(request: Request) -> Any:
    return request.app.state.ml_models["enrichment_layer"]

def get_session_manager(request: Request) -> Any:
    return request.app.state.ml_models["session_manager"]

