"""
Django settings for config project.
"""

import ctypes
import os
from pathlib import Path

from dotenv import load_dotenv


# Point Django to system C-libraries instead of Anaconda's internal ones
for lib_path in ["/lib/x86_64-linux-gnu/libtiff.so.5", "/usr/lib/x86_64-linux-gnu/libtiff.so.5"]:
    try:
        ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
        break
    except Exception:
        pass


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# SECURITY & DEBUG
# ============================================================

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in (
    "true",
    "1",
    "yes",
)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError (f"DJANGO_SECRET_KEY is not set")

# ============================================================
# ALLOWED HOSTS
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,metrobazar.online,admin.metrobazar.online,api.metrobazar.online,.metrobazar.online,*").split(",")
    if host.strip()
]


# Check GDAL availability
try:
    from django.contrib.gis.gdal import HAS_GDAL
except Exception:
    HAS_GDAL = False

USE_GIS = HAS_GDAL and os.getenv("USE_GIS", "False").lower() in ("true", "1", "yes")


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Cloudinary storage (must be before staticfiles)
    "cloudinary_storage",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Cloudinary SDK
    "cloudinary",
]

if USE_GIS:
    INSTALLED_APPS.append("django.contrib.gis")

INSTALLED_APPS += [
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",

    # Local apps
    "authentication.apps.AuthenticationConfig",
    "accounts.apps.AccountsConfig",
    "catalog.apps.CatalogConfig",
    "products.apps.ProductsConfig",
    "logistics.apps.LogisticsConfig",
    "cart.apps.CartConfig",
    "orders.apps.OrdersConfig",
    "payments.apps.PaymentsConfig",
    "riders.apps.RidersConfig",
    "reviews.apps.ReviewsConfig",
    "panel.apps.PanelConfig",
    "wishlist.apps.WishlistConfig",
    "coupons.apps.CouponsConfig",
    "promotions.apps.PromotionsConfig",
    "analytics.apps.AnalyticsConfig",
    "notifications.apps.NotificationsConfig",
    "super_admin.apps.SuperAdminConfig",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.locale.LocaleMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL / WSGI
# ============================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# CUSTOM USER
# ============================================================

AUTH_USER_MODEL = "authentication.User"


# ============================================================
# DATABASE
# ============================================================

if USE_GIS:
    DB_ENGINE_DEFAULT = "django.contrib.gis.db.backends.postgis"
else:
    DB_ENGINE_DEFAULT = "django.db.backends.postgresql"

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", DB_ENGINE_DEFAULT),
        "NAME": os.getenv("DB_NAME", "banglamartdb"),
        "USER": os.getenv("DB_USERNAME", "banglamart"),
        "PASSWORD": os.getenv("DB_PASSWORD", "banglamartpass"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

LANGUAGES = [
    ("en", "English"),
    ("bn", "বাংলা"),
]

TIME_ZONE = "Asia/Dhaka"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = []

if (BASE_DIR / "static").exists():
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]


# ============================================================
# MEDIA FILES & CLOUDINARY STORAGE
# ============================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudinary Environment Credentials
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "dgbhx89au")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "786619224475667")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "Ez9f892aBjooX0zTvP9G-IxFbAU")
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
    "MAGIC_FOLDERS": False,
    "FOLDER": "metrobazar",
}

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# DRF
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),

    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# ============================================================
# CORS
# ============================================================

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://metrobazar.online,https://admin.metrobazar.online,https://api.metrobazar.online",
    ).split(",")
    if origin.strip()
]


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://metrobazar.online,https://admin.metrobazar.online,https://api.metrobazar.online",
    ).split(",")
    if origin.strip()
]


# ============================================================
# CELERY / REDIS
# ============================================================

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379",
)


CELERY_BROKER_URL = REDIS_URL

CELERY_RESULT_BACKEND = REDIS_URL

CELERY_ACCEPT_CONTENT = [
    "json",
]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TIME_LIMIT = 300

CELERY_TASK_SOFT_TIME_LIMIT = 240


CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-otps": {
        "task": "authentication.tasks.cleanup_expired_otps",
        "schedule": 120,
    },

    "cleanup-old-verified-otps": {
        "task": "authentication.tasks.cleanup_old_verified_otps",
        "schedule": 86400,
    },

    "cancel-unpaid-orders": {
        "task": "orders.tasks.cancel_unpaid_orders",
        "schedule": 300,
    },

    "reconcile-payments": {
        "task": "payments.tasks.reconcile_pending_payments",
        "schedule": 900,
    },
}


# ============================================================
# DJANGO REDIS CACHE
# ============================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",

        "LOCATION": os.getenv(
            "REDIS_CACHE_URL",
            "redis://127.0.0.1:6379/1",
        ),

        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}


# ============================================================
# SECURITY SETTINGS
# ============================================================

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

X_FRAME_OPTIONS = "DENY"

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_BROWSER_XSS_FILTER = True


# ============================================================
# PRODUCTION HTTPS SECURITY
# ============================================================
DEBUG = os.getenv("DJANGO_DEBUG","False").lower() == "true"


if not DEBUG:
    # Redirect HTTP → HTTPS
    SECURE_SSL_REDIRECT = True

    # Required when Django is behind Nginx, Cloudflare,
    # Render, Railway, etc.
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    # Only send cookies over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Additional security
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

    X_FRAME_OPTIONS = "DENY"

else:
    # Local development
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0

# ============================================================
# EMAIL CONFIGURATION (Spacemail SMTP)
# ============================================================
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "mail.spacemail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "True").lower() == "true"
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "admin@metrobazar.online")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Metro Bazar Admin <admin@metrobazar.online>")
ADMIN_NOTIFICATION_EMAIL = os.getenv("ADMIN_NOTIFICATION_EMAIL", "metrobazar2025@gmail.com")


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "{levelname} {asctime} "
                "{module} {process:d} {thread:d} "
                "{message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["console"],
        "level": os.getenv(
            "DJANGO_LOG_LEVEL",
            "INFO",
        ),
    },
}