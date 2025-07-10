from django import forms
from .models import Project, Colleague

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'start_date', 'end_date', 'colleagues', 'status', 'organization'] 