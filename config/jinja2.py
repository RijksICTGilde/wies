from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from jinja2 import Environment
from jinja_roos_components import setup_components


def datum_nl(datum, datum_format="N Y"):
    """Format a date using Django's localization (nl-nl)"""
    if datum is None:
        return "?"
    return date_format(datum, datum_format)


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
    env = Environment(**options)  # noqa: S701 - autoescape configured via Django
    setup_components(env)
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "get_csrf_token": get_token,
            "get_csrf_hidden_input": get_csrf_hidden_input,
            "get_toggle_sort_url": get_toggle_sort_url,
            "get_sort_state": get_sort_state,
        }
    )
    env.filters["datum_nl"] = datum_nl

    return env
