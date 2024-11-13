from django.utils.translation import gettext_lazy as _
from django.db import models
from model_utils.models import TimeStampedModel
from djstripe.models import Account as BaseAccount
from djstripe.models.core import Customer as BaseCustomer
from djstripe.models import PaymentIntent

from app.utils.epost import EasyPostUtils, easypost


class ByndeAccount(BaseAccount):
    @property
    def full_name(self) -> str:
        personal_info = self.individual
        return f"{personal_info['first_name']} {personal_info['last_name']}"

    @property
    def shipping_address(self) -> easypost.address:
        if isinstance(self.individual, dict) and 'address' in self.individual:
            address = self.individual['address']
        elif isinstance(self.company, dict) and 'address' in self.company:
            address = self.company['address']
        else:
            return None

        return EasyPostUtils.create_address(
            self.full_name,
            street1=address['line1'],
            street2=address['line2'],
            city=address['city'],
            state=address['state'],
            postal_code=address['postal_code'],
            phone=self.individual['phone']
        )

    def __str__(self):
        return f'{self.email}'

    class Meta:
        proxy = True
        verbose_name = _('account')


class ByndeCustomer(BaseCustomer):
    class Meta:
        proxy = True
        verbose_name = _('customer')


class ByndePayment(TimeStampedModel):
    order = models.OneToOneField(
        'app.Order', on_delete=models.CASCADE, related_name='payment')
    payment_intent = models.OneToOneField(
        PaymentIntent, on_delete=models.CASCADE, related_name='payment')

    class Meta:
        verbose_name = _('payment')
        ordering = ('-modified', )
