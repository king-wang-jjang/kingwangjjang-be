# 문서 INDEX

이 문서는 `kingwangjjang-be` 프로젝트의 모든 기술 문서를 탐색하는 데 도움을 줍니다.

## 핵심 문서

*   [**실행 가이드 (RUNBOOK.md)**](./RUNBOOK.md)
    *   로컬 개발 환경 설정, 서비스 실행 및 디버깅 방법을 안내합니다.
*   [**아키텍처 (ARCHITECTURE.md)**](./ARCHITECTURE.md)
    *   서비스 간의 호출 관계, 데이터 흐름, 인증 방식을 설명합니다.

## 서비스별 문서

각 마이크로서비스에 대한 자세한 정보는 해당 서비스의 `README.md` 파일을 참고하세요.

*   [api-gateway](../api-gateway/README.md)
*   [board-service](../board-service/README.md)
*   [comment-service](../comment-service/README.md)
*   [gpt-service](../gpt-service/README.md)
*   [notification-service](../notification-service/README.md)
*   [user-service](../user-service/README.md)

## 문제 유형별 참고 문서

- **서비스 실행이 안될 때**: 먼저 [실행 가이드](./RUNBOOK.md)를 확인하고, 각 서비스의 로그 파일(`{service-name}/log/`)을 점검하세요.
- **데이터베이스 연결 문제**: `docker-compose.yml`에 DB 서비스가 포함되어 있는지 확인하고, `.env` 파일의 DB 연결 정보 (`DB_HOST`, `DB_USER`, `DB_PASS` 등)가 올바른지 확인하세요.
- **인증(로그인) 실패**: `user-service`의 로그와 `api-gateway`의 `auth_middleware.py` 로직을 확인하세요.
- **서비스 간 통신 오류**: [아키텍처](./ARCHITECTURE.md) 문서를 참고하여 서비스 호출 관계가 올바른지, 대상 서비스가 정상 실행 중인지 확인하세요.
- **AI 기능 문제**: `gpt-service`의 상태와 로그를 확인하세요.
