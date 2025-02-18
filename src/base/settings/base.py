"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 2.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import sys
import stripe
import datetime
import dj_database_url

# from django.core.urlresolvers import reverse_lazy
from authy.api import AuthyApiClient
from distutils.util import strtobool
from boto.s3.connection import SubdomainCallingFormat
from celery.schedules import crontab
from dotenv import load_dotenv

from sentry_sdk.integrations.logging import ignore_logger

import rudderstack.analytics as analytics

analytics.write_key = os.getenv("RUDDERSTACK_WRITE_KEY", "2Y***7A")
analytics.dataPlaneUrl = "https://bundleupigrwiv.dataplane.rudderstack.com"

ignore_logger("django.security.DisallowedHost")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

FIXTURE_FOLDER = os.path.join("app", "fixtures")
FIXTURES_ROOT = os.path.join(PROJECT_ROOT, FIXTURE_FOLDER)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# NOTE: read environment variables from .env
load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = strtobool(os.getenv("DEBUG", "False"))
ALLOWED_HOSTS = []

# The email address that error messages sent to ADMINS and MANAGERS
# SERVER_EMAIL = 'Bynde Error <no-reply@bynde.com>'
SERVER_EMAIL = "Bynde Error <no-reply@bundleup.co>"

# sent exceptions raised in the request/response cycle.
# ADMINS = [('Vinay', 'vinay@bynde.com')]

# send broken link notifications when BrokenLinkEmailsMiddleware is enabled
# MANAGERS = ADMINS


ADMIN = "vinay@bynde.com"


# LOGINAS_REDIRECT_URL = '/loginas-redirect-url'


def CAN_LOGIN_AS(request, target_user):
    return request.user


LOGINAS_REDIRECT_URL = "/user/login/login-as"
# LOGOUT_URL = reverse_lazy('loginas-logout')

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "auditlog",

    "taggit",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_yasg",
    "dj_rest_auth",
    "django_user_agents",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "dj_rest_auth.registration",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "social_django",
    "djstripe",
    "sorl.thumbnail",
    "django_ses",
    "storages",
    "phonenumber_field",
    "sslserver",
    "django_celery_results",
    "django_celery_beat",
    "timezone_field",
    "loginas",
    "django_filters",
    "djmoney",
    "fsm_admin",
    "mptt",
    "cacheops",
    "app.apps.BundleupAppConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "django_user_agents.middleware.UserAgentMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_currentuser.middleware.ThreadLocalUserMiddleware"
]

ROOT_URLCONF = "base.urls"

DATABASES = {"default": dj_database_url.config()}

# Wrap each view in a transaction on this database
DATABASES["default"]["ATOMIC_REQUESTS"] = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(PROJECT_ROOT, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]
# TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS + (
#     'django.core.context_processors.request',
# )

WSGI_APPLICATION = "base.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, "public", "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "public", "media")

# This backend will only work in staging and production.
# see local.py for development
# EMAIL_BACKEND = 'django_ses.SESBackend'
EMAIL_BACKEND = "postmarker.django.EmailBackend"
POSTMARK_API_KEY = os.environ.get("POSTMARK_API_KEY", "")
POSTMARK = {
    "TOKEN": POSTMARK_API_KEY,
    "TEST_MODE": True,
    "VERBOSITY": 1,
}

EMAIL_FROM = "BundleUp <no-reply@bundleup.co>"

PASSWORD_RESET_TIMEOUT_DAYS = 1

SITE_ID = 1

ORDER_COMPLETE_PATH = "/order-complete"
ORDER_COMPLETE_ERROR_PATH = "/order-complete-error"

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        "APP": {
            "client_id": "1011628648286-03s74giq9s9vq2a6dr9t22getrlg2tra.apps.googleusercontent.com",
            "secret": "wbMbLGYzymdmoHox7sspTp_h",
            "key": "AIzaSyCw7O8ydcHBvr2psYkmYhavwCkxZ-wUiuY",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}


# social django configurations
MIDDLEWARE += [
    "social_django.middleware.SocialAuthExceptionMiddleware",
]
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get("FACEBOOK_APP_ID", "174051176589391")
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get(
    "FACEBOOK_SECRET_KEY", "fb3a6d53dbb072f0700de4eff18a82ed"
)
SOCIAL_AUTH_APPSECRET_PROOF = False
SOCIAL_AUTH_FACEBOOK_API_VERSION = "8.0"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/"

# google secret keys
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "773669666509-r1hs25piajn21q0g7t9g1k46hhvq0d99.apps.googleusercontent.com",
)
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get(
    "GOOGLE_SECRET_KEY", "4nU0yQzsKWfNI8ZpFVhI9APa"
)
FRONTEND_GOOGLE_CLIENT_ID = os.environ.get(
    "FRONTEND_GOOGLE_CLIENT_ID",
    "1011628648286-ue9pf98ju9lln7h51oaoo7u1ouj274gc.apps.googleusercontent.com",
)

# Google+ SignIn (google-oauth2)
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["email", "profile", "openid"]


SOCIAL_AUTH_APPLE_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgtJKSlfjTWJmVGMYG
XVZKZbGWDp3+6DhshLf4dUhOr2GgCgYIKoZIzj0DAQehRANCAATVJOn0MVwOzvXZ
ey12E1rSKKHCpA55rqJnsv12kIzYaqT3jT5tjuyHtP/jU/lT74jQCMRrMykX3sw7
zSyzcvSJ
-----END PRIVATE KEY-----"""
SOCIAL_AUTH_APPLE_KEY_ID = os.environ.get(
    "SOCIAL_AUTH_APPLE_KEY_ID", "P774BRUS5H")
# SOCIAL_AUTH_APPLE_PRIVATE_KEY = os.environ.get(
#     'SOCIAL_AUTH_APPLE_PRIVATE_KEY', PRIVATE_KEY)
SOCIAL_AUTH_APPLE_TEAM_ID = os.environ.get(
    "SOCIAL_AUTH_APPLE_TEAM_ID", "8H94847945")
SOCIAL_AUTH_APPLE_CLIENT_ID = os.environ.get(
    "SOCIAL_AUTH_APPLE_CLIENT_ID", "com.bundleup.ios"
)

FACEBOOK_EXTENDED_PERMISSIONS = ["email"]
SOCIAL_AUTH_FACEBOOK_SCOPE = ["email"]
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    "locale": "en_US",
    "fields": "id, name, email, picture",
}
API_VERSION = 8.0
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "base.utils.fb_require_email",
    "social_core.pipeline.social_auth.associate_by_email",
    "social.pipeline.mail.mail_validation",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "base.utils.get_profile_picture",
)

SOCIAL_AUTH_JSONFIELD_ENABLED = True

AUTHENTICATION_BACKENDS = [
    'social_core.backends.open_id.OpenIdAuth',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.google.GoogleOAuth',
    # django model authentication backend
    "django.contrib.auth.backends.AllowAllUsersModelBackend",
    # 'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIAL_AUTH_GOOGLE_ISSUER = "https://accounts.google.com"

# end social django config
AUTH_USER_MODEL = "app.User"
AUTH_CODE_CONFIRM_FAILURE_MAX = 3
ACCOUNT_USER_MODEL_USERNAME_FIELD = "email"

EXPIRING_TOKEN_LIFESPAN = datetime.timedelta(
    days=int(os.environ.get("EXPIRING_TOKEN_LIFESPAN", 15))
)


MANUAL_FUND_RELEASE_TIMEOUT = int(
    os.environ.get("MANUAL_FUND_RELEASE_TIMEOUT", 1)
)  # in days


THUMBNAIL_BACKEND = "base.sorl_thumbnail.Thumbnail"
THUMBNAIL_FORCE_OVERWRITE = True
THUMBNAIL_PRESERVE_FORMAT = True

# in pixels
THUMBNAIL_TINY_IMAGE_SIZE = "60x80"
THUMBNAIL_SMALL_IMAGE_SIZE = "600x800"
# LARGE NOT USED..
THUMBNAIL_LARGE_IMAGE_SIZE = "600x800"
THUMBNAIL_AVATAR_IMAGE_SIZE = "128x128"


TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
TWILIO_AUTHY_API = AuthyApiClient(TWILIO_API_KEY)


AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_S3_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
default_acl = "private"


AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

AWS_S3_FILE_OVERWRITE = True
AWS_QUERYSTRING_AUTH = False
AWS_S3_REGION_NAME = "us-east-1"
AWS_S3_CALLING_FORMAT = SubdomainCallingFormat()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SENDBIRD_APP_ID = os.getenv("SENDBIRD_APP_ID")
SENDBIRD_TOKEN = os.getenv("SENDBIRD_TOKEN")
SENDBIRD_BASE_URL = f"https://api-{SENDBIRD_APP_ID}.sendbird.com/v3"

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_PUBLIC_KEY = os.getenv("PLAID_PUBLIC_KEY")
PLAID_SECRET_KEY = os.getenv("PLAID_SECRET_KEY")
PLAID_ENV = os.getenv("PLAID_END", "sandbox")  # sandbox, development

PEPO_API_KEY = os.getenv("PEPO_API_KEY", "e7ef407c5ece83bc3b6d25cff064462e")
PEPO_SECRET_KEY = os.getenv(
    "PEPO_SECRET_KEY", "690167c4ab08402874d785b186f7ca17")

POSTMARK_API_KEY = os.getenv(
    "POSTMARK_API_KEY", "1a9d30b9-031a-4469-9960-7f01b4457648")


PHONENUMBER_DB_FORMAT = "INTERNATIONAL"

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
    "SECURITY_DEFINITIONS": {
        "oauth2": {
            "type": "apiKey",
            "description": "Example value. Token ac8bfe1ee265c14861b06a4c7ff4a3d9d04c9a1f12d3",
            "name": "Authorization",
            "in": "header",
        }
    },
}
PERSIST_AUTH = True
# LOGIN_URL = 'app:login'
# LOGOUT_URL = 'app:logout'


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # 'rest_framework.authentication.TokenAuthentication',
        #  'rest_framework.authentication.SessionAuthentication',
        #  'rest_framework.authentication.BasicAuthentication',
        "app.backends.authentication.ExpiringTokenAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
        "null": {
            "class": "logging.NullHandler",
            "filters": ["require_debug_false"],
        },
    },
    "loggers": {
        "console": {
            "handlers": ["console"],
            "propagate": True,
        },
        # Don't send invalid host error messages to ADMINS.
        # https://docs.djangoproject.com/en/dev/topics/logging/#django-security
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
    },
}

HUBSPOT_API_KEY = os.environ.get(
    "HUBSPOT_API_KEY", "d7bea843-02b8-445d-a684-f10b409e0c4d"
)

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TEST_MODE = "test" in sys.argv
UNITTEST_MODE = False
CORS_ALLOW_CREDENTIALS = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 11534336  # 11 MB

# STRIPE
STRIPE_PUBLISHABLE_KEY = "pk_test_51Mw5SEL57dGnBnScUFqGMHdOgUaFVUUCDTDMTcjFZ9fSGhJVx80ao3xOD5zJ5Az6yCfzZeOFfFjiUS0CyQUJjvha00TQ474QWO"
STRIPE_CONNECT_CLIENT_ID = os.environ.get("STRIPE_CONNECT_CLIENT_ID")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
# STRIPE_TEST_SECRET_KEY = os.environ.get('STRIPE_TEST_SECRET_KEY')
STRIPE_TEST_SECRET_KEY = STRIPE_SECRET_KEY
# STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY")
STRIPE_LIVE_SECRET_KEY = STRIPE_SECRET_KEY
STRIPE_LIVE_MODE = False
DJSTRIPE_WEBHOOK_VALIDATION = "retrieve_event"
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'
stripe.api_version = '2020-08-27'


EASYPOST_API_KEY = "EZTKe7d49d52491f46998cf625c80c03bd09Us8dlnzcgQJa7Ll3OaKLAw"
LOCAL_DEBUG = bool(os.environ.get("LOCAL_DEBUG"))


BROKER_TRANSPORT = "sqs"
BROKER_TRANSPORT_OPTIONS = {
    "region": "us-east-1",
}
BROKER_USER = os.getenv("AWS_ACCESS_KEY_ID")
BROKER_PASSWORD = os.getenv("AWS_SECRET_ACCESS_KEY")


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_TIME_ZONE = TIME_ZONE
CELERY_RESULT_PERSISTENT = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv
CELERY_TASK_STORE_EAGER_RESULT = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULTS_EXTENDED = True
CELERY_WORKER_REDIRECT_STDOUTS = True
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = "INFO"
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False


CELERY_BEAT_SCHEDULE = {
    # Check order items to create shipments in batch
    "create_shipments_in_batch": {
        "task": "shipment_purchase_shceduler",
        "schedule": crontab(minute="*/1"),  # every hour
    },
    "update_database": {
        "task": "update_data_in_databse",
        "schedule": crontab(minute="*/1"),  # every hour
    },
    "send_heart_beat": {
        "task": "heat_beat_scheduler",
        "schedule": crontab(minute="*/1"),  # every hour
    },
}

DATA_STORAGE_PATH = os.path.join(PROJECT_ROOT, "storage")
DATA_BG_REMOVAL_SOURCE_PATH = os.path.join(
    DATA_STORAGE_PATH, "tmp", "bg_removal_source"
)
LISTING_ITEM_IMAGE_RESIZE_DEFAULT_WIDTH = int(
    os.environ.get("LISTING_ITEM_IMAGE_RESIZE_DEFAULT_WIDTH", 600)
)
LISTING_ITEM_IMAGE_RESIZE_DEFAULT_HEIGHT = int(
    os.environ.get("LISTING_ITEM_IMAGE_RESIZE_DEFAULT_HEIGHT", 800)
)

REDIS_CACHE_LOCATION = os.environ.get(
    "REDIS_CACHE_LOCATION", "redis://redis:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_CACHE_LOCATION,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "cache__",
    }
}
CACHE_DEFAULT_TIMEOUT = 60 * 60  # 1 hour

# https://github.com/Suor/django-cacheops
CACHEOPS_REDIS = REDIS_CACHE_LOCATION
CACHEOPS_DEFAULTS = {"timeout": CACHE_DEFAULT_TIMEOUT}
CACHEOPS_DEGRADE_ON_FAILURE = True
CACHEOPS = {
    "app.listing": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "app.cart": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "app.order": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "app.transaction": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "app.shipment": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "app.user": {"ops": "all", "timeout": CACHE_DEFAULT_TIMEOUT},
    "*.*": {},
}

S3_FIXTURE_DATA_FOLDER_NAME = "fixtures"
AWS_PRODUCTION_STORAGE_BUCKET_NAME = "bundleup-production"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

USPS_USERNAME = os.environ.get("USPS_USERNAME")
USPS_PASSWORD = os.environ.get("USPS_PASSWORD")
CRONITOR_API_KEY = os.environ.get("CRONITOR_API_KEY")
