"""ClearanceJobs scraper — cleared/government tech positions."""
import logging
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

class ClearanceJobsScraper(BaseHTMLScraper):
    SOURCE = "ClearanceJobs"

    def _fetch_title(self, title: str):
        url = f"https://www.clearancejobs.com/jobs?query={quote_plus(title)}&location=US&newJobsOnly=true"
        r = self._get(url)
        if not r:
            return
        soup  = BeautifulSoup(r.text, "lxml")
        cards = (soup.select("div.job-card") or soup.select("article.job")
                 or soup.select("[data-testid='job-card']"))
        for card in cards:
            job = self._parse(card)
            if job:
                self._add(job)
        from scrapers.base import short_delay; short_delay()

    def _parse(self, card) -> Dict[str, Any]:
        def t(*sels):
            for s in sels:
                el = card.select_one(s)
                if el: return el.get_text(strip=True)
            return ""
        def h(*sels):
            for s in sels:
                el = card.select_one(s)
                if el and el.get("href"):
                    href = el["href"]
                    return href if href.startswith("http") else "https://www.clearancejobs.com" + href
            return ""
        title = t("h2 a","a.job-title","h3 a",".position-title a")
        if not title: return {}
        return {
            "title": title, "company": t(".company-name",".employer",".company"),
            "location": t(".location",".job-location",".city-state"),
            "salary": parse_salary(t(".salary",".compensation")),
            "url": h("h2 a","a.job-title","h3 a",".position-title a"),
            "source": self.SOURCE,
            "posted_date": parse_relative_date(t(".posted-date","time",".date")),
            "easy_apply": None, "applicants": None, "description": "",
            "job_type": "full_time",
        }
