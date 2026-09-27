"""Tests for the staff-gated KB publish trigger on the Database admin page.

Publishing the knowledge base was folded into ``beheer/database/`` (it used to
have its own ``beheer/kennisbank/`` page). The action shares the page's staff gate
and its "Recente taken" list.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Task
from wies.core.tests.role_helpers import STAFF_EMAIL, make_staff_user
from wies.kb.views import KB_PUBLISH_COMMAND

User = get_user_model()


class DatabasePublishButtonTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("staff-database"), follow=False)
        assert response.status_code == 302

    def test_non_staff_get_is_denied(self):
        user = User.objects.create_user(email="reader@rijksoverheid.nl", first_name="R", last_name="R")
        self.client.force_login(user)
        response = self.client.get(reverse("staff-database"), follow=False)
        # staff_required redirects to the no-access page
        assert response.status_code == 302

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_sees_publish_button(self):
        self.client.force_login(make_staff_user())
        response = self.client.get(reverse("staff-database"))
        assert response.status_code == 200
        assert b'value="publish_knowledge_base"' in response.content


class DatabasePublishTriggerTest(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_staff_publish_enqueues_task(self):
        self.client.force_login(make_staff_user())
        response = self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"})
        assert response.status_code == 302
        assert Task.objects.filter(command=KB_PUBLISH_COMMAND, status="pending").count() == 1

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_htmx_publish_returns_task_list_partial(self):
        self.client.force_login(make_staff_user())
        response = self.client.post(
            reverse("staff-database"),
            {"action": "publish_knowledge_base"},
            headers={"hx-request": "true"},
        )
        assert response.status_code == 200
        # The shared task list is swapped in, not a KB-specific partial.
        assert "Recente taken" in response.content.decode()
        assert Task.objects.filter(command=KB_PUBLISH_COMMAND).count() == 1

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_second_publish_while_active_does_not_enqueue(self):
        self.client.force_login(make_staff_user())
        self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"})
        self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"})
        assert Task.objects.filter(command=KB_PUBLISH_COMMAND).count() == 1

    def test_non_staff_publish_is_denied(self):
        user = User.objects.create_user(email="reader@rijksoverheid.nl", first_name="R", last_name="R")
        self.client.force_login(user)
        response = self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"}, follow=False)
        assert response.status_code == 302  # bounced by staff_required, not executed
        assert Task.objects.filter(command=KB_PUBLISH_COMMAND).count() == 0
