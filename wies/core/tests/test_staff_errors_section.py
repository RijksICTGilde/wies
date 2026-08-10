"""Tests for the errors section on the statistieken page."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from config.jinja2 import datetime_nl
from wies.core.models import ErrorEvent
from wies.core.views import ERRORS_PER_PAGE

User = get_user_model()

STAFF_EMAIL = "staff@rijksoverheid.nl"

ERROR_TABLE_URL = "/beheer/statistieken/foutmeldingen/"


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class StaffErrorsSectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email=STAFF_EMAIL, first_name="Staff", last_name="User")
        self.client.force_login(self.staff_user)

    def test_dashboard_renders_error_table_inline(self):
        # The table renders with the page (no lazy-load flash); the container id
        # stays because pagination swaps into it.
        ErrorEvent.objects.create(
            level="ERROR", logger_name="django.request", message="Kapot", exception_type="ValueError"
        )

        response = self.client.get("/beheer/statistieken/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Recente foutmeldingen" in body
        assert 'id="error_table_container"' in body
        assert "Foutmeldingen laden" not in body  # no placeholder
        assert "ValueError" in body  # the error itself is already on the page

    def test_error_table_shows_recent_errors(self):
        ErrorEvent.objects.create(level="ERROR", logger_name="django.request", message="Kapot op de detailpagina")

        response = self.client.get(ERROR_TABLE_URL)

        assert response.status_code == 200
        assert "Kapot op de detailpagina" in response.content.decode()

    def test_table_shows_exception_type_not_log_message(self):
        ErrorEvent.objects.create(
            level="ERROR",
            logger_name="django.request",
            message="Internal Server Error: /opdrachten/25/verwijderen/",
            exception_type="TypeError",
            exception_message='can only concatenate str (not "int") to str',
        )

        response = self.client.get(ERROR_TABLE_URL)

        body = response.content.decode()
        assert "TypeError" in body
        assert "Internal Server Error" not in body

    def test_table_falls_back_to_message_without_exception(self):
        # Task failures have no exception type; show the log message instead.
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Task 5 failed: timeout")

        response = self.client.get(ERROR_TABLE_URL)

        assert "Task 5 failed: timeout" in response.content.decode()

    def test_error_table_empty_state(self):
        response = self.client.get(ERROR_TABLE_URL)

        assert response.status_code == 200
        assert "Geen foutmeldingen." in response.content.decode()

    def test_pagination_controls_appear_with_multiple_pages(self):
        for i in range(ERRORS_PER_PAGE + 5):
            ErrorEvent.objects.create(level="ERROR", logger_name="wies", message=f"Fout {i}")

        response = self.client.get(ERROR_TABLE_URL)

        assert response.status_code == 200
        body = response.content.decode()
        assert "Pagina 1 van 2" in body
        assert "Volgende" in body

    def test_no_pagination_controls_on_single_page(self):
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Enige fout")

        response = self.client.get(ERROR_TABLE_URL)

        assert "Pagina" not in response.content.decode()

    def test_second_page_returns_remaining_errors(self):
        for i in range(ERRORS_PER_PAGE + 5):
            ErrorEvent.objects.create(level="ERROR", logger_name="wies", message=f"Fout {i:02d}")

        response = self.client.get(f"{ERROR_TABLE_URL}?pagina=2")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Pagina 2 van 2" in body
        assert "Vorige" in body

    def test_error_detail_page_shows_traceback(self):
        error = ErrorEvent.objects.create(
            level="ERROR",
            logger_name="django.request",
            message="Kapot",
            exception_type="ValueError",
            exception_message="kaboom",
            traceback="Traceback (most recent call last):\n  ValueError: kaboom",
        )

        response = self.client.get(f"/beheer/statistieken/fout/{error.public_id}/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Foutmelding" in body  # full page heading
        assert "Terug naar statistieken" in body  # back link, not a modal
        assert "ValueError: kaboom" in body
        # Deleting lives on the page now, not in a sheet.
        assert f"/beheer/statistieken/fout/{error.public_id}/verwijderen/" in body

    def test_error_detail_always_renders_the_full_page(self):
        # The row and the Mattermost link both navigate to the full page; there
        # is no htmx sheet variant.
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Kapot")

        response = self.client.get(f"/beheer/statistieken/fout/{error.public_id}/", headers={"hx-request": "true"})

        assert response.status_code == 200
        body = response.content.decode()
        assert "<nldd-sheet" not in body
        assert "Terug naar statistieken" in body  # full page chrome

    def test_row_links_to_the_detail_page(self):
        # The whole row navigates to the detail page; no eye button, delete lives there.
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Kapot")

        response = self.client.get(ERROR_TABLE_URL)

        body = response.content.decode()
        assert f'href="/beheer/statistieken/fout/{error.public_id}/"' in body
        assert "nldd-icon-button" not in body
        assert "verwijderen/" not in body

    def test_row_shows_time_where_and_user_columns_for_a_web_error(self):
        # A request-driven error: Waar is the method + path, Gebruiker the email.
        error = ErrorEvent.objects.create(
            level="ERROR",
            logger_name="django.request",
            message="Kapot",
            exception_type="TypeError",
            method="POST",
            path="/opdrachten/25/verwijderen/",
            user_email="jan@rijksoverheid.nl",
        )

        body = self.client.get(ERROR_TABLE_URL).content.decode()

        # Tijd: absolute timestamp (datetime_nl), not a "x geleden" relative label.
        assert datetime_nl(error.timestamp) in body
        # Fout, Waar, Gebruiker columns.
        assert "TypeError" in body
        assert "POST /opdrachten/25/verwijderen/" in body
        assert "jan@rijksoverheid.nl" in body

    def test_row_where_falls_back_to_logger_and_user_to_a_dash(self):
        # A background-task failure: no path (fall back to logger) and no user.
        ErrorEvent.objects.create(level="ERROR", logger_name="wies.tasks", message="Task 5 failed")

        body = self.client.get(ERROR_TABLE_URL).content.decode()

        assert "wies.tasks" in body
        assert "-" in body  # en-dash for the missing user

    def test_delete_redirects_to_the_dashboard(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Weg ermee")

        response = self.client.post(f"/beheer/statistieken/fout/{error.public_id}/verwijderen/", follow=False)

        assert response.status_code == 302
        assert response.url == reverse("staff-dashboard")

    def test_error_detail_requires_staff(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Kapot")
        with override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"]):
            non_staff = User.objects.create_user(email="ns@rijksoverheid.nl", first_name="No", last_name="Staff")
            self.client.force_login(non_staff)

            response = self.client.get(f"/beheer/statistieken/fout/{error.public_id}/", follow=False)

            assert response.status_code == 302
            assert response.url.startswith("/geen-toegang/")

    def test_delete_error_removes_the_error(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Weg ermee")

        self.client.post(f"/beheer/statistieken/fout/{error.public_id}/verwijderen/")

        assert not ErrorEvent.objects.filter(pk=error.pk).exists()

    def test_delete_error_rejects_get(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Blijf staan")

        response = self.client.get(f"/beheer/statistieken/fout/{error.public_id}/verwijderen/")

        assert response.status_code == 405
        assert ErrorEvent.objects.filter(pk=error.pk).exists()

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_error_table_requires_staff(self):
        non_staff = User.objects.create_user(email="notstaff@rijksoverheid.nl", first_name="No", last_name="Staff")
        self.client.force_login(non_staff)

        response = self.client.get(ERROR_TABLE_URL, follow=False)

        assert response.status_code == 302
        assert response.url.startswith("/geen-toegang/")

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_delete_error_requires_staff(self):
        non_staff = User.objects.create_user(email="notstaff@rijksoverheid.nl", first_name="No", last_name="Staff")
        self.client.force_login(non_staff)
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Beschermd")

        response = self.client.post(f"/beheer/statistieken/fout/{error.public_id}/verwijderen/", follow=False)

        assert response.status_code == 302
        assert ErrorEvent.objects.filter(pk=error.pk).exists()
