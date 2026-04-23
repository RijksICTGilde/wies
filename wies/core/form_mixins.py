"""Shared form-rendering helpers for the RVO design system.

Lives in its own module so both ``wies.core.forms`` and
``wies.core.inline_edit.forms`` can import ``RvoFormMixin`` without
creating a circular dependency.
"""

import logging

from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines

logger = logging.getLogger(__name__)


class RvoJinja2Renderer(Jinja2):
    """Custom renderer that uses Django's configured Jinja2 environment with all globals."""

    @property
    def engine(self):
        return engines["jinja2"]


class RvoErrorList(ErrorList):
    """Custom ErrorList with RVO template"""

    template_name = "rvo/forms/errors/list/default.html"


class RvoFormMixin:
    """
    Mixin to automatically configure forms for RVO design system rendering.

    Usage:
        class MyForm(RvoFormMixin, forms.ModelForm):
            # Just define fields as normal
            name = forms.CharField()

    All RVO templates, error styling, and widget configuration happens automatically.
    This Mixin also disables client-side required checks on fields.
    """

    template_name = "rvo/forms/form.html"
    default_renderer = RvoJinja2Renderer()

    # Widget type to template mapping (only includes widgets with existing templates)
    widget_templates = {
        "TextInput": "rvo/forms/widgets/text.html",
        "EmailInput": "rvo/forms/widgets/email.html",
        "Select": "rvo/forms/widgets/select.html",
        "CheckboxSelectMultiple": "rvo/forms/widgets/checkbox_select.html",
        "MultiselectDropdown": "rvo/forms/widgets/multiselect.html",
        "RadioSelect": "rvo/forms/widgets/radio.html",
        "DateInput": "rvo/forms/widgets/date.html",
        "Textarea": "rvo/forms/widgets/textarea.html",
        "CheckboxInput": "rvo/forms/widgets/checkbox.html",
        "OrgPickerWidget": "parts/widgets/org_picker.html",
    }

    # Per-widget extra configuration applied whenever the widget class is
    # mapped to an RVO template. Each entry is merged onto the widget
    # instance. `DateInput` rendering — HTML5 <input type="date"> demands
    # ISO yyyy-mm-dd in its value attribute or the browser silently
    # blanks the field; Django's DateInput defaults to the active
    # locale (Dutch dd-mm-yyyy), so we force ISO here.
    widget_config = {
        "DateInput": {"format": "%Y-%m-%d"},
    }

    def _configure_field_for_rvo(self, field_name):
        field = self.fields[field_name]

        # Disable HTML5 client-side required validation
        field.widget.use_required_attribute = lambda _: False
        field.template_name = "rvo/forms/field.html"

        # Turn off browser autocomplete for every form field by default
        # — Wies fields are domain-specific (Opdracht naam, Looptijd,
        # Collega) and browsers guessing from generic heuristics
        # (name, email) is more nuisance than help.
        field.widget.attrs.setdefault("autocomplete", "off")

        # Auto-assign widget template + any per-widget configuration.
        widget_class_name = field.widget.__class__.__name__
        if widget_class_name in self.widget_templates:
            field.widget.template_name = self.widget_templates[widget_class_name]
            for attr, value in self.widget_config.get(widget_class_name, {}).items():
                setattr(field.widget, attr, value)
        else:
            logger.warning(
                "Widget '%s' for field '%s' not in RVO widget_templates mapping. Using default Django template.",
                widget_class_name,
                field_name,
            )

    def __init__(self, *args, **kwargs):
        # Set custom error class before calling super
        kwargs.setdefault("error_class", RvoErrorList)
        super().__init__(*args, **kwargs)

        # Configure all fields and widgets for RVO
        for field_name in self.fields:
            self._configure_field_for_rvo(field_name)
