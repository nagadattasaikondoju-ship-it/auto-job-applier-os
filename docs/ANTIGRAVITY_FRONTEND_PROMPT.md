# Prompt for Antigravity — connect and finish the Applyon product

Paste everything below the line into Antigravity, with this repo open.

---

You are a senior full-stack engineer working in the Applyon repo (Next.js 16 front end in `src/`, FastAPI backend in `apps/` + `packages/`). The landing page and all logged-in app pages already exist and talk to the real API. Your job is to close the remaining gaps so every feature works end to end, without redesigning anything.

## Read first (in this order) and treat as the source of truth
1. `docs/FRONTEND.md` — app structure, conventions, design tokens, and the **Known gaps** table.
2. `docs/ARCHITECTURE.md` — backend architecture.
3. `node_modules/next/dist/docs/` — this is Next.js 16 with **Cache Components** on. Read `01-app/02-guides/migrating-to-cache-components.md` before touching routing. Rules that already bit us: any component using `usePathname`/`useParams`/`useSearchParams` must be under `<Suspense>`; routes that only render on the client need the `DynamicMarker` (see `src/components/app/dynamic-marker.tsx`).
4. `src/lib/api/endpoints.ts` and `src/lib/api/types.ts` — every backend call goes through `api.*`. Add new endpoints there, with types mirroring the Python response exactly.

## Hard rules
- Frontend talks to the backend ONLY through `src/lib/api/endpoints.ts`. No `fetch` in pages.
- Styling: ONLY the `app-*` Tailwind tokens from `src/app/globals.css` and the components in `src/components/app/ui.tsx`. No new colours, no new UI libraries. Sentence case. Accent green gets dark text.
- Every new screen handles loading, empty and error states, and is keyboard accessible.
- Never render third-party HTML (job descriptions) — plain text only.
- Keep the truthfulness and user-control rules from `docs/ARCHITECTURE.md` section 0: nothing is submitted without approval unless auto-submit consent is granted; AI never invents facts.
- Don't change the landing page (`src/components/*.tsx` outside `src/components/app/`) unless asked.

## Tasks — do them in order. After EACH task: run `npx tsc --noEmit`, `npx eslint src`, `npm run build`, and the backend tests (`uv run pytest`); fix everything; give me a short summary + what to click to verify; then STOP and wait for "continue".

### 1. Fix the user-id mismatch (backend, blocking)
`apps/api/routers/jobs.py`, `matches.py` and `documents.py` pass `current_user.id` (a UUID derived from the Firebase uid) while profiles, resumes, applications, answers and credits store `current_user.user_id` (the raw uid string). With real Firebase users, tailoring fails with "Profile not found" and matches are stored under the wrong id.
- Use `current_user.user_id` everywhere. Change service signatures (`get_jobs_feed`, `run_matching_funnel_for_user`, `tailor_resume_for_job`, `generate_cover_letter`, etc.) from `uuid.UUID` to `str`.
- Add a test that creates a profile with a non-UUID uid (e.g. `"fb_abc123"`) and successfully tailors a resume and lists matches.

### 2. Preferences API + UI
- Backend: `GET /v1/preferences`, `PUT /v1/preferences` (target_roles, seniority, locations, remote_mode, min_salary_lpa, excluded_companies, excluded_keywords, employment_types, daily_application_limit, min_match_score).
- Frontend: new page `src/app/(app)/(shell)/preferences/page.tsx` (add "Job preferences" to the sidebar in `app-shell.tsx`), reusing `QuestionInput`-style chips for multi-selects. Saving re-runs `api.matches.refresh()` and invalidates `["jobs"]` and `["matches"]`.

### 3. Consent state
- Backend: `GET /v1/consents` returning the latest state per purpose.
- Frontend: Settings shows each permission as a real on/off state (not two buttons). Withdrawing `auto_submit` must also stop any active Autopilot campaign.

### 4. Autopilot
- Backend: `POST /v1/autopilot/start` (checks completeness ≥ 80, consents, plan, credits → creates a campaign), `POST /v1/autopilot/{id}/pause`, `POST /v1/autopilot/{id}/resume`, `GET /v1/autopilot` (status, mode review|auto_submit, daily_limit, today's counts, next run time). Wire to the existing `packages/core/services/autopilot.py` and Celery tasks.
- Frontend: replace the "Coming soon" card on the dashboard with real controls, plus a `/autopilot` page: mode selector (Review first — default; Auto-submit only if plan allows AND `auto_submit` consent is granted), daily limit slider (capped by plan), schedule window, start/pause, and today's activity list. Explain clearly what each mode does.

### 5. Resume file upload + documents per job
- Backend: `POST /v1/resumes/upload` (multipart PDF/DOCX ≤ 5 MB, server-side text extraction, same parse response as `POST /v1/resumes`), and `GET /v1/jobs/{id}/documents` (latest resume version + cover letter for that job).
- Frontend: onboarding uploads the file directly (keep the browser PDF extraction as a fallback); add DOCX support. The tailor page loads existing documents on open instead of always asking to generate.

### 6. Full profile editing
- Backend: PATCH/DELETE for experiences, skills; POST/PATCH/DELETE for educations, projects, certifications. Each change creates a new profile version.
- Frontend: edit and delete actions on the Profile page with confirm dialogs; add Projects and Certifications sections.

### 7. Payments (Razorpay)
- Backend: real order creation with Razorpay keys, `POST /v1/webhooks/razorpay` with signature verification and idempotent credit grants.
- Frontend: Billing "Upgrade" opens Razorpay Checkout (load `https://checkout.razorpay.com/v1/checkout.js` only on the billing page), handles success/failure, then refreshes `["credits"]` and `["ledger"]`. Keep the sandbox notice when keys are missing.

### 8. Polish and production readiness
- Live updates: poll `["review-queue"]` and `["notifications"]` every 60 s (already done for notifications) or switch to Supabase/Firebase realtime if the backend supports it.
- Add a Playwright e2e suite in `tests/e2e/` that mocks the API (pattern: intercept `http://localhost:8000/**`) and covers login → onboarding → job → tailor → review → approve → tracker, at desktop and 375 px widths.
- Verify Lighthouse accessibility ≥ 95 on dashboard, jobs, review.
- Update `docs/FRONTEND.md` (remove fixed rows from **Known gaps**).

Start with Task 1. Before writing code, reply with: (a) the exact files you'll change, (b) any risks you see.
