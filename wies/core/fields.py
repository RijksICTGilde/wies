"""Custom Django form fields used across the wies UI."""

from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from wies.core.models import OrganizationUnit, OrganizationUnitRole
from wies.core.widgets import OrgPickerWidget


class OrganizationsField(forms.Field):
    """Field backed by ``OrgPickerWidget``. Cleaned value is a list of
    ``{"organization": OrganizationUnit, "role": str}`` dicts — one
    entry per selected org, exactly one with ``role == "PRIMARY"``.
    """

    widget = OrgPickerWidget
    default_error_messages = {
        "required": "Voeg minimaal 1 opdrachtgever toe.",
        "no_primary": "Er moet precies 1 primaire opdrachtgever zijn.",
        "unknown_org": "Onbekende organisatie geselecteerd.",
    }

    def to_python(self, value):
        """Resolve raw ``{"organization": "<id>", "role": "..."}`` dicts
        into ``OrganizationUnit`` instances.

        Uses a single ``in_bulk`` lookup. Raises ``ValidationError``
        (code ``unknown_org``) when an id can't be parsed as int or
        doesn't match a row. Unknown role values silently collapse to
        ``INVOLVED``.
        """
        if not value:
            return []
        try:
            ids = [int(v["organization"]) for v in value]
        except (TypeError, ValueError, KeyError) as exc:
            raise ValidationError(
                self.error_messages["unknown_org"],
                code="unknown_org",
            ) from exc
        resolved_map = OrganizationUnit.objects.in_bulk(ids)
        out: list[dict] = []
        for v in value:
            org = resolved_map.get(int(v["organization"]))
            if org is None:
                raise ValidationError(
                    self.error_messages["unknown_org"],
                    code="unknown_org",
                )
            role = v.get("role", OrganizationUnitRole.INVOLVED)
            if role not in {OrganizationUnitRole.PRIMARY, OrganizationUnitRole.INVOLVED}:
                role = OrganizationUnitRole.INVOLVED
            out.append({"organization": org, "role": role})
        return out

    def validate(self, value):
        """Enforce selection rules on the cleaned value.

        - When ``required``, at least one org must be selected
          (``required``).
        - Exactly one selection must have ``role == "PRIMARY"``
          (``no_primary``) — zero or multiple primaries are rejected.
        """
        super().validate(value)
        if self.required and not value:
            raise ValidationError(
                self.error_messages["required"],
                code="required",
            )
        if value:
            primary = [v for v in value if v["role"] == OrganizationUnitRole.PRIMARY]
            if len(primary) != 1:
                raise ValidationError(
                    self.error_messages["no_primary"],
                    code="no_primary",
                )
