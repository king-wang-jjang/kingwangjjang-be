# board-service Agent Guide

## Purpose

`board-service` owns board/feed data, board GraphQL queries, views, likes, and
content aggregation behavior.

## Owns

- `Realtime` and `Daily` board/feed collections.
- Board pagination and board view models.
- Board likes and view counts currently stored with board-domain data.
- Board GraphQL schema under `/board-graphql`.

## Does Not Own

- User profile persistence.
- Refresh tokens or OAuth.
- Comment CRUD ownership.
- Notification delivery.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/board-graphql` | Board GraphQL API. |
| `/sample` | Sample GraphQL API; avoid expanding it for production behavior. |

## Data Boundary

Do not add new direct reads from `users` or comment-owned data. If board cards
need comment or user data, prefer one of these patterns:

- Fetch via comment-service or user-service API.
- Add a denormalized read model owned by board-service.
- Add an async event flow once notification/event infrastructure exists.

## Current Boundary Debt

Some existing board code still reads comment-related collections for counts.
Do not expand this pattern. When touching board pagination, plan a migration
toward API/read-model based counts.

## Change Checklist

- Keep board logic inside `app/graphql/modules/board` or `app/services/board`.
- Do not import user-service or comment-service internals.
- Ensure gateway path remains `/boardservice/board-graphql`.
- Add tests around pagination, likes, or views before changing behavior.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app -q
```

