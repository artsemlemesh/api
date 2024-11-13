import os
from django.core.management import BaseCommand
from django.db import transaction
from app.models import Listing, User
from app.constants.status import PRODUCT_STATUS

class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **kwargs):
        user_names = [
            "bhavyashree.duggirala@gmail.com",
            "sophia.cantu05@k12.leanderisd.org",
            "nikkykap@gmail.com",
            "epari.akshita@gmail.com",
            "pratinanda2019@gmail.com"
        ]
        
        to_be_user = User.objects.get(email="kristengode@gmail.com")
        # to_be_user = User.objects.get(email="shubhamg2404@gmail.com")

        for user_name in user_names:
            listings = Listing.objects.filter(created_by__email=user_name, status=PRODUCT_STATUS.published)
            print("len: ", len(listings), "user_name: ", user_name)
            listings.update(created_by=to_be_user)
            # listings.save()
            

        
