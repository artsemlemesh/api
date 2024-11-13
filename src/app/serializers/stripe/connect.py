from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from djstripe.enums import AccountType, BusinessType
from djstripe.models.connect import StripeEnumField
from stripe import AccountLink
from app.models.stripe import ByndeAccount


class BusinessProfileSearialize(serializers.Serializer):
    mcc = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    product_description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, trim_whitespace=True
    )
    support_address = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, trim_whitespace=True
    )
    support_email = serializers.CharField()
    support_phone = serializers.CharField()
    support_url = serializers.CharField()
    url = serializers.CharField()


class ByndeAccountCreateSearializer(serializers.Serializer):
    # business_profile = BusinessProfileSearialize()
    country = serializers.CharField(
        max_length=2, help_text="The country of the account"
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs["email"] = self.context["request"].user.email
        attrs["type"] = AccountType.express
        attrs["capabilities"] = {
            "transfers": {"requested": True},
        }
        return attrs

    def save(self, **kwargs):
        request = self.context["request"]
        response = ByndeAccount._api_create(**self.validated_data)
        response["settings"]["branding"]["icon"] = None
        response["settings"]["branding"]["logo"] = None
        instance = ByndeAccount._create_from_stripe_object(response)
        request.user.account = instance
        request.user.save()
        account_links = AccountLink.create(
            account=instance.id,
            refresh_url=request.build_absolute_uri(reverse("app:stripe-refresh")),
            return_url=request.build_absolute_uri(reverse("app:stripe-return")),
            type="account_onboarding",
            collect="currently_due",
        )

        return account_links
