import pytest
from django.contrib.auth.models import Group
from django.test import TestCase

from wies.core.errors import EmailNotAvailableError, InvalidEmailDomainError
from wies.core.models import Event, User
from wies.core.services.users import create_user, create_users_from_csv, is_allowed_email_domain, update_user


class CreateUserServiceTest(TestCase):
    """Tests for create_user service function"""

    def test_create_user(self):
        """Test creating user"""
        user = create_user(
            None,
            first_name="New",
            last_name="User",
            email="newuser@rijksoverheid.nl",
        )

        # Verify user was created with correct attributes
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.email == "newuser@rijksoverheid.nl"
        assert user.username is not None  # UUID should be generated
        assert User.objects.filter(email="newuser@rijksoverheid.nl").exists()

        # Verify that event was created
        event = Event.objects.filter(name="User.create", context__created_id=user.id).first()
        assert event is not None
        assert event.user_email == ""  # System-created (creator is None)
        assert event.context["email"] == "newuser@rijksoverheid.nl"
        assert event.context["first_name"] == "New"
        assert event.context["last_name"] == "User"

        user2 = create_user(
            user,
            first_name="New2",
            last_name="User2",
            email="newuser2@rijksoverheid.nl",
        )

        # Verify that event is created and creator user is logged
        event2 = Event.objects.filter(name="User.create", context__created_id=user2.id).first()
        assert event2 is not None
        assert event2.user_email == user.email  # Creator is user
        assert event2.context["email"] == "newuser2@rijksoverheid.nl"
        assert event2.context["first_name"] == "New2"
        assert event2.context["last_name"] == "User2"

    def test_create_user_duplicate_email(self):
        """Test that creating user with duplicate email raises EmailNotAvailableError"""
        # Create first user
        create_user(
            None,
            first_name="First",
            last_name="User",
            email="duplicate@rijksoverheid.nl",
        )

        # Try to create second user with same email
        with pytest.raises(EmailNotAvailableError):
            create_user(
                None,
                first_name="Second",
                last_name="User",
                email="duplicate@rijksoverheid.nl",
            )

        # Verify only one user exists with that email
        assert User.objects.filter(email="duplicate@rijksoverheid.nl").count() == 1

    def test_create_user_invalid_email_domain(self):
        """Test that creating user with invalid email domain raises InvalidEmailDomainError"""
        with pytest.raises(InvalidEmailDomainError) as exc_info:
            create_user(
                None,
                first_name="External",
                last_name="User",
                email="external@gmail.com",
            )

        # Verify error contains useful info
        assert exc_info.value.email == "external@gmail.com"
        assert "@rijksoverheid.nl" in exc_info.value.allowed_domains

        # Verify no user was created
        assert not User.objects.filter(email="external@gmail.com").exists()


class UpdateUserServiceTest(TestCase):
    """Tests for update_user service function"""

    def test_update_user(self):
        """Test updating user basic information"""
        # Create a user
        user = create_user(
            None,
            first_name="Original",
            last_name="Name",
            email="original@rijksoverheid.nl",
        )

        # Update the user
        updated_user = update_user(
            None,
            user=user,
            first_name="Updated",
            last_name="NewName",
            email="updated@rijksoverheid.nl",
        )

        # Verify the user was updated
        assert updated_user.id == user.id
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "NewName"
        assert updated_user.email == "updated@rijksoverheid.nl"

        # Verify that event was created
        event = Event.objects.filter(name="User.update", context__updated_id=user.id).first()
        assert event is not None
        assert event.user_email == ""  # Updater is None (system)
        assert event.context["email"] == "updated@rijksoverheid.nl"
        assert event.context["first_name"] == "Updated"
        assert event.context["last_name"] == "NewName"

        # Verify changes were persisted
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.email == "updated@rijksoverheid.nl"

    def test_update_user_email_to_existing(self):
        """Test that updating user email to another user's email raises EmailNotAvailableError"""
        # Create two users
        user1 = create_user(
            None,
            first_name="User",
            last_name="One",
            email="user1@rijksoverheid.nl",
        )
        create_user(
            None,
            first_name="User",
            last_name="Two",
            email="user2@rijksoverheid.nl",
        )

        # Try to update user1's email to user2's email
        with pytest.raises(EmailNotAvailableError):
            update_user(
                None,
                user=user1,
                first_name="User",
                last_name="One",
                email="user2@rijksoverheid.nl",  # This email belongs to user2
            )

        # Verify user1's email was not changed
        user1.refresh_from_db()
        assert user1.email == "user1@rijksoverheid.nl"

    def test_update_user_invalid_email_domain(self):
        """Test that updating user with invalid email domain raises InvalidEmailDomainError"""
        # Create a user with valid email
        user = create_user(
            None,
            first_name="Test",
            last_name="User",
            email="test@rijksoverheid.nl",
        )

        # Try to update to invalid email domain
        with pytest.raises(InvalidEmailDomainError) as exc_info:
            update_user(
                None,
                user=user,
                first_name="Test",
                last_name="User",
                email="test@gmail.com",
            )

        # Verify error contains useful info
        assert exc_info.value.email == "test@gmail.com"

        # Verify user's email was not changed
        user.refresh_from_db()
        assert user.email == "test@rijksoverheid.nl"


class EmailDomainValidationTest(TestCase):
    """Tests for is_allowed_email_domain helper function"""

    def test_allowed_rijksoverheid_domain(self):
        """Test that @rijksoverheid.nl emails are allowed"""
        assert is_allowed_email_domain("test@rijksoverheid.nl") is True

    def test_allowed_minbzk_domain(self):
        """Test that @minbzk.nl emails are allowed"""
        assert is_allowed_email_domain("test@minbzk.nl") is True

    def test_disallowed_external_domain(self):
        """Test that external domains are not allowed"""
        assert is_allowed_email_domain("test@gmail.com") is False
        assert is_allowed_email_domain("test@external.nl") is False

    def test_case_insensitive(self):
        """Test that domain check is case insensitive"""
        assert is_allowed_email_domain("test@RIJKSOVERHEID.NL") is True
        assert is_allowed_email_domain("test@MinBZK.nl") is True


class CreateUsersFromCSVEmailDomainTest(TestCase):
    """Tests for email domain validation in CSV import"""

    def setUp(self):
        """Create required groups for CSV import"""
        Group.objects.get_or_create(name="Beheerder")
        Group.objects.get_or_create(name="Consultant")
        Group.objects.get_or_create(name="Business Development Manager")

    def test_csv_import_valid_emails(self):
        """Test CSV import with valid ODI email addresses"""
        csv_content = """first_name,last_name,email
Jan,Jansen,jan.jansen@rijksoverheid.nl
Piet,Pietersen,piet.pietersen@minbzk.nl"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"] is True
        assert result["users_created"] == 2
        assert len(result["errors"]) == 0

    def test_csv_import_invalid_email_domain(self):
        """Test CSV import rejects invalid email domains"""
        csv_content = """first_name,last_name,email
Jan,Jansen,jan.jansen@gmail.com"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"] is False
        assert result["users_created"] == 0
        assert len(result["errors"]) == 1
        assert "invalid domain" in result["errors"][0]
        assert "@rijksoverheid.nl" in result["errors"][0]

    def test_csv_import_mixed_valid_invalid_emails(self):
        """Test CSV import with mix of valid and invalid email domains"""
        csv_content = """first_name,last_name,email
Jan,Jansen,jan.jansen@rijksoverheid.nl
Piet,Pietersen,piet@external.com
Kees,Ansen,kees@minbzk.nl"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"] is False
        assert result["users_created"] == 0  # No users created when any validation fails
        assert len(result["errors"]) == 1
        assert "Row 3" in result["errors"][0]  # Piet is on row 3

    def test_csv_import_client_email_rejected(self):
        """Test CSV import rejects client email addresses"""
        csv_content = """first_name,last_name,email
Jan,Jansen,jan.jansen@clientorganisatie.nl"""

        result = create_users_from_csv(None, csv_content)

        assert result["success"] is False
        assert "invalid domain" in result["errors"][0]
