import hashlib
import hmac
import requests
import json

from celery import shared_task
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from postmarker.core import PostmarkClient


def send_pepo_email(recipient, template, email_vars):
    email_vars["url"] = f'{settings.SITE_URL}{email_vars["url"]}'
    pepo_url = "https://pepocampaigns.com/api/v1/send/"
    delimiter = "::"
    url_endpoint = "/api/v1/send/"
    request_time = timezone.now().isoformat()
    string_to_sign = f"{url_endpoint}{delimiter}{request_time}"
    signature = hmac.new(
        "test".encode() if settings.TEST_MODE else settings.PEPO_SECRET_KEY.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()
    query_string = {
        "api-key": settings.PEPO_API_KEY,
        "email": recipient,
        "template": template,
        "request-time": request_time,
        "signature": signature,
        "email_vars": json.dumps(email_vars),
    }

    if settings.TEST_MODE:
        print(query_string)
        return True

    response = requests.post(pepo_url, params=query_string)
    if response.status_code >= 400:
        raise Exception(response.json())

    if response.json()["error"]:
        raise Exception(response.json())


@shared_task
def send_email(
    user_pk, email_type, new_email=None, from_email=settings.EMAIL_FROM, **kwargs
):
    """
    This is used for

    1. Email verification when new user is registered
    2. When user change existing email
    3. When request password change if forgotten

    a. For newly registered user there will be just user_pk passed as param
    b. For forgot password, there will be
          user_pk,
          email_type='forgot_password'
    c. For email changed, there will be user_pk,
          email_type='email_updated' and new email

    All of the above 3 scenarios use different HTML template for email

    NOTE: we don't send emails via PEPO in test mode and
      instead return True before sending actual email
    """

    user = get_user_model().objects.get(pk=user_pk)
    recipient = user.email
    token = token_generator.make_token(user)
    uid = force_str(urlsafe_base64_encode(force_bytes(user.pk)))
    # url = reverse('app:verify-email', args=(uid, token))
    url = f"/auth/verify/{uid}/{token}"

    """
    kwargs: dict of vars to be passed into postmark template
    """
    bcc = None

    if "bcc" in kwargs:
        bcc = kwargs.get("bcc")

    reply_email = f"BundleUp <no-reply@bundleup.co>"

    email_vars = kwargs
    email_vars["product_url"] = "https://www.bundleup.co"
    email_vars["product_name"] = "BundleUp"
    email_vars["company_name"] = "BundleUp"
    email_vars["company_address"] = ""
    email_vars["support_email"] = "support@bundleup.co"
    email_vars["user"] = user.full_name_or_email
    email_vars["first_name"] = user.first_name
    email_vars["confirm_code"] = user.code
    email_vars["base_url"] = settings.SITE_URL

    if email_type == "forgot_password":
        template = "password-reset"
        url = f"/reset-password/{uid}/{token}"

    if email_type == "email_updated" and new_email:
        template = "update_email"
        recipient = new_email
        new_email_encoded = force_str(urlsafe_base64_encode(force_bytes(new_email)))
        url = reverse("app:verify-changed-email", args=(uid, token, new_email_encoded))
        email_vars.update({"old_email": user.email, "new_email": new_email})

    if email_type == "notify_admin":
        template = "notify_admin"
        recipient = settings.ADMIN
        # url = f"/user/profile/{user.pk}"
        email_vars["email"] = user.email
        email_vars["username"] = user.full_name_or_email

    if email_type == "notify_user_acceptbrand":
        template = "notify_user_on_brand_accept"
        recipient = user.email
        url = f"/user/profile/{user.pk}"

    if email_type == "sold_bundle":
        template = "sold_bundle"
        # url = f"/user/profile/{user.pk}"
        recipient = user.email

    if email_type == "purchase_bundle":
        template = "receipt"
        # url = f"/user/profile/{user.pk}"
        recipient = user.email


    if email_type == "notify_user_rejectedbrand":
        template = "notify_user_on_brand_reject"
        recipient = user.email
        url = f"/user/profile/{user.pk}"

    if email_type == "new_user_registered":
        template = "new_user"
        # url = f"/user/profile/{user.pk}"
        recipient = user.email
        email_vars["email"] = user.email
        email_vars["username"] = user.full_name_or_email

    if email_type == "new_user_registered_admin":
        template = "new_user"
        # url = f"/user/profile/{user.pk}"
        recipient = settings.ADMIN
        email_vars["email"] = user.email
        email_vars["username"] = user.full_name_or_email

    email_vars["action_url"] = url

    postmark = PostmarkClient(server_token=settings.POSTMARK_API_KEY)

    postmark.emails.send_with_template(
        From=from_email,
        To=recipient,
        TemplateAlias=template,
        TemplateModel=email_vars,
        ReplyTo=kwargs.get("reply_to", reply_email),
        Bcc=bcc
    )
