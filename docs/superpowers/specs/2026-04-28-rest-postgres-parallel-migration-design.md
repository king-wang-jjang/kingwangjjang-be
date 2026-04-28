# REST + PostgreSQL Parallel Migration Design

## Goal

Move the system from GraphQL + MongoDB toward REST API + PostgreSQL without breaking the current application during the transition.

The migration will run the new REST/PostgreSQL path beside the existing GraphQL/MongoDB path. Existing GraphQL endpoints and Mongo controllers stay in place until each frontend workflow has been moved and verified.

## Current System

The backend is a FastAPI microservice system:

- `api-gateway`
- `user-service`
- `board-service`
- `comment-service`
- `gpt-service`
- `notification-service`

The active frontend calls GraphQL through Apollo:

- `/userservice/user-graphql`
- `/boardservice/board-graphql`
- `/commentservice/comment-graphql`

The active persistence layer is MongoDB through service-local `MongoController` classes.

## Migration Strategy

Use a parallel migration:

1. Keep all existing GraphQL endpoints.
2. Keep all existing MongoDB code.
3. Add PostgreSQL as a development database.
4. Add service-local PostgreSQL connection modules.
5. Add REST routers beside the GraphQL routers.
6. Seed PostgreSQL with development data only.
7. Move frontend hooks from Apollo to REST one workflow at a time.
8. Remove GraphQL, Apollo, generated GraphQL types, and MongoDB code only after the REST path fully covers the app.

This design excludes production MongoDB data migration. Development seed data is enough for this phase.

## PostgreSQL Configuration

`kingwangjjang-be/docker-compose.yml` includes a development PostgreSQL service:

- service name: `kingwangjjang-postgres`
- image: `postgres:16-alpine`
- container port: `5432`
- host port: `5432`
- volume: `kingwangjjang-postgres-data`

The local `.env` owns the actual values. Required keys:

```env
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DATABASE_URL
DOCKER_DATABASE_URL
```

Use `DATABASE_URL` when running Python services directly on the host. Use `DOCKER_DATABASE_URL` inside Docker services because containers must connect to `kingwangjjang-postgres`, not `localhost`.

Secrets must stay in `.env` or server environment variables. Do not commit real passwords, OAuth client secrets, JWT secrets, Slack hooks, Discord hooks, or cloud keys.

## Authentication Boundary

The REST implementation must not bind route handlers directly to the current gateway headers. Each service will expose an auth dependency layer:

- `app/auth/principal.py`
- `app/auth/dependencies.py`

The shared shape is:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    user_id: str | None
    auth_provider: str | None
    is_authenticated: bool
```

The first implementation reads the current gateway headers:

- `X-User-Id`
- `X-Auth-Provider`
- `X-Auth-Status`

REST routers depend on `Principal`, not on headers. If authentication later changes to direct JWT verification, session cookies, service tokens, or provider-token validation, only the auth dependency layer should change.

## Database Model

Use SQLAlchemy-style relational tables in PostgreSQL. The first implementation can use one development database with service-owned tables. Later deployment can split into per-service databases by replacing environment URLs.

### User Service

`users`

- `id UUID PRIMARY KEY`
- `user_id TEXT NOT NULL`
- `auth_provider TEXT NOT NULL`
- `nickname TEXT NULL`
- `profile_image TEXT NULL`
- `refresh_token TEXT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- unique key: `(auth_provider, user_id)`

### Board Service

`boards`

- `id UUID PRIMARY KEY`
- `source_id TEXT NULL`
- `category TEXT NOT NULL`
- `no INTEGER NOT NULL`
- `site TEXT NOT NULL`
- `title TEXT NOT NULL`
- `url TEXT NOT NULL`
- `contents JSONB NOT NULL DEFAULT '[]'`
- `gpt_answer TEXT NULL`
- `thumbnail TEXT NULL`
- `comment_count INTEGER NOT NULL DEFAULT 0`
- `like_count INTEGER NOT NULL DEFAULT 0`
- `created_at TIMESTAMPTZ NOT NULL`
- index: `created_at DESC`
- index: `(site, source_id)`

`board_likes`

- `id UUID PRIMARY KEY`
- `board_id UUID NOT NULL`
- `user_id TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- unique key: `(board_id, user_id)`

### Comment Service

`comments`

- `id UUID PRIMARY KEY`
- `board_id UUID NOT NULL`
- `parent_id UUID NULL`
- `user_id TEXT NOT NULL`
- `user_nickname TEXT NULL`
- `content TEXT NOT NULL`
- `like_count INTEGER NOT NULL DEFAULT 0`
- `reply_count INTEGER NOT NULL DEFAULT 0`
- `is_deleted BOOLEAN NOT NULL DEFAULT FALSE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- index: `(board_id, created_at DESC)`
- index: `parent_id`

`comment_likes`

- `id UUID PRIMARY KEY`
- `comment_id UUID NOT NULL`
- `user_id TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- unique key: `(comment_id, user_id)`

## REST API Contract

Response fields intentionally stay close to the existing GraphQL field names to reduce frontend churn.

### User Service

`GET /api/users/me`

Authenticated response:

```json
{
  "Id": "uuid",
  "userId": "12345",
  "nickname": "dev-user",
  "authProvider": "kakao",
  "profileImage": null,
  "createTime": "2026-04-28T00:00:00Z"
}
```

Unauthenticated response:

```json
null
```

### Board Service

`GET /api/boards/realtime?index=0&limit=30`

```json
[
  {
    "_id": "uuid",
    "category": "humor",
    "no": 1,
    "site": "dcinside",
    "title": "seed title",
    "url": "https://example.com/post/1",
    "contents": [],
    "gpt_answer": null,
    "create_time": "2026-04-28T00:00:00Z",
    "thumbnail": null,
    "comment_count": 2,
    "likeCount": 0
  }
]
```

`GET /api/boards/daily?index=0&limit=30`

Returns the same item shape as realtime.

`POST /api/boards/{board_id}/likes`

```json
{
  "boardId": "uuid",
  "site": "dcinside",
  "likeCount": 1
}
```

### Comment Service

`GET /api/comments?boardId={board_id}&page=1&limit=100`

```json
{
  "boardId": "uuid",
  "totalCount": 2,
  "comments": [
    {
      "Id": "uuid",
      "boardId": "uuid",
      "parentId": null,
      "content": "seed comment",
      "userId": "dev-user",
      "userNickname": "dev-user",
      "likeCount": 0,
      "replyCount": 1,
      "isLiked": false,
      "isDeleted": false,
      "createdAt": "2026-04-28T00:00:00Z",
      "updatedAt": "2026-04-28T00:00:00Z"
    }
  ]
}
```

`POST /api/comments`

Request:

```json
{
  "boardId": "uuid",
  "parentId": null,
  "content": "hello"
}
```

Response: created comment object.

`PATCH /api/comments/{comment_id}`

Request:

```json
{
  "content": "updated"
}
```

Response: updated comment object.

`DELETE /api/comments/{comment_id}`

```json
{
  "ok": true
}
```

`POST /api/comments/{comment_id}/like`

```json
{
  "Id": "uuid",
  "likeCount": 1,
  "isLiked": true
}
```

## Frontend Transition

The frontend will not remove Apollo immediately.

Add REST client utilities first, then replace callers:

1. `AuthInitializer` moves from `ME_QUERY` to `GET /userservice/api/users/me`.
2. Board list hooks move from `RealtimePaginationDocument` to `GET /boardservice/api/boards/realtime`.
3. Comment hooks move from GraphQL comment operations to `/commentservice/api/comments`.
4. Apollo providers and GraphQL codegen remain until all GraphQL call sites are gone.

## Development Seed

PostgreSQL seed data should include:

- one development user
- at least three board rows
- root comments and one reply for at least one board
- board/comment likes that exercise authenticated and unauthenticated states

Seed IDs should be stable UUIDs so frontend examples, comments, and boards can refer to the same records across test runs.

## Testing Strategy

Use test-driven changes for each migration step.

Required tests:

- PostgreSQL URL parsing and missing-config failure.
- Auth dependency behavior for anonymous and authenticated requests.
- User REST `GET /api/users/me`.
- Board REST pagination and like idempotency.
- Comment REST list/create/update/delete/like behavior.
- API gateway proxy continues to forward both GraphQL and REST paths.
- Frontend REST client mapping preserves the shapes consumed by existing components.

Existing GraphQL/Mongo behavior should continue to pass until final cleanup.

## Rollout Plan

1. Infrastructure: PostgreSQL compose service and env keys.
2. Backend foundation: per-service PostgreSQL modules and auth dependencies.
3. User REST API.
4. Board REST API and seed boards.
5. Comment REST API and seed comments.
6. Frontend REST clients and hook migration.
7. Verification against local gateway.
8. Cleanup plan for GraphQL/Apollo/Mongo after REST coverage is complete.

## Non-Goals

- No production MongoDB data migration.
- No immediate removal of GraphQL.
- No immediate removal of Apollo Client.
- No redesign of authentication provider flow.
- No service-to-service auth redesign in this phase.

## Decisions

- Use staged parallel migration.
- Use development seed data only.
- Add PostgreSQL Docker setup now.
- Keep current gateway auth headers behind a `Principal` abstraction.
- Use REST response shapes close to the existing GraphQL client shapes.
