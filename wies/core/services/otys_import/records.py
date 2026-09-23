"""Intermediate representation for an OTYS import.

These dataclasses describe OTYS entities in OTYS' own terms (a vacancy, a
candidate, a placement) rather than in Wies model terms. They are the single
contract every adapter produces and the importer consumes, so that swapping the
Excel reader for the live OTYS API later touches only the adapter.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class OtysCandidate:
    """A placed person (OTYS candidate) -> a Wies ``Colleague``."""

    email: str
    first_name: str = ""
    infix: str = ""
    last_name: str = ""

    @property
    def name(self) -> str:
        """Composes the display name, skipping empty parts.

        Mirrors the whitespace handling in ``services/sync.py`` so an OTYS
        candidate reads the same however it entered Wies.
        """
        parts = [part for part in (self.first_name, self.infix, self.last_name) if part]
        return " ".join(parts)


@dataclass
class OtysVacancy:
    """An OTYS vacancy -> a Wies ``Assignment`` + ``Service``.

    ``reference`` is the human OTYS reference (e.g. ``"RIG03965"``) that the
    placement points back to and that we use as the idempotency key.
    ``owner_*`` describe the vacature "Consultant", which maps to the Wies
    assignment owner / business manager.
    """

    reference: str
    name: str = ""
    description: str = ""
    role: str = ""  # OTYS "03. Functies" (e.g. "CIO") -> the Service's Skill
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    owner_name: str = ""
    owner_email: str = ""
    ministry_code: str = ""
    status: str = ""


@dataclass
class OtysPlacement:
    """An OTYS placement -> a Wies ``Placement``.

    ``placement_number`` (e.g. ``"ARIPK2370"``) is the idempotency key.
    ``vacancy_reference`` links back to the ``OtysVacancy`` this placement fills.
    """

    placement_number: str
    vacancy_reference: str
    candidate: OtysCandidate
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


@dataclass
class OtysImportBatch:
    """Everything a single import run carries, source-agnostic."""

    vacancies: list[OtysVacancy] = field(default_factory=list)
    placements: list[OtysPlacement] = field(default_factory=list)

    def vacancy_by_reference(self, reference: str) -> OtysVacancy | None:
        """Returns the vacancy a placement links to, or ``None`` if unknown."""
        for vacancy in self.vacancies:
            if vacancy.reference == reference:
                return vacancy
        return None
