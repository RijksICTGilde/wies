"""Simple test for the labels endpoint"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Count
from django.test import Client, TestCase

from wies.core.models import Label, LabelCategory

User = get_user_model()


class LabelsViewTest(TestCase):
    """Test the labels view endpoint"""

    def setUp(self):
        """Set up test user and permissions"""
        self.client = Client()
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")

        # Add view permission
        perm = Permission.objects.get(codename="view_labelcategory")
        self.user.user_permissions.add(perm)

        # Login
        self.client.force_login(self.user)

        # Create test data
        self.category = LabelCategory.objects.create(name="Test Category", color="#FFFFFF")
        self.label = Label.objects.create(name="Test Label", category=self.category)

    def test_labels_endpoint_loads(self):
        """Test that the /beheer/labels/ endpoint loads successfully"""
        response = self.client.get("/beheer/labels/")

        if response.status_code != 200:
            pass

        assert response.status_code == 200

    def test_usage_count_annotation(self):
        """Test that labels have usage_count annotation"""
        # Test the annotation logic directly
        labels_with_usage = Label.objects.annotate(usage_count=Count("colleagues", distinct=True))

        # Get the test label
        label = labels_with_usage.get(name="Test Label")

        # This should not raise an AttributeError
        usage_count = label.usage_count

        # Should be 0 since no colleagues are assigned
        assert usage_count == 0
