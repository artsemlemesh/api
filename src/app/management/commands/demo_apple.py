import jwt
import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.management import BaseCommand


ACCESS_TOKEN_URL = 'https://appleid.apple.com/auth/token'


# TODO: you paste your code you get from redirect.
access_token = 'c792800b63c584823976aa027f430ac28.0.nrxs.ebXa8DH4htCRajOlAukzyw'


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        client_id, client_secret = self.get_key_and_secret()

        headers = {'content-type': "application/x-www-form-urlencoded"}
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': access_token,
            'grant_type': 'authorization_code',
        }

        res = requests.post(ACCESS_TOKEN_URL, data=data, headers=headers)
        response_dict = res.json()
        id_token = response_dict.get('id_token', None)

        if id_token:
            decoded = jwt.decode(id_token, '', verify=False)
            email = decoded.get('email')
            user_id = decoded['sub']
            print(f'{user_id} => {email}')
        else:
            raise Exception()

        # TODO: Now create user with the given email.

        return True

    def get_key_and_secret(self):
        headers = {
            'kid': settings.SOCIAL_AUTH_APPLE_KEY_ID
        }

        payload = {
            'iss': settings.SOCIAL_AUTH_APPLE_TEAM_ID,
            'iat': timezone.now(),
            'exp': timezone.now() + timedelta(days=180),
            'aud': 'https://appleid.apple.com',
            'sub': settings.SOCIAL_AUTH_APPLE_CLIENT_ID,
        }

        client_secret = jwt.encode(
            payload,
            settings.SOCIAL_AUTH_APPLE_PRIVATE_KEY,
            algorithm='ES256',
            headers=headers
        ).decode("utf-8")

        return settings.SOCIAL_AUTH_APPLE_CLIENT_ID, client_secret
