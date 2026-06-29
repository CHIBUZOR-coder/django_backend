from pathlib import Path
from datetime import timedelta  # sets token expiry times
from dotenv import load_dotenv  # loads your .env file
import os  # reads env variables

load_dotenv()  # activate .env loading — call only once
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-3!kb!@8d6k!z0c3vbm%c9jle)l*xh0d5&mnhfp73o4+l@!70p3"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    # ** Django's built-in apps
    "cloudinary",
    # used for displaying one-time notifications to users (e.g., success or error messages)
    "cloudinary_storage",
    "django.contrib.admin",
    # Admin interface for managing users, products, orders, etc.
    "django.contrib.auth",
    # Provides authentication framework, user management, and permissions system.
    "django.contrib.contenttypes",
    # "django.contrib.sites",  # Optional, needed if you use Django's sites framework for multi-site support.
    "django.contrib.sessions",
    # "django.contrib.messages",  # Optional, provides messaging framework for user notifications.
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Manages static files (CSS, JavaScript, images) for your project.
    # *** Third party packages
    "rest_framework",
    "corsheaders",
    "debug_toolbar",
    # ***Your apps
    # "users",
    "store",
    # "products",
    # "cart",
    # "orders",
]


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


AUTH_USER_MODEL = "store.User"
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ecome_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "ecome_backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# ✅ New — points to NeonDB
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}
# settings.py

# Explicitly forcing os.environ.get guarantees Django grabs the fresh .env data on initialization
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUD_NAME"),
    "API_KEY": os.getenv("API_KEY"),
    "API_SECRET": os.getenv("API_SECRET"),
}
import cloudinary

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
)

FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY")
FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN")  # http://localhost:3000

# Modern Django 6.x Storage Route Mapping
STORAGES = {
    "default": {
        # This securely intercepts user and product images and pushes them to Cloudinary
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # Keeps local development fast by leaving static files processing local
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# # 2. The legacy fallback string — matching StaticCloudinaryStorage
# STATICFILES_STORAGE = "cloudinary_storage.storage.StaticCloudinaryStorage"

# Password validation...
# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # ◄ Make sure this line is present!
MEDIA_URL = (
    "/media/"  # ◄ REQUIRED: Telling Django how to route media fallbacks dynamically
)


INTERNAL_IPS = [
    "127.0.0.1",
]
