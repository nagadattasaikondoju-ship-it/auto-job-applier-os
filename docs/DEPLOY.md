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
   - `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`: leave empty until Firebase login is set up.
4. **Apply.** The first build takes about 10 minutes (it installs Chromium for auto-submitting).
   On every start the API runs database migrations, loads the company list and starts the
   background worker inside the same container, which runs a first job search right away.
5. Copy the API URL, e.g. `https://applyon-api.onrender.com`. Check `…/health/ready` shows
   `"database":"connected","redis":"connected"`.

Costs: everything runs on Render's free plans; no card is needed. Limits:
- Free Postgres expires after 30 days: upgrade it (or export your data) before then.
- The free API sleeps after 15 idle minutes. While asleep, scheduled job searches, matching and
  auto-apply pause; the next visit wakes it (~1 minute).
- The worker shares 512 MB with the API (tested: ~460 MB peak while Chromium submits a form).

For always-on background work, uncomment `applyon-worker` in `render.yaml` (Starter, ~$7/month)
and set `RUN_WORKER_IN_API=false` on `applyon-api`.

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
