# User Service

Kakao OAuth, JWT 세션, refresh token 영속화와 사용자 프로필을 소유하는 FastAPI 서비스입니다. 내부 포트는 `33334`입니다.

## API

| 메서드·내부 경로 | Gateway 공개 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| `GET /login` | `/login` | 없음 | Kakao authorize URL로 redirect |
| `GET /callback` | `/callback` | OAuth code | 사용자 저장, 세션 쿠키 발급, `WEBSITE_URL`로 redirect |
| `POST /api/auth/refresh` | `/userservice/api/auth/refresh` | refresh 쿠키 | access/refresh token 회전, 성공 시 204 |
| `GET /api/users/me` | `/userservice/api/users/me` | 선택 | 로그인 사용자를 반환하며 비로그인은 `null` |
| `PATCH /api/users/me` | `/userservice/api/users/me` | 필수 | `displayName` 수정, 최대 40자 |

세션 쿠키는 HttpOnly, `SameSite=Lax`, path `/`입니다. access token TTL은 1시간, refresh token TTL은 400일이며 성공적으로 갱신할 때마다 다시 400일로 연장됩니다. 브라우저별 refresh token은 `user_sessions`에 SHA-256 해시로 따로 저장하므로 다른 기기에서 새로 로그인해도 기존 세션을 무효화하지 않습니다. 기존 `users.refresh_token`의 평문 토큰은 첫 갱신 트랜잭션에서 새 세션으로 이관되고 제거됩니다. `AUTH_COOKIE_SECURE`로 Secure 속성을 제어하며, 운영에서는 반드시 Secure 쿠키와 충분히 긴 별도의 `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`를 사용하세요.

refresh token 교체는 현재 세션 해시와 요청 token의 해시가 일치할 때만 성공하는 원자적 조건부 갱신입니다. 실패한 refresh 응답은 동시 성공 응답의 새 세션을 지우지 않도록 쿠키를 변경하지 않습니다.

## 실행

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 33334
```

주요 환경변수는 `DATABASE_URL`, `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`, `REDIRECT_URI`, `WEBSITE_URL`, `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, `AUTH_COOKIE_SECURE`입니다.

## 테스트

```bash
poetry run python -m unittest discover -s tests -q
poetry run python -m compileall app -q
```

데이터·인증 경계는 [User Service 에이전트 가이드](../docs/agents/user-service.md)를 참고하세요.
