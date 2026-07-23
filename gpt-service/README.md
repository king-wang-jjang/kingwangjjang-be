# GPT Service

여러 Ollama 및 OpenAI-compatible(vLLM 포함) 서버를 AI 노드로 등록하고,
capability·상태·priority·weight·동시성 한도를 기준으로 요청을 라우팅하는 서비스입니다.

내부 포트는 `33336`입니다. 외부에서는 API Gateway의 `/gptservice` 접두사를
사용하므로 내부 `/api/ai/nodes`는 `/gptservice/api/ai/nodes`로 호출합니다.

## 실행

```bash
poetry install --with dev
poetry run uvicorn app.main:app --reload --port 33336
```

`DATABASE_URL`은 필수입니다. 컨테이너는 `prod.sh`를 통해 기본 포트 `33336`에서
실행되며 `PORT`로 변경할 수 있습니다.

## 인증

- 노드 조회·등록·수정·삭제·health check 전체는
  `X-AI-Admin-Token: <AI_NODE_ADMIN_TOKEN>`을 요구합니다.
- `AI_NODE_ADMIN_TOKEN`이 없을 때는 `SERVER_RUN_MODE`가 `FALSE`인 로컬 모드에서만
  관리 API를 허용합니다. 서버 모드에서는 설정 누락도 거부합니다.
- 추론 API는 `AI_SERVICE_TOKEN`을 설정한 경우
  `X-AI-Service-Token` 헤더를 요구합니다. 토큰이 없을 때는 명시적 로컬 모드
  (`SERVER_RUN_MODE=FALSE`)에서만 허용하며, 서버 모드나 모드 미설정 상태에서는
  설정 오류로 거부합니다.
- 실제 upstream API key는 DB에 저장하지 않습니다. 노드의 `api_key_env`에는
  환경변수 이름만 저장하며 요청 직전에 그 값을 읽습니다.
- 비밀 유출을 막기 위해 `api_key_env`는 `AI_NODE_API_KEY_*`, `VLLM_API_KEY`,
  `OPENAI_API_KEY`, `CHATGPT_API_KEY`만 기본 허용합니다. 다른 AI key 이름은
  `AI_NODE_API_KEY_ENV_ALLOWLIST`에 쉼표로 명시해야 합니다.

## API

- `GET /health`
- `GET|POST /api/ai/nodes`
- `GET|PATCH|DELETE /api/ai/nodes/{id}`
- `POST /api/ai/nodes/{id}/health-check`
- `POST /api/ai/nodes/health-check` — 전체 노드 검사
- `POST /api/ai/analyze` — `{ "content": "..." }`
- `POST /api/ai/chat` — `{ "messages": [...], "capability": "chat", "response_format": null }`
- `POST /api/ai/vision-text` — `{ "image_data_url": "data:image/...;base64,...", "prompt": "..." }`

`/health`는 `{ "status": "ok", "node_count": N }`을 반환하며 Gateway에서는
`/gptservice/health`로 접근합니다.

노드 등록 예시:

```json
{
  "name": "ollama-a",
  "provider": "ollama",
  "base_url": "http://ollama-a:11434",
  "enabled": true,
  "priority": 10,
  "weight": 2,
  "max_concurrency": 4,
  "timeout_seconds": 60,
  "api_key_env": null,
  "models": [
    {
      "name": "gemma4:e4b",
      "capabilities": ["analysis", "chat"],
      "enabled": true,
      "is_default": true
    }
  ]
}
```

## 기존 환경변수 bootstrap

`ai_nodes` 테이블이 비어 있을 때 한 번만 다음 변수를 읽어 노드를 생성합니다.

- `OLLAMA_BASE_URLS` 또는 `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`
- `VLLM_BASE_URL`, `VLLM_MODEL`, `VLLM_API_KEY`, `VLLM_TIMEOUT_SECONDS`

Ollama URL이 하나도 없으면 기존 기본값
`http://100.104.51.52:11434` / `gemma4:e4b`를 등록합니다. 이후 환경변수가
바뀌어도 관리자가 수정한 DB 노드를 덮어쓰지 않습니다.

실패가 `AI_NODE_FAILURE_THRESHOLD`(기본 2)에 도달하면 노드를 unhealthy로
표시합니다. `AI_NODE_RETRY_COOLDOWN_SECONDS`(기본 30초) 뒤에는 자동 복구 probe에
다시 포함됩니다. 전체 요청 deadline은 `AI_REQUEST_DEADLINE_SECONDS`(기본 55초)이며,
후보별 timeout을 남은 후보 수에 맞춰 나눠 첫 노드 지연 뒤에도 failover 시간을
확보합니다.

PostgreSQL 시작 지연은 `AI_DATABASE_STARTUP_ATTEMPTS`(기본 10)와
`AI_DATABASE_STARTUP_DELAY_SECONDS`(기본 2초) 동안 재시도합니다. 현재
`max_concurrency`와 weight cursor는 단일 서비스 프로세스 기준이므로 운영 진입점은
기본 1 worker를 사용합니다. 여러 worker/replica로 확장할 때는 공유 semaphore와
분산 선택 상태가 추가로 필요합니다.

요청 자원 한도는 분석/채팅 텍스트 20만 자, 채팅 메시지 64개, inline 이미지 data
URL 합계 약 20MB, vision prompt 4천 자입니다. degraded 또는 cooldown이 끝난
unhealthy 노드의 half-open 복구 probe는 프로세스 안에서 동시에 하나만 허용합니다.

환경변수·운영 예시는 [실행·운영 가이드](../docs/RUNBOOK.md), 서비스 소유권과
금지 경계는 [GPT Service 에이전트 가이드](../docs/agents/gpt-service.md)를 참고하세요.

## 테스트

```bash
poetry run pytest -q
```
