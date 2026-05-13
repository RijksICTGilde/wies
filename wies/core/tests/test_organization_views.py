from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings

from wies.core.models import OrganizationUnit

User = get_user_model()


@override_settings(DEBUG=True)
class OrganizationAdminViewTest(TestCase):
    """Test the organization admin view (only available in DEBUG mode)"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="test@rijksoverheid.nl", password="testpass123")
        self.url = "/beheer/organisaties/"

    def test_requires_authentication(self):
        response = self.client.get(self.url, follow=False)
        assert response.status_code == 302

    def test_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_accessible_with_permission(self):
        perm = Permission.objects.get(codename="view_organizationunit")
        self.user.user_permissions.add(perm)
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_renders_organization_tree(self):
        perm = Permission.objects.get(codename="view_organizationunit")
        self.user.user_permissions.add(perm)
        self.client.force_login(self.user)

        parent = OrganizationUnit.objects.create(name="Parent Org", label="Parent")
        OrganizationUnit.objects.create(name="Child Org", label="Child", parent=parent)

        response = self.client.get(self.url)
        assert response.status_code == 200
        assert "Parent" in response.content.decode()
        assert "Child" in response.content.decode()
