# 실행 가이드 (RUNBOOK)

이 문서는 프로젝트의 로컬 실행, 디버깅, 환경 변수 설정에 대한 절차를 설명합니다.

## 로컬 실행 절차

이 프로젝트는 Docker Compose를 사용하여 관리하는 것을 권장합니다.

### 사전 요구사항

1.  **Docker & Docker Compose**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치가 필요합니다.
2.  **PostgreSQL**: `docker-compose.yml`에 정의된 `kingwangjjang-postgres`를 사용하거나, 외부 PostgreSQL을 실행하고 `DATABASE_URL`을 설정합니다.

### 실행 단계

1.  **리포지토리 클론**:
    ```bash
    git clone <repository-url>
    cd kingwangjjang-be
    ```

2.  **환경 변수 설정**:
    프로젝트 루트 경로에 `.env` 파일을 생성합니다. 아래는 필수적으로 설정해야 할 환경 변수 예시입니다.
    ```env
    # Docker 이미지 가져올 때 사용할 DockerHub 사용자 이름
    DOCKERHUB_USERNAME=your-dockerhub-username

    # PostgreSQL 연결 정보
    POSTGRES_PORT=15432
    POSTGRES_DB=kingwangjjang
    POSTGRES_USER=kingwangjjang
    POSTGRES_PASSWORD=change-me
    DATABASE_URL=postgresql+psycopg://kingwangjjang:change-me@localhost:15432/kingwangjjang
    DOCKER_DATABASE_URL=postgresql+psycopg://kingwangjjang:change-me@kingwangjjang-postgres:5432/kingwangjjang
    DEV_DATABASE_TARGET=local

    # JWT 인증을 위한 시크릿 키
    JWT_SECRET_KEY=your-access-secret
    JWT_REFRESH_SECRET_KEY=your-refresh-secret

    # AI 서비스 간/관리 API 인증 토큰 (운영에서는 필수)
    AI_SERVICE_TOKEN=your-internal-ai-token
    AI_NODE_ADMIN_TOKEN=your-ai-node-admin-token
    ```

### AI 서버 노드 관리

최초 실행 시 `OLLAMA_BASE_URLS`(또는 `OLLAMA_BASE_URL`)와 `VLLM_BASE_URL`을
사용해 노드 테이블이 비어 있을 때만 기본 노드를 등록합니다. 이후 노드와
모델 변경은 PostgreSQL에 유지되며 관리 API가 기준 정보가 됩니다.

```bash
# 노드 목록 (로컬 소스 실행: 33330, Docker Compose: 8000)
curl -H "X-AI-Admin-Token: $AI_NODE_ADMIN_TOKEN" \
  http://localhost:33330/gptservice/api/ai/nodes

# 모든 노드의 즉시 상태 확인
curl -X POST -H "X-AI-Admin-Token: $AI_NODE_ADMIN_TOKEN" \
  http://localhost:33330/gptservice/api/ai/nodes/health-check
```

Docker Compose로 실행했다면 위 URL의 포트를 `8000`으로 바꿉니다.

정확한 등록 요청 형식은 실행 중인 `gpt-service`의 `/docs`에서 확인할 수
있습니다. API 키 원문은 요청이나 DB에 저장하지 않고 노드의 `api_key_env`에
환경변수 이름만 지정합니다.

3.  **서비스 실행**:
    루트 디렉터리의 `run` 스크립트를 사용합니다.
    ```bash
    # 모든 서비스 시작 (백그라운드)
    ./run.sh up

    # 서비스 로그 확인
    ./run.sh logs

    # 서비스 중지
    ./run.sh down
    ```

4.  **로컬 개발 DB 초기화/seed**:
    상위 통합 루트의 개발 스크립트를 사용하면 로컬 PostgreSQL을 준비한 뒤 정적 개발 데이터와 크롤링된 게시글 데이터를 같은 DB에 넣습니다.
    ```bash
    cd ..
    ./dev.sh seed
    ```

## 자주 발생하는 에러 및 해결법

1.  **Error: `service ... is unhealthy` 또는 `Connection refused`**
    *   **원인**: 서비스가 의존하는 다른 서비스(예: 데이터베이스, 다른 마이크로서비스)에 연결하지 못했습니다.
    *   **해결**:
        *   `.env` 파일의 `DATABASE_URL` 또는 `DOCKER_DATABASE_URL` 연결 정보가 올바른지 확인하세요.
        *   `docker-compose.yml`의 `depends_on` 설정을 확인하고, 의존하는 서비스가 먼저 정상적으로 시작되었는지 로그를 통해 확인하세요.

2.  **Error: `Cannot connect to the Docker daemon`**
    *   **원인**: Docker 데몬이 실행 중이 아니거나 현재 사용자가 Docker를 실행할 권한이 없습니다.
    *   **해결**: Docker Desktop을 실행하거나, Linux의 경우 Docker 서비스를 시작하고 사용자 권한을 확인하세요.

3.  **Error: `manifest for ... not found`**
    *   **원인**: `docker-compose.yml`에 명시된 Docker 이미지를 Docker Hub에서 찾을 수 없습니다.
    *   **해결**: `.env`의 `DOCKERHUB_USERNAME`이 올바른지, 해당 이미지와 태그가 실제로 존재하는지 확인하세요. 이미지를 직접 빌드해야 할 수도 있습니다.

4.  **Error: `Invalid Token` 또는 `401 Unauthorized`**
    *   **원인**: API 요청 시 사용된 JWT 토큰이 유효하지 않습니다.
    *   **해결**: `user-service`를 통해 정상적으로 토큰을 발급받았는지, 만료되지 않았는지 확인하세요.

5.  **Error: `ModuleNotFoundError` (로컬 직접 실행 시)**
    *   **원인**: Python 의존성이 설치되지 않았습니다.
    *   **해결**: 해당 서비스 디렉터리로 이동하여 `poetry install`을 실행하세요.

## 로그 및 트레이스 확인

*   **로그 위치**: 모든 서비스의 로그는 컨테이너 내부의 `/var/log`에 마운트된 프로젝트 루트의 `logs` 디렉터리에 저장됩니다.
*   **실시간 로그 확인**: `run.sh` 스크립트를 사용하여 모든 서비스의 로그를 한 번에 볼 수 있습니다.
    ```bash
    ./run.sh logs
    ```
*   **개별 서비스 로그 확인**:
    ```bash
    docker-compose logs -f <service-name>
    # 예시: docker-compose logs -f kingwangjjang-user-service
    ```
