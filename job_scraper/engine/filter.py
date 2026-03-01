"""
Filter — removes jobs that don't meet search criteria.

Rules enforced:
  1. Salary < MIN_SALARY (if known)
  2. Contains EXCLUDE_KEYWORDS in title or description
  3. Posted more than MAX_JOB_AGE_HOURS ago
  4. Applicants > MAX_APPLICANTS (if known and EASY_APPLY_ONLY = False still filters saturated)
  5. Easy-apply only mode (if EASY_APPLY_ONLY = True)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import config

logger = logging.getLogger(__name__)

_EXCLUDE_LOWER = [kw.lower() for kw in config.EXCLUDE_KEYWORDS]


def _assign_role_category(job: Dict[str, Any]) -> str:
    """Detect which role category a job belongs to from its title."""
    title_lower = (job.get("title") or "").lower()
    for category, titles in config.ROLE_CATEGORIES.items():
        for t in titles:
            if t.lower() in title_lower:
                return category
    # fallback: check common patterns
    if any(kw in title_lower for kw in ["data engineer", "etl", "pipeline"]):
        return "data_engineer"
    if any(kw in title_lower for kw in ["ai engineer", "artificial intelligence"]):
        return "ai_engineer"
    if any(kw in title_lower for kw in ["machine learning", "ml engineer", "mlops"]):
        return "ml_engineer"
    if "data scientist" in title_lower:
        return "data_scientist"
    return "data_engineer"  # default


def _detect_job_type(job: Dict[str, Any]) -> str:
    """Detect job type from existing field or description text."""
    existing = (job.get("job_type") or "").lower().replace(" ", "_")
    if existing in ("full_time", "contract", "contract_to_hire", "part_time"):
        return existing
    # Parse from description / title
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
    ]).lower()
    if "contract to hire" in text or "contract-to-hire" in text or "c2h" in text:
        return "contract_to_hire"
    if any(kw in text for kw in ["contract", "contractor", "1099", "corp to corp", "c2c"]):
        return "contract"
    if "part time" in text or "part-time" in text:
        return "part_time"
    return "full_time"


class Filter:
    def filter(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        passed = []
        removed = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.MAX_JOB_AGE_HOURS)

        for job in jobs:
            # Enrich with role category + job type before filtering
            job["role_category"] = _assign_role_category(job)
            job["job_type"]      = _detect_job_type(job)

            reason = self._reject_reason(job, cutoff)
            if reason:
                logger.debug(
                    "Filtered '%s' @ %s — %s",
                    job.get("title"), job.get("company"), reason
                )
                removed += 1
            else:
                passed.append(job)

        logger.info("Filter: %d → %d jobs (%d removed)", len(jobs), len(passed), removed)
        return passed

    def _reject_reason(self, job: Dict[str, Any], cutoff: datetime) -> str:
        # 1) Salary check (only when explicitly known)
        salary = job.get("salary")
        if salary is not None:
            try:
                if float(salary) < config.MIN_SALARY:
                    return f"salary {salary} < {config.MIN_SALARY}"
            except (ValueError, TypeError):
                pass

        # 2) Exclude keyword check
        combined = " ".join([
            job.get("title", ""), job.get("description", "")
        ]).lower()
        for kw in _EXCLUDE_LOWER:
            if kw in combined:
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

        # 4) Applicants cap (only reject if way over — already saturated)
        applicants = job.get("applicants")
        if applicants is not None:
            try:
                if int(applicants) > config.MAX_APPLICANTS:
                    return f"too many applicants: {applicants}"
            except (ValueError, TypeError):
                pass

        # 5) Easy-apply-only mode
        if config.EASY_APPLY_ONLY and job.get("easy_apply") is False:
            return "easy_apply_only mode"

        return None
