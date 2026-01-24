import pytest
from django.test import TestCase

from wies.core.errors import EmailNotAvailableError
from wies.core.models import Event, User
from wies.core.services.users import create_user, update_user


class CreateUserServiceTest(TestCase):
    """Tests for create_user service function"""

    def test_create_user(self):
        """Test creating user"""
        user = create_user(
            None,
            first_name="New",
            last_name="User",
            email="newuser@example.com",
        )

        # Verify user was created with correct attributes
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.email == "newuser@example.com"
        assert user.username is not None  # UUID should be generated
        assert User.objects.filter(email="newuser@example.com").exists()

        # Verify that event was created
        event = Event.objects.filter(name="User.create", context__created_id=user.id).first()
        assert event is not None
        assert event.user_email == ""  # System-created (creator is None)
        assert event.context["email"] == "newuser@example.com"
        assert event.context["first_name"] == "New"
        assert event.context["last_name"] == "User"

        user2 = create_user(
            user,
            first_name="New2",
            last_name="User2",
            email="newuser2@example.com",
        )

        # Verify that event is created and creator user is logged
        event2 = Event.objects.filter(name="User.create", context__created_id=user2.id).first()
        assert event2 is not None
        assert event2.user_email == user.email  # Creator is user
        assert event2.context["email"] == "newuser2@example.com"
        assert event2.context["first_name"] == "New2"
        assert event2.context["last_name"] == "User2"

    def test_create_user_duplicate_email(self):
        """Test that creating user with duplicate email raises EmailNotAvailableError"""
        # Create first user
        create_user(
            None,
            first_name="First",
            last_name="User",
            email="duplicate@example.com",
        )

        # Try to create second user with same email
        with pytest.raises(EmailNotAvailableError):
            create_user(
                None,
                first_name="Second",
                last_name="User",
                email="duplicate@example.com",
            )

        # Verify only one user exists with that email
        assert User.objects.filter(email="duplicate@example.com").count() == 1


class UpdateUserServiceTest(TestCase):
    """Tests for update_user service function"""

    def test_update_user(self):
        """Test updating user basic information"""
        # Create a user
        user = create_user(
            None,
            first_name="Original",
            last_name="Name",
            email="original@example.com",
        )

        # Update the user
        updated_user = update_user(
            None,
            user=user,
            first_name="Updated",
            last_name="NewName",
            email="updated@example.com",
        )

        # Verify the user was updated
        assert updated_user.id == user.id
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "NewName"
        assert updated_user.email == "updated@example.com"

        # Verify that event was created
        event = Event.objects.filter(name="User.update", context__updated_id=user.id).first()
        assert event is not None
        assert event.user_email == ""  # Updater is None (system)
        assert event.context["email"] == "updated@example.com"
        assert event.context["first_name"] == "Updated"
        assert event.context["last_name"] == "NewName"

        # Verify changes were persisted
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.email == "updated@example.com"

    def test_update_user_email_to_existing(self):
        """Test that updating user email to another user's email raises EmailNotAvailableError"""
        # Create two users
        user1 = create_user(
            None,
            first_name="User",
            last_name="One",
            email="user1@example.com",
        )
        create_user(
            None,
            first_name="User",
            last_name="Two",
            email="user2@example.com",
        )

        # Try to update user1's email to user2's email
        with pytest.raises(EmailNotAvailableError):
            update_user(
                None,
                user=user1,
                first_name="User",
                last_name="One",
                email="user2@example.com",  # This email belongs to user2
            )

        # Verify user1's email was not changed
        user1.refresh_from_db()
        assert user1.email == "user1@example.com"
