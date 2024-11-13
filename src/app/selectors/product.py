
from django.db.models import Q
from app.models import Product


def get_product_detail(*, pk: int):
    return Product.objects.get(pk=pk)


def get_products(*, fetched_by: User):
    if bool(fetched_by and fetched_by.is_superuser):
        query = Q(hidden=False)
        return Product.objects.filter(query)
    return Product.objects.all()
