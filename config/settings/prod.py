import os
import dj_database_url
from decouple import config
from .base import *

DEBUG = False

CORS_ALLOWED_ORIGINS = [
    'https://duespay.vercel.app',
]

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

ALLOWED_HOSTS = [
    'https://duespay.vercel.app',
]
