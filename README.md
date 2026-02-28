#Job Scraper — Full Capabilities
Data Collection (5 Sources)
Source	Method	What it gets
JobSpy	python-jobspy library	LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs — 50 results per job title per site
Dice	Public JSON API	Tech-focused jobs, 4 titles × 5 pages = up to 100 results
RemoteOK	Public REST API	Remote-only jobs across 8 tags (spark, airflow, etl, etc.)
Arbeitnow	Free public API	International/remote jobs, 3 titles × 4 pages
Adzuna	REST API (optional)	Skipped automatically if API keys not set
Search Scope
Titles: Data Engineer, Data Engineering, ETL Engineer, Pipeline Engineer
Location: United States + Remote
Age: Only jobs posted within the last 72 hours
Work types: On-site, remote, hybrid (all included)
Data Pipeline
Collect → Deduplicate → Filter → Score → Save → Notify

Deduplication — MD5 hash of (title + company + location) removes cross-source duplicates, keeping the richer record
Filtering — Removes jobs with salary < $80k, exclude keywords (unpaid, principal, staff engineer, 10+ years), or older than 72h
Scoring (0–100) — 8-factor algorithm:
Title keyword match (+20 core, +10 tech)
Description keyword richness (+3 per keyword, max +15)
Freshness tiers: ≤12h/24h/48h/72h (+25/20/10/5)
Applicant count: <25/<50/<100/unknown (+20/15/10/10)
Easy Apply (+15)
Remote/Hybrid location (+10)
Salary ≥$150k/≥$100k (+10/5)
Dream company: Google, Amazon, Meta, Microsoft, etc. (+15)
Storage
SQLite database (jobs.db) — persists across runs, deduplicates by URL so the same job is never stored twice
Fields: title, company, location, salary, URL, source, score, posted date, easy apply, applicants, notified flag
Output / Notifications
Gmail digest email — HTML email with top 10 jobs by score, color-coded score badges, direct Apply buttons
Google Sheets sync — All jobs scoring ≥50 pushed to "Data Engineer Job Search 2025" spreadsheet (requires service account JSON secret)
Artifacts — jobs.db and scraper.log uploaded to GitHub Actions after every run (downloadable for 7/3 days)
Automation
GitHub Actions — runs automatically every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
Manual trigger — "Run workflow" button in GitHub Actions UI
30-minute timeout safety limit
What it does NOT do
No paid job board APIs (Greenhouse, Lever, Workday)
No applicant tracking / application submission
No resume parsing or matching
No LinkedIn Easy Apply detection for non-LinkedIn sources (Dice, Arbeitnow, etc.)
Google Sheets sync only works if the GOOGLE_SERVICE_ACCOUNT_JSON secret is configured
