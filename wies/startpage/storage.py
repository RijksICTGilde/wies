"""MinIO/S3 access for the ODI start page.

The built Hugo site lives in a MinIO bucket. The bucket is shared with the rest
of Wies; ``STARTPAGE_OBJECT_PREFIX`` (``startpage/``) is this app's namespace in
it. There is one live copy of the site: a publish uploads the new files over it
and then removes whatever the new release no longer contains. A rollback is a
new release upstream.

The web process only reads (``get_object``); the worker also writes
(``upload_site``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def get_client():
    """Build an S3 client pointed at MinIO.

    ``path`` addressing is required: MinIO does not serve virtual-host-style
    ``<bucket>.<host>`` buckets by default.
    """
    return boto3.client(
        "s3",
        endpoint_url=settings.OBJECT_STORE_ENDPOINT,
        aws_access_key_id=settings.OBJECT_STORE_USER,
        aws_secret_access_key=settings.OBJECT_STORE_PASSWORD,
        region_name=settings.OBJECT_STORE_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


class ObjectNotFoundError(Exception):
    """Raised when a requested object is absent."""


class ObjectNotModifiedError(Exception):
    """Raised when a conditional fetch finds the caller's copy still current."""


def ensure_bucket(client=None) -> None:
    """Create the start page bucket if it doesn't exist yet (idempotent).

    Only needed for local/dev seeding — in production the bucket is provisioned
    by ZAD. ``BucketAlreadyOwnedByYou``/``BucketAlreadyExists`` are treated as
    success so repeated seeding is safe.
    """
    client = client or get_client()
    try:
        client.create_bucket(Bucket=settings.OBJECT_STORE_BUCKET_NAME)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise


def _is_missing(error: ClientError) -> bool:
    code = error.response.get("Error", {}).get("Code")
    # MinIO/S3 return NoSuchKey for a missing object; 404 covers head_object.
    return code in {"NoSuchKey", "404", "NoSuchBucket"}


def _is_not_modified(error: ClientError) -> bool:
    # A conditional GET that matches has no error body, so botocore reports the
    # bare HTTP status as the code.
    return error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 304  # noqa: PLR2004 (status code is not magic)


def get_object(key: str, if_none_match: str | None = None, client=None) -> dict:
    """Fetch an object by full key. Raises :class:`ObjectNotFoundError` if absent.

    With ``if_none_match`` (a request's ``If-None-Match`` value) the fetch is
    conditional and raises :class:`ObjectNotModifiedError` when the ETag still
    matches, without transferring the body.

    Returns the raw boto3 response dict (``Body`` is a streaming ``StreamingBody``).
    """
    client = client or get_client()
    extra = {"IfNoneMatch": if_none_match} if if_none_match else {}
    try:
        return client.get_object(Bucket=settings.OBJECT_STORE_BUCKET_NAME, Key=key, **extra)
    except ClientError as error:
        if _is_missing(error):
            raise ObjectNotFoundError(key) from error
        if if_none_match and _is_not_modified(error):
            raise ObjectNotModifiedError(key) from error
        raise


def upload_site(local_root: Path, prefix: str, paths: list[Path] | None = None, client=None) -> int:
    """Make ``<prefix>/`` hold exactly the site under ``local_root``.

    Uploads ``paths`` (default: every file under ``local_root``) to
    ``<prefix>/<relative-path>``, then deletes every other object under
    ``<prefix>/``. The site is replaced in place, so HTML goes last: a page that
    is already live keeps finding its assets while the new ones land.

    Content types are guessed from the filename so the reader can serve assets
    with the right ``Content-Type``. Returns the number of objects uploaded.
    """
    import mimetypes  # noqa: PLC0415 — only needed on the (worker-only) publish path

    client = client or get_client()
    prefix = prefix.rstrip("/")
    if not prefix:
        # The bucket is shared: without a prefix the sweep below would delete
        # every other object in it.
        msg = "upload_site needs a non-empty prefix"
        raise ValueError(msg)

    if paths is None:
        paths = [p for p in local_root.rglob("*") if p.is_file()]
    uploaded = set()
    for path in sorted(paths, key=lambda p: (p.suffix == ".html", p.as_posix())):
        key = f"{prefix}/{path.relative_to(local_root).as_posix()}"
        content_type, _ = mimetypes.guess_type(path.name)
        client.upload_file(
            str(path),
            settings.OBJECT_STORE_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )
        uploaded.add(key)

    _delete_stale(prefix, keep=uploaded, client=client)
    return len(uploaded)


def _delete_stale(prefix: str, keep: set[str], client) -> None:
    """Delete every object under ``<prefix>/`` whose key is not in ``keep``."""
    bucket = settings.OBJECT_STORE_BUCKET_NAME
    stale = [
        obj["Key"]
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=f"{prefix}/")
        for obj in page.get("Contents", [])
        if obj["Key"] not in keep
    ]
    # delete_objects takes at most 1000 keys per call.
    for start in range(0, len(stale), 1000):
        batch = [{"Key": key} for key in stale[start : start + 1000]]
        response = client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
        if response.get("Errors"):
            # A file the release dropped would stay readable; don't report success.
            msg = f"Could not delete {len(response['Errors'])} stale object(s) under {prefix!r}"
            raise RuntimeError(msg)


def iter_body(body, chunk_size: int = 8192) -> Iterator[bytes]:
    """Yield the object body in chunks so serving stays memory-flat.

    ``StreamingBody`` predates ``iter_chunks`` on very old botocore; guard for it.
    """
    if hasattr(body, "iter_chunks"):
        yield from body.iter_chunks(chunk_size)
    else:  # pragma: no cover - defensive
        while chunk := body.read(chunk_size):
            yield chunk
