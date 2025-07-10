from django.db import models
from django.urls import reverse
from multiselectfield import MultiSelectField

PROJECT_STATUS = {
    'LEAD': "LEAD",
    'OPEN': "OPEN",
    'LOPEND': "LOPEND",
    'AFGEWEZEN': "AFGEWEZEN",
    'HISTORISCH': "HISTORISCH",
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
    PROJECT_LEADER = "PROJ_LEAD", "Project leader",

class Colleague(models.Model):
    name = models.CharField(max_length=200)
    skills = MultiSelectField(blank=True, choices=Skills.choices)
    # projects (through m2m relation on Assignment)

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)  #TODO: timezone aware?
    end_date = models.DateField(null=True, blank=True)  #TODO: timezone aware?
    colleagues = models.ManyToManyField(Colleague, through='Assignment', related_name='projects', blank=True)
    status = models.CharField(max_length=20, choices=PROJECT_STATUS, default='LEAD')
    organization = models.CharField(blank=True)
    extra_info = models.TextField(blank=True)
    skills = MultiSelectField(blank=True, choices=Skills.choices)

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Assignment(models.Model):
    colleague = models.ForeignKey('Colleague', models.CASCADE) # TODO: removal of colleague triggers removal of assigment, probably undesirable
    project = models.ForeignKey('Project', models.CASCADE)
