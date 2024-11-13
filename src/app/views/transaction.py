import stripe

from django.conf import settings
from django.http import JsonResponse
from rest_framework import generics, serializers
from rest_framework.utils import json

from app.models import *
stripe.api_key = settings.STRIPE_SECRET_KEY


class TransactionView(generics.GenericAPIView):

    class Transaction_Serializer(serializers.ModelSerializer):
        class Meta:
            model = Transaction
            fields = '__all__'

        def update(self, instance, validated_data):
            transaction = Transaction.objects.get(pk=instance.id)
            transaction.objects.filter(pk=instance.id).update(**validated_data)
            return transaction

    serializer_class = Transaction_Serializer
    def post(self, request, *args, **kwargs):

        stripe.api_key = settings.STRIPE_SECRET_KEY
        json_data = json.loads(request.body)
        listing = Listing.objects.filter(id=json_data['listing_id']).first()

        fee_percentage = .01 * int(listing.platform_fee_pct)
        token = request.user.stripe_account.stripe_access_token     # buyer token
        try:
            customer = get_or_create_customer(
                self.request.user.email,
                json_data['token'],
            )

            charge = stripe.Charge.create(
                amount=listing.buyer_price,
                currency='usd',
                description=listing.description,
                source=token
            )

            transaction = Transaction.create(amount=listing.buyer_price,
                                             currency='usd',
                                             customer_id=customer.id,
                                             description=listing.description,
                                             fee_percent=fee_percentage,
                                             seller_price=listing.seller_price,
                                             shipping_cost=listing.shipping_cost,
                                             seller_user_id=listing.seller.stripe_user_id)

            transfer = stripe.Transfer.create(
                amount=listing.shipping_cost,
                currency='usd',
                destination=json_data['shipping_dest'],
                transfer_group=transaction.transfer_group,
            )

            if charge:
                return JsonResponse({'status': 'success', 'charge_id': charge.id}, status=202)
            # return JsonResponse({'status': 'error'}, status=500)
        except stripe.error.StripeError as e:
            return JsonResponse({'status': 'error'}, status=500)

    def partial_update(self, request, *args, **kwargs):
        serialized = self.get_serializer(
            request.user, data=request.data, partial=True)
        if serialized.status == 1:
            transaction = Transaction.objects.filter(id=serialized.data['pk'])
            transaction.confirmTransfer()
        return self.partial_update(request, *args, **kwargs)


def get_or_create_customer(email, token):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    connected_customers = stripe.Customer.list()
    for customer in connected_customers:
        if customer.email == email:
            print(f'{email} found')
            return customer
    print(f'{email} created')
    return stripe.Customer.create(
        email=email,
        source=token,
    )
