from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from instagrapi import Client
import logging

logger = logging.getLogger("")

app = FastAPI()
router = APIRouter()

class InstaPost:
    def __init__(self):
        self.client = Client()
        self.isLogined = False

    def insta_login(self, username: str, password: str):
        try:
            self.client.login(username, password)
            self.isLogined = True
            message = "로그인에 성공했습니다."
            logger.info(message)
            return True
        except Exception as e:
            if "We couldn't find an account with the username" in str(e):
                logger.info("아이디 혹은 비밀번호를 확인하세요.")
                return False
            else:
                logger.info("로그인에 문제가 있습니다:", e)
                return False

    def get_profile_image(self):
        if self.isLogined:
            profile_img = self.client.user_info_by_username(self.client.username).profile_pic_url
            return profile_img

    def image_upload_one(self, media_path: str, caption: str):
        if self.isLogined:
            try:
                self.client.photo_upload(media_path, caption)
                message = "게시물 업로드를 완료했습니다."
                return message
            except Exception as e:
                logger.info("게시물 업로드 중 문제가 생겼습니다.", e)
        else:
            message = "로그인 먼저 해주세요."
            return message

    def video_upload_one(self, media_path: str, caption: str):
        if self.isLogined:
            try:
                self.client.video_upload(media_path, caption)
                message = "게시물 업로드를 완료했습니다."
                return message
            except Exception as e:
                logger.info("게시물 업로드 중 문제가 생겼습니다.", e)
        else:
            message = "로그인 먼저 해주세요."
            return message

    def album_upload(self, media_path: list, caption: str):
        if self.isLogined:
            try:
                self.client.album_upload(media_path, caption)
                message = "게시물 업로드를 완료했습니다."
                return message
            except Exception as e:
                logger.info("게시물 업로드 중 문제가 생겼습니다.", e)
        else:
            message = "로그인 먼저 해주세요."
            return message

    def insta_logout(self):
        try:
            self.client.logout()
            return True
        except Exception as e:
            logger.info(f"Logout failed: {e}")
            return False

# 인스턴스 생성
insta_post = InstaPost()

class LoginRequest(BaseModel):
    username: str
    password: str

class UploadRequest(BaseModel):
    media_path: str
    caption: str

class AlbumUploadRequest(BaseModel):
    media_paths: list
    caption: str

@router.post("/login/")
async def login(request: LoginRequest):
    success = insta_post.insta_login(request.username, request.password)
    if success:
        return {"message": "로그인에 성공했습니다."}
    else:
        raise HTTPException(status_code=400, detail="아이디 혹은 비밀번호를 확인하세요.")

@router.get("/profile_image/")
async def get_profile_image():
    profile_img = insta_post.get_profile_image()
    if profile_img:
        return {"profile_image": profile_img}
    else:
        raise HTTPException(status_code=400, detail="로그인 먼저 해주세요.")

@router.post("/upload/image/")
async def upload_image(request: UploadRequest):
    message = insta_post.image_upload_one(request.media_path, request.caption)
    return {"message": message}

@router.post("/upload/video/")
async def upload_video(request: UploadRequest):
    message = insta_post.video_upload_one(request.media_path, request.caption)
    return {"message": message}

@router.post("/upload/album/")
async def upload_album(request: AlbumUploadRequest):
    message = insta_post.album_upload(request.media_paths, request.caption)
    return {"message": message}

@router.post("/logout/")
async def logout():
    success = insta_post.insta_logout()
    if success:
        return {"message": "로그아웃에 성공했습니다."}
    else:
        raise HTTPException(status_code=400, detail="로그아웃에 실패했습니다.")

app.include_router(router)
