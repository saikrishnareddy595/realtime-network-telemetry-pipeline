"""Built In scraper — tech-only job board with city pages."""
import logging
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

_CITIES = ["", "nyc", "chicago", "austin", "seattle", "boston", "la", "atlanta"]

class BuiltInScraper(BaseHTMLScraper):
    SOURCE = "BuiltIn"

    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:4]:
            for city in _CITIES[:3]:
                try:
                    self._fetch_city(title, city)
                    from scrapers.base import short_delay; short_delay()
                except Exception as exc:
                    logger.error("BuiltIn '%s'/%s: %s", title, city, exc)
        logger.info("BuiltIn: %d jobs", len(self.jobs))
        return self.jobs

    def _fetch_title(self, title): pass

    def _fetch_city(self, title: str, city: str):
        base = f"https://builtin{''+city if not city else '.com/' + city}.com/jobs"
        url  = f"{base}/search?q={quote_plus(title)}"
        r = self._get(url)
        if not r:
            return
        soup  = BeautifulSoup(r.text, "lxml")
        cards = soup.select("li[data-id]") or soup.select("div.job-card") or soup.select("article.job")
        for card in cards:
            job = self._parse(card)
            if job:
                self._add(job)

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
                    return href if href.startswith("http") else "https://builtin.com" + href
            return ""
        title = t("h2 a","a.job-title",".job-name a")
        if not title: return {}
        return {
            "title": title, "company": t(".company-name",".employer"),
            "location": t(".location",".job-location"),
            "salary": parse_salary(t(".salary",".compensation")),
            "url": h("h2 a","a.job-title",".job-name a"),
            "source": self.SOURCE,
            "posted_date": parse_relative_date(t(".posted-date","time",".date")),
            "easy_apply": None, "applicants": None, "description": "",
        }
