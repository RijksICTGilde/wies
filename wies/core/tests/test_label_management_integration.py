from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Colleague, Label, LabelCategory

User = get_user_model()


class LabelManagementIntegrationTest(TestCase):
    """High-level integration tests for complete label lifecycle"""

    def setUp(self):
        """Create test data"""
        self.client = Client()

        # Create admin user with all label permissions
        self.admin_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )

        # Grant all label permissions
        label_cat_permissions = Permission.objects.filter(
            codename__in=["view_labelcategory", "add_labelcategory", "change_labelcategory", "delete_labelcategory"]
        )
        label_permissions = Permission.objects.filter(
            codename__in=["view_label", "add_label", "change_label", "delete_label"]
        )
        user_permissions = Permission.objects.filter(
            codename__in=["view_user", "add_user", "change_user", "delete_user"]
        )
        self.admin_user.user_permissions.add(*label_cat_permissions, *label_permissions, *user_permissions)

        # Create unprivileged user
        self.regular_user = User.objects.create_user(
            email="regular@rijksoverheid.nl",
            first_name="Regular",
            last_name="User",
        )

    def test_complete_label_lifecycle(self):
        """Test: Create category → Create label → Assign to user → Verify in list → Delete"""
        self.client.force_login(self.admin_user)

        # Step 1: A label category (categories are managed via the
        # "Categorieën beheren" sheet; created directly here as a fixture).
        category = LabelCategory.objects.create(name="Test Category", color="#F9DFDD")
        assert category.color == "#F9DFDD"

        # Step 2: Create a label in that category
        response = self.client.post(
            reverse("label-form-create"), {"category": category.id, "name": "Test Label"}, follow=True
        )
        assert response.status_code == 200

        label = Label.objects.get(name="Test Label", category=category)

        # Step 3: Create a user with that label
        response = self.client.post(
            reverse("user-create"),
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@rijksoverheid.nl",
                "category_Test Category": label.public_id,
            },
            follow=True,
        )
        assert response.status_code == 200

        user = User.objects.get(email="test@rijksoverheid.nl")
        assert label in user.colleague.labels.all()

        response = self.client.get(reverse("admin-users"))
        assert response.status_code == 200
        self.assertContains(response, "Test User")

        # The label survives the category delete under the catch-all
        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": category.public_id}), follow=True
        )
        assert response.status_code == 200

        assert not LabelCategory.objects.filter(id=category.id).exists()
        label.refresh_from_db()
        assert label.category.name == "Overig"

        user.refresh_from_db()
        assert list(user.colleague.labels.all()) == [label]

    def test_label_edit_propagates_correctly(self):
        """Test: Editing a label name propagates to all assigned users/colleagues"""
        self.client.force_login(self.admin_user)

        # Create category and label
        category = LabelCategory.objects.create(name="Brands", color="#0066CC")
        label = Label.objects.create(name="Original Name", category=category)

        # Assign to colleague (linked to user) and standalone colleague
        user = User.objects.create_user(email="user@rijksoverheid.nl", first_name="Test", last_name="User")
        user_colleague = Colleague.objects.create(
            user=user, name="Test User", email="user@rijksoverheid.nl", source="wies"
        )
        user_colleague.labels.add(label)

        colleague = Colleague.objects.create(name="Test Colleague", email="colleague@rijksoverheid.nl", source="wies")
        colleague.labels.add(label)

        response = self.client.post(
            reverse("label-form-edit", kwargs={"public_id": label.public_id}),
            {"name": "Updated Name", "category": category.id},
        )
        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("label-admin")

        # Verify the label name changed
        label.refresh_from_db()
        assert label.name == "Updated Name"

        # Verify both colleagues still have the label
        assert label in user_colleague.labels.all()
        assert label in colleague.labels.all()

    def test_permission_boundaries_enforced(self):
        """Test: Users without permissions cannot access label management"""
        self.client.force_login(self.regular_user)

        # Attempt to view label list
        response = self.client.get(reverse("label-admin"))
        assert response.status_code == 403

        # Attempt to manage categories (create/rename via the beheer sheet)
        response = self.client.get(reverse("label-category-manage"))
        assert response.status_code == 403

        # Create a category as admin first
        category = LabelCategory.objects.create(name="Test", color="#111111")

        # Attempt to delete as regular user
        response = self.client.post(reverse("label-category-delete", kwargs={"public_id": category.public_id}))
        assert response.status_code == 403

        # Verify category still exists
        assert LabelCategory.objects.filter(id=category.id).exists()

    def test_category_delete_moves_labels_to_fallback(self):
        """Deleting a category re-homes its labels under "Overig" instead of
        deleting them, so the colleagues who carry them keep them."""
        self.client.force_login(self.admin_user)

        # Create category with multiple labels
        category = LabelCategory.objects.create(name="Skills", color="#00AA00")
        label1 = Label.objects.create(name="Python", category=category)
        label2 = Label.objects.create(name="Django", category=category)
        label3 = Label.objects.create(name="JavaScript", category=category)

        # Assign labels to colleagues linked to users
        user1 = User.objects.create_user(email="user1@rijksoverheid.nl", first_name="User", last_name="One")
        colleague1 = Colleague.objects.create(
            user=user1, name="User One", email="user1@rijksoverheid.nl", source="wies"
        )
        colleague1.labels.add(label1, label2)

        user2 = User.objects.create_user(email="user2@rijksoverheid.nl", first_name="User", last_name="Two")
        colleague2 = Colleague.objects.create(
            user=user2, name="User Two", email="user2@rijksoverheid.nl", source="wies"
        )
        colleague2.labels.add(label2, label3)

        # Delete the category
        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": category.public_id}), follow=True
        )
        assert response.status_code == 200

        fallback = LabelCategory.objects.get(name="Overig")
        assert set(fallback.labels.values_list("name", flat=True)) == {"Python", "Django", "JavaScript"}

        colleague1.refresh_from_db()
        colleague2.refresh_from_db()
        assert set(colleague1.labels.values_list("name", flat=True)) == {"Python", "Django"}
        assert set(colleague2.labels.values_list("name", flat=True)) == {"Django", "JavaScript"}

    def test_label_without_category_lands_in_fallback(self):
        """Geen categorie gekozen: het label komt onder "Overig" te staan."""
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("label-form-create"), {"name": "Zwevend label"})
        assert response.status_code == 200

        label = Label.objects.get(name="Zwevend label")
        assert label.category.name == "Overig"

    def test_category_delete_merges_duplicate_label_names(self):
        """A label whose name already exists in the catch-all is merged: one
        label survives and it carries the colleagues of both."""
        self.client.force_login(self.admin_user)

        fallback = LabelCategory.objects.create(name="Overig", color="#DCE3EA")
        kept = Label.objects.create(name="Python", category=fallback)
        doomed_category = LabelCategory.objects.create(name="Skills", color="#00AA00")
        duplicate = Label.objects.create(name="Python", category=doomed_category)

        user = User.objects.create_user(email="dup@rijksoverheid.nl", first_name="Dup", last_name="User")
        colleague = Colleague.objects.create(user=user, name="Dup User", email="dup@rijksoverheid.nl", source="wies")
        colleague.labels.add(duplicate)

        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": doomed_category.public_id}), follow=True
        )
        assert response.status_code == 200

        assert not Label.objects.filter(pk=duplicate.pk).exists()
        assert list(colleague.labels.all()) == [kept]

    def test_category_delete_can_take_its_labels_with_it(self):
        """De derde knop in de dialoog: categorie én labels weg, geen verhuizing."""
        self.client.force_login(self.admin_user)

        category = LabelCategory.objects.create(name="Skills", color="#00AA00")
        label = Label.objects.create(name="Python", category=category)

        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": category.public_id}),
            {"labels_verwijderen": "1"},
            follow=True,
        )
        assert response.status_code == 200

        assert not Label.objects.filter(pk=label.pk).exists()
        assert not LabelCategory.objects.filter(name="Overig").exists()

    def test_deleting_the_fallback_itself_removes_its_labels(self):
        """Nothing is left to catch them, so deleting "Overig" is a real delete."""
        self.client.force_login(self.admin_user)

        fallback = LabelCategory.objects.create(name="Overig", color="#DCE3EA")
        label = Label.objects.create(name="Los label", category=fallback)

        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": fallback.public_id}), follow=True
        )
        assert response.status_code == 200

        assert not Label.objects.filter(pk=label.pk).exists()

    def test_duplicate_label_name_in_same_category_prevented(self):
        """Test: Cannot create duplicate label names within the same category"""
        self.client.force_login(self.admin_user)

        # Create category and label
        category = LabelCategory.objects.create(name="Test Category", color="#AABBCC")
        Label.objects.create(name="Duplicate Name", category=category)

        # Attempt to create another label with same name in same category
        self.client.post(reverse("label-form-create"), {"category": category.id, "name": "Duplicate Name"})

        # Should show error or validation failure
        # The exact status depends on form validation - could be 200 with error message
        # or redirect, but duplicate should not be created
        duplicate_count = Label.objects.filter(name="Duplicate Name", category=category).count()
        assert duplicate_count == 1, "Duplicate label was created when it should have been prevented"

    def test_same_label_name_in_different_categories_allowed(self):
        """Test: Can create labels with same name in different categories"""
        self.client.force_login(self.admin_user)

        # Create two categories
        category1 = LabelCategory.objects.create(name="Category 1", color="#111111")
        category2 = LabelCategory.objects.create(name="Category 2", color="#222222")

        # Create label with same name in both categories
        response1 = self.client.post(
            reverse("label-form-create"),
            {"category": category1.id, "name": "Common Name"},
        )

        assert response1.status_code == 200

        response2 = self.client.post(
            reverse("label-form-create"), {"category": category2.id, "name": "Common Name"}, follow=True
        )
        assert response2.status_code == 200

        # Verify both labels exist
        assert Label.objects.filter(name="Common Name", category=category1).exists()
        assert Label.objects.filter(name="Common Name", category=category2).exists()
        assert Label.objects.filter(name="Common Name").count() == 2

    def test_navigation_menu_visibility(self):
        """Test: Beheer menu only visible to users with appropriate permissions"""
        # Regular user without permissions
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, "Beheer")

        # Admin user with permissions
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "Beheer")


class LabelCategoryManageFormsetTest(TestCase):
    """The "Categorieën beheren" sheet: add/remove rows and save run through the
    single manage endpoint, which re-renders the body from the posted state."""

    GREY = "#DCE3EA"

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Admin", last_name="User")
        self.admin_user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=["view_labelcategory", "add_labelcategory", "change_labelcategory", "delete_labelcategory"]
            )
        )
        self.client.force_login(self.admin_user)
        self.url = reverse("label-category-manage")

    def _management(self, total, initial):
        return {
            "form-TOTAL_FORMS": str(total),
            "form-INITIAL_FORMS": str(initial),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }

    def test_plain_submit_saves(self):
        """A plain submit (no extra_row/delete_new_row_index) saves."""
        data = self._management(total=1, initial=0)
        data.update({"form-0-name": "Solo", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == reverse("label-admin")
        assert set(LabelCategory.objects.values_list("name", flat=True)) == {"Solo"}

    def test_save_creates_multiple_new_rows_ignoring_a_gap(self):
        """Saving with two new rows at non-contiguous indices (a removed middle
        row leaves a gap) creates both categories and skips the gap."""
        data = self._management(total=3, initial=0)
        data.update(
            {
                "form-0-name": "Alpha",
                "form-0-color": self.GREY,
                # index 1 intentionally absent — simulates a removed new row
                "form-2-name": "Gamma",
                "form-2-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == reverse("label-admin")
        assert set(LabelCategory.objects.values_list("name", flat=True)) == {"Alpha", "Gamma"}

    def test_extra_row_adds_a_blank_row_and_keeps_typed_values(self):
        """extra_row re-renders the body with one more blank row and no
        validation errors, preserving already-typed values."""
        data = self._management(total=1, initial=0)
        data.update({"extra_row": "1", "form-0-name": "Halfway", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert not LabelCategory.objects.exists()
        # Typed value survives and the counter grew to two rows.
        self.assertContains(response, "Halfway")
        self.assertContains(response, "form-TOTAL_FORMS")
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'name="form-1-name"')  # the new blank row
        self.assertNotContains(response, "verplicht")  # no premature "required"

    def test_delete_new_row_index_removes_row_and_renumbers(self):
        """Removing a new row drops it and renumbers the remaining new rows so no
        blank gap row reappears; other typed values survive."""
        data = self._management(total=3, initial=0)
        data.update(
            {
                "delete_new_row_index": "1",
                "form-0-name": "Alpha",
                "form-0-color": self.GREY,
                "form-1-name": "Beta",
                "form-1-color": self.GREY,
                "form-2-name": "Gamma",
                "form-2-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert not LabelCategory.objects.exists()
        self.assertContains(response, 'value="Alpha"')
        self.assertNotContains(response, 'value="Beta"')
        self.assertContains(response, 'value="Gamma"')
        # Two rows left, contiguous — Gamma renumbered to index 1, no gap.
        self.assertContains(response, "form-TOTAL_FORMS")
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'name="form-1-name" value="Gamma"')

    def test_delete_then_add_does_not_resurrect_the_removed_row(self):
        """Regression: removing a middle new row then adding another must not
        resurrect the removed row as a blank (delete renumbers contiguously)."""
        # Delete the middle of three new rows → server returns two contiguous rows.
        data = self._management(total=3, initial=0)
        data.update(
            {
                "delete_new_row_index": "1",
                "form-0-name": "Alpha",
                "form-0-color": self.GREY,
                "form-1-name": "Beta",
                "form-1-color": self.GREY,
                "form-2-name": "Gamma",
                "form-2-color": self.GREY,
            }
        )
        after_delete = self.client.post(self.url, data)
        self.assertContains(after_delete, 'name="form-1-name" value="Gamma"')

        # Now add a row on the compacted state (2 rows). The new blank lands at
        # index 2; there is no resurrected "Beta" and no stray empty index-1 row.
        add_data = self._management(total=2, initial=0)
        add_data.update(
            {
                "extra_row": "1",
                "form-0-name": "Alpha",
                "form-0-color": self.GREY,
                "form-1-name": "Gamma",
                "form-1-color": self.GREY,
            }
        )
        after_add = self.client.post(self.url, add_data)
        self.assertContains(after_add, 'value="Alpha"')
        self.assertContains(after_add, 'value="Gamma"')
        self.assertNotContains(after_add, 'value="Beta"')
        # Three rows now, the third blank; no phantom blank between the two filled.
        self.assertContains(after_add, "form-TOTAL_FORMS")
        self.assertContains(after_add, 'value="3"')
        self.assertContains(after_add, 'name="form-2-name"')

    def test_add_row_does_not_flash_validation_errors(self):
        """Adding a row must not flash validation errors on other rows, even a
        new row that duplicates an existing category — quiet until Opslaan.

        Regression: as_field_group() reads field.errors, which lazily triggers
        full_clean; the view suppresses that on a re-render.
        """
        existing = LabelCategory.objects.create(name="b", color=self.GREY)
        data = self._management(total=2, initial=1)
        data.update(
            {
                "extra_row": "1",
                "form-0-id": str(existing.pk),
                "form-0-name": "b",
                "form-0-color": self.GREY,
                "form-1-name": "b",  # duplicates existing → would error on save
                "form-1-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        # No validation flashed while still editing.
        self.assertNotContains(response, "nldd-form-field-error-text")
        self.assertNotContains(response, "bestaat al")
        # The typed duplicate value is preserved, and the blank new row is added.
        self.assertContains(response, 'name="form-1-name" value="b"')
        self.assertContains(response, 'name="form-2-name"')

    def test_save_with_blanked_existing_name_shows_error_and_does_not_save(self):
        """Blanking a required name and saving is rejected: re-render with a
        visible wired error, no redirect, nothing saved."""
        category = LabelCategory.objects.create(name="Skills", color=self.GREY)
        data = self._management(total=1, initial=1)
        data.update({"form-0-id": str(category.pk), "form-0-name": "", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") is None
        self.assertContains(response, "Dit veld is verplicht.")
        self.assertContains(response, "nldd-form-field-error-text")
        category.refresh_from_db()
        assert category.name == "Skills"

    def test_remove_then_save_with_duplicate_name_shows_error_without_phantom_row(self):
        """Remove a row, then save into a validation error (duplicate name): the
        error re-render must show no phantom blank row where the removed one was."""
        existing = LabelCategory.objects.create(name="Bestaand", color=self.GREY)

        # Existing row (index 0) + three new rows. Remove the middle new one.
        remove = self._management(total=4, initial=1)
        remove.update(
            {
                "delete_new_row_index": "2",
                "form-0-id": str(existing.pk),
                "form-0-name": "Bestaand",
                "form-0-color": self.GREY,
                "form-1-name": "Nieuw1",
                "form-1-color": self.GREY,
                "form-2-name": "WegHiermee",
                "form-2-color": self.GREY,
                "form-3-name": "Nieuw3",
                "form-3-color": self.GREY,
            }
        )
        after_remove = self.client.post(self.url, remove)
        # Compacted: existing at 0, Nieuw1 at 1, Nieuw3 at 2 — WegHiermee gone.
        self.assertNotContains(after_remove, "WegHiermee")
        self.assertContains(after_remove, 'name="form-2-name" value="Nieuw3"')

        # Save the compacted state, but make the last new row duplicate the
        # existing category's name → unique validation fails.
        save = self._management(total=3, initial=1)
        save.update(
            {
                "form-0-id": str(existing.pk),
                "form-0-name": "Bestaand",
                "form-0-color": self.GREY,
                "form-1-name": "Nieuw1",
                "form-1-color": self.GREY,
                "form-2-name": "Bestaand",  # duplicate → error
                "form-2-color": self.GREY,
            }
        )
        response = self.client.post(self.url, save)
        content = response.content.decode()

        # Nothing saved: no redirect, and no second "Bestaand" created.
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") is None
        assert LabelCategory.objects.filter(name="Bestaand").count() == 1

        # The error is wired and visible on the duplicate row.
        self.assertContains(response, "nldd-form-field-error-text")
        self.assertContains(response, "invalid")

        # Surviving rows keep their values, and there is NO phantom blank row:
        # exactly three rows, contiguous, none with an empty name between filled.
        self.assertContains(response, 'value="Nieuw1"')
        self.assertContains(response, 'name="form-TOTAL_FORMS"')
        self.assertContains(response, 'value="3"')
        assert content.count("data-category-row") == 3
        assert 'name="form-1-name" value=""' not in content
