from wies.core.errors import SuborganizationNotFoundError
from wies.core.models import Suborganization


def get_suborganization_by_name(name: str) -> Suborganization:
    """Resolve a name to an existing Suborganization (case-insensitive).

    Never creates a Suborganization — creating one is a deliberate admin
    action. Raises SuborganizationNotFoundError when no match exists.
    """
    cleaned = name.strip()
    match = Suborganization.objects.filter(name__iexact=cleaned).first()
    if match is None:
        raise SuborganizationNotFoundError(cleaned)
    return match


# CSV headers renamed when "merk" became "onderdeel/programma". A header the import
# does not know is skipped in silence, so an old file would import every row
# without its suborganization and still report success; name the new header instead.
RENAMED_CSV_COLUMNS = {
    "brand": "suborganization",
    "owner_brand": "owner_suborganization",
    "colleague_brand": "colleague_suborganization",
}


def renamed_column_errors(fieldnames) -> list[str]:
    """One error per header that uses a pre-rename suborganization column name."""
    return [
        f"De kolom '{name.strip()}' heet nu '{RENAMED_CSV_COLUMNS[name.strip().lower()]}'. "
        "Pas de kopregel van je bestand aan."
        for name in fieldnames or ()
        if (name or "").strip().lower() in RENAMED_CSV_COLUMNS
    ]
