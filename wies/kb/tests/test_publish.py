"""Tests for the KB publish service (GitHub pull -> MinIO upload -> pointer flip)."""

import io
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings

from wies.kb import publish, storage

_SETTINGS = {
    "KB_CONTENT_GITHUB_REPO": "org/content",
    "KB_CONTENT_GITHUB_TOKEN": "tok",
    "OBJECT_STORE_ENDPOINT": "http://minio:9000",
    "OBJECT_STORE_USER": "ak",
    "OBJECT_STORE_PASSWORD": "sk",
    "OBJECT_STORE_BUCKET_NAME": "kb",
}


def _make_tarball(files: dict[str, bytes]) -> bytes:
    """Build an in-memory .tar.gz with the given {path: content} entries."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


@override_settings(**_SETTINGS)
class PublishLatestTest(TestCase):
    def _wire_github(self, release_json, tarball_bytes):
        """Patch requests.get to answer the release API then the asset download."""
        release_resp = MagicMock(status_code=200)
        release_resp.json.return_value = release_json

        asset_resp = MagicMock(status_code=200)
        asset_resp.iter_content.return_value = [tarball_bytes]
        asset_resp.__enter__.return_value = asset_resp
        asset_resp.__exit__.return_value = False

        # First call = release API, second = asset download (streamed).
        return patch.object(publish.requests, "get", side_effect=[release_resp, asset_resp])

    @patch.object(storage, "set_current_prefix")
    @patch.object(storage, "upload_site", return_value=3)
    @patch.object(storage, "get_client")
    def test_publish_uploads_then_flips_pointer(self, mock_client, mock_upload, mock_flip):
        release = {
            "tag_name": "v1.2.3",
            "assets": [{"name": "site.tar.gz", "url": "https://api/asset/1"}],
        }
        tarball = _make_tarball({"index.html": b"<h1>hi</h1>", "css/app.css": b"body{}"})

        with self._wire_github(release, tarball):
            result = publish.publish_latest()

        assert result.release == "v1.2.3"
        assert result.objects == 3
        # Upload happens under the versioned prefix...
        assert mock_upload.call_args.args[1] == "sites/v1.2.3"
        # ...and the pointer flip happens after (atomic publish).
        mock_flip.assert_called_once_with("sites/v1.2.3", client=mock_upload.call_args.kwargs["client"])

    @override_settings(OBJECT_STORE_ENDPOINT="")
    def test_missing_config_raises_before_any_network(self):
        # No requests.get patch: if config validation didn't run first, this would
        # try to hit GitHub. It must fail fast with a config error instead. Keyed on
        # a still-required field (the token is optional, so an empty token alone must
        # NOT trip this).
        with pytest.raises(publish.PublishError, match="not configured"):
            publish.publish_latest()

    @override_settings(KB_CONTENT_GITHUB_TOKEN="")
    @patch.object(storage, "set_current_prefix")
    @patch.object(storage, "upload_site", return_value=1)
    @patch.object(storage, "get_client")
    def test_no_token_sends_no_auth_header(self, mock_client, mock_upload, mock_flip):
        # A public repo publishes token-free: with no token, kb_publish must not send
        # an Authorization header (a bogus/empty one would 401 on a public repo).
        release = {"tag_name": "v9", "assets": [{"name": "site.tar.gz", "url": "https://api/asset/1"}]}
        tarball = _make_tarball({"index.html": b"<h1>hi</h1>"})

        with self._wire_github(release, tarball) as mock_get:
            result = publish.publish_latest()

        assert result.release == "v9"
        # Every GitHub call (release API + asset download) went out without auth.
        for call in mock_get.call_args_list:
            assert "Authorization" not in call.kwargs["headers"]

    @patch.object(storage, "get_client")
    def test_release_without_tarball_asset_raises(self, mock_client):
        release = {"tag_name": "v1", "assets": [{"name": "notes.txt", "url": "u"}]}
        resp = MagicMock(status_code=200)
        resp.json.return_value = release
        with patch.object(publish.requests, "get", return_value=resp), pytest.raises(publish.PublishError):
            publish.publish_latest()

    def test_extract_rejects_traversal_member(self):
        evil = _make_tarball({"../evil.html": b"x"})
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tar_path = tmp_path / "evil.tar.gz"
            tar_path.write_bytes(evil)
            dest = tmp_path / "out"
            dest.mkdir()
            with pytest.raises(publish.PublishError):
                publish._safe_extract(tar_path, dest)
