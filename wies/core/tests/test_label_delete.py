"""Test for the label delete view"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Label, LabelCategory

User = get_user_model()


class LabelDeleteViewTest(TestCase):
    """Test the label delete endpoint"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="testuser@rijksoverheid.nl", first_name="Test", last_name="User")

        perm = Permission.objects.get(codename="delete_label")
        self.user.user_permissions.add(perm)

        self.client.force_login(self.user)

        self.category = LabelCategory.objects.create(name="Test Category", color="#FFFFFF")
        self.label = Label.objects.create(name="Test Label", category=self.category)

    def test_label_delete_get_returns_centered_dialog(self):
        """GET on label delete should return a centered confirmation dialog, not a sheet."""
        response = self.client.get(f"/beheer/labels/{self.label.public_id}/verwijderen/")
        assert response.status_code == 200
        self.assertContains(response, "nldd-modal-dialog")
        self.assertNotContains(response, "nldd-sheet")

    def test_label_delete_post_deletes_label(self):
        """POST on label delete should delete the label and redirect to the admin."""
        response = self.client.post(f"/beheer/labels/{self.label.public_id}/verwijderen/")
        assert response.status_code == 200
        assert not Label.objects.filter(pk=self.label.pk).exists()
        assert response["HX-Redirect"] == reverse("label-admin")

    def test_label_delete_requires_delete_permission(self):
        """Without delete_label the label survives."""
        other = User.objects.create_user(email="nodelete@rijksoverheid.nl", first_name="No", last_name="Delete")
        other.user_permissions.add(Permission.objects.get(codename="view_labelcategory"))
        self.client.force_login(other)

        response = self.client.post(f"/beheer/labels/{self.label.public_id}/verwijderen/")
        assert response.status_code == 403
        assert Label.objects.filter(pk=self.label.pk).exists()

    def test_label_category_delete_requires_delete_permission(self):
        """Without delete_labelcategory the category survives."""
        other = User.objects.create_user(email="nocatdelete@rijksoverheid.nl", first_name="No", last_name="Cat")
        other.user_permissions.add(Permission.objects.get(codename="view_labelcategory"))
        self.client.force_login(other)

        url = f"/beheer/labels/categorie/{self.category.public_id}/verwijderen/"
        response = self.client.post(url)
        assert response.status_code == 403
        assert LabelCategory.objects.filter(pk=self.category.pk).exists()
