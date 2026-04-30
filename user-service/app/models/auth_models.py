import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FilterType:
    key: str
    value: str


@dataclass
class UserType:
    _id: Optional[str] = None
    user_id: Optional[str] = None
    auth_provider: Optional[str] = None
    nickname: Optional[str] = None
    filter: Optional[FilterType] = None
    profile_image: Optional[str] = None
    create_time: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
