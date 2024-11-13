"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include, re_path
from django.urls import re_path

from rest_framework_nested import routers
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from . import views
from .tasks import create_shipments_in_batch
from .views.hooks import stripe_webhook, easypost_webhook
from .views import shipping_hooks
from .views import ExpoPushNotificationView
app_name = "app"


schema_view = get_schema_view(
    openapi.Info(
        title="Bynde API",
        default_version="v1",
        description="Baby Clothing Bundles",
        terms_of_service="https://bynde.com/terms/",
        contact=openapi.Contact(email="vinay@bynde.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.IsAuthenticated,),
    authentication_classes=(SessionAuthentication,),
)


# USER
urlpatterns = [
    # Auth
    path("auth/register", views.Register.as_view(), name="register"),
    path("auth/confirm", views.ConfirmCodeAPIView.as_view(), name="confirm-code"),
    path("auth/login", views.Login.as_view(), name="login"),
    path("auth/logout", views.LogoutView.as_view(), name="logout"),
    path("auth/forgot", views.ForgotPassword.as_view(), name="forgot-password"),
    path("auth/token/refresh", views.RefreshTokenView.as_view(), name="refresh-token"),
    re_path(
        r"^auth/reset/(?P<uid>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z\-]+)$",
        views.ResetPassword.as_view(),
        name="reset-password",
    ),
    # admin notify url
    path("auth/notify", views.Suggested_brands.as_view(), name="suggested-brands"),
    # path('auth/notifyuser', views.Suggested_brands.as_view(), name='suggested-brands'),
    # verification email for new registration
    re_path(
        r"^auth/verify/" r"(?P<uid>[0-9A-Za-z_\-]+)/" r"(?P<token>[0-9A-Za-z\-]+)$",
        views.VerifyEmail.as_view(),
        name="verify-email",
    ),
    # verification email if existing user change email
    re_path(
        r"^auth/verify/"
        r"(?P<uid>[0-9A-Za-z_\-]+)/"
        r"(?P<token>[0-9A-Za-z\-]+)/"
        r"(?P<new_email>[0-9A-Za-z\-]+)$",
        views.VerifyEmail.as_view(),
        name="verify-changed-email",
    ),
    path(
        r"auth/change-password", views.ChangePassword.as_view(), name="change-password"
    ),
    path("auth/resend", views.ReSendEmail.as_view(), name="re-send-email"),
    # Social
    path(
        "auth/oauth2/login", views.SocialAuthLoginView.as_view(), name="oauth2-signup"
    ),
    path(
        "auth/social/google-tap",
        views.GoogleOneTapLoginView.as_view(),
        name="google-tap",
    ),
    path("auth/social/apple", views.AppleLoginView.as_view(), name="apple-login"),
    path(
        "auth/social/apple/mobile",
        views.AppleLoginViewMobile.as_view(),
        name="apple-login-mobile",
    ),
    path("auth/social/login", views.LoginSocial.as_view(), name="register-social"),
    path(
        "auth/social/connect",
        views.AddSocialProfile.as_view(),
        name="add-social-profile",
    ),
    path("auth/social/<uid>", views.GetSocialProfile.as_view(),
         name="social-profile"),
    path(
        "auth/social/<uid>/delete",
        views.DeleteSocialProfile.as_view(),
        name="delete-social-profile",
    ),
    # Users
    re_path(r"^profile$", views.ProfileAPIView.as_view(), name="profile_view"),
    re_path(r"^profile/delete$", views.DeleteProfile.as_view(),
            name="profile_delete"),
    re_path(
        r"^profile/account$",
        views.ByndeStripeAccountUpdateAPIView.as_view(),
        name="stripe_account_view",
    ),
    re_path(
        r"^profile/stripe-account-link$",
        views.StripeAccountLink.as_view(),
        name="stripe_account_link",
    ),
    re_path(
        r"^profile/stripe-balance$",
        views.StripeBalance.as_view(),
        name="stripe_balance",
    ),
    re_path(
        r"^profile/express$",
        views.ExpressDashboardRefreshAPIView.as_view(),
        name="stripe_express_dashboard",
    ),
    # Notification Endpoint
    path("notification/",
         views.ExpoPushNotificationView.as_view({"post": "update"})),
    path("test-deploy/", views.TestDeploy.as_view({"get": "update"})),
]

# LISTING
router = routers.SimpleRouter()
router.register("products", views.ProductViewSet, basename="product")
# router.register("listing-image", views.SellingImageViewSet,
#                 basename="selling_images")
# router.register("sellings", views.SellingViewSet, basename="selling")
# router.register(
#     "listing-reports", views.ListingReportViewSet, basename="listing-reports"
# ),
# router.register(
#     "listing-ratings", views.ListingRatingViewSet, basename="listing-ratings"
# ),
router.register(
    "expo-notificiation", views.ExpoPushNotificationView, basename="notification"
)
# router.register('listing-item-categories', views.ProductCategoryViewSet,
#                 basename='listing-item-categories'),
# router.register('listing-item-brands', views.ProductBrandViewSet,
#                 basename='listing-item-brands'),
# router.register('listing-item-sizes', views.ProductSizeViewSet,
#                 basename='listing-item-sizes'),

# items_router = routers.NestedSimpleRouter(
#     router, r"sellings", lookup="listing")
# items_router.register(r"items", views.SellingItemViewSet,
#                       basename="selling-item")

# Buyer orders
router.register("orders", views.BuyerOrdersViewSet, basename="orders")
router.register("buyerorder", views.BuyerOrderItemViewSet,
                basename="buyerorder")

# Seller sales
router.register("sales", views.SellerOrderItemViewSet, basename="sales")

# Feedback
router.register('feedback', views.FeedbackViewSet, basename='feedback')

urlpatterns += [
    re_path(r"^", include(router.urls)),
    # re_path(r"^", include(items_router.urls)),
    path('products/<int:pk>/add-favorite/', views.AddFavoriteAPIView.as_view(), name='add-favorite'),
    path('products/<int:pk>/remove-favorite/', views.RemoveFavoriteAPIView.as_view(), name='remove-favorite'),


]

# STRIPE - (stripe/webhook)
urlpatterns += [
    path("stripe/refresh", views.StripeRefreshView.as_view(), name="stripe-refresh"),
    path("stripe/return", views.StripeReturnView.as_view(), name="stripe-return"),
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    path("webhooks/stripe", stripe_webhook, name="stripe_webhook"),
    # path('easypost',create_shipments_in_batch,name = 'batch')
]

# EasyPOST webhook
urlpatterns += [
    path("webhooks/easypost", easypost_webhook, name="easypost_webhook"),
]

# EasyShip - (webhook)
urlpatterns += [
    path("eship/", shipping_hooks.eship_hook, name="eship_hook"),
]

# SWAGGER
urlpatterns += [
    re_path(
        r"^(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]
