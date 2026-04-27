# 실행 가이드 (RUNBOOK)

이 문서는 프로젝트의 로컬 실행, 디버깅, 환경 변수 설정에 대한 절차를 설명합니다.

## 로컬 실행 절차

이 프로젝트는 Docker Compose를 사용하여 관리하는 것을 권장합니다.

### 사전 요구사항

1.  **Docker & Docker Compose**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치가 필요합니다.
2.  **외부 데이터베이스**: `docker-compose.yml`에 데이터베이스가 정의되어 있지 않습니다. MongoDB와 같은 데이터베이스가 외부에서 실행되고 접근 가능해야 합니다. Docker를 사용하여 별도로 실행하거나 클라우드 서비스를 이용할 수 있습니다.
    ```bash
    # 예시: Docker로 MongoDB 실행
    docker run -d -p 27017:27017 --name my-mongo mongo
    ```

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

    # 데이터베이스 연결 정보
    DB_HOST=mongodb://<your-db-host>:<port> # 로컬 Docker 실행 시: mongodb://host.docker.internal:27017
    DB_USER=
    DB_PASS=
    DB_NAME=kingwangjjang

    # JWT 인증을 위한 시크릿 키
    JWT_SECRET=your-super-secret-key
    JWT_ALGORITHM=HS256
    ```

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

## 자주 발생하는 에러 및 해결법

1.  **Error: `service ... is unhealthy` 또는 `Connection refused`**
    *   **원인**: 서비스가 의존하는 다른 서비스(예: 데이터베이스, 다른 마이크로서비스)에 연결하지 못했습니다.
    *   **해결**:
        *   `.env` 파일의 `DB_HOST` 등 연결 정보가 올바른지 확인하세요.
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
