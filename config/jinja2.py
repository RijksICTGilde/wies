from datetime import date

from django.conf import settings
from django.contrib.messages import get_messages
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html, json_script
from jinja2 import Environment
from jinja_roos_components import setup_components

from wies.core.editables import (
    AssignmentEditables,
    ColleagueEditables,
    PlacementEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.inline_edit.jinja import inline_edit
from wies.core.permission_engine import Verb, has_permission
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


def tijdgeleden(dt):
    """Returns Dutch relative time string, e.g. '2 weken geleden'"""
    if dt is None:
        return ""

    SECONDS_PER_MINUTE = 60  # noqa: N806
    MINUTES_PER_HOUR = 60  # noqa: N806
    HOURS_PER_DAY = 24  # noqa: N806
    DAYS_PER_WEEK = 7  # noqa: N806
    MAX_WEEKS = 5  # noqa: N806
    MONTHS_PER_YEAR = 12  # noqa: N806
    DAYS_PER_MONTH = 30  # noqa: N806
    DAYS_PER_YEAR = 365  # noqa: N806

    delta = timezone.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < SECONDS_PER_MINUTE:
        return "zojuist"
    minutes = seconds // SECONDS_PER_MINUTE
    if minutes < MINUTES_PER_HOUR:
        return f"{minutes} {'minuut' if minutes == 1 else 'minuten'} geleden"
    hours = minutes // MINUTES_PER_HOUR
    if hours < HOURS_PER_DAY:
        return f"{hours} uur geleden"
    days = delta.days
    if days < DAYS_PER_WEEK:
        return f"{days} {'dag' if days == 1 else 'dagen'} geleden"
    weeks = days // DAYS_PER_WEEK
    if weeks < MAX_WEEKS:
        return f"{weeks} {'week' if weeks == 1 else 'weken'} geleden"
    months = days // DAYS_PER_MONTH
    if months < MONTHS_PER_YEAR:
        return f"{months} {'maand' if months == 1 else 'maanden'} geleden"
    years = days // DAYS_PER_YEAR
    return f"{years} jaar geleden"


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
            "inline_edit": inline_edit,
            "has_permission": has_permission,
            "Verb": Verb,
            "AssignmentEditables": AssignmentEditables,
            "ColleagueEditables": ColleagueEditables,
            "PlacementEditables": PlacementEditables,
            "ServiceEditables": ServiceEditables,
            "UserEditables": UserEditables,
        }
    )
    env.filters["datum_nl"] = datum_nl
    env.filters["tijdgeleden"] = tijdgeleden
    env.filters["json_script"] = json_script
    env.filters["parse_message_link"] = parse_message_link

    return env
