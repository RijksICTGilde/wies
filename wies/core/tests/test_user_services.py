from django.test import TestCase

from wies.core.models import User
from wies.core.errors import EmailNotAvailableError
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
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertIsNotNone(user.username)  # UUID should be generated
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

        # TODO: test that event is created

        user2 = create_user(
            user,
            first_name="New2",
            last_name="User2",
            email="newuser2@example.com",
        )

        # TODO: verify that event is created and that user2 is logged


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
        with self.assertRaises(EmailNotAvailableError):
            create_user(
                None,
                first_name="Second",
                last_name="User",
                email="duplicate@example.com",
            )

        # Verify only one user exists with that email
        self.assertEqual(User.objects.filter(email="duplicate@example.com").count(), 1)


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
        self.assertEqual(updated_user.id, user.id)
        self.assertEqual(updated_user.first_name, "Updated")
        self.assertEqual(updated_user.last_name, "NewName")
        self.assertEqual(updated_user.email, "updated@example.com")

        # TODO: test if event has been created

        # Verify changes were persisted
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.email, "updated@example.com")

    def test_update_user_email_to_existing(self):
        """Test that updating user email to another user's email raises EmailNotAvailableError"""
        # Create two users
        user1 = create_user(
            None,
            first_name="User",
            last_name="One",
            email="user1@example.com",
        )
        user2 = create_user(
            None,
            first_name="User",
            last_name="Two",
            email="user2@example.com",
        )

        # Try to update user1's email to user2's email
        with self.assertRaises(EmailNotAvailableError):
            update_user(
                None,
                user=user1,
                first_name="User",
                last_name="One",
                email="user2@example.com",  # This email belongs to user2
            )

        # Verify user1's email was not changed
        user1.refresh_from_db()
        self.assertEqual(user1.email, "user1@example.com")
