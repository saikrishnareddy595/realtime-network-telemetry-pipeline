"""
Scorer — assigns a relevance score (0–100) to each job.

Scoring rules:
  +30  Easy Apply enabled
  +25  Posted within last 24 hours
  +20  Fewer than 50 applicants
  +15  Company size 11–200 employees  (not detectable from scrape; skipped unless set)
  +10  Matches a dream company (Google, AWS, Microsoft, Meta, etc.)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import config

logger = logging.getLogger(__name__)

_DREAM_COMPANIES_LOWER = {c.lower() for c in config.DREAM_COMPANIES}


class Scorer:
    def score(self, job: Dict[str, Any]) -> int:
        points = 0

        # +30 — Easy Apply
        if job.get("easy_apply") is True:
            points += 30

        # +25 — Posted within last 24 hours
        posted = job.get("posted_date")
        if posted:
            if isinstance(posted, str):
                try:
                    posted = datetime.fromisoformat(posted).replace(tzinfo=timezone.utc)
                except ValueError:
                    posted = None
            if posted and (datetime.now(timezone.utc) - posted) <= timedelta(hours=24):
                points += 25

        # +20 — Fewer than 50 applicants
        applicants = job.get("applicants")
        if applicants is not None:
            try:
                if int(applicants) < 50:
                    points += 20
            except (ValueError, TypeError):
                pass
        else:
            # No applicant data — give partial credit (10 pts)
            points += 10

        # +15 — Company size 11–200 (not reliably detectable; skip)
        # This would require an additional enrichment API (e.g., Clearbit).

        # +10 — Dream company
        company = (job.get("company") or "").lower()
        if any(dream in company for dream in _DREAM_COMPANIES_LOWER):
            points += 10

        return min(points, 100)

    def score_all(self, jobs):
        for job in jobs:
            job["score"] = self.score(job)
        jobs.sort(key=lambda j: j["score"], reverse=True)
        return jobs
