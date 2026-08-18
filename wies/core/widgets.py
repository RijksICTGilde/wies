"""Custom Django form widgets used across the wies UI."""

from __future__ import annotations

from django import forms
from django.forms import SelectMultiple

from wies.core.models import OrganizationUnit, OrganizationUnitRole
from wies.core.public_id import parse_public_ids


class MultiselectDropdown(SelectMultiple):
    """Multi-select as an NLDD token field: type to filter, picks become tokens."""

    template_name = "forms/widgets/multiselect.html"

    def id_for_label(self, id_, index=None):
        # The host is a custom element, not a labelable control, so the <label>
        # gets no "for"; the name travels via accessible-label.
        return None


class ComboBoxSelect(forms.Select):
    """Single choice as an NLDD combo box: type to filter, pick to commit.

    Form-associated, so it posts like a native <select>, with no bridge needed.
    Use it where the list is long enough that scrolling a dropdown is work.
    """

    template_name = "forms/widgets/combo_box.html"

    def id_for_label(self, id_, index=None):
        # The host is a custom element, not a labelable control, so the <label>
        # gets no "for"; the name travels via accessible-label.
        return None


class OrgPickerWidget(forms.Widget):
    """Renders the org picker trigger and its hidden inputs.

    ``value`` is a list of dicts with keys ``organization`` (an
    OrganizationUnit or its id) and ``role`` (``"PRIMARY"``/``"INVOLVED"``).
    The companion field ``OrganizationsField`` lives in ``wies/core/fields.py``.
    """

    template_name = "widgets/org_picker.html"
    # The JS expects fixed element IDs (assignment-org-*), so one picker per page.
    prefix: str = "org"

    def format_value(self, value):
        """Normalises ``value`` to a list of ``{"organization", "role"}`` dicts.

        Accepts dicts and ``(org, role)`` tuples or lists; drops anything else.
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
        """Parses the submitted POST back into a list of selections."""
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
        """Supplies ``prefix`` and hydrated ``selections`` to the template."""
        ctx = super().get_context(name, value, attrs)
        selections = self.format_value(value)
        raw_public_ids = [s["organization"] for s in selections if not hasattr(s.get("organization"), "id")]
        if raw_public_ids:
            # in_bulk on a UUIDField keys by UUID, but the raw selections hold
            # string tokens, so re-key by str.
            resolved = {
                str(pid): org
                for pid, org in OrganizationUnit.objects.in_bulk(
                    parse_public_ids(raw_public_ids), field_name="public_id"
                ).items()
            }
            for s in selections:
                org = s.get("organization")
                if not hasattr(org, "id"):
                    s["organization"] = resolved.get(str(org), org)
        ctx["widget"]["prefix"] = self.prefix
        ctx["widget"]["selections"] = selections
        return ctx
