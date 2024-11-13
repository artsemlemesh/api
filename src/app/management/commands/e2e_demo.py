import stripe
from django.core.management import BaseCommand
from djstripe.models import Source
from app.models.user import User
from app.models.stripe import ByndeAccount, ByndeCustomer


class Command(BaseCommand):
    @property
    def _test_account_id(self) -> str:
        return 'acct_1HAMtQGjM2qaiEOd'

    def _create_payment_intent(
        self,
        account_id: str,
        payment_method_id: str,
        amount: float,
        fee: float
    ) -> stripe.PaymentIntent:
        return stripe.PaymentIntent.create(
            customer=account_id,
            payment_method=payment_method_id,
            payment_method_types=['card'],
            amount=amount,
            currency='usd',
            application_fee_amount=fee,
            transfer_data={
                'destination': self._test_account_id
            }
        )

    def _cancel_payment_intent(self, stripe_id: str):
        return stripe.PaymentIntent.cancel(stripe_id)

    def _get_payment_intent(self, stripe_id: str):
        return stripe.PaymentIntent.retrieve(stripe_id)

    def _get_token_from_card(self) -> stripe.Token:
        response = stripe.Token.create(
            card={
                "number": "4242424242424242",
                "exp_month": 9,
                "exp_year": 2021,
                "cvc": "314",
            }
        )
        return response

    def _get_customer(self) -> ByndeCustomer:
        user = User.objects.last()
        if not user.customer:
            response = user.get_or_create_stripe_customer()
        return user.customer

    def handle(self, *args, **kwargs):
        customer = self._get_customer()
        token = self._get_token_from_card()
        card_stripe_object: stripe.Card = stripe.Customer.create_source(
            customer.id, source=token.stripe_id)

        # NOTE: Create a new payment intent
        payment_intent = self._create_payment_intent(
            customer.id, card_stripe_object.stripe_id, 1540, 148)

        # payment_intent = self._get_payment_intent(self.TEST_PAYMENT_INTENT_IDS[1])

        # NOTE: Activating an incomplete by setting customer or payment type
        # stripe.PaymentIntent.modify(
        #     payment_intent.stripe_id,
        #     customer=self._test_customer_id,
        #     payment_method=self._test_customer_payment_method)
        
        # NOTE: Confirm the payment intent
        response = payment_intent.confirm()
        print(response)
