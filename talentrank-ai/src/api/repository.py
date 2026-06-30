import json
from pathlib import Path
from typing import Dict, Optional
from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.utils.logging import get_logger

logger = get_logger("api.repository")

class CandidateRepository:
    """
    Manages O(1) access to raw candidate profiles.
    Uses an in-memory index of file offsets in the candidates.jsonl file
    to allow lightning-fast seek and parse operations without loading the 500MB dataset.
    """
    def __init__(self, filepath: Optional[Path] = None):
        settings = get_settings()
        self.filepath = filepath or settings.paths.candidates_jsonl
        self._offset_index: Dict[str, int] = {}
        self._is_indexed = False

    def build_offset_index(self):
        """Scan the JSONL file once and map candidate IDs to their file byte offsets."""
        if self._is_indexed:
            return
        
        logger.info(f"Building candidate file offset index from {self.filepath}...")
        if not self.filepath.exists():
            logger.error(f"Candidates file not found at {self.filepath}!")
            return
        
        offset = 0
        with open(self.filepath, "rb") as f:
            for line in f:
                # Find candidate_id in the first 100 bytes of the line quickly
                chunk = line[:100]
                try:
                    id_start = chunk.find(b'"candidate_id"')
                    if id_start != -1:
                        val_start = chunk.find(b'"', id_start + 14)
                        if val_start != -1:
                            val_end = chunk.find(b'"', val_start + 1)
                            if val_end != -1:
                                cid = chunk[val_start+1:val_end].decode("utf-8")
                                self._offset_index[cid] = offset
                except Exception as e:
                    logger.warning(f"Failed to index offset at {offset}: {e}")
                offset += len(line)
        
        self._is_indexed = True
        logger.info(f"Indexed {len(self._offset_index)} candidates.")

    def get_candidate(self, candidate_id: str) -> Optional[CandidateRecord]:
        """Fetch and parse a single candidate by ID using the file offset index."""
        if not self._is_indexed:
            self.build_offset_index()
            
        offset = self._offset_index.get(candidate_id)
        if offset is None:
            return None
            
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                f.seek(offset)
                line = f.readline()
                raw = json.loads(line)
                return CandidateRecord.from_dict(raw)
        except Exception as e:
            logger.error(f"Error fetching candidate {candidate_id} from JSONL: {e}")
            return None
