# standard library
import uuid
import os
from typing import Optional
import pytz
import stripe
from random import randint

# django
from django.db import models
from django.conf import settings
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
    MinValueValidator,
)
from sorl.thumbnail import get_thumbnail, ImageField as SorlImageField
from phonenumber_field.modelfields import PhoneNumberField

from app.tasks import send_email, send_kits
from app.models.stripe import ByndeAccount, ByndeCustomer
from app.utils.address import Address, validate_address
from app.utils.epost import easypost, EasyPostUtils

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_upload_path(instance, filename):
    filename = f'{uuid.uuid4()}.{filename.split(".")[-1]}'
    return os.path.join("users", str(instance.id), filename)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        app_label = "app"

    """
    -code-review-
    define each choice as a list of tuples, with an all-uppercase name as a class attribute on the model
    """
    id = models.AutoField(primary_key=True)
    environment_id = models.CharField(max_length=255, default="")

    email = models.EmailField(unique=True)
    first_name = models.CharField(
        _("first name"),
        max_length=30,
    )
    last_name = models.CharField(
        _("last name"),
        max_length=150,
    )
    address_line_1 = models.CharField(
        _("address line 1"), max_length=255, null=True, blank=True
    )
    address_line_2 = models.CharField(
        _("address line 2"), max_length=255, null=True, blank=True
    )
    city = models.CharField(_("city"), max_length=255, null=True, blank=True)
    state = models.CharField(_("state"), max_length=255, null=True, blank=True)
    postal_code = models.CharField(
        _("postal_code"), max_length=15, null=True, blank=True
    )
    country = models.CharField(_("country"), max_length=255, null=True, blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=False,
        help_text=_("Designates whether this user should be treated as active."),
    )
    account = models.OneToOneField(
        ByndeAccount,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="user",
        verbose_name=_("Connected Account"),
    )
    customer = models.OneToOneField(
        ByndeCustomer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="user",
        verbose_name=_("Connected Customer"),
    )

    phone = PhoneNumberField(blank=True, null=True)
    photo = SorlImageField(
        upload_to=get_upload_path,
        null=True,
        blank=True,
        help_text="avatar photo",
        max_length=255,
    )
    expo_push_token = models.CharField(max_length=200, null=True, blank=True)

    code = models.CharField(
        _("verification code"),
        max_length=4,
        validators=[MinLengthValidator(4), MaxLengthValidator(4)],
        null=True,
        default=None,
    )
    code_failed_count = models.IntegerField(
        _("verification failure counter"),
        validators=[MinValueValidator(0)],
        null=False,
        default=0,
    )

    is_google_calendar_synced = models.BooleanField(default=False)

    created_date = models.DateTimeField(auto_now_add=True)
    last_modified_date = models.DateTimeField(auto_now=True)

    express_dashboard = models.URLField(
        null=True, blank=True, verbose_name=_("stripe express dashboard link")
    )

    is_deleted = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    objects = UserManager()

    def __str__(self):
        return f"{self.email}"

    @property
    def full_name_or_email(self):
        return (
            f"{self.first_name} {self.last_name}"
            if self.first_name or self.last_name
            else self.email
        )

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def get_short_name(self):
        return (
            f"{self.first_name} {self.last_name[:1]}."
            if self.first_name and self.last_name
            else ""
        )

    # @property
    # def environment_id(self):
    #     return f"{self.environment}_{self.id}"

    @property
    def shipping_address(self) -> easypost.address:
        return EasyPostUtils.create_address(
            self.get_full_name(),
            street1=self.address_line_1,
            street2=self.address_line_2,
            city=self.city,
            state=self.state,
            postal_code=self.postal_code,
            phone=None
            if self.phone is None
            else (
                self.phone.national_number
                if hasattr(self.phone, "national_number")
                else self.phone
            ),
        )

    @property
    def thumbnail(self):
        if not self.photo:
            return None
        return get_thumbnail(
            self.photo, settings.THUMBNAIL_AVATAR_IMAGE_SIZE, crop="center", quality=99
        ).url

    @property
    def is_address_valid(self):
        address, errors = validate_address(
            self.state,
            self.city,
            self.postal_code,
            self.address_line_1 or self.address_line_2,
        )
        return isinstance(address, Address)

    @property
    def current_time(self):
        """
        Based on the user timezone, this function returns user current time based
        on user timezone. user object must have timezone (user.timezone) attr as
        `Asia/Karachi` or `EST`
        """
        user_timezone = pytz.timezone(self.timezone)
        # convert current UTC time to user's timezone
        user_current_time = timezone.now().astimezone(user_timezone)
        return user_current_time

    def get_or_create_stripe_customer(self):
        stripe_object = stripe.Customer.create(email=self.email)
        customer, _ = ByndeCustomer._get_or_create_from_stripe_object(stripe_object)
        self.customer = customer
        self.save()

    def get_express_dashboard_url(self, raise_exception: bool = False) -> Optional[str]:
        if self.express_dashboard:
            return self.express_dashboard
        else:
            try:
                response = stripe.Account.create_login_link(self.account.id)
                self.express_dashboard = response["url"]
                self.save()
                return self.express_dashboard
            except Exception as e:
                if raise_exception:
                    raise e
                else:
                    return None

    @property
    def is_stripe_connected(self) -> bool:
        if self.account:
            return True
        else:
            return False

    def reset_confirm_code(self):
        self.code = "".join(str(randint(0, 9)) for _ in range(4))
        self.code_failed_count = 0

    def send_verification_email(self):
        return send_email.delay(self.pk, email_type="new_user_registered")

    def send_forgot_password_email(self):
        return send_email.delay(self.pk, email_type="forgot_password")

    def send_suggested_brands(self):
        return send_email.delay(self.pk, email_type="notify_admin")

    def send_user_notify(self):
        return send_email.delay(self.pk, email_type="notify_user_acceptbrand")

    def send_user_notify_onreject(self):
        return send_email.delay(self.pk, email_type="notify_user_rejectedbrand")

    def send_email_updated_email(self, new_email):
        return send_email.delay(self.pk, email_type="email_updated", new_email=new_email)

    def send_bundle_sold(self, **kwargs):
        return send_email.delay(self.pk, email_type="sold_bundle", **kwargs)

    def purchased_bundle(self, **kwargs):
        return send_email.delay(self.pk, email_type="purchase_bundle", **kwargs)

    def send_update_email_to_admin(self):
        return send_email.delay(self.pk, email_type="new_user_registered_admin")

    def send_bundle_kits(self, packages: list):
        return send_kits.delay(self.pk, packages=packages)


class SocialProfile(models.Model):
    """
    -code-review-
    define each choice as a list of tuples, with an all-uppercase name as a class attribute on the model
    """

    FACEBOOK = "facebook"
    GOOGLE = "google"

    PROVIDER_CHOICES = ((FACEBOOK, "Facebook"), (GOOGLE, "Google"))
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider_id = models.CharField(max_length=50)
    provider_name = models.CharField(choices=PROVIDER_CHOICES, max_length=8)
    access_token = models.CharField(max_length=350)

    class Meta:
        unique_together = ("user", "provider_name")

    def __str__(self):
        return "{} {}".format(self.user, self.provider_name)


class GoogleSettings(models.Model):
    """
    This model saves credentials/settings for google.
    Supposed to be used with Google Calendar for syncing calendar events
    """

    access_token = models.CharField(max_length=200)
    token_expiry = models.DateTimeField()
    refresh_token = models.CharField(max_length=200)

    # https://developers.google.com/calendar/v3/sync
    sync_token = models.CharField(max_length=200)

    # https://developers.google.com/calendar/v3/push#required_watch_prop
    push_notification_id = models.UUIDField(default=uuid.uuid4)
    calendar_resource_id = models.CharField(max_length=200, blank=True, null=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="google_settings"
    )

    def __str__(self):
        return f"{self.user.email} {self.access_token}"

    class Meta:
        verbose_name_plural = "Google Settings"


class AppleLoginSerialzerModel(models.Model):
    code = models.CharField(max_length=200)
    user = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.user.code}"
