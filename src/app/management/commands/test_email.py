from django.core.management import BaseCommand
from app.tasks import send_email, send_pepo_email


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        response = send_email(8)
        response = send_pepo_email('vinaygode@gmail.com', 'confirmation_email2', {
            'user': 'vinaygode@gmail.com',
            'first_name': 'Something',
            'url': 'http://localhost:3000/auth/verify/MQ/5mm-e1a5bcb2d4541e105031'
        })
        print(response)
