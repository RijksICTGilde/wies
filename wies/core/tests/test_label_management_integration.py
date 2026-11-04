import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Colleague, Label, LabelCategory
from wies.core.roles import ROLE_BUSINESS_MANAGER, ROLE_CONSULTANT, ROLE_USER_ADMIN, setup_roles
from wies.core.tests.role_helpers import STAFF_EMAIL, make_staff_user

User = get_user_model()


class LabelManagementIntegrationTest(TestCase):
    """Integration tests for the complete label lifecycle."""

    def setUp(self):
        """Creates an admin with label permissions and an unprivileged user."""
        self.client = Client()

        self.admin_user = User.objects.create_user(
            email="admin@rijksoverheid.nl",
            first_name="Admin",
            last_name="User",
        )

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

        self.regular_user = User.objects.create_user(
            email="regular@rijksoverheid.nl",
            first_name="Regular",
            last_name="User",
        )

    def test_complete_label_lifecycle(self):
        """Creating a category and label, assigning it, then deleting it all work."""
        # Creating a user also sets contract hours, which only this role may keep.
        self.admin_user.groups.add(Group.objects.get_or_create(name=ROLE_USER_ADMIN)[0])
        self.client.force_login(self.admin_user)

        # Categories are managed via a sheet, so create one directly as a fixture.
        category = LabelCategory.objects.create(name="Test Category", color="#F9DFDD")
        assert category.color == "#F9DFDD"

        response = self.client.post(
            reverse("label-form-create"), {"category": category.id, "name": "Test Label"}, follow=True
        )
        assert response.status_code == 200

        label = Label.objects.get(name="Test Label", category=category)

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

        # Deleting the category deletes its labels too (cascade).
        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": category.public_id}), follow=True
        )
        assert response.status_code == 200

        assert not LabelCategory.objects.filter(id=category.id).exists()
        assert not Label.objects.filter(pk=label.pk).exists()

        user.refresh_from_db()
        assert list(user.colleague.labels.all()) == []

    def test_label_edit_propagates_correctly(self):
        """Editing a label name propagates to every colleague carrying it."""
        self.client.force_login(self.admin_user)

        category = LabelCategory.objects.create(name="Brands", color="#0066CC")
        label = Label.objects.create(name="Original Name", category=category)

        # One colleague linked to a user, one standalone.
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

        label.refresh_from_db()
        assert label.name == "Updated Name"

        assert label in user_colleague.labels.all()
        assert label in colleague.labels.all()

    def test_permission_boundaries_enforced(self):
        """A user without permissions cannot reach label management."""
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("label-admin"))
        assert response.status_code == 403

        response = self.client.get(reverse("label-category-manage"))
        assert response.status_code == 403

        category = LabelCategory.objects.create(name="Test", color="#111111")

        response = self.client.post(reverse("label-category-delete", kwargs={"public_id": category.public_id}))
        assert response.status_code == 403

        assert LabelCategory.objects.filter(id=category.id).exists()

    def test_category_delete_removes_its_labels(self):
        """Deleting a category cascades to its labels and to the colleagues
        carrying them."""
        self.client.force_login(self.admin_user)

        category = LabelCategory.objects.create(name="Skills", color="#00AA00")
        label = Label.objects.create(name="Python", category=category)

        user = User.objects.create_user(email="user1@rijksoverheid.nl", first_name="User", last_name="One")
        colleague = Colleague.objects.create(user=user, name="User One", email="user1@rijksoverheid.nl", source="wies")
        colleague.labels.add(label)

        response = self.client.post(
            reverse("label-category-delete", kwargs={"public_id": category.public_id}), follow=True
        )
        assert response.status_code == 200

        assert not LabelCategory.objects.filter(pk=category.pk).exists()
        assert not Label.objects.filter(pk=label.pk).exists()
        colleague.refresh_from_db()
        assert list(colleague.labels.all()) == []

    def test_label_requires_a_category(self):
        """A label without a category is rejected by the form."""
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse("label-form-create"), {"name": "Zwevend label"})
        assert response.status_code == 200

        assert not Label.objects.filter(name="Zwevend label").exists()
        self.assertContains(response, "Dit veld is verplicht.")

    def test_duplicate_label_name_in_same_category_prevented(self):
        """A duplicate label name within one category is prevented."""
        self.client.force_login(self.admin_user)

        category = LabelCategory.objects.create(name="Test Category", color="#AABBCC")
        Label.objects.create(name="Duplicate Name", category=category)

        self.client.post(reverse("label-form-create"), {"category": category.id, "name": "Duplicate Name"})

        duplicate_count = Label.objects.filter(name="Duplicate Name", category=category).count()
        assert duplicate_count == 1, "Duplicate label was created when it should have been prevented"

    def test_same_label_name_in_different_categories_allowed(self):
        """The same label name is allowed in different categories."""
        self.client.force_login(self.admin_user)

        category1 = LabelCategory.objects.create(name="Category 1", color="#111111")
        category2 = LabelCategory.objects.create(name="Category 2", color="#222222")

        response1 = self.client.post(
            reverse("label-form-create"),
            {"category": category1.id, "name": "Common Name"},
        )

        assert response1.status_code == 200

        response2 = self.client.post(
            reverse("label-form-create"), {"category": category2.id, "name": "Common Name"}, follow=True
        )
        assert response2.status_code == 200

        assert Label.objects.filter(name="Common Name", category=category1).exists()
        assert Label.objects.filter(name="Common Name", category=category2).exists()
        assert Label.objects.filter(name="Common Name").count() == 2

    def test_navigation_menu_visibility(self):
        """The Beheer menu follows the Gebruikersbeheerder role, not loose permissions."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, "Beheer")

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertNotContains(response, "Beheer")

        self.admin_user.groups.add(Group.objects.get_or_create(name=ROLE_USER_ADMIN)[0])
        response = self.client.get(reverse("home"))
        assert response.status_code == 200
        self.assertContains(response, "Beheer")


class LabelCategoryManageFormsetTest(TestCase):
    """The "Categorieen beheren" sheet routes add, remove and save through one
    endpoint that re-renders the body from the posted state."""

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
        """A plain submit saves."""
        data = self._management(total=1, initial=0)
        data.update({"form-0-name": "Solo", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == reverse("label-admin")
        assert set(LabelCategory.objects.values_list("name", flat=True)) == {"Solo"}

    def test_save_creates_multiple_new_rows_ignoring_a_gap(self):
        """Saving two new rows at non-contiguous indices creates both and skips
        the gap left by a removed middle row."""
        data = self._management(total=3, initial=0)
        data.update(
            {
                "form-0-name": "Alpha",
                "form-0-color": self.GREY,
                # Index 1 is absent, simulating a removed new row.
                "form-2-name": "Gamma",
                "form-2-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") == reverse("label-admin")
        assert set(LabelCategory.objects.values_list("name", flat=True)) == {"Alpha", "Gamma"}

    def test_extra_row_adds_a_blank_row_and_keeps_typed_values(self):
        """extra_row adds one blank row, keeps typed values and shows no errors."""
        data = self._management(total=1, initial=0)
        data.update({"extra_row": "1", "form-0-name": "Halfway", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert not LabelCategory.objects.exists()
        self.assertContains(response, "Halfway")
        self.assertContains(response, "form-TOTAL_FORMS")
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'name="form-1-name"')
        self.assertNotContains(response, "verplicht")  # No premature "required".

    def test_delete_new_row_index_removes_row_and_renumbers(self):
        """Removing a new row renumbers the rest, so no blank gap row reappears."""
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
        # Two contiguous rows left: Gamma renumbered to index 1.
        self.assertContains(response, "form-TOTAL_FORMS")
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'name="form-1-name" value="Gamma"')

    def test_delete_then_add_does_not_resurrect_the_removed_row(self):
        """Removing a middle new row then adding another does not resurrect the
        removed row as a blank, because delete renumbers contiguously."""
        # Deleting the middle of three rows returns two contiguous rows.
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

        # Adding on the compacted state puts the blank at index 2, with no
        # resurrected "Beta" and no stray empty index-1 row.
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
        # Three rows, the third blank and none phantom between the filled ones.
        self.assertContains(after_add, "form-TOTAL_FORMS")
        self.assertContains(after_add, 'value="3"')
        self.assertContains(after_add, 'name="form-2-name"')

    def test_add_row_does_not_flash_validation_errors(self):
        """Adding a row flashes no validation errors, even when a new row
        duplicates an existing category.

        as_field_group() reads field.errors, which lazily triggers full_clean, so
        the view suppresses that on a re-render.
        """
        existing = LabelCategory.objects.create(name="b", color=self.GREY)
        data = self._management(total=2, initial=1)
        data.update(
            {
                "extra_row": "1",
                "form-0-id": str(existing.pk),
                "form-0-name": "b",
                "form-0-color": self.GREY,
                "form-1-name": "b",  # Duplicates existing, so it would error on save.
                "form-1-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        self.assertNotContains(response, "nldd-validation-item")
        self.assertNotContains(response, "bestaat al")
        self.assertContains(response, 'name="form-1-name" value="b"')
        self.assertContains(response, 'name="form-2-name"')

    def test_save_with_blanked_existing_name_shows_error_and_does_not_save(self):
        """Blanking a required name and saving is rejected with a visible error
        and no redirect."""
        category = LabelCategory.objects.create(name="Skills", color=self.GREY)
        data = self._management(total=1, initial=1)
        data.update({"form-0-id": str(category.pk), "form-0-name": "", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") is None
        self.assertContains(response, "Dit veld is verplicht.")
        self.assertContains(response, "nldd-validation-item")
        category.refresh_from_db()
        assert category.name == "Skills"

    def test_remove_then_save_with_duplicate_name_shows_error_without_phantom_row(self):
        """After removing a row, a save that fails validation re-renders without a
        phantom blank row where the removed one was."""
        existing = LabelCategory.objects.create(name="Bestaand", color=self.GREY)

        # An existing row plus three new ones; remove the middle new one.
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
        # Compacted: existing at 0, Nieuw1 at 1, Nieuw3 at 2.
        self.assertNotContains(after_remove, "WegHiermee")
        self.assertContains(after_remove, 'name="form-2-name" value="Nieuw3"')

        # The last new row duplicates the existing name, so unique validation fails.
        save = self._management(total=3, initial=1)
        save.update(
            {
                "form-0-id": str(existing.pk),
                "form-0-name": "Bestaand",
                "form-0-color": self.GREY,
                "form-1-name": "Nieuw1",
                "form-1-color": self.GREY,
                "form-2-name": "Bestaand",  # Duplicate, so this errors.
                "form-2-color": self.GREY,
            }
        )
        response = self.client.post(self.url, save)
        content = response.content.decode()

        assert response.status_code == 200
        assert response.headers.get("HX-Redirect") is None
        assert LabelCategory.objects.filter(name="Bestaand").count() == 1

        self.assertContains(response, "nldd-validation-item")
        self.assertContains(response, "invalid")

        # Surviving rows keep their values, with exactly three contiguous rows
        # and no phantom blank between the filled ones.
        self.assertContains(response, 'value="Nieuw1"')
        self.assertContains(response, 'name="form-TOTAL_FORMS"')
        self.assertContains(response, 'value="3"')
        assert content.count("data-category-row") == 3
        assert 'name="form-1-name" value=""' not in content

    def _name_field(self, content, index):
        tag = re.search(rf'<nldd-text-field[^>]*name="form-{index}-name"[^>]*>', content, re.DOTALL)
        assert tag is not None, f"no name field for row {index}"
        return tag.group(0)

    def _color_select(self, content, index):
        tag = re.search(rf'<select[^>]*name="form-{index}-color"[^>]*>', content, re.DOTALL)
        assert tag is not None, f"no color select for row {index}"
        # attrs.html spreads each attribute over several lines.
        return re.sub(r"\s*=\s*", "=", tag.group(0))

    def test_saved_row_fields_are_named_after_their_category(self):
        """The rows share one visible header, so a screen reader needs the
        category in each field's name to tell the rows apart."""
        LabelCategory.objects.create(name="Expertise", color=self.GREY)
        content = self.client.get(self.url).content.decode()

        assert 'accessible-label="Naam van categorie Expertise"' in self._name_field(content, 0)
        assert 'aria-label="Kleur van categorie Expertise"' in self._color_select(content, 0)
        assert 'accessible-label="Naam"' not in content
        assert 'aria-label="Kleur"' not in content

    def test_new_row_fields_are_named_as_new_category(self):
        """A row added with extra_row has no name yet, so it is called a new category."""
        existing = LabelCategory.objects.create(name="Expertise", color=self.GREY)
        data = self._management(total=1, initial=1)
        data.update(
            {"extra_row": "1", "form-0-id": str(existing.pk), "form-0-name": "Expertise", "form-0-color": self.GREY}
        )
        content = self.client.post(self.url, data).content.decode()

        assert 'accessible-label="Naam van categorie Expertise"' in self._name_field(content, 0)
        new_name = self._name_field(content, 1)
        assert 'accessible-label="Naam van nieuwe categorie"' in new_name
        assert "autofocus" in new_name
        assert 'aria-label="Kleur van nieuwe categorie"' in self._color_select(content, 1)

    def test_blank_name_keeps_the_saved_category_in_the_field_name(self):
        """After a rejected save the row is still named after the saved category,
        not after what was typed, and the error stays visible."""
        category = LabelCategory.objects.create(name="Expertise", color=self.GREY)
        data = self._management(total=1, initial=1)
        data.update({"form-0-id": str(category.pk), "form-0-name": "", "form-0-color": self.GREY})
        response = self.client.post(self.url, data)
        content = response.content.decode()

        assert response.headers.get("HX-Redirect") is None
        self.assertContains(response, "nldd-validation-item")
        assert 'accessible-label="Naam van categorie Expertise"' in self._name_field(content, 0)
        assert 'aria-label="Kleur van categorie Expertise"' in self._color_select(content, 0)

    def test_duplicate_name_keeps_the_row_names(self):
        """A new row that duplicates a saved name fails validation; both rows keep
        their own field names."""
        existing = LabelCategory.objects.create(name="Expertise", color=self.GREY)
        data = self._management(total=2, initial=1)
        data.update(
            {
                "form-0-id": str(existing.pk),
                "form-0-name": "Expertise",
                "form-0-color": self.GREY,
                "form-1-name": "Expertise",
                "form-1-color": self.GREY,
            }
        )
        response = self.client.post(self.url, data)
        content = response.content.decode()

        assert response.headers.get("HX-Redirect") is None
        self.assertContains(response, "nldd-validation-item")
        assert 'accessible-label="Naam van categorie Expertise"' in self._name_field(content, 0)
        assert 'accessible-label="Naam van nieuwe categorie"' in self._name_field(content, 1)
        assert 'aria-label="Kleur van nieuwe categorie"' in self._color_select(content, 1)

    def test_column_header_appears_once_above_the_rows(self):
        """One "Naam"/"Kleur" header heads the columns, on open and on every
        body re-render."""
        LabelCategory.objects.create(name="Expertise", color=self.GREY)
        LabelCategory.objects.create(name="Vaardigheden", color=self.GREY)
        opened = self.client.get(self.url).content.decode()
        data = self._management(total=0, initial=0)
        data["extra_row"] = "1"
        rerendered = self.client.post(self.url, data).content.decode()

        for label, content in (("opened", opened), ("extra_row", rerendered)):
            with self.subTest(response=label):
                assert content.count("data-category-header") == 1
                header = re.search(r"<nldd-list-item data-category-header>.*?</nldd-list-item>", content, re.DOTALL)
                assert header is not None
                assert '<nldd-text-cell width="full" text="Naam">' in header.group(0)
                assert '<nldd-text-cell width="112px" text="Kleur">' in header.group(0)
                assert content.index("data-category-header") < content.index("data-category-row")

    def test_only_the_user_admin_role_opens_the_sheet(self):
        """The sheet follows the label permissions, which only the
        Gebruikersbeheerder role carries."""
        setup_roles()
        for role, expected in ((ROLE_USER_ADMIN, 200), (ROLE_CONSULTANT, 403), (ROLE_BUSINESS_MANAGER, 403)):
            with self.subTest(role=role):
                user = User.objects.create_user(email=f"{role}@rijksoverheid.nl", first_name="R", last_name="Ol")
                user.groups.add(Group.objects.get(name=role))
                self.client.force_login(user)
                assert self.client.get(self.url).status_code == expected

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_without_user_admin_role_cannot_open_the_sheet(self):
        """Being Applicatiebeheerder alone does not grant the label permissions."""
        setup_roles()
        self.client.force_login(make_staff_user())
        assert self.client.get(self.url).status_code == 403
