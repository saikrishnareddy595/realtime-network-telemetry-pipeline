"""
Staffing & Prime Vendor portal scrapers.

Each class targets a major US IT staffing company that posts contract,
contract-to-hire, and direct-hire roles for Data/AI engineers.

Sources covered:
  TEKsystems, Kforce, Robert Half, Randstad, Insight Global,
  Apex Systems, Motion Recruitment, CyberCoders, Akkodis (Modis),
  Volt, Harvey Nash, Hays Technology, LanceSoft, Staffmark, Beacon Hill
"""

import logging
from bs4 import BeautifulSoup
from typing import Any, Dict, List
from urllib.parse import quote_plus

from scrapers.base import BaseHTMLScraper, parse_salary, parse_relative_date, short_delay
import config

logger = logging.getLogger(__name__)


def _make_scraper(source_name: str, search_url_template: str,
                  card_sels: List[str], title_sels: List[str],
                  company_sels: List[str], location_sels: List[str],
                  salary_sels: List[str], url_sels: List[str],
                  date_sels: List[str], base_url: str = "",
                  default_type: str = "contract"):
    """Factory that builds a scraper class for a staffing portal."""

    class StaffingScraper(BaseHTMLScraper):
        SOURCE         = source_name
        _URL_TEMPLATE  = search_url_template
        _CARD_SELS     = card_sels
        _TITLE_SELS    = title_sels
        _COMPANY_SELS  = company_sels
        _LOC_SELS      = location_sels
        _SAL_SELS      = salary_sels
        _URL_SELS      = url_sels
        _DATE_SELS     = date_sels
        _BASE_URL      = base_url
        _DEFAULT_TYPE  = default_type

        def _fetch_title(self, title: str):
            url = self._URL_TEMPLATE.format(q=quote_plus(title))
            r = self._get(url)
            if not r:
                return
            soup  = BeautifulSoup(r.text, "lxml")
            cards = []
            for sel in self._CARD_SELS:
                cards = soup.select(sel)
                if cards:
                    break
            for card in cards:
                job = self._parse(card)
                if job:
                    self._add(job)
            short_delay()

        def _parse(self, card) -> Dict[str, Any]:
            def t(*sels):
                for s in sels:
                    el = card.select_one(s)
                    if el:
                        return el.get_text(strip=True)
                return ""
            def h(*sels):
                for s in sels:
                    el = card.select_one(s)
                    if el and el.get("href"):
                        href = el["href"]
                        if href.startswith("http"):
                            return href
                        return self._BASE_URL + href
                return ""

            title = t(*self._TITLE_SELS)
            if not title:
                return {}
            raw_type = t(".job-type",".type",".employment-type","span[class*='type']")
            if "contract to hire" in raw_type.lower() or "c2h" in raw_type.lower():
                job_type = "contract_to_hire"
            elif "contract" in raw_type.lower():
                job_type = "contract"
            elif "full" in raw_type.lower() or "permanent" in raw_type.lower():
                job_type = "full_time"
            else:
                job_type = self._DEFAULT_TYPE

            return {
                "title":       title,
                "company":     t(*self._COMPANY_SELS) or source_name,
                "location":    t(*self._LOC_SELS),
                "salary":      parse_salary(t(*self._SAL_SELS)),
                "url":         h(*self._URL_SELS),
                "source":      self.SOURCE,
                "posted_date": parse_relative_date(t(*self._DATE_SELS)),
                "easy_apply":  None,
                "applicants":  None,
                "description": "",
                "job_type":    job_type,
            }

    StaffingScraper.__name__  = f"{source_name}Scraper"
    StaffingScraper.__qualname__ = f"{source_name}Scraper"
    return StaffingScraper


# ── TEKsystems ────────────────────────────────────────────────────────────────
TEKsystemsScraper = _make_scraper(
    "TEKsystems",
    "https://www.teksystems.com/en/jobs#q={q}&t=Jobs&sort=relevancy",
    ["div.job-card", "li.job-listing", "article.job"],
    ["h2 a", "h3 a", ".job-title a", "a.title"],
    [".company", ".employer", ".client"],
    [".location", ".city-state", ".job-location"],
    [".salary", ".rate", ".compensation"],
    ["h2 a", "h3 a", ".job-title a"],
    [".posted", ".date", "time"],
    "https://www.teksystems.com",
    "contract",
)

# ── Kforce ────────────────────────────────────────────────────────────────────
KforceScraper = _make_scraper(
    "Kforce",
    "https://www.kforce.com/job-seeker/find-a-job/?q={q}&l=United+States",
    ["div.job-card", "article.job-listing", "li.search-result"],
    ["h2 a", "h3 a", ".position-title a", "a.job-title"],
    [".client-name", ".company", ".employer"],
    [".location", ".job-location", ".city"],
    [".salary", ".rate", ".pay"],
    ["h2 a", "h3 a", ".position-title a"],
    [".posted-date", "time", ".date"],
    "https://www.kforce.com",
    "contract",
)

# ── Robert Half ───────────────────────────────────────────────────────────────
RobertHalfScraper = _make_scraper(
    "RobertHalf",
    "https://www.roberthalf.com/us/en/jobs/search?q={q}&l=",
    ["div.job-listing", "article.job", "div[class*='JobCard']"],
    ["h2 a", ".job-title a", "h3 a", "a.job-name"],
    [".company-name", ".client", ".employer"],
    [".location", ".job-location", ".city-state"],
    [".salary", ".hourly-rate", ".compensation"],
    ["h2 a", ".job-title a", "h3 a"],
    [".posted-date", "time", ".date-posted"],
    "https://www.roberthalf.com",
    "contract",
)

# ── Randstad ──────────────────────────────────────────────────────────────────
RandstadScraper = _make_scraper(
    "Randstad",
    "https://www.randstadusa.com/jobs/search/?q={q}&l=United+States",
    ["div.job-card", "article.job-result", "li.job"],
    ["h2 a", "h3 a", ".job-title a", ".position-title a"],
    [".company", ".client", ".employer-name"],
    [".location", ".city", ".job-location"],
    [".salary", ".rate", ".pay-range"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted"],
    "https://www.randstadusa.com",
    "contract",
)

# ── Insight Global ────────────────────────────────────────────────────────────
InsightGlobalScraper = _make_scraper(
    "InsightGlobal",
    "https://jobs.insightglobal.com/jobs?q={q}&l=United+States",
    ["div.job-card", "li.job-listing", "article.job"],
    ["h2 a", "h3 a", "a.job-title", ".position-name a"],
    [".company", ".client-name", ".employer"],
    [".location", ".job-location", ".city"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", "a.job-title"],
    [".date", "time", ".posted-date"],
    "https://jobs.insightglobal.com",
    "contract",
)

# ── Apex Systems ──────────────────────────────────────────────────────────────
ApexSystemsScraper = _make_scraper(
    "ApexSystems",
    "https://www.apexsystems.com/job-seekers/find-a-job?q={q}",
    ["div.job-card", "article.job-listing", "li.result"],
    ["h2 a", "h3 a", ".job-title a", "a.title"],
    [".company", ".client"],
    [".location", ".job-location"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted"],
    "https://www.apexsystems.com",
    "contract",
)

# ── Motion Recruitment ────────────────────────────────────────────────────────
MotionRecruitmentScraper = _make_scraper(
    "MotionRecruitment",
    "https://motionrecruitment.com/job-search?q={q}",
    ["div.job-card", "article.job", "li.job-result"],
    ["h2 a", "h3 a", ".job-title a", "a.job-name"],
    [".company", ".client-company"],
    [".location", ".job-location"],
    [".salary", ".rate", ".compensation"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted-date"],
    "https://motionrecruitment.com",
    "contract",
)

# ── CyberCoders ───────────────────────────────────────────────────────────────
CyberCodersScraper = _make_scraper(
    "CyberCoders",
    "https://www.cybercoders.com/search/?searchterms={q}&location=",
    ["div.job-listing-item", "article.job", "li.listing"],
    ["h2 a", "h3 a", "a.job-title", ".job-title-link"],
    [".company-name", ".employer", ".client"],
    [".location", ".job-location"],
    [".salary-range", ".salary", ".compensation"],
    ["h2 a", "h3 a", "a.job-title", ".job-title-link"],
    [".date-posted", "time", ".posted"],
    "https://www.cybercoders.com",
    "full_time",
)

# ── Akkodis (formerly Modis) ──────────────────────────────────────────────────
Akkodiscraper = _make_scraper(
    "Akkodis",
    "https://www.akkodis.com/en-us/jobs/search?q={q}&location=United+States",
    ["div.job-card", "article.job-listing", "li.job"],
    ["h2 a", "h3 a", ".job-title a", "a.title"],
    [".company", ".client"],
    [".location", ".city"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted"],
    "https://www.akkodis.com",
    "contract",
)

# ── Volt ──────────────────────────────────────────────────────────────────────
VoltScraper = _make_scraper(
    "Volt",
    "https://www.volt.com/job-seekers/job-search?q={q}&l=United+States",
    ["div.job-card", "article.job", "li.search-result"],
    ["h2 a", "h3 a", ".job-title a", "a.position-title"],
    [".company", ".client", ".employer"],
    [".location", ".job-location"],
    [".salary", ".pay"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted-date"],
    "https://www.volt.com",
    "contract",
)

# ── Harvey Nash ───────────────────────────────────────────────────────────────
HarveyNashScraper = _make_scraper(
    "HarveyNash",
    "https://jobs.harveynash.com/en-us?keywords={q}&countryCode=US",
    ["div.job-card", "article.job", "li.result"],
    ["h2 a", "h3 a", ".job-title a", ".role-title a"],
    [".company", ".client"],
    [".location", ".city-state"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted"],
    "https://jobs.harveynash.com",
    "contract",
)

# ── Hays Technology ───────────────────────────────────────────────────────────
HaysTechScraper = _make_scraper(
    "HaysTech",
    "https://www.hays.com/job-search/us-jobs/keyword-{q}",
    ["div.job-item", "article.job", "li.job-card"],
    ["h2 a", "h3 a", ".job-title a", ".role-name a"],
    [".company", ".employer"],
    [".location", ".city"],
    [".salary", ".rate", ".compensation"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"],
    "https://www.hays.com",
    "contract",
)

# ── LanceSoft ─────────────────────────────────────────────────────────────────
LanceSoftScraper = _make_scraper(
    "LanceSoft",
    "https://www.lancesoft.com/jobs?q={q}&location=United+States",
    ["div.job-card", "li.job-listing", "article.job"],
    ["h2 a", "h3 a", ".job-title a", "a.job-name"],
    [".company", ".client-name"],
    [".location", ".city"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted"],
    "https://www.lancesoft.com",
    "contract",
)

# ── Staffmark ─────────────────────────────────────────────────────────────────
StaffmarkScraper = _make_scraper(
    "Staffmark",
    "https://www.staffmark.com/find-jobs?q={q}",
    ["div.job-card", "article.job", "li.result"],
    ["h2 a", "h3 a", ".job-title a", "a.position"],
    [".company", ".client"],
    [".location", ".job-location"],
    [".salary", ".pay-range"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"],
    "https://www.staffmark.com",
    "contract",
)

# ── Beacon Hill ───────────────────────────────────────────────────────────────
BeaconHillScraper = _make_scraper(
    "BeaconHill",
    "https://www.beaconhillstaffing.com/jobs?q={q}&location=United+States",
    ["div.job-card", "article.job", "li.job-listing"],
    ["h2 a", "h3 a", ".job-title a", "a.title"],
    [".company", ".client"],
    [".location", ".city"],
    [".salary", ".rate"],
    ["h2 a", "h3 a", ".job-title a"],
    [".date", "time", ".posted-date"],
    "https://www.beaconhillstaffing.com",
    "contract",
)


# ── Consulting/Federal scrapers ────────────────────────────────────────────────
CognizantScraper = _make_scraper(
    "Cognizant",
    "https://careers.cognizant.com/global/en/search-results?keywords={q}&location=United+States",
    ["li.jobs-list-item", "div.job-card", "article.job"],
    ["h2 a", "h3 a", ".job-title a", "a.job-name"],
    [], [".location", ".city-state"],
    [".salary"], ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"], "https://careers.cognizant.com", "full_time",
)

InfosysScraper = _make_scraper(
    "Infosys",
    "https://career.infosys.com/jobdesc/job-search?role={q}&country=USA",
    ["div.job-card", "li.job", "tr.job-row"],
    ["h2 a", "h3 a", ".job-title a", "td a"],
    [".company"], [".location", ".city", "td.location"],
    [".salary"], ["h2 a", "h3 a", ".job-title a", "td a"],
    [".date", "time"], "https://career.infosys.com", "full_time",
)

SAICScraper = _make_scraper(
    "SAIC",
    "https://jobs.saic.com/jobs?keywords={q}&location=United+States",
    ["li.jobs-list-item", "div.job-card", "article.job"],
    ["h2 a", "h3 a", ".job-title a", "a[data-ph-at-id='job-link']"],
    [], [".location", ".city-state"],
    [".salary"], ["h2 a", "h3 a", ".job-title a", "a[data-ph-at-id='job-link']"],
    [".date", "time"], "https://jobs.saic.com", "full_time",
)

LeidosScraper = _make_scraper(
    "Leidos",
    "https://careers.leidos.com/jobs?keywords={q}&location=United+States",
    ["li.jobs-list-item", "div.job-card", "article"],
    ["h2 a", "h3 a", ".job-title a", "a[data-ph-at-id='job-link']"],
    [], [".location", ".job-location"],
    [".salary"], ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"], "https://careers.leidos.com", "full_time",
)

BoozAllenScraper = _make_scraper(
    "BoozAllen",
    "https://careers.boozallen.com/jobs/SearchJobs/{q}?jobRecordsPerPage=25",
    ["li.jobs-list-item", "div.job-card", "article.job"],
    ["h2 a", "h3 a", ".job-title a", "a[data-ph-at-id='job-link']"],
    [], [".location", ".city-state"],
    [".salary"], ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"], "https://careers.boozallen.com", "full_time",
)

AccentureScraper = _make_scraper(
    "Accenture",
    "https://www.accenture.com/us-en/careers/jobsearch?jk={q}&country=USA",
    ["li.jobs-list-item", "div.job-card", "article.cta-job"],
    ["h2 a", "h3 a", ".job-title a", ".cta-job__title a"],
    [], [".location", ".cta-job__location"],
    [".salary"], ["h2 a", "h3 a", ".job-title a", ".cta-job__title a"],
    [".date", "time"], "https://www.accenture.com", "full_time",
)

CapgeminiScraper = _make_scraper(
    "Capgemini",
    "https://www.capgemini.com/jobs/?search={q}&country=US",
    ["div.job-card", "article.job", "li.result"],
    ["h2 a", "h3 a", ".job-title a", ".title a"],
    [], [".location", ".city"],
    [".salary"], ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"], "https://www.capgemini.com", "full_time",
)

IBMScraper = _make_scraper(
    "IBM",
    "https://www.ibm.com/careers/search?q={q}&country=US",
    ["div.job-card", "li.job-listing", "article.bx--tile"],
    ["h2 a", "h3 a", ".job-title a", ".bx--tile a"],
    [], [".location", ".bx--tag--blue"],
    [".salary"], ["h2 a", "h3 a", ".job-title a"],
    [".date", "time"], "https://www.ibm.com", "full_time",
)
