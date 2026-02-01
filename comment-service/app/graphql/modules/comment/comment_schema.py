import datetime
from typing import List, Optional, Dict
import strawberry
from fastapi import HTTPException
from bson.objectid import ObjectId

from app.db.mongo_controller import MongoController
from app.utils.loghandler import setup_logger
from .comment_type import CommentEntry, CommentList, CreateCommentInput, UpdateCommentInput, DeleteCommentInput


logger = setup_logger()
db_controller = MongoController()


class CommentService:
    @staticmethod
    def get_user_nickname(user_id: str) -> Optional[str]:
        """user_id로 사용자 닉네임 조회"""
        try:
            user = db_controller.find_one("users", {"_id": ObjectId(user_id)})
            if user:
                return user.get("nickname")
            return None
        except Exception as e:
            logger.exception(f"Error fetching user nickname for user_id={user_id}: {e}")
            return None
    
    @staticmethod
    def get_user_nicknames_batch(user_ids: List[str]) -> Dict[str, str]:
        """여러 user_id에 대한 닉네임을 배치로 조회"""
        try:
            user_object_ids = [ObjectId(uid) for uid in user_ids]
            users = db_controller.find("users", {"_id": {"$in": user_object_ids}})
            
            nickname_map = {}
            for user in users:
                nickname_map[str(user["_id"])] = user.get("nickname", "알 수 없음")
            
            return nickname_map
        except Exception as e:
            logger.exception(f"Error batch fetching user nicknames: {e}")
            return {}
    
    @staticmethod
    def convert_to_comment_entries(comments: List[dict], viewer_user_id: Optional[str] = None) -> List[CommentEntry]:
        """댓글 목록을 CommentEntry로 변환"""
        comment_entries = []
        
        # 모든 댓글의 user_id를 수집하여 배치로 닉네임 조회
        user_ids = list(set([str(comment["user_id"]) for comment in comments]))
        nickname_map = CommentService.get_user_nicknames_batch(user_ids)
        
        # 현재 사용자가 좋아요 한 댓글들을 배치로 조회
        liked_comment_ids = set()
        try:
            if viewer_user_id:
                comment_object_ids = [comment["_id"] for comment in comments]
                if comment_object_ids:
                    likes = db_controller.find(
                        "CommentLike",
                        {"comment_id": {"$in": comment_object_ids}, "user_id": ObjectId(viewer_user_id)}
                    )
                    for like in likes:
                        liked_comment_ids.add(str(like.get("comment_id")))
        except Exception:
            # 좋아요 조회 실패 시 무시하고 넘어감
            liked_comment_ids = set()
        
        for comment in comments:
            user_id = str(comment["user_id"])
            comment_entry = CommentEntry(
                _id=str(comment["_id"]),
                board_id=str(comment["board_id"]),
                parent_id=str(comment["parent_id"]) if comment.get("parent_id") else None,
                content=comment["content"],
                user_id=user_id,
                user_nickname=nickname_map.get(user_id, "알 수 없음"),
                like_count=comment.get("like_count", 0),
                is_liked=(str(comment["_id"]) in liked_comment_ids),
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
    def comments(self, board_id: str, page: int = 1, limit: int = 20, info=None) -> CommentList:
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
            root_comments_cursor = db_controller.find("Comment", query, skip=skip, limit=limit, sort=[("created_at", -1)])

            # 각 최상위 댓글의 대댓글들 조회 (2Depth까지만)
            root_comments_list = list(root_comments_cursor)
            all_comments = list(root_comments_list)
            for root_comment in root_comments_list:
                root_id = root_comment["_id"]
                replies = db_controller.find(
                    "Comment", 
                    {"parent_id": root_id, "is_deleted": False},
                    sort=[("created_at", 1)]  # 대댓글은 시간순으로 정렬
                )
                all_comments.extend(list(replies))
            
            # CommentEntry로 변환
            # 현재 요청한 사용자의 ID를 가져와서 is_liked 정보를 포함시킴
            from app.utils.auth_utils import get_authenticated_user_id
            try:
                viewer_user_id = get_authenticated_user_id(info)
            except Exception:
                viewer_user_id = None

            comment_entries = CommentService.convert_to_comment_entries(all_comments, viewer_user_id)
            
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
            
            # 사용자 닉네임 조회
            user_nickname = CommentService.get_user_nickname(str(created_comment["user_id"]))

            return CommentEntry(
                _id=str(created_comment["_id"]),
                board_id=str(created_comment["board_id"]),
                parent_id=str(created_comment["parent_id"]) if created_comment.get("parent_id") else None,
                content=created_comment["content"],
                user_id=str(created_comment["user_id"]),
                user_nickname=user_nickname,
                like_count=created_comment.get("like_count", 0),
                is_liked=False,  # 새로 생성된 댓글은 좋아요 상태가 항상 False
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
            
            # 사용자 닉네임 조회
            user_nickname = CommentService.get_user_nickname(str(updated_comment["user_id"]))
            # 현재 요청 사용자가 이 댓글을 좋아요 했는지 확인
            try:
                existing_like = db_controller.find_one(
                    "CommentLike",
                    {"comment_id": updated_comment["_id"], "user_id": ObjectId(user_id)}
                )
                is_liked = bool(existing_like)
            except Exception:
                is_liked = False

            return CommentEntry(
                _id=str(updated_comment["_id"]),
                board_id=str(updated_comment["board_id"]),
                parent_id=str(updated_comment["parent_id"]) if updated_comment.get("parent_id") else None,
                content=updated_comment["content"],
                user_id=str(updated_comment["user_id"]),
                user_nickname=user_nickname,
                like_count=updated_comment.get("like_count", 0),
                is_liked=is_liked,
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
    def like_comment(self, comment_id: str, info) -> CommentEntry:
        try:
            # API Gateway에서 전달받은 사용자 정보 가져오기
            from app.utils.auth_utils import get_authenticated_user_id
            user_id = get_authenticated_user_id(info)
            
            # 댓글 존재 확인
            comment = db_controller.find_one("Comment", {"_id": ObjectId(comment_id)})
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")
            
            if comment.get("is_deleted", False):
                raise HTTPException(status_code=400, detail="Cannot like deleted comment")
            # 좋아요는 별도 컬렉션(CommentLike)으로 관리: 토글 동작 구현
            existing = db_controller.find_one(
                "CommentLike",
                {"comment_id": ObjectId(comment_id), "user_id": ObjectId(user_id)}
            )

            if existing:
                # 이미 좋아요 되어있으면 취소
                db_controller.delete_one("CommentLike", {"_id": existing["_id"]})
                new_like_count = max(0, comment.get("like_count", 0) - 1)
            else:
                # 좋아요 추가
                like_doc = {
                    "comment_id": comment["_id"],
                    "user_id": ObjectId(user_id),
                    "created_at": datetime.datetime.now()
                }
                db_controller.insert_one("CommentLike", like_doc)
                new_like_count = comment.get("like_count", 0) + 1

            db_controller.update_one(
                "Comment", 
                {"_id": ObjectId(comment_id)}, 
                {"$set": {"like_count": new_like_count, "updated_at": datetime.datetime.now()}}
            )
            
            # 업데이트된 댓글 조회
            updated_comment = db_controller.find_one("Comment", {"_id": ObjectId(comment_id)})
            
            # 사용자 닉네임 조회
            user_nickname = CommentService.get_user_nickname(str(updated_comment["user_id"]))
            # 현재 사용자가 이 댓글을 좋아요 했는지 확인
            try:
                existing_like = db_controller.find_one(
                    "CommentLike",
                    {"comment_id": updated_comment["_id"], "user_id": ObjectId(user_id)}
                )
                is_liked = bool(existing_like)
            except Exception:
                is_liked = False

            return CommentEntry(
                _id=str(updated_comment["_id"]),
                board_id=str(updated_comment["board_id"]),
                parent_id=str(updated_comment["parent_id"]) if updated_comment.get("parent_id") else None,
                content=updated_comment["content"],
                user_id=str(updated_comment["user_id"]),
                user_nickname=user_nickname,
                like_count=updated_comment.get("like_count", 0),
                is_liked=is_liked,
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

