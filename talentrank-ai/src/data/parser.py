"""
Candidate data parser for TalentRank AI.

Handles loading and parsing the full 100k candidate JSONL dataset
into typed CandidateRecord objects, with streaming support and
progress tracking.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Generator, Optional

from src.config.settings import get_settings
from src.data.models import CandidateRecord
from src.utils.io import load_jsonl
from src.utils.logging import get_logger

logger = get_logger("data.parser")


class CandidateParser:
    """
    Parses raw JSONL candidate data into typed CandidateRecord objects.

    Supports both streaming (memory-efficient for 100k records) and
    bulk loading modes.
    """

    def __init__(self, filepath: Optional[Path] = None) -> None:
        settings = get_settings()
        self.filepath = filepath or settings.paths.candidates_jsonl
        self._record_count = 0
        self._error_count = 0

    def stream(
        self,
        max_records: Optional[int] = None,
        log_every: int = 10_000,
    ) -> Generator[CandidateRecord, None, None]:
        """
        Stream-parse candidates one at a time.

        Memory-efficient: at any moment only one record is in memory.

        Args:
            max_records: Maximum number of records to yield.
            log_every: Log progress every N records.

        Yields:
            Parsed CandidateRecord instances.
        """
        logger.info("Streaming candidates from %s", self.filepath.name)
        start_time = time.time()
        self._record_count = 0
        self._error_count = 0

        for raw in load_jsonl(self.filepath, max_records=max_records):
            try:
                record = CandidateRecord.from_dict(raw)
                self._record_count += 1

                if self._record_count % log_every == 0:
                    elapsed = time.time() - start_time
                    rate = self._record_count / elapsed
                    logger.info(
                        "Parsed %d candidates (%.0f records/sec)",
                        self._record_count, rate,
                    )

                yield record
            except Exception as e:
                self._error_count += 1
                cid = raw.get("candidate_id", "UNKNOWN")
                logger.error("Failed to parse %s: %s", cid, e)

        elapsed = time.time() - start_time
        logger.info(
            "Parsing complete: %d records in %.1fs (%d errors)",
            self._record_count, elapsed, self._error_count,
        )

    def load_all(
        self,
        max_records: Optional[int] = None,
    ) -> list[CandidateRecord]:
        """
        Load all candidates into memory.

        For 100k records, this uses approximately 2-3 GB of RAM.
        """
        return list(self.stream(max_records=max_records))

    @property
    def record_count(self) -> int:
        return self._record_count

    @property
    def error_count(self) -> int:
        return self._error_count
