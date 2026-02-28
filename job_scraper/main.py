"""
main.py — Orchestrator for the automated job scraping system.

Pipeline:
  1. Run all scrapers (JobSpy → LinkedIn/Indeed/Glassdoor/ZipRecruiter/Google,
     Dice, RemoteOK, Arbeitnow, Adzuna)
  2. Deduplicate across sources
  3. Filter (salary, keywords, age)
  4. Score (0–100)
  5. Save to SQLite
  6. Sync high-score jobs to Google Sheets
  7. Send Gmail HTML digest alert

Run once: python main.py
Schedule: GitHub Actions (every 6 hours)
"""

import logging
import sys
import time
import os
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any

# ── Make sure imports resolve regardless of CWD ───────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

import config
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.dice           import DiceScraper
from scrapers.remoteok       import RemoteOKScraper
from scrapers.arbeitnow      import ArbeitnowScraper
from scrapers.adzuna         import AdzunaScraper

from engine.deduplicator  import Deduplicator
from engine.scorer        import Scorer
from engine.filter        import Filter

from storage.db           import Database
from output.sheets        import SheetsSync
from output.notifier      import Notifier

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "scraper.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("main")


# ── Scraper registry ──────────────────────────────────────────────────────────
# JobSpy covers LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google in one call.
# Dice, RemoteOK, Arbeitnow are separate reliable sources.
# Adzuna requires API keys (skipped gracefully if not set).
SCRAPERS = [
    ("JobSpy",    JobSpyScraper),
    ("Dice",      DiceScraper),
    ("RemoteOK",  RemoteOKScraper),
    ("Arbeitnow", ArbeitnowScraper),
    ("Adzuna",    AdzunaScraper),
]


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run() -> None:
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Job Scraper starting — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # Step 1 — Collect jobs from all scrapers
    all_jobs: List[Dict[str, Any]] = []
    per_source: Dict[str, int] = defaultdict(int)

    for name, ScraperClass in SCRAPERS:
        logger.info("── Scraping %s …", name)
        try:
            scraper = ScraperClass()
            jobs = scraper.scrape()
            per_source[name] = len(jobs)
            all_jobs.extend(jobs)
            logger.info("   %s: %d jobs collected", name, len(jobs))
        except Exception as exc:
            logger.error("   %s FAILED: %s", name, exc)
            per_source[name] = 0

    logger.info("Total raw jobs: %d", len(all_jobs))

    # Step 2 — Deduplicate
    deduplicator = Deduplicator()
    unique_jobs  = deduplicator.deduplicate(all_jobs)
    logger.info("After deduplication: %d jobs", len(unique_jobs))

    # Step 3 — Filter
    job_filter    = Filter()
    filtered_jobs = job_filter.filter(unique_jobs)
    logger.info("After filtering: %d jobs", len(filtered_jobs))

    # Step 4 — Score
    scorer       = Scorer()
    scored_jobs  = scorer.score_all(filtered_jobs)
    logger.info("Scoring complete — top score: %d", scored_jobs[0]["score"] if scored_jobs else 0)

    # Step 5 — Save to SQLite
    db = Database()
    new_count = db.upsert_jobs(scored_jobs)
    logger.info("Saved %d new jobs to database", new_count)

    # Step 6 — Sync high-score jobs to Google Sheets
    high_score_jobs = [j for j in scored_jobs if j.get("score", 0) >= config.ALERT_SCORE_THRESHOLD]
    sheets = SheetsSync()
    rows_written = sheets.sync(high_score_jobs)
    logger.info("Google Sheets: %d rows written", rows_written)

    # Step 7 — Gmail digest for unnotified jobs above threshold
    unnotified = db.get_unnotified(min_score=config.ALERT_SCORE_THRESHOLD)
    if unnotified:
        notifier = Notifier()
        sent = notifier.send_digest(unnotified)
        if sent:
            db.mark_notified([j["id"] for j in unnotified])
    else:
        logger.info("No new jobs above score threshold to notify about")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("  JOB SCRAPER SUMMARY")
    print("=" * 60)
    print(f"  {'Source':<15} {'Jobs Found':>10}")
    print(f"  {'-'*15} {'-'*10}")
    for name, count in per_source.items():
        print(f"  {name:<15} {count:>10}")
    print(f"  {'-'*15} {'-'*10}")
    print(f"  {'TOTAL RAW':<15} {len(all_jobs):>10}")
    print(f"  {'After dedup':<15} {len(unique_jobs):>10}")
    print(f"  {'After filter':<15} {len(filtered_jobs):>10}")
    print(f"  {'New in DB':<15} {new_count:>10}")
    print(f"  {'Sheets synced':<15} {rows_written:>10}")
    print(f"  {'Emails sent':<15} {'1' if unnotified else '0':>10}")
    print()
    print(f"  TOP 5 JOBS:")
    print(f"  {'Score':<6} {'Title':<35} {'Company':<20}")
    print(f"  {'-'*6} {'-'*35} {'-'*20}")
    for job in scored_jobs[:5]:
        title   = (job.get("title") or "")[:34]
        company = (job.get("company") or "")[:19]
        score   = job.get("score", 0)
        print(f"  {score:<6} {title:<35} {company:<20}")
    print("=" * 60)
    print(f"  Completed in {elapsed:.1f}s")
    print("=" * 60 + "\n")

    db.close()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()
