"""Editables for the user (used by self-edit profile and admin user form).

Permissions live in ``wies/core/permission_rules.py``.
"""

from typing import TYPE_CHECKING, Any, cast

from django.db import transaction

from wies.core.inline_edit import Editable, EditableSet
from wies.core.models import Colleague
from wies.rijksauth.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model


def _save_user_field_and_sync_colleague(field_name: str) -> Callable[[Model, Any], None]:
    """Update the User field and mirror the full name onto the linked Colleague."""

    @transaction.atomic
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


class UserEditables(EditableSet):
    class Meta:
        model = User

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
    email = Editable(
        label="E-mail (ODI)",
        required=True,
    )
