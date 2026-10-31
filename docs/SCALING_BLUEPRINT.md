# Applyon scaling blueprint

From 14 companies and one VM to thousands of boards, fast matching, and safe, evidenced submissions.
It builds on what exists today: FastAPI, Celery with Redis, Postgres with pgvector on Neon, Playwright,
a Google Compute Engine VM, and Vercel. Most of the work is **adding tables and splitting workers**,
not rewriting.

**Principles**

1. **Postgres is the source of truth for every state.** Queues only carry IDs. A lost message is
   recovered by the next scheduler pass, never by re-running a side effect blindly.
2. **Do expensive work lazily.** Fetch only boards that are due, embed only changed content, call an LLM only
   for a shortlist, and prepare an application only when it will be used.
3. **Never guess on the user's behalf.**
   - No invented facts.
   - No AI answers to compliance questions.
   - No CAPTCHA, login or anti-bot bypass.
   - Nothing is marked "submitted" without evidence.
   - An uncertain submit becomes `needs_action`, never a retry.
4. **Cache by content, not by time.** Keys are `(job content_hash, profile_version)`, so caches never go stale
   and never need manual busting.

---

## 1. Target architecture

```
                 ┌──────────── Vercel (Next.js) ────────────┐
                 │  app UI · handoff page · admin/health    │
                 └───────────────┬──────────────────────────┘
                                 │ HTTPS (REST + SSE)
┌────────────────────────────────▼─────────────────────────────────────────┐
│ api (FastAPI, stateless, 2+ replicas)                                      │
│  auth (Firebase) · jobs/matches/applications · handoff tokens · admin      │
└───────┬──────────────────────────────┬───────────────────────────────────┘
        │ SQL                          │ enqueue IDs (Celery / Redis)
┌───────▼────────┐   ┌────────────────▼───────────────────────────────────┐
│ Postgres       │   │ Redis: broker · rate-limit buckets · locks · caches │
│ (Neon)         │   └──┬──────────┬───────────┬───────────┬─────────────┘
│ + pgvector     │      │          │           │           │
│ + FTS (GIN)    │  ┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌────▼─────┐
└───────▲────────┘  │ingest │ │ match   │ │ prepare │ │ browser  │  ← separate worker pools,
        │           │workers│ │ workers │ │ workers │ │ workers  │    scaled independently
        └───────────┴───────┴─┴─────────┴─┴─────────┴─┴──────────┘
                        │                       │           │
                  ATS APIs, OpenWebNinja    Gemini      ATS forms (Playwright)
                                                            │
                                            GCS bucket: screenshots, DOM snapshots
```

### Services and workers

| Process | Responsibility | Concurrency (start) | Scale trigger |
|---|---|---|---|
| `api` | REST/SSE, auth, enqueue, handoff tokens, admin | 2 uvicorn workers | p95 latency > 300 ms |
| `scheduler` (Celery beat, exactly one) | Ticks only: "enqueue what's due". Never does work itself. | 1 | — |
| `ingest` worker | Discovery, board fetch, normalize, dedupe, mark-and-sweep closures | 8 (I/O bound, gevent pool) | `ingest.fetch` queue lag > 10 min |
| `embed` worker | Batch-embed new or changed jobs and profiles | 2 | `embed.batch` depth |
| `match` worker | Per-user incremental matching, LLM shortlist scoring | 4 | match latency SLO |
| `prepare` worker | Resume and cover-letter variants, form-schema fetch, answer plan, truth check | 2 | prepare backlog |
| `browser` worker | Form-schema scraping fallback, submission, evidence capture | 1–2 per 2 GB RAM | submit queue age > 15 min |

Today all of these run in one `worker` container (`infra/gcp/docker-compose.yml`). Phase 1 splits them
into four Compose services from the **same image**, with different `--queues`. That's the only change
needed to scale each one independently.

### Queues (Celery, Redis broker)

| Queue | Message | Producer | Notes |
|---|---|---|---|
| `ingest.schedule` | — | beat, every 60 s | Picks due boards with `SKIP LOCKED` and fans out |
| `ingest.fetch` | `board_id` | scheduler | Per-host token bucket inside the task |
| `ingest.discover` | `candidate_id` | API (user submissions), fetch (outbound ATS links), aggregator ingest | Detects the ATS and creates `ats_boards` rows |
| `ingest.aggregator` | `(source, query_key)` | beat, per preference bucket | OpenWebNinja; credit budget and 12 h query cache (already built) |
| `embed.batch` | list of `job_id` / `profile_version_id` | fetch, profile save | Batches of 100 |
| `match.user` | `user_id` | new-jobs event per bucket, preference change, profile change | Incremental: only jobs newer than the user's watermark |
| `match.llm` | `user_id` + shortlist | `match.user` | Rate-limited; daily per-user budget |
| `prepare.app` | `application_id` | autopilot tick, "Prepare" click | Lazy |
| `browser.submit` | `application_id` | approve, hybrid auto-approve | Lease-based; never retried automatically |
| `browser.scan` | `job_id` | `prepare.app` when no API schema exists | Low priority |
| `notify` | `notification_id` | anywhere | Email or push |
| `maintenance` | — | beat, hourly or nightly | Health rollups, expiry sweep, artifact retention |

Celery settings that matter:
- `task_acks_late=True` and `worker_prefetch_multiplier=1` on `browser.*` and `prepare.*`.
- `visibility_timeout` must be longer than the slowest task (about 15 min).
- Every task must be idempotent on its ID.

---

## 2. Database schema (changes to the current schema)

Existing tables stay: `companies`, `jobs`, `job_aliases`, `job_embeddings`, `job_matches`, `applications`,
`application_events`, `automation_artifacts`, `job_form_schemas`, `answer_bank`, `ai_usage` and the others. Below, **new** tables
and **added columns** only. Migrations are additive.

```sql
-- One row per ATS board we know about. "Company" is the business; a company can have several boards.
CREATE TABLE ats_boards (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       uuid REFERENCES companies(id),
  ats_type         text NOT NULL,          -- greenhouse|lever|ashby|workday|smartrecruiters|workable|recruitee|...
  board_token      text NOT NULL,          -- greenhouse token, lever slug, workday tenant/site, ...
  api_url          text NOT NULL,          -- what we fetch
  host             text NOT NULL,          -- rate-limit key, e.g. boards-api.greenhouse.io
  status           text NOT NULL DEFAULT 'active',  -- active|paused|dead|blocked
  discovered_via   text NOT NULL,          -- seed|user|apply_link|career_page|sitemap|common_crawl|aggregator
  priority         smallint NOT NULL DEFAULT 5,     -- 1 = refresh most often (has subscribers' roles/cities)
  fetch_interval   interval NOT NULL DEFAULT '6 hours',  -- adaptive, see §3.4
  next_fetch_at    timestamptz NOT NULL DEFAULT now(),
  etag             text, last_modified text,          -- HTTP conditional requests
  board_hash       text,                              -- hash of (external_id, updated_at) list
  open_job_count   int NOT NULL DEFAULT 0,
  consecutive_failures int NOT NULL DEFAULT 0,
  circuit_open_until timestamptz,
  last_success_at  timestamptz, last_change_at timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ats_type, board_token)
);
CREATE INDEX ats_boards_due ON ats_boards (next_fetch_at) WHERE status = 'active';

-- Every fetch attempt. Drives source-health dashboards and alerts.
CREATE TABLE board_fetch_runs (
  id bigserial PRIMARY KEY,
  board_id uuid NOT NULL REFERENCES ats_boards(id),
  started_at timestamptz NOT NULL, duration_ms int,
  http_status int, outcome text NOT NULL,      -- changed|unchanged|not_modified|error|circuit_open
  error_class text,                             -- timeout|http_4xx|http_5xx|parse|rate_limited
  jobs_seen int, jobs_new int, jobs_updated int, jobs_closed int, bytes int
);
CREATE INDEX ON board_fetch_runs (board_id, started_at DESC);

-- Discovery inbox: anything that might lead to a board.
CREATE TABLE company_candidates (
  id bigserial PRIMARY KEY,
  url text NOT NULL, domain text NOT NULL,
  source text NOT NULL,                         -- user|apply_link|career_page|sitemap|common_crawl|aggregator
  status text NOT NULL DEFAULT 'pending',       -- pending|resolved|no_ats|failed
  detected_ats text, board_id uuid REFERENCES ats_boards(id),
  attempts smallint NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (domain, source)
);

ALTER TABLE jobs
  ADD COLUMN board_id uuid REFERENCES ats_boards(id),
  ADD COLUMN status text NOT NULL DEFAULT 'open',           -- open|closed
  ADD COLUMN first_seen_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN last_seen_at  timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN closed_at timestamptz,
  ADD COLUMN canonical_job_id uuid REFERENCES jobs(id),      -- NULL = this row is canonical
  ADD COLUMN apply_ats text,                                 -- ATS of the apply URL (may differ from source)
  ADD COLUMN apply_mode text NOT NULL DEFAULT 'handoff',     -- auto|handoff (auto only for supported, captcha-free forms)
  ADD COLUMN role_family text,                               -- data|frontend|backend|pm|design|... (for buckets and variants)
  ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (
      setweight(to_tsvector('english', coalesce(title,'')), 'A') ||
      setweight(to_tsvector('english', coalesce(array_to_string(required_skills,' '),'')), 'B') ||
      setweight(to_tsvector('english', left(coalesce(description_text,''), 20000)), 'C')) STORED;
-- content_hash already exists: keep it as sha256(title|location|description|apply_url) of the *normalized* job.
CREATE UNIQUE INDEX jobs_board_ext ON jobs (board_id, external_id) WHERE board_id IS NOT NULL;
CREATE INDEX jobs_open_recent ON jobs (first_seen_at DESC) WHERE status = 'open' AND canonical_job_id IS NULL;
CREATE INDEX jobs_search ON jobs USING gin (search_tsv);
CREATE INDEX jobs_filter ON jobs (role_family, seniority, status) WHERE canonical_job_id IS NULL;
CREATE INDEX jobs_locations ON jobs USING gin (locations);

-- Durable match-score cache: one LLM call per (profile version, job content), ever.
CREATE TABLE match_scores (
  user_id text NOT NULL, profile_version_id uuid NOT NULL,
  job_id uuid NOT NULL, job_content_hash text NOT NULL,
  rule_score smallint NOT NULL, lexical_score real, vector_score real,
  llm_score smallint, llm_model text, reasons jsonb, gaps jsonb,
  computed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (profile_version_id, job_id, job_content_hash)
);

-- Per-user watermark so matching is incremental.
ALTER TABLE job_preferences ADD COLUMN matched_until timestamptz;

-- Application state machine: see §5. Add lease, idempotency and handoff fields.
ALTER TABLE applications
  ADD COLUMN state text NOT NULL DEFAULT 'matched',
  ADD COLUMN state_changed_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN lease_owner text, ADD COLUMN lease_until timestamptz,
  ADD COLUMN submit_attempts smallint NOT NULL DEFAULT 0,
  ADD COLUMN needs_action_reason text,          -- captcha|login|unsupported_ats|uncertain_submit|job_closed|missing_answer
  ADD COLUMN resume_variant_id uuid, ADD COLUMN evidence jsonb;  -- {before_png, after_png, dom_gz, final_url, confirmation_text}
CREATE INDEX applications_work ON applications (state, state_changed_at);

-- One-click handoff (CAPTCHA, login, Workday, LinkedIn, Naukri, ...).
CREATE TABLE handoff_sessions (
  token text PRIMARY KEY,                       -- 32 random bytes, url-safe
  application_id uuid NOT NULL REFERENCES applications(id),
  user_id text NOT NULL,
  expires_at timestamptz NOT NULL,              -- 2 hours
  opened_at timestamptz, filled_at timestamptz, completed_at timestamptz,
  completion text                               -- extension_confirmed|user_confirmed|abandoned
);

-- Reusable resume variants per role family (cuts tailoring cost ~80%).
CREATE TABLE resume_variants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL, profile_version_id uuid NOT NULL, role_family text NOT NULL,
  content jsonb NOT NULL, truth_check jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (profile_version_id, role_family)
);

-- Answer bank gets a stable question fingerprint and provenance.
ALTER TABLE answer_bank
  ADD COLUMN question_fingerprint text,         -- normalized question → canonical key or sha1
  ADD COLUMN provenance text NOT NULL DEFAULT 'user',   -- user|profile|ai_draft_approved
  ADD COLUMN is_compliance boolean NOT NULL DEFAULT false;
CREATE UNIQUE INDEX answer_bank_q ON answer_bank (user_id, question_fingerprint);
```

**Retention:**
- `board_fetch_runs` keeps 30 days of rows, rolled up nightly into `source_health_daily`.
- Evidence files live in a GCS bucket with a 180-day lifecycle rule. Postgres stores only their paths.

---

## 3. Ingestion at scale

### 3.1 Company discovery funnel

All sources feed `company_candidates`, and one resolver turns candidates into `ats_boards`:

| Source | How | Expected yield |
|---|---|---|
| Seed list | `infra/seed/companies.csv`, extended to about 500 Indian and remote-friendly tech companies | High quality |
| Apply-link mining | Already built: aggregator jobs whose apply URL is an ATS board | Grows daily, for free |
| Outbound ATS links | While fetching a board or a job description, extract links to other boards | Small |
| User submissions | `POST /v1/companies/suggest {url}`, with "Add a company" in the UI | Targeted to what users want |
| Career-page crawl | For a company domain: fetch `/careers`, `/jobs` and the homepage, then look for ATS links or embed scripts (`boards.greenhouse.io/embed`, `jobs.lever.co`, `jobs.ashbyhq.com`, `myworkdayjobs.com`, `smartrecruiters.com`) | Medium |
| Common Crawl index | Monthly query of the CC index for `boards.greenhouse.io/*`, `jobs.lever.co/*`, `jobs.ashbyhq.com/*`; collect distinct tokens | **Thousands of boards in one run**, free |
| Aggregators | OpenWebNinja results: company name + apply URL → candidate | Ongoing |

**Resolver (`ingest.discover`):**
1. Normalize the URL.
2. Run `detect_ats(url)`, which already exists.
3. If the result is unknown, fetch the page once and look for ATS fingerprints.
4. Extract the board token.
5. Validate it with one API call (e.g. `GET boards-api.greenhouse.io/v1/boards/{token}/jobs`, expecting 200 with jobs).
6. Upsert `ats_boards` and link or create the `companies` row.

To keep the index India-focused, give `priority` 1–3 to boards with at least one India or remote location in their
last fetch, and 7–9 to others. Low-priority boards are still kept, at the slowest refresh rate.

### 3.2 ATS detection and connectors

| ATS | Listing endpoint (public) | Incremental signal | Auto-apply |
|---|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{t}/jobs?content=true` | per-job `updated_at` | ✅ (form questions via `/jobs/{id}?questions=true`, no browser needed) |
| Lever | `api.lever.co/v0/postings/{t}?mode=json` | `createdAt` and content hash | ❌ hCaptcha → handoff |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{t}?includeCompensation=true` | content hash | ✅ where no CAPTCHA |
| Workday | `POST https://{tenant}.wd{n}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs` (paged JSON) | `postedOn`, hash | ❌ login wall → handoff |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{id}/postings` | `releasedDate` | ❌ handoff (first version) |
| Workable, Recruitee | Public JSON widgets | hash | ❌ handoff (first version) |
| LinkedIn, Naukri, Indeed | **Only through licensed APIs** (OpenWebNinja). Never scrape or automate. | — | ❌ handoff only |

Each connector implements a single interface (`BaseJobConnector` already exists):

```python
class BoardConnector(Protocol):
    ats_type: str
    def host(self, board) -> str: ...                    # rate-limit key
    async def fetch(self, board, etag, last_modified) -> FetchResult  # status, jobs[], etag, not_modified
    def normalize(self, raw) -> JobIn: ...               # pure, unit-tested with recorded fixtures
    async def form_schema(self, job) -> FormSchema | None  # API-based where possible; None → browser.scan
```

`apply_mode` is decided at normalization time: `auto` only if the apply ATS is supported **and** has no known
CAPTCHA (Greenhouse or Ashby, with a per-board override after a CAPTCHA is seen). Everything else is `handoff`.
Users see this up front ("Auto-apply" or "1-click assisted").

### 3.3 Incremental fetch

```python
async def fetch_board(board_id):
    board = load(board_id)
    if board.circuit_open_until and board.circuit_open_until > now(): return record(board, "circuit_open")
    async with host_limiter(board.host):                      # §3.5
        res = await connector.fetch(board, board.etag, board.last_modified)
    if res.not_modified:                                       # 304: cheapest path
        return reschedule(board, changed=False)
    board_hash = sha256(sorted((j.external_id, j.updated_at) for j in res.jobs))
    if board_hash == board.board_hash:                         # same ids and timestamps: skip normalize
        return reschedule(board, changed=False)
    seen = set()
    for raw in res.jobs:
        job_in = connector.normalize(raw); seen.add(job_in.external_id)
        upsert_job(board, job_in)        # INSERT … ON CONFLICT (board_id, external_id) DO UPDATE
                                         # only when content_hash differs → then enqueue embed + mark "changed"
    close_missing(board, seen, fetch_complete=res.complete)    # §3.7
    board.board_hash = board_hash
    reschedule(board, changed=True)
```

### 3.4 Staggered, adaptive schedule

The scheduler (`ingest.schedule`, every 60 s):

```sql
SELECT id FROM ats_boards
WHERE status='active' AND next_fetch_at <= now()
  AND (circuit_open_until IS NULL OR circuit_open_until < now())
ORDER BY priority, next_fetch_at
LIMIT 200
FOR UPDATE SKIP LOCKED;          -- then set next_fetch_at = now() + interval '30 min' as a claim
```

**Rescheduling rules:**
- `next_fetch_at = now() + fetch_interval × random(0.85, 1.15)`. The jitter spreads load across the hour.
- **Adaptive interval:**
  - If something changed, `fetch_interval = max(1h, interval × 0.7)`.
  - If unchanged, `min(24h, interval × 1.3)`.
  - Boards that post often converge to 1–2 h; quiet ones to 24 h.
- **Priority cap:** boards matching an active preference bucket are capped at 3 h.

**Capacity check:**
- 5,000 boards at an average 8 h interval is about 15,000 fetches a day, or about 10 a minute. That's trivial for one ingest worker.
- 50,000 boards is about 100 a minute, which is still one VM.

### 3.5 Rate limiting, retries, circuit breakers

- **Per-host token bucket in Redis** (Lua script, atomic). Defaults:
  - `boards-api.greenhouse.io` 5 req/s
  - `api.lever.co` 2/s
  - `api.ashbyhq.com` 2/s
  - `*.myworkdayjobs.com` 1/s per tenant
  - anything unknown: 1/s
  - The table lives in config, so it can change without a deploy.
- **Per-host concurrency semaphore** (Redis, with a TTL lease): at most 4 in flight per host.
- **Retries inside the task for transient errors** (timeouts, 429, 5xx): exponential backoff
  `min(60s, 2^attempt) + jitter`, up to 3 attempts. Honor `Retry-After`.
- **No in-task retries for 4xx other than 429.** For example, a 404 means the board was renamed or deleted:
  after 3 consecutive 404s set `status='dead'` and re-resolve the company.
- **Circuit breaker per board:**
  - After 5 consecutive failures, set `circuit_open_until = now() + min(24h, 1h × 2^(failures−5))`.
  - The next success resets it.
- **Circuit breaker per host:** if more than 50% of a host's fetches in the last 10 minutes failed, pause that
  host for 15 minutes (`host_open_until` in Redis).
- Every attempt writes a `board_fetch_runs` row, which is the raw material for the source-health metrics.

### 3.6 Deduplication

Three layers. The canonical row is the one users see; duplicates point to it through `canonical_job_id` plus
the existing `job_aliases` table.

1. **Exact:** the same `(board_id, external_id)`. An upsert updates the row.
2. **Same posting, other source:** the normalized apply URL is equal (`clean_url` already strips tracking).
   Typical case: a JSearch result pointing at a Greenhouse job that's already ingested.
3. **Fuzzy:** `fingerprint = sha1(company_norm | title_norm | primary_city)` matches within 45 days,
   **and** the description's SimHash is within Hamming distance ≤ 6 (64-bit SimHash over word shingles).

**Choosing the canonical row:**
- Prefer, in order: an ATS-direct job, then an aggregator with an ATS apply URL, then any other aggregator. Within the same
  rank, keep the oldest `first_seen_at`.
- When a better source arrives later, swap the canonical row and keep the aliases.
- Track the **duplicate rate** = aliases created ÷ jobs ingested, per source.

### 3.7 Closed and expired jobs

- **ATS boards (mark and sweep):**
  - After a complete successful fetch, open jobs on that board that are missing from the response get
    `status='closed', closed_at=now()`.
  - Guards: skip the sweep if the response looks truncated (`jobs_seen < 50%` of `open_job_count`
    and more than 10 jobs were open), or on any pagination error.
  - A job that reappears is reopened.
- **Aggregator jobs:**
  - Close them when they haven't been re-seen for 21 days.
  - Weekly, also check the apply URL of open matched jobs with `HEAD`/`GET` (rate-limited). A 404 or 410, or a
    "no longer accepting" text pattern, closes the job.
- **Effects on applications:**
  - Closing a job moves its `prepared` or `awaiting_review` applications to `needs_action` with
    `reason=job_closed`, and notifies the user.
  - Submissions in flight check the job's `status` before opening the browser.

---

## 4. Matching pipeline (fast and cheap)

### Event-driven, incremental, bucketed

`preference_buckets` already exists, so use it as the routing table:

1. **Group users into buckets** by `(role_family, seniority, city|remote)`.
2. **New or changed canonical jobs** are tagged with `role_family` (cheap keyword rules, LLM fallback for unknown
   titles, cached per normalized title).
3. **Route them to buckets.** Each affected bucket enqueues `match.user` for its members, **debounced** with a
   Redis `SET NX` of 10 minutes per user.
4. **`match.user` only considers jobs where `first_seen_at > matched_until`**, plus jobs whose content hash changed.
   So a run handles dozens of jobs, not thousands.
5. **A full re-match** (watermark reset) happens only when the user's profile version or preferences change.

### Stages inside `match.user`

| Stage | What | Cost | Output |
|---|---|---|---|
| 1. SQL pre-filter | `status='open' AND canonical_job_id IS NULL`, role-family or title patterns (existing `role_title_patterns`), location or remote-in-reach (existing), experience band, salary floor, exclusions | ms (indexed) | ≤ 2,000 ids |
| 2. Lexical | `ts_rank_cd(search_tsv, q)`, where `q` = target roles (weight A) + top 15 evidenced skills (B). Use ParadeDB `pg_search` BM25 only if the host offers it; `ts_rank_cd` is good enough to start. | ms | top 300 |
| 3. Vector | `1 - (je.embedding <=> :profile_vec)`, HNSW index (exists), on the stage-1 set | ms | top 300 |
| 4. Fuse + rules | Reciprocal-rank fusion of 2 and 3, then the existing `rule_based_score` (skills overlap, title fit, seniority) | ms | top 50, `rule_score` 0–100 |
| 5. LLM shortlist | Only jobs with `rule_score ≥ user threshold − 10` that have **no cached** `match_scores` row for `(profile_version, job_id, content_hash)`; at most **N/day** per plan (free 10, paid 40) | ~$0.0003/job | `llm_score`, reasons, gaps |

```python
def llm_score_shortlist(user, candidates):
    todo = [c for c in candidates if not cached(user.profile_version, c.job_id, c.content_hash)]
    todo = todo[: budget_left_today(user)]
    for batch in chunks(todo, 5):                  # 5 jobs per prompt, fast "lite" model, structured output
        results = gemini.generate_structured(MATCH_PROMPT(profile_brief(user), batch), MatchBatch)
        save_match_scores(user, results)           # durable, re-used forever for this profile+job content
```

**Cost:**
- Each job's text (≈1.5k tokens) goes into at most one prompt per profile version.
- At 10 LLM-scored jobs per user per day, roughly $0.10 per user per month.
- **Embeddings:** one per job `content_hash` and one per profile version, batched 100 per call. They're never recomputed
  unless the content changes.

**Display score:**
- `final = llm_score` when present, otherwise `rule_score`.
- Always show *why*: the reasons, plus the skills matched and missing.
- Matches are written to `job_matches` (exists) with `match_scores` as the cache behind them.

**Latency targets:**
- New job → in matched users' feeds within 15 minutes (p95).
- "Find jobs now" click → first results within 5 s (stages 1–4 synchronous; LLM afterwards, pushed over SSE).

---

## 5. Application preparation (only when needed)

**Triggers** (nothing is prepared otherwise):
1. The autopilot tick picks top matches above the threshold, within the daily cap minus what's already prepared.
2. The user opens a job and clicks **Prepare**.
3. The user clicks **Apply** on a handoff-only job.

**`prepare.app` steps:**
1. **Resume:** take the `resume_variants` row for `(profile_version, role_family)`, or create it once with
   the existing guarded tailoring engine. Then a cheap per-job pass reorders bullets and skills against the job's
   keywords, with **no new content** allowed. The existing `verify_rewrite` and `truth_checker` gates stay mandatory: if
   either fails, fall back to the variant or the master resume and record why.
2. **Cover letter:** a template per `role_family` (generated once per profile version), plus 2–3 job-specific
   sentences grounded in the job description and real experience. Skippable per user.
3. **Form schema** (cheapest first):
   - Cache: `job_form_schemas` (exists), keyed by job, plus a board-level template (most Greenhouse boards share
     their base questions).
   - ATS API: Greenhouse `?questions=true`; Ashby posting API.
   - Browser scan: `browser.scan`, only as a last resort.
4. **Answer plan** for each question:
   - Normalize it to `question_fingerprint` (canonical keys from `form_schema.py`, otherwise a normalized-text hash).
   - Resolve in this order:
     1. **profile facts** (`rule_based_answer`, exists)
     2. **answer bank** (exact fingerprint)
     3. **compliance classifier**: visa, sponsorship, work authorization, relocation, criminal record, age,
        disability, veteran, EEO, salary history where banned. These **always** need a user answer, stored once with
        `is_compliance=true`, `provenance='user'`.
     4. **AI draft**, for open-ended text only, marked `ai_draft` until the user approves it, then saved to the answer bank
     5. otherwise **unresolved**
5. **Gate:** the state moves to `awaiting_review` only if the truth check passed. An application with unresolved required
   answers can still be reviewed, but it can't be auto-submitted, and it shows the missing questions first.

**Never fabricate:**
- No skill, employer, title, date or number may appear in any output unless it appears in the profile snapshot.
  That's enforced in code by the existing validators, and covered by tests on every prompt change.
- Compliance answers never come from AI or from inference.

---

## 6. Submission architecture

### State machine

```
discovered → matched → preparing → awaiting_review ──approve──▶ approved ──lease──▶ submitting
                   │                     │                                       │
                   │                     └──reject──▶ rejected                   ├─▶ submitted (evidence ✔)
                   └──(handoff-only job)──▶ awaiting_review (handoff)            ├─▶ needs_action (captcha|login|
                                                                                 │     uncertain_submit|job_closed|
                                                                                 │     missing_answer|validation)
                                                                                 └─▶ failed (pre-submit error, safe to retry)
needs_action ──user completes in handoff──▶ submitted (user_confirmed | extension_confirmed)
```

**Transition rules:**
- Every transition is a single SQL `UPDATE … WHERE id=$1 AND state=$expected RETURNING`, followed by an
  `application_events` insert (already exists). Two workers can never both move the same application.
- **`failed` vs `needs_action`:**
  - `failed` means we're certain nothing was sent: the error happened before the submit click. It's retryable
    (max 2 automatic retries, with backoff).
  - Anything after the submit click whose outcome is unclear becomes `needs_action(uncertain_submit)`.
    **It's never retried automatically**, because a double application is worse than a manual check.
- **Leases:**
  - `browser.submit` claims with `UPDATE … SET state='submitting', lease_owner=$worker, lease_until=now()+10min WHERE state='approved'`.
  - A `maintenance` task turns expired `submitting` leases into `needs_action(uncertain_submit)`, never back to
    `approved`.
- **Idempotency:** the approve endpoint takes an `Idempotency-Key` header. A submit task refuses to run if
  `evidence.after_png` already exists.

### Browser worker pool

- **Separation:** a separate `browser` service with its own queue. On a 2 GB VM, one or two Chromium contexts; scale
  out with more `browser` replicas or VMs, never by adding threads.
- **Browser lifecycle:**
  - One long-lived browser per worker process, with a **fresh context per application** (isolated cookies).
  - Recycle the browser every 50 jobs or when RSS exceeds 1 GB.
  - Navigation limit 90 s with one retry in a fresh tab (shipped in PR #8). Action limit 25 s.
  - Images, fonts, media and trackers are blocked.
- **Throttles** (Redis semaphores):
  - at most 1 concurrent submission per `(ats_host, board)`
  - at most 6 submissions per minute per ATS host overall
  - at most 10 per hour per user
  - plus random 20–90 s spacing per user, so submissions don't burst
- **Evidence for every attempt** goes to GCS:
  - a screenshot before submit (form filled), a screenshot after submit
  - the final URL
  - a gzipped DOM snapshot of the confirmation page
  - the matched confirmation text
  - Paths go in `applications.evidence`; users can view them from the application page.
- **Confirmation detection** (all required before `submitted`):
  1. An ATS-specific success signal: Greenhouse's confirmation route or "Thank you for applying" text; Ashby's
     "Application submitted" state. Each signal has recorded fixtures.
  2. No visible validation errors.
  3. Optionally, later: confirmation email detected via the user's connected inbox (opt-in).
  4. Otherwise the result is `needs_action(uncertain_submit)`, with the evidence attached for the user.
- **Blockers:** CAPTCHA, a login wall, MFA or a bot challenge stop the run immediately and become `needs_action`.
  There are **no solver services, no stealth plugins and no proxies to evade blocks.** (Managed browser vendors often
  offer CAPTCHA solving; it must stay disabled.)

### One-click handoff (CAPTCHA, Workday, LinkedIn, Naukri, unsupported ATS)

The goal is that the user finishes in under 60 seconds, in **their own browser session**, solving any CAPTCHA
themselves.

1. **"Apply" button** → `POST /v1/applications/{id}/handoff` returns `{url, token}`: a 2-hour, single-user, single-application token.
2. **With the Chrome extension** (an extension API already exists):
   1. The app opens the apply URL with `#applyon=<token>`.
   2. The extension reads the token and calls `GET /v1/handoff/{token}` for the answer plan, resume file and cover letter.
   3. It fills the fields the user can see, highlights compliance and unresolved questions, and never clicks
      Submit.
   4. The user reviews, solves any CAPTCHA and submits.
   5. The extension watches for the ATS confirmation and calls `POST /v1/handoff/{token}/complete` with the final URL
      and a screenshot, giving `submitted (extension_confirmed)`.
3. **Without the extension:**
   - A side-by-side "answer sheet" page: each question with its prepared answer and a copy button, plus
     resume and cover-letter downloads.
   - The job opens in a new tab.
   - The user clicks **"I submitted it"**, giving `submitted (user_confirmed)`.
4. **LinkedIn and Naukri:** the extension only fills fields in forms the user opened and never navigates or submits.
   If a site's terms forbid even that, the answer sheet is the only mode.

### Proving it works (first-ever real submission)

- **CI fixture site:** a small static clone of a Greenhouse-style and an Ashby-style form, plus confirmation pages, served
  in tests. It exercises fill → submit → confirm → evidence → state on every PR.
- **One controlled live submission per supported ATS**, to a test job posted by a company that agrees, such as a
  friendly startup or your own company's ATS trial. Record the evidence. **Never** test against real employers'
  live jobs.

---

## 7. API design (additions)

All list endpoints use **keyset pagination** (`?cursor=` is an opaque base64 of `(sort_key, id)`), not offsets.

| Method + path | Purpose |
|---|---|
| `GET /v1/jobs?q=&role_family=&city=&remote=&posted_after=&cursor=` | Search the canonical open jobs (FTS + filters) |
| `GET /v1/matches?min_score=&state=&cursor=` | The user's feed, with reasons and `apply_mode` |
| `POST /v1/jobs/{id}/prepare` → `202 {application_id}` | Lazy preparation |
| `GET /v1/applications/{id}` | State, answer plan, unresolved questions, evidence links |
| `POST /v1/applications/{id}/approve` (with `Idempotency-Key`) | `awaiting_review` → `approved` |
| `POST /v1/applications/{id}/handoff` → `{url, token, expires_at}` | Start the one-click handoff |
| `GET /v1/handoff/{token}` · `POST /v1/handoff/{token}/complete` | Extension endpoints (token-scoped, rate-limited) |
| `POST /v1/applications/{id}/confirm-submitted` | Manual confirmation |
| `GET /v1/events` (SSE) | Push: new matches, preparation done, submission result |
| `POST /v1/companies/suggest {url}` | User company submissions → discovery |
| `GET /v1/admin/sources/health?window=24h` | Per-ATS and per-host success rate, latency, error classes |
| `GET /v1/admin/boards?status=&ats=&sort=failures` | Board list with circuit state; `POST /v1/admin/boards/{id}/refresh` |

---

## 8. Caching strategy

| What | Where | Key | TTL / invalidation |
|---|---|---|---|
| Board conditional-fetch state | `ats_boards.etag/last_modified/board_hash` | board | Replaced on change |
| Aggregator query results | Redis (exists) | `owm:q:{source}:{query}` | 12 h |
| Job embeddings | `job_embeddings` | `(job_id, content_hash)` | Recomputed only on content change |
| Profile embedding | `profile_embeddings` | `profile_version_id` | Per version |
| LLM match scores | `match_scores` (durable) | `(profile_version, job, content_hash)` | Never expires; a new version is a new key |
| LLM generations (tailoring, letters) | Redis + `ai_usage` | prompt hash + model | 30 days |
| Form schemas | `job_form_schemas` + board template | job / board | Until the job's content hash changes |
| Role family per title | Redis | normalized title | 90 days |
| User feed page 1 | Redis | `feed:{user}:{prefs_version}` | 5 min, busted by `match.user` |
| Public job pages (SEO, later) | Vercel ISR | job id | Revalidated on change |

---

## 9. Observability and monitoring

- **Logs:** JSON lines with `request_id`, `user_id` (hashed), `board_id`, `job_id`, `application_id`, `task`,
  `attempt`, `duration_ms`. Ship them to Google Cloud Logging, which the VM's ops agent already handles.
- **Errors:** Sentry (`SENTRY_DSN` already in config) for the API and all workers, with the task name as a tag.
- **Metrics:** `board_fetch_runs`, `application_events`, `ai_usage` and `match_scores` are already an event log,
  so **most metrics are SQL**:
  - a `/admin/health` page, or Metabase/Grafana pointed at Neon (read replica later)
  - plus a small Prometheus `/metrics` endpoint for queue depth and lag (Celery inspect or Redis `LLEN`), scraped by
    Cloud Monitoring
- **Alerts** (Cloud Monitoring or Grafana → email or Slack):
  - ingestion success < 90% over 1 h
  - any queue's oldest message > 30 min
  - submissions confirmed < 70% over 24 h for any ATS
  - more than 3 `uncertain_submit` in 1 h
  - LLM spend > 120% of the daily budget
  - the API's 5xx rate > 1%

---

## 10. Implementation plan (build order)

### Phase 1: quick wins (1–2 weeks)
1. **Split worker pools**: `ingest`, `match`, `prepare`, `browser` as separate Compose services on the same image.
   Set `acks_late` and `prefetch=1` for the `prepare` and `browser` queues.
2. **The `ats_boards` + `board_fetch_runs` migration.** Backfill from `companies` (they already hold
   `ats_type` and `ats_board_token`). Move `crawl_due_companies` to the `SKIP LOCKED` scheduler with jitter.
3. **Per-host token bucket and circuit breaker** in the fetch path.
4. **`match_scores` cache plus the `matched_until` watermark.** The LLM only sees uncached shortlist jobs, batched 5
   per prompt. This alone cuts Gemini calls by more than 90%.
5. **Lazy preparation**: only autopilot picks and "Prepare" clicks. Add `apply_mode` on jobs and show it in the UI.
6. **Sentry plus a basic `/admin/health` page** (fetch success by ATS, queue depths).
7. **CI fixture-site test** for fill → submit → confirm.

### Phase 2: ingestion and matching at scale (2–4 weeks)
1. Connectors for **Workday** and **SmartRecruiters** listings (ingest only), plus Workable and Recruitee.
2. **Discovery pipeline**: `company_candidates`, the resolver, career-page crawl, user "suggest a company", and a monthly
   **Common Crawl** import. Target: more than 3,000 active boards.
3. **Adaptive intervals, mark-and-sweep closures, aggregator expiry.**
4. **Three-layer dedupe** with SimHash and the canonical swap.
5. **`search_tsv` + RRF hybrid retrieval** and role-family buckets, so matching is event-driven per bucket.
6. **Resume variants per role family**, and form schemas from ATS APIs (Greenhouse questions endpoint).

### Phase 3: reliable submission and handoff (3–4 weeks)
1. **The full state machine** with leases, idempotency keys and the maintenance sweeper.
2. **Evidence capture to GCS**, plus an evidence viewer in the UI.
3. **ATS-specific confirmation detectors**, each with recorded fixtures.
4. **Handoff**: tokens, the answer-sheet page, and extension fill-only mode for Greenhouse, Lever, Ashby, Workday and
   LinkedIn/Naukri fields.
5. **Compliance-question classifier**, plus asking for those answers once during onboarding.
6. **Controlled live submissions** (one per supported ATS) before turning hybrid mode on for anyone.

### Phase 4: analytics, feedback and growth (ongoing)
1. **Outcome tracking**: interview and rejection via a status the user sets, or an opt-in email parser.
   Feed the outcomes back into the ranking weights (`learned_weights` already exists on preferences).
2. **Per-ATS and per-company conversion dashboards; source ROI** (jobs → matches → approved → interviews per
   source, against credits spent).
3. **Public SEO job pages** (Vercel ISR) and email alerts for new matches.
4. **Paid plans**: higher LLM budgets, more daily applications, priority refresh for a user's target companies.

---

## 11. Technology choices for a small team

| Need | Now (recommended) | When to change | Alternative and tradeoff |
|---|---|---|---|
| Postgres | **Neon** (free → Launch plan): pgvector, branching for migrations | More than about 10 GB, or sustained CPU | **Cloud SQL**: no cold starts or compute limits, about $30+/mo; more operational knobs |
| Redis | Container on the VM (appendonly) | More than one VM needs it | **Memorystore** (about $35/mo, managed) or **Upstash** (serverless, per-request pricing) |
| Queue | **Celery + Redis** (keep) | More than about 5 VMs, or exactly-once needs | **Cloud Tasks / Pub/Sub**: managed retries and DLQs, but a rewrite of task plumbing |
| Scheduling | Celery beat (one instance) + DB-driven due-queries | — | Cloud Scheduler → HTTP endpoints (no singleton beat) |
| Vector search | **pgvector HNSW** (keep) | More than about 5M vectors, or under 20 ms needs | Qdrant / Vertex Vector Search; another system to keep in sync |
| Text search | **Postgres FTS** (`tsvector` + GIN) | Typo tolerance, facets at scale | Typesense / Meilisearch (simple to run); OpenSearch is heavy |
| Browser automation | **Self-hosted Playwright** in `browser` workers | Over about 2,000 submissions a day | Browserless / Browserbase (managed sessions, about $0.01–0.05 each). Keep CAPTCHA solving **off**. |
| Object storage | **GCS** bucket with lifecycle rules | — | — |
| Deploy | **One GCE VM** + Docker Compose (shipped) | CPU above 60% sustained | A second VM for `browser`+`prepare`; later a Managed Instance Group, or **Cloud Run jobs** for bursty ingestion |
| LLM | Gemini Flash-Lite for scoring, Flash for tailoring; batched, cached | — | Per-feature model switch via config (already exists) |
| Errors, metrics | **Sentry** + Cloud Logging/Monitoring | — | Grafana Cloud free tier |

**Rough monthly cost at 1,000 active users and 5,000 boards:**

| Item | Cost |
|---|---|
| VM e2-standard-2 | about $50 |
| Neon Launch plan | about $20 |
| Gemini | about $100 (10 scored + 3 tailored per user per day) |
| OpenWebNinja | plan-dependent |
| Sentry | free tier |
| GCS | under $5 |
| **Total** | **about $175–250 / month** |

---

## 12. Metrics (definitions)

| Metric | Definition | Source | Target |
|---|---|---|---|
| New jobs/day | Canonical jobs with `first_seen_at` in the day | `jobs` | ↑ |
| Active boards | `ats_boards.status='active'` with a success in the last 48 h | `ats_boards` | more than 3,000 by the end of Phase 2 |
| Ingestion success rate | Successful ÷ attempted fetches (304 counts as success), per ATS and host | `board_fetch_runs` | ≥ 97% |
| Duplicate rate | Aliases created ÷ jobs ingested, per source | `job_aliases` | Watched, not minimized |
| Freshness | p95 of (seen by us − posted by employer) | `jobs` | ≤ 6 h |
| Match latency | p95 of new job → in a matching user's feed | events | ≤ 15 min |
| LLM cost per user | Σ `ai_usage.cost` ÷ active users, per day | `ai_usage` | ≤ $0.01/day free tier |
| Cache hit rate | Match scores served from cache ÷ needed | `match_scores` | ≥ 90% |
| Preparation success | `awaiting_review` ÷ preparations started | `application_events` | ≥ 95% |
| Truth-check failures | Fallbacks to master resume ÷ preparations | events | ↓ |
| Submission success by ATS | `submitted` ÷ (`submitted` + `needs_action` + `failed`), per ATS | `applications` | ≥ 90% on Greenhouse and Ashby |
| Needs-action rate | `needs_action` ÷ submission attempts, by reason | `applications` | Watch the `uncertain_submit` reason closely |
| Handoff completion | Handoffs completed ÷ opened, by ATS and by extension vs manual | `handoff_sessions` | ≥ 60% |
| User approval rate | Approved ÷ reviewed | events | 40–70% (lower means bad matching) |
| Application → interview | Interviews ÷ submitted, by source, ATS and score band | outcomes | The north star |
