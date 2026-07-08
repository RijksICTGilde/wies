from django.test import RequestFactory, SimpleTestCase

from wies.core.services.urls import current_page_path


class CurrentPagePathTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_prefers_hx_current_url_path_dropping_query(self):
        request = self.factory.get(
            "/inline-edit/",
            headers={"HX-Current-URL": "https://testserver/medewerkers/?collega=5&opdracht=99"},
        )
        assert current_page_path(request) == "/medewerkers/"

    def test_falls_back_to_request_path_when_header_absent(self):
        request = self.factory.get("/inline-edit/")
        assert current_page_path(request) == "/inline-edit/"

    def test_falls_back_to_request_path_when_header_has_no_path(self):
        request = self.factory.get("/inline-edit/", headers={"HX-Current-URL": ""})
        assert current_page_path(request) == "/inline-edit/"
