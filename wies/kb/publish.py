"""Pull the latest built KB site from GitHub and publish it to MinIO.

The private content repo's CI attaches the built Hugo site as a ``.tar.gz`` asset
on each GitHub release. This module (run on the ``db_worker`` via the
``kb_publish`` task) downloads that asset, unpacks it, uploads every file under a
fresh ``sites/<release-tag>`` prefix, then flips the current-pointer so readers
switch over atomically. CI never gets credentials to our infra — we pull.
"""

from __future__ import annotations

import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
from django.conf import settings

from wies.kb import storage

_GITHUB_API = "https://api.github.com"
_DOWNLOAD_TIMEOUT = 300
_SITE_PREFIX_ROOT = "sites"


@dataclass
class PublishResult:
    release: str
    objects: int


class PublishError(Exception):
    """Raised when the release can't be fetched or is malformed."""


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Only authenticate when a token is configured. A public content repo is
    # readable anonymously; sending an *invalid* token there fails with 401 (worse
    # than sending none). A private repo (later) provides a token and authenticates.
    if settings.KB_CONTENT_GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.KB_CONTENT_GITHUB_TOKEN}"
    return headers


def _latest_release() -> dict:
    url = f"{_GITHUB_API}/repos/{settings.KB_CONTENT_GITHUB_REPO}/releases/latest"
    response = requests.get(url, headers=_headers(), timeout=30)
    if response.status_code != 200:  # noqa: PLR2004 (status code is not magic)
        msg = f"Could not fetch latest release ({response.status_code})"
        raise PublishError(msg)
    return response.json()


def _pick_asset(release: dict) -> dict:
    """Pick the built-site tarball from a release's assets."""
    assets = release.get("assets", [])
    tarballs = [a for a in assets if a.get("name", "").endswith((".tar.gz", ".tgz"))]
    if not tarballs:
        msg = f"Release {release.get('tag_name')!r} has no .tar.gz asset"
        raise PublishError(msg)
    # A release should carry exactly one site artifact; if several, take the first
    # by name for determinism.
    return sorted(tarballs, key=lambda a: a["name"])[0]


def _download_asset(asset: dict, dest: Path) -> None:
    # The asset download needs the octet-stream Accept header, not the JSON one.
    headers = {**_headers(), "Accept": "application/octet-stream"}
    with requests.get(asset["url"], headers=headers, timeout=_DOWNLOAD_TIMEOUT, stream=True) as response:
        if response.status_code != 200:  # noqa: PLR2004 (status code is not magic)
            msg = f"Could not download asset {asset['name']!r} ({response.status_code})"
            raise PublishError(msg)
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                handle.write(chunk)


def _safe_extract(tar_path: Path, dest: Path) -> None:
    """Extract a tarball, refusing any member that would escape ``dest``."""
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest.resolve()) + "/") and target != dest.resolve():
                msg = f"Unsafe path in archive: {member.name!r}"
                raise PublishError(msg)
        # Python 3.14: filter="data" also strips absolute paths/links defensively.
        tar.extractall(dest, filter="data")


def _site_root(extracted: Path) -> Path:
    """Locate the Hugo output root inside the extracted tree.

    CI may wrap the site in a single top-level directory (``public/`` or the
    release name); unwrap that so keys aren't prefixed with it.
    """
    entries = [p for p in extracted.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extracted


def _require_config() -> None:
    """Fail with a clear message if the KB secrets aren't configured.

    Validated here (not at worker boot) so a missing KB secret grounds only this
    task, not the whole multi-purpose worker.
    """
    # The token is intentionally NOT required: a public content repo publishes
    # token-free (see _headers). Only the repo name and MinIO target are mandatory.
    # Keyed by the env var an operator sets, so the "missing" message is actionable.
    # ENDPOINT is composed from OBJECT_STORE_HOST + OBJECT_STORE_PORT (see base.py).
    required = {
        "OBJECT_STORE_HOST/PORT": settings.OBJECT_STORE_ENDPOINT,
        "OBJECT_STORE_USER": settings.OBJECT_STORE_USER,
        "OBJECT_STORE_PASSWORD": settings.OBJECT_STORE_PASSWORD,
        "OBJECT_STORE_BUCKET_NAME": settings.OBJECT_STORE_BUCKET_NAME,
        "KB_CONTENT_GITHUB_REPO": settings.KB_CONTENT_GITHUB_REPO,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        msg = f"KB publish is not configured; missing: {', '.join(missing)}"
        raise PublishError(msg)


def publish_latest() -> PublishResult:
    """Download the latest release's site and publish it to MinIO atomically."""
    _require_config()
    release = _latest_release()
    tag = release.get("tag_name") or "latest"
    asset = _pick_asset(release)

    client = storage.get_client()
    # A slash-free prefix segment keeps object keys clean.
    prefix = f"{_SITE_PREFIX_ROOT}/{tag.replace('/', '-')}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tarball = tmp_path / "site.tar.gz"
        _download_asset(asset, tarball)

        extracted = tmp_path / "site"
        extracted.mkdir()
        _safe_extract(tarball, extracted)

        count = storage.upload_site(_site_root(extracted), prefix, client=client)

    if count == 0:
        msg = f"Release {tag!r} artifact contained no files"
        raise PublishError(msg)

    # Flip last: readers only switch once every object is uploaded.
    storage.set_current_prefix(prefix, client=client)
    return PublishResult(release=tag, objects=count)
