import uuid
from django.urls import reverse
from rest_framework import serializers

from app.constants.status import PRODUCT_STATUS
from app.models import Cart, CartItem, Listing
from app.serializers.listing import ListingSerializer


class CartItemListingSerializer(ListingSerializer):
    class Meta(ListingSerializer.Meta):
        # fields = ('id', 'title', 'status', 'buyer_price', 'tags', 'items')
        extra_kwargs = {
            'title': {'read_only': True},
            'status': {'read_only': True},
            'buyer_price': {'read_only': True},
            'tags': {'read_only': True},
            'items': {'read_only': True},
            "front_image_thumbnail": {'read_only': True},
            "front_image_small": {'read_only': True},
            "back_image_small": {'read_only': True}
        }


class CartItemCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        cart = self.context['request'].user.cart
        listing = attrs['listing']
        if cart.items.filter(listing=listing).count():
            raise serializers.ValidationError({
                'listing': 'Already exists in shopping cart.'})
        attrs['cart'] = cart
        return super().validate(attrs)

    class Meta:
        model = CartItem
        fields = ('listing', )


class CartItemDeleteSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        cart = self.context['request'].user.cart
        listing_pk = attrs['listing_pk']
        if not cart.items.filter(listing__pk=listing_pk).count():
            raise serializers.ValidationError({
                'listing_pk': 'Cart Item not found.'})
        return super().validate(attrs)

    class Meta:
        model = CartItem
        fields = ('listing', )


class CartItemSerializer(serializers.ModelSerializer):
    listing = CartItemListingSerializer()

    class Meta:
        model = CartItem
        fields = ('listing', )


class CartRetrieveSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ('items', )


class CartCheckoutSerializer(serializers.ModelSerializer):
    success_url = serializers.SerializerMethodField()
    failure_url = serializers.SerializerMethodField()

    def validate(self, attrs):
        cart = self.instance
        if not cart.items.count():
            raise serializers.ValidationError('Cart is empty.')
        return super().validate(attrs)

    def get_success_url(self, instance):
        url = instance.get_success_url()
        if url:
            return self.context['request'].build_absolute_uri(url)
        else:
            return None

    def get_failure_url(self, instance):
        url = instance.get_failure_url()
        if url:
            return self.context['request'].build_absolute_uri(url)
        else:
            return None

    class Meta:
        model = Cart
        fields = ('stripe_session_id', 'success_url', 'failure_url', )
        extra_kwargs = {
            'stripe_session_id': {'read_only': True},
            'success_url': {'read_only': True},
            'failure_url': {'read_only': True},
        }

    def update(self, instance, validated_data):
        order_id = str(uuid.uuid4())
        success_url = self.context['request'].build_absolute_uri(
            reverse(
                'app:checkout-success-view',
                kwargs={'order_id': order_id}))
        failure_url = self.context['request'].build_absolute_uri(
            reverse(
                'app:checkout-failure-view',
                kwargs={'order_id': order_id}))
        instance.checkout(order_id, success_url, failure_url)
        instance.save()
        return instance


class AnonymousCartItemCreateSerializer(serializers.ModelSerializer):
    listing_pk = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        listing_pk = attrs['listing_pk']
        if not Listing.objects.filter(pk=listing_pk).count():
            raise serializers.ValidationError({
                'listing': 'Already exists in shopping cart.'})
        return super().validate(attrs)

    class Meta:
        model = CartItem
        fields = ('listing_pk', )


class AnonymousCartCheckoutSerializer(CartCheckoutSerializer):
    items = AnonymousCartItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Cart
        fields = ('pk', 'items', 'stripe_session_id', 'success_url', 'failure_url', 'total', 'count', )
        extra_kwargs = {
            'stripe_session_id': {'read_only': True},
            'success_url': {'read_only': True},
            'failure_url': {'read_only': True},
        }

    def validate(self, attrs):
        # attrs = super().validate(attrs)
        items = attrs.get('items', [])

        if not isinstance(items, list):
            raise serializers.ValidationError({'items': 'Invalid items.'})

        if not items:
            raise serializers.ValidationError({'items': 'Cart can not be empty.'})

        for item in items:
            # NOTE: item needs to be pk(int)
            if not Listing.objects.filter(pk=item['listing_pk'], status=PRODUCT_STATUS.published).exists():
                raise serializers.ValidationError({'items': f'Listing not found for {item["listing_pk"]}.'})

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        if (user.is_anonymous):
            items = validated_data.pop('items')
            instance = super().create(validated_data)
            for item in items:
                instance.items.create(listing=Listing.objects.get(pk=item['listing_pk']))
        else:
            instance = Cart.objects.filter(user=user).first()

        # NOTE: Creating order and checking out...
        order_id = str(uuid.uuid4())
        success_url = self.context['request'].build_absolute_uri(
            reverse(
                'app:checkout-success-view',
                kwargs={'order_id': order_id}))
        failure_url = self.context['request'].build_absolute_uri(
            reverse(
                'app:checkout-failure-view',
                kwargs={'order_id': order_id}))
        instance.checkout(order_id, success_url, failure_url)
        instance.save()

        return instance
