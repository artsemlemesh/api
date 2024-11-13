import mock
import factory
# from freezegun import freeze_time
from faker import Faker

from django.test import TestCase, Client
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework import status

from app import factories
from app.utils.base import generate_photo_file


User = get_user_model()


class TestBase(TestCase):
    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.client = Client()
        self.raw_password = 'bynde123'
        self.invalid_raw_password = '123'
        self.photo = generate_photo_file(image_type='png')
        user, created = User.objects.get_or_create(email='vinay@bynde.com')
        if created:
            user.set_password(self.raw_password)
            user.is_active = True
            user.save()
        self.user = user

    def test_root_url(self):
        response = self.client.get(reverse('app:schema-swagger-ui'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.user)
        response = self.client.get(reverse('app:schema-swagger-ui'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# @freeze_time('2020-07-03 00:54:00', tz_offset=0)
@override_settings(
    UNITTEST_MODE=True,
    CACHES={"default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache"
    }}
)
class AuthenticatedUserTestBase(APITestCase):
    SUPER_USER: bool = False
    fake_factory = Faker()

    def setUp(self):
        """
        Setting up User and Listing data before running the tests
        """
        email = self.fake_factory.email()
        password = self.fake_factory.password()

        # Creating and Authenticating user
        if self.SUPER_USER:
            self.user = User.objects.create_superuser(
                email=email, password=password)
        else:
            self.user = User.objects.create(
                email=email, password=password, is_active=True
            )

        # NOTE: Is this required as superuser?
        # self.address_line_1 = "L1"
        # self.city = "NY"
        # self.state = "CF"
        # self.postal_code = "540000"
        # self.country = "US"
        # self.user.save()
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    @property
    def fs(self):
        return factories

    @mock.patch(settings.DEFAULT_FILE_STORAGE, FileSystemStorage)
    def _generate_image_file(self, filename: str, extension: str):
        file = ContentFile(
            factory.django.ImageField()._make_data(
                {'width': 1024, 'height': 768}
            ), f'{filename}.{extension}'
        )
        return file

    def logout(self):
        response = self.client.post(reverse('app:logout'), {})
        self.assertEqual(response.status_code, 200)
