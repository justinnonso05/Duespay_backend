import cloudinary
from decouple import config

from .base import *

DEBUG = True
INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://c5a2096501ac.ngrok-free.app",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http:\/\/([a-zA-Z0-9-]+)\.localhost:5173$",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": config("CLOUDINARY_API_KEY"),
    "API_SECRET": config("CLOUDINARY_API_SECRET"),
}


cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE["CLOUD_NAME"],
    api_key=CLOUDINARY_STORAGE["API_KEY"],
    api_secret=CLOUDINARY_STORAGE["API_SECRET"],
)

EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"

ANYMAIL = {
    "BREVO_API_KEY": config("BREVO_API_KEY"),
}

DEFAULT_FROM_EMAIL = "DuesPay <jcmailer.1@gmail.com>"

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

FRONTEND_URL = "http://localhost:5173"
