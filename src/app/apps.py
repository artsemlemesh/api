from logging import Logger
from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig
logger = Logger(__file__)


class BundleupAppConfig(AppConfig):
    name = 'app'
    verbose_name = _('app')

    def ready(self):
        from . import signals
        from . import webhooks
        logger.info(f"connecting {signals.__name__} and {webhooks.__name__}")
