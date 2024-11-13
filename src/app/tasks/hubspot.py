import os
from django.conf import settings
from celery import shared_task
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput


@shared_task
def hubspot_user_signup(user):
    hubspot = HubSpot(api_key=settings.HUBSPOT_API_KEY)
    # hubspot = HubSpot(api_key='d7bea843-02b8-445d-a684-f10b409e0c4d')
    try:
        simple_public_object_input = SimplePublicObjectInput(
            properties={
                "environment": os.environ.get('DJANGO_SETTINGS_MODULE'),
                "user_pk": user.pk,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "email": user.email,
                "type": "App User",
                "lifecyclestage": "marketingqualifiedlead"
            })
        api_response = hubspot.crm.contacts.basic_api.create(
            simple_public_object_input=simple_public_object_input
        )
    # except ApiException as e:
    #     print("Exception when creating contact: %s\n" % e)
    except Exception:
        pass
