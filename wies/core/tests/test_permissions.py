"""Tests for the permission engine and the rules registered against it.

Covers the engine surface (verb composition, superuser short-circuit,
field vs whole-object lookup) and the production rules in
``permission_rules.py`` — including the placement-bug regression from
PR #311.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.editables import (
    AssignmentEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.permissions import Verb, has_permission

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

    def test_superuser_short_circuits_every_check(self):
        # Even rules that would deny return True for superusers.
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser) is True
        assert has_permission(Verb.UPDATE, self.placement, self.superuser) is True
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser, AssignmentEditables.extra_info) is True
        assert has_permission(Verb.LIST, Assignment, self.superuser) is True

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


class PlacementPermissionBugRegressionTest(_Setup):
    """Regression for PR #311: a colleague placed on an assignment must
    NOT be able to update Placement records on the same assignment.

    Replays the exploit shape from the review: ``POST
    /inline-edit/placement/<id>/colleague/`` as the placed user.
    """

    def test_placed_consultant_cannot_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.placed_user) is False

    def test_owner_can_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.owner_user) is True

    def test_placed_consultant_cannot_replace_colleague_via_endpoint(self):
        client = Client()
        client.force_login(self.placed_user)
        url = reverse("inline-edit", args=["placement", self.placement.id, "colleague"])
        # Try to replace the colleague — should be denied.
        new_colleague = Colleague.objects.create(name="Stolen", email="x@x.nl", source="wies")
        resp = client.post(url, {"colleague": new_colleague.id})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.placement.refresh_from_db()
        assert self.placement.colleague_id == self.placed.id


class ServiceDescriptionRuleTest(_Setup):
    def test_placed_on_service_can_update_description(self):
        assert has_permission(Verb.UPDATE, self.service, self.placed_user, ServiceEditables.description) is True

    def test_owner_cannot_update_service_description_inline(self):
        # BM uses the team editor for service descriptions — the
        # field-level rule excludes them on purpose.
        assert has_permission(Verb.UPDATE, self.service, self.owner_user, ServiceEditables.description) is False


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
