from jinja2 import Environment
from jinja_roos_components import setup_components


def environment(**options):
    env = Environment(**options)
    setup_components(env)
    return env
