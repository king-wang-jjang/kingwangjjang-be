"""
Django settings for kingwangjjang project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
import os, json
from django.core.exceptions import ImproperlyConfigured

_ALLOWED_HOSTS = []

# 프로젝트 폴더에 secrets.json 있는 경우 -> 로컬 세팅
if os.path.isfile('secrets.json'):
    secret_file = os.path.join(BASE_DIR, './secrets.json') 

    with open(secret_file) as f:
        secrets = json.loads(f.read())

    def get_secret(setting, secrets=secrets):
        try:
            return secrets[setting]
        except KeyError:
            error_msg = "Set the {} environment variable".format(setting)
            raise ImproperlyConfigured(error_msg)

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = True
    SECRET_KEY = get_secret('SECRET_KEY')
    DB_HOST = get_secret("DB_HOST")
    DB_USER = get_secret("DB_USER")
    DB_PASSWORD = get_secret("DB_PASSWORD")
    DB_NAME = get_secret("DB_NAME")
    FTP_USER = get_secret("FTP_USER")
    FTP_PASSWORD = get_secret("FTP_PASSWORD")
    CHATGPT_API_KEY = get_secret("CHATGPT_API_KEY")
    
    # ALLOWED_HOSTS
    _ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    
    # Flow Check Log
    print("setting : Local setting, localhost")
    
# 프로젝트 폴더에 secrets.json 없는경우 -> 깃 CI/CD 사용 배포세팅
else:
    # github action setting
    SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
    DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
    DB_HOST = os.environ.get('DB_HOST')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME')
    FTP_USER = os.environ.get('FTP_USER')
    FTP_PASSWORD = os.environ.get('FTP_PASSWORD')
    CHATGPT_API_KEY = os.environ.get("CHATGPT_API_KEY")

    # ALLOWED_HOSTS
    _ALLOWED_HOSTS = ['*']
    
    # Flow Check Log
    print("setting : Deploy setting, Git Actions CI/CD")

FTP_SERVER = "14.35.104.153"
ALLOWED_HOSTS = _ALLOWED_HOSTS

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Graph QL
    'graphene_django',
    'graphene_mongo',
    
    'webCrwaling',
    'kingwangjjang',
    'chatGPT'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kingwangjjang.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [],
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kingwangjjang.wsgi.application'

# Database
# MongoDB settings
DB_URI = 'mongodb://'+ DB_HOST + '/' + DB_USER + ':' + DB_PASSWORD
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': DB_NAME,
        'ENFORCE_SCHEMA': True,
        'CLIENT': {
            'host': DB_URI
        }  
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# GRAPHENE = {
#     "SCHEMA": "webCrwaling.schema.schema"
# }
