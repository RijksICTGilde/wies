from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Placement, Service, Skill, Suborganization
from wies.core.roles import setup_roles
from wies.core.tests.inline_edit_helpers import post_inline_edit

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
        return reverse("inline-edit", args=["colleague", colleague.id, "suborganization"])

    def test_colleague_can_edit_own_suborganization(self):
        self.client.force_login(self.owner_user)
        response = post_inline_edit(
            self.client, self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.id}
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
            self.client, self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.id}
        )
        assert response.status_code == 200
        self.own_colleague.refresh_from_db()
        assert self.own_colleague.suborganization == self.suborg_b

    def test_unrelated_user_cannot_edit_others_suborganization(self):
        self.client.force_login(self.other_user)
        # inline_edit_view returns a permission-denied alert instead of saving.
        self.client.post(self._edit_url(self.own_colleague), {"suborganization": self.suborg_b.id})
        self.own_colleague.refresh_from_db()
        assert self.own_colleague.suborganization == self.suborg_a


class SuborganizationFilterTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth_user = User.objects.create_user(email="viewer@rijksoverheid.nl")
        self.suborg_rig = Suborganization.objects.create(name="Rijks ICT Gilde")
        self.suborg_rc = Suborganization.objects.create(name="Rijksconsultants")

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
        Placement.objects.create(colleague=self.c_rig, service=self.service, source="wies")
        Placement.objects.create(colleague=self.c_rc, service=self.service, source="wies")

    def test_filter_placements_by_suborganization(self):
        self.client.force_login(self.auth_user)
        # The GET filter param stays "merk" (Dutch UI surface).
        response = self.client.get(reverse("home"), {"merk": self.suborg_rig.id})
        assert response.status_code == 200
        self.assertContains(response, "Rig Person")
        self.assertNotContains(response, "Rc Person")


class SuborganizationAdminTest(TestCase):
    def setUp(self):
        setup_roles()
        self.client = Client()
        self.admin_user = User.objects.create_user(email="beheer@rijksoverheid.nl")
        self.admin_user.groups.add(Group.objects.get(name="Beheerder"))
        self.plain_user = User.objects.create_user(email="plain@rijksoverheid.nl")

    def test_admin_requires_permission(self):
        self.client.force_login(self.plain_user)
        response = self.client.get(reverse("merk-admin"))
        assert response.status_code == 403

    def test_beheerder_can_view_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("merk-admin"))
        assert response.status_code == 200

    def test_beheerder_can_create_suborganization(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("merk-create"), {"name": "Nieuw Merk"})
        assert response.status_code == 200
        assert Suborganization.objects.filter(name="Nieuw Merk").exists()

    def test_create_duplicate_suborganization_rejected(self):
        Suborganization.objects.create(name="Bestaand")
        self.client.force_login(self.admin_user)
        self.client.post(reverse("merk-create"), {"name": "Bestaand"})
        assert Suborganization.objects.filter(name="Bestaand").count() == 1

    def test_beheerder_can_delete_suborganization(self):
        suborganization = Suborganization.objects.create(name="Weg")
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse("merk-delete", args=[suborganization.id]))
        assert response.status_code == 200
        assert not Suborganization.objects.filter(id=suborganization.id).exists()
