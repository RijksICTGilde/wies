"""Custom Django form widgets used across the wies UI."""

from __future__ import annotations

import contextlib

from django import forms
from django.forms import SelectMultiple

from wies.core.models import OrganizationUnit, OrganizationUnitRole


class MultiselectDropdown(SelectMultiple):
    """Custom dropdown multiselect widget using the multiselect component."""

    template_name = "rvo/forms/widgets/multiselect.html"

    def id_for_label(self, id_, index=None):
        # Return None so the <label> in field.html gets no "for" attribute.
        # The widget uses aria-labelledby instead.
        return None


class OrgPickerWidget(forms.Widget):
    """Render the org picker trigger + hidden inputs.

    Input/output format (``value``): a list of dicts with keys
    ``organization`` (OrganizationUnit instance OR its int id) and
    ``role`` (``"PRIMARY"`` / ``"INVOLVED"``).

    Used by both the assignment-create form and the inline
    ``organizations`` editable. The companion field
    (``OrganizationsField``) lives in ``wies/core/fields.py``.
    """

    template_name = "rvo/widgets/org_picker.html"
    # The JS expects a fixed prefix + element IDs (assignment-org-*).
    # When we need multiple picker instances in the future, this goes
    # on a parameter; for now we have one picker per page, same ID set.
    prefix: str = "org"

    def format_value(self, value):
        """Normalise the widget's ``value`` to a list of
        ``{"organization", "role"}`` dicts for the template.

        Accepts dicts, ``(org, role)`` tuples, or ``(org, role)`` lists —
        anything else is silently dropped.
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
        """Parse the submitted POST back into a list of selections."""
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
        """Supply ``prefix`` + hydrated ``selections`` to the template."""
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
