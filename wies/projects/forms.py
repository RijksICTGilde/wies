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


class OpdrachtbeschrijvingForm(RVOFormMixin, forms.Form):
    """Form for Opdrachtbeschrijving Rijks ICT Gilde"""

    # Algemene informatie opdracht
    tech_consultant = forms.ModelChoiceField(Colleague.objects, widget=forms.Select(attrs={'class': 'js-colleague-select'}), )    
    opdrachtgever = forms.CharField(label='Opdrachtgever', required=False)
    onderdeel = forms.CharField(label='Onderdeel waar je werkzaam bent', required=False)
    project_naam = forms.CharField(label='Eventueel naam project/opdracht', required=False)
    standplaats = forms.CharField(label='Standplaats opdrachtgever', required=False)
    functietitel = forms.CharField(label='Jouw functietitel bij de opdrachtgever', required=False)
    periode_uren = forms.CharField(label='Periode aanstelling + uren per week', required=False)
    inhurende_manager = forms.CharField(label='Inhurende manager + functietitel', required=False)
    business_manager = forms.CharField(label='Business manager RIG', required=False)
    leidinggevende = forms.CharField(
        label='Leidinggevende op opdracht + functietitel + e-mailadres + mobiele telefoonnummer',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    # Meer over de opdrachtgever
    team_beschrijving = forms.CharField(
        label='Hoe ziet de afdeling/het team eruit (aantal personen, aansturing, werkplek etc.)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    cultuur_sfeer = forms.CharField(
        label='Hoe zou je de cultuur en sfeer omschrijven',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    projecten_uitdagingen = forms.CharField(
        label='Waar is de afdeling mee bezig, welke projecten spelen er momenteel, uitdagingen voor de komende 12 maanden',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    stakeholders = forms.CharField(
        label='Met welke belangrijke stakeholders heb je te maken',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )

    # Functieomschrijving
    algemene_omschrijving = forms.CharField(
        label='Algemene omschrijving opdracht',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    taken_verantwoordelijkheden = forms.CharField(
        label='Belangrijkste taken/verantwoordelijkheden',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    resultaat = forms.CharField(
        label='Wat is het resultaat van de opdracht',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    succesvol_afgerond = forms.CharField(
        label='Wanneer heb jij de opdracht succesvol afgerond',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )


class EvaluatieConsultantForm(RVOFormMixin, forms.Form):
    """Form for Evaluatiegesprek Rijks ICT Gilde - Consultant"""

    # Algemene informatie
    medewerker = forms.CharField(label='Naam medewerker', required=False)
    opdrachtgever = forms.CharField(label='Naam opdrachtgever', required=False)
    manager_collega = forms.CharField(label='Naam manager/collega', required=False)

    # De opdracht en de inzet
    algemene_indruk = forms.CharField(
        label='Algemene indruk over opdracht en opdrachtgever',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    tops = forms.CharField(
        label='Wat ging afgelopen jaar echt goed (tops)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    tips = forms.CharField(
        label='Wat ging afgelopen jaar minder goed (tips)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    opdrachtsfocus = forms.CharField(
        label='Waar ligt opdrachtsfocus (persoonlijk en vanuit opdrachtgever) de aankomende periode',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    nodig_van_opdrachtgever = forms.CharField(
        label='Wat heb je nodig van je opdrachtgever om jouw opdracht (nog) beter uit te voeren?',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    ambities_groei = forms.CharField(
        label='Welke ambities heb je in betrekking tot je huidige opdracht voor het aankomende jaar? Welke groei wil je maken en zijn daar mogelijkheden voor binnen deze opdracht?',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    andere_zaken = forms.CharField(
        label='Andere belangrijke te bespreken zaken (denk aan: conflicten, behaalde resultaten, werkomgeving, wensen, behoeftes, etc.)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )


class EvaluatieOpdrachtgeverForm(RVOFormMixin, forms.Form):
    """Form for Evaluatiegesprek Rijks ICT Gilde - Opdrachtgever"""

    # Algemene informatie
    medewerker = forms.CharField(label='Naam medewerker', required=False)
    opdrachtgever = forms.CharField(label='Naam opdrachtgever', required=False)
    manager_collega = forms.CharField(label='Naam manager/collega', required=False)

    # De opdracht en de inzet
    algemene_indruk = forms.CharField(
        label='Algemene indruk over inzet consultant',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    tops = forms.CharField(
        label='Wat ging afgelopen jaar echt goed (tops)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    tips = forms.CharField(
        label='Wat ging afgelopen jaar minder goed (tips)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    focus_aankomende_periode = forms.CharField(
        label='Waar ligt focus mbt inzet consultant de aankomende periode (indien van toepassing)',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    andere_zaken = forms.CharField(
        label='Andere belangrijke te bespreken zaken',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
