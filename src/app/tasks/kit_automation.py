from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model

from app.utils.bundle_kit_automation.automate import KitAutomation
from app.utils.address import validate_usps_address, standardize_state

username = settings.USPS_USERNAME
password = settings.USPS_PASSWORD
environment = settings.ENVIRONMENT.lower()

available_packages = [
    'LARGE_FLAT_RATE_BOX',
    'MEDIUM_FLAT_RATE_BOX',
    'PADDED_FLAT_RATE_ENVELOPE'
]


@shared_task
def send_kits(user_pk, packages: list, env=environment):
    user = get_user_model().objects.get(pk=user_pk)
    address = {
        'nickname': user.get_full_name(),
        'firstName': user.first_name,
        'lastName': user.last_name,
        'street_address': user.address_line_1 if user.address_line_1 else user.address_line_2,
        'address2': user.address_line_2 if user.address_line_2 else None,
        'city': user.city,
        'state': standardize_state(user.state),
        'postal_code': user.postal_code,
        'country': 'US',
        'phone': str(user.phone) if user.phone else '',
        'email': user.email,
    }
    validation_err = validate_usps_address(**address)
    if len(validation_err[1]) > 0:
        print(validation_err)
        raise Exception('Invalid address provided')
    if env != 'production' or not (username and password):
        print(f'Sending {packages} to {address} attempted')
        return address
    automation = KitAutomation(username, password)
    filtered_packages = [x for x in packages if x in available_packages]
    order_details = automation.send_bundle_kits(address, filtered_packages)
    print('Order Details:', order_details)
    return order_details
