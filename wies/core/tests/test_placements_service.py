from pathlib import Path

from django.test import TestCase, override_settings

from wies.core.models import Ministry
from wies.core.services.placements import create_placements_from_csv

@override_settings(
    # Use simple static files storage for tests
    # Because tests are not running with debug True, you would otherise need to run
    # collectstatic before running the test
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class CreateFromCSVTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        Ministry.objects.create(name='Ministerie van Binnenlandse Zaken', abbreviation='BZK')

    def test_sample_csv_success(self):
        sample_csv_path = Path(__file__).parent.parent / 'static' / 'example_placement_import.csv'
        with open(sample_csv_path) as f:
            csv_content = f.read()

        result = create_placements_from_csv(csv_content)
        self.assertEqual(result['success'], True)
