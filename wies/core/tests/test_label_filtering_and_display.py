from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Label, LabelCategory, Placement, Service, Skill

User = get_user_model()


class LabelFilteringAndDisplayTest(TestCase):
    """High-level integration tests for label filtering and display in views"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create user with view permissions
        self.auth_user = User.objects.create_user(
            email="auth@rijksoverheid.nl",
            first_name="Auth",
            last_name="User",
        )
        view_user_perm = Permission.objects.get(codename="view_user")
        self.auth_user.user_permissions.add(view_user_perm)

        # Create label categories and labels (use get_or_create to avoid conflicts).
        self.thema_category, _ = LabelCategory.objects.get_or_create(name="Thema", defaults={"color": "#0066CC"})
        self.skills_category, _ = LabelCategory.objects.get_or_create(name="Skills", defaults={"color": "#00AA00"})

        self.thema_a_label, _ = Label.objects.get_or_create(name="Digitale weerbaarheid", category=self.thema_category)
        self.thema_b_label, _ = Label.objects.get_or_create(
            name="Artificiële intelligentie", category=self.thema_category
        )
        self.thema_c_label, _ = Label.objects.get_or_create(name="Netwerksamenwerking", category=self.thema_category)

        self.python_label, _ = Label.objects.get_or_create(name="Python", category=self.skills_category)
        self.django_label, _ = Label.objects.get_or_create(name="Django", category=self.skills_category)

        # Create users with linked colleagues that have labels
        self.user1 = User.objects.create_user(email="user1@rijksoverheid.nl", first_name="User", last_name="One")
        self.user1_colleague = Colleague.objects.create(
            user=self.user1, name="User One", email="user1@rijksoverheid.nl", source="wies"
        )
        self.user1_colleague.labels.add(self.thema_a_label, self.python_label)

        self.user2 = User.objects.create_user(email="user2@rijksoverheid.nl", first_name="User", last_name="Two")
        self.user2_colleague = Colleague.objects.create(
            user=self.user2, name="User Two", email="user2@rijksoverheid.nl", source="wies"
        )
        self.user2_colleague.labels.add(self.thema_b_label)

        self.user3 = User.objects.create_user(email="user3@rijksoverheid.nl", first_name="User", last_name="Three")
        self.user3_colleague = Colleague.objects.create(
            user=self.user3, name="User Three", email="user3@rijksoverheid.nl", source="wies"
        )
        self.user3_colleague.labels.add(self.thema_a_label, self.django_label)

        # Create colleagues (without users) with labels
        self.colleague1 = Colleague.objects.create(
            name="Colleague One", email="colleague1@rijksoverheid.nl", source="wies"
        )
        self.colleague1.labels.add(self.thema_a_label)

        self.colleague2 = Colleague.objects.create(
            name="Colleague Two", email="colleague2@rijksoverheid.nl", source="wies"
        )
        self.colleague2.labels.add(self.thema_c_label)

        self.colleague3 = Colleague.objects.create(
            name="Colleague Three", email="colleague3@rijksoverheid.nl", source="wies"
        )
        self.colleague3.labels.add(self.thema_a_label)

        # Create placements
        self.assignment = Assignment.objects.create(name="Test Assignment", source="wies")
        self.skill = Skill.objects.create(name="Python")
        self.service = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")

        self.placement1 = Placement.objects.create(colleague=self.colleague1, service=self.service, source="wies")
        self.placement2 = Placement.objects.create(colleague=self.colleague2, service=self.service, source="wies")
        self.placement3 = Placement.objects.create(colleague=self.colleague3, service=self.service, source="wies")

    def test_filter_users_by_label(self):
        """Test: Filtering users by label returns only users with that label"""
        self.client.force_login(self.auth_user)

        # Filter by the "Digitale weerbaarheid" label
        response = self.client.get(reverse("admin-users"), {"labels": self.thema_a_label.public_id})
        assert response.status_code == 200

        # user1 and user3 have the thema-A label, user2 doesn't
        self.assertContains(response, "User One")
        self.assertContains(response, "User Three")
        self.assertNotContains(response, "User Two")

    def test_filter_users_by_different_label(self):
        """Test: Filtering by different label returns different users"""
        self.client.force_login(self.auth_user)

        # Filter by the "Artificiële intelligentie" label
        response = self.client.get(reverse("admin-users"), {"labels": self.thema_b_label.public_id})
        assert response.status_code == 200

        # Only user2 has the thema-B label
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

        # Filter by the "Digitale weerbaarheid" label
        response = self.client.get(reverse("home"), {"labels": self.thema_a_label.public_id})
        assert response.status_code == 200

        # colleague1 and colleague3 have the thema-A label, colleague2 doesn't
        self.assertContains(response, "Colleague One")
        self.assertContains(response, "Colleague Three")
        self.assertNotContains(response, "Colleague Two")

    def test_filter_placements_by_third_label(self):
        """Test: Filtering placements by the "Netwerksamenwerking" label"""
        self.client.force_login(self.auth_user)

        # Filter by the "Netwerksamenwerking" label
        response = self.client.get(reverse("home"), {"labels": self.thema_c_label.public_id})
        assert response.status_code == 200

        # Only colleague2 has the thema-C label
        self.assertContains(response, "Colleague Two")
        self.assertNotContains(response, "Colleague One")
        self.assertNotContains(response, "Colleague Three")

    def test_combined_filters_placement_label_and_skill(self):
        """Test: Combining label filter with skill filter"""
        self.client.force_login(self.auth_user)

        # Filter by both label and skill
        response = self.client.get(
            reverse("home"), {"labels": self.thema_a_label.public_id, "rol": self.skill.public_id}
        )
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

        response = self.client.get(reverse("home"))
        assert response.status_code == 200

        # Should show colleague name even without labels
        self.assertContains(response, "No Label Colleague")

    def test_filter_persistence_across_pagination(self):
        """Test: Label filters persist when paginating results"""
        self.client.force_login(self.auth_user)

        # Create many users with linked colleagues with same label to trigger pagination
        for i in range(25):
            user = User.objects.create_user(
                email=f"paginated{i}@rijksoverheid.nl",
                first_name="User",
                last_name=f"{i}",
            )
            colleague = Colleague.objects.create(
                user=user, name=f"User {i}", email=f"paginated{i}@rijksoverheid.nl", source="wies"
            )
            colleague.labels.add(self.thema_a_label)

        # Request first page with label filter
        response = self.client.get(reverse("admin-users"), {"labels": self.thema_a_label.public_id, "pagina": 1})
        assert response.status_code == 200

        # All users on this page should have the label
        # None should be from other labels
        self.assertNotContains(response, "User Two")  # user2 has the thema-B label

    def test_label_filter_dropdown_in_ui(self):
        """Test: Label filter dropdown appears in filter bar"""
        self.client.force_login(self.auth_user)

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200

        # Should have label filter option
        self.assertContains(response, "Label")

        # Should show label names in dropdown format "Category: Label"
        # This depends on implementation of filter_groups in view
        self.assertContains(response, "Digitale weerbaarheid")
        self.assertContains(response, "Artificiële intelligentie")

    def test_multiple_colleagues_same_label_all_shown(self):
        """Test: When multiple colleagues have same label, all placements appear"""
        self.client.force_login(self.auth_user)

        # Both colleague1 and colleague3 have the thema-A label
        response = self.client.get(reverse("home"), {"labels": self.thema_a_label.public_id})
        assert response.status_code == 200

        # Both should be in results
        self.assertContains(response, "Colleague One")
        self.assertContains(response, "Colleague Three")

        # Count placements (should be at least 2)
        content = response.content.decode()
        # Both placements should be visible
        assert "Colleague One" in content
        assert "Colleague Three" in content
