import stripe
from django.core.management import BaseCommand
from djstripe.models import Source
from app.models.user import User
from app.models.stripe import ByndeAccount, ByndeCustomer


class Command(BaseCommand):
    SESSION_ID = 'cs_test_zlx3Z8r6YzQwYkcWzaZsVXYSTUtd9pX9neCx3e6sd4OzyHhjG3OffuvR'
    PAYMENT_INTENT_ID = 'pi_1HWCkTDDUuqUDouITqGPOKTP'
    TRANSFER_GROUP = 'TEST_SESSION_CHECKOUT_GROUP1'

    @property
    def _test_account_id(self) -> str:
        return 'acct_1HAMtQGjM2qaiEOd'

    @property
    def _test_account_id_2(self) -> str:
        return 'acct_1HIPZQLOYTv0Hs7U'

    @property
    def _test_items(self) -> dict:
        return [
            {
                'name': 'FAKE ITEM 1',
                'amount': 25 * 100,
                'currency': 'usd',
                'quantity': 1,
            },
            {
                'name': 'FAKE ITEM 2',
                'amount': 35 * 100,
                'currency': 'usd',
                'quantity': 1,
            },
            {
                'name': 'FAKE ITEM 3',
                'amount': 40 * 100,
                'currency': 'usd',
                'quantity': 1,
            },
        ]

    def create_session(self):
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=self._test_items,
            payment_intent_data={
                # 'payment_method_types': ['card'],
                'transfer_group': self.TRANSFER_GROUP,
            },
            success_url='https://example.com/success',
            cancel_url='https://example.com/failure',
        )
        return session

    def test_transer_1(self):
        transfer = stripe.Transfer.create(
            amount=sum([item['amount'] for item in self._test_items[:2]]),
            currency='usd',
            destination=self._test_account_id,
            transfer_group=self.TRANSFER_GROUP,
        )
        return transfer

    def test_transer_2(self):
        transfer = stripe.Transfer.create(
            amount=sum([item['amount'] for item in self._test_items[2:]]),
            currency='usd',
            destination=self._test_account_id_2,
            transfer_group=self.TRANSFER_GROUP,
        )
        return transfer

    def handle(self, *args, **kwargs):
        # session = self.create_session()
        # print(session)
        transfer1 = self.test_transer_1()
        transfer2 = self.test_transer_2()
        print(transfer1)
        print(transfer2)
