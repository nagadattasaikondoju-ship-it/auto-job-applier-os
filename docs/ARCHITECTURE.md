# APPLYON — COMPLETE BACKEND BUILD SPEC v2

> v2 adds: modular-monolith deployment (one image, many entrypoints), Supabase pooler settings, Supabase Realtime instead of custom SSE, preference-bucket matching, Gemini model tiering + Batch API + prompt-cache ordering, smaller embeddings, India HRMS career-page connectors, cross-source dedupe, conditional fetching, extension-first application strategy, fast Playwright settings, AI quality evaluation, cost guardrails, capacity targets, kill switches, ATS canary checks, and a shorter phase plan that ships usable value earlier. Sections 23–28 are new; build phases are now section 28.

You are a principal backend engineer. Build the complete, production-grade backend for **Applyon**, an AI job application copilot for India's next generation of professionals. This is a full product, not a demo. Read this ENTIRE document before writing code. Save it in the repo as `docs/ARCHITECTURE.md` and treat it as the source of truth. Work phase by phase (section 28) and STOP after each phase for my review.

The Next.js front end already exists (with a mock data layer in `src/lib/api/`). The backend must expose a clean REST API that replaces that mock layer.

---

## 0. NON-NEGOTIABLE PRODUCT RULES

1. **Truthfulness:** the AI may reorder, rephrase, emphasize or omit facts from the user's master profile. It must NEVER invent employers, titles, dates, degrees, certifications, tools, skills, metrics or projects. Every generated document passes a deterministic truth check (section 9.4) before it can be used.
2. **User control:** default mode is **Review** — every application waits in the Review Queue for the user's approval. **Auto-submit** is opt-in, per campaign, only for ATS flows marked `trusted`, with daily caps.
3. **No prohibited automation:** NO LinkedIn automation, NO Naukri/Indeed/Glassdoor automation or scraping, no logging in to job boards with user credentials, no automation of any site whose terms forbid it. Do not build a `LinkedInEasyApplyAdapter`. Respect robots.txt for career-page crawling.
4. **No CAPTCHA solving or bot-detection evasion.** If a CAPTCHA, login wall, account-creation step, OTP or anti-bot challenge appears, the worker stops and hands the application to the user (status `needs_user_action`) with a deep link so they can finish in their own browser via the Chrome extension.
5. **Speed:** the API never does slow work inside a request. AI, scraping, PDF rendering and browser automation always run in workers. API responses target p95 < 200 ms.
6. **Privacy:** users own their data; full export and full delete. Compliance with India's DPDP Act (explicit consent, purpose notice, easy withdrawal).

---

## 1. TECH STACK (use exactly this)

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI (async), Pydantic v2, Uvicorn/Gunicorn |
| DB | Supabase Postgres + `pgvector` extension; SQLAlchemy 2.0 (async, asyncpg) + Alembic migrations. App traffic uses the Supavisor **transaction pooler (port 6543)**, which does not support prepared statements: set asyncpg `statement_cache_size=0`, SQLAlchemy `prepared_statement_cache_size=0`, and `NullPool`. Migrations and long-running worker jobs use the direct/session connection (`DIRECT_DATABASE_URL`) |
| Realtime | Supabase Realtime (Postgres changes on `tasks`, `applications`, `notifications`, filtered by `user_id` with RLS) so the front end gets live progress with no custom websocket server. Keep `GET /tasks/{id}` polling as a fallback |
| Auth | Supabase Auth (email magic link, Google OAuth). FastAPI verifies the Supabase JWT via the project's JWKS endpoint |
| Storage | Supabase Storage (private buckets: `resumes`, `documents`, `screenshots`) via signed URLs only |
| Queue | Redis 7 + Celery 5 (+ Celery Beat for schedules), separate queues per workload |
| Cache / rate limits | Redis |
| AI | Google Gemini via the official `google-genai` SDK. Generation model and embedding model names come from env vars (`GEMINI_MODEL_FAST`, `GEMINI_MODEL_SMART`, `GEMINI_EMBED_MODEL`). Always use structured JSON output with a response schema |
| Browser automation | Playwright for Python (Chromium), in separate worker containers |
| PDF | Jinja2 HTML templates → WeasyPrint PDF (ATS-friendly, text-based, single column) |
| Resume parsing | `pypdf` / `pdfplumber` for PDF, `python-docx` for DOCX, then Gemini for structuring |
| Email | Resend (transactional email) |
| Payments | Razorpay (India: UPI, cards, subscriptions) |
| Observability | Sentry (errors), structured JSON logs, OpenTelemetry traces, Flower for Celery, Prometheus metrics endpoint |
| Chrome extension | Manifest V3, TypeScript, Vite build, talks to the API with the user's token |
| Testing | pytest + pytest-asyncio, httpx AsyncClient, testcontainers (Postgres + Redis), respx for HTTP mocks, Playwright tests against local fixture HTML forms |
| Tooling | uv (package manager), ruff, mypy (strict), pre-commit, Docker Compose for local dev |

---

## 2. SYSTEM ARCHITECTURE

```
 Next.js dashboard  ───┐            ┌─── Chrome extension (autofill mode)
                       ▼            ▼
                 FastAPI API (stateless, autoscaled)
          auth · validation · credits · create records · enqueue · return task_id
                              │
                    Redis (broker + cache + rate limits)
                              │
 ┌───────────────┬────────────┼──────────────┬───────────────┬──────────────┐
 ▼               ▼            ▼              ▼               ▼              ▼
ingestion     matching    documents     form_schema     browser_apply   notifications
workers       workers     workers       workers         workers         workers
(APIs, ATS    (filters,   (resume, CL,  (extract the    (Playwright,    (email, in-app,
 boards,       vectors,    answers,      application     adapters,       digests)
 crawlers)     Gemini)     PDF)          questions)      screenshots)
                              │
          Supabase Postgres (+pgvector) · Supabase Storage
                              │
       Application tracker · analytics materialized views · audit log
```

### Why this is fast (copy the patterns the best competitors use)
- **Shared global job index:** jobs are fetched ONCE for all users, not per user. Each job is embedded ONCE.
- **Shared form schemas:** the application form for a job is extracted ONCE (`job_form_schemas`) and reused for every user who applies to that job.
- **Answer bank first, AI second:** most form fields (name, email, phone, CTC, notice period, links, work authorization) are filled from stored answers with zero AI calls. Gemini is only called for new long-form questions.
- **Funnel matching:** SQL hard filters → vector similarity → Gemini only on the top K. AI cost scales with good candidates, not with total jobs.
- **Pre-generation:** when Autopilot is on, documents and answers for accepted matches are generated ahead of time so the Review Queue is "ready to approve" with one click.
- **Workload isolation:** separate queues and worker pools so slow browser jobs never block matching or notifications.
- **Extension-first applying:** the Chrome extension fills forms in the user's own browser, so it costs nothing in server compute, works behind logins and Workday accounts, and never trips bot detection. Server-side browser workers are used only for `trusted` ATS flows. This is the single biggest cost and reliability lever.

### Deployment shape: modular monolith (easy to build, easy to scale)
- ONE codebase and ONE Docker image (plus a second image with Playwright browsers for browser workers). The same image starts as `api`, `worker --queues=...`, or `beat` by command.
- Scale by running more containers of the busy role, not by splitting into microservices. Split a module out only when metrics prove it's needed.
- Celery pools: I/O-bound queues (`ai_matching`, `document_generation`, `notifications`, `job_ingestion`) use `--pool=threads` (or gevent) with concurrency 20–50; CPU-bound PDF rendering uses `--pool=prefork`; browser queue uses prefork with concurrency = number of browsers the container's RAM allows (≈1 per 500 MB).
- Celery tasks are sync functions; call async domain code through one shared helper (`run_async(coro)`) that reuses an event loop per worker thread. Do not create a new event loop per call.

---

## 3. REPOSITORY LAYOUT

```
applyon-backend/
  apps/
    api/            # FastAPI app: routers, schemas, deps, middleware
    workers/        # Celery app, tasks per queue, beat schedule
    browser/        # Playwright worker image: ATS adapters, form engine
    extension/      # Chrome MV3 extension (TypeScript)
  packages/
    core/           # settings, db session, models, repositories, domain services
    ai/             # Gemini client, prompts, schemas, truth checker
    jobs_sources/   # source connectors (adzuna, greenhouse, lever, ashby, arbeitnow, careers, manual)
    documents/      # resume templates, rendering, PDF
  migrations/       # Alembic
  infra/            # docker-compose.yml, Dockerfiles, fly/railway/render configs
  tests/
  docs/ARCHITECTURE.md
```
Domain logic lives in `packages/` so API and workers share it. Routers stay thin.

---

## 4. DATA MODEL (Alembic migrations; every user-owned table has `user_id`, `created_at`, `updated_at`, RLS policies `user_id = auth.uid()` as defense in depth; the backend uses the service role)

**Identity & plans**
- `users_meta` — user_id (FK auth.users), plan, onboarding_status, consent_version, consent_at, marketing_opt_in, timezone (default Asia/Kolkata), deleted_at
- `subscriptions` — user_id, plan (`free|starter|pro|elite`), razorpay_subscription_id, status, current_period_end
- `credits_ledger` — user_id, credit_type (`ai|apply`), amount (+/-), reason, ref_type, ref_id, balance_after, idempotency_key (unique). Balance = latest `balance_after`; writes happen in a transaction with `SELECT ... FOR UPDATE` on a `credit_balances` row
- `credit_holds` — user_id, amount, task_id, status (`held|captured|released`), expires_at (reserve before enqueue, capture on success, release on failure)

**Profile**
- `profiles` — full_name, email, phone, city, state, country, pincode, headline, summary, total_experience_months, current_title, current_company, current_ctc_lpa, expected_ctc_lpa, notice_period_days, currently_serving_notice (bool), work_authorization (jsonb per country), willing_to_relocate, gender/diversity (optional, user-controlled, never auto-filled unless the user allows), links (linkedin, github, portfolio, leetcode, behance), languages, date_of_birth (optional)
- `experiences` — company, title, employment_type, location, start_date, end_date, is_current, bullets (jsonb array of {id, text, skills[], metrics[]})
- `educations` — institution, degree, field, start, end, grade (CGPA/percentage), board (10th/12th for Indian forms)
- `projects`, `certifications`, `skills` (name, normalized_name, category, years, proficiency, source: `resume|user|inferred_confirmed`)
- `resumes` — original upload: file_path, filename, mime, raw_text, parsed_json, parse_status, is_master
- `profile_embeddings` — user_id, kind (`full|skills|summary`), embedding vector, profile_version
- `profile_versions` — immutable snapshot jsonb of the full master profile; every tailored doc references the snapshot it used

**Questionnaire & preferences**
- `questionnaire_sessions` — user_id, status, current_step, answers jsonb, completed_at
- `job_preferences` — target_roles[], role_keywords[], seniority (`intern|fresher|junior|mid|senior|lead`), min_exp, max_exp, locations[] (city list), remote_mode[] (`remote|hybrid|onsite`), min_salary_lpa, company_size[], industries[], excluded_companies[], excluded_keywords[], employment_types[], visa_sponsorship_needed, daily_application_limit, auto_submit_enabled, min_match_score (default 70)
- `answer_bank` — user_id, question_key (normalized canonical key, e.g. `notice_period`, `why_this_company`), question_text, answer_text, answer_type (`short|long|choice|number|boolean|date`), source (`questionnaire|user_edit|ai_approved`), times_used, last_used_at, embedding vector
- `answer_edits` — user_id, application_id, question_text, original_answer, edited_answer, used_for_personalization (bool)

**Jobs (global, not user-owned)**
- `companies` — name, normalized_name, domain, careers_url, ats_type, ats_board_token, country, size, industry, is_active, last_crawled_at, crawl_interval_minutes, failure_count
- `jobs` — source, external_id, company_id, title, normalized_title, seniority, location_raw, locations[] (normalized cities), country, remote_mode, employment_type, description_html, description_text, salary_min_lpa, salary_max_lpa, salary_currency, experience_min, experience_max, required_skills[], application_url, ats_type, posted_at, first_seen_at, last_seen_at, is_active, content_hash (unique), quality_score, is_suspicious
- `job_embeddings` — job_id, embedding vector (HNSW index)
- `job_aliases` — alias_source, alias_external_id, alias_url, canonical_job_id (cross-source duplicates)
- `preference_buckets` — bucket_key (role_cluster|seniority_band|city_or_remote), user_id; index on bucket_key
- `feature_flags` — key, enabled, rules jsonb (kill switches per ATS adapter, per source, per AI feature, auto-submit global switch)
- `job_form_schemas` — job_id, ats_type, schema_json (ordered fields: label, canonical_key, type, required, options, selector hints, step), extraction_method (`api|dom`), extracted_at, version, status
- `ats_flows` — ats_type, flow_version, trusted (bool), success_rate_7d, last_verified_at, notes (admin-controlled; only `trusted` flows may auto-submit)

**Matching & documents**
- `job_matches` — user_id, job_id, profile_version_id, filter_passed, vector_score, match_score, decision (`apply|maybe|skip`), fit_reasons[], gaps[], resume_focus[], risk_flags[], model, prompt_version, user_feedback (`good|bad|null`), status (`new|seen|saved|dismissed|queued`); unique (user_id, job_id, profile_version_id)
- `resume_versions` — user_id, job_id (nullable for general), profile_version_id, content_json, template_id, pdf_path, truth_check_status (`passed|flagged|failed`), flagged_claims jsonb, status (`draft|approved`), version_no
- `cover_letters` — same pattern (text, pdf_path)
- `screening_answers` — user_id, job_id, application_id, field_key, question_text, answer, source (`answer_bank|ai|user`), confidence

**Applications & automation**
- `campaigns` (Autopilot) — user_id, name, preferences_snapshot, mode (`review|auto_submit`), status (`active|paused|stopped`), daily_limit, schedule (time windows IST), started_at, stats jsonb
- `applications` — user_id, job_id, campaign_id, resume_version_id, cover_letter_id, status (`draft|preparing|ready_for_review|approved|submitting|submitted|needs_user_action|failed|withdrawn|interview|offer|rejected|ghosted`), channel (`extension|assisted|auto`), application_url, submitted_at, follow_up_at, automation_task_id, failure_reason, notes
- `application_events` — application_id, type, payload jsonb, actor (`user|system|worker`), created_at (append-only timeline)
- `automation_tasks` — type, user_id, application_id, queue, celery_task_id, status (`queued|running|succeeded|failed|dead`), attempts, idempotency_key (unique), error, started_at, finished_at
- `automation_artifacts` — automation_task_id, step_no, screenshot_path, html_snapshot_path (redacted), log jsonb
- `tasks` — generic user-visible async tasks for polling (`GET /tasks/{id}`): kind, status, progress (0–100), result_ref, error

**Platform**
- `notifications` — user_id, type, title, body, data, read_at, channels[]
- `audit_log` — actor, action, entity, entity_id, metadata
- `ai_usage` — user_id, feature, model, tokens_in, tokens_out, cost_estimate_usd, latency_ms, cached (bool)
- `consents` — user_id, purpose, version, granted_at, withdrawn_at

**Indexes:** every FK; `jobs(is_active, posted_at desc)`, GIN on `jobs.locations`, `jobs.required_skills`, trigram index on `jobs.normalized_title`; HNSW on embedding columns; `job_matches(user_id, status, match_score desc)`; `applications(user_id, status, updated_at desc)`; partial index on `applications(status) where status in ('ready_for_review','needs_user_action')`.

---

## 5. ONBOARDING QUESTIONNAIRE ENGINE ("knows everything about you")

Goal: in ~8 minutes the user ends with (a) a complete master profile, (b) precise job preferences, (c) a filled answer bank covering ~90% of the questions Indian and global application forms ask.

Flow:
1. **Resume upload** → `POST /resumes` → parse task (text extraction → Gemini structured parse into the profile schema) → user reviews and confirms each section (confirmed data becomes the master profile; nothing is used until confirmed).
2. **Adaptive questionnaire** — question definitions live in a versioned YAML/JSON file (`packages/core/questionnaire/v1.yaml`), each with: id, canonical_key, text, type, options, validation, `ask_if` condition, and which table/field it writes to. The engine (`GET /onboarding/next-question`, `POST /onboarding/answer`) skips anything already known from the resume and branches on answers.
   Sections:
   - **Career goal:** target roles (with autocomplete from a role taxonomy), "what do you want to become in 2–3 years", seniority, career switch? (if yes, which transferable skills)
   - **Logistics (India-specific):** current city, preferred cities, remote/hybrid/onsite, willing to relocate, current CTC (LPA), expected CTC, notice period, serving notice?, last working day, work authorization (India + other countries), passport (yes/no), visa sponsorship needed
   - **Filters:** excluded companies, excluded industries, company size, employment type (full-time, internship, contract), minimum salary, daily application limit
   - **Standard form answers:** gender/diversity (optional, "prefer not to say" default), date of birth (optional), 10th/12th marks and graduation CGPA (common in Indian forms), languages, how did you hear about us (default "Company website"), are you related to an employee, willing to work shifts, have you applied before
   - **Story answers (long-form, AI-assisted):** "Tell us about yourself", "Why do you want to work here" (template with company placeholder), "Biggest achievement", "Strengths/weaknesses", "Describe a challenging project", "Why are you leaving your current job". The AI drafts from the confirmed profile; the user edits; final versions go to `answer_bank` with source `questionnaire`.
3. **Consent screen:** explicit, separate consents for (a) processing profile data for matching, (b) generating documents, (c) submitting applications on their behalf in auto-submit mode. Store in `consents`.
4. **Profile completeness score** (0–100) with a list of missing items; Autopilot can only start at ≥ 80.

The questionnaire is re-runnable from settings, and new answer-bank entries are added automatically when the user answers a new question in the Review Queue.

---

## 6. JOB INGESTION

### 6.1 Sources (each is a connector class implementing `fetch(since) -> Iterable[RawJob]` and `normalize(raw) -> JobIn`)
| Connector | Access | Notes |
|---|---|---|
| `AdzunaConnector` | app_id + app_key | country `in` (and others later); query by role keywords × cities; incremental by date; respect quotas, cache responses |
| `GreenhouseBoardConnector` | public, no key | `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`; per company in `companies` |
| `LeverPostingsConnector` | public, no key | `GET https://api.lever.co/v0/postings/{company}?mode=json` |
| `AshbyBoardConnector` | public, no key | `GET https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true` |
| `ArbeitnowConnector` | public | `https://www.arbeitnow.com/api/job-board-api` (paginated) |
| `SmartRecruiters/Workable/Recruitee connectors` | public posting APIs | add behind the same interface |
| `CareerPageCrawler` | robots.txt-respecting | for companies without a known ATS: fetch careers page, read `schema.org/JobPosting` JSON-LD first, fall back to Gemini extraction of the listing page; polite rate limit per domain (1 req/2s), identify with a proper User-Agent |
| `ManualUrlConnector` | user-pasted URL/text | detect ATS from URL pattern; if known ATS, use its public API for that job; else fetch + extract |
| `IndiaHRMSCareerConnectors` | public career pages | many Indian employers hire through HRMS suites with embedded ATS (Keka, Darwinbox, Zoho Recruit, greytHR, PeopleStrong, HROne) or MNC systems (Workday, SAP SuccessFactors, Oracle Taleo/Recruiting). Before building, verify each one's public career-page URL pattern and whether it exposes JSON or JSON-LD; build adapters only for the ones that do, in order of how many seeded companies use them |

Fetch efficiently: send `If-None-Match` / `If-Modified-Since` when sources return ETag/Last-Modified, skip unchanged boards by hashing the response body, use a shared `httpx.AsyncClient` with HTTP/2 and connection pooling, and fetch many boards concurrently with a per-host semaphore.

### 6.2 Company registry & ATS detection
- `companies` is seeded from a CSV (`infra/seed/companies_india.csv`: name, domain, careers_url, ats_type, board_token) and grows automatically: every pasted URL and every Adzuna job with a recognizable ATS URL adds/updates the company.
- `detect_ats(url)` uses URL patterns: `boards.greenhouse.io|job-boards.greenhouse.io` → greenhouse, `jobs.lever.co` → lever, `jobs.ashbyhq.com` → ashby, `*.myworkdayjobs.com` → workday, `jobs.smartrecruiters.com` → smartrecruiters, `apply.workable.com` → workable, `*.recruitee.com` → recruitee, else `unknown`.

### 6.3 Normalization & dedupe
- Normalize title (lowercase, strip seniority tokens into `seniority`), city names (alias map: Bangalore→Bengaluru, Gurgaon→Gurugram, Bombay→Mumbai…), remote mode, salary to LPA, experience range (regex + Gemini fallback only when ambiguous), required skills (skill taxonomy match).
- `content_hash = sha256(normalized_company | normalized_title | primary_location | canonical_application_url)`. Upsert on hash; update `last_seen_at`; mark `is_active=false` when a job disappears from its source for 2 consecutive runs.
- Cross-source dedupe (the same job often appears on Adzuna AND the company's Greenhouse board): resolve aggregator redirect URLs to the final application URL in a background task; also compute a SimHash of the description and treat jobs with the same company + normalized title + SimHash distance ≤ 3 as one job. Prefer the direct ATS record as canonical and keep the other as an alias in `job_aliases`.
- Quality/scam filter: flag jobs with no company domain, payment requests, WhatsApp-only contact, unrealistic salary, or duplicate text across many companies (`is_suspicious`, never auto-applied).

### 6.4 Schedule (Celery Beat)
- Every 30 min: ATS board connectors for companies due (`last_crawled_at + crawl_interval`), spread with jitter
- Every 60 min: Adzuna incremental queries for the union of active users' role × city pairs (deduped)
- Every 6 h: career-page crawler
- On new/changed job: enqueue `embed_job` → then `match_new_job_against_users`
- Nightly: deactivate stale jobs, refresh company crawl intervals based on posting frequency

---

## 7. MATCHING ENGINE (the funnel)

For a user-job pair:
1. **Hard filters (pure SQL, no AI):** role keyword/title similarity (trigram + taxonomy), locations ∩ preferred (or remote allowed), remote mode, experience window (user exp within job range ± 1 year tolerance), salary (job max ≥ user min when known), excluded companies/keywords, employment type, work authorization/visa, `is_suspicious = false`, not already applied/dismissed.
2. **Vector score:** cosine similarity between `profile_embeddings.full` and `job_embeddings` (pgvector). Keep the top K per user per run (K = 3 × daily limit, min 30).
3. **Gemini scoring (top K only, `GEMINI_MODEL_FAST`)**, batched (up to 5 jobs per call) with this exact output schema per job:
```json
{
  "job_id": "uuid",
  "match_score": 84,
  "decision": "apply",
  "fit_reasons": ["Strong SEO and growth experience", "AI automation experience matches the role"],
  "gaps": ["HubSpot experience"],
  "resume_focus": ["SEO growth results", "AI workflow automation"],
  "risk_flags": ["Requires 5+ years experience"]
}
```
   Decision rules: `apply` ≥ user `min_match_score` and no blocking risk flag; `maybe` within 10 points below; else `skip`.
4. **Cache:** Redis key `match:{user_id}:{job_id}:{profile_version}:{prompt_version}` (TTL 30 days) + DB row; never score the same pair twice.
5. **Learning:** user feedback (👍/👎, dismiss reasons, edits) adjusts per-user weights stored in `job_preferences.learned_weights` (title tokens, companies, skills) applied at step 1–2 ranking.

Two triggers: (a) **job-centric** — a new job is matched against all users whose filters could match (reverse filter query); (b) **user-centric** — after onboarding/preference change, match the user against all active jobs.

**Scale optimization: preference buckets.** Matching every new job against every user is users × jobs. Instead, group users into `preference_buckets` keyed by (role cluster, seniority band, city-or-remote). A new job maps to a handful of buckets with one indexed lookup, so only users in those buckets are evaluated. Recompute a user's buckets when their preferences change. Run steps 1–2 as one set-based SQL query per bucket (not a Python loop per user).
**Embeddings:** use the embedding model's reduced output dimension (768 instead of the default) — smaller HNSW index, faster search, little quality loss. Store `halfvec` if pgvector version supports it. Embed the job once on insert; embed the profile once per profile version.
**Urgency tiers:** matches the user is waiting for (onboarding, pasted job, "refresh now") use the real-time Gemini API. Overnight re-scoring and backfills go through the **Gemini Batch API** (about 50% cheaper, results within 24 h).

---

## 8. AI LAYER (`packages/ai`)

- One `GeminiClient` wrapper: async, timeouts, retries with exponential backoff on 429/5xx, structured output (`response_mime_type="application/json"` + `response_schema` from Pydantic), JSON validation with Pydantic (on failure: one repair retry, then fail the task), token/cost logging to `ai_usage`, Redis response cache keyed by sha256(prompt_version + inputs).
- All prompts live in versioned files (`packages/ai/prompts/*.md`) with a `PROMPT_VERSION`. System prompt rules for every generation prompt: use ONLY facts from the provided profile JSON; reference bullet IDs; output JSON only; Indian English; no clichés.
- Global per-model concurrency limit via a Redis semaphore + token bucket to stay under Gemini rate limits; per-user rate limits by plan.
- Prompt-injection defense: job descriptions are wrapped as untrusted data; instructions inside them are ignored; outputs are schema-validated.

- **Model tiering (env-configurable):** `GEMINI_MODEL_LITE` for cheap classification (form-field mapping, seniority/experience extraction, scam check); `GEMINI_MODEL_FAST` for match scoring and screening answers; `GEMINI_MODEL_SMART` only for resume tailoring and cover letters. Never use the smart model where the lite one passes the eval set (section 25).
- **Prompt-cache-friendly ordering:** Gemini caches repeated prompt prefixes automatically on newer models (cache hits are billed far cheaper). Put stable content first — system rules, then the user's profile snapshot — and the variable part (the job) last, so consecutive calls for the same user reuse the cached prefix.
- **Batching:** score up to 5 jobs per call; generate resume + cover letter + screening answers for one application in one structured call when total output fits, instead of three calls.

Functions: `parse_resume`, `score_matches_batch`, `tailor_resume`, `write_cover_letter`, `answer_screening_questions`, `classify_form_field` (map an unknown label to a canonical key), `extract_jobs_from_page`, `draft_story_answer`.

---

## 9. DOCUMENT GENERATION

### 9.1 Tailored resume
Input: profile_version snapshot + job + match (`resume_focus`). Output schema: `{ summary, skills_ordered[], experiences: [{experience_id, bullets: [{source_bullet_id, text}]}], projects: [{project_id, bullets}], keywords_used[], changes_made[] }`. Every bullet MUST reference a `source_bullet_id`.
### 9.2 Cover letter
≤ 300 words, company- and role-specific, facts only from profile, saved as text + PDF.
### 9.3 Screening answers
For each field in the job's form schema not covered by the answer bank: generate an answer using the answer bank + the user's past edits (`answer_edits`, last 10 relevant by embedding similarity) as few-shot style examples. Return a confidence score; low-confidence answers are flagged for the user in the Review Queue.
### 9.4 Truth checker (deterministic, runs before any document is usable)
- Every `source_bullet_id` exists in the snapshot; rewritten bullet must not introduce numbers/percentages/₹ amounts, company names, titles, dates, degrees or tools absent from the source bullet or the profile skill list (regex + normalized entity matching against the snapshot).
- Skills in `skills_ordered` ⊆ profile skills.
- Result: `passed`, `flagged` (show highlights to the user, block auto-submit), or `failed` (regenerate once, then show to the user).
### 9.5 Rendering
Jinja2 templates (2–3 ATS-friendly templates, single column, real text, standard headings) → WeasyPrint PDF → upload to `documents/{user_id}/{application_id}/resume_v{n}.pdf` → `resume_versions` row. File name: `Firstname_Lastname_Resume.pdf`.

---

## 10. APPLICATION ENGINE

### 10.1 Form schema extraction (shared per job, `form_schema` queue)
- If the ATS exposes questions via public API (e.g. Greenhouse `GET .../jobs/{id}?questions=true`, Lever posting details), build the schema from the API.
- Else load the page in Playwright (no submission) and extract fields: label (via `<label for>`, aria-label, aria-labelledby, nearby text, placeholder), input type, required, options, step number for multi-step flows.
- Map each field to a `canonical_key` with rules first (dictionary of ~200 synonyms: "notice period", "CTC", "current salary", "LinkedIn profile URL"...), Gemini `classify_form_field` only for unknowns. Cache mappings globally (`field_label_map` table: normalized_label → canonical_key, confidence).

### 10.2 Answer resolution (per application)
For each schema field: answer bank exact key → answer bank semantic match (embedding, threshold) → profile field → AI-generated (flagged) → unanswerable (application goes to `needs_user_action` with the specific questions listed). File fields get the tailored resume/cover letter PDFs.

### 10.3 Three channels
1. **Extension autofill (launch first):** the Chrome extension detects supported ATS pages (Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, generic forms), calls `GET /extension/fill-plan?url=...` which returns the resolved field→value plan + signed document URLs; the extension fills fields, attaches files, highlights AI-generated answers for review, and the USER clicks submit. The extension then calls `POST /applications/{id}/mark-submitted` (or auto-detects the success page). Works on Workday and login-gated flows because the user is in their own session.
2. **Assisted apply (server-side, default for Autopilot):** a browser worker opens the application URL, fills everything, uploads documents, captures screenshots of every step, and STOPS before the final submit. The application becomes `ready_for_review` with screenshots. On approval, a new task re-opens the page, refills deterministically from the same saved plan, verifies the filled values match, and submits.
3. **Auto-submit (opt-in):** same as assisted, but submits without review ONLY when ALL are true: campaign mode `auto_submit`, ATS flow `trusted`, truth check `passed`, every answer from answer bank/profile (no low-confidence AI answers), match_score ≥ campaign threshold, daily cap not reached, user has `apply` credits.

### 10.4 ATS adapters (`apps/browser/adapters/`)
Interface: `detect(page) -> bool`, `extract_schema(page) -> FormSchema`, `fill(page, plan) -> FillReport`, `go_to_next_step(page)`, `submit(page)`, `verify_success(page) -> bool`, `detect_blockers(page) -> list[Blocker]` (captcha, login, account creation, OTP, unexpected required field). Implement: `GreenhouseAdapter`, `LeverAdapter`, `AshbyAdapter`, `SmartRecruitersAdapter`, `WorkableAdapter`, `RecruiteeAdapter`, `GenericFormAdapter` (heuristic). `WorkdayAdapter` is extension-only at first (Workday requires per-company accounts → hand off to user). Each adapter has fixture HTML pages in `tests/fixtures/ats/` and Playwright tests.

### 10.5 Browser worker rules
- One fresh browser context per task (no shared cookies), realistic but honest User-Agent, human-paced typing delays, timezone Asia/Kolkata.
- Speed: keep one long-lived Chromium process per worker and open a new context per task (contexts start in milliseconds; browsers take seconds). Block images, fonts, media and third-party analytics with `page.route` (keep the ATS's own scripts and CAPTCHA scripts untouched). Wait on specific selectors, never fixed sleeps or `networkidle`.
- Per-domain concurrency limit (max 2 concurrent per ATS host) and per-company pacing.
- Hard timeout 180 s per task; screenshot + redacted HTML snapshot on every step and on failure.
- Blocker detected → stop, status `needs_user_action`, notify user with "Finish in browser" deep link (opens the job with the extension ready).
- Containers: `mcr.microsoft.com/playwright/python` base image, autoscaled on `browser_apply` queue depth, `--max-tasks-per-child=20` to recycle memory.
- Track success/failure per `ats_type` + `flow_version` → nightly job updates `ats_flows.success_rate_7d`; auto-disable `trusted` if success < 90%.

---

## 11. AUTOPILOT — CONTINUOUS AUTO-APPLY LOOP

`POST /autopilot/start` (validate profile completeness ≥ 80, preferences set, consents, plan, credits) → create `campaign` → return `campaign_id` instantly.

Celery Beat runs `autopilot_tick` every 15 minutes for each active campaign inside its schedule window:
1. Compute remaining daily budget = min(campaign.daily_limit, plan cap) − applications created today (IST).
2. Pull the best unqueued `job_matches` with decision `apply` (fresh jobs first, diversified: max 2 per company per week, never re-apply to the same job or the same company+title within 60 days).
3. For each: reserve credits (`credit_holds`) → create `application` (`preparing`) → chain: `generate_documents` → `resolve_answers` → (`form_schema` if missing) → `assisted_fill` (review mode) or `auto_submit` (if all auto-submit conditions pass).
4. Pace submissions across the day (randomized spacing, not bursts).
5. Daily summary notification at 8 PM IST: applied, waiting for review, needs action, new matches.
Pause automatically when: credits exhausted, 3 consecutive failures on the same ATS, user inactive in review for 7 days (review mode), or the user pauses.

---

## 12. REVIEW QUEUE

`GET /review-queue` returns applications in `ready_for_review` and `needs_user_action`, sorted by match score and job freshness, each with: job summary, match explanation, tailored resume diff vs master (with flagged claims), cover letter, every form answer (source + confidence badge), step screenshots.
Actions: approve (single or bulk), edit any answer/document (edits saved to `answer_edits` and upserted into `answer_bank` with source `user_edit`), regenerate a document, reject (with reason → feeds matching learning), "finish in browser".

---

## 13. APPLICATION TRACKER

- Timeline from `application_events`; statuses from section 4.
- Manual status updates + notes + follow-up date; auto follow-up reminder 7 days after submission with no update.
- Optional later: email forwarding inbox (`apply+{user_token}@inbound.applyon...`) to auto-detect interview invites/rejections with Gemini classification (design the table/endpoint now, build in the last phase).
- Each application stores the exact resume version, cover letter and answers submitted (so the user can see what the recruiter saw).

---

## 14. NOTIFICATIONS
`notifications` queue only. Channels: in-app (table + `GET /notifications`, live delivery via Supabase Realtime), email via Resend (templated: welcome, review ready, needs action, daily digest, weekly report, low credits, payment receipts). User-level channel preferences. Never block other queues.

---

## 15. CREDITS, PLANS & PAYMENTS

Plans (config file, not hard-coded): `free`, `starter`, `pro`, `elite` with: monthly AI credits, monthly apply credits, max daily applications, auto-submit allowed (pro+), priority queue (elite).
Credit costs (config): resume tailoring 1 AI, cover letter 1 AI, screening answers 1 AI per application, extension autofill 1 apply, assisted apply 1 apply, auto-submit 2 apply, priority processing +1.
Rules: reserve before enqueue (`credit_holds`), capture after success, release on failure/timeout (hold expiry job every 10 min). Ledger is append-only and idempotent.
Razorpay: subscriptions + one-time credit packs; webhook `POST /webhooks/razorpay` with signature verification, idempotent processing; INR pricing; GST-ready invoice data.

---

## 16. ANALYTICS (P2, but design now)
Materialized views refreshed hourly: applications by source / ATS / role / city / resume template / match-score band → response rate, interview rate, time-to-response. Endpoints: `GET /analytics/overview`, `/analytics/funnel`, `/analytics/breakdown?dim=source|role|city|resume_version`. Admin metrics: ingestion volume, match latency, AI cost per user, ATS success rates, queue depths.

---

## 17. API (FastAPI, `/v1`, OpenAPI documented, cursor pagination, consistent error format `{error: {code, message, details}}`)

- Auth/me: `GET /me`, `PATCH /me`, `DELETE /me` (full delete job), `GET /me/export` (async ZIP export)
- Onboarding: `POST /resumes`, `GET /resumes/{id}`, `POST /resumes/{id}/confirm`, `GET /onboarding/next-question`, `POST /onboarding/answer`, `GET /onboarding/status`, `POST /consents`
- Profile: CRUD `/profile`, `/profile/experiences`, `/profile/educations`, `/profile/projects`, `/profile/skills`, `GET /profile/completeness`
- Preferences: `GET/PUT /preferences`
- Answer bank: CRUD `/answers`
- Jobs: `GET /jobs` (matched feed with filters), `GET /jobs/{id}`, `POST /jobs/import` (URL or text → task), `POST /jobs/discover` (on-demand refresh → task), `POST /jobs/{id}/feedback`, `POST /jobs/{id}/dismiss`, `POST /jobs/{id}/save`
- Matches: `GET /matches`, `POST /matches/{job_id}/rescore`
- Documents: `POST /jobs/{id}/tailor` (→ task), `GET /resume-versions/{id}`, `PATCH /resume-versions/{id}`, `POST /resume-versions/{id}/approve`, `GET /resume-versions/{id}/pdf` (signed URL), same for cover letters
- Applications: `POST /applications` (from job), `GET /applications`, `GET /applications/{id}`, `PATCH /applications/{id}`, `POST /applications/{id}/approve`, `POST /applications/approve-bulk`, `POST /applications/{id}/reject`, `POST /applications/{id}/mark-submitted`, `GET /applications/{id}/events`
- Review queue: `GET /review-queue`
- Autopilot: `POST /autopilot/start`, `POST /autopilot/{id}/pause`, `POST /autopilot/{id}/resume`, `GET /autopilot/{id}`, `PATCH /autopilot/{id}`
- Extension: `GET /extension/fill-plan?url=`, `POST /extension/field-feedback`, `POST /extension/auth/exchange`
- Tasks: `GET /tasks/{id}` (live progress comes through Supabase Realtime on the `tasks` table)
- Billing: `GET /billing/plans`, `POST /billing/checkout`, `GET /billing/credits`, `GET /billing/ledger`, `POST /webhooks/razorpay`
- Notifications: `GET /notifications`, `POST /notifications/{id}/read`
- Analytics: section 16
- Admin (role-gated): companies CRUD + CSV import, ATS flow trust toggles, dead-letter queue viewer/replay, user lookup, job moderation
- Health: `GET /health/live`, `GET /health/ready` (DB + Redis)

Every mutating endpoint accepts an `Idempotency-Key` header (stored 24 h in Redis).

---

## 18. QUEUES & RELIABILITY

Queues: `job_ingestion`, `embeddings`, `ai_matching`, `document_generation`, `form_schema`, `browser_automation`, `autopilot`, `notifications`, `maintenance`, `priority` (elite users).
- `acks_late=True`, `task_reject_on_worker_lost=True`, prefetch 1 for browser/AI queues
- Retries: exponential backoff with jitter (max 5; browser max 2), per-task soft/hard time limits
- Dead-letter: tasks that exhaust retries are written to `automation_tasks` with status `dead` + Redis DLQ list; admin replay endpoint
- Idempotency: every task takes an `idempotency_key`; check-and-set in Redis before doing work
- Per-user rate limits (Redis token bucket) and per-plan daily caps enforced in the API AND re-checked in workers
- Graceful shutdown; worker autoscaling based on queue depth

---

## 19. SECURITY & PRIVACY
- Supabase JWT verification (JWKS cached), role claims for admin; CORS locked to the app + extension origins
- All storage private; signed URLs expire in 10 minutes
- Encrypt sensitive profile fields at rest (phone, DOB, CTC) with application-level encryption (Fernet key from env)
- PII redaction in logs, Sentry and HTML snapshots
- Input validation everywhere; SSRF protection for user-pasted URLs (block private IPs, only http/https, size/time limits)
- Secrets only from env / secret manager; never in code
- DPDP: consent records, purpose-limited processing, `DELETE /me` hard-deletes data + files within 24 h (soft delete immediately), data export, retention policy (screenshots deleted after 30 days, HTML snapshots after 7 days)
- Audit log on approvals, submissions, auto-submit decisions, deletions

---

## 20. OBSERVABILITY
Sentry for API + workers; structured JSON logs with `request_id`, `user_id` (hashed), `task_id`; OpenTelemetry traces across API → Celery; Prometheus metrics (queue depth, task latency, success rate per ATS, AI tokens/cost, ingestion counts); Flower dashboard (admin only).

---

## 21. TESTING (required per phase)
- Unit tests for normalizers, dedupe hash, filters, truth checker (many adversarial cases: invented metric, invented tool, changed date), answer resolution, credit ledger (concurrency test)
- Integration tests with testcontainers (Postgres + pgvector, Redis) for API + Celery (eager mode for some, real worker for others)
- Gemini mocked in tests with recorded fixtures; one optional live smoke test behind an env flag
- Playwright tests for every ATS adapter against local fixture pages (never hit real ATS sites in CI)
- Load test (Locust) for the API: p95 < 200 ms at 200 RPS on the read endpoints
- Coverage ≥ 80% on `packages/`

---

## 22. ENVIRONMENT & DEPLOYMENT
`.env.example`:
```
APP_ENV=development
API_BASE_URL=
FRONTEND_URL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWKS_URL=
DATABASE_URL=            # Supabase pooled connection (asyncpg)
DIRECT_DATABASE_URL=     # for migrations
REDIS_URL=
GEMINI_API_KEY=
GEMINI_MODEL_LITE=
GEMINI_MODEL_FAST=
GEMINI_MODEL_SMART=
GEMINI_EMBED_MODEL=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
RESEND_API_KEY=
EMAIL_FROM=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
FIELD_ENCRYPTION_KEY=
SENTRY_DSN=
EXTENSION_ID=
CRAWLER_USER_AGENT=ApplyonBot/1.0 (+https://applyon.in/bot)
```
Local: `docker compose up` runs api, worker (per queue group), beat, browser worker, redis, flower; Supabase via the Supabase CLI.
Production: API + CPU workers on Railway/Render/Fly.io (or Cloud Run); browser workers as a separate autoscaled service; managed Redis (Upstash/Railway); Supabase Pro. GitHub Actions CI: ruff, mypy, pytest, Docker build; CD on main.

---

## 23. PERFORMANCE PLAYBOOK (apply everywhere)

**API (read path)**
- Verify Supabase JWTs locally with cached JWKS (no network call per request).
- The jobs feed reads only precomputed `job_matches` joined to `jobs` with keyset (cursor) pagination — never computes matches during a request.
- Select only the columns a screen needs; never return `description_html` in list endpoints.
- Cache dashboard counters and plan/credit balances in Redis (short TTL, invalidated on write).
- Use `orjson` responses, gzip/brotli at the proxy, HTTP keep-alive.
- Every list query is backed by an index; CI runs `EXPLAIN` checks on the 10 hottest queries and fails on sequential scans of large tables.

**Write path & workers**
- Bulk operations: insert jobs with `INSERT ... ON CONFLICT (content_hash) DO UPDATE` in batches of 500; create matches with set-based SQL, not row-by-row ORM loops.
- Use Celery `chord`/`chain` for the application pipeline; keep each task small and idempotent so a retry re-does one step, not the whole pipeline.
- Put large payloads (job descriptions, documents) in the DB/storage and pass IDs through the queue, never big blobs.
- Separate `priority` queue for user-waiting work (pasted job, tailor now) so it's never stuck behind Autopilot batches.

**Database hygiene**
- Partition `application_events`, `ai_usage` and `audit_log` by month.
- Archive inactive jobs older than 90 days to a `jobs_archive` table; keep `jobs` small and hot.
- Autovacuum tuning on high-churn tables (`jobs`, `job_matches`, `tasks`).
- pgvector: HNSW with `m=16, ef_construction=64`; set `hnsw.ef_search` per query; always pre-filter with SQL before the vector search (use iterative index scans if the pgvector version supports them).

## 24. CAPACITY TARGETS (design for these from day one)
- 50,000 users, 5,000 daily-active Autopilot users, 300,000 active jobs, 100,000 new/changed jobs per day.
- 25,000 applications prepared per day; median time from "job posted" to "match visible to user" < 30 minutes.
- API p95 < 200 ms on reads, < 400 ms on writes. Tailored documents ready in < 20 s (p95) for user-waiting requests.
- Browser workers: assisted fill < 60 s median per application on trusted ATS flows.
Provide a load-test script (Locust) and a capacity doc estimating containers needed per role at these numbers.

## 25. AI QUALITY EVALUATION (the real differentiator)
- Build `evals/` with a golden dataset: 50 anonymized profiles × 100 real job descriptions (Indian and global) with human-labeled expected match decisions, plus 50 tailoring cases with known "forbidden facts".
- Metrics: match decision accuracy, score correlation with labels, fabrication rate (must be 0 on the truth checker and < 1% on human review), keyword coverage, answer acceptance rate (how often users approve AI answers without edits — tracked in production).
- `make eval` runs the suite against the configured models and prompt versions and writes a report; CI blocks prompt or model changes that lower any metric.
- Production feedback loop: every user edit, rejection and dismiss reason is stored and reviewed weekly to update prompts and the answer bank logic.

## 26. COST GUARDRAILS
- Per-user daily AI budget (tokens) by plan, enforced in `GeminiClient` before each call; per-feature cost dashboard from `ai_usage`.
- Global circuit breaker: if hourly AI spend exceeds a configured limit, pause Autopilot pre-generation (user-waiting requests continue) and alert.
- Skip AI whenever deterministic logic can decide (hard filters, answer bank hits, regex extraction).
- Cache everything that is deterministic for the same inputs (parsing, scoring, form schemas, field-label mappings).
- Monthly cost report per user cohort to check plan pricing against real cost.

## 27. RELIABILITY OF THE APPLICATION ENGINE
- **Kill switches:** `feature_flags` can disable any source connector, ATS adapter, AI feature or auto-submit globally in seconds without a deploy.
- **ATS canary checks:** every 6 hours, for each adapter, open 3 live job application pages in dry-run mode (fill nothing sensitive, never submit), confirm the expected fields and steps are still detected, and alert + set `trusted=false` automatically if the structure changed.
- **Verify before submit:** after filling, read every field value back from the page and compare to the plan; any mismatch → stop and send to review.
- **Proof of submission:** store the confirmation page screenshot and any confirmation text/email reference on the application.
- **Duplicate protection:** a unique constraint on (user_id, canonical_job_id) for submitted applications, checked again inside the submit task right before clicking submit.

## 28. BUILD PHASES — after EACH phase: run ruff, mypy, pytest; fix everything; write a short summary + how to verify locally (curl/HTTPie examples); update docs; then STOP and wait for "continue".
Each phase ends with the front end wired to the new endpoints, so the product is usable after every phase (replace the matching parts of the Next.js mock `src/lib/api/` with a typed client generated from the OpenAPI spec).

1. **Foundation:** repo layout, uv workspace, settings, Docker Compose, single image with api/worker/beat entrypoints, Supabase JWT auth, pooler settings, error format, health checks, Celery + Redis with all queues, `tasks` table + Realtime, feature flags, CI.
2. **Database:** all Alembic migrations (section 4), pgvector, indexes, partitions, RLS policies, seed data (role/skill taxonomies, city aliases, companies CSV, field-label synonyms, plans config).
3. **Profile & onboarding:** resume upload/parse/confirm, profile CRUD, profile versions + embeddings, questionnaire engine + v1 question file, answer bank, consents, completeness score. Front end: onboarding wizard + profile pages live.
4. **Jobs & matching:** connectors (Adzuna, Greenhouse, Lever, Ashby, Arbeitnow, manual URL), ATS detection, normalization, dedupe (incl. cross-source), scam filter, embeddings, preference buckets, hard filters, vector ranking, batched Gemini scoring, caching, feedback, Beat schedules. Front end: jobs feed + job detail live.
5. **Documents + eval harness:** tailoring, cover letters, screening answers, truth checker, templates, PDF, versioning, `evals/` suite. Front end: tailor page live.
6. **Applications + tracker + review queue:** applications, events, form schema extraction (API-based first), field-label mapping, answer resolution, review queue, tracker. Front end: review queue + tracker live.
7. **Chrome extension (first apply channel):** MV3 extension, auth exchange, ATS detection, fill-plan, autofill for Greenhouse/Lever/Ashby/Workday/SmartRecruiters/Workable/generic, file attach, review highlights, mark-submitted, field feedback. → The product is launchable for beta users at the end of this phase.
8. **Credits & billing:** plans config, ledger + holds, enforcement in API + workers, Razorpay subscriptions/packs + webhooks, cost guardrails.
9. **Browser workers + Autopilot:** Playwright service, adapters + fixtures, assisted apply (stop before submit), approve → submit, verify-before-submit, blocker handoff, screenshots, canaries, ATS success tracking; campaigns, autopilot tick, pacing, diversification, auto-submit gating, auto-pause, daily digest.
10. **Notifications, analytics, admin, hardening:** email templates + preferences, materialized views + analytics APIs, admin endpoints + DLQ replay, PII encryption, retention jobs, export/delete, load tests vs section 24, observability (Sentry + logs first, then OpenTelemetry/Prometheus), production deployment docs.
