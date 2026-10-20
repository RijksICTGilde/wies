"""Date display for Wies, shared by templates and Python-built texts."""

from datetime import date

from django.utils.formats import date_format


def datum_nl(datum, fmt="j b Y"):
    """THE date display for Wies, via Django's nl-nl localization.

    House style: months are always three letters, lowercase ('b' → "11 nov
    2024"). Callers only choose which parts to show (e.g. "b Y" for month +
    year on cards); they don't restyle the month.
    """
    if datum is None:
        return "?"
    if isinstance(datum, str):
        try:
            datum = date.fromisoformat(datum)
        except ValueError:
            return datum
    return date_format(datum, fmt)


def date_range_text(start: date | None, end: date | None) -> str:
    """A period in words: "1 jan 2026 t/m 30 jun 2026", "Vanaf 1 jan 2026" or
    "t/m 30 jun 2026"; empty without either date."""
    if start and end:
        return f"{datum_nl(start)} t/m {datum_nl(end)}"
    if start:
        return f"Vanaf {datum_nl(start)}"
    if end:
        return f"t/m {datum_nl(end)}"
    return ""
