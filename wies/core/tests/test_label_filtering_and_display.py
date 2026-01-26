from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import (
    Assignment,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
    User,
)


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class LabelFilteringAndDisplayTest(TestCase):
    """High-level integration tests for label filtering and display in views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create user with view permissions
        self.auth_user = User.objects.create(
            username="auth_user",
            email="auth@example.com",
            first_name="Auth",
            last_name="User",
        )
        view_user_perm = Permission.objects.get(codename="view_user")
        self.auth_user.user_permissions.add(view_user_perm)

        # Create label categories and labels (use get_or_create to avoid conflicts)
        self.merken_category, _ = LabelCategory.objects.get_or_create(name="Merk", defaults={"color": "#0066CC"})
        self.skills_category, _ = LabelCategory.objects.get_or_create(name="Skills", defaults={"color": "#00AA00"})

        self.rig_label, _ = Label.objects.get_or_create(name="Rijks ICT Gilde", category=self.merken_category)
        self.rc_label, _ = Label.objects.get_or_create(name="Rijksconsultants", category=self.merken_category)
        self.iir_label, _ = Label.objects.get_or_create(name="I-Interim Rijk", category=self.merken_category)

        self.python_label, _ = Label.objects.get_or_create(name="Python", category=self.skills_category)
        self.django_label, _ = Label.objects.get_or_create(name="Django", category=self.skills_category)

        # Create users with labels
        self.user1 = User.objects.create(username="user1", email="user1@test.com", first_name="User", last_name="One")
        self.user1.labels.add(self.rig_label, self.python_label)

        self.user2 = User.objects.create(username="user2", email="user2@test.com", first_name="User", last_name="Two")
        self.user2.labels.add(self.rc_label)

        self.user3 = User.objects.create(username="user3", email="user3@test.com", first_name="User", last_name="Three")
        self.user3.labels.add(self.rig_label, self.django_label)

        # Create colleagues with labels
        self.colleague1 = Colleague.objects.create(name="Colleague One", email="colleague1@test.com", source="wies")
        self.colleague1.labels.add(self.rig_label)

        self.colleague2 = Colleague.objects.create(name="Colleague Two", email="colleague2@test.com", source="wies")
        self.colleague2.labels.add(self.iir_label)

        self.colleague3 = Colleague.objects.create(name="Colleague Three", email="colleague3@test.com", source="wies")
        self.colleague3.labels.add(self.rig_label)

        # Create placements
        self.organization = OrganizationUnit.objects.create(
            name="Test Organization", abbreviations=["TO"], organization_type="ministerie"
        )
        self.assignment = Assignment.objects.create(name="Test Assignment", source="wies", status="INGEVULD")
        self.skill = Skill.objects.create(name="Python")
        self.service = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")

        self.placement1 = Placement.objects.create(colleague=self.colleague1, service=self.service, source="wies")
        self.placement2 = Placement.objects.create(colleague=self.colleague2, service=self.service, source="wies")
        self.placement3 = Placement.objects.create(colleague=self.colleague3, service=self.service, source="wies")

    def test_filter_users_by_label(self):
        """Test: Filtering users by label returns only users with that label"""
        self.client.force_login(self.auth_user)

        # Filter by Rijks ICT Gilde label
        response = self.client.get(reverse("admin-users"), {"labels": self.rig_label.id})
        assert response.status_code == 200

        # user1 and user3 have RIG label, user2 doesn't
        self.assertContains(response, "User One")
        self.assertContains(response, "User Three")
        self.assertNotContains(response, "User Two")

    def test_filter_users_by_different_label(self):
        """Test: Filtering by different label returns different users"""
        self.client.force_login(self.auth_user)

        # Filter by Rijksconsultants label
        response = self.client.get(reverse("admin-users"), {"labels": self.rc_label.id})
        assert response.status_code == 200

        # Only user2 has RC label
        self.assertContains(response, "User Two")
        self.assertNotContains(response, "User One")
        self.assertNotContains(response, "User Three")

    def test_filter_users_no_label_shows_all(self):
        """Test: No label filter shows all users"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200

        # All users should be visible (excluding superusers)
        self.assertContains(response, "User One")
        self.assertContains(response, "User Two")
        self.assertContains(response, "User Three")

    def test_filter_users_invalid_label_id(self):
        """Test: Invalid label ID shows no results"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse("admin-users"), {"labels": 99999})
        assert response.status_code == 200

        # No users should match invalid label
        self.assertNotContains(response, "User One")
        self.assertNotContains(response, "User Two")
        self.assertNotContains(response, "User Three")

    def test_filter_placements_by_colleague_label(self):
        """Test: Filtering placements by colleague label works correctly"""
        self.client.force_login(self.auth_user)

        # Filter by Rijks ICT Gilde label
        response = self.client.get(reverse("placements"), {"labels": self.rig_label.id})
        assert response.status_code == 200

        # colleague1 and colleague3 have RIG label, colleague2 doesn't
        self.assertContains(response, "Colleague One")
        self.assertContains(response, "Colleague Three")
        self.assertNotContains(response, "Colleague Two")

    def test_filter_placements_by_iir_label(self):
        """Test: Filtering placements by I-Interim Rijk label"""
        self.client.force_login(self.auth_user)

        # Filter by I-Interim Rijk label
        response = self.client.get(reverse("placements"), {"labels": self.iir_label.id})
        assert response.status_code == 200

        # Only colleague2 has IIR label
        self.assertContains(response, "Colleague Two")
        self.assertNotContains(response, "Colleague One")
        self.assertNotContains(response, "Colleague Three")

    def test_combined_filters_placement_label_and_skill(self):
        """Test: Combining label filter with skill filter"""
        self.client.force_login(self.auth_user)

        # Filter by both label and skill
        response = self.client.get(reverse("placements"), {"labels": self.rig_label.id, "rol": self.skill.id})
        assert response.status_code == 200

        # Should show placements matching both filters
        self.assertContains(response, "Colleague One")
        self.assertContains(response, "Colleague Three")
        self.assertNotContains(response, "Colleague Two")

    def test_empty_filter_state_handling(self):
        """Test: Empty filter states handled gracefully"""
        self.client.force_login(self.auth_user)

        # Create colleague without labels
        no_label_colleague = Colleague.objects.create(
            name="No Label Colleague", email="nolabel@colleague.com", source="wies"
        )

        # Create placement for colleague without labels
        Placement.objects.create(colleague=no_label_colleague, service=self.service, source="wies")

        response = self.client.get(reverse("placements"))
        assert response.status_code == 200

        # Should show colleague name even without labels
        self.assertContains(response, "No Label Colleague")

    def test_filter_persistence_across_pagination(self):
        """Test: Label filters persist when paginating results"""
        self.client.force_login(self.auth_user)

        # Create many users with same label to trigger pagination
        for i in range(25):
            user = User.objects.create(
                username=f"paginated_user_{i}", email=f"paginated{i}@test.com", first_name="User", last_name=f"{i}"
            )
            user.labels.add(self.rig_label)

        # Request first page with label filter
        response = self.client.get(reverse("admin-users"), {"labels": self.rig_label.id, "pagina": 1})
        assert response.status_code == 200

        # All users on this page should have the label
        # None should be from other labels
        self.assertNotContains(response, "User Two")  # user2 has rc_label

    def test_label_filter_dropdown_in_ui(self):
        """Test: Label filter dropdown appears in filter bar"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200

        # Should have label filter option
        self.assertContains(response, "Label")

        # Should show label names in dropdown format "Category: Label"
        # This depends on implementation of filter_groups in view
        self.assertContains(response, "Rijks ICT Gilde")
        self.assertContains(response, "Rijksconsultants")

    def test_multiple_colleagues_same_label_all_shown(self):
        """Test: When multiple colleagues have same label, all placements appear"""
        self.client.force_login(self.auth_user)

        # Both colleague1 and colleague3 have rig_label
        response = self.client.get(reverse("placements"), {"labels": self.rig_label.id})
        assert response.status_code == 200

        # Both should be in results
        self.assertContains(response, "Colleague One")
        self.assertContains(response, "Colleague Three")

        # Count placements (should be at least 2)
        content = response.content.decode()
        # Both placements should be visible
        assert "Colleague One" in content
        assert "Colleague Three" in content
