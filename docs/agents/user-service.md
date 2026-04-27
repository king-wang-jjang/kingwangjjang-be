# user-service Agent Guide

## Purpose

`user-service` owns user identity, login callbacks, JWT issuing, refresh-token
persistence, and user GraphQL queries.

## Owns

- Kakao login redirect and callback.
- Access token and refresh token creation.
- Refresh-token persistence in `users`.
- User profile records.
- User GraphQL schema.

## Does Not Own

- Gateway routing.
- Board, comment, GPT, or notification business logic.
- Client-facing service prefix decisions.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/login` | Redirects to Kakao OAuth authorization. |
| `/callback` | Exchanges Kakao code, persists refresh token, sets access-token cookie. |
| `/user-graphql` | User GraphQL API. |

## Data Boundary

Only `user-service` may write user auth records and refresh tokens. Other
services must use gateway-provided identity headers or user-service APIs.

## Cookie Policy

- Production default: `AUTH_COOKIE_SECURE` unset or true, cookie is secure.
- Local source dev: `dev.ps1` and `dev.sh` set `AUTH_COOKIE_SECURE=FALSE`.
- Do not disable secure cookies in container or production scripts.

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

