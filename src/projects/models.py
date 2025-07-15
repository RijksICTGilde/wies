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

PROJECT_TYPE = {
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
    PROJECT_LEADER = "PROJ_LEAD", "Project leader",

class Colleague(models.Model):
    name = models.CharField(max_length=200)
    skills = MultiSelectField(blank=True, choices=Skills.choices)

    def get_absolute_url(self):
        return reverse("colleague-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

# Create your models here.
class ProjectBase(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)  #TODO: timezone aware?
    end_date = models.DateField(null=True, blank=True)  #TODO: timezone aware?
    # assignments through foreignkey on Assignment
    status = models.CharField(max_length=20, choices=PROJECT_STATUS, default='LEAD')
    organization = models.CharField(blank=True)
    extra_info = models.TextField(blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE, default='GROUP')

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Assignment(models.Model):
    colleague = models.ForeignKey('Colleague', models.CASCADE, related_name='assignments', null=True, blank=True) # TODO: removal of colleague triggers removal of assigment, probably undesirable
    project = models.ForeignKey('ProjectBase', models.CASCADE, related_name='assignments')
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    hours_per_week = models.IntegerField(null=True, blank=True)
    skills = MultiSelectField(blank=True, choices=Skills.choices)

    def get_absolute_url(self):
        return reverse("assignment-detail", kwargs={"pk": self.pk})

class ProjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(project_type='GROUP')

class Project(ProjectBase):
    objects = ProjectManager()

    class Meta:
        proxy = True
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def save(self, *args, **kwargs):
        self.project_type = 'GROUP'
        super().save(*args, **kwargs)

class JobManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(project_type='INDIVIDUAL')

class Job(ProjectBase):
    objects = JobManager()

    class Meta:
        proxy = True
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def save(self, *args, **kwargs):
        self.project_type = 'INDIVIDUAL'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("job-detail", kwargs={"pk": self.pk})
