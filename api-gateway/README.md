# API Gateway

백엔드의 단일 공개 진입점입니다. CORS 처리, access token 검증, 관리자 역할 계산, 신뢰할 수 있는 사용자 헤더 전달, 서비스 프록시와 크롤러 미디어 제공을 담당합니다. DB와 도메인 비즈니스 로직은 소유하지 않습니다.

## 라우팅

| 공개 경로 | 대상 |
| --- | --- |
| `/boardservice/*` | `board-service` |
| `/userservice/*` | `user-service` |
| `/commentservice/*` | `comment-service` |
| `/gptservice/*` | `gpt-service` |
| `/login`, `/callback` | `user-service` |
| `/static/media/*` | `CRAWLER_MEDIA_ROOT`의 파일 |

서비스 접두사는 내부 요청에서 제거됩니다. 예를 들어 `/boardservice/api/boards/daily`는 board 서비스의 `/api/boards/daily`로 전달됩니다.

Gateway는 클라이언트가 보낸 `X-User-Id`, `X-Auth-Provider`, `X-User-Role`, `X-Auth-Status`, `X-Auth-Error`를 제거하고 검증 결과로 다시 설정합니다. downstream의 status, body, redirect와 여러 `Set-Cookie` 헤더를 보존하며 프록시 timeout은 90초입니다.

## 실행

저장소 루트에서 `dev.ps1 up` 또는 `dev.sh up`을 쓰는 것을 권장합니다. 개별 실행은 다음과 같습니다.

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 33330
```

로컬 모드는 `SERVER_RUN_MODE=FALSE`가 필요합니다. 컨테이너 진입점은 `prod.sh`이며 포트 `8000`을 사용합니다.

주요 환경변수는 `SERVER_RUN_MODE`, `CORS_ORIGINS`, `JWT_SECRET_KEY`, `ADMIN_USER_IDS`, `CRAWLER_MEDIA_ROOT`입니다.

## 검증

```bash
python -m pytest ../tests -q
poetry run python -m compileall app -q
```

서비스 경계와 보안 규칙은 [Gateway 에이전트 가이드](../docs/agents/api-gateway.md)를 참고하세요.
