# 백엔드 문서 인덱스

이 문서는 `kingwangjjang-be` 문서의 시작점입니다. 문서 내용은 2026-07-23 현재 저장소 구현을 기준으로 합니다.

## 시작하기

- [프로젝트 README](../README.md): 서비스 구성과 빠른 시작
- [실행·운영 가이드](./RUNBOOK.md): 환경변수, 로컬/컨테이너 실행, 점검과 장애 대응
- [아키텍처](./ARCHITECTURE.md): 서비스 경계, 인증, 데이터와 AI 처리 흐름

## 서비스별 문서

- [API Gateway](../api-gateway/README.md)
- [User Service](../user-service/README.md)
- [Board Service](../board-service/README.md)
- [Comment Service](../comment-service/README.md)
- [GPT Service](../gpt-service/README.md)
- [Notification Service](../notification-service/README.md)

실행 중인 각 FastAPI 서비스의 `/docs`에서는 실제 OpenAPI 명세를 확인할 수 있습니다. 외부 호출 경로에는 Gateway 접두사가 붙지만 서비스 자체 `/docs`에는 접두사가 없는 내부 경로가 표시됩니다.

## 설계·작업 기록

- [인기도 랭킹 선행 작업](./POPULARITY_RANKING_PREWORK.md)
- [`docs/superpowers/specs`](./superpowers/specs): 기능 설계 기록
- [`docs/superpowers/plans`](./superpowers/plans): 구현 계획 기록

설계·계획 문서는 작성 당시의 의사결정 기록입니다. 현재 동작을 확인할 때는 위의 프로젝트/서비스 문서와 코드를 우선하세요.

## 에이전트용 MSA 가이드

- [공통 가이드](./agents/README.md)
- [api-gateway](./agents/api-gateway.md)
- [user-service](./agents/user-service.md)
- [board-service](./agents/board-service.md)
- [comment-service](./agents/comment-service.md)
- [gpt-service](./agents/gpt-service.md)
- [notification-service](./agents/notification-service.md)

서비스를 변경하기 전에 공통 가이드와 해당 서비스 문서를 읽고, 다른 도메인의 데이터를 직접 읽는 대신 API 또는 명시적인 읽기 모델을 사용합니다.
