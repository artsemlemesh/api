from rest_framework.permissions import IsAuthenticated
from app.models.product import Bundle, ProductImage
from django.shortcuts import get_object_or_404


class IsSuperUser(IsAuthenticated,):
    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view) and
            request.user.is_superuser)


class IsBundleOwner(IsAuthenticated):
    """
    Use this permission to disable doing something on other listing
    NOTE: listing should be mentioned by listing_pk url param
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        listing = Bundle.objects.get(
            pk=request.parser_context['kwargs']['listing_pk']
        )
        return (listing is not None and listing.created_by == request.user)


class IsProductImageOwner(IsAuthenticated):
    """
    Use this permission to disable doing something on other listing
    NOTE: listing should be mentioned by listing_pk url param
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        listing = get_object_or_404(
            ProductImage, pk=request.parser_context['kwargs']['pk'])
        return (listing is not None and listing.created_by == request.user)
