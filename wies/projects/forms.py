from django import forms

from .models import Assignment, Colleague, Skill, Placement, Service

class RVOFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                widget.format = '%Y-%m-%d'
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
    class Meta:
        model = Colleague
        fields = '__all__'
        widgets = {
            'skills': forms.SelectMultiple(attrs={'class': 'js-skills-select'})
        }

class PlacementForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Placement
        fields = ['service', 'skills', 'colleague', 'period_source', 'specific_start_date', 'specific_end_date', 'hours_per_week']
        widgets = {
            'skills': forms.SelectMultiple(attrs={'class': 'js-skills-select'}),
            'colleague': forms.Select(attrs={'class': 'js-colleague-select'}),
        }
        labels = {
            'service': 'Dienst',
            'skills': 'Rollen',
            'colleague': 'Consultant',
            'period_source': 'Periode',
            'specific_start_date': 'Start datum',
            'specific_end_date': 'Eind datum',
            'hours_per_week': 'Uren per week',
        }

    def __init__(self, *args, **kwargs):
        assignment_id = kwargs.pop('assignment_id', None)
        super().__init__(*args, **kwargs)
        
        # Filter services to only show services from the same assignment
        if self.instance and self.instance.pk and self.instance.service:
            assignment = self.instance.service.assignment
            self.fields['service'].queryset = Service.objects.filter(assignment=assignment)
        elif assignment_id:
            # For create forms where assignment_id is passed
            self.fields['service'].queryset = Service.objects.filter(assignment_id=assignment_id)


class ServiceForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ['description', 'cost_type', 'fixed_cost', 'hours_per_week', 'period_source', 'specific_start_date', 'specific_end_date']
        labels = {
            'description': 'Omschrijving',
            'cost_type': 'Kosten type',
            'fixed_cost': 'Vaste kosten',
            'hours_per_week': 'Uren per week',
            'period_source': 'Periode',
            'specific_start_date': 'Start datum',
            'specific_end_date': 'Eind datum',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'assignment_id'):
            instance.assignment_id = self.assignment_id
        if commit:
            instance.save()
        return instance
