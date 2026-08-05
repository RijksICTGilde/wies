"""Request URL/path helpers.

Stateless helpers for deriving the URL/path a user is actually on,
independent of which backend endpoint a request hit.
"""

from urllib.parse import urlencode, urlparse


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


def url_with_param(request, name: str, value: str) -> str:
    """Return the current page URL with one query parameter set to ``value``.

    Keeps the filters and the search term that are already in the URL: a sort
    choice must not throw away what the user filtered on. Paging is dropped,
    because a new sort makes the old page number meaningless.
    """
    params = request.GET.copy()
    params[name] = value
    params.pop("page", None)
    query = urlencode(params, doseq=True)
    path = current_page_path(request)
    return f"{path}?{query}" if query else path


def url_without_param(request, name: str) -> str:
    """Return the current page URL with one query parameter removed.

    The counterpart of :func:`url_with_param`, for an option that means "back
    to the default": the parameter is absent rather than set to some value the
    view would have to recognise as "no sorting".
    """
    params = request.GET.copy()
    params.pop(name, None)
    params.pop("page", None)
    query = urlencode(params, doseq=True)
    path = current_page_path(request)
    return f"{path}?{query}" if query else path
