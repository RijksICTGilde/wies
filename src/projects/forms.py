from django import forms

from multiselectfield import MultiSelectFormField

from .models import Project, Colleague, Skills, Assignment, Job

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

class ProjectForm(RVOFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        exclude = ['project_type',]

class ColleagueForm(RVOFormMixin, forms.ModelForm):
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget

    class Meta:
        model = Colleague
        fields = '__all__'

class AssignmentForm(RVOFormMixin, forms.ModelForm):
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)  # overwrite default widget
    
    class Meta:
        model = Assignment
        fields = '__all__'

class JobForm(RVOFormMixin, forms.ModelForm):

    # todo: can this use the existing AssigmentForm?
    skills = MultiSelectFormField(required=False, choices=Skills.choices, widget=forms.SelectMultiple)
    colleague = forms.ModelChoiceField(queryset=Colleague.objects.all(), required=False)
    hours_per_week = forms.IntegerField(required=False)

    class Meta:
        model = Job
        fields = '__all__'
        exclude = ['project_type',]
