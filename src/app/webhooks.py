import stripe
from logging import Logger

from django.db.utils import IntegrityError
from djstripe import webhooks, models

from app.models.stripe import ByndeAccount, ByndeCustomer
from app.models.cart import Cart


logger = Logger(__file__)


@webhooks.handler(
    'account.updated',
    'account.application.deauthorized',
    'account.application.authorized',
    'account.external_account.updated',
    'account.external_account.deleted',
    'account.external_account.created'
)
def stripe_account_event_handler(event, **kwargs):
    try:
        account, _ = ByndeAccount._get_or_create_from_stripe_object(
            event.data.object)
        account.sync_from_stripe_data(event.data.object)
    except BaseException:
        pass


@webhooks.handler(
    'customer.created',
    'customer.updated',
    'customer.deleted',
)
def stripe_customer_event_handler(event, **kwargs):
    try:
        customer, _ = ByndeCustomer._get_or_create_from_stripe_object(
            event.data.object)
        customer.sync_from_stripe_data(event.data.object)
    except BaseException:
        pass

    logger.info(msg="Customer event received.")


@webhooks.handler(
    'customer.source.created',
    'customer.source.updated',
    'customer.source.expiring',
    'customer.source.deleted',
)
def stripe_customer_source_event_hander(event, **kwargs):
    event_object = event.data.object
    if isinstance(event_object, stripe.Card):
        card, _ = models.Card._get_or_create_from_stripe_object(event_object)
        logger.info("A card event received for customer.")
    else:
        msg = f'Unknown type found - {type(event_object)}'
        logger.warn(msg)


@webhooks.handler(
    'payment_intent.succeeded',
    'payment_intent.requires_action',
    'payment_intent.processing',
    'payment_intent.payment_failed',
    'payment_intent.created',
    'payment_intent.canceled',
    'payment_intent.amount_capturable_updated',
)
def stripe_payment_intent_event_handler(event, **kwargs):
    event_obj = event.data.object
    pi_obj, _ = models.PaymentIntent._get_or_create_from_stripe_object(
        event_obj)
    logger.info("PaymentIntent updated.")


@webhooks.handler(
    'checkout.session.completed'
)
def stripe_session_complete_event_handler(event, **kwargs):
    event_obj = event.data.object
    session, _ = models.Session._get_or_create_from_stripe_object(event_obj)
    if Cart.objects.filter(stripe_session_id=session.id).count():
        cart = Cart.objects.filter(stripe_session_id = session.id).first()
        try:
            cart.confirm_checkout()
            cart.save()
        except IntegrityError as e:
            # NOTE: It means that cart already confirmed by success url.
            # So we can ignore this case.
            logger.info(e.__dict__)

    logger.info("Checkout Session event received.")

@webhooks.handler(
    'checkout.session.async_payment_failed'
    # 'checkout.session.async_payment_succeeded'
)
def stripe_session_failure_event_handler(event, **kwargs):
    event_obj = event.data.object
    session, _ = models.Session._get_or_create_from_stripe_object(event_obj)
    # TODO: What to do here?
    logger.info("Checkout Session event received.")
