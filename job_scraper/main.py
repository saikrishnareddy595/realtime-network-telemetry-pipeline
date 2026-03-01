"""
main.py — Orchestrator for the automated job scraping system.

Pipeline:
  1. Run all 50 scrapers in parallel (ThreadPoolExecutor)
  2. Deduplicate (exact hash + NVIDIA NIM semantic embeddings)
  3. Filter  (salary, keywords, age, applicants, job_type)
  4. Score   (multi-factor heuristic)
  5. LLM enrich (NVIDIA NIM — score, summary, skill extraction)
  6. Save to SQLite (local) + Supabase (persistent across runs)
  7. Sync high-score jobs to Google Sheets
  8. Send Gmail HTML digest alert
  9. Scrape LinkedIn posts (separate stream → Supabase)

Run once : python main.py
Schedule : GitHub Actions every 6 hours
"""

import logging
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import config

# ── Logging ────────────────────────────────────────────────────────────────────
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

# ── Scraper imports ────────────────────────────────────────────────────────────
from scrapers.jobspy_scraper   import JobSpyScraper
from scrapers.dice             import DiceScraper
from scrapers.remoteok         import RemoteOKScraper
from scrapers.arbeitnow        import ArbeitnowScraper
from scrapers.adzuna           import AdzunaScraper
from scrapers.remotive         import RemotiveScraper
from scrapers.himalayas        import HimalayasScraper
from scrapers.jobicy           import JobicyScraper
from scrapers.themuse          import TheMuseScraper
from scrapers.usajobs          import USAJobsScraper
from scrapers.jooble           import JoobleScraper
from scrapers.workingnomads    import WorkingNomadsScraper
from scrapers.careerbuilder    import CareerBuilderScraper
from scrapers.monster          import MonsterScraper
from scrapers.builtin          import BuiltInScraper
from scrapers.techfetch        import TechFetchScraper
from scrapers.clearancejobs    import ClearanceJobsScraper
from scrapers.wellfound        import WellfoundScraper
from scrapers.weworkremotely   import WeWorkRemotelyScraper
from scrapers.staffing_scrapers import (
    TEKsystemsScraper, KforceScraper, RobertHalfScraper, RandstadScraper,
    InsightGlobalScraper, ApexSystemsScraper, MotionRecruitmentScraper,
    CyberCodersScraper, Akkodiscraper, VoltScraper, HarveyNashScraper,
    HaysTechScraper, LanceSoftScraper, StaffmarkScraper, BeaconHillScraper,
    CognizantScraper, InfosysScraper, SAICScraper, LeidosScraper,
    BoozAllenScraper, AccentureScraper, CapgeminiScraper, IBMScraper,
)
from scrapers.linkedin_posts   import LinkedInPostsScraper

from engine.deduplicator import Deduplicator
from engine.scorer       import Scorer
from engine.filter       import Filter
from engine.llm          import llm_score_batch

from storage.db              import Database
from storage.supabase_client import SupabaseClient
from output.sheets           import SheetsSync
from output.notifier         import Notifier

# ── Scraper registry ───────────────────────────────────────────────────────────
JOB_SCRAPERS: List[Tuple[str, type]] = [
    # Tier 1 — Free APIs
    ("JobSpy",          JobSpyScraper),
    ("Dice",            DiceScraper),
    ("RemoteOK",        RemoteOKScraper),
    ("Arbeitnow",       ArbeitnowScraper),
    ("Remotive",        RemotiveScraper),
    ("Himalayas",       HimalayasScraper),
    ("Jobicy",          JobicyScraper),
    ("TheMuse",         TheMuseScraper),
    ("USAJobs",         USAJobsScraper),
    ("Jooble",          JoobleScraper),
    ("WorkingNomads",   WorkingNomadsScraper),
    ("Adzuna",          AdzunaScraper),
    # Tier 2 — HTML scrapers
    ("CareerBuilder",   CareerBuilderScraper),
    ("Monster",         MonsterScraper),
    ("BuiltIn",         BuiltInScraper),
    ("TechFetch",       TechFetchScraper),
    ("ClearanceJobs",   ClearanceJobsScraper),
    ("Wellfound",       WellfoundScraper),
    ("WeWorkRemotely",  WeWorkRemotelyScraper),
    # Tier 3 — Staffing / Prime Vendor
    ("TEKsystems",      TEKsystemsScraper),
    ("Kforce",          KforceScraper),
    ("RobertHalf",      RobertHalfScraper),
    ("Randstad",        RandstadScraper),
    ("InsightGlobal",   InsightGlobalScraper),
    ("ApexSystems",     ApexSystemsScraper),
    ("MotionRecruit",   MotionRecruitmentScraper),
    ("CyberCoders",     CyberCodersScraper),
    ("Akkodis",         Akkodiscraper),
    ("Volt",            VoltScraper),
    ("HarveyNash",      HarveyNashScraper),
    ("HaysTech",        HaysTechScraper),
    ("LanceSoft",       LanceSoftScraper),
    ("Staffmark",       StaffmarkScraper),
    ("BeaconHill",      BeaconHillScraper),
    # Tier 4 — Consulting / Federal
    ("Cognizant",       CognizantScraper),
    ("Infosys",         InfosysScraper),
    ("SAIC",            SAICScraper),
    ("Leidos",          LeidosScraper),
    ("BoozAllen",       BoozAllenScraper),
    ("Accenture",       AccentureScraper),
    ("Capgemini",       CapgeminiScraper),
    ("IBM",             IBMScraper),
]


def _run_scraper(name: str, ScraperClass: type) -> Tuple[str, List[Dict[str, Any]]]:
    try:
        jobs = ScraperClass().scrape()
        logger.info("  ✓ %-20s %d jobs", name, len(jobs))
        return name, jobs
    except Exception as exc:
        logger.error("  ✗ %-20s FAILED: %s", name, exc)
        return name, []


def run() -> None:
    t0 = time.time()
    logger.info("=" * 65)
    logger.info("Job Scraper starting — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("LLM enabled: %s | Supabase: %s", config.LLM_ENABLED, bool(config.SUPABASE_URL))
    logger.info("=" * 65)

    supabase = SupabaseClient()

    # ── Step 1: Parallel scraping ──────────────────────────────────────────────
    all_jobs: List[Dict[str, Any]] = []
    per_source: Dict[str, int]     = defaultdict(int)

    logger.info("Running %d scrapers with %d workers …", len(JOB_SCRAPERS), config.MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        futures = {
            pool.submit(_run_scraper, name, cls): name
            for name, cls in JOB_SCRAPERS
        }
        for fut in as_completed(futures):
            name, jobs = fut.result()
            per_source[name] = len(jobs)
            all_jobs.extend(jobs)

    logger.info("Total raw jobs collected: %d", len(all_jobs))

    # ── Step 2: Deduplicate ────────────────────────────────────────────────────
    unique_jobs = Deduplicator().deduplicate(all_jobs)

    # ── Step 3: Filter ────────────────────────────────────────────────────────
    filtered_jobs = Filter().filter(unique_jobs)

    # ── Step 4: Heuristic Score ───────────────────────────────────────────────
    scored_jobs = Scorer().score_all(filtered_jobs)

    # ── Step 5: LLM Enrichment (NVIDIA NIM) ──────────────────────────────────
    if config.LLM_ENABLED:
        scored_jobs = llm_score_batch(scored_jobs, max_jobs=150)

    # ── Step 6: Save ──────────────────────────────────────────────────────────
    db        = Database()
    new_count = db.upsert_jobs(scored_jobs)
    logger.info("SQLite: %d new jobs saved", new_count)

    supabase.upsert_jobs(scored_jobs)

    # ── Step 7: Google Sheets ─────────────────────────────────────────────────
    high_score = [j for j in scored_jobs if j.get("score", 0) >= config.ALERT_SCORE_THRESHOLD]
    rows_written = SheetsSync().sync(high_score)
    logger.info("Google Sheets: %d rows written", rows_written)

    # ── Step 8: Gmail digest ──────────────────────────────────────────────────
    unnotified = db.get_unnotified(min_score=config.ALERT_SCORE_THRESHOLD)
    if unnotified:
        sent = Notifier().send_digest(unnotified)
        if sent:
            db.mark_notified([j["id"] for j in unnotified])
    else:
        logger.info("No new jobs above threshold to notify about")

    # ── Step 9: LinkedIn Posts (separate stream) ───────────────────────────────
    posts: List[Dict[str, Any]] = []
    if config.LINKEDIN_EMAIL:
        logger.info("Scraping LinkedIn posts …")
        posts = LinkedInPostsScraper().scrape()
        supabase.upsert_posts(posts)
        logger.info("LinkedIn Posts: %d new posts pushed to Supabase", len(posts))

    db.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'='*65}")
    print("  JOB SCRAPER SUMMARY")
    print(f"{'='*65}")
    print(f"  {'Source':<20} {'Jobs':>6}")
    print(f"  {'-'*20} {'-'*6}")
    for name, count in sorted(per_source.items()):
        print(f"  {name:<20} {count:>6}")
    print(f"  {'-'*20} {'-'*6}")
    print(f"  {'TOTAL RAW':<20} {len(all_jobs):>6}")
    print(f"  {'After dedup':<20} {len(unique_jobs):>6}")
    print(f"  {'After filter':<20} {len(filtered_jobs):>6}")
    print(f"  {'New in SQLite':<20} {new_count:>6}")
    print(f"  {'Sheets rows':<20} {rows_written:>6}")
    print(f"  {'LinkedIn Posts':<20} {len(posts):>6}")
    print()
    print(f"  TOP 10 JOBS:")
    print(f"  {'Sc':>3} {'LLM':>3}  {'Title':<35} {'Company':<20} {'Type':<10}")
    print(f"  {'--':>3} {'---':>3}  {'-'*35} {'-'*20} {'-'*10}")
    for job in scored_jobs[:10]:
        print(
            f"  {job.get('score',0):>3} "
            f"{str(job.get('llm_score') or ''):>3}  "
            f"{(job.get('title') or '')[:34]:<35} "
            f"{(job.get('company') or '')[:19]:<20} "
            f"{job.get('job_type',''):<10}"
        )
    print(f"{'='*65}")
    print(f"  Completed in {elapsed:.1f}s")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run()
