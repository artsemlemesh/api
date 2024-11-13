from django.core.management import BaseCommand
from app.tasks.orders import create_shipments_in_batch


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        resposne = create_shipments_in_batch()
        print(resposne)
