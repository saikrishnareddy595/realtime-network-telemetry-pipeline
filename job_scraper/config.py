"""
Central configuration for the Job Scraping System.
All user-facing settings are pre-filled here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Search Parameters ──────────────────────────────────────────────────────────
JOB_TITLES = [
    "Data Engineer",
    "Data Engineering",
    "ETL Engineer",
    "Pipeline Engineer",
]

LOCATIONS = ["United States", "Remote USA", "Remote"]

MIN_SALARY = 80_000  # USD / year

WORK_TYPES = ["on-site", "remote", "hybrid"]  # include all

INCLUDE_KEYWORDS = [
    "data pipeline",
    "ETL",
    "Spark",
    "Kafka",
    "Airflow",
    "dbt",
    "SQL",
    "Python",
    "cloud",
    "AWS",
    "GCP",
    "Azure",
    "data warehouse",
]

EXCLUDE_KEYWORDS = [
    "unpaid",
    "10+ years",
    "principal",
    "staff engineer",
]

DREAM_COMPANIES = [
    "Google",
    "Amazon",
    "AWS",
    "Microsoft",
    "Azure",
    "Meta",
    "Facebook",
]

MAX_JOB_AGE_HOURS = 72
MAX_APPLICANTS = 100
EASY_APPLY_ONLY = False  # include all application types

# ── Scoring Thresholds ─────────────────────────────────────────────────────────
ALERT_SCORE_THRESHOLD = 65

# ── Gmail / Alerts ─────────────────────────────────────────────────────────────
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "reddamgufus21188@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_RECIPIENT = "reddamgufus21188@gmail.com"

# ── Google Sheets ──────────────────────────────────────────────────────────────
GOOGLE_SHEET_NAME = "Data Engineer Job Search 2025"
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"
)

# ── Optional API Keys ──────────────────────────────────────────────────────────
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY", "")

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

# ── Scraper Behaviour ──────────────────────────────────────────────────────────
REQUEST_DELAY_MIN = 2.0   # seconds
REQUEST_DELAY_MAX = 5.0   # seconds
HEADLESS_BROWSER = True
PLAYWRIGHT_TIMEOUT = 30_000  # ms

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
