"""USAJobs scraper — US government job board REST API (free key at usajobs.gov)."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from scrapers.base import BaseAPIScraper, short_delay, parse_salary
import config

logger = logging.getLogger(__name__)

class USAJobsScraper(BaseAPIScraper):
    SOURCE = "USAJobs"
    _URL   = "https://data.usajobs.gov/api/search"

    def _fetch_title(self, title: str):
        if not config.USAJOBS_API_KEY:
            return  # skip silently
        headers = {
            "Host":            "data.usajobs.gov",
            "User-Agent":      config.GMAIL_ADDRESS,  # USAJobs requires email as User-Agent
            "Authorization-Key": config.USAJOBS_API_KEY,
        }
        params = {
            "Keyword":       title,
            "DatePosted":    3,
            "ResultsPerPage": 25,
            "Fields":        "min",
        }
        try:
            r = requests.get(self._URL, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("SearchResult", {}).get("SearchResultItems", [])
            for item in items:
                job = self._parse(item)
                if job:
                    self._add(job)
            short_delay()
        except Exception as exc:
            logger.error("USAJobs '%s': %s", title, exc)

    def _parse(self, item: dict) -> Dict[str, Any]:
        m   = item.get("MatchedObjectDescriptor", {})
        title = m.get("PositionTitle", "")
        if not title:
            return {}
        pub = m.get("PublicationStartDate", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        locs   = m.get("PositionLocation", [{}])
        loc    = locs[0].get("LocationName", "United States") if locs else "United States"
        sal    = m.get("PositionRemuneration", [{}])
        salary = None
        if sal:
            lo = sal[0].get("MinimumRange")
            hi = sal[0].get("MaximumRange")
            if lo and hi:
                salary = int((float(lo) + float(hi)) / 2)
            elif lo:
                salary = int(float(lo))
        return {
            "title": title, "company": m.get("OrganizationName","US Government"),
            "location": loc, "salary": salary,
            "url": m.get("PositionURI",""), "source": self.SOURCE,
            "posted_date": posted, "easy_apply": False, "applicants": None,
            "description": m.get("QualificationSummary","")[:500],
            "job_type": "full_time",
        }
