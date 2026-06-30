"""
Orchestrates the entire offline intelligence pipeline.
This pre-computes all embeddings, indexes, and features needed
for the fast online ranking process.
"""

import sys
import time
import dataclasses
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings, reset_settings
from src.data.parser import CandidateParser
from src.data.cleaner import CandidateCleaner
from src.features.pipeline import FeaturePipeline
from src.embeddings.generator import EmbeddingGenerator
from src.retrieval.dense import DenseRetriever
from src.retrieval.lexical import LexicalRetriever
from src.utils.logging import get_logger

logger = get_logger("pipeline.offline")

def run_offline_pipeline(max_records: int | None = None):
    start_time = time.time()
    reset_settings()
    settings = get_settings(project_root=PROJECT_ROOT)

    logger.info("=" * 60)
    logger.info("OFFLINE PIPELINE STARTING")
    
    # 1. Parse and Clean Data
    logger.info("=" * 60)
    logger.info("STEP 1: Load and Clean Data")
    parser = CandidateParser(filepath=settings.paths.candidates_jsonl)
    candidates = parser.load_all(max_records=max_records)
    cleaner = CandidateCleaner()
    candidates = cleaner.clean_batch(candidates)
    logger.info("Loaded %d candidates", len(candidates))

    # 2. Build Feature Store
    logger.info("=" * 60)
    logger.info("STEP 2: Build Feature Store")
    feature_pipeline = FeaturePipeline()
    feature_store = feature_pipeline.run(candidates)
    feature_store.save(settings.paths.feature_store_path)
    logger.info("Saved Feature Store to %s", settings.paths.feature_store_path)

    # 3. Generate Embeddings
    logger.info("=" * 60)
    logger.info("STEP 3: Generate Embeddings")
    emb_generator = EmbeddingGenerator()
    candidate_dicts = [dataclasses.asdict(c) for c in candidates] # Deep convert to dicts
    emb_generator.generate_candidate_embeddings(candidate_dicts, settings.paths.embeddings_matrix_path)
    emb_generator.generate_jd_embedding(settings.paths.jd_embedding_path)

    # 4. Build Retrieval Indices
    logger.info("=" * 60)
    logger.info("STEP 4: Build Indices")
    candidate_ids = [c.candidate_id for c in candidates]
    
    # Dense Index
    emb_matrix = emb_generator.load_embeddings(settings.paths.embeddings_matrix_path)
    dense_retriever = DenseRetriever(emb_matrix, candidate_ids)
    dense_retriever.build_index()
    dense_retriever.save_index(settings.paths.faiss_index_path)
    
    # Lexical Index
    lexical_retriever = LexicalRetriever()
    lexical_retriever.build_index(candidate_dicts, candidate_ids)
    lexical_retriever.save(settings.paths.bm25_index_path)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("OFFLINE PIPELINE COMPLETE in %.1fs", elapsed)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-records", type=int, default=None)
    args = parser.parse_args()
    run_offline_pipeline(max_records=args.max_records)
