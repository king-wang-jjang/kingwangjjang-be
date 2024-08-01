# 우리가 설치한 authlib. fastapi는 starlette 기반이므로 fastapi도 starlette을 사용하는 것 같다.
from authlib.integrations.starlette_client import OAuth
# docs에서는 사용하지 않는 거지만 HTMLResponse가 있어야 내가 원하는 형태로 돌려줄 수 있다.
from starlette.responses import HTMLResponse
# 중요한 정보기 때문에 숨겨놓고 씁시다. google과 twitter에서 받아오시다.
from config import Config

oauth = OAuth()

import os
# Google API용 OAuth 2.0 인증 정보
REDIRECT_URI = 'http://localhost:8000'
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email']


oauth.register(
	name='google',
	client_id= Config().get_env('GOOGLE_CLIENT_ID'),
	client_secret=  Config().get_env('GOOGLE_CLIENT_SECRET'),
	server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

