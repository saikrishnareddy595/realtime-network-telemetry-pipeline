"""
LinkedIn scraper — uses Playwright with playwright-stealth to avoid bot detection.
Searches for Data Engineer roles posted in the last 72 hours.
"""

import logging
import random
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)


class LinkedInScraper:
    SOURCE = "LinkedIn"

    # LinkedIn date-filter codes
    _TIME_FILTER = "r259200"  # 72 hours = 259200 seconds

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def scrape(self) -> List[Dict[str, Any]]:
        """Main entry point — returns list of job dicts."""
        try:
            from playwright.sync_api import sync_playwright
            try:
                from playwright_stealth import stealth_sync
                _has_stealth = True
            except ImportError:
                _has_stealth = False
                logger.warning("playwright-stealth not available; proceeding without it")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=config.HEADLESS_BROWSER)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/121.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                )
                page = context.new_page()
                if _has_stealth:
                    stealth_sync(page)

                for title in config.JOB_TITLES[:2]:  # cap to avoid overload
                    self._scrape_title(page, title)
                    time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))

                browser.close()

        except Exception as exc:
            logger.error("LinkedIn scraper failed: %s", exc)

        logger.info("LinkedIn: collected %d jobs", len(self.jobs))
        return self.jobs

    # ------------------------------------------------------------------
    def _scrape_title(self, page, title: str):
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={title.replace(' ', '%20')}"
            f"&location=United%20States"
            f"&f_TPR={self._TIME_FILTER}"
            f"&f_WT=1%2C2%2C3"  # on-site, remote, hybrid
            f"&redirect=false&position=1&pageNum=0"
        )
        try:
            page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT)
            page.wait_for_timeout(random.randint(2000, 4000))

            # Scroll to load more cards
            for _ in range(3):
                page.keyboard.press("End")
                page.wait_for_timeout(1500)

            cards = page.query_selector_all("div.base-card")
            logger.info("LinkedIn '%s': found %d cards", title, len(cards))

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job:
                        self.jobs.append(job)
                except Exception as e:
                    logger.debug("Card parse error: %s", e)

        except Exception as exc:
            logger.error("LinkedIn page load failed for '%s': %s", title, exc)

    # ------------------------------------------------------------------
    def _parse_card(self, card) -> Dict[str, Any]:
        def _text(sel):
            el = card.query_selector(sel)
            return el.inner_text().strip() if el else ""

        def _attr(sel, attr):
            el = card.query_selector(sel)
            return el.get_attribute(attr) if el else ""

        job_title = _text("h3.base-search-card__title")
        company   = _text("h4.base-search-card__subtitle")
        location  = _text("span.job-search-card__location")
        url       = _attr("a.base-card__full-link", "href") or _attr("a", "href")
        listed_at = _attr("time", "datetime")  # e.g. "2024-01-15"

        if not job_title:
            return {}

        posted_date = None
        if listed_at:
            try:
                posted_date = datetime.fromisoformat(listed_at).replace(tzinfo=timezone.utc)
            except ValueError:
                posted_date = datetime.now(timezone.utc)

        return {
            "title":       job_title,
            "company":     company,
            "location":    location,
            "salary":      None,
            "url":         url.split("?")[0] if url else "",
            "source":      self.SOURCE,
            "posted_date": posted_date,
            "easy_apply":  None,
            "applicants":  None,
            "description": "",
        }
