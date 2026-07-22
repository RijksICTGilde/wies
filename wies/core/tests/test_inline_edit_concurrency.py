import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from wies.core.editables import AssignmentEditables
from wies.core.inline_edit.base import EditableCollection
from wies.core.models import Assignment, Colleague, Placement, Service, Skill
from wies.core.tests.inline_edit_helpers import post_inline_edit
from wies.core.views import _concurrency_token

User = get_user_model()


class InlineEditConcurrencyTests(TestCase):
    """An inline edit based on a stale view of a field must not silently
    overwrite a change someone else made in the meantime. The save comes back
    as the bound form with a warning, and the concurrent value is preserved
    until the user confirms."""

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="owner@rijksoverheid.nl", first_name="O", last_name="w")
        self.owner = Colleague.objects.create(
            user=self.owner_user, name="Owner", email="owner@rijksoverheid.nl", source="wies"
        )
        self.assignment = Assignment.objects.create(name="Original Name", owner=self.owner, source="wies")
        self.client.force_login(self.owner_user)

    def _url(self):
        return reverse("inline-edit", args=["assignment", self.assignment.id, "name"])

    def _token_from_form(self):
        response = self.client.get(self._url(), {"edit": "true"})
        match = re.search(r'name="_concurrency_token"\s+value="([^"]*)"', response.content.decode())
        assert match, "the edit form must embed a _concurrency_token hidden field"
        return match.group(1)

    def test_stale_edit_is_rejected_and_preserves_concurrent_change(self):
        token = self._token_from_form()

        # Someone else changes the name between render and save.
        Assignment.objects.filter(pk=self.assignment.pk).update(name="Concurrent Name")

        response = self.client.post(self._url(), {"name": "My Stale Name", "_concurrency_token": token})

        assert response.status_code == 200
        self.assertContains(response, "door iemand anders gewijzigd")
        # The form is swapped in by HTMX; the live region is what announces the
        # warning to a screen reader.
        self.assertContains(response, 'role="alert"')
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Concurrent Name"

    def test_conflict_rerenders_form_with_fresh_token_and_keeps_input(self):
        token = self._token_from_form()

        Assignment.objects.filter(pk=self.assignment.pk).update(name="Concurrent Name")

        response = self.client.post(self._url(), {"name": "My Stale Name", "_concurrency_token": token})

        # The form comes back (not the display), still holding the submitted
        # value, with a token matching the new state — Opslaan saves anyway.
        content = response.content.decode()
        match = re.search(r'name="_concurrency_token"\s+value="([^"]*)"', content)
        assert match, "the re-rendered form must embed a fresh _concurrency_token"
        assert match.group(1) != token
        assert "My Stale Name" in content

        response = self.client.post(self._url(), {"name": "My Stale Name", "_concurrency_token": match.group(1)})

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "My Stale Name"

    def test_fresh_edit_still_saves(self):
        token = self._token_from_form()

        response = self.client.post(self._url(), {"name": "New Name", "_concurrency_token": token})

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "New Name"


class InlineEditCollectionConcurrencyTokenTests(TestCase):
    """The team (services) edit form embeds a concurrency token that reflects
    the current team, so a save based on a stale team is caught by the same
    check as a scalar field. This save rewrites every row at once, so an
    undetected conflict loses the most data."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="svc@rijksoverheid.nl", first_name="S", last_name="v", is_superuser=True, is_staff=True
        )
        self.client.force_login(self.user)
        self.owner = Colleague.objects.create(name="Owner", email="owner2@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="A", owner=self.owner, source="wies")
        self.service = Service.objects.create(
            description="Original", assignment=self.assignment, skill=Skill.objects.create(name="Python"), source="wies"
        )
        self.url = reverse("inline-edit", args=["assignment", self.assignment.id, "services"])

    def _token(self):
        response = self.client.get(self.url, {"edit": "true"})
        match = re.search(r'name="_concurrency_token"\s+value="([^"]*)"', response.content.decode())
        assert match, "the team edit form must embed a _concurrency_token"
        return match.group(1)

    def test_team_edit_form_embeds_token(self):
        assert self._token()

    def test_token_changes_when_team_changes(self):
        before = self._token()

        Service.objects.filter(pk=self.service.pk).update(description="Changed by someone else")

        assert self._token() != before

    def test_stale_team_save_rerenders_form_with_alert(self):
        token = self._token()

        Service.objects.filter(pk=self.service.pk).update(description="Changed by someone else")

        data = {
            "service-TOTAL_FORMS": "1",
            "service-INITIAL_FORMS": "1",
            "service-MIN_NUM_FORMS": "1",
            "service-MAX_NUM_FORMS": "1000",
            "service-0-id": str(self.service.id),
            "service-0-skill": str(self.service.skill_id),
            "service-0-description": "My edit",
            "service-0-is_filled": "aanvraag",
            "service-0-has_custom_period": "on",
            "_concurrency_token": token,
        }
        response = self.client.post(self.url, data)

        assert response.status_code == 200
        self.assertContains(response, "door iemand anders gewijzigd")
        self.service.refresh_from_db()
        assert self.service.description == "Changed by someone else"


class InlineEditGroupCustomTemplateConcurrencyTests(TestCase):
    """A group with its own ``form_template`` must be protected too.

    ``PlacementEditables.period`` supplies a custom body, which form.html wraps.
    A body that shipped its own form element would carry no ``_concurrency_token``
    and the check would skip silently, so the token must survive that indirection.
    """

    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(email="bm@rijksoverheid.nl", first_name="B", last_name="m")
        self.owner = Colleague.objects.create(
            user=self.owner_user, name="BM", email="bm@rijksoverheid.nl", source="wies"
        )
        self.placed = Colleague.objects.create(name="Placed", email="placed@rijksoverheid.nl", source="wies")
        self.assignment = Assignment.objects.create(name="A", owner=self.owner, source="wies")
        self.service = Service.objects.create(
            description="S", assignment=self.assignment, skill=Skill.objects.create(name="Python"), source="wies"
        )
        today = timezone.now().date()
        self.placement = Placement.objects.create(
            colleague=self.placed,
            service=self.service,
            specific_start_date=today,
            specific_end_date=today + timedelta(days=30),
            period_source=Placement.PLACEMENT,
            source="wies",
        )
        self.client.force_login(self.owner_user)
        self.url = reverse("inline-edit", args=["placement", self.placement.id, "period"])

    def _token(self):
        response = self.client.get(self.url, {"edit": "true"})
        assert response.status_code == 200
        match = re.search(r'name="_concurrency_token"\s+value="([^"]*)"', response.content.decode())
        assert match, "the custom period form must embed a _concurrency_token"
        return match.group(1)

    def test_custom_template_form_embeds_token(self):
        assert self._token()

    def test_stale_period_save_is_caught(self):
        token = self._token()
        today = timezone.now().date()
        concurrent_end = today + timedelta(days=90)
        Placement.objects.filter(pk=self.placement.pk).update(specific_end_date=concurrent_end)

        response = self.client.post(
            self.url,
            {
                "period_source": Placement.PLACEMENT,
                "specific_start_date": today.isoformat(),
                "specific_end_date": (today + timedelta(days=60)).isoformat(),
                "_concurrency_token": token,
            },
        )

        assert response.status_code == 200
        self.assertContains(response, "door iemand anders gewijzigd")
        self.placement.refresh_from_db()
        assert self.placement.specific_end_date == concurrent_end


class ConcurrencyTokenConfigurationTests(TestCase):
    """A collection without an ``audit_state`` has no state to hash, so every
    token would be the same constant and no conflict could ever be detected.
    That must fail loudly at first render rather than pass as "no conflict"."""

    def test_collection_without_audit_state_is_rejected(self):
        owner = Colleague.objects.create(name="O", email="o@rijksoverheid.nl", source="wies")
        assignment = Assignment.objects.create(name="A", owner=owner, source="wies")
        spec = EditableCollection(
            label="Zonder audit_state",
            formset_factory=lambda **kwargs: None,
            initial=lambda obj: [],
            save=lambda obj, formset: None,
        )
        spec.name = "stateless"

        with pytest.raises(ImproperlyConfigured):
            _concurrency_token(AssignmentEditables, spec, assignment)


class TokenlessPostTests(TestCase):
    """A POST without a token cannot be checked for staleness, so it counts as
    a conflict rather than saving unverified. Every form this endpoint renders
    carries a token, so reaching this means the POST was not built on one; the
    warning log makes such a caller visible."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="owner3@rijksoverheid.nl", first_name="O", last_name="w")
        self.owner = Colleague.objects.create(
            user=self.user, name="Owner", email="owner3@rijksoverheid.nl", source="wies"
        )
        self.assignment = Assignment.objects.create(name="Original", owner=self.owner, source="wies")
        self.client.force_login(self.user)
        self.url = reverse("inline-edit", args=["assignment", self.assignment.id, "name"])

    def test_tokenless_post_does_not_save_and_warns(self):
        with self.assertLogs("wies.core.views", level="WARNING") as logs:
            response = self.client.post(self.url, {"name": "No Token"})

        assert response.status_code == 200
        self.assertContains(response, "door iemand anders gewijzigd")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Original"
        assert "without a concurrency token" in "\n".join(logs.output)

    def test_resubmitting_the_returned_form_saves(self):
        """The conflict response carries a fresh token, so the retry goes through
        — a caller that omits the token is slowed by one round-trip, not blocked."""
        self.client.post(self.url, {"name": "No Token"})

        response = post_inline_edit(self.client, self.url, {"name": "No Token"})

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "No Token"
