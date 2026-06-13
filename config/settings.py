from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-change-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
_allowed_hosts = config("ALLOWED_HOSTS", default="", cast=Csv())
if _allowed_hosts:
    ALLOWED_HOSTS = _allowed_hosts
elif DEBUG:
    # Dev: izinkan akses dari HP/emulator via IP LAN (runserver 0.0.0.0:8000)
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "django_htmx",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "apps.core",
    "apps.organization",
    "apps.employees",
    "apps.shifts",
    "apps.attendance",
    "apps.leave",
    "apps.payroll",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.announcement_banners",
                "apps.web.context_processors.notifications",
                "apps.web.context_processors.admin_navigation",
                "apps.web.context_processors.master_data_navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

_db_engine = config("DB_ENGINE", default="django.db.backends.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": _db_engine,
        "NAME": config("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default=""),
        "PORT": config("DB_PORT", default=""),
        "OPTIONS": {},
    }
}

if "mysql" in _db_engine:
    DATABASES["default"]["OPTIONS"] = {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    }
    if config("DB_SSL_CA", default=""):
        DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": config("DB_SSL_CA")}

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:dashboard"
LOGOUT_REDIRECT_URL = "web:login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "HRIS-Lite API",
    "DESCRIPTION": "REST API for HRIS-Lite — mobile (Flutter) and integrations",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://127.0.0.1:8000,http://localhost:8000",
    cast=Csv(),
)
# Flutter web dev server (port acak per sesi, mis. localhost:63896)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
# Hanya untuk development; production set False di .env
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=DEBUG, cast=bool)

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@hris.local")
HRIS_SITE_URL = config("HRIS_SITE_URL", default="http://127.0.0.1:8000")
HRIS_DEFAULT_TENANT_SLUG = config("HRIS_DEFAULT_TENANT_SLUG", default="default")
HRIS_AUTO_PROVISION_EMPLOYEES = config("HRIS_AUTO_PROVISION_EMPLOYEES", default=DEBUG, cast=bool)

_csrf_origins = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = _csrf_origins
elif not DEBUG:
    CSRF_TRUSTED_ORIGINS = [HRIS_SITE_URL.rstrip("/")]
else:
    CSRF_TRUSTED_ORIGINS = []

USE_X_FORWARDED_HOST = config("USE_X_FORWARDED_HOST", default=not DEBUG, cast=bool)

# Audit log retention — DB hanya menyimpan log terbaru; sisanya diarsipkan via archive_audit_logs
HRIS_AUDIT_RETENTION_DAYS = config("HRIS_AUDIT_RETENTION_DAYS", default=365, cast=int)
HRIS_AUDIT_LIST_DEFAULT_DAYS = config("HRIS_AUDIT_LIST_DEFAULT_DAYS", default=90, cast=int)
HRIS_AUDIT_ARCHIVE_BATCH_SIZE = config("HRIS_AUDIT_ARCHIVE_BATCH_SIZE", default=5000, cast=int)
HRIS_AUDIT_ARCHIVE_DIR = config(
    "HRIS_AUDIT_ARCHIVE_DIR",
    default=str(BASE_DIR / "audit_archive"),
)

# Field-level encryption (NIK, rekening, gaji) — wajib set key unik di production
HRIS_FIELD_ENCRYPTION_KEY = config("HRIS_FIELD_ENCRYPTION_KEY", default=SECRET_KEY)

# SMTP (production)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)

if not DEBUG:
    if SECRET_KEY.startswith("django-insecure"):
        raise ValueError("Set SECRET_KEY yang kuat sebelum DEBUG=False.")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=SECURE_SSL_REDIRECT, cast=bool)
    CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=SECURE_SSL_REDIRECT, cast=bool)
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    if not EMAIL_HOST and EMAIL_BACKEND.endswith("smtp.EmailBackend"):
        import warnings

        warnings.warn("EMAIL_HOST belum diset — notifikasi email tidak akan terkirim.")
