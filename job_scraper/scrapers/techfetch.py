"""TechFetch scraper — IT contract/staffing board, heavy contract postings."""
import logging
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date
from urllib.parse import quote_plus
import config

logger = logging.getLogger(__name__)

class TechFetchScraper(BaseHTMLScraper):
    SOURCE = "TechFetch"

    def _fetch_title(self, title: str):
        url = f"https://www.techfetch.com/job/jobsearchresult.aspx?q={quote_plus(title)}&l=USA"
        r = self._get(url)
        if not r:
            return
        soup  = BeautifulSoup(r.text, "lxml")
        cards = (soup.select("div.job-listing") or soup.select("li.job_result")
                 or soup.select("[class*='job-item']"))
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
                    return href if href.startswith("http") else "https://www.techfetch.com" + href
            return ""
        title = t("h2 a","a.job-title",".jobtitle a","h3 a")
        if not title: return {}
        raw_type = t(".job-type",".employment-type","span.type")
        job_type = "contract" if "contract" in raw_type.lower() else "full_time"
        return {
            "title": title, "company": t(".company",".employer",".companyname"),
            "location": t(".location",".city"),
            "salary": parse_salary(t(".salary",".rate",".compensation")),
            "url": h("h2 a","a.job-title",".jobtitle a","h3 a"),
            "source": self.SOURCE,
            "posted_date": parse_relative_date(t(".posted",".date",".dateposted")),
            "easy_apply": None, "applicants": None, "description": "",
            "job_type": job_type,
        }
