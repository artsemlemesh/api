import requests
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration


SITE_URL = 'https://www.bundleup.co'

ALLOWED_HOSTS = [
    '.bundleup.co',
    '.amazonaws.com',
    'd32z6l8weirujj.cloudfront.net',
]

CORS_ORIGIN_WHITELIST = (
    'https://bundleup.co',
    'https://www.bundleup.co',
    'https://bundleup-production.s3-website-us-east-1.amazonaws.com',
    'https://d32z6l8weirujj.cloudfront.net'
)

AWS_STORAGE_BUCKET_NAME = 'bundleup-production'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
POSTMARK['TEST_MODE'] = False
POSTMARK['VERBOSITY'] = 0

# Add Elastic Beanstalk EC2 private IP to allowed hosts used by Elastic Beanstalk health check
ec2_private_ip = None
try:
    ec2_private_ip = requests.get(
        'http://169.254.169.254/latest/meta-data/local-ipv4', timeout=0.01).text
except requests.exceptions.RequestException:
    pass

if ec2_private_ip:
    ALLOWED_HOSTS.append(ec2_private_ip)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

sentry_sdk.init(
    environment="production",
    dsn="https://a942bebf98dd4e09b2ecdf16c122cc24@o399095.ingest.sentry.io/5255677",
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.2,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)

STRIPE_LIVE_MODE = True
STRIPE_PUBLISHABLE_KEY = 'pk_live_51Mw5SEL57dGnBnScBtGE4XBe2KfHsDOiqHtW1D5VUmOWj7NC4KmF6xCR7rmX4mSbvang4qIYdctarVQU7A9n9RzH004kJlhNzV'

SQS_QUEUE_NAME = 'prod-bundleup-queue'

ENVIRONMENT = 'PRODUCTION'

EASYPOST_API_KEY = os.environ.get("EASYPOST_API_KEY_PROD")