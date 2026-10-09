"""Tests for the start page publish service (GitHub pull -> unpack -> replace the site in MinIO)."""

import io
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase, override_settings

from wies.startpage import publish, storage

_SETTINGS = {
    "STARTPAGE_CONTENT_GITHUB_REPO": "org/content",
    "STARTPAGE_CONTENT_GITHUB_TOKEN": "tok",
    "OBJECT_STORE_ENDPOINT": "http://minio:9000",
    "OBJECT_STORE_USER": "ak",
    "OBJECT_STORE_PASSWORD": "sk",
    "OBJECT_STORE_BUCKET_NAME": "startpage",
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

    @patch.object(storage, "upload_site", return_value=2)
    @patch.object(storage, "get_client")
    def test_publish_replaces_site_under_the_prefix(self, mock_client, mock_upload):
        release = {
            "tag_name": "v1.2.3",
            "assets": [{"name": "site.tar.gz", "url": "https://api/asset/1"}],
        }
        tarball = _make_tarball({"index.html": b"<h1>hi</h1>", "css/app.css": b"body{}"})

        with self._wire_github(release, tarball):
            result = publish.publish_latest()

        assert result.release == "v1.2.3"
        assert result.objects == 2
        assert result.skipped == 0
        # One live copy: the release tag is not part of the key.
        assert mock_upload.call_args.args[1] == "startpage"
        assert sorted(p.name for p in mock_upload.call_args.kwargs["paths"]) == ["app.css", "index.html"]

    @patch.object(storage, "upload_site", return_value=1)
    @patch.object(storage, "get_client")
    def test_dotfiles_and_unknown_types_are_skipped(self, mock_client, mock_upload):
        release = {"tag_name": "v1", "assets": [{"name": "site.tar.gz", "url": "u"}]}
        tarball = _make_tarball(
            {
                "public/index.html": b"<h1>hi</h1>",
                "public/.env": b"SECRET=1",
                "public/.git/config": b"[core]",
                "public/backup.sql": b"select 1",
                "public/run.sh": b"#!/bin/sh",
            }
        )

        with self._wire_github(release, tarball):
            result = publish.publish_latest()

        assert [p.name for p in mock_upload.call_args.kwargs["paths"]] == ["index.html"]
        assert result.skipped == 4

    @patch.object(storage, "upload_site")
    @patch.object(storage, "get_client")
    def test_release_without_publishable_files_leaves_site_alone(self, mock_client, mock_upload):
        # upload_site replaces the live site, so it must not run for an empty release.
        release = {"tag_name": "v1", "assets": [{"name": "site.tar.gz", "url": "u"}]}
        with (
            self._wire_github(release, _make_tarball({"notes.sql": b"x"})),
            pytest.raises(publish.PublishError, match="no publishable files"),
        ):
            publish.publish_latest()
        mock_upload.assert_not_called()

    @override_settings(STARTPAGE_OBJECT_PREFIX="")
    def test_empty_prefix_is_refused(self):
        # The bucket is shared; an empty prefix would let a publish sweep all of it.
        with pytest.raises(publish.PublishError, match="STARTPAGE_OBJECT_PREFIX"):
            publish.publish_latest()

    @patch.object(storage, "get_client")
    def test_asset_reported_too_large_is_not_downloaded(self, mock_client):
        release = {
            "tag_name": "v1",
            "assets": [{"name": "site.tar.gz", "url": "u", "size": publish.MAX_DOWNLOAD_BYTES + 1}],
        }
        resp = MagicMock(status_code=200)
        resp.json.return_value = release
        with (
            patch.object(publish.requests, "get", return_value=resp) as mock_get,
            pytest.raises(publish.PublishError, match="larger than"),
        ):
            publish.publish_latest()
        # Only the release lookup went out.
        assert mock_get.call_count == 1

    @patch.object(publish, "MAX_DOWNLOAD_BYTES", 10)
    @patch.object(storage, "get_client")
    def test_download_is_cut_off_at_the_cap(self, mock_client):
        # The reported size is absent/wrong; the stream itself is counted.
        release = {"tag_name": "v1", "assets": [{"name": "site.tar.gz", "url": "u"}]}
        with self._wire_github(release, b"x" * 11), pytest.raises(publish.PublishError, match="larger than"):
            publish.publish_latest()

    @override_settings(OBJECT_STORE_ENDPOINT="")
    def test_missing_config_raises_before_any_network(self):
        # No requests.get patch: if config validation didn't run first, this would
        # try to hit GitHub. It must fail fast with a config error instead. Keyed on
        # a still-required field (the token is optional, so an empty token alone must
        # NOT trip this).
        with pytest.raises(publish.PublishError, match="not configured"):
            publish.publish_latest()

    @override_settings(STARTPAGE_CONTENT_GITHUB_TOKEN="")
    @patch.object(storage, "upload_site", return_value=1)
    @patch.object(storage, "get_client")
    def test_no_token_sends_no_auth_header(self, mock_client, mock_upload):
        # A public repo publishes token-free: with no token, startpage_publish must not send
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

    def _extract(self, tarball: bytes) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tar_path = Path(tmp.name) / "site.tar.gz"
        tar_path.write_bytes(tarball)
        dest = Path(tmp.name) / "out"
        dest.mkdir()
        publish._safe_extract(tar_path, dest)
        return dest

    @patch.object(publish, "MAX_ARCHIVE_MEMBERS", 2)
    def test_extract_rejects_too_many_members(self):
        tarball = _make_tarball({"a.html": b"x", "b.html": b"x", "c.html": b"x"})
        with pytest.raises(publish.PublishError, match="more than 2 entries"):
            self._extract(tarball)

    @patch.object(publish, "MAX_EXTRACTED_BYTES", 10)
    def test_extract_rejects_oversized_content_before_writing(self):
        tarball = _make_tarball({"a.html": b"x" * 6, "b.html": b"x" * 6})
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tar_path = Path(tmp.name) / "site.tar.gz"
        tar_path.write_bytes(tarball)
        dest = Path(tmp.name) / "out"
        dest.mkdir()
        with pytest.raises(publish.PublishError, match="unpacks to more than"):
            publish._safe_extract(tar_path, dest)
        assert list(dest.iterdir()) == []

    def test_extract_rejects_symlink_out_of_tree(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            link = tarfile.TarInfo(name="passwd.html")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tar.addfile(link)
        with pytest.raises(tarfile.FilterError):
            self._extract(buf.getvalue())


@override_settings(OBJECT_STORE_BUCKET_NAME="bucket")
class UploadSiteTest(TestCase):
    def _site(self, files: dict[str, str]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, content in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(content)
        return root

    def _client(self, existing_keys: list[str]) -> MagicMock:
        client = MagicMock()
        client.get_paginator.return_value.paginate.return_value = [{"Contents": [{"Key": k} for k in existing_keys]}]
        client.delete_objects.return_value = {}
        return client

    def test_uploads_html_last_and_deletes_what_the_release_dropped(self):
        root = self._site({"index.html": "<h1>hi</h1>", "css/app.css": "body{}", "z.js": "1"})
        client = self._client(
            ["startpage/index.html", "startpage/css/app.css", "startpage/old/index.html", "startpage/CURRENT"]
        )

        count = storage.upload_site(root, "startpage", client=client)

        assert count == 3
        uploaded = [call.args[2] for call in client.upload_file.call_args_list]
        # Assets land before the page that references them.
        assert uploaded == ["startpage/css/app.css", "startpage/z.js", "startpage/index.html"]
        # The sweep stays inside the start page's own namespace in the shared bucket.
        client.get_paginator.return_value.paginate.assert_called_once_with(Bucket="bucket", Prefix="startpage/")
        deleted = client.delete_objects.call_args.kwargs["Delete"]["Objects"]
        assert deleted == [{"Key": "startpage/old/index.html"}, {"Key": "startpage/CURRENT"}]

    def test_nothing_stale_means_no_delete_call(self):
        root = self._site({"index.html": "x"})
        client = self._client(["startpage/index.html"])
        storage.upload_site(root, "startpage", client=client)
        client.delete_objects.assert_not_called()

    def test_empty_prefix_is_refused_before_touching_the_bucket(self):
        root = self._site({"index.html": "x"})
        client = self._client([])
        for prefix in ("", "/"):
            with self.subTest(prefix=prefix), pytest.raises(ValueError, match="non-empty prefix"):
                storage.upload_site(root, prefix, client=client)
        client.upload_file.assert_not_called()
        client.delete_objects.assert_not_called()

    def test_failed_delete_is_not_reported_as_success(self):
        root = self._site({"index.html": "x"})
        client = self._client(["startpage/old.html"])
        client.delete_objects.return_value = {"Errors": [{"Key": "startpage/old.html", "Code": "AccessDenied"}]}
        with pytest.raises(RuntimeError, match="stale"):
            storage.upload_site(root, "startpage", client=client)
