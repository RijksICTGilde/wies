"""Helpers shared by the views: panel URLs, sort controls, safe return paths, CSV upload limit."""

import urllib.parse

from django.core.exceptions import ValidationError
from django.http import Http404, QueryDict
from django.urls import reverse

from wies.core.services.urls import is_local_path

# Query params that drive the side panel; stripped when (re)building a page URL.
# ``bewerken`` puts the panel in edit mode (the child sheet).
PANEL_PARAMS = (
    "pagina",
    "collega",
    "opdracht",
    "aanvraag",
    "bewerken",
    "teamlid",
    "veld",
    "nieuwe-opdracht",
    "uitgeklapt",
)


def url_drop_params(path, query, names, **overrides):
    """Rebuild ``path`` from ``query`` (a QueryDict) with ``names`` dropped and
    ``overrides`` applied. Returns ``path`` alone when no params remain."""
    params = query.copy()
    for name in names:
        params.pop(name, None)
    for key, value in overrides.items():
        params[key] = value
    encoded = params.urlencode()
    return f"{path}?{encoded}" if encoded else path


def build_panel_url(request, **overrides):
    """Build a URL on the current path, preserving filters but replacing panel params."""
    return url_drop_params(request.path, request.GET, PANEL_PARAMS, **overrides)


def sort_control_context(active_order: str, options: list[tuple[str, str]], default_label: str) -> dict:
    """The four keys parts/sort_control.html reads, built once for every list.

    ``options`` are (value, label) pairs in menu order; ``active_order`` is ""
    for the default, which has no ``?order=`` value of its own.
    """
    labels = dict(options)
    return {
        "active_order": active_order,
        "sort_options": [{"value": value, "label": label} for value, label in options],
        "default_sort_label": default_label,
        "active_sort_label": labels.get(active_order, default_label),
    }


def build_close_url(request):
    """Build close URL preserving current filters."""
    return url_drop_params(request.path, request.GET, PANEL_PARAMS)


def is_side_panel_request(request):
    """True for the HTMX requests that render a panel partial.

    Lets a view 404 an unresolved panel target instead of rendering a template
    with no ``panel_data``; a full-page load stays graceful and shows no panel.
    """
    return request.headers.get("HX-Target") in ("side-panel-content", "side-panel-container")


def resolve_panel_object(request, model, public_id, *, select_related=()):
    """Looks up a side-panel object (Assignment, Colleague, ...) by its public_id.

    A miss (including a malformed public_id) raises Http404 only for the HTMX
    panel request; a full-page load gets None and renders without a panel. Only
    for models whose panel has no per-object visibility rule.
    """
    qs = model.objects.select_related(*select_related) if select_related else model.objects.all()
    try:
        return qs.get(public_id=public_id)
    except model.DoesNotExist, ValidationError, ValueError:
        if is_side_panel_request(request):
            raise Http404 from None
        return None


def page_url_behind_panel(request) -> str:
    """The page the side panel was opened over, with the panel params dropped.

    The panel is an overlay on a real page, so after deleting we return there
    instead of jumping to the assignment list. Falls back to that list when the
    HX-Current-URL header is absent, or (being client controlled) names a path
    that would leave the site.
    """
    current = request.headers.get("HX-Current-URL")
    if not current:
        return reverse("assignment-list")
    parsed = urllib.parse.urlparse(current)
    if not is_local_path(parsed.path):
        return reverse("assignment-list")
    # Keep pagina/filters; collega goes too, or the colleague panel would open.
    return url_drop_params(parsed.path, QueryDict(parsed.query), ("opdracht", "collega"))


def safe_return_path(raw: str | None, fallback: str) -> str:
    """Returns ``raw`` only when it is a path on this site, else the fallback.

    The value comes from a hidden input, so the client controls it. It ends up in
    HX-Location/HX-Push-Url, where a protocol-relative "//host" — or "/\\host",
    which browsers read the same way — would point at a foreign origin.
    """
    if is_local_path(raw):
        return raw
    return fallback


# Safety ceiling so a single upload can't exhaust a worker's memory
MAX_CSV_UPLOAD_BYTES = 50 * 1024 * 1024


_CSV_MAX_MB = MAX_CSV_UPLOAD_BYTES // (1024 * 1024)


CSV_TOO_LARGE_MSG = f"Bestand te groot. Upload een CSV-bestand van maximaal {_CSV_MAX_MB} MB."


def csv_too_large(csv_file) -> bool:
    return bool(csv_file.size) and csv_file.size > MAX_CSV_UPLOAD_BYTES
