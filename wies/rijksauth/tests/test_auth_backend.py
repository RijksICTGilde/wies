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

    def test_first_login_claims_unclaimed_account_and_persists_sub(self):
        """First login for a pre-provisioned account binds the OIDC sub by email match."""
        user = authenticate(
            request=None,
            username="sub-abc",
            email="test@rijksoverheid.nl",
        )

        assert user is not None
        assert user.pk == self.test_user.pk
        user.refresh_from_db()
        assert user.oidc_sub == "sub-abc"

    def test_authenticate_by_oidc_sub_ignores_email(self):
        """Once bound, a user is matched on the stable OIDC sub, not the email claim."""
        self.test_user.oidc_sub = "sub-abc"
        self.test_user.save(update_fields=["oidc_sub"])

        # Email in the token differs (e.g. changed upstream); sub still identifies the user.
        user = authenticate(
            request=None,
            username="sub-abc",
            email="changed@rijksoverheid.nl",
        )

        assert user is not None
        assert user.pk == self.test_user.pk

    def test_authenticate_denies_email_already_bound_to_other_sub(self):
        """A token whose email is already bound to a different sub must NOT take over the account."""
        self.test_user.oidc_sub = "real-sub"
        self.test_user.save(update_fields=["oidc_sub"])

        user = authenticate(
            request=None,
            username="attacker-sub",
            email="test@rijksoverheid.nl",
        )

        assert user is None
        self.test_user.refresh_from_db()
        assert self.test_user.oidc_sub == "real-sub"

    def test_authenticate_denies_unknown_email(self):
        """Authentication fails when no account matches the sub or the email."""
        user = authenticate(
            request=None,
            username="whatever-sub",
            email="not@existing.com",
        )

        assert user is None

    def test_second_login_uses_sub_after_claim(self):
        """After the first-login claim, a later login with the same sub matches regardless of email."""
        first = authenticate(request=None, username="sub-abc", email="test@rijksoverheid.nl")
        assert first is not None

        second = authenticate(request=None, username="sub-abc", email="renamed@rijksoverheid.nl")

        assert second is not None
        assert second.pk == first.pk

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
