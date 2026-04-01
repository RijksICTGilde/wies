"""Test for the label delete view"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase

from wies.core.models import Label, LabelCategory

User = get_user_model()


class LabelDeleteViewTest(TestCase):
    """Test the label delete endpoint"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")

        perm = Permission.objects.get(codename="delete_label")
        self.user.user_permissions.add(perm)

        self.client.login(username="testuser", password="testpass123")

        self.category = LabelCategory.objects.create(name="Test Category", color="#FFFFFF")
        self.label = Label.objects.create(name="Test Label", category=self.category)

    def test_label_delete_get_returns_confirmation(self):
        """GET on label delete should return a confirmation modal, not crash"""
        response = self.client.get(f"/instellingen/labels/{self.label.pk}/verwijderen/")
        assert response.status_code == 200

    def test_label_delete_post_deletes_label(self):
        """POST on label delete should delete the label"""
        response = self.client.post(f"/instellingen/labels/{self.label.pk}/verwijderen/")
        assert response.status_code == 200
        assert not Label.objects.filter(pk=self.label.pk).exists()
