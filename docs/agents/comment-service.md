# comment-service Agent Guide

## Purpose

`comment-service` owns comment CRUD, replies, comment likes, and comment GraphQL
behavior.

## Owns

- `Comment` collection.
- Comment creation, update, soft delete, reply counts, and comment likes.
- Comment GraphQL schema under `/comment-graphql`.

## Does Not Own

- Board content storage.
- User profile persistence.
- OAuth, JWT issuing, or refresh-token storage.
- Gateway route decisions.

## Public Entry Points

| Path | Description |
| --- | --- |
| `/comment-graphql` | Comment GraphQL API. |

## Data Boundary

Comment mutations should trust identity headers from gateway after auth status
checks. Do not resolve user details by directly reading `users`. If comments
need display names, prefer one of these:

- Ask user-service through an API.
- Store a denormalized display snapshot on comment write.
- Build a read model populated by user events.

## Current Boundary Debt

Some existing code directly looks up `users` for nicknames and DB user IDs.
Do not add more direct user collection reads. Plan a migration when changing
comment identity or display-name behavior.

## Change Checklist

- Keep auth checks based on gateway headers.
- Do not import user-service internals.
- Keep comment data writes inside comment-service.
- Add tests around create/update/delete authorization before changing mutations.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app -q
```

