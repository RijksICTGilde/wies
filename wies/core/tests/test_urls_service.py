import pytest
from django.http import QueryDict
from django.test import RequestFactory, SimpleTestCase

from wies.core.services.urls import (
    current_page_path,
    current_page_url_on,
    hx_current_url,
    is_local_path,
    rebuild_url,
    safe_return_path,
    url_replacing_param,
    url_with_param,
    url_without_param,
)


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


class SafeReturnPathTests(SimpleTestCase):
    def test_keeps_a_site_path(self):
        assert safe_return_path("/opdrachten/?opdracht=1", "/fallback/") == "/opdrachten/?opdracht=1"

    def test_falls_back_for_anything_that_can_leave_the_site(self):
        for raw in (None, "", "//evil.example", "/\\evil.example", "https://evil.example/"):
            with self.subTest(raw=raw):
                assert safe_return_path(raw, "/fallback/") == "/fallback/"


class RebuildUrlTests(SimpleTestCase):
    def test_drops_names_and_sets_overrides(self):
        query = QueryDict("zoek=a&opdracht=1&pagina=2")
        assert rebuild_url("/", query, drop=("opdracht", "pagina"), collega="5") == "/?zoek=a&collega=5"

    def test_accepts_a_raw_query_string(self):
        assert rebuild_url("/", "zoek=a&opdracht=1", drop=("opdracht",)) == "/?zoek=a"

    def test_keeps_blank_values(self):
        assert rebuild_url("/", "nieuwe-opdracht=&zoek=a") == "/?nieuwe-opdracht=&zoek=a"

    def test_override_replaces_every_value(self):
        assert rebuild_url("/", "label=1&label=2", label="3") == "/?label=3"

    def test_repeated_params_survive(self):
        assert rebuild_url("/", "label=1&label=2&pagina=3", drop=("pagina",)) == "/?label=1&label=2"

    def test_returns_bare_path_when_nothing_remains(self):
        assert rebuild_url("/opdrachten/", "pagina=2", drop=("pagina",)) == "/opdrachten/"

    def test_re_encodes_hostile_keys_and_values(self):
        url = rebuild_url("/", "a=%0d%0aSet-Cookie:x", **{'x"><script>': "1"})
        assert url == "/?a=%0D%0ASet-Cookie%3Ax&x%22%3E%3Cscript%3E=1"

    def test_leaves_the_given_querydict_alone(self):
        query = QueryDict("zoek=a")
        rebuild_url("/", query, drop=("zoek",), pagina=2)
        assert query.urlencode() == "zoek=a"


class UrlReplacingParamTests(SimpleTestCase):
    def test_swaps_one_param_for_another(self):
        url = url_replacing_param("/opdrachten/?zoek=a&aanvraag=x", "aanvraag", opdracht="y")
        assert url == "/opdrachten/?zoek=a&opdracht=y"

    def test_refuses_a_url_that_leaves_the_site(self):
        for url in ("/\\evil.example?x=1", "//evil.example/x", "https://evil.example/"):
            with self.subTest(url=url), pytest.raises(ValueError, match="not a local path"):
                url_replacing_param(url, "x")


class SortUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_with_param_keeps_filters_and_drops_paging(self):
        request = self.factory.get("/", {"label": "1", "pagina": "3"})
        assert url_with_param(request, "order", "naam") == "/?label=1&order=naam"

    def test_without_param_drops_it_and_paging(self):
        request = self.factory.get("/", {"label": "1", "order": "naam", "pagina": "3"})
        assert url_without_param(request, "order") == "/?label=1"

    def test_uses_the_address_bar_path_during_a_partial_request(self):
        request = self.factory.get("/inline-edit/", {"label": "1"}, headers={"HX-Current-URL": "https://testserver/"})
        assert url_with_param(request, "order", "naam") == "/?label=1&order=naam"


class HxCurrentUrlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_parses_a_site_url(self):
        request = self.factory.get("/x/", headers={"HX-Current-URL": "https://testserver/medewerkers/?zoek=a"})
        parsed = hx_current_url(request)
        assert (parsed.path, parsed.query) == ("/medewerkers/", "zoek=a")

    def test_strips_a_foreign_host(self):
        # Only the path is checked, so the client's host must not survive.
        request = self.factory.get("/x/", headers={"HX-Current-URL": "https://evil.example/medewerkers/?a=1"})
        assert hx_current_url(request).geturl() == "/medewerkers/?a=1"

    def test_none_when_absent_or_off_site(self):
        for headers in ({}, {"HX-Current-URL": "https://testserver//evil.example/"}):
            with self.subTest(headers=headers):
                assert hx_current_url(self.factory.get("/x/", headers=headers)) is None


class CurrentPageUrlOnTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_keeps_the_address_bar_query_on_that_path_minus_paging(self):
        request = self.factory.get(
            "/x/", headers={"HX-Current-URL": "https://testserver/beheer/gebruikers/?zoek=a&pagina=2"}
        )
        assert current_page_url_on(request, "/beheer/gebruikers/") == "/beheer/gebruikers/?zoek=a"

    def test_bare_path_when_the_address_bar_is_elsewhere(self):
        request = self.factory.get("/x/", headers={"HX-Current-URL": "https://testserver/elders/?zoek=a"})
        assert current_page_url_on(request, "/beheer/gebruikers/") == "/beheer/gebruikers/"
