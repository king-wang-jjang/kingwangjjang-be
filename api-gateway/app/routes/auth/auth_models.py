from pydantic import BaseModel, Field
from typing import Optional

class KakaoUserInfo(BaseModel):
    _id: int
    email: Optional[str]
    nickname: str
    profile_image: Optional[str]

class MongoUser(BaseModel):
    id: str = Field(alias="_id")
    kakao_id: int
    email: Optional[str]
    nickname: str
    profile_image: Optional[str]
