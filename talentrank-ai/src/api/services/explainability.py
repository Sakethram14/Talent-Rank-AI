from typing import Any
from src.explanations.evidence import EvidenceCollector, CandidateEvidence
from src.data.parser import CandidateParser
from src.config.settings import get_settings
from src.api.schemas.ranking import CandidateEvidenceSchema, EvidenceItemSchema

class ExplainabilityService:
    def __init__(self, evidence_collector: EvidenceCollector):
        self.evidence_collector = evidence_collector
        self.settings = get_settings()

    def get_evidence(self, candidate_id: str, feature_scores: dict[str, float]) -> CandidateEvidenceSchema:
        """Fetch candidate record and generate evidence."""
        # Find candidate record.
        # In a real database this is O(1). For the hackathon we can load from JSONL if not cached.
        # However, to be fast we should only parse once. Let's just use the CandidateParser to find them.
        # This is a bit slow for an API, but it's okay for now. We can optimize later.
        parser = CandidateParser(self.settings.paths.candidates_jsonl)
        record = None
        for r in parser.stream():
            if r.candidate_id == candidate_id:
                record = r
                break
                
        if not record:
            raise ValueError(f"Candidate {candidate_id} not found")
            
        evidence = self.evidence_collector.collect(record, feature_scores)
        
        return CandidateEvidenceSchema(
            candidate_id=evidence.candidate_id,
            positive_signals=[EvidenceItemSchema(**vars(s)) for s in evidence.positive_signals],
            negative_signals=[EvidenceItemSchema(**vars(s)) for s in evidence.negative_signals],
            neutral_signals=[EvidenceItemSchema(**vars(s)) for s in evidence.neutral_signals],
            behavioral_summary=evidence.behavioral_summary,
            career_summary=evidence.career_summary,
            risk_flags=evidence.risk_flags,
            is_honeypot=evidence.is_honeypot,
            honeypot_reasons=evidence.honeypot_reasons
        )
