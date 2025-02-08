from typing import Optional
import datetime
from dataclasses import dataclass, field

@dataclass
class FilterType:
    key: str
    value: str

@dataclass
class UserType:
    _id: Optional[str] = field(default=None, repr=False) 
    user_id: Optional[str] = None
    auth_organization: Optional[str] = None
    nickname: Optional[str] = None
    filter: Optional[FilterType] = None
    profile_image: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    create_time: datetime.datetime = field(default_factory=datetime.datetime.now)
