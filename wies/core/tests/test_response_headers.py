from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from wies.core.middleware import ResponseHeadersMiddleware


class ResponseHeadersTestBase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _process(self, response):
        """Run a response through the middleware and return it."""
        middleware = ResponseHeadersMiddleware(lambda request: response)
        return middleware(self.factory.get("/"))


class CacheControlHeaderTest(ResponseHeadersTestBase):
    """ResponseHeadersMiddleware must keep HTML documents out of the browser
    cache so a deploy's new hashed static URLs take effect immediately."""

    def test_html_response_gets_no_store(self):
        response = self._process(HttpResponse("<html></html>", content_type="text/html; charset=utf-8"))
        assert response["Cache-Control"] == "no-store"

    def test_non_html_response_is_untouched(self):
        response = self._process(HttpResponse("{}", content_type="application/json"))
        assert not response.has_header("Cache-Control")

    def test_existing_cache_control_is_preserved(self):
        # WhiteNoise stamps static responses with an immutable Cache-Control
        # before this middleware runs; those must not be overwritten.
        response = HttpResponse("body{}", content_type="text/css")
        response["Cache-Control"] = "max-age=315360000, public, immutable"
        result = self._process(response)
        assert result["Cache-Control"] == "max-age=315360000, public, immutable"


class SecurityHeaderTest(ResponseHeadersTestBase):
    """ResponseHeadersMiddleware adds the security headers not covered by
    Django's SecurityMiddleware, on every response regardless of content type."""

    def test_permissions_policy_blocks_sensitive_apis(self):
        response = self._process(HttpResponse("<html></html>", content_type="text/html"))
        assert response["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"

    def test_content_security_policy_locks_down_to_self(self):
        response = self._process(HttpResponse("<html></html>", content_type="text/html"))
        csp = response["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        # Clickjacking protection: the app must not be embeddable in a frame.
        assert "frame-ancestors 'none'" in csp
        # No external origins are whitelisted for any resource type.
        assert "https://" not in csp
        assert "http://" not in csp

    def test_security_headers_set_on_non_html_responses_too(self):
        response = self._process(HttpResponse("{}", content_type="application/json"))
        assert response.has_header("Permissions-Policy")
        assert response.has_header("Content-Security-Policy")
