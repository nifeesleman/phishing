# PhishGuard

<<<<<<< HEAD
PhishGuard is a full-stack phishing detection platform built around a Flask machine-learning API, a React + TypeScript frontend, and Supabase for authentication and persistent storage. Authenticated users can scan suspicious URLs, review their personal scan history, and export results. Administrators can view platform-wide analytics, recent detections, and authentication history.

## What the platform does

- Detects whether a submitted URL is likely **phishing** or **legitimate**
- Stores authenticated scan results in Supabase
- Falls back to a local SQLite history store if the remote history store is unavailable
- Lets users review, search, sort, paginate, and export their scan history
- Lets administrators monitor scan activity, phishing trends, risky URLs, and user auth history

## Architecture

### Backend (`backend/`)

The backend is a Flask API that:

- loads the trained model and vectorizer from `model.pkl` and `vectorizer.pkl`
- normalizes and preprocesses URLs before inference
- verifies Supabase JWTs for protected routes
- persists scans to the `scans` table in Supabase
- falls back to `backend\instance\scan_history.sqlite` if Supabase persistence is unavailable
- exposes admin analytics based on stored scan data

Main backend areas:

- `app.py` - Flask app factory and service wiring
- `routes\api.py` - HTTP endpoints
- `services\model_service.py` - ML inference
- `services\scan_service.py` - scanning, persistence, history, analytics
- `services\auth_service.py` - backend-assisted signup via Supabase Admin API
- `supabase\migrations\` - database schema and policy migrations
- `tests\` - backend unit tests

### Frontend (`frontend/`)

The frontend is a React app using Vite, TypeScript, and TanStack Router. It:

- handles sign up and sign in with Supabase Auth
- sends authenticated scan requests to the Flask API
- shows scan verdicts and confidence scores
- provides a history dashboard with filtering, sorting, and CSV export
- provides an admin dashboard for aggregate analytics

Main frontend areas:

- `src\routes\` - route definitions
- `src\pages\LandingPage.tsx` - marketing/entry page
- `src\pages\DashboardPage.tsx` - URL scan flow
- `src\pages\HistoryPage.tsx` - user history and CSV export
- `src\pages\AdminPage.tsx` - admin analytics
- `src\services\api.ts` - typed frontend API client
- `e2e\` - Playwright end-to-end tests

### Data flow

1. A user signs in through Supabase Auth in the frontend.
2. The frontend sends the access token to the Flask API.
3. The backend validates the token, preprocesses the URL, and runs the ML model.
4. The backend stores the result in Supabase (or local SQLite fallback if needed).
5. The frontend displays the verdict and later reads history or analytics from the API.

## Repository structure
=======
PhishGuard is a full-stack phishing detection platform that combines a Flask-based machine learning API, a React + TypeScript frontend, and Supabase for authentication and cloud persistence. The application lets users scan suspicious URLs, review their detection history, and access an administrative analytics dashboard for monitoring platform activity.

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Repository Structure](#repository-structure)
5. [Technology Stack](#technology-stack)
6. [Prerequisites](#prerequisites)
7. [Configuration](#configuration)
8. [Running the Project Locally](#running-the-project-locally)
9. [Running with Docker Compose](#running-with-docker-compose)
10. [Supabase Setup](#supabase-setup)
11. [API Reference](#api-reference)
12. [Testing and Quality Checks](#testing-and-quality-checks)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)

## Overview

PhishGuard is designed to support phishing awareness and URL risk assessment in a modern web application. The platform accepts a URL from an authenticated user, applies the backend detection pipeline, returns a Perdict with confidence data, and stores the result for later review. If cloud persistence is temporarily unavailable, the backend can fall back to a local SQLite history store to avoid losing scan data.

The repository contains:

- a Flask API for URL analysis, authentication-aware routing, and persistence
- a React frontend for user workflows and administrative reporting
- Supabase migrations for database structure and access policies
- automated test coverage for both backend and frontend flows
- legacy research artifacts, including the original phishing detection notebook and model files

## Key Features

### End-user capabilities

- Account registration through the backend signup endpoint and Supabase Auth
- Secure sign-in and authenticated API requests
- URL scanning with phishing or legitimate Perdicts
- Confidence scores and model metadata in scan results
- Personal history view with search, filtering, sorting, pagination, and export

### Administrative capabilities

- Platform-level scan statistics
- Daily activity reporting across configurable time ranges
- Recent scan visibility
- High-risk URL monitoring
- Optional authentication-history reporting through Supabase-backed admin workflows

### Reliability features

- JWT verification for protected routes
- Clear validation errors for malformed requests
- Local SQLite fallback when remote history persistence is unavailable
- Configurable CORS and admin access controls

## Architecture

### High-level flow

1. The frontend authenticates users with Supabase.
2. The frontend sends the access token with scan and history requests.
3. The Flask API verifies the JWT and validates the request payload.
4. The backend runs the phishing detection pipeline and produces a Perdict.
5. The result is stored in Supabase when available, or in local SQLite as a fallback.
6. The frontend renders scan results, history, and admin analytics.

### Backend

The backend application lives in `backend/` and is centered around `app.py`, which wires together:

- `routes/api.py` for HTTP endpoints
- `services/model_service.py` for model loading and inference
- `services/scan_service.py` for scanning, persistence, history, and analytics
- `services/auth_service.py` for backend-assisted signup
- `utils/auth.py` and related utilities for JWT verification and error handling

The backend loads configuration from `backend/.env` first, then falls back to the repository root `.env`.

### Frontend

The frontend application lives in `frontend/` and uses Vite, React, and TypeScript. It provides:

- authentication-aware user flows
- a protected dashboard for submitting URLs
- a history page for reviewing past scans
- an admin page for analytics and monitoring
- a typed API client for backend communication

## Repository Structure
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

```text
FYP-Project/
|- backend/
|  |- app.py
|  |- config/
<<<<<<< HEAD
=======
|  |- ml/
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
|  |- routes/
|  |- services/
|  |- supabase/
|  |- tests/
<<<<<<< HEAD
|  |- model.pkl
|  `- vectorizer.pkl
=======
|  |- phishing_model.pkl
|  |- train_phishing_model.py
|  |- Phishing URL Detection.ipynb
|  `- requirements.txt
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
|- frontend/
|  |- src/
|  |- e2e/
|  |- package.json
|  `- vite.config.ts
|- docker-compose.yml
`- README.md
```

<<<<<<< HEAD
## Core features

### User features

- Email/password account creation
- Login with Supabase Auth
- Protected URL scanning dashboard
- Confidence-based phishing verdicts
- Personal history with:
  - text search
  - verdict filtering
  - sorting by date or confidence
  - pagination
  - CSV export

### Admin features

- Overview cards for total scans, phishing detections, unique users, and average confidence
- Daily threat activity charts
- Top risky URLs
- Recent scans view
- Optional authentication-history view using the Supabase Admin API

## Technology stack

| Layer | Tools |
| --- | --- |
| Backend API | Flask, Flask-CORS, requests |
| ML | scikit-learn, pandas, joblib |
| Frontend | React, TypeScript, Vite |
| Routing/Data UI | TanStack Router, Radix UI, Recharts |
| Auth and persistence | Supabase Auth, Supabase Postgres |
| Local fallback storage | SQLite |
| Testing | unittest, Vitest, Playwright |
=======
## Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, TanStack Router |
| UI and charts | Radix UI, Recharts |
| Backend API | Flask, Flask-CORS, requests |
| ML and data processing | scikit-learn, pandas, numpy, joblib |
| Authentication and database | Supabase Auth, Supabase Postgres |
| Local fallback storage | SQLite |
| Testing | Python unittest, Vitest, Playwright |
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
| Containerization | Docker, Docker Compose |

## Prerequisites

<<<<<<< HEAD
For local development, have the following available:

- Python 3
- Node.js and npm
- Docker Desktop (optional, only for containerized runs)
- A Supabase project with Auth enabled

## Environment configuration

There are two supported ways to run the project:

1. **Local standalone development** - backend and frontend started separately
2. **Docker Compose** - both services started together

Copy the relevant example files before running anything.

### Root `.env` for Docker Compose

Create a root `.env` file from `.env.example`:
=======
Before running the project locally, install:

- Python 3
- Node.js and npm
- Docker Desktop (optional, for containerized setup)
- A Supabase project with authentication enabled

## Configuration

PhishGuard supports two common setups:

1. **Local development** with backend and frontend started separately
2. **Docker Compose** with both services started from the repository root

### Root environment file

For Docker Compose and shared local defaults, copy the root example file:
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

```bash
copy .env.example .env
```

<<<<<<< HEAD
The root file contains both backend and frontend variables for Docker Compose:
=======
Example variables:
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_JWKS_URL=
SUPABASE_JWT_SECRET=
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SCANS_TABLE=scans
ADMIN_EMAILS=
ADMIN_ROLES=admin
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080

VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
VITE_API_BASE_URL=http://localhost:5000

E2E_USER_EMAIL=
E2E_USER_PASSWORD=
E2E_ADMIN_EMAIL=
E2E_ADMIN_PASSWORD=
E2E_SIGNUP_EMAIL=
E2E_SIGNUP_PASSWORD=
E2E_SCAN_URL=https://example.com/login
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000
```

<<<<<<< HEAD
### Backend environment variables

For standalone backend development, create `backend\.env` from `backend\.env.example`.

Required or commonly used backend settings:

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Base URL of the Supabase project |
| `SUPABASE_SERVICE_ROLE_KEY` | Needed for backend signup and admin-level access |
| `SUPABASE_PUBLISHABLE_KEY` | Used when the backend needs to operate on behalf of an authenticated user |
| `SUPABASE_JWKS_URL` | JWKS endpoint used to verify JWTs |
| `SUPABASE_JWT_SECRET` | Optional alternative to JWKS-based JWT verification |
| `SUPABASE_JWT_AUDIENCE` | Expected JWT audience, default `authenticated` |
| `SUPABASE_SCANS_TABLE` | Scan persistence table, default `scans` |
| `ADMIN_EMAILS` | Comma-separated admin emails |
| `ADMIN_ROLES` | Comma-separated admin roles |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `MODEL_PATH` | Path to the trained model file |
| `VECTORIZER_PATH` | Path to the vectorizer file |
| `LOCAL_HISTORY_DB_PATH` | SQLite fallback history path |
| `SUPABASE_TIMEOUT_SECONDS` | Request timeout for upstream Supabase calls |
| `ADMIN_ANALYTICS_FETCH_LIMIT` | Cap for analytics row fetches |

Notes:

- The backend loads `backend\.env` first, then falls back to the repository root `.env`.
- If `SUPABASE_JWKS_URL` is not provided but `SUPABASE_URL` is set, the backend derives the JWKS URL automatically.
- If `SUPABASE_ISSUER` is not provided but `SUPABASE_URL` is set, the backend derives the issuer automatically.

### Frontend environment variables

For standalone frontend development, create `frontend\.env` from `frontend\.env.example`.

| Variable | Purpose |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable/anon key |
| `VITE_API_BASE_URL` | Base URL of the Flask API |

Notes:

- The frontend expects the backend at `VITE_API_BASE_URL`.
- If `VITE_API_BASE_URL` is omitted in the browser, the client falls back to `http(s)://<current-host>:5000`.

## Supabase setup

PhishGuard expects a Supabase project with Auth enabled and the SQL migrations in `backend\supabase\migrations\` applied.

### Required database behavior

The migrations create and/or rely on:
=======
### Backend environment file

For standalone backend development:

```bash
copy backend\.env.example backend\.env
```

Important backend variables:

| Variable | Description |
| --- | --- |
| `SUPABASE_URL` | Supabase project base URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Required for admin-level backend operations such as signup support |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key used for authenticated access workflows |
| `SUPABASE_JWKS_URL` | JWKS endpoint used for JWT verification |
| `SUPABASE_JWT_SECRET` | Optional JWT secret fallback |
| `SUPABASE_JWT_AUDIENCE` | Expected JWT audience, default `authenticated` |
| `SUPABASE_SCANS_TABLE` | Scan persistence table name |
| `ADMIN_EMAILS` | Comma-separated admin email allowlist |
| `ADMIN_ROLES` | Comma-separated admin roles |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `MODEL_PATH` | Path to the trained model artifact |
| `VECTORIZER_PATH` | Path to the vectorizer artifact when required |
| `LOCAL_HISTORY_DB_PATH` | SQLite fallback database path |

### Frontend environment file

For standalone frontend development:

```bash
copy frontend\.env.example frontend\.env
```

Frontend variables:

| Variable | Description |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key |
| `VITE_API_BASE_URL` | Base URL for the Flask API |

## Running the Project Locally

### 1. Start the backend

```bash
cd backend
python -m venv .venv
. .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The backend runs on `http://127.0.0.1:5000`.

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://127.0.0.1:3000`.

### 3. Recommended development workflow

1. Start the backend.
2. Start the frontend.
3. Create an account or sign in.
4. Submit a URL from the dashboard.
5. Review saved results on the history page.
6. Open the admin dashboard with an authorized admin account.

## Running with Docker Compose

From the repository root:

```bash
copy .env.example .env
docker compose up --build
```

Default service URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`

The Compose configuration passes the root `.env` values into both services.

## Supabase Setup

PhishGuard expects a Supabase project with:

- Auth enabled
- the required tables and policies applied
- backend credentials configured through environment variables

Database migrations are stored in `backend/supabase/migrations/`.

### Expected data model

The current application expects database support for:
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

- `profiles`
- `user_roles`
- `scans`
<<<<<<< HEAD
- row-level security policies for user-owned scan access
- a trigger that creates a default profile and `user` role for new accounts

### `scans` table

The current migration creates a `public.scans` table with fields including:
=======

The `scans` table is used for persisted URL scan history and analytics, with fields for values such as:
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

- `user_id`
- `email`
- `url`
- `normalized_url`
- `hostname`
- `inferred_target`
- `result`
- `confidence_score`
- `detection_method`
- `details`
- `model_name`
- `model_version`
- `metadata`
- `created_at`

<<<<<<< HEAD
It also creates indexes for:

- user history lookups
- result/date analytics
- recent scan retrieval
- trigram URL search

### Access and policies

The migration enables row-level security and applies policies so authenticated users can:

- read only their own scans
- insert only their own scans

### Promoting an admin

After creating a user, promote them in Supabase:
=======
### Admin role setup

To promote a user to admin in Supabase:
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

```sql
insert into public.user_roles (user_id, role)
values ('YOUR-USER-ID', 'admin')
on conflict (user_id, role) do nothing;
```

<<<<<<< HEAD
You can also list admin emails or roles through:

- `ADMIN_EMAILS`
- `ADMIN_ROLES`

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

The backend starts on:

- `http://127.0.0.1:5000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend starts on:

- `http://127.0.0.1:3000`

### Recommended local development flow

1. Start the backend in one terminal
2. Start the frontend in another terminal
3. Create or log into an account
4. Scan a URL from `/dashboard`
5. Review stored records in `/history`
6. Open `/admin` with an admin account

## Running with Docker Compose

From the repository root:

```bash
copy .env.example .env
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`

Docker Compose passes the root `.env` values into both services.

## API overview

The Flask backend exposes these main routes:

| Method | Route | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/` | No | Health/status payload with service name and model version |
| `POST` | `/auth/signup` | No | Creates a new user via Supabase Admin API |
| `POST` | `/scan` | Yes | Validates and scans a URL, then stores the result |
| `GET` | `/history` | Yes | Returns the authenticated user's scan history |
| `GET` | `/admin/stats` | Admin | Returns platform analytics and optional auth history |

### Example: scan a URL
=======
## API Reference

### Public routes

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/` | Health response with service status and model version |
| `POST` | `/auth/signup` | Creates a user through the backend auth service |

### Authenticated routes

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/scan` | Scans a URL and persists the result |
| `POST` | `/predict` | Returns a simplified prediction response for a URL |
| `GET` | `/history` | Returns paginated scan history for the current user |

### Admin routes

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/admin/stats` | Returns aggregate analytics and optional auth history |

### Example request
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

```http
POST /scan
Authorization: Bearer <supabase-access-token>
Content-Type: application/json

{
  "url": "https://example.com/login"
}
```

Example response:

```json
{
  "result": "phishing",
  "confidence": 0.91
}
```

<<<<<<< HEAD
If remote persistence fails, the response may also include:

```json
{
  "result": "phishing",
  "confidence": 0.91,
  "warning": "Scan completed and was saved to local history because the remote history store is unavailable."
}
```

### Example: history query parameters

`GET /history` supports:

- `limit` - 1 to 100
- `offset` - 0 or higher
- `search` - URL substring search
- `result` - `phishing` or `legit`
- `sort` - `newest`, `oldest`, `confidence_desc`, `confidence_asc`

### Example: admin analytics query parameters

`GET /admin/stats` supports:

- `range` - `7d`, `30d`, `90d`
- `include_auth_history` - `true` or `false`

## Testing
=======
### History query parameters

`GET /history` supports:

- `limit` from `1` to `100`
- `offset` of `0` or greater
- `search` for substring matching
- `result` as `phishing` or `legit`
- `sort` as `newest`, `oldest`, `confidence_desc`, or `confidence_asc`

### Admin analytics query parameters

`GET /admin/stats` supports:

- `range` as `7d`, `30d`, or `90d`
- `include_auth_history` as a boolean-style query flag

## Testing and Quality Checks
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

### Backend tests

```bash
cd backend
python -m unittest discover -s tests -v
```

<<<<<<< HEAD
The backend tests cover route behavior, validation, auth-related logic, scan services, and fallback storage.

=======
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
### Frontend unit tests

```bash
cd frontend
npm install
npm run test -- --run
```

### Frontend linting

```bash
cd frontend
npm run lint
```

<<<<<<< HEAD
### Frontend E2E tests

```bash
cd frontend
npm run test:e2e
```

Notes:

- Playwright uses `PLAYWRIGHT_BASE_URL`, defaulting to `http://127.0.0.1:3000`
- The E2E flows depend on the `E2E_*` environment variables in the root `.env`

## Build commands

=======
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
### Frontend production build

```bash
cd frontend
npm run build
```

<<<<<<< HEAD
## Error handling and fallback behavior

The backend is designed to fail clearly and preserve scan results when possible:

- invalid request bodies return validation errors
- non-admin users are blocked from admin routes
- Supabase upstream failures are surfaced as errors where appropriate
- scan persistence and history retrieval fall back to local SQLite when remote storage is unavailable
=======
### Frontend end-to-end tests

```bash
cd frontend
npm run test:e2e
```
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786

## Troubleshooting

### The frontend cannot reach the backend

<<<<<<< HEAD
Check:

- `VITE_API_BASE_URL` is set correctly
- the backend is running on port `5000`
- `CORS_ALLOWED_ORIGINS` includes your frontend origin

### Sign up works poorly or fails

Check:

- `SUPABASE_SERVICE_ROLE_KEY` is configured
- the backend can reach your Supabase project
- the email and password meet validation rules

### Protected requests return unauthorized

Check:

- the user is signed in through Supabase
- the frontend is sending a valid access token
- backend JWT settings match your Supabase project

### Admin page returns forbidden

Check:

- the account has the `admin` role in `public.user_roles`
- the email or role is allowed by backend admin configuration

### Scans are not appearing in Supabase history

Check:

- `SUPABASE_SCANS_TABLE` points to the correct table
- the scans migration was applied
- RLS policies are present
- if Supabase is down, inspect the local fallback database in `backend\instance\scan_history.sqlite`

## Notes for contributors

- Prefer updating the backend and frontend `.env.example` files when new configuration is introduced.
- Keep API behavior aligned with `frontend\src\services\api.ts`.
- If you change persistence or roles behavior, update the Supabase migrations and this README together.

=======
Check that:

- the backend is running on port `5000`
- `VITE_API_BASE_URL` points to the correct API
- `CORS_ALLOWED_ORIGINS` includes the frontend origin

### Authentication requests fail

Check that:

- Supabase credentials are configured correctly
- the backend can reach the Supabase project
- JWT-related values match your Supabase configuration

### Admin endpoints return forbidden

Check that:

- the account has an `admin` role in `public.user_roles`
- the account email or role is allowed by backend configuration

### Scan history is missing from Supabase

Check that:

- the migrations were applied
- `SUPABASE_SCANS_TABLE` points to the correct table
- row-level security policies exist
- the fallback database at `backend/instance/scan_history.sqlite` is not being used because of an upstream failure

## Contributing

Contributions are welcome. When making changes:

- keep backend and frontend configuration examples up to date
- update this README when setup, architecture, or API behavior changes
- keep frontend API usage aligned with the backend route contract
- include or update tests when functionality changes
>>>>>>> 0f6a9ea79a9cdd0c272e30d1a1fa0eb68e64c786
