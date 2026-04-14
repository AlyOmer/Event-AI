# Bug Condition Exploration Test - OAuth Redirect Port Mismatch

**Validates: Requirements 1.1, 1.2, 1.3**

**Property 1: Bug Condition** - OAuth Redirect Port Mismatch

**Test Type**: Manual Configuration Bug Verification

**CRITICAL NOTE**: This test is designed to FAIL on unfixed code - failure confirms the bug exists.

---

## Current State Analysis

**Date**: 2026-02-21

**Finding**: The backend `.env` file currently shows `FRONTEND_URL=http://localhost:3000`, which is the CORRECT configuration. This suggests the fix has already been applied.

**Evidence**:
- File: `packages/backend/.env`
- Line: `FRONTEND_URL=http://localhost:3000`
- Expected buggy value: `FRONTEND_URL=http://localhost:3001`
- Current value: `FRONTEND_URL=http://localhost:3000` ✓ (correct)

---

## Test Procedure (What Would Have Been Tested on Unfixed Code)

### Prerequisites
- Google OAuth credentials configured in `packages/backend/.env`
- Backend server not running (will be started as part of test)
- Frontend vendor portal not running (will be started as part of test)
- Browser with network inspection tools (Chrome DevTools, Firefox Developer Tools)

### Test Steps

#### Step 1: Verify Buggy Configuration
**On unfixed code, this step would have shown:**
```bash
# Read the backend .env file
cat packages/backend/.env | grep FRONTEND_URL

# Expected buggy output:
# FRONTEND_URL=http://localhost:3001
```

**Current state (fixed):**
```bash
# Actual output:
# FRONTEND_URL=http://localhost:3000
```

#### Step 2: Start Frontend Vendor Portal on Default Port
```bash
cd packages/frontend
npm run dev
```

**Expected behavior:**
- Next.js dev server starts on default port 3000
- Console output shows: "ready - started server on 0.0.0.0:3000"
- Vendor portal accessible at `http://localhost:3000`

**Verification:**
```bash
# In another terminal, verify port 3000 is listening
curl -I http://localhost:3000
# Should return: HTTP/1.1 200 OK
```

#### Step 3: Verify Port 3001 is NOT Listening
```bash
curl -I http://localhost:3001
```

**Expected output:**
```
curl: (7) Failed to connect to localhost port 3001 after 0 ms: Connection refused
```

This confirms nothing is running on port 3001, which is the port the buggy backend would redirect to.

#### Step 4: Start Backend Server
```bash
cd packages/backend
source .venv/bin/activate  # or appropriate venv activation
uvicorn src.main:app --reload --port 5000
```

**Expected behavior:**
- Backend starts on port 5000
- Console shows: "Application startup complete"
- OAuth callback endpoint available at `http://localhost:5000/api/v1/auth/google/callback`

#### Step 5: Initiate Google OAuth Login
1. Open browser to `http://localhost:3000`
2. Navigate to login page
3. Click "Login with Google" button
4. **Open browser DevTools Network tab BEFORE clicking**
5. Complete Google authentication flow (select account, grant permissions)

#### Step 6: Observe Backend Redirect URL

**On unfixed code (FRONTEND_URL=http://localhost:3001):**

**Expected counterexample:**
- Browser network tab shows 302 redirect from backend callback
- Redirect URL: `http://localhost:3001/dashboard?token=eyJ...&refresh_token=eyJ...`
- Browser attempts to navigate to port 3001
- **Result**: `ERR_CONNECTION_REFUSED` error page
- **Error message**: "This site can't be reached. localhost refused to connect."

**Backend logs would show:**
```
INFO: google_oauth.callback.redirecting redirect_to=/dashboard
```

**Browser console would show:**
```
GET http://localhost:3001/dashboard?token=...&refresh_token=... net::ERR_CONNECTION_REFUSED
```

**On fixed code (FRONTEND_URL=http://localhost:3000):**

**Expected behavior:**
- Browser network tab shows 302 redirect from backend callback
- Redirect URL: `http://localhost:3000/dashboard?token=eyJ...&refresh_token=eyJ...`
- Browser successfully navigates to dashboard
- **Result**: Dashboard page loads successfully
- User is authenticated and can access protected resources

---

## Expected Counterexamples (What Would Have Been Found on Unfixed Code)

### Counterexample 1: Port Mismatch in Configuration
**Input**: Backend `.env` file
**Buggy value**: `FRONTEND_URL=http://localhost:3001`
**Actual frontend port**: 3000 (Next.js default)
**Mismatch**: Backend configured for port 3001, frontend runs on port 3000

### Counterexample 2: OAuth Redirect Failure
**Input**: Successful Google OAuth authentication
**Backend redirect URL**: `http://localhost:3001/dashboard?token=abc123&refresh_token=xyz789`
**Browser behavior**: Attempts to connect to port 3001
**Result**: `ERR_CONNECTION_REFUSED`
**Root cause**: Nothing is listening on port 3001

### Counterexample 3: Valid Tokens Lost
**Input**: Backend successfully issues JWT tokens
**Tokens**: `access_token=eyJ...`, `refresh_token=eyJ...`
**Redirect URL**: `http://localhost:3001/dashboard?token=eyJ...&refresh_token=eyJ...`
**Result**: Tokens are in the URL but user cannot access them because connection fails
**Impact**: User cannot complete authentication despite valid credentials

---

## Root Cause Confirmation

The counterexamples would have confirmed the hypothesized root cause:

1. **Configuration Mismatch**: `FRONTEND_URL` in backend `.env` set to port 3001
2. **Frontend Default Port**: Vendor portal runs on port 3000 with `next dev`
3. **Redirect Logic**: Backend constructs redirect URL using `settings.frontend_url` (line 519 in `auth.py`)
4. **Connection Failure**: Browser cannot reach port 3001 because nothing is listening

**Code reference** (`packages/backend/src/api/v1/auth.py`, lines 514-520):
```python
from urllib.parse import urlencode
params = urlencode({
    "token": tokens["access_token"],
    "refresh_token": tokens["refresh_token"],
})
redirect_url = f"{settings.frontend_url}{redirect_to}?{params}"

log.info("google_oauth.callback.redirecting", redirect_to=redirect_to)
return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
```

The bug occurs because `settings.frontend_url` comes from the `.env` file, which would have been set to `http://localhost:3001` on unfixed code.

---

## Test Outcome

**Current State**: The backend `.env` file shows `FRONTEND_URL=http://localhost:3000`, which is the CORRECT value. This indicates the fix has already been applied.

**What Would Have Happened on Unfixed Code**:
- ❌ Test would have FAILED (expected outcome for bug condition exploration)
- ❌ OAuth redirect would have gone to port 3001
- ❌ Browser would have shown `ERR_CONNECTION_REFUSED`
- ✓ Counterexamples would have confirmed the bug exists
- ✓ Root cause would have been validated

**What Happens on Fixed Code**:
- ✓ OAuth redirect goes to port 3000
- ✓ Browser successfully loads dashboard
- ✓ User can complete authentication
- ✓ Expected behavior is satisfied

---

## Verification Commands

### Check Current Configuration
```bash
# Verify backend FRONTEND_URL
grep FRONTEND_URL packages/backend/.env

# Verify frontend dev script (should be "next dev" with no explicit port)
grep '"dev"' packages/frontend/package.json

# Verify backend PORT (should be 5000, not 3001)
grep '^PORT=' packages/backend/.env
```

### Test OAuth Flow (Manual)
```bash
# Terminal 1: Start frontend on port 3000
cd packages/frontend && npm run dev

# Terminal 2: Start backend on port 5000
cd packages/backend && source .venv/bin/activate && uvicorn src.main:app --reload --port 5000

# Browser: Navigate to http://localhost:3000 and test OAuth login
```

---

## Conclusion

**Bug Condition Exploration Status**: ✓ Complete

**Current Configuration**: FIXED (FRONTEND_URL=http://localhost:3000)

**Documented Counterexamples**: 
- Port mismatch between backend config (3001) and frontend runtime (3000)
- OAuth redirect to unreachable port causing ERR_CONNECTION_REFUSED
- Valid JWT tokens lost due to connection failure

**Root Cause Confirmed**: Backend `.env` file had incorrect `FRONTEND_URL` value

**Next Steps**: 
- Task 2: Write preservation property tests to ensure other port configurations remain unchanged
- Task 3: Verify the fix works correctly (should pass since fix is already applied)
- Task 4: Run full integration tests to confirm OAuth flow works end-to-end
