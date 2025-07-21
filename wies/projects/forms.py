from django import forms

from multiselectfield import MultiSelectFormField

from .models import Assignment, Colleague, Skills, Placement, Service

class RVOFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if name == "colleagues":
                # Forceer de juiste class voor Select2
                widget.attrs['class'] = "js-colleague-select utrecht-select utrecht-select--html-select"
            elif name == "skills":
                # Forceer de juiste class voor Select2
                widget.attrs['class'] = "js-skills-select utrecht-select utrecht-select--html-select"
            elif isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input utrecht-textbox--sm'
            elif isinstance(widget, forms.TextInput):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input'
            elif isinstance(widget, forms.Textarea):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textarea utrecht-textarea--html-textarea'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-select utrecht-select--html-select'
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-select utrecht-select--html-select utrecht-select--multiple'

class AssignmentForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'
        exclude = ['assignment_type',]

class ColleagueForm(RVOFormMixin, forms.ModelForm):
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget

    class Meta:
        model = Colleague
        fields = '__all__'

class PlacementForm(RVOFormMixin, forms.ModelForm):
    # nested inside assignment, so assignment is dropped in form
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget
    
    class Meta:
        model = Placement
        fields = ['skills', 'colleague', 'start_date', 'end_date', 'hours_per_week']

    def save(self, commit = ...):
        instance = super().save(commit=False)
        if hasattr(self, 'assignment_id'):  # to distinguish update from create
            instance.assignment_id = self.assignment_id
        if commit:
            instance.save()
        return instance


class ServiceForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ['description', 'cost']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'assignment_id'):
            instance.assignment_id = self.assignment_id
        if commit:
            instance.save()
        return instance
