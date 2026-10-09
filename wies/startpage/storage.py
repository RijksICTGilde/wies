"""MinIO/S3 access for the ODI start page.

The built Hugo site lives in a MinIO bucket. The bucket is shared with the rest
of Wies; ``startpage/`` is this app's namespace in it. Each publish uploads the site under
its own prefix (``startpage/<release-tag>/``) and then flips a tiny pointer object
(``STARTPAGE_CURRENT_POINTER_KEY``) that holds the name of the active prefix. Readers
resolve the active prefix through that pointer, so they never see a half-written
site and a rollback is just repointing.

The web process only reads (``get_current_prefix`` + ``get_object``); the worker
also writes (``upload_site`` + ``set_current_prefix``).
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
    """Raised when a requested object (or the pointer) is absent."""


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


def get_current_prefix(client=None) -> str:
    """Return the active site prefix (e.g. ``startpage/v1.2.3``), no trailing slash.

    Raises :class:`ObjectNotFoundError` if nothing has been published yet.
    """
    client = client or get_client()
    try:
        obj = client.get_object(Bucket=settings.OBJECT_STORE_BUCKET_NAME, Key=settings.STARTPAGE_CURRENT_POINTER_KEY)
    except ClientError as error:
        if _is_missing(error):
            raise ObjectNotFoundError(settings.STARTPAGE_CURRENT_POINTER_KEY) from error
        raise
    return obj["Body"].read().decode("utf-8").strip().rstrip("/")


def set_current_prefix(prefix: str, client=None) -> None:
    """Point the start page at ``prefix`` (atomic publish flip)."""
    client = client or get_client()
    client.put_object(
        Bucket=settings.OBJECT_STORE_BUCKET_NAME,
        Key=settings.STARTPAGE_CURRENT_POINTER_KEY,
        Body=prefix.rstrip("/").encode("utf-8"),
        ContentType="text/plain",
    )


def get_object(key: str, client=None) -> dict:
    """Fetch an object by full key. Raises :class:`ObjectNotFoundError` if absent.

    Returns the raw boto3 response dict (``Body`` is a streaming ``StreamingBody``).
    """
    client = client or get_client()
    try:
        return client.get_object(Bucket=settings.OBJECT_STORE_BUCKET_NAME, Key=key)
    except ClientError as error:
        if _is_missing(error):
            raise ObjectNotFoundError(key) from error
        raise


def upload_site(local_root: Path, prefix: str, client=None) -> int:
    """Upload every file under ``local_root`` to ``<prefix>/<relative-path>``.

    Content types are guessed from the filename so the reader can serve assets
    with the right ``Content-Type``. Returns the number of objects uploaded.
    """
    import mimetypes  # noqa: PLC0415 — only needed on the (worker-only) publish path

    client = client or get_client()
    prefix = prefix.rstrip("/")
    count = 0
    for path in sorted(p for p in local_root.rglob("*") if p.is_file()):
        rel = path.relative_to(local_root).as_posix()
        content_type, _ = mimetypes.guess_type(path.name)
        client.upload_file(
            str(path),
            settings.OBJECT_STORE_BUCKET_NAME,
            f"{prefix}/{rel}",
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )
        count += 1
    return count


def iter_body(body, chunk_size: int = 8192) -> Iterator[bytes]:
    """Yield the object body in chunks so serving stays memory-flat.

    ``StreamingBody`` predates ``iter_chunks`` on very old botocore; guard for it.
    """
    if hasattr(body, "iter_chunks"):
        yield from body.iter_chunks(chunk_size)
    else:  # pragma: no cover - defensive
        while chunk := body.read(chunk_size):
            yield chunk
