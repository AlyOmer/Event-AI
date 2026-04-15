---
id: 3
title: Fix Google OAuth Sign-In 307 Redirect Loop
stage: green
date: 2026-04-15
surface: agent
model: Claude Opus 4.6
feature: user-auth
branch: main
user: ali
command: fix
labels: ["google-oauth", "user-portal", "auth-callback", "cors", "middleware"]
links:
  spec: specs/002-user-auth/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - packages/user/src/app/auth/callback/page.tsx
  - packages/user/src/middleware.ts
  - packages/backend/src/api/v1/auth.py
  - packages/backend/src/services/google_oauth_service.py
  - packages/backend/src/config/database.py
tests:
  - Manual: Google OAuth flow end-to-end (login → Google consent → callback → dashboard)
---

## Prompt

use claude skills and see user portal login apis . when i try to sigin with google when i click on it give 307 or401 error contionously or sometimes fallback

## Response snapshot

Root cause analysis identified 3 critical issues in the Google OAuth flow for the user portal:

1. **Missing `/auth/callback` page** — The user portal had no page to receive and process OAuth tokens from the backend redirect. The backend was redirecting directly to `/dashboard?token=...` which is a protected route.

2. **Middleware 307 loop** — The Next.js middleware checked for a `userToken` cookie on every non-public route. When the backend redirected to `/dashboard?token=...`, no cookie existed yet (tokens were in URL params, not yet persisted), so middleware issued a 307 redirect to `/login`, creating an infinite loop.

3. **CORS missing port 3003** — The backend default CORS origins did not include `http://localhost:3003` (user portal), blocking fetch calls from the callback page.

Additionally fixed: `handle_callback()` return type annotation was `tuple[dict, str]` but returned 3 values.

## Outcome

- ✅ Impact: Fixes Google Sign-In for user portal — eliminates 307 redirect loops and 401 errors
- 🧪 Tests: Manual end-to-end verification required (start backend + user portal, click Google sign-in)
- 📁 Files: 1 new (auth/callback/page.tsx), 4 modified (middleware.ts, auth.py, google_oauth_service.py, database.py)
- 🔁 Next prompts: Test end-to-end flow, verify with production Google OAuth credentials
- 🧠 Reflection: The core issue was an architectural gap — backend OAuth redirecting to a protected frontend route before the client had a chance to persist auth tokens. The fix introduces a dedicated public callback page as the redirect target.

## Evaluation notes (flywheel)

- Failure modes observed: Backend redirecting to protected routes before client-side token persistence; middleware intercepting OAuth redirects
- Graders run and results (PASS/FAIL): N/A — manual verification pending
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add login page error display for ?error= query param from OAuth failures
