import datetime

from django.db import models
from django.urls import reverse
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


ASSIGNMENT_STATUS = {
    'LEAD': "LEAD",
    'VACATURE': "VACATURE",
    'INGEVULD': "INGEVULD",
    'AFGEWEZEN': "AFGEWEZEN",
}

ASSIGNMENT_TYPE = {
    'GROUP': "GROUP",
    'INDIVIDUAL': "INDIVIDUAL",
}

SOURCE_CHOICES = {
    'wies': 'WIES',
    'exact': 'Exact',
    'otys_iir': 'OTYS IIR',
}


class Brand(models.Model):
    name = models.CharField(max_length=50)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Expertise(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'expertises'
    
    def __str__(self):
        return self.name

class Ministry(models.Model):
    name = models.CharField(max_length=98)
    abbreviation = models.CharField(max_length=10)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'ministries'
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

class Skill(models.Model):
    name = models.CharField(max_length=30, unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Colleague(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='colleague')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    brand = models.ForeignKey('Brand', models.SET_NULL, null=True, blank=False)
    expertises = models.ManyToManyField('Expertise', blank=True)
    skills = models.ManyToManyField('Skill', blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='wies')
    source_id = models.CharField(blank=True)
    source_url = models.URLField(null=True, blank=True)  # only for non wies
    # placements via reversed relation

    @property
    def end_date(self):
        """
        Max end_date of current placements.
        This property has N+1 query issues.
        Use get_colleague_end_date_efficient() from statistics module instead for batch operations.
        """
        from .querysets import annotate_placement_dates

        end_date = None
        today_date = datetime.datetime.today().date()

        # Use optimized query with select_related and annotations
        placements = annotate_placement_dates(
            self.placements.select_related('service__assignment')
        )

        for placement in placements:
            # Use annotated fields instead of properties
            placement_start = placement.actual_start_date
            placement_end = placement.actual_end_date

            # filtering out ill-formed placements and historical and future placements
            if (placement_end is None
                or placement_start is None
                or placement_start > today_date
                or placement_end < today_date):
                # todo: probably should make end-date required when someone is assigned (on placement?)
                # this otherwise leads to difficult to interpret results
                continue
            if end_date is None or placement_end > end_date:
                end_date = placement_end
        return end_date

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

# Create your models here.
class Assignment(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)  #TODO: timezone aware?
    end_date = models.DateField(null=True, blank=True)  #TODO: timezone aware?
    # placements through foreignkey on Placement
    # services through foreignkey on Service
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='LEAD')
    organization = models.CharField(blank=True)
    ministry = models.ForeignKey('Ministry', models.SET_NULL, null=True, blank=False)
    extra_info = models.TextField(blank=True)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE, default='GROUP')


    @property
    def phase(self):
        today_date = datetime.datetime.today().date()
        if None in (self.start_date, self.end_date):
            # this is undertermined
            return None
        if self.start_date > today_date:
            return "planned"
        elif self.end_date < today_date:
            return "completed"
        else:
            return "active"

    def get_absolute_url(self):
        return reverse("assignment-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Placement(models.Model):
    SERVICE = "SERVICE"
    PLACEMENT = "PLACEMENT"
    SOURCE_CHOICES = {
        SERVICE: "Neem over van dienst",
        PLACEMENT: "Specifiek voor inzet"
    }
    
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='placements', null=True, blank=True) # TODO: removal of colleague triggers removal of placement, probably undesirable
    service = models.ForeignKey('Service', models.CASCADE, related_name='placements')
    period_source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SERVICE)
    specific_start_date = models.DateField(null=True, blank=True) # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True) # do not use, use properties below
    hours_source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SERVICE)
    specific_hours_per_week = models.IntegerField(null=True, blank=True)

    @property
    def start_date(self):
        # TODO: can this be sped-up by using annotated column with prefetch_related?
        if self.period_source == 'SERVICE':
            return self.service.start_date
        else:
            return self.specific_start_date
        
    @property
    def end_date(self):
        if self.period_source == 'SERVICE':
            return self.service.end_date
        else:
            return self.specific_end_date

    @property
    def hours_per_week(self):
        if self.hours_source == 'SERVICE':
            return self.service.hours_per_week
        else:
            return self.specific_hours_per_week

    def get_absolute_url(self):
        return reverse("placement-detail", kwargs={"pk": self.pk})


class Service(models.Model):
    ASSIGNMENT = "ASSIGNMENT"
    SERVICE = "SERVICE"
    PERIOD_SOURCE_CHOICES = {
        ASSIGNMENT: "Neem over van opdracht",
        SERVICE: "Specifiek voor dienst"
    }

    assignment = models.ForeignKey('Assignment', models.CASCADE, related_name='services')
    description = models.CharField(max_length=500)
    skill = models.ForeignKey('Skill', models.SET_NULL, related_name='services', null=True, blank=True)
    hours_per_week = models.IntegerField(null=True, blank=True)
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=ASSIGNMENT)
    specific_start_date = models.DateField(null=True, blank=True) # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True) # do not use, use properties below
    # placements via reverse relation

    @property
    def start_date(self):
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.start_date
        else:
            return self.specific_start_date
        
    @property
    def end_date(self):
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.end_date
        else:
            return self.specific_end_date

    def __str__(self):
        return f"{self.description} "

    def get_absolute_url(self):
        return reverse("service-detail", kwargs={"pk": self.pk})


class Note(models.Model):
    assignment = models.ForeignKey('Assignment', models.CASCADE, related_name='notes')
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.colleague.name} on {self.assignment.name}"
