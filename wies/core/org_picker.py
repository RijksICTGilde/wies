"""Shared organisation picker — a `forms.Widget` + `forms.Field` used
by both the Assignment create form and the Assignment inline-edit
`organizations` editable.

The widget renders a trigger button + hidden inputs shaped like a
Django formset (`org-N-organization`, `org-N-role`), lets the existing
`assignment_org_tree.js` manipulate them via an RVO dialog, and parses
the submitted POST back into a list of `{organization, role}` dicts.

The field validates the list (at least one entry when required,
exactly one PRIMARY, no unknown orgs) and resolves org ids to
`OrganizationUnit` instances.
"""

from __future__ import annotations

import contextlib

from django import forms
from django.core.exceptions import ValidationError

from wies.core.models import OrganizationUnit, OrganizationUnitRole


class OrgPickerWidget(forms.Widget):
    """Render the org picker trigger + hidden inputs.

    Input/output format (``value``): a list of dicts with keys
    ``organization`` (OrganizationUnit instance OR its int id) and
    ``role`` (``"PRIMARY"`` / ``"INVOLVED"``).
    """

    template_name = "parts/widgets/org_picker.html"
    # The JS expects a fixed prefix + element IDs (assignment-org-*).
    # When we need multiple picker instances in the future, this goes
    # on a parameter; for now we have one picker per page, same ID set.
    prefix: str = "org"

    def format_value(self, value):
        """Normalise the widget's ``value`` to a list of
        ``{"organization", "role"}`` dicts for the template.

        Accepts dicts, ``(org, role)`` tuples, or ``(org, role)`` lists —
        anything else is silently dropped.

        Example::

            format_value([(org_a, "PRIMARY"), {"organization": org_b, "role": "INVOLVED"}])
            # -> [{"organization": org_a, "role": "PRIMARY"},
            #     {"organization": org_b, "role": "INVOLVED"}]
        """
        if not value:
            return []
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, (tuple, list)):
                out.append({"organization": item[0], "role": item[1]})
        return out

    def value_from_datadict(self, data, files, name):
        """Parse the submitted POST back into a list of selections.

        The JS renders a formset-shaped payload (``org-TOTAL_FORMS``,
        ``org-N-organization``, ``org-N-role``); this method walks that
        shape and returns ``[{"organization": "<id>", "role": "PRIMARY"|"INVOLVED"}, ...]``.
        Missing or non-numeric ``TOTAL_FORMS`` yields an empty list.
        """
        try:
            total = int(data.get(f"{self.prefix}-TOTAL_FORMS", 0) or 0)
        except TypeError, ValueError:
            total = 0
        picked = []
        for i in range(total):
            org_id = data.get(f"{self.prefix}-{i}-organization")
            role = data.get(f"{self.prefix}-{i}-role", OrganizationUnitRole.INVOLVED)
            if org_id:
                picked.append({"organization": org_id, "role": role})
        return picked

    def get_context(self, name, value, attrs):
        """Supply ``prefix`` + hydrated ``selections`` to the template.

        Selections are normalised via ``format_value``, and any entry
        whose ``organization`` is still a raw id (the shape returned by
        ``value_from_datadict`` on a re-rendered form) is resolved to an
        ``OrganizationUnit`` instance in a single ``in_bulk`` lookup.
        The template can then treat every row uniformly — ``.id`` and
        ``.name`` are always available.
        """
        ctx = super().get_context(name, value, attrs)
        selections = self.format_value(value)
        raw_ids = [s["organization"] for s in selections if not hasattr(s.get("organization"), "id")]
        if raw_ids:
            try:
                ids = [int(x) for x in raw_ids]
            except TypeError, ValueError:
                ids = []
            resolved = OrganizationUnit.objects.in_bulk(ids) if ids else {}
            for s in selections:
                org = s.get("organization")
                if not hasattr(org, "id"):
                    with contextlib.suppress(TypeError, ValueError):
                        s["organization"] = resolved.get(int(org), org)
        ctx["widget"]["prefix"] = self.prefix
        ctx["widget"]["selections"] = selections
        return ctx


class OrganizationsField(forms.Field):
    """Field backed by `OrgPickerWidget`. Cleaned value is a list of
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
