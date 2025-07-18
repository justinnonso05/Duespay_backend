import os
import dj_database_url
from decouple import config
from .base import *

DEBUG = False


INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']

CORS_ALLOWED_ORIGINS = [
    'https://duespay.vercel.app',
    'https://duespay.app',
    'https://www.duespay.app',
    'http://localhost:5173',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/([a-zA-Z0-9-]+)\.duespay.app$",
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

MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware'
)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


ALLOWED_HOSTS = [
    'duespay.pythonanywhere.com',
    'duespay.onrender.com',
    # add host production server here
]


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'jcmailer.1@gmail.com'
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = f"DUESPAY <{EMAIL_HOST_USER}>"

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

FRONTEND_URL = "https://www.duespay.app"
