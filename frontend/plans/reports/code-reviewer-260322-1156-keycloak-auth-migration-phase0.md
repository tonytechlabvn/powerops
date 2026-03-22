# Code Review: Phase 0 Keycloak Auth Migration

## Scope
- **Files**: 15 (realm config, docker-compose, 8 backend, 4 frontend, pyproject.toml)
- **LOC**: ~1,100 across changed files
- **Focus**: Keycloak OIDC migration — security, breaking changes, edge cases

## Overall Assessment

Solid migration from bcrypt-based password auth to Keycloak OIDC. The architecture is clean: Keycloak RS256 JWKS validation on the backend, PKCE authorization code flow on the frontend, and a dual-auth middleware (Bearer JWT + X-API-Key) for backward compatibility. User model cleanly replaces `password_hash` with `keycloak_id`. However, there are several security issues ranging from critical to medium that must be addressed before production deployment.

---

## Critical Issues

### C1. Hardcoded client secret in realm-export.json (SECURITY)
**File**: `keycloak/realm-export.json` line 38
```json
"secret": "powerops-api-secret"
```
The `powerops-api` confidential client has a hardcoded plaintext secret. This secret is checked into version control. Even though `docker-compose.yml` uses `${KEYCLOAK_CLIENT_SECRET:-powerops-api-secret}` as a fallback, the realm import seeds this value directly into Keycloak.

**Impact**: Credential exposure if repo is public or cloned by unauthorized parties. The default secret is trivially guessable.

**Fix**: Remove `"secret"` from realm-export.json. After Keycloak starts, use the Keycloak Admin API or CLI to rotate the client secret. Document this in a post-deploy step. At minimum, use a placeholder and document that it MUST be changed.

### C2. Keycloak running in dev mode (`start-dev`) (SECURITY)
**File**: `docker-compose.yml` line 56
```yaml
command: start-dev --import-realm
```
`start-dev` disables caching, enables all features in dev mode, and crucially does NOT enforce HTTPS. Combined with `sslRequired: "none"` in realm-export.json (line 5), tokens travel in plaintext over HTTP.

**Impact**: JWT tokens, credentials, and session data transmitted unencrypted. Man-in-the-middle attacks trivial on any network path.

**Fix**: For production, use `start --optimized` with a build stage (`kc.sh build` then `kc.sh start`). Set `sslRequired: "external"` in realm config. Keep `start-dev` only in a separate `docker-compose.dev.yml` override file.

### C3. `directAccessGrantsEnabled: true` on API client (SECURITY)
**File**: `keycloak/realm-export.json` line 41
The `powerops-api` client has Resource Owner Password Credentials (ROPC) grant enabled. This allows direct username/password authentication, bypassing MFA and all Keycloak login flows.

**Impact**: Attackers who obtain or brute-force credentials can authenticate directly without going through Keycloak's brute-force protection UI. Undermines the purpose of moving to Keycloak.

**Fix**: Set `"directAccessGrantsEnabled": false` on the `powerops-api` client. The backend should only accept tokens issued via the authorization code flow.

### C4. PKCE `code_verifier` not sent to backend during code exchange (SECURITY)
**File**: `frontend/src/components/auth/auth-provider.tsx` lines 76, 94-108; `backend/api/routes/auth-routes.py` lines 69-118

The frontend stores the PKCE verifier in `sessionStorage` (line 76) but never sends it to the backend during the callback. The backend's `/api/auth/callback` endpoint exchanges the code without the `code_verifier` parameter (lines 86-94). Since `powerops-api` is a confidential client (has a secret), Keycloak may accept the exchange without verifier, but this defeats the purpose of PKCE.

**Impact**: PKCE protection is effectively bypassed. Authorization code interception attacks are not mitigated.

**Fix**: Frontend should send `code_verifier` in the callback request body. Backend should include it in the token exchange:
```python
# auth-routes.py callback
code_verifier = body.get("code_verifier")
token_data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": redirect_uri,
    "client_id": s.keycloak_client_id,
    "code_verifier": code_verifier,  # ADD THIS
}
```
```typescript
// auth-provider.tsx handleCallback
const verifier = sessionStorage.getItem('pkce_verifier')
const data = await apiClient.post<TokenResponse>('/api/auth/callback', {
  code,
  redirect_uri: redirectUri,
  code_verifier: verifier,  // ADD THIS
})
sessionStorage.removeItem('pkce_verifier')
```

---

## High Priority

### H1. `_require_admin` does not actually check admin role (AUTH BYPASS)
**File**: `backend/api/routes/user-routes.py` lines 62-70

The function extracts user state but never verifies the user has admin privileges. Any authenticated user can list/create/update/deactivate users.

```python
def _require_admin(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if isinstance(state, dict):
        return state  # <-- returns without any admin check
    return {"user_id": getattr(state, "id", None), "is_admin": False}
```

**Impact**: Privilege escalation. Any authenticated user can manage all users.

**Fix**: Check Keycloak roles from `request.state.user["roles"]` or check `Team.is_admin` membership:
```python
def _require_admin(request: Request) -> dict:
    state = getattr(request.state, "user", None)
    if state is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if isinstance(state, dict):
        roles = state.get("roles", [])
        if "admin" not in roles:
            raise HTTPException(status_code=403, detail="Admin access required")
        return state
    raise HTTPException(status_code=403, detail="Admin access required")
```

### H2. `registrationAllowed: true` enables self-registration (SECURITY)
**File**: `keycloak/realm-export.json` line 6

Open self-registration allows anyone to create accounts in the Keycloak realm. Combined with auto-provisioning in `sync_keycloak_user`, any self-registered user gets a PowerOps account.

**Impact**: Unauthorized access. Any internet user can register and gain access.

**Fix**: Set `"registrationAllowed": false`. Manage user provisioning through Keycloak admin console or API.

### H3. Default admin credentials in docker-compose (SECURITY)
**File**: `docker-compose.yml` lines 66-67
```yaml
KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN:-admin}
KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
```
Default `admin/admin` Keycloak admin credentials. Even with env var overrides, the fallback is dangerous.

**Impact**: If env vars aren't set, Keycloak admin console is accessible with trivial credentials.

**Fix**: Remove defaults. Fail fast if env vars are missing. For dev, use `.env.example` with documented values.

### H4. No token expiry awareness in frontend (TOKEN MANAGEMENT)
**File**: `frontend/src/components/auth/auth-provider.tsx`

There is no proactive token refresh mechanism. The access token (15-minute TTL per realm config) will expire silently, and the next API call will get a 401. The `refreshTokens()` function exists but is only called on initial mount (line 160), not on token expiry.

**Impact**: Users get unexpectedly logged out after 15 minutes of inactivity, poor UX. API calls fail silently.

**Fix**: Add a refresh interceptor to `api-client.ts` that catches 401s and attempts token refresh before retrying, or set up a timer based on token expiry:
```typescript
// In api-client.ts handleResponse or a fetch wrapper
if (res.status === 401 && _refreshToken) {
  const refreshed = await refreshTokens()
  if (refreshed) {
    // Retry original request
    return fetch(url, { ...options, headers: authHeaders() })
  }
}
```

### H5. Unused `time` import (CODE QUALITY)
**File**: `backend/core/keycloak-auth-service.py` line 9
```python
import time
```
Imported but never used.

**Fix**: Remove the unused import.

---

## Medium Priority

### M1. `sync_keycloak_user` auto-provisions all users without org-scoping (DATA INTEGRITY)
**File**: `backend/core/keycloak-auth-service.py` lines 96-113

First-time users are assigned to whichever org happens to exist first (`scalar_one_or_none()`). If multiple orgs exist, user assignment is non-deterministic. Also, a default org is auto-created for the very first user, which may not be desired.

**Fix**: Add explicit org assignment logic — either from Keycloak groups/claims or require admin pre-provisioning.

### M2. `keycloak_url` internal vs external URL confusion (CONFIG)
**Files**: `backend/core/config.py` line 54; `backend/api/routes/auth-routes.py` line 60; `backend/core/keycloak-auth-service.py` line 49

The `keycloak_url` setting defaults to `http://keycloak:8080` (Docker internal). The `keycloak_public_url` is used for frontend config, but `validate_keycloak_jwt` (line 49) uses the internal URL for the issuer check. If Keycloak's issuer claim in tokens uses the public URL (which it does when accessed via public URL), JWT validation will fail because the issuer won't match.

**Impact**: JWT validation fails in production when Keycloak is accessed through a reverse proxy/public URL.

**Fix**: The `expected_issuer` in `validate_keycloak_jwt` should match what Keycloak puts in its tokens. Use `keycloak_public_url` for issuer validation when set:
```python
expected_issuer = f"{s.keycloak_public_url or s.keycloak_url}/realms/{s.keycloak_realm}"
```

### M3. No request body schema validation on callback/refresh (INPUT VALIDATION)
**File**: `backend/api/routes/auth-routes.py` lines 79, 128

Both endpoints use `await request.json()` with manual `.get()` instead of Pydantic models. This skips FastAPI's automatic validation and OpenAPI documentation.

**Fix**: Create Pydantic request models:
```python
class CodeExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str
```

### M4. Catch-all exception handling swallows errors (DEBUGGING)
**File**: `backend/api/middleware/auth-middleware.py` lines 106-114

`_decode_keycloak_jwt` catches all exceptions and returns `None`, making it impossible to distinguish between expired tokens, invalid signatures, network errors to JWKS endpoint, and misconfiguration. Only logged at `DEBUG` level.

**Fix**: Log at `WARNING` level and differentiate between expected JWT errors and unexpected infrastructure errors:
```python
except jwt.ExpiredSignatureError:
    logger.debug("JWT expired")
    return None
except jwt.PyJWTError as exc:
    logger.warning("JWT validation failed: %s", exc)
    return None
except Exception as exc:
    logger.error("Unexpected error during JWT validation: %s", exc)
    return None
```

### M5. No database migration — relies on `create_all` (DATA MANAGEMENT)
The `User` model changed from `password_hash` to `keycloak_id`. There are no Alembic migration files. `Base.metadata.create_all` in `database.py` (line 93) only creates new tables/columns — it won't remove `password_hash` or alter existing rows.

**Impact**: Existing databases will have stale `password_hash` column. Existing users won't have `keycloak_id` set, causing lookup failures.

**Fix**: Create an Alembic migration that: (1) adds `keycloak_id` column, (2) drops `password_hash` column, (3) documents the user re-provisioning plan.

### M6. Logout endpoint doesn't revoke access token (SESSION MANAGEMENT)
**File**: `backend/api/routes/auth-routes.py` lines 154-175

Only the refresh token is revoked at Keycloak. The access token remains valid until expiry (15 min). Frontend clears local state, but the token can still be used if intercepted.

**Impact**: Tokens remain usable after logout for up to 15 minutes.

**Fix**: This is a known OIDC limitation. Consider: (1) shorter access token TTL, (2) token introspection for sensitive ops, or (3) accept the 15-min window and document it.

---

## Low Priority

### L1. `_load_core` dynamic import pattern is fragile and duplicated
**Files**: `auth-middleware.py`, `auth-routes.py`, `user-routes.py`, `org-routes.py`

The `_load_core()` function for loading kebab-case Python modules is duplicated across 4 files. It manipulates `sys.modules` directly and uses relative filesystem paths.

**Fix**: Extract to a shared utility (e.g., `backend/utils/module-loader.py`) and import it.

### L2. Frontend `_refreshToken` module-scope variable (STATE MANAGEMENT)
**File**: `frontend/src/components/auth/auth-provider.tsx` line 52
```typescript
let _refreshToken: string | null = null
```
Module-scope mutable variable. Survives component unmount/remount but is lost on page refresh. Acceptable for current architecture (Keycloak session cookie provides persistence), but worth documenting.

### L3. `AuthCallbackPage` is purely visual (MINOR)
**File**: `frontend/src/components/auth/auth-callback-page.tsx`

The component renders a static "Completing sign in..." message. The actual callback logic is in `AuthProvider` via the `useEffect`. This is fine architecturally but could show error states if the exchange fails.

---

## Edge Cases Found by Scout

1. **API key auth sets `org_id: None`**: `auth-middleware.py` line 91 hardcodes `org_id: None` for API key auth. Any downstream code that relies on `request.state.user["org_id"]` for scoping will break for API key users.

2. **Race condition in `sync_keycloak_user`**: Two concurrent first-login requests could both create a "Default Organization" due to read-then-write without a lock. The unique constraint on `org.name` would cause one to fail.

3. **Keycloak audience validation mismatch**: `validate_keycloak_jwt` accepts `["powerops-api", "powerops-frontend", "account"]` as audiences. If Keycloak issues tokens with `azp` but not matching `aud`, validation may fail or be too permissive depending on PyJWT version.

4. **`bcrypt` removed from pyproject.toml but no grep hits remain**: Clean removal confirmed — no leftover references to bcrypt, password_hash, or verify_password in the backend codebase.

5. **No CORS configuration for Keycloak**: If Keycloak runs on a different origin from the frontend, browser requests to Keycloak endpoints may fail. The realm config has `webOrigins` set, which handles Keycloak-side CORS, but the backend needs its own CORS setup for the callback endpoint.

---

## Positive Observations

1. **Clean separation of concerns**: Keycloak JWT validation, user sync, and middleware are in distinct modules
2. **Dual-auth middleware**: Backward-compatible X-API-Key support alongside Keycloak JWT
3. **PKCE flow chosen over implicit**: Correct modern OIDC approach for SPAs
4. **In-memory token storage**: Both frontend access token and refresh token stored in memory (not localStorage), mitigating XSS token theft
5. **User model migration is clean**: `keycloak_id` replaces `password_hash` with proper unique index
6. **Brute force protection enabled**: `bruteForceProtected: true` in realm config
7. **Confidential API client + public frontend client**: Correct client type separation

---

## Recommended Actions (Priority Order)

1. **[CRITICAL]** Fix PKCE: send `code_verifier` from frontend to backend and include in token exchange (C4)
2. **[CRITICAL]** Remove hardcoded client secret from realm-export.json (C1)
3. **[CRITICAL]** Disable `directAccessGrantsEnabled` on API client (C3)
4. **[CRITICAL]** Plan production Keycloak deployment with TLS (C2)
5. **[HIGH]** Fix `_require_admin` to actually verify admin role (H1)
6. **[HIGH]** Set `registrationAllowed: false` (H2)
7. **[HIGH]** Remove default admin credentials or fail without env vars (H3)
8. **[HIGH]** Add token refresh interceptor in frontend API client (H4)
9. **[MEDIUM]** Fix issuer URL mismatch between internal/external Keycloak URLs (M2)
10. **[MEDIUM]** Add Pydantic request models for callback/refresh endpoints (M3)
11. **[MEDIUM]** Create Alembic migration for User model changes (M5)
12. **[MEDIUM]** Improve error differentiation in JWT validation (M4)

---

## Metrics

| Metric | Value |
|--------|-------|
| Type Coverage | N/A (Python: `ignore_missing_imports=true`; TS: implicit via tsx) |
| Test Coverage | 0% (no tests for new auth code observed) |
| Linting Issues | 1 (unused `time` import in keycloak-auth-service.py) |
| Security Issues | 4 critical, 3 high, 3 medium |

---

## Unresolved Questions

1. Is there a deployment plan for production Keycloak (TLS termination, persistent storage, HA)?
2. How will existing users (if any) be migrated to Keycloak accounts?
3. Should the frontend use `powerops-frontend` (public client) directly with Keycloak, bypassing the backend code exchange entirely? This is the more standard SPA pattern and would make PKCE work end-to-end without backend involvement.
4. Is there an `.env.example` or deployment doc that lists required environment variables for the new Keycloak settings?
5. Should API key auth users have `org_id` resolved from the DB rather than hardcoded to `None`?
