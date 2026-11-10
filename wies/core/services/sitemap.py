"""The pages on the sitemap: the menus and the footer, flattened for one user.

The gates are the ones the menus ask (``show_*`` in ``visibility_rules``), so
the list never offers a page the menu hides, and never misses one it shows.
"""

from dataclasses import dataclass

from django.urls import reverse

from wies.core.visibility_rules import show_bm_page, show_staff_pages, show_user_admin_pages


@dataclass(frozen=True)
class SitemapLink:
    text: str
    url: str


@dataclass(frozen=True)
class SitemapSection:
    title: str
    links: list[SitemapLink]


def _links(*pairs: tuple[str, str]) -> list[SitemapLink]:
    return [SitemapLink(text, reverse(name)) for text, name in pairs]


def sitemap_sections(request) -> list[SitemapSection]:
    """The sections of the sitemap for ``request.user``; an empty section is left out."""
    work = [("Wie zit waar?", "home"), ("Aanvragen", "assignment-list")]
    if show_bm_page(request):
        # The menu's "Business management" only redirects here.
        work.append(("Bezetting", "bezetting"))
    work.append(("Mijn profiel", "user-profile"))

    admin = []
    if show_user_admin_pages(request):
        admin += [
            ("Gebruikers", "admin-users"),
            ("Labels", "label-admin"),
            ("Merken", "suborganization-admin"),
            ("Rollen", "role-matrix"),
        ]
    if show_staff_pages(request):
        admin += [("Statistieken", "staff-dashboard"), ("Database", "staff-database")]

    about = [
        ("Handleiding", "handleiding"),
        ("Veelgestelde vragen", "faq"),
        ("Contact", "contact"),
        ("Privacy", "privacy"),
        ("Beveiliging", "beveiliging"),
        ("Toegankelijkheid", "toegankelijkheid"),
    ]

    sections = [("Werken in Wies", work), ("Beheer", admin), ("Over Wies", about)]
    return [SitemapSection(title, _links(*pairs)) for title, pairs in sections if pairs]
