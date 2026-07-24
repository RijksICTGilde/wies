"""Unguessable, URL-facing identifiers for records whose sequential PK must stay
internal (defense against enumeration). Short and readable rather than a 36-char
UUID: a 12-char base58 token carries ~70 bits of entropy, which is unguessable at
this scale, while the unique constraint on the column rules out any collision."""

import secrets

# Base58 (the Bitcoin alphabet): digits + letters minus 0, O, I and l, so the
# token stays unambiguous when read aloud or retyped.
_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

PUBLIC_ID_LENGTH = 12


def generate_public_id() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(PUBLIC_ID_LENGTH))


class PublicIdConverter:
    """URL path converter matching exactly a base58 public_id, so a malformed
    value 404s at routing instead of reaching the database."""

    regex = r"[1-9A-HJ-NP-Za-km-z]{12}"

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return str(value)
