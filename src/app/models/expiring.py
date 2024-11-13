import datetime
from django.conf import settings
from django.utils import timezone
from rest_framework.authtoken.models import Token


class ExpiringToken(Token):
    """Extend Token to add an expired method."""

    class Meta(object):
        proxy = True

    @property
    def is_expired(self):
        """Return boolean indicating token expiration."""
        now = timezone.now()
        if self.created < now - settings.EXPIRING_TOKEN_LIFESPAN:
            return True
        return False

    @property
    def should_refresh(self):
        """Return boolean indicating if token should be refreshed."""
        now = timezone.now()
        n_days = settings.EXPIRING_TOKEN_LIFESPAN - datetime.timedelta(days=int(5))
        if self.created < now - n_days:
            return True
        return False
