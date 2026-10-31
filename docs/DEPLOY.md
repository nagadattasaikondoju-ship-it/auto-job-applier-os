# Deploying Applyon

| Part | Where | How |
|---|---|---|
| Website (Next.js) | Vercel, project `applyon` | Auto-deploys from GitHub |
| API, worker, Redis, HTTPS | Google Compute Engine VM (Mumbai) | `infra/gcp/` (Docker Compose) |
| Database (Postgres + pgvector) | Neon | Connection string in the VM's `.env` |

## 1. Database: Neon (free, doesn't expire)

[Neon](https://neon.tech)'s free plan doesn't expire and supports `pgvector`, which Applyon needs for matching.

1. Sign up at neon.tech (GitHub or Google login) and create a project in **AWS Asia Pacific (Singapore)**.
2. On the project dashboard, click **Connect** and copy the connection string (pooled or not: `setup.sh`
   uses the pooled one for the app and derives the direct one for migrations), e.g. `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`.
   Use it exactly as shown: Applyon converts `sslmode`/`channel_binding` for its database driver.

The backend creates the tables and the `vector` extension by itself on first start.

## 2. Backend: one Google Compute Engine VM (Mumbai)

The API, the background worker (job search, matching, auto-apply with Chromium, scheduler), Redis and
HTTPS (Caddy, free automatic certificate) run with Docker Compose on one VM: `infra/gcp/`.

1. Create a Google Cloud account at [console.cloud.google.com](https://console.cloud.google.com). New
   accounts get free credit for the first 90 days; a billing account (card) is required.
2. **Compute Engine → VM instances → Create instance:**
   - Name `applyon-api`, region **asia-south1 (Mumbai)**.
   - Machine type **e2-small** (2 vCPU shared, 2 GB). Measured use is about 0.5 GB, plus Chromium while submitting.
   - Boot disk: **Ubuntu 24.04 LTS**, 20 GB.
   - Firewall: tick **Allow HTTP traffic** and **Allow HTTPS traffic**.
   - Create. Optional: **VPC network → IP addresses** → reserve the VM's external IP as static, so it never changes.
3. Click **SSH** next to the VM and run:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/nagadattasaikondoju-ship-it/auto-job-applier-os/main/infra/gcp/setup.sh | sudo bash
   ```

   It asks for the Neon connection string, the Gemini key, the OpenWebNinja key (optional), the
   Firebase project ID and the website URL. They're saved to `/opt/applyon/infra/gcp/.env` (root only).
   The first build takes about 10 minutes. At the end it prints the API URL, e.g.
   `https://34-93-12-34.sslip.io`, a free hostname for the VM's IP that gets a real HTTPS certificate.
4. Check `https://<API URL>/health/ready` shows `"database":"connected","redis":"connected"`.

Updates are automatic: every 5 minutes the VM checks `main` and rebuilds when it changed
(log: `/var/log/applyon-update.log`).

Day-to-day commands (in the VM's SSH window):

```bash
cd /opt/applyon/infra/gcp
sudo docker compose ps                    # what's running
sudo docker compose logs -f --tail 100 api worker
sudo nano .env && sudo docker compose up -d   # change a setting
```

Other keys (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `REALTIME_JOBS_API_KEY`, `REALTIME_JOBS_SOURCES`,
`RESEND_API_KEY`, `SENTRY_DSN`) go in the same `.env` file.

## 3. Point the website at the API

Vercel → project `applyon` → Settings → Environment Variables:

- `NEXT_PUBLIC_API_BASE_URL` = the API URL printed by `setup.sh`
- Later: `NEXT_PUBLIC_FIREBASE_*` from the Firebase console (Project settings → Web app)

Then **Deployments → Redeploy** (NEXT_PUBLIC values are built into the site).

If the website URL ever changes, update `CORS_ORIGINS` and `FRONTEND_URL` in the VM's `.env` and run `sudo docker compose up -d`.

## 4. Logins

The API only accepts Firebase logins. Set `FIREBASE_PROJECT_ID` in the VM's `.env` and `NEXT_PUBLIC_FIREBASE_*` on
Vercel to let people sign up.

`ALLOW_DEV_LOGIN` is `false`. Setting it to `true` lets the site be tried with "Continue as dev user"
without Firebase, but **anyone can then sign in as anyone and read their resume and applications**.
Only use it briefly, for a private test with no real data.
