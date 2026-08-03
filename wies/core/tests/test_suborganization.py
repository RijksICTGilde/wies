from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wies.core.errors import SuborganizationNotFoundError
from wies.core.forms import SuborganizationForm
from wies.core.models import Assignment, Colleague, Placement, Service, Skill, Suborganization
from wies.core.roles import setup_roles
from wies.core.services.suborganizations import get_suborganization_by_name
from wies.core.tests.inline_edit_helpers import post_inline_edit
from wies.core.views import PlacementListView, UserListView

User = get_user_model()


class SuborganizationModelTest(TestCase):
    def test_suborganization_name_unique(self):
        Suborganization.objects.create(name="Rijks ICT Gilde")
        with pytest.raises(IntegrityError), transaction.atomic():
            Suborganization.objects.create(name="Rijks ICT Gilde")

    def test_colleague_has_single_suborganization(self):
        suborganization = Suborganization.objects.create(name="Rijksconsultants")
        colleague = Colleague.objects.create(
            name="Kees", email="kees@rijksoverheid.nl", source="wies", suborganization=suborganization
        )
        assert colleague.suborganization == suborganization
        assert suborganization.colleagues.count() == 1

    def test_deleting_suborganization_nulls_colleague(self):
        suborganization = Suborganization.objects.create(name="RADIO")
        colleague = Colleague.objects.create(
            name="Ann", email="ann@rijksoverheid.nl", source="wies", suborganization=suborganization
        )
        suborganization.delete()
        colleague.refresh_from_db()
        assert colleague.suborganization is None


class GetSuborganizationByNameTest(TestCase):
    """The shared resolver used by CSV imports and OTYS sync: look up, never create."""

    def test_exact_match(self):
        suborg = Suborganization.objects.create(name="Rijks ICT Gilde")
        assert get_suborganization_by_name("Rijks ICT Gilde") == suborg

    def test_case_insensitive_match(self):
        suborg = Suborganization.objects.create(name="I-Interim Rijk")
        assert get_suborganization_by_name("i-interim rijk") == suborg

    def test_strips_surrounding_whitespace(self):
        suborg = Suborganization.objects.create(name="Rijksconsultants")
        assert get_suborganization_by_name("  Rijksconsultants  ") == suborg

    def test_unknown_name_raises(self):
        with pytest.raises(SuborganizationNotFoundError):
            get_suborganization_by_name("Onbekend Merk")

    def test_never_creates(self):
        with pytest.raises(SuborganizationNotFoundError):
            get_suborganization_by_name("Onbekend Merk")
        assert Suborganization.objects.count() == 0


class SuborganizationInlineEditPermissionTest(TestCase):
    """Suborganization keeps the same permission as labels: self-edit + Beheerder."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.suborg_a = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.suborg_b = Suborganization.objects.create(name="Rijksconsultants")

        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl", first_name="Owner")
        self.own_colleague = Colleague.objects.create(
            user=self.owner_user,
            name="Owner",
            email="owner@rijksoverheid.nl",
            source="wies",
            suborganization=self.suborg_a,
        )

        self.admin_user = User.objects.create_user(email="admin@rijksoverheid.nl", first_name="Admin")
        self.admin_user.groups.add(Group.objects.get(name="Beheerder"))

        self.other_user = User.objects.create_user(email="other@rijksoverheid.nl", first_name="Other")

    def _edit_url(self, colleague):
        return reverse("inline-edit", args=["colleague", colleague.public_id, "suborganization"])

    def test_colleague_can_edit_own_suborganization(self):
        self.client.force_login(self.owner_user)
        response = post_inline_edit(
            self.client, self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.public_id}
        )
        assert response.status_code == 200
        self.own_colleague.refresh_from_db()
        assert self.own_colleague.suborganization == self.suborg_b

    def test_beheerder_can_edit_suborganization_with_change_colleague_perm(self):
        # Grant the admin the standard change_colleague permission (the same
        # gate that governs editing any other colleague field inline).
        perm = Permission.objects.get(codename="change_colleague", content_type__app_label="core")
        self.admin_user.user_permissions.add(perm)
        self.client.force_login(self.admin_user)
        response = post_inline_edit(
            self.client, self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.public_id}
        )
        assert response.status_code == 200
        self.own_colleague.refresh_from_db()
        assert self.own_colleague.suborganization == self.suborg_b

    def test_unrelated_user_cannot_edit_others_suborganization(self):
        self.client.force_login(self.other_user)
        # inline_edit_view returns a permission-denied alert instead of saving.
        self.client.post(self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.public_id})
        self.own_colleague.refresh_from_db()
        assert self.own_colleague.suborganization == self.suborg_a


class SuborganizationPlacementFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth_user = User.objects.create_user(email="viewer@rijksoverheid.nl")
        self.suborg_rig = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.suborg_rc = Suborganization.objects.create(name="Rijksconsultants")
        self.suborg_radio = Suborganization.objects.create(name="RADIO")

        self.skill = Skill.objects.create(name="Python")
        self.assignment = Assignment.objects.create(
            name="A", source="wies", start_date=date(2025, 1, 1), end_date=date(2030, 1, 1)
        )
        self.service = Service.objects.create(assignment=self.assignment, skill=self.skill, source="wies")

        self.c_rig = Colleague.objects.create(
            name="Rig Person", email="rig@x.nl", source="wies", suborganization=self.suborg_rig
        )
        self.c_rc = Colleague.objects.create(
            name="Rc Person", email="rc@x.nl", source="wies", suborganization=self.suborg_rc
        )
        # A colleague with no merk, to prove the filter excludes NULLs.
        self.c_none = Colleague.objects.create(name="No Merk", email="none@x.nl", source="wies")
        Placement.objects.create(colleague=self.c_rig, service=self.service, source="wies")
        Placement.objects.create(colleague=self.c_rc, service=self.service, source="wies")
        Placement.objects.create(colleague=self.c_none, service=self.service, source="wies")

    def _merk_group(self, params=None):
        request = RequestFactory().get("/", params or {})
        request.user = self.auth_user
        view = PlacementListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        return next(g for g in context["filter_groups"] if g.get("name") == "merk")

    def _count_for(self, suborganization, params=None):
        group = self._merk_group(params)
        option = next(o for o in group["options"] if o["value"] == str(suborganization.public_id))
        return option["count"]

    def test_filter_placements_by_suborganization(self):
        self.client.force_login(self.auth_user)
        # The GET filter param stays "merk" (Dutch UI surface).
        response = self.client.get(reverse("home"), {"merk": self.suborg_rig.public_id})
        assert response.status_code == 200
        self.assertContains(response, "Rig Person")
        self.assertNotContains(response, "Rc Person")
        self.assertNotContains(response, "No Merk")

    def test_filter_placements_multiselect_is_or_within_group(self):
        """Selecting two merken returns colleagues in either (OR within group)."""
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("home"), {"merk": [self.suborg_rig.public_id, self.suborg_rc.public_id]})
        assert response.status_code == 200
        self.assertContains(response, "Rig Person")
        self.assertContains(response, "Rc Person")
        self.assertNotContains(response, "No Merk")

    def test_placement_merk_filter_group_counts(self):
        """The merk filter group reports the number of matching placements per option."""
        assert self._count_for(self.suborg_rig) == 1
        assert self._count_for(self.suborg_rc) == 1
        assert self._count_for(self.suborg_radio) == 0

    def test_placement_merk_counts_exclude_the_merk_filter_itself(self):
        """Counts within the merk group ignore an active merk selection, so the
        user can still see the size of the other (unselected) merken."""
        # Even though only 'Rijks ICT Gilde' is selected, the other merk keeps its count.
        assert self._count_for(self.suborg_rig, {"merk": self.suborg_rig.public_id}) == 1
        assert self._count_for(self.suborg_rc, {"merk": self.suborg_rig.public_id}) == 1

    def test_invalid_merk_param_is_ignored(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("home"), {"merk": "not-a-uuid"})
        assert response.status_code == 200
        # Unparseable filter is dropped, so nothing is filtered out.
        self.assertContains(response, "Rig Person")
        self.assertContains(response, "Rc Person")


class SuborganizationUserFilterTest(TestCase):
    """The merk filter on the user list (admin-users)."""

    def setUp(self):
        self.client = Client()
        self.auth_user = User.objects.create_user(email="viewer@rijksoverheid.nl", first_name="View", last_name="Er")
        self.auth_user.user_permissions.add(Permission.objects.get(codename="view_user"))

        self.suborg_rig = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.suborg_rc = Suborganization.objects.create(name="Rijksconsultants")
        self.suborg_radio = Suborganization.objects.create(name="RADIO")

        self.user_rig = User.objects.create_user(
            email="rig@rijksoverheid.nl", first_name="Rigbertha", last_name="Gildezel"
        )
        Colleague.objects.create(
            user=self.user_rig,
            name="Rigbertha Gildezel",
            email="rig@rijksoverheid.nl",
            source="wies",
            suborganization=self.suborg_rig,
        )
        self.user_rc = User.objects.create_user(
            email="rc@rijksoverheid.nl", first_name="Consultina", last_name="Rijkszwaan"
        )
        Colleague.objects.create(
            user=self.user_rc,
            name="Consultina Rijkszwaan",
            email="rc@rijksoverheid.nl",
            source="wies",
            suborganization=self.suborg_rc,
        )

    def _merk_group(self, params=None):
        request = RequestFactory().get("/", params or {})
        request.user = self.auth_user
        view = UserListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        return next(g for g in context["filter_groups"] if g.get("name") == "merk")

    def _count_for(self, suborganization, params=None):
        group = self._merk_group(params)
        option = next(o for o in group["options"] if o["value"] == str(suborganization.public_id))
        return option["count"]

    def test_filter_users_by_suborganization(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(reverse("admin-users"), {"merk": self.suborg_rig.public_id})
        assert response.status_code == 200
        self.assertContains(response, "Rigbertha")
        self.assertNotContains(response, "Consultina")

    def test_filter_users_multiselect_is_or_within_group(self):
        self.client.force_login(self.auth_user)
        response = self.client.get(
            reverse("admin-users"), {"merk": [self.suborg_rig.public_id, self.suborg_rc.public_id]}
        )
        assert response.status_code == 200
        self.assertContains(response, "Rigbertha")
        self.assertContains(response, "Consultina")

    def test_user_merk_filter_group_present_with_counts(self):
        group = self._merk_group()
        assert group["type"] == "select-multi"
        # Every suborganization is offered as an option, with a usage count.
        option_labels = {o["label"] for o in group["options"]}
        assert {"Rijks ICT Gilde", "Rijksconsultants", "RADIO"} <= option_labels
        assert self._count_for(self.suborg_rig) == 1
        assert self._count_for(self.suborg_rc) == 1
        assert self._count_for(self.suborg_radio) == 0


class SuborganizationAdminTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.admin_user = User.objects.create_user(email="beheer@rijksoverheid.nl")
        self.admin_user.groups.add(Group.objects.get(name="Beheerder"))
        self.plain_user = User.objects.create_user(email="plain@rijksoverheid.nl")

    def test_admin_requires_permission(self):
        self.client.force_login(self.plain_user)
        response = self.client.get(reverse("suborganization-admin"))
        assert response.status_code == 403

    def test_beheerder_can_view_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("suborganization-admin"))
        assert response.status_code == 200

    def test_beheerder_can_create_suborganization(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("suborganization-create"), {"name": "Nieuw Merk"})
        assert response.status_code == 200
        assert Suborganization.objects.filter(name="Nieuw Merk").exists()

    def test_create_duplicate_suborganization_rejected(self):
        Suborganization.objects.create(name="Bestaand")
        self.client.force_login(self.admin_user)
        self.client.post(reverse("suborganization-create"), {"name": "Bestaand"})
        assert Suborganization.objects.filter(name="Bestaand").count() == 1

    def test_beheerder_can_delete_suborganization(self):
        suborganization = Suborganization.objects.create(name="Weg")
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("suborganization-delete", args=[suborganization.public_id]))
        assert response.status_code == 200
        assert not Suborganization.objects.filter(id=suborganization.id).exists()

    def test_edit_get_renders_form_modal(self):
        suborganization = Suborganization.objects.create(name="Oud")
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("suborganization-edit", args=[suborganization.public_id]))
        assert response.status_code == 200
        self.assertContains(response, "Oud")

    def test_beheerder_can_edit_suborganization(self):
        suborganization = Suborganization.objects.create(name="Oud")
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("suborganization-edit", args=[suborganization.public_id]), {"name": "Nieuw"}
        )
        assert response.status_code == 200
        assert response["HX-Retarget"] == "#suborganization_list_container"
        assert response["HX-Trigger"] == "closeModal"
        suborganization.refresh_from_db()
        assert suborganization.name == "Nieuw"

    def test_edit_to_existing_name_rejected(self):
        Suborganization.objects.create(name="Bestaand")
        target = Suborganization.objects.create(name="Anders")
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("suborganization-edit", args=[target.public_id]), {"name": "Bestaand"})
        assert response.status_code == 200
        target.refresh_from_db()
        # The name is unchanged because the duplicate is rejected.
        assert target.name == "Anders"

    def test_edit_keeping_own_name_is_allowed(self):
        """Saving the edit form without changing the name must not trip the
        uniqueness check against the instance's own row."""
        suborganization = Suborganization.objects.create(name="Zelfde")
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("suborganization-edit", args=[suborganization.public_id]), {"name": "Zelfde"}
        )
        assert response.status_code == 200
        assert response.get("HX-Trigger") == "closeModal"
        suborganization.refresh_from_db()
        assert suborganization.name == "Zelfde"

    def test_delete_with_usage_get_shows_warning_count(self):
        suborganization = Suborganization.objects.create(name="Inuse")
        Colleague.objects.create(
            name="Gebruiker", email="gebruiker@rijksoverheid.nl", source="wies", suborganization=suborganization
        )
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("suborganization-delete", args=[suborganization.public_id]))
        assert response.status_code == 200
        # The warning names how many colleagues still use the merk.
        self.assertContains(response, "1 collega")

    def test_delete_nulls_colleague_via_view(self):
        suborganization = Suborganization.objects.create(name="Inuse")
        colleague = Colleague.objects.create(
            name="Gebruiker", email="gebruiker@rijksoverheid.nl", source="wies", suborganization=suborganization
        )
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("suborganization-delete", args=[suborganization.public_id]))
        assert response.status_code == 200
        colleague.refresh_from_db()
        assert colleague.suborganization_id is None

    def test_create_get_not_allowed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("suborganization-create"))
        assert response.status_code == 405

    def test_delete_get_renders_modal_not_405(self):
        suborganization = Suborganization.objects.create(name="Weg")
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("suborganization-delete", args=[suborganization.public_id]))
        assert response.status_code == 200


class SuborganizationAdminPermissionGranularityTest(TestCase):
    """Each endpoint is gated by its own permission, not just 'is Beheerder'."""

    def setUp(self):
        setup_roles()
        self.client = Client()
        self.suborg = Suborganization.objects.create(name="Bestaand")

    def _user_with(self, *codenames):
        user = User.objects.create_user(email=f"{'_'.join(codenames)}@rijksoverheid.nl")
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="core"))
        return user

    def test_view_only_user_cannot_create(self):
        self.client.force_login(self._user_with("view_suborganization"))
        response = self.client.post(reverse("suborganization-create"), {"name": "Nieuw"})
        assert response.status_code == 403
        assert not Suborganization.objects.filter(name="Nieuw").exists()

    def test_view_only_user_cannot_edit(self):
        self.client.force_login(self._user_with("view_suborganization"))
        response = self.client.get(reverse("suborganization-edit", args=[self.suborg.public_id]))
        assert response.status_code == 403

    def test_view_only_user_cannot_delete(self):
        self.client.force_login(self._user_with("view_suborganization"))
        response = self.client.post(reverse("suborganization-delete", args=[self.suborg.public_id]))
        assert response.status_code == 403
        assert Suborganization.objects.filter(id=self.suborg.id).exists()

    def test_add_permission_allows_create(self):
        self.client.force_login(self._user_with("add_suborganization"))
        response = self.client.post(reverse("suborganization-create"), {"name": "Nieuw"})
        assert response.status_code == 200
        assert Suborganization.objects.filter(name="Nieuw").exists()


class SuborganizationFormTest(TestCase):
    def test_duplicate_name_rejected(self):
        Suborganization.objects.create(name="Bestaand")
        form = SuborganizationForm(data={"name": "Bestaand"})
        assert not form.is_valid()
        assert "name" in form.errors

    def test_duplicate_name_is_case_insensitive(self):
        Suborganization.objects.create(name="Rijks ICT Gilde")
        form = SuborganizationForm(data={"name": "rijks ict gilde"})
        assert not form.is_valid()
        assert "name" in form.errors

    def test_edit_excludes_own_row_from_uniqueness_check(self):
        suborganization = Suborganization.objects.create(name="Rijks ICT Gilde")
        # Re-saving the same instance with the same name (even different case) is fine.
        form = SuborganizationForm(data={"name": "Rijks ICT Gilde"}, instance=suborganization)
        assert form.is_valid()

    def test_unique_name_accepted(self):
        Suborganization.objects.create(name="Bestaand")
        form = SuborganizationForm(data={"name": "Nieuw"})
        assert form.is_valid()
