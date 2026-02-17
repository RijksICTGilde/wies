from django.contrib.auth.models import Permission
from django.test import Client, TestCase

from wies.core.models import OrganizationUnit, User


class OrganizationAdminViewTest(TestCase):
    """Test the organization admin view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.url = "/instellingen/organisaties/"

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
