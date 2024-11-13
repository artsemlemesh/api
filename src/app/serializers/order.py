from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from app.constants.status import ORDER_ITEM_STATUS
from app.models.order import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'


class SellerOrderItemConfirmSerializer(serializers.ModelSerializer):
    status = serializers.HiddenField(default=ORDER_ITEM_STATUS.active)

    class Meta:
        model = OrderItem
        fields = ('status', )

    def validate(self, attrs):
        if self.instance.listing.created_by != self.context['request'].user:
            raise serializers.ValidationError(_(
                'You are not permitted to cancel.'))
        if self.instance.status == ORDER_ITEM_STATUS.ready_to_ship:
            raise serializers.ValidationError(_(
                'This order item was already confirmed.'))
        if self.instance.status not in [
                ORDER_ITEM_STATUS.active, ORDER_ITEM_STATUS.label_failure]:
            raise serializers.ValidationError(_(
                'This order item can not ship.'))
        return super().validate(attrs)

    def update(self, instance, validated_data):
        instance.confirm_to_ship()
        instance.save()
        return instance


class SellerOrderItemCancelSerializer(serializers.ModelSerializer):
    status = serializers.HiddenField(default=ORDER_ITEM_STATUS.active)
    reason = serializers.CharField(
        write_only=True, required=True, label=_('cancel reason'))

    class Meta:
        model = OrderItem
        fields = ('status', 'reason')

    def validate(self, attrs):
        if self.instance.listing.created_by != self.context['request'].user:
            raise serializers.ValidationError(_(
                'You are not permitted to cancel.'))
        if not self.instance.can_be_canceled():
            raise serializers.ValidationError(_(
                'This order item can not be canceled.'))
        return super().validate(attrs)

    def update(self, instance, validated_data):
        try:
            instance.cancel(validated_data['reason'])
        except Exception as e:
            raise serializers.ValidationError(e)
        return super().update(instance, validated_data)


class SellerOrderItemPickupCreateSerializer(serializers.ModelSerializer):
    min_datetime = serializers.DateTimeField(
        write_only=True, help_text=_('min datetime'))
    max_datetime = serializers.DateTimeField(
        write_only=True, help_text=_('max datetime'))
    instructions = serializers.CharField(
        write_only=True, help_text=_('Please give any instructions here.')
    )

    class Meta:
        model = OrderItem
        fields = ('min_datetime', 'max_datetime', 'instructions')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance.listing.created_by != self.context['request'].user:
            raise serializers.ValidationError(
                'Seller is only permitted to request pickup')
        if not hasattr(self.instance, 'shipment'):
            raise serializers.ValidationError('Shipment was not created yet.')
        if self.instance.status == ORDER_ITEM_STATUS.canceled:
            raise serializers.ValidationError('Canceled shipment can not be picked up.')
        if hasattr(self.instance.shipment, 'pickup'):
            raise serializers.ValidationError('Pickup already scheduled.')
        return attrs

    def update(self, instance, validated_data):
        try:
            instance.shipment.create_pickup(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(e)
        return instance


class SellerOrderItemPickupCancelSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('pk', )

    def validate(self, attrs):
        if self.instance.listing.created_by != self.context['request'].user:
            raise serializers.ValidationError(_(
                'Sller is only permitted to request pickup'))
        if not hasattr(self.instance, 'shipment'):
            raise serializers.ValidationError('Shipment was not created yet.')
        if not hasattr(self.instance.shipment, 'pickup'):
            raise serializers.ValidationError('Pickup not found.')
        return super().validate(attrs)

    def update(self, instance, validated_data):
        try:
            instance.shipment.cancel_pickup()
        except Exception as e:
            raise serializers.ValidationError(e)
        return instance
