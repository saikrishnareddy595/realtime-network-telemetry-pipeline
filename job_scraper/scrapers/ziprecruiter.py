"""
ZipRecruiter scraper — public job listings page with BeautifulSoup.
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


class ZipRecruiterScraper:
    SOURCE = "ZipRecruiter"

    _SEARCH_URL = (
        "https://www.ziprecruiter.com/candidate/search"
        "?search={query}&location={location}&days=3&page={page}"
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
                    logger.error("ZipRecruiter '%s'/'%s' failed: %s", title, location, exc)
        logger.info("ZipRecruiter: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_jobs(self, title: str, location: str, pages: int = 2):
        query = quote_plus(title)
        loc   = quote_plus(location)
        headers = self._headers()

        for page in range(1, pages + 1):
            url = self._SEARCH_URL.format(query=query, location=loc, page=page)
            try:
                resp = self._session.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                jobs = self._parse_html(resp.text)
                self.jobs.extend(jobs)
                logger.debug("ZipRecruiter '%s' page %d: %d jobs", title, page, len(jobs))
                time.sleep(random.uniform(1.5, 3.0))
            except Exception as exc:
                logger.warning("ZipRecruiter page %d failed: %s", page, exc)

    # ------------------------------------------------------------------
    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        cards = (
            soup.select("article.job_result")
            or soup.select("div[data-testid='job-card']")
            or soup.select("div.job_content")
        )

        for card in cards:
            try:
                job = self._parse_card(card)
                if job:
                    results.append(job)
            except Exception as e:
                logger.debug("ZipRecruiter card error: %s", e)
        return results

    # ------------------------------------------------------------------
    def _parse_card(self, card) -> Dict[str, Any]:
        def _txt(*sels):
            for s in sels:
                el = card.select_one(s)
                if el:
                    return el.get_text(strip=True)
            return ""

        def _href(*sels):
            for s in sels:
                el = card.select_one(s)
                if el and el.get("href"):
                    h = el["href"]
                    return h if h.startswith("http") else "https://www.ziprecruiter.com" + h
            return ""

        title    = _txt("h2.title a", "a.job_link", "h2 a")
        company  = _txt("a.company_name", "p.company_name", "span.company")
        location = _txt("p.location", "span.location")
        salary   = _txt("p.salary", "span.salary_range")
        url      = _href("h2.title a", "a.job_link", "h2 a")
        date_txt = _txt("p.date", "span.posted_time", "time")

        # Also try data attributes
        if not title:
            title = card.get("data-job-title", "")
        if not company:
            company = card.get("data-company", "")

        if not title:
            return {}

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "salary":      self._parse_salary(salary),
            "url":         url,
            "source":      self.SOURCE,
            "posted_date": self._parse_date(date_txt),
            "easy_apply":  True,  # ZipRecruiter is primarily easy apply
            "applicants":  None,
            "description": "",
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_salary(text: str):
        import re
        if not text:
            return None
        nums = re.findall(r"[\d,]+", text)
        vals = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 0]
        if not vals:
            return None
        avg = sum(vals) / len(vals)
        if "hour" in text.lower() and avg < 1000:
            avg *= 2080
        elif "month" in text.lower() and avg < 50000:
            avg *= 12
        return int(avg)

    @staticmethod
    def _parse_date(text: str):
        import re
        now = datetime.now(timezone.utc)
        if not text:
            return now
        text = text.lower()
        if "today" in text or "now" in text or "just" in text:
            return now
        m = re.search(r"(\d+)\s*(h|d|hour|day|hr)", text)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("h"):
                return now - timedelta(hours=n)
            return now - timedelta(days=n)
        return now

    @staticmethod
    def _headers():
        return {
            "User-Agent":      ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer":         "https://www.ziprecruiter.com/",
        }
