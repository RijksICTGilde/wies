import logging

from django import forms
from django.contrib.auth.models import Group
from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines

from .models import User, Brand

logger = logging.getLogger(__name__)


class RvoJinja2Renderer(Jinja2):
    """Custom renderer that uses Django's configured Jinja2 environment with all globals."""
    @property
    def engine(self):
        return engines['jinja2']


class RvoErrorList(ErrorList):
    """Custom ErrorList with RVO template"""
    template_name = 'rvo/forms/errors/list/default.html'


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
    template_name = 'rvo/forms/form.html'
    default_renderer = RvoJinja2Renderer()

    # Widget type to template mapping (only includes widgets with existing templates)
    widget_templates = {
        'TextInput': 'rvo/forms/widgets/text.html',
        'EmailInput': 'rvo/forms/widgets/email.html',
        'Select': 'rvo/forms/widgets/select.html',
        'CheckboxSelectMultiple': 'rvo/forms/widgets/checkbox_select.html',
    }

    def __init__(self, *args, **kwargs):
        # Set custom error class before calling super
        kwargs.setdefault('error_class', RvoErrorList)
        super().__init__(*args, **kwargs)

        # Configure all fields and widgets for RVO
        for field_name, field in self.fields.items():
            # Disable HTML5 client-side required validation
            field.widget.use_required_attribute = lambda _: False
            field.template_name = 'rvo/forms/field.html'

            # Auto-assign widget template based on widget type
            widget_class_name = field.widget.__class__.__name__
            if widget_class_name in self.widget_templates:
                field.widget.template_name = self.widget_templates[widget_class_name]
            else:
                logger.warning(
                    "Widget '%s' for field '%s' not in RVO widget_templates mapping. "
                    "Using default Django template.",
                    widget_class_name,
                    field_name
                )


class UserForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating User instances"""

    first_name = forms.CharField(label='Voornaam', required=True)
    last_name = forms.CharField(label='Achternaam', required=True)
    email = forms.EmailField(label='Email (ODI)', required=True)
    brand = forms.ModelChoiceField(
        label='Merk',
        queryset=Brand.objects.all(),
        required=False,
        empty_label='Geen merk',
    )
    groups = forms.ModelMultipleChoiceField(
        label='Rollen',
        queryset=Group.objects.filter(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'brand', 'groups']
