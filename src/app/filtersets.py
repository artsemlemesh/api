from django_filters import rest_framework as filters
from app.models.product import Product, ProductBrand, ProductCategory, ProductSize


class ProductFilterSet(filters.FilterSet):
    slug = filters.CharFilter(lookup_expr='iexact')
    title = filters.CharFilter(lookup_expr='icontains')

    gender = filters.CharFilter(
        field_name='gender', lookup_expr='iexact')
    quality = filters.CharFilter(
        field_name='quality', lookup_expr='iexact')
    category = filters.ModelMultipleChoiceFilter(
        to_field_name='id',
        queryset=ProductCategory.objects.all()
    )
    brand = filters.ModelMultipleChoiceFilter(
        to_field_name='id',
        queryset=ProductBrand.objects.all()
    )
    size = filters.ModelMultipleChoiceFilter(
        to_field_name='id',
        queryset=ProductSize.objects.all()
    )

    class Meta:
        model = Product
        fields = ['title']
        together = ['tags__name', 'gender', 'quality',
                    'category', 'brand', 'size']
