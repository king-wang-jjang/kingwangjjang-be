# Board Service

게시글, 크롤링 지표, 실시간·일간 랭킹, Top 10 이력, 좋아요와 게시글 AI 분석 결과를 소유하는 FastAPI 서비스입니다. 내부 포트는 `33333`입니다.

## 조회 API

아래 내부 경로 앞에 Gateway 공개 접두사 `/boardservice`를 붙여 호출합니다.

| 메서드·내부 경로 | 설명 |
| --- | --- |
| `GET /api/boards/realtime` | 실시간 목록 |
| `GET /api/boards/daily` | 현재 일간 랭킹 |
| `GET /api/boards/filters` | 최근 24시간 크롤링 성공 사이트 필터 |
| `GET /api/boards/daily/history/dates` | 저장된 Top 10 날짜 목록 |
| `GET /api/boards/daily/history?date=YYYY-MM-DD` | 특정 날짜 Top 10 |
| `GET /api/boards/{board_id}/ai` | 저장된 분석 상태·결과 |

실시간·일간 목록은 `index`, `limit`, 반복 가능한 `sites`, `category`, `tag`, `q`, `has_thumbnail` 필터를 지원합니다. history 날짜 목록의 `limit`은 1~365, history 결과의 `limit`은 1~100입니다.

사이트 필터에는 최근 24시간 안에 게시글 저장 또는 원문 지표 갱신이 한 건 이상 성공한 사이트만 표시됩니다. 성공 여부는 `board_metric_snapshots`의 `crawl_status=success`와 `captured_at`을 기준으로 판단합니다.

## 인증 API

| 메서드·내부 경로 | 권한 | 설명 |
| --- | --- | --- |
| `POST /api/boards/{board_id}/likes` | 로그인 | 게시글 좋아요 추가 |
| `POST /api/boards/{board_id}/ai` | 로그인 | 수동 분석 job 시작, 미완료 작업은 202 |
| `GET /api/boards/ai/jobs/{job_id}` | 로그인 | 프로세스 메모리의 수동 분석 job 조회 |
| `POST /api/boards/{board_id}/images/{image_index}/vision-text` | 로그인 | 게시글 이미지 텍스트 추출 |
| `GET /api/boards/daily/shorts-package[?date=...]` | 관리자 | live 또는 과거 Top 10 제작용 JSON |

인증·관리자 권한은 Gateway가 설정한 신뢰 헤더를 사용합니다. 외부에서 서비스 포트로 직접 호출하지 마세요.

## 자동 AI 분석

서비스 기동 시 기본 1개의 worker가 `pending` 게시글을 가져와 GPT 서비스에 분석을 요청하고 요약·태그·참여도 점수/이유를 저장합니다. 기본 AI 노드의 동시 추론 한도와 충돌하지 않도록 보수적인 값이 사용됩니다.

- `ANALYSIS_WORKER_CONCURRENCY`: 1~16, 기본 1
- `DISABLE_ANALYSIS_WORKER=TRUE`: worker 비활성화
- `AI_SERVICE_URL`: GPT 서비스 주소
- `AI_SERVICE_TOKEN`: GPT 추론용 내부 토큰
- `AI_ANALYSIS_MAX_INPUT_CHARS`: 모델과 무관한 분석 입력 상한, 기본 16,000자
- `AI_ANALYSIS_MIN_BODY_CHARS`: 제목을 제외한 최소 본문 길이, 기본 20자
- `AI_ANALYSIS_MIN_LANGUAGE_CHARS`: 숫자만 있는 행을 거르는 최소 문자 신호, 기본 4자
- `AI_ANALYSIS_VISION_FALLBACK_ENABLED`: 짧은 이미지 게시글의 vision 보강, 기본 `TRUE`
- `AI_ANALYSIS_VISION_MAX_IMAGES`: 한 게시글에서 보강할 로컬 이미지 수, 기본 2장(최대 4장)
- `AI_ANALYSIS_VISION_MAX_IMAGE_BYTES`: 자동 보강 이미지 크기 상한, 기본 10MB
- `AI_ANALYSIS_VISION_MAX_PIXELS`: 애니메이션 frame을 포함한 총 픽셀 상한, 기본 4천만
- `AI_ANALYSIS_VISION_PROMPT`: 장면·맥락·이미지 내 텍스트를 요청하는 자동 보강 prompt
- `AI_ANALYSIS_RETRYABLE_BACKOFF_SECONDS`: vision 인프라 오류 재시도 간격, 기본 300초

분석 입력은 제목과 각 텍스트·이미지 텍스트 블록의 순서를 유지한 채 상한 안에서
공평하게 축약됩니다. 제목만 있거나 본문이 기준보다 짧은 게시글은 그대로 요약하지
않습니다. 로컬 `CRAWLER_MEDIA_ROOT` 아래 이미지가 있으면 경로 이탈을 차단하고 이미지
수·파일 크기를 제한한 뒤 GPT 서비스의 `vision` capability로 먼저 보강합니다. 원격
`source_url`은 자동으로 가져오지 않습니다. 이미지 형식·디코딩 가능 여부·총
픽셀 수도 확인해 손상 파일과 압축 폭탄을 vision 노드로 보내지 않습니다. 사용할 수
있는 vision 노드가 없거나
보강 후에도 최소 본문 길이에 못 미치면 분석은 실패 처리되어 제목만으로 결과를
만들지 않습니다. vision 노드의 timeout·503처럼 일시적인 인프라 오류는 본문
부족과 구분해 다음 재시도 시각을 예약하며, 손상 파일이나 실제 내용 부족만 콘텐츠
오류로 남깁니다. 인증·payload 설정 문제를 뜻하는 비재시도 4xx는 무한 예약하지
않고 일반 retry budget을 소진한 뒤 `failed`로 표시합니다.

소스 실행에서 상대 `CRAWLER_MEDIA_ROOT`는 현재 서비스 작업 디렉터리가 아니라
`kingwangjjang-be/`와 `CrawlScheduler/`를 포함하는 워크스페이스를 기준으로
해석합니다. Compose에서는 절대 경로 `/app/public`과 read-only volume을 사용합니다.

수동 분석 job 상태는 프로세스 메모리에 있으므로 재시작 시 사라지지만, 완료된 게시글 분석 결과는 PostgreSQL에 남습니다.

## 실행과 테스트

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 33333
poetry run pytest -q
```

주요 환경변수는 `DATABASE_URL`, `AI_SERVICE_URL`, `AI_SERVICE_TOKEN`, `ADMIN_USER_IDS`, `CRAWLER_MEDIA_ROOT`와 위 worker 변수입니다. 서비스 경계는 [Board Service 에이전트 가이드](../docs/agents/board-service.md)를 참고하세요.
