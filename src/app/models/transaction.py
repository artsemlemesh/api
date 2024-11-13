import stripe
from logging import Logger

from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from django_fsm import FSMField

from model_utils.fields import MonitorField
from model_utils import Choices
from model_utils.models import TimeStampedModel


logger = Logger(__file__)


class StripeAccount(TimeStampedModel):
    user = models.OneToOneField(
        'app.User', on_delete=models.CASCADE, related_name='stripe_account')
    account_id = models.CharField(max_length=255, null=True, blank=True)
    customer_id = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return '{} {}'.format(self.account_id, self.user)


class TRANSACTION_STATUS:
    pending = 'pending'
    complete = 'complete'


TRANSACTION_TYPE = Choices(
    'purchase',
    'payout',
    'refund'
)


class Transaction(TimeStampedModel):
    TRANSACTION_STATUS_CHOICES = (
        (TRANSACTION_STATUS.pending, _('pending')),
        (TRANSACTION_STATUS.complete, _('complete')),
    )

    bundle = models.ForeignKey(
        'app.Bundle', on_delete=models.SET_NULL, null=True)
    amount = MoneyField(
        max_digits=10, decimal_places=4, default_currency='USD')
    tx_type = models.CharField(choices=TRANSACTION_TYPE, max_length=8)

    status = FSMField(
        choices=TRANSACTION_STATUS_CHOICES,
        default=TRANSACTION_STATUS.pending)
    status_changed = MonitorField(monitor='status')
    transfer_details = models.TextField(default='Done')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def transfer_to_user_stripe(self):
        """
        This function transfer the transaction amount to user's stripe account
        If something went wrong from stripe side, transaction will be updated
        to status 'pending' and error details will be saved to
        transaction.transfer_details
        """
        try:
            stripe.Transfer.create(
                amount=int(self.amount * 100),
                currency="usd",
                destination=self.user.stripe_account.account_id,
                source_type='bank_account'
            )

        except Exception as e:
            self.status = 'pending'
            self.transfer_details = e.__dict__
            self.save()
            logger.error(e.__dict__)
