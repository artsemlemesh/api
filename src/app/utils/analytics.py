import rudderstack.analytics as analytics
from django.conf import settings


def track_analytics(user_id, event, properties={}):
    try:
        if settings.ENVIRONMENT.lower() != "local":
            analytics.track(user_id, event, properties)
    except Exception as e:
        print("An error occurred while tracking:", e)
