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

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "jcmailer.1@gmail.com"
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = f"DUESPAY <{EMAIL_HOST_USER}>"

KORAPAY_SECRET_KEY = config("KORAPAY_TEST_SECRET_KEY", default="")
KORAPAY_PUBLIC_KEY = config("KORAPAY_TEST_PUBLIC_KEY", default="")
KORAPAY_ENCRYPTION_KEY = config("KORAPAY_TEST_ENCRYPTION_KEY", default="")

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
NGROK_URL = "https://300e5c2440fa.ngrok-free.app"
KORAPAY_WEBHOOK_URL = f"{NGROK_URL}/api/transactions/webhook/"