from .base import *
from decouple import config

DEBUG = True
INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'