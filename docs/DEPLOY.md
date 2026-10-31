# Deploying Applyon

| Part | Where | How |
|---|---|---|
| Website (Next.js) | Vercel, project `applyon` | Auto-deploys from GitHub |
| API, worker, Postgres, Redis | Render | `render.yaml` Blueprint |

## 1. Backend on Render (one time)

1. Sign in at [render.com](https://render.com) with GitHub.
2. **New → Blueprint** → choose `auto-job-applier-os` and the branch to deploy.
3. Render shows what it will create: `applyon-db` (Postgres), `applyon-redis` and `applyon-api`, all on free plans.
   Fill in the secret values it asks for:
   - `GEMINI_API_KEY`: required for AI parsing, scoring and tailoring.
   - `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`: optional, but strongly recommended for a much bigger job pool.
   - `JSEARCH_API_KEY`: optional. JSearch (OpenWebNinja, https://app.openwebninja.com/api/jsearch) adds Google for Jobs listings (LinkedIn, Naukri, company sites). Each role + city query runs at most every 12 hours to save credits, and any Greenhouse, Lever or Ashby board it finds is added to the crawl list automatically.
   - `REALTIME_JOBS_API_KEY`: optional. Real-Time Jobs Data (OpenWebNinja, https://app.openwebninja.com/api/realtime-jobs-data) searches Google for Jobs, Indeed and LinkedIn for India. Choose sources with `REALTIME_JOBS_SOURCES` (default `["google_jobs","indeed","linkedin"]`; each costs one credit per role + city search). Uses `JSEARCH_API_KEY` when unset.
   - `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`: leave empty until Firebase login is set up.
4. **Apply.** The first build takes about 10 minutes (it installs Chromium for auto-submitting).
   On every start the API runs database migrations, loads the company list and starts the
   background worker inside the same container, which runs a first job search right away.
5. Copy the API URL, e.g. `https://applyon-api.onrender.com`. Check `…/health/ready` shows
   `"database":"connected","redis":"connected"`.

Costs: everything runs on Render's free plans; no card is needed. Limits:
- Free Postgres expires after 30 days: switch to Neon (section 1b) or upgrade it before then.
- The free API sleeps after 15 idle minutes. While asleep, scheduled job searches, matching and
  auto-apply pause; the next visit wakes it (~1 minute).
- The worker shares 512 MB with the API (tested: ~460 MB peak while Chromium submits a form).

For always-on background work, uncomment `applyon-worker` in `render.yaml` (Starter, ~$7/month)
and set `RUN_WORKER_IN_API=false` on `applyon-api`.

## 1b. Free database that doesn't expire: Neon

Render's free Postgres is deleted after 30 days. [Neon](https://neon.tech)'s free plan doesn't expire
and supports `pgvector`, which Applyon needs for matching.

1. Sign up at neon.tech (GitHub or Google login) and create a project. Pick the **AWS Asia Pacific
   (Singapore)** region, closest to Render's Singapore region and to users in India.
2. On the project dashboard, click **Connect**, turn **Connection pooling off**, and copy the
   connection string. It looks like
   `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
   Paste it exactly as shown: Applyon converts `sslmode`/`channel_binding` for its database driver.
3. On Render, open `applyon-api` → **Environment**, set both `DATABASE_URL` and `DIRECT_DATABASE_URL`
   to that string, and save. The redeploy creates the tables and the `vector` extension by itself.
4. Check `…/health/ready` shows `"database":"connected"`.

Data in the old Render database is not copied over. To keep it, run
`pg_dump --no-owner --no-acl "<old Render external URL>" | psql "<Neon URL>"` before switching.
Neon's free compute sleeps after a few idle minutes and wakes in well under a second on the next query.

## 2. Point the website at the API

Vercel → project `applyon` → Settings → Environment Variables:

- `NEXT_PUBLIC_API_BASE_URL` = the Render API URL
- Later: `NEXT_PUBLIC_FIREBASE_*` from the Firebase console (Project settings → Web app)

Then **Deployments → Redeploy** (NEXT_PUBLIC values are built into the site).

If the website URL ever changes, update `CORS_ORIGINS` and `FRONTEND_URL` on both Render services.

## 3. Logins

The API only accepts Firebase logins. Set `FIREBASE_*` on Render and `NEXT_PUBLIC_FIREBASE_*` on
Vercel to let people sign up.

`ALLOW_DEV_LOGIN` is `false`. Setting it to `true` lets the site be tried with "Continue as dev user"
without Firebase, but **anyone can then sign in as anyone and read their resume and applications**.
Only use it briefly, for a private test with no real data.
