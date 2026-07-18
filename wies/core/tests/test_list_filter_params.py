from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class ListFilterInvalidLabelParamTests(TestCase):
    """A non-numeric ``?labels=`` value must be ignored instead of raising a 500.
    The org and rol filters already skip non-digit values; the label filter must
    behave the same, so a hand-edited or stale URL degrades gracefully."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="V", last_name="iewer")

    def test_home_ignores_non_numeric_label_param(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "abc"})

        assert response.status_code == 200

    def test_admin_users_ignores_non_numeric_label_param(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin-users"), {"labels": "abc"})

        assert response.status_code == 200

    def test_valid_label_param_still_works(self):
        """A numeric value is still honoured (guards against over-filtering)."""
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"), {"labels": "999999"})

        assert response.status_code == 200
