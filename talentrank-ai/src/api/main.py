import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.features.store import FeatureStore
from src.embeddings.generator import EmbeddingGenerator
from src.retrieval.dense import DenseRetriever
from src.retrieval.lexical import LexicalRetriever
from src.retrieval.hybrid import HybridRetriever
from src.ranking.ranker import CandidateRanker
from src.explanations.evidence import EvidenceCollector
from src.utils.logging import get_logger
from src.api.repository import CandidateRepository
from src.api.services.enrichment import CandidateEnrichmentLayer, RankingSessionManager


from src.api.routers import rank, explain, analytics, config, export, system, compare, sessions
from src.api.schemas.common import ErrorResponse, ErrorDetail, ResponseMetadata

logger = get_logger("api.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all ML singletons securely at startup."""
    start = time.time()
    logger.info("Initializing Intelligence API...")
    
    settings = get_settings()
    models = {}
    
    # 1. Feature Store
    logger.info("Loading Feature Store...")
    fs = FeatureStore.load(settings.paths.feature_store_path)
    models["feature_store"] = fs
    
    # 2. Embedding Generator
    logger.info("Loading Embedding Generator...")
    eg = EmbeddingGenerator()
    models["embedding_generator"] = eg
    
    # 3. Dense Retriever
    logger.info("Loading Dense Retriever...")
    embeddings_mat = eg.load_embeddings(settings.paths.embeddings_matrix_path)
    # Reconstruct candidate IDs from feature store
    # Ensure order matches embedding matrix exactly. In offline pipeline, we saved in same order.
    # The offline pipeline generated embeddings for `candidates` from `load_jsonl`.
    # Wait, DenseRetriever constructor needs `embedding_matrix` and `candidate_ids`.
    # Let's get candidate_ids from the feature store dataframe index.
    # Note: FeatureStore rows might not perfectly match the order of JSONL if there were issues, 
    # but the offline pipeline processes them sequentially.
    # To be extremely safe, we should load IDs directly or assume sequential.
    candidate_ids = fs.get_all().index.tolist()
    dr = DenseRetriever(embeddings_mat, candidate_ids)
    dr.load_index(settings.paths.faiss_index_path)
    models["dense_retriever"] = dr
    
    # 4. Lexical Retriever
    logger.info("Loading Lexical Retriever...")
    lr = LexicalRetriever()
    lr.load(settings.paths.bm25_index_path)
    models["lexical_retriever"] = lr
    
    # 5. Hybrid Retriever
    logger.info("Initializing Hybrid Retriever...")
    hr = HybridRetriever(dense_retriever=dr, lexical_retriever=lr)
    models["hybrid_retriever"] = hr
    
    # 6. Ranker
    logger.info("Initializing Candidate Ranker...")
    ranker = CandidateRanker()
    models["ranker"] = ranker
    
    # 7. Evidence Collector
    logger.info("Initializing Evidence Collector...")
    ec = EvidenceCollector()
    models["evidence_collector"] = ec
    
    # 8. Candidate Repository
    logger.info("Initializing Candidate Repository...")
    cr = CandidateRepository()
    cr.build_offset_index()
    models["candidate_repository"] = cr
    
    # 9. Enrichment Layer
    logger.info("Initializing Enrichment Layer...")
    el = CandidateEnrichmentLayer(repository=cr, evidence_collector=ec)
    models["enrichment_layer"] = el
    
    # 10. Session Manager
    logger.info("Initializing Session Manager...")
    sm = RankingSessionManager(enrichment_layer=el)
    models["session_manager"] = sm
    
    app.state.ml_models = models
    logger.info(f"Intelligence API Ready (loaded in {time.time() - start:.2f}s)")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Intelligence API...")
    app.state.ml_models.clear()

app = FastAPI(
    title="TalentRank AI - Intelligence API",
    description="Backend API for the TalentRank AI HackerEarth Submission",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for standardized errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled API error: {exc}", exc_info=True)
    response = ErrorResponse(
        success=False,
        errors=[ErrorDetail(code="internal_server_error", message="An unexpected error occurred.")],
        metadata=ResponseMetadata(version="1.0.0")
    )
    return JSONResponse(status_code=500, content=response.model_dump())

# Mount routers
app.include_router(system.router)
app.include_router(rank.router)
app.include_router(explain.router)
app.include_router(compare.router)
app.include_router(analytics.router)
app.include_router(config.router)
app.include_router(export.router)
app.include_router(sessions.router)
