"""Tests for the staff-gated KB publish trigger on the Database admin page.

Publishing the knowledge base was folded into ``beheer/database/`` (it used to
have its own ``beheer/kennisbank/`` page). The action shares the page's staff gate
and its "Recente taken" list.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wies.core.models import Task
from wies.core.services.tasks import get_task_label
from wies.core.tests.role_helpers import STAFF_EMAIL, make_staff_user
from wies.kb.publish import KB_PUBLISH_COMMAND

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

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_htmx_swap_carries_the_flash_message(self):
        # The swap replaces the task list, not base.html, so the banner has to ride
        # along out-of-band; otherwise the message is consumed without being shown
        # and resurfaces on the next full page load.
        self.client.force_login(make_staff_user())
        response = self.client.post(
            reverse("staff-database"),
            {"action": "publish_knowledge_base"},
            headers={"hx-request": "true"},
        )
        body = response.content.decode()
        assert 'hx-swap-oob="outerHTML"' in body
        assert "Publicatie is gestart" in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_htmx_swap_shows_the_already_active_error(self):
        self.client.force_login(make_staff_user())
        self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"})
        response = self.client.post(
            reverse("staff-database"),
            {"action": "publish_knowledge_base"},
            headers={"hx-request": "true"},
        )
        assert "Er is al een publicatietaak actief" in response.content.decode()


class TaskListRenderingTest(TestCase):
    """The shared task list is rendered for mixed task types."""

    def setUp(self):
        self.client = Client()

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_task_is_named_by_its_label_not_its_status(self):
        self.client.force_login(make_staff_user())
        Task.objects.create(
            command=KB_PUBLISH_COMMAND, label="ODI startpagina publiceren", status="pending", timeout_minutes=15
        )
        body = self.client.get(reverse("staff-database")).content.decode()
        assert 'text="ODI startpagina publiceren"' in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_publish_result_reports_release_and_file_count(self):
        self.client.force_login(make_staff_user())
        Task.objects.create(
            command=KB_PUBLISH_COMMAND,
            label="ODI startpagina publiceren",
            status="completed",
            timeout_minutes=15,
            result={"release": "v1.2.3", "objects": 42},
        )
        body = self.client.get(reverse("staff-database")).content.decode()
        assert "Release v1.2.3, 42 bestanden gepubliceerd" in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_publish_result_without_a_release_tag_omits_the_word_release(self):
        # An untagged artifact left a dangling "Release 7 bestanden gepubliceerd".
        self.client.force_login(make_staff_user())
        Task.objects.create(
            command=KB_PUBLISH_COMMAND,
            label="ODI startpagina publiceren",
            status="completed",
            timeout_minutes=15,
            result={"release": "", "objects": 7},
        )
        body = self.client.get(reverse("staff-database")).content.decode()
        assert "7 bestanden gepubliceerd" in body
        assert "Release 7" not in body

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_failed_publish_shows_the_error(self):
        self.client.force_login(make_staff_user())
        Task.objects.create(
            command=KB_PUBLISH_COMMAND,
            label="ODI startpagina publiceren",
            status="failed",
            timeout_minutes=15,
            error_message="Could not fetch latest release (404)",
        )
        body = self.client.get(reverse("staff-database")).content.decode()
        assert "Could not fetch latest release (404)" in body

    def test_non_staff_publish_is_denied(self):
        user = User.objects.create_user(email="reader@rijksoverheid.nl", first_name="R", last_name="R")
        self.client.force_login(user)
        response = self.client.post(reverse("staff-database"), {"action": "publish_knowledge_base"}, follow=False)
        assert response.status_code == 302  # bounced by staff_required, not executed
        assert Task.objects.filter(command=KB_PUBLISH_COMMAND).count() == 0


class TaskLabelTest(TestCase):
    """``create_task`` snapshots the label a TaskCommand declares for itself."""

    def test_label_comes_from_the_command_class(self):
        assert get_task_label(KB_PUBLISH_COMMAND) == "ODI startpagina publiceren"
        assert get_task_label("sync_organizations") == "Organisaties synchroniseren"

    def test_unknown_command_falls_back_to_its_name(self):
        # Rows written before this field existed, and commands without a label,
        # still have to render something usable in the list.
        assert get_task_label("no_such_command") == "no_such_command"

    @override_settings(STAFF_EMAILS=[STAFF_EMAIL])
    def test_unlabelled_task_renders_its_command(self):
        self.client = Client()
        self.client.force_login(make_staff_user())
        Task.objects.create(command="sync_organizations", label="", status="pending", timeout_minutes=5)
        body = self.client.get(reverse("staff-database")).content.decode()
        assert 'text="sync_organizations"' in body
