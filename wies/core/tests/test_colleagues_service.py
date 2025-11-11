from django.test import TestCase

from wies.core.services.colleagues import create_colleague


class ColleagueTests(TestCase):
    """Tests for create_colleague service function"""

    def test_create_colleague(self):
        """Test that create_colleague creates a new Colleague with correct data"""
        colleague = create_colleague(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )

        self.assertEqual(colleague.first_name, "John")
        self.assertEqual(colleague.last_name, "Doe")
        self.assertEqual(colleague.email, "john.doe@example.com")
