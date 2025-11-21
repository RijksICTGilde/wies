from django.test import TestCase
from django.contrib.auth import authenticate

from wies.core.models import Brand, Colleague, EmailAlias, User
from wies.core.auth_backend import AuthBackend

class AuthBackendTest(TestCase):
    """Tests for custom authentication backend"""

    def setUp(self):
        """Create test data"""
        self.test_user = User.objects.create(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User",
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
        backend = AuthBackend()
        user = backend.get_user(self.test_user.pk)

        self.assertEqual(user.pk, self.test_user.pk)
        self.assertEqual(user.email, "test@example.com")

    def test_get_user_non_existent(self):
        """Test that get_user returns None for non-existent ID"""
        backend = AuthBackend()
        user = backend.get_user(0)

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
        # Create base colleague
        colleague = User.objects.create(
            username="original_username",
            email="lookup@example.com",
            first_name="Lookup",
            last_name="Test",
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
        self.assertEqual(user.pk, colleague.pk)
        self.assertEqual(user.email, "lookup@example.com")
        self.assertEqual(user.username, "original_username")  # Original username preserved

    def test_authenticate_with_email_alias(self):
        """Test that authentication works with email alias"""
        EmailAlias.objects.create(user=self.test_user, email="alias@example.com")

        user = authenticate(
            request=None,
            username="any_username",
            email="alias@example.com",
            extra_fields={}
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.test_user.pk)
        self.assertEqual(user.email, "test@example.com")  # Primary email

    def test_colleague_matched_on_primary_email_not_alias(self):
        """Test that Colleague is matched on primary ODI email, not login alias"""
        # User with primary ODI email and an alias
        user = User.objects.create(
            username="odi_user",
            email="odi@example.com",
            first_name="ODI",
            last_name="User",
        )
        EmailAlias.objects.create(user=user, email="alias@example.com")

        # Colleague with ODI email (should match on primary email)
        brand = Brand.objects.create(name="Test Brand")
        colleague = Colleague.objects.create(
            name="ODI User",
            email="odi@example.com",
            brand=brand,
        )

        # Login with alias email
        authenticate(
            request=None,
            username="odi_user",
            email="alias@example.com",
            extra_fields={}
        )

        colleague.refresh_from_db()
        self.assertEqual(colleague.user, user)

    def test_colleague_not_matched_on_alias_email(self):
        """Test that Colleague with alias email is NOT matched (only ODI email matches)"""
        # User with primary ODI email
        user = User.objects.create(
            username="odi_user",
            email="odi@example.com",
            first_name="ODI",
            last_name="User",
        )
        EmailAlias.objects.create(user=user, email="alias@example.com")

        # Colleague with alias email (should NOT match)
        brand = Brand.objects.create(name="Test Brand")
        colleague = Colleague.objects.create(
            name="Alias Colleague",
            email="alias@example.com",
            brand=brand,
        )

        # Login with alias email
        authenticate(
            request=None,
            username="odi_user",
            email="alias@example.com",
            extra_fields={}
        )

        colleague.refresh_from_db()
        self.assertIsNone(colleague.user)  # Should NOT be linked

    def test_authenticate_primary_email_takes_precedence(self):
        """Test that primary email lookup works even if alias exists"""
        EmailAlias.objects.create(user=self.test_user, email="alias@example.com")

        user = authenticate(
            request=None,
            username="any_username",
            email="test@example.com",
            extra_fields={}
        )

        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.test_user.pk)
