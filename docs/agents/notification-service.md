# notification-service Agent Guide

## Purpose

`notification-service` is intended to own user notifications. It is currently a
scaffold, not a fully wired service.

## Owns

- Future notification delivery workflows.
- Notification templates and delivery adapters.
- Notification state if persistence is added.

## Does Not Own

- Board write logic.
- Comment write logic.
- User authentication.
- GPT summarization.

## Public Entry Points

No production endpoint is currently wired through `docker-compose.yml`.
Do not assume this service is deployed until compose and gateway routes are
added.

## Data Boundary

Notification triggers should arrive through events or explicit service APIs.
Do not import board-service, comment-service, or user-service DB controllers.

## Change Checklist

- Choose sync API vs async event flow before implementation.
- Keep delivery credentials in environment variables only.
- Add retry and idempotency rules before sending external notifications.
- Avoid making business services block on notification delivery.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall . -q
```

