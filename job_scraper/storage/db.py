"""
SQLite storage handler.

Table: jobs
  id           INTEGER PRIMARY KEY AUTOINCREMENT
  title        TEXT
  company      TEXT
  location     TEXT
  salary       INTEGER
  url          TEXT UNIQUE
  source       TEXT
  score        INTEGER
  posted_date  TEXT    (ISO-8601)
  easy_apply   INTEGER (0/1)
  applicants   INTEGER
  scraped_at   TEXT    (ISO-8601)
  notified     INTEGER (0/1)
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    company     TEXT,
    location    TEXT,
    salary      INTEGER,
    url         TEXT    UNIQUE,
    source      TEXT,
    score       INTEGER DEFAULT 0,
    posted_date TEXT,
    easy_apply  INTEGER DEFAULT 0,
    applicants  INTEGER,
    scraped_at  TEXT,
    notified    INTEGER DEFAULT 0
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

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Insert or ignore jobs. Returns number of new rows inserted.
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

                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO jobs
                        (title, company, location, salary, url, source, score,
                         posted_date, easy_apply, applicants, scraped_at, notified)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,0)
                    """,
                    (
                        job.get("title", ""),
                        job.get("company", ""),
                        job.get("location", ""),
                        job.get("salary"),
                        job.get("url", ""),
                        job.get("source", ""),
                        job.get("score", 0),
                        posted,
                        easy_int,
                        job.get("applicants"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                if cur.rowcount > 0:
                    new_count += 1
            except Exception as exc:
                logger.warning("DB upsert error for '%s': %s", job.get("title"), exc)

        conn.commit()
        logger.info("DB: %d new jobs saved (out of %d)", new_count, len(jobs))
        return new_count

    # ------------------------------------------------------------------
    def get_unnotified(self, min_score: int = 0) -> List[Dict[str, Any]]:
        """Return jobs that have not been emailed yet, above min_score."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE notified=0 AND score >= ? ORDER BY score DESC",
            (min_score,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def mark_notified(self, ids: List[int]):
        if not ids:
            return
        conn = self._connect()
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"UPDATE jobs SET notified=1 WHERE id IN ({placeholders})", ids)
        conn.commit()
        logger.info("DB: marked %d jobs as notified", len(ids))

    # ------------------------------------------------------------------
    def get_all_above_score(self, min_score: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE score >= ? ORDER BY score DESC",
            (min_score,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
