from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe
from django.utils.http import urlencode
from jinja_roos_components import setup_components

# Nederlandse maandnamen
MAANDEN_KORT = ['jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
MAANDEN_LANG = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december']


def datum_nl(datum, format='kort'):
    """
    Formatteert een datum in het Nederlands.

    Formats:
    - 'kort': "jan 24" (maand jaar)
    - 'lang': "1 januari 2024" (dag maand jaar)
    - 'maand_jaar': "januari 2024"
    """
    if datum is None:
        return "?"

    maand_idx = datum.month - 1

    if format == 'kort':
        return f"{MAANDEN_KORT[maand_idx]} {datum.strftime('%y')}"
    elif format == 'lang':
        return f"{datum.day} {MAANDEN_LANG[maand_idx]} {datum.year}"
    elif format == 'maand_jaar':
        return f"{MAANDEN_LANG[maand_idx]} {datum.year}"
    else:
        return datum.strftime(format)


def get_csrf_hidden_input(request):
        """Returns a hidden input field with CSRF token"""
        token = get_token(request)
        return mark_safe(f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">')


def get_toggle_sort_url(request, field):
    """
    Build URL for sortable table headers that toggles sort direction.
    If field is currently sorted ascending, returns URL for descending sort.
    If field is sorted descending or not sorted, returns URL for ascending sort.
    Preserves all other query parameters.
    """
    params = request.GET.copy()
    current_order = params.get('order', '')

    # Toggle: if currently ascending, switch to descending; otherwise ascending
    if current_order == field:
        params['order'] = f'-{field}'
    else:
        params['order'] = field

    return f"{request.path}?{params.urlencode()}"


def get_sort_state(request, field):
    """
    Get the current sort state for a field.
    Returns: 'ascending', 'descending', or None
    """
    current_order = request.GET.get('order', '')
    if current_order == field:
        return 'ascending'
    elif current_order == f'-{field}':
        return 'descending'
    return None


def environment(**options):
    env = Environment(**options)
    setup_components(env)
    env.globals.update({
        'static': static,
        'url': reverse,
        'get_csrf_token': get_token,
        'get_csrf_hidden_input': get_csrf_hidden_input,
        'get_toggle_sort_url': get_toggle_sort_url,
        'get_sort_state': get_sort_state,
    })
    env.filters['datum_nl'] = datum_nl

    return env
