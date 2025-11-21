from django.db import IntegrityError
from django.test import TestCase

from wies.core.models import EmailAlias, User
from wies.core.errors import EmailNotAvailableError
from wies.core.services.users import create_user, get_user_by_email, update_user


class GetUserByEmailTest(TestCase):
    """Tests for get_user_by_email service function"""

    def setUp(self):
        self.user = User.objects.create(
            username="test_user",
            email="primary@example.com",
            first_name="Test",
            last_name="User",
        )

    def test_returns_none_for_new_email(self):
        """Test that unused email returns None"""
        self.assertIsNone(get_user_by_email("new@example.com"))

    def test_finds_primary_email(self):
        """Test that primary email returns the user"""
        self.assertEqual(get_user_by_email("primary@example.com"), self.user)

    def test_finds_alias(self):
        """Test that alias email returns the user"""
        EmailAlias.objects.create(user=self.user, email="alias@example.com")
        self.assertEqual(get_user_by_email("alias@example.com"), self.user)

    def test_returns_none_for_unknown_email(self):
        """Test that unknown email returns None"""
        self.assertIsNone(get_user_by_email("unknown@example.com"))


class CreateUserServiceTest(TestCase):
    """Tests for create_user service function"""

    def test_create_user_with_aliases(self):
        """Test creating user with email aliases"""
        user = create_user(
            first_name="New",
            last_name="User",
            email="newuser@example.com",
            email_aliases=["alias1@example.com", "alias2@example.com"]
        )
        aliases = list(user.email_aliases.values_list('email', flat=True))
        self.assertEqual(sorted(aliases), ["alias1@example.com", "alias2@example.com"])


class UpdateUserServiceTest(TestCase):
    """Tests for update_user service function"""

    def setUp(self):
        self.user = User.objects.create(
            username="test_user",
            email="primary@example.com",
            first_name="Test",
            last_name="User",
        )

    def test_replaces_aliases(self):
        """Test that updating user replaces all aliases"""
        EmailAlias.objects.create(user=self.user, email="old@example.com")

        update_user(
            user=self.user,
            first_name="Test",
            last_name="User",
            email="primary@example.com",
            email_aliases=["new@example.com"]
        )

        aliases = list(self.user.email_aliases.values_list('email', flat=True))
        self.assertEqual(aliases, ["new@example.com"])


class EmailAliasModelTest(TestCase):
    """Tests for EmailAlias model"""

    def setUp(self):
        self.user = User.objects.create(
            username="test_user",
            email="primary@example.com",
            first_name="Test",
            last_name="User",
        )

    def test_cascade_delete(self):
        """Test that aliases are deleted when user is deleted"""
        EmailAlias.objects.create(user=self.user, email="alias@example.com")
        self.user.delete()
        self.assertEqual(EmailAlias.objects.count(), 0)


class EmailUniquenessServiceTest(TestCase):
    """Tests for email uniqueness validation in service layer"""

    def setUp(self):
        self.user1 = User.objects.create(
            username="user1",
            email="user1@example.com",
        )
        self.user2 = User.objects.create(
            username="user2",
            email="user2@example.com",
        )

    def test_cannot_create_user_with_duplicate_primary_email(self):
        """DB should reject duplicate primary email"""
        with self.assertRaises(IntegrityError):
            User.objects.create(username="user3", email="user1@example.com")

    def test_rejects_alias_matching_existing_primary(self):
        """Service rejects alias matching another user's primary email"""
        with self.assertRaises(EmailNotAvailableError) as ctx:
            create_user(
                first_name='New',
                last_name='User',
                email='newuser@example.com',
                email_aliases=['user1@example.com']
            )
        self.assertEqual(ctx.exception.field, 'email_aliases')

    def test_cannot_create_duplicate_alias(self):
        """Two aliases cannot have the same email"""
        EmailAlias.objects.create(user=self.user1, email="shared@example.com")
        with self.assertRaises(IntegrityError):
            EmailAlias.objects.create(user=self.user2, email="shared@example.com")

    def test_rejects_primary_matching_other_user_alias(self):
        """Service rejects primary email matching another user's alias"""
        EmailAlias.objects.create(user=self.user2, email="alias@example.com")
        with self.assertRaises(EmailNotAvailableError) as ctx:
            update_user(
                user=self.user1,
                first_name='Test',
                last_name='User',
                email='alias@example.com',
            )
        self.assertEqual(ctx.exception.field, 'email')

    def test_rejects_alias_matching_own_primary(self):
        """Service rejects alias matching own primary email"""
        with self.assertRaises(EmailNotAvailableError) as ctx:
            update_user(
                user=self.user1,
                first_name='Test',
                last_name='User',
                email='user1@example.com',
                email_aliases=['user1@example.com']
            )
        self.assertEqual(ctx.exception.field, 'email_aliases')

    def test_rejects_alias_matching_other_user_primary(self):
        """Service rejects alias matching another user's primary"""
        with self.assertRaises(EmailNotAvailableError) as ctx:
            update_user(
                user=self.user1,
                first_name='Test',
                last_name='User',
                email='user1@example.com',
                email_aliases=['user2@example.com']
            )
        self.assertEqual(ctx.exception.field, 'email_aliases')

    def test_rejects_alias_matching_other_user_alias(self):
        """Service rejects alias matching another user's alias"""
        EmailAlias.objects.create(user=self.user2, email="taken@example.com")
        with self.assertRaises(EmailNotAvailableError) as ctx:
            update_user(
                user=self.user1,
                first_name='Test',
                last_name='User',
                email='user1@example.com',
                email_aliases=['taken@example.com']
            )
        self.assertEqual(ctx.exception.field, 'email_aliases')

    def test_allows_keeping_own_aliases(self):
        """Service allows user to keep their existing aliases"""
        EmailAlias.objects.create(user=self.user1, email="myalias@example.com")
        # Should not raise
        update_user(
            user=self.user1,
            first_name='Test',
            last_name='User',
            email='user1@example.com',
            email_aliases=['myalias@example.com']
        )
