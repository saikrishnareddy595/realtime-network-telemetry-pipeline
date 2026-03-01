"""
LinkedIn Posts scraper — scrapes LinkedIn *posts* (not job listings) where
people announce openings, share referrals, or say "reach out to me".

Requires: LINKEDIN_EMAIL and LINKEDIN_PASSWORD in config/env.
Uses Playwright in headless mode to log in and search posts.
Uses NVIDIA NIM LLM to extract structured data from unstructured post text.
"""

import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import config

logger = logging.getLogger(__name__)

# Search queries that tend to surface job-related posts
_POST_QUERIES = [
    "data engineer hiring",
    "data engineer opportunity",
    "AI engineer job opening",
    "machine learning engineer referral",
    "data engineer reach out",
    "MLOps engineer we're hiring",
    "data engineer DM me",
    "data pipeline engineer openings",
    "LLM engineer hiring",
    "generative AI engineer job",
]


class LinkedInPostsScraper:
    SOURCE = "LinkedInPosts"

    def __init__(self):
        self.posts: List[Dict[str, Any]] = []
        self._seen_urls: set = set()

    def scrape(self) -> List[Dict[str, Any]]:
        if not config.LINKEDIN_EMAIL or not config.LINKEDIN_PASSWORD:
            logger.info("LinkedIn Posts: skipped (no credentials configured)")
            return []
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed")
            return []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=config.HEADLESS_BROWSER)
            ctx     = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                )
            )
            page = ctx.new_page()
            try:
                if not self._login(page):
                    return []
                for query in _POST_QUERIES[:6]:  # limit to 6 queries per run
                    try:
                        self._search_posts(page, query)
                        time.sleep(random.uniform(3, 6))
                    except Exception as exc:
                        logger.warning("LinkedIn post query '%s' failed: %s", query, exc)
            finally:
                browser.close()

        logger.info("LinkedIn Posts: collected %d posts", len(self.posts))
        return self.posts

    # ── Login ─────────────────────────────────────────────────────────────────
    def _login(self, page) -> bool:
        try:
            page.goto("https://www.linkedin.com/login", timeout=30_000)
            page.fill("#username", config.LINKEDIN_EMAIL)
            page.fill("#password", config.LINKEDIN_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_timeout(4000)
            if "feed" in page.url or "checkpoint" not in page.url:
                logger.info("LinkedIn Posts: logged in successfully")
                return True
            logger.warning("LinkedIn login may require 2FA / CAPTCHA — posts skipped")
            return False
        except Exception as exc:
            logger.error("LinkedIn login failed: %s", exc)
            return False

    # ── Search posts ──────────────────────────────────────────────────────────
    def _search_posts(self, page, query: str):
        from urllib.parse import quote_plus
        url = (
            f"https://www.linkedin.com/search/results/content/"
            f"?keywords={quote_plus(query)}&sortBy=date_posted"
        )
        page.goto(url, timeout=30_000)
        page.wait_for_timeout(3000)

        # Scroll to load more posts
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        # Grab all post containers
        cards = page.query_selector_all(
            "div.feed-shared-update-v2, div[data-urn*='urn:li:activity']"
        )
        logger.debug("LinkedIn Posts query '%s': %d raw cards", query, len(cards))

        for card in cards[:20]:
            try:
                post = self._extract_post(card)
                if post and post.get("post_url","") not in self._seen_urls:
                    self._seen_urls.add(post.get("post_url",""))
                    self.posts.append(post)
            except Exception as exc:
                logger.debug("Post parse error: %s", exc)

    # ── Extract a single post ─────────────────────────────────────────────────
    def _extract_post(self, card) -> Dict[str, Any]:
        # Text content
        text_el = card.query_selector("span.break-words, div.feed-shared-text")
        post_text = text_el.inner_text() if text_el else ""
        if not post_text or len(post_text) < 50:
            return {}

        # Author name
        author_el = card.query_selector(
            "span.feed-shared-actor__name, a.app-aware-link span[aria-hidden='true']"
        )
        author_name = author_el.inner_text().strip() if author_el else ""

        # Author headline
        headline_el = card.query_selector(
            "span.feed-shared-actor__description"
        )
        author_headline = headline_el.inner_text().strip() if headline_el else ""

        # Author profile URL
        profile_el = card.query_selector("a.app-aware-link[href*='/in/']")
        author_profile = profile_el.get_attribute("href") if profile_el else ""
        if author_profile and not author_profile.startswith("http"):
            author_profile = "https://www.linkedin.com" + author_profile

        # Post URL
        time_el  = card.query_selector("a[href*='/feed/update/']")
        post_url = time_el.get_attribute("href") if time_el else ""
        if post_url and not post_url.startswith("http"):
            post_url = "https://www.linkedin.com" + post_url

        # Approximate posted date (LinkedIn uses relative times)
        time_text_el = card.query_selector(
            "span.feed-shared-actor__sub-description"
        )
        posted_date = datetime.now(timezone.utc)  # fallback; LI posts are fresh

        # Extract contact email from post text
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", post_text)
        contact_email = emails[0] if emails else ""

        # Use NVIDIA NIM to parse the post
        llm_data: Dict[str, Any] = {}
        if config.LLM_ENABLED:
            from engine.llm import parse_linkedin_post
            llm_data = parse_linkedin_post(post_text, author_name) or {}

        is_job = llm_data.get("is_job_posting", self._looks_like_job(post_text))
        if not is_job:
            return {}

        return {
            "post_text":          post_text[:2000],
            "author_name":        author_name,
            "author_headline":    author_headline,
            "author_profile_url": author_profile,
            "extracted_title":    llm_data.get("job_title", ""),
            "extracted_company":  llm_data.get("company", ""),
            "contact_email":      contact_email or llm_data.get("contact_email", ""),
            "contact_linkedin":   llm_data.get("contact_linkedin", author_profile),
            "contact_name":       llm_data.get("contact_name", author_name),
            "post_url":           post_url,
            "posted_date":        posted_date,
            "is_job_posting":     True,
            "score":              llm_data.get("score", 40),
            "role_category":      llm_data.get("role_category", "data_engineer"),
        }

    # ── Fallback keyword check ────────────────────────────────────────────────
    @staticmethod
    def _looks_like_job(text: str) -> bool:
        text_lower = text.lower()
        triggers = [
            "we're hiring", "we are hiring", "looking for a", "open position",
            "job opening", "reach out", "dm me", "send resume", "send your cv",
            "apply now", "referral", "opportunity", "we need a", "join our team",
            "contact me", "email me", "#hiring", "#datajobs", "#aiengineerjobs",
        ]
        return any(t in text_lower for t in triggers)
