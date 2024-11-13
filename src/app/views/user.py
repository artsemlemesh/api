from django.shortcuts import redirect
from django.utils.encoding import smart_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import password_changed, validate_password
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.utils.decorators import method_decorator
from django.utils.encoding import DjangoUnicodeDecodeError, force_str
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from requests.exceptions import HTTPError
from rest_framework import generics, mixins, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from social_core.backends.oauth import BaseOAuth2
from social_core.exceptions import AuthForbidden, AuthTokenError, MissingBackend
from social_django.utils import load_backend, load_strategy
from rest_framework.authtoken.models import Token
from app import models
from app.mixins import UserSerializerMixin
from app.serializers.user import (
    RegisterSerializer,
    GoogleOneTapLoginSerializer,
    AppleLoginSerializer,
    LoginSerializer,
    ProfileSerializer,
    ExpressDashboardSerializer,
    SocialAuthLoginSerializer,
    ConfirmCodeSerializer,
    AppleLoginSerializerMobile,
)
from dj_rest_auth.views import LoginView
from app.constants.status import PRODUCT_STATUS
from app.models.expiring import ExpiringToken
from ..serializers.user import ExpoPushNotification
import stripe

# https://simpleisbetterthancomplex.com/tutorial/2016/11/28/how-to-filter-querysets-dynamically.html
from django.conf import settings
from ..serializers.user import ExpoPushNotification
from rest_framework import viewsets
from ..utils.notification import send_push_message

sensitive_post_method = sensitive_post_parameters("password")


@method_decorator(sensitive_post_method, name="dispatch")
class Register(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    model = get_user_model()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["url_params"] = self.kwargs
        return context


class ExpoPushNotificationView(viewsets.ViewSet):
    def update(self, request):
        user_email = request.data.get("email")
        try:
            res = get_user_model().objects.get(email=user_email)
        except Exception as e:
            return Response("Email Not Found", status=status.HTTP_400_BAD_REQUEST)
        serializer = ExpoPushNotification(res, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"token": "Token saved"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestDeploy(viewsets.ViewSet):
    def update(self, request):
        return Response(
            {"Data": "Dummy data new Zahid"}, status=status.HTTP_201_CREATED
        )


class ConfirmCodeAPIView(generics.UpdateAPIView):
    serializer_class = ConfirmCodeSerializer
    permission_classes = ()
    queryset = get_user_model().objects.all()

    def get_object(self):
        email = self.request.data.get("email")
        return self.queryset.get(email__iexact=email)


class RefreshTokenView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ["put"]

    def update(self, request):
        token, _ = ExpiringToken.objects.get_or_create(user=request.user)
        if token.should_refresh:
            token.delete()
            token = ExpiringToken.objects.create(user=request.user)
        return Response(status=status.HTTP_200_OK, data={'token': token.key})


class LoginSocial(generics.CreateAPIView):
    class LoginSocialSerializer(UserSerializerMixin, serializers.ModelSerializer):
        PROVIDER_CHOICES = (("facebook", "Facebook"), ("google", "Google"))

        email = serializers.EmailField()
        provider_name = serializers.ChoiceField(choices=PROVIDER_CHOICES)
        provider_id = serializers.CharField(max_length=50)
        access_token = serializers.CharField(max_length=350)

        class Meta:
            model = get_user_model()
            read_only_fields = (
                "phone",
                "is_superuser",
                "is_staff",
                "is_active",
                "date_joined",
                "last_login",
                "groups",
                "user_permissions",
                "photo",
            )
            exclude = ("password",)

        def create(self, validated_data):
            user, _ = get_user_model().objects.update_or_create(
                email=self.validated_data.get("email"),
                defaults={
                    "first_name": self.validated_data.get("first_name"),
                    "last_name": self.validated_data.get("last_name"),
                    "email": self.validated_data.get("email"),
                    "is_active": True,
                },
            )
            self.user = user
            self.create_social_profile()
            self.generate_auth_token()
            return user

        def create_social_profile(self):
            provider_id = self.validated_data.pop("provider_id")
            provider_name = self.validated_data.pop("provider_name")
            access_token = self.validated_data.pop("access_token")
            models.SocialProfile.objects.update_or_create(
                user=self.user,
                provider_name=provider_name,
                defaults={
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "access_token": access_token,
                },
            )

    serializer_class = LoginSocialSerializer
    model = get_user_model()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.get_data())


class Login(LoginView):
    serializer_class = LoginSerializer
    token_model = models.ExpiringToken

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        data = response.data
        return Response({"id": request.user.id, "token": data["key"]})


class VerifyEmail(generics.GenericAPIView):
    class VerifyEmailSerializer(UserSerializerMixin, serializers.Serializer):
        class Meta:
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.user = None
            self.request = self.context["request"]

        def validate(self, data):
            """
            This is used for both email verification when new user is
            registered and when user change existing email
            For newly registered user there will be just uid and token passed
            as url kwargs
            For email changed, there will be uid, token and new_email url
            kwargs based on whether new_email kwarg is passed
            we'll either mark active=True or change existing email to new_email
            """
            url_params = self.context["url_params"]
            token = url_params.get("token")
            uid = url_params.get("uid")
            new_email = url_params.get("new_email")
            if new_email:
                new_email = force_str(urlsafe_base64_decode(new_email))

            try:
                token = force_str(token)
                user_pk = smart_str(urlsafe_base64_decode(uid))
                self.user = get_user_model().objects.get(pk=user_pk)
                check_token = token_generator.check_token(self.user, token)

                if check_token:
                    return data
                else:
                    raise ValidationError(
                        detail="Link was expired. Please try to login to resend "
                               "email verification link."
                    )
                # ExpiringTokenModel = apps.get_model('app', 'ExpiringToken')
                # token = ExpiringTokenModel.objects.get(key=token)
                # user = token.user
            except get_user_model().DoesNotExist:
                raise ValidationError(detail="User does not exist")
            except DjangoUnicodeDecodeError:
                raise ValidationError(
                    detail="Link was expired. Please try to login to resend "
                           "email verification link."
                )

            # is_token_valid = token_generator.check_token(user, token)

            if not token.is_expired:
                self.user.email = new_email if new_email else self.user.email
                return data
            elif new_email:
                # send verification email to newly updated email
                self.user.send_email_updated_email(new_email=new_email)
                raise ValidationError(
                    detail="Link was expired. Please check your inbox again."
                )
            else:
                # send verification to newly registered email
                self.user.send_verification_email()
                raise ValidationError(
                    detail="Link was expired. Please check your inbox again."
                )

        def activate_account(self):
            self.user.is_active = True
            self.user.save()

    serializer_class = VerifyEmailSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.activate_account()
        return Response(serializer.get_data())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["url_params"] = self.kwargs
        return context


class ForgotPassword(generics.GenericAPIView):
    class ForgotPasswordSerializer(serializers.Serializer):
        email = serializers.EmailField()

        class Meta:
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.request = self.context["request"]

        def validate(self, data):
            try:
                user = get_user_model().objects.get(email=data.get("email"))
                user.send_forgot_password_email()
            except get_user_model().DoesNotExist:
                raise ValidationError(detail="Email does not exist")

            return data

    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"message": "Password reset link has been sent to your inbox."})


sensitive_post_method = sensitive_post_parameters("new_password", "confirm_password")


class Suggested_brands(generics.GenericAPIView):
    class suggestedbrandSerializer(serializers.Serializer):
        email = serializers.EmailField()

        class Meta:
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.request = self.context["request"]

        def validate(self, data):
            try:
                user = get_user_model().objects.get(email=data.get("email"))
                user.send_suggested_brands()
            except get_user_model().DoesNotExist:
                raise ValidationError(detail="Email does not exist")

            return data

    serializer_class = suggestedbrandSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"message": "Sugessted Brands sent to admin for review."})


@method_decorator(sensitive_post_method, name="dispatch")
class ResetPassword(generics.GenericAPIView):
    class ResetPasswordSerializer(serializers.Serializer):
        new_password = serializers.CharField(max_length=200)
        confirm_password = serializers.CharField(max_length=200)

        class Meta:
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.user = None
            self.request = self.context["request"]

        def validate_link(self):
            url_params = self.context["url_params"]
            uid = url_params.get("uid")
            token = url_params.get("token")
            try:
                user_id = force_str(urlsafe_base64_decode(uid))
                user = get_user_model().objects.get(id=user_id)
            except get_user_model().DoesNotExist:
                raise ValidationError(detail="User does not exist")
            except DjangoUnicodeDecodeError:
                raise ValidationError(
                    detail="Link was expired. Please resend "
                           "link from forgot password"
                )

            check_token = token_generator.check_token(user, token)

            if check_token:
                self.user = user
            else:
                user.send_forgot_password_email()
                raise ValidationError(
                    detail="Link was expired. Please check your inbox again."
                )

        def validate_new_password(self, new_password):
            data = self.initial_data
            if new_password != data.get("confirm_password"):
                raise ValidationError("Passwords do not match.")

            if validate_password(new_password) is None:
                return new_password

        def reset_password(self):
            self.user.set_password(self.validated_data.get("new_password"))
            self.user.save()

    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.validate_link()
        serializer.is_valid(raise_exception=True)
        serializer.reset_password()
        return Response({"message": "Your password has been reset."})

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["url_params"] = self.kwargs
        return context


@method_decorator(sensitive_post_method, name="dispatch")
class ChangePassword(generics.GenericAPIView):
    class ChangePasswordSerializer(serializers.Serializer):
        current_password = serializers.CharField(max_length=200)
        new_password = serializers.CharField(max_length=200)
        confirm_new_password = serializers.CharField(max_length=200)

        class Meta:
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.user = self.context["request"].user

        def validate(self, data):
            if not self.user.check_password(data.get("current_password")):
                raise ValidationError("Your current password is invalid")

            new_password = data.get("new_password")
            if data.get("new_password") != data.get("confirm_new_password"):
                raise ValidationError("Passwords do not match.")

            # validate password length, strong etc
            validate_password(new_password, user=self.user)
            return data

        def change_password(self):
            new_password = self.validated_data.get("new_password")
            self.user.set_password(new_password)
            self.user.save()
            password_changed(new_password)

    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.change_password()
        return Response({"message": "Your password has been changed."})


class ReSendEmail(generics.GenericAPIView):
    class ReSendEmailSerializer(serializers.Serializer):
        """
        This serializer is used for re send verification email if newly
        registered user has missed already sent email and want to resent
        This is also used for re send verification email if user has changed
        existing email and has missed verification email sent first time
        and want to resend
        """

        email = serializers.EmailField()
        user = serializers.PrimaryKeyRelatedField(
            queryset=get_user_model().objects.all(), required=False, allow_null=True
        )

        class Meta:
            fields = "__all__"

        def validate(self, data):
            user = data.get("user")
            if user:
                user.send_email_updated_email(new_email=data.get("email"))
            else:
                try:
                    user = get_user_model().objects.get(email=data.get("email"))
                    user.send_verification_email()
                except get_user_model().DoesNotExist:
                    pass

            return data

    serializer_class = ReSendEmailSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"message": "Verification email sent to your inbox."})


class RemoveUser(generics.UpdateAPIView):
    class RemoveUserSerializer(UserSerializerMixin, serializers.ModelSerializer):
        is_active = serializers.BooleanField()

        class Meta:
            model = get_user_model()
            fields = ("is_active",)

    serializer_class = RemoveUserSerializer
    queryset = get_user_model().objects.all()
    permission_classes = (IsAuthenticated,)
    http_method_names = ["put"]


class ProfileAPIView(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, generics.GenericAPIView
):
    http_method_names = [
        "get",
        "put",
        "patch",
        "options",
    ]
    queryset = get_user_model().objects.none()
    serializer_class = ProfileSerializer
    # authentication_classes = (TokenAuthentication, )
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        print("request", request.GET)
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        res = super().partial_update(request, *args, **kwargs)
        return res


class ExpressDashboardRefreshAPIView(mixins.UpdateModelMixin, generics.GenericAPIView):
    http_method_names = ["post"]
    queryset = get_user_model().objects.none()
    serializer_class = ExpressDashboardSerializer
    # authentication_classes = (TokenAuthentication, )
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class StripeAccountLink(mixins.RetrieveModelMixin, generics.GenericAPIView):
    http_method_names = ["get"]
    queryset = get_user_model().objects.none()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        if self.request.user.account is None:
            return Response({})
        print(self.request.user.account.id)
        account_links = stripe.AccountLink.create(
            account=self.request.user.account.id,
            refresh_url=request.build_absolute_uri(reverse("app:stripe-refresh")),
            return_url=request.build_absolute_uri(reverse("app:stripe-return")),
            type="account_onboarding",
            collect="currently_due",
        )
        print(account_links)
        return Response(account_links)


class StripeBalance(mixins.RetrieveModelMixin, generics.GenericAPIView):
    http_method_names = ["get"]
    queryset = get_user_model().objects.none()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        if self.request.user.account is None:
            return Response({})

        balance = stripe.Balance.retrieve(stripe_account=self.request.user.account.id)
        return Response(balance)


class DeleteSocialProfile(generics.RetrieveDestroyAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.SocialProfile
            fields = ("provider_id", "provider_name", "access_token")
            read_only_fields = ("user",)
            ref_name = "DeleteSocialProfile"

        def create(self, validated_data):
            validated_data["user"] = self.context["request"].user
            return super().create(validated_data)

        @property
        def data(self):
            data = super().data
            data["id"] = models.SocialProfile.objects.get(
                user_id=self.context["request"].user,
                provider_name=data["provider_name"],
            ).id
            data["user"] = self.context["request"].user.id
            return data

    serializer_class = InputSerializer
    queryset = models.SocialProfile.objects.all()
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        id = instance.pk
        self.perform_destroy(instance)
        return Response({"id": id}, status=status.HTTP_200_OK)


class DeleteProfile(generics.DestroyAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.User
            fields = ("email",)
            ref_name = "DeleteProfile"

    serializer_class = InputSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = models.User.objects.filter(email=self.request.user.email)
        return queryset

    def destroy(self, request, *args, **kwargs):
        user = self.request.user

        listings = models.Listing.objects.filter(created_by=user, status=PRODUCT_STATUS.published)
        for listing in listings:
            listing.status = PRODUCT_STATUS.draft
            listing.save()

        user.is_deleted = True
        user.email = f"{user.email}_{user.id}_deleted"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.save()
        Token.objects.filter(user=user).delete()
        return Response(status=status.HTTP_200_OK, data={"message": "Profile deleted"})


class GetSocialProfile(generics.ListAPIView):
    class GetSocialProfileSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.SocialProfile
            fields = "__all__"

    serializer_class = GetSocialProfileSerializer
    queryset = models.SocialProfile.objects.all()
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return self.queryset.filter(user__id=self.kwargs.get("user_id"))


class AddSocialProfile(generics.CreateAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = models.SocialProfile
            fields = ("provider_id", "provider_name", "access_token")
            read_only_fields = ("user",)
            ref_name = "AddSocialProfile"

        def create(self, validated_data):
            validated_data["user"] = self.context["request"].user
            return super().create(validated_data)

        @property
        def data(self):
            data = super().data
            data["id"] = models.SocialProfile.objects.get(
                user_id=self.context["request"].user,
                provider_name=data["provider_name"],
            ).id
            data["user"] = self.context["request"].user.id
            return data

    serializer_class = InputSerializer
    model = models.SocialProfile

from app.utils.analytics import track_analytics
class SocialAuthLoginView(generics.GenericAPIView):
    """Login with Oauth2 providers like facebook and google"""

    serializer_class = SocialAuthLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        """Authenticate user through the provider and access_token"""
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.data.get("provider")
        strategy = load_strategy(request)

        try:
            backend = load_backend(strategy=strategy, name=provider, redirect_uri=None)

        except MissingBackend:
            return Response(
                {"error": "Please provide a valid provider"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if isinstance(backend, BaseOAuth2):
                access_token = serializer.data.get("access_token")
                try:
                    user = backend.do_auth(access_token, backend=backend)
                except HTTPError as error:
                    return Response(
                        {
                            "error": {
                                "access_token": "Invalid token. "
                                                "Please provide Oauth2 token",
                                "details": str(error),
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except AuthForbidden as error:
                    return Response(
                        {
                            "error": {
                                "access_token": "Invalid token",
                                "details": str(error),
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except HTTPError as error:
            return Response(
                {
                    "error": {
                        "access_token": "Invalid token. " "Please provide Oauth2 token",
                        "details": str(error),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AuthTokenError as error:
            return Response(
                {"error": "Invalid credentials", "details": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            authenticated_user = backend.do_auth(access_token, user=user)
        except HTTPError as error:
            return Response(
                {"error": "invalid token", "details": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AuthForbidden as error:
            return Response(
                {"error": "invalid token", "details": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if authenticated_user:
            is_new_user = not authenticated_user.last_login
            authenticated_user.is_active = True
            authenticated_user.save()

            login(request, authenticated_user)
            token = self.generate_auth_token(authenticated_user)
            serializer_data = ProfileSerializer(authenticated_user).data
            serializer_data.update({"token": str(token)})
            if is_new_user:
                # Added analytics tracking here
                try:
                    track_analytics(
                        authenticated_user.email,
                        'User Created',
                        {
                            'email': authenticated_user.email,
                            'first_name': authenticated_user.first_name,
                            'last_name': authenticated_user.last_name,
                            'user_id': authenticated_user.id,
                            'env': settings.ENVIRONMENT.lower(),
                            'provider': provider,  
                            'method': 'oauth2'
                        }
                    )
                    print(f"Analytics tracked for user login: {authenticated_user.email}")
                except Exception as e:
                    print(f"Error tracking analytics for user login: {str(e)}")
            return Response(status=status.HTTP_200_OK, data=serializer_data)

        return Response(
            {"error": "Invalid Credentials", "detials": "Invalid Token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def generate_auth_token(self, user):
        token, _ = ExpiringToken.objects.get_or_create(user=user)

        if token.is_expired:
            # If the token is expired then delete and generate a new one.
            token.delete()
            token = ExpiringToken.objects.create(user=user)
        return token


class GoogleOneTapLoginView(generics.CreateAPIView):
    serializer_class = GoogleOneTapLoginSerializer
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK
        return response


class AppleLoginView(generics.CreateAPIView):
    serializer_class = AppleLoginSerializer
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK
        token = response.data["token"]
        if token is not None:
            url = f"{settings.SITE_URL}/social/apple?code=" + token
            response = redirect(url)
            return response
        else:
            url = f"{settings.SITE_URL}"
            response = redirect(url)
            return response


class AppleLoginViewMobile(generics.CreateAPIView):
    serializer_class = AppleLoginSerializerMobile
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        try:
            request.data['first_name'] = request.data['first_name'] if request.data['first_name'] else 'Apple'
            request.data['last_name'] = request.data['last_name'] if request.data['last_name'] else 'User'
            response = super().post(request, *args, **kwargs)
            response.status_code = status.HTTP_200_OK
            return response
        except Exception as e:
            print('error', e)
            return Response(status=status.HTTP_400_BAD_REQUEST)
