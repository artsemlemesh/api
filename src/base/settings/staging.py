import requests
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from .base import *


SITE_URL = 'https://uat.bundleup.co'

# Enable bellow 2 variables if we need to check UAT issues from localhost
# ALLOWED_HOSTS = ['*']
# CORS_ORIGIN_ALLOW_ALL = True

# Disable bellow 2 variables if we need to check UAT issues from localhost
ALLOWED_HOSTS = [
    '.bynde.com',
    '.bundleup.co',
    '.amazonaws.com',
    'd3jdz1qvhqmos3.cloudfront.net',
    'bundleup-uat.eba-3ju5gctp.us-east-1.elasticbeanstalk.com'
]

CORS_ORIGIN_WHITELIST = (
    'http://localhost:3000',
    'https://uat.bynde.com',
    'https://uat.bundleup.co',
    'https://bynde-staging.s3-website-us-east-1.amazonaws.com',
    'https://d3jdz1qvhqmos3.cloudfront.net'
)


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
    environment="staging",
    dsn="https://a942bebf98dd4e09b2ecdf16c122cc24@o399095.ingest.sentry.io/5255677",
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.2,
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)

AWS_STORAGE_BUCKET_NAME = 'bundleup-staging'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

SQS_QUEUE_NAME = 'uat-bundleup-queue'

ENVIRONMENT = 'STAGING'

