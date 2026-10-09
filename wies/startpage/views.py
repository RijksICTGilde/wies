"""Views for the ODI start page.

:func:`article` is a catch-all that streams the built Hugo site (homepage, HTML
articles *and* assets) out of MinIO, behind the project-wide
``LoginRequiredMiddleware`` (so a logged-out request is bounced to SSO before it
reaches here). The site owns its landing page, so the root path resolves to
``<prefix>/index.html``. It must go through Django precisely because these
objects are private; WhiteNoise runs before auth and would serve them to anyone.
"""

from __future__ import annotations

import posixpath

from django.conf import settings
from django.http import Http404, HttpResponseNotModified, StreamingHttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET

from wies.startpage import storage

_ASSET_CACHE_CONTROL = "private, no-cache"


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


@require_GET
def article(request, path: str = ""):
    """Stream a built article/asset from MinIO, gated by the login middleware."""
    # A path without a trailing slash and no file extension is a Hugo pretty URL;
    # redirect ``/x`` -> ``/x/`` so relative asset links resolve consistently.
    if path and not path.endswith("/") and "." not in posixpath.basename(path):
        return redirect(request.path + "/")

    key = _resolve_key(path, settings.STARTPAGE_OBJECT_PREFIX.strip("/"))

    try:
        # If-None-Match compares weakly (RFC 9110), MinIO only matches the exact
        # strong tag; a compressing proxy in front of us weakens ours to W/"...".
        etag = request.headers.get("If-None-Match", "").replace("W/", "")
        obj = storage.get_object(key, if_none_match=etag or None)
    except storage.ObjectNotFoundError as error:
        # Also the answer when nothing has been published yet.
        raise Http404 from error
    except storage.ObjectNotModifiedError:
        # Only assets carry an ETag (below), so only they are revalidated.
        response = HttpResponseNotModified()
        response["Cache-Control"] = _ASSET_CACHE_CONTROL
        return response

    content_type = obj.get("ContentType") or "application/octet-stream"
    response = StreamingHttpResponse(storage.iter_body(obj["Body"]), content_type=content_type)
    if content_type.startswith("text/html"):
        # Pages are never kept, like the rest of Wies's HTML.
        response["Cache-Control"] = "private, no-store"
    else:
        # Assets may be kept by the browser (never a shared cache) but are
        # revalidated on every use, so a publish shows up immediately and an
        # unchanged asset costs a 304 instead of a re-stream.
        response["Cache-Control"] = _ASSET_CACHE_CONTROL
        if obj.get("ETag"):
            response["ETag"] = obj["ETag"]
    return response
