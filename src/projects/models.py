from django.db import models
from django.urls import reverse


PROJECT_STATUS = {
    'LEAD': "LEAD",
    'OPEN': "OPEN",
    'LOPEND': "LOPEND",
    'AFGEWEZEN': "AFGEWEZEN",
    'HISTORISCH': "HISTORISCH",
}


class Colleague(models.Model):
    name = models.CharField(max_length=200)
    function = models.CharField(max_length=200)
    # projects through m2m relation

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

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Assignment(models.Model):
    colleague = models.ForeignKey('Colleague', models.CASCADE) # TODO: removal of colleague triggers removal of assigment, probably undesirable
    project = models.ForeignKey('Project', models.CASCADE)
