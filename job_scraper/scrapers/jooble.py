"""Jooble scraper — REST API (key already in config)."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from scrapers.base import BaseAPIScraper, short_delay, parse_salary, parse_relative_date
import config

logger = logging.getLogger(__name__)

class JoobleScraper(BaseAPIScraper):
    SOURCE = "Jooble"
    _URL   = "https://jooble.org/api/{key}"

    def _fetch_title(self, title: str):
        if not config.JOOBLE_API_KEY:
            return
        url = self._URL.format(key=config.JOOBLE_API_KEY)
        payload = {"keywords": title, "location": "United States", "page": 1, "resultonpage": 30}
        try:
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            for item in r.json().get("jobs", []):
                job = self._parse(item)
                if job:
                    self._add(job)
            short_delay()
        except Exception as exc:
            logger.error("Jooble '%s': %s", title, exc)

    def _parse(self, item: dict) -> Dict[str, Any]:
        title = item.get("title", "")
        if not title:
            return {}
        pub = item.get("updated", "")
        try:
            posted = datetime.fromisoformat(pub.rstrip("Z")).replace(tzinfo=timezone.utc)
        except Exception:
            posted = parse_relative_date(pub)
        return {
            "title": title, "company": item.get("company",""),
            "location": item.get("location","United States"),
            "salary": parse_salary(item.get("salary","")),
            "url": item.get("link",""), "source": self.SOURCE,
            "posted_date": posted, "easy_apply": None, "applicants": None,
            "description": (item.get("snippet","") or "")[:500],
        }
