from django import forms
from django.forms import formset_factory


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

class AssignmentForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'
        exclude = ['assignment_type', 'ministry']
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
        exclude = ['source', 'source_id', 'source_url']
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
        fields = ['service', 'colleague', 'period_source', 'specific_start_date', 'specific_end_date', 'hours_per_week']
        widgets = {
            'colleague': forms.Select(attrs={'class': 'js-colleague-select'}),
        }
        labels = {
            'service': 'Dienst',
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


# TODO: maybe this can also be achived with custom formset renderer 
# https://docs.djangoproject.com/en/5.2/ref/forms/renderers/#django.forms.renderers.BaseRenderer.formset_template_name
class HiddenServiceForm(forms.ModelForm):
    """All attributes are hidden"""
    class Meta:
        model = Service
        fields = ['description', 'hours_per_week']
        widgets = {
            'description': forms.HiddenInput(),
            'hours_per_week': forms.HiddenInput(),
        }
        # fields = '__all__'
        # exclude = ['assignment']

class NewServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['description', 'hours_per_week']
        # fields = '__all__'
        # exclude = ['assignment']


HiddenServiceFormSet = formset_factory(HiddenServiceForm, extra=0)

class AssignmentCreateForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['name']
