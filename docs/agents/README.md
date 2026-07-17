# Agent MSA Guide

This directory is the agent-facing guide for working on each backend service.
Use it before editing service code. The goal is to keep MSA boundaries explicit
and prevent cross-service shortcuts.

## Service Map

| Service | Runtime status | Port | Agent doc |
| --- | --- | ---: | --- |
| api-gateway | active | 8000 | [api-gateway.md](./api-gateway.md) |
| user-service | active | 33334 | [user-service.md](./user-service.md) |
| board-service | active | 33333 | [board-service.md](./board-service.md) |
| comment-service | active | 33335 | [comment-service.md](./comment-service.md) |
| gpt-service | active | 33336 | [gpt-service.md](./gpt-service.md) |
| notification-service | scaffold | 8000 | [notification-service.md](./notification-service.md) |

## Global Agent Rules

- Keep business ownership inside the service that owns the domain.
- Do not read or write another service's collections directly.
- Do not add DB dependencies to `api-gateway`.
- Expose cross-service data through REST APIs or purpose-built read models.
- Preserve trusted identity headers from gateway only: `X-User-Id`, `X-Auth-Provider`, `X-Auth-Status`, `X-Auth-Error`.
- Strip client-supplied identity headers at the gateway before forwarding.
- If a change needs another service's data, update the producer service API first instead of importing its DB layer.
- For local source execution, use `dev.ps1` or `dev.sh`.
- For container execution, use `run.ps1` or `run.sh`.

## Local Source Commands

```bash
./dev.sh up
./dev.sh logs
./dev.sh down
```

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1 up
.\dev.ps1 logs
.\dev.ps1 down
```

## Verification Baseline

Run these after changing gateway, user auth, or agent docs:

```bash
python -m pytest tests -q
```

```powershell
.\user-service\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\api-gateway\.venv\Scripts\python.exe -m compileall app -q
.\user-service\.venv\Scripts\python.exe -m compileall app -q
```
