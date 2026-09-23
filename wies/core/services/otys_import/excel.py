"""Excel adapter: a manual OTYS ``.xlsx`` export -> ``OtysImportBatch``.

This is the only module that knows about spreadsheets. It is written to survive
layout drift, because the sample already moved columns between revisions and the
brief is explicit that "the exact location in the excel will not" stay the same:

- Tables are found by their section-marker cell ("Vacature module",
  "Plaatsingenmodule"), not by fixed row numbers.
- Within a table, the row after the marker is treated as the header and turned
  into a ``{logical_field: column_index}`` map via an alias table, so columns may
  be reordered or renamed within known variants without code changes.
- Header labels are normalised (whitespace collapsed, all dash variants folded to
  a plain hyphen) before matching, so a "Kandidaat [en-dash] Email" header with an
  en-dash matches the same field as a plain-hyphen one.

When the OTYS API replaces this file, a sibling ``api`` adapter will build the
same ``OtysImportBatch`` and nothing downstream changes.
"""

from __future__ import annotations

import datetime
import io
import re

import openpyxl

from wies.core.services.otys_import.records import (
    OtysCandidate,
    OtysImportBatch,
    OtysPlacement,
    OtysVacancy,
)


class ExcelParseError(Exception):
    """Raised with a Dutch, user-facing message when the workbook can't be read."""


# Section markers that identify the two stacked tables in the source sheet.
VACANCY_MARKER = "vacature module"
PLACEMENT_MARKER = "plaatsingenmodule"

# Logical field -> the header labels (normalised) that may carry it, in
# preference order: when several of these columns are present, the reader takes
# the first one with a non-empty value. Add variants here as new exports surface
# them; the parser needs no other change.
VACANCY_ALIASES: dict[str, list[str]] = {
    "reference": ["referentie"],
    "name": ["functietitel"],
    # OTYS puts the opdrachtomschrijving in "Bedrijfscultuur"; "Functie
    # omschrijving" is the documented field and kept as a fallback.
    "description": ["bedrijfscultuur", "functie omschrijving"],
    "role": ["03. functies", "functies", "functie"],
    "start_date": ["startdatum"],
    "end_date": ["einddatum"],
    "owner_name": ["consultant"],
    "owner_email": ["consultant email", "consultant e-mail"],
    "ministry_code": ["02. ministerie(s)", "ministerie(s)", "ministerie"],
    "status": ["status"],
}

PLACEMENT_ALIASES: dict[str, list[str]] = {
    "placement_number": ["plaatsing - plaatsingsnummer", "plaatsingsnummer"],
    "vacancy_reference": ["plaatsing - vacature referentienummer", "vacature referentienummer"],
    "last_name": ["kandidaat - achternaam", "achternaam"],
    "infix": ["kandidaat - tussenvoegsel", "tussenvoegsel"],
    "first_name": ["kandidaat - voornaam", "voornaam"],
    "email": ["kandidaat - email", "kandidaat - e-mail", "email", "e-mail"],
    "start_date": ["plaatsing - startdatum", "startdatum"],
    "end_date": ["plaatsing - einddatum", "einddatum"],
}

# Fields that must be present as columns for the import to make sense.
REQUIRED_VACANCY_FIELDS = {"reference", "name", "owner_email", "ministry_code"}
REQUIRED_PLACEMENT_FIELDS = {"placement_number", "vacancy_reference", "email"}


def _normalize_header(value: object) -> str:
    """Folds dash variants, collapses whitespace and lowercases a header label."""
    text = "" if value is None else str(value)
    # Fold the Unicode dash block (hyphen U+2010 .. horizontal bar U+2015) and the
    # minus sign (U+2212) to a plain hyphen, so an en-dash header matches a plain one.
    text = re.sub("[‐-―−]", "-", text)  # noqa: RUF001 (ambiguous chars) - the point is to fold those very characters
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _to_date(value: object) -> datetime.date | None:
    """Accepts openpyxl ``datetime`` cells and ``DD-MM-YYYY`` strings."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # Reuse the DD-MM-YYYY convention of the existing CSV importer.
    day, month, year = text.split(" ")[0].split("-")
    return datetime.date(int(year), int(month), int(day))


def _cell(value: object) -> str:
    return "" if value is None else str(value).strip()


def _clean_name_part(value: object) -> str:
    """Strips OTYS' trailing parenthetical suffixes from a name part.

    OTYS decorates the achternaam with a candidate id and a domain tag, e.g.
    ``"Kolkman (36) (LenB)"``. Only the name itself belongs in Wies, so every
    trailing ``(...)`` group is removed: ``"Kolkman (36) (LenB)" -> "Kolkman"``.
    """
    text = _cell(value)
    while True:
        stripped = re.sub(r"\s*\([^()]*\)\s*$", "", text).strip()
        if stripped == text:
            return text
        text = stripped


def _find_marker_row(rows: list[list], marker: str) -> int | None:
    """Returns the index of the row whose first non-empty cell equals ``marker``."""
    for index, row in enumerate(rows):
        for cell in row:
            if _normalize_header(cell) == marker:
                return index
            if _cell(cell):
                break  # marker must be the row's first filled cell
    return None


def _build_column_map(header_row: list, aliases: dict[str, list[str]]) -> dict[str, list[int]]:
    """Maps each logical field to its column indices, in alias-preference order.

    A field can resolve to several columns (e.g. description -> Bedrijfscultuur
    then Functie omschrijving); the value reader picks the first non-empty one.
    """
    # label -> column index, so we can look columns up per alias in order.
    label_to_column: dict[str, int] = {}
    for column_index, cell in enumerate(header_row):
        label = _normalize_header(cell)
        if label and label not in label_to_column:
            label_to_column[label] = column_index

    column_map: dict[str, list[int]] = {}
    for field_name, labels in aliases.items():
        indices = [label_to_column[label] for label in labels if label in label_to_column]
        if indices:
            column_map[field_name] = indices
    return column_map


def _read_table(rows: list[list], marker: str, aliases: dict[str, list[str]], required: set[str]):
    """Yields ``(column_map, data_row)`` for each data row of a marked table.

    The header is the first non-empty row after the marker; data runs until a
    fully blank row or the end of the sheet.
    """
    marker_index = _find_marker_row(rows, marker)
    if marker_index is None:
        raise ExcelParseError(f"Kon de tabel '{marker}' niet vinden in het bestand.")

    header_index = None
    for index in range(marker_index + 1, len(rows)):
        if any(_cell(cell) for cell in rows[index]):
            header_index = index
            break
    if header_index is None:
        raise ExcelParseError(f"De tabel '{marker}' heeft geen kolomkoppen.")

    column_map = _build_column_map(rows[header_index], aliases)
    missing = required - set(column_map)
    if missing:
        readable = ", ".join(sorted(missing))
        raise ExcelParseError(f"De tabel '{marker}' mist kolommen: {readable}.")

    data_rows = []
    for index in range(header_index + 1, len(rows)):
        row = rows[index]
        if not any(_cell(cell) for cell in row):
            break  # blank row ends the table
        data_rows.append(row)
    return column_map, data_rows


def _value(row: list, column_map: dict[str, list[int]], field_name: str):
    """Returns the first non-empty cell across a field's columns, in alias order."""
    last = None
    for index in column_map.get(field_name, []):
        if index >= len(row):
            continue
        value = row[index]
        if _cell(value):
            return value
        last = value  # remember an empty/None so the field still resolves
    return last


def _select_sheet(workbook) -> list[list]:
    """Returns the source sheet's rows: the one carrying both section markers."""
    for sheet in workbook.worksheets:
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        has_vacancy = _find_marker_row(rows, VACANCY_MARKER) is not None
        has_placement = _find_marker_row(rows, PLACEMENT_MARKER) is not None
        if has_vacancy and has_placement:
            return rows
    raise ExcelParseError(
        "Geen geldige OTYS-export gevonden. Verwacht een tabblad met een "
        "'Vacature module'- en een 'Plaatsingenmodule'-tabel."
    )


def parse_excel(file_bytes: bytes) -> OtysImportBatch:
    """Parses an uploaded OTYS ``.xlsx`` into an ``OtysImportBatch``."""
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
    except Exception as exc:  # openpyxl raises a grab-bag of exceptions on a bad file
        message = "Kon het Excel-bestand niet lezen. Controleer of het een geldig .xlsx-bestand is."
        raise ExcelParseError(message) from exc

    try:
        rows = _select_sheet(workbook)

        vacancy_map, vacancy_rows = _read_table(rows, VACANCY_MARKER, VACANCY_ALIASES, REQUIRED_VACANCY_FIELDS)
        placement_map, placement_rows = _read_table(
            rows, PLACEMENT_MARKER, PLACEMENT_ALIASES, REQUIRED_PLACEMENT_FIELDS
        )
    finally:
        workbook.close()

    batch = OtysImportBatch()

    for row in vacancy_rows:
        reference = _cell(_value(row, vacancy_map, "reference"))
        if not reference:
            continue  # a vacancy without its key can't be linked or upserted
        batch.vacancies.append(
            OtysVacancy(
                reference=reference,
                name=_cell(_value(row, vacancy_map, "name")),
                description=_cell(_value(row, vacancy_map, "description")),
                role=_cell(_value(row, vacancy_map, "role")),
                start_date=_to_date(_value(row, vacancy_map, "start_date")),
                end_date=_to_date(_value(row, vacancy_map, "end_date")),
                owner_name=_cell(_value(row, vacancy_map, "owner_name")),
                owner_email=_cell(_value(row, vacancy_map, "owner_email")),
                ministry_code=_cell(_value(row, vacancy_map, "ministry_code")),
                status=_cell(_value(row, vacancy_map, "status")),
            )
        )

    for row in placement_rows:
        placement_number = _cell(_value(row, placement_map, "placement_number"))
        if not placement_number:
            continue
        candidate = OtysCandidate(
            email=_cell(_value(row, placement_map, "email")),
            first_name=_clean_name_part(_value(row, placement_map, "first_name")),
            infix=_clean_name_part(_value(row, placement_map, "infix")),
            last_name=_clean_name_part(_value(row, placement_map, "last_name")),
        )
        batch.placements.append(
            OtysPlacement(
                placement_number=placement_number,
                vacancy_reference=_cell(_value(row, placement_map, "vacancy_reference")),
                candidate=candidate,
                start_date=_to_date(_value(row, placement_map, "start_date")),
                end_date=_to_date(_value(row, placement_map, "end_date")),
            )
        )

    return batch
