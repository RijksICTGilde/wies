from django.db import models
from django.urls import reverse


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
    start_date = models.DateField()  #TODO: timezone aware
    colleagues = models.ManyToManyField(Colleague, through='Assignment', related_name='projects')

    def get_absolute_url(self):
        return reverse("project-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

class Assignment(models.Model):
    colleague = models.ForeignKey('Colleague', models.CASCADE) # TODO: removal of colleague triggers removal of assigment, probably undesirable
    project = models.ForeignKey('Project', models.CASCADE)
