import os
import uuid
from typing import Optional, List, Dict
from datetime import timedelta
from collections import defaultdict
from decimal import Decimal

# django
from django.db import models, transaction
from django.core.cache import cache
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.db.models import JSONField
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django_fsm import FSMField, transition
from djstripe.enums import PaymentIntentStatus
from django.apps import apps

from model_utils import FieldTracker
# third party library
from celery.result import AsyncResult
from celery.worker.control import revoke
from taggit.managers import TaggableManager
from djmoney.money import Money
from sorl.thumbnail import (
    get_thumbnail, ImageField as SorlImageField
)

from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

# https://github.com/django-money/django-money
from djmoney.models.fields import MoneyField
from mptt.models import MPTTModel, TreeForeignKey

from app.constants.status import PRODUCT_STATUS, ORDER_ITEM_STATUS, BUNDLE_TYPES
from app.tasks.orders import release_fund_manually
#     remove_background_from_product_single_image
from app.models.base import AuthStampedModel
from app.utils.analytics import track_analytics


UserModelRef = get_user_model()


def get_upload_path(instance, filename):
    filename = f'{uuid.uuid4()}.{filename.split(".")[-1]}'
    return f'bundles/{filename}'


class BundleManager(models.manager.Manager):
    def get_all_purchased(self, current_user):
        return self.get_queryset().filter(purchased_by=current_user)


class ProductManager(models.manager.Manager):
    def get_all_published(self):
        return self.get_queryset()


class Bundle(TimeStampedModel, AuthStampedModel):
    _errors = defaultdict(list)

    STATUS_CHOICES = (
        (PRODUCT_STATUS.sold, _('sold')),
        (PRODUCT_STATUS.shipped, _('shipped')),
        (PRODUCT_STATUS.received, _('received')),
    )
    BUNDLE_TYPE_CHOICES = (
        (BUNDLE_TYPES.outgoing, _('outgoing')),
        (BUNDLE_TYPES.incoming, _('incoming')),
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(max_length=2000, blank=True, null=True)
    shipping_type = models.ForeignKey(
        'app.ShippingRate', on_delete=models.SET_NULL,
        null=True, blank=False, related_name='bundles',
        verbose_name=_('shipping type'))
    shipping_cost = MoneyField(
        max_digits=10, decimal_places=4,
        default_currency='USD', default=0
    )
    hidden = models.BooleanField(default=False)
    width = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name=_('width in cm'), default=10)
    height = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name=_('height in cm'), default=10)
    length = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(100)],
        verbose_name=_('length in cm'), default=10)
    weight = models.FloatField(
        validators=[MinValueValidator(1)],
        verbose_name=_('actual weight in kg'), default=1)

    tags = TaggableManager(blank=True)
    purchased_by = models.ForeignKey(
        UserModelRef, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchased_bundles")
    status = FSMField(
        choices=STATUS_CHOICES, default=PRODUCT_STATUS.sold)
    type = FSMField(
        choices=BUNDLE_TYPE_CHOICES, default=BUNDLE_TYPES.outgoing)
    status_changed = MonitorField(monitor='status')
    objects = BundleManager()

    def get_tags(self):
        """ names() is a django-taggit method, returning a ValuesListQuerySet
        (basically just an iterable) containing the name of each tag
        as a string
        """
        return self.tags.names()

    def __str__(self):
        return f'{self.title}'

    @property
    def tracking_details(self) -> Optional[List[Dict]]:
        if self.status not in [PRODUCT_STATUS.sold, PRODUCT_STATUS.received]:
            return None

        last_shipment = self.shipments()
        print(last_shipment)
        if last_shipment:
            return last_shipment[0].tracker.tracking_details
        return None

    @property
    def shipments(self):
        OrderItemModel = apps.get_model('app', 'OrderItem')
        try:
            order_item = OrderItemModel.objects.get(bundle=self)
        except:
            return None
        ShipmentModel = apps.get_model('app', 'Shipment')
        print(ShipmentModel)
        try:
            shipment = ShipmentModel.objects.filter(order_item=order_item)
        except Exception as e:
            print("Error due to this ", e)
            return []
        return shipment

    def can_be_sold(self) -> bool:
        return True

    def status_change(self) -> bool:
        return True

    @transition(
        field='status',
        source=[PRODUCT_STATUS.sold],
        target=PRODUCT_STATUS.shipped,
        conditions=[]
    )
    @transaction.atomic()
    def shifting_status(self):
        # NOTE: Don't need to create payment_intent or shipment here.
        pass

    @transition(
        field='status',
        source=[PRODUCT_STATUS.shipped],
        target=PRODUCT_STATUS.received,
        conditions=[]
    )
    @transaction.atomic()
    def received_bundle(self):
        # NOTE: Don't need to create payment_intent or shipment here.
        pass


class PublishedBundleModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=PRODUCT_STATUS.published)


class PublishedBundle(Bundle):
    class Meta:
        proxy = True
        verbose_name = _('published bundle')
        ordering = ('-modified',)

    objects = PublishedBundleModelManager()


class ReleasableBundleModelManager(models.Manager):
    def get_queryset(self):
        from_time = now() - timedelta(
            days=settings.MANUAL_FUND_RELEASE_TIMEOUT)
        return super().get_queryset().filter(
            order_item__shipment__tracker__status='delivered',
            order_item__shipment__tracker__updated_at__lt=from_time,
            order_item__status=ORDER_ITEM_STATUS.in_transit
            # order_item__order__payment_intent__status=PaymentIntentStatus.
            # requires_confirmation,
        ).distinct()

    def send_release_message_to_celery(self):
        for instance in self.all():
            instance.release_fund()


class ReleasableBundle(Bundle):
    objects = ReleasableBundleModelManager()

    class Meta:
        proxy = True
        verbose_name = _('releasable bundle')

    def release_fund(self):
        release_fund_manually.delay(
            self.payments.filter(
                payment_intent__status=PaymentIntentStatus.
                requires_confirmation
            ).last().payment_intent.id)


class BG_REMOVAL_STATUS:
    to_do = 't'
    pending = 'p'
    in_progress = 'i'
    done = 'd'
    failed = 'f'


class Product(TimeStampedModel, AuthStampedModel):
    GENDER_CHOICES = (
        ('girl', 'Girl'),
        ('boy', 'Boy'),
        ('neutral', 'Neutral'),
    )
    QUALITY_CHOICES = (
        ('nwt', 'New With Tag'),
        ('nwot', 'New Without Tag'),
        ('excellent', 'Excellent Used'),
        ('good', 'Good Used'),
        ('play', 'Play'),
    )
    BG_REMOVAL_STATUS_CHOICES = (
        (BG_REMOVAL_STATUS.to_do, _('to do')),
        (BG_REMOVAL_STATUS.pending, _('pending')),
        (BG_REMOVAL_STATUS.in_progress, _('in progress')),
        (BG_REMOVAL_STATUS.done, _('done')),
        (BG_REMOVAL_STATUS.failed, _('failed')),
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(null=True, blank=True, max_length=255)

    bundle = models.ForeignKey(
        Bundle, related_name='items', on_delete=models.SET_NULL,
        blank=True, null=True
    )
    front_image_large = SorlImageField(
        _('front image'), upload_to=get_upload_path,
        null=True, blank=True)
    back_image_large = SorlImageField(
        _('back image'), upload_to=get_upload_path,
        null=True, blank=True)
    gender = models.CharField(
        choices=GENDER_CHOICES, default='neutral', max_length=9)
    quality = models.CharField(
        choices=QUALITY_CHOICES, default='draft', max_length=9)
    brand = models.ForeignKey(
        'app.ProductBrand', on_delete=models.DO_NOTHING,
        related_name='products', blank=True, null=True
    )
    category = models.ForeignKey(
        'app.ProductCategory', on_delete=models.DO_NOTHING,
        related_name='products', null=True, blank=True
    )
    size = models.ForeignKey(
        'app.ProductSize', on_delete=models.DO_NOTHING,
        related_name='products', blank=True, null=True
    )
    created_by = models.ForeignKey(
        UserModelRef, on_delete=models.SET_NULL, null=True, blank=False,
        related_name="created_items")
    favourite = models.ManyToManyField(UserModelRef, related_name='favourites', blank=True)

    # Background removal scope
    bg_removal_task_uuid = models.UUIDField(
        blank=True, null=True, verbose_name=_('background removal task id'))
    bg_removed_front_image_large = SorlImageField(
        _('front image without background'), upload_to=get_upload_path,
        null=True, blank=True)
    bg_removed_back_image_large = SorlImageField(
        _('back image without background'), upload_to=get_upload_path,
        null=True, blank=True)
    bg_removal_status = FSMField(
        choices=BG_REMOVAL_STATUS_CHOICES, default=BG_REMOVAL_STATUS.to_do)
    bg_removal_details = JSONField(default=None, null=True, blank=True)
    bg_removed_at = models.DateTimeField(
        null=True, blank=True)
    objects = ProductManager()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        if not isinstance(self.bg_removal_details, dict):
            self.bg_removal_details = {}

        __mappings = {
            'front_source': 'bg_removed_front_image_large',
            'back_source': 'bg_removed_back_image_large',
        }
        for key, attr_name in __mappings.items():
            if key not in self.bg_removal_details:
                continue
            resized_filename = self.bg_removal_details[key]
            if os.path.isfile(resized_filename):
                setattr(
                    self,
                    attr_name,
                    ContentFile(
                        open(resized_filename, 'rb').read(),
                        os.path.basename(resized_filename)
                    ))
            else:
                del self.bg_removal_details[key]

        if self.pk:
            old = self.__class__.objects.get(pk=self.pk)
            changed_fields = []
            for field in self.__class__._meta.get_fields():
                field_name = field.name
                if getattr(old, field_name) != getattr(self, field_name):
                    changed_fields.append(field_name)
            kwargs['update_fields'] = changed_fields
        super().save(*args, **kwargs)

    @property
    def progress(self) -> str:
        mapping = dict(self.BG_REMOVAL_STATUS_CHOICES)
        # return mapping.get(self.bg_removal_status)
        return mapping[BG_REMOVAL_STATUS.done]

    def get_images_to_remove(self, new_images):
        current_set = set(self.images.values_list("id", flat=True))
        new_set = set(new_images)
        return current_set - new_set

    def detach_images(self, images):
        self.images.filter(pk__in=images).update(product=None)

    def detach_all_images(self):
        self.images.all().update(product=None)

    # @transition(
    #     'bg_removal_status',
    #     source=[
    #         BG_REMOVAL_STATUS.to_do, BG_REMOVAL_STATUS.done,
    #         BG_REMOVAL_STATUS.failed],
    #     target=BG_REMOVAL_STATUS.pending
    # )
    # def request_to_remove_background(self, raise_exception: bool = False):
    #     task = remove_background_from_product_images.apply_async(
    #         (self.pk, raise_exception), countdown=2)
    #     self.bg_removal_task_uuid = task.id

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.in_progress],
        target=BG_REMOVAL_STATUS.done
    )
    def finished_to_remove_background(self):
        pass

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.in_progress],
        target=BG_REMOVAL_STATUS.failed
    )
    def failed_to_remove_background(self, err: Exception):
        self.bg_removal_details = self.bg_removal_details or {}.update({
            'error': str(err)
        })

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.pending, BG_REMOVAL_STATUS.in_progress],
        target=BG_REMOVAL_STATUS.to_do
    )
    def cancel_background_removal(self):
        # NOTE: should revoke the task in pending or progress in this case.
        if self.bg_removal_task_uuid:
            revoke(self.bg_removal_task_uuid, terminate=True)

    @property
    def bg_removal_task_result(self) -> Optional[AsyncResult]:
        if self.bg_removal_task_uuid:
            return AsyncResult(self.bg_removal_task_uuid)
        else:
            return None

    @property
    def front_image_small(self) -> Optional[str]:
        # TODO: temporarily remove bg removal
        # if not self.bg_removed_front_image_large:
        #     return None
        # return get_thumbnail(
        #     self.bg_removed_front_image_large,
        #     settings.THUMBNAIL_SMALL_IMAGE_SIZE,
        #     crop='center', quality=99
        # ).url
        if not self.front_image_large:
            return None
        return get_thumbnail(
            self.front_image_large,
            settings.THUMBNAIL_SMALL_IMAGE_SIZE,
            crop='center', quality=99
        ).url

    @property
    def shipping_item_name(self) -> str:
        return "{pk}__{category}_{brand}_{gender}".format(
            pk=self.pk,
            category=self.category,
            brand=self.brand,
            gender=self.gender
        )

    @property
    def front_image_thumbnail(self) -> Optional[str]:
        if not self.bg_removed_front_image_large:
            return None
        return get_thumbnail(
            self.bg_removed_front_image_large,
            settings.THUMBNAIL_TINY_IMAGE_SIZE,
            crop='center', quality=99
        ).url

    @property
    def back_image_small(self) -> Optional[str]:
        # TODO: temporarily remove bg removal
        # if not self.bg_removed_back_image_large:
        #     return None
        # return get_thumbnail(
        #     self.bg_removed_back_image_large,
        #     settings.THUMBNAIL_SMALL_IMAGE_SIZE,
        #     crop='center', quality=99
        # ).url
        if not self.back_image_large:
            return None
        return get_thumbnail(
            self.back_image_large,
            settings.THUMBNAIL_SMALL_IMAGE_SIZE,
            crop='center', quality=99
        ).url

    def thumbnail(self) -> str:
        thumbnail_src = self.front_image_thumbnail \
            if self.front_image_thumbnail \
            else self.back_image_small
        if thumbnail_src:
            return mark_safe('<img src="%s" />' % thumbnail_src)
        else:
            return mark_safe('<br />')


class ProductImage(TimeStampedModel, AuthStampedModel):
    BG_REMOVAL_STATUS_CHOICES = (
        (BG_REMOVAL_STATUS.to_do, _('to do')),
        (BG_REMOVAL_STATUS.pending, _('pending')),
        (BG_REMOVAL_STATUS.in_progress, _('in progress')),
        (BG_REMOVAL_STATUS.done, _('done')),
        (BG_REMOVAL_STATUS.failed, _('failed')),
    )

    product = models.ForeignKey(
        'app.Product', related_name='images', on_delete=models.CASCADE, blank=True, null=True)

    image_large = SorlImageField(
        _('image large'), upload_to=get_upload_path,
        null=True, blank=True)

    created_by = models.ForeignKey(
        UserModelRef, on_delete=models.SET_NULL, null=True, blank=False,
        related_name="created_images")

    bg_removed_image_large = SorlImageField(
        _('background removed image large'), upload_to=get_upload_path,
        null=True, blank=True)

    bg_removal_status = FSMField(
        choices=BG_REMOVAL_STATUS_CHOICES, default=BG_REMOVAL_STATUS.to_do)

    bg_removal_task_uuid = models.UUIDField(
        blank=True, null=True, verbose_name=_('background removal task id'))

    bg_removed_at = models.DateTimeField(
        null=True, blank=True)

    bg_removal_details = JSONField(default=None, null=True, blank=True)

    @property
    def image_small(self):
        if not self.image_large:
            return None
        current_image = self.image_large

        if self.bg_removed_image_large:
            current_image = self.bg_removed_image_large

        return get_thumbnail(
            current_image,
            settings.THUMBNAIL_SMALL_IMAGE_SIZE,
            crop='center', quality=99
        ).url

    @property
    def image_thumbnail(self) -> Optional[str]:
        if not self.bg_removed_image_large:
            return None
        return get_thumbnail(
            self.bg_removed_image_large,
            settings.THUMBNAIL_TINY_IMAGE_SIZE,
            crop='center', quality=99
        ).url

    @property
    def status_cache_id(self):
        return f"bg_progress_{self.pk}"

    @property
    def progress(self) -> str:
        mapping = dict(self.BG_REMOVAL_STATUS_CHOICES)
        status = cache.get(self.status_cache_id)
        if status:
            return mapping.get(status)
        else:
            return mapping.get(self.bg_removal_status)

    def thumbnail(self) -> str:
        thumbnail_src = self.image_thumbnail \
            if self.image_thumbnail \
            else self.image_small
        if thumbnail_src:
            return mark_safe('<img src="%s" />' % thumbnail_src)
        else:
            return mark_safe('<br />')

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.to_do, BG_REMOVAL_STATUS.pending],
        target=BG_REMOVAL_STATUS.in_progress
    )
    def started_to_remove_background(self):
        cache.set(self.status_cache_id, BG_REMOVAL_STATUS.in_progress)

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.in_progress],
        target=BG_REMOVAL_STATUS.done
    )
    def finished_to_remove_background(self):
        cache.delete(self.status_cache_id)

    @transition(
        'bg_removal_status',
        source=[BG_REMOVAL_STATUS.in_progress],
        target=BG_REMOVAL_STATUS.failed
    )
    def failed_to_remove_background(self, err: Exception):
        self.bg_removal_details = self.bg_removal_details or {}.update({
            'error': str(err)
        })

    # def request_to_remove_background(self, raise_exception: bool = False):
    #     task = remove_background_from_product_single_image.apply_async(
    #         (self.pk, raise_exception), countdown=2)
        # self.bg_removal_task_uuid = task.i


class BundleReport(TimeStampedModel, AuthStampedModel):
    """ Bundle Report by User """

    reported_by = models.ForeignKey(
        UserModelRef,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    bundle = models.ForeignKey(
        Bundle,
        on_delete=models.CASCADE,
        related_name="reports"
    )

    reported = models.BooleanField(default=True)
    reason = models.TextField(max_length=10000, blank=True)

    def __str__(self):
        return f"{self.reported_by} {self.bundle}"


class BundleRating(TimeStampedModel, AuthStampedModel):
    """ Bundle ratings by User """

    rated_by = models.ForeignKey(
        UserModelRef,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    bundle = models.ForeignKey(
        Bundle,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1),
                    MaxValueValidator(5)])
    feedback = models.TextField(max_length=10000, blank=True)

    def __str__(self):
        return f"{self.rating} {self.bundle}"


class ProductCategory(MPTTModel, TimeStampedModel):
    """ Product Categories """
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="children")
    slug = models.SlugField(null=True, blank=True, max_length=255)

    def __str__(self):
        return f"{self.name}"

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        # unique_together = ('slug', 'parent')

    def save(self, *args, **kwargs):
        if not self.id or not self.slug:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        if not self.title:
            self.title = self.name
        super(ProductCategory, self).save(*args, **kwargs)


class ThingPriority(models.IntegerChoices):
    LOW = 0, 'Pending'
    NORMAL = 1, 'Approved'
    HIGH = 2, 'Reject'


class ProductBrand(MPTTModel, TimeStampedModel):
    """ Product Brands"""
    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="children")
    slug = models.SlugField(null=True, blank=True, max_length=255)
    suggested = models.BooleanField(
        _('is suggested'), default=False)
    Approved = models.IntegerField(
        default=ThingPriority.LOW, choices=ThingPriority.choices, blank=True)

    Suggested_by = models.IntegerField(default=0, blank=True)

    def __str__(self):
        return f"{self.name}"

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Product Brand"
        verbose_name_plural = "Product Brands"

    def save(self, *args, **kwargs):

        if not self.pk:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        if not self.title:
            self.title = self.name
        super(ProductBrand, self).save(*args, **kwargs)


class SuggestedProductBrand(MPTTModel, TimeStampedModel):
    """ Product Brands"""
    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="children")
    slug = models.SlugField(null=True, blank=True, max_length=255)
    suggested = models.BooleanField(
        _('is suggested'), default=False)

    def __str__(self):
        return f"{self.name}"

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Suggested Product Brand"
        verbose_name_plural = "Suggested Product Brands"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        if not self.title:
            self.title = self.name
        super(SuggestedProductBrand, self).save(*args, **kwargs)


class ProductSize(MPTTModel, TimeStampedModel):
    """ Product Sizes"""
    name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="children")
    slug = models.SlugField(null=True, blank=True, max_length=255)

    def __str__(self):
        return f"{self.name}"

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Product Size"
        verbose_name_plural = "Product Sizes"

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            self.slug = slugify(self.name)
        if not self.title:
            self.title = self.name
        super(ProductSize, self).save(*args, **kwargs)
