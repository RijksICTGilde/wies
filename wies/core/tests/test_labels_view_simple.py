"""Simple test for the labels endpoint"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from wies.core.models import LabelCategory, Label

User = get_user_model()


@override_settings(STORAGES={
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
})
class LabelsViewTest(TestCase):
    """Test the labels view endpoint"""

    def setUp(self):
        """Set up test user and permissions"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Add view permission
        perm = Permission.objects.get(codename='view_labelcategory')
        self.user.user_permissions.add(perm)

        # Login
        self.client.login(username='testuser', password='testpass123')

        # Create test data
        self.category = LabelCategory.objects.create(name='Test Category', color='#FFFFFF')
        self.label = Label.objects.create(name='Test Label', category=self.category)

    def test_labels_endpoint_loads(self):
        """Test that the /instellingen/labels/ endpoint loads successfully"""
        response = self.client.get('/instellingen/labels/')


        if response.status_code != 200:
            print(f"Response content: {response.content.decode('utf-8')[:1000]}")

        self.assertEqual(response.status_code, 200)

    def test_usage_count_annotation(self):
        """Test that labels have usage_count annotation"""
        from wies.core.models import Label
        from django.db.models import Count

        # Test the annotation logic directly
        labels_with_usage = Label.objects.annotate(
            usage_count=Count('users', distinct=True) + Count('colleagues', distinct=True)
        )

        # Get the test label
        label = labels_with_usage.get(name='Test Label')

        # This should not raise an AttributeError
        usage_count = label.usage_count

        # Should be 0 since no users or colleagues are assigned
        self.assertEqual(usage_count, 0)
