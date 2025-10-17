from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from wies.projects.models import Colleague, Brand


class ColleagueEmailSecurityTest(TestCase):
    def setUp(self):
        # Create BDM group
        self.bdm_group = Group.objects.create(name='BDM')

        # Create test user with BDM permissions
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.groups.add(self.bdm_group)

        # Create brand
        self.brand = Brand.objects.create(name='Test Brand')

        # Create colleague with initial email, linked to the user
        self.colleague = Colleague.objects.create(
            name='Test Colleague',
            email='original@example.com',
            brand=self.brand,
            user=self.user  # Link colleague to user so permission check passes
        )

        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def test_handcrafted_post_cannot_change_email(self):
        """Test that a crafted POST request cannot change colleague email"""
        original_email = self.colleague.email

        # Attempt to update email via POST
        response = self.client.post(
            f'/colleagues/{self.colleague.pk}/update',
            {
                'name': 'Test Colleague',
                'email': 'hacked@malicious.com',  # Attempt to change email
                'brand': self.brand.pk,
            }
        )

        # Check that request succeeded (redirect on success)
        self.assertEqual(response.status_code, 302, 'Form submission should succeed with redirect')

        # Refresh from database
        self.colleague.refresh_from_db()

        # Email should remain unchanged
        self.assertEqual(
            self.colleague.email,
            original_email,
            'Email was changed via POST request - security vulnerability!'
        )

    def test_post_can_change_name(self):
        """Test that POST request can change other fields like name"""
        # Attempt to update name via POST
        response = self.client.post(
            f'/colleagues/{self.colleague.pk}/update',
            {
                'name': 'Updated Name',
                'brand': self.brand.pk,
                'email': 'original@example.com',
            }
        )

        # Check that request succeeded (redirect on success)
        self.assertEqual(response.status_code, 302, 'Form submission should succeed with redirect')

        # Refresh from database
        self.colleague.refresh_from_db()

        # Name should be updated
        self.assertEqual(self.colleague.name, 'Updated Name')
