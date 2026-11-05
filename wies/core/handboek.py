"""The pages of the handbook (/handboek/), rendered from docs/handboek/ by
``generate_docs_html``. One list feeds the generator, the view and the menu."""

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class HandboekPage:
    slug: str
    title: str
    # Pages in a group are listed under its name in the menu.
    group: str = ""

    @property
    def source(self) -> str:
        return f"docs/handboek/{self.slug}.md"

    @property
    def template(self) -> str:
        return f"handboek/{self.slug}.html"

    @property
    def path(self) -> str:
        if self is HANDBOEK_PAGES[0]:
            return reverse("handboek")
        return reverse("handboek-page", args=[self.slug])


HANDBOEK_PAGES = [
    HandboekPage("organisatie", "Organisatie"),
    HandboekPage("visie", "Visie"),
    HandboekPage("privacy-en-beveiliging", "Data, privacy en beveiliging"),
    HandboekPage("aan-de-slag", "Aan de slag", group="Techniek"),
    HandboekPage("de-code", "De code", group="Techniek"),
    HandboekPage("samenwerken", "Samenwerken", group="Techniek"),
]

HANDBOEK_BY_SLUG = {page.slug: page for page in HANDBOEK_PAGES}
