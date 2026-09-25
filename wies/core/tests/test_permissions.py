"""Tests for the permission engine and the rules registered against it.

Covers the engine surface (verb composition, field vs whole-object
lookup) and the production rules in ``permissions.py``.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from wies.core.editables import (
    AssignmentEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.permission_engine import (
    ANY,
    OWN,
    PLACED,
    SCOPES,
    WIES_SOURCED,
    Grant,
    Role,
    Verb,
    all_of,
    has_permission,
    registered_rules,
    rule,
)
from wies.core.roles import ROLE_BDM, ROLE_OFFICE_ASSISTANT, ROLE_STAFF

from .inline_edit_helpers import post_inline_edit
from .role_helpers import grant_bdm, grant_consultant

User = get_user_model()


class _Setup(TestCase):
    """Common fixture: BDM owner, placed consultant, unrelated user, assignment with a service."""

    def setUp(self):
        # The owner is a BDM: ownership only grants edit rights combined with
        # the BDM role (see ``update_assignment`` in permissions.py).
        self.owner_user = grant_bdm(User.objects.create_user(email="bm@x.nl", first_name="B", last_name="M"))
        self.owner = Colleague.objects.create(user=self.owner_user, name="B M", email="bm@x.nl", source="wies")

        self.placed_user = grant_consultant(
            User.objects.create_user(email="placed@x.nl", first_name="P", last_name="L")
        )
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

    def test_superuser_flag_carries_no_rights(self):
        # Every rule names a role, and the superuser flag is not one: ModelBackend
        # turns it into every Django permission, which no rule asks for.
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser) is False
        assert has_permission(Verb.UPDATE, self.placement, self.superuser) is False
        assert has_permission(Verb.UPDATE, self.assignment, self.superuser, AssignmentEditables.extra_info) is False
        assert has_permission(Verb.UPDATE, self.unrelated_user, self.superuser) is False

    def test_field_rule_overrides_object_rule(self):
        # The placed consultant fails the whole-object update rule but
        # passes the field-level rule for `extra_info` (description).
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user) is False
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user, AssignmentEditables.extra_info) is True

    def test_verb_list_or_composes(self):
        # The BDM owner passes UPDATE on assignment; not LIST-only test, but
        # demonstrates list normalisation.
        assert has_permission([Verb.UPDATE, Verb.DELETE], self.assignment, self.owner_user) is True
        # A verb the user can't do AND another they also can't do → False.
        assert has_permission([Verb.DELETE], self.assignment, self.placed_user) is False

    def test_verb_tuple_works_as_list(self):
        assert has_permission((Verb.UPDATE,), self.assignment, self.owner_user) is True

    @override_settings(STAFF_EMAILS=["other@x.nl"])
    def test_the_staff_role_is_held_by_the_address_list_not_a_group(self):
        """No rule names ``ROLE_STAFF`` today, so only this test holds the promise
        in ``Role``: a rule may name it like any other role, though there is no group
        of that name to ask."""
        holder = Role(ROLE_STAFF)

        assert Group.objects.filter(name=ROLE_STAFF).exists() is False
        assert holder.qualifies(self.unrelated_user, self.assignment, Verb.UPDATE) is True
        assert holder.qualifies(self.owner_user, self.assignment, Verb.UPDATE) is False


class AssignmentPermissionRulesTest(_Setup):
    def test_bdm_owner_can_update_whole_assignment(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.owner_user) is True

    def test_non_bdm_owner_cannot_update_or_delete(self):
        """Ownership alone grants nothing: an owner outside the BDM group is
        treated as any other viewer (see ``update_assignment``)."""
        plain_user = User.objects.create_user(email="plain@x.nl", first_name="P", last_name="O")
        plain = Colleague.objects.create(user=plain_user, name="P O", email="plain@x.nl", source="wies")
        owned = Assignment.objects.create(name="Plain", owner=plain, source="wies")

        assert has_permission(Verb.UPDATE, owned, plain_user) is False
        assert has_permission(Verb.DELETE, owned, plain_user) is False

    def test_placed_consultant_cannot_update_whole_assignment(self):
        # This is the placement-bug fix — historically this was True.
        assert has_permission(Verb.UPDATE, self.assignment, self.placed_user) is False

    def test_unrelated_user_cannot_update(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.unrelated_user) is False

    def test_external_assignment_not_editable_by_owner(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.UPDATE, ext, self.owner_user) is False

    def test_change_assignment_perm_does_not_grant_update(self):
        # Assignment rights come from the BDM role only; a
        # direct Django permission grant opens nothing.
        u = User.objects.create_user(email="hp@x.nl", first_name="H", last_name="P")
        u.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        # Refresh so the permissions cache is rebuilt.
        u = User.objects.get(pk=u.pk)
        assert has_permission(Verb.UPDATE, self.assignment, u) is False


class BdmCanEditAnyAssignmentTest(_Setup):
    """A BDM can edit and delete wies-sourced assignments and their
    chained Service/Placement records (issues #392, #313). External-source
    assignments stay read-only."""

    def setUp(self):
        super().setUp()
        self.admin_user = grant_bdm(User.objects.create_user(email="admin@x.nl", first_name="O", last_name="B"))

    def test_a_bdm_can_update_assignment(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.admin_user) is True

    def test_a_bdm_can_delete_assignment(self):
        assert has_permission(Verb.DELETE, self.assignment, self.admin_user) is True

    def test_a_bdm_cannot_delete_external_assignment(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.DELETE, ext, self.admin_user) is False

    def test_a_bdm_can_update_service(self):
        assert has_permission(Verb.UPDATE, self.service, self.admin_user) is True

    def test_a_bdm_can_update_placement(self):
        assert has_permission(Verb.UPDATE, self.placement, self.admin_user) is True

    def test_a_bdm_can_update_field_level_rules(self):
        a, s = self.assignment, self.service
        assert has_permission(Verb.UPDATE, a, self.admin_user, field=AssignmentEditables.name) is True
        assert has_permission(Verb.UPDATE, a, self.admin_user, field=AssignmentEditables.extra_info) is True
        assert has_permission(Verb.UPDATE, s, self.admin_user, field=ServiceEditables.description) is True

    def test_a_bdm_cannot_update_external_assignment(self):
        ext = Assignment.objects.create(name="X", owner=self.owner, source="otys_iir")
        assert has_permission(Verb.UPDATE, ext, self.admin_user) is False

    def test_unrelated_user_still_denied(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.unrelated_user) is False


class ExternalOpdrachtIsReadOnlyDownTheChainTest(_Setup):
    """A dienst and a plaatsing are as read-only as the opdracht they hang under,
    because each rule states ``WIES_SOURCED`` for itself.

    The BDM role is the widest audience these rules name, so an opdracht managed
    elsewhere shows here first if one of them stopped asking.
    """

    def setUp(self):
        super().setUp()
        self.admin_user = grant_bdm(User.objects.create_user(email="extern@x.nl", first_name="O", last_name="B"))

    def _targets(self):
        """One entry per UPDATE rule that requires ``WIES_SOURCED``, re-read from the
        database so no answer comes from a relation cached before the source changed."""
        assignment = Assignment.objects.get(pk=self.assignment.pk)
        service = Service.objects.get(pk=self.service.pk)
        placement = Placement.objects.get(pk=self.placement.pk)
        return [
            ("Opdracht bewerken", assignment, None),
            ("Dienst bewerken", service, None),
            ("Teamlid verplaatsen", placement, None),
            ("Naam van een opdracht bewerken", assignment, AssignmentEditables.name),
            ("Extra informatie bewerken", assignment, AssignmentEditables.extra_info),
            ("Dienstomschrijving bewerken", service, ServiceEditables.description),
        ]

    def test_an_externally_managed_opdracht_refuses_every_rule_under_it(self):
        Assignment.objects.filter(pk=self.assignment.pk).update(source="otys_iir")

        for label, obj, field in self._targets():
            with self.subTest(rule=label):
                assert has_permission(Verb.UPDATE, obj, self.admin_user, field) is False

    def test_the_same_rules_all_answer_yes_while_the_opdracht_comes_from_wies(self):
        """Otherwise the refusals above could be the BDM role falling short rather
        than the source of the opdracht."""
        for label, obj, field in self._targets():
            with self.subTest(rule=label):
                assert has_permission(Verb.UPDATE, obj, self.admin_user, field) is True

    def test_every_rule_that_requires_the_source_is_watched_somewhere(self):
        """The two tests above reach exactly as far as ``_targets``, which is written
        out by hand: a rule that starts requiring ``WIES_SOURCED`` would be read-only
        in production and unwatched here."""
        # ``_targets`` only asks UPDATE; the DELETE rule is watched by
        # ``BdmCanEditAnyAssignmentTest::test_a_bdm_cannot_delete_external_assignment``.
        watched = {label for label, _obj, _field in self._targets()} | {"Opdracht verwijderen"}

        assert watched == {rule.label for rule in registered_rules().values() if WIES_SOURCED in rule.requires}


class TheRoleNotOwnershipReachesTheDienstAndPlaatsingTest(_Setup):
    """The BDM role carries every wies-sourced opdracht, so a BDM reaches the
    diensten and plaatsingen of one they do not own; without the role nobody does."""

    def setUp(self):
        super().setUp()
        stranger = grant_bdm(User.objects.create_user(email="bm2@x.nl", first_name="B", last_name="2"))
        Colleague.objects.create(user=stranger, name="B 2", email="bm2@x.nl", source="wies")
        self.other_bdm_user = User.objects.get(pk=stranger.pk)

    def test_the_owning_bdm_reaches_the_dienst(self):
        assert has_permission(Verb.UPDATE, self.service, self.owner_user) is True

    def test_a_bdm_who_does_not_own_the_opdracht_reaches_both(self):
        for label, obj in (("Dienst bewerken", self.service), ("Teamlid verplaatsen", self.placement)):
            with self.subTest(rule=label):
                assert has_permission(Verb.UPDATE, obj, self.other_bdm_user) is True

    def test_without_the_role_neither_is_reached(self):
        for label, obj in (("Dienst bewerken", self.service), ("Teamlid verplaatsen", self.placement)):
            with self.subTest(rule=label):
                assert has_permission(Verb.UPDATE, obj, self.unrelated_user) is False


@override_settings(STAFF_EMAILS=["staff@x.nl"])
class StaffMemberHasNoAssignmentRightsTest(_Setup):
    """Application administration (``STAFF_EMAILS``) carries no functional rights:
    without the BDM role a staff member may not edit or delete an assignment."""

    def setUp(self):
        super().setUp()
        self.staff_user = User.objects.create_user(email="staff@x.nl", first_name="S", last_name="T")

    def test_staff_cannot_update_assignment(self):
        assert has_permission(Verb.UPDATE, self.assignment, self.staff_user) is False

    def test_staff_cannot_delete_assignment(self):
        assert has_permission(Verb.DELETE, self.assignment, self.staff_user) is False

    def test_staff_cannot_update_service_or_placement(self):
        assert has_permission(Verb.UPDATE, self.service, self.staff_user) is False
        assert has_permission(Verb.UPDATE, self.placement, self.staff_user) is False

    def test_staff_with_the_bdm_role_can_update(self):
        grant_bdm(self.staff_user)
        assert has_permission(Verb.UPDATE, self.assignment, self.staff_user) is True


class PlacementPermissionTest(_Setup):
    """A colleague placed on an assignment must not be able to update
    Placement records on the same assignment — only the assignment's
    a BDM can.

    The endpoint shape is ``POST /inline-edit/placement/<id>/colleague/``.
    """

    def test_placed_consultant_cannot_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.placed_user) is False

    def test_bdm_owner_can_update_placement_via_engine(self):
        assert has_permission(Verb.UPDATE, self.placement, self.owner_user) is True

    def test_placed_consultant_cannot_replace_colleague_via_endpoint(self):
        client = Client()
        client.force_login(self.placed_user)
        url = reverse("inline-edit", args=["placement", self.placement.public_id, "colleague"])
        # Try to replace the colleague — should be denied.
        new_colleague = Colleague.objects.create(name="Stolen", email="x@x.nl", source="wies")
        resp = client.post(url, {"colleague": new_colleague.public_id})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.placement.refresh_from_db()
        assert self.placement.colleague_id == self.placed.id


class InlineEditExistenceOracleTest(_Setup):
    """The generic inline-edit endpoint must not reveal whether an object
    exists to a viewer who may not touch it: 'not found' and 'not allowed'
    must be indistinguishable, so sequential PKs can't be walked as an oracle.

    ``update_placement`` is BDM-owner-only, and the placement is made *planned*
    (future start) so an unrelated consultant can neither edit nor see it.
    """

    def setUp(self):
        super().setUp()
        # _Setup.placement has no dates, so visibility_rules treats it as
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
        BDM-owner-only) and cannot see it (it is planned). The response for the real,
        hidden placement must match the response for a non-existent public_id."""
        self.client.force_login(self.unrelated_user)
        missing_public_id = uuid.uuid4()

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

    def test_bdm_owner_can_update_service_description(self):
        assert has_permission(Verb.UPDATE, self.service, self.owner_user, ServiceEditables.description) is True


class PlacedWithoutTheConsultantRoleTest(_Setup):
    """A colleague placed on the opdracht in another role reaches its text
    fields through no other door."""

    def setUp(self):
        super().setUp()
        # Office assistent: a role with no rights on an opdracht at all, so the
        # placement is the only door left to try.
        self.placed_other_user = User.objects.create_user(email="placed-other@x.nl", first_name="P", last_name="B")
        self.placed_other_user.groups.add(Group.objects.get_or_create(name=ROLE_OFFICE_ASSISTANT)[0])
        placed_other = Colleague.objects.create(
            user=self.placed_other_user, name="P B", email="placed-other@x.nl", source="wies"
        )
        # Placed on the same dienst as the consultant, and not the owner of it.
        Placement.objects.create(colleague=placed_other, service=self.service, source="wies")

    def test_a_placement_in_another_role_reaches_no_opdracht_text_field(self):
        for editable in (AssignmentEditables.name, AssignmentEditables.extra_info):
            with self.subTest(field=editable.name):
                assert has_permission(Verb.UPDATE, self.assignment, self.placed_other_user, editable) is False

    def test_a_placement_in_another_role_reaches_no_dienstomschrijving(self):
        assert has_permission(Verb.UPDATE, self.service, self.placed_other_user, ServiceEditables.description) is False


class UserEmailFieldRuleTest(TestCase):
    """The inline route to an e-mail address is closed to everyone.

    Demonstrates that field-level rules can be *stricter* than the whole-object
    rule: the address is changed on the user form, which is where
    ``may_change_email`` can see the new one.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="self@x.nl", first_name="S", last_name="E")
        self.office_assistant = User.objects.create_user(email="adm@x.nl", first_name="A", last_name="D")
        group, _created = Group.objects.get_or_create(name=ROLE_OFFICE_ASSISTANT)
        self.office_assistant.groups.add(group)
        self.staff = User.objects.create_user(email="app@x.nl", first_name="A", last_name="A")

    def test_self_can_update_first_name(self):
        # Whole-object rule: self-edit allowed.
        assert has_permission(Verb.UPDATE, self.user, self.user) is True

    def test_self_cannot_update_email(self):
        # Field-level rule: stricter than the whole-object rule that just allowed it.
        assert has_permission(Verb.UPDATE, self.user, self.user, UserEditables.email) is False

    def test_office_assistant_can_update_the_whole_user(self):
        """The other half of the override: the role ``rule(UPDATE, User, ...)`` names
        really does reach this account, so ``test_office_assistant_cannot_update_email_inline``
        is the field rule refusing and not an editor falling short."""
        assert has_permission(Verb.UPDATE, self.user, self.office_assistant) is True

    def test_office_assistant_cannot_update_email_inline(self):
        assert has_permission(Verb.UPDATE, self.user, self.office_assistant, UserEditables.email) is False

    @override_settings(STAFF_EMAILS=["app@x.nl"])
    def test_application_administration_cannot_either(self):
        """Application administration is the one authority that may move a
        ``STAFF_EMAILS`` address at all, so if any route stayed open it would be
        this one."""
        assert has_permission(Verb.UPDATE, self.user, self.staff, UserEditables.email) is False


class UnknownTargetReturnsFalseTest(TestCase):
    """If no rule is registered for (verb, model[, field]), the engine
    returns False — fail-closed by default."""

    def test_no_rule_means_denied(self):
        u = User.objects.create_user(email="x@x.nl", first_name="X", last_name="X")
        # READ on Assignment isn't registered — should deny.
        a = Assignment.objects.create(name="A", source="wies")
        assert has_permission(Verb.READ, a, u) is False


class SaveEditSpecsHasNoInternalGateTest(_Setup):
    """``save_edit_specs`` trusts its caller: it performs NO permission check.

    Authorization for every save path is upstream — ``inline_edit_view`` checks
    before saving, and the child-sheet views build a permission-filtered spec
    list via ``assignment_edit_specs`` / ``placement_edit_specs``. This test pins
    that contract down so it stays visible: it drives ``save_edit_specs`` directly
    with a spec the placed consultant may NOT update and shows the write goes
    through regardless — proving the gate cannot live here and any new caller must
    pre-filter its specs (or it silently bypasses field-level permissions).
    """

    def test_save_edit_specs_writes_without_checking_permission(self):
        from django.test import RequestFactory  # noqa: PLC0415

        from wies.core.editables import ServiceEditables  # noqa: PLC0415
        from wies.core.services.inline_edit_save import save_edit_specs  # noqa: PLC0415

        # Sanity: the placed consultant genuinely cannot UPDATE the description of
        # a service they are not placed on... but save_edit_specs does not consult
        # that rule.
        other_service = Service.objects.create(
            description="Andermans rol", assignment=self.assignment, skill=self.skill, source="wies"
        )
        assert has_permission(Verb.UPDATE, other_service, self.placed_user, ServiceEditables.description) is False

        request = RequestFactory().post("/")
        request.user = self.placed_user
        save_edit_specs(
            request,
            [(ServiceEditables, ServiceEditables.description, other_service)],
            {"description": "Bypassed"},
        )

        other_service.refresh_from_db()
        # The write went through: the check MUST be upstream, never here.
        assert other_service.description == "Bypassed"


class AssignmentMemberSheetPermissionTest(_Setup):
    """The team-member child sheets (add/edit/delete) gate on the assignment's
    ``services`` UPDATE rule — an unrelated user gets a 403 and no mutation.

    ``placement_edit_view`` and the single-field ``assignment_edit_view`` already
    have 403 tests; these cover the two remaining mutating child-sheet endpoints.
    """

    def test_member_edit_forbidden_for_unrelated_user(self):
        client = Client()
        client.force_login(self.unrelated_user)
        url = reverse("assignment-member-edit", args=[self.assignment.public_id])

        resp = client.post(url, {"skill": self.skill.public_id, "is_filled": "aanvraag"})

        assert resp.status_code == 403
        # No new service row was created behind the forbidden response.
        assert self.assignment.services.count() == 1

    def test_member_delete_forbidden_for_unrelated_user(self):
        client = Client()
        client.force_login(self.unrelated_user)
        url = reverse(
            "assignment-member-delete",
            args=[self.assignment.public_id, self.service.public_id],
        )

        resp = client.post(url, {"terug_url": f"/?opdracht={self.assignment.public_id}"})

        assert resp.status_code == 403
        assert Service.objects.filter(pk=self.service.pk).exists()

    def test_member_edit_allowed_for_bdm_owner(self):
        # Guards against the 403 tests passing for the wrong reason (e.g. the
        # endpoint 403-ing everyone).
        owner_client = Client()
        owner_client.force_login(self.owner_user)
        url = reverse("assignment-member-edit", args=[self.assignment.public_id])

        resp = owner_client.post(url, {"skill": self.skill.public_id, "is_filled": "aanvraag"})

        # 204 on success, or a 200 re-render on a form error — but never 403.
        assert resp.status_code != 403


class AssignmentAdminCanEditServiceAndPlacementOverHttpTest(_Setup):
    """A BDM can edit Service and Placement records end-to-end over the
    inline-edit HTTP endpoint, not just at the engine level.

    The engine-level equivalents live in ``BdmCanEditAnyAssignmentTest``;
    these drive the real ``inline_edit_view`` request so the whole stack (lookup,
    ``_permission_denied``, save) is exercised for a BDM editor.
    """

    def setUp(self):
        super().setUp()
        self.admin_user = grant_bdm(User.objects.create_user(email="admin@x.nl", first_name="O", last_name="B"))
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_a_bdm_can_edit_service_description_inline(self):
        url = reverse("inline-edit", args=["service", self.service.public_id, "description"])

        resp = post_inline_edit(self.client, url, {"description": "Bdm-bewerking"})

        assert resp.status_code == 200
        self.assertNotContains(resp, "geen rechten")
        self.service.refresh_from_db()
        assert self.service.description == "Bdm-bewerking"

    def test_a_bdm_can_edit_placement_period_inline(self):
        # An unrelated user is refused this exact edit (see
        # InlineEditExistenceOracleTest); a BDM must be able to save it.
        url = reverse("inline-edit", args=["placement", self.placement.public_id, "period"])

        resp = post_inline_edit(
            self.client,
            url,
            {
                "period_source": Placement.PLACEMENT,
                "specific_start_date": "2026-03-01",
                "specific_end_date": "2026-06-30",
            },
        )

        assert resp.status_code == 200
        self.assertNotContains(resp, "geen rechten")
        self.placement.refresh_from_db()
        assert str(self.placement.specific_start_date) == "2026-03-01"
        assert str(self.placement.specific_end_date) == "2026-06-30"


class ScopeVocabularyTest(_Setup):
    """The relations a rule can name, asked directly.

    ``OWN`` is named by no rule today: a BDM carries every wies-sourced opdracht,
    so nothing narrows to the one they own. It stays because merk scoping (#526)
    combines with it, and it is measured here so it cannot rot unnoticed.
    """

    def test_own_is_the_business_manager_of_the_opdracht(self):
        for obj in (self.assignment, self.service, self.placement):
            with self.subTest(model=type(obj).__name__):
                assert OWN.predicate(self.owner_user, obj, None) is True
                assert OWN.predicate(self.placed_user, obj, None) is False

    def test_any_asks_for_no_relation_at_all(self):
        assert ANY.parts == frozenset()
        assert ANY.predicate(self.unrelated_user, self.assignment, None) is True


class AllOfScopeTest(_Setup):
    """``all_of`` builds the relation that is two relations at once, which is
    what merk scoping (#526) needs: "eigen, en binnen je merk"."""

    def setUp(self):
        super().setUp()
        self.own_and_placed = all_of(OWN, PLACED)
        # The owner is placed on their own opdracht; the consultant only placed.
        Placement.objects.create(colleague=self.owner, service=self.service, source="wies")

    def test_it_holds_only_when_every_part_holds(self):
        assert self.own_and_placed.predicate(self.owner_user, self.assignment, None) is True
        assert self.own_and_placed.predicate(self.placed_user, self.assignment, None) is False
        assert self.own_and_placed.predicate(self.unrelated_user, self.assignment, None) is False

    def test_it_carries_the_parts_of_both(self):
        assert self.own_and_placed.parts == {"own", "placed"}

    def test_its_label_names_both_relations(self):
        assert self.own_and_placed.label == f"{OWN.label}, {PLACED.label}"

    def test_a_part_covers_the_combination_but_not_the_other_way_round(self):
        """What ``_rule_cell`` reads: a grant on "eigen" also answers the row for
        "eigen, waarop je geplaatst bent", and a grant that needs both does not
        answer the row that needs only one."""
        assert OWN.parts <= self.own_and_placed.parts
        assert not self.own_and_placed.parts <= OWN.parts
        assert ANY.parts <= self.own_and_placed.parts


class RuleRegistrationTest(SimpleTestCase):
    """What ``rule()`` refuses, and why it refuses it there.

    The role page lays its rows out by walking ``SCOPES``, so a relation that is
    not in that tuple would be enforced while printing no row at all. Registration
    is the last moment where the mistake is still visible, since it happens at
    import and takes the whole app down with it.
    """

    def test_a_combination_that_is_not_a_named_scope_is_refused(self):
        """The trap ``all_of`` warns about: built inline it equals no constant, so
        ``in SCOPES`` says no even when the very same call appears in ``SCOPES``.

        The target is not a model on purpose: a grant that got through would be
        registered under a key nothing looks up rather than replace a real rule.
        """

        class _Target:
            pass

        with pytest.raises(ValueError, match="not in SCOPES"):
            rule(Verb.UPDATE, _Target, label="Iets bewerken", grants=[Grant(Role(ROLE_BDM), all_of(OWN, PLACED))])

        assert (Verb.UPDATE, _Target, None) not in registered_rules()

    def test_every_relation_the_rules_name_is_in_the_vocabulary(self):
        """The other half, and the invariant the guard exists for: the production
        rules pass it, so this is not a guard that refuses everything."""
        for key, registered in registered_rules().items():
            for grant in registered.grants:
                with self.subTest(rule=registered.label, scope=grant.scope, key=key):
                    assert grant.scope in SCOPES
