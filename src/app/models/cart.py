import stripe
from typing import Optional

from django.db import models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from model_utils.models import TimeStampedModel
from djstripe.models import PaymentIntent, Session
from django.apps import apps
from django.conf import settings
# from app.models.user import send
from ..tasks import send_pepo_email
from ..utils.epost import EasyPostUtils
from ..utils.notification import send_push_message
from app.models.user import User
from app.models.order import Order, ByndeCustomer
from app.utils.analytics import track_analytics


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE,
        related_name='cart', verbose_name=_('shopping cart'),
        null=True, blank=True)
    stripe_session_id = models.CharField(
        max_length=80, null=True, blank=True,
        verbose_name=_('stripe session id')
    )
    stripe_payment_intent_id = models.CharField(
        max_length=48, null=True, blank=True,
        verbose_name=_('stripe payment intent id'))
    order_id = models.UUIDField(
        null=True, blank=True, verbose_name=_('order id candidate'))

    class Meta:
        verbose_name = _('shopping cart')
        ordering = ('-modified', )

    @property
    def count(self) -> int:
        return self.items.count()

    @property
    def total(self) -> int:
        return sum([item.bundle.buyer_price.amount for item in self.items.all()])

    def get_success_url(self) -> Optional[str]:
        if self.order_id:
            return reverse(
                'app:checkout-success-view',
                kwargs={'order_id': self.order_id})
        else:
            return None

    def get_failure_url(self) -> Optional[str]:
        if self.order_id:
            return reverse(
                'app:checkout-failure-view',
                kwargs={'order_id': self.order_id})
        else:
            return None

    @transaction.atomic()
    def checkout(self, order_id: str, success_url: str, failure_url: str):
        if self.user:
            if not self.user.customer:
                self.user.get_or_create_stripe_customer()
            customer = self.user.customer
        else:
            # Anonymous case
            stripe_customer_obj = stripe.Customer.create()
            customer, created = ByndeCustomer._get_or_create_from_stripe_object(
                stripe_customer_obj)
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            billing_address_collection='auto',
            shipping_address_collection={
                'allowed_countries': ['US'],
            },
            line_items=[item.to_dict() for item in self.items.all()],
            payment_intent_data={
                'transfer_group': f'{self.order_id}',
            },
            success_url=success_url,
            cancel_url=failure_url,
        )
        self.order_id = order_id
        self.stripe_session_id = session.id
        self.stripe_payment_intent_id = session.payment_intent

        # NOTE: I think we should change bundle status here
        # so as to avoid selling a single bundle to multiple customers?

    @transaction.atomic()
    def confirm_checkout(self):
        # TODO: create bundle with cart items

        # NOTE: Confirm the payment intent first if not.
        payment_intent_obj = stripe.PaymentIntent.retrieve(
            self.stripe_payment_intent_id)
        if not PaymentIntent.objects.filter(
                id=self.stripe_payment_intent_id).count():
            payment_intent, _ = PaymentIntent._get_or_create_from_stripe_object(
                payment_intent_obj)
        else:
            payment_intent = PaymentIntent.objects.get(
                id=self.stripe_payment_intent_id)

        session_obj = Session.stripe_class.retrieve(self.stripe_session_id)
        address = session_obj.shipping.address

        stripe_customer_obj = stripe.Customer.retrieve(session_obj.customer)
        customer, created = ByndeCustomer._get_or_create_from_stripe_object(
            stripe_customer_obj)
        if not self.user:
            user_seller = ''
            # Anonymous case
            email = session_obj.customer_details['email']
            if not User.objects.filter(email__iexact=email).exists():
                user = User.objects.create_user(email=email)
            else:
                user = User.objects.get(email__iexact=email)
            if not hasattr(customer, 'user'):
                customer.user = user
                customer.save()

            if hasattr(user, 'cart'):
                user.cart.delete()

            self.user = user

        # NOTE: Should be converted to order here.
        order = Order.objects.create(
            platform_order_id=self.order_id,
            customer=customer,
            payment_intent=payment_intent,
            address_line_1=address.line1,
            address_line_2=address.line2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code)
        for item in self.items.all():
            order_item = order.order_items.create(
                bundle=item.bundle)
            order_item.bundle.sold()
            order_item.bundle.purchased_by = self.user
            seller_email = order_item.bundle.created_by
            try:
                if seller_email != '' and seller_email is not None:
                    user_seller = User.objects.get(email=seller_email)
            except Exception as e:
                print(seller_email)
                print("Error due to", e)
                break
            seller_expo_push_token = user_seller.expo_push_token
            listing_title = order_item.bundle.title
            order_item.bundle.save()
            track_analytics(
                self.user.email,
                'Bundle Purchased',
                {
                    'id': item.bundle.id,
                    'title': item.bundle.title,
                    'price': item.bundle.seller_price.amount,
                    'buyer_price': item.bundle.buyer_price.amount,
                    'creator_email': item.bundle.created_by.email,
                    'buyer_email':  self.user.email,
                    'env': (settings.ENVIRONMENT).lower(),
                }
            )
            oid = str(self.order_id)
            send_push_message(seller_expo_push_token, 'Sold Item! ' + listing_title, {
                "order_id": oid,
                "purchased_by": self.user.email,
            })
            # can't send bundle sold because we don't have the label ready yet. happens in a batch
            # seller_email.send_bundle_sold({'listing_title': listing_title,'postage_url': shipment.label_url})
            self.user.purchased_bundle()
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items',
        verbose_name=_('cart items'))
    product = models.ForeignKey(
        'app.Product', on_delete=models.CASCADE,
        related_name='cart_items')

    class Meta:
        ordering = ('cart', 'product', )
        unique_together = ('cart', 'product', )
        verbose_name = _('shopping cart item')

    def to_dict(self) -> dict:
        return {
            'product_id': self.product.id,
            'name': self.product.title,
            'quantity': 1,
        }
