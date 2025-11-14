from django import forms
from django.contrib.auth.models import Group

from .models import User, Brand


class UserForm(forms.ModelForm):
    """Form for creating and updating User instances"""

    first_name = forms.CharField(
        label='Voornaam',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'utrecht-textbox utrecht-textbox--html-input rvo-input',
        }),
    )

    last_name = forms.CharField(
        label='Achternaam',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'utrecht-textbox utrecht-textbox--html-input rvo-input',
        }),
    )

    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'utrecht-textbox utrecht-textbox--html-input rvo-input',
        }),
    )

    brand = forms.ModelChoiceField(
        label='Merk',
        queryset=Brand.objects.all(),
        required=False,
        empty_label='Geen merk',
        widget=forms.Select(attrs={
            'class': 'utrecht-select utrecht-select--html-select rvo-select',
        }),
    )

    groups = forms.ModelMultipleChoiceField(
        label='Rollen',
        queryset=Group.objects.filter(name__in=['Administrator', 'Consultant', 'BDM']),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'brand', 'groups']
