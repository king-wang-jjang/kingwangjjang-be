# from pydantic import BaseModel
# from bson import ObjectId

# class User(BaseModel):
#     id: str
#     name: str
#     email: str

#     class Config:
#         # MongoDB에서 ObjectId를 사용하기 위해 문자열로 변환
#         json_encoders = {
#             ObjectId: str
#         }