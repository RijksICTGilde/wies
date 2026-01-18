import pytest
from django.contrib.auth import authenticate
from django.test import TestCase

from wies.core.auth_backend import AuthBackend
from wies.core.models import User


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
                "first_name": "Test",
                "last_name": "User",
            },
        )

        assert user.email == "test@example.com"
        assert user.username == "test_user"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_authenticate_not_existing_colleague(self):
        """Test that authentication fails for non-existing Colleague"""
        user = authenticate(
            request=None,
            username="nonexisting",
            email="not@existing.com",
            extra_fields={
                "first_name": "Not",
                "last_name": "Existing",
            },
        )

        assert user is None

    def test_get_user_existing(self):
        """Test that get_user returns existing Colleague by ID"""
        backend = AuthBackend()
        user = backend.get_user(self.test_user.pk)

        assert user.pk == self.test_user.pk
        assert user.email == "test@example.com"

    def test_get_user_non_existent(self):
        """Test that get_user returns None for non-existent ID"""
        backend = AuthBackend()
        user = backend.get_user(0)

        assert user is None

    def test_authenticate_missing_username(self):
        """Test that authentication raises ValueError for missing username"""
        with pytest.raises(ValueError, match=r"(?i)username"):
            authenticate(
                request=None,
                username=None,
                email="test@example.com",
                extra_fields={},
            )

    def test_authenticate_empty_username(self):
        """Test that authentication raises ValueError for empty username"""
        with pytest.raises(ValueError, match=r"(?i)username"):
            authenticate(
                request=None,
                username="",
                email="test@example.com",
                extra_fields={},
            )

    def test_authenticate_missing_email(self):
        """Test that authentication raises ValueError for missing email"""
        with pytest.raises(ValueError, match=r"(?i)email"):
            authenticate(
                request=None,
                username="test_user",
                email=None,
                extra_fields={},
            )

    def test_authenticate_empty_email(self):
        """Test that authentication raises ValueError for empty email"""
        with pytest.raises(ValueError, match=r"(?i)email"):
            authenticate(
                request=None,
                username="test_user",
                email="",
                extra_fields={},
            )

    def test_authenticate_with_none_extra_fields(self):
        """Test that authentication works with extra_fields=None (uses default)"""
        user = authenticate(
            request=None,
            username="test_user",
            email="test@example.com",
            extra_fields=None,
        )

        assert user is not None
        assert user.email == "test@example.com"

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
            email="lookup@example.com",  # Same email
            extra_fields={
                "first_name": "Lookup",
                "last_name": "Test",
            },
        )

        # Should find the colleague by email, not username
        assert user.pk == colleague.pk
        assert user.email == "lookup@example.com"
        assert user.username == "original_username"  # Original username preserved
