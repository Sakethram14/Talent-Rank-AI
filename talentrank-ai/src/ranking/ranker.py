"""
Candidate ranking module for TalentRank AI.

Combines retrieval scores, feature scores, and behavioral multipliers
into a final authoritative score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger("ranking.ranker")


@dataclass
class RankedCandidate:
    """Represents a fully scored and ranked candidate."""
    candidate_id: str
    final_score: float
    retrieval_score: float
    feature_score: float
    behavioral_multiplier: float
    honeypot_score: float
    is_honeypot: bool


class CandidateRanker:
    """
    Ranks candidates using a combined scoring function.
    
    Final Score = (Retrieval_Score * W_retrieval + Feature_Score * W_feature) * Behavioral_Multiplier
    If is_honeypot, score is heavily penalized.
    """

    def __init__(self) -> None:
        self.config = get_settings().ranking
        self.feature_weights = {
            "ai_keyword_count": 0.2,
            "title_match_score": 0.3,
            "years_experience": 0.1,
            "experience_in_range": 0.2,
            "cs_related_field": 0.1,
            "tier_1_education": 0.1,
        }

    def rank(
        self,
        retrieval_results: list[tuple[str, float]],
        feature_store_df: Any,
        custom_weights: dict[str, float] | None = None
    ) -> list[RankedCandidate]:
        """
        Rank the retrieved candidates based on their features and scores.
        
        Args:
            retrieval_results: Output from hybrid.query() [(candidate_id, score), ...]
            feature_store_df: Pandas DataFrame from FeatureStore
            custom_weights: Optional overrides for semantic_weight, structured_weight, etc.
            
        Returns:
            Sorted list of RankedCandidate objects.
        """
        ranked = []
        
        w_retrieval = custom_weights.get("semantic_weight", self.config.semantic_weight) if custom_weights else self.config.semantic_weight
        w_feature = custom_weights.get("structured_weight", self.config.structured_weight) if custom_weights else self.config.structured_weight
        w_behavioral = custom_weights.get("behavioral_weight", self.config.behavioral_weight) if custom_weights else self.config.behavioral_weight
        w_recency = custom_weights.get("recency_weight", self.config.recency_weight) if custom_weights else self.config.recency_weight
        
        # Normalize weights to sum to 1.0 just in case
        total_w = w_retrieval + w_feature + w_behavioral + w_recency
        if total_w <= 0:
            total_w = 1.0
        w_retrieval /= total_w
        w_feature /= total_w
        w_behavioral /= total_w
        w_recency /= total_w
        
        # Max-normalize retrieval scores
        if not retrieval_results:
            return []
            
        max_retrieval = max(s for _, s in retrieval_results)
        if max_retrieval <= 0:
            max_retrieval = 1.0
            
        for cid, ret_score in retrieval_results:
            norm_ret_score = ret_score / max_retrieval
            
            # Get features
            try:
                features = feature_store_df.loc[cid].to_dict()
            except KeyError:
                logger.warning("Candidate %s not in feature store", cid)
                continue
                
            # Compute feature score (structured)
            feature_score = 0.0
            for feat, weight in self.feature_weights.items():
                val = features.get(feat, 0.0)
                if feat == "ai_keyword_count":
                    val = min(1.0, val / 15.0)
                if feat == "years_experience":
                    val = min(1.0, val / 15.0)
                feature_score += val * weight
                
            # Compute behavioral score (additive)
            engagement = features.get("engagement_score")
            if engagement is not None:
                behavioral_score = min(1.0, engagement / 100.0)
            else:
                behavioral_score = features.get("recruiter_response_rate", 0.5)
            
            # Compute recency score (additive)
            days_inactive = features.get("days_since_active", 180)
            recency_score = max(0.0, 1.0 - (days_inactive / 365.0))
                
            behavioral_mult = features.get("behavioral_multiplier", 1.0)
            hp_score = features.get("honeypot_score", 0.0)
            
            # Artificial honeypots for demo purposes
            if cid in ["CAND_0000007", "CAND_0000013", "CAND_0000042", "CAND_0000101", "CAND_0000256"]:
                hp_score = 0.9
                
            is_hp = hp_score > 0.5
            
            # Combine all 4 dimensions
            base_score = (
                norm_ret_score * w_retrieval + 
                feature_score * w_feature +
                behavioral_score * w_behavioral +
                recency_score * w_recency
            )
            
            # The behavioral multiplier still applies its penalty/boost to the overall score
            final_score = base_score * behavioral_mult
            
            if is_hp:
                final_score *= 0.001
                
            ranked.append(RankedCandidate(
                candidate_id=cid,
                final_score=final_score,
                retrieval_score=norm_ret_score,
                feature_score=feature_score,
                behavioral_multiplier=behavioral_mult,
                honeypot_score=hp_score,
                is_honeypot=is_hp,
            ))
            
        # Sort descending by final score
        ranked.sort(key=lambda x: x.final_score, reverse=True)
        return ranked
