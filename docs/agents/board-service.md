# board-service Agent Guide

## Purpose

`board-service` owns board/feed data, board REST endpoints, views, likes, and content aggregation behavior.

## Owns

- `Realtime` and `Daily` board/feed tables.
- Board pagination and board view models.
- Board likes and view counts currently stored with board-domain data.
- Board REST endpoints under `/api/boards`.

## Does Not Own

- User profile persistence.
- Refresh tokens or OAuth.
- Comment CRUD ownership.
- Notification delivery.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/api/boards/realtime` | Realtime board list. |
| `/api/boards/daily` | Daily board list. |
| `/api/boards/{board_id}/likes` | Board like endpoint. |

## Data Boundary

Do not add new direct reads from `users` or comment-owned data. If board cards
need comment or user data, prefer one of these patterns:

- Fetch via comment-service or user-service API.
- Add a denormalized read model owned by board-service.
- Add an async event flow once notification/event infrastructure exists.

## Current Boundary Debt

Board read models should remain in PostgreSQL. Prefer service APIs or explicit read models for cross-service data.

## Change Checklist

- Keep board logic inside `app/routes` and `app/repositories`.
- Do not import user-service or comment-service internals.
- Ensure gateway path remains under `/boardservice/api/boards`.
- Add tests around pagination, likes, or views before changing behavior.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app -q
```
