"""
Base scraper classes — shared patterns to reduce boilerplate.
"""

import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from fake_useragent import UserAgent

import config

logger = logging.getLogger(__name__)
_ua = UserAgent()


def random_delay():
    time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))


def short_delay():
    time.sleep(random.uniform(1.0, 2.0))


def parse_salary(text: str) -> Optional[int]:
    if not text:
        return None
    t = text.lower()
    nums = re.findall(r"[\d,]+", text.replace("$", ""))
    vals = []
    for n in nums:
        v = int(n.replace(",", ""))
        if v > 0:
            vals.append(v)
    if not vals:
        return None
    avg = sum(vals) / len(vals)
    if "hour" in t and avg < 1000:
        avg *= 2080
    elif "month" in t and avg < 50_000:
        avg *= 12
    elif "week" in t and avg < 10_000:
        avg *= 52
    return int(avg)


def parse_relative_date(text: str) -> datetime:
    now = datetime.now(timezone.utc)
    if not text:
        return now
    t = text.lower()
    if any(w in t for w in ("just", "now", "today", "moment")):
        return now
    m = re.search(r"(\d+)\s*(s|m|h|d|w|hour|min|day|week|month)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if unit.startswith("s"):
            return now - timedelta(seconds=n)
        if unit.startswith("m"):
            return now - timedelta(minutes=n) if "min" in t else now - timedelta(days=n * 30)
        if unit.startswith("h"):
            return now - timedelta(hours=n)
        if unit.startswith("d"):
            return now - timedelta(days=n)
        if unit.startswith("w"):
            return now - timedelta(weeks=n)
    return now


class BaseAPIScraper:
    """Base for scrapers that call a REST/JSON API."""
    SOURCE = ""

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._seen_urls: set = set()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": _ua.random,
            "Accept":     "application/json",
        })

    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:6]:   # top 6 titles per source
            try:
                self._fetch_title(title)
                random_delay()
            except Exception as exc:
                logger.error("%s '%s' failed: %s", self.SOURCE, title, exc)
        logger.info("%s: collected %d jobs", self.SOURCE, len(self.jobs))
        return self.jobs

    def _fetch_title(self, title: str):
        raise NotImplementedError

    def _add(self, job: Dict[str, Any]):
        url = job.get("url", "")
        if url and url not in self._seen_urls:
            self._seen_urls.add(url)
            self.jobs.append(job)


class BaseHTMLScraper:
    """Base for scrapers that parse HTML with BeautifulSoup."""
    SOURCE = ""

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._seen_urls: set = set()
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent":      _ua.random,
            "Accept":          "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES[:4]:
            try:
                self._fetch_title(title)
                random_delay()
            except Exception as exc:
                logger.error("%s '%s' failed: %s", self.SOURCE, title, exc)
        logger.info("%s: collected %d jobs", self.SOURCE, len(self.jobs))
        return self.jobs

    def _fetch_title(self, title: str):
        raise NotImplementedError

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            r = self._session.get(
                url, headers=self._headers(), timeout=15, **kwargs
            )
            r.raise_for_status()
            return r
        except Exception as exc:
            logger.warning("%s GET %s failed: %s", self.SOURCE, url[:80], exc)
            return None

    def _add(self, job: Dict[str, Any]):
        url = job.get("url", "")
        if url and url not in self._seen_urls:
            self._seen_urls.add(url)
            self.jobs.append(job)
