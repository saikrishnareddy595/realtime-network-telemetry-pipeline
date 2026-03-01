"""The Muse scraper — free public API."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

class TheMuseScraper(BaseAPIScraper):
    SOURCE  = "TheMuse"
    _URL    = "https://www.themuse.com/api/public/jobs"
    _CATS   = ["Data Science", "IT", "Software Engineer"]

    def scrape(self) -> List[Dict[str, Any]]:
        for cat in self._CATS:
            for page in range(1, 4):
                try:
                    params = {"category": cat, "page": page, "level": "Senior Level,Mid Level"}
                    r = self._session.get(self._URL, params=params, timeout=15)
                    r.raise_for_status()
                    results = r.json().get("results", [])
                    if not results:
                        break
                    for item in results:
                        job = self._parse(item)
                        if job:
                            self._add(job)
                    short_delay()
                except Exception as exc:
                    logger.error("TheMuse cat '%s' p%d: %s", cat, page, exc)
        logger.info("TheMuse: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("name", "")
        if not title:
            return {}
        pub = item.get("publication_date", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        locs   = item.get("locations", [{}])
        loc    = locs[0].get("name", "United States") if locs else "United States"
        company = item.get("company", {}).get("name", "")
        url     = item.get("refs", {}).get("landing_page", "")
        return {
            "title": title, "company": company, "location": loc,
            "salary": None, "url": url, "source": self.SOURCE,
            "posted_date": posted, "easy_apply": None, "applicants": None,
            "description": (item.get("contents","") or "")[:500],
        }
