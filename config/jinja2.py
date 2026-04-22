from datetime import date

from django.conf import settings
from django.contrib.messages import get_messages
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html, json_script
from jinja2 import Environment
from jinja_roos_components import setup_components

from wies.core.services.version import get_app_version


def parse_message_link(extra_tags: str) -> dict | None:
    """Parse a structured link from message extra_tags.

    Format: "link:<url>|<text>"
    Returns {"url": ..., "text": ...} or None.
    """
    if not extra_tags:
        return None
    for tag in extra_tags.split():
        if tag.startswith("link:"):
            parts = tag[5:].split("|", 1)
            if len(parts) == 2:  # noqa: PLR2004
                return {"url": parts[0], "text": parts[1]}
    return None


def datum_nl(datum, fmt="N Y"):
    """Format a date using Django's localization (nl-nl)"""
    if datum is None:
        return "?"
    if isinstance(datum, str):
        try:
            datum = date.fromisoformat(datum)
        except ValueError:
            return datum
    return date_format(datum, fmt)


def get_csrf_hidden_input(request):
    """Returns a hidden input field with CSRF token"""
    token = get_token(request)
    return format_html('<input type="hidden" name="csrfmiddlewaretoken" value="{}">', token)


def get_toggle_sort_url(request, field):
    """
    Build URL for sortable table headers that toggles sort direction.
    If field is currently sorted ascending, returns URL for descending sort.
    If field is sorted descending or not sorted, returns URL for ascending sort.
    Preserves all other query parameters.
    """
    params = request.GET.copy()
    current_order = params.get("order", "")

    # Toggle: if currently ascending, switch to descending; otherwise ascending
    if current_order == field:
        params["order"] = f"-{field}"
    else:
        params["order"] = field

    return f"{request.path}?{params.urlencode()}"


def get_sort_state(request, field):
    """
    Get the current sort state for a field.
    Returns: 'ascending', 'descending', or None
    """
    current_order = request.GET.get("order", "")
    if current_order == field:
        return "ascending"
    if current_order == f"-{field}":
        return "descending"
    return None


def environment(**options):
    env = Environment(**options)  # noqa: S701 - autoescape handled by Django
    setup_components(env)
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "get_csrf_token": get_token,
            "get_csrf_hidden_input": get_csrf_hidden_input,
            "get_toggle_sort_url": get_toggle_sort_url,
            "get_sort_state": get_sort_state,
            "get_messages": get_messages,
            "DEBUG": settings.DEBUG,
            "APP_VERSION": get_app_version(),
        }
    )
    env.filters["datum_nl"] = datum_nl
    env.filters["json_script"] = json_script
    env.filters["parse_message_link"] = parse_message_link

    return env
