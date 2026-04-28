# comment-service Agent Guide

## Purpose

`comment-service` owns comment CRUD, replies, comment likes, and comment REST behavior.

## Owns

- `comments` and `comment_likes` tables.
- Comment creation, update, soft delete, reply counts, and comment likes.
- Comment REST endpoints under `/api/comments`.

## Does Not Own

- Board content storage.
- User profile persistence.
- OAuth, JWT issuing, or refresh-token storage.
- Gateway route decisions.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/api/comments` | Comment list/create API. |
| `/api/comments/{comment_id}` | Comment update/delete API. |
| `/api/comments/{comment_id}/like` | Comment like API. |

## Data Boundary

Comment mutations should trust identity headers from gateway after auth status
checks. Do not resolve user details by directly reading `users`. If comments
need display names, prefer one of these:

- Ask user-service through an API.
- Store a denormalized display snapshot on comment write.
- Build a read model populated by user events.

## Current Boundary Debt

Comment identity should come from trusted gateway headers. User display snapshots should be stored on write or fetched through user-service APIs.

## Change Checklist

- Keep auth checks based on gateway headers.
- Do not import user-service internals.
- Keep comment data writes inside comment-service.
- Add tests around create/update/delete authorization before changing mutations.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app -q
```
