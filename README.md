# SchemeSathi AI

**Your Guide to Government Opportunities**

SchemeSathi AI is an independent civic-tech project intended to help people find
government schemes, understand preliminary eligibility, prepare document
checklists, and locate official application instructions. It is **not** an
official government website and is not endorsed by any government authority.

## Current status

- **Phase 1:** Responsive, accessible frontend foundation, reusable UI, routes,
  environment-based API configuration, and FastAPI health endpoint.
- **Phase 2:** Scheme listing, search, filters, sorting, save controls, and
  detail routes use the versioned catalogue API. The public catalogue returns
  only records with a verified source and no pending human review.
- **Phase 4:** A normalized SQLAlchemy catalogue stores schemes, categories,
  eligibility rules, documents, sources, state coverage, deadlines, and related
  user activity. Administrators curate records and verify the underlying
  official sources before publication.
- **Phase 5:** The signed-in dashboard shows profile completion, saved schemes,
  application summaries, verified upcoming deadlines, and paginated
  recommendations. Recommendations use recorded beneficiary groups and
  verified structured criteria; they explain matches and unknowns and never
  promise eligibility. No LLM or RAG is used.
- **Phase 6:** A deterministic Python eligibility engine evaluates only
  supported structured rules. It returns criterion-level results, uncertainty,
  profile values used, and verified source references. Hypothetical answers
  are validated, temporary overrides and do not alter the saved profile.
- **Phase 7:** An administrator-managed official knowledge base extracts
  approved HTML, PDF, and DOCX sources, stores traceable chunks and embeddings,
  and provides authenticated hybrid semantic/keyword retrieval. Retrieved text
  remains untrusted source material; no conversational assistant is included.
- **Phase 8:** The authenticated `/assistant` workspace uses an explicit
  LangGraph workflow to route requests, retrieve verified catalogue/RAG
  evidence, call the deterministic eligibility engine when appropriate, and
  ask Groq only to explain that evidence. Conversations, citations, and
  feedback are private to their signed-in owner. It never treats RAG text as
  instructions or guarantees eligibility, approval, deadlines, or benefits.
- **Phase 9:** The assistant now routes each request through focused
  multi-step guidance components for scheme discovery, deterministic
  eligibility assessment, document checklists, application guidance, and
  database-backed source validation. Each execution is audit-logged without
  storing prompts, message text, profile data, or provider payloads.
- **Phase 10:** Signed-in users can save scheme records, keep a
  preparation-only document checklist, follow source-backed application
  guidance, and privately track their self-reported application progress.
  SchemeSathi never uploads documents, accepts government-portal passwords,
  or submits applications.
- **Phase 3:** Email/password registration and login, revocable server-side
  sessions, protected profile editing, validation, and SQLAlchemy persistence
  are implemented. Passwords are Argon2-hashed and the session token is stored
  only as a hash; the browser receives it in an HttpOnly, SameSite=Lax cookie.

Profile fields are limited to information useful for organizing discovery:
name, optional age, state/territory, occupation, education level, an optional-
to-decline family income range, and beneficiary groups. The app does not ask
for Aadhaar numbers, bank details, caste, or exact income. Profile information
is not an eligibility decision.

The signed-in scheme detail page includes a preliminary eligibility check.
Assessments use only structured `rule_data` attached to a verified scheme with
at least one verified source and no pending human review. Free-text criteria
are never interpreted as executable rules; missing profile values and
unsupported rules remain unknown or require confirmation. The result is
informational and never guarantees eligibility or approval. Migration
`0005_structured_eligibility_rules`
adds the nullable `rule_data` JSON column, and
`0006_eligibility_rule_sources` adds the optional foreign-key reference from a
rule to its verified supporting source. Apply migrations with the normal
Alembic upgrade command.

Personalized discovery is available to authenticated users at
`/api/v1/recommendations` with `page` and `page_size` pagination. Its response
includes profile completion, reasons, criterion results, missing information,
and verified source references. `/api/v1/dashboard/summary` returns only the
signed-in user’s application counts and upcoming deadlines backed by a
verified scheme source. Recently viewed tracking and application editing are
not yet supported; saved schemes remain browser-local. The dashboard’s AI
assistant action is intentionally unavailable in this phase.

Email verification and password recovery use one-hour, single-use tokens. In
local development, the development email inbox makes those messages available
without claiming that an email was sent. For deployment, configure the SMTP
adapter, HTTPS, `ENVIRONMENT=production`, and `AUTH_COOKIE_SECURE=true`.
Authentication endpoints are rate-limited to 10 requests per IP and endpoint
per 15-minute window using database-backed counters.

## Requirements

- Node.js 20.19+ or 22.12+ and npm
- Python 3.11+
- Docker and Docker Compose (optional, for the local PostgreSQL container)

## Data sources and publication

The application does not currently have a documented, unified government API
for all-India schemes or recruitment notices. The official myScheme portal has
no public API documentation located for this project, and its
[terms of use](https://www.myscheme.gov.in/terms-of-use) prohibit automated
collection without written authorization. The
[data.gov.in API catalogue](https://www.data.gov.in/apis) is dataset-specific;
an API key, dataset licence, and update frequency must be checked for each
dataset. Official recruitment portals such as NCS, Employment News, UPSC, and
SSC publish notices, but no common public API for all vacancies, deadlines,
and required documents has been identified.

SchemeSathi does not scrape these sites or invent scheme details, vacancies,
deadlines, or document requirements. Public scheme records require a verified
official source and administrator review; job notices likewise require
verification against the recruiting authority's notice. This means the
catalogue can be empty until reviewed records are added. To integrate an API,
provide its public documentation and specific dataset/feed identifiers. Keep
any API key in the backend environment, never in Vite/browser variables.

## Install

Copy the root environment example to `.env` and adjust local values if needed:

```text
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.

Install frontend dependencies from the repository root (the npm workspace
forwards installation to `frontend/`):

```text
npm install
```

Create a virtual environment and install backend dependencies from the
repository root:

```text
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows or
`source .venv/bin/activate` on macOS/Linux, then run:

```text
python -m pip install -r backend/requirements-dev.txt
```

## Run locally

The backend uses a SQLite database at the project root (`schemesathi.db`) by
default for local development. Create or upgrade its schema from the
repository root:

```text
alembic -c backend/alembic.ini upgrade head
```

Start the API:

```text
uvicorn app.main:app --reload --app-dir backend
```

Start the frontend from the repository root:

```text
node node_modules/vite/bin/vite.js frontend --config frontend/vite.config.ts --host 127.0.0.1
```

Keep that terminal open. Vite should print a **Local** URL; open
`http://127.0.0.1:5173/` in your browser. Use `Ctrl+C` to stop the server. The
same direct command works in Git Bash without relying on npm's script-shell
forwarding. The API health endpoint is
`http://localhost:8000/health`; interactive API documentation is at
`http://localhost:8000/docs`.
The versioned catalogue API is available at `/api/v1/schemes`,
`/api/v1/categories`, and `/api/v1/health`. It supports `page`, `page_size`,
`q`, `category`, `state`, `government_level`, and `status` query parameters.
Only source-verified records are returned. Signed-in profile
access is available at `/api/v1/profile` (GET/PATCH); identity is derived
from the HttpOnly session cookie. Personalized discovery is served from
`/api/v1/recommendations` and `/api/v1/dashboard/summary`; both derive the user
from that same authenticated session.

The guided eligibility page is available at
`/schemes/{scheme_id}/eligibility-check` for signed-in users. The API endpoint
`POST /api/v1/schemes/{scheme_id}/eligibility-check` evaluates the authenticated
user's profile by default. To test temporary answers without saving them, send
an explicitly validated object such as
`{"answers":{"age":24,"state":"Bihar"}}`. Supported structured rules include
age and household-size bounds, state/location and education/occupation/status
matching, beneficiary categories, and conservative annual-income-band
threshold comparisons. Each evaluated criterion cites its directly linked
verified source. Rules without such a source, unsupported operators, and
malformed rules require confirmation; overlapping income bands remain unknown.
The compatibility endpoint `/api/v1/schemes/{scheme_id}/eligibility` remains
available.

## Official knowledge base

Phase 7 migrations create `scheme_knowledge_chunks` with a PostgreSQL `vector`
embedding column and SQLite JSON test/development variant. PostgreSQL must use
the supplied `pgvector/pgvector` image or have the pgvector extension installed;
the migration enables the extension. Embeddings use a configurable
OpenAI-compatible provider and must contain exactly 1536 dimensions. Configure
the backend environment (never the Vite frontend environment):

```text
OFFICIAL_SOURCE_ALLOWLIST=india.gov.in,mygov.in
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_API_URL=https://embedding-provider.example/v1/embeddings
EMBEDDING_API_KEY=your-private-server-key
EMBEDDING_MODEL=your-1536-dimension-model
KNOWLEDGE_MAX_AGE_DAYS=365
```

The example host names and provider URL above are configuration examples, not
endorsed scheme sources. Choose the allowlist domains and embedding provider
yourself. Add secrets only to the server-side `.env`; do not commit them.
Without an embedding provider, ingestion and retrieval return a service error
instead of fake embeddings.

### Add and verify a source

1. Research the source independently. Confirm that the content is published by
   the relevant government authority and that the URL is within a domain you
   control in `OFFICIAL_SOURCE_ALLOWLIST`. An allowlisted domain or PDF file
   alone does not establish official status.
2. Create or select an account, then grant administrator access out of band in
   the database (`UPDATE users SET is_admin = TRUE WHERE email = ...`). Never
   expose this privilege through public signup or frontend input.
3. As that administrator, create the source with
   `POST /api/v1/admin/schemes/{scheme_id}/sources`. New sources start
   unverified.
4. Review the current document and its issuing authority, then call
   `POST /api/v1/admin/sources/{source_id}/verify` with a concise verification
   note. This action is audited. Verification is a human assertion, not an
   automatic consequence of the URL or file type.
5. For a verified scheme, call `POST
   /api/v1/admin/knowledge/ingest` as multipart form data with `source_id`.
   Include an HTML, PDF, or DOCX `document` upload to index a reviewed copy,
   or omit the upload to fetch the registered HTTPS URL. URL fetching rejects
   unallowlisted hosts, non-public DNS results, redirects, unsupported content,
   and files over 10 MB. State, category, publication date, and effective date
   can be provided as form metadata.
6. Re-verify sources when their validity is checked again. Retrieval excludes
   stale/unverified sources and records older than `KNOWLEDGE_MAX_AGE_DAYS`.
   Reverification updates the indexed chunks' verification timestamp only when
   the administrator has reviewed the registered content; changed content must
   still be re-indexed. Re-indexing changed content replaces the previous
   chunks for that source; identical normalized extracted content is reported
   as a duplicate even when a document container's bytes differ.
7. Treat a failed ingest as work to review, never as a verified record. The API
   returns an extraction, provider, fetch, or database error to the
   administrator and writes a bounded `knowledge.ingestion_failed` audit event
   with the source identifier and error reason (not the uploaded document
   contents). Correct the source or configuration and retry the ingest.

Authenticated internal services can call `POST /api/v1/knowledge/retrieve`
with a query and optional scheme, state, and category filters. Each passage
includes its source URL/title, document and chunk identifiers, content hash,
dates, verification state, relevance score, and the explicit
`untrusted_source_text` trust-boundary label. Retrieved passages are data, not
instructions; retrieval does not guarantee that they are correct, current, or
official. There is no answer-generation or chat endpoint in Phase 7.

## AI assistant

Phase 8 adds a protected `/assistant` page and matching `/api/v1/assistant/*`
API. It is intentionally a small, explicit LangGraph workflow:

1. Deterministically classify the request intent.
2. Retrieve trusted scheme records and fresh, verified knowledge chunks.
3. Run the existing Python eligibility rules engine only for a recognised
   scheme eligibility question.
4. Ask Groq to explain the supplied evidence; it is not asked to decide facts
   or calculate eligibility.
5. Reject unsafe model output, attach only database-backed source citations,
   and persist the user/assistant messages to the authenticated user's
   conversation.

Configure Groq on the server only. No key is exposed to Vite or the browser:

```text
GROQ_API_KEY=your-server-side-key
GROQ_MODEL=your-enabled-groq-model
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
GROQ_TIMEOUT_SECONDS=20
```

`GROQ_MODEL` deliberately has no default: choose a model enabled for your own
Groq account. The assistant uses a short bounded retry for transient provider
errors. If Groq or the embedding provider is unavailable, it returns a
helpful, cited fallback where evidence exists; it does not invent an answer.

The UI supports new and previous conversations, source cards (including the
stored last-verified date), suggested follow-up questions, loading state, and
helpful/not-helpful feedback. Conversation reads and writes are scoped to the
current user; another account receives `404` for a conversation it does not
own. Apply the new migration before deploying:

```text
alembic -c backend/alembic.ini upgrade head
```

Assistant answers are explanatory guidance, not legal advice or an official
decision. Source passages are untrusted data: directives inside a document do
not control the assistant. Follow the cited source link to verify any scheme
fact before acting.

### Structured guidance workflow

Phase 9 extends—not replaces—the Phase 8 LangGraph workflow. It first runs
structured discovery and the existing fresh, verified RAG retrieval once, then
uses a conditional edge to choose one specialized component:

- **Eligibility:** invokes only the existing deterministic Python rules
  engine. Missing profile values remain unknown or require confirmation; the
  model does not calculate an outcome.
- **Documents:** uses only `SchemeDocument` records belonging to a verified
  scheme, together with retrieved official passages. It never infers a
  document from general knowledge.
- **Application:** uses only recorded application instructions and a recorded
  official portal, while explicitly stating that no application was submitted
  or confirmed.
- **Source validation:** removes evidence unless its citation is an existing,
  current verified source attached to the same scheme. Conflicting retrieved
  amounts, dates, and thresholds are flagged for the user rather than silently
  resolved.

Every invocation writes an `assistant.workflow_executed` audit event containing
only its intent, node names, component failure codes, and citation count. A
component/provider failure produces a safe fallback instead of a fabricated
claim. Scheme data, eligibility rules, and verification states remain read-only
to the assistant; their existing authorized administration process is unchanged.

## Saved schemes and application tracking

Phase 10 adds `/saved-schemes`, `/schemes/{schemeId}/documents`,
`/schemes/{schemeId}/apply`, `/applications`, and `/applications/{applicationId}`.
Apply the migration before deployment:

```text
alembic -c backend/alembic.ini upgrade head
```

Document items are available only for an active verified scheme with a current
verified source. A source is current for `KNOWLEDGE_MAX_AGE_DAYS` (365 days by
default); stale or undated sources make the saved record unavailable for
checklist and application guidance until re-reviewed. Saved scheme cards show
the latest recorded verification date and explain when guidance is unavailable.
Each document requirement is flagged when it has no individual source link in
the catalogue and should be confirmed with the official source. Marking an item
**ready** records preparation only; it does not upload, inspect, or officially
validate the document.

Application tracking is private to the signed-in owner. Its controlled states
are planning, preparing documents, ready to apply, submitted externally, in
progress, completed, and not proceeding. Moving to **submitted externally**
requires the user's explicit confirmation that they personally submitted
through the official portal. No government submission integration exists here,
so SchemeSathi never submits or verifies an application automatically.

## Notifications and deadline reminders

Phase 11 adds authenticated `/notifications` and `/settings` pages, private
notification history, read/unread state, per-user in-app/email/reminder
preferences, and optional server-side SMTP delivery. User time zones are
validated IANA names; reminder calendar dates are evaluated in the selected
time zone.

Apply the Phase 11 migration before starting the reminder worker:
`alembic -c backend/alembic.ini upgrade head`.

Deadline reminders are generated only for saved schemes or actively tracked
applications and only from an active, verified scheme with a known
future deadline, a current deadline verification timestamp, and a current
verified source linked directly to that deadline. "Current" uses
`KNOWLEDGE_MAX_AGE_DAYS` (365 days by default). Unknown, stale, undated, or
unlinked deadlines do not generate reminders. No deadline is inferred, and not
every scheme is expected to have one. Reminder notices link back to the
recorded source. If a deadline or source changes, pending reminders are
invalidated before delivery; old history remains visibly marked withdrawn.

Administrators must manually verify deadlines against their source. Create or
update them with `POST /api/v1/admin/schemes/{scheme_id}/deadlines` and
`PUT /api/v1/admin/schemes/{scheme_id}/deadlines/{deadline_id}`. A known
deadline requires an existing current verified source belonging to the same
scheme; unknown deadlines must have no closing time. These changes are audited.
The database migration adds nullable source metadata, so pre-existing deadline
records remain non-remindable until reviewed and linked.

The MVP scheduler is a bounded, idempotent one-shot job rather than an
in-process web-server scheduler. After applying the migration, run
`python -m app.notifications` from `backend\` every 15 minutes using cron,
systemd, or Windows Task Scheduler. Each run creates deduplicated 7-day and
1-day reminders and retries eligible transient email failures with bounded
backoff. In `ENVIRONMENT=test`, email delivery is explicitly skipped. To enable
email in a deployed backend, configure `EMAIL_PROVIDER=smtp`, `SMTP_HOST`,
`SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `EMAIL_FROM` on the server;
never expose these credentials to Vite or the browser. Delivery failures are
recorded and do not remove the in-app history.

The frontend API client reads `VITE_API_BASE_URL` and
`VITE_GOOGLE_CLIENT_ID` at build time. Copy the root `.env.example` to `.env`;
both Vite and the API load the root `.env` for local development. Vite only
exposes variables prefixed with `VITE_` to browser code:

```text
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`. Restart the API and
Vite after editing the file. The root `.env` is gitignored; do not commit it.
The frontend calls the API for authentication, profile management, and scheme
discovery. New accounts must verify their email
before signing in. For local testing, use **Read local development inbox** on
`/verify-email`; the password reset flow has the corresponding development
inbox option. The development inbox is disabled when `ENVIRONMENT=production`
or `EMAIL_PROVIDER=smtp`.

For real delivery, set these values in the API environment (the root `.env`
when using Docker Compose): `EMAIL_PROVIDER=smtp`, `SMTP_HOST`, `SMTP_PORT`,
`SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, and `FRONTEND_BASE_URL`.
Use a TLS-capable SMTP service and keep credentials out of frontend settings.
SMTP delivery failures are returned as service errors; the API does not claim
an email was sent.

For Resend SMTP, use `SMTP_HOST=smtp.resend.com`, `SMTP_PORT=465`, and
`SMTP_USERNAME=resend`. Set `SMTP_PASSWORD` to a Resend API key with sending
permission; do not paste that key into the frontend or commit it to git. Use a
verified sender domain in `EMAIL_FROM` before inviting real users.

Profile onboarding saves each step, includes a review step, and allows optional
questions to be skipped. State, education level, and occupation are needed to
complete onboarding. District, rural/urban area, student/employment status,
household size, income range, and beneficiary groups are optional. Age is
optional; the app does not request date of birth, gender, Aadhaar, bank account
numbers, or government-portal passwords.

## Administrator data quality

Phase 12 adds a protected `/admin` dashboard and `/api/v1/admin` endpoints for
scheme and category management, source review, eligibility/document quality
checks, RAG status and extraction failures, correction review, assistant
feedback, review history, and audit logs. Backend endpoints enforce the
administrator role; hiding the frontend route is not used as authorization.
New or edited scheme records remain unverified or require human review until an
authorized administrator checks current official sources. Missing application
URLs and stale or unsupported data are shown as quality flags rather than being
silently treated as verified. User-submitted corrections are review requests
and never modify scheme data automatically.

Apply the review-attribution and history migration before deployment:

```text
alembic -c backend/alembic.ini upgrade head
```

Grant administrator access only to an explicitly authorized account through a
controlled operator process. The application does not provide public
self-service administrator promotion. Record and protect that provisioning
operation according to the deployment's access-control policy. Admin actions
are attributed to the acting user, with before/after snapshots for scheme
changes and recorded review/audit history. Source ingestion remains available
through the protected source registration and ingestion API; re-indexing uses
the existing content-hash deduplication. Do not place credentials or private
user details in review notes or records.

## Optional Google sign-in

Google sign-in uses Google Identity Services and is disabled until a Google
OAuth web client ID is configured. In Google Cloud Console, create an OAuth
client for a web application and allow the exact local origins you use (for
example, `http://localhost:5173` and `http://localhost:8080`). The client ID is
public configuration, not a client secret.

For local development, put both values in the root `.env` file. The API loads
that file when it starts, and Vite is configured to read the same root file
while exposing only `VITE_`-prefixed variables to browser code. Restart both
servers after changing it. For Docker Compose, both values are also read from
the root `.env` during build/startup:

```text
GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
VITE_GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
```

The API verifies the Google ID token and verified email before creating or
linking an account. Never put a Google client secret or other server secret in
the frontend environment.

## Phase 13 release readiness

The latest test report, bounded security review, known limitations, environment
variable reference, local validation commands, migration instructions, and
deployment checklist are documented in
[docs/PHASE13_READINESS_REPORT.md](./docs/PHASE13_READINESS_REPORT.md). The
current workspace is not production signed off: the full frontend suite has
known failures and automated browser E2E coverage is not configured.

## Checks

From the repository root:

```text
npm test
npm run lint
npm run format:check
npm run build
```

From the repository root with the virtual environment active:

```text
python -m pytest backend/tests
```

## Docker Compose

Copy `.env.example` to `.env`, set a private `POSTGRES_PASSWORD` and matching
`DATABASE_URL`, then start the frontend, API, and PostgreSQL container:

```text
docker compose up --build
```

The frontend is served at `http://localhost:8080`, the API at
`http://localhost:8000`, and PostgreSQL at `localhost:5432`. The API container
runs Alembic migrations before starting.

## Project structure

```text
backend/
  app/main.py
  tests/
frontend/
  src/components/layout/
  src/components/ui/
  src/lib/
  src/pages/
  src/styles/
  src/test/
  tests/
```

## Configuration

See the root `.env.example` for local API/CORS and future integration settings.
Never commit `.env` files, API keys, or real credentials.
