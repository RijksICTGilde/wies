"""Tests for the start page article catch-all view (auth gate, serving, traversal)."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import Client, TestCase
from django.urls import reverse

from wies.startpage import storage
from wies.startpage.views import _resolve_key

User = get_user_model()


class _FakeBody:
    """Minimal StreamingBody stand-in: supports iter_chunks."""

    def __init__(self, data: bytes):
        self._data = data

    def iter_chunks(self, chunk_size=8192):
        for i in range(0, len(self._data), chunk_size):
            yield self._data[i : i + chunk_size]

    def read(self, *_):
        return self._data


def _fake_object(data: bytes, content_type: str) -> dict:
    return {"Body": _FakeBody(data), "ContentType": content_type}


class ResolveKeyTest(TestCase):
    """Unit tests for the path->key mapping (pretty URLs + traversal)."""

    def test_root_resolves_to_index(self):
        assert _resolve_key("", "startpage/v1") == "startpage/v1/index.html"

    def test_directory_resolves_to_index(self):
        assert _resolve_key("onboarding/", "startpage/v1") == "startpage/v1/onboarding/index.html"

    def test_asset_key_is_verbatim(self):
        assert _resolve_key("css/app.css", "startpage/v1") == "startpage/v1/css/app.css"

    def test_traversal_is_rejected(self):
        for bad in ("../../etc/passwd", "a/../../b", "foo/.."):
            with self.subTest(bad=bad), pytest.raises(Http404):
                _resolve_key(bad, "startpage/v1")


class ArticleViewAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_unauthenticated_request_redirects_to_login(self):
        response = self.client.get("/odi-startpagina/onboarding/", follow=False)
        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_unauthenticated_root_redirects_to_login(self):
        # The homepage is gated too.
        response = self.client.get("/odi-startpagina/", follow=False)
        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))


class ArticleViewServingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="reader@rijksoverheid.nl", first_name="Read", last_name="Er")
        self.client.force_login(self.user)

    @patch.object(storage, "get_object")
    def test_root_serves_site_homepage(self, mock_get):
        # The site owns its landing page: the root resolves to <prefix>/index.html,
        # streamed from MinIO.
        mock_get.return_value = _fake_object(b"<h1>Start</h1>", "text/html")
        response = self.client.get("/odi-startpagina/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/html"
        assert b"".join(response.streaming_content) == b"<h1>Start</h1>"
        mock_get.assert_called_once_with("startpage/index.html", if_none_match=None)

    @patch.object(storage, "get_object")
    def test_serves_html_article(self, mock_get):
        mock_get.return_value = _fake_object(b"<h1>Hi</h1>", "text/html")
        response = self.client.get("/odi-startpagina/onboarding/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/html"
        assert b"".join(response.streaming_content) == b"<h1>Hi</h1>"
        mock_get.assert_called_once_with("startpage/onboarding/index.html", if_none_match=None)

    @patch.object(storage, "get_object")
    def test_serves_asset_with_content_type(self, mock_get):
        mock_get.return_value = _fake_object(b"body{}", "text/css")
        response = self.client.get("/odi-startpagina/css/app.css")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/css"
        mock_get.assert_called_once_with("startpage/css/app.css", if_none_match=None)

    @patch.object(storage, "get_object", side_effect=storage.ObjectNotFoundError("x"))
    def test_unknown_key_is_404(self, mock_get):
        response = self.client.get("/odi-startpagina/does-not-exist/")
        assert response.status_code == 404

    def test_extensionless_path_redirects_to_trailing_slash(self):
        response = self.client.get("/odi-startpagina/onboarding", follow=False)
        assert response.status_code == 302
        assert response.url == "/odi-startpagina/onboarding/"

    @patch.object(storage, "get_object")
    def test_html_is_not_cached(self, mock_get):
        mock_get.return_value = {**_fake_object(b"x", "text/html"), "ETag": '"abc"'}
        response = self.client.get("/odi-startpagina/onboarding/")
        assert response["Cache-Control"] == "private, no-store"
        assert "ETag" not in response

    @patch.object(storage, "get_object")
    def test_asset_is_revalidated_by_etag(self, mock_get):
        mock_get.return_value = {**_fake_object(b"body{}", "text/css"), "ETag": '"abc"'}
        response = self.client.get("/odi-startpagina/css/app.css")
        assert response["Cache-Control"] == "private, no-cache"
        assert response["ETag"] == '"abc"'

    @patch.object(storage, "get_object", side_effect=storage.ObjectNotModifiedError("x"))
    def test_matching_etag_is_304_without_body(self, mock_get):
        response = self.client.get("/odi-startpagina/css/app.css", headers={"If-None-Match": '"abc"'})
        assert response.status_code == 304
        assert response.content == b""
        mock_get.assert_called_once_with("startpage/css/app.css", if_none_match='"abc"')

    @patch.object(storage, "get_object", side_effect=storage.ObjectNotModifiedError("x"))
    def test_weakened_etag_still_matches(self, mock_get):
        # A compressing proxy turns our ETag into a weak one; MinIO wants the strong form.
        response = self.client.get("/odi-startpagina/css/app.css", headers={"If-None-Match": 'W/"abc"'})
        assert response.status_code == 304
        mock_get.assert_called_once_with("startpage/css/app.css", if_none_match='"abc"')

    @patch.object(storage, "get_object")
    def test_only_get_is_allowed(self, mock_get):
        for method in ("post", "head", "put", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)("/odi-startpagina/css/app.css")
                assert response.status_code == 405
        mock_get.assert_not_called()
