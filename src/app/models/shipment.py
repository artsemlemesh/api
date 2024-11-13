from datetime import datetime, timedelta
from typing import Union, Optional

# django
from django.apps import apps
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_fsm import FSMField
from django.db.models import JSONField

# https://django-model-utils.readthedocs.io/en/latest/fields.html
from model_utils.fields import MonitorField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from app.utils.epost import easypost

from app.constants.status import PRODUCT_STATUS, ORDER_ITEM_STATUS
from app.utils.epost import EasyPostUtils


class ShippingRate(TimeStampedModel):
    type = models.CharField(
        max_length=64, unique=True, verbose_name=_('rate type'))
    rate = models.FloatField(
        _('rate'), validators=[MinValueValidator(0.0)]
    )

    class Meta:
        verbose_name = _('shipping rate')
        ordering = ('rate',)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)
            if old.rate != self.rate:
                for bundle in self.listings.filter(
                        status=PRODUCT_STATUS.published).all():
                    bundle.shipping_cost = self.rate
                    bundle.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.type

    def __repr__(self):
        return f"<ShippingRate({self.pk}):{self.type}(${self.rate})>"


class SHIPMENT_STATUS:
    created = 'created'
    label_pending = 'label_pending'
    label_generated = 'label_generated'
    in_transit = 'in-transit'
    received = 'received'
    error = 'error'


SHIPMENT_TYPE = Choices('purchase', 'return')


class ShipmentModelManager(models.Manager):
    def get_or_create_from_easypost_object(
            self, order_item, easypost_object: easypost.shipment
    ):
        return self.get_or_create(
            easypost_shipment_id=easypost_object.id,
            order_item=order_item,
            defaults={
                'shipment_type': SHIPMENT_TYPE.purchase,
                'status': SHIPMENT_STATUS.label_generated,
                'courier_id': easypost_object.selected_rate.id,
                'label_url': easypost_object.postage_label.label_url,
            }
        )

    def update_data_from_easypost(
            self, order_item, easypost_object: easypost.shipment
    ):
        if easypost_object.status == 'delivered':
            status = SHIPMENT_STATUS.received,
        else:
            status = easypost_object.status
        # elif easypost_object.status == ''
        return self.get_or_create(
            easypost_shipment_id=easypost_object.id,
            order_item=order_item,

            defaults={
                'shipment_type': SHIPMENT_TYPE.purchase,
                'status': status,
                'courier_id': easypost_object.selected_rate.id,
                'label_url': easypost_object.postage_label.label_url,
            }
        )


class Shipment(TimeStampedModel):
    STATUS_CHOICES = (
        (SHIPMENT_STATUS.created, _('created')),
        (SHIPMENT_STATUS.label_pending, _('label pending')),
        (SHIPMENT_STATUS.label_generated, _('label generated')),
        (SHIPMENT_STATUS.in_transit, _('in transit')),
        (SHIPMENT_STATUS.received, _('received')),
        (SHIPMENT_STATUS.error, _('error')),
    )

    order_item = models.OneToOneField(
        'app.OrderItem', on_delete=models.SET_NULL, null=True,
        related_name='shipment')
    shipment_type = models.CharField(
        choices=SHIPMENT_TYPE, max_length=8)

    status = FSMField(
        choices=STATUS_CHOICES, default=SHIPMENT_STATUS.created)
    status_changed = MonitorField(monitor='status')
    easypost_shipment_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True)
    courier_id = models.CharField(
        max_length=255, null=True, blank=True)
    label_url = models.URLField(
        verbose_name=_('label url'), null=True, blank=True)

    objects = ShipmentModelManager()

    def __str__(self):
        return f'{self.easypost_shipment_id}'

    def retrieve_label_url_from_easypost(self):
        shipment = EasyPostUtils.retrieve_shipment(self.easypost_shipment_id)
        self.label_url = shipment.postage_label.label_url

    def create_pickup(
            self,
            min_datetime: Union[datetime, str],
            max_datetime: Union[datetime, str],
            instructions: str
    ):
        PickUpModelRef = apps.get_model('app', 'Pickup')
        
        # this block fixes this error: Original error:
        #  Object of type datetime is not JSON serializable
        if isinstance(min_datetime, datetime):
            min_datetime = min_datetime.isoformat()
        if isinstance(max_datetime, datetime):
            max_datetime = max_datetime.isoformat()
        
        return PickUpModelRef.objects.create(
            self, min_datetime, max_datetime, instructions)

    def cancel_pickup(self):
        if not hasattr(self, 'pickup'):
            raise Exception("Pickup was not created for this shipment yet.")

        PickUpModelRef = apps.get_model('app', 'Pickup')
        EasyPostUtils.cancel_pickup(self.pickup.easypost_id)
        PickUpModelRef.objects.filter(pk=self.pickup.pk).delete()

    @property
    def can_refund(self) -> bool:
        return (
                self.status == SHIPMENT_STATUS.label_generated and
                (
                        settings.UNITTEST_MODE or (
                        timezone.now() > timedelta(days=15) + self.status_changed
                )
                )
        )

    def refund(self) -> bool:
        if not self.can_refund:
            return False

        # If a pickup was made for this shipment, the pickup should be canceled as well.
        if hasattr(self, 'pickup'):
            self.cancel_pickup()

        response = EasyPostUtils.refund_shipment(self.easypost_shipment_id)
        # TODO: do something with response here.
        return response.get('refund_status') == 'submitted'


class ShipmentTracker(models.Model):
    shipment = models.OneToOneField(
        Shipment, on_delete=models.CASCADE, related_name='tracker')
    easypost_id = models.CharField(
        max_length=48, verbose_name=_('easypost tracker id'))
    tracking_code = models.CharField(
        max_length=48, null=True, blank=True)
    tracking_url = models.CharField(
        max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, verbose_name=_('status'))
    signed_by = models.CharField(
        max_length=40, verbose_name=_('signed by'), null=True, blank=True)
    est_delivery_date = models.DateTimeField(
        verbose_name=_('estimated delivery date'), null=True, blank=True)
    tracking_details = JSONField(verbose_name=_('tracking details'))
    created_at = models.DateTimeField(verbose_name=_('created at'))
    updated_at = models.DateTimeField(verbose_name=_('updated at'))

    class Meta:
        verbose_name = _('tracker')
        verbose_name_plural = _('trackers')
        ordering = ('-updated_at',)

    @classmethod
    @transaction.atomic()
    def _update_or_create_from_easypost_object(
            cls, easypost_tracker: easypost.tracker
    ):
        shipment = Shipment.objects.get(
            easypost_shipment_id=easypost_tracker.shipment_id)
        instance, created = cls.objects.update_or_create(
            shipment=shipment,
            easypost_id=easypost_tracker.id,
            tracking_code=easypost_tracker.tracking_code,
            defaults={
                'status': easypost_tracker.status,
                'signed_by': easypost_tracker.signed_by,
                'est_delivery_date': easypost_tracker.est_delivery_date,
                'tracking_details': [
                    item.to_dict() for item
                    in easypost_tracker.tracking_details],
                'created_at': easypost_tracker.created_at,
                'tracking_url' : easypost_tracker.public_url,
                'updated_at': easypost_tracker.updated_at,
            }
        )
        if instance.shipment.order_item.status == 'd' :
            print('Order Item received')
            pass
        else:
            if instance.status == 'delivered':
                instance.shipment.order_item.bundle.status = PRODUCT_STATUS.shipped
                instance.shipment.order_item.bundle.save()
            else:
                instance.shipment.order_item.status = ORDER_ITEM_STATUS.in_transit
            instance.shipment.order_item.save()

        return instance, created


class PICKUP_STATUS:
    unknown = 'unknown'
    scheduled = 'scheduled'
    canceled = 'canceled'


class PickupModelManager(models.Manager):
    def create(
            self,
            shipment: Shipment,
            min_datetime: Union[datetime, str],
            max_datetime: Union[datetime, str],
            instructions: Optional[str],
            *args, **kwargs
    ):
        pickup = EasyPostUtils.create_and_buy_pickup(
            shipment.easypost_shipment_id,
            # print("Shipment Address Verified",shipment.order_item.bundle.created_by.shipping_address),
            shipment.order_item.bundle.created_by.shipping_address,
            min_datetime, max_datetime,
            reference=f"SHIPMENT__{shipment.pk}",
            instructions=instructions
        )
        if pickup.status == PICKUP_STATUS.unknown: 
            pickup.buy()
        return super().create(
            shipment=shipment,
            easypost_id=pickup.id,
            min_datetime=min_datetime,
            max_datetime=max_datetime,
            status=pickup.status,
            *args, **kwargs
        )

class PickUp(TimeStampedModel):
    STATUS_CHOICES = (
        (PICKUP_STATUS.unknown, _('unknown')),
        (PICKUP_STATUS.scheduled, _('scheduled')),
        (PICKUP_STATUS.canceled, _('canceled')),
    )

    shipment = models.OneToOneField(
        Shipment, on_delete=models.CASCADE, related_name='pickup')
    easypost_id = models.CharField(
        max_length=48, verbose_name=_('easypost pickup id'))
    min_datetime = models.DateTimeField(_('min datetime'))
    max_datetime = models.DateTimeField(_('max datetime'))
    status = FSMField(choices=STATUS_CHOICES, default=PICKUP_STATUS.unknown)

    objects = PickupModelManager()

    class Meta:
        verbose_name = _('pickup')
        ordering = ('-modified',)
