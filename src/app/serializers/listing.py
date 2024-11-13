from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
import stripe
from djstripe import models

from app.models.product import (
    PRODUCT_STATUS, Bundle, Product,
    BundleReport, BundleRating,
    ProductCategory, ProductBrand,
    ProductSize, ProductImage
)
from app.paginations import StandardResultsSetPagination
from app.serializers.tag import ByndeTagListSerializer
from app.utils.address import Address, validate_address
from app.serializers.user import ProfileSerializer
from app.serializers.shipment import ShipmentSerializer
from app.utils import (
    Base64ImageField,
    inline_serializer,
    RecursiveFieldSerializer
)
from app.tasks import send_email, send_pepo_email


class TagsField(serializers.Field):
    """ custom field to serialize/deserialize TaggableManager instances.
    """

    def to_representation(self, value):
        """ in drf this method is called to convert a custom datatype into a primitive,
        serializable datatype.

        In this context, value is a plain django queryset containing a list of
        strings. This queryset is obtained thanks to get_tags() method on the
        Task model.

        Drf is able to serialize a queryset, hence we simply return it without
        doing nothing.
        """
        return value

    def to_internal_value(self, data):
        """ this method is called to restore a primitive datatype into its internal
        python representation.

        This method should raise a serializers.ValidationError
        if the data is invalid.
        """
        return data


class ProductCategoryCreateSerializer(serializers.ModelSerializer):
    """ Product Category Create serializer """
    class Meta:
        model = ProductCategory
        fields = "__all__"


class ProductCategorySerializer(serializers.ModelSerializer):
    """ Product Category Get serializer """
    children = RecursiveFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "slug", "title", "children"]


class ProductCategoryShortSerializer(serializers.ModelSerializer):
    """ Product Category Get serializer without children"""

    class Meta:
        model = ProductCategory
        fields = ["id", "name"]


class ProductBrandCreateSerializer(serializers.ModelSerializer):
    """ Product Brand Create serializer """

    class Meta:
        model = ProductBrand
        fields = ('id', 'name', 'title', 'parent', 'slug')

        extra_kwargs = {
            'slug': {'read_only': True},
            'parent': {'required': False}
        }

    @property
    def current_user(self):
        return self.context['request'].user

    def validate(self, attrs):

        attrs = super().validate(attrs)
        name = attrs['name']
        if ProductBrand.objects.filter(name=name).exists():
            raise serializers.ValidationError({'name': 'Already exists.'})

        attrs['Suggested_by'] = self.current_user.pk

        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.suggested = True
        instance.save()
        user = get_user_model().objects.get(email=self.current_user.email)
        user.send_suggested_brands()
        print('-------------Admin notify mail sent successfully -------------------- ')
        return instance


class ProductBrandSerializer(serializers.ModelSerializer):
    """ Product Brand Get serializer """
    children = RecursiveFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProductBrand
        fields = ["id", "name", "children", "slug", "title", "suggested"]


class ProductBrandShortSerializer(serializers.ModelSerializer):
    """ Product Brand Get serializer without children """

    class Meta:
        model = ProductBrand
        fields = ["id", "name"]


class ProductSizeCreateSerializer(serializers.ModelSerializer):
    """ Product Size Create serializer """
    class Meta:
        model = ProductSize
        fields = "__all__"


class ProductSizeSerializer(serializers.ModelSerializer):
    """ Product Size Get serializer """
    children = RecursiveFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSize
        fields = ["id", "name", "children", "slug", "title"]


class ProductSizeShortSerializer(serializers.ModelSerializer):
    """ Product Size Get serializer without children """

    class Meta:
        model = ProductSize
        fields = ["id", "name"]


class ProductImageSerializer(serializers.ModelSerializer):
    image_large = Base64ImageField(
        max_length=None, use_url=True, required=False)

    bg_removed_image_large = Base64ImageField(
        max_length=None, use_url=True, required=False)

    id = serializers.IntegerField(required=False)

    # id = serializers.PrimaryKeyRelatedField(
    #     queryset=ProductImage.objects.all(), required=False)

    def validate(self, attrs):
        product = self.context.get('product')
        request = self.context.get('request')
        listing_pk = request.parser_context['kwargs'].get('pk')
        if not listing_pk:
            listing_pk = request.data.get('pk')
        if 'id' in attrs:
            get_object_or_404(ProductImage, Q(pk=attrs['id']) & (
                Q(product=None) | Q(product__id=listing_pk)))
        attrs['created_by'] = self.context.get('request').user
        if product:
            attrs["product"] = product
        else:
            attrs['product_id'] = listing_pk
        return attrs

    def create(self, validated_data):
        if 'id' in validated_data:
            _id = validated_data.pop("id")
            listing_image = ProductImage.objects.filter(id=_id)
            listing_image.update(**validated_data)
            return listing_image.first()
        else:
            return super().create(validated_data)

    class Meta:
        model = ProductImage
        fields = ("image_large", "id", "image_small", "bg_removed_image_large")


class ProductImageRetrivalSerializer(ProductImageSerializer):
    image_large = serializers.SerializerMethodField()

    def get_image_large(self, obj):
        if obj.bg_removed_image_large:
            return obj.bg_removed_image_large
        return obj.image_large


class BundleSerializer(serializers.ModelSerializer):
    queryset = Bundle.objects.all()

    # NOTE: What's this for?
    # filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    # filterset_class = BundleFilter
    # ----------------------

    ordering_fields = ('buyer_price', 'created')
    ordering = ('-created')
    pagination_class = StandardResultsSetPagination

    def get_image(obj, x):
        return None

    tags = ByndeTagListSerializer()
    items = inline_serializer(many=True, fields={
        'id': serializers.IntegerField(),
        'front_image_thumbnail': serializers.CharField(),
        'front_image_small': serializers.CharField(),
        'front_image_large': serializers.ImageField(use_url=True),
        'back_image_small': serializers.CharField(),
        'back_image_large': serializers.ImageField(use_url=True),
        'gender': serializers.CharField(),
        'quality': serializers.CharField(),
        'brand': ProductBrandShortSerializer(),
        'category': ProductCategoryShortSerializer(),
        'size': ProductSizeShortSerializer(),
        'images': ProductImageSerializer(many=True)
    })

    class Meta:
        model = Bundle
        fields = ('id', 'title', 'description', 'slug', 'status',
                  'buyer_price', 'tags', 'items')


class BundlePurchaseSerializer(serializers.ModelSerializer):
    street_address = serializers.CharField(
        write_only=True, required=True, help_text=_('delivery address'))
    city = serializers.CharField(
        write_only=True, required=True, help_text=_('city'))
    postal_code = serializers.CharField(
        write_only=True, required=True, help_text=_('postal code'))
    state = serializers.CharField(
        write_only=True, required=True, help_text=_('state'))

    token_id = serializers.CharField(
        write_only=True, required=False,
        help_text=_(
            'Card validate token provided by stripe. ' +
            'It can be used instead of card information.'))

    card_number = serializers.CharField(write_only=True, required=False)
    exp_year = serializers.IntegerField(write_only=True, required=False)
    exp_month = serializers.IntegerField(write_only=True, required=False)
    cvc = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Bundle
        fields = (
            'state', 'city', 'postal_code', 'street_address',
            'card_number', 'exp_year',
            'exp_month', 'cvc', 'token_id', )

    @property
    def current_user(self):
        return self.context['request'].user

    def validate(self, attrs):
        errors = {}
        attrs = super().validate(attrs)
        attrs['purchased_by'] = self.current_user

        if self.instance.status == PRODUCT_STATUS.sold:
            errors.update({
                'status': _('This listing already sold.')})
        elif self.instance.status != PRODUCT_STATUS.published:
            errors.update({
                'status': _('This listing can not be sold.')})

        # Validate shipping address
        address, _addr_errors = validate_address(
            attrs.pop('state', ''),
            attrs.pop('city', ''),
            attrs.pop('postal_code', ''),
            attrs.pop('street_address', ''),
        )
        if isinstance(address, Address):
            attrs['state'] = address.state
            attrs['city'] = address.city
            attrs['postal_code'] = address.postal_code
            attrs['street_address'] = address.street_address
        else:
            errors.update(_addr_errors)

        card_number = attrs.pop('card_number', None)
        exp_year = attrs.pop('exp_year', None)
        exp_month = attrs.pop('exp_month', None)
        cvc = attrs.pop('cvc', None)
        token_id = attrs.pop('token_id', None)

        if not self.current_user.customer:
            self.current_user.get_or_create_stripe_customer()

        if not self.current_user.customer.default_source:
            if token_id:
                try:
                    card_object = stripe.Customer.create_source(
                        self.current_user.customer.id, source=token_id)
                    attrs['card_id'] = models.Card.\
                        _get_or_create_from_stripe_object(card_object).id
                except Exception as e:
                    errors.update({
                        'token_id': str(e)
                    })
            elif all(not item for item in [
                card_number, exp_year, exp_month, cvc
            ]):
                errors.update({
                    'token_id': _('token_id or card information is required.')
                })
            else:
                if not card_number:
                    errors.update({
                        'card_number': _('card_number is required.')
                    })
                if not exp_year:
                    errors.update({
                        'exp_year': _('exp_year is required.')
                    })
                if not exp_month:
                    errors.update({
                        'exp_month': _('exp_month is required.')
                    })
                if not cvc:
                    errors.update({
                        'cvc': _('cvc is required.')
                    })

                if not errors:
                    token = stripe.Token.create(
                        card={
                            "number": card_number,
                            "exp_month": exp_month,
                            "exp_year": exp_year,
                            "cvc": cvc,
                        })
                    try:
                        attrs['card_id'] = stripe.Customer.create_source(
                            self.current_user.customer.id, source=token.id
                        )
                    except Exception as e:
                        errors.update({
                            'card_number': str(e)
                        })
        else:
            attrs['card_id'] = self.current_user.customer.default_source.id

        if errors:
            raise serializers.ValidationError(errors)

        return super().validate(attrs)

    def update(self, instance, validated_data):
        card_id = validated_data.pop('card_id')
        street_address = validated_data.pop('street_address')
        city = validated_data.pop('city')
        postal_code = validated_data.pop('postal_code')
        state = validated_data.pop('state')
        if instance.order_item.status:
            pass
        else:
            if instance.can_be_sold:
                try:
                    instance.sold(
                        self.current_user.customer.id,
                        card_id,
                        self.current_user.get_full_name(),
                        self.current_user.phone,
                        street_address,
                        city,
                        postal_code,
                        state,
                        street_address_2=None)
                    instance.purchased_by = self.current_user
                    instance.save()
                    return instance
                except Exception as e:
                    raise serializers.ValidationError(e)
            else:
                raise serializers.ValidationError(instance._errors)


class BundleTrackerSerializer(serializers.ModelSerializer):
    def validate(self, attrs) -> dict:
        if self.instance.status not in [
                PRODUCT_STATUS.sold, PRODUCT_STATUS.receive]:
            raise serializers.ValidationError(_(
                'Can not check tracking details'))

    class Meta:
        model = Bundle
        fields = ('tracking_details', )


class BundleCheckoutSerializer(serializers.ModelSerializer):
    listing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True, help_text=_('Bundle Ids'))

    class Meta:
        model = Bundle
        fields = ('listing_ids',)

    @property
    def current_user(self):
        return self.context['request'].user


class BundleReceiveSerializer(serializers.ModelSerializer):
    status = serializers.HiddenField(default=PRODUCT_STATUS.published)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not self.instance.order_item.can_be_received():
            raise serializers.ValidationError(self.instance._errors)

        return attrs

    def update(self, instance, validate):
        instance.order_item.receive()
        instance.received_listing()
        instance.order_item.save()
        instance.save()
        return instance

    class Meta:
        model = Bundle
        fields = ('status', )


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'id', 'title',
            'gender',
            'quality',
            'brand'
        )


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    brand = serializers.CharField(
        source='brand.name', read_only=True)
    category = serializers.CharField(
        source='category.name', read_only=True)
    size = serializers.CharField(
        source='size.name', read_only=True)
    quality = serializers.CharField(source='get_quality_display', read_only=True) 



    def validate(self, attrs):
        request = self.context.get('request')
        listing_pk = request.parser_context['kwargs'].get('listing_pk')
        if listing_pk:
            listing = Bundle.objects.get(pk=listing_pk)
        else:
            pk = request.parser_context['kwargs'].get('pk')
            instance = self.Meta.model.objects.get(pk=pk)
            listing = instance.listing

        if listing.status not in ['published']:
            raise serializers.ValidationError(
                'Status of associated listing should be published')
        return super().validate(attrs)

    class Meta:
        model = Product
        fields = (
            'pk', 'title',
            'gender', 'quality', 'brand', 'category', 'size',
            'images', 'favourite'
        )
        read_only_fields = ('pk', 'title',
                            'gender', 'quality', 'brand', 'category', 'size',
                            'images', 'favourite'
                            )


class SellingItemSerializer(ProductSerializer):
    class Meta(ProductSerializer.Meta):
        ref_name = 'SellingItem'


class SellingItemCreateSerializer(SellingItemSerializer):
    images = ProductImageSerializer(many=True, required=False)

    @property
    def _request(self):
        return self.context.get('request')

    @property
    def current_user(self):
        return self._request.user

    def validate(self, attrs):
        kwargs = self._request.parser_context['kwargs']
        if 'listing_id' not in attrs:
            attrs['listing_id'] = kwargs.get('listing_pk')
        attrs['created_by'] = self.current_user
        return super().validate(attrs)

    # def update(self, validated_data):
    #     if 'images' in validated_data:
    #         del validated_data['images']
    #     return super().update(validated_data)

    def create(self, validated_data):
        images = validated_data.pop("images", None)

        instance = Product.objects.create(**validated_data)

        if images:
            context = {
                "request": self._request,
                "product": instance
            }
            ser = ProductImageSerializer(
                data=images, context=context, many=True)
            ser.is_valid(raise_exception=True)
            ser.save()
            # for image in images:
            #     params = {
            #         "product": instance,
            #         "created_by": validated_data.get("created_by", None),
            #         **image
            #     }
            #     ProductImage.objects.create(**params)

        return instance

    def save(self, **kwargs):
        return super().save(**kwargs)

    class Meta(SellingItemSerializer.Meta):
        ref_name = 'SellingItemCreate'
        read_only_fields = (
            'front_image_small', 'back_image_small',
            'front_image_thumbnail',
        )


class SellingItemDetailSerializer(serializers.ModelSerializer):
    front_image_thumbnail = serializers.CharField()
    front_image_small = serializers.CharField()

    images = ProductImageSerializer(many=True)

    @property
    def _request(self):
        return self.context.get('request')

    def filter_images_id(self, images):
        return list(
            map(
                lambda each: each.get("id"),
                filter(lambda _each: _each.get("id"), images)
            )
        )

    def update(self, instance, validated_data):
        if 'images' in validated_data:
            images = validated_data.pop("images")
            if len(images):
                # Get all the IDs for images
                updated_images = self.filter_images_id(images)

                # Find the Ids of images to remove
                images_to_remove = instance.get_images_to_remove(
                    updated_images)

                # Detach images
                instance.detach_images(images_to_remove)

                # Create New Images
                context = {
                    "request": self._request,
                    "product": instance
                }
                ser = ProductImageSerializer(
                    data=images, context=context, many=True)
                ser.is_valid(raise_exception=True)
                ser.save()
            else:
                instance.detach_all_images()

        return super().update(instance, validated_data)

    class Meta:
        model = Product
        ref_name = 'SellingApiItemRetrieveUpdateDestroy'
        fields = '__all__'


class SellingItemBackgroundRemovalStatus(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('progress',)
        read_only_fields = ('progress',)


class SellingImageBackgroundRemovalStatus(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('progress', )
        read_only_fields = ('progress',)


class SellingListSerializer(serializers.ModelSerializer):
    tags = ByndeTagListSerializer()
    items = inline_serializer(many=True, fields={
        'id': serializers.IntegerField(),
        'front_image_thumbnail': serializers.CharField(),
        'front_image_small': serializers.CharField(),
        'front_image_large': serializers.ImageField(),
        'back_image_large': serializers.ImageField(),
        'back_image_small': serializers.CharField(),
        'bg_removal_status': serializers.CharField(),
        'gender': serializers.CharField(),
        'quality': serializers.CharField(),
        'brand': ProductBrandShortSerializer(),
        'category': ProductCategoryShortSerializer(),
        'size': ProductSizeShortSerializer(),
        'images': ProductImageSerializer(many=True)
    })

    class Meta:
        model = Bundle
        fields = ('pk', 'title', 'status', 'shipping_cost', 'shipping_type',
                  'description', 'seller_price', 'tags', 'items', 'seller_notes')


class SellingDetailSerializer(serializers.ModelSerializer):
    tags = TagsField(source="get_tags")
    shipments = ShipmentSerializer(many=True, read_only=True)

    class Meta:
        model = Bundle
        ref_name = 'SellingApiRetrieveUpdateDestroy'
        fields = (
            'pk', 'title', 'tags', 'status', 'description',
            'seller_price', 'shipping_type',
            'shipping_cost', 'shipments', 'created_by', 'seller_notes')

    def update(self, instance, validated_data):
        tags = validated_data.pop(
            'get_tags') if 'get_tags' in validated_data else None
        instance = super().update(instance, validated_data)
        if tags:
            instance.tags.set(tags)
        return instance


class SellingPublishSerializer(serializers.ModelSerializer):
    status = serializers.HiddenField(default=PRODUCT_STATUS.published)

    class Meta:
        model = Bundle
        fields = ('status', )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Validate seller's address
        if not self.instance.created_by.is_stripe_connected:
            raise serializers.ValidationError(_(
                'Your stripe account was not connected yet.'))
        if self.instance.status == PRODUCT_STATUS.published:
            raise serializers.ValidationError(_("Already published."))
        elif self.instance.status == PRODUCT_STATUS.sold:
            raise serializers.ValidationError(_("Already sold out."))
        elif not self.instance.can_publish():
            raise serializers.ValidationError(self.instance._errors)
        return attrs

    def save(self):
        self.instance.publish()
        self.instance.save()
        return self.instance


class SellingCreateSerializer(serializers.ModelSerializer):
    tags = ByndeTagListSerializer()
    items = SellingItemCreateSerializer(many=True, required=False)

    class Meta:
        model = Bundle
        ref_name = 'Selling'
        fields = (
            'id', 'title', 'tags', 'description',
            'seller_price', 'shipping_type', 'items', 'created_by', 'seller_notes')

    def validate(self, attrs):
        attrs['created_by'] = self.context.get('request').user
        return attrs

    def create(self, validated_data):
        items = validated_data.pop('items', [])
        instance = super().create(validated_data)
        for item in items:
            Product.objects.create(listing=instance, **item)
        return instance


class BundleReportCreateSerializer(serializers.ModelSerializer):
    reported_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = BundleReport
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=BundleReport.objects.all(),
                fields=['reported_by', 'listing'],
                message="This Item has already been reported."
            )
        ]


class BundleReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = BundleReport
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method.lower() == 'get':
            fields['reported_by'] = ProfileSerializer(
                read_only=True,
                context=self.context
            )
            fields['listing'] = ProductDetailSerializer(
                read_only=True,
                context=self.context
            )
        return fields


class BundleRatingCreateSerializer(serializers.ModelSerializer):
    """ Bundle Rating Create serializer """
    rated_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = BundleRating
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=BundleRating.objects.all(),
                fields=['rated_by', 'listing'],
                message="This Item has already been rated."
            )
        ]


class BundleRatingSerializer(serializers.ModelSerializer):
    """ Bundle Rating Get serializer """

    class Meta:
        model = BundleRating
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method.lower() == 'get':
            fields['rated_by'] = ProfileSerializer(
                read_only=True,
                context=self.context
            )
            fields['listing'] = BundleDetailSerializer(
                read_only=True,
                context=self.context
            )
        return fields
