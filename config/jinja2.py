from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.messages import get_messages
from django.contrib.staticfiles import finders
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html, json_script
from jinja2 import Environment

from wies.core.editables import (
    AssignmentEditables,
    ColleagueEditables,
    PlacementEditables,
    ServiceEditables,
    UserEditables,
)
from wies.core.form_mixins import wire_field_errors
from wies.core.inline_edit.jinja import inline_edit, inline_edit_form
from wies.core.permission_engine import Verb, has_permission
from wies.core.permissions import is_staff_member
from wies.core.services.organizations import get_org_breadcrumb, get_org_levels_action
from wies.core.services.urls import current_page_path, url_with_param, url_without_param
from wies.core.services.version import get_app_version, get_nldd_version


def parse_message_link(extra_tags: str) -> dict | None:
    """Parse a structured link from message extra_tags.

    Format: "link:<url>|<text>"
    Returns {"url": ..., "text": ...} or None.
    """
    if not extra_tags:
        return None
    # extra_tags bevat alleen deze link-tag (het level, bv. "success", zit in
    # message.tags). Niet op witruimte splitsen: de linktekst mag spaties bevatten
    # ("Bekijk opdracht"), en een split() kapte die af tot "Bekijk".
    prefix = "link:"
    start = extra_tags.find(prefix)
    if start == -1:
        return None
    url, sep, text = extra_tags[start + len(prefix) :].partition("|")
    if sep:
        return {"url": url, "text": text}
    return None


def datum_nl(datum, fmt="j b Y"):
    """THE date display for Wies, via Django's nl-nl localization.

    House style: months are always three letters, lowercase ('b' → "11 nov
    2024"). Callers only choose which parts to show (e.g. "b Y" for month +
    year on cards); they don't restyle the month.
    """
    if datum is None:
        return "?"
    if isinstance(datum, str):
        try:
            datum = date.fromisoformat(datum)
        except ValueError:
            return datum
    return date_format(datum, fmt)


NL_TIMEZONE = ZoneInfo("Europe/Amsterdam")


def datetime_nl(dt, fmt="%Y-%m-%d %H:%M:%S"):
    """Format a timezone-aware datetime in Dutch local time (Europe/Amsterdam).

    The project stores times in UTC (TIME_ZONE=UTC); this converts to the local
    zone for display, honouring daylight saving.
    """
    if dt is None:
        return ""
    if timezone.is_aware(dt):
        dt = dt.astimezone(NL_TIMEZONE)
    return dt.strftime(fmt)


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


def nldd_asset(filename: str) -> str:
    """URL for a vendored design-system asset, cache-busted on its version.

    The file names are fixed (nldd.min.js, css/global.css), so without this a
    browser can keep serving the previous design system from cache after an
    upgrade. See get_nldd_version for why production does not need it.
    """
    url = static(f"vendor/nldd/{filename}")
    version = get_nldd_version()
    return f"{url}?v={version}" if version else url


def app_asset(filename: str) -> str:
    """URL for one of our own static files, cache-busted on its mtime.

    Same reason as nldd_asset, for the files we write ourselves: runserver
    serves static straight from disk without Cache-Control, so a browser falls
    back to heuristic caching and can keep running a stale ui_handlers.js or
    app.css after an edit — the file name never changes. APP_VERSION is no use
    as the token here: it is <branch>-<short-sha> in development and does not
    move when you save a file.

    DEBUG only. Production runs WhiteNoise's manifest storage, which content-
    hashes the names, so the query would add nothing and the stat() per asset
    per request would cost something. Also skipped when the file cannot be
    found, so a typo'd path still renders (and still 404s, visibly).
    """
    url = static(filename)
    if not settings.DEBUG:
        return url
    path = finders.find(filename)
    if not path:
        return url
    return f"{url}?v={int(Path(path).stat().st_mtime)}"


def environment(**options):
    env = Environment(**options)  # noqa: S701 - autoescape handled by Django
    env.globals.update(
        {
            "static": static,
            "nldd_asset": nldd_asset,
            "app_asset": app_asset,
            "url": reverse,
            "get_csrf_token": get_token,
            "get_csrf_hidden_input": get_csrf_hidden_input,
            "get_toggle_sort_url": get_toggle_sort_url,
            "get_sort_state": get_sort_state,
            "get_messages": get_messages,
            "is_staff_member": is_staff_member,
            "DEBUG": settings.DEBUG,
            "APP_VERSION": get_app_version(),
            "inline_edit": inline_edit,
            "inline_edit_form": inline_edit_form,
            "wire_field_errors": wire_field_errors,
            "get_org_breadcrumb": get_org_breadcrumb,
            "get_org_levels_action": get_org_levels_action,
            "current_page_path": current_page_path,
            "url_with_param": url_with_param,
            "url_without_param": url_without_param,
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
    env.filters["datetime_nl"] = datetime_nl
    env.filters["tijdgeleden"] = tijdgeleden
    env.filters["json_script"] = json_script
    env.filters["parse_message_link"] = parse_message_link

    return env
