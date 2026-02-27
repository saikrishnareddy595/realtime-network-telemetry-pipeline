"""
RemoteOK scraper — public REST API, no auth required.
Endpoint: https://remoteok.com/api?tags=data-engineer
"""

import logging
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import requests

import config

logger = logging.getLogger(__name__)


class RemoteOKScraper:
    SOURCE = "RemoteOK"

    _API_TAGS = [
        "data-engineer",
        "etl",
        "data-pipeline",
        "big-data",
    ]

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._seen_ids: set = set()

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        for tag in self._API_TAGS[:2]:
            try:
                self._fetch_tag(tag)
                time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
            except Exception as exc:
                logger.error("RemoteOK tag '%s' failed: %s", tag, exc)
        logger.info("RemoteOK: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_tag(self, tag: str):
        url = f"https://remoteok.com/api?tags={tag}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        data = resp.json()
        # First element is a metadata/legal notice dict — skip it
        for item in data[1:]:
            try:
                job = self._parse_item(item)
                if job and job["url"] not in self._seen_ids:
                    self._seen_ids.add(job["url"])
                    self.jobs.append(job)
            except Exception as e:
                logger.debug("RemoteOK item parse error: %s", e)

    # ------------------------------------------------------------------
    def _parse_item(self, item: dict) -> Dict[str, Any]:
        job_id   = item.get("id", "")
        title    = item.get("position", "")
        company  = item.get("company", "")
        location = item.get("location", "Remote")
        url      = item.get("url", f"https://remoteok.com/l/{job_id}")
        tags     = " ".join(item.get("tags", []))
        salary_min = item.get("salary_min") or item.get("annual_salary_min")
        salary_max = item.get("salary_max") or item.get("annual_salary_max")

        salary = None
        if salary_min and salary_max:
            salary = int((salary_min + salary_max) / 2)
        elif salary_min:
            salary = int(salary_min)
        elif salary_max:
            salary = int(salary_max)

        epoch = item.get("epoch")
        if epoch:
            posted_date = datetime.fromtimestamp(epoch, tz=timezone.utc)
        else:
            posted_date = datetime.now(timezone.utc)

        if not title:
            return {}

        return {
            "title":       title,
            "company":     company,
            "location":    location or "Remote",
            "salary":      salary,
            "url":         url,
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  True,  # RemoteOK is generally direct apply
            "applicants":  item.get("applicants"),
            "description": tags,
        }
