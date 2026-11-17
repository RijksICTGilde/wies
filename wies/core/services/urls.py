"""Request URL/path helpers.

Stateless helpers for deriving the URL/path a user is actually on,
independent of which backend endpoint a request hit, and for rebuilding a
URL with some query parameters dropped or set.
"""

from typing import TYPE_CHECKING
from urllib.parse import SplitResult, urlsplit

from django.http import QueryDict
from django.utils.http import url_has_allowed_host_and_scheme

if TYPE_CHECKING:
    from collections.abc import Iterable

# The page number in every list URL (the views' ``page_kwarg``). Dropped from
# any URL that changes what the list shows, since page 2 of the old order or
# selection means nothing in the new one.
PAGE_PARAM = "pagina"


def is_local_path(raw: str | None) -> bool:
    """Return whether ``raw`` is a path on this site.

    For client-controlled values that end up in a link or redirect. A plain
    ``startswith("/")`` check is not enough: browsers read ``\\`` as ``/``, so
    ``/\\evil.example`` lands on a foreign origin just like ``//evil.example``.
    Django's check normalises that and rejects any host or scheme; requiring a
    leading ``/`` keeps relative paths out as well.
    """
    return bool(raw) and raw.startswith("/") and url_has_allowed_host_and_scheme(raw, allowed_hosts=None)


def safe_return_path(raw: str | None, fallback: str) -> str:
    """Return ``raw`` only when it is a path on this site, else ``fallback``.

    For a return URL the client sends along (a hidden ``terug_url`` input). It
    ends up in HX-Location/HX-Push-Url, where a protocol-relative "//host" — or
    "/\\host", which browsers read the same way — would point at a foreign origin.
    """
    if is_local_path(raw):
        return raw
    return fallback


def rebuild_url(path: str, query: QueryDict | str, *, drop: Iterable[str] = (), **params) -> str:
    """Rebuild ``path`` from ``query`` with ``drop`` removed and ``params`` set.

    The one routine that rebuilds a URL. ``query`` is a QueryDict (``request.GET``)
    or a raw query string; blank values survive, so ``?nieuwe-opdracht=`` does.
    A param in ``params`` replaces every value the key had. Returns ``path``
    alone when no params remain.

    Only ``query`` may be client input: it is re-encoded. ``path`` is used as
    is, so it must come from the server (``request.path``, ``reverse()``) or
    have passed :func:`is_local_path`.
    """
    rebuilt = (QueryDict(query) if isinstance(query, str) else query).copy()
    for name in drop:
        rebuilt.pop(name, None)
    for key, value in params.items():
        rebuilt[key] = value
    encoded = rebuilt.urlencode()
    return f"{path}?{encoded}" if encoded else path


def hx_current_url(request) -> SplitResult | None:
    """Return the parsed ``HX-Current-URL`` header, or None.

    During an HTMX partial request the backend endpoint (e.g. ``/inline-edit/``)
    differs from the page in the browser; the header carries the URL actually
    shown in the address bar. It is client controlled, so a URL whose path would
    leave the site (``https://host//evil.example``) counts as absent, and the
    scheme and host are stripped: only the path is checked, so the client's
    host must not survive into a ``geturl()``.
    """
    hx_url = request.headers.get("HX-Current-URL", "")
    if not hx_url:
        return None
    parsed = urlsplit(hx_url)
    return parsed._replace(scheme="", netloc="") if is_local_path(parsed.path) else None


def current_page_path(request) -> str:
    """Return the path of the page the user is currently viewing.

    The path of :func:`hx_current_url`, falling back to ``request.path``.
    """
    parsed = hx_current_url(request)
    return parsed.path if parsed else request.path


def url_with_param(request, name: str, value: str) -> str:
    """Return the current page URL with one query parameter set to ``value``.

    Keeps the filters and the search term that are already in the URL: a sort
    choice must not throw away what the user filtered on. Paging is dropped,
    because a new sort makes the old page number meaningless.
    """
    return rebuild_url(current_page_path(request), request.GET, drop=(PAGE_PARAM,), **{name: value})


def url_without_param(request, name: str) -> str:
    """Return the current page URL with one query parameter removed.

    The counterpart of :func:`url_with_param`, for an option that means "back
    to the default": the parameter is absent rather than set to some value the
    view would have to recognise as "no sorting".
    """
    return rebuild_url(current_page_path(request), request.GET, drop=(name, PAGE_PARAM))


def current_page_url_on(request, path: str) -> str:
    """Return the address-bar URL when it is on ``path``, else bare ``path``.

    For a redirect after a sheet that opened over a filtered list: the
    filters, search and order in the address bar survive. ``HX-Current-URL``
    is client controlled, so only its query is used, and only on ``path``.
    Paging is dropped, as in :func:`url_with_param`.
    """
    parsed = hx_current_url(request)
    if parsed is None or parsed.path != path:
        return path
    return rebuild_url(path, parsed.query, drop=(PAGE_PARAM,))


def url_replacing_param(url: str, name: str, **params) -> str:
    """Return ``url`` with the query parameter ``name`` dropped and ``params`` set.

    ``url`` must be a path on this site, as :func:`safe_return_path` returns;
    anything else raises ValueError rather than pass a foreign origin through.
    """
    if not is_local_path(url):
        msg = f"not a local path: {url!r}"
        raise ValueError(msg)
    parsed = urlsplit(url)
    return rebuild_url(parsed.path, parsed.query, drop=(name,), **params)
