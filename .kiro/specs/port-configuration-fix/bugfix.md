# Bugfix Requirements Document

## Introduction

After Google OAuth login, users experience connection failures because the backend redirects to `localhost:3001/dashboard`, but the frontend vendor portal runs on `localhost:3000` by default. This causes `ERR_CONNECTION_REFUSED` errors and prevents successful authentication. Additionally, inconsistent port configurations across multiple packages lead to 404 errors when making API calls.

The bug affects the OAuth flow and general API connectivity across the following components:
- Backend OAuth redirect configuration (`FRONTEND_URL`)
- Frontend vendor portal default dev port
- User portal API URL configuration
- Admin portal API URL configuration
- Agentic event orchestrator backend API URL

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user completes Google OAuth login THEN the backend redirects to `http://localhost:3001/dashboard` causing `ERR_CONNECTION_REFUSED` because the frontend vendor portal runs on port 3000

1.2 WHEN the frontend vendor portal starts with `next dev` THEN it runs on port 3000 by default but the backend `FRONTEND_URL` is configured for port 3001

1.3 WHEN the backend `FRONTEND_URL` environment variable is set to `http://localhost:3001` THEN OAuth callbacks redirect to an unreachable port

1.4 WHEN frontend applications make API calls THEN some may use incorrect port configurations leading to 404 errors

### Expected Behavior (Correct)

2.1 WHEN a user completes Google OAuth login THEN the backend SHALL redirect to `http://localhost:3000/dashboard` matching the frontend vendor portal's actual port

2.2 WHEN the frontend vendor portal starts with `next dev` THEN it SHALL run on port 3000 and the backend `FRONTEND_URL` SHALL be configured to match this port

2.3 WHEN the backend `FRONTEND_URL` environment variable is configured THEN it SHALL be set to `http://localhost:3000` to match the frontend vendor portal's default port

2.4 WHEN frontend applications make API calls THEN they SHALL use the correct backend API URL `http://localhost:5000/api/v1`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the user portal runs with `next dev -p 3003` THEN it SHALL CONTINUE TO run on port 3003 as configured

3.2 WHEN the admin portal runs with `next dev -p 3002` THEN it SHALL CONTINUE TO run on port 3002 as configured

3.3 WHEN the backend API server runs THEN it SHALL CONTINUE TO run on port 5000 as configured

3.4 WHEN the agentic event orchestrator runs THEN it SHALL CONTINUE TO run on port 8000 as configured

3.5 WHEN Google OAuth callback URI is configured THEN it SHALL CONTINUE TO use `http://localhost:5000/api/v1/auth/google/callback` as the redirect URI

3.6 WHEN CORS origins are configured THEN they SHALL CONTINUE TO include all necessary frontend ports (3000, 3001, 3002, 3003)

3.7 WHEN the user portal or admin portal complete OAuth login THEN their respective redirect flows SHALL CONTINUE TO work correctly with their configured ports
