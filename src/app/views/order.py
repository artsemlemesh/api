from rest_framework import viewsets, decorators
from rest_framework.permissions import IsAuthenticated
from app.models.order import Order, OrderItem
from app.serializers.order import OrderSerializer, OrderItemSerializer,\
    SellerOrderItemCancelSerializer, SellerOrderItemConfirmSerializer,\
    SellerOrderItemPickupCreateSerializer, SellerOrderItemPickupCancelSerializer


class BuyerOrdersViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated, )
    http_method_names = ('get', 'patch', )

    def get_queryset(self):
        return Order.objects.filter(customer__user=self.request.user)


class BuyerOrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = (IsAuthenticated, )
    http_method_names = ('get', 'patch', )
    def get_queryset(self):
        return OrderItem.objects.filter(
            listing__purchased_by=self.request.user
        )

class SellerOrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = (IsAuthenticated, )
    http_method_names = ('get', 'patch', )

    def get_queryset(self):
        return OrderItem.objects.filter(
            listing__created_by=self.request.user
        )

    def get_serializer_class(self):
        if self.action == 'cancel':
            return SellerOrderItemCancelSerializer
        elif self.action == 'confirm_to_ship':
            return SellerOrderItemConfirmSerializer
        elif self.action == 'create_pickup':
            return SellerOrderItemPickupCreateSerializer
        elif self.action == 'cancel_pickup':
            return SellerOrderItemPickupCancelSerializer
        else:
            return super().get_serializer_class()

    @decorators.action(
        detail=True, methods=['patch'],
        url_path='confirm_to_ship', url_name='confirm_to_ship')
    def confirm_to_ship(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @decorators.action(
        detail=True, methods=['patch'], url_path='cancel', url_name='cancel'
    )
    def cancel(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @decorators.action(
        detail=True, methods=['patch'],
        url_path='create_pickup', url_name='create_pickup'
    )
    def create_pickup(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @decorators.action(
        detail=True, methods=['patch'],
        url_path='cancel_pickup', url_name='cancel_pickup'
    )
    def cancel_pickup(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
