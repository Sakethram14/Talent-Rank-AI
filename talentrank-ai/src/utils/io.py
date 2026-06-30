"""
I/O utilities for TalentRank AI.

Handles JSONL streaming, JSON, pickle, and parquet serialization
with consistent error handling and logging.
"""

from __future__ import annotations

import json
import pickle
import gzip
from pathlib import Path
from typing import Any, Generator, Optional

from src.utils.logging import get_logger

logger = get_logger("utils.io")


def load_jsonl(
    filepath: Path,
    batch_size: Optional[int] = None,
    max_records: Optional[int] = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Stream-parse a JSONL file, yielding one record at a time.

    Handles both plain .jsonl and gzipped .jsonl.gz files.
    Memory-efficient: never loads the full file into RAM.

    Args:
        filepath: Path to the JSONL or JSONL.GZ file.
        batch_size: Not used for streaming; kept for API consistency.
        max_records: Maximum number of records to yield (None = all).

    Yields:
        Parsed dict for each valid JSONL line.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"JSONL file not found: {filepath}")

    open_fn = gzip.open if filepath.suffix == ".gz" else open
    open_kwargs = {"mode": "rt", "encoding": "utf-8"}

    count = 0
    errors = 0
    with open_fn(filepath, **open_kwargs) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                yield record
                count += 1
                if max_records and count >= max_records:
                    logger.info(
                        "Reached max_records=%d at line %d", max_records, line_num
                    )
                    return
            except json.JSONDecodeError as e:
                errors += 1
                logger.warning("Invalid JSON at line %d: %s", line_num, e)

    logger.info(
        "Loaded %d records from %s (%d parse errors)",
        count, filepath.name, errors,
    )


def load_jsonl_all(
    filepath: Path,
    max_records: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Load all records from a JSONL file into a list."""
    return list(load_jsonl(filepath, max_records=max_records))


def load_json(filepath: Path) -> Any:
    """Load a JSON file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Loaded JSON from %s", filepath.name)
    return data


def save_json(data: Any, filepath: Path, indent: int = 2) -> None:
    """Save data to a JSON file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    logger.info("Saved JSON to %s", filepath.name)


def save_pickle(obj: Any, filepath: Path) -> None:
    """Serialize an object to a pickle file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Saved pickle to %s (%.2f MB)", filepath.name, filepath.stat().st_size / 1e6)


def load_pickle(filepath: Path) -> Any:
    """Deserialize an object from a pickle file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Pickle file not found: {filepath}")
    with open(filepath, "rb") as f:
        obj = pickle.load(f)
    logger.info("Loaded pickle from %s", filepath.name)
    return obj
