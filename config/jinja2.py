from jinja2 import Environment
from jinja_roos_components import setup_components
from django.templatetags.static import static
from django.urls import reverse
from django.contrib.auth.context_processors import auth
from wies.projects.views import assignments_url_with_tab


def environment(**options):
    env = Environment(**options)
    setup_components(env)
    env.globals.update({
        'static': static,
        'url': reverse,
        'assignments_url_with_tab': lambda request, tab_key: assignments_url_with_tab({'request': request}, tab_key),
    })
    return env
