"""Shared form-rendering helpers for design system integration.

Lives in its own module so both ``wies.core.forms`` and
``wies.core.inline_edit.forms`` can import form mixins without
creating a circular dependency.
"""

import logging

from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines

logger = logging.getLogger(__name__)


class WiesJinja2Renderer(Jinja2):
    """Custom renderer that uses Django's configured Jinja2 environment with all globals."""

    @property
    def engine(self):
        return engines["jinja2"]


class NlddErrorList(ErrorList):
    """Custom ErrorList with NLDD template"""

    template_name = "nldd/forms/errors/list/default.html"


class _BaseFormMixin:
    """Shared form configuration logic for any design system.

    Subclasses set ``_form_template``, ``_field_template``, ``_error_class``,
    and ``widget_templates`` to wire up the correct templates.
    """

    _form_template: str
    _field_template: str
    _error_class: type[ErrorList]

    default_renderer = WiesJinja2Renderer()

    widget_templates: dict[str, str] = {}

    # Invisible widgets need no template; skip the warning for them (#389).
    widgets_without_rvo_template = {
        "HiddenInput",
        "MultipleHiddenInput",
    }

    # Per-widget extra configuration applied whenever the widget class is
    # mapped to a template. `DateInput` rendering — HTML5 <input type="date">
    # demands ISO yyyy-mm-dd in its value attribute or the browser silently
    # blanks the field; Django's DateInput defaults to the active
    # locale (Dutch dd-mm-yyyy), so we force ISO here.
    widget_config = {
        "DateInput": {"format": "%Y-%m-%d"},
    }

    @property
    def template_name(self):
        return self._form_template

    @template_name.setter
    def template_name(self, value):
        self._form_template = value

    def _configure_field(self, field_name: str) -> None:
        field = self.fields[field_name]

        # Disable HTML5 client-side required validation
        field.widget.use_required_attribute = lambda _: False
        field.template_name = self._field_template

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
        elif widget_class_name in self.widgets_without_rvo_template:
            pass
        else:
            logger.warning(
                "Widget '%s' for field '%s' not in widget_templates mapping. Using default Django template.",
                widget_class_name,
                field_name,
            )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("error_class", self._error_class)
        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            self._configure_field(field_name)

    # Backward-compat alias used by forms that dynamically add fields
    # after __init__ and then configure them individually.
    _configure_field_for_rvo = _configure_field


class NlddFormMixin(_BaseFormMixin):
    """Configure forms for NLDD design system rendering.

    Uses native HTML inputs (no Shadow DOM web components) so HTMX
    and Django form handling work without a bridge layer.
    """

    _form_template = "nldd/forms/form.html"
    _field_template = "nldd/forms/field.html"
    _error_class = NlddErrorList

    widget_templates = {
        "TextInput": "nldd/forms/widgets/text.html",
        "EmailInput": "nldd/forms/widgets/email.html",
        "Select": "nldd/forms/widgets/select.html",
        "CheckboxSelectMultiple": "nldd/forms/widgets/checkbox_select.html",
        "MultiselectDropdown": "nldd/forms/widgets/multiselect.html",
        "RadioSelect": "nldd/forms/widgets/radio.html",
        "DateInput": "nldd/forms/widgets/date.html",
        "Textarea": "nldd/forms/widgets/textarea.html",
        "CheckboxInput": "nldd/forms/widgets/checkbox.html",
        "OrgPickerWidget": "nldd/widgets/org_picker.html",
    }
