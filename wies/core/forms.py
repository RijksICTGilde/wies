import logging

from django import forms
from django.contrib.auth.models import Group
from django.forms.renderers import Jinja2
from django.forms.utils import ErrorList
from django.template import engines
from django.core.exceptions import ValidationError

from .models import User, Label, LabelCategory, get_next_display_order

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
        'RadioSelect': 'rvo/forms/widgets/radio.html',
    }

    def _configure_field_for_rvo(self, field_name):
        field = self.fields[field_name]

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

    def __init__(self, *args, **kwargs):
        # Set custom error class before calling super
        kwargs.setdefault('error_class', RvoErrorList)
        super().__init__(*args, **kwargs)

        # Configure all fields and widgets for RVO
        for field_name in self.fields:
            self._configure_field_for_rvo(field_name)
            

class LabelCategoryForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating LabelCategory instances"""

    name = forms.CharField(label='Naam', required=True)
    color = forms.ChoiceField(label='Kleur label', choices=[
        ('#DCE3EA', 'Grijs'),
        ('#B3D7EE', 'Blauw'),
        ('#FFE9B8', 'Geel'),
        ('#C4DBB7', 'Groen'),
        ('#F9DFDD', 'Rood'),
    ], widget=forms.RadioSelect)
    display_order = forms.IntegerField(
        label='Volgorde',
        min_value=0,
        required=True,
        help_text='Lagere waarden verschijnen eerst',
        widget=forms.TextInput(attrs={'type': 'number', 'min': '0'})
    )

    class Meta:
        model = LabelCategory
        fields = ['name', 'color', 'display_order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  # only for new category
            self.fields['display_order'].initial = get_next_display_order()


class LabelForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating Label instances"""

    name = forms.CharField(label='Naam', required=True)
    class Meta:
        model = Label
        fields = ['name']

    def __init__(self, *args, **kwargs):
        self.category_id = kwargs.pop('category_id', None)
        super().__init__(*args, **kwargs)


    def clean_name(self):
        new_name = self.cleaned_data['name']
        creating_new_label = self.instance.id is None

        # when creating new one, we need category for validation initiated on form instance
        # when editing, we already have the instance for this
        if creating_new_label:
            if Label.objects.filter(category=self.category_id, name=new_name).exists():
                raise ValidationError("Naam wordt al gebruikt")
            else:
                return new_name
        else:
            original_name = self.instance.name
            if new_name == original_name:
                return new_name
            elif Label.objects.filter(category=self.instance.category, name=new_name).exists():
                raise ValidationError("Naam wordt al gebruikt")
            else:
                return new_name


class UserForm(RvoFormMixin, forms.ModelForm):
    """Form for creating and updating User instances"""

    first_name = forms.CharField(label='Voornaam', required=True)
    last_name = forms.CharField(label='Achternaam', required=True)
    email = forms.EmailField(label='Email (ODI)', required=True)
    groups = forms.ModelMultipleChoiceField(
        label='Rollen',
        queryset=Group.objects.filter(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    # Init will create category_* fields for the different label categories

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'groups']
        # label attribute is manually constructed and serialized below

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Map labels stored on model to separate fields per category, which are dynamically generated
        instance = kwargs.get('instance')
        self._category_field_names = set()
        for category in LabelCategory.objects.all():
            field_name = f'category_{category.name}'

            initial = None
            if instance and instance.labels.filter(category=category).exists():
                initial = instance.labels.filter(category=category).first()  # this maps potential multiple in DB to single!
                
            self.fields[field_name] = forms.ModelChoiceField(
                label=category.name,
                queryset=Label.objects.filter(category=category),
                required=False,
                initial=initial,
            )

            # used in clean
            self._category_field_names.add(field_name)

            # necessary because RVOForm init already ran and otherwise wrong templates are referenced
            self._configure_field_for_rvo(field_name)
        

    def clean(self):
        cleaned_data = super().clean()

        # combine selected labels into single label attribute
        cleaned_data['labels'] = []
        for category_field_name in self._category_field_names:
            selected_label = cleaned_data.pop(category_field_name)
            if selected_label is not None:
                cleaned_data['labels'].append(selected_label)

        return cleaned_data
