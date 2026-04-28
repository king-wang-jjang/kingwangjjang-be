from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_optional_principal, require_principal
from app.auth.principal import Principal
from app.repositories.comments import CommentRepository


router = APIRouter(prefix="/api/comments", tags=["comments"])


class CreateCommentRequest(BaseModel):
    boardId: str
    parentId: str | None = None
    content: str


class UpdateCommentRequest(BaseModel):
    content: str


def _to_comment_response(comment: dict) -> dict:
    return {
        "Id": comment["id"],
        "boardId": comment["board_id"],
        "parentId": comment.get("parent_id"),
        "content": comment["content"],
        "userId": comment["user_id"],
        "userNickname": comment.get("user_nickname"),
        "likeCount": comment.get("like_count", 0),
        "replyCount": comment.get("reply_count", 0),
        "isLiked": comment.get("is_liked", False),
        "isDeleted": comment.get("is_deleted", False),
        "createdAt": comment["created_at"],
        "updatedAt": comment["updated_at"],
    }


@router.get("")
def list_comments(
    boardId: str,
    page: int = 1,
    limit: int = 20,
    principal: Principal = Depends(get_optional_principal),
):
    result = CommentRepository().list_comments(
        board_id=boardId,
        page=page,
        limit=limit,
        viewer_user_id=principal.user_id if principal.is_authenticated else None,
    )
    return {
        "boardId": result["board_id"],
        "totalCount": result["total_count"],
        "comments": [_to_comment_response(comment) for comment in result["comments"]],
    }


@router.post("")
def create_comment(payload: CreateCommentRequest, principal: Principal = Depends(require_principal)):
    try:
        comment = CommentRepository().create_comment(
            board_id=payload.boardId,
            parent_id=payload.parentId,
            content=payload.content,
            user_id=principal.user_id or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_comment_response(comment)


@router.patch("/{comment_id}")
def update_comment(
    comment_id: str,
    payload: UpdateCommentRequest,
    principal: Principal = Depends(require_principal),
):
    try:
        comment = CommentRepository().update_comment(comment_id, payload.content, principal.user_id or "")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    return _to_comment_response(comment)


@router.delete("/{comment_id}")
def delete_comment(comment_id: str, principal: Principal = Depends(require_principal)):
    try:
        deleted = CommentRepository().delete_comment(comment_id, principal.user_id or "")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if deleted is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {"deleted": deleted}


@router.post("/{comment_id}/like")
def like_comment(comment_id: str, principal: Principal = Depends(require_principal)):
    try:
        comment = CommentRepository().toggle_like(comment_id, principal.user_id or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    return _to_comment_response(comment)
