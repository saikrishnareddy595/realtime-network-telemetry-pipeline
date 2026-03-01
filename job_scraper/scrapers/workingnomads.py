"""Working Nomads scraper — free API for remote jobs."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

class WorkingNomadsScraper(BaseAPIScraper):
    SOURCE = "WorkingNomads"
    _URL   = "https://www.workingnomads.com/api/exposed_jobs/"
    _CATS  = ["data-science", "engineering", "devops-sysadmin"]

    def scrape(self) -> List[Dict[str, Any]]:
        for cat in self._CATS:
            try:
                r = self._session.get(self._URL, params={"category": cat}, timeout=15)
                r.raise_for_status()
                for item in r.json():
                    job = self._parse(item)
                    if job:
                        self._add(job)
                short_delay()
            except Exception as exc:
                logger.error("WorkingNomads cat '%s': %s", cat, exc)
        logger.info("WorkingNomads: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("title", "")
        if not title:
            return {}
        pub = item.get("pub_date", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        return {
            "title": title, "company": item.get("company",""),
            "location": item.get("location","Remote") or "Remote",
            "salary": None, "url": item.get("url",""),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": True, "applicants": None,
            "description": (item.get("description","") or "")[:500],
        }
