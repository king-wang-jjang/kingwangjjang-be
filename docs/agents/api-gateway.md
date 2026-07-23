# api-gateway Agent Guide

## Purpose

`api-gateway` is the single public backend entrypoint. It routes requests,
performs stateless access-token verification, strips untrusted identity headers,
and forwards trusted auth context to downstream services.

## Owns

- Public routing prefixes.
- CORS and edge middleware.
- Stateless access-token decoding.
- Trusted forwarding headers for downstream services.
- Proxy response preservation, including redirect headers and `Set-Cookie`.

## Does Not Own

- User records.
- Refresh tokens.
- OAuth provider exchanges.
- Business data collections.
- Board, comment, GPT, or notification business logic.

## Routes

| Public path | Target |
| --- | --- |
| `/boardservice/*` | `board-service` |
| `/userservice/*` | `user-service` |
| `/commentservice/*` | `comment-service` |
| `/gptservice/*` | `gpt-service` |
| `/login` | `user-service /login` |
| `/callback` | `user-service /callback` |
| `/static/media/*` | crawler media root (when it exists at startup) |

## Data Boundary

The gateway must not import service database modules or database drivers.
If gateway logic needs user state, add or consume a user-service API instead.

## Security Rules

- Always strip incoming `X-User-Id`, `X-Auth-Provider`, `X-User-Role`, `X-Auth-Status`, and `X-Auth-Error`.
- Only gateway middleware may set trusted identity headers.
- Resolve the administrator role from `ADMIN_USER_IDS`; never trust a client-supplied role.
- Do not refresh tokens in gateway. Refresh-token ownership belongs to `user-service`.
- Preserve downstream `Set-Cookie` headers when proxying auth redirects.

## Change Checklist

- Confirm new routes are represented in `app/routes/index.py`.
- Confirm no DB imports exist under `api-gateway/app`.
- Confirm auth middleware remains stateless.
- Run root tests after route or auth changes.

## Verification

```bash
python -m pytest tests -q
```

```powershell
.\api-gateway\.venv\Scripts\python.exe -m compileall app -q
```
