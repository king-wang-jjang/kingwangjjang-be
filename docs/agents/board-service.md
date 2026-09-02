# board-service Agent Guide

## Purpose

`board-service` owns board/feed data, board REST endpoints, ranking snapshots, likes, persisted AI analysis results, and content aggregation behavior.

## Owns

- `boards`, metric snapshots, and daily Top 10 snapshots.
- Board pagination and board view models.
- Board likes and source engagement metrics stored with board-domain data.
- Automatic analysis workers and persisted summary/tag/engagement results.
- The administrator-only Top 10 Shorts package contract.
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
| `/api/boards/daily/history/dates` | Available daily Top 10 snapshot dates. |
| `/api/boards/daily/history?date=YYYY-MM-DD` | Stored Top 10 ranking for a date. |
| `/api/boards/daily/shorts-package` | Admin-only live or historical Shorts production package. |
| `/api/boards/ai/resources` | Admin-only analysis backlog and worker throughput. |
| `/api/boards/{board_id}/ai` | Read or request board analysis. |
| `/api/boards/ai/jobs/{job_id}` | Read an authenticated manual-analysis job. |
| `/api/boards/{board_id}/images/{image_index}/vision-text` | Authenticated image text extraction. |
| `/api/boards/{board_id}/likes` | Board like endpoint. |

The backlog endpoint reports `overloaded` when the oldest pending analysis has
waited at least 10 minutes or pending depth reaches 10 jobs per configured
worker. It reports `busy` from 2 minutes, 2 jobs per worker, or a stale
processing job.

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
- Keep actual model inference behind `gpt-service` and send `X-AI-Service-Token`.
- Treat manual analysis jobs as process-local state unless a persistent job store is introduced.
- Add tests around pagination, likes, or views before changing behavior.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app -q
```
