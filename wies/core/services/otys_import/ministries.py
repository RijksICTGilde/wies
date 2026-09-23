"""Ministry code -> organisaties.overheid.nl mapping.

OTYS labels a vacature's ministry with a short code (e.g. ``"I&W"``). Wies links
an assignment to its primary opdrachtgever through ``OrganizationUnit``, whose
``source_url`` points at organisaties.overheid.nl. This module bridges the two.

We key on the **numeric system id** in the organisaties.overheid.nl URL
(``https://organisaties.overheid.nl/<system_id>/<slug>/``) rather than the full
URL, because the synced ``OrganizationUnit.source_url`` carries a name-derived
slug and a trailing slash that a hand-copied URL would not reproduce exactly.
The system id is the stable part, so the importer matches on it.

This map is deliberately hardcoded: it is the interim bridge until the OTYS API
delivers a resolvable organisation identifier directly.
"""

from __future__ import annotations

# OTYS ministry code -> organisaties.overheid.nl numeric system id.
# Codes are matched case-insensitively and after stripping whitespace; a few
# common spelling variants map to the same id.
MINISTRY_SYSTEM_IDS: dict[str, str] = {
    "az": "123",  # Algemene Zaken
    "buza": "2515",  # Buitenlandse Zaken
    "bz": "2515",
    "bzk": "9632",  # Binnenlandse Zaken en Koninkrijksrelaties
    "def": "4958",  # Defensie
    "defensie": "4958",
    "ez": "10621",  # Economische Zaken (en Klimaat) — one record, EZ and EZK share it
    "ezk": "10621",
    "fin": "68820",  # Financiën
    "financien": "68820",
    "ienw": "112773",  # Infrastructuur en Waterstaat
    "i&w": "112773",
    "jenv": "11906",  # Justitie en Veiligheid
    "j&v": "11906",
    "lvvn": "22387697",  # Landbouw, Visserij, Voedselzekerheid en Natuur
    "lnv": "22387697",
    "ocw": "71852",  # Onderwijs, Cultuur en Wetenschap
    "szw": "19087",  # Sociale Zaken en Werkgelegenheid
    "vws": "8591",  # Volksgezondheid, Welzijn en Sport
    # 2024-era ministries; ids remain live for historical reference.
    "kgg": "29481996",  # Klimaat en Groene Groei
    "vro": "29481991",  # Volkshuisvesting en Ruimtelijke Ordening
    "aenm": "29481986",  # Asiel en Migratie
    "a&m": "29481986",
}


def _normalize(code: str) -> str:
    return (code or "").strip().lower()


def resolve_ministry_system_id(code: str) -> str | None:
    """Returns the organisaties.overheid.nl system id for a ministry code.

    ``None`` when the code is empty or unmapped, so the caller can surface the
    gap as a warning instead of failing the whole import.
    """
    return MINISTRY_SYSTEM_IDS.get(_normalize(code))
