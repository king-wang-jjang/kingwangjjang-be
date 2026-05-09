from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_principal
from app.auth.principal import Principal
from app.repositories.boards import BoardRepository
from app.utils.llm import LLMError


router = APIRouter(prefix="/api/boards", tags=["boards"])


def _to_board_response(board: dict) -> dict:
    return {
        "_id": board["id"],
        "category": board["category"],
        "no": board["no"],
        "site": board["site"],
        "title": board["title"],
        "url": board["url"],
        "contents": board.get("contents"),
        "gpt_answer": board.get("gpt_answer"),
        "tags": board.get("tags", []),
        "analysis_status": board.get("analysis_status"),
        "analysis_retry_count": board.get("analysis_retry_count", 0),
        "analysis_error": board.get("analysis_error"),
        "create_time": board["created_at"],
        "thumbnail": board.get("thumbnail"),
        "comment_count": board.get("comment_count", 0),
        "likeCount": board.get("like_count", 0),
    }


def _to_analysis_response(analysis: dict) -> dict:
    return {
        "boardId": analysis["board_id"],
        "status": analysis["status"],
        "summary": analysis.get("summary"),
        "tags": analysis.get("tags", []),
        "retryCount": analysis.get("retry_count", 0),
        "error": analysis.get("error"),
        "requestedAt": analysis.get("requested_at"),
        "startedAt": analysis.get("started_at"),
        "updatedAt": analysis.get("updated_at"),
    }


@router.get("/realtime")
def realtime(index: int = 0, limit: int = 30):
    return [_to_board_response(board) for board in BoardRepository().list_realtime(index, limit)]


@router.get("/daily")
def daily(index: int = 0, limit: int = 30):
    return [_to_board_response(board) for board in BoardRepository().list_daily(index, limit)]


@router.get("/{board_id}/ai")
def get_board_analysis(board_id: str):
    result = BoardRepository().get_analysis(board_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return _to_analysis_response(result)


@router.post("/{board_id}/ai", status_code=status.HTTP_202_ACCEPTED)
def request_board_analysis(board_id: str):
    try:
        result = BoardRepository().request_analysis(board_id)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail="AI analysis failed") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return _to_analysis_response(result)


@router.post("/{board_id}/likes")
def add_like(board_id: str, principal: Principal = Depends(require_principal)):
    result = BoardRepository().add_like(board_id, principal.user_id or "")
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return {
        "boardId": result["board_id"],
        "site": result["site"],
        "likeCount": result["like_count"],
    }
