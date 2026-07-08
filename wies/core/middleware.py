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
        # Current implementation uses 'unsafe-inline' for scripts and styles.
        # This is a pragmatic choice that still provides protection against loading
        # resources from untrusted external domains.
        #
        # TODO: Refactor to strict nonce-based CSP which requires:
        # - Moving inline event handlers (onclick/onsubmit) to external JS files
        # - Moving inline style attributes to CSS classes
        # - Adding nonce attributes to all <script> and <style> tags
        # - Generating unique nonce per request in this middleware
        #
        # See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
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
