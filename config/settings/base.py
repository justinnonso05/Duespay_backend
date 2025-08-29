import os
from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# move this to env
SECRET_KEY = "django-insecure-4131hh(xs@!1d&b98l+si8yrmf!-u0g(@wv67u&^o27r3p4=r9"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main.apps.MainConfig",
    "association.apps.AssociationConfig",
    "payers.apps.PayersConfig",
    "payments.apps.PaymentsConfig",
    "transactions.apps.TransactionsConfig",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]

UNFOLD = {
    "SITE_TITLE": "Duespay Super Admin Dashboard",
    "SITE_HEADER": "DuesPay Super Admin",
    "SITE_BRAND": "DuesPay",
    "SHOW_HISTORY": True,
    "COLLAPSIBLE_NAV": True,
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "main.AdminUser"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "EXCEPTION_HANDLER": "main.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("main.renderers.CustomJSONRenderer",),
    "PAGE_SIZE": 7,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DuesPay API",
    "DESCRIPTION": "Dynamic dues payment platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SHOW_WARNINGS": False,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

NUBAPI_TOKEN = config("NUBAPI_KEY", default="")

KORAPAY_BASE_URL = "https://api.korapay.com/merchant/api/v1"

KORAPAY_SECRET_KEY = config("KORAPAY_SECRET_KEY", default="")
KORAPAY_PUBLIC_KEY = config("KORAPAY_PUBLIC_KEY", default="")
KORAPAY_ENCRYPTION_KEY = config("KORAPAY_ENCRYPTION_KEY", default="")

GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")

# OCR_SPACE_API_KEY = config('OCR_SPACE_API_KEY', default='helloworld')

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "korapay_webhooks.log",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "main.views": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "main.services": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "payments.services": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
