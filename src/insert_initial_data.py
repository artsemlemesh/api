import sys
import os
import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser

try:
    print(os.getenv('ADMIN_EMAIL'), os.getenv('ADMIN_PASSWORD'))
    sys.stdout.write('Creating super user.\n')
    user = User.objects.get(email=os.environ['ADMIN_EMAIL'])
    sys.stderr.write('Super user already exists.\n')
except User.DoesNotExist:
    User.objects.create_superuser(
        os.environ['ADMIN_EMAIL'],
        os.environ['ADMIN_PASSWORD']
    )


sys.stdout.write('Done setting up database.\n')
