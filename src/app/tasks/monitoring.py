import cronitor
from django.conf import settings
from celery import shared_task


cronitor.api_key = settings.CRONITOR_API_KEY
monitor = cronitor.Monitor('{}-CELERY-MONITOR'.format(settings.ENVIRONMENT))

@shared_task(name='heat_beat_scheduler')
def send_heart_beat():
    monitor.ping(message="Alive!")