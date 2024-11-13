import datetime
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.utils.timezone import now

import factory

from djstripe.models import PaymentIntent

from app.models import (
    Listing, Product, ProductCategory,
    ProductBrand, ProductSize, ListingImage,
    ProductBrand, ProductSize,
    Order, OrderItem,
    ByndeCustomer, ShippingRate
)
from factory import fuzzy
from faker import Faker

from app.models.product import SuggestedProductBrand

fake = Faker()
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Create test user."""
    class Meta:
        model = User

    password = fake.password()
    last_login = now()
    is_superuser = False
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = factory.LazyAttribute(
        lambda x: "{}.{}@example.com".format(x.first_name, x.last_name))
    is_staff = False
    is_active = True
    created_date = fuzzy.FuzzyDateTime(now() - datetime.timedelta(days=365))

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        """Add user as e member for `extracted` group,
        Usage:
            create managers group
            >>> group = GroupFactory.create(name='manager')
            >>> manager = UserFactory.create(groups=[group])
        """
        if not create:
            return

        if extracted:
            for group in extracted:
                self.groups.add(group)


class GroupFactory(factory.django.DjangoModelFactory):
    """Create test group."""
    class Meta:
        model = Group

    name = "manager"


class ShippingRateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ShippingRate
        django_get_or_create = ("type",)

    type = "FlatRatePaddedEnvelope"
    rate = 7.75


class ProductCategoryFactory(factory.django.DjangoModelFactory):
    """ Product category factory """
    class Meta:
        model = ProductCategory
        django_get_or_create = ["name"]
    name = fake.name()


class ProductBrandFactory(factory.django.DjangoModelFactory):
    """ Product brand factory """
    class Meta:
        model = ProductBrand
        django_get_or_create = ["name"]
    name = fake.name()

class SuggestedProductBrandFactory(factory.django.DjangoModelFactory):
    """ Product brand factory """
    class Meta:
        model = SuggestedProductBrand
        django_get_or_create = ["name"]
    name = fake.name()


class ProductSizeFactory(factory.django.DjangoModelFactory):
    """ Product Size factory """
    class Meta:
        model = ProductSize
        django_get_or_create = ["name"]
    name = fake.name()


class ListingFactory(factory.django.DjangoModelFactory):
    """Create test List."""
    class Meta:
        model = Listing

    title = fake.name()
    status = 'draft'
    description = fake.sentence()
    seller_price = "50"
    buyer_price = "50"
    shipping_cost = "25"
    platform_premium = "25"
    created_by = None
    # shipping_type = factory.SubFactory(ShippingRateFactory)

    def __init__(self, created_by):
        self.created_by = created_by

    @factory.post_generation
    def post_tags(self, create, extracted, **kwargs):
        self.tags.add(u'Tag 1', u'Tag 2')
        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ProductFactory(factory.django.DjangoModelFactory):
    """Create test Product."""
    class Meta:
        model = Product

    listing = factory.SubFactory(ListingFactory)
    front_image_large = factory.LazyAttribute(
        lambda _: ContentFile(
            factory.django.ImageField()._make_data(
                {'width': 1024, 'height': 768}
            ), 'example_front.jpg'
        )
    )
    back_image_large = factory.LazyAttribute(
        lambda _: ContentFile(
            factory.django.ImageField()._make_data(
                {'width': 1024, 'height': 768}
            ), 'example_back.jpg'
        )
    )
    gender = factory.fuzzy.FuzzyChoice(
        Product.GENDER_CHOICES, getter=lambda c: c[0])
    quality = factory.fuzzy.FuzzyChoice(
        Product.QUALITY_CHOICES, getter=lambda c: c[0])
    brand = factory.SubFactory(ProductBrandFactory)
    category = factory.SubFactory(ProductCategoryFactory)
    size = factory.SubFactory(ProductSizeFactory)
    created_by = factory.SubFactory(UserFactory)


class ListingImageFactory(factory.django.DjangoModelFactory):
    """Create test ListingImage"""
    class Meta:
        model = ListingImage
    
    @staticmethod
    def mark_image_processed(instance):
        instance.started_to_remove_background()
        instance.finished_to_remove_background()
        # instance.bg_removed_status = 'd'
        instance.bg_removed_image_large = instance.image_large
        instance.bg_removed_at = now()
        instance.save()

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        bg_removed = kwargs.pop('bg_removed', False)
        instance = super()._create(model_class, *args, **kwargs)
        
        if bg_removed:
            instance.bg_removed_status = 'd'
            instance.bg_removed_image_large = instance.image_large
            instance.bg_removed_at = now()
            instance.save()
        return instance

    def __init__(self, created_by=None, product=None, bg_removed=False):
        self.created_by = created_by
        self.product = product

    # @factory.post_generation
    # def mark_complete(self, create, extracted, **kwargs):
    #     bg_removed = kwargs.get('bg_removed')
    #     if bg_removed:
    #         self.bg_removed_status = 'd'
    #         self.bg_removed_image_large = self.image_large
    #         self.bg_removed_at = now()
    #         self.save()

    image_large = factory.LazyAttribute(
        lambda _: ContentFile(
            factory.django.ImageField()._make_data(
                {'width': 1024, 'height': 768}
            ), 'example_image.jpg'
        )
    )

    bg_removed_image_large = None
    created_by = None
    product = None
class PaymentIntentFactory(factory.django.DjangoModelFactory):
    id = "pq_" + fake.pystr(min_chars=24, max_chars=24)
    amount = 100
    amount_capturable = 0
    amount_received = 100
    livemode = False
    payment_method_types = ['card']

    class Meta:
        model = PaymentIntent


class ByndeCustomerFactory(factory.django.DjangoModelFactory):
    id = "cus_" + fake.pystr(min_chars=14, max_chars=14)
    balance = 0
    delinquent = False
    livemode = False

    class Meta:
        model = ByndeCustomer


class OrderFactory(factory.django.DjangoModelFactory):
    platform_order_id = uuid.uuid4()
    customer = factory.SubFactory(ByndeCustomerFactory)
    payment_intent = factory.SubFactory(PaymentIntentFactory)

    address_line_1 = fake.street_address()
    city = fake.city()
    state = fake.state()
    postal_code = fake.postcode()
    country = fake.country_code()
    phone = fake.phone_number()

    class Meta:
        model = Order


class OrderItemFactor(factory.django.DjangoModelFactory):
    order = factory.SubFactory(OrderFactory)
    listing = factory.SubFactory(ListingFactory)

    class Meta:
        model = OrderItem
