# API Gateway

마이크로서비스 아키텍처의 중앙 게이트웨이입니다.

## 기능

- 인증 및 권한 관리
- 요청 라우팅
- 미들웨어 처리

## 실행

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

