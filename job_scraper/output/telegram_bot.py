"""
telegram_bot.py — Sends instant Telegram alerts for:
  1. High-score job listings (score >= ALERT_SCORE_THRESHOLD)
  2. LinkedIn recruiter posts with contact email extracted

Uses the Telegram Bot API (no library needed — pure requests).

Setup:
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Message your bot once, then visit:
     https://api.telegram.org/bot<TOKEN>/getUpdates
     to find your CHAT_ID
  3. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env / GitHub Secrets
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

import config

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot"
_MAX_RETRIES = 3
_RETRY_DELAY = 2  # seconds


class TelegramBot:
    def __init__(self):
        self._token = config.TELEGRAM_BOT_TOKEN
        self._chat_id = config.TELEGRAM_CHAT_ID
        self._enabled = bool(self._token and self._chat_id)
        if not self._enabled:
            logger.info("Telegram: not configured (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")

    # ── Public API ────────────────────────────────────────────────────────────

    def send_job_alerts(self, jobs: List[Dict[str, Any]]) -> int:
        """Send one message per high-score job. Returns count sent."""
        if not self._enabled or not jobs:
            return 0
        sent = 0
        # sort by combined score descending, cap at 15 per run to avoid spam
        top = sorted(jobs, key=lambda j: (j.get("llm_score") or 0) + j.get("score", 0), reverse=True)[:15]
        for job in top:
            msg = self._format_job(job)
            if self._send(msg):
                sent += 1
                time.sleep(0.4)  # respect Telegram rate limit (30 msg/sec)
        logger.info("Telegram: sent %d job alerts", sent)
        return sent

    def send_recruiter_posts(self, posts: List[Dict[str, Any]]) -> int:
        """Send LinkedIn recruiter posts (especially those with contact emails). Returns count sent."""
        if not self._enabled or not posts:
            return 0
        sent = 0
        # Prioritise posts with email contacts and high score
        sorted_posts = sorted(
            posts,
            key=lambda p: (bool(p.get("contact_email")), p.get("score", 0)),
            reverse=True,
        )[:20]
        for post in sorted_posts:
            msg = self._format_post(post)
            if self._send(msg):
                sent += 1
                time.sleep(0.4)
        logger.info("Telegram: sent %d LinkedIn recruiter posts", sent)
        return sent

    def send_digest_summary(self, total_raw: int, total_after_filter: int,
                             new_in_db: int, top_jobs: List[Dict[str, Any]]) -> bool:
        """Send a short run-summary message after each scraper run."""
        if not self._enabled:
            return False
        lines = [
            "🤖 *JobScraper Run Complete*",
            f"📦 Raw collected: `{total_raw}`",
            f"✅ After filter:  `{total_after_filter}`",
            f"🆕 New in DB:     `{new_in_db}`",
            "",
            "🏆 *Top 5 This Run:*",
        ]
        for i, job in enumerate(top_jobs[:5], 1):
            score = job.get("score", 0)
            llm = job.get("llm_score") or ""
            title = self._esc(job.get("title", ""))
            company = self._esc(job.get("company", ""))
            lines.append(f"{i}\\. `{score}` [{title} @ {company}]({job.get('url', '')})")
        return self._send("\n".join(lines))

    # ── Formatters ────────────────────────────────────────────────────────────

    @staticmethod
    def _format_job(job: Dict[str, Any]) -> str:
        score      = job.get("score", 0)
        llm_score  = job.get("llm_score")
        title      = TelegramBot._esc(job.get("title", "Unknown Title"))
        company    = TelegramBot._esc(job.get("company", "Unknown Company"))
        location   = TelegramBot._esc(job.get("location", "Unknown Location"))
        source     = TelegramBot._esc(job.get("source", ""))
        url        = job.get("url", "")
        salary     = job.get("salary")
        job_type   = job.get("job_type", "").replace("_", "\\-")
        easy_apply = job.get("easy_apply")
        skills     = job.get("skills") or []
        summary    = TelegramBot._esc((job.get("llm_summary") or "")[:200])

        # Score emoji
        if score >= 80:
            star = "🟢"
        elif score >= 60:
            star = "🟡"
        else:
            star = "🟠"

        lines = [
            f"{star} *{title}*",
            f"🏢 {company} · 📍 {location}",
        ]

        score_line = f"📊 Score: `{score}`"
        if llm_score is not None:
            score_line += f"  🤖 AI: `{llm_score}`"
        lines.append(score_line)

        if salary:
            lines.append(f"💰 ${int(salary):,}/yr")
        if job_type:
            lines.append(f"📋 {job_type}")
        if easy_apply:
            lines.append("⚡ Easy Apply")
        if source:
            lines.append(f"🔗 Source: {source}")
        if skills:
            lines.append(f"🛠 {' · '.join(skills[:5])}")
        if summary:
            lines.append(f"\n_{summary}_")
        if url:
            lines.append(f"\n[👉 Apply Here]({url})")

        return "\n".join(lines)

    @staticmethod
    def _format_post(post: Dict[str, Any]) -> str:
        author       = TelegramBot._esc(post.get("author_name", "Unknown"))
        headline     = TelegramBot._esc(post.get("author_headline", ""))
        profile_url  = post.get("author_profile_url", "")
        post_url     = post.get("post_url", "")
        title        = TelegramBot._esc(post.get("extracted_title", ""))
        company      = TelegramBot._esc(post.get("extracted_company", ""))
        email        = post.get("contact_email", "")
        linkedin_url = post.get("contact_linkedin", "")
        text         = TelegramBot._esc((post.get("post_text") or "")[:400])
        score        = post.get("score", 0)
        role         = post.get("role_category", "").replace("_", " ").title()

        lines = [
            f"📢 *LinkedIn Recruiter Post* — Score `{score}`",
        ]

        if profile_url:
            lines.append(f"👤 [{author}]({profile_url})")
        else:
            lines.append(f"👤 *{author}*")

        if headline:
            lines.append(f"_{headline}_")
        if title:
            lines.append(f"💼 {title}" + (f" @ {company}" if company else ""))
        if role:
            lines.append(f"🏷 {role}")

        # Contact info — the most important part
        if email:
            lines.append(f"\n📧 *Email: `{email}`*")
        if linkedin_url and linkedin_url != profile_url:
            lines.append(f"🔗 [Contact on LinkedIn]({linkedin_url})")

        if text:
            lines.append(f"\n{text}…")

        if post_url:
            lines.append(f"\n[👉 View Post on LinkedIn]({post_url})")

        return "\n".join(lines)

    # ── Low-level send ────────────────────────────────────────────────────────

    def _send(self, text: str) -> bool:
        """Send a MarkdownV2 message with retry logic."""
        if not self._enabled:
            return False
        url = f"{_BASE}{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = requests.post(url, json=payload, timeout=10)
                data = resp.json()
                if data.get("ok"):
                    return True
                # Telegram often rejects bad MarkdownV2; fall back to plain text
                if "can't parse" in str(data.get("description", "")).lower():
                    payload["parse_mode"] = "HTML"
                    payload["text"] = self._strip_markdown(text)
                    continue
                logger.warning("Telegram API error (attempt %d): %s", attempt, data)
            except requests.RequestException as exc:
                logger.warning("Telegram send failed (attempt %d): %s", attempt, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)
        return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _esc(text: str) -> str:
        """Escape special chars for Telegram MarkdownV2."""
        special = r"_*[]()~`>#+-=|{}.!"
        return "".join(f"\\{c}" if c in special else c for c in text)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Very rough fallback: strip markdown markers."""
        import re
        text = re.sub(r"[*_`\[\]\\]", "", text)
        return text[:4096]
