"""Request URL/path helpers.

Stateless helpers for deriving the URL/path a user is actually on,
independent of which backend endpoint a request hit.
"""

from urllib.parse import urlparse


def current_page_path(request) -> str:
    """Return the path of the page the user is currently viewing.

    Prefers the HTMX ``HX-Current-URL`` header (using only its path
    component), falling back to ``request.path``. During an HTMX partial
    request the backend endpoint (e.g. ``/inline-edit/``) differs from the
    page in the browser, so ``request.path`` alone would be wrong; the
    header carries the URL actually shown in the address bar.
    """
    hx_url = request.headers.get("HX-Current-URL", "")
    if hx_url:
        path = urlparse(hx_url).path
        if path:
            return path
    return request.path
