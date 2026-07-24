"""Tests for the permission engine and the rules registered against it.

Covers the engine surface (verb composition, field vs whole-object
lookup) and the production rules in ``permissions.py``.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.editables import (
    AssignmentEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.permission_engine import Verb, has_permission
from wies.core.public_id import generate_public_id

User = get_user_model()


class _Setup(TestCase):
    """Common fixture: BM owner, placed consultant, unrelated user, assignment with a service."""

    def setUp(self):
        self.owner_user = User.objects.create_user(email="bm@x.nl", first_name="B", last_name="M")
        self.owner = Colleague.objects.create(user=self.owner_user, name="B M", email="bm@x.nl", source="wies")

        self.placed_user = User.objects.create_user(email="placed@x.nl", first_name="P", last_name="L")
        self.placed = Colleague.objects.create(user=self.placed_user, name="P L", email="placed@x.nl", source="wies")

        self.unrelated_user = User.objects.create_user(email="other@x.nl", first_name="O", last_name="T")

        self.superuser = User.objects.create_user(
            email="su@x.nl", first_name="S", last_name="U", is_superuser=True, is_staff=True
        )

        self.assignment = Assignment.objects.create(name="A", owner=self.owner, source="wies")
        self.skill = Skill.objects.create(name="Rol")
        self.service = Service.objects.create(
            description="Dienst", assignment=self.assignment, skill=self.skill, source="wies"
        )
        self.placement = Placement.objects.create(colleague=self.placed, service=self.service, source="wies")


class HasPermissionEngineTest(_Setup):
    def test_anonymous_user_denied(self):
        from django.contrib.auth.models import AnonymousUser  # noqa: PLC0415

        assert has_permission(Verb.UPDATE, self.assignment, AnonymousUser()) is False

    def test_superuser_gets_all_perms_via_django_model_backend(self):
        # The engine no longer short-circuits superusers; they pass because
        # rules consult user.has_perm(...) and AuthBackend (inheriting from
        # ModelBackend) grants superusers every permission.
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser) is True
        assert has_permission(Verb.UPDATE, self.placement, self.superuser) is True
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser, AssignmentEditables.extra_info) is True

    def test_field_rule_overrides_object_rule(self):
        # The placed consultant fails the whole-object update rule but
        # passes the field-level rule for `extra_info` (description).
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user) is False
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user, AssignmentEditables.extra_info) is True

    def test_verb_list_or_composes(self):
        # Owner passes UPDATE on assignment; not LIST-only test, but
        # demonstrates list normalisation.
        assert has_permission([Verb.UPDATE, Verb.DELETE], self.assignment, self.owner_user) is True
        # A verb the user can't do AND another they also can't do → False.
        assert has_permission([Verb.DELETE], self.assignment, self.placed_user) is False

    def test_verb_tuple_works_as_list(self):
        assert has_permission((Verb.UPDATE,), self.assignment, self.owner_user) is True


class AssignmentPermissionRulesTest(_Setup):
    def test_owner_can_update_whole_assignment(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.owner_user) is True

    def test_placed_consultant_cannot_update_whole_assignment(self):
        # This is the placement-bug fix — historically this was True.
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user) is False

    def test_unrelated_user_cannot_update(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.unrelated_user) is False

    def test_external_assignment_not_editable_by_owner(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.UPDATE, ext, self.owner_user) is False

    def test_change_assignment_perm_grants_update(self):
        # Granting the Django permission directly (e.g. via a Beheerder
        # role that holds it, or per-user grant) lets the user update.
        u = User.objects.create_user(email="hp@x.nl", first_name="H", last_name="P")
        u.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        # Refresh so the permissions cache is rebuilt.
        u = User.objects.get(pk=u.pk)
        assert has_permission(Verb.UPDATE, self.assignment, u) is True


@override_settings(STAFF_EMAILS=["staff@x.nl"])
class StaffMemberCanEditAssignmentTest(_Setup):
    """Users in ``STAFF_EMAILS`` can edit wies-sourced assignments and their
    chained Service/Placement records (issue #392). External-source
    assignments stay read-only."""

    def setUp(self):
        super().setUp()
        self.staff_user = User.objects.create_user(email="staff@x.nl", first_name="S", last_name="T")

    def test_staff_can_update_assignment(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.staff_user) is True

    def test_staff_can_delete_assignment(self):
        assert has_permission(Verb.DELETE, self.assignment, self.staff_user) is True

    def test_staff_cannot_delete_external_assignment(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.DELETE, ext, self.staff_user) is False

    def test_staff_can_update_service(self):
        assert has_permission(Verb.UPDATE, self.service, self.staff_user) is True

    def test_staff_can_update_placement(self):
        assert has_permission(Verb.UPDATE, self.placement, self.staff_user) is True

    def test_staff_cannot_update_external_assignment(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.UPDATE, ext, self.staff_user) is False

    def test_non_staff_unrelated_user_still_denied(self):
        # Sanity check that the override doesn't accidentally grant everyone.
        assert has_permission(Verb.UPDATE, self.assignment, self.unrelated_user) is False


class PlacementPermissionTest(_Setup):
    """A colleague placed on an assignment must not be able to update
    Placement records on the same assignment — only the assignment
    owner (or an admin holder of ``core.change_assignment``) can.

    The endpoint shape is ``POST /inline-edit/placement/<id>/colleague/``.
    """

    def test_placed_consultant_cannot_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.placed_user) is False

    def test_owner_can_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.owner_user) is True

    def test_placed_consultant_cannot_replace_colleague_via_endpoint(self):
        client = Client()
        client.force_login(self.placed_user)
        url = reverse("inline-edit", args=["placement", self.placement.public_id, "colleague"])
        # Try to replace the colleague — should be denied.
        new_colleague = Colleague.objects.create(name="Stolen", email="x@x.nl", source="wies")
        resp = client.post(url, {"colleague": new_colleague.id})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.placement.refresh_from_db()
        assert self.placement.colleague_id == self.placed.id


class InlineEditExistenceOracleTest(_Setup):
    """The generic inline-edit endpoint must not reveal whether an object
    exists to a viewer who may not touch it: 'not found' and 'not allowed'
    must be indistinguishable, so sequential PKs can't be walked as an oracle.

    ``update_placement`` is owner-only, and the placement is made *planned*
    (future start) so an unrelated consultant can neither edit nor see it.
    """

    def setUp(self):
        super().setUp()
        # _Setup.placement has no dates, so placement_visibility treats it as
        # active (publicly visible). Push its start into the future so it is
        # genuinely hidden from the unrelated viewer — the oracle test's premise.
        today = timezone.now().date()
        self.placement.specific_start_date = today + timedelta(days=30)
        self.placement.specific_end_date = today + timedelta(days=120)
        self.placement.period_source = Placement.PLACEMENT
        self.placement.save()

    def _get(self, public_id):
        return self.client.get(reverse("inline-edit", args=["placement", public_id, "period"]))

    def test_existing_forbidden_and_missing_are_indistinguishable(self):
        """An unrelated consultant cannot edit this placement (update_placement is
        owner-only) and cannot see it (it is planned). The response for the real,
        hidden placement must match the response for a non-existent public_id."""
        self.client.force_login(self.unrelated_user)
        missing_public_id = generate_public_id()

        forbidden = self._get(self.placement.public_id)
        missing = self._get(missing_public_id)

        assert forbidden.status_code == missing.status_code
        normalize = lambda resp, pid: resp.content.decode().replace(str(pid), "ID")  # noqa: E731
        assert normalize(forbidden, self.placement.public_id) == normalize(missing, missing_public_id)

    def test_forbidden_response_leaks_no_object_data(self):
        """The denial response must not carry the hidden colleague's name."""
        self.client.force_login(self.unrelated_user)

        response = self._get(self.placement.public_id)

        assert response.status_code == 200
        self.assertNotContains(response, "P L")


class ServiceDescriptionRuleTest(_Setup):
    def test_placed_on_service_can_update_description(self):
        assert has_permission(Verb.UPDATE, self.service, self.placed_user, ServiceEditables.description) is True

    def test_owner_can_update_service_description(self):
        assert has_permission(Verb.UPDATE, self.service, self.owner_user, ServiceEditables.description) is True


class UserEmailFieldRuleTest(TestCase):
    """Email is admin-only — even on the user's own profile.

    Demonstrates that field-level rules can be *stricter* than the
    whole-object rule.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="self@x.nl", first_name="S", last_name="E")
        self.admin = User.objects.create_user(email="adm@x.nl", first_name="A", last_name="D")
        self.admin.user_permissions.add(Permission.objects.get(codename="change_user"))
        self.admin = User.objects.get(pk=self.admin.pk)  # rebuild perm cache

    def test_self_can_update_first_name(self):
        # Whole-object rule: self-edit allowed.
        assert has_permission(Verb.UPDATE, self.user, self.user) is True

    def test_self_cannot_update_email(self):
        # Field-level rule: stricter override; admin-only.
        assert has_permission(Verb.UPDATE, self.user, self.user, UserEditables.email) is False

    def test_admin_can_update_email(self):
        assert has_permission(Verb.UPDATE, self.user, self.admin, UserEditables.email) is True


class UnknownTargetReturnsFalseTest(TestCase):
    """If no rule is registered for (verb, model[, field]), the engine
    returns False — fail-closed by default."""

    def test_no_rule_means_denied(self):
        u = User.objects.create_user(email="x@x.nl", first_name="X", last_name="X")
        # READ on Assignment isn't registered — should deny.
        a = Assignment.objects.create(name="A", source="wies")
        assert has_permission(Verb.READ, a, u) is False
