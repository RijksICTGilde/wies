"""Tests for the errors section on the statistieken page."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from wies.core.models import ErrorEvent
from wies.core.views import ERRORS_PER_PAGE

User = get_user_model()

STAFF_EMAIL = "staff@rijksoverheid.nl"


@override_settings(STAFF_EMAILS=[STAFF_EMAIL])
class StaffErrorsSectionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(email=STAFF_EMAIL, first_name="Staff", last_name="User")
        self.client.force_login(self.staff_user)

    def test_errors_section_shows_recent_errors(self):
        ErrorEvent.objects.create(level="ERROR", logger_name="django.request", message="Kapot op de detailpagina")

        response = self.client.get("/beheer/statistieken/")

        assert response.status_code == 200
        body = response.content.decode()
        assert "Recente foutmeldingen" in body
        assert "Kapot op de detailpagina" in body

    def test_empty_state(self):
        response = self.client.get("/beheer/statistieken/")

        assert response.status_code == 200
        assert "Geen foutmeldingen." in response.content.decode()

    def test_first_page_caps_at_page_size(self):
        for i in range(ERRORS_PER_PAGE + 5):
            ErrorEvent.objects.create(level="ERROR", logger_name="wies", message=f"Fout {i}")

        response = self.client.get("/beheer/statistieken/")

        assert response.status_code == 200
        # The "load more" sentinel appears when there is a next page.
        assert "Meer laden..." in response.content.decode()

    def test_htmx_next_page_returns_rows_partial(self):
        for i in range(ERRORS_PER_PAGE + 5):
            ErrorEvent.objects.create(level="ERROR", logger_name="wies", message=f"Fout {i}")

        response = self.client.get("/beheer/statistieken/?pagina=2", headers={"HX-Request": "true"})

        assert response.status_code == 200
        body = response.content.decode()
        # Rows partial only — no full-page chrome such as the section heading.
        assert "Recente foutmeldingen" not in body
        assert "<c-table" not in body

    def test_hidden_errors_are_excluded(self):
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Zichtbaar")
        ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Verborgen", visible=False)

        response = self.client.get("/beheer/statistieken/")

        body = response.content.decode()
        assert "Zichtbaar" in body
        assert "Verborgen" not in body

    def test_hide_error_marks_invisible(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Weg ermee")

        response = self.client.post(f"/beheer/statistieken/fout/{error.id}/verbergen/")

        assert response.status_code == 200
        error.refresh_from_db()
        assert error.visible is False

    def test_hide_error_rejects_get(self):
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Blijf staan")

        response = self.client.get(f"/beheer/statistieken/fout/{error.id}/verbergen/")

        assert response.status_code == 405
        error.refresh_from_db()
        assert error.visible is True

    @override_settings(STAFF_EMAILS=["other@rijksoverheid.nl"])
    def test_hide_error_requires_staff(self):
        non_staff = User.objects.create_user(email="notstaff@rijksoverheid.nl", first_name="No", last_name="Staff")
        self.client.force_login(non_staff)
        error = ErrorEvent.objects.create(level="ERROR", logger_name="wies", message="Beschermd")

        response = self.client.post(f"/beheer/statistieken/fout/{error.id}/verbergen/", follow=False)

        assert response.status_code == 302
        error.refresh_from_db()
        assert error.visible is True
