from django.core.exceptions import ImproperlyConfigured
from .base import *

ALLOWED_HOSTS = ['*']

CORS_ALLOW_HEADERS = [
    'sentry-trace',  
    'Authorization',
    'Content-Type',
]

CORS_ORIGIN_ALLOW_ALL = True

SITE_URL = 'http://localhost:3000'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'byndeapp@gmail.com'
EMAIL_HOST_PASSWORD = 'Z0j2NSIr3On3'
EMAIL_USE_TLS = True
EMAIL_PORT = 587

AWS_STORAGE_BUCKET_NAME = 'bundleup-staging'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

AWS_ACCESS_KEY_ID = 'AKIA366NSBPRJSYVUMPW'
AWS_SECRET_ACCESS_KEY = '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'
AWS_S3_ACCESS_KEY_ID = 'AKIA366NSBPRJSYVUMPW'
AWS_S3_SECRET_ACCESS_KEY = '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'
EASY_SHIP_SECRET_KEY = 'webh_69409f161f3c46faa5ea9a14bc735e1a'

PEPO_API_KEY = 'e7ef407c5ece83bc3b6d25cff064462e'
PEPO_SECRET_KEY = '690167c4ab08402874d785b186f7ca17'
TEST_MODE = False

if not os.environ.get('DATABASE_URL'):
    DATABASE_HOSTNAME = os.environ.get('DATABASE_HOSTNAME')
    DATABASE_USERNAME = os.environ.get('DATABASE_USERNAME')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
    DATABASE_NAME = os.environ.get('DATABASE_NAME')
    DATABASE_PORT = os.environ.get('DATABASE_PORT', 5433)

    if any(not conf for conf in [
        DATABASE_HOSTNAME, DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD
    ]):
        raise ImproperlyConfigured('DATABASE_URL or DATABASE credential is required.')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': DATABASE_NAME,
            'USER': DATABASE_USERNAME,
            'PASSWORD': DATABASE_PASSWORD,
            'HOST': DATABASE_HOSTNAME,
            'PORT': DATABASE_PORT,
        }
    }

SQS_QUEUE_NAME = 'local-bundleup-queue'

ENVIRONMENT = 'LOCAL'
