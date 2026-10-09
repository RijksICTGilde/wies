"""Pull the latest built start page site from GitHub and publish it to MinIO.

The private content repo's CI attaches the built Hugo site as a ``.tar.gz`` asset
on each GitHub release. This module (run on the ``db_worker`` via the
``startpage_publish`` task) downloads that asset, unpacks it and replaces the live
site under ``STARTPAGE_OBJECT_PREFIX`` with it. CI never gets credentials to our
infra — we pull.

The content repo is trusted to write articles, not to be free of mistakes: the
archive is size-capped, extracted with the ``data`` filter, and only files of a
known web type are published.
"""

from __future__ import annotations

import logging
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from django.conf import settings

from wies.startpage import storage

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"
# Per-read timeout; the download as a whole is bounded by _DOWNLOAD_DEADLINE_SECONDS.
_DOWNLOAD_TIMEOUT = 30
_DOWNLOAD_DEADLINE_SECONDS = 300

# Bounds on what one release may make the worker download and unpack. Far above
# a text-and-images site, far below what fills the worker's disk.
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000

# Only these file types are published. Anything else in the archive (and any
# dotfile or dot-directory, e.g. a stray .env or .git/) is skipped, so an
# upstream packaging mistake doesn't end up readable by every user.
PUBLISHABLE_SUFFIXES = frozenset(
    {
        ".html", ".css", ".js", ".mjs", ".json", ".xml", ".txt", ".webmanifest",
        ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
        ".woff", ".woff2", ".ttf", ".pdf",
    }
)  # fmt: skip

# The task command name + timeout, declared next to the work they describe and
# imported by the staff view that enqueues it.
STARTPAGE_PUBLISH_COMMAND = "startpage_publish"
STARTPAGE_PUBLISH_TIMEOUT_MINUTES = 15


@dataclass
class PublishResult:
    release: str
    objects: int
    skipped: int


class PublishError(Exception):
    """Raised when the release can't be fetched or is malformed."""


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Only authenticate when a token is configured. A private content repo needs
    # one; a public repo is readable anonymously, and sending an *invalid* token
    # there fails with 401 (worse than sending none).
    if settings.STARTPAGE_CONTENT_GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.STARTPAGE_CONTENT_GITHUB_TOKEN}"
    return headers


def _latest_release() -> dict:
    url = f"{_GITHUB_API}/repos/{settings.STARTPAGE_CONTENT_GITHUB_REPO}/releases/latest"
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
    too_large = f"Asset {asset['name']!r} is larger than {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB"
    if asset.get("size", 0) > MAX_DOWNLOAD_BYTES:
        raise PublishError(too_large)

    # The asset download needs the octet-stream Accept header, not the JSON one.
    headers = {**_headers(), "Accept": "application/octet-stream"}
    deadline = time.monotonic() + _DOWNLOAD_DEADLINE_SECONDS
    with requests.get(asset["url"], headers=headers, timeout=_DOWNLOAD_TIMEOUT, stream=True) as response:
        if response.status_code != 200:  # noqa: PLR2004 (status code is not magic)
            msg = f"Could not download asset {asset['name']!r} ({response.status_code})"
            raise PublishError(msg)
        written = 0
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                # The size GitHub reports is only a claim; count what arrives.
                written += len(chunk)
                if written > MAX_DOWNLOAD_BYTES:
                    raise PublishError(too_large)
                if time.monotonic() > deadline:
                    msg = f"Downloading asset {asset['name']!r} took longer than {_DOWNLOAD_DEADLINE_SECONDS} seconds"
                    raise PublishError(msg)
                handle.write(chunk)


def _safe_extract(tar_path: Path, dest: Path) -> None:
    """Extract a tarball, refusing an oversized one or a member that would escape ``dest``."""
    root = dest.resolve()
    with tarfile.open(tar_path, "r:gz") as tar:
        # Walk the headers before writing anything: a member's declared size is
        # known before its data is read, so a decompression bomb is refused here.
        total = 0
        for count, member in enumerate(tar, start=1):
            if count > MAX_ARCHIVE_MEMBERS:
                msg = f"Archive has more than {MAX_ARCHIVE_MEMBERS} entries"
                raise PublishError(msg)
            total += member.size
            if total > MAX_EXTRACTED_BYTES:
                msg = f"Archive unpacks to more than {MAX_EXTRACTED_BYTES // (1024 * 1024)} MB"
                raise PublishError(msg)
            target = (dest / member.name).resolve()
            if target != root and not target.is_relative_to(root):
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


def _publishable_files(site_root: Path) -> tuple[list[Path], list[str]]:
    """Split the site's files into those to publish and the (relative) ones to skip."""
    publish: list[Path] = []
    skipped: list[str] = []
    for path in sorted(p for p in site_root.rglob("*") if p.is_file()):
        rel = path.relative_to(site_root)
        hidden = any(part.startswith(".") for part in rel.parts)
        if hidden or path.suffix.lower() not in PUBLISHABLE_SUFFIXES:
            skipped.append(rel.as_posix())
        else:
            publish.append(path)
    return publish, skipped


def _require_config() -> None:
    """Fail with a clear message if the start page secrets aren't configured.

    Validated here (not at worker boot) so a missing start page secret grounds only this
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
        "STARTPAGE_CONTENT_GITHUB_REPO": settings.STARTPAGE_CONTENT_GITHUB_REPO,
        # The bucket is shared and a publish deletes what it didn't upload under
        # this prefix; empty would mean "the whole bucket".
        "STARTPAGE_OBJECT_PREFIX": settings.STARTPAGE_OBJECT_PREFIX.strip("/"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        msg = f"Start page publish is not configured; missing: {', '.join(missing)}"
        raise PublishError(msg)


def publish_latest() -> PublishResult:
    """Download the latest release's site and replace the live site in MinIO with it."""
    _require_config()
    release = _latest_release()
    tag = release.get("tag_name") or ""
    asset = _pick_asset(release)

    client = storage.get_client()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tarball = tmp_path / "site.tar.gz"
        _download_asset(asset, tarball)

        extracted = tmp_path / "site"
        extracted.mkdir()
        _safe_extract(tarball, extracted)

        site_root = _site_root(extracted)
        files, skipped = _publishable_files(site_root)
        # Checked before the upload: publishing replaces the live site, and an
        # empty release must not wipe it.
        if not files:
            msg = f"Release {tag!r} artifact contained no publishable files"
            raise PublishError(msg)
        if skipped:
            # Names capped: a whole mis-packaged directory shouldn't flood the log.
            logger.warning("Release %r: %d file(s) not published, e.g. %s", tag, len(skipped), ", ".join(skipped[:20]))

        count = storage.upload_site(site_root, settings.STARTPAGE_OBJECT_PREFIX, paths=files, client=client)

    return PublishResult(release=tag, objects=count, skipped=len(skipped))
