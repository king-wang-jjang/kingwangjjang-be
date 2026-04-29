# Kingwangjjang Backend Project

킹왕짱 프로젝트는 최신 웹 애플리케이션을 위한 마이크로서비스 기반 백엔드입니다. 사용자 관리, 게시판, 댓글, 알림 및 AI 기능을 제공합니다.

## 서비스 목록

| 서비스명                 | 역할                                     | 경로                        |
| ------------------------ | ---------------------------------------- | --------------------------- |
| **api-gateway**          | 모든 클라이언트 요청의 단일 진입점         | `/api-gateway`              |
| **user-service**         | 사용자 계정, 프로필, 인증 관리           | `/user-service`             |
| **board-service**        | 게시글 생성 및 관리                      | `/board-service`            |
| **comment-service**      | 게시글 댓글 관리                         | `/comment-service`          |
| **gpt-service**          | AI 기반 기능 제공                        | `/gpt-service`              |
| **notification-service** | 사용자 알림 전송                         | `/notification-service`     |

## 실행 방법

### Docker Compose (권장)

프로젝트를 실행하는 가장 표준적인 방법입니다. Docker가 설치되어 있어야 합니다.

1.  **환경 파일 생성**: 프로젝트 루트에 `.env.example` 파일이 있다면 `.env` 파일로 복사합니다. 없다면 필요한 환경 변수를 포함한 `.env` 파일을 직접 생성해야 합니다. (필수 변수는 `docs/RUNBOOK.md` 참고)

2.  **서비스 실행**: 아래 스크립트를 실행합니다.
    ```bash
    # Linux/macOS
    ./run.sh up

    # Windows (PowerShell)
    ./run.ps1 up
    ```

### 로컬 직접 실행

각 서비스는 Poetry를 사용하는 Python 프로젝트입니다. 개별 서비스의 `README.md`를 참고하여 직접 실행할 수 있습니다. (의존성 문제로 권장하지 않음)

## 테스트 실행 방법

`board-service`를 예로 들면, 해당 서비스 디렉터리로 이동하여 아래 명령어를 실행합니다. 다른 서비스도 유사한 방식으로 테스트할 수 있습니다.

```bash
# board-service 디렉터리에서 실행
poetry install
poetry run pytest
```

## 문서

더 자세한 정보는 아래 문서를 참고하세요.

*   [문서 인덱스 (docs/INDEX.md)](./docs/INDEX.md)