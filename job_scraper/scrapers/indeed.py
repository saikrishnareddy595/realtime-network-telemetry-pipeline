"""
Indeed scraper — uses the unofficial JSON API with BeautifulSoup HTML fallback.
"""

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

import config

logger = logging.getLogger(__name__)
ua = UserAgent()


class IndeedScraper:
    SOURCE = "Indeed"

    _JSON_API = (
        "https://www.indeed.com/jobs?q={query}&l={location}"
        "&fromage=3&sort=date&limit=25&start={start}&format=json"
    )
    _HTML_URL = (
        "https://www.indeed.com/jobs?q={query}&l={location}"
        "&fromage=3&sort=date&limit=25&start={start}"
    )

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._session = requests.Session()

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:2]:
            for location in ["United States", "Remote"]:
                try:
                    self._fetch_jobs(title, location)
                    time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
                except Exception as exc:
                    logger.error("Indeed scraper error (%s / %s): %s", title, location, exc)
        logger.info("Indeed: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_jobs(self, title: str, location: str, pages: int = 2):
        query = quote_plus(title)
        loc   = quote_plus(location)
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        for page in range(pages):
            start = page * 25
            url = self._HTML_URL.format(query=query, location=loc, start=start)
            try:
                resp = self._session.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                jobs = self._parse_html(resp.text)
                self.jobs.extend(jobs)
                logger.debug("Indeed '%s' page %d: %d jobs", title, page, len(jobs))
                time.sleep(random.uniform(1.5, 3.0))
            except Exception as exc:
                logger.warning("Indeed page %d failed: %s", page, exc)

    # ------------------------------------------------------------------
    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for card in soup.select("div.job_seen_beacon, div.jobsearch-SerpJobCard"):
            try:
                job = self._parse_card(card)
                if job:
                    results.append(job)
            except Exception as e:
                logger.debug("Indeed card parse error: %s", e)
        return results

    # ------------------------------------------------------------------
    def _parse_card(self, card) -> Dict[str, Any]:
        title_el   = card.select_one("h2.jobTitle span, a.jobtitle")
        company_el = card.select_one("span.companyName, span.company")
        loc_el     = card.select_one("div.companyLocation, span.location")
        salary_el  = card.select_one("div.salary-snippet-container, span.salaryText")
        link_el    = card.select_one("a[id^='job_'], a.jobtitle")
        date_el    = card.select_one("span.date")

        job_title = title_el.get_text(strip=True) if title_el else ""
        if not job_title:
            return {}

        company  = company_el.get_text(strip=True) if company_el else ""
        location = loc_el.get_text(strip=True) if loc_el else ""
        salary_text = salary_el.get_text(strip=True) if salary_el else ""
        salary = self._parse_salary(salary_text)

        href = ""
        if link_el:
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://www.indeed.com" + href

        posted_date = self._parse_date(date_el.get_text(strip=True) if date_el else "")

        return {
            "title":       job_title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "url":         href,
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  None,
            "applicants":  None,
            "description": "",
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_salary(text: str):
        """Extract annual salary integer from a salary string."""
        import re
        if not text:
            return None
        nums = re.findall(r"[\d,]+", text)
        if not nums:
            return None
        vals = [int(n.replace(",", "")) for n in nums]
        # If hourly, annualise (assume 2080 hrs/year)
        if "hour" in text.lower() or "/hr" in text.lower():
            return int(sum(vals) / len(vals) * 2080)
        # If monthly
        if "month" in text.lower():
            return int(sum(vals) / len(vals) * 12)
        return int(sum(vals) / len(vals)) if vals else None

    @staticmethod
    def _parse_date(text: str):
        now = datetime.now(timezone.utc)
        if not text:
            return now
        text = text.lower()
        if "just" in text or "today" in text:
            return now
        if "hour" in text:
            import re
            m = re.search(r"(\d+)", text)
            hrs = int(m.group(1)) if m else 1
            return now - timedelta(hours=hrs)
        if "day" in text:
            import re
            m = re.search(r"(\d+)", text)
            days = int(m.group(1)) if m else 1
            return now - timedelta(days=days)
        return now
