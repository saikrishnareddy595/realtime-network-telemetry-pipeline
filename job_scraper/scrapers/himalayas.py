"""Himalayas scraper — free public API for remote jobs."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

class HimalayasScraper(BaseAPIScraper):
    SOURCE = "Himalayas"
    _URL   = "https://himalayas.app/jobs/api"

    def _fetch_title(self, title: str):
        try:
            r = self._session.get(self._URL, params={"q": title, "limit": 50}, timeout=15)
            r.raise_for_status()
            for item in r.json().get("jobs", []):
                job = self._parse(item)
                if job:
                    self._add(job)
            short_delay()
        except Exception as exc:
            logger.error("Himalayas '%s': %s", title, exc)

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("title", "")
        if not title:
            return {}
        pub = item.get("publishedAt", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        from scrapers.base import parse_salary
        sal_min = item.get("salaryMin") or 0
        sal_max = item.get("salaryMax") or 0
        salary  = int((sal_min + sal_max) / 2) if sal_min or sal_max else None
        return {
            "title": title, "company": item.get("companyName",""),
            "location": item.get("locationRestrictions","Remote") or "Remote",
            "salary": salary, "url": item.get("applicationLink", item.get("url","")),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": True, "applicants": None,
            "description": (item.get("description","") or "")[:500],
        }
