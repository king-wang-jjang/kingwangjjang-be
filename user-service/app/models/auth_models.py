import strawberry
from typing import Optional
import datetime
from dataclasses import field  # 기본값을 설정하기 위해 필요

@strawberry.type
class FilterType:
    key: str
    value: str

@strawberry.type
class UserType:
    _id: Optional[str] = None
    # id: int = strawberry.field(name="user_id")
    # id: int
    user_id:  Optional[str] = None
    auth_provider: Optional[str] = None
    nickname: Optional[str] = None
    filter: Optional[FilterType] = None
    profile_image: Optional[str] = None
    # 현재 시간으로 기본값 설정
    create_time: datetime.datetime = field(default_factory=datetime.datetime.now)
