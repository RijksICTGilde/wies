"""URLs for the start page app.

Mounted under a single ``include()`` in ``config/urls.py`` (at
``/odi-startpagina/``, matching the content site's Hugo ``baseURL`` path). Kept
deliberately relative — no hardcoded prefix and all links built via ``url()`` —
so promoting the app to its own subdomain later is a mount change plus a redirect,
not a prefix hunt.

A single catch-all streams the whole published site from MinIO, including the
homepage: the empty path resolves to ``<prefix>/index.html`` in ``views.article``.
"""

from django.urls import re_path

from wies.startpage import views

urlpatterns = [
    # Catch-all for the built Hugo site (homepage + articles + assets).
    re_path(r"^(?P<path>.*)$", views.article, name="startpage-article"),
]
