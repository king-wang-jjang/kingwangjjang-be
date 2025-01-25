from pydantic import BaseModel, Field
from typing import Optional

class UserInfo(BaseModel):
    id: int  # 카카오 고유 ID
    auth_organization: Optional[str] = None  # 인증 기관 (선택적 필드)
    user_id: Optional[int] = None  # 사용자 ID (선택적 필드)
    nickname: Optional[str] = None  # 닉네임 (선택적 필드)
    filter: Optional[dict] = None  # 필터 데이터 (선택적 필드)
    profile_image: Optional[str] = None  # 프로필 이미지 URL (선택적 필드)
