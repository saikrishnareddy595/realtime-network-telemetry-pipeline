"""
Filter — removes jobs that don't meet search criteria.

Rules:
  - Salary < $80,000 (if salary is known)
  - Contains any EXCLUDE_KEYWORDS in title or description
  - Posted more than 72 hours ago
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)

_EXCLUDE_LOWER = [kw.lower() for kw in config.EXCLUDE_KEYWORDS]


class Filter:
    def filter(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        passed = []
        removed = 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.MAX_JOB_AGE_HOURS)

        for job in jobs:
            reason = self._reject_reason(job, cutoff)
            if reason:
                logger.debug("Filtered out '%s' @ %s — %s", job.get("title"), job.get("company"), reason)
                removed += 1
            else:
                passed.append(job)

        logger.info("Filter: %d → %d jobs (%d removed)", len(jobs), len(passed), removed)
        return passed

    # ------------------------------------------------------------------
    def _reject_reason(self, job: Dict[str, Any], cutoff: datetime):
        # 1) Salary check (only when salary is explicitly known)
        salary = job.get("salary")
        if salary is not None:
            try:
                if float(salary) < config.MIN_SALARY:
                    return f"salary {salary} < {config.MIN_SALARY}"
            except (ValueError, TypeError):
                pass

        # 2) Exclude keyword check
        combined_text = " ".join([
            (job.get("title") or ""),
            (job.get("description") or ""),
        ]).lower()

        for kw in _EXCLUDE_LOWER:
            if kw in combined_text:
                return f"excluded keyword: {kw}"

        # 3) Age check
        posted = job.get("posted_date")
        if posted:
            if isinstance(posted, str):
                try:
                    posted = datetime.fromisoformat(posted).replace(tzinfo=timezone.utc)
                except ValueError:
                    posted = None
            if posted and posted < cutoff:
                return f"too old: {posted.isoformat()}"

        return None  # no rejection reason → keep
