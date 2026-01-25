from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from wies.core.models import OrganizationUnit, User


class OrganizationUnitViewTestCase(TestCase):
    """Base test case with common setup for organization view tests."""

    def setUp(self):
        # Create a beheerder user with organization permissions
        self.beheerder = User.objects.create_user(
            username="beheerder@test.nl",
            email="beheerder@test.nl",
            password="testpass123",
        )
        # Add organization permissions
        for codename in [
            "view_organizationunit",
            "add_organizationunit",
            "change_organizationunit",
            "delete_organizationunit",
        ]:
            perm = Permission.objects.get(codename=codename)
            self.beheerder.user_permissions.add(perm)

        # Create a regular user without permissions
        self.regular_user = User.objects.create_user(
            username="user@test.nl",
            email="user@test.nl",
            password="testpass123",
        )

        # Create test organizations
        self.ministry = OrganizationUnit.objects.create(
            name="Ministerie van BZK",
            abbreviations=["BZK"],
            organization_type="ministerie",
        )
        self.dg = OrganizationUnit.objects.create(
            name="DGDOO",
            abbreviations=["DGDOO"],
            organization_type="directoraat_generaal",
            parent=self.ministry,
        )


class OrganizationUnitListViewTest(OrganizationUnitViewTestCase):
    def test_list_requires_permission(self):
        """Users without view permission cannot access the list."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("organization-list"))
        assert response.status_code == 403

    def test_list_shows_organizationunits(self):
        """Beheerder can see organization list."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-list"))
        assert response.status_code == 200
        assert "Ministerie van BZK" in response.content.decode()

    def test_list_filters_by_type(self):
        """Type filter works correctly."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-list") + "?type=ministerie")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Ministerie van BZK" in content

    def test_list_search(self):
        """Search filter works correctly."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-list") + "?search=BZK")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Ministerie van BZK" in content

    def test_list_search_previous_names(self):
        """Search also finds organizations by their previous names."""
        OrganizationUnit.objects.create(
            name="Huidige Naam",
            organization_type="gemeente",
            previous_names=[{"name": "Vorige Naam", "until": "2024-01-01"}],
        )
        self.client.force_login(self.beheerder)

        # Search by previous name should find the org
        response = self.client.get(reverse("organization-list") + "?search=Vorige")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Huidige Naam" in content

    def test_list_hides_inactive_by_default(self):
        """Inactive organizations are hidden by default in the view."""
        OrganizationUnit.objects.create(
            name="Inactive Org",
            organization_type="gemeente",
            is_active=False,
        )
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-list"))
        content = response.content.decode()
        assert "Inactive Org" not in content

    def test_list_unauthenticated_redirects(self):
        """Unauthenticated users are redirected to login."""
        response = self.client.get(reverse("organization-list"))
        assert response.status_code == 302
        assert "inloggen" in response.url


class OrganizationUnitCreateViewTest(OrganizationUnitViewTestCase):
    def test_create_requires_permission(self):
        """Users without add permission cannot create organizations."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("organization-create"))
        assert response.status_code == 403

    def test_create_form_get(self):
        """Beheerder can access create form."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-create"))
        assert response.status_code == 200
        assert "Nieuwe organisatie-eenheid" in response.content.decode()

    def test_create_organizationunit(self):
        """Beheerder can create an organization."""
        self.client.force_login(self.beheerder)
        response = self.client.post(
            reverse("organization-create"),
            {
                "name": "Nieuwe Gemeente",
                "abbreviations_input": "",
                "organization_type": "gemeente",
                "parent": "",
                "is_active": True,
            },
        )
        # Should redirect on success
        assert response.status_code in [200, 302]
        assert OrganizationUnit.objects.filter(name="Nieuwe Gemeente").exists()


class OrganizationUnitEditViewTest(OrganizationUnitViewTestCase):
    def test_edit_requires_permission(self):
        """Users without change permission cannot edit organizations."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("organization-edit", args=[self.ministry.pk]))
        assert response.status_code == 403

    def test_edit_form_get(self):
        """Beheerder can access edit form."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-edit", args=[self.ministry.pk]))
        assert response.status_code == 200
        assert "Ministerie van BZK" in response.content.decode()

    def test_edit_organizationunit(self):
        """Beheerder can edit an organization."""
        self.client.force_login(self.beheerder)
        response = self.client.post(
            reverse("organization-edit", args=[self.ministry.pk]),
            {
                "name": "Ministerie van BZK (updated)",
                "abbreviations_input": "BZK",
                "organization_type": "ministerie",
                "parent": "",
                "is_active": True,
            },
        )
        assert response.status_code in [200, 302]
        self.ministry.refresh_from_db()
        assert self.ministry.name == "Ministerie van BZK (updated)"

    def test_edit_shows_children_warning(self):
        """Edit form shows warning when organization has children."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-edit", args=[self.ministry.pk]))
        assert response.status_code == 200
        content = response.content.decode()
        assert "onderliggende eenheden" in content

    def test_edit_nonexistent_returns_404(self):
        """Editing non-existent organization returns 404."""
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-edit", args=[99999]))
        assert response.status_code == 404

    def test_edit_leaf_shows_delete_button(self):
        """Edit form for leaf org shows delete button."""
        leaf = OrganizationUnit.objects.create(
            name="Leaf Org",
            organization_type="afdeling",
        )
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-edit", args=[leaf.pk]))
        assert response.status_code == 200
        content = response.content.decode()
        assert "Verwijderen" in content


class OrganizationUnitDeleteViewTest(OrganizationUnitViewTestCase):
    def test_delete_requires_permission(self):
        """Users without delete permission cannot delete organizations."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("organization-delete", args=[self.dg.pk]))
        assert response.status_code == 403

    def test_delete_confirmation(self):
        """Beheerder sees delete confirmation."""
        leaf = OrganizationUnit.objects.create(
            name="Leaf Org",
            organization_type="afdeling",
        )
        self.client.force_login(self.beheerder)
        response = self.client.get(reverse("organization-delete", args=[leaf.pk]))
        assert response.status_code == 200
        assert "Weet je zeker" in response.content.decode()

    def test_delete_organizationunit(self):
        """Beheerder can delete organization without children."""
        leaf = OrganizationUnit.objects.create(
            name="Leaf Org",
            organization_type="afdeling",
        )
        self.client.force_login(self.beheerder)
        # Use HTMX header as delete is triggered from modal
        response = self.client.post(reverse("organization-delete", args=[leaf.pk]), headers={"hx-request": "true"})
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == "/instellingen/organisaties/"
        assert not OrganizationUnit.objects.filter(pk=leaf.pk).exists()

    def test_cannot_delete_with_children(self):
        """Cannot delete organization that has children."""
        self.client.force_login(self.beheerder)
        # Use HTMX header to get the modal response
        response = self.client.get(
            reverse("organization-delete", args=[self.ministry.pk]), headers={"hx-request": "true"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "onderliggende eenheden" in content


class OrganizationUnitFormValidationTest(OrganizationUnitViewTestCase):
    def test_hierarchy_validation_in_form(self):
        """Form validation prevents invalid hierarchy."""
        self.client.force_login(self.beheerder)
        afdeling = OrganizationUnit.objects.create(
            name="Afdeling X",
            organization_type="afdeling",
        )
        # Try to create a DG under an Afdeling (invalid)
        response = self.client.post(
            reverse("organization-create"),
            {
                "name": "Ongeldig DG",
                "abbreviations_input": "",
                "organization_type": "directoraat_generaal",
                "parent": afdeling.pk,
                "is_active": True,
            },
        )
        # Form should show error, not redirect
        assert response.status_code == 200
        assert not OrganizationUnit.objects.filter(name="Ongeldig DG").exists()

    def test_root_type_cannot_have_parent(self):
        """Root type (ministerie) cannot have parent."""
        self.client.force_login(self.beheerder)
        response = self.client.post(
            reverse("organization-create"),
            {
                "name": "Ongeldig Ministerie",
                "abbreviations_input": "",
                "organization_type": "ministerie",
                "parent": self.ministry.pk,  # ministerie under ministerie
                "is_active": True,
            },
        )
        # Form should show error, not redirect
        assert response.status_code == 200
        assert not OrganizationUnit.objects.filter(name="Ongeldig Ministerie").exists()
