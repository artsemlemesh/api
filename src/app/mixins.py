
"""
A mixin which provides some helper classes for User app
"""
import json

from django.conf import settings
from django.core.serializers import serialize
from rest_framework.exceptions import PermissionDenied
from oauth2client.client import OAuth2WebServerFlow

from .models import SocialProfile
from .models.expiring import ExpiringToken


class UserSerializerMixin(object):
    """
    This class provide helper methods for user related serializers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = self.context['request']
        self.user = None

    def get_data(self):
        """
        Serialize user and its related objects.
        A serializer must provide self.user to consume this method
        """

        # TODO: This method or mixin should be removed later.
        # This is what serializer does!

        user = serialize('json', [self.user])
        user = json.loads(user)[0]['fields']
        user.pop('password')
        profiles = serialize(
            'json', SocialProfile.objects.filter(user=self.user))
        profiles = json.loads(profiles)
        user['social_profiles'] = [profiles[i]['fields']
                                   for i in range(len(profiles))]
        user['token'] = self.user.auth_token.key
        user['id'] = self.user.id
        user['is_stripe_connected'] = self.user.is_stripe_connected

        if self.user.photo:
            user['photo'] = self.request.build_absolute_uri(
                self.user.photo.url)
            user['thumbnail'] = self.user.thumbnail
            user['stripe_account'] = {}

        user['google_authorization_url'] = get_google_authorization_url()

        return user

    def generate_auth_token(self):
        token, _ = ExpiringToken.objects.get_or_create(user=self.user)

        if token.is_expired:
            # If the token is expired then delete and generate a new one.
            token.delete()
            ExpiringToken.objects.create(user=self.user)


def get_google_authorization_url():
    scopes = 'https://www.googleapis.com/auth/calendar.readonly'
    flow = OAuth2WebServerFlow(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scope=scopes,
        redirect_uri=f'{settings.SITE_URL}/settings/calendar',
        prompt='consent',
        include_granted_scopes='true',
        access_type='offline'
    )
    return flow.step1_get_authorize_url()


class OwnershipMixin(object):
    """
    Mixin providing a dispatch overload that checks object ownership. is_staff
    and is_supervisor are considered object owners as well.
    This mixin must be loaded before any class based views
    are loaded for example class SomeView(OwnershipMixin, ListView)
    """

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        # we need to manually "wake up" self.request.user
        # which is still a SimpleLazyObject at this point
        # and manually obtain this object's owner information.
        current_user = self.request.user._wrapped if hasattr(
            self.request.user, '_wrapped') else self.request.user
        object_owner = getattr(self.get_object(), 'author')

        if current_user != object_owner and not current_user.is_superuser and\
                not current_user.is_staff:
            raise PermissionDenied
        return super(OwnershipMixin, self).dispatch(request, *args, **kwargs)
