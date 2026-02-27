"""
Adzuna scraper — REST API (free tier).
Skips gracefully if API keys are not configured.
"""

import logging
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests

import config

logger = logging.getLogger(__name__)


class AdzunaScraper:
    SOURCE = "Adzuna"
    _BASE = "https://api.adzuna.com/v1/api/jobs/us/search/{page}"

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
            logger.info("Adzuna: API keys not configured — skipping")
            return []

        for title in config.JOB_TITLES[:2]:
            try:
                self._fetch_title(title)
                time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
            except Exception as exc:
                logger.error("Adzuna '%s' failed: %s", title, exc)

        logger.info("Adzuna: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_title(self, title: str, pages: int = 3):
        for page in range(1, pages + 1):
            url = self._BASE.format(page=page)
            params = {
                "app_id":     config.ADZUNA_APP_ID,
                "app_key":    config.ADZUNA_APP_KEY,
                "what":       title,
                "where":      "United States",
                "results_per_page": 20,
                "max_days_old": 3,
                "sort_by":    "date",
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    job = self._parse_item(item)
                    if job:
                        self.jobs.append(job)
                time.sleep(random.uniform(1, 2))
            except Exception as exc:
                logger.warning("Adzuna page %d failed: %s", page, exc)

    # ------------------------------------------------------------------
    def _parse_item(self, item: dict) -> Dict[str, Any]:
        title    = item.get("title", "")
        company  = item.get("company", {}).get("display_name", "")
        location = item.get("location", {}).get("display_name", "")
        url      = item.get("redirect_url", "")
        desc     = item.get("description", "")

        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        salary = None
        if salary_min and salary_max:
            salary = int((salary_min + salary_max) / 2)
        elif salary_min:
            salary = int(salary_min)
        elif salary_max:
            salary = int(salary_max)

        created = item.get("created")
        posted_date = datetime.now(timezone.utc)
        if created:
            try:
                posted_date = datetime.fromisoformat(created.rstrip("Z")).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        if not title:
            return {}

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "url":         url,
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  None,
            "applicants":  None,
            "description": desc[:500],
        }
