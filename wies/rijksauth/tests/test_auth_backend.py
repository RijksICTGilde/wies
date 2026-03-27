import pytest
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase

from wies.rijksauth.auth_backend import AuthBackend

User = get_user_model()


class AuthBackendTest(TestCase):
    """Tests for custom authentication backend"""

    def setUp(self):
        """Create test data"""
        self.test_user = User.objects.create_user(
            email="test@rijksoverheid.nl",
            first_name="Test",
            last_name="User",
        )

    def test_authenticate_existing_user(self):
        """Test that authentication succeeds for existing User"""
        user = authenticate(
            request=None,
            username="test_sub",
            email="test@rijksoverheid.nl",
        )

        assert user.email == "test@rijksoverheid.nl"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_authenticate_not_existing_user(self):
        """Test that authentication fails for non-existing User"""
        user = authenticate(
            request=None,
            username="nonexisting",
            email="not@existing.com",
        )

        assert user is None

    def test_get_user_existing(self):
        """Test that get_user returns existing User by ID"""
        backend = AuthBackend()
        user = backend.get_user(self.test_user.pk)

        assert user.pk == self.test_user.pk
        assert user.email == "test@rijksoverheid.nl"

    def test_get_user_non_existent(self):
        """Test that get_user returns None for non-existent ID"""
        backend = AuthBackend()
        user = backend.get_user(0)

        assert user is None

    def test_authenticate_missing_username(self):
        """Test that authentication raises ValueError for missing username"""
        with pytest.raises(ValueError, match=r"(?i)username"):
            authenticate(request=None, username=None, email="test@rijksoverheid.nl")

    def test_authenticate_empty_username(self):
        """Test that authentication raises ValueError for empty username"""
        with pytest.raises(ValueError, match=r"(?i)username"):
            authenticate(request=None, username="", email="test@rijksoverheid.nl")

    def test_authenticate_missing_email(self):
        """Test that authentication raises ValueError for missing email"""
        with pytest.raises(ValueError, match=r"(?i)email"):
            authenticate(request=None, username="test_sub", email=None)

    def test_authenticate_empty_email(self):
        """Test that authentication raises ValueError for empty email"""
        with pytest.raises(ValueError, match=r"(?i)email"):
            authenticate(request=None, username="test_sub", email="")

    def test_authenticate_uses_email_for_lookup(self):
        """Test that authentication uses email (not username) for User lookup"""
        other_user = User.objects.create_user(
            email="lookup@rijksoverheid.nl",
            first_name="Lookup",
            last_name="Test",
        )

        # Authenticate with different username but same email
        user = authenticate(
            request=None,
            username="different_sub",
            email="lookup@rijksoverheid.nl",
        )

        # Should find the user by email, not username
        assert user.pk == other_user.pk
        assert user.email == "lookup@rijksoverheid.nl"
