from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe
from jinja_roos_components import setup_components


def get_csrf_hidden_input(request):
        """Returns a hidden input field with CSRF token"""
        token = get_token(request)
        return mark_safe(f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">')


def environment(**options):
    env = Environment(**options)
    setup_components(env)
    env.globals.update({
        'static': static,
        'url': reverse,
        'get_csrf_token': get_token,
        'get_csrf_hidden_input': get_csrf_hidden_input,
    })

    return env
