# 백엔드 실행·운영 가이드

이 문서는 2026-07-23 현재 로컬 소스 실행, Docker Compose 실행, 주요 환경변수와 점검 절차를 설명합니다.

## 사전 요구사항

- 로컬 소스 실행: Python, Poetry, PostgreSQL
- 컨테이너 실행: Docker와 Docker Compose v2
- 루트 `.env`: `.env.example`을 복사해 생성

서비스별 Poetry 환경은 서로 독립적입니다. 로컬 소스 실행 전 각 활성 서비스 디렉터리에서 의존성을 설치합니다.

```powershell
poetry install
```

## 필수 환경변수

`.env.example`에 전체 목록과 로컬 기본값이 있습니다. 운영 환경에서는 적어도 다음 값을 명시적으로 설정하세요.

| 영역 | 변수 | 설명 |
| --- | --- | --- |
| 이미지 | `DOCKERHUB_USERNAME` | Compose가 가져올 서비스 이미지 소유자 |
| PostgreSQL | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Compose PostgreSQL 초기화 값 |
| DB 연결 | `DATABASE_URL`, `DOCKER_DATABASE_URL` | 각각 호스트/컨테이너 내부 연결 문자열 |
| JWT | `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY` | access/refresh 서명 키 |
| OAuth | `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`, `REDIRECT_URI`, `WEBSITE_URL` | Kakao 로그인과 완료 redirect |
| 쿠키 | `AUTH_COOKIE_SECURE` | HTTPS 운영은 `TRUE`, HTTP 로컬은 `FALSE` |
| 관리자 | `ADMIN_USER_IDS` | 쉼표로 구분한 OAuth user ID, 비어 있으면 전부 거부 |
| 내부 AI | `AI_SERVICE_TOKEN`, `AI_NODE_ADMIN_TOKEN` | 운영에서 추론/관리 API를 보호하는 별도 토큰 |
| 미디어 | `CRAWLER_MEDIA_ROOT`, `CRAWLER_MEDIA_HOST_ROOT` | 소스 실행 경로/Compose 호스트 mount 경로 |

`SERVER_RUN_MODE=FALSE`는 로컬 소스 모드이며 `dev.ps1`/`dev.sh`가 프로세스에 자동 설정합니다. Compose는 `SERVER_RUN_MODE=TRUE`여야 내부 컨테이너 이름으로 라우팅합니다. `.env.example`은 Compose 기준으로 `TRUE`이며, 로컬 HTTP를 위해 `AUTH_COOKIE_SECURE=FALSE`를 사용합니다. HTTPS 운영에서는 이를 반드시 `TRUE`로 바꾸세요. 비밀값은 저장소에 커밋하지 않습니다.

## 로컬 소스 실행

루트 개발 스크립트는 `gpt-service`, Gateway, board/user/comment 서비스를 백그라운드 프로세스로 실행합니다. 포트는 각각 `33336`, `33330`, `33333`, `33334`, `33335`입니다.

```powershell
Copy-Item .env.example .env
.\dev.ps1 seed
.\dev.ps1 up
.\dev.ps1 ps
.\dev.ps1 logs
.\dev.ps1 down
```

Linux/macOS에서는 `./dev.sh <command>`를 사용합니다. `seed`는 user/board/comment 테이블을 만들고 결정적인 개발용 데이터를 넣습니다. 기존 데이터를 모두 초기화하는 명령은 아니므로 각 seed 모듈의 동작을 변경하기 전에 확인하세요.

DB 선택은 `DEV_DATABASE_TARGET`으로 제어합니다.

- `local`: `DATABASE_URL`의 로컬 DB 사용
- `server`: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`로 지정한 서버 DB 필수 사용
- `auto`: 서버 DB에 접속할 수 있으면 사용하고 아니면 로컬 DB로 fallback

## Docker Compose 실행

Compose는 PostgreSQL과 Gateway, board/user/comment/GPT 서비스를 실행합니다. 알림 서비스는 포함하지 않습니다. 루트 스크립트는 `kingwangjjang-network` 외부 네트워크를 자동 생성합니다.

```powershell
.\run.ps1 pull
.\run.ps1 up
.\run.ps1 ps
.\run.ps1 logs
.\run.ps1 down
```

Linux/macOS에서는 `./run.sh <command>`를 사용합니다. Gateway는 `http://localhost:8000`, PostgreSQL은 `${POSTGRES_PORT:-5432}`로 노출됩니다. 나머지 서비스는 Docker 네트워크 안에서만 접근합니다.

`run.ps1 clean`/`run.sh clean`은 `docker compose down -v --remove-orphans`를 실행하여 PostgreSQL named volume도 삭제합니다. 복구할 백업이 있거나 데이터를 버려도 되는 경우에만 사용하세요.

## 기동 점검

```powershell
# 로컬 소스 실행
Invoke-RestMethod http://localhost:33336/health
Invoke-RestMethod http://localhost:33330/boardservice/api/boards/realtime?limit=1

# Docker Compose
Invoke-RestMethod http://localhost:8000/gptservice/health
Invoke-RestMethod http://localhost:8000/boardservice/api/boards/realtime?limit=1
```

GPT health 응답은 `status`와 등록된 `node_count`를 반환합니다. 서비스별 OpenAPI는 로컬 포트의 `/docs`에서 확인할 수 있습니다. Docker Compose는 내부 서비스 포트를 호스트에 공개하지 않으므로 외부에서는 Gateway 경로를 사용합니다.

## 인증과 관리자 설정

Kakao 개발자 콘솔의 redirect URI는 Gateway의 `/callback`과 일치해야 합니다. 로컬 소스 실행은 보통 `http://localhost:33330/callback`, 로컬 Compose는 `http://localhost:8000/callback`, 운영은 공개 HTTPS origin을 사용합니다.

로그인 후 `GET /userservice/api/users/me`의 `userId`를 `ADMIN_USER_IDS`에 등록하고 Gateway와 `board-service`를 재시작합니다. 관리자 전용 `GET /boardservice/api/boards/daily/shorts-package`는 오늘의 live Top 10을, `?date=YYYY-MM-DD`는 저장된 이력을 JSON 제작 패키지로 반환합니다.

세션 쿠키 정책은 다음과 같습니다.

- HttpOnly, `SameSite=Lax`, path `/`
- access token 1시간, refresh token 400일
- `AUTH_COOKIE_SECURE=TRUE`면 HTTPS에서만 전송
- `POST /userservice/api/auth/refresh`가 두 토큰을 회전하고 세션 만료를 다시 400일로 연장
- 브라우저별 세션을 `user_sessions`에 SHA-256 해시로 저장하므로 다른 기기의 새 로그인이 기존 세션을 덮어쓰지 않음

refresh token 해시가 DB의 활성 세션과 다르거나 만료되면 `401 invalid_refresh_token`을 반환하며 쿠키는 변경하지 않습니다. 동시 요청에서는 조건부 갱신에 성공한 첫 요청만 토큰을 회전합니다. 이전 버전의 `users.refresh_token` 값은 첫 refresh 성공 시 원자적으로 `user_sessions`로 이관되고 제거됩니다. 유효한 세션이 없다면 다시 로그인해야 합니다.

이 버전을 처음 배포하기 전에는 DB를 백업하고 user-service 계정에 `CREATE TABLE`과 `CREATE INDEX` 권한이 있는지 확인하세요. 기동 후 `user_sessions`의 FK·unique 제약·인덱스가 생성됐는지 확인해야 합니다. legacy token이 한 번 이관되면 구버전 user-service는 새 해시 세션을 읽을 수 없으므로, 구버전으로 롤백한 사용자는 다시 로그인해야 할 수 있습니다.

## 게시글 자동 분석

`board-service`는 기본 1개 worker로 `pending` 게시글을 처리합니다. 기본 AI 노드의 동시 추론 한도가 1이므로, 처리량을 높일 때는 AI 노드의 `max_concurrency`도 함께 확인하세요.

| 변수 | 기본값 | 의미 |
| --- | ---: | --- |
| `ANALYSIS_WORKER_CONCURRENCY` | 1 | worker 수, 1~16으로 제한 |
| `ANALYSIS_WORKER_IDLE_INTERVAL_SECONDS` | 3 | 처리할 항목이 없을 때 대기 시간 |
| `ANALYSIS_WORKER_ACTIVE_INTERVAL_SECONDS` | 0.2 | 항목 처리 후 다음 polling까지 대기 |
| `DISABLE_ANALYSIS_WORKER` | `FALSE` | `TRUE`면 worker 비활성화 |
| `AI_ANALYSIS_MAX_INPUT_CHARS` | 16000 | board·GPT 서비스가 함께 적용하는 분석 입력 상한 |
| `AI_ANALYSIS_MIN_BODY_CHARS` | 20 | 제목·중복 블록을 제외한 최소 본문 문자 수 |
| `AI_ANALYSIS_MIN_LANGUAGE_CHARS` | 4 | 숫자·경로만 있는 본문을 거르는 최소 문자 신호 |
| `AI_ANALYSIS_VISION_FALLBACK_ENABLED` | `TRUE` | 짧은 이미지 게시글의 로컬 미디어 보강 |
| `AI_ANALYSIS_VISION_MAX_IMAGES` | 2 | 게시글당 vision 보강 이미지 수, 최대 4 |
| `AI_ANALYSIS_VISION_MAX_IMAGE_BYTES` | 10000000 | 자동 보강할 이미지 한 장의 최대 크기 |
| `AI_ANALYSIS_VISION_MAX_PIXELS` | 40000000 | animation frame을 포함한 총 픽셀 상한 |
| `AI_ANALYSIS_VISION_PROMPT` | `.env.example` 참고 | 장면·맥락·보이는 텍스트를 요청하는 prompt |
| `AI_ANALYSIS_RETRYABLE_BACKOFF_SECONDS` | 300 | vision 인프라 오류 재시도 간격 |

Board가 GPT를 호출하려면 두 서비스의 `AI_SERVICE_TOKEN` 값이 같아야 합니다. Compose에서는 `AI_SERVICE_URL`이 내부 GPT 서비스 주소로 자동 덮어써집니다.
`AI_ANALYSIS_MAX_INPUT_CHARS`는 등록된 분석 노드 중 가장 작은 context에 맞춰 두
서비스에 같은 값으로 설정하세요. 본문이 기준보다 짧으면 로컬
`CRAWLER_MEDIA_ROOT`의 이미지만 제한적으로 vision 보강하며, 원격 URL은 가져오지
않습니다. 보강 후에도 기준에 못 미치면 worker가 제목만으로 요약하지 않고 실패
상태를 기록합니다.

## AI 노드 관리

관리 API는 Gateway 경로로 호출할 수 있습니다.

```powershell
$headers = @{ 'X-AI-Admin-Token' = $env:AI_NODE_ADMIN_TOKEN }
Invoke-RestMethod -Headers $headers http://localhost:33330/gptservice/api/ai/nodes
Invoke-RestMethod -Method Post -Headers $headers http://localhost:33330/gptservice/api/ai/nodes/health-check
```

Compose에서는 포트를 `8000`으로 바꿉니다. 추론 호출은 별도의 `X-AI-Service-Token`을 사용합니다. 노드의 `api_key_env`에는 key 자체가 아니라 허용된 환경변수 이름만 저장합니다.

AI 노드 테이블이 비어 있을 때만 `OLLAMA_BASE_URLS`/`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `VLLM_BASE_URL`, `VLLM_MODEL` 등으로 bootstrap합니다. 이후에는 관리 API로 변경하세요.
특히 기존 노드가 있는 운영 DB에 `VLLM_BASE_URL`만 추가해도 vision 노드는 생기지
않습니다. 이미지 본문 보강을 켰다면 관리 API에 `vision` capability 모델을
명시적으로 등록하고 health check가 성공하는지 확인하세요.

## 테스트

```powershell
# 서비스 경계와 통합 wiring
python -m pytest tests -q

# 서비스별
.\board-service\.venv\Scripts\python.exe -m pytest board-service\tests -q
.\comment-service\.venv\Scripts\python.exe -m pytest comment-service\tests -q
.\gpt-service\.venv\Scripts\python.exe -m pytest gpt-service\tests -q
.\user-service\.venv\Scripts\python.exe -m unittest discover -s user-service\tests -q
```

루트 테스트 중 `test_root_dev_all_script.py`는 백엔드 저장소의 상위 워크스페이스에 통합 실행기 `dev-all.ps1`이 있는 구성을 검사합니다. 백엔드 저장소만 체크아웃했다면 해당 파일은 별도 워크스페이스 구성 없이는 실패합니다.

## 문제 해결

### `service ... is unhealthy` / `Connection refused`

- `DATABASE_URL`과 `DOCKER_DATABASE_URL`의 host가 실행 방식에 맞는지 확인합니다.
- `.\run.ps1 logs` 또는 `.\dev.ps1 logs`에서 먼저 실패한 서비스를 찾습니다.
- GPT는 PostgreSQL 준비를 기다려 재시도하지만 최종 실패하면 board 서비스도 healthy 의존성을 만족하지 못합니다.

### Gateway `404 Invalid path prefix`

공개 접두사가 `/boardservice`, `/userservice`, `/commentservice`, `/gptservice` 중 하나인지 확인합니다. `/login`과 `/callback`만 접두사 없이 허용됩니다.

### `401 authentication_required` / `403 administrator_required`

- 브라우저 요청에 쿠키가 포함되는지 확인합니다.
- 서비스 포트가 아니라 Gateway로 호출했는지 확인합니다.
- 관리자 API라면 로그인 사용자의 OAuth ID가 `ADMIN_USER_IDS`에 있는지 확인합니다.

### GPT `503` 또는 분석이 계속 `pending`

- `GET /gptservice/health`와 관리자 health check로 노드 상태를 확인합니다.
- `AI_SERVICE_TOKEN`이 board/GPT 양쪽에서 같은지 확인합니다.
- 등록 노드의 capability에 `analysis`가 있고 enabled 상태인지 확인합니다.
- `DISABLE_ANALYSIS_WORKER`와 worker 로그를 확인합니다.

### 미디어가 `404`

- 소스 실행은 `CRAWLER_MEDIA_ROOT`가 실제 디렉터리를 가리키는지 확인합니다.
- Compose는 `CRAWLER_MEDIA_HOST_ROOT`가 호스트에서 존재하며 컨테이너 `/app/public`에 mount되는지 확인합니다.
- Gateway는 미디어 루트가 기동 시 존재할 때만 `/static/media`를 mount하므로 설정 수정 후 재시작합니다.
