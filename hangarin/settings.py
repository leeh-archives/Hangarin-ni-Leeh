"""
Settings for the Hangarin project.

Everything that changes between my laptop and PythonAnywhere is read from
environment variables, so nothing secret has to live in the repo.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file():
    """Read KEY=value lines from a .env file next to manage.py (if there is one).
    Real environment variables always win. The file is git-ignored."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_file()


# ---------------------------------------------------------------- basics

# On PythonAnywhere set DJANGO_SECRET_KEY and DJANGO_DEBUG=0 (see README).
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-dev-key-please-change-on-the-server",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".pythonanywhere.com"]
ALLOWED_HOSTS += [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

CSRF_TRUSTED_ORIGINS = ["https://*.pythonanywhere.com"]
CSRF_TRUSTED_ORIGINS += [
    o for o in os.environ.get("DJANGO_CSRF_ORIGINS", "").split(",") if o
]


# ---------------------------------------------------------------- apps

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "taskmanager",
    "pwa",

    # login, sign up and sign in with Google / GitHub
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "hangarin.urls"

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
                "taskmanager.context_processors.social_login",
            ],
        },
    },
]

WSGI_APPLICATION = "hangarin.wsgi.application"


# ---------------------------------------------------------------- database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------- passwords

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------- language / time

LANGUAGE_CODE = "en-us"

# Deadlines are shown in this time zone. Change it (or set DJANGO_TIME_ZONE)
# if you're somewhere else.
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Manila")

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------- static / media

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # filled by `collectstatic` on the server

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------- login (django-allauth)

# The Google / GitHub keys live in .env instead of the admin's "Social applications"
# page, so we don't need the Sites app (or a SITE_ID) here.

LOGIN_URL = "/accounts/login/"            # where login_required sends people
LOGIN_REDIRECT_URL = "/"                  # after a successful login
LOGOUT_REDIRECT_URL = "/accounts/login/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"         # allauth's own logout redirect
ACCOUNT_LOGOUT_ON_GET = True              # logging out doesn't ask a second time

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# you can log in with your username or your email
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if DEBUG else "https"

# Google / GitHub keys come from the environment or the .env file.
# A button only shows up on the login page once its keys are filled in.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [{"client_id": GOOGLE_CLIENT_ID, "secret": GOOGLE_CLIENT_SECRET, "key": ""}],
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["github"] = {
        "APPS": [{"client_id": GITHUB_CLIENT_ID, "secret": GITHUB_CLIENT_SECRET, "key": ""}],
        "SCOPE": ["user:email"],
    }

# first-time Google / GitHub users get an account straight away, no extra form
SOCIALACCOUNT_AUTO_SIGNUP = True

# PythonAnywhere terminates https before Django, so trust its header
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------- email

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ---------------------------------------------------------------- PWA (installable app)

PWA_APP_NAME = "Hangarin"
PWA_APP_DESCRIPTION = "A simple, cozy task and to-do manager"
PWA_APP_THEME_COLOR = "#E88BAA"
PWA_APP_BACKGROUND_COLOR = "#FFF5F8"
PWA_APP_DISPLAY = "standalone"
PWA_APP_SCOPE = "/"
PWA_APP_ORIENTATION = "portrait"
PWA_APP_START_URL = "/"
PWA_APP_STATUS_BAR_COLOR = "default"
PWA_APP_DIR = "ltr"

PWA_APP_LANG = "en-US"

PWA_APP_ICONS = [
    {"src": "/static/taskmanager/img/icon-192x192.png", "sizes": "192x192"},
    {"src": "/static/taskmanager/img/icon-512x512.png", "sizes": "512x512"},
]
PWA_APP_ICONS_APPLE = [
    {"src": "/static/taskmanager/img/icon-192x192.png", "sizes": "192x192"},
    {"src": "/static/taskmanager/img/icon-512x512.png", "sizes": "512x512"},
]

PWA_SERVICE_WORKER_PATH = os.path.join(
    BASE_DIR, "taskmanager", "static", "taskmanager", "serviceworker.js"
)
