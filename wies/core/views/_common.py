"""Helpers shared by the views: panel URLs, sort controls, CSV upload limit."""

from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse

from wies.core.services.urls import PAGE_PARAM, hx_current_url, rebuild_url

# Query params that drive the side panel; stripped when (re)building a page URL.
# ``bewerken`` and ``toevoegen`` open a child sheet on the panel. The list's page
# number goes too: "Meer tonen" fetches page N without pushing it, so a card
# from that page would otherwise put ``pagina=N`` in the address bar when its
# panel opens, and a reload would show page N alone.
PANEL_PARAMS = (
    PAGE_PARAM,
    "collega",
    "opdracht",
    "aanvraag",
    "bewerken",
    "toevoegen",
    "veld",
    "nieuwe-opdracht",
    "uitgeklapt",
)


def build_panel_url(request, **overrides):
    """Build a URL on the current path, preserving filters but replacing panel params."""
    return rebuild_url(request.path, request.GET, drop=PANEL_PARAMS, **overrides)


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
    return rebuild_url(request.path, request.GET, drop=PANEL_PARAMS)


def is_side_panel_request(request):
    """True for the HTMX requests that render a panel partial.

    Lets a view 404 an unresolved panel target instead of rendering a template
    with no ``panel_data``; a full-page load stays graceful and shows no panel.
    """
    return request.headers.get("HX-Target") == "side-panel-content"


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
    HX-Current-URL header is absent or names a path that would leave the site.
    Drops the same params as :func:`build_close_url`: ``collega`` too, or the
    colleague panel would open, and ``pagina``, or the list shows one page.
    """
    current = hx_current_url(request)
    if current is None:
        return reverse("assignment-list")
    return rebuild_url(current.path, current.query, drop=PANEL_PARAMS)


# Safety ceiling so a single upload can't exhaust a worker's memory
MAX_CSV_UPLOAD_BYTES = 50 * 1024 * 1024


_CSV_MAX_MB = MAX_CSV_UPLOAD_BYTES // (1024 * 1024)


CSV_TOO_LARGE_MSG = f"Bestand te groot. Upload een CSV-bestand van maximaal {_CSV_MAX_MB} MB."


def csv_too_large(csv_file) -> bool:
    return bool(csv_file.size) and csv_file.size > MAX_CSV_UPLOAD_BYTES
