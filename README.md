# Kingwangjjang Backend

킹왕짱의 API Gateway와 도메인별 FastAPI 서비스를 모아 둔 백엔드 저장소입니다. 현재 사용자 인증, 게시글·Top 10, 댓글, AI 분석 기능을 제공하며 알림 서비스는 아직 스캐폴드 단계입니다.

## 서비스 구성

| 서비스 | 역할 | 로컬 소스 포트 | 공개 Gateway 경로 |
| --- | --- | ---: | --- |
| `api-gateway` | CORS, JWT 검증, 권한 계산, 요청 프록시, 크롤러 미디어 제공 | 33330 | `/` |
| `user-service` | Kakao OAuth, 세션 갱신, 사용자 프로필 | 33334 | `/login`, `/callback`, `/userservice/*` |
| `board-service` | 실시간·일간 게시글, Top 10 이력, AI 분석, 좋아요, Shorts 패키지 | 33333 | `/boardservice/*` |
| `comment-service` | 댓글·답글 CRUD와 좋아요 | 33335 | `/commentservice/*` |
| `gpt-service` | AI 노드 레지스트리, 분석·채팅·이미지 텍스트 추출 | 33336 | `/gptservice/*` |
| `notification-service` | 향후 알림 기능을 위한 스캐폴드 | 8000 | 미연결 |

Docker Compose에서는 Gateway만 호스트의 `8000` 포트로 노출됩니다. 서비스 내부 포트는 위 표와 같으며 PostgreSQL 호스트 포트는 기본 `POSTGRES_PORT` 값입니다.

## 빠른 시작

### 로컬 소스 실행

Python과 Poetry, 접근 가능한 PostgreSQL이 필요합니다.

```powershell
Copy-Item .env.example .env
.\dev.ps1 seed
.\dev.ps1 up
.\dev.ps1 ps
```

Linux/macOS에서는 같은 명령을 `./dev.sh`로 실행합니다. 로컬 Gateway 주소는 `http://localhost:33330`입니다.

### Docker Compose 실행

`.env`의 `DOCKERHUB_USERNAME`과 데이터베이스·인증 값을 채운 뒤 실행합니다. Compose에는 `SERVER_RUN_MODE=TRUE`가 필요하며, HTTPS 운영에서는 `AUTH_COOKIE_SECURE=TRUE`로 바꿉니다. 실행 스크립트가 외부 Docker 네트워크 `kingwangjjang-network`를 없으면 생성합니다.

```powershell
Copy-Item .env.example .env
.\run.ps1 up
.\run.ps1 ps
```

Linux/macOS에서는 `./run.sh`를 사용합니다. 컨테이너 Gateway 주소는 `http://localhost:8000`입니다.

> `run.ps1 clean`과 `run.sh clean`은 PostgreSQL 볼륨까지 제거합니다. 개발 데이터를 지워도 될 때만 사용하세요.

### 로컬 vLLM 요약 서비스

호스트의 OpenAI-compatible vLLM이 `8000` 포트에서 실행 중이면, PostgreSQL이나
전체 MSA를 시작하지 않고 요약용 GPT 서비스만 `33336` 포트에 실행할 수 있습니다.

```powershell
docker compose -f docker-compose.vllm.yml up -d
docker compose -f docker-compose.summary.yml up -d --build
Invoke-RestMethod http://127.0.0.1:8000/v1/models
Invoke-RestMethod http://127.0.0.1:33336/health
```

기본 API 모델은 `Qwen/Qwen3.8-27B`이며 `analysis`와 `chat` capability로 등록됩니다.
RTX 50 시리즈 24GB 환경에서는 `RadixArk/Qwen3.8-27B-NVFP4` 체크포인트를
vLLM의 `modelopt` 양자화 모드와 `--language-model-only` 옵션으로 실행합니다.
현재 8K 컨텍스트에 맞춰 분석 입력은 12,000자로 제한되고 출력은 512토큰으로
제한됩니다. 초과 입력은 앞·중간·끝 문맥을 보존하는 기존 절단 로직을 사용합니다.
설정과 노드 레지스트리는 `kingwangjjang-summary_gpt-summary-data` 볼륨에 유지됩니다.
새 게시글은 DB에 `pending` 상태로 등록되고 board-service worker가 비동기로 요약합니다.
완료된 요약·태그·반응 점수는 `boards` 테이블에 저장되어 이후 요청은 DB 값을 재사용합니다.
종료할 때는 `docker compose -f docker-compose.summary.yml down`과
`docker compose -f docker-compose.vllm.yml down`을 사용하세요.

## 주요 공개 API

- 인증: `GET /login`, `GET /callback`, `POST /userservice/api/auth/refresh`
- 사용자: `GET|PATCH /userservice/api/users/me`
- 게시글: `GET /boardservice/api/boards/realtime`, `GET /boardservice/api/boards/daily`
- Top 10: `GET /boardservice/api/boards/daily/history`, `GET /boardservice/api/boards/daily/history/dates`
- 댓글: `/commentservice/api/comments`
- AI 노드·추론: `/gptservice/api/ai/*`

전체 계약은 각 서비스의 `/docs`와 [서비스 문서](./docs/INDEX.md)를 함께 참고하세요. 브라우저·프런트엔드 요청은 서비스 포트에 직접 보내지 말고 Gateway를 통과해야 신뢰할 수 있는 사용자 헤더와 관리자 권한이 전달됩니다.

## 테스트

```powershell
python -m pytest tests -q
.\board-service\.venv\Scripts\python.exe -m pytest board-service\tests -q
.\comment-service\.venv\Scripts\python.exe -m pytest comment-service\tests -q
.\gpt-service\.venv\Scripts\python.exe -m pytest gpt-service\tests -q
.\user-service\.venv\Scripts\python.exe -m unittest discover -s user-service\tests -q
```

가상환경이 없다면 각 서비스 디렉터리에서 먼저 `poetry install`을 실행하세요.

## 문서

- [문서 인덱스](./docs/INDEX.md)
- [아키텍처](./docs/ARCHITECTURE.md)
- [실행·운영 가이드](./docs/RUNBOOK.md)
- [에이전트용 MSA 경계](./docs/agents/README.md)
