"""Wellfound (AngelList) scraper — startup jobs, often equity + above-market comp."""
import logging
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

class WellfoundScraper(BaseHTMLScraper):
    SOURCE = "Wellfound"

    def _fetch_title(self, title: str):
        url = f"https://wellfound.com/jobs?q={quote_plus(title)}&l=United+States"
        r = self._get(url)
        if not r:
            return
        soup  = BeautifulSoup(r.text, "lxml")
        cards = (soup.select("div[class*='JobListing']") or soup.select("div.job-listing")
                 or soup.select("[data-test='StartupResult']"))
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
                    return href if href.startswith("http") else "https://wellfound.com" + href
            return ""
        title = t("h2 a","a[data-test='job-title']",".job-title a")
        if not title: return {}
        return {
            "title": title, "company": t(".startup-name",".company-name","h3 a"),
            "location": t(".location","[data-test='location']"),
            "salary": parse_salary(t(".compensation",".salary","[data-test='comp']")),
            "url": h("h2 a","a[data-test='job-title']",".job-title a"),
            "source": self.SOURCE,
            "posted_date": parse_relative_date(t("time",".posted-date",".date")),
            "easy_apply": None, "applicants": None, "description": "",
        }
