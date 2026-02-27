"""
Glassdoor scraper — BeautifulSoup with rotating user agents.
Uses the public Glassdoor job search page (no login required for initial results).
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


class GlassdoorScraper:
    SOURCE = "Glassdoor"

    _SEARCH_URL = (
        "https://www.glassdoor.com/Job/us-{query}-jobs-SRCH_IL.0,2_IN1_KO3,{end}.htm"
        "?fromAge=3&sortBy=date_desc"
    )

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._session = requests.Session()

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:2]:
            try:
                self._fetch_title(title)
                time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
            except Exception as exc:
                logger.error("Glassdoor '%s' failed: %s", title, exc)
        logger.info("Glassdoor: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_title(self, title: str):
        slug = title.lower().replace(" ", "-")
        end  = 3 + len(slug)
        url  = self._SEARCH_URL.format(query=slug, end=end)
        headers = self._headers()

        try:
            resp = self._session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            jobs = self._parse_html(resp.text)
            self.jobs.extend(jobs)
            logger.debug("Glassdoor '%s': %d jobs", title, len(jobs))
        except Exception as exc:
            logger.warning("Glassdoor request failed: %s", exc)
            # Fallback: try alternative URL pattern
            self._fallback_fetch(title)

    # ------------------------------------------------------------------
    def _fallback_fetch(self, title: str):
        """Fallback to simple search URL pattern."""
        url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(title)}&locId=1&locT=N&jobType=&fromAge=3&minSalary=0&includeNoPay=true&radius=100&cityId=-1&minRating=0.0&industryId=-1&sgocId=-1&seniorityType=all&companyId=-1&employerSizes=0&applicationType=0&remoteWorkType=0"
        headers = self._headers()
        try:
            resp = self._session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            jobs = self._parse_html(resp.text)
            self.jobs.extend(jobs)
        except Exception as exc:
            logger.warning("Glassdoor fallback also failed: %s", exc)

    # ------------------------------------------------------------------
    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Try multiple card selectors as Glassdoor changes its markup
        cards = (
            soup.select("li.JobsList_jobListItem__JBBUV")
            or soup.select("li[data-test='jobListing']")
            or soup.select("article.jobCard")
            or soup.select("div.job-listing")
        )

        for card in cards:
            try:
                job = self._parse_card(card)
                if job:
                    results.append(job)
            except Exception as e:
                logger.debug("Glassdoor card parse error: %s", e)

        return results

    # ------------------------------------------------------------------
    def _parse_card(self, card) -> Dict[str, Any]:
        def _txt(*selectors):
            for sel in selectors:
                el = card.select_one(sel)
                if el:
                    return el.get_text(strip=True)
            return ""

        def _href(*selectors):
            for sel in selectors:
                el = card.select_one(sel)
                if el and el.get("href"):
                    h = el["href"]
                    return h if h.startswith("http") else "https://www.glassdoor.com" + h
            return ""

        title    = _txt("a.JobCard_seoLink__WdqHZ", "a[data-test='job-link']", "h2 a", "a.jobtitle")
        company  = _txt("span.EmployerProfile_compactEmployerName__LE242", "span[data-test='employer-name']", "div.jobEmpolyerName")
        location = _txt("div.JobCard_location__N_iYE", "span[data-test='emp-location']", "span.loc")
        salary   = _txt("div.JobCard_salaryEstimate__QpbTW", "span[data-test='detailSalary']")
        url      = _href("a.JobCard_seoLink__WdqHZ", "a[data-test='job-link']", "a.jobtitle")
        date_txt = _txt("div.JobCard_listingAge__KuaxZ", "span[data-test='job-age']")

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
            "easy_apply":  None,
            "applicants":  None,
            "description": "",
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_salary(text: str):
        import re
        if not text:
            return None
        nums = re.findall(r"[\d,]+", text.replace("$", ""))
        if not nums:
            return None
        vals = [int(n.replace(",", "")) for n in nums if int(n.replace(",", "")) > 0]
        if not vals:
            return None
        avg = sum(vals) / len(vals)
        # Glassdoor shows annual figures, but if < 1000 assume hourly
        if avg < 1000:
            avg *= 2080
        return int(avg)

    @staticmethod
    def _parse_date(text: str):
        import re
        now = datetime.now(timezone.utc)
        if not text:
            return now
        text = text.lower()
        if "now" in text or "today" in text or "just" in text:
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
            "Referer":         "https://www.glassdoor.com/",
        }
