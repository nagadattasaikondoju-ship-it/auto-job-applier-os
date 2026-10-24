# Applyon front end — how it's built and how to extend it

The landing page lives at `/` (plus the SEO pages). The logged-in product lives in two route groups:

```
src/app/
  (auth)/login, (auth)/signup          Firebase login (or local dev login)
  (app)/layout.tsx                     Providers + RequireAuth + DynamicMarker
  (app)/onboarding                     Resume → questionnaire → DPDP consent
  (app)/(shell)/layout.tsx             Sidebar + top bar (AppShell)
  (app)/(shell)/dashboard              Stats, top matches, review count, funnel
  (app)/(shell)/jobs                   Matched job feed, import a job
  (app)/(shell)/jobs/[id]              Job detail + fit analysis + feedback
  (app)/(shell)/jobs/[id]/tailor       Tailored resume + cover letter + truth check
  (app)/(shell)/review                 Review queue: edit answers, approve/skip
  (app)/(shell)/applications           Tracker (table on desktop, cards on mobile)
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
src/lib/pdf-text.ts       Reads PDF/.txt resumes in the browser (pdfjs-dist)
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

## Known gaps (backend endpoints the UI needs next)

| Gap | Effect today | Needed endpoint |
|---|---|---|
| **User id mismatch** — `jobs.py`, `matches.py`, `documents.py` use `current_user.id` (UUID derived from the Firebase uid), while profiles/resumes/applications store `current_user.user_id` (raw uid) | With real Firebase users, tailoring returns "Profile not found" and matches are stored under a different id | Use `current_user.user_id` (string) everywhere; change service signatures from `uuid.UUID` to `str` |
| No Autopilot API | Dashboard shows Autopilot as "Coming soon" | `POST /v1/autopilot/start`, `POST /v1/autopilot/{id}/pause`, `POST /v1/autopilot/{id}/resume`, `GET /v1/autopilot` |
| No preferences API | Roles/cities/salary/daily limit only editable by redoing onboarding | `GET/PUT /v1/preferences` |
| No consent read API | Settings can grant/withdraw but can't show current state | `GET /v1/consents` |
| No file upload | Resume text is extracted in the browser (PDF/.txt only, no DOCX) | `POST /v1/resumes/upload` (multipart) |
| No document list per job | Tailored results disappear on reload | `GET /v1/jobs/{id}/documents` (latest resume version + cover letter) |
| Profile CRUD is partial | Can't edit/delete experiences, skills, education, projects | `PATCH/DELETE` for each, `POST` for education/projects/certifications |
| Payments are sandbox | "Upgrade" shows a sandbox notice | Razorpay order + checkout + webhook |
