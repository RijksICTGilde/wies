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

        # Using geolocation, microphone or camera is completely blocked
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content-Security-Policy
        #
        # script-src is 'self' only: all JavaScript is served from static files,
        # with no inline <script> blocks and no on*= handlers (event handling is
        # delegated from external JS), so scripts need neither 'unsafe-inline' nor
        # a nonce. style-src still allows 'unsafe-inline' because RVO components and
        # templates rely on inline style attributes.
        #
        # See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

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
