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

    def test_get_user_existing(self):
        """Test that get_user returns existing Colleague by ID"""
        from wies.core.auth_backend import AuthBackend
        backend = AuthBackend()

        user = backend.get_user(self.colleague.pk)

        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.colleague.pk)
        self.assertEqual(user.email, "test@example.com")

    def test_get_user_non_existent(self):
        """Test that get_user returns None for non-existent ID"""
        from wies.core.auth_backend import AuthBackend
        backend = AuthBackend()

        user = backend.get_user(99999)

        self.assertIsNone(user)

    def test_authenticate_missing_username(self):
        """Test that authentication raises ValueError for missing username"""
        with self.assertRaises(ValueError) as context:
            authenticate(
                request=None,
                username=None,
                email="test@example.com",
                extra_fields={}
            )

        self.assertIn("username", str(context.exception).lower())

    def test_authenticate_empty_username(self):
        """Test that authentication raises ValueError for empty username"""
        with self.assertRaises(ValueError) as context:
            authenticate(
                request=None,
                username="",
                email="test@example.com",
                extra_fields={}
            )

        self.assertIn("username", str(context.exception).lower())

    def test_authenticate_missing_email(self):
        """Test that authentication raises ValueError for missing email"""
        with self.assertRaises(ValueError) as context:
            authenticate(
                request=None,
                username="test_user",
                email=None,
                extra_fields={}
            )

        self.assertIn("email", str(context.exception).lower())

    def test_authenticate_empty_email(self):
        """Test that authentication raises ValueError for empty email"""
        with self.assertRaises(ValueError) as context:
            authenticate(
                request=None,
                username="test_user",
                email="",
                extra_fields={}
            )

        self.assertIn("email", str(context.exception).lower())

    def test_authenticate_with_none_extra_fields(self):
        """Test that authentication works with extra_fields=None (uses default)"""
        user = authenticate(
            request=None,
            username="test_user",
            email="test@example.com",
            extra_fields=None
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "test@example.com")

    def test_authenticate_uses_email_for_lookup(self):
        """Test that authentication uses email (not username) for Colleague lookup"""
        # Create colleague with different username but same email
        different_username_colleague = Colleague.objects.create(
            username="original_username",
            email="lookup@example.com",
            first_name="Lookup",
            last_name="Test",
            brand=self.brand
        )

        # Authenticate with different username but same email
        user = authenticate(
            request=None,
            username="different_username",  # Different from stored username
            email="lookup@example.com",     # Same email
            extra_fields={
                'first_name': 'Lookup',
                'last_name': 'Test'
            }
        )

        # Should find the colleague by email, not username
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, different_username_colleague.pk)
        self.assertEqual(user.email, "lookup@example.com")
        self.assertEqual(user.username, "original_username")  # Original username preserved
