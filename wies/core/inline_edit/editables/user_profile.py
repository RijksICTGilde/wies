"""Editables for the user's own profile (first_name, last_name)."""

from typing import TYPE_CHECKING, Any, cast

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Colleague
from wies.rijksauth.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model


def _can_edit_own_profile(user, target_user):
    # Even superusers edit via the regular /profiel/ flow.
    return user.is_authenticated and user == target_user


def _save_user_field_and_sync_colleague(field_name: str) -> Callable[[Model, Any], None]:
    """Update the User field and mirror the full name onto the linked Colleague."""

    def _save(user: User, value: Any) -> None:
        setattr(user, field_name, value)
        user.save(update_fields=[field_name])
        colleague, _ = Colleague.objects.get_or_create(
            user=user,
            defaults={
                "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "email": user.email,
                "source": "wies",
            },
        )
        colleague.name = f"{user.first_name} {user.last_name}".strip()
        colleague.save(update_fields=["name"])

    return cast("Callable[[Model, Any], None]", _save)


class UserProfileEditables(EditableSet):
    model = User
    object_permission = staticmethod(_can_edit_own_profile)

    first_name = Editable(
        label="Voornaam",
        required=True,
        error_messages={"required": "Voornaam is verplicht"},
        save=_save_user_field_and_sync_colleague("first_name"),
    )
    last_name = Editable(
        label="Achternaam",
        required=True,
        error_messages={"required": "Achternaam is verplicht"},
        save=_save_user_field_and_sync_colleague("last_name"),
    )
