import datetime

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser


ASSIGNMENT_STATUS = {
    'VACATURE': "VACATURE",
    'INGEVULD': "INGEVULD",
}

SOURCE_CHOICES = {
    'otys_iir': 'OTYS IIR',
    'wies': 'Wies',
}


class Brand(models.Model):
    name = models.CharField(max_length=50)
    
    class Meta:
        ordering = ['name']
    
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

class User(AbstractUser):
    email = models.EmailField(unique=True)
    brand = models.ForeignKey('Brand', models.SET_NULL, null=True, blank=True, related_name='users')


class Colleague(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='colleague')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    brand = models.ForeignKey('Brand', models.SET_NULL, null=True, blank=False)
    skills = models.ManyToManyField('Skill', blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(null=True, blank=True)
    # placements via reversed relation

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

# Create your models here.
class Assignment(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(null=True, blank=True)
    # placements through foreignkey on Placement
    # services through foreignkey on Service
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='LEAD')
    organization = models.CharField(blank=True)
    ministry = models.ForeignKey('Ministry', models.SET_NULL, null=True, blank=False)
    owner = models.ForeignKey('Colleague', models.SET_NULL, null=True, blank=False, related_name='owned_assignments')
    extra_info = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(null=True, blank=True)

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
    PERIOD_SOURCE_CHOICES = {
        SERVICE: "Neem over van dienst",
        PLACEMENT: "Specifiek voor inzet"
    }
    
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='placements')  # if we implement anonymization, this should maybe be changed
    service = models.ForeignKey('Service', models.CASCADE, related_name='placements')
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=SERVICE)
    specific_start_date = models.DateField(null=True, blank=True) # do not use, use properties below
    specific_end_date = models.DateField(null=True, blank=True) # do not use, use properties below
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(null=True, blank=True)  # only for non wies

    @property
    def start_date(self):
        """
        This property has N+1 query issues.
        Use `core.querysets.annotate_placement_dates` instead for batch operations.
        """
        if self.period_source == 'SERVICE':
            return self.service.start_date
        else:
            return self.specific_start_date

    @property
    def end_date(self):
        """
        This property has N+1 query issues.
        Use `core.querysets.annotate_placement_dates` instead for batch operations.
        """
        if self.period_source == 'SERVICE':
            return self.service.end_date
        else:
            return self.specific_end_date

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
    period_source = models.CharField(max_length=10, choices=PERIOD_SOURCE_CHOICES, default=ASSIGNMENT)
    specific_start_date = models.DateField(null=True, blank=True) # do not use directly, see property below
    specific_end_date = models.DateField(null=True, blank=True) # do not use directly, see property below
    # placements via reverse relation
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_id = models.CharField(blank=True)
    source_url = models.URLField(null=True, blank=True)  # only for non wies

    @property
    def start_date(self):
        """
        This does not scale well on batch operations
        consider a dedicated function similar to `core.querysets.annotate_placement_dates`
        """
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.start_date
        else:
            return self.specific_start_date
        
    @property
    def end_date(self):
        """
        This does not scale well on batch operations
        consider a dedicated function similar to `core.querysets.annotate_placement_dates`
        """
        if self.period_source == 'ASSIGNMENT':
            return self.assignment.end_date
        else:
            return self.specific_end_date

    def __str__(self):
        return f"{self.description} "

    def get_absolute_url(self):
        return reverse("service-detail", kwargs={"pk": self.pk})
