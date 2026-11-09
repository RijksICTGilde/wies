from django.test import RequestFactory, SimpleTestCase

from wies.core.services.urls import current_page_path, is_local_path


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

    def test_falls_back_to_request_path_when_header_path_leaves_the_site(self):
        # The header is client controlled; "//host" and "/\host" both resolve
        # to another origin in a browser.
        for current in ("https://testserver//evil.example/", "https://testserver/\\evil.example/"):
            with self.subTest(current=current):
                request = self.factory.get("/inline-edit/", headers={"HX-Current-URL": current})
                assert current_page_path(request) == "/inline-edit/"


class IsLocalPathTests(SimpleTestCase):
    def test_accepts_site_paths(self):
        for raw in ("/", "/opdrachten/", "/opdrachten/?opdracht=1&zoek=a"):
            with self.subTest(raw=raw):
                assert is_local_path(raw)

    def test_rejects_anything_that_can_leave_the_site(self):
        for raw in (
            None,
            "",
            "//evil.example",
            "/\\evil.example",
            "\\\\evil.example",
            "https://evil.example/",
            "javascript:alert(1)",
            "opdrachten/",
        ):
            with self.subTest(raw=raw):
                assert not is_local_path(raw)
