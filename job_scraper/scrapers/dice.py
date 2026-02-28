"""
Dice scraper — tech-focused job board with JSON API.
Dice has a public search endpoint that returns JSON results.
"""

import logging
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from urllib.parse import quote_plus

import requests
from fake_useragent import UserAgent

import config

logger = logging.getLogger(__name__)
ua = UserAgent()


class DiceScraper:
    SOURCE = "Dice"

    # Dice public search API
    _API_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self._session = requests.Session()

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        for title in config.JOB_TITLES:
            try:
                self._fetch_title(title)
                time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
            except Exception as exc:
                logger.error("Dice '%s' failed: %s", title, exc)
        logger.info("Dice: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _fetch_title(self, title: str, pages: int = 5):
        headers = {
            "User-Agent":    ua.random,
            "Accept":        "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer":       "https://www.dice.com/",
            "Origin":        "https://www.dice.com",
            "x-api-key":     "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",  # public key
        }

        for page in range(1, pages + 1):
            params = {
                "q":            title,
                "countryCode2": "US",
                "radius":       "30",
                "radiusUnit":   "mi",
                "page":         page,
                "pageSize":     20,
                "facets":       "employmentType|postedDate|workFromHomeAvailability|employerType|easyApply|isRemote",
                "date":         "THREE",      # last 3 days
                "fields":       "id|jobId|guid|summary|title|postedDate|modifiedDate|jobLocation.displayName|detailsPageUrl|salary|clientBrandId|companyPageUrl|companyLogoUrl|positionId|companyName|employmentType|isHighlighted|score|easyApply|employerType|workFromHomeAvailability|isRemote|debug",
                "culture":      "en",
                "recommendations": "true",
                "interactionId": "0",
                "fj":           "true",
            }

            try:
                resp = self._session.get(self._API_URL, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("data", []):
                    job = self._parse_item(item)
                    if job:
                        self.jobs.append(job)
                logger.debug("Dice '%s' page %d: %d items", title, page, len(data.get("data", [])))
                time.sleep(random.uniform(1, 2))
            except Exception as exc:
                logger.warning("Dice page %d failed: %s", page, exc)

    # ------------------------------------------------------------------
    def _parse_item(self, item: dict) -> Dict[str, Any]:
        title    = item.get("title", "")
        company  = item.get("companyName", "")
        location = ""
        loc_obj  = item.get("jobLocation")
        if isinstance(loc_obj, dict):
            location = loc_obj.get("displayName", "")
        elif isinstance(loc_obj, list) and loc_obj:
            location = loc_obj[0].get("displayName", "")

        url       = item.get("detailsPageUrl", "")
        easy_apply = item.get("easyApply", False)
        is_remote  = item.get("isRemote", False)

        salary_text = item.get("salary", "")
        salary = self._parse_salary(salary_text)

        posted_raw = item.get("postedDate", "")
        posted_date = datetime.now(timezone.utc)
        if posted_raw:
            try:
                posted_date = datetime.fromisoformat(
                    posted_raw.rstrip("Z")
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        if not title:
            return {}

        if is_remote and not location:
            location = "Remote"

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "url":         url,
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  easy_apply,
            "applicants":  None,
            "description": item.get("summary", "")[:500],
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
        return int(avg)
