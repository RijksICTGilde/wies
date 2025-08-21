from django import forms

from .models import Assignment, Colleague, Skill, Placement, Service, Ministry, Brand, Expertise

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
            elif isinstance(widget, forms.EmailInput):
                # TODO: check if there is better fitted css for this
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input'
            elif isinstance(widget, forms.NumberInput):
                # TODO: check if there is better fitted css for this
                widget.attrs['class'] = widget.attrs.get('class', '') + ' utrecht-textbox utrecht-textbox--html-input'

class AssignmentForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'
        exclude = ['assignment_type',]
        labels = {
            'name': 'Naam',
            'start_date': 'Start datum',
            'end_date': 'Eind datum',
            'status': 'Status',
            'organization': 'Opdrachtgever',
            'ministry': 'Ministerie',
            'extra_info': 'Extra informatie',
        }

class ColleagueForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Colleague
        fields = '__all__'
        exclude = ['source', 'source_id', 'source_url', 'user']
        widgets = {
            'expertises': forms.SelectMultiple(attrs={'class': 'js-expertises-select-multiple'}),
            'skills': forms.SelectMultiple(attrs={'class': 'js-skills-select-create-multiple'})
        }
        labels = {
            'name': 'Naam',
            'brand': 'Merk',
            'expertises': 'ODI-expertise',
            'skills': 'Rollen',
        }

class PlacementForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Placement
        fields = ['colleague', 'period_source', 'specific_start_date', 'specific_end_date', 'hours_source', 'specific_hours_per_week']
        widgets = {
            'colleague': forms.Select(attrs={'class': 'js-colleague-select'}),
        }
        labels = {
            'colleague': 'Consultant',
            'period_source': 'Periode',
            'specific_start_date': 'Start datum',
            'specific_end_date': 'Eind datum',
            'hours_source': 'Uren per week',
            'specific_hours_per_week': 'Uren per week',
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'service_id'):
            instance.service_id = self.service_id
        if commit:
            instance.save()
        return instance


class ServiceForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ['description', 'skill', 'cost_type', 'fixed_cost', 'hours_per_week', 'period_source', 'specific_start_date', 'specific_end_date']
        widgets = {
            'skill': forms.Select(attrs={'class': 'js-skills-select-single'}),
        }
        labels = {
            'description': 'Omschrijving',
            'skill': 'Rol',
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
