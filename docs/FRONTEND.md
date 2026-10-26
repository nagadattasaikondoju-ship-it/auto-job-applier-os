# Applyon front end — how it's built and how to extend it

The landing page lives at `/` (plus the SEO pages). The logged-in product lives in two route groups:

```
src/app/
  (auth)/login, (auth)/signup          Firebase login (or local dev login)
  (app)/layout.tsx                     Providers + RequireAuth + DynamicMarker
  (app)/onboarding                     Upload resume → check parsed profile → ATS score + fixes
                                       → 7-question preferences → DPDP consent → start auto-apply
  (app)/(shell)/layout.tsx             Sidebar + top bar (AppShell)
  (app)/(shell)/dashboard              Getting-started checklist, stats, top matches, funnel
  (app)/(shell)/resume                 Resume & ATS: upload, score, bullet rewrites, versions, PDF/DOCX
  (app)/(shell)/preferences            Roles, cities, level, salary, notice, exclusions, apply mode
  (app)/(shell)/auto-apply             Start/pause, Review vs Hybrid, daily limit, live progress
  (app)/(shell)/follow-ups             Due follow-ups with editable email drafts
  (app)/(shell)/jobs                   Matched job feed, saved jobs, "Find jobs now", import a job
  (app)/(shell)/jobs/[id]              Job detail + fit analysis + feedback
  (app)/(shell)/jobs/[id]/tailor       Tailored resume + cover letter + truth check
  (app)/(shell)/review                 Review queue: edit answers, approve/skip
  (app)/(shell)/applications           Kanban tracker (drag between stages) + table + CSV export
  (app)/(shell)/applications/[id]      Answers, status updates, timeline
  (app)/(shell)/answers                Answer bank
  (app)/(shell)/profile                Master profile editor
  (app)/(shell)/billing                Plan, credits, ledger
  (app)/(shell)/notifications          Notifications
  (app)/(shell)/settings               Consents, data export, delete account

src/lib/api/types.ts      Response/request types, mirroring apps/api/routers/*.py
src/lib/api/client.ts     fetch wrapper: base URL, bearer token, error parsing
src/lib/api/endpoints.ts  `api.*` — the ONLY place pages talk to the backend
src/lib/auth.tsx          AuthProvider (Firebase, or dev token when Firebase isn't configured)
src/lib/firebase.ts       Firebase web SDK init from NEXT_PUBLIC_FIREBASE_*
src/lib/format.ts         Salary, dates, status labels/tones
src/components/app/ui.tsx Buttons, cards, badges, inputs, dialog, tabs, score ring…
```

## Conventions

- **Data:** TanStack Query. Query keys: `["profile"]`, `["jobs", ...]`, `["job", id]`, `["matches", ...]`, `["review-queue", page]`, `["applications", ...]`, `["application", id]`, `["answers"]`, `["credits"]`, `["ledger", page]`, `["notifications", ...]`, `["analytics", ...]`. Invalidate the related keys after every mutation.
- **Design tokens:** only the `app-*` tokens defined in `src/app/globals.css` (from DESIGN.md / Duna): `bg-app-bg`, `bg-app-card`, `bg-app-surface`, `text-app-ink`, `text-app-ink-2`, `text-app-muted`, `border-app-border`, `bg-app-accent`, `rounded-app-md|lg|xl`. Green accent (`#01A77D`) carries dark text, not white (contrast). Headlines use `font-display` (Instrument Serif); numbers use `font-mono`.
- **States:** every page handles loading (skeletons), empty (EmptyState with a next step), and error (ErrorState with retry).
- **Accessibility:** labelled inputs, `aria-current` in nav, visible focus rings, native `<dialog>` for modals, tables with captions and `scope`.
- **Job descriptions** are rendered as plain text only — never inject third-party HTML.
- **Cache Components** is on (`next.config.ts`). Anything that reads the URL (`usePathname`, `useParams`, `useSearchParams`) must sit inside `<Suspense>` — `(shell)/loading.tsx` covers pages, the sidebar nav has its own boundary. `RequireAuth` deliberately reads `window.location` instead of `usePathname`.

## Run it locally

```bash
cp .env.example .env.local      # fill NEXT_PUBLIC_* (leave Firebase empty for dev login)
npm install
npm run dev                     # http://localhost:3000 → /login
```

Backend: `docker compose -f infra/docker-compose.yml up` (or uvicorn) with `APP_ENV=development`. With Firebase unset, the login page offers "Continue as dev user", which sends `dev-token-<uid>`.

## How auto-apply works (end to end)

1. **Discovery** (Celery beat, hourly; or "Find jobs now"): Greenhouse/Lever/Ashby boards from
   `infra/seed/companies_india.csv` plus Adzuna searches for each user's roles and cities.
2. **Matching** (every 30 min, and right after "Start auto-apply"): hard filters on title, city/remote,
   experience and exclusions → rule-based skill/title score → Gemini scores the top 8 (rules if AI is down).
3. **Preparing** (every 15 min): for matches above the user's minimum score, the form is read from the
   ATS, answers come from the profile, then the answer bank, then AI. Each application waits in the
   Review queue; only required questions must be answered.
4. **Submitting**: on Approve (or Hybrid at 90+ with nothing to review) a Playwright worker fills the real
   form with the reviewed answers, attaches the resume PDF and marks it **submitted only when the page
   confirms it**. CAPTCHAs, logins or unconfirmed submits go back to the user as "needs action".
5. **Tracking**: submitted applications get a follow-up date 6 days later; the Follow-ups page drafts the email.

## Known gaps / next round

| Gap | Effect today | What's needed |
|---|---|---|
| Small job pool | ~670 jobs from 14 company boards; very few frontend/design/data roles | Adzuna API keys (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) and a longer verified company list |
| Gemini free-tier quota | AI scoring/tailoring hit 429s; rules take over for matching, tailoring returns "try again" | A paid Gemini key, or lower AI use per run |
| Crawl speed | One embedding call per job (~6 min for 670 jobs) | Batch embeddings |
| Multi-resume profiles, weekly report, similar-job clustering | Not built (core flow first) | New endpoints + pages |
| Gmail reply detection, full-auto mode, LinkedIn | Deliberately out of scope for launch | Later phases |
| Profile CRUD is partial | Can't edit/delete every education/project entry | `PATCH/DELETE` per section |
| Payments are sandbox | "Upgrade" shows a sandbox notice | Razorpay order + checkout + webhook |
