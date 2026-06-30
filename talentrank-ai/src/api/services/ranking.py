import time
from typing import Any
import pandas as pd
import numpy as np
from src.embeddings.generator import EmbeddingGenerator
from src.retrieval.hybrid import HybridRetriever
from src.features.store import FeatureStore
from src.ranking.ranker import CandidateRanker, RankedCandidate
from src.api.schemas.ranking import RankingFilter
from src.utils.logging import get_logger

logger = get_logger("api.services.ranking")

class RankingService:
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        hybrid_retriever: HybridRetriever,
        feature_store: FeatureStore,
        ranker: CandidateRanker
    ):
        self.embedding = embedding_generator
        self.retriever = hybrid_retriever
        self.feature_store = feature_store
        self.ranker = ranker

    def rank_candidates(
        self, 
        job_description: str, 
        top_k: int, 
        filters: RankingFilter | None = None,
        custom_weights: dict[str, float] | None = None
    ) -> list[RankedCandidate]:
        """Core ranking pipeline."""
        start_time = time.time()
        
        # 1. Embed JD
        from sentence_transformers import SentenceTransformer
        # Since EmbeddingGenerator uses offline batch processing, we can directly encode for a single string.
        # But wait, EmbeddingGenerator._model is loaded. We can use it.
        jd_vec = self.embedding._model.encode(job_description, normalize_embeddings=True)
        jd_vec = jd_vec.reshape(1, -1)
        
        # 2. Retrieve Hybrid Top N (we retrieve more than top_k to allow filtering)
        retrieve_k = max(300, top_k * 3)
        retrieval_results = self.retriever.query(jd_vec, job_description, top_k=retrieve_k)
        
        # 3. Load features for retrieved candidates
        df = self.feature_store.get_all()
        
        # 4. Rank candidates
        ranked = self.ranker.rank(retrieval_results, df, custom_weights=custom_weights)
        
        # 5. Apply filters
        filtered_ranked = []
        honeypots_to_add = []
        
        for rc in ranked:
            if filters:
                if filters.exclude_honeypots and rc.is_honeypot:
                    continue
            
            if rc.is_honeypot:
                if len(honeypots_to_add) < 10:
                    honeypots_to_add.append(rc)
                continue
                
            # Fetch features for other filters
            try:
                feat = df.loc[rc.candidate_id]
            except KeyError:
                continue
                
            if filters and filters.min_experience_years is not None and feat.get("years_experience", 0) < filters.min_experience_years:
                continue
            if filters and filters.max_experience_years is not None and feat.get("years_experience", 0) > filters.max_experience_years:
                continue
            
            filtered_ranked.append(rc)
            if len(filtered_ranked) >= top_k:
                break
                
        if not (filters and filters.exclude_honeypots):
            filtered_ranked.extend(honeypots_to_add)
                
        logger.info(f"Ranking completed in {time.time() - start_time:.2f}s")
        return filtered_ranked
