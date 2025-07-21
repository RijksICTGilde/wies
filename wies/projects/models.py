from django.db import models
from django.urls import reverse
from django.db.models import Max

from multiselectfield import MultiSelectField

ASSIGNMENT_STATUS = {
    'LEAD': "LEAD",
    'OPEN': "OPEN",
    'LOPEND': "LOPEND",
    'AFGEWEZEN': "AFGEWEZEN",
    'HISTORISCH': "HISTORISCH",
}

ASSIGNMENT_TYPE = {
    'GROUP': "GROUP",
    'INDIVIDUAL': "INDIVIDUAL",
}


class Skills(models.TextChoices):
    BACKEND_DEVELOPMENT = "BE_DEV", "Backend development",
    FRONTEND_DEVELOPMENT = "FE_DEV", "Frontend development",
    PRODUCT_OWNER = "PO", "Product owner",
    UX_DESIGNER = "UX_DES", "UX designer",
    AI_CONSULTANT = "AI_CONS", "AI Consultant",
    AI_JURIST = "AI_JUR", "AI Jurist",
    RESEARCHER = "RES", "Researcher",
    DATA_ENGINEER = "DAT_ENG", "Data engineer",
    ASSIGNMENT_LEADER = "PROJ_LEAD", "Project leader",

class Colleague(models.Model):
    name = models.CharField(max_length=200)
    skills = MultiSelectField(blank=True, choices=Skills.choices)
    # placements via reversed relation

    @property
    def end_date(self):
        return self.placements.aggregate(Max('end_date'))['end_date__max']

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
    extra_info = models.TextField(blank=True)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE, default='GROUP')

    def get_absolute_url(self):
        return reverse("assignment-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Placement(models.Model):
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='placements', null=True, blank=True) # TODO: removal of colleague triggers removal of placement, probably undesirable
    assignment = models.ForeignKey('Assignment', models.CASCADE, related_name='placements')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    hours_per_week = models.IntegerField(null=True, blank=True)
    skills = MultiSelectField(blank=True, choices=Skills.choices)

    def get_absolute_url(self):
        return reverse("placement-detail", kwargs={"pk": self.pk})


class Service(models.Model):
    assignment = models.ForeignKey('Assignment', models.CASCADE, related_name='services')
    description = models.CharField(max_length=500)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.description} - €{self.cost}"

    def get_absolute_url(self):
        return reverse("service-detail", kwargs={"pk": self.pk})
