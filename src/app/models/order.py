import stripe
from collections import defaultdict
from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from djstripe.models import PaymentIntent
from model_utils.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField

from app.constants.status import PRODUCT_STATUS, ORDER_ITEM_STATUS
from app.models import ByndeCustomer, Bundle, Shipment
from app.models.shipment import SHIPMENT_STATUS
from app.utils.epost import EasyPostUtils
from app.tasks import send_pepo_email

# import logging
# logger = logging.getLogger(__name__)


class Order(TimeStampedModel):
    platform_order_id = models.UUIDField(
        unique=True, verbose_name=_('platform order id'))
    customer = models.ForeignKey(
        ByndeCustomer, on_delete=models.CASCADE,
        related_name='orders', verbose_name=_('customer'))
    payment_intent = models.OneToOneField(
        PaymentIntent, on_delete=models.CASCADE,
        related_name='payment_intent_order', verbose_name=_('stripe payment intent'))

    address_line_1 = models.CharField(
        _('address line 1'), max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(
        _('address line 2'), max_length=255, null=True, blank=True)
    city = models.CharField(
        _('city'), max_length=255, null=True, blank=True)
    state = models.CharField(
        _('state'), max_length=255, null=True, blank=True)
    postal_code = models.CharField(
        _('postal_code'), max_length=15, null=True, blank=True)
    country = models.CharField(
        _('country'), max_length=255, null=True, blank=True)
    phone = PhoneNumberField(
        blank=True, null=True, verbose_name=_('phone number'))

    class Meta:
        verbose_name = _('order')
        ordering = ('-modified', )

    @property
    def active_items(self):
        return self.order_items.exclude(
            status__in=[
                ORDER_ITEM_STATUS.canceled,
                ORDER_ITEM_STATUS.in_return
            ])

    @property
    def count(self) -> int:
        return self.active_items.count()


class OrderItemModelManager(models.Manager):
    def get_items_ready_to_ship(self):
        return super().get_queryset().filter(
            status__in=[
                ORDER_ITEM_STATUS.active,
                ORDER_ITEM_STATUS.ready_to_ship
            ])



class OrderItem(TimeStampedModel):
    ORDER_ITEM_STATUS_CHOICES = (
        (ORDER_ITEM_STATUS.active, _('active')),
        (ORDER_ITEM_STATUS.ready_to_ship, _('ready to ship')),
        (ORDER_ITEM_STATUS.label_pending, _('in progress of label printing')),
        (ORDER_ITEM_STATUS.label_printed, _('postage label purchased')),
        (ORDER_ITEM_STATUS.label_failure, _('failed to print postage label')),
        (ORDER_ITEM_STATUS.in_transit, _('in transit')),
        (ORDER_ITEM_STATUS.received, _('received')),
        (ORDER_ITEM_STATUS.canceled, _('canceled')),
        (ORDER_ITEM_STATUS.in_return, _('in return')),
    )

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='order_items', verbose_name=_('order'))
    bundle = models.OneToOneField(
        Bundle, on_delete=models.CASCADE, related_name='order_item',
        verbose_name=_('bundle'))
    status = FSMField(
        choices=ORDER_ITEM_STATUS_CHOICES, default=ORDER_ITEM_STATUS.active,
        verbose_name=_('order item status'))

    reason = models.TextField(_('failure reason'), null=True, blank=True)

    batch = models.CharField(max_length=255,blank=True,null=True,verbose_name=_('batch_id'))

    shipmentid = models.CharField(max_length=255,blank=True,null=True,verbose_name=_('shipment_id'))

    objects = OrderItemModelManager()

    class Meta:
        verbose_name = _('order item')
        unique_together = ('order', 'bundle', )
        ordering = ('order', '-modified', )

    def create_shipment(
        self,
        street_address_1: str, city: str, postal_code: str, state: str,
        street_address_2: str = None
    ):
        # TODO: Not done yet.
        from_address = self.bundle.created_by.shipping_address
        to_address = EasyPostUtils.create_address(
            self.order.customer.user.get_full_name(),
            street1=street_address_1,
            city=city, state=state, postal_code=postal_code,
            phone=self.order.customer.user.phone,
            street2=street_address_2
        )
        customs_items = [
            EasyPostUtils.create_customs_item(
                self.bundle.title,
                quantity=1,
                # Need to be adjusted later
                value=self.bundle.seller_price.amount,
                weight=1,
                hs_tariff_number=self.pk
            )]
        customs_info = EasyPostUtils.create_customs_info(
            self.order.customer.user.get_full_name(),
            customs_items, contents_type='other'
        )
        kwargs = {}
        if self.bundle.shipping_type:
            kwargs = {
                "predefined_package": self.bundle.shipping_type.rate_type
            }

        parcel = EasyPostUtils.create_parcel(
            # self.bundle.length,
            # self.bundle.width,
            # self.bundle.height,
            self.bundle.weight,
            **kwargs
        )
        shipment = EasyPostUtils.create_shipment(
            to_address, from_address,
            parcel, customs_info, buy_postage_label=True
        )

        # TODO: We will move to batch based workflow and
        # printing label will be done by an independence endpoint by seller
        # if not shipment.rates:
        #     raise Exception('Unfortunately no courier available.')
        shipment, created = Shipment.objects.\
            get_or_create_from_easypost_object(self, shipment)
        self.bundle.sold()
        self.bundle.save()
        return shipment

    def __get_parcel(self):
        kwargs = {}
        if self.bundle.shipping_type:
            kwargs = {
                "predefined_package": self.bundle.shipping_type.type
            }
        return EasyPostUtils.create_parcel(self.bundle.weight, **kwargs)

    # def save(self, *args, **kwargs):
    #     if self.pk:
    #         old_status = OrderItem.objects.get(pk=self.pk).status
    #         if old_status != self.status:
    #             print(f"OrderItem {self.pk} state changing from {old_status} to {self.status}")
    #     super().save(*args, **kwargs)





    def to_shipment_dict(self) -> dict:
        return {
            'reference': f'ORDER_ITEM__{self.pk}',
            'from_address': self.bundle.created_by.shipping_address,
            'to_address': {
                'name': self.order.customer.name,
                'street1': self.order.address_line_1,
                'street2': self.order.address_line_2,
                'city': self.order.city,
                'state': self.order.state,
                'zip': self.order.postal_code
            },
            'parcel': self.__get_parcel(),
            'carrier': 'USPS',
            'service': 'Priority',
        }

    def can_be_received(self) -> bool:
        # NOTE: This code just moved from bundle model
        # and need to consider later.
        _errors = defaultdict(list)
        if self.bundle.status not in [
                PRODUCT_STATUS.sold, PRODUCT_STATUS.shipped]:
            _errors['status'].append(_(
                'This bundle can not be received yet.'))
        # NOTE: instance should have payment and shipment
        if not hasattr(self.order, 'payment_intent'):
            _errors['status'].append(_(
                'No payment found for this bundle'))
        # elif self.order.payment_intent.status !=\
        #         'requires_confirmation':
        #     _errors['status'].append(_(
        #         'Can not confirm the payment.'))

        if not hasattr(self, 'shipment'):
            _errors['status'].append(_(
                'No shipment found for this bundle.'))
        # TODO: Require to check tracker for the corresponding shipment?
        return bool(_errors.keys())

    @transaction.atomic()
    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.in_transit],
        target=ORDER_ITEM_STATUS.received,
        conditions = []
        # conditions=[can_be_received()]
    )
    def receive(self):
        pass
        # stripe.Transfer.create(
        #     amount=int(self.bundle.seller_price.amount * 100),
        #     currency='usd',
        #     destination=self.bundle.created_by.account.id,
        #     transfer_group=self.order.platform_order_id,
        # )

    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.label_failure],
        target=ORDER_ITEM_STATUS.ready_to_ship,
        conditions=[]
    )
    def confirm_to_ship(self):
        pass

    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.ready_to_ship],
        target=ORDER_ITEM_STATUS.label_pending,
        conditions=[]
    )
    def wait_to_print_label(self):
        pass

    def __can_be_printed(self) -> bool:
        return hasattr(self, 'shipment')

    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.label_pending],
        target=ORDER_ITEM_STATUS.label_printed,
        conditions=[__can_be_printed]
    )
    def label_printed(self):
        if hasattr(self, 'shipment') and not self.shipment.label_url:
            self.shipment.retrieve_label_url_from_easypost()
            self.save()


    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.ready_to_ship,ORDER_ITEM_STATUS.label_pending],
        target=ORDER_ITEM_STATUS.label_printed,
        conditions=[]
    )
    def print_label(self):
        pass

    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.ready_to_ship, ORDER_ITEM_STATUS.label_pending,
                ORDER_ITEM_STATUS.label_printed],
        target=ORDER_ITEM_STATUS.in_transit,
        conditions=[]
    )
    def intransition(self):
        pass
    #
    def batch_id(self,batchid):
        self.batch = batchid
        self.save()
    def shipmentID(self,shipment_id):
        self.shipmentid = shipment_id
        self.save()


    @transition(
        'status',
        source=[
            ORDER_ITEM_STATUS.label_pending,
            ORDER_ITEM_STATUS.active,
            ORDER_ITEM_STATUS.ready_to_ship
        ],
        target=ORDER_ITEM_STATUS.label_failure
    )
    def failed_to_print_label(self, ex: BaseException):
        self.reason = str(ex)

    def can_be_canceled(self) -> bool:
        # NOTE: Only when the shipping label wasn't created,
        # the seller can cancel. We need to define condition here.
        if self.shipment and self.shipment.status not in [
                SHIPMENT_STATUS.created, SHIPMENT_STATUS.error,
                SHIPMENT_STATUS.label_generated,
                SHIPMENT_STATUS.label_pending]:
            return False
        else:
            return True

    @transaction.atomic()
    @transition(
        'status',
        source=[ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.in_transit,
                ORDER_ITEM_STATUS.label_printed],
        target=ORDER_ITEM_STATUS.canceled,
        conditions=[can_be_canceled]
    )
    def cancel(self, reason: str, raise_exception: bool = True):
        """
        - raise when the shipment is unable to be refunded
        """
        # NOTE: Refund shipment
        # If we let sellers print postage, we may not need to do the
        # followings. So cancel can be done before printing label.
        # But enabled this for now.
        # We should determine if this is required or not.
        try:
            shipment = self.shipment
            if shipment.can_refund:
                shipment.refund()
        except Shipment.DoesNotExist:
            # NOTE: shipment wasn't created yet.
            pass
        # EasyPostUtils.refund_shipment(self.shipment.easypost_shipment_id)

        # NOTE: Refund the corresponding payment intent partially

        if not settings.UNITTEST_MODE:
            stripe.Refund.create(
                amount=int(self.bundle.buyer_price.amount * 100),
                payment_intent=self.order.payment_intent.id,
            )

            # TODO: Send email to the buyer with message(cancel reason)
            send_pepo_email(
                self.order.customer.user.email, 'seller_cancel_email',
                {
                    'listing_title': self.bundle.title,
                    'reason': reason,
                    'url': 'NOTHING HERE.'
                }
            )
