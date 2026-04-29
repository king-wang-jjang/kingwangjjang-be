# Backend Docs Index

`kingwangjjang-be` backend documentation starts here. Agent-specific MSA
guides live under `docs/agents` and should be checked before editing a service.

## Agent MSA Docs

- [Agent MSA Guide](./agents/README.md)
- [api-gateway](./agents/api-gateway.md)
- [user-service](./agents/user-service.md)
- [board-service](./agents/board-service.md)
- [comment-service](./agents/comment-service.md)
- [gpt-service](./agents/gpt-service.md)
- [notification-service](./agents/notification-service.md)

## Project Docs

- [Runbook](./RUNBOOK.md)
- [Architecture](./ARCHITECTURE.md)

## Service READMEs

- [api-gateway](../api-gateway/README.md)
- [user-service](../user-service/README.md)
- [board-service](../board-service/README.md)
- [comment-service](../comment-service/README.md)
- [gpt-service](../gpt-service/README.md)
- [notification-service](../notification-service/README.md)

## Agent Usage

- Start with [Agent MSA Guide](./agents/README.md) for global boundaries.
- Open the service-specific agent doc before changing service code.
- If a service needs another service's data, prefer API/read-model integration
  over direct DB access.
- Keep `api-gateway` free of DB ownership and business logic.
