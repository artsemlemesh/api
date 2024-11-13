from django.core.management import BaseCommand
from app.tasks import send_kits


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('user_pk', type=int)

    def handle(self, *args, **kwargs):
        user_pk = kwargs['user_pk']
        packages = [
            'LARGE_FLAT_RATE_BOX',
            'MEDIUM_FLAT_RATE_BOX',
            'PADDED_FLAT_RATE_ENVELOPE'
        ]
        response = send_kits(user_pk, packages, 'production')  # env set to prod to actually test sending the kits
        print('\nResponse:', response)
