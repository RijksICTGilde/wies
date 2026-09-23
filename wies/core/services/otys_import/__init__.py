"""Interim OTYS import: read a manual Excel export today, the OTYS API later.

The package is split into three layers that never leak into one another:

- ``records``  — the source-agnostic intermediate representation
  (``OtysImportBatch``). It is the contract between "where the data came
  from" and "how it lands in Wies models".
- ``excel``    — the adapter that turns an uploaded ``.xlsx`` into an
  ``OtysImportBatch``. A future ``api`` adapter will build the same object
  from the live ``OTYSAPI`` client, and nothing downstream changes.
- ``importer`` — consumes an ``OtysImportBatch`` and upserts Wies models.

``ministries`` holds the hardcoded ministry-code -> organisaties.overheid.nl
URL map used to link an assignment to its primary opdrachtgever.
"""

from wies.core.services.otys_import.excel import ExcelParseError, parse_excel
from wies.core.services.otys_import.importer import import_batch
from wies.core.services.otys_import.records import (
    OtysCandidate,
    OtysImportBatch,
    OtysPlacement,
    OtysVacancy,
)

__all__ = [
    "ExcelParseError",
    "OtysCandidate",
    "OtysImportBatch",
    "OtysPlacement",
    "OtysVacancy",
    "import_batch",
    "parse_excel",
]
