import json

import jwt
import requests
from typing import Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import (
    serializers, exceptions
)
from dj_rest_auth.serializers import LoginSerializer
from app.utils import Base64ImageField, inline_serializer
from app.mixins import UserSerializerMixin
from app.tasks import hubspot_user_signup
from app.models.expiring import ExpiringToken
from app.models.user import AppleLoginSerialzerModel
from rest_framework.response import Response
from app.utils.analytics import track_analytics
class RegisterSerializer(UserSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'write_only': True},
            'password': {'write_only': True}
        }

    @staticmethod
    def validate_password(password):
        if validate_password(password) is None:
            return password

    @staticmethod
    def validate_email(email):
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise exceptions.ValidationError('A user already exists with this email')

        return email

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['email'] = self.__class__.validate_email(attrs.pop('email'))
        attrs['password'] = self.__class__.validate_password(attrs.pop('password'))
        return attrs

    def create(self, validated_data):
        
        email = validated_data.get('email')
        environment =  settings.ENVIRONMENT
        
        user = get_user_model().objects.create_user(**validated_data)
        user.is_active = False
        
        # Conditionally set the verification code based on environment and email
        if environment == 'STAGING':
            user.code = '1234'
        else:
            user.reset_confirm_code()
        user.save()
        track_analytics(
            user.email,
            'User Created',
            {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_id': user.id,
                'env': environment.lower(),
            }
        )

        self.user = user

        # NOTE: Sending email address to the user and admin
        transaction.on_commit(
            lambda: (
                user.send_verification_email(),
                user.send_update_email_to_admin()
            )
        )

        # hubspot = HubspotWrapper()
        # hubspot.user_signup(user)
        hubspot_user_signup(user)

        return user


class LoginSerializer(LoginSerializer):
    class Meta:
        fields = ('email', 'password', 'token', )

    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        UserModel = get_user_model()
        user = None

        if 'allauth' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            user = self._validate_email(email, password)
        else:
            # Authentication without using allauth
            if email:
                try:
                    username = UserModel.objects.get(email__iexact=email).get_username()
                except UserModel.DoesNotExist:
                    pass

            if username:
                user = self._validate_username_email(username, '', password)

        # Did we get back an active user?
        if user and not user.is_deleted:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise exceptions.ValidationError(msg)

            token, created = ExpiringToken.objects.get_or_create(user=user)
            if token.is_expired:
                # If the token is expired then delete and generate a new one.
                token.delete()
                ExpiringToken.objects.create(user=user)
        else:
            msg = _('Unable to log in with provided credentials.')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('E-mail is not verified.'))

        attrs['user'] = user
        return attrs

class ExpoPushNotification(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('expo_push_token',)

class ConfirmCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'code', )
        extra_kwargs = {
            'email': {'write_only': True},
            'code': {'write_only': True}
        }

    def validate(self, attrs):
        if self.instance.is_anonymous:
            raise serializers.ValidationError(_('Not authorized.'))
        if self.instance.is_active:
            raise serializers.ValidationError(_('You already confirmed.'))
        code = attrs['code']
        if(code == None):
            print("Code not found")
            raise serializers.ValidationError(_('Code not given.'))
        if self.instance.code != code:
            if self.instance.code_failed_count < settings.AUTH_CODE_CONFIRM_FAILURE_MAX:
                self.instance.code_failed_count += 1
                self.instance.save()
            else:
                self.instance.reset_confirm_code()
                self.instance.send_verification_email()
                self.instance.save()
            raise serializers.ValidationError(_('Invalid Code!'))

        return attrs

    def update(self, instance, validated_data):
        instance.code = None
        instance.is_active = True
        instance.code_failed_count = 0
        instance.save()

        return instance


class ProfileSerializer(serializers.ModelSerializer):
    photo = Base64ImageField(
        max_length=None, use_url=True, required=False)
    account = inline_serializer(many=False, fields={
        'email': serializers.CharField(),
        'company': serializers.JSONField(),
        'requirements': serializers.JSONField()
    })

    class Meta:
        model = get_user_model()
        fields = (
            'pk', 'email', 'first_name', 'last_name',
            'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
            'phone', 'photo', 'thumbnail', 'express_dashboard',
            'expo_push_token', 'created_date', 'is_stripe_connected', 'account'
        )
        read_only_fields = ('email', 'created_date', 'thumbnail', 'account')


class ExpressDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('express_dashboard', )
        extra_kwargs = {
            'express_dashboard': {'read_only': True}
        }

    @property
    def __current_user(self):
        return self.context['request'].user

    def validate(self, attrs):
        if not self.__current_user.account:
            raise serializers.ValidationError(_(
                'Stripe account not connected!'))
        elif self.__current_user.account.type != 'express':
            raise serializers.ValidationError(_(
                'Stripe Express type account only has the dashboard!'))

        try:
            self.instance.get_express_dashboard_url(True)
        except Exception as e:
            raise serializers.ValidationError(e.user_message)
        return attrs


SOCIAL_PROVIDER_CHOICES = (
    ('google-oauth2', 'Google'),
    ('facebook', 'Facebook'),
)


class SocialAuthLoginSerializer(serializers.Serializer):
    """
    Serializer which accepts an OAuth2 access token and provider.
    """
    provider = serializers.ChoiceField(
        choices=SOCIAL_PROVIDER_CHOICES, required=True,
        help_text="values are : google-oauth2 and facebook"
    )
    access_token = serializers.CharField(
        max_length=4096, required=True, trim_whitespace=True,
        help_text="Access token is provided by Facebook, Google, etc"
    )


class GoogleOneTapLoginSerializer(serializers.ModelSerializer):
    credential = serializers.CharField(write_only=True, required=True)
    token = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('credential', 'token', )

    def validate_credential(self, credential: str):
        try:
            decoded_credentials = jwt.decode(credential, verify=False)
        except Exception as e:
            raise serializers.ValidationError({'credential': 'Invalid credential.'})

        required_keys = (
            'exp', 'iat', 'nbf', 'email_verified', 'iss', 'azp',
            'aud', 'email', 'given_name', 'family_name',
        )
        for key in required_keys:
            if key not in decoded_credentials:
                raise serializers.ValidationError({
                    'credential': f'Invalid credential ({key} is missing.)'
                })

        if not decoded_credentials['email_verified']:
            raise serializers.ValidationError({'credential': 'Not verified.'})

        if decoded_credentials['iss'] != settings.SOCIAL_AUTH_GOOGLE_ISSUER \
                or decoded_credentials['azp'] != settings.FRONTEND_GOOGLE_CLIENT_ID \
                or decoded_credentials['aud'] != settings.FRONTEND_GOOGLE_CLIENT_ID:
            raise serializers.ValidationError({'credential': 'Not authorized credential'})

        if not settings.UNITTEST_MODE:
            # NOTE: We skip time validation in unittest
            now = datetime.now()
            if datetime.fromtimestamp(decoded_credentials['exp']) < now\
                    or datetime.fromtimestamp(decoded_credentials['iat']) > now\
                    or datetime.fromtimestamp(decoded_credentials['nbf']) > now:
                raise serializers.ValidationError({'credential': 'Expired.'})

        self.email = decoded_credentials['email']
        self.given_name = decoded_credentials['given_name']
        self.family_name = decoded_credentials['family_name']
        self.picture_url = decoded_credentials.get('picture')

        return credential

    def validate(self, attrs):
        attrs = super().validate(attrs)

        return attrs

    def get_token(self, obj):
        return obj.auth_token.key

    def create(self, validated_data):
        UserModel = get_user_model()
        if UserModel.objects.filter(email__iexact=self.email).exists():
            self.instance = UserModel.objects.get(email__iexact=self.email)
        else:
            self.instance = UserModel.objects.create_user(
                email=self.email,
                first_name=self.given_name,
                last_name=self.family_name,
                photo=self.picture_url
            )
        return self.instance

class AppleLoginSerializerMobile(serializers.ModelSerializer):
    ACCESS_TOKEN_URL = 'https://appleid.apple.com/auth/token'

    access_token = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    token = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('access_token', 'first_name', 'last_name', 'token', 'is_active',)

    def __get_key_and_secret(self) -> Tuple[str, str]:
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
        )

        return settings.SOCIAL_AUTH_APPLE_CLIENT_ID, client_secret

    def validate_access_token(self, access_token: str):
        client_id, client_secret = self.__get_key_and_secret()

        headers = {'content-type': "application/x-www-form-urlencoded"}
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': access_token,
            'grant_type': 'authorization_code',
        }

        try:
            res = requests.post(self.ACCESS_TOKEN_URL, data=data, headers=headers)
            res.raise_for_status()
            response_dict = res.json()
            id_token = response_dict.get('id_token')

            if not id_token:
                raise serializers.ValidationError('Invalid token')

            decoded = jwt.decode(id_token, options={"verify_signature": False})
            email = decoded.get('email')

            if not email:
                raise serializers.ValidationError('Cannot get email address.')

            self.email = email
        except requests.exceptions.RequestException as e:
            raise serializers.ValidationError(f'Apple API error: {e}')

        return access_token

    def get_token(self, obj):
        return obj.auth_token.key

    def create(self, validated_data):
        UserModel = get_user_model()
        email = self.email
        if UserModel.objects.filter(email__iexact=email).exists():
            instance = UserModel.objects.get(email__iexact=email)
            token, created = ExpiringToken.objects.get_or_create(user=instance)
            if token.should_refresh:
                token.delete()
                ExpiringToken.objects.create(user=instance)
        else:
            first_name = validated_data.get('first_name')
            last_name = validated_data.get('last_name')
            instance = UserModel.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            track_analytics(
                instance.email,
                'User Created',
                {
                    'email': instance.email,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'user_id': instance.id,
                    'env': settings.ENVIRONMENT.lower(),
                }
            )
        return instance

class AppleLoginSerializer(serializers.ModelSerializer):
    ACCESS_TOKEN_URL = 'https://appleid.apple.com/auth/token'
    code = serializers.CharField(write_only=True, required=True)
    user = serializers.CharField(write_only=True, required=False)
    token = serializers.SerializerMethodField()
    first_name = ''
    last_name = ''
    class Meta:
        model = AppleLoginSerialzerModel
        fields = ('code', 'user', 'token', )

    def __get_key_and_secret(self) -> Tuple[str, str]:
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
        )

        return settings.SOCIAL_AUTH_APPLE_CLIENT_ID, client_secret

    def validate_user(self, user):
        user_ = json.loads(user)
        user_data = user_['name']
        self.first_name = user_data['firstName']
        self.last_name = user_data['lastName']
        return user

    def validate_code(self, code: str):
        client_id, client_secret = self.__get_key_and_secret()

        headers = {'content-type': "application/x-www-form-urlencoded"}
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
        }
        res = requests.post(self.ACCESS_TOKEN_URL, data=data, headers=headers)
        response_dict = res.json()
        id_token = response_dict.get('id_token', None)

        if not id_token:
            raise serializers.ValidationError('Invalid token')

        decoded = jwt.decode(id_token, options={"verify_signature": False})
        if not decoded.get('email'):
            raise serializers.ValidationError('Can not get email address.')
        self.email = decoded.get('email')
        self.code = code
        return code

    def get_token(self, obj):
       try:
           auth_token = obj.auth_token.key
           return auth_token
       except:
           pass

    def create(self, validated_data):
        UserModel = get_user_model()
        if UserModel.objects.filter(email__iexact=self.email).exists():
            self.instance = UserModel.objects.get(email__iexact=self.email)
            return self.instance
        elif self.first_name !='' and self.last_name !='':
            self.instance = UserModel.objects.create_user(
                email=self.email,
                first_name=self.first_name,
                last_name=self.last_name,
                is_active=True,
            )
            return self.instance

        return Response
