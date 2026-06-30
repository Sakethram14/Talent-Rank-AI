"""
Configuration Manager for TalentRank AI Backend.

Provides a safe abstraction for runtime updates to scoring weights and thresholds
without modifying the static frozen dataclasses directly.
"""

from typing import Any, Dict
from pydantic import BaseModel
from src.config.settings import get_settings, RankingConfig

class RankingWeightsUpdate(BaseModel):
    """Schema for updating ranking weights."""
    semantic_weight: float | None = None
    structured_weight: float | None = None
    behavioral_weight: float | None = None
    recency_weight: float | None = None


class ConfigManager:
    """Manages runtime configuration overrides."""
    
    def __init__(self):
        self._settings = get_settings()
        # Store runtime overrides
        self._ranking_overrides: Dict[str, float] = {}
        
    def update_ranking_weights(self, updates: RankingWeightsUpdate) -> dict[str, float]:
        """Update ranking weights safely."""
        update_dict = updates.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            self._ranking_overrides[k] = v
        return self.get_active_ranking_weights()
        
    def get_active_ranking_weights(self) -> dict[str, float]:
        """Get the current active ranking weights (defaults + overrides)."""
        defaults = {
            "semantic_weight": self._settings.ranking.semantic_weight,
            "structured_weight": self._settings.ranking.structured_weight,
            "behavioral_weight": self._settings.ranking.behavioral_weight,
            "recency_weight": self._settings.ranking.recency_weight,
        }
        defaults.update(self._ranking_overrides)
        return defaults

# Global singleton
config_manager = ConfigManager()
