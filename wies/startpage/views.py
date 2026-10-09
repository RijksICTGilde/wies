"""Views for the ODI start page.

A single surface, behind the project-wide ``LoginRequiredMiddleware`` (so a
logged-out request is bounced to SSO before it reaches here):

- :func:`article` — a catch-all that streams the built Hugo site (homepage, HTML
  articles *and* assets) out of MinIO. The site owns its own landing page, so the
  root path resolves to ``<prefix>/index.html`` here — there is no separate Django
  portal. It must go through Django precisely because these objects are private;
  WhiteNoise runs before auth and would serve them to anyone.
"""

from __future__ import annotations

import posixpath

from django.http import Http404, StreamingHttpResponse
from django.shortcuts import redirect

from wies.startpage import storage


def _resolve_key(path: str, prefix: str) -> str:
    """Map a request path under the start page mount to a MinIO object key.

    Applies Hugo's pretty-URL rule (a directory path resolves to its
    ``index.html``) and refuses anything that could escape ``prefix``.
    """
    # Reject traversal outright rather than relying on it normalizing to a
    # contained-but-wrong key: intent is clearer and there are no surprise keys.
    if ".." in path.split("/"):
        raise Http404

    # normpath collapses ``.`` and duplicate slashes; the leading ``/`` anchors
    # the result so it can never become absolute-escaping. It also strips a
    # trailing slash, so decide the index.html rule from the *original* path.
    wants_index = path == "" or path.endswith("/")
    normalized = posixpath.normpath("/" + path).lstrip("/")
    if wants_index:
        normalized = f"{normalized}/index.html" if normalized else "index.html"

    key = f"{prefix}/{normalized}"
    # Defence in depth: after joining, the key must still sit under the prefix.
    if not key.startswith(f"{prefix}/"):
        raise Http404
    return key


def article(request, path: str = ""):
    """Stream a built article/asset from MinIO, gated by the login middleware."""
    # A path without a trailing slash and no file extension is a Hugo pretty URL;
    # redirect ``/x`` -> ``/x/`` so relative asset links resolve consistently.
    if path and not path.endswith("/") and "." not in posixpath.basename(path):
        return redirect(request.path + "/")

    try:
        prefix = storage.get_current_prefix()
    except storage.ObjectNotFoundError as error:
        # Nothing published yet — treat as not-found rather than a 500.
        raise Http404 from error

    key = _resolve_key(path, prefix)

    try:
        obj = storage.get_object(key)
    except storage.ObjectNotFoundError as error:
        raise Http404 from error

    content_type = obj.get("ContentType") or "application/octet-stream"
    response = StreamingHttpResponse(storage.iter_body(obj["Body"]), content_type=content_type)
    # These objects are private, behind auth — never let a shared cache (or the
    # browser, across a re-auth) hold on to them.
    response["Cache-Control"] = "private, no-store"
    return response
