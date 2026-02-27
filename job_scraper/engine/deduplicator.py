"""
Deduplicator — removes duplicate jobs across multiple sources.
Hash key: lowercase(title) + lowercase(company) + lowercase(location)
"""

import hashlib
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self):
        self._seen: dict = {}  # hash -> job dict (keep highest-scored or first)

    # ------------------------------------------------------------------
    def deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate a list of job dicts.
        If two jobs share the same (title, company, location) hash,
        keep the one with a non-None salary, or the first one found.
        """
        for job in jobs:
            key = self._make_key(job)
            if key not in self._seen:
                self._seen[key] = job
            else:
                # Prefer the entry with more data
                existing = self._seen[key]
                if existing.get("salary") is None and job.get("salary") is not None:
                    self._seen[key] = job
                elif existing.get("easy_apply") is None and job.get("easy_apply") is not None:
                    self._seen[key]["easy_apply"] = job["easy_apply"]

        unique = list(self._seen.values())
        logger.info("Deduplicator: %d jobs in → %d unique", len(jobs), len(unique))
        return unique

    # ------------------------------------------------------------------
    @staticmethod
    def _make_key(job: Dict[str, Any]) -> str:
        raw = (
            (job.get("title") or "").lower().strip()
            + "|"
            + (job.get("company") or "").lower().strip()
            + "|"
            + (job.get("location") or "").lower().strip()
        )
        return hashlib.md5(raw.encode()).hexdigest()
