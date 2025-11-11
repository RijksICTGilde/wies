from django.test import TestCase
from django.contrib.auth import authenticate

from wies.core.models import Colleague, Brand


class AuthBackendTest(TestCase):
    """Tests for custom authentication backend"""

    def setUp(self):
        """Create test data"""
        self.brand = Brand.objects.create(name="Test Brand")
        self.colleague = Colleague.objects.create(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            brand=self.brand
        )

    def test_authenticate_existing_colleague(self):
        """Test that authentication succeeds for existing Colleague"""
        user = authenticate(
            request=None,
            username="test_user",
            email="test@example.com",
            extra_fields={
                'first_name': 'Test',
                'last_name': 'User'
            }
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "test_user")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")

    def test_authenticate_not_existing_colleague(self):
        """Test that authentication fails for non-existing Colleague"""
        user = authenticate(
            request=None,
            username="nonexisting",
            email="not@existing.com",
            extra_fields={
                'first_name': 'Not',
                'last_name': 'Existing'
            }
        )

        self.assertIsNone(user)
