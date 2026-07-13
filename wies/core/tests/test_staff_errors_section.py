"""Tests for the errors section on the statistieken page."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

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

    def test_dashboard_hosts_error_table_container(self):
        # The dashboard shows the heading + a container that lazy-loads the table.
        response = self.client.get("/beheer/statistieken/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Recente foutmeldingen" in body
        assert 'id="error_table_container"' in body

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

    def test_error_detail_shows_traceback_in_modal(self):
        error = ErrorEvent.objects.create(
            level="ERROR",
            logger_name="django.request",
            message="Kapot",
            traceback="Traceback (most recent call last):\n  ValueError: kaboom",
        )

        response = self.client.get(f"/beheer/statistieken/fout/{error.id}/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "errorDetailDialog" in body  # renders as a modal dialog
        assert "ValueError: kaboom" in body

    def test_error_detail_requires_staff(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Kapot")
        with override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"]):
            non_staff = User.objects.create_user(email="ns@rijksoverheid.nl", first_name="No", last_name="Staff")
            self.client.force_login(non_staff)

            response = self.client.get(f"/beheer/statistieken/fout/{error.id}/", follow=False)

            assert response.status_code == 302
            assert response.url.startswith("/geen-toegang/")

    def test_hidden_errors_are_excluded(self):
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Zichtbaar")
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Verborgen", visible=False)

        response = self.client.get(ERROR_TABLE_URL)

        body = response.content.decode()
        assert "Zichtbaar" in body
        assert "Verborgen" not in body

    def test_hide_error_marks_invisible_and_returns_table(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Weg ermee")

        response = self.client.post(f"/beheer/statistieken/fout/{error.id}/verbergen/")

        assert response.status_code == 200
        error.refresh_from_db()
        assert error.visible is False
        # The refreshed fragment no longer contains the hidden error.
        assert "Weg ermee" not in response.content.decode()

    def test_hide_error_rejects_get(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Blijf staan")

        response = self.client.get(f"/beheer/statistieken/fout/{error.id}/verbergen/")

        assert response.status_code == 405
        error.refresh_from_db()
        assert error.visible is True

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_error_table_requires_staff(self):
        non_staff = User.objects.create_user(email="notstaff@rijksoverheid.nl", first_name="No", last_name="Staff")
        self.client.force_login(non_staff)

        response = self.client.get(ERROR_TABLE_URL, follow=False)

        assert response.status_code == 302
        assert response.url.startswith("/geen-toegang/")

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_hide_error_requires_staff(self):
        non_staff = User.objects.create_user(email="notstaff@rijksoverheid.nl", first_name="No", last_name="Staff")
        self.client.force_login(non_staff)
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Beschermd")

        response = self.client.post(f"/beheer/statistieken/fout/{error.id}/verbergen/", follow=False)

        assert response.status_code == 302
        error.refresh_from_db()
        assert error.visible is True
