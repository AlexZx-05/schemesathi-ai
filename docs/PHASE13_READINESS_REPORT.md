# Phase 13: End-to-End Testing, Security Review, and Production Readiness

**Review date:** 2026-10-23  
**Scope:** Current SchemeSathi AI workspace. No production deployment, external
email delivery, Groq call, or embedding-provider call was performed as part of
this review.

## Executive summary

The backend and frontend unit/integration suites pass, and the production
frontend build succeeds. The application is still **not ready for production
sign-off**: there is no automated browser-level end-to-end runner, the
catalogue still contains illustrative demo records rather than a populated,
verified set of real schemes, and production provider/deployment operations
require environment-specific verification.

## Test report

| Check | Result | Notes |
|---|---|---|
| Backend unit, integration, API, migration, and configuration tests | **81 passed** | `.venv\Scripts\python.exe -m pytest backend\tests -q` |
| Admin dashboard frontend tests | **2 passed** | `npm run test --workspace frontend -- --run tests/AdminDashboard.test.tsx` |
| Full frontend unit tests | **33 passed** | `npm run test --workspace frontend -- --run` |
| Frontend production build / TypeScript | **Passed** | `npm run build`; Vite reports a generated JavaScript chunk above 500 kB. |
| Frontend lint | **Passed with 2 warnings** | Existing React Fast Refresh warnings in `AuthContext.tsx` and `SavedSchemesContext.tsx`. |
| Formatting of changed frontend files | **Passed** | Targeted Prettier check passed after formatting the navigation change. |
| Whole frontend formatting check | **Failed** | The whole-workspace Prettier check reported 17 unrelated files needing formatting. All directly changed frontend files pass a targeted Prettier check; unrelated files were not rewritten. |
| Automated browser E2E | **Not configured / not run** | Current frontend test runner is Vitest with jsdom; no Playwright or Cypress E2E suite is configured. |

Backend coverage includes authentication, catalogue/pagination, profile and
eligibility, guidance/application tracking, notifications, assistant/RAG,
administration, and migrations. The automated tests do not replace an actual
browser-and-server production-like smoke test.

## Security review

A read-only review examined authentication/session handling, password storage,
CSRF/origin validation, CORS, rate limiting, role enforcement, ownership
checks, database query construction, uploads and external URL validation,
assistant/RAG handling, and logging/error behavior. The reviewer reported **no
concrete exploitable security vulnerabilities** in the inspected workspace.
This is a bounded code review, not a penetration test, dependency audit, or
certification.

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| — | — | — | — | No concrete exploitable vulnerability identified in the reviewed code. | — |

## Fixed during Phase 13

- Added administrator dashboard tests proving ordinary users do not request or
  access admin data, plus backend authorization tests on admin mutations.
- Added an end-to-end admin workflow test for source registration, eligibility
  and document requirements, unknown deadlines, and audit records.
- Tightened the admin quality report to flag rules using unsupported
  eligibility operators, not just unknown fields.
- Fixed a malformed mobile navigation CSS class that prevented the open-menu
  style from being applied; the navigation interaction test now passes.
- Fixed optional age handling in profile editing so an empty field is kept
  `null` instead of being coerced to numeric zero.
- Updated frontend tests to wait for asynchronous auth state, match current
  branding/summary markup, and verify authenticated API-backed save/unsave
  behavior rather than the retired local-storage flow.
- Made local development configuration persistent through the ignored root
  `.env` file for both backend startup and Vite's `VITE_`-filtered variables.
- Added configuration tests verifying root `.env` loading without overriding
  variables explicitly provided by the process; isolated auth tests from local
  SMTP settings.
- Captured actual test/build/lint results and outstanding failures below;
  successful build or backend tests are not represented as proof that all
  journeys or third-party integrations work.

## Critical journey coverage and limitations

The repository has component tests and backend API integration tests for many
pieces of the critical flows. It does **not** yet automate the entire sequence
from browser registration/email verification through onboarding, personalized
recommendations, eligibility, assistant interaction, saving, document
checklist, and application tracking in a single E2E test.

Other known limitations:

- There is no automatically populated verified government scheme catalogue.
  Demo records are explicitly labelled and must not be represented as real
  government programmes.
- Groq, SMTP, and embedding integrations depend on valid server-side
  credentials and external service availability; these integrations were not
  exercised against live providers during this review.
- Google sign-in requires the operator's own OAuth web client ID in the root
  `.env` and the exact frontend origin to be authorized in Google Cloud
  Console. No client ID is included in the repository.
- Browser accessibility and responsive behavior were not systematically
  validated across screen readers, devices, or browsers.
- A successful frontend build still emits a bundle-size warning.
- The whole-workspace format check still flags unrelated files as reported
  above.

## Local setup and validation

Requirements: Node.js 20.19+ or 22.12+, npm, Python 3.11+, and optionally Docker
with Docker Compose for PostgreSQL.

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
alembic -c backend\alembic.ini upgrade head
```

For local SQLite development, set the root `.env` to use development values,
then run the API and frontend in separate terminals:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

```powershell
npm run dev
```

Seeded records are illustrative only. To add real records, use `/admin` after
provisioning an authorized administrator and independently verifying each
official source.

Run the checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
npm run test --workspace frontend -- --run
npm run build
npm run lint --workspace frontend
npm run format:check
```

## Environment variables

Copy `.env.example` for local configuration. Keep server-only credentials out
of frontend variables and source control.

| Variable | Purpose / production guidance |
|---|---|
| `DATABASE_URL` | SQLAlchemy database URL. Use a managed/secured PostgreSQL service in production; local development defaults to SQLite. |
| `API_CORS_ORIGINS` | Comma-separated exact browser origins. Restrict to deployed frontend origins; do not use a wildcard with credentialed sessions. |
| `AUTH_COOKIE_SECURE` | Set `true` in production behind HTTPS. Session cookies are HttpOnly and SameSite. |
| `ENVIRONMENT` | Set `production` for deployment; development-only verification inbox behavior is disabled there. |
| `FRONTEND_BASE_URL` | Public HTTPS frontend URL used in email links. |
| `EMAIL_PROVIDER` | `smtp` for real mail delivery; keep SMTP credentials server-side. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` | SMTP connection and sender configuration. Use provider-issued credentials and TLS. |
| `GOOGLE_CLIENT_ID` | Optional server-side Google OAuth audience/client ID. |
| `VITE_GOOGLE_CLIENT_ID` | Optional public Google web client ID used by the browser; never place a client secret here. |
| `VITE_API_BASE_URL` | Browser-visible API base URL. Must point to the deployed HTTPS API in production. |
| `GROQ_API_KEY` | Server-only Groq credential. Required for live Groq responses; never expose to Vite. |
| `GROQ_MODEL`, `GROQ_API_URL`, `GROQ_TIMEOUT_SECONDS` | Groq model, API endpoint, and bounded request timeout. Validate provider support and limits before deployment. |
| `OFFICIAL_SOURCE_ALLOWLIST` | Comma-separated reviewed source domains permitted for ingestion. Allowlisting does not establish source truth or scheme verification. |
| `EMBEDDING_PROVIDER`, `EMBEDDING_API_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL` | Server-side embedding integration for RAG. The configured model must return the required 1536 dimensions. |
| `KNOWLEDGE_MAX_AGE_DAYS` | Maximum age before a verified source is considered stale; choose an operationally appropriate review interval. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Docker Compose PostgreSQL initialization. Use a unique strong password and do not expose the database port publicly. |

The `.env.example` contains development placeholders, not production secrets.
Never share or commit a populated `.env`.

## Database migrations

After configuring the target database, apply migrations from the repository
root:

```powershell
alembic -c backend\alembic.ini upgrade head
```

Back up the database before upgrades in production, validate migrations against
a staging copy, and document a tested restore procedure. The Docker API
container runs migrations during startup; production operators should confirm
that this matches their release and rollback strategy.

## Deployment checklist

- [ ] Use HTTPS end-to-end; set `ENVIRONMENT=production` and
      `AUTH_COOKIE_SECURE=true`.
- [ ] Set exact production CORS origins and a production HTTPS API URL in
      `VITE_API_BASE_URL`.
- [ ] Store secrets in a server-side secret manager; rotate any credential
      suspected to have been exposed.
- [ ] Provision administrator access through a controlled operator procedure;
      verify ordinary users cannot access administrator APIs.
- [ ] Configure PostgreSQL with pgvector, private network access, backups, and a
      tested restore procedure.
- [ ] Apply and verify migrations in staging before production deployment.
- [ ] Configure and test SMTP, Groq, and embedding providers separately; verify
      timeouts, quotas, failure handling, and monitoring with provider-safe
      test accounts.
- [ ] Set the source domain allowlist and independently verify real scheme
      claims against current official sources. Keep unknown dates unknown.
- [ ] Do not advertise demo entries as real schemes. Require human review and
      traceable source references before displaying government claims as
      verified.
- [ ] Configure and monitor the scheduled notification job; verify idempotency,
      timezone, retries, and delivery failures in staging.
- [ ] Add a browser-level critical-journey E2E suite before calling the
      release test gate green.
- [ ] Review accessibility on target browsers/devices and fix or approve the
      bundle-size warning with an intentional performance budget.
- [ ] Configure production logs, alerting, rate-limit storage appropriate to
      the deployment topology, incident response, and privacy/data-retention
      policies.
- [ ] Run the full backend and frontend suites, build, lint, and formatting
      checks against the exact release candidate and retain their outputs.
