"""Tests for the inline_edit infrastructure.

Creates on-the-fly EditableSets bound to real models (Assignment,
Colleague), hits the generic view, and asserts the response shape +
persistence behaviour. Registrations are cleaned up in tearDown to
avoid leaking into unrelated tests.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.editables import REGISTRY
from wies.core.editables.assignment import AssignmentEditables
from wies.core.editables.placement import PlacementEditables
from wies.core.editables.service import ServiceEditables
from wies.core.fields import OrganizationsField
from wies.core.forms import AssignmentCreateForm
from wies.core.inline_edit.base import (
    Editable,
    EditableGroup,
    EditableSet,
)
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.permission_engine import Verb, registered_rules, rule
from wies.core.widgets import OrgPickerWidget

User = get_user_model()


def _register(cls: type[EditableSet]) -> type[EditableSet]:
    """Register a dynamically-created EditableSet in REGISTRY under
    its model label. Auto-registration via __init_subclass__ is gone
    — tests that build EditableSets on the fly must opt in explicitly.
    """
    REGISTRY[cls.model._meta.model_name] = cls  # noqa: SLF001 — _meta is Django's canonical API
    return cls


def _make_set(cls_name: str, /, model, **attrs):
    """Build an EditableSet subclass with `class Meta: model = ...`.

    Use in tests that need ad-hoc EditableSets:

        cls = _make_set("MyEditables", Assignment, name=Editable())

    ``cls_name`` is positional-only so callers can pass an Editable
    attribute also named ``name`` without conflict.
    """
    meta_cls = type("Meta", (), {"model": model})
    return type(cls_name, (EditableSet,), {"Meta": meta_cls, **attrs})


def _snapshot_rules():
    """Snapshot the global permission rule registry so tests can
    register ad-hoc rules and restore on tearDown."""
    return dict(registered_rules())


def _restore_rules(snapshot):
    """Restore the rule registry to a previous snapshot."""
    from wies.core.permission_engine import _RULES  # noqa: PLC0415

    _RULES.clear()
    _RULES.update(snapshot)


def _make_assignment_editables(**overrides):
    """Build a fresh EditableSet for Assignment. Using a local factory
    avoids Python caching the class at import time across tests.
    """
    attrs = {
        "name": Editable(),
        "extra_info": Editable(),
    }
    attrs.update(overrides)
    return _register(_make_set("TestAssignmentEditables", Assignment, **attrs))


class InlineEditInfrastructureTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="inline@rijksoverheid.nl",
            first_name="Inline",
            last_name="Tester",
        )
        self.client.force_login(self.user)
        # The user_logged_in signal auto-creates a Colleague for the
        # user. Grab it for use as assignment owner.
        self.colleague = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(
            name="Original name",
            extra_info="Original description",
            owner=self.colleague,
            source="wies",
        )

        # Snapshot + install a fresh EditableSet per test.
        self._prev_registry = dict(REGISTRY)
        self.editables = _make_assignment_editables()
        self.url = reverse(
            "inline-edit",
            args=["assignment", self.assignment.pk, "name"],
        )

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_unknown_model_returns_404(self):
        resp = self.client.get(reverse("inline-edit", args=["unknown", 1, "name"]))
        assert resp.status_code == 404

    def test_unknown_name_returns_404(self):
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "nope"])
        resp = self.client.get(url)
        assert resp.status_code == 404

    def test_get_returns_display_partial(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        self.assertContains(resp, "Original name")
        self.assertContains(resp, "editable-field-display")
        self.assertContains(resp, "rvo-icon-bewerken")

    def test_get_edit_returns_form(self):
        resp = self.client.get(self.url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, 'name="name"')
        self.assertContains(resp, "rvo-form-field")
        self.assertContains(resp, "Opslaan")
        self.assertContains(resp, "Annuleren")

    def test_get_cancel_returns_display(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        self.assertContains(resp, "Original name")
        # Cancel doesn't render a form.
        self.assertNotContains(resp, "Opslaan")

    def test_post_valid_saves_and_returns_display(self):
        resp = self.client.post(self.url, {"name": "Updated name"})
        assert resp.status_code == 200
        self.assertContains(resp, "Updated name")
        # No big alert banner on the happy path — instead the pencil
        # button carries a `--just-saved` class that drives a CSS
        # pencil→checkmark→pencil flash.
        self.assertNotContains(resp, "rvo-alert--success")
        self.assertContains(resp, "edit-icon-button--just-saved")
        self.assertContains(resp, "edit-icon-button__check")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Updated name"

    def test_post_invalid_returns_form_with_error(self):
        # Empty string fails the required check (Assignment.name is
        # non-null + has no blank=True).
        resp = self.client.post(self.url, {"name": ""})
        assert resp.status_code == 200
        self.assertContains(resp, "rvo-form-field__error")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Original name"


class InlineEditPermissionTest(TestCase):
    """Permission denial flows. Rules are registered ad-hoc against the
    test EditableSet's editable, snapshotted in setUp and restored in
    tearDown so production rules aren't disturbed.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="perms@rijksoverheid.nl",
            first_name="P",
            last_name="P",
        )
        self.client.force_login(self.user)
        self.assignment = Assignment.objects.create(
            name="N",
            source="wies",
        )
        self._prev_registry = dict(REGISTRY)
        self._prev_rules = _snapshot_rules()

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)
        _restore_rules(self._prev_rules)

    def test_object_permission_denied_returns_display_with_alert(self):
        # No placement, no ownership, no Beheerder perm → whole-object
        # rule update_assignment denies → alert rendered.
        _register(_make_set("ObjectDeniedEditables", Assignment, name=Editable()))
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        # No edit trigger rendered on a denied response.
        self.assertNotContains(resp, "rvo-icon-bewerken")
        # And no form.
        self.assertNotContains(resp, 'name="name"')

    def test_field_permission_denied_returns_display_with_alert(self):
        # Field-level denial: register a rule against this editable that
        # always returns False, even though the whole-object rule might
        # otherwise allow.
        cls = _register(_make_set("FieldDeniedEditables", Assignment, name=Editable()))
        rule(Verb.UPDATE, cls.name)(lambda u, o: False)
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")

    def test_post_denied_does_not_save(self):
        cls = _register(_make_set("PostDeniedEditables", Assignment, name=Editable()))
        rule(Verb.UPDATE, cls.name)(lambda u, o: False)
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])
        resp = self.client.post(url, {"name": "hacked"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "N"


class InlineEditGroupTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Superuser so the engine's is_superuser short-circuit allows
        # all UPDATEs — these tests focus on group rendering/save, not auth.
        self.user = User.objects.create_user(
            email="group@rijksoverheid.nl",
            first_name="G",
            last_name="G",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.assignment = Assignment.objects.create(
            name="G",
            source="wies",
        )
        self._prev_registry = dict(REGISTRY)

        def _period_clean(cleaned):
            s, e = cleaned.get("start_date"), cleaned.get("end_date")
            if s and e and e < s:
                raise ValidationError({"end_date": "Einddatum moet na startdatum liggen."})
            return cleaned

        _register(
            _make_set(
                "PeriodEditables",
                Assignment,
                start_date=Editable(),
                end_date=Editable(),
                period=EditableGroup(
                    label="Looptijd",
                    fields=["start_date", "end_date"],
                    clean=_period_clean,
                ),
            )
        )
        self.url = reverse("inline-edit", args=["assignment", self.assignment.pk, "period"])

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_group_edit_renders_both_fields(self):
        resp = self.client.get(self.url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, 'name="start_date"')
        self.assertContains(resp, 'name="end_date"')

    def test_group_post_valid_saves_both(self):
        resp = self.client.post(
            self.url,
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        self.assignment.refresh_from_db()
        assert str(self.assignment.start_date) == "2026-03-01"
        assert str(self.assignment.end_date) == "2026-06-30"

    def test_group_cross_field_rule_surfaces_error(self):
        resp = self.client.post(
            self.url,
            {"start_date": "2026-06-30", "end_date": "2026-03-01"},
        )
        assert resp.status_code == 200
        self.assertContains(resp, "Einddatum moet na startdatum")
        self.assignment.refresh_from_db()
        assert self.assignment.start_date is None
        assert self.assignment.end_date is None


class InlineEditCustomSaveTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Superuser so permission checks pass; this test focuses on the
        # custom-save dispatch, not auth.
        self.user = User.objects.create_user(
            email="cs@rijksoverheid.nl",
            first_name="C",
            last_name="S",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.assignment = Assignment.objects.create(
            name="Before",
            source="wies",
        )
        self._prev_registry = dict(REGISTRY)
        self.save_calls = []

        def _custom_save(obj, value):
            self.save_calls.append((obj.pk, value))
            obj.name = f"Custom:{value}"
            obj.save()

        _register(_make_set("CustomSaveEditables", Assignment, name=Editable(save=_custom_save)))
        self.url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_custom_save_is_invoked(self):
        self.client.post(self.url, {"name": "Raw"})
        assert self.save_calls == [(self.assignment.pk, "Raw")]
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Custom:Raw"


class InlineEditDisplayTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Superuser so permission checks pass; this test focuses on
        # display rendering, not auth.
        self.user = User.objects.create_user(
            email="disp@rijksoverheid.nl",
            first_name="D",
            last_name="D",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.assignment = Assignment.objects.create(
            name="Shown",
            source="wies",
        )
        self._prev_registry = dict(REGISTRY)

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_default_display_shows_current_value(self):
        _register(_make_set("DefaultDisplayEditables", Assignment, name=Editable()))
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])
        resp = self.client.get(url)
        self.assertContains(resp, "Shown")

    def test_callable_display_is_invoked(self):
        _register(
            _make_set(
                "CallableDisplayEditables",
                Assignment,
                name=Editable(display=lambda o: f"[[ {o.name} ]]"),
            )
        )
        url = reverse("inline-edit", args=["assignment", self.assignment.pk, "name"])
        resp = self.client.get(url)
        self.assertContains(resp, "[[ Shown ]]")


class AssignmentPanelRenderTest(TestCase):
    """Verify inline_edit() Jinja global works when embedded in the
    assignment_panel_content.html template (HTMX panel-swap flow).
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="panel@rijksoverheid.nl",
            first_name="Panel",
            last_name="Tester",
        )
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(
            name="Panel Assignment",
            owner=self.colleague,  # user is owner → can edit
            source="wies",
        )

    def test_panel_renders_edit_button_for_owner(self):
        """Loading the home page with ?opdracht=<id> renders the panel
        with the inline-edit pencil for name + extra_info."""
        response = self.client.get(f"/?opdracht={self.assignment.id}")
        assert response.status_code == 200
        self.assertContains(response, "Panel Assignment")
        # Edit icon present for this authorized user.
        self.assertContains(response, "rvo-icon-bewerken")
        # Name should be addressable at the new inline-edit URL.
        self.assertContains(
            response,
            f"/inline-edit/assignment/{self.assignment.id}/name/",
        )


class ProfilePageRenderTest(TestCase):
    """Regression test: /profiel/ renders without the `SimpleLazyObject`
    has no `_meta` crash. `request.user` is a lazy wrapper and must be
    addressed via `obj._meta`, not `type(obj)._meta`.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="prof@rijksoverheid.nl",
            first_name="Prof",
            last_name="Tester",
        )
        self.client.force_login(self.user)

    def test_profile_page_renders(self):
        response = self.client.get("/profiel/")
        assert response.status_code == 200
        # Editable name field is present.
        self.assertContains(response, "inline-edit-user-")
        # Edit pencil for own profile.
        self.assertContains(response, "rvo-icon-bewerken")


class AssignmentEditablesFullTest(TestCase):
    """Covers the step-4 additions: start_date, end_date, owner, period."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="full@rijksoverheid.nl",
            first_name="F",
            last_name="F",
        )
        # Grant change_assignment so the user can edit regardless of ownership.
        self.user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        # Put user's Colleague in the BDM group so it shows up in owner choices.
        bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")
        self.user.groups.add(bdm_group)
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(
            name="Full Test",
            source="wies",
            owner=self.colleague,
        )

    def _url(self, name):
        return reverse("inline-edit", args=["assignment", self.assignment.id, name])

    def test_start_date_post_saves(self):
        resp = self.client.post(self._url("start_date"), {"start_date": "2026-05-01"})
        assert resp.status_code == 200
        self.assignment.refresh_from_db()
        assert str(self.assignment.start_date) == "2026-05-01"

    def test_period_group_renders_both_date_inputs(self):
        resp = self.client.get(self._url("period") + "?edit=true")
        self.assertContains(resp, 'name="start_date"')
        self.assertContains(resp, 'name="end_date"')

    def test_period_group_saves_both_dates(self):
        resp = self.client.post(
            self._url("period"),
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        self.assignment.refresh_from_db()
        assert str(self.assignment.start_date) == "2026-03-01"
        assert str(self.assignment.end_date) == "2026-06-30"

    def test_period_group_rejects_end_before_start(self):
        resp = self.client.post(
            self._url("period"),
            {"start_date": "2026-06-30", "end_date": "2026-03-01"},
        )
        assert resp.status_code == 200
        self.assertContains(resp, "Einddatum moet na startdatum liggen")
        self.assignment.refresh_from_db()
        assert self.assignment.start_date is None
        assert self.assignment.end_date is None

    def test_owner_edit_form_limits_choices_to_bdms(self):
        # A non-BDM colleague should not appear as an option.
        User.objects.create_user(
            email="notbdm@rijksoverheid.nl",
            first_name="Not",
            last_name="BDM",
        )
        resp = self.client.get(self._url("owner") + "?edit=true")
        self.assertContains(resp, self.colleague.name)
        self.assertNotContains(resp, "Not BDM")

    def test_owner_display_uses_custom_partial(self):
        resp = self.client.get(self._url("owner"))
        self.assertContains(resp, self.colleague.name)
        # Email link is rendered by the custom display partial.
        self.assertContains(resp, f"mailto:{self.colleague.email}")


class AssignmentCreateFormIntegrationTest(TestCase):
    """Verify that AssignmentCreateForm composes its fields from the
    shared AssignmentEditables declaration — labels/widgets/errors that
    change on the Editable must flow through into the create form
    automatically.
    """

    def test_labels_come_from_editables(self):
        form = AssignmentCreateForm()
        # Each form field's label matches the Editable's label.
        for name in ["name", "extra_info", "start_date", "end_date", "owner"]:
            assert form.fields[name].label == getattr(AssignmentEditables, name).label

    def test_owner_queryset_filtered_to_bdm_group(self):
        # ModelChoiceField queryset is derived from Editable.choices — it
        # includes the BDM group filter defined in the editables module.
        form = AssignmentCreateForm()
        qs = form.fields["owner"].queryset
        # The generated SQL references the BDM group name.
        assert "Business Development Manager" in str(qs.query)

    def test_period_cross_field_rule_applies(self):
        form = AssignmentCreateForm(
            data={
                "name": "X",
                "start_date": "2026-06-01",
                "end_date": "2026-01-01",
                "owner": "",
            }
        )
        form.is_valid()  # populate errors
        assert "Einddatum moet na startdatum liggen." in form.errors.get("end_date", [])


class PlacementServiceEditablesTest(TestCase):
    """Smoke tests for step-6: Placement + Service editables register
    and permission flows chain up to the parent assignment."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="ps@rijksoverheid.nl",
            first_name="P",
            last_name="S",
        )
        self.user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        self.client.force_login(self.user)
        col = Colleague.objects.get(user=self.user)
        assignment = Assignment.objects.create(
            name="A",
            owner=col,
            source="wies",
        )
        skill = Skill.objects.create(name="Rol X")
        self.service = Service.objects.create(
            description="Dienst X",
            assignment=assignment,
            skill=skill,
            source="wies",
        )
        self.placement = Placement.objects.create(
            colleague=col,
            service=self.service,
            source="wies",
        )

    def test_service_editable_registered_for_service_model(self):
        assert hasattr(ServiceEditables, "description")

    def test_placement_editable_registered_for_placement_model(self):
        assert hasattr(PlacementEditables, "colleague")

    def test_service_description_inline_edit_saves(self):
        url = reverse("inline-edit", args=["service", self.service.id, "description"])
        resp = self.client.post(url, {"description": "Nieuwe dienst"})
        assert resp.status_code == 200
        self.service.refresh_from_db()
        assert self.service.description == "Nieuwe dienst"

    def test_service_edit_denied_for_unrelated_user(self):
        unrelated = User.objects.create_user(
            email="other@rijksoverheid.nl",
            first_name="O",
            last_name="O",
        )
        c = Client()
        c.force_login(unrelated)
        url = reverse("inline-edit", args=["service", self.service.id, "description"])
        resp = c.post(url, {"description": "Gehackt"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.service.refresh_from_db()
        assert self.service.description == "Dienst X"


class AssignmentServicesDisplayTest(TestCase):
    """Regression tests for the services collection display partial —
    guard the HTML contract (filled rows render as anchors navigating
    to the colleague panel; vacant rows render as plain divs)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="svc-display@rijksoverheid.nl",
            first_name="Svc",
            last_name="Display",
        )
        self.user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(
            name="A",
            owner=self.colleague,
            source="wies",
        )
        skill = Skill.objects.create(name="Rol X")
        filled_service = Service.objects.create(
            description="Dienst gevuld",
            assignment=self.assignment,
            skill=skill,
            source="wies",
        )
        Placement.objects.create(
            colleague=self.colleague,
            service=filled_service,
            source="wies",
        )
        Service.objects.create(
            description="Dienst vacant",
            assignment=self.assignment,
            skill=skill,
            source="wies",
            status="OPEN",
        )
        self.url = reverse("inline-edit", args=["assignment", self.assignment.id, "services"])

    def test_filled_row_is_anchor_to_colleague_panel(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        expected_href = f"/opdrachten/?collega={self.colleague.id}"
        self.assertContains(resp, f'href="{expected_href}"')
        self.assertContains(resp, f'hx-get="{expected_href}"')
        self.assertContains(resp, 'hx-target="#side_panel-content"')
        self.assertContains(resp, f'title="Bekijk {self.colleague.name}"')
        self.assertContains(resp, "rvo-item-list__item--filled")

    def test_vacant_row_has_no_link(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        self.assertContains(resp, "rvo-item-list__item--vacant")
        self.assertContains(resp, "Openstaand")
        # Vacant row should not carry an hx-target (only filled anchors do).
        content = resp.content.decode()
        vacant_start = content.index("rvo-item-list__item--vacant")
        vacant_end = content.index("</div>", vacant_start)
        assert "hx-get" not in content[vacant_start:vacant_end]
        assert "href=" not in content[vacant_start:vacant_end]


class ServiceDescriptionPermissionTest(TestCase):
    """Field-level permission: a consultant placed on a service may
    edit that service's description; but not another service's, and
    not the non-description fields.
    """

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="bm@rijksoverheid.nl", first_name="Bm", last_name="Boss")
        self.owner = Colleague.objects.create(
            user=self.owner_user, name="Bm Boss", email="bm@rijksoverheid.nl", source="wies"
        )

        self.placed_user = User.objects.create_user(email="placed@rijksoverheid.nl", first_name="P", last_name="Laced")
        self.placed = Colleague.objects.create(
            user=self.placed_user, name="P Laced", email="placed@rijksoverheid.nl", source="wies"
        )

        self.other_user = User.objects.create_user(email="other@rijksoverheid.nl", first_name="O", last_name="Ther")
        self.other = Colleague.objects.create(
            user=self.other_user, name="O Ther", email="other@rijksoverheid.nl", source="wies"
        )

        assignment = Assignment.objects.create(name="A", owner=self.owner, source="wies")
        skill = Skill.objects.create(name="Rol")

        self.my_service = Service.objects.create(
            description="Mijn rol", assignment=assignment, skill=skill, source="wies"
        )
        Placement.objects.create(colleague=self.placed, service=self.my_service, source="wies")

        self.other_service = Service.objects.create(
            description="Andermans rol", assignment=assignment, skill=skill, source="wies"
        )
        Placement.objects.create(colleague=self.other, service=self.other_service, source="wies")

    def _desc_url(self, service):
        return reverse("inline-edit", args=["service", service.id, "description"])

    def test_placed_consultant_edits_own_description(self):
        self.client.force_login(self.placed_user)
        resp = self.client.post(self._desc_url(self.my_service), {"description": "Nieuwe rol"})
        assert resp.status_code == 200
        self.my_service.refresh_from_db()
        assert self.my_service.description == "Nieuwe rol"

    def test_placed_consultant_cannot_edit_other_service_description(self):
        self.client.force_login(self.placed_user)
        resp = self.client.post(self._desc_url(self.other_service), {"description": "Gestolen"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.other_service.refresh_from_db()
        assert self.other_service.description == "Andermans rol"

    def test_placed_consultant_cannot_edit_skill(self):
        self.client.force_login(self.placed_user)
        url = reverse("inline-edit", args=["service", self.my_service.id, "skill"])
        new_skill = Skill.objects.create(name="Andere rol")
        resp = self.client.post(url, {"skill": new_skill.id})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.my_service.refresh_from_db()
        assert self.my_service.skill_id != new_skill.id

    def test_owner_cannot_use_inline_pencil(self):
        """BM edits descriptions via the team editor, not the per-row
        pencil — so the inline description edit is denied for them."""
        self.client.force_login(self.owner_user)
        resp = self.client.post(self._desc_url(self.my_service), {"description": "BM probeert"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.my_service.refresh_from_db()
        assert self.my_service.description == "Mijn rol"


class OrgPickerWidgetTest(TestCase):
    """Unit tests for the shared OrgPickerWidget + OrganizationsField.
    Both the Assignment create form and the inline `organizations`
    editable compose them, so these tests lock in the parsing +
    validation contract.
    """

    def setUp(self):
        self.org_a = OrganizationUnit.objects.create(name="Org A")
        self.org_b = OrganizationUnit.objects.create(name="Org B")

    def test_widget_parses_formset_shaped_post(self):
        w = OrgPickerWidget()
        data = {
            "org-TOTAL_FORMS": "2",
            "org-0-organization": str(self.org_a.id),
            "org-0-role": "PRIMARY",
            "org-1-organization": str(self.org_b.id),
            "org-1-role": "INVOLVED",
        }
        parsed = w.value_from_datadict(data, {}, "organizations")
        assert parsed == [
            {"organization": str(self.org_a.id), "role": "PRIMARY"},
            {"organization": str(self.org_b.id), "role": "INVOLVED"},
        ]

    def test_widget_ignores_missing_total_forms(self):
        assert OrgPickerWidget().value_from_datadict({}, {}, "organizations") == []

    def test_field_resolves_org_ids_to_instances(self):
        f = OrganizationsField(required=True)
        cleaned = f.clean(
            [
                {"organization": self.org_a.id, "role": "PRIMARY"},
                {"organization": self.org_b.id, "role": "INVOLVED"},
            ]
        )
        assert cleaned[0]["organization"] == self.org_a
        assert cleaned[0]["role"] == "PRIMARY"
        assert cleaned[1]["organization"] == self.org_b

    def test_field_requires_exactly_one_primary(self):
        f = OrganizationsField(required=True)
        # Zero primaries among selected orgs.
        with self.assertRaises(ValidationError) as exc:  # noqa: PT027
            f.clean(
                [
                    {"organization": self.org_a.id, "role": "INVOLVED"},
                    {"organization": self.org_b.id, "role": "INVOLVED"},
                ]
            )
        assert "primaire" in str(exc.exception).lower()

    def test_field_required_empty_raises(self):
        f = OrganizationsField(required=True)
        with self.assertRaises(ValidationError):  # noqa: PT027
            f.clean([])

    def test_field_rejects_unknown_org_id(self):
        f = OrganizationsField(required=True)
        with self.assertRaises(ValidationError):  # noqa: PT027
            f.clean([{"organization": 99999, "role": "PRIMARY"}])


class InlineOrganizationsEditTest(TestCase):
    """End-to-end: the `organizations` inline editable persists
    AssignmentOrganizationUnit rows with the right roles."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="orgs@rijksoverheid.nl",
            first_name="O",
            last_name="O",
        )
        self.user.user_permissions.add(Permission.objects.get(codename="change_assignment"))
        self.client.force_login(self.user)
        col = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(
            name="Orgs test",
            owner=col,
            source="wies",
        )
        self.org_a = OrganizationUnit.objects.create(name="Org A")
        self.org_b = OrganizationUnit.objects.create(name="Org B")

    def test_post_with_two_orgs_persists_through_rows(self):
        url = reverse("inline-edit", args=["assignment", self.assignment.id, "organizations"])
        self.client.post(
            url,
            {
                "org-TOTAL_FORMS": "2",
                "org-0-organization": self.org_a.id,
                "org-0-role": "PRIMARY",
                "org-1-organization": self.org_b.id,
                "org-1-role": "INVOLVED",
            },
        )
        rows = AssignmentOrganizationUnit.objects.filter(
            assignment=self.assignment,
        ).order_by("role")
        assert {(r.organization_id, r.role) for r in rows} == {
            (self.org_a.id, "PRIMARY"),
            (self.org_b.id, "INVOLVED"),
        }

    def test_post_without_primary_shows_error(self):
        url = reverse("inline-edit", args=["assignment", self.assignment.id, "organizations"])
        resp = self.client.post(
            url,
            {
                "org-TOTAL_FORMS": "2",
                "org-0-organization": self.org_a.id,
                "org-0-role": "INVOLVED",
                "org-1-organization": self.org_b.id,
                "org-1-role": "INVOLVED",
            },
        )
        assert resp.status_code == 200
        self.assertContains(resp, "primaire")

    def test_get_edit_prefills_existing_organizations(self):
        """Editable.initial must feed the edit form with current values —
        confirms the GET ?edit=true path reads through OrganizationsField."""
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.org_a, role="PRIMARY")
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=self.org_b, role="INVOLVED")
        url = reverse("inline-edit", args=["assignment", self.assignment.id, "organizations"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        # Hidden inputs generated by OrgPickerWidget carry the two
        # org ids and their roles from the initial payload.
        self.assertContains(resp, f'data-org-id="{self.org_a.id}"')
        self.assertContains(resp, f'data-org-id="{self.org_b.id}"')
        self.assertContains(resp, 'data-org-role="PRIMARY"')
        self.assertContains(resp, 'data-org-role="INVOLVED"')


class ColleagueLabelsInlineEditTest(TestCase):
    """End-to-end inline editing of labels_<category_id>. Verifies the
    dynamic resolver builds the right Editable and that saving a category
    leaves labels in other categories alone.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="labels@rijksoverheid.nl",
            first_name="L",
            last_name="L",
        )
        self.user.user_permissions.add(Permission.objects.get(codename="change_colleague"))
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)

        self.expertise = LabelCategory.objects.create(name="Expertise", color="#DCE3EA")
        self.thema = LabelCategory.objects.create(name="Thema", color="#B3D7EE")

        self.label_ai = Label.objects.create(name="AI", category=self.expertise)
        self.label_cloud = Label.objects.create(name="Cloud", category=self.expertise)
        self.label_weerbaar = Label.objects.create(name="Digitale weerbaarheid", category=self.thema)

        # Pre-existing selections across both categories.
        self.colleague.labels.add(self.label_ai, self.label_weerbaar)

    def test_post_replaces_only_target_category(self):
        """Saving labels_<expertise.id> with [Cloud] must swap AI→Cloud
        within Expertise but leave the Thema label untouched."""
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.id, f"labels_{self.expertise.id}"],
        )
        resp = self.client.post(url, {"labels": [self.label_cloud.id]})
        assert resp.status_code == 200
        current = set(self.colleague.labels.values_list("pk", flat=True))
        assert current == {self.label_cloud.id, self.label_weerbaar.id}

    def test_get_display_shows_current_category_labels(self):
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.id, f"labels_{self.expertise.id}"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 200
        # Label from the right category appears; label from the other
        # category does not.
        self.assertContains(resp, "AI")
        self.assertNotContains(resp, "Digitale weerbaarheid")

    def test_unknown_category_id_returns_404(self):
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.id, "labels_999999"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 404

    def test_non_integer_suffix_returns_404(self):
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.id, "labels_abc"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 404


class UserProfileColleagueAutoCreateTest(TestCase):
    """User.first_name / last_name saves through the inline-edit view
    must create a linked Colleague when none exists, and keep its name
    in sync on subsequent edits.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="autocol@rijksoverheid.nl",
            first_name="Oud",
            last_name="Naam",
        )
        # `user_logged_in` (fired by force_login) auto-creates a
        # Colleague. Delete it AFTER force_login to exercise the
        # get_or_create branch of the save hook.
        self.client.force_login(self.user)
        Colleague.objects.filter(user=self.user).delete()

    def test_first_name_save_creates_colleague(self):
        assert not Colleague.objects.filter(user=self.user).exists()
        url = reverse("inline-edit", args=["user", self.user.id, "first_name"])
        resp = self.client.post(url, {"first_name": "Nieuwe"})
        assert resp.status_code == 200
        colleague = Colleague.objects.get(user=self.user)
        # Name reflects combined user.first_name + user.last_name.
        assert colleague.name == "Nieuwe Naam"

    def test_subsequent_last_name_save_updates_colleague_name(self):
        url_last = reverse("inline-edit", args=["user", self.user.id, "last_name"])
        self.client.post(url_last, {"last_name": "Anders"})
        colleague = Colleague.objects.get(user=self.user)
        assert colleague.name == "Oud Anders"


class InlineEditJinjaGlobalErrorTest(TestCase):
    """The jinja global `inline_edit` raises RuntimeError for unknown
    model/editable — a misconfiguration should be loud, not silent.
    """

    def setUp(self):
        self._prev_registry = dict(REGISTRY)

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_unknown_model_raises(self):
        from wies.core.inline_edit.jinja import inline_edit as inline_edit_fn  # noqa: PLC0415

        # Strip registry — colleague editable set must be absent to hit
        # the "no EditableSet" branch.
        REGISTRY.clear()
        assignment = Assignment.objects.create(name="X", source="wies")
        with self.assertRaises(RuntimeError) as exc:  # noqa: PT027
            inline_edit_fn({}, assignment, "name")
        assert "No EditableSet registered" in str(exc.exception)

    def test_unknown_editable_raises(self):
        from wies.core.inline_edit.jinja import inline_edit as inline_edit_fn  # noqa: PLC0415

        # Empty EditableSet so the registry entry exists but the name
        # doesn't resolve statically or dynamically.
        _register(_make_set("EmptyAssignmentEditables", Assignment))
        assignment = Assignment.objects.create(name="X", source="wies")
        with self.assertRaises(RuntimeError) as exc:  # noqa: PT027
            inline_edit_fn({}, assignment, "nonsuch")
        assert "No editable 'nonsuch'" in str(exc.exception)

    def test_none_obj_returns_empty(self):
        from wies.core.inline_edit.jinja import inline_edit as inline_edit_fn  # noqa: PLC0415

        # Calling the global on a None object renders nothing — gate for
        # optional FKs used in templates (`inline_edit(panel.owner, ...)`).
        result = inline_edit_fn({}, None, "name")
        assert str(result) == ""
