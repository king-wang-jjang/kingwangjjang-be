# Notification Service

향후 알림 전달을 위한 FastAPI 스캐폴드입니다. 현재는 빈 애플리케이션 객체만 있으며 다음 항목은 아직 구현되지 않았습니다.

- 알림 API와 메시지 계약
- 푸시·이메일·webhook 전송 로직
- 재시도와 idempotency
- 알림 영속화
- Gateway/Compose/다른 서비스 연결

따라서 현재 운영 서비스로 간주하거나 board/comment 동작이 알림을 발생시킨다고 가정하면 안 됩니다.

개별 스캐폴드 실행은 다음과 같습니다.

```bash
poetry install
poetry run uvicorn main:app --reload --port 8000
```

구현을 시작하기 전에 동기 API와 비동기 이벤트 중 전달 방식을 결정하고 [Notification Service 에이전트 가이드](../docs/agents/notification-service.md)의 경계를 따르세요.
