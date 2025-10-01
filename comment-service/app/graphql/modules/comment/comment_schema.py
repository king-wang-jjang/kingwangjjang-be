import datetime
from typing import List, Optional
import strawberry
from fastapi import HTTPException
from bson.objectid import ObjectId

from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger
from .comment_type import CommentEntry, CommentList, CreateCommentInput, UpdateCommentInput, DeleteCommentInput, LikeCommentInput


logger = setup_logger()
db_controller = MongoController()


class CommentService:
    @staticmethod
    def convert_to_comment_entries(comments: List[dict]) -> List[CommentEntry]:
        """댓글 목록을 CommentEntry로 변환"""
        comment_entries = []
        
        for comment in comments:
            comment_entry = CommentEntry(
                _id=str(comment["_id"]),
                board_id=str(comment["board_id"]),
                parent_id=str(comment["parent_id"]) if comment.get("parent_id") else None,
                content=comment["content"],
                user_id=str(comment["user_id"]),
                like_count=comment.get("like_count", 0),
                reply_count=comment.get("reply_count", 0),
                is_deleted=comment.get("is_deleted", False),
                created_at=comment["created_at"],
                updated_at=comment["updated_at"]
            )
            comment_entries.append(comment_entry)
        
        return comment_entries
    
    @staticmethod
    def update_reply_count(comment_id: str):
        """댓글의 대댓글 수 업데이트"""
        try:
            # 직계 자식 수 계산
            reply_count = db_controller.count("Comment", {"parent_id": ObjectId(comment_id), "is_deleted": False})
            db_controller.update_one(
                "Comment", 
                {"_id": ObjectId(comment_id)}, 
                {"$set": {"reply_count": reply_count}}
            )
        except Exception as e:
            logger.exception(f"Error updating reply count for comment {comment_id}: {e}")


@strawberry.type
class Query:
    @strawberry.field
    def comments(self, board_id: str, page: int = 1, limit: int = 20) -> CommentList:
        try:
            # 페이지네이션을 위한 skip 계산
            skip = (page - 1) * limit
            
            # 최상위 댓글만 조회 (parent_id가 null인 댓글)
            query = {
                "board_id": ObjectId(board_id),
                "parent_id": None,
                "is_deleted": False
            }
            
            # 총 댓글 수 조회
            total_count = db_controller.count("Comment", {"board_id": ObjectId(board_id), "is_deleted": False})
            
            # 최상위 댓글 조회
            root_comments = db_controller.find("Comment", query, skip=skip, limit=limit, sort=[("created_at", -1)])
            
            # 각 최상위 댓글의 대댓글들 조회 (2Depth까지만)
            all_comments = list(root_comments)
            for root_comment in root_comments:
                root_id = root_comment["_id"]
                replies = db_controller.find(
                    "Comment", 
                    {"parent_id": root_id, "is_deleted": False},
                    sort=[("created_at", 1)]  # 대댓글은 시간순으로 정렬
                )
                all_comments.extend(replies)
            
            # CommentEntry로 변환
            comment_entries = CommentService.convert_to_comment_entries(all_comments)
            
            return CommentList(
                board_id=board_id,
                comments=comment_entries,
                total_count=total_count
            )
        except Exception as e:
            logger.exception(f"Error fetching comments for board_id={board_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch comments")


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_comment(self, input: CreateCommentInput, info) -> CommentEntry:
        try:
            # API Gateway에서 전달받은 사용자 정보 가져오기
            from app.utils.auth_utils import get_authenticated_user_id
            user_id = get_authenticated_user_id(info)
            
            now = datetime.datetime.now()
            board_id = ObjectId(input.board_id)
            
            # 대댓글인 경우 부모 댓글이 최상위 댓글인지 확인
            if input.parent_id:
                parent = db_controller.find_one("Comment", {"_id": ObjectId(input.parent_id)})
                if not parent:
                    raise HTTPException(status_code=404, detail="Parent comment not found")
                
                # 부모가 이미 대댓글인 경우 (2Depth 초과) 에러
                if parent.get("parent_id"):
                    raise HTTPException(status_code=400, detail="Cannot create reply to a reply (max 2 depth)")
            
            # 댓글 생성
            comment_doc = {
                "board_id": board_id,
                "parent_id": ObjectId(input.parent_id) if input.parent_id else None,
                "content": input.content,
                "user_id": ObjectId(user_id),
                "like_count": 0,
                "reply_count": 0,
                "is_deleted": False,
                "created_at": now,
                "updated_at": now
            }
            
            # 댓글 삽입
            result = db_controller.insert_one("Comment", comment_doc)
            comment_id = result.inserted_id
            
            # 대댓글인 경우 부모 댓글의 대댓글 수 업데이트
            if input.parent_id:
                CommentService.update_reply_count(input.parent_id)
            
            # 생성된 댓글 조회
            created_comment = db_controller.find_one("Comment", {"_id": comment_id})
            
            return CommentEntry(
                _id=str(created_comment["_id"]),
                board_id=str(created_comment["board_id"]),
                parent_id=str(created_comment["parent_id"]) if created_comment.get("parent_id") else None,
                content=created_comment["content"],
                user_id=str(created_comment["user_id"]),
                like_count=created_comment.get("like_count", 0),
                reply_count=created_comment.get("reply_count", 0),
                is_deleted=created_comment.get("is_deleted", False),
                created_at=created_comment["created_at"],
                updated_at=created_comment["updated_at"]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error creating comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to create comment")
    
    @strawberry.mutation
    def update_comment(self, input: UpdateCommentInput, info) -> CommentEntry:
        try:
            # API Gateway에서 전달받은 사용자 정보 가져오기
            from app.utils.auth_utils import get_authenticated_user_id
            user_id = get_authenticated_user_id(info)
            
            # 댓글 존재 확인 및 권한 확인
            comment = db_controller.find_one("Comment", {"_id": ObjectId(input.comment_id)})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            if str(comment["user_id"]) != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to update this comment")
            
            if comment.get("is_deleted", False):
                raise HTTPException(status_code=400, detail="Cannot update deleted comment")
            
            # 댓글 업데이트
            update_data = {
                "content": input.content,
                "updated_at": datetime.datetime.now()
            }
            
            db_controller.update_one(
                "Comment", 
                {"_id": ObjectId(input.comment_id)}, 
                {"$set": update_data}
            )
            
            # 업데이트된 댓글 조회
            updated_comment = db_controller.find_one("Comment", {"_id": ObjectId(input.comment_id)})
            
            return CommentEntry(
                _id=str(updated_comment["_id"]),
                board_id=str(updated_comment["board_id"]),
                parent_id=str(updated_comment["parent_id"]) if updated_comment.get("parent_id") else None,
                content=updated_comment["content"],
                user_id=str(updated_comment["user_id"]),
                like_count=updated_comment.get("like_count", 0),
                reply_count=updated_comment.get("reply_count", 0),
                is_deleted=updated_comment.get("is_deleted", False),
                created_at=updated_comment["created_at"],
                updated_at=updated_comment["updated_at"]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error updating comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to update comment")
    
    @strawberry.mutation
    def delete_comment(self, input: DeleteCommentInput, info) -> bool:
        try:
            # API Gateway에서 전달받은 사용자 정보 가져오기
            from app.utils.auth_utils import get_authenticated_user_id
            user_id = get_authenticated_user_id(info)
            
            # 댓글 존재 확인 및 권한 확인
            comment = db_controller.find_one("Comment", {"_id": ObjectId(input.comment_id)})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            if str(comment["user_id"]) != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
            
            if comment.get("is_deleted", False):
                raise HTTPException(status_code=400, detail="Comment already deleted")
            
            # 소프트 삭제
            db_controller.update_one(
                "Comment", 
                {"_id": ObjectId(input.comment_id)}, 
                {"$set": {"is_deleted": True, "updated_at": datetime.datetime.now()}}
            )
            
            # 부모 댓글의 대댓글 수 업데이트
            if comment.get("parent_id"):
                CommentService.update_reply_count(str(comment["parent_id"]))
            
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error deleting comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete comment")
    
    @strawberry.mutation
    def like_comment(self, input: LikeCommentInput, info) -> CommentEntry:
        try:
            # API Gateway에서 전달받은 사용자 정보 가져오기
            from app.utils.auth_utils import get_authenticated_user_id
            user_id = get_authenticated_user_id(info)
            
            # 댓글 존재 확인
            comment = db_controller.find_one("Comment", {"_id": ObjectId(input.comment_id)})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            if comment.get("is_deleted", False):
                raise HTTPException(status_code=400, detail="Cannot like deleted comment")
            
            # 좋아요 중복 확인 (실제 구현에서는 별도 컬렉션에서 관리)
            # 여기서는 간단히 좋아요 수만 증가시킴
            new_like_count = comment.get("like_count", 0) + 1
            
            db_controller.update_one(
                "Comment", 
                {"_id": ObjectId(input.comment_id)}, 
                {"$set": {"like_count": new_like_count, "updated_at": datetime.datetime.now()}}
            )
            
            # 업데이트된 댓글 조회
            updated_comment = db_controller.find_one("Comment", {"_id": ObjectId(input.comment_id)})
            
            return CommentEntry(
                _id=str(updated_comment["_id"]),
                board_id=str(updated_comment["board_id"]),
                parent_id=str(updated_comment["parent_id"]) if updated_comment.get("parent_id") else None,
                content=updated_comment["content"],
                user_id=str(updated_comment["user_id"]),
                like_count=updated_comment.get("like_count", 0),
                reply_count=updated_comment.get("reply_count", 0),
                is_deleted=updated_comment.get("is_deleted", False),
                created_at=updated_comment["created_at"],
                updated_at=updated_comment["updated_at"]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error liking comment: {e}")
            raise HTTPException(status_code=500, detail="Failed to like comment")


schema = strawberry.Schema(query=Query, mutation=Mutation)

