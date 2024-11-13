from mptt.admin import DraggableMPTTAdmin
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token

from sorl.thumbnail.admin import AdminImageMixin

from . import models

admin.site.unregister(Group)


@admin.register(get_user_model())
class UserAdmin(BaseUserAdmin):
    list_display = ('pk', 'environment_id', 'email', 'first_name', 'last_name', 'is_active',
                    'is_address_valid', 'is_deleted', 'phone', 'photo')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {
            'fields': (
                'first_name', 'last_name', 'phone',
                'photo', 'expo_push_token')}),
        (_('Address info'), {
            'fields': (
                'address_line_1', 'address_line_2', 'city', 'state',
                'postal_code', 'country')}),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff',
                'is_superuser', 'is_google_calendar_synced', 'is_deleted',)}),
        (_('Stripe'), {
            'fields': (
                'account', 'customer'
            )
        })
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

    search_fields = ('first_name', 'last_name', 'email', 'phone',)
    list_filter = ('is_active', 'is_google_calendar_synced')
    ordering = ('email',)
    actions = ['send_verification_email']
    change_form_template = 'user/loginas-change.html'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_superuser=False)

    @staticmethod
    def social_profiles(obj):
        if models.SocialProfile.objects.filter(user=obj).count() > 0:
            url = reverse('admin:user_socialprofile_changelist')
            url = '{}?user__id__exact={}'.format(url, obj.pk)
            return format_html(mark_safe(
                '<a href="{}">{}</a>'.format(url, 'Visit here')))

    def send_verification_email(self, request, queryset):
        for user in queryset:
            user.send_verification_email()

        self.message_user(
            request,
            f'Verification email sent to {len(queryset)} user(s) successfully.'
        )

    send_verification_email.short_description = \
        "Send verification email to selected users"


class CartItemAdmin(admin.TabularInline):
    model = models.CartItem


@admin.register(models.Cart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'order_id', 'count', 'modified')
    inlines = [CartItemAdmin]


class OrderItemAdmin(admin.TabularInline):
    model = models.OrderItem
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'customer', 'platform_order_id', 'count', 'modified',)
    inlines = [OrderItemAdmin]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(models.OrderItem)
class OrderItemTempAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'status',)


@admin.register(models.SocialProfile)
class SocialUserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'provider_id', 'provider_name',
                    'access_token', 'get_user')
    fieldsets = (
        (None, {'fields': (
            'provider_id', 'provider_name', 'access_token', 'user')}),
    )

    search_fields = ('provider_name', 'user__first_name',
                     'user__last_name', 'user__email')
    ordering = ('provider_name',)
    list_filter = ('provider_name',)

    def get_user(self, obj):
        url = reverse('admin:user_user_change', args=(obj.user.pk,))
        return format_html(mark_safe(
            '<a href="{}">{}</a>'.format(url, obj.user)))

    get_user.short_description = "Related User"


@admin.register(models.GoogleSettings)
class GoogleSettingsAdmin(admin.ModelAdmin):
    list_display = ('pk', 'access_token', 'token_expiry',
                    'calendar_resource_id', 'user')


class ProductInlineAdmin(AdminImageMixin, admin.TabularInline):
    model = models.Product
    fields = (
        'front_image_large', 'back_image_large',
        'category', 'gender', 'brand', 'size',
        'bg_removal_status',)


@admin.register(models.ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "thumbnail",)


@admin.register(models.Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'title', 'item_count', 'status',
        'shipping_type', 'created_by', 'purchased_by', 'created')
    search_fields = ('title', 'event_type', 'status')
    ordering = ('created', 'modified')
    list_filter = ('status', 'shipping_type', 'hidden',
                   'created_by', 'purchased_by')
    fields = (
        'title', 'slug',
        'shipping_type', 'shipping_cost',
        'status', 'status_changed',
        'created_by', 'purchased_by')
    inlines = [ProductInlineAdmin]

    def get_queryset(self, request):
        qs = super(BundleAdmin, self).get_queryset(request)
        qs = qs.annotate(Count('items'))
        return qs

    def item_count(self, obj):
        return obj.items__count

    item_count.admin_product_field = 'items__count'


@admin.register(models.ReleasableBundle)
class ReleasableBundleAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'status')
    actions = ['release_fund']

    def release_fund(self, request, queryset):
        for instance in queryset.all():
            instance.release_fund()
        self.message_user(
            request,
            f'{len(queryset)} bundle(s) will be released manually.')

    release_fund.short_description = "Release Fund Manually"


@admin.register(models.ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('type', 'rate', 'modified',)


@admin.register(models.Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'easypost_shipment_id', 'courier_id', 'status', 'label_url'
    )


@admin.register(models.ShipmentTracker)
class ShipmentTrackerAdmin(admin.ModelAdmin):
    list_display = (
        'shipment', 'tracking_code', 'status', 'created_at', 'updated_at'
    )


@admin.register(models.Product)
class ProductAdmin(AdminImageMixin, admin.ModelAdmin):
    list_display = (
        'pk', 'thumbnail', 'bundle', 'title', 'slug',
        'gender', 'quality', 'brand', 'category', 'size',)
    search_fields = ('bundle__brand', 'event_type', 'status')
    ordering = ('created', 'modified')
    list_filter = ('quality', 'gender', 'brand', 'category', 'size')


@admin.register(models.BundleReport)
class BundleReportAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'reported_by', 'bundle',
        'reported', 'reason'
    )

    search_fields = ('bundle', 'reported_by', 'reason', 'reported')
    ordering = ('reported', 'created', 'modified')
    list_filter = ('reported', 'reported_by', 'bundle')


@admin.register(models.BundleRating)
class BundleRatingAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'rated_by', 'bundle',
        'rating', 'feedback'
    )

    search_fields = ('bundle', 'rated_by', 'feedback')
    ordering = ('created', 'modified')
    list_filter = ('rated_by', 'bundle')


@admin.register(models.ProductCategory)
class ProductCategoryAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ('tree_actions', 'something', 'pk', 'slug', 'title')
    list_display_links = ('something',)

    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name,  # Or whatever you want to put here
        )

    something.short_description = _('Category Tree')
    search_fields = ("name",)


@admin.register(models.ProductBrand)
class ProductBrandAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ('tree_actions', 'something', 'pk',
                    'slug', 'title', 'suggested',)
    list_display_links = ('something',)

    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name,  # Or whatever you want to put here
        )

    something.short_description = _('Brand Tree')
    search_fields = ("name",)


@admin.register(models.SuggestedProductBrand)
class SuggestedProductBrandAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ('tree_actions', 'something', 'pk',
                    'slug', 'title', 'suggested',)
    list_display_links = ('something',)

    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name,  # Or whatever you want to put here
        )

    something.short_description = _('Suggested Brand Tree')
    search_fields = ("name",)


@admin.register(models.ProductSize)
class ProductSizeAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ('tree_actions', 'something', 'pk', 'slug', 'title')
    list_display_links = ('something',)

    def something(self, instance):
        return format_html(
            '<div style="text-indent:{}px">{}</div>',
            instance._mpttfield('level') * self.mptt_level_indent,
            instance.name,  # Or whatever you want to put here
        )

    something.short_description = _('Size Tree')
    search_fields = ("name",)
