# gpt-service Agent Guide

## Purpose

`gpt-service` is intended to own AI summarization, tagging, and LLM-backed
content enrichment. It is currently a scaffold, not a fully wired service.

## Owns

- Future GPT/LLM integration boundaries.
- Prompting and AI model adapters.
- AI-specific request and response schemas.

## Does Not Own

- Board persistence.
- User authentication.
- Comment persistence.
- Gateway routing policy.

## Public Entry Points

No production endpoint is currently wired through `docker-compose.yml`.
Do not assume this service is deployed until compose and gateway routes are
added.

## Data Boundary

GPT features should receive content through explicit API calls or events. Do
not let GPT code import board-service DB controllers directly.

## Change Checklist

- Define the API contract before wiring gateway routes.
- Keep API keys in environment variables only.
- Do not log prompts if they can contain private user data.
- Add timeout and error handling around model calls.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall . -q
```

