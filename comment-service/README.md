# Comment Service

댓글·답글, 수정·소프트 삭제와 댓글 좋아요를 소유하는 FastAPI 서비스입니다. 내부 포트는 `33335`, Gateway 공개 접두사는 `/commentservice`입니다.

## API

| 메서드·내부 경로 | 인증 | 설명 |
| --- | --- | --- |
| `GET /api/comments?boardId=...&page=1&limit=20` | 선택 | 게시글 댓글과 답글 조회 |
| `POST /api/comments` | 필수 | 댓글 또는 `parentId`가 있는 답글 생성 |
| `PATCH /api/comments/{comment_id}` | 작성자 | 내용 수정 |
| `DELETE /api/comments/{comment_id}` | 작성자 | 소프트 삭제 |
| `POST /api/comments/{comment_id}/like` | 필수 | 좋아요 토글 |

쓰기 요청의 사용자 ID는 Gateway가 검증해 전달한 헤더만 신뢰합니다. 댓글에는 작성 당시 사용자 표시명 snapshot이 저장될 수 있지만 사용자 프로필의 소유권은 user 서비스에 있습니다.

## 실행과 테스트

```bash
poetry install
poetry run uvicorn app.main:app --reload --port 33335
poetry run pytest -q
```

필수 환경변수는 `DATABASE_URL`입니다. 서비스 경계는 [Comment Service 에이전트 가이드](../docs/agents/comment-service.md)를 참고하세요.
