from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class MigrationTest(TestCase):
    def test_no_missing_migrations(self):
        """Ensure all model changes have migrations."""
        out = StringIO()
        # --check exits with error if migrations needed
        # --dry-run doesn't create files
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        # If we get here without exception, no migrations needed
