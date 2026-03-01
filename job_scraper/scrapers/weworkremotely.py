"""WeWorkRemotely scraper — large remote-only job board via RSS feed."""
import logging
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay
import config

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]

class WeWorkRemotelyScraper(BaseAPIScraper):
    SOURCE = "WeWorkRemotely"

    def scrape(self) -> List[Dict[str, Any]]:
        for feed_url in _RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:50]:
                    job = self._parse(entry)
                    if job:
                        self._add(job)
                short_delay()
            except Exception as exc:
                logger.error("WWR feed %s: %s", feed_url, exc)
        logger.info("WeWorkRemotely: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass

    def _parse(self, entry) -> Dict[str, Any]:
        raw_title = entry.get("title","")
        # WWR titles are "Company: Job Title"
        parts  = raw_title.split(":", 1)
        company = parts[0].strip() if len(parts) == 2 else ""
        title   = parts[1].strip() if len(parts) == 2 else raw_title
        if not title: return {}
        pub = entry.get("published","")
        try:
            posted = parsedate_to_datetime(pub).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        return {
            "title": title, "company": company, "location": "Remote",
            "salary": None, "url": entry.get("link",""),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": True, "applicants": None,
            "description": entry.get("summary","")[:500],
        }
