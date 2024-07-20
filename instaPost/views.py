from fastapi import FastAPI, Form, Request, Depends, File, UploadFile, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.sessions import SessionMiddleware, Session
from pydantic import BaseModel
from typing import Optional
from .instaPost import InstaPost
import logging
import os

logger = logging.getLogger("")

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key='your-secret-key')

templates = Jinja2Templates(directory="templates")


class LoginForm(BaseModel):
    username: str
    password: str


class PhotoUploadForm(BaseModel):
    caption: Optional[str] = None


router = APIRouter()


def get_session(request: Request):
    return request.session


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...),
                session: Session = Depends(get_session)):
    form = LoginForm(username=username, password=password)

    # Instagram 로그인 시도
    client = InstaPost()
    login_result = client.insta_login(form.username, form.password)

    if login_result:
        # 로그인 성공 시
        session['insta_login'] = True
        return RedirectResponse(url='/upload_photo', status_code=303)
    else:
        # 로그인 실패 시
        return HTMLResponse("Login failed. Please try again.", status_code=400)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/upload_photo", response_class=HTMLResponse)
async def upload_photo(request: Request, media_file: UploadFile = File(...), caption: str = Form(None),
                       session: Session = Depends(get_session)):
    if not session.get('insta_login'):
        return HTMLResponse("Login first!", status_code=403)

    try:
        image_path = os.path.join("image", media_file.filename)
        with open(image_path, "wb") as f:
            f.write(await media_file.read())

        media_path = image_path

        # 미디어 업로드
        client = InstaPost()
        client.image_upload_one(media_path, caption)

        return HTMLResponse("Upload success!", status_code=200)
    except Exception as e:
        logger.error("Error uploading photo: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload_photo", response_class=HTMLResponse)
async def upload_photo_form(request: Request, session: Session = Depends(get_session)):
    if not session.get('insta_login'):
        return HTMLResponse("Login first!", status_code=403)

    return templates.TemplateResponse("upload_photo.html", {"request": request})


@router.get("/logout")
async def logout(request: Request, session: Session = Depends(get_session)):
    if session.get('insta_login'):
        client = InstaPost()
        client.insta_logout()
        del session['insta_login']
        messages.info(request, "You have been logged out successfully.")

    return RedirectResponse(url='/')


# 라우터를 애플리케이션에 추가
app.include_router(router)
