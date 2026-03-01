"""
SQLite storage handler.
"""

import logging
import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    salary          INTEGER,
    url             TEXT UNIQUE NOT NULL,
    source          TEXT,
    score           INTEGER DEFAULT 0,
    llm_score       INTEGER,
    llm_reason      TEXT,
    llm_summary     TEXT,
    posted_date     TEXT,
    easy_apply      INTEGER DEFAULT 0,
    applicants      INTEGER,
    description     TEXT,
    job_type        TEXT DEFAULT 'full_time',
    role_category   TEXT DEFAULT 'data_engineer',
    skills          TEXT, -- JSON string
    scraped_at      TEXT,
    notified        INTEGER DEFAULT 0,
    applied         INTEGER DEFAULT 0,
    saved           INTEGER DEFAULT 0,
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_score      ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_scraped_at ON jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_notified   ON jobs(notified);
"""


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._conn = None
        self._init_db()

    def _connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        conn = self._connect()
        conn.executescript(_CREATE_SQL)
        conn.commit()
        logger.debug("Database initialised at %s", self.db_path)

    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Insert or update jobs. Updates scores and metadata but
        preserves 'notified', 'applied', 'saved', and 'notes'.
        """
        conn = self._connect()
        new_count = 0
        for job in jobs:
            try:
                posted = job.get("posted_date")
                if isinstance(posted, datetime):
                    posted = posted.isoformat()

                easy = job.get("easy_apply")
                easy_int = 1 if easy is True else (0 if easy is False else None)

                skills_json = json.dumps(job.get("skills", []))

                # Use ON CONFLICT to update metadata but preserve user state
                cur = conn.execute(
                    """
                    INSERT INTO jobs (
                        title, company, location, salary, url, source, score,
                        llm_score, llm_reason, llm_summary, posted_date,
                        easy_apply, applicants, description, job_type,
                        role_category, skills, scraped_at, notified
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    ON CONFLICT(url) DO UPDATE SET
                        score         = excluded.score,
                        llm_score     = excluded.llm_score,
                        llm_reason    = excluded.llm_reason,
                        llm_summary   = excluded.llm_summary,
                        skills        = excluded.skills,
                        salary        = excluded.salary,
                        applicants    = excluded.applicants,
                        description   = excluded.description,
                        role_category = excluded.role_category,
                        job_type      = excluded.job_type,
                        scraped_at    = excluded.scraped_at
                    """,
                    (
                        job.get("title", ""),
                        job.get("company", ""),
                        job.get("location", ""),
                        job.get("salary"),
                        job.get("url", ""),
                        job.get("source", ""),
                        job.get("score", 0),
                        job.get("llm_score"),
                        job.get("llm_reason"),
                        job.get("llm_summary"),
                        posted,
                        easy_int,
                        job.get("applicants"),
                        job.get("description", ""),
                        job.get("job_type", "full_time"),
                        job.get("role_category", "data_engineer"),
                        skills_json,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                if cur.rowcount > 0 and cur.lastrowid is not None:
                    # SQLite rowcount > 0 for updates too, but we want to know if it's new
                    # Actually rowcount tells us how many rows were affected.
                    # We can use a more precise way to count 'new' if needed.
                    pass
                
                # Check if it was an insert or update
                # In SQLite, if it's an update, rowcount is 1.
                # To distinguish, we'd need to check changes() or similar.
                # For now, let's just count total processed.
            except Exception as exc:
                logger.warning("DB upsert error for '%s': %s", job.get("title"), exc)

        conn.commit()
        # We'll just return the count of successfully processed jobs for now
        return len(jobs)

    def get_unnotified(self, min_score: int = 0) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE notified=0 AND score >= ? ORDER BY score DESC",
            (min_score,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def mark_notified(self, ids: List[int]):
        if not ids:
            return
        conn = self._connect()
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"UPDATE jobs SET notified=1 WHERE id IN ({placeholders})", ids)
        conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("skills"):
            try:
                d["skills"] = json.loads(d["skills"])
            except:
                d["skills"] = []
        return d

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
