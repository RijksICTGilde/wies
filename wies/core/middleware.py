from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# Content-Security-Policy
#
# script-src is 'self' only: all JavaScript is served from static files,
# with no inline <script> blocks and no on*= handlers (event handling is
# delegated from external JS), so scripts need neither 'unsafe-inline' nor
# a nonce. style-src still allows 'unsafe-inline' because RVO components and
# templates rely on inline style attributes.
#
# See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)

# Using geolocation, microphone or camera is completely blocked
PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"


def add_security_headers(headers: MutableMapping[str, str], path: str, url: str) -> None:
    """Put the security headers on WhiteNoise's own responses.

    WhiteNoise sits above this middleware and answers static requests itself,
    so without this hook those responses carry no CSP at all. That matters for
    one of them: the WCAG report at /toegankelijkheid/onderzoek/ is a full HTML
    document an anonymous visitor opens directly.

    Signature is WhiteNoise's ``add_headers_function``; ``headers`` is mutated
    in place.
    """
    headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    headers["Permissions-Policy"] = PERMISSIONS_POLICY
    # XFrameOptionsMiddleware also sits below WhiteNoise, so spell it out here.
    headers["X-Frame-Options"] = "DENY"


class ResponseHeadersMiddleware:
    """
    Post-processes every response to add headers not covered by Django's
    SecurityMiddleware: security headers (Permissions-Policy,
    Content-Security-Policy) and cache headers (no-store on HTML documents).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response["Permissions-Policy"] = PERMISSIONS_POLICY
        response["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

        # Never cache HTML documents. They embed content-hashed static URLs
        # (WhiteNoise ManifestStaticFilesStorage), so a browser that reuses a
        # stale HTML page after a deploy would request old hashes that no longer
        # exist on the new container -> 404 -> unstyled page. Django sets no
        # Cache-Control on HTML by default, which lets browsers heuristically
        # cache it; force no-store so every navigation fetches fresh HTML while
        # the immutable hashed assets stay aggressively cached.
        #
        # Guard: skip anything already carrying Cache-Control (e.g. WhiteNoise
        # static responses) and only touch HTML responses.
        if not response.has_header("Cache-Control") and "text/html" in response.get("Content-Type", ""):
            response["Cache-Control"] = "no-store"

        return response
