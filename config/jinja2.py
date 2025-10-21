from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe

from wies.projects.views import assignments_url_with_tab, placements_url_with_filters


def environment(**options):
    env = Environment(**options)

    def get_csrf_hidden_input(request):
        """Returns a hidden input field with CSRF token"""
        token = get_token(request)
        return mark_safe(f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">')

    env.globals.update({
        'static': static,
        'url': reverse,
        'get_csrf_token': get_token,
        'get_csrf_hidden_input': get_csrf_hidden_input,
        'assignments_url_with_tab': lambda request, tab_key: assignments_url_with_tab({'request': request}, tab_key),
        'placements_url_with_filters': lambda request, url_name: placements_url_with_filters({'request': request}, url_name),
    })

    return env
