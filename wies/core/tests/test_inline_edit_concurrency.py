import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wies.core.models import Assignment, Colleague, Service, Skill

User = get_user_model()


class InlineEditConcurrencyTests(TestCase):
    """An inline edit based on a stale view of a field must not silently
    overwrite a change someone else made in the meantime. The save is rejected
    with a 'reload' message and the concurrent value is preserved."""

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
        self.assertContains(response, "Herlaad de pagina")
        self.assignment.refresh_from_db()
        assert self.assignment.name == "Concurrent Name"

    def test_fresh_edit_still_saves(self):
        token = self._token_from_form()

        response = self.client.post(self._url(), {"name": "New Name", "_concurrency_token": token})

        assert response.status_code == 200
        self.assignment.refresh_from_db()
        assert self.assignment.name == "New Name"


class InlineEditCollectionConcurrencyTokenTests(TestCase):
    """The team (services) edit form embeds a concurrency token that reflects
    the current team, so a save based on a stale team is caught by the same
    check as a scalar field (the audit flagged this collection save as the
    worst case for lost updates)."""

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
