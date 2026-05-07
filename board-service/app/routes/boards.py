from fastapi import APIRouter, Depends, HTTPException

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
        "create_time": board["created_at"],
        "thumbnail": board.get("thumbnail"),
        "comment_count": board.get("comment_count", 0),
        "likeCount": board.get("like_count", 0),
    }


@router.get("/realtime")
def realtime(index: int = 0, limit: int = 30):
    return [_to_board_response(board) for board in BoardRepository().list_realtime(index, limit)]


@router.get("/daily")
def daily(index: int = 0, limit: int = 30):
    return [_to_board_response(board) for board in BoardRepository().list_daily(index, limit)]


@router.post("/{board_id}/ai")
def analyze_board(board_id: str):
    try:
        result = BoardRepository().analyze_board(board_id)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail="AI analysis failed") from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return {
        "boardId": result["board_id"],
        "summary": result["summary"],
        "tags": result["tags"],
    }


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
