# REST PostgreSQL Parallel Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add REST API + PostgreSQL paths beside the existing GraphQL + MongoDB implementation, then migrate frontend hooks to REST without removing GraphQL yet.

**Architecture:** Each backend service gets its own PostgreSQL connection module, SQLAlchemy table models, repository, auth principal dependency, and REST router. Existing GraphQL routers and Mongo controllers remain active until the frontend is fully migrated.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, psycopg 3, PostgreSQL 16, pytest/unittest, Next.js 14, React hooks, fetch-based REST client.

---

## File Structure

Backend infrastructure:

- Modify: `docker-compose.yml` to keep the PostgreSQL dev service and pass `DATABASE_URL` into source services.
- Modify: `dev.ps1` and `dev.sh` to load `DATABASE_URL` from the root `.env` file when running outside Docker.
- Modify: `tests/test_dev_scripts.py` to verify the dev scripts expose database configuration.
- Modify: `tests/test_msa_auth_boundaries.py` to verify gateway proxy still supports REST and GraphQL prefixes.

User service:

- Modify: `user-service/pyproject.toml` to add `sqlalchemy` and `psycopg`.
- Create: `user-service/app/auth/principal.py`.
- Create: `user-service/app/auth/dependencies.py`.
- Create: `user-service/app/db/postgres.py`.
- Create: `user-service/app/db/models.py`.
- Create: `user-service/app/db/seed.py`.
- Create: `user-service/app/repositories/users.py`.
- Create: `user-service/app/routes/users.py`.
- Modify: `user-service/app/main.py` to include the REST router.
- Modify: `user-service/app/services/auth_service.py` to accept the new user repository shape without removing `MongoController`.
- Test: `user-service/tests/test_rest_users.py`.

Board service:

- Modify: `board-service/pyproject.toml` to add explicit `sqlalchemy` and `psycopg`.
- Create: `board-service/app/auth/principal.py`.
- Create: `board-service/app/auth/dependencies.py`.
- Create: `board-service/app/db/postgres.py`.
- Create: `board-service/app/db/models.py`.
- Create: `board-service/app/db/seed.py`.
- Create: `board-service/app/repositories/boards.py`.
- Create: `board-service/app/routes/boards.py`.
- Modify: `board-service/app/main.py` to include the REST router.
- Test: `board-service/tests/test_rest_boards.py`.

Comment service:

- Modify: `comment-service/pyproject.toml` to add `sqlalchemy` and `psycopg`.
- Create: `comment-service/app/auth/principal.py`.
- Create: `comment-service/app/auth/dependencies.py`.
- Create: `comment-service/app/db/postgres.py`.
- Create: `comment-service/app/db/models.py`.
- Create: `comment-service/app/db/seed.py`.
- Create: `comment-service/app/repositories/comments.py`.
- Create: `comment-service/app/routes/comments.py`.
- Modify: `comment-service/app/main.py` to include the REST router.
- Test: `comment-service/tests/test_rest_comments.py`.

Frontend:

- Create: `../kingwangjjang-fe/src/api/http.ts`.
- Create: `../kingwangjjang-fe/src/api/user-api.ts`.
- Create: `../kingwangjjang-fe/src/api/board-api.ts`.
- Create: `../kingwangjjang-fe/src/api/comment-api.ts`.
- Modify: `../kingwangjjang-fe/src/auth/auth-initializer.tsx`.
- Modify: `../kingwangjjang-fe/src/hooks/use-infinite-scrollable-post-list.ts`.
- Modify: `../kingwangjjang-fe/src/hooks/use-board.ts`.
- Modify: `../kingwangjjang-fe/src/hooks/use-comments.ts`.
- Modify: `../kingwangjjang-fe/src/types/user.ts`.
- Modify: `../kingwangjjang-fe/src/types/comment.ts`.

---

### Task 1: Backend Infrastructure Guardrails

**Files:**
- Modify: `tests/test_dev_scripts.py`
- Modify: `tests/test_msa_auth_boundaries.py`
- Modify: `dev.ps1`
- Modify: `dev.sh`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Write failing tests for PostgreSQL configuration in dev scripts**

Add these assertions to `tests/test_dev_scripts.py`:

```python
def test_dev_scripts_export_database_url_for_local_services():
    sh_content = (ROOT / "dev.sh").read_text(encoding="utf-8")
    ps1_content = (ROOT / "dev.ps1").read_text(encoding="utf-8")

    assert "DATABASE_URL=<from .env>" in sh_content
    assert "DATABASE_URL=<from .env>" in ps1_content
    assert "load_dev_env_file" in sh_content
    assert "Import-DevEnvFile" in ps1_content
```

- [ ] **Step 2: Write failing tests for REST proxy support**

Add this test to `tests/test_msa_auth_boundaries.py`:

```python
def test_gateway_proxy_keeps_rest_and_graphql_service_prefixes():
    routes = read(API_GATEWAY_APP / "routes" / "index.py")

    assert '"boardservice/"' in routes
    assert '"userservice/"' in routes
    assert '"commentservice/"' in routes
    assert "path.startswith(prefix)" in routes
    assert "path[len(prefix):]" in routes
```

- [ ] **Step 3: Run tests and verify the first test fails**

Run:

```powershell
python -m pytest tests/test_dev_scripts.py tests/test_msa_auth_boundaries.py -q
```

Expected: `test_dev_scripts_export_database_url_for_local_services` fails because `dev.ps1` and `dev.sh` do not load `DATABASE_URL` from `.env` yet.

- [ ] **Step 4: Update PowerShell dev script**

In `dev.ps1`, update `$DevEnv`:

```powershell
$DevEnv = 'SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL=<from .env>'
```

Add this function after `Ensure-Env`:

```powershell
function Import-DevEnvFile {
  $envPath = Join-Path $RootDir '.env'
  if (-not (Test-Path $envPath)) {
    return
  }

  foreach ($rawLine in Get-Content $envPath) {
    $line = $rawLine.Trim()
    if ($line -eq '' -or $line.StartsWith('#') -or -not $line.Contains('=')) {
      continue
    }

    $parts = $line -split '=', 2
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    if ($name -match '^[A-Za-z_][A-Za-z0-9_]*$' -and -not [Environment]::GetEnvironmentVariable($name, 'Process')) {
      [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
  }
}
```

In `Start-DevService`, read `DATABASE_URL` from the current process and pass it to the child service process:

```powershell
$databaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL', 'Process')
if (-not $databaseUrl) {
  throw 'DATABASE_URL is required. Set it in .env or the current shell.'
}
$escapedDatabaseUrl = $databaseUrl.Replace("'", "''")
$command = "`$env:SERVER_RUN_MODE='FALSE'; `$env:AUTH_COOKIE_SECURE='FALSE'; `$env:DATABASE_URL='$escapedDatabaseUrl'; poetry run uvicorn app.main:app --host 0.0.0.0 --port $Port *> '$logFile'"
```

In `Cmd-Up`, call the importer after `Ensure-Env`:

```powershell
Import-DevEnvFile
```

- [ ] **Step 5: Update shell dev script**

In `dev.sh`, set the grep-friendly dev env string without committing secrets:

```bash
DEV_ENV="SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL=<from .env>"
```

Add this function after `ensure_env`:

```bash
load_dev_env_file() {
  local env_file="$ROOT_DIR/.env"
  [[ -f "$env_file" ]] || return 0

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" || "$line" != *=* ]] && continue

    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && -z "${!key+x}" ]]; then
      export "$key=$value"
    fi
  done < "$env_file"
}
```

In `cmd_up`, call the loader after `ensure_env`:

```bash
load_dev_env_file
```

In the service start command, require and pass the loaded value:

```bash
: "${DATABASE_URL:?DATABASE_URL is required. Set it in .env or the current shell.}"
env SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE DATABASE_URL="$DATABASE_URL" poetry run uvicorn app.main:app --host 0.0.0.0 --port "$port" >"$log_file" 2>&1
```

- [ ] **Step 6: Verify compose configuration**

Run:

```powershell
docker compose config --quiet
```

Expected: exit code `0`. Existing local warnings about Docker config access, missing `DOCKERHUB_USERNAME`, or obsolete compose `version` are acceptable during this task.

- [ ] **Step 7: Run infrastructure tests**

Run:

```powershell
python -m pytest tests/test_dev_scripts.py tests/test_msa_auth_boundaries.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit infrastructure changes**

Run:

```powershell
git add docker-compose.yml dev.ps1 dev.sh tests/test_dev_scripts.py tests/test_msa_auth_boundaries.py docs/superpowers/specs/2026-04-28-rest-postgres-parallel-migration-design.md
git commit -m "chore: add postgres parallel migration foundation"
```

---

### Task 2: User Service REST Foundation

**Files:**
- Modify: `user-service/pyproject.toml`
- Create: `user-service/app/auth/principal.py`
- Create: `user-service/app/auth/dependencies.py`
- Create: `user-service/app/db/postgres.py`
- Create: `user-service/app/db/models.py`
- Create: `user-service/app/db/seed.py`
- Create: `user-service/app/repositories/users.py`
- Create: `user-service/app/routes/users.py`
- Modify: `user-service/app/main.py`
- Test: `user-service/tests/test_rest_users.py`

- [ ] **Step 1: Add failing user REST tests**

Create `user-service/tests/test_rest_users.py`:

```python
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault("JWT_SECRET_KEY", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.routes.users import router as users_router


def build_client(principal: Principal | None = None):
    app = FastAPI()
    app.include_router(users_router)

    if principal is not None:
        app.dependency_overrides[get_optional_principal] = lambda: principal

    return TestClient(app)


def test_me_returns_null_for_anonymous_user():
    client = build_client(Principal(user_id=None, auth_provider=None, is_authenticated=False))

    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json() is None


def test_me_returns_authenticated_principal_user(monkeypatch):
    user_id = str(uuid4())

    class FakeRepository:
        def get_or_create_from_principal(self, principal):
            return {
                "id": user_id,
                "user_id": principal.user_id,
                "auth_provider": principal.auth_provider,
                "nickname": "dev-user",
                "profile_image": None,
                "created_at": "2026-04-28T00:00:00Z",
            }

    from app.routes import users

    monkeypatch.setattr(users, "UserRepository", lambda: FakeRepository())
    client = build_client(Principal(user_id="12345", auth_provider="kakao", is_authenticated=True))

    response = client.get("/api/users/me")

    assert response.status_code == 200
    assert response.json() == {
        "Id": user_id,
        "userId": "12345",
        "nickname": "dev-user",
        "authProvider": "kakao",
        "profileImage": None,
        "createTime": "2026-04-28T00:00:00Z",
    }
```

- [ ] **Step 2: Run the new tests and verify import failure**

Run:

```powershell
cd user-service
python -m pytest tests/test_rest_users.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.auth'`.

- [ ] **Step 3: Add dependencies**

In `user-service/pyproject.toml`, under `[tool.poetry.dependencies]`, add:

```toml
sqlalchemy = "^2.0.36"
psycopg = { extras = ["binary"], version = "^3.2.3" }
```

- [ ] **Step 4: Implement auth principal**

Create `user-service/app/auth/principal.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str | None
    auth_provider: str | None
    is_authenticated: bool
```

Create `user-service/app/auth/dependencies.py`:

```python
from fastapi import HTTPException, Request, status

from app.auth.principal import Principal


def get_optional_principal(request: Request) -> Principal:
    auth_status = request.headers.get("X-Auth-Status", "unauthenticated")
    user_id = request.headers.get("X-User-Id")
    auth_provider = request.headers.get("X-Auth-Provider")
    is_authenticated = auth_status == "authenticated" and bool(user_id)
    return Principal(user_id=user_id, auth_provider=auth_provider, is_authenticated=is_authenticated)


def require_principal(request: Request) -> Principal:
    principal = get_optional_principal(request)
    if not principal.is_authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return principal
```

- [ ] **Step 5: Implement PostgreSQL connection**

Create `user-service/app/db/postgres.py`:

```python
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


class Base(DeclarativeBase):
    pass


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 6: Implement user SQL model**

Create `user-service/app/db/models.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("auth_provider", "user_id", name="uq_users_provider_user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_image: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 7: Implement user repository**

Create `user-service/app/repositories/users.py`:

```python
from sqlalchemy import select

from app.auth.principal import Principal
from app.db.models import User
from app.db.postgres import Base, SessionLocal, engine


class UserRepository:
    def __init__(self):
        Base.metadata.create_all(bind=engine)

    def get_or_create_from_principal(self, principal: Principal) -> dict:
        if not principal.user_id:
            raise ValueError("principal.user_id is required")

        auth_provider = principal.auth_provider or "unknown"

        with SessionLocal() as session:
            user = session.scalar(
                select(User).where(
                    User.user_id == principal.user_id,
                    User.auth_provider == auth_provider,
                )
            )
            if user is None:
                user = User(
                    user_id=principal.user_id,
                    auth_provider=auth_provider,
                    nickname="dev-user",
                    profile_image=None,
                )
                session.add(user)
                session.commit()
                session.refresh(user)

            return {
                "id": user.id,
                "user_id": user.user_id,
                "auth_provider": user.auth_provider,
                "nickname": user.nickname,
                "profile_image": user.profile_image,
                "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
            }
```

- [ ] **Step 8: Implement user REST router**

Create `user-service/app/routes/users.py`:

```python
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.repositories.users import UserRepository


router = APIRouter(prefix="/api/users", tags=["users"])


def _to_me_response(user: dict) -> dict:
    return {
        "Id": user["id"],
        "userId": user["user_id"],
        "nickname": user.get("nickname"),
        "authProvider": user["auth_provider"],
        "profileImage": user.get("profile_image"),
        "createTime": user["created_at"],
    }


@router.get("/me")
def me(principal: Principal = Depends(get_optional_principal)):
    if not principal.is_authenticated:
        return None

    user = UserRepository().get_or_create_from_principal(principal)
    return _to_me_response(user)
```

- [ ] **Step 9: Include router in main**

In `user-service/app/main.py`, add:

```python
from app.routes.users import router as users_router
```

After `app.include_router(auth_router)`, add:

```python
app.include_router(users_router)
```

- [ ] **Step 10: Run user REST tests**

Run:

```powershell
cd user-service
python -m pytest tests/test_rest_users.py -q
```

Expected: `2 passed`.

- [ ] **Step 11: Commit user REST foundation**

Run:

```powershell
git add user-service/pyproject.toml user-service/app/auth user-service/app/db/postgres.py user-service/app/db/models.py user-service/app/repositories user-service/app/routes/users.py user-service/app/main.py user-service/tests/test_rest_users.py
git commit -m "feat: add user rest postgres foundation"
```

---

### Task 3: Board Service REST API

**Files:**
- Modify: `board-service/pyproject.toml`
- Create: `board-service/app/auth/principal.py`
- Create: `board-service/app/auth/dependencies.py`
- Create: `board-service/app/db/postgres.py`
- Create: `board-service/app/db/models.py`
- Create: `board-service/app/db/seed.py`
- Create: `board-service/app/repositories/boards.py`
- Create: `board-service/app/routes/boards.py`
- Modify: `board-service/app/main.py`
- Test: `board-service/tests/test_rest_boards.py`

- [ ] **Step 1: Add failing board REST tests**

Create `board-service/tests/test_rest_boards.py`:

```python
import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.auth.dependencies import get_optional_principal
from app.auth.principal import Principal
from app.routes.boards import router as boards_router


class FakeRepository:
    def list_realtime(self, index: int, limit: int):
        assert index == 0
        assert limit == 30
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "category": "humor",
                "no": 1,
                "site": "dcinside",
                "title": "seed title",
                "url": "https://example.com/post/1",
                "contents": [],
                "gpt_answer": None,
                "created_at": "2026-04-28T00:00:00Z",
                "thumbnail": None,
                "comment_count": 2,
                "like_count": 0,
            }
        ]

    def list_daily(self, index: int, limit: int):
        return self.list_realtime(index, limit)

    def add_like(self, board_id: str, user_id: str):
        return {"board_id": board_id, "site": "dcinside", "like_count": 1}


def build_client(monkeypatch, principal=None):
    from app.routes import boards

    monkeypatch.setattr(boards, "BoardRepository", lambda: FakeRepository())
    app = FastAPI()
    app.include_router(boards_router)
    if principal is not None:
        app.dependency_overrides[get_optional_principal] = lambda: principal
    return TestClient(app)


def test_realtime_returns_graphql_compatible_shape(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get("/api/boards/realtime")

    assert response.status_code == 200
    assert response.json()[0]["_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()[0]["likeCount"] == 0
    assert response.json()[0]["create_time"] == "2026-04-28T00:00:00Z"


def test_add_like_requires_authentication(monkeypatch):
    client = build_client(monkeypatch, Principal(user_id=None, auth_provider=None, is_authenticated=False))

    response = client.post("/api/boards/11111111-1111-1111-1111-111111111111/likes")

    assert response.status_code == 401


def test_add_like_returns_like_count(monkeypatch):
    client = build_client(monkeypatch, Principal(user_id="dev-user", auth_provider="local", is_authenticated=True))

    response = client.post("/api/boards/11111111-1111-1111-1111-111111111111/likes")

    assert response.status_code == 200
    assert response.json() == {
        "boardId": "11111111-1111-1111-1111-111111111111",
        "site": "dcinside",
        "likeCount": 1,
    }
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```powershell
cd board-service
python -m pytest tests/test_rest_boards.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.auth'`.

- [ ] **Step 3: Add dependencies**

In `board-service/pyproject.toml`, under `[tool.poetry.dependencies]`, add explicit entries:

```toml
sqlalchemy = "^2.0.36"
psycopg = { extras = ["binary"], version = "^3.2.3" }
```

- [ ] **Step 4: Implement auth dependency**

Create the same `Principal`, `get_optional_principal`, and `require_principal` files from Task 2 under `board-service/app/auth/`.

- [ ] **Step 5: Implement PostgreSQL module**

Create `board-service/app/db/postgres.py` with the same content as Task 2.

- [ ] **Step 6: Implement board SQL models**

Create `board-service/app/db/models.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    no: Mapped[int] = mapped_column(Integer, nullable=False)
    site: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    contents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    gpt_answer: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class BoardLike(Base):
    __tablename__ = "board_likes"
    __table_args__ = (UniqueConstraint("board_id", "user_id", name="uq_board_likes_board_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 7: Implement board repository**

Create `board-service/app/repositories/boards.py`:

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Board, BoardLike
from app.db.postgres import Base, SessionLocal, engine


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


class BoardRepository:
    def __init__(self):
        Base.metadata.create_all(bind=engine)

    def _to_dict(self, board: Board) -> dict:
        return {
            "id": board.id,
            "category": board.category,
            "no": board.no,
            "site": board.site,
            "title": board.title,
            "url": board.url,
            "contents": board.contents,
            "gpt_answer": board.gpt_answer,
            "created_at": _iso(board.created_at),
            "thumbnail": board.thumbnail,
            "comment_count": board.comment_count,
            "like_count": board.like_count,
        }

    def list_realtime(self, index: int, limit: int) -> list[dict]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(Board).order_by(Board.created_at.desc()).offset(index * limit).limit(limit)
            ).all()
            return [self._to_dict(row) for row in rows]

    def list_daily(self, index: int, limit: int) -> list[dict]:
        return self.list_realtime(index, limit)

    def add_like(self, board_id: str, user_id: str) -> dict:
        with SessionLocal() as session:
            board = session.get(Board, board_id)
            if board is None:
                raise KeyError("Board not found")

            like = BoardLike(board_id=board_id, user_id=user_id)
            session.add(like)
            try:
                board.like_count += 1
                session.commit()
            except IntegrityError:
                session.rollback()
                board = session.get(Board, board_id)

            return {"board_id": board.id, "site": board.site, "like_count": board.like_count}
```

- [ ] **Step 8: Implement board REST router**

Create `board-service/app/routes/boards.py`:

```python
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_principal
from app.auth.principal import Principal
from app.repositories.boards import BoardRepository


router = APIRouter(prefix="/api/boards", tags=["boards"])


def _to_board_response(item: dict) -> dict:
    return {
        "_id": item["id"],
        "category": item["category"],
        "no": item["no"],
        "site": item["site"],
        "title": item["title"],
        "url": item["url"],
        "contents": item["contents"],
        "gpt_answer": item.get("gpt_answer"),
        "create_time": item["created_at"],
        "thumbnail": item.get("thumbnail"),
        "comment_count": item.get("comment_count", 0),
        "likeCount": item.get("like_count", 0),
    }


@router.get("/realtime")
def realtime(index: int = 0, limit: int = 30):
    return [_to_board_response(item) for item in BoardRepository().list_realtime(index, limit)]


@router.get("/daily")
def daily(index: int = 0, limit: int = 30):
    return [_to_board_response(item) for item in BoardRepository().list_daily(index, limit)]


@router.post("/{board_id}/likes")
def add_like(board_id: str, principal: Principal = Depends(require_principal)):
    try:
        result = BoardRepository().add_like(board_id, principal.user_id or "")
    except KeyError:
        raise HTTPException(status_code=404, detail="Board not found")

    return {
        "boardId": result["board_id"],
        "site": result["site"],
        "likeCount": result["like_count"],
    }
```

- [ ] **Step 9: Include router in main**

In `board-service/app/main.py`, add:

```python
from app.routes.boards import router as boards_router
```

After creating `app`, add:

```python
app.include_router(boards_router)
```

- [ ] **Step 10: Run board tests**

Run:

```powershell
cd board-service
python -m pytest tests/test_rest_boards.py -q
```

Expected: `3 passed`.

- [ ] **Step 11: Commit board REST API**

Run:

```powershell
git add board-service/pyproject.toml board-service/app/auth board-service/app/db/postgres.py board-service/app/db/models.py board-service/app/repositories board-service/app/routes/boards.py board-service/app/main.py board-service/tests/test_rest_boards.py
git commit -m "feat: add board rest postgres api"
```

---

### Task 4: Comment Service REST API

**Files:**
- Modify: `comment-service/pyproject.toml`
- Create: `comment-service/app/auth/principal.py`
- Create: `comment-service/app/auth/dependencies.py`
- Create: `comment-service/app/db/postgres.py`
- Create: `comment-service/app/db/models.py`
- Create: `comment-service/app/repositories/comments.py`
- Create: `comment-service/app/routes/comments.py`
- Modify: `comment-service/app/main.py`
- Test: `comment-service/tests/test_rest_comments.py`

- [ ] **Step 1: Add failing comment REST tests**

Create `comment-service/tests/test_rest_comments.py`:

```python
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.auth.dependencies import get_optional_principal, require_principal
from app.auth.principal import Principal
from app.routes.comments import router as comments_router


class FakeRepository:
    def list_comments(self, board_id: str, page: int, limit: int, viewer_user_id: str | None):
        return {
            "board_id": board_id,
            "total_count": 1,
            "comments": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "board_id": board_id,
                    "parent_id": None,
                    "content": "seed comment",
                    "user_id": "dev-user",
                    "user_nickname": "dev-user",
                    "like_count": 0,
                    "reply_count": 0,
                    "is_liked": False,
                    "is_deleted": False,
                    "created_at": "2026-04-28T00:00:00Z",
                    "updated_at": "2026-04-28T00:00:00Z",
                }
            ],
        }

    def create_comment(self, board_id: str, parent_id: str | None, content: str, user_id: str):
        return self.list_comments(board_id, 1, 1, user_id)["comments"][0] | {"content": content}

    def like_comment(self, comment_id: str, user_id: str):
        return {"id": comment_id, "like_count": 1, "is_liked": True}


def build_client(monkeypatch, principal=None):
    from app.routes import comments

    monkeypatch.setattr(comments, "CommentRepository", lambda: FakeRepository())
    app = FastAPI()
    app.include_router(comments_router)
    if principal is not None:
        app.dependency_overrides[get_optional_principal] = lambda: principal
        app.dependency_overrides[require_principal] = lambda: principal
    return TestClient(app)


def test_list_comments_returns_graphql_compatible_shape(monkeypatch):
    client = build_client(monkeypatch, Principal(user_id=None, auth_provider=None, is_authenticated=False))

    response = client.get("/api/comments?boardId=11111111-1111-1111-1111-111111111111&page=1&limit=100")

    assert response.status_code == 200
    assert response.json()["boardId"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()["comments"][0]["Id"] == "22222222-2222-2222-2222-222222222222"
    assert response.json()["comments"][0]["isLiked"] is False


def test_create_comment_requires_authentication(monkeypatch):
    client = build_client(monkeypatch, Principal(user_id=None, auth_provider=None, is_authenticated=False))

    response = client.post("/api/comments", json={"boardId": "11111111-1111-1111-1111-111111111111", "content": "hello"})

    assert response.status_code == 401


def test_like_comment_returns_like_state(monkeypatch):
    client = build_client(monkeypatch, Principal(user_id="dev-user", auth_provider="local", is_authenticated=True))

    response = client.post("/api/comments/22222222-2222-2222-2222-222222222222/like")

    assert response.status_code == 200
    assert response.json() == {
        "Id": "22222222-2222-2222-2222-222222222222",
        "likeCount": 1,
        "isLiked": True,
    }
```

- [ ] **Step 2: Run tests and verify import failure**

Run:

```powershell
cd comment-service
python -m pytest tests/test_rest_comments.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.auth'`.

- [ ] **Step 3: Add dependencies**

In `comment-service/pyproject.toml`, under `[tool.poetry.dependencies]`, add:

```toml
sqlalchemy = "^2.0.36"
psycopg = { extras = ["binary"], version = "^3.2.3" }
```

- [ ] **Step 4: Implement auth and PostgreSQL modules**

Create the same auth dependency files from Task 2 under `comment-service/app/auth/`.

Create `comment-service/app/db/postgres.py` with the same content as Task 2.

- [ ] **Step 5: Implement comment SQL models**

Create `comment-service/app/db/models.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    board_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_likes_comment_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    comment_id: Mapped[str] = mapped_column(String(36), ForeignKey("comments.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 6: Implement comment repository**

Create `comment-service/app/repositories/comments.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import Comment, CommentLike
from app.db.postgres import Base, SessionLocal, engine


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


class CommentRepository:
    def __init__(self):
        Base.metadata.create_all(bind=engine)

    def _to_dict(self, comment: Comment, is_liked: bool = False) -> dict:
        return {
            "id": comment.id,
            "board_id": comment.board_id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "user_id": comment.user_id,
            "user_nickname": comment.user_nickname,
            "like_count": comment.like_count,
            "reply_count": comment.reply_count,
            "is_liked": is_liked,
            "is_deleted": comment.is_deleted,
            "created_at": _iso(comment.created_at),
            "updated_at": _iso(comment.updated_at),
        }

    def list_comments(self, board_id: str, page: int, limit: int, viewer_user_id: str | None) -> dict:
        offset = (page - 1) * limit
        with SessionLocal() as session:
            total_count = session.scalar(
                select(func.count()).select_from(Comment).where(Comment.board_id == board_id, Comment.is_deleted.is_(False))
            ) or 0
            root_comments = session.scalars(
                select(Comment)
                .where(Comment.board_id == board_id, Comment.parent_id.is_(None), Comment.is_deleted.is_(False))
                .order_by(Comment.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            rows = list(root_comments)
            for root in root_comments:
                rows.extend(
                    session.scalars(
                        select(Comment)
                        .where(Comment.parent_id == root.id, Comment.is_deleted.is_(False))
                        .order_by(Comment.created_at.asc())
                    ).all()
                )

            liked_ids = set()
            if viewer_user_id and rows:
                liked_ids = {
                    like.comment_id
                    for like in session.scalars(
                        select(CommentLike).where(
                            CommentLike.user_id == viewer_user_id,
                            CommentLike.comment_id.in_([row.id for row in rows]),
                        )
                    ).all()
                }

            return {
                "board_id": board_id,
                "total_count": total_count,
                "comments": [self._to_dict(row, row.id in liked_ids) for row in rows],
            }

    def create_comment(self, board_id: str, parent_id: str | None, content: str, user_id: str) -> dict:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            comment = Comment(
                board_id=board_id,
                parent_id=parent_id,
                content=content,
                user_id=user_id,
                user_nickname=user_id,
                created_at=now,
                updated_at=now,
            )
            session.add(comment)
            if parent_id:
                parent = session.get(Comment, parent_id)
                if parent:
                    parent.reply_count += 1
            session.commit()
            session.refresh(comment)
            return self._to_dict(comment, False)

    def like_comment(self, comment_id: str, user_id: str) -> dict:
        with SessionLocal() as session:
            comment = session.get(Comment, comment_id)
            if comment is None:
                raise KeyError("Comment not found")
            like = CommentLike(comment_id=comment_id, user_id=user_id)
            session.add(like)
            try:
                comment.like_count += 1
                session.commit()
                is_liked = True
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(CommentLike).where(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id)
                )
                if existing:
                    session.delete(existing)
                    comment = session.get(Comment, comment_id)
                    comment.like_count = max(0, comment.like_count - 1)
                    session.commit()
                    is_liked = False
                else:
                    is_liked = False
            comment = session.get(Comment, comment_id)
            return {"id": comment.id, "like_count": comment.like_count, "is_liked": is_liked}
```

- [ ] **Step 7: Implement comment REST router**

Create `comment-service/app/routes/comments.py`:

```python
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_optional_principal, require_principal
from app.auth.principal import Principal
from app.repositories.comments import CommentRepository


router = APIRouter(prefix="/api/comments", tags=["comments"])


class CreateCommentRequest(BaseModel):
    boardId: str
    parentId: str | None = None
    content: str


class UpdateCommentRequest(BaseModel):
    content: str


def _to_comment_response(item: dict) -> dict:
    return {
        "Id": item["id"],
        "boardId": item["board_id"],
        "parentId": item.get("parent_id"),
        "content": item["content"],
        "userId": item["user_id"],
        "userNickname": item.get("user_nickname"),
        "likeCount": item["like_count"],
        "replyCount": item["reply_count"],
        "isLiked": item["is_liked"],
        "isDeleted": item["is_deleted"],
        "createdAt": item["created_at"],
        "updatedAt": item["updated_at"],
    }


@router.get("")
def list_comments(boardId: str, page: int = 1, limit: int = 20, principal: Principal = Depends(get_optional_principal)):
    result = CommentRepository().list_comments(
        board_id=boardId,
        page=page,
        limit=limit,
        viewer_user_id=principal.user_id if principal.is_authenticated else None,
    )
    return {
        "boardId": result["board_id"],
        "totalCount": result["total_count"],
        "comments": [_to_comment_response(item) for item in result["comments"]],
    }


@router.post("")
def create_comment(payload: CreateCommentRequest, principal: Principal = Depends(require_principal)):
    item = CommentRepository().create_comment(payload.boardId, payload.parentId, payload.content, principal.user_id or "")
    return _to_comment_response(item)


@router.post("/{comment_id}/like")
def like_comment(comment_id: str, principal: Principal = Depends(require_principal)):
    try:
        result = CommentRepository().like_comment(comment_id, principal.user_id or "")
    except KeyError:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"Id": result["id"], "likeCount": result["like_count"], "isLiked": result["is_liked"]}
```

- [ ] **Step 8: Include router in main**

In `comment-service/app/main.py`, add:

```python
from app.routes.comments import router as comments_router
```

After creating `app`, add:

```python
app.include_router(comments_router)
```

- [ ] **Step 9: Run comment tests**

Run:

```powershell
cd comment-service
python -m pytest tests/test_rest_comments.py -q
```

Expected: `3 passed`.

- [ ] **Step 10: Commit comment REST API**

Run:

```powershell
git add comment-service/pyproject.toml comment-service/app/auth comment-service/app/db/postgres.py comment-service/app/db/models.py comment-service/app/repositories comment-service/app/routes/comments.py comment-service/app/main.py comment-service/tests/test_rest_comments.py
git commit -m "feat: add comment rest postgres api"
```

---

### Task 5: Development Seed Data

**Files:**
- Create: `user-service/app/db/seed.py`
- Create: `board-service/app/db/seed.py`
- Create: `comment-service/app/db/seed.py`
- Test: `user-service/tests/test_seed_data.py`
- Test: `board-service/tests/test_seed_data.py`
- Test: `comment-service/tests/test_seed_data.py`

- [ ] **Step 1: Add seed tests**

Create `board-service/tests/test_seed_data.py`:

```python
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import SEED_BOARD_IDS, seed_boards


def test_board_seed_uses_stable_ids():
    assert SEED_BOARD_IDS[0] == "11111111-1111-1111-1111-111111111111"


def test_board_seed_returns_three_records():
    rows = seed_boards(dry_run=True)

    assert len(rows) == 3
    assert rows[0]["id"] == "11111111-1111-1111-1111-111111111111"
```

Create `comment-service/tests/test_seed_data.py`:

```python
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import seed_comments


def test_comment_seed_references_seed_board():
    rows = seed_comments(dry_run=True)

    assert rows[0]["board_id"] == "11111111-1111-1111-1111-111111111111"
    assert rows[1]["parent_id"] == rows[0]["id"]
```

Create `user-service/tests/test_seed_data.py`:

```python
import sys
from pathlib import Path


SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.db.seed import seed_users


def test_user_seed_contains_dev_user():
    rows = seed_users(dry_run=True)

    assert rows[0]["user_id"] == "dev-user"
    assert rows[0]["auth_provider"] == "local"
```

- [ ] **Step 2: Run seed tests and verify import failures**

Run:

```powershell
cd board-service
python -m pytest tests/test_seed_data.py -q
cd ..\comment-service
python -m pytest tests/test_seed_data.py -q
cd ..\user-service
python -m pytest tests/test_seed_data.py -q
```

Expected: each service fails with `ModuleNotFoundError` for `app.db.seed`.

- [ ] **Step 3: Implement user seed**

Create `user-service/app/db/seed.py`:

```python
from datetime import datetime, timezone


def seed_users(dry_run: bool = False) -> list[dict]:
    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "user_id": "dev-user",
            "auth_provider": "local",
            "nickname": "dev-user",
            "profile_image": None,
            "refresh_token": None,
            "created_at": datetime(2026, 4, 28, tzinfo=timezone.utc),
        }
    ]
    if dry_run:
        return rows

    from app.db.models import User
    from app.db.postgres import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        for row in rows:
            if session.get(User, row["id"]) is None:
                session.add(User(**row))
        session.commit()
    return rows
```

- [ ] **Step 4: Implement board seed**

Create `board-service/app/db/seed.py`:

```python
from datetime import datetime, timezone


SEED_BOARD_IDS = [
    "11111111-1111-1111-1111-111111111111",
    "11111111-1111-1111-1111-111111111112",
    "11111111-1111-1111-1111-111111111113",
]


def seed_boards(dry_run: bool = False) -> list[dict]:
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    rows = [
        {
            "id": SEED_BOARD_IDS[0],
            "source_id": "seed-1",
            "category": "humor",
            "no": 1,
            "site": "dcinside",
            "title": "seed title 1",
            "url": "https://example.com/post/1",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 2,
            "like_count": 0,
            "created_at": created_at,
        },
        {
            "id": SEED_BOARD_IDS[1],
            "source_id": "seed-2",
            "category": "issue",
            "no": 2,
            "site": "ygosu",
            "title": "seed title 2",
            "url": "https://example.com/post/2",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 0,
            "like_count": 0,
            "created_at": created_at,
        },
        {
            "id": SEED_BOARD_IDS[2],
            "source_id": "seed-3",
            "category": "free",
            "no": 3,
            "site": "ppomppu",
            "title": "seed title 3",
            "url": "https://example.com/post/3",
            "contents": [],
            "gpt_answer": None,
            "thumbnail": None,
            "comment_count": 0,
            "like_count": 0,
            "created_at": created_at,
        },
    ]
    if dry_run:
        return rows

    from app.db.models import Board
    from app.db.postgres import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        for row in rows:
            if session.get(Board, row["id"]) is None:
                session.add(Board(**row))
        session.commit()
    return rows
```

- [ ] **Step 5: Implement comment seed**

Create `comment-service/app/db/seed.py`:

```python
from datetime import datetime, timezone


def seed_comments(dry_run: bool = False) -> list[dict]:
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    root_id = "22222222-2222-2222-2222-222222222222"
    rows = [
        {
            "id": root_id,
            "board_id": "11111111-1111-1111-1111-111111111111",
            "parent_id": None,
            "user_id": "dev-user",
            "user_nickname": "dev-user",
            "content": "seed comment",
            "like_count": 0,
            "reply_count": 1,
            "is_deleted": False,
            "created_at": created_at,
            "updated_at": created_at,
        },
        {
            "id": "22222222-2222-2222-2222-222222222223",
            "board_id": "11111111-1111-1111-1111-111111111111",
            "parent_id": root_id,
            "user_id": "dev-user",
            "user_nickname": "dev-user",
            "content": "seed reply",
            "like_count": 0,
            "reply_count": 0,
            "is_deleted": False,
            "created_at": created_at,
            "updated_at": created_at,
        },
    ]
    if dry_run:
        return rows

    from app.db.models import Comment
    from app.db.postgres import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        for row in rows:
            if session.get(Comment, row["id"]) is None:
                session.add(Comment(**row))
        session.commit()
    return rows
```

- [ ] **Step 6: Run seed tests**

Run:

```powershell
cd board-service
python -m pytest tests/test_seed_data.py -q
cd ..\comment-service
python -m pytest tests/test_seed_data.py -q
cd ..\user-service
python -m pytest tests/test_seed_data.py -q
```

Expected: all seed tests pass.

- [ ] **Step 7: Commit seed data**

Run:

```powershell
git add user-service/app/db/seed.py user-service/tests/test_seed_data.py board-service/app/db/seed.py board-service/tests/test_seed_data.py comment-service/app/db/seed.py comment-service/tests/test_seed_data.py
git commit -m "feat: add postgres development seed data"
```

---

### Task 6: Frontend REST Client And Auth Migration

**Files:**
- Create: `../kingwangjjang-fe/src/api/http.ts`
- Create: `../kingwangjjang-fe/src/api/user-api.ts`
- Modify: `../kingwangjjang-fe/src/auth/auth-initializer.tsx`
- Modify: `../kingwangjjang-fe/src/types/user.ts`

- [ ] **Step 1: Add REST user type**

In `../kingwangjjang-fe/src/types/user.ts`, replace `MeResponse` with:

```typescript
import type { UserType } from '../auth/types';

export type MeUserResponse = UserType;
```

- [ ] **Step 2: Add fetch helper**

Create `../kingwangjjang-fe/src/api/http.ts`:

```typescript
import { CONFIG } from 'src/config-global';

type RequestOptions = RequestInit & {
  skipJsonParse?: boolean;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${CONFIG.serverUrl}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with status ${response.status}`);
  }

  if (options.skipJsonParse) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
```

- [ ] **Step 3: Add user API client**

Create `../kingwangjjang-fe/src/api/user-api.ts`:

```typescript
import type { MeUserResponse } from 'src/types/user';

import { apiFetch } from './http';

export function getMe() {
  return apiFetch<MeUserResponse>('/userservice/api/users/me');
}
```

- [ ] **Step 4: Convert AuthInitializer from Apollo to REST**

In `../kingwangjjang-fe/src/auth/auth-initializer.tsx`, remove Apollo imports and replace the component with:

```tsx
'use client';

import { useEffect } from 'react';

import { getMe } from 'src/api/user-api';
import { useAuthStore } from 'src/store/auth-store';

type Props = {
  children: React.ReactNode;
};

export function AuthInitializer({ children }: Props) {
  const { login, logout } = useAuthStore();

  useEffect(() => {
    let mounted = true;

    async function checkUserSession() {
      try {
        const user = await getMe();
        if (!mounted) return;

        if (user) {
          login(user);
        } else {
          logout();
        }
      } catch (error) {
        console.error('Failed to get user info:', error);
        if (mounted) {
          logout();
        }
      }
    }

    checkUserSession();

    return () => {
      mounted = false;
    };
  }, [login, logout]);

  return <>{children}</>;
}
```

- [ ] **Step 5: Run frontend typecheck**

Run:

```powershell
cd ..\kingwangjjang-fe
npm run ts
```

Expected: existing `src/hooks/use-comments.ts` GraphQL generated type errors may still fail until Task 8. There must be no new `AuthInitializer` or `src/api/user-api.ts` errors.

- [ ] **Step 6: Commit frontend auth REST migration**

Run:

```powershell
git add src/api/http.ts src/api/user-api.ts src/auth/auth-initializer.tsx src/types/user.ts
git commit -m "feat: migrate auth initializer to rest"
```

---

### Task 7: Frontend Board REST Migration

**Files:**
- Create: `../kingwangjjang-fe/src/api/board-api.ts`
- Modify: `../kingwangjjang-fe/src/hooks/use-infinite-scrollable-post-list.ts`
- Modify: `../kingwangjjang-fe/src/hooks/use-board.ts`
- Modify: `../kingwangjjang-fe/src/_mock/_board.ts`
- Modify: `../kingwangjjang-fe/src/sections/board/view/board-view.tsx`

- [ ] **Step 1: Add board REST types and client**

Create `../kingwangjjang-fe/src/api/board-api.ts`:

```typescript
import { apiFetch } from './http';

export type BoardPost = {
  _id?: string | null;
  category: string;
  no: number;
  site: string;
  title: string;
  url: string;
  contents?: string | unknown[] | null;
  gpt_answer?: string | null;
  create_time: string;
  thumbnail?: string | null;
  comment_count?: number | null;
  likeCount?: number | null;
};

export function getRealtimeBoards(index: number, limit = 30) {
  return apiFetch<BoardPost[]>(`/boardservice/api/boards/realtime?index=${index}&limit=${limit}`);
}

export function getDailyBoards(index: number, limit = 30) {
  return apiFetch<BoardPost[]>(`/boardservice/api/boards/daily?index=${index}&limit=${limit}`);
}

export function addBoardLike(boardId: string) {
  return apiFetch<{ boardId: string; site: string; likeCount: number }>(
    `/boardservice/api/boards/${boardId}/likes`,
    { method: 'POST' }
  );
}
```

- [ ] **Step 2: Refactor infinite scroll hook**

Replace `../kingwangjjang-fe/src/hooks/use-infinite-scrollable-post-list.ts` with:

```typescript
import type { BoardPost } from 'src/api/board-api';

import { useRef, useState, useEffect, useCallback } from 'react';

import { getRealtimeBoards } from 'src/api/board-api';

const useInfiniteScrollablePostList = () => {
  const [pageIndex, setPageIndex] = useState(0);
  const [data, setData] = useState<{ realtimePagination: BoardPost[] }>({ realtimePagination: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const loadingRef = useRef(null);

  const loadPage = useCallback(async (index: number) => {
    setLoading(true);
    try {
      const items = await getRealtimeBoards(index);
      setData((prev) => ({
        realtimePagination:
          index === 0 ? items : [...(prev.realtimePagination || []), ...items],
      }));
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPage(pageIndex);
  }, [loadPage, pageIndex]);

  useEffect(() => {
    let observerRefValue: any = null;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !loading && !error) {
          setPageIndex((prev) => prev + 1);
        }
      },
      { threshold: 1 }
    );

    if (loadingRef.current) {
      observer.observe(loadingRef.current);
      observerRefValue = loadingRef.current;
    }

    return () => {
      if (observerRefValue) {
        observer.unobserve(observerRefValue);
      }
    };
  }, [error, loading]);

  return { loadingRef, data, loading, error };
};

export default useInfiniteScrollablePostList;
```

- [ ] **Step 3: Update board hook types**

In `../kingwangjjang-fe/src/hooks/use-board.ts`, remove GraphQL generated imports and use `BoardPost[]`:

```typescript
import type { BoardPost } from 'src/api/board-api';
```

Change state initialization:

```typescript
const [postData, setPostData] = useState<BoardPost[]>(POSTITEMS as BoardPost[]);
```

- [ ] **Step 4: Update board view type imports**

In `../kingwangjjang-fe/src/sections/board/view/board-view.tsx`, replace generated GraphQL type imports with:

```typescript
import type { BoardPost } from 'src/api/board-api';
```

Where the component expects `RealtimePaginationQuery['realtimePagination'][number]`, use `BoardPost`.

- [ ] **Step 5: Run frontend typecheck**

Run:

```powershell
cd ..\kingwangjjang-fe
npm run ts
```

Expected: if comment hook still imports missing GraphQL like types, the remaining failures must be confined to `src/hooks/use-comments.ts`.

- [ ] **Step 6: Commit frontend board REST migration**

Run:

```powershell
git add src/api/board-api.ts src/hooks/use-infinite-scrollable-post-list.ts src/hooks/use-board.ts src/_mock/_board.ts src/sections/board/view/board-view.tsx
git commit -m "feat: migrate board feed to rest"
```

---

### Task 8: Frontend Comment REST Migration

**Files:**
- Create: `../kingwangjjang-fe/src/api/comment-api.ts`
- Modify: `../kingwangjjang-fe/src/hooks/use-comments.ts`
- Modify: `../kingwangjjang-fe/src/types/comment.ts`

- [ ] **Step 1: Add comment REST client**

Create `../kingwangjjang-fe/src/api/comment-api.ts`:

```typescript
import type { Comment } from 'src/types/comment';

import { apiFetch } from './http';

export type CommentListResponse = {
  boardId: string;
  totalCount: number;
  comments: Comment[];
};

export type CreateCommentPayload = {
  boardId: string;
  parentId?: string | null;
  content: string;
};

export function getComments(boardId: string, page = 1, limit = 100) {
  return apiFetch<CommentListResponse>(
    `/commentservice/api/comments?boardId=${boardId}&page=${page}&limit=${limit}`
  );
}

export function createComment(payload: CreateCommentPayload) {
  return apiFetch<Comment>('/commentservice/api/comments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function likeComment(commentId: string) {
  return apiFetch<{ Id: string; likeCount: number; isLiked: boolean }>(
    `/commentservice/api/comments/${commentId}/like`,
    { method: 'POST' }
  );
}
```

- [ ] **Step 2: Replace comment hook**

Replace `../kingwangjjang-fe/src/hooks/use-comments.ts` with:

```typescript
import type { Comment } from 'src/types/comment';

import { useMemo, useState, useEffect, useCallback } from 'react';

import {
  getComments,
  likeComment as likeCommentRequest,
  createComment as createCommentRequest,
} from 'src/api/comment-api';
import { useAuthStore } from 'src/store/auth-store';

type UseCommentsParams = {
  boardId: string;
  site: string;
  enabled?: boolean;
};

export const useComments = ({ boardId, enabled = true }: UseCommentsParams) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [creatingComment, setCreatingComment] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { user } = useAuthStore();

  const refetch = useCallback(async () => {
    if (!enabled || !boardId) return;

    setLoading(true);
    try {
      const data = await getComments(`${boardId}`, 1, 100);
      setComments(data.comments);
      setTotalCount(data.totalCount);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [boardId, enabled]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const addComment = useCallback(
    async (content: string) => {
      if (!user) throw new Error('User not authenticated');

      setCreatingComment(true);
      try {
        const created = await createCommentRequest({ boardId: `${boardId}`, content });
        setComments((prev) => [created, ...prev]);
        setTotalCount((prev) => prev + 1);
        return created.Id;
      } finally {
        setCreatingComment(false);
      }
    },
    [boardId, user]
  );

  const addReply = useCallback(
    async (parentId: string, content: string) => {
      if (!user) throw new Error('User not authenticated');

      const created = await createCommentRequest({ boardId: `${boardId}`, parentId, content });
      await refetch();
      return created.Id;
    },
    [boardId, user, refetch]
  );

  const likeComment = useCallback(async (commentId: string) => {
    const result = await likeCommentRequest(commentId);
    setComments((prev) =>
      prev.map((comment) =>
        comment.Id === commentId
          ? { ...comment, likeCount: result.likeCount, isLiked: result.isLiked }
          : comment
      )
    );
  }, []);

  const memoizedTotalCount = useMemo(() => totalCount, [totalCount]);

  return {
    comments,
    totalCount: memoizedTotalCount,
    loading,
    error,
    refetch,
    creatingComment,
    addComment,
    addReply,
    likeComment,
  };
};
```

- [ ] **Step 3: Ensure comment response type includes `isLiked`**

In `../kingwangjjang-fe/src/types/comment.ts`, ensure `CreateCommentResponse` contains:

```typescript
isLiked: boolean;
```

- [ ] **Step 4: Run frontend typecheck**

Run:

```powershell
cd ..\kingwangjjang-fe
npm run ts
```

Expected: no `src/hooks/use-comments.ts` missing GraphQL type errors remain.

- [ ] **Step 5: Commit frontend comment REST migration**

Run:

```powershell
git add src/api/comment-api.ts src/hooks/use-comments.ts src/types/comment.ts
git commit -m "feat: migrate comments to rest"
```

---

### Task 9: End-to-End Local Verification

**Files:**
- No production file changes expected.

- [ ] **Step 1: Install backend dependencies**

Run in each changed service:

```powershell
cd user-service
poetry install
cd ..\board-service
poetry install
cd ..\comment-service
poetry install
```

Expected: dependencies install successfully.

- [ ] **Step 2: Start PostgreSQL**

Run from `kingwangjjang-be`:

```powershell
docker compose up -d kingwangjjang-postgres
```

Expected: PostgreSQL container starts and healthcheck becomes healthy.

- [ ] **Step 3: Seed development data**

Run:

```powershell
cd user-service
poetry run python -c "from app.db.seed import seed_users; seed_users()"
cd ..\board-service
poetry run python -c "from app.db.seed import seed_boards; seed_boards()"
cd ..\comment-service
poetry run python -c "from app.db.seed import seed_comments; seed_comments()"
```

Expected: commands exit with code `0`.

- [ ] **Step 4: Run backend tests**

Run from `kingwangjjang-be`:

```powershell
python -m pytest tests -q
cd user-service
python -m pytest tests -q
cd ..\board-service
python -m pytest tests -q
cd ..\comment-service
python -m pytest tests -q
```

Expected: all tests pass.

- [ ] **Step 5: Start backend source services**

Run from `kingwangjjang-be`:

```powershell
powershell -ExecutionPolicy Bypass -File .\dev.ps1 up
```

Expected: gateway on `8000`, board on `33333`, user on `33334`, and comment on `33335`.

- [ ] **Step 6: Probe REST endpoints through gateway**

Run:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/userservice/api/users/me
Invoke-WebRequest -UseBasicParsing http://localhost:8000/boardservice/api/boards/realtime
Invoke-WebRequest -UseBasicParsing "http://localhost:8000/commentservice/api/comments?boardId=11111111-1111-1111-1111-111111111111&page=1&limit=100"
```

Expected: all return HTTP `200`. `/users/me` may return `null` without auth.

- [ ] **Step 7: Run frontend verification**

Run from `kingwangjjang-fe`:

```powershell
npm run lint
npm run ts
```

Expected: lint has no errors. TypeScript has no GraphQL-generated missing-type errors from migrated hooks.

- [ ] **Step 8: Manual browser check**

Run frontend if it is not already running:

```powershell
npm run dev
```

Open:

```text
http://localhost:8083/board/
```

Expected: board list renders from REST seed data, comments load for seed board records, and unauthenticated like/comment actions still require auth.

- [ ] **Step 9: Review verification status**

Run from `kingwangjjang-be`:

```powershell
git status --short
```

Run from `../kingwangjjang-fe`:

```powershell
git status --short
```

Expected: no new source changes were produced by verification. If a source file changed during verification, return to the task that owns that file, rerun that task's tests, and use that task's commit step.

---

## Self-Review Checklist

- Spec coverage: infrastructure, auth boundary, DB model, REST API contract, frontend transition, seed data, and verification are covered.
- Placeholder scan: no incomplete implementation slots and no cleanup step removes GraphQL prematurely.
- Type consistency: backend response keys match frontend REST clients: `Id`, `boardId`, `userId`, `likeCount`, `isLiked`, `create_time`, `createdAt`.
- Scope control: production MongoDB data migration, final GraphQL removal, and auth redesign remain outside this plan.
