import os
from django.core.management import BaseCommand
from django.db import transaction
from app.models import Product, ListingImage


class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **kwargs):
        products = Product.objects.all()
        for each in products:
            params = {
                "product": each,
                "image_large": each.front_image_large,
                "created_by": each.created_by
            }
            front = ListingImage(**params).save()
            if each.back_image_large:
                params["image_large"] = each.back_image_large
                back = ListingImage(**params).save()
        print("Done")
