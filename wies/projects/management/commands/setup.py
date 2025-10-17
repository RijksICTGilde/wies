from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
import os


class Command(BaseCommand):
    help = 'Setup initial groups and superuser for the application'

    def handle(self, *args, **options):
        # Create groups
        _, bdm_created = Group.objects.get_or_create(name='BDM')
        _, consultants_created = Group.objects.get_or_create(name='Consultants')

        if bdm_created:
            self.stdout.write(self.style.SUCCESS('Created BDM group'))
        else:
            self.stdout.write('BDM group already exists')

        if consultants_created:
            self.stdout.write(self.style.SUCCESS('Created Consultants group'))
        else:
            self.stdout.write('Consultants group already exists')

        # Create superuser (using Django's DJANGO_SUPERUSER_* environment variables)
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if username and email and password:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
            else:
                self.stdout.write(f'Superuser {username} already exists')
        else:
            self.stdout.write(self.style.WARNING(
                'Skipping superuser creation - set DJANGO_SUPERUSER_USERNAME, '
                'DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD environment variables'
            ))
