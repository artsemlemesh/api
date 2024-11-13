from __future__ import absolute_import
from celery import Celery

app = Celery('bundleup')


app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
