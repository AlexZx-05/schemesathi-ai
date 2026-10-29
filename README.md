# SchemeSathi AI

**Your guide to government schemes and opportunities.**

SchemeSathi AI is a civic-tech application that helps people explore
government schemes, understand recorded eligibility information, prepare
application documents, and find government job notices.

## Why I made this

Government information can be difficult to find and understand. I made
SchemeSathi AI to bring useful information into one place and explain it in
clearer language, so people can decide what to explore and where to check the
official details.

SchemeSathi AI is an independent project. It is **not** a government website
and is not endorsed by a government authority. It does not decide eligibility,
guarantee approval, or submit applications.

## What you can do

- Browse and search schemes and job notices available in the app.
- Create an account and add profile details to get more relevant suggestions.
- Ask the AI assistant questions about information stored in the app.
- Review source links and check important details with the official authority.
- Save schemes, prepare document checklists, and track your own application
  progress.

The assistant uses Groq to explain information when it is configured. It must
use verified information stored in the app for scheme facts. If there is no
verified information for a question, it should say so rather than make up an
answer.

### About scheme and job listings

There is no single confirmed public feed that provides every current Indian
government scheme and job opening. This app does not scrape government
websites or invent listings. Scheme and job records need an official source
and administrator review before they are shown as verified. Listings may be
limited until reviewed records or approved data feeds are added.

## Run the application on Windows

You need:

- Node.js 20.19+ or 22.12+
- Python 3.11+

Open **PowerShell** in the project folder and follow these steps.

### 1. Set up the environment

Create a local settings file if you do not already have one. If you already
have a `.env` file, keep it and do not overwrite it:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Install the frontend and backend packages:

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

If PowerShell prevents virtual environment activation, you can run the Python
commands directly with `.\.venv\Scripts\python.exe`.

### 2. Configure the AI assistant

Open the root `.env` file and set your Groq key and a model enabled for your
Groq account:

```text
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=your-enabled-groq-model
```

Keep this file private. Do not send API keys in chat or commit `.env` to
GitHub. The assistant's greeting and feature introduction work without Groq;
AI explanations require a configured key and model.

### 3. Set up the database

From the project folder, with the virtual environment active, run:

```powershell
alembic -c backend\alembic.ini upgrade head
```

By default, the local app uses a SQLite database file named
`schemesathi.db`.

### 4. Start the backend

In the first PowerShell terminal, run:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

The API will be available at `http://localhost:8000`. You can check that it is
running at `http://localhost:8000/health`. API documentation is at
`http://localhost:8000/docs`.

### 5. Start the frontend

Open a second PowerShell terminal in the project folder and run:

```powershell
node node_modules/vite/bin/vite.js frontend --config frontend/vite.config.ts --host 127.0.0.1
```

Open `http://127.0.0.1:5173` in your browser. Keep both terminals open while
using the application. Press `Ctrl+C` in each terminal to stop its server.

For local sign-up, use the development email inbox shown on the verification
page to verify your account.

## Optional features

- **Google sign-in:** Set `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` in
  `.env`.
- **Email delivery:** Configure the SMTP settings in `.env`. Without SMTP,
  local development uses the development inbox for account verification.
- **Official document search:** The assistant can search reviewed documents
  when an approved embedding provider is configured. See the example settings
  in `.env.example`.

Restart the backend and frontend after changing `.env`.

## Run with Docker

Docker Compose is an alternative to the local setup. Set a private
`POSTGRES_PASSWORD` and the matching database settings in `.env`, then run:

```powershell
docker compose up --build
```

The frontend is served at `http://localhost:8080` and the API at
`http://localhost:8000`.

## Run checks

From the project folder:

```powershell
npm test
npm run lint
npm run build
```

With the Python virtual environment active:

```powershell
python -m pytest backend\tests
```

## Project folders

```text
backend/    Python API, database models, and backend tests
frontend/   React website and frontend tests
docs/       Project reports and additional documentation
```

## Keep your information safe

- Never commit `.env`, API keys, passwords, or real user information.
- Check official sources before acting on scheme or job information.
- Do not use SchemeSathi AI as a substitute for an official government
  decision or application portal.
