"""Tests for the inline_edit infrastructure.

Creates on-the-fly EditableSets bound to real models (Assignment,
Colleague), hits the generic view, and asserts the response shape +
persistence behaviour. Registrations are cleaned up in tearDown to
avoid leaking into unrelated tests.
"""

import json
import re
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.editables import REGISTRY
from wies.core.editables.assignment import AssignmentEditables, _services_render_change
from wies.core.editables.placement import PlacementEditables
from wies.core.editables.service import ServiceEditables
from wies.core.fields import OrganizationsField
from wies.core.inline_edit.base import (
    Editable,
    EditableGroup,
    EditableSet,
)
from wies.core.inline_edit.forms import build_combined_form_class
from wies.core.models import (
    Assignment,
    AssignmentOrganizationUnit,
    Colleague,
    Event,
    Label,
    LabelCategory,
    OrganizationUnit,
    Placement,
    Service,
    Skill,
)
from wies.core.permission_engine import Verb, registered_rules, rule
from wies.core.services.assignments import assignment_create_specs
from wies.core.services.users import create_user
from wies.core.tests.inline_edit_helpers import post_inline_edit
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
            args=["assignment", self.assignment.public_id, "name"],
        )

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_unknown_model_returns_404(self):
        resp = self.client.get(reverse("inline-edit", args=["unknown", uuid.uuid4(), "name"]))
        assert resp.status_code == 404

    def test_unknown_name_returns_404(self):
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "nope"])
        resp = self.client.get(url)
        assert resp.status_code == 404

    def test_get_returns_display_partial(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        self.assertContains(resp, "Original name")
        self.assertContains(resp, "editable-field-display")
        self.assertContains(resp, "edit-icon-button__pencil")

    def test_only_pencil_enters_edit_mode(self):
        """The value itself is not clickable — only the pencil button opens
        edit mode — so interactive content inside it (links, "Toon meer")
        doesn't bubble into edit mode (#395)."""
        resp = self.client.get(self.url)
        content = resp.content.decode()
        value_div = content.split('class="editable-field-display__value"')[1].split(">")[0]
        assert "hx-get" not in value_div
        assert 'role="button"' not in value_div
        # The pencil button still carries the edit trigger.
        assert "edit=true" in content
        assert "edit-icon-button" in content
        # And a tooltip aiding discoverability now the value isn't clickable.
        assert 'title="Bewerk ' in content

    def test_get_edit_returns_form(self):
        resp = self.client.get(self.url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, 'name="name"')
        self.assertContains(resp, "nldd-form-field")
        self.assertContains(resp, "Opslaan")
        self.assertContains(resp, "Annuleren")

    def test_get_cancel_returns_display(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        self.assertContains(resp, "Original name")
        # Cancel doesn't render a form.
        self.assertNotContains(resp, "Opslaan")

    def test_post_valid_saves_and_returns_display(self):
        resp = post_inline_edit(self.client, self.url, {"name": "Updated name"})
        assert resp.status_code == 200
        self.assertContains(resp, "Updated name")
        # Save feedback is a notification triggered client-side via HX-Trigger.
        # The label rides along so the message can name what was saved.
        assert json.loads(resp["HX-Trigger-After-Swap"]) == {"inline-edit-saved": {"label": ""}}
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Updated name"

    def test_post_unchanged_value_announces_nothing(self):
        """The onboarding wizard submits every field on "Volgende", so an
        untouched one must not announce a save that did not happen."""
        resp = post_inline_edit(self.client, self.url, {"name": "Original name"})
        assert resp.status_code == 200
        assert "HX-Trigger-After-Swap" not in resp

    def test_post_invalid_returns_form_with_error(self):
        # Empty string fails the required check (Assignment.name is
        # non-null + has no blank=True).
        resp = self.client.post(self.url, {"name": ""})
        assert resp.status_code == 200
        self.assertContains(resp, "nldd-form-field-error-text")
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
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        # No edit trigger rendered on a denied response.
        self.assertNotContains(resp, "edit-icon-button__pencil")
        # And no form.
        self.assertNotContains(resp, 'name="name"')

    def test_field_permission_denied_returns_display_with_alert(self):
        # Field-level denial: register a rule against this editable that
        # always returns False, even though the whole-object rule might
        # otherwise allow.
        cls = _register(_make_set("FieldDeniedEditables", Assignment, name=Editable()))
        rule(Verb.UPDATE, cls.name)(lambda u, o: False)
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")

    def test_post_denied_does_not_save(self):
        cls = _register(_make_set("PostDeniedEditables", Assignment, name=Editable()))
        rule(Verb.UPDATE, cls.name)(lambda u, o: False)
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])
        resp = self.client.post(url, {"name": "hacked"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "N"


class InlineEditGroupTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user(None, "G", "G", "group@rijksoverheid.nl")
        self.client.force_login(self.user)

        # Owner so the permission engine allows all UPDATEs
        # these tests focus on group rendering/save, not auth.
        self.assignment = Assignment.objects.create(
            name="G",
            source="wies",
            owner=self.user.colleague,
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
                # Stands in for AssignmentEditables, so it records audit events
                # (object_type defaults to the model's name, "Assignment").
                audit_events=True,
                start_date=Editable(),
                end_date=Editable(),
                period=EditableGroup(
                    label="Opdrachtperiode",
                    fields=["start_date", "end_date"],
                    clean=_period_clean,
                ),
            )
        )
        self.url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "period"])

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_group_edit_renders_both_fields(self):
        resp = self.client.get(self.url + "?edit=true")
        assert resp.status_code == 200
        self.assertContains(resp, 'name="start_date"')
        self.assertContains(resp, 'name="end_date"')

    def test_group_post_valid_saves_both(self):
        resp = post_inline_edit(
            self.client,
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

    def test_group_post_emits_event_per_changed_field(self):
        resp = post_inline_edit(
            self.client,
            self.url,
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        events = Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update")
        field_names = sorted(e.context["field_name"] for e in events)
        assert field_names == ["end_date", "start_date"]

    def test_inline_edit_records_client_ip_and_user_agent(self):
        """End-to-end guard: a real inline-edit POST must thread the request down
        to the audit event, so Event.ip / user_agent are populated."""
        resp = post_inline_edit(
            self.client,
            self.url,
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
            REMOTE_ADDR="203.0.113.9",
            HTTP_USER_AGENT="Mozilla/5.0 (inline editor)",
        )
        assert resp.status_code == 200
        event = Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update").first()
        assert event is not None
        assert event.ip == "203.0.113.9"
        assert event.user_agent == "Mozilla/5.0 (inline editor)"

    def test_group_post_emits_event_only_for_changed_field(self):
        self.assignment.start_date = "2026-03-01"
        self.assignment.save()
        resp = post_inline_edit(
            self.client,
            self.url,
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        events = list(Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update"))
        assert len(events) == 1
        assert events[0].context["field_name"] == "end_date"

    def test_group_post_no_change_no_events(self):
        self.assignment.start_date = "2026-03-01"
        self.assignment.end_date = "2026-06-30"
        self.assignment.save()
        resp = post_inline_edit(
            self.client,
            self.url,
            {"start_date": "2026-03-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        assert not Event.objects.filter(object_type="Assignment", object_id=self.assignment.id).exists()


class InlineEditCustomSaveTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user(None, email="cs@rijksoverheid.nl", first_name="C", last_name="S")
        self.client.force_login(self.user)

        # Owner so permission checks pass;
        # this test focuses on the custom-save dispatch, not auth.
        self.assignment = Assignment.objects.create(
            name="Before",
            source="wies",
            owner=self.user.colleague,
        )
        self._prev_registry = dict(REGISTRY)
        self.save_calls = []

        def _custom_save(obj, value):
            self.save_calls.append((obj.pk, value))
            obj.name = f"Custom:{value}"
            obj.save()

        _register(_make_set("CustomSaveEditables", Assignment, name=Editable(save=_custom_save)))
        self.url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_custom_save_is_invoked(self):
        post_inline_edit(self.client, self.url, {"name": "Raw"})
        assert self.save_calls == [(self.assignment.pk, "Raw")]
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Custom:Raw"


class InlineEditDisplayTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user(
            None,
            email="disp@rijksoverheid.nl",
            first_name="D",
            last_name="D",
        )
        self.client.force_login(self.user)

        # Owner so permission checks pass;
        # this test focuses on display rendering, not auth.
        self.assignment = Assignment.objects.create(
            name="Shown",
            source="wies",
            owner=self.user.colleague,
        )
        self._prev_registry = dict(REGISTRY)

    def tearDown(self):
        REGISTRY.clear()
        REGISTRY.update(self._prev_registry)

    def test_default_display_shows_current_value(self):
        _register(_make_set("DefaultDisplayEditables", Assignment, name=Editable()))
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])
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
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "name"])
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
        # The owner field only offers BDM colleagues, so the combined edit form
        # needs the owner to be a valid choice for itself.
        bdm_group, _ = Group.objects.get_or_create(name="Business Development Manager")
        self.user.groups.add(bdm_group)
        self.organization = OrganizationUnit.objects.create(name="PanelOrg", label="Panel Org")
        self.assignment = Assignment.objects.create(
            name="Panel Assignment",
            owner=self.colleague,  # user is owner → can edit
            source="wies",
        )

    def test_panel_renders_edit_button_for_owner(self):
        """Loading the home page with ?opdracht=<id> renders the panel with the
        edit buttons that open the child sheets (per-field inline edit has been
        replaced by one combined form)."""
        response = self.client.get(f"/?opdracht={self.assignment.public_id}")
        assert response.status_code == 200
        self.assertContains(response, "Panel Assignment")
        self.assertContains(response, f"opdracht={self.assignment.public_id}&amp;bewerken=1")
        self.assertContains(response, f"opdracht={self.assignment.public_id}&amp;teamlid=nieuw-aanvraag")
        self.assertContains(response, f"opdracht={self.assignment.public_id}&amp;teamlid=nieuw-ingevuld")

    def test_unresolved_panel_target_404s_for_htmx_request(self):
        """A panel HTMX request whose opdracht can't be resolved must 404 (so
        HTMX shows the graceful "Niet gevonden" partial) rather than returning a
        full page that gets swapped into the slide-over. Guards the HX-Target
        string match in _is_side_panel_request (side-panel-content, hyphens)."""
        response = self.client.get(
            "/?opdracht=999",  # integer, never a valid public_id
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert response.status_code == 404

    def test_edit_param_renders_combined_form(self):
        """?opdracht=<id>&bewerken=1 renders the child sheet with one form over
        all assignment fields, posting to the assignment-edit endpoint."""
        response = self.client.get(f"/?opdracht={self.assignment.public_id}&bewerken=1")
        assert response.status_code == 200
        self.assertContains(response, "Opdracht bewerken")
        self.assertContains(response, f"/opdracht/{self.assignment.public_id}/bewerken/")
        for field in ("name", "extra_info", "owner", "start_date", "end_date"):
            self.assertContains(response, f'name="{field}"')

    def test_teamlid_nieuw_renders_member_form(self):
        """?opdracht=<id>&teamlid=nieuw-aanvraag renders the member child sheet
        with one preset row, posting to the member endpoint."""
        response = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid=nieuw-aanvraag")
        assert response.status_code == 200
        self.assertContains(response, "Aanvraag toevoegen")
        self.assertContains(response, f"/opdracht/{self.assignment.public_id}/teamlid/")
        # The status radios post on their own (nldd-radio-button-field is
        # form-associated), so the group carries the field name and there is no
        # hidden-input bridge left to keep in sync.
        self.assertContains(response, '<nldd-radio-button-group name="is_filled"')
        self.assertNotContains(response, "data-status-input")

    def test_teamlid_edit_renders_existing_member(self):
        """?teamlid=<service public_id> renders the row of that one member."""
        skill = Skill.objects.create(name="Ontwerper")
        service = Service.objects.create(assignment=self.assignment, skill=skill, source="wies")
        response = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid={service.public_id}")
        assert response.status_code == 200
        self.assertContains(response, "Teamlid bewerken")
        self.assertContains(response, 'name="service_public_id"')

    def test_member_post_adds_a_service_and_keeps_others(self):
        """A member POST only touches its own row: existing services survive."""
        skill = Skill.objects.create(name="Ontwerper")
        existing = Service.objects.create(assignment=self.assignment, skill=skill, source="wies")
        response = self.client.post(
            f"/opdracht/{self.assignment.public_id}/teamlid/",
            {
                "service_public_id": "",
                "placement_public_id": "",
                "is_filled": "aanvraag",
                "skill": str(skill.public_id),
                "has_custom_period": "on",
                "terug_url": f"/?opdracht={self.assignment.public_id}",
            },
        )
        assert response.status_code == 204
        services = list(self.assignment.services.all())
        assert len(services) == 2
        assert existing.id in [s.id for s in services]

    def test_member_post_without_skill_blocks_instead_of_deleting(self):
        """An empty role is rejected by the required Rol field; the endpoint
        re-renders with the error on the combo box (via its own error-message
        attribute), not a top banner, instead of a silent no-op."""
        skill = Skill.objects.create(name="Ontwerper")
        service = Service.objects.create(assignment=self.assignment, skill=skill, source="wies")
        response = self.client.post(
            f"/opdracht/{self.assignment.public_id}/teamlid/",
            {
                "service_public_id": str(service.public_id),
                "placement_public_id": "",
                "is_filled": "aanvraag",
                "skill": "",
                "has_custom_period": "on",
            },
        )
        assert response.status_code == 200
        # nldd-form-field only reveals the message when the combo reflects `invalid`
        # and points at the error text by id via `error-message` (see forms/field.html).
        self.assertContains(response, 'error-message="error-skill-1"')
        self.assertContains(response, '<nldd-form-field-error-text id="error-skill-1" invalid>Dit veld is verplicht.')
        self.assertNotContains(response, 'nldd-banner variant="critical"')
        assert self.assignment.services.filter(id=service.id).exists()

    def test_member_delete_removes_only_that_service(self):
        skill = Skill.objects.create(name="Ontwerper")
        keep = Service.objects.create(assignment=self.assignment, skill=skill, source="wies")
        gone = Service.objects.create(assignment=self.assignment, skill=skill, source="wies")
        response = self.client.post(
            f"/opdracht/{self.assignment.public_id}/teamlid/{gone.public_id}/verwijderen/",
            {"terug_url": f"/?opdracht={self.assignment.public_id}"},
        )
        assert response.status_code == 204
        assert "HX-Location" in response
        ids = set(self.assignment.services.values_list("id", flat=True))
        assert keep.id in ids
        assert gone.id not in ids

    def test_edit_post_saves_and_redirects_back(self):
        """A valid POST saves every field and sends the client back to the
        parent panel via HX-Location."""
        response = self.client.post(
            f"/opdracht/{self.assignment.public_id}/bewerken/",
            {
                "name": "Hernoemd",
                "extra_info": "Toelichting",
                "owner": str(self.colleague.public_id),
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "org-TOTAL_FORMS": "1",
                "org-INITIAL_FORMS": "0",
                "org-MIN_NUM_FORMS": "1",
                "org-MAX_NUM_FORMS": "1000",
                "org-0-organization": str(self.organization.public_id),
                "org-0-role": "PRIMARY",
                "terug_url": f"/?opdracht={self.assignment.public_id}",
            },
        )
        assert response.status_code == 204
        assert "HX-Location" in response
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Hernoemd"
        assert self.assignment.extra_info == "Toelichting"
        assert str(self.assignment.start_date) == "2026-01-01"

    def test_edit_post_with_errors_rerenders_form(self):
        """An invalid POST (missing required name) re-renders the child sheet
        with the error instead of saving."""
        response = self.client.post(
            f"/opdracht/{self.assignment.public_id}/bewerken/",
            {
                "name": "",
                "owner": str(self.colleague.public_id),
                "org-TOTAL_FORMS": "1",
                "org-INITIAL_FORMS": "0",
                "org-MIN_NUM_FORMS": "1",
                "org-MAX_NUM_FORMS": "1000",
                "org-0-organization": str(self.organization.public_id),
                "org-0-role": "PRIMARY",
            },
        )
        assert response.status_code == 200
        self.assertContains(response, "Opdrachtnaam is verplicht")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Panel Assignment"


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
        self.assertContains(response, "Prof Tester")
        self.assertContains(response, reverse("profile-name-edit"))


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
        return reverse("inline-edit", args=["assignment", self.assignment.public_id, name])

    def test_start_date_post_saves(self):
        resp = post_inline_edit(self.client, self._url("start_date"), {"start_date": "2026-05-01"})
        assert resp.status_code == 200
        self.assignment.refresh_from_db()
        assert str(self.assignment.start_date) == "2026-05-01"

    def test_period_group_renders_both_date_inputs(self):
        resp = self.client.get(self._url("period") + "?edit=true")
        self.assertContains(resp, 'name="start_date"')
        self.assertContains(resp, 'name="end_date"')

    def test_period_group_saves_both_dates(self):
        resp = post_inline_edit(
            self.client,
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

    def test_owner_link_present_on_display(self):
        # The navigation link to the owner's profile is supplied by the
        # editable's display_context, not a panel-only extra (#395).
        resp = self.client.get(self._url("owner"))
        self.assertContains(resp, f"collega={self.colleague.public_id}")

    def test_owner_link_survives_cancel(self):
        # Edit + cancel must re-render the link, not drop it to plain text (#395).
        resp = self.client.get(self._url("owner") + "?cancel=true")
        assert resp.status_code == 200
        self.assertContains(resp, f"collega={self.colleague.public_id}")
        self.assertContains(resp, f"mailto:{self.colleague.email}")

    def test_owner_link_survives_save(self):
        # A successful save re-renders the display; the link must persist (#395).
        resp = post_inline_edit(self.client, self._url("owner"), {"owner": self.colleague.public_id})
        assert resp.status_code == 200
        self.assertContains(resp, f"collega={self.colleague.public_id}")


class AssignmentCreateFormIntegrationTest(TestCase):
    """Verify that the assignment-create sheet form composes its fields from the
    shared AssignmentEditables declaration — labels/widgets/errors that change on
    the Editable must flow through automatically. The form is built from
    ``assignment_create_specs()`` (the live create-sheet flow).
    """

    def _form_cls(self):
        form_cls, _ = build_combined_form_class(assignment_create_specs())
        return form_cls

    def test_labels_come_from_editables(self):
        form = self._form_cls()()
        for name in ["name", "extra_info", "start_date", "end_date", "owner"]:
            assert str(form.fields[name].label) == str(getattr(AssignmentEditables, name).label)

    def test_owner_queryset_filtered_to_bdm_group(self):
        # The owner queryset is derived from the Editable's choices — it includes
        # the BDM group filter defined in the editables module.
        form = self._form_cls()()
        qs = form.fields["owner"].queryset
        assert "Business Development Manager" in str(qs.query)

    def test_period_cross_field_rule_applies(self):
        form = self._form_cls()(
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
        url = reverse("inline-edit", args=["service", self.service.public_id, "description"])
        resp = post_inline_edit(self.client, url, {"description": "Nieuwe dienst"})
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
        url = reverse("inline-edit", args=["service", self.service.public_id, "description"])
        resp = c.post(url, {"description": "Gehackt"})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.service.refresh_from_db()
        assert self.service.description == "Dienst X"

    def test_placement_period_edit_logs_event_on_assignment(self):
        """A period edit on a placement (the profile path) is mirrored as a
        Team event on the parent assignment timeline (#393)."""
        url = reverse("inline-edit", args=["placement", self.placement.public_id, "period"])
        resp = post_inline_edit(
            self.client,
            url,
            {
                "period_source": Placement.PLACEMENT,
                "specific_start_date": "2026-06-19",
                "specific_end_date": "2026-12-31",
            },
        )
        assert resp.status_code == 200
        assignment = self.service.assignment
        events = list(Event.objects.filter(object_type="Assignment", object_id=assignment.id, action="update"))
        assert len(events) == 1
        change = events[0].context["changes"][0]
        assert change["new"]["end_date"] == "2026-12-31"
        assert change["new"]["has_custom_period"] is False


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
        self.url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "services"])

    def test_filled_row_is_clickable_to_placement_panel(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        # Renders inside the open NLDD side panel, so it swaps the inner
        # content (#side-panel-content) rather than rebuilding the sheet.
        self.assertContains(resp, 'hx-target="#side-panel-content"')
        self.assertContains(resp, "plaatsing=")
        self.assertContains(resp, self.colleague.name)
        filled_row = self._row_containing(resp, self.colleague.name)
        assert "hx-get" in filled_row
        assert "plaatsing=" in filled_row

    @staticmethod
    def _rows(resp) -> list[str]:
        """The team rows, in render order, as raw `nldd-list-item` markup."""
        content = resp.content.decode()
        return [f"<nldd-list-item{part}" for part in content.split("<nldd-list-item")[1:]]

    def _row_containing(self, resp, needle: str) -> str:
        match = next((row for row in self._rows(resp) if needle in row), None)
        assert match is not None, f"no team row containing {needle!r}"
        return match

    def test_vacant_row_has_no_link(self):
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        self.assertContains(resp, "Aanvraag")
        # A vacancy has nothing to link to — only filled rows open a panel. The
        # ROW must stay non-interactive; the row menu (with its own hx-gets)
        # sits in slot="end", outside the row action, so check the open tag.
        vacant_row = self._row_containing(resp, "Aanvraag")
        open_tag = vacant_row.split(">", 1)[0]
        assert "hx-get" not in open_tag
        assert "href=" not in open_tag
        assert "Bekijk teamlid" not in vacant_row

    def test_vacant_row_renders_before_filled_row(self):
        """Vacancies-first ordering (issue #331) — even though the filled
        service was created first."""
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        rows = self._rows(resp)
        vacant_pos = next(i for i, row in enumerate(rows) if "Aanvraag" in row)
        filled_pos = next(i for i, row in enumerate(rows) if self.colleague.name in row)
        assert vacant_pos < filled_pos

    def test_display_omits_team_level_edit_button(self):
        """`EditableCollection.hide_edit_button=True` must apply on every
        render path — the panel template, the post-save re-render, and
        a direct GET on the inline-edit URL all suppress the team-level
        pencil. The parent template provides its own "Team bewerken"
        trigger."""
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        content = resp.content.decode()
        team_wrapper = content.split('id="inline-edit-assignment-')[1]
        # No clickable wrapper, no pencil button on the team-level
        # editable-field-display (per-row description pencils are still
        # rendered and unrelated to this check).
        team_outer = team_wrapper.split("<nldd-list")[0]
        assert 'role="button"' not in team_outer
        assert "edit-icon-button" not in team_outer

    def test_row_menu_edit_url_uses_public_id(self):
        """The row "Aanvraag/Rol wijzigen" action must build its panel URL from
        the assignment's public_id, not its integer PK — the panel resolver
        looks up by public_id and a bare integer 404s ("Niet gevonden")."""
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        filled_row = self._row_containing(resp, self.colleague.name)
        service = Placement.objects.get(colleague=self.colleague).service
        assert f"opdracht={self.assignment.public_id}&teamlid={service.public_id}" in filled_row
        # Never the integer service or assignment PK.
        assert f"teamlid={service.id}" not in filled_row
        assert f"opdracht={self.assignment.id}&teamlid=" not in filled_row

    def test_row_menu_view_url_uses_public_id(self):
        """ "Bekijk teamlid" must build ?plaatsing= from the placement's
        public_id, not its integer PK."""
        resp = self.client.get(self.url + "?cancel=true")
        assert resp.status_code == 200
        filled_row = self._row_containing(resp, self.colleague.name)
        placement = Placement.objects.get(colleague=self.colleague)
        assert f"plaatsing={placement.public_id}" in filled_row
        assert f"plaatsing={placement.id}&" not in filled_row

    def test_row_menu_edit_url_resolves_to_member_panel(self):
        """End-to-end: the URL the row menu emits must actually open the
        member-edit panel (HTTP 200), not the "Niet gevonden" partial."""
        service = Placement.objects.get(colleague=self.colleague).service
        panel = self.client.get(
            f"/?opdracht={self.assignment.public_id}&teamlid={service.public_id}",
            headers={"hx-request": "true", "hx-target": "side-panel-content"},
        )
        assert panel.status_code == 200
        self.assertContains(panel, "Teamlid bewerken")


class AssignmentServicesAuditTest(TestCase):
    """Editing one team member via the member-edit route emits one audit
    event with a before/after team summary.

    Team editing moved from the (now read-only) ``services`` inline-edit
    collection to the per-member flow: the ``assignment-member-edit`` route
    posts a single row (a plain, prefix-free ``ServiceForm``) and mutates exactly
    that one service (``save_service_from_form``). Because a member POST only touches
    its own row, every save produces a one-row audit diff — which is exactly
    what these tests already assert. The endpoint routes through
    ``member_audit_event``, which snapshots the whole team before/after around
    the mutation, so the event context (``field_name``/``field_label``/
    ``changes``) is unchanged.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="svc-audit@rijksoverheid.nl",
            first_name="Svc",
            last_name="Audit",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        self.assignment = Assignment.objects.create(name="A", owner=self.colleague, source="wies")
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_java = Skill.objects.create(name="Java")
        self.filled_service = Service.objects.create(
            description="Filled", assignment=self.assignment, skill=self.skill_python, source="wies"
        )
        self.placement = Placement.objects.create(colleague=self.colleague, service=self.filled_service, source="wies")
        self.vacant_service = Service.objects.create(
            description="Vacant", assignment=self.assignment, skill=self.skill_java, source="wies", status="OPEN"
        )
        self.member_url = reverse("assignment-member-edit", args=[self.assignment.public_id])

    def _post_member(self, row):
        """POST one team-member row to the member-edit endpoint the way the
        child sheet does: a single, prefix-free ``ServiceForm``."""
        data = {
            **row,
            "terug_url": f"/?opdracht={self.assignment.public_id}",
        }
        return self.client.post(self.member_url, data)

    def _member_row(self, *, service, skill, description, is_filled=False, colleague=None):
        row = {
            "service_public_id": str(service.public_id),
            "skill": str(skill.public_id),
            "description": description,
            "is_filled": "ingevuld" if is_filled else "aanvraag",
            "has_custom_period": "on",  # inherit assignment period
        }
        if is_filled and colleague is not None:
            row["colleague"] = str(colleague.public_id)
            placement = Placement.objects.filter(service=service).first()
            if placement is not None:
                row["placement_public_id"] = str(placement.public_id)
        return row

    def test_services_post_emits_event_on_change(self):
        # Fill the previously vacant Java service with the colleague — the
        # diff should list one "Gewijzigd" line for it.
        resp = self._post_member(
            self._member_row(
                service=self.vacant_service,
                skill=self.skill_java,
                description="Vacant",
                is_filled=True,
                colleague=self.colleague,
            )
        )
        assert resp.status_code == 204
        events = list(Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update"))
        assert len(events) == 1
        event = events[0]
        assert event.context["field_name"] == "services"
        assert event.context["field_label"] == "Team"
        # Event stores only the rows that changed (delta), not full
        # team state. Here only the vacant row flipped — one change.
        changes = event.context["changes"]
        assert len(changes) == 1
        change = changes[0]
        assert change["old"]["id"] == self.vacant_service.id
        assert change["old"]["colleague_name"] is None
        assert change["new"]["colleague_name"] == self.colleague.name

    def test_services_post_no_change_no_event(self):
        # Re-post the filled row exactly as it stands: no field changes, so
        # the before/after team state is identical and no event is emitted.
        resp = self._post_member(
            self._member_row(
                service=self.filled_service,
                skill=self.skill_python,
                description="Filled",
                is_filled=True,
                colleague=self.colleague,
            )
        )
        assert resp.status_code == 204
        assert not Event.objects.filter(object_type="Assignment", object_id=self.assignment.id).exists()

    def test_member_post_filled_without_colleague_blocks(self):
        """Status "Geplaatste consultant" without a consultant is rejected at the
        Consultant field, instead of silently saving as a vacancy."""
        response = self._post_member(
            self._member_row(
                service=self.vacant_service,
                skill=self.skill_java,
                description="Vacant",
                is_filled=True,  # ingevuld, but no colleague passed
            )
        )
        assert response.status_code == 200
        self.assertContains(response, 'error-message="error-colleague-1"')
        self.assertContains(
            response, '<nldd-form-field-error-text id="error-colleague-1" invalid>Selecteer een consultant.'
        )
        # The silent save did not happen: no placement, no colleague.
        assert not Placement.objects.filter(service=self.vacant_service).exists()

    def test_services_post_emits_event_on_period_change(self):
        """A period-only edit still emits a team audit event (#393)."""
        # Filled row: drop the inherit checkbox and give a custom period.
        resp = self._post_member(
            {
                "service_public_id": str(self.filled_service.public_id),
                "skill": str(self.skill_python.public_id),
                "description": "Filled",
                "is_filled": "ingevuld",
                "colleague": str(self.colleague.public_id),
                "placement_public_id": str(self.placement.public_id),
                "placement_start_date": "2026-01-01",
                "placement_end_date": "2026-06-30",
            }
        )
        assert resp.status_code == 204
        self.placement.refresh_from_db()
        assert self.placement.specific_start_date is not None
        events = list(Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update"))
        assert len(events) == 1
        changes = events[0].context["changes"]
        assert len(changes) == 1
        assert changes[0]["old"]["id"] == self.filled_service.id

    def test_switch_filled_to_aanvraag_removes_placement(self):
        """Flipping a filled service to "aanvraag" must free the placement,
        even when the (hidden) consultant select still posts its value —
        is_filled is authoritative, not the lingering colleague."""
        # Filled row switched to aanvraag, but colleague + placement_public_id
        # still posted (JS only hides the field; this is the bug case).
        resp = self._post_member(
            {
                "service_public_id": str(self.filled_service.public_id),
                "skill": str(self.skill_python.public_id),
                "description": "Filled",
                "is_filled": "aanvraag",
                "has_custom_period": "on",
                "colleague": str(self.colleague.public_id),
                "placement_public_id": str(self.placement.public_id),
            }
        )
        assert resp.status_code == 204
        # Placement gone, service kept as an open aanvraag.
        assert not Placement.objects.filter(id=self.placement.id).exists()
        self.filled_service.refresh_from_db()
        assert self.filled_service.status == "OPEN"
        assert not self.filled_service.placements.exists()

    def test_new_skill_creates_and_links_skill(self):
        """Posting the __new__ sentinel with a name must create a Skill and
        link it to the service. member_form.js sends skill=__new__ +
        new_skill_name for a role typed by the user that is not an existing one."""
        assert not Skill.objects.filter(name="Rust").exists()
        resp = self._post_member(
            {
                "service_public_id": str(self.vacant_service.public_id),
                "skill": "__new__",
                "new_skill_name": "Rust",
                "description": "Vacant",
                "is_filled": "aanvraag",
                "has_custom_period": "on",
            }
        )
        assert resp.status_code == 204
        new_skill = Skill.objects.get(name="Rust")
        self.vacant_service.refresh_from_db()
        assert self.vacant_service.skill_id == new_skill.id

    def test_new_skill_name_matching_existing_reuses_it(self):
        """__new__ with a name that already exists must reuse the existing
        Skill (get_or_create by unique name), not create a duplicate."""
        before = Skill.objects.count()
        resp = self._post_member(
            {
                "service_public_id": str(self.vacant_service.public_id),
                "skill": "__new__",
                "new_skill_name": "Python",  # already exists (self.skill_python)
                "description": "Vacant",
                "is_filled": "aanvraag",
                "has_custom_period": "on",
            }
        )
        assert resp.status_code == 204
        assert Skill.objects.count() == before
        self.vacant_service.refresh_from_db()
        assert self.vacant_service.skill_id == self.skill_python.id

    def test_member_sheet_renders_public_id_hidden_inputs(self):
        """The member-edit sheet must render the hidden ``service_public_id``
        and ``placement_public_id`` inputs so the single-row POST
        round-trips the public_ids back to save_service_from_form, which
        updates that Service/Placement in place. Without them the save would
        create a new row instead of editing the existing one.

        Each member opens in its own single-row sheet (``?teamlid=<public_id>``),
        so the ids are asserted per row instead of across one combined formset."""

        def hidden_value(content, field_name):
            m = re.search(
                rf'<input type="hidden"\s+name="{re.escape(field_name)}"\s+value="([^"]*)"',
                content,
            )
            return m.group(1) if m else None

        vacant = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid={self.vacant_service.public_id}")
        assert vacant.status_code == 200
        vacant_content = vacant.content.decode()
        assert hidden_value(vacant_content, "service_public_id") == str(self.vacant_service.public_id)
        assert hidden_value(vacant_content, "placement_public_id") == ""

        filled = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid={self.filled_service.public_id}")
        assert filled.status_code == 200
        filled_content = filled.content.decode()
        assert hidden_value(filled_content, "service_public_id") == str(self.filled_service.public_id)
        assert hidden_value(filled_content, "placement_public_id") == str(self.placement.public_id)

    def test_member_sheet_offers_new_role_option_with_hidden_input(self):
        """The Rol combo must offer the discrete "+ Nieuwe rol" option
        (value ``__new__``) rather than free-typing, and the name field it
        reveals must render ``hidden`` for a row whose skill is an existing
        role, so member_form.js only has to unhide it on selection."""
        resp = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid={self.filled_service.public_id}")
        assert resp.status_code == 200
        content = resp.content.decode()
        # The discrete option is a real menu item; the combo is not allow-custom.
        assert 'value="__new__"' in content
        assert "allow-custom" not in content
        # This row has an existing skill, so the new-role name field starts hidden.
        m = re.search(r"<div data-new-skill-field\s*([^>]*)>", content)
        assert m is not None
        assert "hidden" in m.group(1)

    def test_description_only_edit_preserves_pks_and_emits_one_diff_line(self):
        """Editing only the description must update the existing Service
        in place (same PK, Placement kept with its metadata) and the
        audit event must list exactly one Toelichting line."""
        original_service_id = self.filled_service.id
        original_placement_id = self.placement.id
        resp = self._post_member(
            self._member_row(
                service=self.filled_service,
                skill=self.skill_python,
                description="New description",
                is_filled=True,
                colleague=self.colleague,
            )
        )
        assert resp.status_code == 204

        self.filled_service.refresh_from_db()
        self.placement.refresh_from_db()
        assert self.filled_service.id == original_service_id
        assert self.filled_service.description == "New description"
        assert self.placement.id == original_placement_id

        events = list(Event.objects.filter(object_type="Assignment", object_id=self.assignment.id, action="update"))
        assert len(events) == 1
        changes = events[0].context["changes"]
        assert len(changes) == 1
        assert changes[0]["old"]["id"] == self.filled_service.id
        assert changes[0]["old"]["description"] == "Filled"
        assert changes[0]["new"]["description"] == "New description"

    def test_remove_member_deletes_only_that_service(self):
        """Removing a team member (its own "Verwijderen" route) deletes that
        row's service and leaves the rest of the team untouched.

        The old formset-gap deletion path is gone: deletion now has a
        dedicated ``assignment-member-delete`` endpoint that deletes that one
        service directly (``service.delete()``), so the "blank errored form"
        bug the original test guarded against can no longer occur."""
        original_vacant_id = self.vacant_service.id
        delete_url = reverse(
            "assignment-member-delete", args=[self.assignment.public_id, self.vacant_service.public_id]
        )
        resp = self.client.post(delete_url, {"terug_url": f"/?opdracht={self.assignment.public_id}"})
        assert resp.status_code == 204
        # The removed service must actually be gone from the DB.
        assert not Service.objects.filter(id=original_vacant_id).exists()
        # And the surviving service is unchanged.
        assert Service.objects.filter(id=self.filled_service.id).exists()


class AssignmentServicesEditFormPeriodTest(TestCase):
    """Regression: opening the team editor must reflect each row's
    *effective* period — when a row's dates differ from the assignment
    period (the placement has custom dates, OR the placement inherits
    from a service that has custom dates), the "Neem opdrachtperiode
    over" checkbox must render UNCHECKED with the row's actual dates
    pre-filled. In production we see every row come up with the
    checkbox checked, hiding any custom dates.

    The form initial only looks at ``placement.period_source`` and
    treats anything ``!= PLACEMENT`` as "inherit assignment period" —
    but a placement that inherits from a service with custom dates
    still effectively has a custom period relative to the assignment.
    """

    def setUp(self):
        import datetime  # noqa: PLC0415 (import not at top level) — scoped to setUp to keep the regression test self-contained

        self.client = Client()
        self.user = User.objects.create_user(
            email="svc-period@rijksoverheid.nl",
            first_name="Svc",
            last_name="Period",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.colleague = Colleague.objects.get(user=self.user)
        # Assignment runs the full multi-year window seen in the screenshot.
        self.assignment_start = datetime.date(2025, 1, 1)
        self.assignment_end = datetime.date(2028, 12, 31)
        self.assignment = Assignment.objects.create(
            name="A",
            owner=self.colleague,
            source="wies",
            start_date=self.assignment_start,
            end_date=self.assignment_end,
        )
        self.skill = Skill.objects.create(name="Software Engineer")
        self.custom_start = datetime.date(2026, 3, 1)
        self.custom_end = datetime.date(2027, 2, 28)

        # Row A: service + placement both inherit from assignment.
        self.service_inherit = Service.objects.create(
            description="Inherits",
            assignment=self.assignment,
            skill=self.skill,
            source="wies",
            period_source=Service.ASSIGNMENT,
        )
        self.placement_inherit = Placement.objects.create(
            colleague=self.colleague,
            service=self.service_inherit,
            source="wies",
            period_source=Placement.SERVICE,
        )

        # Row B: service inherits, placement has its own custom dates.
        # ``placement.period_source = PLACEMENT``.
        self.service_for_custom_placement = Service.objects.create(
            description="Service inherits, placement custom",
            assignment=self.assignment,
            skill=self.skill,
            source="wies",
            period_source=Service.ASSIGNMENT,
        )
        self.colleague_custom_placement = Colleague.objects.create(name="Erik van Raalte", email="erik@example.test")
        self.placement_custom = Placement.objects.create(
            colleague=self.colleague_custom_placement,
            service=self.service_for_custom_placement,
            source="wies",
            period_source=Placement.PLACEMENT,
            specific_start_date=self.custom_start,
            specific_end_date=self.custom_end,
        )

        # Row C: service has custom dates, placement inherits from the
        # service. The placement's effective period therefore differs
        # from the assignment, even though ``placement.period_source =
        # SERVICE``. This is the case where the screenshot shows custom
        # dates but the checkbox renders as "inherit assignment".
        self.service_custom = Service.objects.create(
            description="Service custom, placement inherits",
            assignment=self.assignment,
            skill=self.skill,
            source="wies",
            period_source=Service.SERVICE,
            specific_start_date=self.custom_start,
            specific_end_date=self.custom_end,
        )
        self.colleague_via_service = Colleague.objects.create(name="Marcel Wansinck", email="marcel@example.test")
        self.placement_via_service = Placement.objects.create(
            colleague=self.colleague_via_service,
            service=self.service_custom,
            source="wies",
            period_source=Placement.SERVICE,
        )

        self.url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "services"])

    def test_initial_data_reflects_effective_period_per_row(self):
        """Direct check on ``_services_initial``: every row whose effective
        dates differ from the assignment must carry
        ``has_custom_period = False`` so the checkbox renders unchecked."""
        from wies.core.editables.assignment import (  # noqa: PLC0415 (import not at top level) — private helper imported here to keep its use scoped to this regression test
            _services_initial,
        )

        rows = _services_initial(self.assignment)
        by_placement = {r["placement_public_id"]: r for r in rows}

        inherit_row = by_placement[str(self.placement_inherit.public_id)]
        custom_placement_row = by_placement[str(self.placement_custom.public_id)]
        via_service_row = by_placement[str(self.placement_via_service.public_id)]

        # Sanity: the effective dates returned to the template match the
        # screenshot (assignment range vs custom range).
        assert inherit_row["placement_start_date"] == self.assignment_start
        assert inherit_row["placement_end_date"] == self.assignment_end
        assert custom_placement_row["placement_start_date"] == self.custom_start
        assert custom_placement_row["placement_end_date"] == self.custom_end
        assert via_service_row["placement_start_date"] == self.custom_start
        assert via_service_row["placement_end_date"] == self.custom_end

        # Inheriting row → checkbox checked.
        assert inherit_row["has_custom_period"] is True, (
            f"inheriting placement should render with checkbox checked, "
            f"got has_custom_period={inherit_row['has_custom_period']!r}"
        )
        # Custom placement → checkbox unchecked.
        assert custom_placement_row["has_custom_period"] is False, (
            f"placement with period_source=PLACEMENT should render with "
            f"checkbox unchecked, got "
            f"has_custom_period={custom_placement_row['has_custom_period']!r}"
        )
        # Placement inheriting a custom *service* period → checkbox must
        # be UNCHECKED, because the row's effective dates differ from
        # the assignment. This is the production bug: ``has_custom_period``
        # is True here (only the placement's own period_source is checked,
        # not the service chain).
        assert via_service_row["has_custom_period"] is False, (
            "placement with period_source=SERVICE on a service that has "
            "its own custom dates rendered as inheriting the assignment "
            "period — but its effective period differs from the assignment. "
            f"Got has_custom_period={via_service_row['has_custom_period']!r}, "
            f"effective dates "
            f"{via_service_row['placement_start_date']} to "
            f"{via_service_row['placement_end_date']} "
            f"vs assignment {self.assignment_start} to {self.assignment_end}."
        )

    def test_member_sheet_renders_period_choice_matching_effective_period(self):
        """End-to-end: opening a member's edit sheet (``?teamlid=<service-id>``)
        must render that row's period choice matching its effective period.

        Team editing moved to the per-member sheets, so each row is fetched
        via its own single-row sheet instead of one combined ?edit render.
        The old "Neem opdrachtperiode over" checkbox became a segmented
        control (``data-period-choice``) backed by a hidden
        ``has_custom_period`` input: ``value="on"`` / segment ``SERVICE`` =
        inherit the assignment period, empty / segment ``PLACEMENT`` = custom.
        The regression guarded is the same: a row whose effective dates differ
        from the assignment must NOT come up as "inherit"."""

        def period_state_for_service(service_public_id: str) -> tuple[str, str]:
            """(hidden has_custom_period value, segmented-control value) for
            the one row rendered in this member's sheet."""
            resp = self.client.get(f"/?opdracht={self.assignment.public_id}&teamlid={service_public_id}")
            assert resp.status_code == 200
            content = resp.content.decode()
            hidden = re.search(
                r'<input[^>]*name="has_custom_period"[^>]*value="([^"]*)"',
                content,
            )
            assert hidden, f"no has_custom_period input found for service {service_public_id}"
            control = re.search(
                r'<nldd-segmented-control[^>]*value="(SERVICE|PLACEMENT)"[^>]*data-period-choice', content
            )
            assert control, f"no period-choice control found for service {service_public_id}"
            return hidden.group(1), control.group(1)

        inherit_value, inherit_segment = period_state_for_service(self.service_inherit.public_id)
        custom_value, custom_segment = period_state_for_service(self.service_for_custom_placement.public_id)
        via_value, via_segment = period_state_for_service(self.service_custom.public_id)

        # Inheriting placement → "inherit assignment period" (correct today).
        assert inherit_value == "on", f"inheriting row should render as inherit, got value={inherit_value!r}"
        assert inherit_segment == "SERVICE"
        # Placement with its own custom period → "custom".
        assert custom_value == "", (
            "placement with period_source=PLACEMENT rendered as inheriting the "
            "assignment period — its custom period is being hidden."
        )
        assert custom_segment == "PLACEMENT"
        # Placement inheriting a custom service period → "custom", because its
        # effective dates differ from the assignment (the original bug).
        assert via_value == "", (
            "placement that inherits from a service with custom dates rendered "
            "as inheriting the assignment period — but its effective dates differ."
        )
        assert via_segment == "PLACEMENT"


class ServicesRenderChangeUnitTests(TestCase):
    """Pure-function checks for `_services_render_change` covering each
    branch (added / removed / skill changed / colleague filled /
    description add/remove/change)."""

    def _row(self, sid, skill_name, colleague_name=None, description="", **period):
        return {
            "id": sid,
            "skill_name": skill_name,
            "colleague_name": colleague_name,
            "description": description,
            **period,
        }

    def test_added(self):
        change = {"old": None, "new": self._row(2, "Java", None)}
        assert _services_render_change(change) == {"text": "Java (open) toegevoegd"}

    def test_removed(self):
        change = {"old": self._row(2, "Java", None), "new": None}
        assert _services_render_change(change) == {"text": "Java (open) verwijderd"}

    def test_colleague_filled(self):
        change = {"old": self._row(1, "Java", None), "new": self._row(1, "Java", "Anna")}
        assert _services_render_change(change) == {"text": "Java (open) naar Java (Anna) gewijzigd"}

    def test_skill_changed(self):
        change = {"old": self._row(1, "Python", "Jan"), "new": self._row(1, "TypeScript", "Jan")}
        assert _services_render_change(change) == {
            "text": "Python (Jan) naar TypeScript (Jan) gewijzigd",
        }

    def test_description_changed(self):
        change = {
            "old": self._row(1, "Python", "Jan", description="oud"),
            "new": self._row(1, "Python", "Jan", description="nieuw"),
        }
        assert _services_render_change(change) == {
            "text": 'de toelichting voor Python (Jan) van "oud" naar "nieuw" gewijzigd',
        }

    def test_description_added_from_empty(self):
        change = {
            "old": self._row(1, "Python", "Jan", description=""),
            "new": self._row(1, "Python", "Jan", description="nieuw"),
        }
        assert _services_render_change(change) == {
            "text": 'de toelichting "nieuw" voor Python (Jan) toegevoegd',
        }

    def test_description_removed_to_empty(self):
        change = {
            "old": self._row(1, "Python", "Jan", description="oud"),
            "new": self._row(1, "Python", "Jan", description=""),
        }
        assert _services_render_change(change) == {
            "text": 'de toelichting "oud" voor Python (Jan) verwijderd',
        }

    def test_period_custom_set(self):
        # Switching from inherited to a custom period (#393).
        # `has_custom_period` is inverted: True == inherits, False == own.
        # Inherited still shows the dates so the old period stays visible.
        change = {
            "old": self._row(
                1, "Python", "Jan", has_custom_period=True, start_date="2026-01-01", end_date="2026-06-30"
            ),
            "new": self._row(
                1, "Python", "Jan", has_custom_period=False, start_date="2026-01-01", end_date="2026-06-30"
            ),
        }
        assert _services_render_change(change) == {
            "text": (
                "de periode van Python (Jan) van 01-01-2026 t/m 30-06-2026"
                " (volgt opdracht) naar 01-01-2026 t/m 30-06-2026 gewijzigd"
            ),
        }

    def test_period_dates_changed(self):
        change = {
            "old": self._row(
                1, "Python", "Jan", has_custom_period=False, start_date="2026-01-01", end_date="2026-06-30"
            ),
            "new": self._row(
                1, "Python", "Jan", has_custom_period=False, start_date="2026-02-01", end_date="2026-06-30"
            ),
        }
        assert _services_render_change(change) == {
            "text": (
                "de periode van Python (Jan) van 01-01-2026 t/m 30-06-2026 naar 01-02-2026 t/m 30-06-2026 gewijzigd"
            ),
        }


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
        return reverse("inline-edit", args=["service", service.public_id, "description"])

    def test_placed_consultant_edits_own_description(self):
        self.client.force_login(self.placed_user)
        resp = post_inline_edit(self.client, self._desc_url(self.my_service), {"description": "Nieuwe rol"})
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
        url = reverse("inline-edit", args=["service", self.my_service.public_id, "skill"])
        new_skill = Skill.objects.create(name="Andere rol")
        resp = self.client.post(url, {"skill": new_skill.public_id})
        assert resp.status_code == 200
        self.assertContains(resp, "geen rechten")
        self.my_service.refresh_from_db()
        assert self.my_service.skill_id != new_skill.id

    def test_owner_can_use_inline_pencil(self):
        """BM can edit descriptions inline, consistent with skill and period."""
        self.client.force_login(self.owner_user)
        resp = post_inline_edit(self.client, self._desc_url(self.my_service), {"description": "BM past aan"})
        assert resp.status_code == 200
        self.assertNotContains(resp, "geen rechten")
        self.my_service.refresh_from_db()
        assert self.my_service.description == "BM past aan"


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
            "org-0-organization": self.org_a.public_id,
            "org-0-role": "PRIMARY",
            "org-1-organization": self.org_b.public_id,
            "org-1-role": "INVOLVED",
        }
        parsed = w.value_from_datadict(data, {}, "organizations")
        assert parsed == [
            {"organization": self.org_a.public_id, "role": "PRIMARY"},
            {"organization": self.org_b.public_id, "role": "INVOLVED"},
        ]

    def test_widget_ignores_missing_total_forms(self):
        assert OrgPickerWidget().value_from_datadict({}, {}, "organizations") == []

    def test_field_resolves_public_ids_to_instances(self):
        f = OrganizationsField(required=True)
        cleaned = f.clean(
            [
                {"organization": self.org_a.public_id, "role": "PRIMARY"},
                {"organization": self.org_b.public_id, "role": "INVOLVED"},
            ]
        )
        assert cleaned[0]["organization"] == self.org_a
        assert cleaned[0]["role"] == "PRIMARY"
        assert cleaned[1]["organization"] == self.org_b

    def test_field_rejects_pk_posing_as_public_id(self):
        # The client only ever sees public_ids; a raw pk must not resolve.
        f = OrganizationsField(required=True)
        with self.assertRaises(ValidationError):  # noqa: PT027
            f.clean([{"organization": str(self.org_a.id), "role": "PRIMARY"}])

    def test_field_requires_exactly_one_primary(self):
        f = OrganizationsField(required=True)
        # Zero primaries among selected orgs.
        with self.assertRaises(ValidationError) as exc:  # noqa: PT027
            f.clean(
                [
                    {"organization": self.org_a.public_id, "role": "INVOLVED"},
                    {"organization": self.org_b.public_id, "role": "INVOLVED"},
                ]
            )
        assert "primaire" in str(exc.exception).lower()

    def test_field_required_empty_raises(self):
        f = OrganizationsField(required=True)
        with self.assertRaises(ValidationError):  # noqa: PT027
            f.clean([])

    def test_field_rejects_unknown_public_id(self):
        f = OrganizationsField(required=True)
        with self.assertRaises(ValidationError):  # noqa: PT027
            f.clean([{"organization": uuid.uuid4(), "role": "PRIMARY"}])


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
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "organizations"])
        post_inline_edit(
            self.client,
            url,
            {
                "org-TOTAL_FORMS": "2",
                "org-0-organization": self.org_a.public_id,
                "org-0-role": "PRIMARY",
                "org-1-organization": self.org_b.public_id,
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
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "organizations"])
        resp = self.client.post(
            url,
            {
                "org-TOTAL_FORMS": "2",
                "org-0-organization": self.org_a.public_id,
                "org-0-role": "INVOLVED",
                "org-1-organization": self.org_b.public_id,
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
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "organizations"])
        resp = self.client.get(url + "?edit=true")
        assert resp.status_code == 200
        # Hidden inputs generated by OrgPickerWidget carry the two org
        # public_ids and their roles from the initial payload.
        self.assertContains(resp, f'data-org-id="{self.org_a.public_id}"')
        self.assertContains(resp, f'data-org-id="{self.org_b.public_id}"')
        self.assertContains(resp, 'data-org-role="PRIMARY"')
        self.assertContains(resp, 'data-org-role="INVOLVED"')

    def test_display_renders_breadcrumb_ancestors(self):
        """Regression for issue #331 — the editables refactor dropped the
        ancestor chain; it must render as clickable links with separators
        above the org label itself."""
        ministry = OrganizationUnit.objects.create(name="Ministerie X", label="MinX")
        directorate = OrganizationUnit.objects.create(name="Directie Y", label="DirY", parent=ministry)
        team = OrganizationUnit.objects.create(name="Team Z", label="TeamZ", parent=directorate)
        AssignmentOrganizationUnit.objects.create(assignment=self.assignment, organization=team, role="PRIMARY")
        url = reverse("inline-edit", args=["assignment", self.assignment.public_id, "organizations"])
        resp = self.client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert content.index("MinX") < content.index("DirY") < content.index("TeamZ")
        self.assertContains(resp, "<nldd-link")
        self.assertContains(resp, "\u203a")


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
            args=["colleague", self.colleague.public_id, f"labels_{self.expertise.id}"],
        )
        resp = post_inline_edit(self.client, url, {"labels": [self.label_cloud.public_id]})
        assert resp.status_code == 200
        current = set(self.colleague.labels.values_list("pk", flat=True))
        assert current == {self.label_cloud.id, self.label_weerbaar.id}

    def test_get_display_shows_current_category_labels(self):
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.public_id, f"labels_{self.expertise.id}"],
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
            args=["colleague", self.colleague.public_id, "labels_999999"],
        )
        resp = self.client.get(url)
        assert resp.status_code == 404

    def test_non_integer_suffix_returns_404(self):
        url = reverse(
            "inline-edit",
            args=["colleague", self.colleague.public_id, "labels_abc"],
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
        url = reverse("inline-edit", args=["user", self.user.public_id, "first_name"])
        resp = post_inline_edit(self.client, url, {"first_name": "Nieuwe"})
        assert resp.status_code == 200
        colleague = Colleague.objects.get(user=self.user)
        # Name reflects combined user.first_name + user.last_name.
        assert colleague.name == "Nieuwe Naam"

    def test_subsequent_last_name_save_updates_colleague_name(self):
        url_last = reverse("inline-edit", args=["user", self.user.public_id, "last_name"])
        post_inline_edit(self.client, url_last, {"last_name": "Anders"})
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
