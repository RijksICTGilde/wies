"""The page under the side panel: opening, closing and leaving it on a filtered, paged list."""

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from wies.core.views._common import build_close_url, build_panel_url, page_url_behind_panel


class PanelUrlTests(SimpleTestCase):
    """A card appended by "Meer tonen" is built during a ?pagina=2 request. Its
    panel URL must not carry the page number, or a reload of the opened panel
    shows page 2 of the list alone."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/", {"label": "1", "pagina": "2", "opdracht": "x"})

    def test_opening_a_panel_on_page_2_keeps_filters_and_drops_paging(self):
        assert build_panel_url(self.request, collega="y") == "/?label=1&collega=y"

    def test_closing_a_panel_keeps_filters_and_drops_paging(self):
        assert build_close_url(self.request) == "/?label=1"

    def test_page_behind_panel_drops_panel_params_and_paging(self):
        request = self.factory.post(
            "/opdrachten/x/verwijderen/",
            headers={"HX-Current-URL": "https://testserver/?label=1&pagina=2&opdracht=x&bewerken=1"},
        )
        assert page_url_behind_panel(request) == "/?label=1"

    def test_page_behind_panel_falls_back_to_the_list(self):
        request = self.factory.post("/opdrachten/x/verwijderen/")
        assert page_url_behind_panel(request) == reverse("assignment-list")
