"""Permission gates on the two CSV bulk-import endpoints.

Both create records in bulk, so losing the decorator is worth catching.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague

User = get_user_model()


class CsvImportPermissionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="noimport@rijksoverheid.nl",
            first_name="No",
            last_name="Import",
        )
        # A permission that grants no import right, so the user is authenticated
        # but unauthorised rather than anonymous.
        self.user.user_permissions.add(Permission.objects.get(codename="view_labelcategory"))
        self.client.force_login(self.user)

    def test_user_import_requires_add_user(self):
        response = self.client.get(reverse("user-import-csv"))
        assert response.status_code == 403

    def test_user_import_post_creates_nothing_without_permission(self):
        before = User.objects.count()
        response = self.client.post(reverse("user-import-csv"))
        assert response.status_code == 403
        assert User.objects.count() == before

    def test_assignment_import_requires_all_add_permissions(self):
        response = self.client.get(reverse("assignment-import-csv"))
        assert response.status_code == 403

    def test_assignment_import_denies_a_partial_permission_set(self):
        """add_assignment alone is not enough; the view needs all four."""
        self.user.user_permissions.add(Permission.objects.get(codename="add_assignment"))
        before = (Assignment.objects.count(), Colleague.objects.count())

        response = self.client.post(reverse("assignment-import-csv"))
        assert response.status_code == 403
        assert (Assignment.objects.count(), Colleague.objects.count()) == before
