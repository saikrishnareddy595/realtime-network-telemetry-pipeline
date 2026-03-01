"""Monster scraper — HTML scraping via public RSS feed."""
import logging
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List
from scrapers.base import BaseAPIScraper, short_delay, parse_salary
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

class MonsterScraper(BaseAPIScraper):
    SOURCE = "Monster"

    def _fetch_title(self, title: str):
        # Monster exposes an RSS feed for job searches
        url = (f"https://www.monster.com/rss/l-us_q-{quote_plus(title)}.xml"
               f"?daterecency=3")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:30]:
                job = self._parse(entry)
                if job:
                    self._add(job)
            short_delay()
        except Exception as exc:
            logger.error("Monster '%s': %s", title, exc)

    def _parse(self, entry) -> Dict[str, Any]:
        title = entry.get("title", "")
        if not title:
            return {}
        pub  = entry.get("published", "")
        try:
            posted = parsedate_to_datetime(pub).replace(tzinfo=timezone.utc)
        except Exception:
            posted = datetime.now(timezone.utc)
        summary = entry.get("summary", "")
        return {
            "title": title,
            "company": entry.get("author","") or entry.get("dc_creator",""),
            "location": entry.get("location","United States") or "United States",
            "salary": parse_salary(summary),
            "url": entry.get("link",""),
            "source": self.SOURCE, "posted_date": posted,
            "easy_apply": None, "applicants": None,
            "description": summary[:500],
        }
