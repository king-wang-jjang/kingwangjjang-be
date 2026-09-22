# user-service Agent Guide

## Purpose

`user-service` owns user identity, login callbacks, JWT issuing, refresh-token persistence, and user REST APIs.

## Owns

- Kakao login redirect and callback.
- Access token and refresh token creation.
- Browser-specific refresh-token hash persistence in `user_sessions`.
- Atomic migration of legacy plaintext tokens from `users.refresh_token` on first refresh.
- User profile records.
- User REST endpoints.

## Does Not Own

- Gateway routing.
- Board, comment, GPT, or notification business logic.
- Client-facing service prefix decisions.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/login` | Redirects to Kakao OAuth authorization. |
| `/callback` | Exchanges Kakao code, adds a hashed browser session, and sets session cookies. |
| `/api/auth/refresh` | Atomically rotates the browser session hash and both session cookies. |
| `/api/users/me` | Returns the current authenticated user. |
| `PATCH /api/users/me` | Updates the current user's display name. |
| `GET /api/admin/users` | Lists users with search, role filter, and pagination; admin only. |
| `GET /api/admin/users/{id}` | Reads a profile by internal user ID; admin only. |
| `PATCH /api/admin/users/{id}` | Updates only the display name of an existing user; admin only. |

Admin user APIs recheck the access cookie and `ADMIN_USER_IDS` as well as trusted
gateway identity headers. Keep the allowlist and JWT secret consistent with the
gateway. Roles remain allowlist-based; profile mutations cannot change roles or
OAuth identity, create missing accounts, or expose refresh credentials.

## Data Boundary

Only `user-service` may write user auth records and refresh-token hashes. Other
services must use gateway-provided identity headers or user-service APIs.

## Cookie Policy

- Production default: `AUTH_COOKIE_SECURE` unset or true, cookies are secure.
- Local source dev: `dev.ps1` and `dev.sh` set `AUTH_COOKIE_SECURE=FALSE`.
- Do not disable secure cookies in container or production scripts.
- Access and refresh cookies are HttpOnly, SameSite=Lax, path `/`; current TTLs are 1 hour and 400 days.
- A successful refresh resets both the cookie and persisted session expiry to 400 days.
- A new login adds a session and must not overwrite another browser's session.

## Change Checklist

- Keep DB access lazy in service modules to avoid import-time DB connections.
- Do not move OAuth or refresh-token logic back to gateway.
- Keep token issuer as `user-service`.
- Add tests for token or persistence behavior before changing auth code.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall app -q
```
