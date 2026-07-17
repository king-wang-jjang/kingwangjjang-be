# gpt-service Agent Guide

## Purpose

`gpt-service` owns AI summarization, tagging, vision extraction, and the
registry of upstream AI server nodes.

## Owns

- AI node and model registration.
- Capability-aware node selection, health tracking, and failover.
- Prompting and AI model adapters.
- AI-specific request and response schemas.

## Does Not Own

- Board persistence.
- User authentication.
- Comment persistence.
- Gateway routing policy.

## Public Entry Points

- Internal inference: `/api/ai/analyze`, `/api/ai/chat`, `/api/ai/vision-text`.
- Node management: `/api/ai/nodes` and `/api/ai/nodes/{node_id}/health-check`.
- Gateway prefix for management: `/gptservice/api/ai/...`.
- Local source port: `33336`.

Node management requires `X-AI-Admin-Token` when `AI_NODE_ADMIN_TOKEN` is set.
Inference requires `X-AI-Service-Token` when `AI_SERVICE_TOKEN` is set. Both
tokens must be configured in production.

## Data Boundary

GPT features should receive content through explicit API calls or events. Do
not let GPT code import board-service DB controllers directly.

## Change Checklist

- Define the API contract before wiring gateway routes.
- Keep API keys in environment variables only.
- Store only an API-key environment-variable name (`api_key_env`) on a node.
- Do not log prompts if they can contain private user data.
- Add timeout and error handling around model calls.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall . -q
```
