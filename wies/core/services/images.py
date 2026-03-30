import hashlib


def process_profile_picture(image_bytes: bytes) -> tuple[bytes, str, str]:
    """Compute SHA-256 hash for raw image bytes.

    Returns (image_bytes, content_type, sha256_hash).
    """
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    return image_bytes, "image/jpeg", image_hash
