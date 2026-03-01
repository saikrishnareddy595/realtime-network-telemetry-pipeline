"""CareerBuilder scraper — HTML scraping of public search results."""
import logging
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

class CareerBuilderScraper(BaseHTMLScraper):
    SOURCE = "CareerBuilder"

    def _fetch_title(self, title: str):
        for page in range(1, 4):
            url = (f"https://www.careerbuilder.com/jobs?keywords={quote_plus(title)}"
                   f"&location=United+States&date_posted=3&page_number={page}")
            r = self._get(url)
            if not r:
                break
            soup = BeautifulSoup(r.text, "lxml")
            cards = (soup.select("li.job-listing-item")
                     or soup.select("div.data-results-content")
                     or soup.select("[data-testid='job-listing']"))
            if not cards:
                break
            for card in cards:
                job = self._parse(card)
                if job:
                    self._add(job)
            from scrapers.base import short_delay; short_delay()

    def _parse(self, card) -> Dict[str, Any]:
        def t(*sels):
            for s in sels:
                el = card.select_one(s)
                if el:
                    return el.get_text(strip=True)
            return ""
        def h(*sels):
            for s in sels:
                el = card.select_one(s)
                if el and el.get("href"):
                    href = el["href"]
                    return href if href.startswith("http") else "https://www.careerbuilder.com" + href
            return ""
        title    = t("h2.job-title", "[data-testid='job-title']", "h2 a")
        company  = t("div.job-listing-company", "[data-testid='company-name']", "span.company")
        location = t("div.job-listing-location", "[data-testid='location']")
        salary   = t("span.job-listing-salary", ".salary")
        url      = h("h2.job-title a", "[data-testid='job-title'] a", "h2 a")
        date_txt = t(".posted-date", "time", ".date-posted")
        if not title:
            return {}
        return {
            "title": title, "company": company, "location": location,
            "salary": parse_salary(salary), "url": url, "source": self.SOURCE,
            "posted_date": parse_relative_date(date_txt),
            "easy_apply": None, "applicants": None, "description": "",
        }
