from datetime import datetime, timezone

from sqlalchemy import asc, desc, select

from app.db.models import Comment, CommentLike
from app.db.postgres import Base, get_engine, get_session_factory


class CommentRepository:
    def __init__(self):
        Base.metadata.create_all(bind=get_engine())

    def list_comments(
        self,
        board_id: str,
        page: int,
        limit: int,
        viewer_user_id: str | None = None,
    ) -> dict:
        safe_page = max(page, 1)
        safe_limit = max(limit, 1)
        offset = (safe_page - 1) * safe_limit

        with get_session_factory()() as session:
            total_count = len(
                session.scalars(
                    select(Comment).where(
                        Comment.board_id == board_id,
                        Comment.is_deleted.is_(False),
                    )
                ).all()
            )
            roots = session.scalars(
                select(Comment)
                .where(
                    Comment.board_id == board_id,
                    Comment.parent_id.is_(None),
                    Comment.is_deleted.is_(False),
                )
                .order_by(desc(Comment.created_at))
                .offset(offset)
                .limit(safe_limit)
            ).all()

            comments: list[Comment] = []
            for root in roots:
                comments.append(root)
                replies = session.scalars(
                    select(Comment)
                    .where(
                        Comment.parent_id == root.id,
                        Comment.is_deleted.is_(False),
                    )
                    .order_by(asc(Comment.created_at))
                ).all()
                comments.extend(replies)

            liked_ids = self._liked_comment_ids(session, comments, viewer_user_id)
            return {
                "board_id": board_id,
                "total_count": total_count,
                "comments": [self._to_dict(comment, comment.id in liked_ids) for comment in comments],
            }

    def create_comment(self, board_id: str, parent_id: str | None, content: str, user_id: str) -> dict:
        now = datetime.now(timezone.utc)

        with get_session_factory()() as session:
            if parent_id:
                parent = session.get(Comment, parent_id)
                if parent is None or parent.is_deleted:
                    raise ValueError("Parent comment not found")
                if parent.parent_id:
                    raise ValueError("Cannot create reply to a reply")

            comment = Comment(
                board_id=board_id,
                parent_id=parent_id,
                content=content,
                user_id=user_id,
                user_nickname=user_id,
                like_count=0,
                reply_count=0,
                is_deleted=False,
                created_at=now,
                updated_at=now,
            )
            session.add(comment)

            if parent_id:
                parent = session.get(Comment, parent_id)
                if parent is not None:
                    parent.reply_count = int(parent.reply_count or 0) + 1

            session.commit()
            session.refresh(comment)
            return self._to_dict(comment, False)

    def update_comment(self, comment_id: str, content: str, user_id: str) -> dict | None:
        with get_session_factory()() as session:
            comment = session.get(Comment, comment_id)
            if comment is None:
                return None
            if comment.user_id != user_id:
                raise PermissionError("Not authorized to update this comment")
            if comment.is_deleted:
                raise ValueError("Cannot update deleted comment")

            comment.content = content
            comment.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(comment)
            is_liked = self._is_liked(session, comment.id, user_id)
            return self._to_dict(comment, is_liked)

    def delete_comment(self, comment_id: str, user_id: str) -> bool | None:
        with get_session_factory()() as session:
            comment = session.get(Comment, comment_id)
            if comment is None:
                return None
            if comment.user_id != user_id:
                raise PermissionError("Not authorized to delete this comment")
            if comment.is_deleted:
                raise ValueError("Comment already deleted")

            comment.is_deleted = True
            comment.updated_at = datetime.now(timezone.utc)
            if comment.parent_id:
                parent = session.get(Comment, comment.parent_id)
                if parent is not None:
                    parent.reply_count = max(0, int(parent.reply_count or 0) - 1)
            session.commit()
            return True

    def toggle_like(self, comment_id: str, user_id: str) -> dict | None:
        with get_session_factory()() as session:
            comment = session.get(Comment, comment_id)
            if comment is None:
                return None
            if comment.is_deleted:
                raise ValueError("Cannot like deleted comment")

            like = session.scalar(
                select(CommentLike).where(
                    CommentLike.comment_id == comment_id,
                    CommentLike.user_id == user_id,
                )
            )
            is_liked = like is None
            if like is None:
                session.add(CommentLike(comment_id=comment_id, user_id=user_id))
                comment.like_count = int(comment.like_count or 0) + 1
            else:
                session.delete(like)
                comment.like_count = max(0, int(comment.like_count or 0) - 1)

            comment.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(comment)
            return self._to_dict(comment, is_liked)

    @staticmethod
    def _liked_comment_ids(session, comments: list[Comment], viewer_user_id: str | None) -> set[str]:
        if not viewer_user_id or not comments:
            return set()

        comment_ids = [comment.id for comment in comments]
        likes = session.scalars(
            select(CommentLike).where(
                CommentLike.comment_id.in_(comment_ids),
                CommentLike.user_id == viewer_user_id,
            )
        ).all()
        return {like.comment_id for like in likes}

    @staticmethod
    def _is_liked(session, comment_id: str, user_id: str) -> bool:
        return bool(
            session.scalar(
                select(CommentLike).where(
                    CommentLike.comment_id == comment_id,
                    CommentLike.user_id == user_id,
                )
            )
        )

    @staticmethod
    def _to_dict(comment: Comment, is_liked: bool) -> dict:
        return {
            "id": comment.id,
            "board_id": comment.board_id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "user_id": comment.user_id,
            "user_nickname": comment.user_nickname or comment.user_id,
            "like_count": int(comment.like_count or 0),
            "reply_count": int(comment.reply_count or 0),
            "is_liked": is_liked,
            "is_deleted": bool(comment.is_deleted),
            "created_at": comment.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": comment.updated_at.isoformat().replace("+00:00", "Z"),
        }
