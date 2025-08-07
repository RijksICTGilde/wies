import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Removes the SQLite database file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_true',
            help='Do not prompt for confirmation',
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES['default']
        
        if db_config['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('This command only works with SQLite databases')
        
        db_path = db_config['NAME']
        
        if not os.path.exists(db_path):
            self.stdout.write(
                self.style.WARNING(f'Database file does not exist: {db_path}')
            )
            return
        
        if not options['noinput']:
            confirm = input(f'Are you sure you want to delete {db_path}? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Operation cancelled.')
                return
        
        try:
            os.remove(db_path)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully removed database file: {db_path}')
            )
        except OSError as e:
            raise CommandError(f'Error removing database file: {e}')
