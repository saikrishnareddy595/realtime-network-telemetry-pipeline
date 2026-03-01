"""
hackernews.py — Scrapes the monthly Hacker News "Who's Hiring?" threads.

These are posted on the first weekday of each month by the HN team.
We fetch the top-level story via the Algolia HN API, then parse
comment text for relevant job postings.

No API key required.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from html import unescape

import requests

import config

logger = logging.getLogger(__name__)

_ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
_ALGOLIA_ITEM = "https://hn.algolia.com/api/v1/items/{}"

# Keywords that suggest a data/AI engineering role
_RELEVANT_KW = [
    "data engineer", "machine learning", "ml engineer", "ai engineer",
    "llm", "generative ai", "data pipeline", "etl", "data scientist",
    "mlops", "nlp engineer", "computer vision", "data platform",
    "spark", "kafka", "airflow", "dbt", "snowflake", "databricks",
]

# Signals that a comment is a job post (not a seeker or meta)
_JOB_POST_SIGNALS = [
    "we're hiring", "we are hiring", "we're looking", "we are looking",
    "join us", "join our team", "we need", "apply at", "apply via",
    "|", "remote", "onsite", "full-time", "contract",
]


class HackerNewsHiringScraper:
    SOURCE = "HackerNews"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "JobScraper/2.0 (github job aggregator)"

    def scrape(self) -> List[Dict[str, Any]]:
        story_id = self._find_whos_hiring_story()
        if not story_id:
            logger.warning("HackerNews: could not find current Who's Hiring thread")
            return []

        logger.info("HackerNews: parsing thread %d", story_id)
        comments = self._fetch_comments(story_id)
        jobs = []
        for comment in comments:
            job = self._parse_comment(comment)
            if job:
                jobs.append(job)

        logger.info("HackerNews: extracted %d relevant job comments", len(jobs))
        return jobs

    # ── Thread discovery ──────────────────────────────────────────────────────

    def _find_whos_hiring_story(self) -> Optional[int]:
        """Find the most recent 'Ask HN: Who is hiring?' story."""
        try:
            resp = self._session.get(
                _ALGOLIA_SEARCH,
                params={
                    "query": "Ask HN: Who is hiring?",
                    "tags": "story,ask_hn",
                    "hitsPerPage": 5,
                },
                timeout=10,
            )
            data = resp.json()
            hits = data.get("hits", [])
            if hits:
                return int(hits[0]["objectID"])
        except Exception as exc:
            logger.error("HackerNews: story search failed: %s", exc)
        return None

    # ── Comment fetching ──────────────────────────────────────────────────────

    def _fetch_comments(self, story_id: int) -> List[Dict[str, Any]]:
        """Fetch top-level comments (job posts) from the story."""
        try:
            resp = self._session.get(_ALGOLIA_ITEM.format(story_id), timeout=15)
            data = resp.json()
            return data.get("children", [])
        except Exception as exc:
            logger.error("HackerNews: comment fetch failed for %d: %s", story_id, exc)
            return []

    # ── Comment → job dict ────────────────────────────────────────────────────

    def _parse_comment(self, comment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to extract a job posting from a HN comment dict."""
        text_raw = comment.get("text") or ""
        if not text_raw or len(text_raw) < 80:
            return None

        # Unescape HTML entities and strip tags
        text = unescape(re.sub(r"<[^>]+>", " ", text_raw)).strip()

        # Check relevance
        text_lower = text.lower()
        if not any(kw in text_lower for kw in _RELEVANT_KW):
            return None
        if not any(sig in text_lower for sig in _JOB_POST_SIGNALS):
            return None

        # Extract structured fields from typical HN hiring format:
        # "Company | Role | Location | Remote/Onsite | URL | Description"
        title, company, location, url = self._extract_fields(text)

        # Extract contact email if present
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        contact_email = emails[0] if emails else ""

        # Detect job type
        job_type = "full_time"
        if re.search(r"\bcontract\b|\b1099\b|\bc2c\b", text_lower):
            job_type = "contract"
        elif re.search(r"part.?time", text_lower):
            job_type = "part_time"

        # Detect work type
        is_remote = bool(re.search(r"\bremote\b", text_lower))

        comment_id = comment.get("objectID") or comment.get("id", "")
        post_url = f"https://news.ycombinator.com/item?id={comment_id}" if comment_id else ""

        return {
            "title":       title or "Software Engineer (Data/AI)",
            "company":     company or "Unknown Company (HN)",
            "location":    ("Remote" if is_remote else location) or "USA",
            "url":         url or post_url,
            "source":      self.SOURCE,
            "description": text[:3000],
            "posted_date": datetime.now(timezone.utc),
            "job_type":    job_type,
            "easy_apply":  False,
            "contact_email": contact_email,
            "salary":      self._extract_salary(text),
        }

    # ── Field extractors ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_fields(text: str):
        """Parse pipe-delimited HN format: Company | Role | Location | ..."""
        parts = [p.strip() for p in text.split("|")]
        company  = parts[0] if len(parts) > 0 else ""
        title    = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""

        # Extract URL
        url_match = re.search(r"https?://\S+", text)
        url = url_match.group(0).rstrip(".,)>") if url_match else ""

        # If first segment is very long, likely no pipe format
        if len(company) > 60:
            company = ""
        if len(title) > 80:
            title = ""

        return title, company, location, url

    @staticmethod
    def _extract_salary(text: str) -> Optional[int]:
        """Try to parse a salary figure from comment text."""
        # e.g. "$120k", "$150,000", "120k-150k"
        m = re.search(r"\$(\d{2,3})k", text, re.IGNORECASE)
        if m:
            return int(m.group(1)) * 1000
        m = re.search(r"\$(\d{3},?\d{3})", text)
        if m:
            return int(m.group(1).replace(",", ""))
        return None
