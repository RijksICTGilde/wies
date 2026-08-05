from wies.core.errors import SuborganizationNotFoundError
from wies.core.models import Suborganization


def get_suborganization_by_name(name: str) -> Suborganization:
    """Resolve a brand name to an existing Suborganization (case-insensitive).

    Never creates a Suborganization — creating a brand is a deliberate admin
    action. Raises SuborganizationNotFoundError when no match exists.
    """
    cleaned = name.strip()
    match = Suborganization.objects.filter(name__iexact=cleaned).first()
    if match is None:
        raise SuborganizationNotFoundError(cleaned)
    return match
